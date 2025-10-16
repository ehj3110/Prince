"""
Diagnostic Script: Visualize Propagation End Detection
========================================================

This script visualizes how the current propagation end detection algorithm works.
It shows:
1. Force vs time curve
2. 2nd derivative of force
3. Detected peaks in 2nd derivative
4. Current propagation end location
5. Lifting point location

Usage:
    python diagnose_propagation_end.py <path_to_autolog_csv>
    
Example:
    python diagnose_propagation_end.py "post-processing/autolog_L48-L50.csv"
"""

import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# Add support modules to path
sys.path.insert(0, str(Path(__file__).parent / 'support_modules'))
from adhesion_metrics_calculator import AdhesionMetricsCalculator

def visualize_propagation_detection(csv_file, layer_num=0):
    """
    Visualize the propagation end detection for a specific layer.
    
    Args:
        csv_file: Path to autolog CSV file
        layer_num: Which layer to visualize (0 = first layer)
    """
    # Load data
    df = pd.read_csv(csv_file)
    times = df['Elapsed Time (s)'].to_numpy()
    forces = df['Force (N)'].to_numpy()
    positions = df['Position (mm)'].to_numpy()
    
    # Initialize calculator
    calculator = AdhesionMetricsCalculator()
    
    # Get smoothed force
    smoothed_force = calculator._apply_smoothing(forces)
    
    # Find peak (simplified - just find max force)
    peak_idx = np.argmax(smoothed_force)
    
    # Find motion end (simplified - use end of data)
    motion_end_idx = len(smoothed_force) - 1
    
    # === REPLICATE THE ALGORITHM ===
    
    # 1. Define search region
    search_start_abs = peak_idx
    search_end_abs = motion_end_idx
    
    # 2. Find lifting point (maximum travel)
    travel_positions = positions[search_start_abs:search_end_abs]
    min_pos_relative_idx = np.argmin(travel_positions)
    lifting_point_idx = search_start_abs + min_pos_relative_idx
    
    # 3. Define reverse search start (90% of way to lifting point)
    reverse_search_start_idx = int(peak_idx + 0.9 * (lifting_point_idx - peak_idx))
    
    # 4. Calculate 2nd derivative
    region_of_interest = smoothed_force[peak_idx:lifting_point_idx+1]
    second_derivative = np.gradient(np.gradient(region_of_interest))
    
    # 5. Find peaks in 2nd derivative
    peaks_indices = []
    for i in range(1, len(second_derivative) - 1):
        if second_derivative[i] > second_derivative[i-1] and second_derivative[i] > second_derivative[i+1]:
            peaks_indices.append(i)
    
    # 6. Filter for peaks before 90% point
    reverse_search_start_relative = reverse_search_start_idx - peak_idx
    valid_peaks = [p for p in peaks_indices if p <= reverse_search_start_relative]
    
    # 7. Take LAST valid peak
    if valid_peaks:
        last_peak_relative_idx = valid_peaks[-1]
        propagation_end_idx = peak_idx + last_peak_relative_idx
        
        # Also calculate what FIRST peak would give
        first_peak_relative_idx = valid_peaks[0]
        alternative_prop_end_idx = peak_idx + first_peak_relative_idx
    else:
        propagation_end_idx = lifting_point_idx
        alternative_prop_end_idx = lifting_point_idx
    
    # === CREATE VISUALIZATION ===
    
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
    
    # Plot 1: Force vs Time
    ax1.plot(times, forces, 'lightgray', alpha=0.5, label='Raw Force', linewidth=1)
    ax1.plot(times, smoothed_force, 'b-', label='Smoothed Force', linewidth=2)
    ax1.axvline(times[peak_idx], color='red', linestyle='--', alpha=0.7, label='Peak Force')
    ax1.axvline(times[lifting_point_idx], color='orange', linestyle='--', alpha=0.7, label='Lifting Point')
    ax1.axvline(times[reverse_search_start_idx], color='purple', linestyle=':', alpha=0.5, label='90% Search Start')
    ax1.axvline(times[propagation_end_idx], color='green', linestyle='-', linewidth=2, label='CURRENT: Propagation End (LAST peak)')
    if propagation_end_idx != alternative_prop_end_idx:
        ax1.axvline(times[alternative_prop_end_idx], color='cyan', linestyle='--', linewidth=2, label='ALTERNATIVE: First peak')
    ax1.set_ylabel('Force (N)', fontsize=12)
    ax1.set_title('Force vs Time - Propagation End Detection', fontsize=14, fontweight='bold')
    ax1.legend(loc='upper right', fontsize=9)
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Position vs Time
    ax2.plot(times, positions, 'k-', linewidth=1.5)
    ax2.axvline(times[peak_idx], color='red', linestyle='--', alpha=0.7)
    ax2.axvline(times[lifting_point_idx], color='orange', linestyle='--', alpha=0.7)
    ax2.axvline(times[propagation_end_idx], color='green', linestyle='-', linewidth=2)
    if propagation_end_idx != alternative_prop_end_idx:
        ax2.axvline(times[alternative_prop_end_idx], color='cyan', linestyle='--', linewidth=2)
    ax2.set_ylabel('Position (mm)', fontsize=12)
    ax2.set_title('Stage Position', fontsize=12)
    ax2.grid(True, alpha=0.3)
    ax2.invert_yaxis()  # Invert so down is positive
    
    # Plot 3: 2nd Derivative with peaks
    time_region = times[peak_idx:lifting_point_idx+1]
    ax3.plot(time_region, second_derivative, 'b-', linewidth=1.5, label='2nd Derivative')
    ax3.axhline(0, color='k', linestyle='-', alpha=0.3, linewidth=0.5)
    
    # Mark all peaks in 2nd derivative
    for peak_rel_idx in peaks_indices:
        time_val = times[peak_idx + peak_rel_idx]
        y_val = second_derivative[peak_rel_idx]
        if peak_rel_idx in valid_peaks:
            ax3.plot(time_val, y_val, 'ro', markersize=8, label='Valid Peak' if peak_rel_idx == valid_peaks[0] else '')
        else:
            ax3.plot(time_val, y_val, 'ko', markersize=6, alpha=0.3, label='Excluded Peak' if peak_rel_idx == peaks_indices[0] else '')
    
    # Highlight the selected peaks
    if valid_peaks:
        # Current method: LAST peak
        last_peak_time = times[peak_idx + valid_peaks[-1]]
        last_peak_y = second_derivative[valid_peaks[-1]]
        ax3.plot(last_peak_time, last_peak_y, 'go', markersize=12, markeredgewidth=2, markeredgecolor='darkgreen', 
                 label='Selected (LAST peak)', zorder=10)
        
        # Alternative: FIRST peak
        if len(valid_peaks) > 1:
            first_peak_time = times[peak_idx + valid_peaks[0]]
            first_peak_y = second_derivative[valid_peaks[0]]
            ax3.plot(first_peak_time, first_peak_y, 'co', markersize=12, markeredgewidth=2, markeredgecolor='darkcyan',
                     label='Alternative (FIRST peak)', zorder=10)
    
    ax3.axvline(times[reverse_search_start_idx], color='purple', linestyle=':', alpha=0.5, label='90% Cutoff')
    ax3.set_xlabel('Time (s)', fontsize=12)
    ax3.set_ylabel('2nd Derivative', fontsize=12)
    ax3.set_title('Second Derivative of Force (Inflection Point Detection)', fontsize=12)
    ax3.legend(loc='upper right', fontsize=9)
    ax3.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Print diagnostic information
    print("\n" + "="*70)
    print("PROPAGATION END DETECTION DIAGNOSTIC")
    print("="*70)
    print(f"\nFile: {csv_file}")
    print(f"\nKey Indices:")
    print(f"  Peak Force:           idx={peak_idx:5d}  time={times[peak_idx]:.3f}s  force={smoothed_force[peak_idx]:.4f}N")
    print(f"  Lifting Point:        idx={lifting_point_idx:5d}  time={times[lifting_point_idx]:.3f}s  pos={positions[lifting_point_idx]:.4f}mm")
    print(f"  90% Search Start:     idx={reverse_search_start_idx:5d}  time={times[reverse_search_start_idx]:.3f}s")
    print(f"\n2nd Derivative Analysis:")
    print(f"  Total peaks found:    {len(peaks_indices)}")
    print(f"  Valid peaks (<90%):   {len(valid_peaks)}")
    
    if valid_peaks:
        print(f"\nCURRENT METHOD (LAST peak):")
        print(f"  Propagation End:      idx={propagation_end_idx:5d}  time={times[propagation_end_idx]:.3f}s  force={smoothed_force[propagation_end_idx]:.4f}N")
        print(f"  Distance from peak:   {times[propagation_end_idx] - times[peak_idx]:.3f}s")
        
        if len(valid_peaks) > 1:
            print(f"\nALTERNATIVE METHOD (FIRST peak):")
            print(f"  Propagation End:      idx={alternative_prop_end_idx:5d}  time={times[alternative_prop_end_idx]:.3f}s  force={smoothed_force[alternative_prop_end_idx]:.4f}N")
            print(f"  Distance from peak:   {times[alternative_prop_end_idx] - times[peak_idx]:.3f}s")
            print(f"\nDIFFERENCE:")
            print(f"  Time difference:      {times[propagation_end_idx] - times[alternative_prop_end_idx]:.3f}s")
            print(f"  Force difference:     {smoothed_force[propagation_end_idx] - smoothed_force[alternative_prop_end_idx]:.4f}N")
    else:
        print(f"\nNo valid peaks found - using lifting point as fallback")
    
    print("="*70)
    
    # Save plot
    output_file = Path(csv_file).parent / f"propagation_diagnostic_{Path(csv_file).stem}.png"
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\nPlot saved to: {output_file}")
    
    plt.show()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nERROR: Please provide a CSV file path")
        print("\nExample files to try:")
        print("  - post-processing/autolog_L48-L50.csv")
        print("  - post-processing/autolog_L347-L349.csv")
        print("  - post-processing/autolog_L365-L370.csv")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    
    if not Path(csv_file).exists():
        print(f"ERROR: File not found: {csv_file}")
        sys.exit(1)
    
    visualize_propagation_detection(csv_file)
