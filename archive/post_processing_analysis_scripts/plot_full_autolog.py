"""
Plot Full Autolog Files with Smoothing
======================================

Plots the entire autolog_L45-L49.csv file for each dataset with heavy smoothing.

Author: Cheng Sun Lab Team
Date: February 10, 2026
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from scipy.signal import medfilt, savgol_filter
import argparse


def apply_smoothing(data, heavy=True):
    """Apply smoothing to force data."""
    if heavy:
        median_kernel = 93
        sg_window = 153
        sg_order = 3
        print(f"  Applying HEAVY smoothing: median={median_kernel}, SG window={sg_window}")
    else:
        median_kernel = 31
        sg_window = 51
        sg_order = 3
        print(f"  Applying standard smoothing: median={median_kernel}, SG window={sg_window}")
    
    # Apply median filter
    if len(data) >= median_kernel:
        data = medfilt(data, kernel_size=median_kernel)
    
    # Apply Savitzky-Golay filter
    if len(data) >= sg_window:
        data = savgol_filter(data, window_length=sg_window, polyorder=sg_order)
    
    return data


def main():
    parser = argparse.ArgumentParser(
        description="Plot full autolog files with smoothing"
    )
    parser.add_argument('--root', type=str, required=True,
                        help='Root folder containing material subfolders')
    parser.add_argument('--output', type=str, default='full_autolog_smoothed.png',
                        help='Output plot filename')
    parser.add_argument('--smooth', action='store_true',
                        help='Apply heavy smoothing')
    
    args = parser.parse_args()
    
    root_path = Path(args.root)
    output_path = root_path / args.output
    
    print("=" * 80)
    print("FULL AUTOLOG FILE PLOTTING")
    print("=" * 80)
    print(f"Root folder: {root_path}")
    print(f"Output: {output_path}")
    print(f"Smoothing: {'HEAVY' if args.smooth else 'NONE'}")
    print("=" * 80)
    
    folders = sorted([f for f in root_path.iterdir() if f.is_dir()])
    folders = [f for f in folders if 'Continuous' not in f.name]
    
    fig, ax = plt.subplots(figsize=(14, 8))
    
    colors_used = {}
    
    for folder in folders:
        csv_file = folder / "autolog_L45-L49.csv"
        
        if not csv_file.exists():
            print(f"[SKIP] {folder.name}: autolog_L45-L49.csv not found")
            continue
        
        print(f"\nProcessing: {folder.name}")
        df = pd.read_csv(csv_file)
        
        # Standardize column names
        column_mapping = {}
        for col in df.columns:
            if 'time' in col.lower():
                column_mapping[col] = 'Time'
            elif 'force' in col.lower():
                column_mapping[col] = 'Force'
        
        df.rename(columns=column_mapping, inplace=True)
        
        if 'Time' not in df.columns or 'Force' not in df.columns:
            print(f"  [ERROR] Missing Time or Force column")
            continue
        
        time_data = df['Time'].values
        force_data = df['Force'].values
        
        # Remove NaN
        valid_mask = ~(np.isnan(time_data) | np.isnan(force_data))
        time_data = time_data[valid_mask]
        force_data = force_data[valid_mask]
        
        if len(time_data) == 0:
            print(f"  [ERROR] No valid data")
            continue
        
        # Reset time to start at 0
        time_data = time_data - time_data[0]
        
        print(f"  Data points: {len(time_data)}")
        print(f"  Duration: {time_data[-1]:.1f}s")
        print(f"  Force range: {force_data.min():.4f}N to {force_data.max():.4f}N")
        
        # Apply smoothing
        if args.smooth:
            force_data = apply_smoothing(force_data, heavy=True)
        
        # Plot
        line = ax.plot(time_data, force_data, linewidth=1.5, label=folder.name, alpha=0.8)
        colors_used[folder.name] = line[0].get_color()
        
        print(f"  [OK] Plotted {len(time_data)} points")
    
    # Format plot
    ax.set_xlabel('Time (s)', fontsize=14, fontweight='bold')
    ax.set_ylabel('Force (N)', fontsize=14, fontweight='bold')
    ax.set_title('Full Autolog Files (L45-L49) - All Layers', fontsize=16, fontweight='bold')
    ax.legend(fontsize=10, loc='best')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    
    print("\n" + "=" * 80)
    print(f"[SUCCESS] Plot saved to: {output_path}")
    print("=" * 80)


if __name__ == '__main__':
    main()
