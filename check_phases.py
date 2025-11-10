import pandas as pd
import numpy as np

df = pd.read_csv('test_autolog_L60-L65.csv')

print("Data around index 260 (where Sandwich starts):")
print("=" * 80)
subset = df.iloc[250:340]

for idx in subset.index:
    phase = df.loc[idx, 'Phase']
    time = df.loc[idx, 'Elapsed Time (s)']
    pos = df.loc[idx, 'Position (mm)']
    force = df.loc[idx, 'Force (N)']
    
    # Calculate position change from previous point
    if idx > 0:
        prev_pos = df.loc[idx-1, 'Position (mm)']
        pos_change = pos - prev_pos
        direction = "DOWN" if pos_change > 0.001 else ("UP  " if pos_change < -0.001 else "STAT")
    else:
        pos_change = 0
        direction = "    "
    
    marker = "<<<" if idx in [258, 260, 320] else ""
    print(f"{idx:4d}  {time:7.3f}s  {phase:10s}  Pos:{pos:7.4f}mm  dPos:{pos_change:7.4f}  {direction}  Force:{force:7.5f}N  {marker}")

print("\n" + "=" * 80)
print("Summary:")
print(f"  Index 258: Phase changes to {df.loc[258, 'Phase']}")
print(f"  Index 320: Phase changes to {df.loc[320, 'Phase']}")
print(f"  Position at 250: {df.loc[250, 'Position (mm)']:.4f}mm")
print(f"  Position at 260: {df.loc[260, 'Position (mm)']:.4f}mm")
print(f"  Position at 320: {df.loc[320, 'Position (mm)']:.4f}mm")
print(f"  Total position change 250->320: {df.loc[320, 'Position (mm)'] - df.loc[250, 'Position (mm)']:.4f}mm (negative = upward)")
