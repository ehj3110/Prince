"""
Troubleshooting Script for Propagation End Detection

Generates a 3x3 plot array for the first 3 layers showing:
- Row 1: Smoothed force data
- Row 2: First derivative of smoothed force
- Row 3: Second derivative of smoothed force

Each plot shows vertical lines for:
- Peak force location (dashed)
- 1st derivative zero crossing (if applicable)
- 2nd derivative zero crossing (propagation end)
"""

import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, 'post-processing')
sys.path.insert(0, 'support_modules')

from RawData_Processor import RawDataProcessor
from adhesion_metrics_calculator import AdhesionMetricsCalculator


def find_first_derivative_zero_crossing(first_deriv, peak_idx):
    """
    Find first negative-to-positive zero crossing after peak.
    
    Returns index relative to the derivative array, or None if not found.
    """
    for i in range(1, len(first_deriv)):
        if first_deriv[i-1] < 0 and first_deriv[i] >= 0:
            return i
    return None


def find_first_derivative_threshold(first_deriv, threshold_pct=0.10):
    """
    Find LAST point BEFORE 1st derivative magnitude drops below threshold.
    
    Since 1st derivative is negative (force decreasing), we look for the most negative
    value (peak magnitude) and then find the last point before it rises above threshold.
    
    Args:
        first_deriv: First derivative array
        threshold_pct: Threshold as fraction of peak (default 0.10 = 10%)
        
    Returns:
        Index of last point before threshold crossing, or None if not found
    """
    # Find most negative value (peak magnitude of decrease)
    min_val = np.min(first_deriv)
    threshold = min_val * threshold_pct  # e.g., -0.5 * 0.1 = -0.05
    
    # Find first point after the peak where derivative is less negative than threshold
    min_idx = np.argmin(first_deriv)
    for i in range(min_idx + 1, len(first_deriv)):
        if first_deriv[i] > threshold:  # Less negative than threshold
            # Return the PREVIOUS point (last point before crossing)
            return max(0, i - 1)
    return None


def find_second_derivative_threshold(second_deriv, threshold_pct=0.10):
    """
    Find LAST point BEFORE 2nd derivative drops below threshold_pct of peak value.
    
    Args:
        second_deriv: Second derivative array
        threshold_pct: Threshold as fraction of peak (default 0.10 = 10%)
        
    Returns:
        Tuple of (last_point_before_threshold_idx, peak_idx)
    """
    # Find highest positive peak
    positive_mask = second_deriv > 0
    if not np.any(positive_mask):
        max_idx = np.argmax(second_deriv)
        max_val = second_deriv[max_idx]
    else:
        positive_deriv = second_deriv.copy()
        positive_deriv[~positive_mask] = -np.inf
        max_idx = np.argmax(positive_deriv)
        max_val = second_deriv[max_idx]
    
    # Calculate threshold
    threshold = max_val * threshold_pct
    
    # Find where it drops below threshold after the peak
    for i in range(max_idx + 1, len(second_deriv)):
        if second_deriv[i] < threshold:
            # Return the PREVIOUS point (last point before crossing)
            return max(0, i - 1), max_idx
    
    # If not found, use halfway point
    halfway = max_idx + int(0.5 * (len(second_deriv) - max_idx))
    return halfway, max_idx


def find_second_derivative_propagation_end(second_deriv):
    """
    Find propagation end using second derivative method:
    1. Find highest positive peak of 2nd derivative
    2. Find first zero crossing after that peak
    
    Returns:
        Tuple of (zero_crossing_idx, peak_idx)
    """
    # Find highest positive peak
    positive_mask = second_deriv > 0
    if not np.any(positive_mask):
        max_idx = np.argmax(second_deriv)
    else:
        positive_deriv = second_deriv.copy()
        positive_deriv[~positive_mask] = -np.inf
        max_idx = np.argmax(positive_deriv)
    
    # Find zero crossing after peak
    for i in range(max_idx + 1, len(second_deriv)):
        if second_deriv[i] <= 0:
            return i, max_idx
    
    # If no crossing found, use halfway point
    halfway = max_idx + int(0.5 * (len(second_deriv) - max_idx))
    return halfway, max_idx


def plot_troubleshooting_derivatives(csv_filepath, output_path=None):
    """
    Create 3x3 troubleshooting plots for the first 3 layers.
    """
    # Initialize
    calc = AdhesionMetricsCalculator()
    proc = RawDataProcessor(calc)
    
    # Process CSV to get layer boundaries
    layers = proc.process_csv(csv_filepath)
    
    if len(layers) == 0:
        print("ERROR: No layers detected!")
        return
    
    # Load raw data
    df = pd.read_csv(csv_filepath)
    time_data = df['Elapsed Time (s)'].to_numpy()
    force_data = df['Force (N)'].to_numpy()
    position_data = df['Position (mm)'].to_numpy()
    
    # Apply smoothing
    smoothed_force = calc._apply_smoothing(force_data)
    
    # Process first 3 layers only
    num_layers = min(3, len(layers))
    
    # Create figure
    fig, axes = plt.subplots(3, num_layers, figsize=(6*num_layers, 12))
    if num_layers == 1:
        axes = axes.reshape(3, 1)
    
    for layer_idx in range(num_layers):
        layer = layers[layer_idx]
        layer_num = layer['number']
        
        # Get indices for this layer's lifting phase
        start_idx = layer['start_idx']
        end_idx = layer['end_idx']
        
        # Find peak in this region
        layer_force = smoothed_force[start_idx:end_idx+1]
        peak_idx_relative = np.argmax(layer_force)
        peak_idx_abs = start_idx + peak_idx_relative
        peak_time = time_data[peak_idx_abs]
        
        # === CALCULATE 80% LIFTING POINT (SAME AS ACTUAL ALGORITHM) ===
        travel_positions = position_data[peak_idx_abs:end_idx+1]
        min_pos = np.min(travel_positions)
        max_pos = position_data[peak_idx_abs]
        target_position = max_pos - 0.8 * (max_pos - min_pos)
        
        # Find index where position reaches 80% point
        lifting_80pct_idx = peak_idx_abs
        for i in range(peak_idx_abs, end_idx+1):
            if position_data[i] <= target_position:
                lifting_80pct_idx = i
                break
        else:
            # If never reached, use minimum position
            min_pos_relative_idx = np.argmin(travel_positions)
            lifting_80pct_idx = peak_idx_abs + min_pos_relative_idx
        
        lifting_80pct_time = time_data[lifting_80pct_idx]
        
        # Define time window: -0.25s before peak to +1s after peak (for visualization)
        time_window_start = peak_time - 0.25
        time_window_end = peak_time + 1.0
        
        # Find indices for this time window
        window_mask = (time_data >= time_window_start) & (time_data <= time_window_end)
        window_indices = np.where(window_mask)[0]
        
        if len(window_indices) == 0:
            print(f"Warning: No data in time window for layer {layer_num}")
            continue
        
        window_start = window_indices[0]
        window_end = window_indices[-1]
        
        # Extract data for this window
        window_time = time_data[window_start:window_end+1]
        window_force = smoothed_force[window_start:window_end+1]
        
        # === CALCULATE DERIVATIVES USING ACTUAL ALGORITHM APPROACH ===
        # Region of interest: from peak to 80% lifting point (CONSTRAINED)
        region_of_interest = smoothed_force[peak_idx_abs:lifting_80pct_idx+1]
        
        # First derivative of the CONSTRAINED region
        first_deriv = np.gradient(region_of_interest)
        
        # Second derivative of the CONSTRAINED region
        second_deriv = np.gradient(first_deriv)
        
        # Time array for the constrained region
        region_time = time_data[peak_idx_abs:lifting_80pct_idx+1]
        
        # Find zero crossings and thresholds
        # 1st derivative: negative to positive zero crossing
        first_deriv_crossing_idx = find_first_derivative_zero_crossing(first_deriv, 0)
        first_deriv_threshold_idx = find_first_derivative_threshold(first_deriv, threshold_pct=0.10)
        
        # 2nd derivative: zero crossing and threshold after highest positive peak
        second_deriv_crossing_idx, second_deriv_peak_idx = find_second_derivative_propagation_end(second_deriv)
        second_deriv_threshold_idx, _ = find_second_derivative_threshold(second_deriv, threshold_pct=0.10)
        
        # Convert to absolute time values
        peak_time_val = peak_time
        
        first_deriv_time = None
        if first_deriv_crossing_idx is not None:
            first_deriv_time = region_time[first_deriv_crossing_idx]
        
        first_deriv_threshold_time = None
        if first_deriv_threshold_idx is not None:
            first_deriv_threshold_time = region_time[first_deriv_threshold_idx]
        
        second_deriv_time = region_time[second_deriv_crossing_idx]
        second_deriv_peak_time = region_time[second_deriv_peak_idx]
        second_deriv_threshold_time = region_time[second_deriv_threshold_idx]
        
        # === SET COMMON X-AXIS LIMITS FOR ALL THREE PLOTS ===
        # Use the visualization window for consistent alignment
        x_min = time_window_start
        x_max = time_window_end
        
        # === ROW 1: Smoothed Force ===
        ax = axes[0, layer_idx]
        ax.plot(window_time, window_force, 'b-', linewidth=2, label='Smoothed Force')
        ax.axvline(peak_time_val, color='red', linestyle='--', linewidth=2, 
                   label='Peak Force', alpha=0.7)
        ax.axvline(lifting_80pct_time, color='cyan', linestyle=':', linewidth=2,
                   label='80% Lifting Point', alpha=0.7)
        if first_deriv_time:
            ax.axvline(first_deriv_time, color='orange', linestyle='--', linewidth=2,
                       label='1st Deriv Zero Cross', alpha=0.7)
        if first_deriv_threshold_time:
            ax.axvline(first_deriv_threshold_time, color='gold', linestyle='--', linewidth=2,
                       label='1st Deriv 10% Thresh', alpha=0.7)
        ax.axvline(second_deriv_peak_time, color='green', linestyle='-.', linewidth=2,
                   label='2nd Deriv Peak', alpha=0.7)
        ax.axvline(second_deriv_time, color='purple', linestyle='--', linewidth=2,
                   label='2nd Deriv Zero Cross', alpha=0.7)
        ax.axvline(second_deriv_threshold_time, color='magenta', linestyle='--', linewidth=2,
                   label='2nd Deriv 10% Thresh', alpha=0.7)
        ax.set_xlim(x_min, x_max)
        ax.set_xlabel('Time (s)', fontsize=10, fontweight='bold')
        ax.set_ylabel('Force (N)', fontsize=10, fontweight='bold')
        ax.set_title(f'Layer {layer_num} - Smoothed Force', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=7, loc='best')
        
        # === ROW 2: First Derivative ===
        ax = axes[1, layer_idx]
        ax.plot(region_time, first_deriv, 'g-', linewidth=2, label='1st Derivative')
        ax.axhline(0, color='black', linestyle='-', linewidth=1, alpha=0.3)
        
        # Add threshold line
        min_val = np.min(first_deriv)
        threshold_val = min_val * 0.10
        ax.axhline(threshold_val, color='gold', linestyle=':', linewidth=1, alpha=0.5,
                   label=f'10% Threshold ({threshold_val:.4f})')
        
        ax.axvline(peak_time_val, color='red', linestyle='--', linewidth=2,
                   label='Peak Force', alpha=0.7)
        ax.axvline(lifting_80pct_time, color='cyan', linestyle=':', linewidth=2,
                   label='80% Lifting Point', alpha=0.7)
        if first_deriv_time:
            ax.axvline(first_deriv_time, color='orange', linestyle='--', linewidth=2,
                       label='Zero Crossing', alpha=0.7)
        if first_deriv_threshold_time:
            ax.axvline(first_deriv_threshold_time, color='gold', linestyle='--', linewidth=2,
                       label='10% Threshold', alpha=0.7)
        ax.axvline(second_deriv_peak_time, color='green', linestyle='-.', linewidth=2,
                   label='2nd Deriv Peak', alpha=0.7)
        ax.axvline(second_deriv_time, color='purple', linestyle='--', linewidth=2,
                   label='2nd Deriv Zero', alpha=0.7)
        ax.axvline(second_deriv_threshold_time, color='magenta', linestyle='--', linewidth=2,
                   label='2nd Deriv 10%', alpha=0.7)
        ax.set_xlim(x_min, x_max)
        ax.set_xlabel('Time (s)', fontsize=10, fontweight='bold')
        ax.set_ylabel('dF/dt', fontsize=10, fontweight='bold')
        ax.set_title(f'Layer {layer_num} - First Derivative', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=7, loc='best')
        
        # === ROW 3: Second Derivative ===
        ax = axes[2, layer_idx]
        ax.plot(region_time, second_deriv, 'm-', linewidth=2, label='2nd Derivative')
        ax.axhline(0, color='black', linestyle='-', linewidth=1, alpha=0.3)
        
        # Add threshold line
        positive_mask = second_deriv > 0
        if np.any(positive_mask):
            max_val = np.max(second_deriv[positive_mask])
        else:
            max_val = np.max(second_deriv)
        threshold_val_2nd = max_val * 0.10
        ax.axhline(threshold_val_2nd, color='magenta', linestyle=':', linewidth=1, alpha=0.5,
                   label=f'10% Threshold ({threshold_val_2nd:.4f})')
        
        ax.axvline(peak_time_val, color='red', linestyle='--', linewidth=2,
                   label='Peak Force', alpha=0.7)
        ax.axvline(lifting_80pct_time, color='cyan', linestyle=':', linewidth=2,
                   label='80% Lifting Point', alpha=0.7)
        if first_deriv_time:
            ax.axvline(first_deriv_time, color='orange', linestyle='--', linewidth=2,
                       label='1st Deriv Zero', alpha=0.7)
        if first_deriv_threshold_time:
            ax.axvline(first_deriv_threshold_time, color='gold', linestyle='--', linewidth=2,
                       label='1st Deriv 10%', alpha=0.7)
        ax.axvline(second_deriv_peak_time, color='green', linestyle='-.', linewidth=2,
                   label='Max Peak', alpha=0.7)
        ax.axvline(second_deriv_time, color='purple', linestyle='--', linewidth=2,
                   label='Zero Cross', alpha=0.7)
        ax.axvline(second_deriv_threshold_time, color='magenta', linestyle='--', linewidth=2,
                   label='10% Threshold', alpha=0.7)
        ax.set_xlim(x_min, x_max)
        
        # Mark the highest positive peak with a star
        positive_mask = second_deriv > 0
        if np.any(positive_mask):
            positive_deriv = second_deriv.copy()
            positive_deriv[~positive_mask] = -np.inf
            max_idx = np.argmax(positive_deriv)
            max_time = region_time[max_idx]
            ax.plot(max_time, second_deriv[max_idx], 'g*', markersize=15)
        
        ax.set_xlabel('Time (s)', fontsize=10, fontweight='bold')
        ax.set_ylabel('d²F/dt²', fontsize=10, fontweight='bold')
        ax.set_title(f'Layer {layer_num} - Second Derivative', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8, loc='best')
        
        print(f"\nLayer {layer_num} Analysis:")
        print(f"  Peak time: {peak_time_val:.3f} s")
        print(f"  80% lifting point: {lifting_80pct_time:.3f} s ({lifting_80pct_time - peak_time_val:.3f}s after peak)")
        print(f"\n  1st derivative:")
        if first_deriv_time:
            print(f"    Zero crossing: {first_deriv_time:.3f} s ({first_deriv_time - peak_time_val:.3f}s after peak)")
        else:
            print(f"    Zero crossing: NOT FOUND")
        if first_deriv_threshold_time:
            print(f"    10% threshold: {first_deriv_threshold_time:.3f} s ({first_deriv_threshold_time - peak_time_val:.3f}s after peak)")
        else:
            print(f"    10% threshold: NOT FOUND")
        
        print(f"\n  2nd derivative:")
        print(f"    Peak (fastest decay): {second_deriv_peak_time:.3f} s ({second_deriv_peak_time - peak_time_val:.3f}s after peak)")
        print(f"    Zero crossing (current): {second_deriv_time:.3f} s ({second_deriv_time - peak_time_val:.3f}s after peak)")
        print(f"    10% threshold (NEW): {second_deriv_threshold_time:.3f} s ({second_deriv_threshold_time - peak_time_val:.3f}s after peak)")
        
        print(f"\n  Constrained region length: {len(region_of_interest)} points ({lifting_80pct_time - peak_time_val:.3f}s duration)")
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"\n✓ Troubleshooting plot saved to: {output_path}")
    else:
        plt.show()
    
    plt.close()


if __name__ == "__main__":
    # Files to analyze
    test_files = [
        r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V2\Water_1mm_SteppedCone_BPAGDA_6000\autolog_L430-L435.csv",
        r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V2\Water_1mm_SteppedCone_BPAGDA_6000\autolog_L365-L370.csv",
        r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V2\Water_1mm_SteppedCone_BPAGDA_6000\autolog_L60-L65.csv"
    ]
    
    base_output_dir = r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V2\Water_1mm_SteppedCone_BPAGDA_6000"
    
    print("="*80)
    print("Propagation End Troubleshooting Tool")
    print("="*80)
    
    for test_file in test_files:
        file_name = Path(test_file).stem  # Get filename without extension
        output_file = os.path.join(base_output_dir, f"TROUBLESHOOT_{file_name}.png")
        
        print(f"\n{'='*80}")
        print(f"Processing: {Path(test_file).name}")
        print(f"{'='*80}")
        
        plot_troubleshooting_derivatives(test_file, output_file)
        
        print(f"\n✓ Plot saved to: {output_file}")
    
    print("\n" + "="*80)
    print("All analyses complete!")
    print("="*80)
    print("\nReview the plots to check:")
    print("  1. Does the 10% threshold (magenta) look better than zero crossing (purple)?")
    print("  2. Is the propagation end detection consistent across speeds?")
    print("  3. Are we choosing the right point (last before crossing)?")
    print("  4. Should we adjust the threshold percentage?")
