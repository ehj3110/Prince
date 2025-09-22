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
from scipy.signal import savgol_filter
from scipy import integrate
import warnings
from typing import Dict, Tuple, Optional, Union
from pathlib import Path


class AdhesionMetricsCalculator:
    """
    Unified calculator for adhesion metrics using second derivative propagation end detection
    and current Savitzky-Golay smoothing methodology.
    """
    
    def __init__(self, 
                 smoothing_window=3, 
                 smoothing_polyorder=1,
                 baseline_threshold_factor=0.002,
                 min_peak_height=0.01,
                 min_peak_distance=50):
        """
        Initialize the adhesion metrics calculator.
        
        Args:
            smoothing_window (int): Savitzky-Golay window length (must be odd) - using light smoothing
            smoothing_polyorder (int): Polynomial order for smoothing - using linear
            baseline_threshold_factor (float): Threshold above baseline for initiation detection (N)
            min_peak_height (float): Minimum peak height for detection (N)
            min_peak_distance (int): Minimum distance between peaks (data points)
        """
        self.smoothing_window = smoothing_window if smoothing_window % 2 == 1 else smoothing_window + 1
        self.smoothing_polyorder = smoothing_polyorder
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
            time_data: Time values (seconds)
            position_data: Position values (mm)
            force_data: Force values (N)
            layer_number: Layer identifier (optional)
            motion_end_idx: Index where stage motion ends (optional, uses full data if None)
            
        Returns:
            Dictionary containing all calculated metrics
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
            
        # Apply smoothing using current methodology
        smoothed_force = self._apply_smoothing(forces)
        
        # Calculate metrics using current methodology
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
            csv_filepath: Path to CSV file
            time_col: Name of time column
            position_col: Name of position column
            force_col: Name of force column
            layer_number: Layer identifier (optional)
            
        Returns:
            Dictionary containing all calculated metrics
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
            df: DataFrame with time, position, force data
            time_col: Name of time column
            position_col: Name of position column  
            force_col: Name of force column
            layer_number: Layer identifier (optional)
            
        Returns:
            Dictionary containing all calculated metrics
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
        Apply current smoothing methodology (Savitzky-Golay filter).
        
        Args:
            force_data: Raw force data
            
        Returns:
            Smoothed force data
        """
        if len(force_data) < self.smoothing_window:
            # Not enough data for smoothing
            return force_data.copy()
            
        try:
            # Use light smoothing methodology (matches comprehensive_diagnostic)
            smoothed = savgol_filter(force_data, 
                                   window_length=self.smoothing_window,
                                   polyorder=self.smoothing_polyorder)
            return smoothed
        except Exception as e:
            warnings.warn(f"Smoothing failed: {e}. Using raw data.")
            return force_data.copy()
    
    def _calculate_metrics(self, 
                         times: np.ndarray, 
                         positions: np.ndarray, 
                         forces: np.ndarray, 
                         smoothed_force: np.ndarray,
                         layer_number: Optional[int],
                         motion_end_idx: Optional[int]) -> Dict:
        """
        Calculate all adhesion metrics using current methodology.
        """
        results = {'layer_number': layer_number}
        
        # Step 1: Find peak force
        peak_idx, peak_force = self._find_peak_force(smoothed_force)
        results['peak_force'] = peak_force
        results['peak_force_position'] = positions[peak_idx]
        results['peak_force_time'] = times[peak_idx] - times[0]  # Relative time
        
        # Step 2: Find propagation end using second derivative maximum
        prop_end_idx = self._find_propagation_end_second_derivative(
            times, smoothed_force, peak_idx, motion_end_idx)
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
            positions, forces, smoothed_force, baseline, pre_init_idx, prop_end_idx)
        results.update(work_metrics)
        
        # Step 8: Calculate dynamic metrics
        dynamic_metrics = self._calculate_dynamic_metrics(
            times, forces, smoothed_force, pre_init_idx, peak_idx, prop_end_idx)
        results.update(dynamic_metrics)
        
        # Step 9: Calculate data quality metrics
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
        Find pre-initiation start (baseline crossing before peak).
        """
        threshold = baseline + self.baseline_threshold_factor
        
        # Search backwards from peak
        search_start = max(0, peak_idx - 300)  # Limit search range
        
        for i in range(peak_idx - 1, search_start, -1):
            if smoothed_force[i] <= threshold:
                return i + 1  # Return first point above threshold
                
        return search_start
    
    def _find_propagation_end_second_derivative(self, 
                                              times: np.ndarray, 
                                              smoothed_force: np.ndarray, 
                                              peak_idx: int,
                                              motion_end_idx: Optional[int]) -> int:
        """
        Find propagation end using second derivative maximum method.
        """
        # Determine search region
        if motion_end_idx is None:
            motion_end_idx = len(smoothed_force)
        else:
            motion_end_idx = min(motion_end_idx, len(smoothed_force))
            
        if peak_idx >= motion_end_idx - 2:
            return min(peak_idx + 5, len(smoothed_force) - 1)
        
        try:
            # Calculate first derivative using np.diff (matches comprehensive_diagnostic)
            first_derivative = np.diff(smoothed_force)
            
            # Calculate second derivative using np.diff (matches comprehensive_diagnostic)  
            second_derivative = np.diff(first_derivative)
            
            # Adjust indices for shortened arrays due to diff operations
            # first_derivative has len(smoothed_force) - 1 points
            # second_derivative has len(smoothed_force) - 2 points
            
            # Find maximum second derivative after peak
            # Need to adjust peak_idx for second_derivative array indexing
            if peak_idx >= len(second_derivative):
                # Peak is too close to end, use fallback
                return min(peak_idx + 5, len(smoothed_force) - 1)
                
            search_start_idx = max(0, peak_idx - 1)  # Adjust for diff operation
            search_end_idx = min(len(second_derivative), motion_end_idx - 2) if motion_end_idx else len(second_derivative)
            
            if search_start_idx >= search_end_idx:
                return min(peak_idx + 5, len(smoothed_force) - 1)
                
            search_region = second_derivative[search_start_idx:search_end_idx]
            if len(search_region) == 0:
                return peak_idx
                
            max_second_deriv_idx = np.argmax(search_region)
            # Convert back to original smoothed_force indexing
            prop_end_idx = search_start_idx + max_second_deriv_idx + 2  # +2 to account for double diff
            
            return min(prop_end_idx, len(smoothed_force) - 1)
            
        except Exception as e:
            warnings.warn(f"Second derivative calculation failed: {e}. Using fallback method.")
            # Fallback: simple search for force stabilization
            return self._find_propagation_end_fallback(smoothed_force, peak_idx, motion_end_idx)
    
    def _find_propagation_end_fallback(self, smoothed_force: np.ndarray, peak_idx: int, motion_end_idx: int) -> int:
        """
        Fallback method for propagation end detection.
        """
        # Simple method: find where force stabilizes after peak
        search_end = min(motion_end_idx, len(smoothed_force))
        
        for i in range(peak_idx + 5, search_end):
            if i + 25 < search_end:
                window = smoothed_force[i:i+25]
                if np.std(window) < 0.005:  # Force stabilized
                    return i
                    
        return min(peak_idx + 100, search_end - 1)
    
    def _calculate_work_metrics(self, 
                              positions: np.ndarray, 
                              forces: np.ndarray, 
                              smoothed_force: np.ndarray,
                              baseline: float,
                              pre_init_idx: int, 
                              prop_end_idx: int) -> Dict:
        """
        Calculate work and energy metrics.
        """
        results = {}
        
        # Extract peel region data
        peel_positions = positions[pre_init_idx:prop_end_idx+1]
        peel_forces = forces[pre_init_idx:prop_end_idx+1]
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
