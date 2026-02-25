"""
Generate Progressive Reveal Master Plots for Final Presentation Data (No FEP)
============================================================================

Creates 4 versions of master plots with progressive data reveal (excluding FEP):
- Version 1: PDMS - Unsealed only
- Version 2: PDMS - Unsealed + PDMS - Sealed
- Version 3: PDMS - Unsealed + PDMS - Sealed + Hybrid
- Version 4: All 4 non-FEP conditions

All versions use consistent axis ranges for smooth transitions.

Usage:
    python generate_final_progressive_plots_no_fep.py
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
    Load data from all Final subfolders
    
    Returns:
        DataFrame with all data, radius calculated, distances made positive
    """
    all_data = []
    max_fep_area = None
    
    subfolders = sorted([d for d in final_dir.iterdir() if d.is_dir()])
    
    print(f"\nLoading data from {len(subfolders)} folders:")
    
    # First pass: find max FEP area
    for folder in subfolders:
        if folder.name == 'FEP':
            csv_path = folder / "automated_work_of_adhesion.csv"
            if csv_path.exists():
                fep_df = pd.read_csv(csv_path)
                if 'Cross_Sectional_Area_mm2' in fep_df.columns:
                    max_fep_area = fep_df['Cross_Sectional_Area_mm2'].max()
                    print(f"  Max FEP area: {max_fep_area:.2f} mm²")
                    break
    
    # Second pass: load and filter data
    folders_to_skip = ['Hybrid - Compliant']  # Skip old Hybrid-Compliant data
    
    for folder in subfolders:
        # Skip folders we want to exclude
        if folder.name in folders_to_skip:
            print(f"  [SKIP] Excluding {folder.name} (old data)")
            continue
            
        csv_path = folder / "automated_work_of_adhesion.csv"
        
        if not csv_path.exists():
            print(f"  [X] Missing CSV in {folder.name}")
            continue
        
        df = pd.read_csv(csv_path)
        
        # Filter out areas larger than max FEP area
        if max_fep_area is not None and 'Cross_Sectional_Area_mm2' in df.columns:
            initial_count = len(df)
            df = df[df['Cross_Sectional_Area_mm2'] <= max_fep_area].copy()
            filtered_count = initial_count - len(df)
            if filtered_count > 0:
                print(f"  Filtered {filtered_count} layers with area > {max_fep_area:.2f} mm² from {folder.name}")
        
        # Add condition name
        df['condition'] = folder.name
        
        # Fix negative distances by taking absolute value
        if 'Total_Peel_Distance_mm' in df.columns:
            df['Total_Peel_Distance_mm'] = df['Total_Peel_Distance_mm'].abs()
        
        # Calculate radius from cross-sectional area
        if 'Cross_Sectional_Area_mm2' in df.columns:
            df['radius_mm'] = np.sqrt(df['Cross_Sectional_Area_mm2'] / np.pi)
            # Round to 0.5mm bins to group layers from same autolog file
            # Use ceiling to ensure largest values round up (5.22 -> 5.5, not 5.0)
            df['radius_mm'] = np.ceil(df['radius_mm'] / 0.5) * 0.5
        
        # Standardize column names for plotting
        # Map to expected column names used in plotting
        if 'peak_force_corrected' in df.columns:
            df['peak_force'] = df['peak_force_corrected']
        elif 'peak_force_N' in df.columns:
            df['peak_force'] = df['peak_force_N']
        elif 'Peak_Force_N' in df.columns:
            df['peak_force'] = df['Peak_Force_N']
        
        # Work of adhesion can be in multiple formats
        if 'Work_of_Adhesion_mJ' in df.columns:
            df['work_of_adhesion_corrected_mJ'] = df['Work_of_Adhesion_mJ']
        elif 'work_of_adhesion_mJ' in df.columns:
            df['work_of_adhesion_corrected_mJ'] = df['work_of_adhesion_mJ']
        elif 'work_of_adhesion_corrected_mJ' not in df.columns:
            # Already has the correct name
            pass
        
        if 'Total_Peel_Distance_mm' in df.columns:
            df['total_peel_distance'] = df['Total_Peel_Distance_mm']
        elif 'peel_distance_mm' in df.columns:
            df['total_peel_distance'] = df['peel_distance_mm']
        
        if 'Peak_Retraction_Force_N' in df.columns:
            df['peak_retraction_force_N'] = df['Peak_Retraction_Force_N']
        # peak_retraction_force_N already has correct name from batch_process_v9
        
        all_data.append(df)
        print(f"  [OK] {folder.name}: {len(df)} measurements")
    
    # Combine all data
    combined_df = pd.concat(all_data, ignore_index=True)
    
    print(f"\nTotal measurements: {len(combined_df)}")
    print(f"Conditions: {sorted(combined_df['condition'].unique())}")
    
    return combined_df


def get_global_axis_ranges(df, metrics, x_col='radius_mm', condition_col='condition'):
    """
    Calculate global axis ranges from AGGREGATED MEAN data for consistent scaling
    
    This calculates ranges from the actual averaged points that will be plotted.
    
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
        
        # X range from all unique x values - add 10% padding
        x_min = min(all_x_values)
        x_max = max(all_x_values)
        x_range = x_max - x_min
        x_min = x_min - 0.10 * x_range
        x_max = x_max + 0.10 * x_range
        
        # Y range from aggregated means - add 10% padding
        y_min = min(all_means)
        y_max = max(all_means)
        y_range = y_max - y_min
        y_min = y_min - 0.1 * y_range
        y_max = y_max + 0.1 * y_range
        
        # Ensure non-negative if appropriate
        if y_min < 0 and min(all_means) >= 0:
            y_min = 0
        
        ranges[metric_col] = (x_min, x_max, y_min, y_max)
        print(f"  {metric_col}: X=[{x_min:.3f}, {x_max:.3f}], Y=[{y_min:.3f}, {y_max:.3f}]")
    
    return ranges


def create_progressive_plots(combined_df, output_dir):
    """
    Create 4 versions of master plots with progressive reveal (no FEP)
    
    Version 1: PDMS - Unsealed only
    Version 2: PDMS - Unsealed + PDMS - Sealed
    Version 3: PDMS - Unsealed + PDMS - Sealed + Hybrid
    Version 4: All 4 non-FEP conditions
    """
    
    # Define metrics to plot
    metrics = [
        ('peak_force', 'Peak Force (N)'),
        ('work_of_adhesion_corrected_mJ', 'Work of Adhesion (mJ)'),
        ('total_peel_distance', 'Total Peel Distance (mm)'),
        ('peak_retraction_force_N', 'Peak Retraction Force (N)')
    ]
    
    # Filter out FEP from all data for range calculation
    non_fep_df = combined_df[combined_df['condition'] != 'FEP'].copy()
    
    # Get global ranges from non-FEP data only
    print("\nCalculating global axis ranges (excluding FEP)...")
    global_ranges = get_global_axis_ranges(non_fep_df, metrics)
    
    # Define progressive reveal sequence (no FEP)
    reveal_sequence = [
        {
            'version': 1,
            'conditions': ['PDMS - Unsealed'],
            'description': 'PDMS - Unsealed only'
        },
        {
            'version': 2,
            'conditions': ['PDMS - Unsealed', 'PDMS - Sealed'],
            'description': 'Both PDMS conditions'
        },
        {
            'version': 3,
            'conditions': ['PDMS - Unsealed', 'PDMS - Sealed', 'Hybrid'],
            'description': 'PDMS + Hybrid'
        },
        {
            'version': 4,
            'conditions': ['PDMS - Unsealed', 'PDMS - Sealed', 'Hybrid', 'Hybrid - Compliant'],
            'description': 'All 4 non-FEP conditions'
        }
    ]
    
    # Generate plots for each version
    for reveal in reveal_sequence:
        version = reveal['version']
        conditions = reveal['conditions']
        description = reveal['description']
        
        print(f"\n{'='*80}")
        print(f"Generating Version {version}: {description}")
        print(f"{'='*80}")
        
        # Filter data for this version
        version_df = combined_df[combined_df['condition'].isin(conditions)].copy()
        
        print(f"Conditions: {conditions}")
        print(f"Total measurements: {len(version_df)}")
        
        # Generate mean plot
        mean_output = output_dir / f"Master_Mean_Plot_NoFEP_{version}.png"
        print(f"\nGenerating mean plot...")
        
        create_4subplot_mean_plot(
            version_df,
            x_col='radius_mm',
            metrics=metrics,
            condition_col='condition',
            xlabel='Radius (mm)',
            output_path=str(mean_output),
            title="Adhesion Metrics Comparison (Mean)",
            axis_ranges=global_ranges
        )
        
        print(f"  [OK] Saved: {mean_output.name}")
        
        # Generate log-log plot
        loglog_output = output_dir / f"Master_LogLog_Plot_NoFEP_{version}.png"
        print(f"\nGenerating log-log plot...")
        
        create_4subplot_loglog_plot(
            version_df,
            x_col='radius_mm',
            metrics=metrics,
            condition_col='condition',
            xlabel='Radius (mm)',
            output_path=str(loglog_output),
            title="Adhesion Metrics Comparison (Mean)",
            axis_ranges=global_ranges
        )
        
        print(f"  [OK] Saved: {loglog_output.name}")


def main():
    """Generate progressive reveal master plots (no FEP)"""
    
    final_dir = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\Presentation data\Final")
    
    print("="*80)
    print("PROGRESSIVE REVEAL MASTER PLOTS - NO FEP")
    print("="*80)
    
    # Load and prepare data
    combined_df = load_and_prepare_data(final_dir)
    
    # Create output directory
    output_dir = final_dir / "progressive_plots"
    output_dir.mkdir(exist_ok=True)
    print(f"\n[OK] Output directory: {output_dir}")
    
    # Generate progressive plots
    create_progressive_plots(combined_df, output_dir)
    
    print("\n" + "="*80)
    print("PROGRESSIVE PLOTS COMPLETE (NO FEP)")
    print("="*80)
    print(f"\nGenerated 8 plots in: {output_dir}")
    print("  - 4 mean plots (versions 1-4, no FEP)")
    print("  - 4 log-log plots (versions 1-4, no FEP)")
    print("\nAll plots use consistent axis ranges for smooth transitions.")


if __name__ == "__main__":
    main()
