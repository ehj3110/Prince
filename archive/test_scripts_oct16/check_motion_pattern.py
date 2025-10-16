import pandas as pd
import numpy as np

# Load sandwich data
df = pd.read_csv(r'C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V2\Water_1mm_SandwichedCone_BPAGDA_6000umps\autolog_L335-L340.csv')
times = df['Elapsed Time (s)'].values
pos = df['Position (mm)'].values
forces = df['Force (N)'].values

print('=== Motion Analysis ===\n')

motions = [
    (10, 199, "Motion 0"),
    (209, 291, "Motion 1"),
    (1151, 1677, "Motion 2"),
    (1687, 1770, "Motion 3"),
    (2630, 3146, "Motion 4"),
    (3156, 3237, "Motion 5"),
]

for start, end, label in motions:
    start_pos = pos[start]
    end_pos = pos[end]
    delta = end_pos - start_pos
    direction = "DOWN" if delta < 0 else "UP"
    print(f"{label} (idx {start}-{end}): {start_pos:.2f}mm → {end_pos:.2f}mm ({delta:+.2f}mm {direction})")
    
print('\n=== Correct Pattern ===')
print('Motion 0 (DOWN): Sandwiching (53.25mm → 47.20mm)')
print('Motion 1 (UP): Lifting/Adhesion Test (47.20mm → 53.68mm) ← THIS IS THE ADHESION TEST')
print('Motion 2 (DOWN): Retraction (53.68mm → 47.20mm)')
print('--- Next Layer ---')
print('Motion 3 (UP): Lifting/Adhesion Test (47.20mm → 53.68mm)')
print('Motion 4 (DOWN): Retraction (53.68mm → 47.20mm)')
