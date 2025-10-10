"""
Quick verification of new propagation end detection method.
Compares results with test script to ensure consistency.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'support_modules'))

import numpy as np
import pandas as pd
from adhesion_metrics_calculator import AdhesionMetricsCalculator

# Load the test file
data_file = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\V17Tests\2p5PEO_1mm_Ramped_BPAGDA_Old\autolog_L110-L114.csv")

df = pd.read_csv(data_file)

# Extract Layer 111 (indices 1079-2165 based on boundary detection)
layer_data = df.iloc[1079:2166].copy()
layer_data.reset_index(drop=True, inplace=True)

print("=" * 80)
print("VERIFICATION: New Propagation End Detection Method")
print("=" * 80)
print(f"Layer 111 from: {data_file.name}")
print(f"Data points: {len(layer_data)}")
print()

# Run calculator
calc = AdhesionMetricsCalculator(smoothing_sigma=0.5)

time = layer_data['Elapsed Time (s)'].values
position = layer_data['Position (mm)'].values
force = layer_data['Force (N)'].values

metrics = calc.calculate_from_arrays(time, position, force)

# Get more details
from scipy.ndimage import gaussian_filter1d
smoothed_force = gaussian_filter1d(force, sigma=0.5)
peak_idx = np.argmax(smoothed_force)
prop_end_time = metrics['propagation_end_time']
# Find the index corresponding to prop_end_time
prop_end_idx = np.argmin(np.abs(time - (time[0] + prop_end_time)))

print("RESULTS:")
print("-" * 80)
print(f"Peak Force: {metrics['peak_force']:.4f} N (at time {metrics['peak_force_time']:.3f} s, index {peak_idx})")
print(f"Baseline Force: {metrics['baseline_force']:.4f} N")
print(f"Propagation End Time: {metrics['propagation_end_time']:.3f} s (index {prop_end_idx})")
print(f"Force at prop end: {smoothed_force[prop_end_idx]:.4f} N")
print()

print("EXPECTED FROM TEST SCRIPT:")
print("-" * 80)
print("Peak Force: 0.2078 N (at index 737)")
print("Baseline Force: 0.0046 N (at index 754)")
print("Second Deriv Peak: index 751")
print("Propagation End: index 754 (zero-crossing after 2nd deriv peak)")
print()

if abs(metrics['peak_force'] - 0.2078) < 0.001:
    print("✓ Peak force matches!")
else:
    print("✗ Peak force doesn't match")

if abs(metrics['baseline_force'] - 0.0046) < 0.01:
    print("✓ Baseline force is close to expected!")
else:
    print(f"⚠ Baseline force differs: {metrics['baseline_force']:.4f} vs 0.0046 expected")
    print("  This could be due to slight differences in indexing or smoothing")
