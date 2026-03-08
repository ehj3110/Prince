import pandas as pd

df = pd.read_csv(r'C:\Users\cheng sun\BoyuanSun\Slicing\Evan\10SqmmCylinder\Printing_Logs\ToProcess\peak_cycle_continuous.csv')

print('Extracted cycle durations:')
print('=' * 70)

for col in df.columns[::3]:
    folder = col.replace('_Time', '')
    time_col = folder + '_Time'
    force_col = folder + '_Force'
    
    if time_col in df.columns and force_col in df.columns:
        valid_data = df[time_col].notna()
        count = valid_data.sum()
        duration = df[time_col][valid_data].max() if count > 0 else 0
        print(f'{folder:35s} {count:4d} points, {duration:6.3f}s duration')

print('=' * 70)
