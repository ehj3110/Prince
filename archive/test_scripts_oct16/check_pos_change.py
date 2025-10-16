import pandas as pd
import numpy as np

df = pd.read_csv('C:/Users/ehunt/OneDrive - Northwestern University/Lab Work/Nissan/Adhesion Tests/SteppedConeTests/V2/Water_1mm_SteppedCone_BPAGDA_6000/autolog_L335-L340.csv')
pos = df.iloc[:, 1].values
time = df.iloc[:, 0].values

print('Position changes in first 400 indices:')
for i in range(0, 400, 10):
    print(f'idx {i:3d}: t={time[i]:6.3f}s, pos={pos[i]:6.2f}mm')
