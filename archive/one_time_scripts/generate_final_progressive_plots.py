"""
Generate Progressive Reveal Master Plots for Final Presentation Data
====================================================================

Creates 4 versions of master plots with progressive data reveal:
- Version 1: FEP only
- Version 2: FEP + PDMS - Unsealed
- Version 3: FEP + PDMS - Unsealed + PDMS - Sealed
- Version 4: All 5 folders

All versions use consistent axis ranges for smooth transitions.

Usage:
    python generate_final_progressive_plots.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import sys

# Set Times New Roman font globally
matplotlib.rcParams['font.family'] = 'Times New Roman'
matplotlib.rcParams['font.sans-serif'] = ['Times New Roman']
matplotlib.rcParams['font.serif'] = ['Times New Roman']

# Add plotting modules
sys.path.insert(0, str(Path(__file__).parent / 'post-processing'))
from tempo_picker_plot_styles import create_4subplot_mean_plot, create_4subplot_loglog_plot


def load_and_prepare_data(final_dir):
    """
    Load data from MASTER_all_metrics.csv (reprocessed data with proper skip distance)
    
    Returns:
        DataFrame with all data, radius calculated, distances made positive
    """
    # Load from MASTER file which has the reprocessed data
    master_path = final_dir / "MASTER_all_metrics.csv"
    
    if not master_path.exists():
        raise FileNotFoundError(f"MASTER_all_metrics.csv not found in {final_dir}")
    
    print(f"\nLoading data from MASTER_all_metrics.csv...")
    df = pd.read_csv(master_path)
    
    # Standardize condition column name
    if 'Condition' in df.columns:
        df['condition'] = df['Condition']
    
    print(f"  Total rows: {len(df)}")
    print(f"  Conditions: {sorted(df['condition'].unique())}")
    
    # Fix negative distances by taking absolute value
    if 'Total_Peel_Distance_mm' in df.columns:
        df['Total_Peel_Distance_mm'] = df['Total_Peel_Distance_mm'].abs()
    
    # Calculate radius from cross-sectional area
    if 'Cross_Sectional_Area_mm2' in df.columns:
        df['radius_mm'] = np.sqrt(df['Cross_Sectional_Area_mm2'] / np.pi)
        # Round to 0.5mm bins to group layers from same autolog file
        df['radius_mm'] = np.ceil(df['radius_mm'] / 0.5) * 0.5
    
    # Standardize column names for plotting
    if 'Peak_Force_N' in df.columns:
        df['peak_force'] = df['Peak_Force_N']
    elif 'peak_force_corrected' in df.columns:
        df['peak_force'] = df['peak_force_corrected']
    
    # Work of adhesion
    if 'Work_of_Adhesion_mJ' in df.columns:
        df['work_of_adhesion_corrected_mJ'] = df['Work_of_Adhesion_mJ']
    elif 'work_of_adhesion_mJ' in df.columns:
        df['work_of_adhesion_corrected_mJ'] = df['work_of_adhesion_mJ']
    
    if 'Total_Peel_Distance_mm' in df.columns:
        df['total_peel_distance'] = df['Total_Peel_Distance_mm']
    
    if 'Peak_Retraction_Force_N' in df.columns:
        df['peak_retraction_force_N'] = df['Peak_Retraction_Force_N']
    
    # Check for any low peel distances (false peaks)
    for cond in df['condition'].unique():
        cond_df = df[df['condition'] == cond]
        low_peel = cond_df[cond_df['total_peel_distance'] < 1.0]
        if len(low_peel) > 0:
            print(f"  WARNING: {cond} has {len(low_peel)} rows with peel distance < 1.0mm (potential false peaks)")
    
    print(f"\nTotal measurements: {len(df)}")
    
    return df


def get_global_axis_ranges(df, metrics, x_col='radius_mm', condition_col='condition'):
    """
    Calculate global axis ranges from AGGREGATED MEAN data for consistent scaling
    
    This calculates ranges from the actual averaged points that will be plotted,
    including normalization for peak force (which gets normalized to relative scale).
    
    Args:
        df: DataFrame with all data
        metrics: List of (column, label) tuples
        x_col: Column name for x-axis (default: radius_mm)
        condition_col: Column for grouping conditions
        
    Returns:
        Dictionary of {metric_col: (x_min, x_max, y_min, y_max)}
    """
    ranges = {}
    
    # Get all conditions
    conditions = df[condition_col].unique()
    
    for metric_col, _ in metrics:
        # Collect all aggregated mean values across all conditions
        all_means = []
        all_x_values = []
        
        for condition in conditions:
            condition_data = df[df[condition_col] == condition][[x_col, metric_col]].dropna()
            
            if len(condition_data) == 0:
                continue
            
            # Group by x-axis and calculate MEAN (exactly as plotting does)
            # This groups ~5 layers per radius point
            grouped = condition_data.groupby(x_col)[metric_col].agg(['mean']).reset_index()
            
            # Collect the means and x values
            all_means.extend(grouped['mean'].values)
            all_x_values.extend(grouped[x_col].values)
        
        if len(all_means) == 0:
            continue
        
        # X range from all unique x values - add 5% padding
        x_min = min(all_x_values)
        x_max = max(all_x_values)
        x_range = x_max - x_min
        x_min = x_min - 0.05 * x_range
        x_max = x_max + 0.05 * x_range
        
        # Y range from aggregated means - add 10% padding
        y_min = min(all_means)
        y_max = max(all_means)
        y_range = y_max - y_min
        y_min = y_min - 0.1 * y_range
        y_max = y_max + 0.1 * y_range
        
        # Ensure non-negative if appropriate
        if y_min < 0 and min(all_means) >= 0:
            y_min = 0
        
        # Add extra headroom for error bars (20% above max)
        y_max = y_max + 0.1 * y_range
        
        ranges[metric_col] = (x_min, x_max, y_min, y_max)
        print(f"  {metric_col}: X=[{x_min:.3f}, {x_max:.3f}], Y=[{y_min:.3f}, {y_max:.3f}]")
    
    return ranges


def create_progressive_plots(combined_df, output_dir):
    """
    Create 4 versions of master plots with progressive reveal
    
    Version 1: FEP only
    Version 2: FEP + PDMS - Unsealed
    Version 3: FEP + both PDMS
    Version 4: All 5 folders
    """
    
    # Define metrics to plot
    metrics = [
        ('peak_force', 'Peak Force (N)'),
        ('work_of_adhesion_corrected_mJ', 'Work of Adhesion (mJ)'),
        ('total_peel_distance', 'Total Peel Distance (mm)'),
        ('peak_retraction_force_N', 'Peak Retraction Force (N)')
    ]
    
    # Get global ranges from ALL data (for WITH FEP plots)
    print("\nCalculating global axis ranges (with FEP)...")
    global_ranges = get_global_axis_ranges(combined_df, metrics)
    
    # Get separate ranges for No FEP plots (exclude FEP data)
    print("Calculating axis ranges for No FEP plots...")
    no_fep_df = combined_df[combined_df['condition'] != 'FEP'].copy()
    no_fep_ranges = get_global_axis_ranges(no_fep_df, metrics)
    
    # Define progressive reveal sequence
    # Note: PDMS folder renamed to "PDMS - Sealed"
    reveal_sequence = [
        # WITH FEP plots
        {
            'version': 1,
            'conditions': ['FEP'],
            'description': 'FEP only',
            'prefix': ''
        },
        {
            'version': 2,
            'conditions': ['FEP', 'PDMS - Unsealed'],
            'description': 'FEP + PDMS Unsealed',
            'prefix': ''
        },
        {
            'version': 3,
            'conditions': ['FEP', 'PDMS - Unsealed', 'PDMS - Sealed'],
            'description': 'FEP + both PDMS',
            'prefix': ''
        },
        {
            'version': 4,
            'conditions': ['FEP', 'PDMS - Unsealed', 'PDMS - Sealed', 'Hybrid', 'Hybrid - Compliant'],
            'description': 'All 5 conditions',
            'prefix': ''
        },
        # NO FEP plots
        {
            'version': 1,
            'conditions': ['PDMS - Unsealed'],
            'description': 'PDMS Unsealed only',
            'prefix': 'NoFEP_'
        },
        {
            'version': 2,
            'conditions': ['PDMS - Unsealed', 'PDMS - Sealed'],
            'description': 'Both PDMS',
            'prefix': 'NoFEP_'
        },
        {
            'version': 3,
            'conditions': ['PDMS - Unsealed', 'PDMS - Sealed', 'Hybrid'],
            'description': 'PDMS + Hybrid',
            'prefix': 'NoFEP_'
        },
        {
            'version': 4,
            'conditions': ['PDMS - Unsealed', 'PDMS - Sealed', 'Hybrid', 'Hybrid - Compliant'],
            'description': 'All 4 non-FEP conditions',
            'prefix': 'NoFEP_'
        }
    ]
    
    # Generate plots for each version
    for reveal in reveal_sequence:
        version = reveal['version']
        conditions = reveal['conditions']
        description = reveal['description']
        prefix = reveal.get('prefix', '')
        
        # Use appropriate axis ranges based on whether FEP is included
        if prefix == 'NoFEP_':
            current_ranges = no_fep_ranges
        else:
            current_ranges = global_ranges
        
        print(f"\n{'='*80}")
        print(f"Generating {prefix}Version {version}: {description}")
        print(f"{'='*80}")
        
        # Filter data for this version
        version_df = combined_df[combined_df['condition'].isin(conditions)].copy()
        
        print(f"Conditions: {conditions}")
        print(f"Total measurements: {len(version_df)}")
        
        # Generate mean plot
        mean_output = output_dir / f"{prefix}Master_Mean_Plot_{version}.png"
        print(f"\nGenerating mean plot...")
        
        create_4subplot_mean_plot(
            version_df,
            x_col='radius_mm',
            metrics=metrics,
            condition_col='condition',
            xlabel='Radius (mm)',
            output_path=str(mean_output),
            title="Adhesion Metrics Comparison (Mean)",
            axis_ranges=current_ranges
        )
        
        print(f"  [OK] Saved: {mean_output.name}")
        
        # Generate log-log plot
        loglog_output = output_dir / f"{prefix}Master_LogLog_Plot_{version}.png"
        print(f"\nGenerating log-log plot...")
        
        create_4subplot_loglog_plot(
            version_df,
            x_col='radius_mm',
            metrics=metrics,
            condition_col='condition',
            xlabel='Radius (mm)',
            output_path=str(loglog_output),
            title="Adhesion Metrics Comparison (Mean)",
            axis_ranges=current_ranges
        )
        
        print(f"  [OK] Saved: {loglog_output.name}")


def main():
    """Generate progressive reveal master plots"""
    
    final_dir = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\Presentation data\Final")
    
    print("="*80)
    print("PROGRESSIVE REVEAL MASTER PLOTS - FINAL PRESENTATION DATA")
    print("="*80)
    
    # Load and prepare data from MASTER_all_metrics.csv
    combined_df = load_and_prepare_data(final_dir)
    
    # Create output directory
    output_dir = final_dir / "progressive_plots"
    output_dir.mkdir(exist_ok=True)
    print(f"[OK] Output directory: {output_dir}")
    
    # Generate progressive plots
    create_progressive_plots(combined_df, output_dir)
    
    print("\n" + "="*80)
    print("PROGRESSIVE PLOTS COMPLETE")
    print("="*80)
    print(f"\nGenerated 16 plots in: {output_dir}")
    print("  - 4 mean plots with FEP (versions 1-4)")
    print("  - 4 log-log plots with FEP (versions 1-4)")
    print("  - 4 mean plots without FEP (NoFEP versions 1-4)")
    print("  - 4 log-log plots without FEP (NoFEP versions 1-4)")
    print("\nWith-FEP and No-FEP plots use separate axis ranges.")
    print("Data loaded from MASTER_all_metrics.csv (reprocessed with 500um skip).")


if __name__ == "__main__":
    main()
