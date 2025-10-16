"""
Test the peak detection fix on the actual L430-L435 file
"""
import sys
import os
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'post-processing'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'support_modules'))

from RawData_Processor import RawDataProcessor
from adhesion_metrics_calculator import AdhesionMetricsCalculator

# Test on the actual file with the false peak
csv_file = 'C:/Users/ehunt/OneDrive - Northwestern University/Lab Work/Nissan/Adhesion Tests/SteppedConeTests/V2/Water_1mm_SteppedCone_BPAGDA_6000/autolog_L430-L435.csv'

print(f"Testing peak detection on L430-L435 (Water 6000um/s)")
print(f"This file has a false raw peak at t=40.505s (0.5378N)")
print(f"The smoothed peak should be at a different location\n")

# Initialize processor
calc = AdhesionMetricsCalculator()
processor = RawDataProcessor(calc)

# Process the file
layers = processor.process_csv(csv_file)

# Find Layer 434
for layer in layers:
    if layer['number'] == 434:
        print(f"\n{'='*70}")
        print(f"Layer 434 Analysis:")
        print(f"{'='*70}")
        print(f"Peak Force: {layer['peak_force']:.4f} N")
        print(f"Peak Time: {layer['peak_time']:.3f} s")
        print(f"Peak Index: {layer['peak_idx']}")
        
        # Load raw data to check
        df = pd.read_csv(csv_file)
        time_data = df.iloc[:, 0].values
        force_data = df.iloc[:, 2].values
        
        # Check what force value is at the detected peak
        detected_force = force_data[layer['peak_idx']]
        print(f"Force at detected peak index: {detected_force:.4f} N")
        
        # Check false peak location
        false_peak_time = 40.505
        false_peak_idx = np.argmin(np.abs(time_data - false_peak_time))
        false_peak_force = force_data[false_peak_idx]
        print(f"\nFalse raw peak: t={time_data[false_peak_idx]:.3f}s, F={false_peak_force:.4f}N, idx={false_peak_idx}")
        
        # Get lifting phase boundaries
        lifting_start, lifting_end = layer['phases']['lifting']
        print(f"\nLifting phase: idx {lifting_start}-{lifting_end}")
        print(f"Lifting time range: {time_data[lifting_start]:.3f}s to {time_data[lifting_end]:.3f}s")
        
        # Check if peak is within lifting phase
        if lifting_start <= layer['peak_idx'] <= lifting_end:
            print(f"\n✓ Peak index {layer['peak_idx']} IS within lifting phase")
        else:
            print(f"\n✗ Peak index {layer['peak_idx']} is OUTSIDE lifting phase!")
        
        # Check if we're using smoothed peak or false peak
        if abs(layer['peak_time'] - false_peak_time) < 0.1:
            print(f"\n❌ PROBLEM: Peak at {layer['peak_time']:.3f}s is the FALSE PEAK!")
        else:
            print(f"\n✅ SUCCESS: Peak at {layer['peak_time']:.3f}s is NOT the false peak (which is at {false_peak_time:.3f}s)")
            print(f"   Peak force {layer['peak_force']:.4f}N is from smoothed segmented data")
        
        break
