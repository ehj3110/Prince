import pandas as pd
import numpy as np

df = pd.read_csv(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\Presentation data\Final\Hybrid - Compliant\automated_work_of_adhesion.csv")

print("=" * 80)
print("HYBRID - COMPLIANT DATA ANALYSIS")
print("=" * 80)

print(f"\nTotal rows: {len(df)}")

print("\nCross-sectional area:")
print(f"  Min: {df['Cross_Sectional_Area_mm2'].min():.2f} mm²")
print(f"  Max: {df['Cross_Sectional_Area_mm2'].max():.2f} mm²")

print("\nRadius (calculated from area):")
df['radius_calc'] = np.sqrt(df['Cross_Sectional_Area_mm2'] / np.pi)
print(f"  Min: {df['radius_calc'].min():.2f} mm")
print(f"  Max: {df['radius_calc'].max():.2f} mm")

print("\nUnique cross-sectional areas:")
area_counts = df['Cross_Sectional_Area_mm2'].value_counts().sort_index()
for area, count in area_counts.items():
    radius = np.sqrt(area / np.pi)
    radius_binned = np.ceil(radius / 0.5) * 0.5
    print(f"  {area:.2f} mm² (radius {radius:.2f} → bins to {radius_binned:.1f} mm): {count} measurements")

print("\nSource files:")
source_files = sorted(df['Source_File'].unique())
for sf in source_files:
    print(f"  {sf}")

print("\nLayer numbers from filenames:")
import re
layers = []
for sf in source_files:
    match = re.search(r'L(\d+)', sf)
    if match:
        layers.append(int(match.group(1)))
print(f"  Layer range: {min(layers)} to {max(layers)}")

print("\n" + "=" * 80)
print("EXPECTED: Should have same range as other conditions (layers 46-329)")
print("=" * 80)
