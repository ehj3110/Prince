"""
Quick diagnostic to compare test script results with full analysis results
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'support_modules'))

import numpy as np
from pathlib import Path
from RawData_Processor import RawDataProcessor
from adhesion_metrics_calculator import AdhesionMetricsCalculator

# Load the autolog file
file_path = r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\V17Tests\2p5PEO_1mm_Ramped_BPAGDA_Old\autolog_L110-L114.csv"

processor = RawDataProcessor()
processor.load_autolog(file_path)

# Get Layer 111 data (indices 1079-2165 based on processor output)
layer_df = processor.df.iloc[1079:2166].copy()
layer_df = layer_df.reset_index(drop=True)

print("Layer 111 Diagnostic")
print("=" * 60)
print(f"Total data points: {len(layer_df)}")

# Extract arrays
time = layer_df['Time'].values
force = layer_df['Force'].values
position = layer_df['Pos'].values

# Create calculator
calc = AdhesionMetricsCalculator(smoothing_sigma=0.5)

# Calculate metrics
results = calc.calculate_from_arrays(
    times=time,
    forces=force,
    positions=position,
    layer_number=111,
    motion_end_idx=869  # From processor output
)

print("\nFull Analysis Results:")
print(f"  Peak Force: {results['peak_force']:.4f} N")
print(f"  Baseline Force: {results['baseline_force']:.4f} N")
print(f"  Peak Force Time: {results['peak_force_time']:.3f} s")
print(f"  Propagation End Time: {results['propagation_end_time']:.3f} s")
print(f"  Propagation Duration: {results['propagation_duration']:.3f} s")

# Get the smoothed force to check the value at propagation end
from scipy.ndimage import gaussian_filter1d
smoothed_force = gaussian_filter1d(force, sigma=0.5)

peak_idx = np.argmax(smoothed_force)
prop_end_time_absolute = time[0] + results['propagation_end_time']

# Find the index corresponding to propagation end time
prop_end_idx = np.argmin(np.abs(time - prop_end_time_absolute))

print(f"\nDiagnostic Info:")
print(f"  Peak index: {peak_idx}")
print(f"  Propagation end index: {prop_end_idx}")
print(f"  Smoothed force at prop end: {smoothed_force[prop_end_idx]:.4f} N")
print(f"  Raw force at prop end: {force[prop_end_idx]:.4f} N")

print("\n" + "=" * 60)
print("Expected from test script:")
print("  Peak index: 737")
print("  Propagation end index: 754")
print("  Force at prop end: 0.0046 N")
