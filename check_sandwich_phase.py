import pandas as pd

df = pd.read_csv('test_autolog_L60-L65.csv')

print('Position changes around sandwich->lift transition:')
print('='*80)
for i in range(1544, 1875, 1):
    if i == 0:
        continue
    pos = df.iloc[i]['Position (mm)']
    prev_pos = df.iloc[i-1]['Position (mm)']
    delta = pos - prev_pos
    phase = df.iloc[i]['Phase']
    
    # Only print if phase changed or around transition
    if i >= 1540 and i <= 1565:
        direction = "DOWN" if delta < 0 else "UP  " if delta > 0 else "STAT"
        print(f'{i}: {phase:10s} | pos={pos:7.4f} | delta={delta:+7.4f} | {direction}')
    
    if i >= 1850 and i <= 1875:
        direction = "DOWN" if delta < 0 else "UP  " if delta > 0 else "STAT"
        print(f'{i}: {phase:10s} | pos={pos:7.4f} | delta={delta:+7.4f} | {direction}')
