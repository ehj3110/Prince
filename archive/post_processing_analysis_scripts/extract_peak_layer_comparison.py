"""
Extract Peak Layer Data for Comparison
======================================

Extracts time, position, and force data from the layer with the most prominent
force peak in autolog_L45-L49.csv files across multiple material folders.

Output: A single CSV where each folder's data is in separate columns
(FolderName_Time, FolderName_Position, FolderName_Force)

Author: Cheng Sun Lab Team
Date: February 6, 2026
"""

import pandas as pd
import numpy as np
from pathlib import Path
import argparse
import sys


def detect_layer_boundaries(df):
    """
    Detect layer boundaries using Phase column or motion profile.
    Returns list of (start_idx, end_idx, layer_num) tuples.
    """
    boundaries = []
    
    # Method 1: Use Phase column if available
    if 'Phase' in df.columns:
        phase = df['Phase'].values
        in_layer = False
        start_idx = None
        layer_count = 0
        
        for i, p in enumerate(phase):
            if not in_layer and p in ['Exposure', 'Lift', 'Pause']:
                in_layer = True
                start_idx = i
                layer_count += 1
            elif in_layer and (p not in ['Exposure', 'Lift', 'Pause'] or i == len(phase) - 1):
                end_idx = i if i == len(phase) - 1 else i - 1
                boundaries.append((start_idx, end_idx, layer_count))
                in_layer = False
        
        if boundaries:
            return boundaries
    
    # Method 2: Motion profile analysis (fallback)
    position = df['Position'].values
    pos_diff = np.diff(position)
    
    # Find upward motion starts (lifting)
    lift_starts = []
    for i in range(1, len(pos_diff) - 5):
        if pos_diff[i] > 0.01 and np.mean(pos_diff[i:i+5]) > 0.01:
            lift_starts.append(i)
    
    # Group into layers
    if len(lift_starts) > 0:
        layer_count = 0
        for i, lift_idx in enumerate(lift_starts):
            layer_count += 1
            start_idx = max(0, lift_idx - 100)
            
            if i < len(lift_starts) - 1:
                end_idx = lift_starts[i + 1] - 1
            else:
                end_idx = len(df) - 1
            
            boundaries.append((start_idx, end_idx, layer_count))
    
    return boundaries


def find_peak_layer(df, boundaries):
    """
    Find the layer with the highest force peak.
    If highest is the last layer, return second highest instead.
    
    Returns (start_idx, end_idx, layer_num, peak_force)
    """
    if not boundaries:
        return None
    
    force = df['Force'].values
    layer_peaks = []
    
    for start_idx, end_idx, layer_num in boundaries:
        layer_force = force[start_idx:end_idx+1]
        peak_force = np.max(layer_force)
        layer_peaks.append((start_idx, end_idx, layer_num, peak_force))
    
    # Sort by peak force (descending)
    layer_peaks.sort(key=lambda x: x[3], reverse=True)
    
    # If highest is last layer, use second highest
    if len(layer_peaks) > 1 and layer_peaks[0][2] == boundaries[-1][2]:
        print(f"  Highest peak is in last layer (L{layer_peaks[0][2]}), using second highest (L{layer_peaks[1][2]})")
        return layer_peaks[1]
    else:
        print(f"  Peak layer: L{layer_peaks[0][2]} with peak force {layer_peaks[0][3]:.4f}N")
        return layer_peaks[0]


def extract_layer_data(df, start_idx, end_idx):
    """
    Extract time, position, and force data for specified layer.
    """
    layer_df = df.iloc[start_idx:end_idx+1][['Time', 'Position', 'Force']].copy()
    
    # Reset time to start from 0 for this layer
    layer_df['Time'] = layer_df['Time'] - layer_df['Time'].iloc[0]
    
    return layer_df


def process_folder(folder_path):
    """
    Process autolog_L45-L49.csv in the given folder.
    Returns (folder_name, layer_dataframe) or None if file not found/error.
    """
    csv_file = folder_path / "autolog_L45-L49.csv"
    
    if not csv_file.exists():
        print(f"  [SKIP] autolog_L45-L49.csv not found")
        return None
    
    try:
        df = pd.read_csv(csv_file)
        
        # Standardize column names (handle variations)
        column_mapping = {}
        for col in df.columns:
            if 'time' in col.lower():
                column_mapping[col] = 'Time'
            elif 'position' in col.lower():
                column_mapping[col] = 'Position'
            elif 'force' in col.lower():
                column_mapping[col] = 'Force'
            elif 'phase' in col.lower():
                column_mapping[col] = 'Phase'
        
        df.rename(columns=column_mapping, inplace=True)
        
        # Validate required columns
        required_cols = ['Time', 'Position', 'Force']
        if not all(col in df.columns for col in required_cols):
            print(f"  [ERROR] Missing required columns. Found: {df.columns.tolist()}")
            return None
        
        # Detect layer boundaries
        boundaries = detect_layer_boundaries(df)
        if not boundaries:
            print(f"  [ERROR] No layers detected")
            return None
        
        print(f"  Detected {len(boundaries)} layers")
        
        # Find peak layer
        peak_layer = find_peak_layer(df, boundaries)
        if not peak_layer:
            print(f"  [ERROR] Could not find peak layer")
            return None
        
        start_idx, end_idx, layer_num, peak_force = peak_layer
        
        # Extract data
        layer_data = extract_layer_data(df, start_idx, end_idx)
        
        folder_name = folder_path.name
        return (folder_name, layer_data)
        
    except Exception as e:
        print(f"  [ERROR] {e}")
        return None


def combine_and_save(folder_data_list, output_path):
    """
    Combine data from multiple folders into a single CSV.
    Each folder gets three columns: FolderName_Time, FolderName_Position, FolderName_Force
    """
    if not folder_data_list:
        print("\n[ERROR] No data to save")
        return False
    
    # Find the maximum number of rows needed
    max_rows = max(len(data) for _, data in folder_data_list)
    
    # Build combined dataframe
    combined_df = pd.DataFrame()
    
    for folder_name, layer_data in folder_data_list:
        # Pad with NaN if this layer is shorter than max
        padded_data = layer_data.copy()
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
    print(f"\n[OK] Saved combined data to: {output_path}")
    print(f"     Total rows: {max_rows}")
    print(f"     Total columns: {len(combined_df.columns)}")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Extract peak layer data from autolog_L45-L49.csv files for comparison"
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
        default=None,
        help='Output CSV file path (default: peak_layer_comparison.csv in root folder)'
    )
    
    args = parser.parse_args()
    
    root_path = Path(args.root)
    if not root_path.exists():
        print(f"[ERROR] Root folder not found: {root_path}")
        sys.exit(1)
    
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = root_path / "peak_layer_comparison.csv"
    
    print("=" * 80)
    print("PEAK LAYER DATA EXTRACTION")
    print("=" * 80)
    print(f"Root folder: {root_path}")
    print(f"Output file: {output_path}")
    print("=" * 80)
    
    # Find all subfolders with autolog_L45-L49.csv
    folder_data_list = []
    
    for folder in sorted(root_path.iterdir()):
        if not folder.is_dir():
            continue
        
        print(f"\nProcessing: {folder.name}")
        result = process_folder(folder)
        
        if result:
            folder_data_list.append(result)
            print(f"  [OK] Extracted {len(result[1])} data points")
    
    print("\n" + "=" * 80)
    print(f"Successfully processed {len(folder_data_list)} folder(s)")
    print("=" * 80)
    
    # Combine and save
    if combine_and_save(folder_data_list, output_path):
        print("\n[SUCCESS] Extraction complete!")
    else:
        print("\n[FAILED] Could not save output file")
        sys.exit(1)


if __name__ == "__main__":
    main()
