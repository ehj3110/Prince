"""
Compare what happens when we use original vs reset time data
"""
import pandas as pd
import numpy as np
from adhesion_metrics_calculator import AdhesionMetricsCalculator

# Load data
df = pd.read_csv("autolog_L198-L200.csv")
if 'Elapsed Time (s)' in df.columns:
    df = df.rename(columns={'Elapsed Time (s)': 'Time', 'Position (mm)': 'Position', 'Force (N)': 'Force'})

print("COMPARING ORIGINAL vs RESET TIME DATA")
print("="*60)

# Layer 198 setup
start_idx = 0
end_idx = 619
times = df['Time'].values
positions = df['Position'].values  
forces = df['Force'].values

calc = AdhesionMetricsCalculator()

print("TEST 1: Using ORIGINAL time data (like test calculator)")
print("-" * 40)
original_times = times[start_idx:end_idx+1]
original_positions = positions[start_idx:end_idx+1]
original_forces = forces[start_idx:end_idx+1]

print(f"Time range: {original_times[0]:.3f} to {original_times[-1]:.3f} seconds")

result1 = calc.calculate_from_arrays(original_times, original_positions, original_forces, layer_number=198)
print(f"Peak Time: {result1['peak_force_time']:.3f} s")
print(f"Prop End Time: {result1['propagation_end_time']:.3f} s")

print("\nTEST 2: Using RESET time data (like hybrid plotter)")
print("-" * 40)
reset_times = times[start_idx:end_idx+1] - times[start_idx]  # Reset to start at 0
reset_positions = positions[start_idx:end_idx+1]
reset_forces = forces[start_idx:end_idx+1]

print(f"Time range: {reset_times[0]:.3f} to {reset_times[-1]:.3f} seconds")

result2 = calc.calculate_from_arrays(reset_times, reset_positions, reset_forces, layer_number=198)
print(f"Peak Time: {result2['peak_force_time']:.3f} s")
print(f"Prop End Time: {result2['propagation_end_time']:.3f} s")

print(f"\nDIFFERENCES:")
print(f"Peak Time Diff: {abs(result1['peak_force_time'] - result2['peak_force_time']):.3f} s")
print(f"Prop End Time Diff: {abs(result1['propagation_end_time'] - result2['propagation_end_time']):.3f} s")

print(f"\nWHY IS THERE A DIFFERENCE?")
print("Both should use the same force data and same indices...")
print("Let's check if the force data is identical:")
print(f"Force data identical: {np.array_equal(original_forces, reset_forces)}")
print(f"Position data identical: {np.array_equal(original_positions, reset_positions)}")

# The difference must be in how the calculator handles the time data internally
print(f"\nDEBUG: Check peak detection")
print(f"Original peak index in calculator: ?")
print(f"Reset peak index in calculator: ?")

# Let's manually check what's different
from scipy.signal import savgol_filter
smoothed_force = savgol_filter(original_forces, window_length=3, polyorder=1)
peak_idx = np.argmax(smoothed_force)

print(f"\nManual check:")
print(f"Peak index: {peak_idx}")
print(f"Peak time (original): {original_times[peak_idx]:.3f} s")
print(f"Peak time (reset): {reset_times[peak_idx]:.3f} s")
print(f"Peak force: {smoothed_force[peak_idx]:.6f} N")
