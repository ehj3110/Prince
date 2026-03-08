"""
Plot Peak Cycles with Synchronized Lift Start Times
===================================================

Modified version of plot_peak_cycles.py that can synchronize lift start times
across all curves.

Author: Cheng Sun Lab Team
Date: February 10, 2026
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import argparse


def plot_peak_cycles_synced(csv_path, output_path, apply_smoothing=True, 
                           sync_lift=True, show_lift_markers=False):
    """
    Plot Time vs Force with synchronized lift start times.
    
    Args:
        csv_path: Path to extracted CSV file
        output_path: Path to save figure
        apply_smoothing: Apply heavy smoothing
        sync_lift: Synchronize all lift starts to same time
        show_lift_markers: Show vertical lines at lift start
    """
    from scipy.signal import medfilt, savgol_filter
    
    # Read the CSV
    df = pd.read_csv(csv_path)
    
    # Get all folder names (column names ending with _Time)
    all_columns = df.columns.tolist()
    folders = sorted(list(set([col.split('_Time')[0] for col in all_columns if '_Time' in col])))
    
    # Filter out continuous folders
    non_continuous_folders = [f for f in folders if 'Continuous' not in f]
    
    print(f"Found {len(non_continuous_folders)} non-continuous folders:")
    for f in non_continuous_folders:
        print(f"  - {f}")
    
    # Process each folder's data
    processed_data = {}
    
    for folder in non_continuous_folders:
        time_col = f"{folder}_Time"
        force_col = f"{folder}_Force"
        lift_start_time_col = f"{folder}_Lift_Start_Time"
        baseline_col = f"{folder}_Baseline_Force"
        
        if time_col not in df.columns or force_col not in df.columns:
            print(f"[SKIP] {folder}: Missing required columns")
            continue
        
        # Extract data
        time_data = df[time_col].values
        force_data = df[force_col].values
        
        # Remove NaN
        valid_mask = ~(np.isnan(time_data) | np.isnan(force_data))
        time_data = time_data[valid_mask]
        force_data = force_data[valid_mask]
        
        if len(time_data) == 0:
            print(f"[SKIP] {folder}: No valid data")
            continue
        
        # Get lift start time and baseline from metadata
        if lift_start_time_col in df.columns:
            lift_start_time = df[lift_start_time_col].dropna().iloc[0]
            baseline = df[baseline_col].dropna().iloc[0]
            print(f"  {folder}: lift start = {lift_start_time:.3f}s, baseline = {baseline:.6f}N")
        else:
            lift_start_time = 0
            baseline = force_data[:10].mean()
            print(f"  {folder}: Using calculated baseline = {baseline:.6f}N")
        
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
        
        processed_data[folder] = {
            'time': time_data,
            'force': force_data,
            'baseline': baseline,
            'lift_start_time': lift_start_time
        }
    
    if not processed_data:
        print("[ERROR] No data to plot")
        return
    
    # Create plot
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # If syncing lift, use first folder as reference
    if sync_lift:
        reference_lift_time = processed_data[non_continuous_folders[0]]['lift_start_time']
        print(f"\nSynchronizing lift starts to t={reference_lift_time:.3f}s")
    
    colors = {}
    
    # Plot each folder
    for folder in non_continuous_folders:
        if folder not in processed_data:
            continue
        
        time_data = processed_data[folder]['time'].copy()
        force_data = processed_data[folder]['force'].copy()
        
        # Synchronize lift start if requested
        if sync_lift:
            time_shift = reference_lift_time - processed_data[folder]['lift_start_time']
            time_data = time_data + time_shift
            print(f"  {folder}: shifted by {time_shift:+.3f}s")
        
        # Determine line style
        if 'PDMS' in folder and 'V2' not in folder:
            linestyle = '--'
        else:
            linestyle = '-'
        
        # Plot
        line = ax.plot(time_data, force_data, linestyle=linestyle, linewidth=2.5, 
                      label=folder, alpha=0.8)
        colors[folder] = line[0].get_color()
    
    # Mark lift start times (if requested)
    if show_lift_markers:
        for folder in non_continuous_folders:
            if folder not in processed_data:
                continue
            
            if sync_lift:
                lift_time = reference_lift_time
            else:
                lift_time = processed_data[folder]['lift_start_time']
            
            ax.axvline(x=lift_time, color=colors[folder], linestyle=':', 
                      linewidth=1.5, alpha=0.6)
    
    # Format plot
    ax.set_xlabel('Time (s)', fontsize=14, fontweight='bold')
    ax.set_ylabel('Relative Force (N)', fontsize=14, fontweight='bold')
    ax.set_title('Peak Cycle Comparison - Synchronized Lift Start (Linear Scale)', 
                fontsize=16, fontweight='bold')
    ax.legend(fontsize=12, loc='best')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"\n[SUCCESS] Plot saved to: {output_path}")
    else:
        plt.show()


def main():
    parser = argparse.ArgumentParser(
        description="Plot peak cycles with synchronized lift start times"
    )
    parser.add_argument('--csv', type=str, required=True,
                       help='Path to CSV file')
    parser.add_argument('--output', type=str, required=True,
                       help='Output plot filename')
    parser.add_argument('--smooth', action='store_true',
                       help='Apply heavy smoothing')
    parser.add_argument('--sync-lift', action='store_true',
                       help='Synchronize lift start times')
    parser.add_argument('--show-lift-markers', action='store_true',
                       help='Show vertical lines at lift start')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("SYNCHRONIZED PEAK CYCLE PLOTTING")
    print("=" * 80)
    print(f"CSV: {args.csv}")
    print(f"Output: {args.output}")
    print(f"Smoothing: {'HEAVY' if args.smooth else 'NONE'}")
    print(f"Sync lift: {args.sync_lift}")
    print(f"Show lift markers: {args.show_lift_markers}")
    print("=" * 80)
    
    plot_peak_cycles_synced(args.csv, args.output, 
                           apply_smoothing=args.smooth,
                           sync_lift=args.sync_lift,
                           show_lift_markers=args.show_lift_markers)


if __name__ == '__main__':
    main()
