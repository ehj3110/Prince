#!/usr/bin/env python3
"""
Comprehensive diagnostic plot: Force, 1st derivative, and 2nd derivative for all layers
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks

# Load the data
df = pd.read_csv("autolog_L198-L200.csv")
df = df.rename(columns={'Elapsed Time (s)': 'Time', 'Position (mm)': 'Position', 'Force (N)': 'Force'})

time_data = df['Time'].values
raw_force_data = df['Force'].values

# Apply smoothing for better visual presentation (matching final analysis parameters)
from scipy.signal import savgol_filter
force_data = savgol_filter(raw_force_data, window_length=3, polyorder=1)
print("Using lightly smoothed force data for analysis (same as final visualization)")

# Extract layer numbers from filename
import re
filename = "autolog_L198-L200.csv"
layer_match = re.search(r'L(\d+)-L(\d+)', filename)
if layer_match:
    start_layer = int(layer_match.group(1))
    layer_numbers = [start_layer, start_layer + 1, start_layer + 2]
else:
    layer_numbers = [198, 199, 200]

# Find peaks using same method as main script
peaks, _ = find_peaks(force_data, height=0.08, distance=150, prominence=0.05)

print("=== COMPREHENSIVE DERIVATIVE DIAGNOSTIC ===")
print(f"Found {len(peaks)} peaks at indices: {peaks}")
for i, peak_idx in enumerate(peaks):
    print(f"  Layer {layer_numbers[i]}: Peak at {time_data[peak_idx]:.3f}s, Force={force_data[peak_idx]:.6f}N")

# Create 3x3 subplot grid
fig, axes = plt.subplots(3, 3, figsize=(18, 15))
fig.suptitle('Force Analysis: Raw Force, 1st Derivative, 2nd Derivative', fontsize=16, fontweight='bold')

# Colors for each layer
colors = ['red', 'blue', 'green']

for i, peak_idx in enumerate(peaks):
    if i >= 3:
        break
    
    layer_num = layer_numbers[i]
    color = colors[i]
    
    # Define window around peak (±1 second for focused view)
    window_duration = 1.0  # seconds before and after peak
    sampling_rate = 1.0 / np.mean(np.diff(time_data))  # Calculate actual sampling rate
    window_points = int(window_duration * sampling_rate)
    
    start_idx = max(0, peak_idx - window_points)
    end_idx = min(len(force_data), peak_idx + window_points)
    
    # Extract windowed data
    window_time = time_data[start_idx:end_idx]
    window_force = force_data[start_idx:end_idx]
    
    # Calculate derivatives
    first_derivative = np.diff(window_force)  # dF/dt
    second_derivative = np.diff(first_derivative)  # d²F/dt²
    
    # Time arrays for derivatives (shorter due to diff operations)
    first_deriv_time = window_time[1:]  # One less point
    second_deriv_time = window_time[2:]  # Two less points
    
    # Peak time for reference lines
    peak_time = time_data[peak_idx]
    
    # Find critical points for additional vertical lines
    # 1. Minimum of first derivative (steepest descent)
    min_first_deriv_idx = np.argmin(first_derivative)
    min_first_deriv_time = first_deriv_time[min_first_deriv_idx]
    min_first_deriv_value = first_derivative[min_first_deriv_idx]
    
    # 2. Maximum of second derivative (greatest acceleration)
    max_second_deriv_idx = np.argmax(second_derivative)
    max_second_deriv_time = second_deriv_time[max_second_deriv_idx]
    max_second_deriv_value = second_derivative[max_second_deriv_idx]
    
    # Row 1: Raw Force
    ax_force = axes[i, 0]
    ax_force.plot(window_time, window_force, color=color, linewidth=2, label=f'Layer {layer_num} Force')
    ax_force.axvline(peak_time, color='black', linestyle='--', alpha=0.7, label='Peak')
    ax_force.axvline(min_first_deriv_time, color='purple', linestyle=':', alpha=0.7, label='Min dF/dt')
    ax_force.axvline(max_second_deriv_time, color='orange', linestyle='-.', alpha=0.7, label='Max d²F/dt²')
    ax_force.axhline(0, color='gray', linestyle='-', alpha=0.3)
    ax_force.set_title(f'Layer {layer_num} - Raw Force')
    ax_force.set_xlabel('Time (s)')
    ax_force.set_ylabel('Force (N)')
    ax_force.legend()
    ax_force.grid(True, alpha=0.3)
    
    # Add peak annotation
    ax_force.plot(peak_time, force_data[peak_idx], 'o', color='black', markersize=8, zorder=5)
    ax_force.annotate(f'Peak: {force_data[peak_idx]:.3f}N', 
                     xy=(peak_time, force_data[peak_idx]),
                     xytext=(10, 10), textcoords='offset points',
                     bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8),
                     fontsize=9)
    
    # Row 2: First Derivative (dF/dt)
    ax_first = axes[i, 1]
    ax_first.plot(first_deriv_time, first_derivative, color=color, linewidth=2, label=f'dF/dt')
    ax_first.axvline(peak_time, color='black', linestyle='--', alpha=0.7, label='Peak')
    ax_first.axvline(min_first_deriv_time, color='purple', linestyle=':', alpha=0.9, linewidth=2, label='Min dF/dt')
    ax_first.axvline(max_second_deriv_time, color='orange', linestyle='-.', alpha=0.7, label='Max d²F/dt²')
    ax_first.axhline(0, color='gray', linestyle='-', alpha=0.5, label='Zero derivative')
    
    # Add threshold lines for stabilization detection
    ax_first.axhline(0.005, color='red', linestyle=':', alpha=0.5, label='±5mN threshold')
    ax_first.axhline(-0.005, color='red', linestyle=':', alpha=0.5)
    
    # Mark the minimum point
    ax_first.plot(min_first_deriv_time, min_first_deriv_value, 'o', color='purple', markersize=8, zorder=5)
    
    ax_first.set_title(f'Layer {layer_num} - First Derivative (dF/dt)')
    ax_first.set_xlabel('Time (s)')
    ax_first.set_ylabel('dF/dt (N/sample)')
    ax_first.legend()
    ax_first.grid(True, alpha=0.3)
    
    # Row 3: Second Derivative (d²F/dt²)
    ax_second = axes[i, 2]
    ax_second.plot(second_deriv_time, second_derivative, color=color, linewidth=2, label=f'd²F/dt²')
    ax_second.axvline(peak_time, color='black', linestyle='--', alpha=0.7, label='Peak')
    ax_second.axvline(min_first_deriv_time, color='purple', linestyle=':', alpha=0.7, label='Min dF/dt')
    ax_second.axvline(max_second_deriv_time, color='orange', linestyle='-.', alpha=0.9, linewidth=2, label='Max d²F/dt²')
    ax_second.axhline(0, color='gray', linestyle='-', alpha=0.5, label='Zero 2nd derivative')
    
    # Mark the maximum point
    ax_second.plot(max_second_deriv_time, max_second_deriv_value, 'o', color='orange', markersize=8, zorder=5)
    
    ax_second.set_title(f'Layer {layer_num} - Second Derivative (d²F/dt²)')
    ax_second.set_xlabel('Time (s)')
    ax_second.set_ylabel('d²F/dt² (N/sample²)')
    ax_second.legend()
    ax_second.grid(True, alpha=0.3)
    
    # Print some diagnostic info
    print(f"\nLayer {layer_num} Analysis:")
    print(f"  Window: {window_time[0]:.3f}s to {window_time[-1]:.3f}s")
    print(f"  Peak time: {peak_time:.3f}s, Force: {force_data[peak_idx]:.6f}N")
    print(f"  Min 1st derivative: {min_first_deriv_time:.3f}s, Value: {min_first_deriv_value:.6f}")
    print(f"  Max 2nd derivative: {max_second_deriv_time:.3f}s, Value: {max_second_deriv_value:.6f}")
    print(f"  Force range: {window_force.min():.6f}N to {window_force.max():.6f}N")
    print(f"  1st derivative range: {first_derivative.min():.6f} to {first_derivative.max():.6f}")
    print(f"  2nd derivative range: {second_derivative.min():.6f} to {second_derivative.max():.6f}")
    
    # Find where first derivative crosses zero after peak
    peak_relative_idx = peak_idx - start_idx
    if peak_relative_idx < len(first_derivative):
        post_peak_first_deriv = first_derivative[peak_relative_idx:]
        zero_crossings = []
        for j in range(len(post_peak_first_deriv)-1):
            if (post_peak_first_deriv[j] > 0 and post_peak_first_deriv[j+1] <= 0) or \
               (post_peak_first_deriv[j] < 0 and post_peak_first_deriv[j+1] >= 0):
                crossing_time = first_deriv_time[peak_relative_idx + j + 1]
                zero_crossings.append(crossing_time)
        
        print(f"  First derivative zero crossings after peak: {zero_crossings[:3]}")

plt.tight_layout()
plt.subplots_adjust(top=0.93)
plt.savefig('diagnostic_L198-L200_derivatives_SMOOTHED_CORRECTED.png', dpi=150, bbox_inches='tight')
print(f"\nDiagnostic plot saved as: diagnostic_L198-L200_derivatives_SMOOTHED_CORRECTED.png")

print("\n=== ANALYSIS GUIDE ===")
print("Raw Force (Column 1): Shows the actual peeling force vs time")
print("1st Derivative (Column 2): Shows rate of force change - look for:")
print("  - Negative values during force drop after peak")
print("  - Zero crossings where force stabilizes")
print("  - Red lines show ±5mN threshold used for detection")
print("2nd Derivative (Column 3): Shows acceleration of force change - look for:")
print("  - Inflection points where concavity changes")
print("  - Transition from negative to positive (or vice versa)")
print("  - Zero crossings indicate transition points in force behavior")
print("3rd Derivative (Column 4): Shows jerk (rate of acceleration change) - look for:")
print("  - Rapid transitions in force behavior")
print("  - Sharp changes in acceleration patterns")
print("  - Maximum absolute values indicate most dramatic transitions")
print("\nVertical Line Legend:")
print("  Black dashed: Peak force location")
print("  Purple dotted: Minimum 1st derivative (steepest force drop)")
print("  Orange dash-dot: Maximum 2nd derivative (greatest acceleration)")
print("  Brown dash-dot-dot: Maximum |3rd derivative| (greatest jerk)")
