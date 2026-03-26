"""
Final comparison: Test Calculator vs Normal Calculator
Find the exact difference in propagation end calculation
"""
import pandas as pd
import numpy as np
from scipy.signal import savgol_filter
from adhesion_metrics_calculator import AdhesionMetricsCalculator

# Load data
df = pd.read_csv("autolog_L198-L200.csv")
if 'Elapsed Time (s)' in df.columns:
    df = df.rename(columns={'Elapsed Time (s)': 'Time', 'Position (mm)': 'Position', 'Force (N)': 'Force'})

print("FINAL COMPARISON: TEST CALCULATOR vs NORMAL CALCULATOR")
print("="*60)

# Layer 198 data - EXACT same boundaries as test calculator uses
layer_start = 0
layer_end = 619  # Test calculator uses range(0, 619)

times = df['Time'].values[layer_start:layer_end]
positions = df['Position'].values[layer_start:layer_end]
forces = df['Force'].values[layer_start:layer_end]

print(f"Using EXACT same data as test calculator:")
print(f"  Indices: {layer_start} to {layer_end-1} ({len(times)} points)")
print(f"  Time range: {times[0]:.3f} to {times[-1]:.3f} seconds")

# Test 1: Manual calculation (same as test calculator logic)
print(f"\nTEST CALCULATOR LOGIC (Manual):")
smoothed_force = savgol_filter(forces, window_length=3, polyorder=1)
peak_idx = np.argmax(smoothed_force)
peak_time = times[peak_idx]
peak_force = smoothed_force[peak_idx]

# Propagation end calculation (test calculator method)
first_derivative = np.diff(smoothed_force)
second_derivative = np.diff(first_derivative)
search_start_idx = max(0, peak_idx - 1)
second_deriv_search = second_derivative[search_start_idx:]
max_second_deriv_idx = np.argmax(second_deriv_search)
prop_end_idx = search_start_idx + max_second_deriv_idx + 2

if prop_end_idx >= len(times):
    prop_end_idx = len(times) - 1

prop_end_time_test = times[prop_end_idx]
baseline_test = smoothed_force[prop_end_idx]

print(f"  Peak Time: {peak_time:.3f} s")
print(f"  Prop End Time: {prop_end_time_test:.3f} s")
print(f"  Peak Index: {peak_idx}")
print(f"  Prop End Index: {prop_end_idx}")

# Test 2: Normal calculator with EXACT same data
print(f"\nNORMAL CALCULATOR:")
calc = AdhesionMetricsCalculator()
result = calc.calculate_from_arrays(times, positions, forces, layer_number=198)

print(f"  Peak Time: {result['peak_force_time']:.3f} s")
print(f"  Prop End Time: {result['propagation_end_time']:.3f} s")

# Check if there are differences
print(f"\nCOMPARISON:")
peak_diff = abs(peak_time - result['peak_force_time'])
prop_diff = abs(prop_end_time_test - result['propagation_end_time'])

print(f"  Peak Time Difference: {peak_diff:.3f} s")
print(f"  Prop End Time Difference: {prop_diff:.3f} s")

if prop_diff > 0.01:  # If more than 0.01s difference
    print(f"\n🚨 FOUND THE ISSUE!")
    print(f"  Test Calculator Prop End: {prop_end_time_test:.3f} s")
    print(f"  Normal Calculator Prop End: {result['propagation_end_time']:.3f} s")
    print(f"  Difference: {prop_diff:.3f} s")
    print(f"\nThe normal calculator IS calculating different propagation end times!")
    print(f"This suggests there's a bug in the normal calculator's propagation end method.")
else:
    print(f"\n✅ Both calculators give SAME results!")
    print(f"The issue must be elsewhere (data boundaries, time conversion, etc.)")

# Also check what times you reported as "correct"
print(f"\nExpected values (from your observations):")
print(f"  Layer 198 should be ~11.7s")
print(f"  Test calculator shows: {prop_end_time_test:.3f} s")
print(f"  Normal calculator shows: {result['propagation_end_time']:.3f} s")
