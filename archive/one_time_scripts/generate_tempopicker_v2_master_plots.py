"""
Generate TEMPO Picker V2 Master Plots
======================================

Read automated_work_of_adhesion.csv from each subfolder and create master plots.

Author: Cheng Sun Lab Team
Date: January 20, 2026
"""

import pandas as pd
import numpy as np
from pathlib import Path
import tempo_picker_plot_styles as tempo_styles

def main():
    """Main processing function"""
    
    # Path to TEMPO Picker V2 directory
    v2_dir = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\TEMPO Picker\V2")
    
    print("="*80)
    print("TEMPO PICKER V2 MASTER PLOT GENERATOR")
    print("="*80)
    print(f"Master Directory: {v2_dir}\n")
    
    if not v2_dir.exists():
        print(f"ERROR: Directory not found: {v2_dir}")
        return
    
    # Find all subdirectories
    subdirs = [d for d in v2_dir.iterdir() if d.is_dir() and d.name != 'plots']
    subdirs.sort()
    
    print(f"Found {len(subdirs)} subdirectories:")
    for d in subdirs:
        print(f"  - {d.name}")
    
    # Collect data from all folders
    all_data = []
    
    for subdir in subdirs:
        # Check for automated_work_of_adhesion.csv
        data_file = subdir / "automated_work_of_adhesion.csv"
        
        if not data_file.exists():
            print(f"\nWARNING: No automated_work_of_adhesion.csv in {subdir.name}")
            continue
        
        print(f"\nLoading data from {subdir.name}...")
        
        try:
            df = pd.read_csv(data_file)
            
            # Add folder name as condition
            df['folder'] = subdir.name
            df['condition'] = subdir.name  # Use folder name as condition label
            
            # Print summary
            print(f"  Loaded {len(df)} measurements")
            if 'cross_sectional_area_mm2' in df.columns:
                print(f"  Area range: {df['cross_sectional_area_mm2'].min():.3f} to {df['cross_sectional_area_mm2'].max():.3f} mm²")
            
            all_data.append(df)
            
        except Exception as e:
            print(f"  ERROR loading {data_file.name}: {e}")
            continue
    
    if not all_data:
        print("\nERROR: No data loaded from any folder!")
        return
    
    # Combine all data
    print(f"\n{'='*80}")
    print("COMBINING DATA")
    print(f"{'='*80}")
    
    combined_df = pd.concat(all_data, ignore_index=True)
    
    # Rename columns to match expected format (lowercase with underscores)
    print("\nStandardizing column names...")
    column_rename_map = {
        'Layer_Number': 'layer_number',
        'Peak_Force_N': 'peak_force',
        'Work_of_Adhesion_mJ': 'work_of_adhesion_corrected_mJ',
        'Initiation_Time_s': 'initiation_time_s',
        'Propagation_Duration_s': 'propagation_duration_s',
        'Total_Duration_s': 'total_duration_s',
        'Distance_to_Peak_mm': 'pre_initiation_distance',
        'Distance_to_Propagate_mm': 'propagation_distance',
        'Total_Peel_Distance_mm': 'total_peel_distance',
        'Peak_Retraction_Force_N': 'peak_retraction_force_N',
        'Cross_Sectional_Area_mm2': 'cross_sectional_area_mm2'
    }
    
    combined_df.rename(columns=column_rename_map, inplace=True)
    print(f"Renamed {len(column_rename_map)} columns")
    
    # Calculate radius BEFORE saving
    if 'radius_mm' not in combined_df.columns:
        combined_df['radius_mm'] = np.sqrt(combined_df['cross_sectional_area_mm2'] / np.pi)
        print("Calculated radius_mm from cross_sectional_area_mm2")
        
        # Print radius summary for each condition
        print("\nRadius summary by condition:")
        for condition in sorted(combined_df['condition'].unique()):
            cond_data = combined_df[combined_df['condition'] == condition]
            print(f"  {condition}:")
            print(f"    Min radius: {cond_data['radius_mm'].min():.3f} mm")
            print(f"    Max radius: {cond_data['radius_mm'].max():.3f} mm")
            print(f"    Unique radii: {cond_data['radius_mm'].nunique()}")
    
    # Save combined data (now with radius)
    output_csv = v2_dir / "MASTER_tempopicker_v2_combined.csv"
    combined_df.to_csv(output_csv, index=False)
    print(f"\nSaved combined data to {output_csv.name}")
    print(f"Total measurements: {len(combined_df)}")
    
    # Print summary by condition
    print(f"\n{'='*80}")
    print("DATA SUMMARY")
    print(f"{'='*80}")
    for condition in sorted(combined_df['condition'].unique()):
        count = len(combined_df[combined_df['condition'] == condition])
        print(f"  {condition}: {count} measurements")
    
    # Generate master plots
    print(f"\n{'='*80}")
    print("GENERATING MASTER PLOTS")
    print(f"{'='*80}")
    
    # Define metrics to plot (same as V2 plots)
    metrics = [
        ('peak_force', 'Relative Peak Force'),
        ('work_of_adhesion_corrected_mJ', 'Work of Adhesion (mJ)'),
        ('total_peel_distance', 'Total Peel Distance (mm)'),
        ('peak_retraction_force_N', 'Peak Retraction Force (N)')
    ]
    
    xlabel = 'Radius (mm)'
    
    # Generate mean plot
    print("\n1. Creating mean plot...")
    try:
        tempo_styles.create_4subplot_mean_plot(
            df=combined_df,
            x_col='radius_mm',
            metrics=metrics,
            condition_col='condition',
            xlabel=xlabel,
            output_path=str(v2_dir / "MASTER_tempopicker_v2_mean_analysis.png")
        )
        print("   ✓ Mean plot saved")
    except Exception as e:
        print(f"   ✗ Error creating mean plot: {e}")
        import traceback
        traceback.print_exc()
    
    # Generate median plot
    print("\n2. Creating median plot...")
    try:
        tempo_styles.create_4subplot_median_plot(
            df=combined_df,
            x_col='radius_mm',
            metrics=metrics,
            condition_col='condition',
            xlabel=xlabel,
            output_path=str(v2_dir / "MASTER_tempopicker_v2_median_analysis.png")
        )
        print("   ✓ Median plot saved")
    except Exception as e:
        print(f"   ✗ Error creating median plot: {e}")
        import traceback
        traceback.print_exc()
    
    # Generate log-log plot
    print("\n3. Creating log-log plot...")
    try:
        tempo_styles.create_4subplot_loglog_plot(
            df=combined_df,
            x_col='radius_mm',
            metrics=metrics,
            condition_col='condition',
            xlabel=xlabel,
            output_path=str(v2_dir / "MASTER_tempopicker_v2_loglog_analysis.png")
        )
        print("   ✓ Log-log plot saved")
    except Exception as e:
        print(f"   ✗ Error creating log-log plot: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n{'='*80}")
    print("COMPLETE!")
    print(f"{'='*80}")
    print(f"\nGenerated files:")
    print(f"  - {output_csv.name}")
    print(f"  - MASTER_tempopicker_v2_mean_analysis.png")
    print(f"  - MASTER_tempopicker_v2_median_analysis.png")
    print(f"  - MASTER_tempopicker_v2_loglog_analysis.png")


if __name__ == "__main__":
    main()
