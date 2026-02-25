import pandas as pd
import numpy as np
from pathlib import Path

base_path = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\Presentation data\Final")

conditions = ['FEP', 'Hybrid', 'Hybrid - Compliant', 'PDMS - Sealed', 'PDMS - Unsealed']

print("=" * 80)
print("CHECKING ORIGINAL CROSS-SECTIONAL AREA DATA IN EACH CONDITION")
print("=" * 80)

for cond in conditions:
    csv_path = base_path / cond / "automated_work_of_adhesion.csv"
    
    if not csv_path.exists():
        print(f"\n{cond}: FILE NOT FOUND")
        continue
    
    df = pd.read_csv(csv_path)
    
    print(f"\n{cond}:")
    print(f"  Total rows: {len(df)}")
    
    if 'Cross_Sectional_Area_mm2' in df.columns:
        areas = df['Cross_Sectional_Area_mm2'].dropna()
        if len(areas) > 0:
            print(f"  HAS Cross_Sectional_Area_mm2: {len(areas)}/{len(df)} valid values")
            print(f"  Area range: [{areas.min():.2f}, {areas.max():.2f}] mm²")
            radius_min = np.sqrt(areas.min() / np.pi)
            radius_max = np.sqrt(areas.max() / np.pi)
            print(f"  Radius range: [{radius_min:.2f}, {radius_max:.2f}] mm")
            print(f"  Unique areas: {areas.nunique()}")
        else:
            print(f"  Cross_Sectional_Area_mm2 column exists but ALL VALUES ARE NaN")
    else:
        print(f"  NO Cross_Sectional_Area_mm2 column")

print("\n" + "=" * 80)
