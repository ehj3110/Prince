"""Debug script to check what data is being plotted"""

import pandas as pd
import numpy as np
from pathlib import Path

# Load the combined CSV
csv_path = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\TEMPO Picker\V2\MASTER_tempopicker_v2_combined.csv")
df = pd.read_csv(csv_path)

# Focus on 5umTEMPO_400umGap_Good
condition = '5umTEMPO_400umGap_Good'
df_cond = df[df['condition'] == condition].copy()

print(f"Data for {condition}:")
print(f"Total rows: {len(df_cond)}")
print(f"\nColumn names: {df_cond.columns.tolist()}")

# Check total_peel_distance
print(f"\nTotal Peel Distance stats:")
print(f"  Min: {df_cond['total_peel_distance'].min():.4f}")
print(f"  Max: {df_cond['total_peel_distance'].max():.4f}")
print(f"  Mean: {df_cond['total_peel_distance'].mean():.4f}")

# Check if there are any zero or near-zero values
zero_count = len(df_cond[df_cond['total_peel_distance'] < 0.1])
print(f"  Values < 0.1mm: {zero_count}")

# Group by radius and aggregate (like the plotting function does)
print(f"\nAggregated by radius (mean):")
grouped = df_cond.groupby('radius_mm')['total_peel_distance'].agg(['mean', 'count']).reset_index()
grouped = grouped.sort_values('radius_mm')

print(f"Number of unique radius values: {len(grouped)}")
print(f"\nFirst 10 aggregated points:")
print(grouped.head(10))

print(f"\nLast 10 aggregated points:")
print(grouped.tail(10))

# Check for any aggregated values near zero
near_zero = grouped[grouped['mean'] < 0.5]
if len(near_zero) > 0:
    print(f"\n⚠ Found {len(near_zero)} aggregated points with mean < 0.5mm:")
    print(near_zero)
else:
    print(f"\n✓ No aggregated points with mean < 0.5mm")

# Check the raw data for those near-zero aggregated points
if len(near_zero) > 0:
    print(f"\nChecking raw data for near-zero aggregated points:")
    for idx, row in near_zero.iterrows():
        radius = row['radius_mm']
        raw_data = df_cond[df_cond['radius_mm'] == radius]['total_peel_distance']
        print(f"\nRadius {radius:.4f}mm ({row['count']} points):")
        print(f"  Raw values: {raw_data.tolist()}")
        print(f"  Mean: {raw_data.mean():.4f}")
