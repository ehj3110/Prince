"""
Test Adhesion Calculator with Derivative Plotting
================================================

This is a copy of the current adhesion_metrics_c        # Calculate basic metrics
        results = {
            'layer_number': layer_number,
            'peak_force': peak_force,
            'baseline_force': baseline,
            'peak_force_corrected': peak_force - baseline,
            'peak_time': peak_time,
            'propagation_end_time': prop_end_time,
            'max_second_deriv_time': max_second_deriv_time,
            'time_peak_to_prop_end': prop_end_time - peak_time,
            'smoothing_window': self.smoothing_window,
            'smoothing_polyorder': self.smoothing_polyorder
        }
        
        # Print the key metrics to console
        print(f"\nLayer {layer_number} Metrics:")
        print(f"  Peak Time: {peak_time:.3f} s")
        print(f"  Propagation End Time: {prop_end_time:.3f} s")
        print(f"  Peak Force: {peak_force:.6f} N")
        print(f"  Baseline Force: {baseline:.6f} N")
        print(f"  Time from Peak to Prop End: {prop_end_time - peak_time:.3f} s")
        
        return resultsadded plotting
capabilities to visualize the first and second derivatives. This allows us to
see exactly what the current method is detecting without changing the calculation.

Author: Test version for debugging
Date: September 21, 2025
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter
from scipy import integrate
import warnings
from typing import Dict, Tuple, Optional, Union
from pathlib import Path


class TestAdhesionCalculatorWithDerivatives:
    """
    Test version of AdhesionMetricsCalculator with derivative plotting capabilities.
    """
    
    def __init__(self, 
                 smoothing_window=3, 
                 smoothing_polyorder=1,
                 baseline_threshold_factor=0.002,
                 min_peak_height=0.01,
                 min_peak_distance=50):
        """
        Initialize the test adhesion metrics calculator.
        """
        self.smoothing_window = smoothing_window if smoothing_window % 2 == 1 else smoothing_window + 1
        self.smoothing_polyorder = smoothing_polyorder
        self.baseline_threshold_factor = baseline_threshold_factor
        self.min_peak_height = min_peak_height
        self.min_peak_distance = min_peak_distance
        
    def analyze_single_layer_with_plots(self, 
                                      time_data: np.ndarray, 
                                      position_data: np.ndarray, 
                                      force_data: np.ndarray,
                                      layer_number: int,
                                      save_path: Optional[str] = None) -> Dict:
        """
        Analyze a single layer and create derivative plots showing the calculation process.
        
        Args:
            time_data: Time values for the layer
            position_data: Position values for the layer
            force_data: Force values for the layer
            layer_number: Layer identifier
            save_path: Optional path to save the plot
            
        Returns:
            Dictionary containing calculated metrics
        """
        # Apply smoothing
        smoothed_force = self._apply_smoothing(force_data)
        
        # Find peak
        peak_idx, peak_force = self._find_peak_force(smoothed_force)
        
        # Find propagation end (this is what we want to visualize)
        prop_end_idx = self._find_propagation_end_second_derivative(
            time_data, smoothed_force, peak_idx, len(smoothed_force))
        
        # Calculate baseline
        baseline = smoothed_force[prop_end_idx]
        
        # Calculate derivatives using current method
        first_derivative = np.diff(smoothed_force)
        second_derivative = np.diff(first_derivative)
        
        # Adjust indices for derivative arrays
        first_deriv_times = time_data[1:]  # One less point
        second_deriv_times = time_data[2:]  # Two less points
        
        # Find the critical points
        peak_time = time_data[peak_idx]
        prop_end_time = time_data[prop_end_idx]
        
        # Find max second derivative for verification
        search_start_idx = max(0, peak_idx - 1)
        search_end_idx = min(len(second_derivative), len(smoothed_force) - 2)
        if search_start_idx < search_end_idx:
            search_region = second_derivative[search_start_idx:search_end_idx]
            max_second_deriv_rel_idx = np.argmax(search_region)
            max_second_deriv_idx = search_start_idx + max_second_deriv_rel_idx
            max_second_deriv_time = second_deriv_times[max_second_deriv_idx]
        else:
            max_second_deriv_time = prop_end_time
        
        # Create the plot
        fig, axes = plt.subplots(3, 1, figsize=(12, 10))
        fig.suptitle(f'Layer {layer_number} - Current Method Derivative Analysis', fontsize=14, fontweight='bold')
        
        # Plot 1: Smoothed Force
        axes[0].plot(time_data, force_data, 'lightgray', alpha=0.7, label='Raw Force')
        axes[0].plot(time_data, smoothed_force, 'blue', linewidth=2, label='Smoothed Force')
        axes[0].axvline(peak_time, color='black', linestyle='--', alpha=0.8, label='Peak')
        axes[0].axvline(prop_end_time, color='orange', linestyle='-.', linewidth=2, label='Propagation End')
        axes[0].axhline(baseline, color='red', linestyle=':', alpha=0.8, label=f'Baseline: {baseline:.4f}N')
        
        # Mark key points
        axes[0].plot(peak_time, peak_force, 'o', color='black', markersize=8, zorder=5)
        axes[0].plot(prop_end_time, baseline, 'o', color='orange', markersize=8, zorder=5)
        
        axes[0].set_title('Force Data with Key Points')
        axes[0].set_xlabel('Time (s)')
        axes[0].set_ylabel('Force (N)')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        
        # Plot 2: First Derivative
        axes[1].plot(first_deriv_times, first_derivative, 'green', linewidth=2, label='dF/dt')
        axes[1].axvline(peak_time, color='black', linestyle='--', alpha=0.8, label='Peak')
        axes[1].axvline(prop_end_time, color='orange', linestyle='-.', linewidth=2, label='Propagation End')
        axes[1].axhline(0, color='gray', linestyle='-', alpha=0.5, label='Zero derivative')
        
        axes[1].set_title('First Derivative (dF/dt)')
        axes[1].set_xlabel('Time (s)')
        axes[1].set_ylabel('dF/dt (N/sample)')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)
        
        # Plot 3: Second Derivative
        axes[2].plot(second_deriv_times, second_derivative, 'red', linewidth=2, label='d²F/dt²')
        axes[2].axvline(peak_time, color='black', linestyle='--', alpha=0.8, label='Peak')
        axes[2].axvline(prop_end_time, color='orange', linestyle='-.', linewidth=2, label='Propagation End')
        axes[2].axvline(max_second_deriv_time, color='purple', linestyle=':', linewidth=2, label='Max d²F/dt²')
        axes[2].axhline(0, color='gray', linestyle='-', alpha=0.5, label='Zero 2nd derivative')
        
        # Mark the maximum point
        if search_start_idx < search_end_idx:
            axes[2].plot(max_second_deriv_time, second_derivative[max_second_deriv_idx], 'o', 
                        color='purple', markersize=8, zorder=5)
        
        axes[2].set_title('Second Derivative (d²F/dt²)')
        axes[2].set_xlabel('Time (s)')
        axes[2].set_ylabel('d²F/dt² (N/sample²)')
        axes[2].legend()
        axes[2].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Derivative plot saved to: {save_path}")
        
        plt.show()
        
        # Calculate basic metrics
        results = {
            'layer_number': layer_number,
            'peak_force': peak_force,
            'baseline_force': baseline,
            'peak_force_corrected': peak_force - baseline,
            'peak_time': peak_time,
            'propagation_end_time': prop_end_time,
            'max_second_deriv_time': max_second_deriv_time,
            'time_peak_to_prop_end': prop_end_time - peak_time,
            'smoothing_window': self.smoothing_window,
            'smoothing_polyorder': self.smoothing_polyorder
        }
        
        # Print summary
        print(f"\\nLayer {layer_number} Analysis Summary:")
        print(f"  Peak Force: {peak_force:.6f}N at {peak_time:.3f}s")
        print(f"  Baseline: {baseline:.6f}N at {prop_end_time:.3f}s (propagation end)")
        print(f"  Max 2nd Derivative: {max_second_deriv_time:.3f}s")
        print(f"  Time from peak to propagation end: {prop_end_time - peak_time:.3f}s")
        print(f"  Smoothing: window={self.smoothing_window}, polyorder={self.smoothing_polyorder}")
        
        return results
    
    def _apply_smoothing(self, force_data: np.ndarray) -> np.ndarray:
        """Apply light smoothing methodology."""
        if len(force_data) < self.smoothing_window:
            return force_data.copy()
            
        try:
            smoothed = savgol_filter(force_data, 
                                   window_length=self.smoothing_window,
                                   polyorder=self.smoothing_polyorder)
            return smoothed
        except Exception as e:
            warnings.warn(f"Smoothing failed: {e}. Using raw data.")
            return force_data.copy()
    
    def _find_peak_force(self, smoothed_force: np.ndarray) -> Tuple[int, float]:
        """Find peak force index and value."""
        peak_idx = np.argmax(smoothed_force)
        peak_force = smoothed_force[peak_idx]
        return peak_idx, peak_force
    
    def _find_propagation_end_second_derivative(self, 
                                              times: np.ndarray, 
                                              smoothed_force: np.ndarray, 
                                              peak_idx: int,
                                              motion_end_idx: Optional[int]) -> int:
        """
        Find propagation end using current second derivative maximum method.
        """
        # Determine search region
        if motion_end_idx is None:
            motion_end_idx = len(smoothed_force)
        else:
            motion_end_idx = min(motion_end_idx, len(smoothed_force))
            
        if peak_idx >= motion_end_idx - 2:
            return min(peak_idx + 5, len(smoothed_force) - 1)
        
        try:
            # Calculate first derivative using np.diff (current method)
            first_derivative = np.diff(smoothed_force)
            
            # Calculate second derivative using np.diff (current method)  
            second_derivative = np.diff(first_derivative)
            
            # Adjust indices for shortened arrays due to diff operations
            if peak_idx >= len(second_derivative):
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
            warnings.warn(f"Second derivative calculation failed: {e}. Using fallback.")
            return min(peak_idx + 50, len(smoothed_force) - 1)


def test_on_all_layers():
    """Test function to analyze all three layers from L198-L200 data."""
    
    # Load data
    df = pd.read_csv("autolog_L198-L200.csv")
    
    # Handle column name variations
    if 'Elapsed Time (s)' in df.columns:
        df = df.rename(columns={'Elapsed Time (s)': 'Time', 'Position (mm)': 'Position', 'Force (N)': 'Force'})
    
    # Layer boundaries (from hybrid plotter output)
    layer_boundaries = [
        (0, 619, 198),      # Layer 198
        (619, 1099, 199),   # Layer 199  
        (1099, 1433, 200)   # Layer 200
    ]
    
    # Create calculator with correct light smoothing settings
    calc = TestAdhesionCalculatorWithDerivatives(
        smoothing_window=3,
        smoothing_polyorder=1,
        baseline_threshold_factor=0.002,
        min_peak_height=0.01,
        min_peak_distance=50
    )
    
    all_results = []
    
    for start_idx, end_idx, layer_num in layer_boundaries:
        print(f"\n{'='*60}")
        print(f"Analyzing Layer {layer_num}")
        print(f"{'='*60}")
        
        # Extract layer data
        times = df['Time'].values[start_idx:end_idx]
        positions = df['Position'].values[start_idx:end_idx]
        forces = df['Force'].values[start_idx:end_idx]
        
        # Analyze with plots
        results = calc.analyze_single_layer_with_plots(
            times, positions, forces, 
            layer_number=layer_num,
            save_path=f"test_layer_{layer_num}_current_method_derivatives.png"
        )
        
        all_results.append(results)
    
    return all_results


if __name__ == "__main__":
    print("Testing current adhesion calculator method with derivative visualization...")
    print("Analyzing all three layers: 198, 199, 200")
    results = test_on_all_layers()
    
    print(f"\n{'='*60}")
    print("SUMMARY OF ALL LAYERS")
    print(f"{'='*60}")
    for result in results:
        layer = result['layer_number']
        print(f"Layer {layer}:")
        print(f"  Peak Force: {result['peak_force']:.6f}N")
        print(f"  Baseline: {result['baseline_force']:.6f}N") 
        print(f"  Corrected Peak: {result['peak_force_corrected']:.6f}N")
        print(f"  Peak to Prop End: {result['time_peak_to_prop_end']:.3f}s")
        print()
    
    print("Test complete! Check the individual layer derivative plots:")
    for result in results:
        layer = result['layer_number']
        print(f"  - test_layer_{layer}_current_method_derivatives.png")
