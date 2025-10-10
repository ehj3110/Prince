"""
Debug Derivative Plotter
========================

A dedicated debugging tool to visualize the force data, first derivative, and
second derivative for a single layer. This helps in understanding and verifying
the propagation end point detection algorithm.

Author: Cheng Sun Lab Team
Date: September 22, 2025
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import find_peaks, savgol_filter
from pathlib import Path
import argparse
import sys

# Add the parent directory to the path to allow sibling imports
sys.path.append(str(Path(__file__).resolve().parent.parent))

from adhesion_metrics_calculator import AdhesionMetricsCalculator
from RawData_Processor import RawDataProcessor # Import the main processor

def plot_layer_derivatives(csv_filepath: str, target_layer_num: int):
    """
    Analyzes a specific layer from a CSV file and plots its derivatives.

    Args:
        csv_filepath (str): Path to the autolog CSV file.
        target_layer_num (int): The layer number to analyze (e.g., 48, 49, 50).
    """
    # --- 1. Load and Segment Data ---
    try:
        df = pd.read_csv(csv_filepath)
        df.rename(columns={
            'Elapsed Time (s)': 'Time',
            'Position (mm)': 'Position',
            'Force (N)': 'Force'
        }, inplace=True)
    except FileNotFoundError:
        print(f"Error: File not found at {csv_filepath}")
        return

    # Use simple peak detection to find layer segments
    force_data_full = df['Force'].values
    smoothed_force_full = savgol_filter(force_data_full, 11, 2)
    peaks, _ = find_peaks(smoothed_force_full, height=0.01, distance=150, prominence=0.005)

    # Use an instance of RawDataProcessor to get layer numbers and boundaries
    temp_processor = RawDataProcessor()
    layer_numbers = temp_processor._extract_layer_numbers(csv_filepath)
    boundaries = temp_processor._find_layer_boundaries(peaks, df['Position'].values, df['Time'].values, layer_numbers)
    
    # The user provides a 1-based index (1, 2, 3...). Convert it to a 0-based index.
    target_layer_index = target_layer_num - 1

    # Validate the user's input against the number of detected layers.
    if not (0 <= target_layer_index < len(peaks)):
        print(f"Error: Invalid layer index '{target_layer_num}'. Please provide a number between 1 and {len(peaks)}.")
        return

    # The user might also provide an actual layer number. Check for that as a fallback.
    if target_layer_num in layer_numbers:
        target_layer_index = layer_numbers.index(target_layer_num)

    if target_layer_index >= len(boundaries):
        print(f"Error: Could not determine boundaries for layer {target_layer_num}.")
        return

    # Isolate the data for the target layer using the correct boundaries
    start_idx, end_idx = boundaries[target_layer_index]
    actual_layer_number = layer_numbers[target_layer_index]

    layer_df = df.iloc[start_idx:end_idx].copy()
    layer_df['Time'] = layer_df['Time'] - layer_df['Time'].iloc[0] # Reset time for segment

    time_data = layer_df['Time'].values
    force_data = layer_df['Force'].values
    pos_data = layer_df['Position'].values

    print(f"Analyzing Layer {actual_layer_number} from index {start_idx} to {end_idx}")

    # --- 2. Perform Calculations (mirroring AdhesionMetricsCalculator) ---
    # Increase smoothing sigma for more aggressive smoothing, as requested.
    calculator = AdhesionMetricsCalculator(smoothing_sigma=1.0)
    smoothed_force = calculator._apply_smoothing(force_data)
    
    # Find peak within the layer segment
    peak_idx, peak_force = calculator._find_peak_force(smoothed_force)
    peak_time = time_data[peak_idx]

    # Find propagation end point (the method we are debugging)
    prop_end_idx = calculator._find_propagation_end(
        smoothed_force, peak_idx, pos_data, motion_end_idx=len(smoothed_force)-1
    )
    prop_end_time = time_data[prop_end_idx]

    # Calculate baseline from this point
    baseline = calculator._calculate_baseline(smoothed_force, prop_end_idx)

    # --- 3. Calculate Derivatives for Plotting ---
    # Region of interest for derivatives (from peak to end)
    region_of_interest = smoothed_force[peak_idx:len(smoothed_force)]
    second_derivative = np.gradient(np.gradient(region_of_interest))
    first_derivative = np.gradient(region_of_interest)

    # Find the max of the second derivative within the region
    max_2nd_deriv_relative_idx = np.argmax(second_derivative)
    max_2nd_deriv_global_idx = peak_idx + max_2nd_deriv_relative_idx
    max_2nd_deriv_time = time_data[max_2nd_deriv_global_idx]

    # --- 4. Create the 3-Panel Plot ---
    fig, axes = plt.subplots(3, 1, figsize=(15, 12), sharex=True)
    fig.suptitle(f'Derivative Debugging for Layer {actual_layer_number}', fontsize=16, fontweight='bold')

    # -- Panel 1: Force Data --
    ax1 = axes[0]
    ax1.plot(time_data, force_data, 'k-', alpha=0.3, label='Raw Force')
    ax1.plot(time_data, smoothed_force, 'b-', linewidth=2, label='Smoothed Force')
    ax1.axvline(peak_time, color='r', linestyle='--', label=f'Peak Force ({peak_force:.3f} N)')
    ax1.axvline(prop_end_time, color='g', linestyle='--', label=f'Detected Prop End ({prop_end_time:.2f} s)')
    ax1.axhline(baseline, color='purple', linestyle=':', label=f'Calculated Baseline ({baseline:.3f} N)')
    ax1.plot(peak_time, peak_force, 'ro')
    ax1.plot(prop_end_time, smoothed_force[prop_end_idx], 'go')
    ax1.set_title('Force Profile')
    ax1.set_ylabel('Force (N)')
    ax1.legend()
    ax1.grid(True, alpha=0.5)

    # -- Panel 2: First Derivative --
    ax2 = axes[1]
    # We plot the derivative for the whole segment to see the context
    full_first_deriv = np.gradient(smoothed_force)
    ax2.plot(time_data, full_first_deriv, 'm-', label='dF/dt')
    ax2.axvline(peak_time, color='r', linestyle='--')
    ax2.axvline(prop_end_time, color='g', linestyle='--')
    ax2.axhline(0, color='k', linestyle=':', alpha=0.5)
    ax2.set_title('First Derivative (dF/dt)')
    ax2.set_ylabel('Rate of Change (N/pt)')
    ax2.legend()
    ax2.grid(True, alpha=0.5)

    # -- Panel 3: Second Derivative --
    ax3 = axes[2]
    # We plot the derivative for the whole segment to see the context
    full_second_deriv = np.gradient(full_first_deriv)
    ax3.plot(time_data, full_second_deriv, 'c-', label='d²F/dt²')
    ax3.axvline(peak_time, color='r', linestyle='--')
    ax3.axvline(prop_end_time, color='g', linestyle='--')
    # Mark the point the algorithm CHOSE as the max
    ax3.axvline(max_2nd_deriv_time, color='orange', linestyle='-.', linewidth=2, label=f'Max d²F/dt² ({max_2nd_deriv_time:.2f} s)')
    ax3.plot(max_2nd_deriv_time, full_second_deriv[max_2nd_deriv_global_idx], 'o', color='orange', markersize=8)
    ax3.axhline(0, color='k', linestyle=':', alpha=0.5)
    ax3.set_title('Second Derivative (d²F/dt²)')
    ax3.set_xlabel('Time (s)')
    ax3.set_ylabel('Curvature (N/pt²)')
    ax3.legend()
    ax3.grid(True, alpha=0.5)

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    
    # Save the plot
    save_filename = f"debug_derivatives_layer_{actual_layer_number}.png"
    plt.savefig(save_filename, dpi=150)
    print(f"\nPlot saved to: {save_filename}")

    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Debug the adhesion metrics calculator by plotting derivatives for a specific layer."
    )
    parser.add_argument(
        "csv_file",
        type=str,
        help="Path to the 'autolog_...csv' file to analyze."
    )
    parser.add_argument(
        "layer",
        type=int,
        help="The layer to analyze, as a 1-based index (e.g., 1 for the first layer, 2 for the second)."
    )
    args = parser.parse_args()

    # Construct the full path if a relative path is given
    filepath = Path(args.csv_file)
    
    # --- Robust Path Checking ---
    # If the file is not found at the given path, check if it exists inside the script's directory.
    if not filepath.exists():
        script_dir = Path(__file__).parent
        alternative_path = script_dir / filepath.name
        if alternative_path.exists():
            filepath = alternative_path

    if not filepath.exists():
        print(f"FATAL: Could not find the file '{args.csv_file}'")
    else:
        plot_layer_derivatives(str(filepath), args.layer)