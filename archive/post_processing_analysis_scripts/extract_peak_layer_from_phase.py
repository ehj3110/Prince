"""
Extract Peak Layer Data Using Phase Column
==========================================

Uses the Phase column from autolog files to properly extract:
- Exposure phase from layer with highest relative peak (not last layer)
- Lift phase from same layer
- Pause phase from the NEXT layer

Author: Cheng Sun Lab Team
Date: February 10, 2026
"""

import pandas as pd
import numpy as np
from pathlib import Path
import argparse
import sys


def find_highest_relative_peak_layer(df):
    """
    Find the layer with the highest relative peak force that is NOT the last layer.
    Uses Phase column to identify layers properly.
    
    Returns: layer_number of selected layer
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
        print(f"  [ERROR] No Phase column found!")
        return None
    
    # Find all exposure phases (each represents a layer)
    exposure_starts = []
    prev_phase = None
    
    for idx, phase in enumerate(df['Phase']):
        if phase == 'Exposure' and prev_phase != 'Exposure':
            exposure_starts.append(idx)
        prev_phase = phase
    
    print(f"  Found {len(exposure_starts)} layers")
    
    if len(exposure_starts) < 2:
        print(f"  [ERROR] Need at least 2 layers (to exclude last one)")
        return None
    
    # Exclude last layer
    eligible_layers = exposure_starts[:-1]
    print(f"  Excluding last layer, evaluating {len(eligible_layers)} layers")
    
    # For each layer, find peak force and baseline
    layer_info = []
    
    for layer_idx, start_idx in enumerate(eligible_layers):
        # Find where this layer ends (next layer starts, or end of data)
        if layer_idx + 1 < len(exposure_starts):
            end_idx = exposure_starts[layer_idx + 1]
        else:
            end_idx = len(df)
        
        layer_data = df.iloc[start_idx:end_idx]
        
        # Find lift start within this layer
        lift_rows = layer_data[layer_data['Phase'] == 'Lift']
        if len(lift_rows) == 0:
            continue
        
        lift_start_idx = lift_rows.index[0]
        
        # Baseline: average force in 10 points before lift
        baseline_start = max(start_idx, lift_start_idx - 10)
        baseline = df.loc[baseline_start:lift_start_idx-1, 'Force'].mean()
        
        # Peak force: maximum during this layer
        peak_force = layer_data['Force'].max()
        relative_peak = peak_force - baseline
        
        layer_info.append({
            'layer_number': layer_idx,
            'start_idx': start_idx,
            'end_idx': end_idx,
            'peak_force': peak_force,
            'baseline': baseline,
            'relative_peak': relative_peak,
            'lift_start_idx': lift_start_idx
        })
    
    if not layer_info:
        print(f"  [ERROR] No valid layers found")
        return None
    
    # Find layer with highest relative peak
    best_layer = max(layer_info, key=lambda x: x['relative_peak'])
    
    print(f"  Selected layer {best_layer['layer_number']} (of {len(eligible_layers)-1})")
    print(f"  Highest RELATIVE peak: {best_layer['relative_peak']:.4f}N")
    print(f"  (absolute: {best_layer['peak_force']:.4f}N, baseline: {best_layer['baseline']:.4f}N)")
    
    return best_layer, eligible_layers, exposure_starts


def extract_layer_data(df, best_layer, exposure_starts):
    """
    Extract Exposure + Lift from selected layer, plus Pause from next layer.
    """
    layer_num = best_layer['layer_number']
    
    # Get exposure start for selected layer
    exposure_start = exposure_starts[layer_num]
    
    # Find where lift phase ends (pause begins) in selected layer
    layer_data = df.iloc[best_layer['start_idx']:best_layer['end_idx']]
    lift_rows = layer_data[layer_data['Phase'] == 'Lift']
    
    if len(lift_rows) == 0:
        print(f"  [ERROR] No lift phase found in selected layer")
        return None
    
    # Find last index of lift phase in selected layer
    lift_end_idx = lift_rows.index[-1]
    
    # Now get pause from NEXT layer
    next_layer_num = layer_num + 1
    if next_layer_num < len(exposure_starts):
        next_exposure_start = exposure_starts[next_layer_num]
        
        # Extract pause data from next layer (from its start until its exposure begins)
        # Actually, the pause is BEFORE the exposure in the next layer
        # So we need to find where the next layer's exposure actually starts
        
        # Get data from end of current lift until next exposure
        next_layer_data = df.iloc[lift_end_idx+1:next_exposure_start]
        
        # This should be the pause phase
        pause_data = next_layer_data[next_layer_data['Phase'] == 'Pause']
        
        if len(pause_data) > 0:
            final_end_idx = pause_data.index[-1]
            print(f"  Including pause from next layer (layer {next_layer_num})")
        else:
            # No pause found, just use next exposure start
            final_end_idx = next_exposure_start - 1
            print(f"  [WARNING] No pause found in next layer, using exposure start")
    else:
        # No next layer, just extract to end of current layer
        final_end_idx = best_layer['end_idx'] - 1
        print(f"  [INFO] No next layer, using end of current layer")
    
    # Extract full cycle: Exposure → Lift → Pause
    cycle_df = df.loc[exposure_start:final_end_idx, ['Time', 'Position', 'Force', 'Phase']].copy()
    
    # Calculate lift start time (relative to exposure start)
    lift_start_time = df.loc[best_layer['lift_start_idx'], 'Time'] - df.loc[exposure_start, 'Time']
    
    # Reset time to 0
    cycle_df['Time'] = cycle_df['Time'] - cycle_df['Time'].iloc[0]
    
    # Add metadata columns
    cycle_df['Lift_Start_Time'] = lift_start_time
    cycle_df['Baseline_Force'] = best_layer['baseline']
    
    print(f"  Extracted data from index {exposure_start} to {final_end_idx}")
    print(f"  Total points: {len(cycle_df)}")
    print(f"  Time range: 0.000s to {cycle_df['Time'].iloc[-1]:.3f}s")
    print(f"  Lift start time (relative): {lift_start_time:.3f}s")
    
    # Print phase breakdown
    phase_counts = cycle_df['Phase'].value_counts()
    print(f"  Phase breakdown:")
    for phase in ['Exposure', 'Lift', 'Pause']:
        if phase in phase_counts:
            phase_time = cycle_df[cycle_df['Phase'] == phase]['Time'].iloc[-1] - cycle_df[cycle_df['Phase'] == phase]['Time'].iloc[0] if phase in phase_counts else 0
            print(f"    {phase}: {phase_counts[phase]} points, ~{phase_time:.1f}s")
    
    return cycle_df


def process_folder(folder_path):
    """
    Process autolog_L45-L49.csv in the given folder.
    Returns (folder_name, cycle_dataframe) or None if file not found/error.
    """
    # Look for autolog_L45-L49.csv specifically
    csv_file = folder_path / "autolog_L45-L49.csv"
    
    if not csv_file.exists():
        print(f"  [SKIP] autolog_L45-L49.csv not found")
        return None
    
    print(f"  Reading: {csv_file.name}")
    
    try:
        df = pd.read_csv(csv_file)
        
        # Find highest relative peak layer
        result = find_highest_relative_peak_layer(df)
        if result is None:
            return None
        
        best_layer, eligible_layers, exposure_starts = result
        
        # Extract the data
        cycle_data = extract_layer_data(df, best_layer, exposure_starts)
        
        if cycle_data is None:
            return None
        
        folder_name = folder_path.name
        return (folder_name, cycle_data)
        
    except Exception as e:
        print(f"  [ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Extract peak layer data using Phase column from autolog files"
    )
    parser.add_argument(
        '--root',
        type=str,
        required=True,
        help='Root folder containing material subfolders'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='peak_layer_from_phase.csv',
        help='Output CSV filename (default: peak_layer_from_phase.csv)'
    )
    
    args = parser.parse_args()
    
    root_path = Path(args.root)
    
    if not root_path.exists():
        print(f"[ERROR] Root path does not exist: {root_path}")
        sys.exit(1)
    
    print("=" * 80)
    print("PEAK LAYER DATA EXTRACTION - USING PHASE COLUMN")
    print("=" * 80)
    print(f"Root folder: {root_path}")
    output_path = root_path / args.output
    print(f"Output file: {output_path}")
    print("=" * 80)
    
    # Get all subdirectories
    folders = sorted([f for f in root_path.iterdir() if f.is_dir()])
    
    if not folders:
        print(f"[ERROR] No subfolders found in {root_path}")
        sys.exit(1)
    
    # Process each folder
    folder_data_list = []
    
    for folder in folders:
        print(f"\nProcessing: {folder.name}")
        result = process_folder(folder)
        if result is not None:
            folder_data_list.append(result)
    
    if not folder_data_list:
        print("\n[ERROR] No data extracted from any folder")
        sys.exit(1)
    
    # Combine all data into single CSV
    # Pad to max length
    lengths = [len(data) for _, data in folder_data_list]
    max_rows = max(lengths)
    min_rows = min(lengths)
    
    print(f"\n[INFO] Cycle lengths: {min_rows} to {max_rows} points")
    
    # Build combined dataframe
    combined_df = pd.DataFrame()
    
    for folder_name, cycle_data in folder_data_list:
        # Pad with NaN if this cycle is shorter than max
        padded_data = cycle_data.copy()
        if len(padded_data) < max_rows:
            padding = pd.DataFrame(
                np.nan, 
                index=range(len(padded_data), max_rows),
                columns=padded_data.columns
            )
            padded_data = pd.concat([padded_data, padding], ignore_index=True)
        
        # Rename columns with folder prefix
        padded_data.columns = [f"{folder_name}_{col}" for col in padded_data.columns]
        
        # Add to combined dataframe
        combined_df = pd.concat([combined_df, padded_data], axis=1)
    
    # Save to CSV
    combined_df.to_csv(output_path, index=False)
    
    print("\n" + "=" * 80)
    print(f"Successfully processed {len(folder_data_list)} folder(s)")
    print("=" * 80)
    print(f"\n[OK] Saved combined data to: {output_path}")
    print(f"     Max cycle length: {max_rows} points")
    print(f"     Total columns: {len(combined_df.columns)}")
    
    print("\n[SUCCESS] Extraction complete!")


if __name__ == '__main__':
    main()
