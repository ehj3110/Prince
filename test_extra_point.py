"""
Test the impact of the extra data point
"""
import pandas as pd
import numpy as np
from adhesion_metrics_calculator import AdhesionMetricsCalculator

# Load data
df = pd.read_csv("autolog_L198-L200.csv")
if 'Elapsed Time (s)' in df.columns:
    df = df.rename(columns={'Elapsed Time (s)': 'Time', 'Position (mm)': 'Position', 'Force (N)': 'Force'})

times = df['Time'].values
positions = df['Position'].values
forces = df['Force'].values

calc = AdhesionMetricsCalculator()

print("TESTING IMPACT OF EXTRA DATA POINT")
print("="*40)

# Test 1: Using 619 points (0 to 618)
print("TEST 1: 619 points (0 to 618)")
segment1_time = times[0:619] - times[0]
segment1_position = positions[0:619]
segment1_force = forces[0:619]
result1 = calc.calculate_from_arrays(segment1_time, segment1_position, segment1_force, layer_number=198)
print(f"  Length: {len(segment1_time)}")
print(f"  Prop End Time: {result1['propagation_end_time']:.3f} s")

# Test 2: Using 620 points (0 to 619) - like hybrid plotter
print("\nTEST 2: 620 points (0 to 619)")
segment2_time = times[0:620] - times[0] 
segment2_position = positions[0:620]
segment2_force = forces[0:620]
result2 = calc.calculate_from_arrays(segment2_time, segment2_position, segment2_force, layer_number=198)
print(f"  Length: {len(segment2_time)}")
print(f"  Prop End Time: {result2['propagation_end_time']:.3f} s")

print(f"\nDifference: {abs(result1['propagation_end_time'] - result2['propagation_end_time']):.3f} s")

# Let's check what that extra data point is
print(f"\nExtra data point analysis:")
print(f"  Time at index 619: {times[619]:.3f} s")
print(f"  Force at index 619: {forces[619]:.6f} N")
print(f"  This point is at: {times[619] - times[0]:.3f} s relative time")

# Check if this matches what the hybrid plotter reported
print(f"\nHybrid plotter reported: 11.803 s")
print(f"620-point result: {result2['propagation_end_time']:.3f} s")
print(f"Match: {abs(result2['propagation_end_time'] - 11.803) < 0.01}")
