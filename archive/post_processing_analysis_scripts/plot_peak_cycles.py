"""
Plot peak cycle data for non-continuous files.
Time vs Force with logarithmic Y-axis.
PFPE: solid lines, PDMS: dashed lines.
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import argparse


def plot_peak_cycles(csv_path, output_path=None, apply_smoothing=True, 
                     median_kernel=93, savgol_window=153, normalize_baseline=True,
                     baseline_window=0.1, use_log_scale=True):
    """
    Plot Time vs Force for non-continuous files.
    
    Args:
        csv_path: Path to peak_cycle_continuous.csv
        output_path: Optional path to save figure
        apply_smoothing: Apply heavy smoothing (3x standard)
        median_kernel: Median filter kernel size
        savgol_window: Savitzky-Golay window size
        normalize_baseline: Show relative force (subtract pre-lift baseline)
        baseline_window: Not used anymore (kept for compatibility)
        use_log_scale: Use logarithmic Y-axis (default: True)
    """
    from scipy.signal import medfilt, savgol_filter
    
    # Read the CSV
    df = pd.read_csv(csv_path)
    
    # Get all folder names (column names ending with _Time)
    time_columns = [col for col in df.columns if col.endswith('_Time')]
    folder_names = [col.replace('_Time', '') for col in time_columns]
    
    # Filter out metadata columns and continuous files
    folder_names = [name for name in folder_names 
                   if not name.endswith('_Lift_Start') 
                   and not name.endswith('_Baseline')
                   and 'Continuous' not in name]
    non_continuous_folders = folder_names
    
    print(f"Found {len(non_continuous_folders)} non-continuous folders:")
    for name in non_continuous_folders:
        print(f"  - {name}")
    
    if apply_smoothing:
        print(f"\nApplying HEAVY smoothing: median={median_kernel}, SG window={savgol_window}")
    
    if normalize_baseline:
        print(f"Calculating relative force (force - baseline at lift start)")
    
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 7))
    
    # Track global min for offset calculation
    global_min = 0
    
    # Store processed data
    processed_data = {}
    
    # First pass: process all data, calculate baselines
    for folder in non_continuous_folders:
        time_col = f"{folder}_Time"
        position_col = f"{folder}_Position"
        force_col = f"{folder}_Force"
        lift_start_time_col = f"{folder}_Lift_Start_Time"
        baseline_col = f"{folder}_Baseline_Force"
        
        time_data = df[time_col].dropna().values
        position_data = df[position_col].dropna().values
        force_data = df[force_col].dropna().values
        
        # Try to read lift start time and baseline from CSV metadata columns
        if lift_start_time_col in df.columns:
            lift_start_time = df[lift_start_time_col].dropna().iloc[0]
            baseline = df[baseline_col].dropna().iloc[0]
            lift_start_idx = np.argmin(np.abs(time_data - lift_start_time))
            print(f"  {folder}: Using saved lift start time = {lift_start_time:.3f}s, baseline = {baseline:.6f}N")
        else:
            # Fallback: calculate from position data
            pos_diff = np.diff(position_data)
            motion_threshold = 0.001  # mm
            
            lift_start_idx = 0
            for i in range(len(pos_diff) - 5):
                window = pos_diff[i:i+5]
                if np.sum(window > motion_threshold) >= 4:
                    lift_start_idx = i
                    break
            
            # Calculate baseline as force right before lift starts (average 10 points before)
            baseline_start = max(0, lift_start_idx - 10)
            baseline = np.mean(force_data[baseline_start:lift_start_idx]) if lift_start_idx > 0 else force_data[0]
        
        # Apply smoothing if requested
        if apply_smoothing:
            mk = min(median_kernel if median_kernel % 2 == 1 else median_kernel + 1, 
                    len(force_data) if len(force_data) % 2 == 1 else len(force_data) - 1)
            sw = min(savgol_window if savgol_window % 2 == 1 else savgol_window + 1,
                    len(force_data) if len(force_data) % 2 == 1 else len(force_data) - 1)
            
            force_data = medfilt(force_data, kernel_size=mk)
            force_data = savgol_filter(force_data, window_length=sw, polyorder=3)
        
        processed_data[folder] = {
            'time': time_data,
            'force': force_data,
            'baseline': baseline,
            'lift_start_idx': lift_start_idx
        }
        
        # Track minimum for log scale offset
        if normalize_baseline:
            relative_force = force_data - baseline
            global_min = min(global_min, relative_force.min())
        else:
            global_min = min(global_min, force_data.min())
    
    # Calculate offset to ensure all values are positive (only needed for log scale)
    offset = 0
    if use_log_scale and global_min < 0:
        offset = abs(global_min) + 1e-6
    
    if normalize_baseline:
        print(f"\nBaseline (pre-lift force) values:")
        for folder, data in processed_data.items():
            print(f"  {folder}: {data['baseline']:.6f}N at t={data['time'][data['lift_start_idx']]:.3f}s")
    
    if offset > 0:
        print(f"\n[INFO] Adding offset of {offset:.6f}N to ensure positive forces for log scale")
    
    # Second pass: plot with baseline subtraction
    colors = {}
    for idx, folder in enumerate(non_continuous_folders):
        time_data = processed_data[folder]['time']
        force_data = processed_data[folder]['force'].copy()
        
        # Apply baseline subtraction if requested
        if normalize_baseline:
            force_data = force_data - processed_data[folder]['baseline']
        
        # Add offset if needed
        force_data = force_data + offset
        
        # Determine line style
        if 'PFPE' in folder:
            linestyle = '-'  # Solid for PFPE
        else:  # PDMS
            linestyle = '--'  # Dashed for PDMS
        
        # Plot with bolder lines
        line = ax.plot(time_data, force_data, 
                linestyle=linestyle, 
                linewidth=2.5,
                label=folder,
                alpha=0.85)
        
        # Store color for lift start marker
        colors[folder] = line[0].get_color()
        
    # Mark lift start times
    for folder in non_continuous_folders:
        lift_start_time = processed_data[folder]['time'][processed_data[folder]['lift_start_idx']]
        ax.axvline(x=lift_start_time, color=colors[folder], linestyle=':', 
                   linewidth=1.5, alpha=0.6, label=f'{folder} lift start')
    
    # Formatting
    ax.set_xlabel('Time (s)', fontsize=12, fontweight='bold')
    
    ylabel = 'Force (N)'
    if normalize_baseline:
        ylabel = 'Relative Force (N) [Force - Pre-lift Baseline]'
    if offset > 0:
        ylabel += f' + {offset:.1e}'
    
    ax.set_ylabel(ylabel, fontsize=12, fontweight='bold')
    
    if use_log_scale:
        ax.set_yscale('log')  # Logarithmic Y-axis
    
    ax.grid(True, alpha=0.3, which='both' if use_log_scale else 'major')
    ax.legend(loc='best', framealpha=0.9, fontsize=10)
    
    title = 'Peak Cycle Force Profiles - Non-Continuous Files'
    if apply_smoothing:
        title += ' (Heavy Smoothing)'
    if normalize_baseline:
        title += ' [Relative to Pre-lift Baseline]'
    if not use_log_scale:
        title += ' - Linear Scale'
    ax.set_title(title, fontsize=14, fontweight='bold', pad=15)
    
    plt.tight_layout()
    
    # Save or show
    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"\n[SUCCESS] Plot saved to: {output_path}")
    else:
        plt.show()
    
    return fig, ax


def main():
    parser = argparse.ArgumentParser(description='Plot peak cycle data for non-continuous files')
    parser.add_argument('--csv', type=str, 
                        default='peak_cycle_continuous.csv',
                        help='Path to CSV file (default: peak_cycle_continuous.csv in current dir)')
    parser.add_argument('--output', type=str, 
                        default='peak_cycles_comparison.png',
                        help='Output plot filename (default: peak_cycles_comparison.png)')
    parser.add_argument('--show', action='store_true',
                        help='Show plot instead of saving')
    parser.add_argument('--smooth', action='store_true',
                        help='Apply heavy smoothing (3x standard: median=93, SG=153)')
    parser.add_argument('--median', type=int, default=93,
                        help='Median filter kernel size (default: 93)')
    parser.add_argument('--savgol', type=int, default=153,
                        help='Savitzky-Golay window size (default: 153)')
    parser.add_argument('--normalize', action='store_true',
                        help='Normalize all baselines to common value (default: enabled with --smooth)')
    parser.add_argument('--no-normalize', action='store_true',
                        help='Disable baseline normalization')
    parser.add_argument('--baseline-window', type=float, default=0.1,
                        help='Fraction of early data for baseline calculation (default: 0.1)')
    parser.add_argument('--linear', action='store_true',
                        help='Use linear Y-axis instead of logarithmic')
    
    args = parser.parse_args()
    
    # Default: normalize when smoothing unless explicitly disabled
    normalize = args.normalize or (args.smooth and not args.no_normalize)
    
    # Check if CSV exists
    csv_path = Path(args.csv)
    if not csv_path.exists():
        # Try looking in ToProcess folder
        alt_path = Path(r"C:\Users\cheng sun\BoyuanSun\Slicing\Evan\10SqmmCylinder\Printing_Logs\ToProcess") / args.csv
        if alt_path.exists():
            csv_path = alt_path
        else:
            print(f"[ERROR] CSV file not found: {args.csv}")
            print(f"[ERROR] Also checked: {alt_path}")
            return
    
    print(f"Reading data from: {csv_path}")
    
    # Plot
    output_path = None if args.show else str(csv_path.parent / args.output)
    plot_peak_cycles(str(csv_path), output_path, 
                    apply_smoothing=args.smooth,
                    median_kernel=args.median,
                    savgol_window=args.savgol,
                    normalize_baseline=normalize,
                    baseline_window=args.baseline_window,
                    use_log_scale=not args.linear)


if __name__ == '__main__':
    main()
