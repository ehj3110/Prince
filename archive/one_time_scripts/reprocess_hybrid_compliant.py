"""
Reprocess Hybrid - Compliant folder with 400um skip to avoid false peaks
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent / 'support_modules'))
sys.path.insert(0, str(Path(__file__).parent / 'post-processing'))
from adhesion_metrics_calculator import AdhesionMetricsCalculator
from RawData_Processor import RawDataProcessor

folder_path = Path(r'C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\Presentation data\Final\Hybrid - Compliant')

print("="*80)
print("REPROCESSING HYBRID - COMPLIANT WITH 500um SKIP")
print("="*80)

# Initialize with 500um skip
calculator = AdhesionMetricsCalculator(skip_initial_distance_um=500)
processor = RawDataProcessor(calculator)

autolog_files = sorted(folder_path.glob('autolog_*.csv'))
print(f'Found {len(autolog_files)} autolog files')

all_results = []
for autolog_file in autolog_files:
    try:
        layers_data = processor.process_csv(str(autolog_file))
        for layer_obj in layers_data:
            layer_num = layer_obj.get('layer_number', 0)
            metrics = layer_obj.get('metrics', {})
            metrics['layer_number'] = layer_num
            metrics['source_file'] = autolog_file.name
            metrics['condition'] = folder_path.name
            all_results.append(metrics)
    except Exception as e:
        print(f'Error: {e}')

df_results = pd.DataFrame(all_results)
print(f'Processed {len(df_results)} layers')

# Map area from existing file (READ-ONLY)
area_csv = folder_path / 'automated_work_of_adhesion.csv'
existing_df = pd.read_csv(area_csv)
area_map = dict(zip(existing_df['Layer_Number'], existing_df['Cross_Sectional_Area_mm2']))
df_results['Cross_Sectional_Area_mm2'] = df_results['layer_number'].map(area_map)

# Standardize columns
df_results['Peak_Force_N'] = df_results.get('peak_force_corrected', df_results.get('peak_force', 0))
df_results['Work_of_Adhesion_mJ'] = df_results.get('work_of_adhesion_corrected_mJ', df_results.get('work_of_adhesion_mJ', 0))
df_results['Total_Peel_Distance_mm'] = df_results.get('total_peel_distance', 0).abs()
df_results['Layer_Number'] = df_results['layer_number']
df_results['Source_File'] = df_results['source_file']
df_results['Condition'] = df_results['condition']

# Load existing MASTER and update
master_path = folder_path.parent / 'MASTER_all_metrics.csv'
master_df = pd.read_csv(master_path)
print(f'Original MASTER: {len(master_df)} rows')

# Remove old Hybrid - Compliant rows
master_df = master_df[master_df['Condition'] != 'Hybrid - Compliant']
print(f'After removing old: {len(master_df)} rows')

# Add new results
master_df = pd.concat([master_df, df_results], ignore_index=True)
print(f'After adding new: {len(master_df)} rows')

# Save
master_df.to_csv(master_path, index=False)
print(f'Saved updated MASTER')

peak_min = df_results['Peak_Force_N'].min()
peak_max = df_results['Peak_Force_N'].max()
print(f'Peak Force range for Hybrid-Compliant: {peak_min:.4f} - {peak_max:.4f} N')
