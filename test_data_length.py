"""
Test if data length difference is causing the issue
"""
import pandas as pd
import numpy as np
from scipy.signal import savgol_filter
from adhesion_metrics_calculator import AdhesionMetricsCalculator

# Load data
df = pd.read_csv("autolog_L198-L200.csv")
if 'Elapsed Time (s)' in df.columns:
    df = df.rename(columns={'Elapsed Time (s)': 'Time', 'Position (mm)': 'Position', 'Force (N)': 'Force'})

print("TESTING DATA LENGTH EFFECT")
print("="*40)

calc = AdhesionMetricsCalculator()

# Test 1: 619 points (like test calculator uses)
print(f"TEST 1: 619 points (test calculator range)")
start_idx = 0
end_idx = 619
times1 = df['Time'].values[start_idx:end_idx] - df['Time'].values[start_idx]  # 619 points
positions1 = df['Position'].values[start_idx:end_idx] 
forces1 = df['Force'].values[start_idx:end_idx]

print(f"  Data length: {len(times1)}")
print(f"  Time range: {times1[0]:.3f} to {times1[-1]:.3f} s")

result1 = calc.calculate_from_arrays(times1, positions1, forces1, layer_number=198)
print(f"  Propagation End Time: {result1['propagation_end_time']:.3f} s")

# Test 2: 620 points (like hybrid plotter uses)
print(f"\nTEST 2: 620 points (hybrid plotter range)")
times2 = df['Time'].values[start_idx:end_idx+1] - df['Time'].values[start_idx]  # 620 points
positions2 = df['Position'].values[start_idx:end_idx+1]
forces2 = df['Force'].values[start_idx:end_idx+1]

print(f"  Data length: {len(times2)}")
print(f"  Time range: {times2[0]:.3f} to {times2[-1]:.3f} s")

result2 = calc.calculate_from_arrays(times2, positions2, forces2, layer_number=198)
print(f"  Propagation End Time: {result2['propagation_end_time']:.3f} s")

print(f"\nCOMPARISON:")
print(f"  619 points: {result1['propagation_end_time']:.3f} s")
print(f"  620 points: {result2['propagation_end_time']:.3f} s")
print(f"  Difference: {abs(result1['propagation_end_time'] - result2['propagation_end_time']):.3f} s")

print(f"\nExpected from test calculator: ~11.704 s")
diff1 = abs(result1['propagation_end_time'] - 11.704)
diff2 = abs(result2['propagation_end_time'] - 11.704)

print(f"  619 points difference from expected: {diff1:.3f} s")
print(f"  620 points difference from expected: {diff2:.3f} s")

if diff1 < diff2:
    print(f"✅ 619 points is closer to test calculator!")
    print(f"The issue is that hybrid plotter uses end_idx+1 instead of end_idx")
elif diff2 < diff1:
    print(f"✅ 620 points is closer to test calculator!")
else:
    print(f"Both are equally close/far from test calculator")

# Check what the extra data point is
if len(times2) > len(times1):
    extra_time = times2[-1]
    extra_force = forces2[-1]
    print(f"\nExtra data point:")
    print(f"  Time: {extra_time:.3f} s")
    print(f"  Force: {extra_force:.6f} N")
    print(f"  This extra point may be affecting the search region!")
