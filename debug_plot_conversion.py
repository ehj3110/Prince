"""
Debug why 11.719s calculated time becomes ~11.8s on the plot
"""
import pandas as pd
import numpy as np
from adhesion_metrics_calculator import AdhesionMetricsCalculator

# Load data
df = pd.read_csv("autolog_L198-L200.csv")
if 'Elapsed Time (s)' in df.columns:
    df = df.rename(columns={'Elapsed Time (s)': 'Time', 'Position (mm)': 'Position', 'Force (N)': 'Force'})

print("DEBUGGING THE 11.719s → 11.8s CONVERSION ERROR")
print("="*50)

# Simulate exact hybrid plotter process
times = df['Time'].values
positions = df['Position'].values
forces = df['Force'].values

# Layer 198 boundaries from hybrid plotter
start_idx = 0
end_idx = 619

print(f"Layer boundaries: {start_idx} to {end_idx}")
print(f"Start time: {times[start_idx]:.3f}s")

# Extract segment with reset time (like hybrid plotter)
segment_time = times[start_idx:end_idx+1] - times[start_idx]  # Reset to start at 0
segment_position = positions[start_idx:end_idx+1]
segment_force = forces[start_idx:end_idx+1]

print(f"Segment length: {len(segment_time)} points")

# Calculate with correct light smoothing settings
calc = AdhesionMetricsCalculator(
    smoothing_window=3,
    smoothing_polyorder=1,
    baseline_threshold_factor=0.002,
    min_peak_height=0.01,
    min_peak_distance=50
)
metrics = calc.calculate_from_arrays(segment_time, segment_position, segment_force, layer_number=198)

print(f"\nCalculator result:")
print(f"  Propagation End Time (relative): {metrics['propagation_end_time']:.3f}s")

# Now trace the hybrid plotter conversion step by step
print(f"\nHybrid plotter conversion:")

# Step 1: Convert to global time
prop_end_global_time = times[start_idx] + metrics['propagation_end_time']
print(f"  Step 1 - Global time: {times[start_idx]:.3f} + {metrics['propagation_end_time']:.3f} = {prop_end_global_time:.3f}s")

# Step 2: Find closest index (current hybrid plotter method)
prop_end_idx = np.argmin(np.abs(times - prop_end_global_time))
final_plot_time = times[prop_end_idx]

print(f"  Step 2 - Find closest index in FULL time array:")
print(f"    Searching for: {prop_end_global_time:.3f}s")
print(f"    Found index: {prop_end_idx}")
print(f"    Final plot time: {final_plot_time:.3f}s")

# Show the problem - let's see what's near that index
print(f"\nNearby times around index {prop_end_idx}:")
for i in range(max(0, prop_end_idx-3), min(len(times), prop_end_idx+4)):
    marker = " <-- SELECTED" if i == prop_end_idx else ""
    diff = abs(times[i] - prop_end_global_time)
    print(f"    Index {i}: {times[i]:.3f}s (diff: {diff:.3f}s){marker}")

# Check if we should be searching in the layer segment instead
print(f"\nAlternative: Search within layer segment only:")
layer_times = times[start_idx:end_idx+1]
local_prop_end_idx = np.argmin(np.abs(layer_times - prop_end_global_time))
global_prop_end_idx = start_idx + local_prop_end_idx
alternative_plot_time = times[global_prop_end_idx]

print(f"  Local index in segment: {local_prop_end_idx}")
print(f"  Global index: {global_prop_end_idx}")
print(f"  Alternative plot time: {alternative_plot_time:.3f}s")

print(f"\nCOMPARISON:")
print(f"  Target time: {prop_end_global_time:.3f}s")
print(f"  Current method gives: {final_plot_time:.3f}s")
print(f"  Alternative method gives: {alternative_plot_time:.3f}s")
print(f"  You see on plot: ~11.8s")

# Which is closer to 11.8?
print(f"\nWhich matches your observation of ~11.8s?")
print(f"  Current ({final_plot_time:.3f}s): {abs(final_plot_time - 11.8):.3f}s difference")
print(f"  Alternative ({alternative_plot_time:.3f}s): {abs(alternative_plot_time - 11.8):.3f}s difference")
