"""Add Cross_Sectional_Area_mm2 to all condition CSVs based on FEP layer-to-area mapping"""

import pandas as pd
import numpy as np
from pathlib import Path

# Load FEP data to get layer-to-area mapping
fep_csv = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\Presentation data\Final\FEP\automated_work_of_adhesion.csv")
fep_df = pd.read_csv(fep_csv)

# Create a mapping of layer ranges to areas from FEP data
layer_area_map = {}
for idx, row in fep_df.iterrows():
    layer = row['Layer_Number']
    area = row['Cross_Sectional_Area_mm2']
    if not np.isnan(area):
        # Round layer to nearest 25 to create ranges
        layer_range = round(layer / 25) * 25
        if layer_range not in layer_area_map:
            layer_area_map[layer_range] = []
        layer_area_map[layer_range].append(area)

# Average the areas for each layer range
layer_area_avg = {k: np.mean(v) for k, v in layer_area_map.items()}

print("Layer-to-area mapping from FEP:")
for layer_range in sorted(layer_area_avg.keys()):
    print(f"  Layer ~{layer_range}: {layer_area_avg[layer_range]:.2f} mm²")

# Function to assign area based on source filename
def assign_area_from_source(source_file):
    if pd.isna(source_file):
        return np.nan
    
    # Extract layer number from filename like "autolog_L101-L105.csv"
    import re
    match = re.search(r'L(\d+)', str(source_file))
    if match:
        layer_num = int(match.group(1))
        layer_range = round(layer_num / 25) * 25
        return layer_area_avg.get(layer_range, np.nan)
    return np.nan

# Process all other condition folders
final_dir = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\Presentation data\Final")

for folder in ['Hybrid', 'Hybrid - Compliant', 'PDMS - Sealed', 'PDMS - Unsealed']:
    csv_path = final_dir / folder / 'automated_work_of_adhesion.csv'
    
    if not csv_path.exists():
        print(f"\n[X] Not found: {folder}")
        continue
    
    df = pd.read_csv(csv_path)
    
    # Add Cross_Sectional_Area_mm2 column if not present
    if 'Cross_Sectional_Area_mm2' not in df.columns:
        df['Cross_Sectional_Area_mm2'] = df['Source_File'].apply(assign_area_from_source)
        df.to_csv(csv_path, index=False)
        valid_areas = df['Cross_Sectional_Area_mm2'].notna().sum()
        print(f"\n[OK] {folder}: Added area to {valid_areas}/{len(df)} layers")
    else:
        print(f"\n[!] {folder}: Already has Cross_Sectional_Area_mm2 column")

print("\n[OK] Complete!")
