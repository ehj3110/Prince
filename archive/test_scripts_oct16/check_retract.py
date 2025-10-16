import pandas as pd
import numpy as np

df = pd.read_csv(r'C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V2\Water_1mm_SteppedCone_BPAGDA_6000\autolog_L430-L435.csv')

position = df['Position (mm)'].values
time = df['Elapsed Time (s)'].values

print("Checking motion pattern for first two layers:")
print("\nLayer 1 region (indices 0-500):")
for i in range(0, 500, 50):
    print(f"  Index {i}: Time={time[i]:.3f}s, Pos={position[i]:.3f}mm")

print("\nLooking for RETRACT after first LIFT (around index 320-400):")
for i in range(300, 450, 10):
    print(f"  Index {i}: Time={time[i]:.3f}s, Pos={position[i]:.3f}mm")
