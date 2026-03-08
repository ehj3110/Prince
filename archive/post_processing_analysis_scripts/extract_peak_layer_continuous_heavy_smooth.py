"""
Extract Peak Layer Data for Continuous Motion Files - HEAVY SMOOTHING VERSION
=============================================================================

Same as extract_peak_layer_continuous.py but with TRIPLE the smoothing:
- Median filter: kernel = 93 (was 31)
- Savitzky-Golay: window = 153, order = 3 (was 51)

This aggressive smoothing helps eliminate negative force values for log plotting.

Author: Cheng Sun Lab Team
Date: February 10, 2026
"""

import pandas as pd
import numpy as np
from pathlib import Path
import argparse
import sys
from scipy.signal import find_peaks, medfilt, savgol_filter


def apply_heavy_smoothing(force_data, median_kernel=93, savgol_window=153, savgol_order=3):
    """
    Apply very aggressive smoothing to force data.
    Triple the smoothing parameters used in standard processing.
    """
    # Ensure odd kernel sizes
    if median_kernel % 2 == 0:
        median_kernel += 1
    if savgol_window % 2 == 0:
        savgol_window += 1
    
    # Ensure window is not larger than data
    median_kernel = min(median_kernel, len(force_data) if len(force_data) % 2 == 1 else len(force_data) - 1)
    savgol_window = min(savgol_window, len(force_data) if len(force_data) % 2 == 1 else len(force_data) - 1)
    
    # Ensure order is less than window
    savgol_order = min(savgol_order, savgol_window - 1)
    
    print(f"    Applying smoothing: median={median_kernel}, SG window={savgol_window}, order={savgol_order}")
    
    # Step 1: Median filter to remove outliers and spikes
    smoothed = medfilt(force_data, kernel_size=median_kernel)
    
    # Step 2: Savitzky-Golay filter for smooth curve
    smoothed = savgol_filter(smoothed, window_length=savgol_window, polyorder=savgol_order)
    
    return smoothed


def find_motion_cycles(position, force, min_peak_height=0.01, min_distance=100):
    """
    Find motion cycles by detecting force peaks and tracking back to motion start.
    
    Returns list of (start_idx, end_idx, peak_idx, peak_force) tuples.
    """
    # Find all significant force peaks
    peaks, properties = find_peaks(force, height=min_peak_height, distance=min_distance)
    
    if len(peaks) == 0:
        return []
    
    # Sort peaks by force magnitude to identify major cycles
    peak_forces = force[peaks]
    sorted_indices = np.argsort(peak_forces)[::-1]  # Descending order
    
    cycles = []
    
    for peak_idx in peaks[sorted_indices]:
        peak_force = force[peak_idx]
        
        # Search backwards from peak to find lift start (when position starts changing)
        lift_start_idx = find_lift_start(position, peak_idx)
        
        # Search forwards from peak to find propagation end (force drops to baseline)
        prop_end_idx = find_propagation_end(force, peak_idx, len(force) - 1)
        
        cycles.append((lift_start_idx, prop_end_idx, peak_idx, peak_force))
    
    return cycles


def find_lift_start(position, peak_idx, lookback_window=300):
    """
    Find when the stage starts moving by looking backwards from peak.
    Detects when position begins to increase consistently.
    """
    # Search window: up to 300 points before peak, or start of data
    search_start = max(0, peak_idx - lookback_window)
    
    # Get position data leading up to peak
    pos_segment = position[search_start:peak_idx+1]
    
    if len(pos_segment) < 10:
        return search_start
    
    # Calculate position derivative (rate of change)
    pos_diff = np.diff(pos_segment)
    
    # Find where position starts consistently increasing
    # Look for sustained positive motion (at least 5 consecutive increases)
    motion_threshold = 0.001  # mm - very small to catch gentle starts
    
    for i in range(len(pos_diff) - 5):
        # Check if next 5 points show consistent upward motion
        window = pos_diff[i:i+5]
        if np.sum(window > motion_threshold) >= 4:  # At least 4 of 5 points moving up
            return search_start + i
    
    # If no clear start found, use earliest point with any upward motion
    for i in range(len(pos_diff)):
        if pos_diff[i] > motion_threshold:
            return search_start + i
    
    # Fallback: go back a fixed amount from peak
    return max(0, peak_idx - 100)


def find_exposure_start(position, lift_start_idx, lookback_window=300):
    """
    Find the start of exposure phase (beginning of this layer's cycle).
    Looks backward from lift start to find when the previous cycle's motion ended.
    The exposure starts when position becomes stable after previous retraction.
    """
    # Search window: up to 300 points before lift start
    search_start = max(0, lift_start_idx - lookback_window)
    
    # Get position data leading up to lift start
    pos_segment = position[search_start:lift_start_idx]
    
    if len(pos_segment) < 10:
        return search_start
    
    # Calculate position changes
    pos_diff = np.abs(np.diff(pos_segment))
    
    # Find where position becomes stable (exposure phase)
    # Stable = very small changes for consecutive points
    stable_threshold = 0.0005  # mm - very small movement
    stable_count = 5  # Need 5 consecutive stable points
    
    # Search backward from lift start to find stable region
    for i in range(len(pos_diff) - stable_count, -1, -1):
        window = pos_diff[i:i+stable_count]
        if np.all(window < stable_threshold):
            # Found stable region (exposure phase)
            # Keep going back to find where it started (previous motion ended)
            for j in range(i, -1, -1):
                if pos_diff[j] > stable_threshold * 3:
                    # Previous motion found, exposure starts right after
                    return search_start + j + 1
            # If no previous motion found, start from beginning of search
            return search_start
    
    # If no clear stable region, use a modest lookback
    return max(0, lift_start_idx - 150)


def find_propagation_end(force, peak_idx, max_search_idx, threshold_factor=0.05):
    """
    Find propagation end by searching forward from peak until force drops
    to baseline + 5% of peak force.
    """
    peak_force = force[peak_idx]
    
    # Estimate baseline from region after peak (use median of latter portion)
    search_region = force[peak_idx:min(peak_idx + 200, max_search_idx)]
    if len(search_region) > 20:
        baseline = np.median(search_region[-20:])
    else:
        baseline = np.min(search_region)
    
    # Calculate threshold: baseline + 5% of corrected peak
    corrected_peak = peak_force - baseline
    threshold = baseline + (corrected_peak * threshold_factor)
    
    # Search forward from peak
    for i in range(peak_idx + 1, max_search_idx + 1):
        if force[i] <= threshold:
            return i
    
    # If never drops below threshold, use a fixed distance from peak
    return min(peak_idx + 150, max_search_idx)


def extract_highest_cycle_data(df):
    """
    Extract the complete layer cycle with the highest force peak.
    Extracts from exposure start through to propagation end.
    Applies HEAVY smoothing (3x standard parameters) to eliminate negatives.
    Returns DataFrame with Time, Position, Force columns (time reset to 0).
    """
    # Standardize column names
    column_mapping = {}
    for col in df.columns:
        if 'time' in col.lower():
            column_mapping[col] = 'Time'
        elif 'position' in col.lower():
            column_mapping[col] = 'Position'
        elif 'force' in col.lower():
            column_mapping[col] = 'Force'
    
    df.rename(columns=column_mapping, inplace=True)
    
    position = df['Position'].values
    force_raw = df['Force'].values
    time = df['Time'].values
    
    # Apply heavy smoothing to force data
    print("  Applying HEAVY smoothing (3x standard)...")
    force = apply_heavy_smoothing(force_raw)
    
    # Find all motion cycles using smoothed force
    cycles = find_motion_cycles(position, force)
    
    if not cycles:
        print(f"  [ERROR] No cycles detected")
        return None
    
    print(f"  Detected {len(cycles)} cycles")
    
    # Get the cycle with highest peak force (first in sorted list)
    lift_start, prop_end, peak_idx, peak_force = cycles[0]
    
    print(f"  Highest peak: {peak_force:.4f}N at index {peak_idx}")
    print(f"  Lift start: index {lift_start}")
    
    # Find exposure start (beginning of this layer, after previous cycle ended)
    exposure_start = find_exposure_start(position, lift_start)
    
    print(f"  Exposure start: index {exposure_start}")
    print(f"  Prop end: index {prop_end}")
    print(f"  Full layer: {prop_end - exposure_start + 1} points")
    print(f"  Time range: {time[exposure_start]:.3f}s to {time[prop_end]:.3f}s")
    print(f"  Total duration: {time[prop_end] - time[exposure_start]:.3f}s")
    
    # Extract the full layer data from exposure start to propagation end
    cycle_df = pd.DataFrame({
        'Time': time[exposure_start:prop_end+1] - time[exposure_start],
        'Position': position[exposure_start:prop_end+1],
        'Force': force[exposure_start:prop_end+1]  # Use smoothed force
    })
    
    # Check for negative values
    min_force = cycle_df['Force'].min()
    if min_force < 0:
        print(f"  [WARNING] Minimum force: {min_force:.6f}N (negative value found)")
    else:
        print(f"  Minimum force: {min_force:.6f}N")
    
    return cycle_df


def process_folder(folder_path, output_df, folder_name):
    """
    Process a single folder and add its data to output DataFrame.
    """
    print(f"\nProcessing: {folder_name}")
    
    # Look for autolog CSV files
    csv_files = list(folder_path.glob("autolog*.csv"))
    
    if not csv_files:
        print(f"  [SKIP] No autolog CSV files found")
        return False
    
    # Use the first autolog file found
    csv_path = csv_files[0]
    print(f"  Reading: {csv_path.name}")
    
    try:
        df = pd.read_csv(csv_path)
        cycle_data = extract_highest_cycle_data(df)
        
        if cycle_data is None:
            return False
        
        # Add to output with folder name prefix
        output_df[f'{folder_name}_Time'] = cycle_data['Time']
        output_df[f'{folder_name}_Position'] = cycle_data['Position']
        output_df[f'{folder_name}_Force'] = cycle_data['Force']
        
        print(f"  [OK] Extracted {len(cycle_data)} data points")
        return True
        
    except Exception as e:
        print(f"  [ERROR] {str(e)}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Extract peak cycle data from continuous motion files with HEAVY smoothing (3x)'
    )
    parser.add_argument('--root', type=str, required=True,
                        help='Root directory containing material folders')
    parser.add_argument('--output', type=str, default='peak_cycle_continuous_heavy_smooth.csv',
                        help='Output CSV filename (default: peak_cycle_continuous_heavy_smooth.csv)')
    
    args = parser.parse_args()
    
    root_path = Path(args.root)
    
    if not root_path.exists():
        print(f"[ERROR] Root path does not exist: {root_path}")
        sys.exit(1)
    
    print("=" * 80)
    print("PEAK CYCLE DATA EXTRACTION - CONTINUOUS MOTION (HEAVY SMOOTHING)")
    print("=" * 80)
    print(f"Root folder: {root_path}")
    print(f"Output file: {root_path / args.output}")
    print("Smoothing: median=93, SG window=153 (3x standard)")
    print("=" * 80)
    
    # Get all subdirectories
    folders = [f for f in root_path.iterdir() if f.is_dir()]
    
    if not folders:
        print(f"[ERROR] No subfolders found in {root_path}")
        sys.exit(1)
    
    # Create output DataFrame
    output_df = pd.DataFrame()
    success_count = 0
    
    # Process each folder
    for folder in sorted(folders):
        if process_folder(folder, output_df, folder.name):
            success_count += 1
    
    if success_count == 0:
        print("\n[ERROR] No data extracted from any folder")
        sys.exit(1)
    
    # Save combined data
    output_path = root_path / args.output
    output_df.to_csv(output_path, index=False)
    
    print("\n" + "=" * 80)
    print(f"Successfully processed {success_count} folder(s)")
    print("=" * 80)
    
    # Report statistics
    max_length = len(output_df)
    print(f"\n[INFO] Cycle lengths: {output_df.notna().sum().min()} to {max_length} points")
    
    print(f"\n[OK] Saved combined data to: {output_path}")
    print(f"     Max cycle length: {max_length} points")
    print(f"     Total columns: {len(output_df.columns)}")
    
    print("\n[SUCCESS] Extraction complete!")


if __name__ == '__main__':
    main()
