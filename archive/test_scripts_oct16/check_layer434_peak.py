"""
Check Layer 434 peak detection - should use smoothed peak, not raw false peak
"""
import sys
import os
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'post-processing'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'support_modules'))

from RawData_Processor import RawDataProcessor
from adhesion_metrics_calculator import AdhesionMetricsCalculator

# Test on L430-435 which includes Layer 434
csv_file = 'PrintingLogs_Backup/SteppedCone_V1_10mm2to100mm2_50umLayers_V2/2025-08-26/Print 1/autolog_L430-L435.csv'

print(f"Checking Layer 434 peak detection\n")

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
        time_data = df['Elapsed Time (s)'].values
        force_data = df['Force (N)'].values
        
        # Show force values around the peak
        peak_idx = layer['peak_idx']
        print(f"\nForce values around peak index {peak_idx}:")
        for i in range(max(0, peak_idx-5), min(len(force_data), peak_idx+6)):
            marker = " <-- PEAK" if i == peak_idx else ""
            print(f"  idx {i}: t={time_data[i]:.3f}s, F={force_data[i]:.4f}N{marker}")
        
        # Check for false peak around 40.5s
        false_peak_time = 40.505
        false_peak_idx = np.argmin(np.abs(time_data - false_peak_time))
        print(f"\nFalse peak check (around t=40.505s):")
        print(f"  idx {false_peak_idx}: t={time_data[false_peak_idx]:.3f}s, F={force_data[false_peak_idx]:.4f}N")
        
        # Check real smoothed peak around 40.74s
        real_peak_time = 40.740
        real_peak_idx = np.argmin(np.abs(time_data - real_peak_time))
        print(f"\nReal smoothed peak check (around t=40.740s):")
        print(f"  idx {real_peak_idx}: t={time_data[real_peak_idx]:.3f}s, F={force_data[real_peak_idx]:.4f}N")
        
        if layer['peak_time'] > 40.7:
            print(f"\n✅ SUCCESS: Peak at {layer['peak_time']:.3f}s uses SMOOTHED peak (not false spike at 40.5s)")
        else:
            print(f"\n❌ PROBLEM: Peak at {layer['peak_time']:.3f}s is still using false spike")
        
        break
