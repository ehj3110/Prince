"""
Enhanced Adhesion Metrics Calculator
====================================

This module provides advanced analysis methods for adhesion measurements during
resin 3D printing peeling operations. It enhances the basic PeakForceLogger
with more sophisticated timing, force gradient, and work calculations.

Author: Enhanced by Claude for improved adhesion analysis
Date: September 15, 2025
"""

import numpy as np
import warnings
import sys
import os

# Try to import scipy - only needed for legacy EnhancedAdhesionAnalyzer
try:
    from scipy import integrate, signal
    from scipy.ndimage import gaussian_filter1d
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print("Warning: scipy not available. Legacy EnhancedAdhesionAnalyzer will not work.")

# Import the new Two-Step Baseline Analyzer (now in same directory)
from two_step_baseline_analyzer import TwoStepBaselineAnalyzer

class EnhancedAdhesionAnalyzer:
    """
    Advanced adhesion analysis with improved timing accuracy and force metrics.
    """
    
    def __init__(self, smoothing_sigma=0.5, noise_threshold=0.005):
        """
        Initialize the enhanced adhesion analyzer.
        
        Args:
            smoothing_sigma (float): Gaussian smoothing parameter for noise reduction
            noise_threshold (float): Force threshold for noise filtering (N)
        """
        self.smoothing_sigma = smoothing_sigma
        self.noise_threshold = noise_threshold
        
    def analyze_peel_data(self, timestamps, positions, forces):
        """
        Perform comprehensive analysis of peeling data.
        
        Args:
            timestamps (array): Time data points
            positions (array): Position data (mm)
            forces (array): Force data (N)
            
        Returns:
            dict: Comprehensive analysis results
        """
        if len(timestamps) < 3:
            return self._empty_results()
            
        # Convert to numpy arrays and filter data
        times = np.array(timestamps)
        pos = np.array(positions)
        force = np.array(forces)
        
        # Remove invalid data points
        valid_mask = ~(np.isnan(times) | np.isnan(pos) | np.isnan(force))
        times = times[valid_mask]
        pos = pos[valid_mask]
        force = force[valid_mask]
        
        if len(times) < 3:
            return self._empty_results()
            
        # Smooth force data to reduce noise
        force_smooth = gaussian_filter1d(force, sigma=self.smoothing_sigma)
        
        # Calculate enhanced metrics
        results = {}
        
        # 1. Enhanced Timing Analysis
        timing_results = self._analyze_peel_timing(times, pos, force, force_smooth)
        results.update(timing_results)
        
        # 2. Force Gradient Analysis
        gradient_results = self._analyze_force_gradients(times, pos, force_smooth)
        results.update(gradient_results)
        
        # 3. Enhanced Work Calculations
        work_results = self._calculate_enhanced_work(times, pos, force, force_smooth)
        results.update(work_results)
        
        # 4. Mechanical Properties
        mechanical_results = self._analyze_mechanical_properties(times, pos, force_smooth)
        results.update(mechanical_results)
        
        # 5. Force Oscillation Analysis
        oscillation_results = self._analyze_force_oscillations(times, force, force_smooth)
        results.update(oscillation_results)
        
        return results
    
    def _analyze_peel_timing(self, times, positions, force, force_smooth):
        """Enhanced timing analysis with improved baseline correction and completion detection."""
        results = {}
        
        # Step 1: Better baseline determination using multiple methods
        # Method 1: Last 5% of data (more conservative)
        final_segment_size = max(20, len(force) // 20)  # At least 20 points or 5% of data
        final_segment = force[-final_segment_size:]
        
        # Method 2: Look for the most stable region in final portion
        # Split final segment into smaller windows and find most stable
        if len(final_segment) >= 10:
            window_size = max(5, len(final_segment) // 4)
            min_std = float('inf')
            best_baseline = np.median(final_segment)
            
            for i in range(0, len(final_segment) - window_size, window_size//2):
                window = final_segment[i:i+window_size]
                if len(window) >= 5:
                    window_std = np.std(window)
                    if window_std < min_std:
                        min_std = window_std
                        best_baseline = np.median(window)
            
            true_baseline = best_baseline
        else:
            true_baseline = np.median(final_segment)
        
        # Step 2: Correct all forces relative to improved baseline
        corrected_force = force - true_baseline
        corrected_force_smooth = force_smooth - true_baseline
        
        results['true_baseline'] = true_baseline
        results['baseline_corrected'] = True
        
        # Step 3: Find peel initiation - when corrected force crosses above baseline
        # Use more conservative threshold for initiation
        initiation_threshold = 3 * self.noise_threshold  # Increased from 2x
        positive_force_mask = corrected_force_smooth > initiation_threshold
        
        if np.any(positive_force_mask):
            positive_indices = np.where(positive_force_mask)[0]
            
            # Require sustained positive force (at least 5 consecutive points for reliability)
            peel_start_idx = None
            for i in range(len(positive_indices) - 4):  # Changed from 2 to 4
                consecutive = True
                for j in range(4):  # Check 5 consecutive points
                    if positive_indices[i+j+1] != positive_indices[i+j] + 1:
                        consecutive = False
                        break
                if consecutive:
                    peel_start_idx = positive_indices[i]
                    break
            
            if peel_start_idx is not None:
                results['peel_initiation_time'] = times[peel_start_idx] - times[0]
                results['peel_initiation_position'] = positions[peel_start_idx]
                results['peel_initiation_force'] = corrected_force[peel_start_idx]
            else:
                # Fallback to first positive force
                peel_start_idx = positive_indices[0]
                results['peel_initiation_time'] = times[peel_start_idx] - times[0]
                results['peel_initiation_position'] = positions[peel_start_idx]
                results['peel_initiation_force'] = corrected_force[peel_start_idx]
        else:
            # No clear peel initiation detected
            peel_start_idx = 0
            results['peel_initiation_time'] = 0.0
            results['peel_initiation_position'] = positions[0]
            results['peel_initiation_force'] = corrected_force[0]
        
        # Step 4: Find peak force with corrected baseline
        if np.any(corrected_force > 0):
            peak_idx = np.argmax(corrected_force)
            results['peak_force_time'] = times[peak_idx] - times[0]
            results['peak_force_position'] = positions[peak_idx]
            results['peak_force_magnitude'] = corrected_force[peak_idx]
            results['time_to_peak_from_initiation'] = times[peak_idx] - times[peel_start_idx]
        else:
            results['peak_force_time'] = float('nan')
            results['peak_force_position'] = float('nan')
            results['peak_force_magnitude'] = 0.0
            results['time_to_peak_from_initiation'] = float('nan')
            peak_idx = len(times) // 2  # Fallback for completion calculation
        
        # Step 5: Find peel completion - when force returns to baseline after peak
        # Improved completion detection with better sustained return logic
        completion_threshold = 2 * self.noise_threshold  # Within 2x noise of baseline
        
        # Only look after the peak
        post_peak_indices = np.arange(peak_idx + 1, len(times))
        
        if len(post_peak_indices) > 0:
            post_peak_corrected_force = corrected_force_smooth[post_peak_indices]
            
            # Find where force returns to baseline (within threshold)
            baseline_return_mask = np.abs(post_peak_corrected_force) < completion_threshold
            
            if np.any(baseline_return_mask):
                baseline_indices = np.where(baseline_return_mask)[0]
                
                # Look for sustained return to baseline (at least 8 consecutive points)
                completion_idx = None
                min_consecutive = 8  # Increased for more reliable detection
                
                for i in range(len(baseline_indices) - min_consecutive + 1):
                    consecutive_count = 1
                    for j in range(1, min_consecutive):
                        if i+j < len(baseline_indices):
                            if baseline_indices[i+j] == baseline_indices[i+j-1] + 1:
                                consecutive_count += 1
                            else:
                                break
                        else:
                            break
                    
                    if consecutive_count >= min_consecutive:
                        candidate_idx = post_peak_indices[baseline_indices[i]]
                        
                        # Additional check: ensure no significant force activity after this point
                        remaining_force = corrected_force_smooth[candidate_idx:]
                        remaining_max = np.max(np.abs(remaining_force)) if len(remaining_force) > 10 else 0
                        
                        # If there's significant activity later, this might be premature
                        if remaining_max <= 4 * self.noise_threshold:
                            completion_idx = candidate_idx
                            break
                        # Otherwise keep looking for a better completion point
                
                if completion_idx is not None:
                    results['peel_completion_time'] = times[completion_idx] - times[0]
                    results['peel_completion_position'] = positions[completion_idx]
                    results['total_peel_duration'] = times[completion_idx] - times[peel_start_idx]
                    results['peak_to_completion_time'] = times[completion_idx] - times[peak_idx]
                else:
                    # Fallback: find the last point where force is significantly above baseline
                    # then find the next sustained return
                    significant_force_mask = np.abs(post_peak_corrected_force) > 3 * self.noise_threshold
                    if np.any(significant_force_mask):
                        last_significant_idx = np.where(significant_force_mask)[0][-1]
                        # Look for baseline return after this point
                        later_baseline_mask = baseline_return_mask[last_significant_idx+5:]
                        if np.any(later_baseline_mask):
                            later_baseline_indices = np.where(later_baseline_mask)[0]
                            completion_idx = post_peak_indices[last_significant_idx + 5 + later_baseline_indices[0]]
                        else:
                            completion_idx = post_peak_indices[last_significant_idx + 5] if last_significant_idx + 5 < len(post_peak_indices) else post_peak_indices[-1]
                    else:
                        completion_idx = post_peak_indices[baseline_indices[0]]
                    
                    results['peel_completion_time'] = times[completion_idx] - times[0]
                    results['peel_completion_position'] = positions[completion_idx]
                    results['total_peel_duration'] = times[completion_idx] - times[peel_start_idx]
                    results['peak_to_completion_time'] = times[completion_idx] - times[peak_idx]
            else:
                # No clear return to baseline - use end of data
                results['peel_completion_time'] = times[-1] - times[0]
                results['peel_completion_position'] = positions[-1]
                results['total_peel_duration'] = times[-1] - times[peel_start_idx]
                results['peak_to_completion_time'] = times[-1] - times[peak_idx]
        else:
            # No post-peak data
            results['peel_completion_time'] = float('nan')
            results['peel_completion_position'] = float('nan')
            results['total_peel_duration'] = float('nan')
            results['peak_to_completion_time'] = float('nan')
        
        return results
    
    def _analyze_force_gradients(self, times, positions, force_smooth):
        """Analyze force gradients with baseline correction for mechanical insights."""
        results = {}
        
        # Apply baseline correction
        final_segment_size = max(10, len(force_smooth) // 10)
        final_segment = force_smooth[-final_segment_size:]
        true_baseline = np.median(final_segment)
        corrected_force_smooth = force_smooth - true_baseline
        
        # Calculate gradients with corrected forces
        force_gradient_time = np.gradient(corrected_force_smooth, times)  # N/s
        force_gradient_pos = np.gradient(corrected_force_smooth, positions)  # N/mm
        
        # Find maximum force rate (stiffness indicator)
        if len(force_gradient_time) > 0:
            results['max_force_rate'] = np.max(np.abs(force_gradient_time))
            results['max_loading_rate'] = np.max(force_gradient_time)
            results['max_unloading_rate'] = np.abs(np.min(force_gradient_time))
            
            # Find positions of maximum rates
            max_loading_idx = np.argmax(force_gradient_time)
            max_unloading_idx = np.argmin(force_gradient_time)
            
            results['max_loading_rate_position'] = positions[max_loading_idx]
            results['max_unloading_rate_position'] = positions[max_unloading_idx]
        
        # Position-based stiffness with corrected forces
        if len(force_gradient_pos) > 0:
            results['max_position_stiffness'] = np.max(np.abs(force_gradient_pos))
            results['avg_position_stiffness'] = np.mean(np.abs(force_gradient_pos))
        
        return results
    
    def _calculate_enhanced_work(self, times, positions, force, force_smooth):
        """Enhanced work calculation with baseline correction."""
        results = {}
        
        # Step 1: Apply baseline correction
        final_segment_size = max(10, len(force) // 10)
        final_segment = force[-final_segment_size:]
        true_baseline = np.median(final_segment)
        corrected_force = force - true_baseline
        
        # Method 1: Trapezoidal integration with baseline correction
        positive_force = np.maximum(corrected_force, 0)  # Only positive work (adhesion)
        negative_force = np.minimum(corrected_force, 0)  # Energy dissipation
        
        # Convert positions to meters for work calculation
        pos_m = positions / 1000.0
        
        if len(pos_m) > 1:
            # Positive work (adhesion energy) - baseline corrected
            positive_work_J = np.trapz(positive_force, pos_m)
            results['work_of_adhesion_mJ'] = positive_work_J * 1000
            
            # Negative work (energy dissipation) 
            negative_work_J = np.trapz(np.abs(negative_force), pos_m)
            results['energy_dissipation_mJ'] = negative_work_J * 1000
            
            # Total energy
            total_work_J = np.trapz(np.abs(corrected_force), pos_m)
            results['total_energy_mJ'] = total_work_J * 1000
            
            # Method 2: Simpson's rule for higher accuracy (if enough points)
            if len(pos_m) >= 3:
                try:
                    simpson_work_J = integrate.simpson(positive_force, pos_m)
                    results['work_of_adhesion_simpson_mJ'] = simpson_work_J * 1000
                except:
                    results['work_of_adhesion_simpson_mJ'] = results['work_of_adhesion_mJ']
            
            # Method 3: Already baseline-corrected, so use it directly
            results['work_baseline_corrected_mJ'] = results['work_of_adhesion_mJ']
            
            # Energy density (work per unit distance)
            total_distance = np.max(pos_m) - np.min(pos_m)
            if total_distance > 0:
                results['energy_density_mJ_per_mm'] = (positive_work_J * 1000) / (total_distance * 1000)
        
        return results
    
    def _analyze_mechanical_properties(self, times, positions, force_smooth):
        """Analyze mechanical properties from force-displacement curve."""
        results = {}
        
        if len(positions) < 3:
            return results
        
        # Calculate compliance (displacement per unit force)
        # Find linear region (typically before peak force)
        if np.max(force_smooth) > self.noise_threshold:
            peak_idx = np.argmax(force_smooth)
            
            # Analyze first 70% of data leading to peak
            linear_region_end = int(peak_idx * 0.7)
            if linear_region_end > 2:
                linear_forces = force_smooth[:linear_region_end]
                linear_positions = positions[:linear_region_end]
                
                # Linear regression to find stiffness
                if len(linear_forces) > 2 and np.std(linear_forces) > 0:
                    try:
                        # Fit F = k * x + b
                        coeffs = np.polyfit(linear_positions, linear_forces, 1)
                        stiffness_N_per_mm = coeffs[0]
                        results['adhesion_stiffness_N_per_mm'] = stiffness_N_per_mm
                        results['compliance_mm_per_N'] = 1.0 / stiffness_N_per_mm if stiffness_N_per_mm != 0 else float('inf')
                        
                        # R-squared for fit quality
                        linear_forces_pred = np.polyval(coeffs, linear_positions)
                        ss_res = np.sum((linear_forces - linear_forces_pred) ** 2)
                        ss_tot = np.sum((linear_forces - np.mean(linear_forces)) ** 2)
                        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
                        results['stiffness_fit_r_squared'] = r_squared
                    except:
                        pass
        
        # Hysteresis analysis (if data shows loading/unloading cycle)
        # This is more complex and would require identifying loading vs unloading phases
        
        return results
    
    def _analyze_force_oscillations(self, times, force, force_smooth):
        """Analyze force oscillations and noise characteristics."""
        results = {}
        
        if len(force) < 10:
            return results
        
        # Analyze noise/oscillations by comparing raw vs smoothed force
        force_noise = force - force_smooth
        
        results['force_noise_rms'] = np.sqrt(np.mean(force_noise**2))
        results['force_noise_std'] = np.std(force_noise)
        results['force_signal_to_noise'] = np.std(force_smooth) / np.std(force_noise) if np.std(force_noise) > 0 else float('inf')
        
        # Frequency analysis of oscillations
        if len(times) > 1:
            dt = np.mean(np.diff(times))
            sampling_rate = 1.0 / dt
            
            # Remove DC component for frequency analysis
            force_ac = force - np.mean(force)
            
            # Simple dominant frequency detection
            try:
                # Use FFT to find dominant frequencies
                fft_force = np.fft.fft(force_ac)
                freqs = np.fft.fftfreq(len(force_ac), dt)
                
                # Only look at positive frequencies
                pos_freq_idx = freqs > 0
                pos_freqs = freqs[pos_freq_idx]
                pos_fft_mag = np.abs(fft_force[pos_freq_idx])
                
                if len(pos_fft_mag) > 0:
                    dominant_freq_idx = np.argmax(pos_fft_mag)
                    results['dominant_oscillation_frequency_hz'] = pos_freqs[dominant_freq_idx]
                    results['oscillation_amplitude'] = pos_fft_mag[dominant_freq_idx] / len(force_ac)
                
            except:
                # Frequency analysis failed
                pass
        
        return results
    
    def _empty_results(self):
        """Return empty results structure for invalid data."""
        return {
            'peel_initiation_time': float('nan'),
            'peel_initiation_position': float('nan'),
            'peel_initiation_force': float('nan'),
            'peak_force_time': float('nan'),
            'peak_force_position': float('nan'),
            'peak_force_magnitude': 0.0,
            'time_to_peak_from_initiation': float('nan'),
            'peel_completion_time': float('nan'),
            'peel_completion_position': float('nan'),
            'total_peel_duration': float('nan'),
            'peak_to_completion_time': float('nan'),
            'max_force_rate': 0.0,
            'max_loading_rate': 0.0,
            'max_unloading_rate': 0.0,
            'work_of_adhesion_mJ': 0.0,
            'energy_dissipation_mJ': 0.0,
            'total_energy_mJ': 0.0,
            'work_baseline_corrected_mJ': 0.0,
            'energy_density_mJ_per_mm': 0.0
        }

    def format_results_for_csv(self, results):
        """Format results for CSV output with proper precision."""
        formatted = {}
        
        # Define precision for different metric types
        time_precision = 4      # seconds
        force_precision = 4     # Newtons
        position_precision = 4  # mm
        energy_precision = 4    # mJ
        rate_precision = 3      # N/s
        freq_precision = 2      # Hz
        
        # Format each result with appropriate precision
        for key, value in results.items():
            if np.isnan(value) or np.isinf(value):
                formatted[key] = "NaN"
            elif 'time' in key.lower() or 'duration' in key.lower():
                formatted[key] = f"{value:.{time_precision}f}"
            elif 'force' in key.lower() and 'rate' not in key.lower():
                formatted[key] = f"{value:.{force_precision}f}"
            elif 'position' in key.lower():
                formatted[key] = f"{value:.{position_precision}f}"
            elif 'energy' in key.lower() or 'work' in key.lower() or '_mJ' in key:
                formatted[key] = f"{value:.{energy_precision}f}"
            elif 'rate' in key.lower():
                formatted[key] = f"{value:.{rate_precision}f}"
            elif 'frequency' in key.lower() or '_hz' in key.lower():
                formatted[key] = f"{value:.{freq_precision}f}"
            else:
                formatted[key] = f"{value:.4f}"
                
        return formatted


def create_analyzer(analyzer_type="two_step_baseline", **kwargs):
    """
    Factory function to create the appropriate analyzer based on type.
    
    Args:
        analyzer_type (str): Type of analyzer to create
            - "enhanced" or "legacy": Original EnhancedAdhesionAnalyzer (requires scipy)
            - "two_step_baseline" or "production": New TwoStepBaselineAnalyzer (default)
        **kwargs: Additional arguments passed to analyzer constructor
        
    Returns:
        Analyzer instance
    """
    if analyzer_type.lower() in ["enhanced", "legacy"]:
        if not SCIPY_AVAILABLE:
            print(f"Warning: scipy not available, falling back to TwoStepBaselineAnalyzer instead of {analyzer_type}")
            return TwoStepBaselineAnalyzer(**kwargs)
        return EnhancedAdhesionAnalyzer(**kwargs)
    elif analyzer_type.lower() in ["two_step_baseline", "production"]:
        return TwoStepBaselineAnalyzer(**kwargs)
    else:
        # Default to the production analyzer
        print(f"Warning: Unknown analyzer type '{analyzer_type}', defaulting to 'two_step_baseline'")
        return TwoStepBaselineAnalyzer(**kwargs)


# Test function for development
if __name__ == "__main__":
    # Test the analyzer with simulated data
    analyzer = EnhancedAdhesionAnalyzer()
    
    # Create test data
    t = np.linspace(0, 2.0, 100)  # 2 seconds
    pos = 10 + t * 2  # Moving from 10mm to 14mm
    
    # Simulate realistic peeling force curve
    force = np.zeros_like(t)
    
    # Add noise
    noise = np.random.normal(0, 0.01, len(t))
    
    # Create force profile: gradual increase, peak, then decay
    for i, time in enumerate(t):
        if time < 0.5:
            force[i] = 0.02 * time  # Gradual increase
        elif time < 1.0:
            force[i] = 0.01 + 0.3 * (time - 0.5)  # Rapid increase to peak
        elif time < 1.5:
            force[i] = 0.16 - 0.2 * (time - 1.0)  # Decay from peak
        else:
            force[i] = 0.06 - 0.1 * (time - 1.5)  # Return to baseline
    
    force = np.maximum(force + noise, 0)  # Add noise and ensure non-negative
    
    # Analyze
    results = analyzer.analyze_peel_data(t, pos, force)
    
    # Display results
    print("Enhanced Adhesion Analysis Results:")
    print("=" * 40)
    formatted_results = analyzer.format_results_for_csv(results)
    for key, value in formatted_results.items():
        print(f"{key}: {value}")
