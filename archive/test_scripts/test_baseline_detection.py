#!/usr/bin/env python3
"""
Test script for baseline detection methods.
Visualizes smoothed force data and its derivatives for a specific layer.
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))
sys.path.insert(0, str(parent_dir / "support_modules"))
sys.path.insert(0, str(Path(__file__).parent))

from adhesion_metrics_calculator import AdhesionMetricsCalculator
import pandas as pd


def find_autolog_with_layer(master_folder, target_layer):
    """
    Find autolog CSV file that contains the target layer.
    
    Args:
        master_folder: Path to V17Tests folder
        target_layer: Layer number to find (e.g., 111)
    
    Returns:
        Path to autolog file or None if not found
    """
    master_path = Path(master_folder)
    
    # Search all subdirectories for autolog files
    for autolog_file in master_path.rglob("autolog_*.csv"):
        # Extract layer range from filename
        filename = autolog_file.stem
        if 'L' in filename and '-' in filename:
            try:
                import re
                layer_nums = re.findall(r'L(\d+)', filename)
                if len(layer_nums) >= 2:
                    start = int(layer_nums[0])
                    end = int(layer_nums[1])
                    if start <= target_layer <= end:
                        return autolog_file
            except:
                continue
    
    return None


def extract_layer_data(csv_file, target_layer):
    """
    Extract data for a specific layer from autolog CSV.
    Uses the same layer boundary detection as RawData_Processor.
    
    Args:
        csv_file: Path to autolog CSV
        target_layer: Layer number to extract
    
    Returns:
        Dictionary with time, position, force arrays for the layer
    """
    # Load CSV
    df = pd.read_csv(csv_file)
    time_data = df['Elapsed Time (s)'].to_numpy()
    force_data = df['Force (N)'].to_numpy()
    position_data = df['Position (mm)'].to_numpy()
    
    # Smooth force for peak detection
    calculator = AdhesionMetricsCalculator(smoothing_sigma=0.5)
    smoothed_force = calculator._apply_smoothing(force_data)
    
    # Use RawData_Processor for layer boundary detection
    from RawData_Processor import RawDataProcessor
    processor = RawDataProcessor(calculator, None)
    
    # Get layer numbers from filename
    import re
    filename = Path(csv_file).stem
    layer_nums = re.findall(r'L(\d+)', filename)
    start_layer = int(layer_nums[0])
    end_layer = int(layer_nums[1])
    layer_numbers = list(range(start_layer, end_layer + 1))
    
    # Detect peaks
    from scipy.signal import find_peaks
    peaks, _ = find_peaks(smoothed_force, height=0.01, distance=150, prominence=0.005)
    print(f"Detected {len(peaks)} peaks in file")
    
    # Find layer boundaries
    layer_boundaries = processor._find_layer_boundaries(peaks, position_data, time_data, layer_numbers)
    print(f"Found {len(layer_boundaries)} layer boundaries")
    
    # Find index for target layer
    layer_index = target_layer - start_layer
    
    if layer_index < 0 or layer_index >= len(layer_boundaries):
        raise ValueError(f"Layer {target_layer} not found in this file (index {layer_index}, boundaries: {len(layer_boundaries)})")
    
    start_idx, end_idx = layer_boundaries[layer_index]
    
    print(f"Layer {target_layer} data: indices {start_idx} to {end_idx}")
    
    return {
        'time': time_data[start_idx:end_idx+1],
        'position': position_data[start_idx:end_idx+1],
        'force': force_data[start_idx:end_idx+1],
        'start_idx': start_idx,
        'end_idx': end_idx,
        'smoothed_force': smoothed_force[start_idx:end_idx+1]
    }


def calculate_derivatives(time, smoothed_force):
    """
    Calculate first and second derivatives of smoothed force.
    
    Args:
        time: Time array
        smoothed_force: Smoothed force array
    
    Returns:
        Tuple of (first_derivative, second_derivative)
    """
    # First derivative: dF/dt
    first_deriv = np.gradient(smoothed_force, time)
    
    # Second derivative: d²F/dt²
    second_deriv = np.gradient(first_deriv, time)
    
    return first_deriv, second_deriv


def find_propagation_end_new_method(time, position, smoothed_force, peak_force_idx):
    """
    Find propagation end using new constrained search method.
    
    Searches within first 50% of data between peak force and end of lifting phase.
    Finds the peak of the second derivative, then finds first zero-crossing after that peak.
    
    Args:
        time: Time array
        position: Position array
        smoothed_force: Smoothed force array
        peak_force_idx: Index of peak force
    
    Returns:
        Tuple of (prop_end_idx, second_deriv_peak_idx)
    """
    # Find end of lifting motion (where stage stops moving down)
    # Look for when position stops decreasing
    motion_end_idx = peak_force_idx
    for i in range(peak_force_idx + 10, len(position) - 10):
        # Check if position has stabilized (stopped decreasing)
        window = position[i:i+10]
        if np.std(window) < 0.01:  # Stable position
            motion_end_idx = i
            break
    
    # Constrain search to first 50% between peak and motion end
    search_end_idx = peak_force_idx + int((motion_end_idx - peak_force_idx) * 0.5)
    
    print(f"  Force peak index: {peak_force_idx}")
    print(f"  Motion end index: {motion_end_idx}")
    print(f"  Search constrained to indices {peak_force_idx} - {search_end_idx} (50% of peak-to-motion-end)")
    
    # Calculate second derivative
    _, second_deriv = calculate_derivatives(time, smoothed_force)
    
    # Find the highest POSITIVE peak of the second derivative within search window
    search_region_2nd_deriv = second_deriv[peak_force_idx:search_end_idx]
    
    # Only consider positive values
    positive_mask = search_region_2nd_deriv > 0
    if not np.any(positive_mask):
        print("  WARNING: No positive values found in second derivative search region!")
        return peak_force_idx, peak_force_idx
    
    # Find the maximum among positive values
    positive_values = search_region_2nd_deriv[positive_mask]
    positive_indices = np.where(positive_mask)[0]
    max_positive_idx = positive_indices[np.argmax(positive_values)]
    second_deriv_peak_idx = peak_force_idx + max_positive_idx
    
    print(f"  Second derivative peak (max positive): {second_deriv[second_deriv_peak_idx]:.6f} at index {second_deriv_peak_idx}")
    
    # Find first zero-crossing of second derivative AFTER the second derivative peak
    prop_end_idx = search_end_idx  # Default to end of search window
    
    for i in range(second_deriv_peak_idx + 1, search_end_idx):
        # Look for zero crossing (sign change)
        if i < len(second_deriv) - 1:
            if (second_deriv[i-1] < 0 and second_deriv[i] >= 0) or \
               (second_deriv[i-1] > 0 and second_deriv[i] <= 0):
                prop_end_idx = i
                print(f"  Found second derivative zero-crossing at index {i} (after 2nd deriv peak)")
                break
    
    if prop_end_idx == search_end_idx:
        print(f"  No zero-crossing found, using end of search window at index {search_end_idx}")
    
    return prop_end_idx, second_deriv_peak_idx


def plot_force_and_derivatives(layer_data, target_layer):
    """
    Create a 3-panel plot showing force and its derivatives.
    Includes markers for peak force, second derivative peak, and propagation end.
    Plots are cropped to ±1 second from peak force.
    
    Args:
        layer_data: Dictionary with time, force, and smoothed_force
        target_layer: Layer number for title
    """
    time = layer_data['time']
    force = layer_data['force']
    position = layer_data['position']
    smoothed_force = layer_data['smoothed_force']
    
    # Find peak force
    peak_force_idx = np.argmax(smoothed_force)
    peak_time = time[peak_force_idx]
    peak_force_value = smoothed_force[peak_force_idx]
    
    print(f"\nPeak force: {peak_force_value:.4f} N at time {peak_time:.3f} s (index {peak_force_idx})")
    
    # Find propagation end using new method
    prop_end_idx, second_deriv_peak_idx = find_propagation_end_new_method(time, position, smoothed_force, peak_force_idx)
    prop_end_time = time[prop_end_idx]
    prop_end_force = smoothed_force[prop_end_idx]
    second_deriv_peak_time = time[second_deriv_peak_idx]
    
    print(f"Propagation end: {prop_end_force:.4f} N at time {prop_end_time:.3f} s (index {prop_end_idx})")
    
    # Calculate derivatives
    first_deriv, second_deriv = calculate_derivatives(time, smoothed_force)
    
    second_deriv_peak_value = second_deriv[second_deriv_peak_idx]
    
    # Adjust time to start from 0
    time_relative = time - time[0]
    peak_time_relative = peak_time - time[0]
    prop_end_time_relative = prop_end_time - time[0]
    second_deriv_peak_time_relative = second_deriv_peak_time - time[0]
    
    # Crop data to ±1 second from peak
    crop_start_time = peak_time_relative - 1.0
    crop_end_time = peak_time_relative + 1.0
    
    crop_mask = (time_relative >= crop_start_time) & (time_relative <= crop_end_time)
    
    time_cropped = time_relative[crop_mask]
    force_cropped = force[crop_mask]
    smoothed_cropped = smoothed_force[crop_mask]
    first_deriv_cropped = first_deriv[crop_mask]
    second_deriv_cropped = second_deriv[crop_mask]
    
    # Create figure with 3 subplots
    fig, axes = plt.subplots(3, 1, figsize=(12, 10))
    fig.suptitle(f'Layer {target_layer} - Baseline Detection Analysis (±1s from peak)', fontsize=14, fontweight='bold')
    
    # Panel 1: Raw and Smoothed Force
    ax1 = axes[0]
    ax1.plot(time_cropped, force_cropped, 'lightgray', alpha=0.5, linewidth=0.5, label='Raw Force')
    ax1.plot(time_cropped, smoothed_cropped, 'b-', linewidth=2, label='Smoothed Force')
    ax1.axhline(y=0, color='k', linestyle='--', alpha=0.3)
    
    # Mark peak force, second deriv peak, and propagation end
    ax1.axvline(x=peak_time_relative, color='orange', linestyle='--', linewidth=2, alpha=0.7, label='Peak Force')
    ax1.axvline(x=second_deriv_peak_time_relative, color='purple', linestyle=':', linewidth=2, alpha=0.7, label='2nd Deriv Peak')
    ax1.axvline(x=prop_end_time_relative, color='red', linestyle='--', linewidth=2, alpha=0.7, label='Propagation End')
    ax1.plot(peak_time_relative, peak_force_value, 'o', color='orange', markersize=10, markeredgecolor='black', markeredgewidth=1.5)
    ax1.plot(prop_end_time_relative, prop_end_force, 's', color='red', markersize=10, markeredgecolor='black', markeredgewidth=1.5)
    
    ax1.set_ylabel('Force (N)', fontsize=11, fontweight='bold')
    ax1.set_title('Force Data', fontsize=11)
    ax1.legend(loc='upper right', fontsize=9)
    ax1.grid(True, alpha=0.3)
    
    # Panel 2: First Derivative
    ax2 = axes[1]
    ax2.plot(time_cropped, first_deriv_cropped, 'g-', linewidth=1.5, label='First Derivative (dF/dt)')
    ax2.axhline(y=0, color='k', linestyle='--', alpha=0.3)
    
    # Mark peak force, second deriv peak, and propagation end
    ax2.axvline(x=peak_time_relative, color='orange', linestyle='--', linewidth=2, alpha=0.7, label='Peak Force')
    ax2.axvline(x=second_deriv_peak_time_relative, color='purple', linestyle=':', linewidth=2, alpha=0.7, label='2nd Deriv Peak')
    ax2.axvline(x=prop_end_time_relative, color='red', linestyle='--', linewidth=2, alpha=0.7, label='Propagation End')
    
    ax2.set_ylabel('dF/dt (N/s)', fontsize=11, fontweight='bold')
    ax2.set_title('First Derivative of Smoothed Force', fontsize=11)
    ax2.legend(loc='upper right', fontsize=9)
    ax2.grid(True, alpha=0.3)
    
    # Panel 3: Second Derivative
    ax3 = axes[2]
    ax3.plot(time_cropped, second_deriv_cropped, 'r-', linewidth=1.5, label='Second Derivative (d²F/dt²)')
    ax3.axhline(y=0, color='k', linestyle='--', alpha=0.3)
    
    # Mark peak force, second deriv peak, and propagation end
    ax3.axvline(x=peak_time_relative, color='orange', linestyle='--', linewidth=2, alpha=0.7, label='Peak Force')
    ax3.axvline(x=second_deriv_peak_time_relative, color='purple', linestyle=':', linewidth=2, alpha=0.7, label='2nd Deriv Peak')
    ax3.axvline(x=prop_end_time_relative, color='red', linestyle='--', linewidth=2, alpha=0.7, label='Propagation End (Zero Cross)')
    ax3.plot(second_deriv_peak_time_relative, second_deriv_peak_value, '^', color='purple', markersize=10, markeredgecolor='black', markeredgewidth=1.5)
    
    ax3.set_xlabel('Time (s)', fontsize=11, fontweight='bold')
    ax3.set_ylabel('d²F/dt² (N/s²)', fontsize=11, fontweight='bold')
    ax3.set_title('Second Derivative of Smoothed Force', fontsize=11)
    ax3.legend(loc='upper right', fontsize=9)
    ax3.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save plot
    output_path = Path(__file__).parent / f'baseline_test_L{target_layer}.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\nPlot saved to: {output_path}")
    
    plt.show()


def main():
    """
    Main function to test baseline detection for layer 111.
    """
    # Configuration
    master_folder = r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\V17Tests"
    working_folder = "2p5PEO_1mm_Ramped_BPAGDA_Old"
    target_layer = 111
    
    print("="*80)
    print("BASELINE DETECTION TEST")
    print("="*80)
    print(f"Target layer: {target_layer}")
    print(f"Working folder: {working_folder}\n")
    
    # Find autolog file containing layer 111
    search_path = Path(master_folder) / working_folder
    autolog_file = find_autolog_with_layer(search_path, target_layer)
    
    if autolog_file is None:
        print(f"ERROR: Could not find autolog file containing layer {target_layer}")
        return 1
    
    print(f"Found autolog file: {autolog_file.name}\n")
    
    # Extract layer data
    try:
        layer_data = extract_layer_data(autolog_file, target_layer)
        print(f"Extracted {len(layer_data['time'])} data points for layer {target_layer}\n")
    except Exception as e:
        print(f"ERROR extracting layer data: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Plot force and derivatives
    try:
        plot_force_and_derivatives(layer_data, target_layer)
        print("\n[OK] Baseline test completed successfully!")
    except Exception as e:
        print(f"ERROR creating plot: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
