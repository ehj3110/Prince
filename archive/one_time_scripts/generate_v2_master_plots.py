#!/usr/bin/env python3
"""
Generate master plots for V2 selected datasets (2p5PEO and Water_1000).
Creates scatter plots with polynomial trendlines in standard format.

Author: Cheng Sun Lab Team
Date: January 20, 2026
"""

import sys
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# Set Times New Roman as default font
plt.rcParams['font.family'] = 'Times New Roman'
plt.rcParams['font.size'] = 12


def create_master_scatter_plots(df, output_path):
    """
    Create a 2x2 master plot showing scatter plots with trendlines.
    Standard format: scatter points + shaded SEM + polynomial trendline
    
    Args:
        df: DataFrame with metrics and 'condition_label' column
        output_path: Path to save figure
    """
    fig, axes = plt.subplots(2, 2, figsize=(16, 12), dpi=300)
    axes = axes.flatten()
    
    # Metrics to plot (4 subplots)
    metrics = [
        ('peak_force', 'Peak Adhesion Force (N)'),
        ('work_of_adhesion_corrected_mJ', 'Work of Adhesion (mJ)'),
        ('pre_initiation_distance', 'Pre-Initiation Distance (mm)'),
        ('propagation_distance', 'Propagation Distance (mm)')
    ]
    
    # Get unique conditions and assign colors
    conditions = sorted(df['condition_label'].unique())
    colors = plt.cm.tab10(np.linspace(0, 1, len(conditions)))
    color_map = dict(zip(conditions, colors))
    
    for idx, (metric_col, ylabel) in enumerate(metrics):
        ax = axes[idx]
        
        for condition in conditions:
            condition_data = df[df['condition_label'] == condition].copy()
            color = color_map[condition]
            
            # Use absolute value for distance metrics
            if 'distance' in metric_col:
                condition_data[metric_col] = condition_data[metric_col].abs()
            
            # Sort by layer number
            condition_data = condition_data.sort_values('layer_number')
            
            # Get data
            x_values = condition_data['layer_number'].values
            y_values = condition_data[metric_col].values
            
            # Remove NaN values
            mask = ~np.isnan(y_values)
            x_clean = x_values[mask]
            y_clean = y_values[mask]
            
            if len(x_clean) == 0:
                continue
            
            # Calculate mean and SEM in bins
            # Group into bins of ~10 layers for better visualization
            bin_size = max(10, len(x_clean) // 10)
            n_bins = max(5, len(x_clean) // bin_size)
            bins = np.linspace(x_clean.min(), x_clean.max(), n_bins + 1)
            bin_centers = (bins[:-1] + bins[1:]) / 2
            
            bin_means = []
            bin_sems = []
            bin_x = []
            
            for i in range(len(bins) - 1):
                mask = (x_clean >= bins[i]) & (x_clean < bins[i+1])
                if i == len(bins) - 2:  # Last bin includes right edge
                    mask = (x_clean >= bins[i]) & (x_clean <= bins[i+1])
                
                bin_data = y_clean[mask]
                if len(bin_data) > 0:
                    bin_x.append(bin_centers[i])
                    bin_means.append(bin_data.mean())
                    bin_sems.append(bin_data.std() / np.sqrt(len(bin_data)) if len(bin_data) > 1 else 0)
            
            bin_x = np.array(bin_x)
            bin_means = np.array(bin_means)
            bin_sems = np.array(bin_sems)
            
            # Simplify condition label for legend
            label = "2.5% PEO" if '2p5PEO' in condition else "Water"
            
            # Plot shaded SEM region
            if len(bin_x) > 0:
                ax.fill_between(bin_x, bin_means - bin_sems, bin_means + bin_sems,
                               color=color, alpha=0.2, zorder=1)
            
            # Plot scatter points (all data)
            ax.scatter(x_clean, y_clean, s=20, color=color, alpha=0.5, 
                      edgecolors='none', zorder=3)
            
            # Fit and plot polynomial trendline
            if len(x_clean) > 3:
                try:
                    # Fit 2nd degree polynomial
                    z = np.polyfit(x_clean, y_clean, 2)
                    p = np.poly1d(z)
                    
                    # Create smooth x-axis for trendline
                    x_smooth = np.linspace(x_clean.min(), x_clean.max(), 100)
                    y_smooth = p(x_smooth)
                    
                    # Plot trendline
                    ax.plot(x_smooth, y_smooth, '-', color=color, linewidth=2, 
                           alpha=0.8, label=label, zorder=2)
                except:
                    # If polynomial fit fails, just show data with label
                    ax.plot([], [], '-', color=color, linewidth=2, label=label)
            else:
                # Not enough points for trendline
                ax.plot([], [], 'o', color=color, label=label)
        
        # Format subplot
        ax.set_xlabel('Layer Number', fontsize=12, fontweight='bold')
        ax.set_ylabel(ylabel, fontsize=12, fontweight='bold')
        ax.set_title(ylabel, fontsize=14, fontweight='bold', pad=10)
        ax.legend(fontsize=11, loc='best', framealpha=0.9)
        ax.grid(True, alpha=0.3)
        
        # Set y-axis to start at 0 if all values are positive
        y_min = df[df['condition_label'].isin(conditions)][metric_col].min()
        if 'distance' in metric_col:
            y_min = df[df['condition_label'].isin(conditions)][metric_col].abs().min()
        if y_min >= 0:
            ax.set_ylim(bottom=0)
    
    # Main title
    fig.suptitle('V2 SteppedCone Analysis: 2.5% PEO vs Water (1000 μm/s)', 
                fontsize=18, fontweight='bold', y=0.995)
    plt.tight_layout(rect=[0, 0, 1, 0.98])
    
    # Save
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ Saved: {output_path.name}")


def create_master_plots_v2():
    """
    Generate master analysis plots for V2 selected datasets.
    """
    # Define paths
    v2_dir = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V2")
    master_csv = v2_dir / "MASTER_v2_selected_metrics.csv"
    
    if not master_csv.exists():
        print(f"Error: Master CSV not found: {master_csv}")
        print("Please run batch_process_v2_selected.py first.")
        return
    
    print("="*80)
    print("GENERATING V2 MASTER PLOTS")
    print("="*80)
    print(f"Reading data from: {master_csv.name}\n")
    
    # Load data
    df = pd.read_csv(master_csv)
    print(f"Loaded {len(df)} layers")
    print(f"Conditions:")
    for cond in df['folder'].unique():
        n_layers = len(df[df['folder'] == cond])
        print(f"  - {cond}: {n_layers} layers")
    print()
    
    # Rename folder to condition_label for consistency
    df['condition_label'] = df['folder']
    
    # =========================================================================
    # Master Scatter Plot (4 subplots: scatter + trendlines)
    # =========================================================================
    print("\n" + "="*80)
    print("GENERATING MASTER SCATTER PLOTS")
    print("="*80)
    
    create_master_scatter_plots(
        df=df,
        output_path=v2_dir / 'MASTER_v2_analysis.png'
    )
    
    # =========================================================================
    # Generate Summary Statistics
    # =========================================================================
    print("\n" + "="*80)
    print("SUMMARY STATISTICS BY CONDITION")
    print("="*80)
    
    summary_cols = ['peak_force', 'work_of_adhesion_corrected_mJ', 
                    'pre_initiation_distance', 'propagation_distance',
                    'pre_initiation_duration', 'propagation_duration']
    
    for condition in df['condition_label'].unique():
        cond_data = df[df['condition_label'] == condition]
        
        # Simplify condition name for display
        display_name = "2.5% PEO" if '2p5PEO' in condition else "Water"
        
        print(f"\n{display_name} (n={len(cond_data)} layers):")
        print("-" * 60)
        
        for col in summary_cols:
            if col in df.columns:
                # Use absolute value for distance metrics
                if 'distance' in col:
                    data = cond_data[col].abs()
                else:
                    data = cond_data[col]
                
                mean_val = data.mean()
                std_val = data.std()
                median_val = data.median()
                print(f"  {col:40s}: {mean_val:8.3f} ± {std_val:6.3f} (median: {median_val:8.3f})")
    
    print("\n" + "="*80)
    print("V2 MASTER PLOT GENERATION COMPLETE")
    print("="*80)
    print(f"Output directory: {v2_dir}")
    print("Generated plots:")
    print("  - MASTER_v2_analysis.png (4-subplot scatter plot with trendlines)")
    print("="*80)


if __name__ == "__main__":
    create_master_plots_v2()
