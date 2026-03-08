"""
Export Processed Data for Custom Plotting
=========================================

Exports smoothed, synchronized, relative force data to CSV for custom plotting.

Author: Cheng Sun Lab Team
Date: February 10, 2026
"""

import pandas as pd
import numpy as np
from pathlib import Path
import argparse


def export_processed_data(csv_path, output_path, apply_smoothing=True, sync_lift=True):
    """
    Export processed data (smoothed, relative force, synchronized) to CSV.
    
    Args:
        csv_path: Path to extracted CSV file
        output_path: Path to save processed CSV
        apply_smoothing: Apply heavy smoothing
        sync_lift: Synchronize all lift starts to same time
    """
    from scipy.signal import medfilt, savgol_filter
    
    # Read the CSV
    df = pd.read_csv(csv_path)
    
    # Get all folder names (column names ending with _Time)
    all_columns = df.columns.tolist()
    folders = sorted(list(set([col.split('_Time')[0] for col in all_columns if '_Time' in col])))
    
    # Filter out continuous folders and metadata columns
    non_continuous_folders = [f for f in folders if 'Continuous' not in f and 'Lift_Start' not in f and 'Baseline' not in f]
    
    print(f"Processing {len(non_continuous_folders)} folders:")
    for f in non_continuous_folders:
        print(f"  - {f}")
    
    # Process each folder's data
    processed_data = {}
    max_length = 0
    
    for folder in non_continuous_folders:
        time_col = f"{folder}_Time"
        force_col = f"{folder}_Force"
        position_col = f"{folder}_Position"
        lift_start_time_col = f"{folder}_Lift_Start_Time"
        baseline_col = f"{folder}_Baseline_Force"
        
        if time_col not in df.columns or force_col not in df.columns:
            print(f"[SKIP] {folder}: Missing required columns")
            continue
        
        # Extract data (make copies to avoid modifying original)
        time_data = df[time_col].values.copy()
        force_data = df[force_col].values.copy()
        position_data = df[position_col].values.copy() if position_col in df.columns else None
        
        # Remove NaN
        if position_data is not None:
            valid_mask = ~(np.isnan(time_data) | np.isnan(force_data) | np.isnan(position_data))
        else:
            valid_mask = ~(np.isnan(time_data) | np.isnan(force_data))
        time_data = time_data[valid_mask]
        force_data = force_data[valid_mask]
        if position_data is not None:
            position_data = position_data[valid_mask]
        
        if len(time_data) == 0:
            print(f"[SKIP] {folder}: No valid data")
            continue
        
        # Get lift start time and baseline from metadata
        if lift_start_time_col in df.columns:
            lift_start_time = df[lift_start_time_col].dropna().iloc[0]
            baseline = df[baseline_col].dropna().iloc[0]
            print(f"  {folder}: lift={lift_start_time:.3f}s, baseline={baseline:.6f}N")
        else:
            lift_start_time = 0
            baseline = force_data[:10].mean()
            print(f"  {folder}: Calculated baseline={baseline:.6f}N")
        
        # Apply smoothing
        if apply_smoothing:
            median_kernel = 93
            sg_window = 153
            sg_order = 3
            
            if len(force_data) >= median_kernel:
                force_data = medfilt(force_data, kernel_size=median_kernel)
            
            if len(force_data) >= sg_window:
                force_data = savgol_filter(force_data, window_length=sg_window, polyorder=sg_order)
        
        # Calculate relative force (force - baseline)
        force_data = force_data - baseline
        
        # Synchronize lift start if requested
        if sync_lift and lift_start_time > 0:
            # Will sync after processing all folders
            pass
        
        processed_data[folder] = {
            'time': time_data,
            'force': force_data,
            'position': position_data,
            'lift_start_time': lift_start_time
        }
        
        max_length = max(max_length, len(time_data))
    
    if not processed_data:
        print("[ERROR] No data to export")
        return
    
    # Synchronize lift starts if requested
    if sync_lift:
        reference_lift_time = processed_data[list(processed_data.keys())[0]]['lift_start_time']
        print(f"\nSynchronizing to lift start = {reference_lift_time:.3f}s")
        
        for folder in processed_data.keys():
            time_shift = reference_lift_time - processed_data[folder]['lift_start_time']
            processed_data[folder]['time'] = processed_data[folder]['time'] + time_shift
            print(f"  {folder}: shifted by {time_shift:+.3f}s")
    
    # Create output DataFrame
    output_df = pd.DataFrame()
    
    for folder in sorted(processed_data.keys()):
        time_data = processed_data[folder]['time']
        force_data = processed_data[folder]['force']
        position_data = processed_data[folder]['position']
        
        # Pad with NaN to match max length
        if len(time_data) < max_length:
            time_padded = np.pad(time_data, (0, max_length - len(time_data)), 
                                constant_values=np.nan)
            force_padded = np.pad(force_data, (0, max_length - len(force_data)), 
                                 constant_values=np.nan)
            if position_data is not None:
                position_padded = np.pad(position_data, (0, max_length - len(position_data)), 
                                        constant_values=np.nan)
            else:
                position_padded = np.full(max_length, np.nan)
        else:
            time_padded = time_data
            force_padded = force_data
            position_padded = position_data if position_data is not None else np.full(len(time_data), np.nan)
        
        output_df[f"{folder}_Time_s"] = time_padded
        output_df[f"{folder}_Position_mm"] = position_padded
        output_df[f"{folder}_RelativeForce_N"] = force_padded
    
    # Save to CSV
    output_df.to_csv(output_path, index=False)
    
    print(f"\n[SUCCESS] Exported {len(output_df)} rows, {len(output_df.columns)} columns")
    print(f"[SUCCESS] Saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Export processed data for custom plotting"
    )
    parser.add_argument('--csv', type=str, required=True,
                       help='Path to extracted CSV file')
    parser.add_argument('--output', type=str, required=True,
                       help='Output CSV filename')
    parser.add_argument('--smooth', action='store_true',
                       help='Apply heavy smoothing')
    parser.add_argument('--sync-lift', action='store_true',
                       help='Synchronize lift start times')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("EXPORT PROCESSED DATA FOR PLOTTING")
    print("=" * 80)
    print(f"Input CSV: {args.csv}")
    print(f"Output CSV: {args.output}")
    print(f"Smoothing: {'HEAVY' if args.smooth else 'NONE'}")
    print(f"Sync lift: {args.sync_lift}")
    print("=" * 80)
    
    export_processed_data(args.csv, args.output, 
                         apply_smoothing=args.smooth,
                         sync_lift=args.sync_lift)


if __name__ == '__main__':
    main()
