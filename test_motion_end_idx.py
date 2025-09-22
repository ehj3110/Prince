"""
Test if motion_end_idx parameter is causing the propagation end difference
"""
import pandas as pd
import numpy as np
from scipy.signal import savgol_filter
from adhesion_metrics_calculator import AdhesionMetricsCalculator

# Load data
df = pd.read_csv("autolog_L198-L200.csv")
if 'Elapsed Time (s)' in df.columns:
    df = df.rename(columns={'Elapsed Time (s)': 'Time', 'Position (mm)': 'Position', 'Force (N)': 'Force'})

print("TESTING MOTION_END_IDX PARAMETER EFFECT")
print("="*50)

# Layer 198 data (reset time like hybrid plotter)
start_idx = 0
end_idx = 619
times = df['Time'].values[start_idx:end_idx+1] - df['Time'].values[start_idx]  # Reset time
positions = df['Position'].values[start_idx:end_idx+1]
forces = df['Force'].values[start_idx:end_idx+1]

print(f"Data length: {len(times)} points")
print(f"Time range: {times[0]:.3f} to {times[-1]:.3f} seconds")

calc = AdhesionMetricsCalculator()

# Test 1: Normal calculator with motion_end_idx=None (default)
print(f"\nTEST 1: motion_end_idx=None (default)")
result1 = calc.calculate_from_arrays(times, positions, forces, layer_number=198, motion_end_idx=None)
print(f"  Propagation End Time: {result1['propagation_end_time']:.3f} s")

# Test 2: Normal calculator with motion_end_idx=len(forces) (like test calculator)
print(f"\nTEST 2: motion_end_idx=len(forces) (like test calculator)")
result2 = calc.calculate_from_arrays(times, positions, forces, layer_number=198, motion_end_idx=len(forces))
print(f"  Propagation End Time: {result2['propagation_end_time']:.3f} s")

# Test 3: Let's also test with the exact length the test calculator uses
print(f"\nTEST 3: motion_end_idx=len(smoothed_force)")
smoothed_force = savgol_filter(forces, window_length=3, polyorder=1)
result3 = calc.calculate_from_arrays(times, positions, forces, layer_number=198, motion_end_idx=len(smoothed_force))
print(f"  Propagation End Time: {result3['propagation_end_time']:.3f} s")

print(f"\nCOMPARISON:")
print(f"  Test 1 (None): {result1['propagation_end_time']:.3f} s")
print(f"  Test 2 (len(forces)): {result2['propagation_end_time']:.3f} s") 
print(f"  Test 3 (len(smoothed_force)): {result3['propagation_end_time']:.3f} s")

print(f"\nExpected from test calculator: ~11.704 s")

# Check which one matches the test calculator
differences = [
    abs(result1['propagation_end_time'] - 11.704),
    abs(result2['propagation_end_time'] - 11.704), 
    abs(result3['propagation_end_time'] - 11.704)
]

best_match = np.argmin(differences)
test_names = ["None", "len(forces)", "len(smoothed_force)"]

print(f"\nBest match: Test {best_match + 1} ({test_names[best_match]}) with difference {differences[best_match]:.3f} s")

if differences[best_match] < 0.01:
    print(f"✅ FOUND THE SOLUTION! Use motion_end_idx={test_names[best_match]}")
else:
    print(f"❌ None of these match the test calculator exactly")

# Also test the search region calculation manually
print(f"\nDEBUG: Search region lengths")
print(f"  len(forces): {len(forces)}")
print(f"  len(smoothed_force): {len(smoothed_force)}")
print(f"  len(second_derivative): {len(smoothed_force) - 2}")

# Manual calculation of search regions
peak_idx = np.argmax(smoothed_force)
print(f"  Peak index: {peak_idx}")

# Case 1: motion_end_idx = None
search_end_1 = len(smoothed_force) - 2  # len(second_derivative)
print(f"  Search end (None): {search_end_1}")

# Case 2: motion_end_idx = len(forces)
search_end_2 = min(len(smoothed_force) - 2, len(forces) - 2)
print(f"  Search end (len(forces)): {search_end_2}")

# Case 3: motion_end_idx = len(smoothed_force) 
search_end_3 = min(len(smoothed_force) - 2, len(smoothed_force) - 2)
print(f"  Search end (len(smoothed_force)): {search_end_3}")

print(f"\nSearch region differences may explain the propagation end differences!")
