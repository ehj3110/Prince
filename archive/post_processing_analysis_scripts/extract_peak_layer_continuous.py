"""
Extract Peak Layer Data for Continuous Motion Files
===================================================

Specialized extraction for continuous motion recordings where stage moves
and stops cyclically but phase labels are incomplete. Uses position data
to identify lift start and extracts the cycle with the highest force peak.

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
from scipy.signal import find_peaks


def find_motion_cycles(position, force, min_peak_height=0.01, min_distance=100):
    """
    Find motion cycles by detecting force peaks and tracking back to motion start.
    
    Returns list of (start_idx, end_idx, peak_idx, peak_force, peak_position, baseline) tuples.
    Sorted by peak force (descending), but includes original peak position for chronological ordering.
    Baseline is the force value right before lift starts.
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
        
        # Calculate baseline as force right before lift starts (average 10 points before lift)
        baseline_start = max(0, lift_start_idx - 10)
        baseline = np.mean(force[baseline_start:lift_start_idx]) if lift_start_idx > 0 else force[lift_start_idx]
        
        # Search forwards from peak to find propagation end (force drops to baseline)
        prop_end_idx = find_propagation_end(force, peak_idx, len(force) - 1)
        
        # Store peak_idx for chronological ordering later, and baseline
        cycles.append((lift_start_idx, prop_end_idx, peak_idx, peak_force, peak_idx, baseline))
    
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
    
    # If no clear start found, use earliest point with any upward motion
    for i in range(len(pos_diff)):
        if pos_diff[i] > motion_threshold:
            return search_start + i
    
    # Fallback: go back a fixed amount from peak
    return max(0, peak_idx - 100)


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
    Extract the complete layer cycle with the highest RELATIVE force peak.
    Relative peak = peak_force - baseline (force before lift).
    Finds highest relative peak that is NOT the last layer chronologically.
    Extracts: Exposure → Lift (from that layer) → Pause (from next layer).
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
    force = df['Force'].values
    time = df['Time'].values
    
    # Find all motion cycles
    cycles = find_motion_cycles(position, force)
    
    if not cycles:
        print(f"  [ERROR] No cycles detected")
        return None
    
    print(f"  Detected {len(cycles)} cycles")
    
    # Sort cycles chronologically by peak position
    cycles_chrono = sorted(cycles, key=lambda x: x[4])  # Sort by peak_position (index 4)
    
    # Calculate relative peak force for each cycle (peak - baseline)
    # Exclude the last cycle chronologically
    if len(cycles_chrono) > 1:
        eligible_cycles = cycles_chrono[:-1]  # Exclude last layer
        print(f"  Excluding last layer, evaluating {len(eligible_cycles)} cycles")
    else:
        print(f"  [WARNING] Only 1 cycle found, using it despite being last")
        eligible_cycles = cycles_chrono
    
    # Find cycle with highest relative peak
    relative_peaks = []
    for cycle in eligible_cycles:
        lift_start, prop_end, peak_idx, peak_force, peak_position, baseline = cycle
        relative_peak = peak_force - baseline
        relative_peaks.append((relative_peak, cycle))
    
    # Sort by relative peak (descending) and get highest
    relative_peaks.sort(key=lambda x: x[0], reverse=True)
    highest_relative_peak, highest_cycle = relative_peaks[0]
    
    lift_start, prop_end, peak_idx, peak_force, peak_position, baseline = highest_cycle
    
    print(f"  Highest RELATIVE peak: {highest_relative_peak:.4f}N (absolute: {peak_force:.4f}N, baseline: {baseline:.4f}N)")
    print(f"  Peak at index {peak_idx}, lift start at index {lift_start}")
    
    # Find exposure start (beginning of this layer, after previous cycle ended)
    exposure_start = find_exposure_start(position, lift_start)
    
    # Find which cycle is our highest relative peak in chronological order
    highest_cycle_chrono_idx = None
    for i, cycle in enumerate(cycles_chrono):
        if cycle[4] == peak_position:  # Match by peak position
            highest_cycle_chrono_idx = i
            break
    
    # Get the pause from next layer if it exists
    if highest_cycle_chrono_idx is not None and highest_cycle_chrono_idx < len(cycles_chrono) - 1:
        # There is a next cycle
        next_cycle = cycles_chrono[highest_cycle_chrono_idx + 1]
        next_lift_start = next_cycle[0]  # When next layer's lift starts
        
        # The pause ends when the next lift starts
        # So extract from current exposure start to just before next lift
        final_end = next_lift_start - 1
        
        print(f"  Including pause from next layer")
        print(f"  Next layer lift start: index {next_lift_start}")
        print(f"  Final end (before next lift): index {final_end}")
    else:
        # No next cycle, just use propagation end
        final_end = prop_end
        print(f"  [INFO] No next layer found, using propagation end")
    
    print(f"  Exposure start: index {exposure_start}")
    print(f"  Final end (with next pause): index {final_end}")
    print(f"  Full layer (Exposure→Lift→Pause): {final_end - exposure_start + 1} points")
    print(f"  Time range: {time[exposure_start]:.3f}s to {time[final_end]:.3f}s")
    print(f"  Total duration: {time[final_end] - time[exposure_start]:.3f}s")
    
    # Extract the full layer data from exposure start to final end
    cycle_df = df.iloc[exposure_start:final_end+1][['Time', 'Position', 'Force']].copy()
    
    # Calculate lift start time relative to exposure start (before reset)
    lift_start_time_relative = time[lift_start] - time[exposure_start]
    
    # Reset time to start from 0
    cycle_df['Time'] = cycle_df['Time'] - cycle_df['Time'].iloc[0]
    
    # Add Phase column
    phase_labels = []
    for idx in range(len(cycle_df)):
        current_time = cycle_df['Time'].iloc[idx]
        if current_time < lift_start_time_relative:
            phase_labels.append('Exposure')
        elif current_time < (time[prop_end] - time[exposure_start]):
            phase_labels.append('Lift')
        else:
            phase_labels.append('Pause')
    
    cycle_df['Phase'] = phase_labels
    
    # Add metadata columns for lift start time and baseline
    cycle_df['Lift_Start_Time'] = lift_start_time_relative
    cycle_df['Baseline_Force'] = baseline
    
    print(f"  Lift start time (relative): {lift_start_time_relative:.3f}s")
    
    return cycle_df


def process_folder(folder_path):
    """
    Process autolog_L45-L49.csv in the given folder for continuous motion.
    Returns (folder_name, cycle_dataframe) or None if file not found/error.
    """
    csv_file = folder_path / "autolog_L45-L49.csv"
    
    if not csv_file.exists():
        print(f"  [SKIP] autolog_L45-L49.csv not found")
        return None
    
    try:
        df = pd.read_csv(csv_file)
        
        # Validate required columns exist (with flexible names)
        has_time = any('time' in col.lower() for col in df.columns)
        has_position = any('position' in col.lower() for col in df.columns)
        has_force = any('force' in col.lower() for col in df.columns)
        
        if not (has_time and has_position and has_force):
            print(f"  [ERROR] Missing required columns")
            return None
        
        # Extract highest cycle
        cycle_data = extract_highest_cycle_data(df)
        
        if cycle_data is None:
            return None
        
        folder_name = folder_path.name
        return (folder_name, cycle_data)
        
    except Exception as e:
        print(f"  [ERROR] {e}")
        import traceback
        traceback.print_exc()
        return None


def combine_and_save(folder_data_list, output_path):
    """
    Combine data from multiple folders into a single CSV.
    Each folder gets three columns: FolderName_Time, FolderName_Position, FolderName_Force
    Cycles may have different lengths, so pad shorter ones with NaN.
    """
    if not folder_data_list:
        print("\n[ERROR] No data to save")
        return False
    
    # Find the maximum number of rows needed
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
    print(f"\n[OK] Saved combined data to: {output_path}")
    print(f"     Max cycle length: {max_rows} points")
    print(f"     Total columns: {len(combined_df.columns)}")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Extract peak cycle data from continuous motion autolog_L45-L49.csv files"
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
        help='Output CSV file path (default: peak_cycle_continuous.csv in root folder)'
    )
    
    args = parser.parse_args()
    
    root_path = Path(args.root)
    if not root_path.exists():
        print(f"[ERROR] Root folder not found: {root_path}")
        sys.exit(1)
    
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = root_path / "peak_cycle_continuous.csv"
    
    print("=" * 80)
    print("PEAK CYCLE DATA EXTRACTION - CONTINUOUS MOTION")
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
