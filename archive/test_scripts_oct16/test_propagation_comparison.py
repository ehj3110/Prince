"""
Quick test to compare propagation end detection before and after fix
"""
import sys
import pandas as pd
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'support_modules'))
from adhesion_metrics_calculator import AdhesionMetricsCalculator

# Test on a sample autolog file
test_file = r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V2\Water_1mm_SteppedCone_BPAGDA_1000\autolog_L100-L105.csv"

print("\n" + "="*80)
print("PROPAGATION END DETECTION TEST")
print("="*80)
print(f"\nTest file: {Path(test_file).name}\n")

# Load data
df = pd.read_csv(test_file)
time_data = df['Elapsed Time (s)'].to_numpy()
force_data = df['Force (N)'].to_numpy()
position_data = df['Position (mm)'].to_numpy()

# Initialize calculator
calc = AdhesionMetricsCalculator()

# Apply smoothing
smoothed_force = calc._apply_smoothing(force_data)

# Find peaks
peak_indices, _ = calc._detect_peaks(smoothed_force, height_threshold=0.01)
print(f"Found {len(peak_indices)} peaks")

if len(peak_indices) >= 3:
    # Test on first 3 layers
    for i in range(3):
        print(f"\n--- Layer {i+1} ---")
        peak_idx = peak_indices[i]
        peak_time = time_data[peak_idx]
        peak_force = force_data[peak_idx]
        
        print(f"Peak at index {peak_idx}, time {peak_time:.3f}s, force {peak_force:.4f}N")
        
        # Find motion end (approximation)
        motion_end_idx = min(peak_idx + 500, len(smoothed_force) - 1)
        
        # Call the propagation end detection
        prop_end_idx = calc._find_propagation_end_reverse_search(
            smoothed_force, peak_idx, position_data, motion_end_idx
        )
        
        prop_end_time = time_data[prop_end_idx]
        prop_end_pos = position_data[prop_end_idx]
        
        print(f"Propagation end at index {prop_end_idx}, time {prop_end_time:.3f}s, position {prop_end_pos:.3f}mm")
        print(f"Duration from peak to prop_end: {prop_end_time - peak_time:.3f}s")
        
        # Calculate 80% lifting point for reference
        search_region_positions = position_data[peak_idx:motion_end_idx]
        min_pos = np.min(search_region_positions)
        max_pos = position_data[peak_idx]
        target_80pct = max_pos - 0.8 * (max_pos - min_pos)
        print(f"80% lifting position: {target_80pct:.3f}mm (range: {max_pos:.3f} to {min_pos:.3f}mm)")

print("\n" + "="*80)
print("Test complete!")
print("="*80 + "\n")
