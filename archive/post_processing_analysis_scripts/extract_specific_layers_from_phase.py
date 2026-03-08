"""
Extract Specific Layer Numbers Using Phase Column
=================================================

Extracts specified layer numbers from autolog files using Phase column.

Author: Cheng Sun Lab Team
Date: February 10, 2026
"""

import pandas as pd
import numpy as np
from pathlib import Path
import argparse
import sys


def extract_specific_layer(df, layer_number):
    """
    Extract a specific layer number using Phase column.
    Layer 0 = first layer, Layer 1 = second layer, etc.
    Extracts: Exposure + Lift from selected layer + Pause from next layer.
    
    Returns: layer_data dict with all info
    """
    # Standardize column names
    column_mapping = {}
    for col in df.columns:
        if 'phase' in col.lower():
            column_mapping[col] = 'Phase'
        elif 'time' in col.lower():
            column_mapping[col] = 'Time'
        elif 'position' in col.lower():
            column_mapping[col] = 'Position'
        elif 'force' in col.lower():
            column_mapping[col] = 'Force'
    
    df.rename(columns=column_mapping, inplace=True)
    
    if 'Phase' not in df.columns:
        return None
    
    # Find all exposure phase starts
    exposure_starts = []
    prev_phase = None
    
    for idx, phase in enumerate(df['Phase']):
        if phase == 'Exposure' and prev_phase != 'Exposure':
            exposure_starts.append(idx)
        prev_phase = phase
    
    if layer_number >= len(exposure_starts):
        return None
    
    # Get the specified layer
    exposure_start = exposure_starts[layer_number]
    
    # Find where this layer ends
    if layer_number + 1 < len(exposure_starts):
        next_exposure_start = exposure_starts[layer_number + 1]
    else:
        next_exposure_start = len(df)
    
    layer_data_raw = df.iloc[exposure_start:next_exposure_start]
    
    # Find lift start
    lift_rows = layer_data_raw[layer_data_raw['Phase'] == 'Lift']
    if len(lift_rows) == 0:
        return None
    
    lift_start_idx = lift_rows.index[0]
    lift_end_idx = lift_rows.index[-1]
    
    # Calculate baseline (10 points before lift)
    baseline_start = max(exposure_start, lift_start_idx - 10)
    baseline = df.loc[baseline_start:lift_start_idx-1, 'Force'].mean()
    
    # Peak force in this layer
    peak_force = layer_data_raw['Force'].max()
    peak_idx = layer_data_raw['Force'].idxmax()
    
    # Get pause from next layer if available
    if layer_number + 1 < len(exposure_starts):
        next_layer_start = exposure_starts[layer_number + 1]
        # Extract from current exposure start to just before next exposure
        next_layer_data = df.iloc[lift_end_idx+1:next_layer_start]
        pause_data = next_layer_data[next_layer_data['Phase'] == 'Pause']
        
        if len(pause_data) > 0:
            final_end_idx = pause_data.index[-1]
        else:
            final_end_idx = next_layer_start - 1
    else:
        final_end_idx = next_exposure_start - 1
    
    # Extract cycle
    cycle_df = df.loc[exposure_start:final_end_idx, ['Time', 'Position', 'Force', 'Phase']].copy()
    
    # Calculate lift start time relative to exposure start
    lift_start_time = df.loc[lift_start_idx, 'Time'] - df.loc[exposure_start, 'Time']
    
    # Reset time
    cycle_df['Time'] = cycle_df['Time'] - cycle_df['Time'].iloc[0]
    
    # Add metadata
    cycle_df['Lift_Start_Time'] = lift_start_time
    cycle_df['Baseline_Force'] = baseline
    
    relative_peak = peak_force - baseline
    
    return {
        'data': cycle_df,
        'layer_number': layer_number,
        'peak_force': peak_force,
        'baseline': baseline,
        'relative_peak': relative_peak,
        'lift_start_time': lift_start_time
    }


def main():
    parser = argparse.ArgumentParser(
        description="Extract specific layers using Phase column"
    )
    parser.add_argument('--root', type=str, required=True,
                        help='Root folder containing material subfolders')
    parser.add_argument('--output', type=str, default='peak_layer_specific.csv',
                        help='Output CSV filename')
    parser.add_argument('--layers', type=str, required=True,
                        help='Comma-separated layer numbers for each folder (e.g., "2,2,2,2,2")')
    parser.add_argument('--exclude', type=str, default='',
                        help='Comma-separated list of folder names to exclude (e.g., "PDMSV2_800nm")')
    
    args = parser.parse_args()
    
    root_path = Path(args.root)
    layer_numbers = [int(x.strip()) for x in args.layers.split(',')]
    exclude_list = [x.strip() for x in args.exclude.split(',') if x.strip()]
    
    print("=" * 80)
    print("SPECIFIC LAYER EXTRACTION - USING PHASE COLUMN")
    print("=" * 80)
    print(f"Root folder: {root_path}")
    print(f"Layer numbers: {layer_numbers}")
    if exclude_list:
        print(f"Excluding: {exclude_list}")
    output_path = root_path / args.output
    print(f"Output file: {output_path}")
    print("=" * 80)
    
    folders = sorted([f for f in root_path.iterdir() if f.is_dir()])
    
    # Filter non-continuous only
    folders = [f for f in folders if 'Continuous' not in f.name]
    
    # Filter out excluded folders
    if exclude_list:
        folders = [f for f in folders if f.name not in exclude_list]
    
    if len(folders) != len(layer_numbers):
        print(f"[ERROR] Need {len(folders)} layer numbers, got {len(layer_numbers)}")
        sys.exit(1)
    
    folder_data_list = []
    
    for folder, layer_num in zip(folders, layer_numbers):
        print(f"\nProcessing: {folder.name}")
        csv_file = folder / "autolog_L45-L49.csv"
        
        if not csv_file.exists():
            print(f"  [SKIP] autolog_L45-L49.csv not found")
            continue
        
        print(f"  Reading: {csv_file.name}")
        print(f"  Extracting layer {layer_num}")
        
        try:
            df = pd.read_csv(csv_file)
            result = extract_specific_layer(df, layer_num)
            
            if result is None:
                print(f"  [ERROR] Could not extract layer {layer_num}")
                continue
            
            print(f"  Relative peak: {result['relative_peak']:.4f}N (absolute: {result['peak_force']:.4f}N, baseline: {result['baseline']:.4f}N)")
            print(f"  Lift start time: {result['lift_start_time']:.3f}s")
            print(f"  Extracted {len(result['data'])} points")
            
            folder_data_list.append((folder.name, result['data']))
            
        except Exception as e:
            print(f"  [ERROR] {str(e)}")
            import traceback
            traceback.print_exc()
    
    if not folder_data_list:
        print("\n[ERROR] No data extracted")
        sys.exit(1)
    
    # Combine data
    lengths = [len(data) for _, data in folder_data_list]
    max_rows = max(lengths)
    
    combined_df = pd.DataFrame()
    
    for folder_name, cycle_data in folder_data_list:
        padded_data = cycle_data.copy()
        if len(padded_data) < max_rows:
            padding = pd.DataFrame(np.nan, index=range(len(padded_data), max_rows), columns=padded_data.columns)
            padded_data = pd.concat([padded_data, padding], ignore_index=True)
        
        padded_data.columns = [f"{folder_name}_{col}" for col in padded_data.columns]
        combined_df = pd.concat([combined_df, padded_data], axis=1)
    
    combined_df.to_csv(output_path, index=False)
    
    print("\n" + "=" * 80)
    print(f"Successfully processed {len(folder_data_list)} folder(s)")
    print("=" * 80)
    print(f"\n[OK] Saved to: {output_path}")
    print(f"     Total columns: {len(combined_df.columns)}")
    print("\n[SUCCESS] Extraction complete!")


if __name__ == '__main__':
    main()
