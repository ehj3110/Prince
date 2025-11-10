"""
Debug Single Layer Derivatives
===============================

Plots force, 1st derivative, and 2nd derivative for a single layer
to help tune propagation end detection.

Usage:
    python debug_single_layer_derivatives.py test_autolog_L430-L435.csv 1
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import sys

# Add support modules to path
sys.path.insert(0, str(Path(__file__).parent / "support_modules"))
sys.path.insert(0, str(Path(__file__).parent / "post-processing"))

from adhesion_metrics_calculator import AdhesionMetricsCalculator
from RawData_Processor import RawDataProcessor


def plot_layer_derivatives(csv_filepath: str, layer_index: int = 0):
    """
    Plots force and derivatives for a specific layer.
    
    Args:
        csv_filepath: Path to CSV file
        layer_index: 0-based layer index (0 = first layer)
    """
    print(f"Loading: {csv_filepath}")
    
    # Load data and process to find boundaries
    calculator = AdhesionMetricsCalculator()
    processor = RawDataProcessor(calculator)
    
    # Process the file to get layer boundaries
    layers = processor.process_csv(csv_filepath)
    
    if not layers:
        print("ERROR: No layers detected!")
        return
    
    if layer_index >= len(layers):
        print(f"ERROR: Layer index {layer_index} out of range. Found {len(layers)} layers.")
        return
    
    # Get the target layer
    layer = layers[layer_index]
    layer_num = layer['number']
    print(f"\nAnalyzing Layer {layer_num}")
    
    # Load full data
    df = pd.read_csv(csv_filepath)
    time_data_full = df['Elapsed Time (s)'].to_numpy()
    force_data_full = df['Force (N)'].to_numpy()
    position_data_full = df['Position (mm)'].to_numpy()
    
    # Get boundary info
    if 'phases' in layer:
        lift_start, lift_end = layer['phases']['lifting']
        retract_start, retract_end = layer['phases']['retraction']
    else:
        print("ERROR: No phase boundary information in layer!")
        return
    
    # Extract layer data (lifting phase only)
    time_data = time_data_full[lift_start:lift_end+1]
    force_data = force_data_full[lift_start:lift_end+1]
    position_data = position_data_full[lift_start:lift_end+1]
    
    # Make time relative to layer start
    time_data_relative = time_data - time_data[0]
    
    print(f"  Lifting phase: indices {lift_start}-{lift_end} ({len(time_data)} points)")
    print(f"  Time range: {time_data[0]:.3f}s to {time_data[-1]:.3f}s")
    
    # Apply smoothing
    smoothed_force = calculator._apply_smoothing(force_data)
    
    # Find peak
    peak_idx_local = np.argmax(smoothed_force)
    peak_force = smoothed_force[peak_idx_local]
    peak_time = time_data_relative[peak_idx_local]
    
    # Find propagation end
    prop_end_idx_local = calculator._find_propagation_end_reverse_search(
        smoothed_force, 
        peak_idx_local, 
        position_data, 
        motion_end_idx=len(smoothed_force)-1
    )
    prop_end_time = time_data_relative[prop_end_idx_local]
    prop_end_force = smoothed_force[prop_end_idx_local]
    
    # Calculate baseline
    baseline = calculator._calculate_baseline(smoothed_force, prop_end_idx_local)
    
    # Calculate derivatives
    first_deriv = np.gradient(smoothed_force)
    second_deriv = np.gradient(first_deriv)
    
    # Find the most prominent negative peak in first derivative (what the algorithm uses)
    from scipy.signal import find_peaks
    region_for_analysis = first_deriv[peak_idx_local:]
    inverted_deriv = -region_for_analysis
    peaks, properties = find_peaks(inverted_deriv, prominence=0.001)
    
    if len(peaks) > 0:
        most_prominent_peak_idx = peaks[np.argmax(properties['prominences'])]
        prominent_peak_local_idx = peak_idx_local + most_prominent_peak_idx
        prominent_peak_time = time_data_relative[prominent_peak_local_idx]
        prominent_peak_value = first_deriv[prominent_peak_local_idx]
    else:
        # Fallback to minimum
        min_idx = np.argmin(region_for_analysis)
        prominent_peak_local_idx = peak_idx_local + min_idx
        prominent_peak_time = time_data_relative[prominent_peak_local_idx]
        prominent_peak_value = first_deriv[prominent_peak_local_idx]
    
    # Find max second derivative after peak (for reference)
    second_deriv_after_peak = second_deriv[peak_idx_local:]
    max_2nd_deriv_local_idx = peak_idx_local + np.argmax(second_deriv_after_peak)
    max_2nd_deriv_time = time_data_relative[max_2nd_deriv_local_idx]
    
    # Create figure
    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
    fig.suptitle(f'Derivative Analysis - Layer {layer_num}\n'
                 f'File: {Path(csv_filepath).name}', 
                 fontsize=14, fontweight='bold')
    
    # Panel 1: Force
    ax1 = axes[0]
    ax1.plot(time_data_relative, force_data, 'gray', alpha=0.3, linewidth=0.5, label='Raw Force')
    ax1.plot(time_data_relative, smoothed_force, 'b-', linewidth=2, label='Smoothed Force')
    ax1.axvline(peak_time, color='red', linestyle='--', linewidth=1.5, label=f'Peak ({peak_force:.4f} N)')
    ax1.axvline(prop_end_time, color='green', linestyle='--', linewidth=1.5, 
                label=f'Prop End ({prop_end_time:.3f}s)')
    ax1.axhline(baseline, color='purple', linestyle=':', linewidth=1.5, 
                label=f'Baseline ({baseline:.4f} N)')
    ax1.plot(peak_time, peak_force, 'ro', markersize=8)
    ax1.plot(prop_end_time, prop_end_force, 'go', markersize=8)
    ax1.set_ylabel('Force (N)', fontsize=11)
    ax1.set_title('Force Profile', fontsize=12)
    ax1.legend(loc='best', fontsize=9)
    ax1.grid(True, alpha=0.3)
    
    # Panel 2: First Derivative
    ax2 = axes[1]
    ax2.plot(time_data_relative, first_deriv, 'm-', linewidth=1.5, label='dF/dt')
    ax2.axvline(peak_time, color='red', linestyle='--', linewidth=1.5, label='Peak')
    ax2.axvline(prop_end_time, color='green', linestyle='--', linewidth=1.5, label='Prop End')
    ax2.axvline(prominent_peak_time, color='orange', linestyle='-.', linewidth=2, 
                label=f'Prominent Neg Peak ({prominent_peak_value:.4f})')
    ax2.plot(prominent_peak_time, prominent_peak_value, 'o', color='orange', markersize=8)
    # Show 10% threshold line
    threshold_value = prominent_peak_value * 0.10
    ax2.axhline(threshold_value, color='orange', linestyle=':', linewidth=1, 
                label=f'10% Threshold ({threshold_value:.4f})')
    ax2.axhline(0, color='black', linestyle=':', alpha=0.5)
    ax2.set_ylabel('dF/dt (N/point)', fontsize=11)
    ax2.set_title('First Derivative', fontsize=12)
    ax2.legend(loc='best', fontsize=9)
    ax2.grid(True, alpha=0.3)
    
    # Panel 3: Second Derivative
    ax3 = axes[2]
    ax3.plot(time_data_relative, second_deriv, 'c-', linewidth=1.5, label='d²F/dt²')
    ax3.axvline(peak_time, color='red', linestyle='--', linewidth=1.5, label='Peak')
    ax3.axvline(prop_end_time, color='green', linestyle='--', linewidth=1.5, label='Prop End')
    ax3.axvline(max_2nd_deriv_time, color='orange', linestyle='-.', linewidth=2, 
                label=f'Max d²F/dt² ({max_2nd_deriv_time:.3f}s)')
    ax3.plot(max_2nd_deriv_time, second_deriv[max_2nd_deriv_local_idx], 'o', 
             color='orange', markersize=8)
    ax3.axhline(0, color='black', linestyle=':', alpha=0.5)
    ax3.set_xlabel('Time (s)', fontsize=11)
    ax3.set_ylabel('d²F/dt² (N/point²)', fontsize=11)
    ax3.set_title('Second Derivative', fontsize=12)
    ax3.legend(loc='best', fontsize=9)
    ax3.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save plot
    output_filename = f"debug_derivatives_Layer{layer_num}.png"
    plt.savefig(output_filename, dpi=150, bbox_inches='tight')
    print(f"\n✓ Plot saved: {output_filename}")
    
    # Print metrics
    print(f"\nMetrics:")
    print(f"  Peak Force: {peak_force:.4f} N at {peak_time:.3f}s")
    print(f"  Prop End: {prop_end_force:.4f} N at {prop_end_time:.3f}s")
    print(f"  Baseline: {baseline:.4f} N")
    print(f"  Duration (peak to prop end): {prop_end_time - peak_time:.3f}s")
    print(f"  Prominent neg peak in dF/dt: {prominent_peak_value:.4f} at {prominent_peak_time:.3f}s")
    print(f"  10% threshold: {prominent_peak_value * 0.10:.4f}")
    print(f"  Max 2nd derivative at: {max_2nd_deriv_time:.3f}s")
    
    plt.show()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_single_layer_derivatives.py <csv_file> [layer_index]")
        print("  layer_index: 0-based index (default: 0 = first layer)")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    layer_idx = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    
    if not Path(csv_file).exists():
        print(f"ERROR: File not found: {csv_file}")
        sys.exit(1)
    
    plot_layer_derivatives(csv_file, layer_idx)
