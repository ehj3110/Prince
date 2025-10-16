"""
Troubleshooting Script for Propagation End Detection - DERIVATIVE SMOOTHING COMPARISON

Generates TWO 3x3 plot arrays for the first 3 layers:
- LEFT FIGURE: RAW derivatives (no additional smoothing on derivatives)
- RIGHT FIGURE: SMOOTHED derivatives (Savgol filter applied to derivatives)

BOTH use smoothed force data as the starting point, but differ in whether
the derivatives themselves are smoothed.

Each shows:
- Row 1: Smoothed force data
- Row 2: First derivative of force
- Row 3: Second derivative of force
"""

import sys
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


def find_second_derivative_propagation_end(second_deriv):
    """
    Find propagation end using second derivative method:
    1. Find highest positive peak of 2nd derivative
    2. Find first zero crossing after that peak
    
    Returns index relative to the derivative array.
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
            return i
    
    # If no crossing found, use halfway point
    return max_idx + int(0.5 * (len(second_deriv) - max_idx))


def plot_comparison(csv_filepath, output_path=None):
    """
    Create side-by-side comparison: raw derivatives vs smoothed derivatives.
    Both use the same smoothed force data as input.
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
    
    # Apply smoothing to force data (SAME FOR BOTH FIGURES)
    smoothed_force = calc._apply_smoothing(force_data)
    
    # Process first 3 layers only
    num_layers = min(3, len(layers))
    
    # Create TWO figures side-by-side
    fig_raw_deriv, axes_raw_deriv = plt.subplots(3, num_layers, figsize=(6*num_layers, 12))
    fig_smooth_deriv, axes_smooth_deriv = plt.subplots(3, num_layers, figsize=(6*num_layers, 12))
    
    if num_layers == 1:
        axes_raw_deriv = axes_raw_deriv.reshape(3, 1)
        axes_smooth_deriv = axes_smooth_deriv.reshape(3, 1)
    
    for layer_idx in range(num_layers):
        layer = layers[layer_idx]
        layer_num = layer['number']
        
        # Get indices for this layer's lifting phase
        start_idx = layer['start_idx']
        end_idx = layer['end_idx']
        
        # === COMMON PROCESSING (SAME FOR BOTH) ===
        # Find peak in smoothed data
        layer_force_smooth = smoothed_force[start_idx:end_idx+1]
        peak_idx_relative = np.argmax(layer_force_smooth)
        peak_idx_abs = start_idx + peak_idx_relative
        peak_time = time_data[peak_idx_abs]
        
        # Calculate 80% lifting point
        travel_positions = position_data[peak_idx_abs:end_idx+1]
        min_pos = np.min(travel_positions)
        max_pos = position_data[peak_idx_abs]
        target_position = max_pos - 0.8 * (max_pos - min_pos)
        
        lifting_80pct_idx = peak_idx_abs
        for i in range(peak_idx_abs, end_idx+1):
            if position_data[i] <= target_position:
                lifting_80pct_idx = i
                break
        else:
            min_pos_relative_idx = np.argmin(travel_positions)
            lifting_80pct_idx = peak_idx_abs + min_pos_relative_idx
        
        lifting_80pct_time = time_data[lifting_80pct_idx]
        
        # Region of interest (SAME FOR BOTH)
        region_force = smoothed_force[peak_idx_abs:lifting_80pct_idx+1]
        region_time = time_data[peak_idx_abs:lifting_80pct_idx+1]
        
        # === RAW DERIVATIVES (NO ADDITIONAL SMOOTHING) ===
        first_deriv_raw = np.gradient(region_force)
        second_deriv_raw = np.gradient(first_deriv_raw)
        
        first_zero_raw = find_first_derivative_zero_crossing(first_deriv_raw, 0)
        second_zero_raw = find_second_derivative_propagation_end(second_deriv_raw)
        
        first_deriv_time_raw = region_time[first_zero_raw] if first_zero_raw else None
        second_deriv_time_raw = region_time[second_zero_raw]
        
        # === SMOOTHED DERIVATIVES (APPLY SAVGOL TO DERIVATIVES) ===
        from scipy.signal import savgol_filter
        
        # Smooth the first derivative
        if len(first_deriv_raw) >= 9:
            first_deriv_smooth = savgol_filter(first_deriv_raw, window_length=9, polyorder=2)
        else:
            first_deriv_smooth = first_deriv_raw.copy()
        
        # Smooth the second derivative
        second_deriv_pre = np.gradient(first_deriv_smooth)
        if len(second_deriv_pre) >= 9:
            second_deriv_smooth = savgol_filter(second_deriv_pre, window_length=9, polyorder=2)
        else:
            second_deriv_smooth = second_deriv_pre.copy()
        
        first_zero_smooth = find_first_derivative_zero_crossing(first_deriv_smooth, 0)
        second_zero_smooth = find_second_derivative_propagation_end(second_deriv_smooth)
        
        first_deriv_time_smooth = region_time[first_zero_smooth] if first_zero_smooth else None
        second_deriv_time_smooth = region_time[second_zero_smooth]
        
        # === VISUALIZATION WINDOW ===
        time_window_start = peak_time - 0.25
        time_window_end = peak_time + 1.0
        
        window_mask = (time_data >= time_window_start) & (time_data <= time_window_end)
        window_indices = np.where(window_mask)[0]
        
        if len(window_indices) == 0:
            continue
        
        window_start = window_indices[0]
        window_end = window_indices[-1]
        window_time = time_data[window_start:window_end+1]
        window_force_smooth = smoothed_force[window_start:window_end+1]
        
        x_min = time_window_start
        x_max = time_window_end
        
        # ============================================================
        # RAW DERIVATIVE PLOTS (LEFT FIGURE)
        # ============================================================
        
        # Row 1: Smoothed Force
        ax = axes_raw_deriv[0, layer_idx]
        ax.plot(window_time, window_force_smooth, 'b-', linewidth=2, label='Smoothed Force')
        ax.axvline(peak_time, color='red', linestyle='--', linewidth=2, 
                   label='Peak Force', alpha=0.7)
        ax.axvline(lifting_80pct_time, color='cyan', linestyle=':', linewidth=2,
                   label='80% Lifting Point', alpha=0.7)
        if first_deriv_time_raw:
            ax.axvline(first_deriv_time_raw, color='orange', linestyle='--', linewidth=2,
                       label='1st Deriv Zero Cross', alpha=0.7)
        ax.axvline(second_deriv_time_raw, color='purple', linestyle='--', linewidth=2,
                   label='2nd Deriv Zero Cross\n(Prop End)', alpha=0.7)
        ax.set_xlim(x_min, x_max)
        ax.set_xlabel('Time (s)', fontsize=10, fontweight='bold')
        ax.set_ylabel('Force (N)', fontsize=10, fontweight='bold')
        ax.set_title(f'Layer {layer_num} - Smoothed Force', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=7, loc='best')
        
        # Row 2: First Derivative (RAW - no additional smoothing)
        ax = axes_raw_deriv[1, layer_idx]
        ax.plot(region_time, first_deriv_raw, 'g-', linewidth=2, label='1st Deriv (Raw)')
        ax.axhline(0, color='black', linestyle='-', linewidth=1, alpha=0.3)
        ax.axvline(peak_time, color='red', linestyle='--', linewidth=2, alpha=0.7)
        ax.axvline(lifting_80pct_time, color='cyan', linestyle=':', linewidth=2, alpha=0.7)
        if first_deriv_time_raw:
            ax.axvline(first_deriv_time_raw, color='orange', linestyle='--', linewidth=2, alpha=0.7)
        ax.axvline(second_deriv_time_raw, color='purple', linestyle='--', linewidth=2, alpha=0.7)
        ax.set_xlim(x_min, x_max)
        ax.set_xlabel('Time (s)', fontsize=10, fontweight='bold')
        ax.set_ylabel('dF/dt', fontsize=10, fontweight='bold')
        ax.set_title(f'Layer {layer_num} - 1st Deriv (RAW)', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=7, loc='best')
        
        # Row 3: Second Derivative (RAW - no additional smoothing)
        ax = axes_raw_deriv[2, layer_idx]
        ax.plot(region_time, second_deriv_raw, 'm-', linewidth=2, label='2nd Deriv (Raw)')
        ax.axhline(0, color='black', linestyle='-', linewidth=1, alpha=0.3)
        ax.axvline(peak_time, color='red', linestyle='--', linewidth=2, alpha=0.7)
        ax.axvline(lifting_80pct_time, color='cyan', linestyle=':', linewidth=2, alpha=0.7)
        if first_deriv_time_raw:
            ax.axvline(first_deriv_time_raw, color='orange', linestyle='--', linewidth=2, alpha=0.7)
        ax.axvline(second_deriv_time_raw, color='purple', linestyle='--', linewidth=2, alpha=0.7)
        
        # Mark highest positive peak
        positive_mask = second_deriv_raw > 0
        if np.any(positive_mask):
            positive_deriv = second_deriv_raw.copy()
            positive_deriv[~positive_mask] = -np.inf
            max_idx = np.argmax(positive_deriv)
            max_time = region_time[max_idx]
            ax.plot(max_time, second_deriv_raw[max_idx], 'r*', markersize=15)
        
        ax.set_xlim(x_min, x_max)
        ax.set_xlabel('Time (s)', fontsize=10, fontweight='bold')
        ax.set_ylabel('d²F/dt²', fontsize=10, fontweight='bold')
        ax.set_title(f'Layer {layer_num} - 2nd Deriv (RAW)', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=7, loc='best')
        
        # ============================================================
        # SMOOTHED DERIVATIVE PLOTS (RIGHT FIGURE)
        # ============================================================
        
        # Row 1: Smoothed Force (SAME AS LEFT)
        ax = axes_smooth_deriv[0, layer_idx]
        ax.plot(window_time, window_force_smooth, 'b-', linewidth=2, label='Smoothed Force')
        ax.axvline(peak_time, color='red', linestyle='--', linewidth=2, 
                   label='Peak Force', alpha=0.7)
        ax.axvline(lifting_80pct_time, color='cyan', linestyle=':', linewidth=2,
                   label='80% Lifting Point', alpha=0.7)
        if first_deriv_time_smooth:
            ax.axvline(first_deriv_time_smooth, color='orange', linestyle='--', linewidth=2,
                       label='1st Deriv Zero Cross', alpha=0.7)
        ax.axvline(second_deriv_time_smooth, color='purple', linestyle='--', linewidth=2,
                   label='2nd Deriv Zero Cross\n(Prop End)', alpha=0.7)
        ax.set_xlim(x_min, x_max)
        ax.set_xlabel('Time (s)', fontsize=10, fontweight='bold')
        ax.set_ylabel('Force (N)', fontsize=10, fontweight='bold')
        ax.set_title(f'Layer {layer_num} - Smoothed Force', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=7, loc='best')
        
        # Row 2: First Derivative (SMOOTHED with Savgol)
        ax = axes_smooth_deriv[1, layer_idx]
        ax.plot(region_time, first_deriv_smooth, 'g-', linewidth=2, label='1st Deriv (Smoothed)')
        ax.axhline(0, color='black', linestyle='-', linewidth=1, alpha=0.3)
        ax.axvline(peak_time, color='red', linestyle='--', linewidth=2, alpha=0.7)
        ax.axvline(lifting_80pct_time, color='cyan', linestyle=':', linewidth=2, alpha=0.7)
        if first_deriv_time_smooth:
            ax.axvline(first_deriv_time_smooth, color='orange', linestyle='--', linewidth=2, alpha=0.7)
        ax.axvline(second_deriv_time_smooth, color='purple', linestyle='--', linewidth=2, alpha=0.7)
        ax.set_xlim(x_min, x_max)
        ax.set_xlabel('Time (s)', fontsize=10, fontweight='bold')
        ax.set_ylabel('dF/dt', fontsize=10, fontweight='bold')
        ax.set_title(f'Layer {layer_num} - 1st Deriv (SMOOTHED)', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=7, loc='best')
        
        # Row 3: Second Derivative (SMOOTHED with Savgol)
        ax = axes_smooth_deriv[2, layer_idx]
        ax.plot(region_time, second_deriv_smooth, 'm-', linewidth=2, label='2nd Deriv (Smoothed)')
        ax.axhline(0, color='black', linestyle='-', linewidth=1, alpha=0.3)
        ax.axvline(peak_time, color='red', linestyle='--', linewidth=2, alpha=0.7)
        ax.axvline(lifting_80pct_time, color='cyan', linestyle=':', linewidth=2, alpha=0.7)
        if first_deriv_time_smooth:
            ax.axvline(first_deriv_time_smooth, color='orange', linestyle='--', linewidth=2, alpha=0.7)
        ax.axvline(second_deriv_time_smooth, color='purple', linestyle='--', linewidth=2, alpha=0.7)
        
        # Mark highest positive peak
        positive_mask = second_deriv_smooth > 0
        if np.any(positive_mask):
            positive_deriv = second_deriv_smooth.copy()
            positive_deriv[~positive_mask] = -np.inf
            max_idx = np.argmax(positive_deriv)
            max_time = region_time[max_idx]
            ax.plot(max_time, second_deriv_smooth[max_idx], 'r*', markersize=15)
        
        ax.set_xlim(x_min, x_max)
        ax.set_xlabel('Time (s)', fontsize=10, fontweight='bold')
        ax.set_ylabel('d²F/dt²', fontsize=10, fontweight='bold')
        ax.set_title(f'Layer {layer_num} - 2nd Deriv (SMOOTHED)', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=7, loc='best')
        
        # Print comparison
        print(f"\n{'='*60}")
        print(f"Layer {layer_num} Comparison:")
        print(f"{'='*60}")
        print(f"\nRAW DERIVATIVES (no additional smoothing):")
        print(f"  Peak time: {peak_time:.3f} s")
        print(f"  1st deriv zero: {first_deriv_time_raw:.3f}s" if first_deriv_time_raw else "  1st deriv zero: NOT FOUND")
        print(f"  2nd deriv zero (prop end): {second_deriv_time_raw:.3f}s")
        
        print(f"\nSMOOTHED DERIVATIVES (Savgol filter applied):")
        print(f"  Peak time: {peak_time:.3f} s")
        print(f"  1st deriv zero: {first_deriv_time_smooth:.3f}s" if first_deriv_time_smooth else "  1st deriv zero: NOT FOUND")
        print(f"  2nd deriv zero (prop end): {second_deriv_time_smooth:.3f}s")
    
    # Save figures
    fig_raw_deriv.tight_layout()
    fig_smooth_deriv.tight_layout()
    
    if output_path:
        base_path = Path(output_path)
        raw_deriv_path = base_path.parent / f"{base_path.stem}_RAW_DERIV{base_path.suffix}"
        smooth_deriv_path = base_path.parent / f"{base_path.stem}_SMOOTH_DERIV{base_path.suffix}"
        
        fig_raw_deriv.savefig(raw_deriv_path, dpi=300, bbox_inches='tight')
        fig_smooth_deriv.savefig(smooth_deriv_path, dpi=300, bbox_inches='tight')
        
        print(f"\n✓ RAW DERIVATIVE plot saved to: {raw_deriv_path}")
        print(f"✓ SMOOTHED DERIVATIVE plot saved to: {smooth_deriv_path}")
    else:
        plt.show()
    
    plt.close('all')


if __name__ == "__main__":
    test_file = r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V2\Water_1mm_SteppedCone_BPAGDA_6000\autolog_L430-L435.csv"
    
    output_file = r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V2\Water_1mm_SteppedCone_BPAGDA_6000\TROUBLESHOOT_comparison.png"
    
    print("="*60)
    print("Propagation End Comparison: RAW vs SMOOTHED DERIVATIVES")
    print("="*60)
    print(f"\nProcessing: {Path(test_file).name}")
    print("\nBOTH figures use smoothed force data.")
    print("LEFT: Raw derivatives (np.gradient only)")
    print("RIGHT: Smoothed derivatives (Savgol filter applied)")
    
    plot_comparison(test_file, output_file)
    
    print("\n" + "="*60)
    print("Comparison complete!")
    print("="*60)
    print("\nCompare the two figures to see:")
    print("  - How derivative smoothing affects zero-crossing detection")
    print("  - Whether raw derivatives give sharper transitions")
    print("  - Which method is more reliable at 6000 µm/s")
