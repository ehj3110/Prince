import pandas as pd
import numpy as np

# Read the automated work of adhesion file
v9_file = r'C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V9\FEP_500um_Air_V19\automated_work_of_adhesion.csv'
df = pd.read_csv(v9_file)

print(f'Total layers: {len(df)}')
print(f'\nColumns: {df.columns.tolist()}')
print(f'\nUnique area values (mm²):')
unique_areas = df['Cross_Sectional_Area_mm2'].unique()
for area in unique_areas:
    count = (df['Cross_Sectional_Area_mm2'] == area).sum()
    radius = np.sqrt(area / np.pi)
    print(f'  Area: {area:.4f} mm² (r = {radius:.2f} mm) - {count} layers')

print(f'\nArea mapping (Layer -> Area):')
for idx, row in df.iterrows():
    print(f'  Layer {row["Layer_Number"]}: {row["Cross_Sectional_Area_mm2"]:.4f} mm²')
