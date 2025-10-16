import pandas as pd
import numpy as np

# Load sandwich data
df = pd.read_csv(r'C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V2\Water_1mm_SandwichedCone_BPAGDA_6000umps\autolog_L335-L340.csv')
times = df['Elapsed Time (s)'].values
pos = df['Position (mm)'].values
forces = df['Force (N)'].values

print('=== Analyzing Sandwich Data Structure ===\n')
print('First 15 rows:')
for i in range(0, 15):
    print(f'  idx {i:3d}: t={times[i]:6.3f}s, pos={pos[i]:7.4f}mm, F={forces[i]:8.5f}N')

print('\n Rows around first motion (200-220):')
for i in range(200, 221):
    print(f'  idx {i:3d}: t={times[i]:6.3f}s, pos={pos[i]:7.4f}mm, F={forces[i]:8.5f}N')

# Find where position starts changing
print('\n=== Finding where actual lifting starts ===')
stable_pos = pos[100]
for i in range(100, min(400, len(pos))):
    if abs(pos[i] - stable_pos) > 0.02:
        print(f'Position starts changing at idx {i}: t={times[i]:.3f}s')
        print(f'  Before: {stable_pos:.4f}mm')
        print(f'  After: {pos[i]:.4f}mm')
        print(f'  Force: {forces[i]:.5f}N')
        break
