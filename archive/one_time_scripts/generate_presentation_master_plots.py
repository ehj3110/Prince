"""
Generate Master Plots for Presentation Data
============================================

Create comprehensive master comparison plots for all Presentation data conditions
using the same format as V9 and TEMPO Picker master plots.

Generates:
- Mean aggregation plots (4 metrics: Peak Force, Work of Adhesion, Total Peel Distance, Peak Retraction Force)
- Median aggregation plots
- Log-log scaling plots

Usage:
    python generate_presentation_master_plots.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent / 'support_modules'))
sys.path.insert(0, str(Path(__file__).parent))

# Import plotting styles
from tempo_picker_plot_styles import (
    create_4subplot_mean_plot,
    create_4subplot_median_plot,
    create_4subplot_loglog_plot
)


def main():
    """Generate master plots for Presentation data"""
    
    pres_dir = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\Presentation data\Final")
    
    print("="*80)
    print("PRESENTATION DATA MASTER PLOT GENERATOR")
    print("="*80)
    print(f"Master Directory: {pres_dir}")
    
    # Get all subdirectories
    folders = sorted([f for f in pres_dir.iterdir() if f.is_dir()])
    
    if not folders:
        print("\n[X] No folders found!")
        return
    
    print(f"\nFound {len(folders)} subdirectories:")
    for folder in folders:
        print(f"  - {folder.name}")
    
    # Load data from all folders
    print("\n" + "="*80)
    print("LOADING DATA")
    print("="*80)
    
    all_data = []
    
    for folder in folders:
        csv_file = folder / "automated_work_of_adhesion.csv"
        
        if not csv_file.exists():
            print(f"\nWarning: No automated_work_of_adhesion.csv in {folder.name}")
            continue
        
        print(f"\nLoading data from {folder.name}...")
        df = pd.read_csv(csv_file)
        
        # Add condition column
        df['condition'] = folder.name
        
        print(f"  Loaded {len(df)} measurements")
        
        all_data.append(df)
    
    if not all_data:
        print("\n[X] No data loaded!")
        return
    
    # Combine all data
    print("\n" + "="*80)
    print("COMBINING DATA")
    print("="*80)
    
    combined_df = pd.concat(all_data, ignore_index=True)
    
    # Standardize column names (handle different formats)
    print("\nStandardizing column names...")
    column_rename_map = {
        'Layer_Number': 'layer_number',
        'Peak_Force_N': 'peak_force',
        'Work_of_Adhesion_mJ': 'work_of_adhesion_corrected_mJ',
        'Total_Peel_Distance_mm': 'total_peel_distance',
        'Peak_Retraction_Force_N': 'peak_retraction_force_N',
        'Cross_Sectional_Area_mm2': 'cross_sectional_area_mm2',
        'Distance_to_Peak_mm': 'pre_initiation_distance',
        'Distance_to_Propagate_mm': 'propagation_distance',
        'Initiation_Time_s': 'initiation_time',
        'Propagation_Duration_s': 'propagation_duration',
        'Total_Duration_s': 'total_duration'
    }
    
    # Apply renaming
    combined_df = combined_df.rename(columns=column_rename_map)
    print(f"Renamed {len([k for k in column_rename_map.keys() if k in combined_df.columns])} columns")
    
    # Calculate radius if not present
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
    
    # Save combined data
    output_csv = pres_dir / "MASTER_presentation_combined.csv"
    combined_df.to_csv(output_csv, index=False)
    print(f"\nSaved combined data to {output_csv.name}")
    print(f"Total measurements: {len(combined_df)}")
    
    # Summary by condition
    print("\n" + "="*80)
    print("DATA SUMMARY")
    print("="*80)
    for condition in sorted(combined_df['condition'].unique()):
        count = len(combined_df[combined_df['condition'] == condition])
        print(f"  {condition}: {count} measurements")
    
    # Generate master plots
    print("\n" + "="*80)
    print("GENERATING MASTER PLOTS")
    print("="*80)
    
    # Define metrics to plot
    metrics = [
        ('peak_force', 'Relative Peak Force'),
        ('work_of_adhesion_corrected_mJ', 'Work of Adhesion (mJ)'),
        ('total_peel_distance', 'Total Peel Distance (mm)'),
        ('peak_retraction_force_N', 'Peak Retraction Force (N)')
    ]
    
    # 1. Mean plot
    print("\n1. Creating mean plot...")
    mean_output = pres_dir / "MASTER_presentation_mean_analysis.png"
    create_4subplot_mean_plot(
        combined_df,
        x_col='radius_mm',
        metrics=metrics,
        condition_col='condition',
        xlabel='Radius (mm)',
        output_path=str(mean_output)
    )
    print("   [OK] Mean plot saved")
    
    # 2. Median plot
    print("\n2. Creating median plot...")
    median_output = pres_dir / "MASTER_presentation_median_analysis.png"
    create_4subplot_median_plot(
        combined_df,
        x_col='radius_mm',
        metrics=metrics,
        condition_col='condition',
        xlabel='Radius (mm)',
        output_path=str(median_output)
    )
    print("   [OK] Median plot saved")
    
    # 3. Log-log plot
    print("\n3. Creating log-log plot...")
    loglog_output = pres_dir / "MASTER_presentation_loglog_analysis.png"
    create_4subplot_loglog_plot(
        combined_df,
        x_col='radius_mm',
        metrics=metrics,
        condition_col='condition',
        xlabel='Radius (mm)',
        output_path=str(loglog_output)
    )
    print("   [OK] Log-log plot saved")
    
    # Final summary
    print("\n" + "="*80)
    print("COMPLETE!")
    print("="*80)
    print("\nGenerated files:")
    print(f"  - {output_csv.name}")
    print(f"  - {mean_output.name}")
    print(f"  - {median_output.name}")
    print(f"  - {loglog_output.name}")
    print("="*80)


if __name__ == "__main__":
    main()
