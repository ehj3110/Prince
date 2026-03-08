"""
Analyze Peak Force and Propagation Time for All Layers
======================================================

Creates a table of peak force and propagation time for each layer in each dataset.

Propagation time = time from peak force until force returns to baseline.

Author: Cheng Sun Lab Team
Date: February 10, 2026
"""

import pandas as pd
import numpy as np
from pathlib import Path
from scipy.signal import medfilt, savgol_filter
import argparse


def apply_smoothing(data, heavy=True):
    """Apply smoothing to force data."""
    if heavy:
        median_kernel = 93
        sg_window = 153
        sg_order = 3
    else:
        median_kernel = 31
        sg_window = 51
        sg_order = 3
    
    # Apply median filter
    if len(data) >= median_kernel:
        data = medfilt(data, kernel_size=median_kernel)
    
    # Apply Savitzky-Golay filter
    if len(data) >= sg_window:
        data = savgol_filter(data, window_length=sg_window, polyorder=sg_order)
    
    return data


def analyze_layer(df, layer_number, smooth=True):
    """
    Analyze a specific layer for peak force and propagation time.
    
    Returns dict with:
        - peak_force: absolute peak force (N)
        - baseline: force before lift (N)
        - relative_peak: peak - baseline (N)
        - propagation_time: time from peak until return to baseline (s)
        - lift_start_time: when lift phase begins (s)
        - peak_time: when peak occurs (s)
    """
    # Standardize column names
    column_mapping = {}
    for col in df.columns:
        if 'phase' in col.lower():
            column_mapping[col] = 'Phase'
        elif 'time' in col.lower():
            column_mapping[col] = 'Time'
        elif 'force' in col.lower():
            column_mapping[col] = 'Force'
    
    df = df.rename(columns=column_mapping)
    
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
    
    layer_data = df.iloc[exposure_start:next_exposure_start].copy()
    
    # Find lift start
    lift_rows = layer_data[layer_data['Phase'] == 'Lift']
    if len(lift_rows) == 0:
        return None
    
    lift_start_idx = lift_rows.index[0]
    
    # Calculate baseline (10 points before lift)
    baseline_start = max(exposure_start, lift_start_idx - 10)
    baseline = df.loc[baseline_start:lift_start_idx-1, 'Force'].mean()
    
    # Get time and force data for this layer
    time_data = layer_data['Time'].values
    force_data = layer_data['Force'].values
    
    # Apply smoothing if requested
    if smooth:
        force_data = apply_smoothing(force_data, heavy=True)
    
    # Find peak force
    peak_idx = np.argmax(force_data)
    peak_force = force_data[peak_idx]
    peak_time = time_data[peak_idx]
    
    relative_peak = peak_force - baseline
    
    # Calculate lift start time
    lift_start_time = df.loc[lift_start_idx, 'Time']
    
    # Calculate propagation time (time from peak until return to baseline)
    # Define "return to baseline" as when force drops below baseline + 5% of relative peak
    threshold = baseline + 0.05 * relative_peak
    
    propagation_time = None
    
    # Look at data after the peak
    if peak_idx < len(force_data) - 1:
        post_peak_force = force_data[peak_idx:]
        post_peak_time = time_data[peak_idx:]
        
        # Find first point where force drops below threshold
        below_threshold = post_peak_force < threshold
        
        if np.any(below_threshold):
            return_idx = np.argmax(below_threshold)
            return_time = post_peak_time[return_idx]
            propagation_time = return_time - peak_time
        else:
            # Force never returns to baseline in this layer
            propagation_time = time_data[-1] - peak_time
    
    return {
        'layer_number': layer_number,
        'peak_force': peak_force,
        'baseline': baseline,
        'relative_peak': relative_peak,
        'propagation_time': propagation_time,
        'lift_start_time': lift_start_time,
        'peak_time': peak_time
    }


def main():
    parser = argparse.ArgumentParser(
        description="Analyze peak force and propagation time for all layers"
    )
    parser.add_argument('--root', type=str, required=True,
                        help='Root folder containing material subfolders')
    parser.add_argument('--output', type=str, default='layer_analysis_table.csv',
                        help='Output CSV filename')
    parser.add_argument('--smooth', action='store_true',
                        help='Apply heavy smoothing before analysis')
    
    args = parser.parse_args()
    
    root_path = Path(args.root)
    output_path = root_path / args.output
    
    print("=" * 80)
    print("LAYER ANALYSIS - PEAK FORCE AND PROPAGATION TIME")
    print("=" * 80)
    print(f"Root folder: {root_path}")
    print(f"Output: {output_path}")
    print(f"Smoothing: {'HEAVY' if args.smooth else 'NONE'}")
    print("=" * 80)
    
    folders = sorted([f for f in root_path.iterdir() if f.is_dir()])
    folders = [f for f in folders if 'Continuous' not in f.name]
    
    results = []
    
    for folder in folders:
        csv_file = folder / "autolog_L45-L49.csv"
        
        if not csv_file.exists():
            print(f"[SKIP] {folder.name}: autolog_L45-L49.csv not found")
            continue
        
        print(f"\nProcessing: {folder.name}")
        df = pd.read_csv(csv_file)
        
        # Find number of layers
        column_mapping = {}
        for col in df.columns:
            if 'phase' in col.lower():
                column_mapping[col] = 'Phase'
        
        df_temp = df.rename(columns=column_mapping)
        
        if 'Phase' not in df_temp.columns:
            print(f"  [ERROR] No Phase column")
            continue
        
        exposure_starts = []
        prev_phase = None
        
        for idx, phase in enumerate(df_temp['Phase']):
            if phase == 'Exposure' and prev_phase != 'Exposure':
                exposure_starts.append(idx)
            prev_phase = phase
        
        num_layers = len(exposure_starts)
        print(f"  Found {num_layers} layers")
        
        # Analyze each layer
        for layer_num in range(num_layers):
            result = analyze_layer(df, layer_num, smooth=args.smooth)
            
            if result is None:
                print(f"    Layer {layer_num}: [ERROR] Could not analyze")
                continue
            
            print(f"    Layer {layer_num}: Peak={result['relative_peak']:.4f}N, "
                  f"Propagation={result['propagation_time']:.3f}s" if result['propagation_time'] else "N/A")
            
            results.append({
                'Material': folder.name,
                'Layer': layer_num,
                'Absolute_Peak_Force_N': result['peak_force'],
                'Baseline_Force_N': result['baseline'],
                'Relative_Peak_Force_N': result['relative_peak'],
                'Lift_Start_Time_s': result['lift_start_time'],
                'Peak_Time_s': result['peak_time'],
                'Propagation_Time_s': result['propagation_time']
            })
    
    # Create DataFrame and save
    if results:
        results_df = pd.DataFrame(results)
        results_df.to_csv(output_path, index=False)
        
        print("\n" + "=" * 80)
        print(f"[SUCCESS] Analyzed {len(results)} layers across {len(folders)} materials")
        print(f"[SUCCESS] Table saved to: {output_path}")
        print("=" * 80)
        
        # Print summary
        print("\nSUMMARY:")
        print(results_df.to_string(index=False))
    else:
        print("\n[ERROR] No results to save")


if __name__ == '__main__':
    main()
