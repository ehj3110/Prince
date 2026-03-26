"""
Material Stiffness Analyzer
============================

Estimates membrane material properties from force-displacement curves.
Uses intelligent data cropping and multiple fitting models to extract stiffness.

Key Features:
- Smart data cropping using 2nd derivative inflection points
- Multiple fit models: linear, exponential, logarithmic, power law
- Goodness-of-fit metrics (R², RMSE, AIC)
- Robust to noisy data
- Scaling analysis with area and radius

Author: Cheng Sun Lab Team
Date: December 3, 2025
"""

import numpy as np
import pandas as pd
from scipy import optimize, stats, signal
from scipy.signal import savgol_filter
from typing import Dict, List, Tuple, Optional
import warnings


class MaterialStiffnessAnalyzer:
    """
    Analyze force-displacement curves to extract material stiffness.
    """
    
    def __init__(self, 
                 derivative_window: int = 11,
                 derivative_polyorder: int = 2,
                 crop_percentile: float = 0.90):
        """
        Initialize the analyzer.
        
        Args:
            derivative_window: Window size for Savitzky-Golay filter (must be odd)
            derivative_polyorder: Polynomial order for smoothing
            crop_percentile: Use middle X% of data between inflection points
        """
        self.derivative_window = derivative_window
        self.derivative_polyorder = derivative_polyorder
        self.crop_percentile = crop_percentile
        
    def analyze_stiffness(self,
                         displacement: np.ndarray,
                         force: np.ndarray,
                         baseline_idx: Optional[int] = None,
                         peak_idx: Optional[int] = None,
                         auto_crop: bool = True) -> Dict:
        """
        Complete stiffness analysis with automatic cropping and multiple fits.
        
        Args:
            displacement: Displacement data in mm
            force: Force data in N
            baseline_idx: Starting index for analysis (if None, uses first point)
            peak_idx: Ending index for analysis (if None, uses point of max force)
            auto_crop: Whether to use 2nd derivative cropping
            
        Returns:
            Dictionary with stiffness estimates from all models and fit quality
        """
        # Extract relevant region
        if baseline_idx is None:
            baseline_idx = 0
        if peak_idx is None:
            peak_idx = np.argmax(force)
            
        disp = displacement[baseline_idx:peak_idx+1].copy()
        force_data = force[baseline_idx:peak_idx+1].copy()
        
        # Ensure data is valid
        if len(disp) < 5:
            return self._empty_result("Insufficient data points")
        
        # Make displacement relative (start at 0)
        disp = disp - disp[0]
        force_data = force_data - force_data[0]  # Baseline correct
        
        # Auto-crop using second derivative if requested
        if auto_crop:
            crop_start, crop_end, inflection_info = self._auto_crop_data(disp, force_data)
            
            if crop_start is not None and crop_end is not None:
                disp_cropped = disp[crop_start:crop_end+1]
                force_cropped = force_data[crop_start:crop_end+1]
                
                # Only use cropped data if we have enough points (at least 30)
                if len(disp_cropped) >= 30:
                    disp = disp_cropped
                    force_data = force_cropped
                    crop_success = True
                else:
                    crop_success = False
                    inflection_info = f"Cropped data too short ({len(disp_cropped)} points), using full data"
            else:
                crop_success = False
                inflection_info = "Auto-crop failed, using full data"
        else:
            crop_success = False
            inflection_info = "Auto-crop disabled"
        
        # Ensure we still have enough data after cropping
        if len(disp) < 5:
            return self._empty_result("Insufficient data after cropping")
        
        # Fit all models
        results = {
            'cropped': crop_success,
            'crop_info': inflection_info,
            'n_points_used': len(disp),
            'displacement_range_mm': (float(disp[0]), float(disp[-1])),
            'force_range_N': (float(force_data[0]), float(force_data[-1]))
        }
        
        # 1. Linear fit: F = k * x
        linear_result = self._fit_linear(disp, force_data)
        results['linear'] = linear_result
        
        # 2. Exponential fit: F = a * (exp(b*x) - 1)
        exponential_result = self._fit_exponential(disp, force_data)
        results['exponential'] = exponential_result
        
        # 3. Logarithmic fit: F = a * log(1 + b*x)
        logarithmic_result = self._fit_logarithmic(disp, force_data)
        results['logarithmic'] = logarithmic_result
        
        # 4. Power law fit: F = a * x^n
        power_law_result = self._fit_power_law(disp, force_data)
        results['power_law'] = power_law_result
        
        # Select best model based on AIC (lower is better)
        best_model = self._select_best_model(results)
        results['best_model'] = best_model
        results['best_stiffness_N_per_mm'] = results[best_model]['stiffness_N_per_mm']
        results['best_r_squared'] = results[best_model]['r_squared']
        
        return results
    
    def _auto_crop_data(self, 
                       displacement: np.ndarray, 
                       force: np.ndarray) -> Tuple[Optional[int], Optional[int], str]:
        """
        Automatically crop data using second derivative analysis.
        
        Finds inflection points at the start (lifting begins) and end (approaching plateau).
        Returns the middle 90% (or specified percentile) of data between these points.
        
        Args:
            displacement: Displacement array
            force: Force array
            
        Returns:
            (start_idx, end_idx, info_string)
        """
        try:
            # Calculate second derivative
            if len(force) < self.derivative_window:
                return None, None, f"Data too short for derivative (need {self.derivative_window} points)"
            
            # Smooth data for better derivative
            force_smooth = savgol_filter(force, 
                                        window_length=self.derivative_window,
                                        polyorder=self.derivative_polyorder)
            
            # Second derivative
            second_deriv = np.gradient(np.gradient(force_smooth, displacement), displacement)
            
            # Find peaks in absolute second derivative (inflection points)
            abs_second_deriv = np.abs(second_deriv)
            
            # Use prominence to find significant inflection points
            peaks, properties = signal.find_peaks(abs_second_deriv, 
                                                 prominence=np.std(abs_second_deriv))
            
            if len(peaks) < 2:
                return None, None, f"Found {len(peaks)} inflection points (need at least 2)"
            
            # Sort by prominence and take top 2
            sorted_peaks = peaks[np.argsort(properties['prominences'])[-2:]]
            sorted_peaks = np.sort(sorted_peaks)  # Order by time
            
            start_inflection = sorted_peaks[0]
            end_inflection = sorted_peaks[-1]
            
            # Calculate crop range (middle X% of data between inflections)
            total_range = end_inflection - start_inflection
            crop_margin = (1.0 - self.crop_percentile) / 2.0
            
            crop_start = int(start_inflection + crop_margin * total_range)
            crop_end = int(end_inflection - crop_margin * total_range)
            
            # Ensure valid range
            crop_start = max(0, crop_start)
            crop_end = min(len(force) - 1, crop_end)
            
            if crop_end <= crop_start:
                return None, None, "Invalid crop range"
            
            info = (f"Inflections at indices {start_inflection}, {end_inflection}; "
                   f"using middle {self.crop_percentile*100:.0f}% ({crop_start}-{crop_end})")
            
            return crop_start, crop_end, info
            
        except Exception as e:
            return None, None, f"Auto-crop error: {str(e)}"
    
    def _fit_linear(self, disp: np.ndarray, force: np.ndarray) -> Dict:
        """
        Linear fit: F = k * x
        
        This represents a simple elastic response where stiffness is constant.
        """
        try:
            # Linear regression through origin (force should be 0 at disp=0)
            slope, intercept, r_value, p_value, std_err = stats.linregress(disp, force)
            
            # For stiffness, we want the slope (N/mm)
            stiffness = abs(slope)
            
            # Predicted values
            force_pred = slope * disp + intercept
            
            # Calculate metrics
            ss_res = np.sum((force - force_pred) ** 2)
            ss_tot = np.sum((force - np.mean(force)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            
            rmse = np.sqrt(np.mean((force - force_pred) ** 2))
            
            # AIC = n*ln(RSS/n) + 2*k where k is number of parameters
            n = len(disp)
            aic = n * np.log(ss_res / n + 1e-10) + 2 * 2  # 2 parameters (slope, intercept)
            
            return {
                'model': 'linear',
                'stiffness_N_per_mm': stiffness,
                'parameters': {'slope': slope, 'intercept': intercept},
                'r_squared': r_squared,
                'rmse': rmse,
                'aic': aic,
                'success': True
            }
            
        except Exception as e:
            return {'model': 'linear', 'success': False, 'error': str(e),
                   'stiffness_N_per_mm': 0.0, 'r_squared': 0.0}
    
    def _fit_exponential(self, disp: np.ndarray, force: np.ndarray) -> Dict:
        """
        Exponential fit: F = a * (exp(b*x) - 1)
        
        This represents strain-stiffening behavior where stiffness increases with deformation.
        Instantaneous stiffness: dF/dx = a*b*exp(b*x)
        Initial stiffness (x→0): k₀ = a*b
        """
        try:
            # Initial guess: a ~ max_force, b ~ 1/mean_disp
            max_force = np.max(force)
            max_disp = np.max(disp)
            mean_disp = np.mean(disp[disp > 0]) if np.any(disp > 0) else 1.0
            
            a_guess = max_force
            b_guess = 1.0 / (mean_disp + 1e-6)
            
            def exp_model(x, a, b):
                return a * (np.exp(b * x) - 1)
            
            # Fit with reasonable bounds
            popt, pcov = optimize.curve_fit(exp_model, disp, force, 
                                           p0=[a_guess, b_guess],
                                           bounds=([max_force*0.1, 0.01], [max_force*10, 100]),
                                           maxfev=10000)
            
            a, b = popt
            
            # Initial stiffness (at x=0)
            stiffness = abs(a * b)
            
            # Predicted values
            force_pred = exp_model(disp, a, b)
            
            # Calculate metrics
            ss_res = np.sum((force - force_pred) ** 2)
            ss_tot = np.sum((force - np.mean(force)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            
            rmse = np.sqrt(np.mean((force - force_pred) ** 2))
            
            n = len(disp)
            aic = n * np.log(ss_res / n + 1e-10) + 2 * 2
            
            return {
                'model': 'exponential',
                'stiffness_N_per_mm': stiffness,  # Initial stiffness
                'parameters': {'a': a, 'b': b},
                'r_squared': r_squared,
                'rmse': rmse,
                'aic': aic,
                'success': True,
                'note': 'Stiffness reported is initial value (at x=0)'
            }
            
        except Exception as e:
            return {'model': 'exponential', 'success': False, 'error': str(e),
                   'stiffness_N_per_mm': 0.0, 'r_squared': 0.0}
    
    def _fit_logarithmic(self, disp: np.ndarray, force: np.ndarray) -> Dict:
        """
        Logarithmic fit: F = a * log(1 + b*x)
        
        This represents strain-softening behavior where stiffness decreases with deformation.
        Instantaneous stiffness: dF/dx = a*b/(1 + b*x)
        Initial stiffness (x→0): k₀ = a*b
        """
        try:
            # Initial guess
            max_force = np.max(force)
            max_disp = np.max(disp)
            mean_disp = np.mean(disp[disp > 0]) if np.any(disp > 0) else 1.0
            
            a_guess = max_force * 2  # Slightly higher for log model
            b_guess = 1.0 / (mean_disp + 1e-6)
            
            def log_model(x, a, b):
                return a * np.log(1 + b * x)
            
            # Fit with reasonable bounds
            popt, pcov = optimize.curve_fit(log_model, disp, force,
                                           p0=[a_guess, b_guess],
                                           bounds=([max_force*0.1, 0.01], [max_force*10, 100]),
                                           maxfev=10000)
            
            a, b = popt
            
            # Initial stiffness (at x=0)
            stiffness = abs(a * b)
            
            # Predicted values
            force_pred = log_model(disp, a, b)
            
            # Calculate metrics
            ss_res = np.sum((force - force_pred) ** 2)
            ss_tot = np.sum((force - np.mean(force)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            
            rmse = np.sqrt(np.mean((force - force_pred) ** 2))
            
            n = len(disp)
            aic = n * np.log(ss_res / n + 1e-10) + 2 * 2
            
            return {
                'model': 'logarithmic',
                'stiffness_N_per_mm': stiffness,  # Initial stiffness
                'parameters': {'a': a, 'b': b},
                'r_squared': r_squared,
                'rmse': rmse,
                'aic': aic,
                'success': True,
                'note': 'Stiffness reported is initial value (at x=0)'
            }
            
        except Exception as e:
            return {'model': 'logarithmic', 'success': False, 'error': str(e),
                   'stiffness_N_per_mm': 0.0, 'r_squared': 0.0}
    
    def _fit_power_law(self, disp: np.ndarray, force: np.ndarray) -> Dict:
        """
        Power law fit: F = a * x^n
        
        This is a generalized form that can represent various behaviors:
        - n = 1: Linear (constant stiffness)
        - n > 1: Strain-stiffening
        - n < 1: Strain-softening
        
        Instantaneous stiffness: dF/dx = a*n*x^(n-1)
        Initial stiffness depends on n (undefined for n<1 at x=0)
        """
        try:
            # Avoid log of zero by filtering out x=0
            valid_idx = disp > 1e-6
            if np.sum(valid_idx) < 5:
                return {'model': 'power_law', 'success': False, 
                       'error': 'Insufficient non-zero displacement data',
                       'stiffness_N_per_mm': 0.0, 'r_squared': 0.0}
            
            disp_valid = disp[valid_idx]
            force_valid = force[valid_idx]
            
            # Also filter negative forces for log fitting
            positive_force_idx = force_valid > 1e-6
            if np.sum(positive_force_idx) < 5:
                return {'model': 'power_law', 'success': False,
                       'error': 'Insufficient positive force data',
                       'stiffness_N_per_mm': 0.0, 'r_squared': 0.0}
            
            disp_valid = disp_valid[positive_force_idx]
            force_valid = force_valid[positive_force_idx]
            
            # Log-log linear regression: log(F) = log(a) + n*log(x)
            log_disp = np.log(disp_valid)
            log_force = np.log(force_valid)
            
            n, log_a, r_value, p_value, std_err = stats.linregress(log_disp, log_force)
            a = np.exp(log_a)
            
            # Effective stiffness at median displacement
            median_disp = np.median(disp_valid)
            if n >= 1:
                # Stiffness is well-defined
                stiffness = abs(a * n * median_disp**(n-1))
            else:
                # For n<1, report "effective" stiffness at median point
                stiffness = abs(a * n * median_disp**(n-1))
            
            # Predicted values (on full data)
            force_pred = a * disp_valid**n
            
            # Calculate metrics
            ss_res = np.sum((force_valid - force_pred) ** 2)
            ss_tot = np.sum((force_valid - np.mean(force_valid)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            
            rmse = np.sqrt(np.mean((force_valid - force_pred) ** 2))
            
            n_points = len(disp_valid)
            aic = n_points * np.log(ss_res / n_points + 1e-10) + 2 * 2
            
            return {
                'model': 'power_law',
                'stiffness_N_per_mm': stiffness,  # At median displacement
                'parameters': {'a': a, 'n': n},
                'r_squared': r_squared,
                'rmse': rmse,
                'aic': aic,
                'success': True,
                'note': f'Stiffness at median displacement ({median_disp:.3f} mm); n={n:.3f}'
            }
            
        except Exception as e:
            return {'model': 'power_law', 'success': False, 'error': str(e),
                   'stiffness_N_per_mm': 0.0, 'r_squared': 0.0}
    
    def _select_best_model(self, results: Dict) -> str:
        """
        Select best model based on AIC (Akaike Information Criterion).
        Lower AIC indicates better model considering both fit quality and complexity.
        """
        models = ['linear', 'exponential', 'logarithmic', 'power_law']
        valid_models = [m for m in models if results[m]['success']]
        
        if not valid_models:
            return 'linear'  # Default fallback
        
        # Find model with lowest AIC
        best_model = min(valid_models, key=lambda m: results[m]['aic'])
        
        return best_model
    
    def _empty_result(self, reason: str) -> Dict:
        """Return empty result dictionary with error message."""
        return {
            'error': reason,
            'cropped': False,
            'crop_info': reason,
            'n_points_used': 0,
            'best_model': 'none',
            'best_stiffness_N_per_mm': 0.0,
            'best_r_squared': 0.0,
            'linear': {'success': False, 'stiffness_N_per_mm': 0.0, 'r_squared': 0.0},
            'exponential': {'success': False, 'stiffness_N_per_mm': 0.0, 'r_squared': 0.0},
            'logarithmic': {'success': False, 'stiffness_N_per_mm': 0.0, 'r_squared': 0.0},
            'power_law': {'success': False, 'stiffness_N_per_mm': 0.0, 'r_squared': 0.0}
        }
    
    def add_to_dataframe(self, 
                        df: pd.DataFrame,
                        displacement_col: str = 'displacement_array',
                        force_col: str = 'force_array',
                        baseline_col: str = 'baseline_idx',
                        peak_col: str = 'peak_idx') -> pd.DataFrame:
        """
        Add stiffness analysis to dataframe with array columns.
        
        Args:
            df: DataFrame with force/displacement arrays
            displacement_col: Name of column containing displacement arrays
            force_col: Name of column containing force arrays
            baseline_col: Name of column with baseline indices
            peak_col: Name of column with peak indices
            
        Returns:
            DataFrame with additional stiffness columns
        """
        results_list = []
        
        for idx, row in df.iterrows():
            disp = row[displacement_col]
            force = row[force_col]
            baseline_idx = int(row[baseline_col]) if baseline_col in df.columns else None
            peak_idx = int(row[peak_col]) if peak_col in df.columns else None
            
            result = self.analyze_stiffness(disp, force, baseline_idx, peak_idx)
            results_list.append(result)
        
        # Add main results
        df['material_stiffness_N_per_mm'] = [r['best_stiffness_N_per_mm'] for r in results_list]
        df['material_stiffness_model'] = [r['best_model'] for r in results_list]
        df['material_stiffness_r_squared'] = [r['best_r_squared'] for r in results_list]
        df['stiffness_data_cropped'] = [r['cropped'] for r in results_list]
        
        # Add all model results
        for model in ['linear', 'exponential', 'logarithmic', 'power_law']:
            df[f'stiffness_{model}_N_per_mm'] = [
                r[model]['stiffness_N_per_mm'] if r[model]['success'] else np.nan 
                for r in results_list
            ]
            df[f'stiffness_{model}_r_squared'] = [
                r[model]['r_squared'] if r[model]['success'] else np.nan
                for r in results_list
            ]
        
        return df


# Example usage and testing
if __name__ == "__main__":
    print("Material Stiffness Analyzer - Test Mode")
    print("=" * 60)
    
    # Create synthetic data
    np.random.seed(42)
    
    # Test 1: Linear elastic material
    print("\nTest 1: Linear Elastic Material")
    disp_linear = np.linspace(0, 2, 100)  # mm
    force_linear = 0.5 * disp_linear + np.random.normal(0, 0.01, 100)  # 0.5 N/mm stiffness
    
    analyzer = MaterialStiffnessAnalyzer()
    result = analyzer.analyze_stiffness(disp_linear, force_linear, auto_crop=False)
    
    print(f"  Best model: {result['best_model']}")
    print(f"  Stiffness: {result['best_stiffness_N_per_mm']:.4f} N/mm (expected: 0.5)")
    print(f"  R²: {result['best_r_squared']:.4f}")
    
    # Test 2: Exponential strain-stiffening
    print("\nTest 2: Strain-Stiffening Material")
    disp_exp = np.linspace(0, 2, 100)
    force_exp = 0.3 * (np.exp(0.8 * disp_exp) - 1) + np.random.normal(0, 0.01, 100)
    
    result = analyzer.analyze_stiffness(disp_exp, force_exp, auto_crop=False)
    
    print(f"  Best model: {result['best_model']}")
    print(f"  Initial stiffness: {result['best_stiffness_N_per_mm']:.4f} N/mm")
    print(f"  R²: {result['best_r_squared']:.4f}")
    
    # Test 3: With auto-cropping
    print("\nTest 3: Auto-Cropping Test")
    # Add noise at beginning and plateau at end
    disp_noisy = np.linspace(0, 3, 150)
    force_noisy = np.zeros(150)
    force_noisy[20:100] = 0.4 * disp_noisy[20:100] + np.random.normal(0, 0.01, 80)
    force_noisy[100:] = force_noisy[99] + np.random.normal(0, 0.01, 50)  # Plateau
    
    result = analyzer.analyze_stiffness(disp_noisy, force_noisy, auto_crop=True)
    
    print(f"  Cropping: {result['cropped']}")
    print(f"  Crop info: {result['crop_info']}")
    print(f"  Points used: {result['n_points_used']}/150")
    print(f"  Best model: {result['best_model']}")
    print(f"  Stiffness: {result['best_stiffness_N_per_mm']:.4f} N/mm")
    
    print("\n" + "=" * 60)
    print("All tests completed!")
