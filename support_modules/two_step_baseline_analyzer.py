"""
Two-Step Baseline Adhesion Analyzer
===================================

This module implements the refined 2-step baseline method developed during
the September 2025 analysis sessions. It provides accurate propagation end
detection using maximum 2nd derivative timing combined with traditional
force averaging for robust baseline measurements.

Key Features:
- Step 1: Propagation end detection using max 2nd derivative timing
- Step 2: Baseline measurement using traditional stabilization averaging
- Comprehensive timing and force analysis
- Production-ready integration with PeakForceLogger

Author: Enhanced Analysis Team
Date: September 17, 2025
"""

import numpy as np

# Try to import scipy - provide fallback if not available
try:
    from scipy.signal import savgol_filter
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print("Warning: scipy not available for TwoStepBaselineAnalyzer. Using simple moving average fallback.")
    
    def savgol_filter(data, window_length, polyorder):
        """Fallback function when scipy is not available - simple moving average"""
        if len(data) < window_length:
            return data.copy()
        
        # Simple moving average as fallback
        kernel = np.ones(window_length) / window_length
        # Pad the data to handle edges
        padded = np.pad(data, (window_length//2, window_length//2), mode='edge')
        smoothed = np.convolve(padded, kernel, mode='valid')
        return smoothed[:len(data)]

class TwoStepBaselineAnalyzer:
    """
    Advanced adhesion analysis using the refined 2-step baseline method.
    
    This analyzer implements the exact methods developed and validated during
    the comprehensive analysis sessions with L48-L50 and L198-L200 datasets.
    """
    
    def __init__(self, sampling_rate=50, smoothing_window=3, smoothing_order=1):
        """
        Initialize the Two-Step Baseline Analyzer.
        
        Args:
            sampling_rate (float): Data sampling rate in Hz (default: 50)
            smoothing_window (int): Savitzky-Golay window length (default: 3)
            smoothing_order (int): Savitzky-Golay polynomial order (default: 1)
            
        Note:
            If scipy is not available, smoothing falls back to moving average.
        """
        self.sampling_rate = sampling_rate
        self.smoothing_window = smoothing_window
        self.smoothing_order = smoothing_order
        
    def analyze_peel_data(self, timestamps, positions, forces):
        """
        Perform comprehensive analysis using the 2-step baseline method.
        
        Args:
            timestamps (array): Time data points (absolute timestamps)
            positions (array): Position data (mm)  
            forces (array): Force data (N)
            
        Returns:
            dict: Analysis results with all requested metrics
        """
        if len(timestamps) < 10:
            return self._empty_results()
            
        # Convert to numpy arrays and clean data
        times = np.array(timestamps)
        positions = np.array(positions) 
        forces = np.array(forces)
        
        # Remove invalid data points
        valid_mask = ~(np.isnan(times) | np.isnan(positions) | np.isnan(forces))
        times = times[valid_mask]
        positions = positions[valid_mask]
        forces = forces[valid_mask]
        
        if len(times) < 10:
            return self._empty_results()
            
        # Apply light smoothing (matching our analysis parameters)
        if len(forces) >= self.smoothing_window:
            smoothed_forces = savgol_filter(forces, 
                                          window_length=self.smoothing_window, 
                                          polyorder=self.smoothing_order)
        else:
            smoothed_forces = forces.copy()
            
        # Convert absolute timestamps to elapsed time for analysis
        elapsed_times = times - times[0]
        
        # Core analysis using our validated methods
        return self._perform_two_step_analysis(elapsed_times, positions, forces, smoothed_forces)
    
    def _perform_two_step_analysis(self, elapsed_times, positions, forces, smoothed_forces):
        """
        Execute the 2-step baseline analysis method.
        """
        results = {}
        
        # Step 1: Peak Detection (use smoothed for better identification)
        peak_idx = self._detect_peak_force(smoothed_forces)
        if peak_idx is None:
            return self._empty_results()
            
        peak_time = elapsed_times[peak_idx]
        peak_force = smoothed_forces[peak_idx]
        raw_peak_force = forces[peak_idx]  # Raw reading for comparison
        
        # Step 2: Two-Step Baseline Method
        # Part A: Propagation end using max 2nd derivative timing
        propagation_end_idx = self._detect_propagation_end_2step(peak_idx, elapsed_times, 
                                                               positions, smoothed_forces)
        
        # Part B: Baseline using traditional averaging at propagation end
        baseline_force = self._calculate_traditional_baseline(propagation_end_idx, smoothed_forces)
        
        # Step 3: Comprehensive Timing Analysis
        timing_results = self._analyze_timing_metrics(elapsed_times, positions, smoothed_forces, 
                                                    peak_idx, propagation_end_idx)
        
        # Step 4: Force Analysis
        force_results = self._analyze_force_metrics(smoothed_forces, forces, peak_idx, 
                                                   propagation_end_idx, baseline_force)
        
        # Step 5: Work of Adhesion Calculation
        work_results = self._calculate_work_of_adhesion(positions, smoothed_forces, 
                                                      baseline_force, peak_idx, propagation_end_idx)
        
        # Compile results in requested order
        results = {
            'peak_force_N': peak_force,
            'work_of_adhesion_mJ': work_results['work_of_adhesion_mJ'],
            'pre_initiation_time_s': timing_results['pre_initiation_time_s'],
            'propagation_time_s': timing_results['propagation_time_s'], 
            'total_peeling_time_s': timing_results['total_peeling_time_s'],
            'distance_to_peel_start_mm': timing_results['distance_to_peel_start_mm'],
            'distance_to_full_peel_mm': timing_results['distance_to_full_peel_mm'],
            'peak_retraction_force_N': force_results['peak_retraction_force_N'],
            'pre_peel_force_N': force_results['pre_peel_force_N'],
            'raw_peak_force_reading_N': raw_peak_force,
            'baseline_reading_N': baseline_force,
            
            # Additional internal data for debugging/validation
            '_peak_idx': peak_idx,
            '_propagation_end_idx': propagation_end_idx,
            '_analysis_points': len(elapsed_times)
        }
        
        return results
    
    def _detect_peak_force(self, smoothed_forces):
        """
        Detect peak force using the same method as our analysis scripts.
        """
        # Find the maximum force (simple but effective for our data)
        peak_idx = np.argmax(smoothed_forces)
        
        # Basic validation - peak should be significant
        if smoothed_forces[peak_idx] > 0.01:  # Minimum 10mN peak
            return peak_idx
        return None
    
    def _detect_propagation_end_2step(self, peak_idx, elapsed_times, positions, smoothed_forces):
        """
        Step 1 of 2-step method: Find propagation end using maximum 2nd derivative timing.
        
        This implements the exact method from our final_layer_visualization.py analysis.
        """
        # Define ±1s window around peak (matching our diagnostic plots)
        window_points = int(1.0 * self.sampling_rate)  # ±1s window
        
        start_idx = max(0, peak_idx - window_points)
        end_idx = min(len(smoothed_forces), peak_idx + window_points)
        
        if end_idx - start_idx < 20:  # Need minimum points for derivatives
            return peak_idx + 10  # Fallback
            
        # Extract window data
        window_force = smoothed_forces[start_idx:end_idx]
        window_time = elapsed_times[start_idx:end_idx]
        
        # Calculate 1st and 2nd derivatives (matching our diagnostic method)
        if len(window_force) < 3:
            return peak_idx + 10  # Fallback
            
        first_derivative = np.diff(window_force)
        if len(first_derivative) < 2:
            return peak_idx + 10  # Fallback
            
        second_derivative = np.diff(first_derivative)
        second_deriv_time = (window_time[:-2] + window_time[2:]) / 2
        
        # Find maximum 2nd derivative point (most rapid acceleration)
        max_second_deriv_idx = np.argmax(second_derivative)
        max_second_deriv_time = second_deriv_time[max_second_deriv_idx]
        
        # Convert back to global index
        # Find closest time index in original data
        time_diffs = np.abs(elapsed_times - max_second_deriv_time)
        propagation_end_idx = np.argmin(time_diffs)
        
        return propagation_end_idx
    
    def _calculate_traditional_baseline(self, propagation_end_idx, smoothed_forces, window_size=25):
        """
        Step 2 of 2-step method: Traditional force averaging at the propagation end point.
        
        This implements the exact baseline calculation from our analysis.
        """
        if propagation_end_idx is None:
            return 0.0
            
        start_idx = propagation_end_idx
        end_idx = min(propagation_end_idx + window_size, len(smoothed_forces))
        
        if end_idx <= start_idx:
            return 0.0
            
        baseline_value = np.mean(smoothed_forces[start_idx:end_idx])
        return baseline_value
    
    def _analyze_timing_metrics(self, elapsed_times, positions, smoothed_forces, peak_idx, prop_end_idx):
        """
        Calculate comprehensive timing metrics.
        """
        results = {}
        
        # Pre-initiation time: assume start until force starts rising significantly
        # Look for when force exceeds baseline + 3 standard deviations
        baseline_region = smoothed_forces[:min(50, len(smoothed_forces)//4)]  # First 25% or 50 points
        baseline_std = np.std(baseline_region) if len(baseline_region) > 1 else 0.01
        baseline_mean = np.mean(baseline_region) if len(baseline_region) > 0 else 0
        
        initiation_threshold = baseline_mean + 3 * baseline_std
        initiation_idx = 0
        for i in range(len(smoothed_forces)):
            if smoothed_forces[i] > initiation_threshold:
                initiation_idx = i
                break
                
        # Timing calculations
        initiation_time = elapsed_times[initiation_idx] if initiation_idx < len(elapsed_times) else elapsed_times[0]
        peak_time = elapsed_times[peak_idx] if peak_idx < len(elapsed_times) else elapsed_times[-1]
        prop_end_time = elapsed_times[prop_end_idx] if prop_end_idx < len(elapsed_times) else elapsed_times[-1]
        
        results['pre_initiation_time_s'] = peak_time - initiation_time
        results['propagation_time_s'] = prop_end_time - peak_time  
        results['total_peeling_time_s'] = prop_end_time - initiation_time
        
        # Distance calculations
        initiation_pos = positions[initiation_idx] if initiation_idx < len(positions) else positions[0]
        peak_pos = positions[peak_idx] if peak_idx < len(positions) else positions[-1]
        prop_end_pos = positions[prop_end_idx] if prop_end_idx < len(positions) else positions[-1]
        
        results['distance_to_peel_start_mm'] = abs(peak_pos - initiation_pos)
        results['distance_to_full_peel_mm'] = abs(prop_end_pos - peak_pos)
        
        return results
    
    def _analyze_force_metrics(self, smoothed_forces, raw_forces, peak_idx, prop_end_idx, baseline_force):
        """
        Calculate force-related metrics.
        """
        results = {}
        
        # Peak retraction force (relative to baseline)
        peak_force = smoothed_forces[peak_idx]
        results['peak_retraction_force_N'] = peak_force - baseline_force
        
        # Pre-peel force (force before significant loading begins)
        pre_peel_region = smoothed_forces[:min(20, len(smoothed_forces)//10)]  # First 10% or 20 points
        results['pre_peel_force_N'] = np.mean(pre_peel_region) if len(pre_peel_region) > 0 else 0.0
        
        return results
    
    def _calculate_work_of_adhesion(self, positions, smoothed_forces, baseline_force, peak_idx, prop_end_idx):
        """
        Calculate work of adhesion using trapezoidal integration with baseline correction.
        """
        results = {}
        
        # Define integration region from peak to propagation end
        start_idx = peak_idx
        end_idx = min(prop_end_idx + 10, len(positions))  # Slightly beyond propagation end
        
        if end_idx <= start_idx or end_idx - start_idx < 2:
            results['work_of_adhesion_mJ'] = 0.0
            return results
            
        # Extract relevant data
        work_positions = positions[start_idx:end_idx]
        work_forces = smoothed_forces[start_idx:end_idx]
        
        # Baseline correction
        corrected_forces = work_forces - baseline_force
        corrected_forces = np.maximum(corrected_forces, 0)  # Only positive contributions
        
        # Convert positions to meters for work calculation
        work_positions_m = work_positions / 1000.0
        
        # Trapezoidal integration
        if len(work_positions_m) >= 2:
            work_J = np.trapz(corrected_forces, work_positions_m)
            work_mJ = abs(work_J) * 1000  # Convert to milliJoules and ensure positive
        else:
            work_mJ = 0.0
            
        results['work_of_adhesion_mJ'] = work_mJ
        return results
    
    def _empty_results(self):
        """
        Return empty results structure for failed analysis.
        """
        return {
            'peak_force_N': 0.0,
            'work_of_adhesion_mJ': 0.0,
            'pre_initiation_time_s': 0.0,
            'propagation_time_s': 0.0,
            'total_peeling_time_s': 0.0,
            'distance_to_peel_start_mm': 0.0,
            'distance_to_full_peel_mm': 0.0,
            'peak_retraction_force_N': 0.0,
            'pre_peel_force_N': 0.0,
            'raw_peak_force_reading_N': 0.0,
            'baseline_reading_N': 0.0,
            '_analysis_points': 0
        }
