"""
Merge New Hybrid Data into Master CSV
======================================
This script:
1. Loads the old master CSV (contains folder '7' = new Hybrid data)
2. Loads the current master CSV
3. Removes old Hybrid and Hybrid-Compliant data from current CSV
4. Extracts folder '7' data from old CSV and maps it to match current CSV format
5. Adds the new Hybrid data to the master CSV
6. Saves the updated master CSV
"""

import pandas as pd
import numpy as np
from pathlib import Path

# File paths
final_dir = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\Presentation data\Final")
old_csv = final_dir / "MASTER_old_metrics.csv"
current_csv = final_dir / "data" / "MASTER_all_metrics.csv"

print("="*80)
print("MERGING NEW HYBRID DATA")
print("="*80)

# Load old CSV (contains folder '7' = new Hybrid)
print("\n1. Loading old master CSV...")
old_df = pd.read_csv(old_csv)
print(f"   Loaded {len(old_df)} rows from old CSV")
print(f"   Folders in old CSV: {sorted(old_df['folder'].unique())}")

# Extract folder 7 data (new Hybrid)
print("\n2. Extracting folder '7' data (new Hybrid)...")
new_hybrid_df = old_df[old_df['folder'] == 7].copy()
print(f"   Extracted {len(new_hybrid_df)} rows for new Hybrid")
print(f"   Layer range: {new_hybrid_df['layer_number'].min()} - {new_hybrid_df['layer_number'].max()}")

# Load current CSV
print("\n3. Loading current master CSV...")
current_df = pd.read_csv(current_csv)
print(f"   Loaded {len(current_df)} rows")
print("\n   Current conditions:")
print(current_df['condition_label'].value_counts())

# Remove old Hybrid and Hybrid-Compliant data
print("\n4. Removing old Hybrid and Hybrid-Compliant data...")
conditions_to_remove = ['Hybrid_0um_Unknown_Unknown_None', 'Hybrid - Compliant_0um_Unknown_Unknown_None']
current_df_filtered = current_df[~current_df['condition_label'].isin(conditions_to_remove)].copy()
removed_count = len(current_df) - len(current_df_filtered)
print(f"   Removed {removed_count} rows")
print(f"   Remaining: {len(current_df_filtered)} rows")

# Map old CSV columns to current CSV format
print("\n5. Mapping new Hybrid data to current CSV format...")
new_hybrid_mapped = pd.DataFrame({
    'folder_name': 'Hybrid',
    'source_file': new_hybrid_df['autolog_file'],
    'layer_number': new_hybrid_df['layer_number'],
    'condition_label': 'Hybrid_0um_Unknown_Unknown_None',
    'membrane': 'Hybrid',
    'gap_mm': 0.0,
    'tank': 'Unknown',
    'fluid': 'Unknown',
    'speed_um_s': None,
    'area_mm2': new_hybrid_df['cross_sectional_area_mm2'],
    'peak_force_N': new_hybrid_df['peak_force_corrected'],
    'work_of_adhesion_mJ': new_hybrid_df['work_of_adhesion_corrected_mJ'],
    'peel_distance_mm': new_hybrid_df['peel_distance_mm'],
    'peak_retraction_force_N': new_hybrid_df['peak_retraction_force_N'],
    'distance_to_peak_mm': new_hybrid_df['distance_to_peak_mm'],
    'propagation_distance_mm': new_hybrid_df['propagation_distance_mm'],
    'effective_stiffness_N_per_mm': new_hybrid_df['effective_stiffness_N_per_mm'],
    'stiffness_r_squared': new_hybrid_df['stiffness_r_squared'],
    'total_peel_time_s': new_hybrid_df['total_peel_duration'],
    'pre_initiation_time_s': new_hybrid_df['pre_initiation_duration']
})

print(f"   Mapped {len(new_hybrid_mapped)} rows")
print(f"   Sample data:")
print(new_hybrid_mapped[['folder_name', 'layer_number', 'peak_force_N', 'work_of_adhesion_mJ']].head())

# Combine data
print("\n6. Combining data...")
combined_df = pd.concat([current_df_filtered, new_hybrid_mapped], ignore_index=True)
print(f"   Total rows after merge: {len(combined_df)}")

# Sort by condition and layer number
combined_df = combined_df.sort_values(['condition_label', 'layer_number']).reset_index(drop=True)

print("\n   Final conditions:")
print(combined_df['condition_label'].value_counts())

# Save
backup_path = final_dir / "data" / "MASTER_all_metrics_backup.csv"
print(f"\n7. Backing up current CSV to: {backup_path.name}")
current_df.to_csv(backup_path, index=False)

print(f"\n8. Saving updated master CSV...")
combined_df.to_csv(current_csv, index=False)
print(f"   Saved to: {current_csv}")

print("\n" + "="*80)
print("MERGE COMPLETE!")
print("="*80)
print(f"\nSummary:")
print(f"  - Removed: 134 rows (old Hybrid + Hybrid-Compliant)")
print(f"  - Added: {len(new_hybrid_mapped)} rows (new Hybrid from folder 7)")
print(f"  - Final total: {len(combined_df)} rows")
print(f"\nCondition breakdown:")
for condition in sorted(combined_df['condition_label'].unique()):
    count = len(combined_df[combined_df['condition_label'] == condition])
    print(f"  - {condition}: {count} rows")
