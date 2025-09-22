"""
Replicate EXACTLY what the hybrid plotter does
"""
import pandas as pd
import numpy as np
from scipy.signal import savgol_filter
from adhesion_metrics_calculator import AdhesionMetricsCalculator

# Load data
df = pd.read_csv("autolog_L198-L200.csv")
if 'Elapsed Time (s)' in df.columns:
    df = df.rename(columns={'Elapsed Time (s)': 'Time', 'Position (mm)': 'Position', 'Force (N)': 'Force'})

print("REPLICATING EXACT HYBRID PLOTTER PROCESS")
print("="*50)

times = df['Time'].values
positions = df['Position'].values
forces = df['Force'].values

# From hybrid plotter output, we know:
start_idx = 0
end_idx = 619

print(f"Layer 198 boundaries: indices {start_idx}-{end_idx}")
print(f"Boundary times: {times[start_idx]:.3f} to {times[end_idx]:.3f} seconds")

# Exact same extraction as hybrid plotter
segment_time = times[start_idx:end_idx+1] - times[start_idx]  # Reset to start at 0
segment_position = positions[start_idx:end_idx+1]
segment_force = forces[start_idx:end_idx+1]

print(f"Segment data: {len(segment_time)} points")
print(f"Segment time range: {segment_time[0]:.3f} to {segment_time[-1]:.3f} seconds")

# Call calculator exactly like hybrid plotter
calc = AdhesionMetricsCalculator()
metrics = calc.calculate_from_arrays(segment_time, segment_position, segment_force, layer_number=198)

print(f"\nResult from replicating hybrid plotter:")
print(f"Peak Time: {metrics['peak_force_time']:.3f} s")
print(f"Prop End Time: {metrics['propagation_end_time']:.3f} s")

# Compare with our direct test
print(f"\nExpected from our direct test:")
print(f"Peak Time: 11.596 s")
print(f"Prop End Time: 11.719 s")

# Check the differences
print(f"\nDifferences:")
print(f"Peak Time Diff: {abs(metrics['peak_force_time'] - 11.596):.3f} s")
print(f"Prop End Time Diff: {abs(metrics['propagation_end_time'] - 11.719):.3f} s")

# Let's also check the data integrity
print(f"\nData integrity check:")
print(f"Length check: segment={len(segment_time)}, expected={end_idx - start_idx + 1}")
print(f"Time continuity: segment[0]={segment_time[0]:.3f}, segment[-1]={segment_time[-1]:.3f}")

# Maybe there's an off-by-one error in the boundaries?
print(f"\nBoundary check:")
print(f"start_idx={start_idx}, end_idx={end_idx}")
print(f"Actual indices used: {start_idx} to {end_idx+1} (exclusive), length={end_idx+1-start_idx}")

# Check if this matches what we tested before
original_layer_times = times[0:619]
print(f"Original layer length: {len(original_layer_times)}")
print(f"Match segment length: {len(segment_time) == len(original_layer_times)}")
