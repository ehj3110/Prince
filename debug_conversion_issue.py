"""
Debug the time conversion issue in hybrid plotter
"""
import pandas as pd
import numpy as np
from adhesion_metrics_calculator import AdhesionMetricsCalculator

# Load data
df = pd.read_csv("autolog_L198-L200.csv")
if 'Elapsed Time (s)' in df.columns:
    df = df.rename(columns={'Elapsed Time (s)': 'Time', 'Position (mm)': 'Position', 'Force (N)': 'Force'})

print("DEBUGGING TIME CONVERSION IN HYBRID PLOTTER")
print("="*50)

# Simulate exactly what hybrid plotter does
times = df['Time'].values
positions = df['Position'].values
forces = df['Force'].values

# Layer 198 boundaries from hybrid plotter
start_idx = 0
end_idx = 619

print(f"Layer 198 boundaries: {start_idx} to {end_idx}")
print(f"Global time at start: {times[start_idx]:.3f}s")
print(f"Global time at end: {times[end_idx]:.3f}s")

# Step 1: Extract segment with time reset (like hybrid plotter)
segment_time = times[start_idx:end_idx+1] - times[start_idx]  # Reset to start at 0
segment_position = positions[start_idx:end_idx+1]
segment_force = forces[start_idx:end_idx+1]

print(f"Segment time range: {segment_time[0]:.3f} to {segment_time[-1]:.3f}s")

# Step 2: Calculate with normal calculator
calc = AdhesionMetricsCalculator()
metrics = calc.calculate_from_arrays(segment_time, segment_position, segment_force, layer_number=198)

print(f"\nCalculator result (relative time):")
print(f"  Propagation End Time: {metrics['propagation_end_time']:.3f}s")

# Step 3: Simulate hybrid plotter's conversion back to global time
print(f"\nHybrid plotter conversion process:")

# This is what the current hybrid plotter does:
prop_end_global_time = times[start_idx] + metrics['propagation_end_time']
print(f"  Step 1 - Add layer start time: {times[start_idx]:.3f} + {metrics['propagation_end_time']:.3f} = {prop_end_global_time:.3f}s")

# Find closest index in FULL time array
prop_end_idx = np.argmin(np.abs(times - prop_end_global_time))
final_plot_time = times[prop_end_idx]

print(f"  Step 2 - Find closest global index: {prop_end_idx}")
print(f"  Step 3 - Final plot time: {final_plot_time:.3f}s")

print(f"\nPROBLEM IDENTIFIED:")
print(f"  Calculator gives: {metrics['propagation_end_time']:.3f}s (relative)")
print(f"  Should convert to: {prop_end_global_time:.3f}s (global)")
print(f"  But plot shows: {final_plot_time:.3f}s")
print(f"  Conversion error: {abs(final_plot_time - prop_end_global_time):.3f}s")

# Check nearby indices to see what's happening
print(f"\nNearby time values around index {prop_end_idx}:")
for i in range(max(0, prop_end_idx-3), min(len(times), prop_end_idx+4)):
    marker = " <-- SELECTED" if i == prop_end_idx else ""
    print(f"  Index {i}: {times[i]:.3f}s{marker}")

# Check if this explains the 11.8s you're seeing
print(f"\nDoes {final_plot_time:.3f}s match what you see on the plot (~11.8s)?")
if abs(final_plot_time - 11.8) < 0.05:
    print("YES - This explains the discrepancy!")
