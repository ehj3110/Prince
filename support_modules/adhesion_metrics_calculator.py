"""
Adhesion Metrics Calculator
===========================

Unified calculator for adhesion metrics during DLP resin 3D printing.
Implements the exact methodology defined in WORK_OF_ADHESION_METRICS_DEFINITIONS.md

This calculator can work with:
- Live data arrays during printing
- Saved CSV files for post-processing
- Pandas DataFrames for batch analysis

Author: Cheng Sun Lab Team
Date: September 19, 2025
"""

import numpy as np
import pandas as pd
from scipy import integrate
from scipy.signal import savgol_filter, medfilt
import warnings
from typing import Dict, Tuple, Optional, Union
from pathlib import Path


class AdhesionMetricsCalculator:
    """
    Unified calculator for adhesion metrics using a reverse-search, second-derivative
    propagation end detection method and two-step filtering (Median + Savitzky-Golay).
    """
    
    def __init__(self, 
                 median_kernel=5,
                 savgol_window=9,
                 savgol_order=2,
                 baseline_threshold_factor=0.002,
                 min_peak_height=0.01,
                 min_peak_distance=50):
        """
        Initialize the adhesion metrics calculator. 
        
        Args:
            median_kernel (int): Kernel size for median filter (must be odd, for outlier rejection).
            savgol_window (int): Window length for Savitzky-Golay filter (must be odd).
            savgol_order (int): Polynomial order for Savitzky-Golay filter.
            baseline_threshold_factor (float): Threshold above baseline for initiation detection (N).
            min_peak_height (float): Minimum peak height for detection (N).
            min_peak_distance (int): Minimum distance between peaks (data points).
        """
        self.median_kernel = median_kernel if median_kernel % 2 == 1 else median_kernel + 1
        self.savgol_window = savgol_window if savgol_window % 2 == 1 else savgol_window + 1
        self.savgol_order = savgol_order
        self.baseline_threshold_factor = baseline_threshold_factor
        self.min_peak_height = min_peak_height
        self.min_peak_distance = min_peak_distance
        
    def calculate_from_arrays(self, 
                            time_data: np.ndarray, 
                            position_data: np.ndarray, 
                            force_data: np.ndarray,
                            layer_number: Optional[int] = None,
                            motion_end_idx: Optional[int] = None) -> Dict:
        """
        Calculate adhesion metrics from numpy arrays (live data or pre-loaded).
        
        Args:
            time_data: Time values (seconds).
            position_data: Position values (mm).
            force_data: Force values (N).
            layer_number: Layer identifier (optional).
            motion_end_idx: Index where stage motion ends (optional, uses full data if None).
            
        Returns:
            Dictionary containing all calculated metrics.
        """
        # Convert to numpy arrays and validate
        times = np.asarray(time_data)
        positions = np.asarray(position_data)
        forces = np.asarray(force_data)
        
        if len(times) != len(positions) or len(times) != len(forces):
            raise ValueError("Time, position, and force arrays must have the same length")
            
        if len(times) < 10:
            return self._empty_results(layer_number)
            
        # Remove any NaN or infinite values
        valid_mask = np.isfinite(times) & np.isfinite(positions) & np.isfinite(forces)
        times = times[valid_mask]
        positions = positions[valid_mask]
        forces = forces[valid_mask]
        
        if len(times) < 10:
            return self._empty_results(layer_number)
            
        # Apply smoothing using Gaussian filter
        smoothed_force = self._apply_smoothing(forces)
        
        # Calculate metrics using the new methodology
        return self._calculate_metrics(times, positions, forces, smoothed_force, 
                                     layer_number, motion_end_idx)
    
    def calculate_from_csv(self, 
                          csv_filepath: Union[str, Path],
                          time_col: str = 'Time',
                          position_col: str = 'Position', 
                          force_col: str = 'Force',
                          layer_number: Optional[int] = None) -> Dict:
        """
        Calculate adhesion metrics from a CSV file.
        
        Args:
            csv_filepath: Path to CSV file.
            time_col: Name of time column.
            position_col: Name of position column.
            force_col: Name of force column.
            layer_number: Layer identifier (optional).
            
        Returns:
            Dictionary containing all calculated metrics.
        """
        try:
            df = pd.read_csv(csv_filepath)
            return self.calculate_from_dataframe(df, time_col, position_col, force_col, layer_number)
        except Exception as e:
            print(f"Error reading CSV file {csv_filepath}: {e}")
            return self._empty_results(layer_number)
    
    def calculate_from_dataframe(self, 
                               df: pd.DataFrame,
                               time_col: str = 'Time',
                               position_col: str = 'Position',
                               force_col: str = 'Force',
                               layer_number: Optional[int] = None) -> Dict:
        """
        Calculate adhesion metrics from a pandas DataFrame.
        
        Args:
            df: DataFrame with time, position, force data.
            time_col: Name of time column.
            position_col: Name of position column.  
            force_col: Name of force column.
            layer_number: Layer identifier (optional).
            
        Returns:
            Dictionary containing all calculated metrics.
        """
        try:
            # Extract data arrays
            time_data = df[time_col].values
            position_data = df[position_col].values
            force_data = df[force_col].values
            
            return self.calculate_from_arrays(time_data, position_data, force_data, layer_number)
        except KeyError as e:
            print(f"Column not found in DataFrame: {e}")
            return self._empty_results(layer_number)
        except Exception as e:
            print(f"Error processing DataFrame: {e}")
            return self._empty_results(layer_number)
    
    def _apply_smoothing(self, force_data: np.ndarray) -> np.ndarray:
        """
        Apply two-step filtering: Median filter for outlier rejection, then Savitzky-Golay for smoothing.
        
        This is the optimal filtering approach determined through comprehensive testing.
        - Step 1: Median filter (kernel=5) removes sharp outlier peaks
        - Step 2: Savitzky-Golay filter (window=9, order=2) smooths while preserving peak shape
        
        Args:
            force_data: Raw force data.
            
        Returns:
            Smoothed force data.
        """
        if len(force_data) < max(self.median_kernel, self.savgol_window):
            return force_data.copy()
            
        try:
            # Step 1: Median filter for outlier rejection (removes sharp spikes)
            median_filtered = medfilt(force_data, kernel_size=self.median_kernel)
            
            # Step 2: Savitzky-Golay filter for smoothing (preserves peak shape)
            smoothed = savgol_filter(median_filtered, 
                                    window_length=self.savgol_window,
                                    polyorder=self.savgol_order)
            return smoothed
        except Exception as e:
            warnings.warn(f"Two-step filtering failed: {e}. Using raw data.")
            return force_data.copy()
    
    def _calculate_metrics(self, 
                         times: np.ndarray, 
                         positions: np.ndarray, 
                         forces: np.ndarray, 
                         smoothed_force: np.ndarray,
                         layer_number: Optional[int],
                         motion_end_idx: Optional[int]) -> Dict:
        """
        Calculate all adhesion metrics using the new methodology.
        """
        results = {'layer_number': layer_number}
        
        # Step 1: Find peak force
        peak_idx, peak_force = self._find_peak_force(smoothed_force)
        results['peak_force'] = peak_force
        results['peak_force_position'] = positions[peak_idx]
        results['peak_force_time'] = times[peak_idx] - times[0]  # Relative time
        
        # Step 2: Find propagation end using the new reverse search method
        prop_end_idx = self._find_propagation_end_reverse_search(
            smoothed_force, peak_idx, positions, motion_end_idx)
        results['propagation_end_position'] = positions[prop_end_idx]
        results['propagation_end_time'] = times[prop_end_idx] - times[0]
        
        # Step 3: Calculate baseline using force at propagation end
        baseline = self._calculate_baseline(smoothed_force, prop_end_idx)
        results['baseline_force'] = baseline
        results['peak_force_corrected'] = peak_force - baseline
        
        # Step 4: Find pre-initiation start
        pre_init_idx = self._find_pre_initiation(smoothed_force, peak_idx, baseline)
        results['pre_initiation_position'] = positions[pre_init_idx]
        results['pre_initiation_time'] = times[pre_init_idx] - times[0]
        results['pre_initiation_force'] = smoothed_force[pre_init_idx]
        
        # Step 5: Calculate temporal metrics
        results['pre_initiation_duration'] = times[peak_idx] - times[pre_init_idx]
        results['propagation_duration'] = times[prop_end_idx] - times[peak_idx]
        results['total_peel_duration'] = times[prop_end_idx] - times[pre_init_idx]
        
        # Step 6: Calculate spatial metrics
        results['pre_initiation_distance'] = positions[peak_idx] - positions[pre_init_idx]
        results['propagation_distance'] = positions[prop_end_idx] - positions[peak_idx]
        results['total_peel_distance'] = positions[prop_end_idx] - positions[pre_init_idx]
        
        # Step 7: Calculate work and energy metrics
        work_metrics = self._calculate_work_metrics(
            positions, forces, smoothed_force, baseline, pre_init_idx, peak_idx, prop_end_idx)
        results.update(work_metrics)
        
         # Step 8: Calculate effective stiffness from pre-initiation stage
        stiffness_metrics = self._calculate_stiffness(
            positions, forces, smoothed_force, baseline, pre_init_idx, peak_idx)
        results.update(stiffness_metrics)
        
        # Step 9: Calculate dynamic metrics
        dynamic_metrics = self._calculate_dynamic_metrics(
            times, forces, smoothed_force, pre_init_idx, peak_idx, prop_end_idx)
        results.update(dynamic_metrics)
        
        # Step 10: Calculate data quality metrics
        quality_metrics = self._calculate_quality_metrics(forces, smoothed_force, baseline, peak_force)
        results.update(quality_metrics)
        
        return results
    
    def _calculate_baseline(self, smoothed_force: np.ndarray, prop_end_idx: int) -> float:
        """
        Calculate baseline using force at propagation end point.
        This is the force registered when crack propagation stops.
        """
        return smoothed_force[prop_end_idx]
    
    def _find_peak_force(self, smoothed_force: np.ndarray) -> Tuple[int, float]:
        """
        Find peak force index and value.
        """
        peak_idx = np.argmax(smoothed_force)
        peak_force = smoothed_force[peak_idx]
        return peak_idx, peak_force
    
    def _find_pre_initiation(self, smoothed_force: np.ndarray, peak_idx: int, baseline: float) -> int:
        """
        Find pre-initiation start - the point where force crosses baseline.
        
        Searches backwards from peak to find where force equals baseline (within tolerance).
        This represents the moment when adhesion forces begin to develop.
        
        Special case for sandwich data: If the force starts HIGHER than baseline
        (indicating pre-existing adhesion), use the beginning of the data as the
        pre-initiation point.
        
        Args:
            smoothed_force: Smoothed force array
            peak_idx: Index of peak force
            baseline: Baseline force level
            
        Returns:
            Index where force crosses baseline before peak
        """
        # Small tolerance for numerical comparison (0.1% of baseline or minimum 0.001 N)
        tolerance = max(abs(baseline) * 0.001, 0.001)
        
        # Search backwards from peak to find baseline crossing
        search_start = max(0, peak_idx - 300)  # Limit search range
        
        # Special case: Check if the force at the beginning is already above baseline
        # This happens with sandwich data where adhesion exists before lifting starts
        if smoothed_force[search_start] > (baseline + tolerance):
            # Force starts above baseline - use the beginning as pre-initiation
            return search_start
        
        for i in range(peak_idx - 1, search_start, -1):
            # Check if force is at or below baseline (within tolerance)
            if smoothed_force[i] <= (baseline + tolerance):
                return i  # Return the baseline crossing point
                
        # If no crossing found, return search start
        return search_start

    def _find_propagation_end_reverse_search(self, 
                                           smoothed_force: np.ndarray, 
                                           peak_idx: int,
                                           positions: np.ndarray,
                                           motion_end_idx: Optional[int]) -> int:
        """
        Find propagation end using second derivative 10% threshold method.
        
        Method:
        1. Find the HIGHEST POSITIVE PEAK of the second derivative after peak force
        2. Calculate 10% threshold of that peak value
        3. Find the LAST point BEFORE the derivative drops below this threshold
        4. This is where propagation ends
        
        Physical meaning: The highest positive 2nd derivative peak is where force is 
        decaying fastest. The 10% threshold marks when the decay rate has diminished
        to just 10% of its maximum, indicating propagation has essentially completed.
        Using the last point BEFORE crossing ensures we capture the full propagation zone.
        """
        # 1. Define the full search region from the peak to the end of motion
        search_start_abs = peak_idx
        search_end_abs = motion_end_idx if motion_end_idx is not None else len(smoothed_force) - 1
        
        if (search_end_abs - search_start_abs) < 10:
            return search_end_abs  # Not enough data, return end of motion

        # 2. Determine the "80% point in lifting stage" for position constraint
        try:
            travel_positions = positions[search_start_abs:search_end_abs]
            if len(travel_positions) > 0:
                # Find the minimum position (maximum travel point)
                min_pos = np.min(travel_positions)
                max_pos = positions[peak_idx]
                
                # 80% of the lifting distance
                target_position = max_pos - 0.8 * (max_pos - min_pos)
                
                # Find index where position first reaches or passes the 80% point
                lifting_80pct_idx = search_start_abs
                for i in range(search_start_abs, search_end_abs):
                    if positions[i] <= target_position:
                        lifting_80pct_idx = i
                        break
                else:
                    # If never reached 80%, use the minimum position index
                    min_pos_relative_idx = np.argmin(travel_positions)
                    lifting_80pct_idx = search_start_abs + min_pos_relative_idx
            else:
                lifting_80pct_idx = search_end_abs
        except Exception:
            lifting_80pct_idx = search_end_abs

        # 3. Calculate second derivative for the region of interest
        try:
            # Region is from peak to 80% lifting point
            region_of_interest = smoothed_force[peak_idx:lifting_80pct_idx+1]
            if len(region_of_interest) < 5:
                return lifting_80pct_idx

            # Calculate second derivative using np.gradient
            second_derivative = np.gradient(np.gradient(region_of_interest))
            
            # 4. Find the HIGHEST POSITIVE PEAK of the second derivative
            # Only consider positive values
            positive_mask = second_derivative > 0
            if not np.any(positive_mask):
                # No positive peaks found, use the maximum value
                max_second_deriv_idx = np.argmax(second_derivative)
                max_second_deriv_value = second_derivative[max_second_deriv_idx]
            else:
                # Find the index of the maximum among positive values
                positive_second_deriv = second_derivative.copy()
                positive_second_deriv[~positive_mask] = -np.inf
                max_second_deriv_idx = np.argmax(positive_second_deriv)
                max_second_deriv_value = second_derivative[max_second_deriv_idx]
            
            # 5. Calculate 10% threshold and find LAST point BEFORE crossing
            threshold = max_second_deriv_value * 0.10
            
            # Search forward from the maximum to find where it drops below threshold
            threshold_idx = None
            for i in range(max_second_deriv_idx + 1, len(second_derivative)):
                if second_derivative[i] < threshold:
                    # Found the crossing point - return the PREVIOUS index
                    # (last point before it drops below threshold)
                    threshold_idx = max(0, i - 1)
                    break
            
            # If no threshold crossing found, use a conservative estimate
            if threshold_idx is None:
                # Use a point that's halfway from max to end
                threshold_idx = max_second_deriv_idx + int(0.5 * (len(second_derivative) - max_second_deriv_idx))
            
            # Convert back to absolute index in the original array
            propagation_end_idx = peak_idx + threshold_idx
            
            # Ensure we don't exceed the 80% lifting point
            propagation_end_idx = min(propagation_end_idx, lifting_80pct_idx)
            
            return propagation_end_idx

        except Exception as e:
            warnings.warn(f"Second derivative 10% threshold search failed: {e}. Using 80% lifting point as fallback.")
            return lifting_80pct_idx
    
    def _calculate_work_metrics(self, 
                              positions: np.ndarray, 
                              forces: np.ndarray, 
                              smoothed_force: np.ndarray,
                              baseline: float,
                              pre_init_idx: int,
                              peak_idx: int,
                              prop_end_idx: int) -> Dict:
        """
        Calculate work and energy metrics.
        
        Work of adhesion is integrated from PEAK FORCE to PROPAGATION END
        (not from pre-initiation start).
        """
        results = {}
        
        # Extract peel region data - FROM PEAK TO PROPAGATION END
        peel_positions = positions[peak_idx:prop_end_idx+1]
        peel_forces = forces[peak_idx:prop_end_idx+1]
        peel_forces_corrected = peel_forces - baseline
        
        if len(peel_positions) < 2:
            results.update({
                'work_of_adhesion_mJ': 0.0,
                'work_of_adhesion_corrected_mJ': 0.0,
                'energy_dissipation_mJ': 0.0,
                'total_energy_mJ': 0.0,
                'energy_density_mJ_per_mm': 0.0
            })
            return results
        
        # Convert positions to meters for work calculation
        peel_positions_m = peel_positions / 1000.0
        
        # Ensure positions are in increasing order for integration
        if np.any(np.diff(peel_positions_m) <= 0):
            warnings.warn("Peel positions are not in increasing order. Sorting may be required.")
            sorted_indices = np.argsort(peel_positions_m)
            peel_positions_m = peel_positions_m[sorted_indices]
            peel_forces = peel_forces[sorted_indices]
            peel_forces_corrected = peel_forces_corrected[sorted_indices]
        
        try:
            # Work of adhesion (trapezoidal integration)
            work_J = np.trapz(peel_forces, peel_positions_m)
            results['work_of_adhesion_mJ'] = work_J * 1000
            
            # Baseline-corrected work
            work_corrected_J = np.trapz(peel_forces_corrected, peel_positions_m)
            results['work_of_adhesion_corrected_mJ'] = work_corrected_J * 1000
            
            # Energy dissipation (negative work regions)
            negative_forces = np.minimum(peel_forces_corrected, 0)
            dissipation_J = np.trapz(np.abs(negative_forces), peel_positions_m)
            results['energy_dissipation_mJ'] = dissipation_J * 1000
            
            # Total energy
            total_energy_J = np.trapz(np.abs(peel_forces_corrected), peel_positions_m)
            results['total_energy_mJ'] = total_energy_J * 1000
            
            # Energy density
            total_distance = np.max(peel_positions) - np.min(peel_positions)
            if total_distance > 0:
                results['energy_density_mJ_per_mm'] = (work_corrected_J * 1000) / total_distance
            else:
                results['energy_density_mJ_per_mm'] = 0.0
                
        except Exception as e:
            warnings.warn(f"Work calculation failed: {e}")
            results.update({
                'work_of_adhesion_mJ': 0.0,
                'work_of_adhesion_corrected_mJ': 0.0,
                'energy_dissipation_mJ': 0.0,
                'total_energy_mJ': 0.0,
                'energy_density_mJ_per_mm': 0.0
            })
        
        return results
    
    def _calculate_stiffness(self,
                           positions: np.ndarray,
                           forces: np.ndarray,
                           smoothed_force: np.ndarray,
                           baseline: float,
                           pre_init_idx: int,
                           peak_idx: int) -> Dict:
        """
        Calculate effective stiffness from the pre-initiation stage.
        
        Uses the first 50% of the pre-initiation data (most linear region)
        to calculate stiffness as the slope of the force-position curve.
        
        Returns:
            Dict with stiffness metrics in N/mm
        """
        results = {}
        
        try:
            # Extract pre-initiation region
            pre_init_positions = positions[pre_init_idx:peak_idx+1]
            pre_init_forces = smoothed_force[pre_init_idx:peak_idx+1]
            
            # Baseline-correct the forces
            pre_init_forces_corrected = pre_init_forces - baseline
            
            # Use only the first 50% of the pre-initiation data (most linear)
            half_length = len(pre_init_positions) // 2
            if half_length < 3:
                # Not enough data points for reliable linear fit
                results['effective_stiffness_N_per_mm'] = 0.0
                results['stiffness_r_squared'] = 0.0
                return results
            
            linear_positions = pre_init_positions[:half_length]
            linear_forces = pre_init_forces_corrected[:half_length]
            
            # Perform linear regression: F = k * x + b
            # where k is the stiffness (slope)
            from scipy import stats
            slope, intercept, r_value, p_value, std_err = stats.linregress(linear_positions, linear_forces)
            
            # Stiffness is the absolute value of the slope (N/mm)
            # Note: slope will be negative (force decreases as position increases during retraction)
            results['effective_stiffness_N_per_mm'] = abs(slope)
            results['stiffness_r_squared'] = r_value ** 2  # Coefficient of determination
            
        except Exception as e:
            warnings.warn(f"Stiffness calculation failed: {e}")
            results.update({
                'effective_stiffness_N_per_mm': 0.0,
                'stiffness_r_squared': 0.0
            })
        
        return results
    
    def _calculate_dynamic_metrics(self, 
                                 times: np.ndarray, 
                                 forces: np.ndarray, 
                                 smoothed_force: np.ndarray,
                                 pre_init_idx: int, 
                                 peak_idx: int, 
                                 prop_end_idx: int) -> Dict:
        """
        Calculate dynamic analysis metrics.
        """
        results = {}
        
        try:
            # Calculate force gradients
            force_gradient = np.gradient(smoothed_force, times)
            
            # Loading phase (pre-initiation to peak)
            loading_gradients = force_gradient[pre_init_idx:peak_idx+1]
            if len(loading_gradients) > 0:
                results['max_loading_rate_N_per_s'] = np.max(loading_gradients)
            else:
                results['max_loading_rate_N_per_s'] = 0.0
            
            # Unloading phase (peak to propagation end)
            unloading_gradients = force_gradient[peak_idx:prop_end_idx+1]
            if len(unloading_gradients) > 0:
                results['max_unloading_rate_N_per_s'] = np.abs(np.min(unloading_gradients))
            else:
                results['max_unloading_rate_N_per_s'] = 0.0
                
        except Exception as e:
            warnings.warn(f"Dynamic metrics calculation failed: {e}")
            results.update({
                'max_loading_rate_N_per_s': 0.0,
                'max_unloading_rate_N_per_s': 0.0
            })
        
        return results
    
    def _calculate_quality_metrics(self, 
                                 forces: np.ndarray, 
                                 smoothed_force: np.ndarray,
                                 baseline: float, 
                                 peak_force: float) -> Dict:
        """
        Calculate data quality metrics.
        """
        results = {}
        
        try:
            # Force noise analysis
            force_noise = forces - smoothed_force
            noise_std = np.std(force_noise)
            
            # Signal-to-noise ratio
            signal_amplitude = peak_force - baseline
            if noise_std > 0:
                snr = signal_amplitude / noise_std
            else:
                snr = float('inf')
            
            results['force_noise_std'] = noise_std
            results['signal_to_noise_ratio'] = snr
            
        except Exception as e:
            warnings.warn(f"Quality metrics calculation failed: {e}")
            results.update({
                'force_noise_std': 0.0,
                'signal_to_noise_ratio': 0.0
            })
        
        return results
    
    def _empty_results(self, layer_number: Optional[int] = None) -> Dict:
        """
        Return empty results structure for invalid data.
        """
        return {
            'layer_number': layer_number,
            'baseline_force': 0.0,
            'peak_force': 0.0,
            'peak_force_corrected': 0.0,
            'peak_force_position': 0.0,
            'peak_force_time': 0.0,
            'pre_initiation_position': 0.0,
            'pre_initiation_time': 0.0,
            'pre_initiation_force': 0.0,
            'propagation_end_position': 0.0,
            'propagation_end_time': 0.0,
            'pre_initiation_duration': 0.0,
            'propagation_duration': 0.0,
            'total_peel_duration': 0.0,
            'pre_initiation_distance': 0.0,
            'propagation_distance': 0.0,
            'total_peel_distance': 0.0,
            'work_of_adhesion_mJ': 0.0,
            'work_of_adhesion_corrected_mJ': 0.0,
            'energy_dissipation_mJ': 0.0,
            'total_energy_mJ': 0.0,
            'energy_density_mJ_per_mm': 0.0,
            'max_loading_rate_N_per_s': 0.0,
            'max_unloading_rate_N_per_s': 0.0,
            'force_noise_std': 0.0,
            'signal_to_noise_ratio': 0.0
        }
    
    def format_results_for_csv(self, results: Dict, precision: int = 4) -> Dict:
        """
        Format results for CSV output with specified precision.
        
        Args:
            results: Dictionary of calculated metrics
            precision: Number of decimal places
            
        Returns:
            Dictionary with formatted values
        """
        formatted = {}
        
        for key, value in results.items():
            if key == 'layer_number' and value is not None:
                formatted[key] = int(value)
            elif isinstance(value, (int, float)):
                if np.isnan(value) or np.isinf(value):
                    formatted[key] = "NaN"
                else:
                    formatted[key] = round(float(value), precision)
            else:
                formatted[key] = value
                
        return formatted


# Example usage and testing functions
if __name__ == "__main__":
    # Test the calculator with simulated data
    print("Testing Adhesion Metrics Calculator...")
    
    # Create test data
    t = np.linspace(0, 2.0, 200)  # 2 seconds, 100 Hz sampling
    pos = 10 + t * 2  # Moving from 10mm to 14mm
    
    # Simulate realistic peeling force curve
    force = np.zeros_like(t)
    for i, time in enumerate(t):
        if time < 0.3:
            force[i] = 0.01  # Baseline
        elif time < 1.0:
            force[i] = 0.01 + 0.3 * (time - 0.3)  # Gradual increase
        elif time < 1.2:
            force[i] = 0.22 - 0.15 * (time - 1.0)  # Peak and drop
        else:
            force[i] = 0.07 - 0.075 * (time - 1.2)  # Return to baseline
    
    # Add some noise
    force += np.random.normal(0, 0.005, len(t))
    force = np.maximum(force, 0)  # Ensure non-negative
    
    # Test the calculator
    calculator = AdhesionMetricsCalculator()
    results = calculator.calculate_from_arrays(t, pos, force, layer_number=1)
    
    # Display results
    print("\nCalculated Metrics:")
    print("=" * 40)
    formatted_results = calculator.format_results_for_csv(results)
    for key, value in formatted_results.items():
        print(f"{key}: {value}")
    
    print(f"\nTest completed successfully!")
