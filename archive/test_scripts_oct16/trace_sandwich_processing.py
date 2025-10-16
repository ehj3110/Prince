"""
Trace through sandwich data processing to understand where sandwich step data is leaking
"""
import sys
import os
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'post-processing'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'support_modules'))

csv_file = 'C:/Users/ehunt/OneDrive - Northwestern University/Lab Work/Nissan/Adhesion Tests/SteppedConeTests/V2/Water_1mm_SteppedCone_BPAGDA_6000/autolog_L335-L340.csv'

# Load the data
df = pd.read_csv(csv_file)
time = df.iloc[:, 0].values
pos = df.iloc[:, 1].values
force = df.iloc[:, 2].values

print("="*70)
print("SANDWICH DATA STRUCTURE ANALYSIS")
print("="*70)
print(f"\nTotal rows: {len(time)}")
print(f"Time range: {time[0]:.2f}s to {time[-1]:.2f}s")

print(f"\nFirst 20 rows (showing pause/sandwich region):")
for i in range(20):
    print(f"  idx {i:3d}: t={time[i]:6.3f}s, pos={pos[i]:6.2f}mm, F={force[i]:7.4f}N")

print(f"\n\nNow let's trace what the boundary detector finds:")
print("="*70)

from RawData_Processor import RawDataProcessor
from adhesion_metrics_calculator import AdhesionMetricsCalculator

calc = AdhesionMetricsCalculator()
processor = RawDataProcessor(calc)

# Process and show Layer 335 details
layers = processor.process_csv(csv_file)

if len(layers) > 0:
    layer = layers[0]  # Layer 335
    print(f"\n\nLAYER 335 BOUNDARIES:")
    print("="*70)
    
    lifting_start, lifting_end = layer['phases']['lifting']
    retract_start, retract_end = layer['phases']['retraction']
    sandwich_start, sandwich_end = layer['phases']['sandwich']
    
    print(f"\nSandwich phase: idx {sandwich_start}-{sandwich_end}")
    if sandwich_start != sandwich_end:
        print(f"  Time: {time[sandwich_start]:.3f}s to {time[sandwich_end]:.3f}s")
        print(f"  Position: {pos[sandwich_start]:.2f}mm to {pos[sandwich_end]:.2f}mm")
        print(f"  First 10 rows of sandwich phase:")
        for i in range(sandwich_start, min(sandwich_start+10, sandwich_end+1)):
            print(f"    idx {i}: t={time[i]:.3f}s, pos={pos[i]:.2f}mm, F={force[i]:.4f}N")
    
    print(f"\nLifting phase: idx {lifting_start}-{lifting_end}")
    print(f"  Time: {time[lifting_start]:.3f}s to {time[lifting_end]:.3f}s")
    print(f"  Position: {pos[lifting_start]:.2f}mm to {pos[lifting_end]:.2f}mm")
    print(f"  First 10 rows of lifting phase:")
    for i in range(lifting_start, min(lifting_start+10, lifting_end+1)):
        print(f"    idx {i}: t={time[i]:.3f}s, pos={pos[i]:.2f}mm, F={force[i]:.4f}N")
    
    print(f"\n\nQUESTIONS TO ANSWER:")
    print("="*70)
    print(f"1. Is the lifting phase starting AFTER the sandwich step completes?")
    if lifting_start > 200:
        print(f"   ✓ YES - lifting starts at idx {lifting_start} (after sandwich)")
    else:
        print(f"   ✗ NO - lifting starts at idx {lifting_start} (TOO EARLY - includes sandwich!)")
    
    print(f"\n2. What data was passed to the calculator?")
    print(f"   Lifting phase indices: {lifting_start} to {lifting_end}")
    print(f"   This is {lifting_end - lifting_start + 1} data points")
    
    print(f"\n3. Does the lifting phase include any pause/sandwich data?")
    # Check if lifting phase includes early indices
    if lifting_start < 200:
        print(f"   ✗ YES - lifting starts at idx {lifting_start} which is during pause/sandwich!")
        print(f"   The pause/sandwich region is roughly idx 0-370")
    else:
        print(f"   ✓ NO - lifting starts at idx {lifting_start}, after pause/sandwich")
    
    print(f"\n4. What force values are in the lifting phase?")
    lifting_forces = force[lifting_start:lifting_end+1]
    print(f"   Min force: {np.min(lifting_forces):.4f}N")
    print(f"   Max force: {np.max(lifting_forces):.4f}N")
    print(f"   Mean force: {np.mean(lifting_forces):.4f}N")
    
    print(f"\n5. What did the calculator report as the peak?")
    print(f"   Peak force: {layer['peak_force']:.4f}N")
    print(f"   Peak time: {layer['peak_time']:.3f}s")
    print(f"   Peak index: {layer['peak_idx']}")
    print(f"   Force at peak idx in global array: {force[layer['peak_idx']]:.4f}N")
