#!/usr/bin/env python3
"""
Generate master speed analysis plot combining all test conditions from a V17Tests folder.
Shows all fluid types and gap sizes on the same plots for comparison.
"""

import sys
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import numpy as np
import re


def parse_folder_name(folder_name):
    """Extract test parameters from folder name."""
    parts = folder_name.split('_')
    if len(parts) < 4:
        return None
    
    fluid_type = parts[0]  # e.g., "Water", "2p5PEO"
    gap = parts[1]  # e.g., "1mm", "5mm"
    test_type = parts[2]  # e.g., "Ramped", "Constant"
    
    return {
        'fluid': fluid_type,
        'gap': gap,
        'type': test_type,
        'label': f"{fluid_type}_{gap}"
    }


def load_all_metrics(master_folder):
    """Load and combine metrics from all test subfolders."""
    master_path = Path(master_folder)
    all_data = []
    
    # Find all autolog_metrics.csv files in subfolders
    for subfolder in master_path.iterdir():
        if not subfolder.is_dir():
            continue
        
        metrics_file = subfolder / "autolog_metrics.csv"
        if not metrics_file.exists():
            continue
        
        # Parse folder name to get test parameters
        params = parse_folder_name(subfolder.name)
        if params is None:
            continue
        
        # Load CSV
        try:
            df = pd.read_csv(metrics_file)
            
            # Add metadata columns
            df['fluid_type'] = params['fluid']
            df['gap_size'] = params['gap']
            df['test_type'] = params['type']
            df['condition_label'] = params['label']
            
            all_data.append(df)
            print(f"Loaded: {subfolder.name} ({len(df)} layers)")
        except Exception as e:
            print(f"Error loading {metrics_file}: {e}")
    
    if not all_data:
        return None
    
    # Combine all data
    combined_df = pd.concat(all_data, ignore_index=True)
    print(f"\nTotal: {len(combined_df)} layers from {len(all_data)} test conditions")
    
    return combined_df


def calculate_mean_per_condition(df, speed_col, value_col, group_col):
    """Calculate mean values for each speed within each test condition."""
    results = {}
    
    for condition in df[group_col].unique():
        condition_df = df[df[group_col] == condition]
        
        # Group by speed and calculate mean
        grouped = condition_df.groupby(speed_col)[value_col].agg(['mean', 'std', 'count'])
        speeds = grouped.index.values
        means = grouped['mean'].values
        stds = grouped['std'].fillna(0).values
        
        # Sort by speed
        sort_idx = np.argsort(speeds)
        
        results[condition] = {
            'speeds': speeds[sort_idx],
            'means': means[sort_idx],
            'stds': stds[sort_idx],
            'all_speeds': condition_df[speed_col].values,
            'all_values': condition_df[value_col].values
        }
    
    return results


def create_polynomial_fit(x, y, degree=2):
    """Create 2nd order polynomial fit."""
    if len(x) < degree + 1:
        return x, y, None
    
    coeffs = np.polyfit(x, y, degree)
    poly_func = np.poly1d(coeffs)
    
    x_fit = np.linspace(x.min(), x.max(), 100)
    y_fit = poly_func(x_fit)
    
    return x_fit, y_fit, coeffs


def plot_master_analysis(master_folder, output_path=None):
    """Create master plot with all test conditions."""
    
    # Load all data
    df = load_all_metrics(master_folder)
    if df is None:
        print("No data found!")
        return
    
    # Determine column names
    if 'Speed_um_s' in df.columns:
        df['speed_mm_min'] = df['Speed_um_s'] / 1000.0 * 60.0
        speed_col = 'speed_mm_min'
    else:
        speed_col = 'speed_mm_min'
    
    peak_force_col = 'Peak_Force_N' if 'Peak_Force_N' in df.columns else 'peak_force_N'
    woa_col = 'Work_of_Adhesion_mJ' if 'Work_of_Adhesion_mJ' in df.columns else 'work_of_adhesion_mJ'
    retraction_col = 'Peak_Retraction_Force_N' if 'Peak_Retraction_Force_N' in df.columns else 'peak_retraction_force_N'
    peel_dist_col = 'Total_Peel_Distance_mm' if 'Total_Peel_Distance_mm' in df.columns else 'peel_distance_mm'
    
    # Calculate absolute retraction
    df['abs_retraction'] = np.abs(df[retraction_col])
    
    # Define color scheme for different conditions
    # Combination of fluid type and gap size
    color_map = {
        'Water_1mm': '#1f77b4',      # Blue
        'Water_5mm': '#ff7f0e',      # Orange
        '2p5PEO_1mm': '#2ca02c',     # Green
        '2p5PEO_5mm': '#d62728',     # Red
        'PEO_1mm': '#9467bd',        # Purple
        'PEO_5mm': '#8c564b',        # Brown
    }
    
    # Calculate means for each condition
    pf_data = calculate_mean_per_condition(df, speed_col, peak_force_col, 'condition_label')
    woa_data = calculate_mean_per_condition(df, speed_col, woa_col, 'condition_label')
    pd_data = calculate_mean_per_condition(df, speed_col, peel_dist_col, 'condition_label')
    pr_data = calculate_mean_per_condition(df, speed_col, 'abs_retraction', 'condition_label')
    
    # Create figure
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Master Speed Analysis - All Test Conditions', fontsize=18, fontweight='bold')
    
    # Plot 1: Peak Force
    ax1 = axes[0, 0]
    for condition, data in pf_data.items():
        color = color_map.get(condition, '#808080')
        # Individual points (very transparent)
        ax1.scatter(data['all_speeds'], data['all_values'], c=color, alpha=0.05, s=30, edgecolors='none')
        # Mean points (75% transparent = 0.25 alpha)
        ax1.scatter(data['speeds'], data['means'], c=color, alpha=0.25, s=80, 
                   edgecolors='black', linewidth=1, label=condition, zorder=5)
        # Polynomial fit
        if len(data['speeds']) >= 3:
            x_fit, y_fit, _ = create_polynomial_fit(data['speeds'], data['means'], degree=2)
            ax1.plot(x_fit, y_fit, color=color, linewidth=2, linestyle='--', alpha=0.8, zorder=4)
    
    ax1.set_xlabel('Speed (mm/min)', fontsize=13, fontweight='bold')
    ax1.set_ylabel('Peak Force (N)', fontsize=13, fontweight='bold')
    ax1.set_title('Peak Force vs. Speed', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=10, loc='best')
    
    # Plot 2: Work of Adhesion
    ax2 = axes[0, 1]
    for condition, data in woa_data.items():
        color = color_map.get(condition, '#808080')
        ax2.scatter(data['all_speeds'], data['all_values'], c=color, alpha=0.05, s=30, edgecolors='none')
        ax2.scatter(data['speeds'], data['means'], c=color, alpha=0.25, s=80,
                   edgecolors='black', linewidth=1, label=condition, zorder=5)
        if len(data['speeds']) >= 3:
            x_fit, y_fit, _ = create_polynomial_fit(data['speeds'], data['means'], degree=2)
            ax2.plot(x_fit, y_fit, color=color, linewidth=2, linestyle='--', alpha=0.8, zorder=4)
    
    ax2.set_xlabel('Speed (mm/min)', fontsize=13, fontweight='bold')
    ax2.set_ylabel('Work of Adhesion (mJ)', fontsize=13, fontweight='bold')
    ax2.set_title('Work of Adhesion vs. Speed', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend(fontsize=10, loc='best')
    
    # Plot 3: Peel Distance
    ax3 = axes[1, 0]
    for condition, data in pd_data.items():
        color = color_map.get(condition, '#808080')
        ax3.scatter(data['all_speeds'], data['all_values'], c=color, alpha=0.05, s=30, edgecolors='none')
        ax3.scatter(data['speeds'], data['means'], c=color, alpha=0.25, s=80,
                   edgecolors='black', linewidth=1, label=condition, zorder=5)
        if len(data['speeds']) >= 3:
            x_fit, y_fit, _ = create_polynomial_fit(data['speeds'], data['means'], degree=2)
            ax3.plot(x_fit, y_fit, color=color, linewidth=2, linestyle='--', alpha=0.8, zorder=4)
    
    ax3.set_xlabel('Speed (mm/min)', fontsize=13, fontweight='bold')
    ax3.set_ylabel('Total Peel Distance (mm)', fontsize=13, fontweight='bold')
    ax3.set_title('Peel Distance vs. Speed', fontsize=14, fontweight='bold')
    ax3.grid(True, alpha=0.3)
    ax3.legend(fontsize=10, loc='best')
    
    # Plot 4: Retraction Force
    ax4 = axes[1, 1]
    for condition, data in pr_data.items():
        color = color_map.get(condition, '#808080')
        ax4.scatter(data['all_speeds'], data['all_values'], c=color, alpha=0.05, s=30, edgecolors='none')
        ax4.scatter(data['speeds'], data['means'], c=color, alpha=0.25, s=80,
                   edgecolors='black', linewidth=1, label=condition, zorder=5)
        if len(data['speeds']) >= 3:
            x_fit, y_fit, _ = create_polynomial_fit(data['speeds'], data['means'], degree=2)
            ax4.plot(x_fit, y_fit, color=color, linewidth=2, linestyle='--', alpha=0.8, zorder=4)
    
    ax4.set_xlabel('Speed (mm/min)', fontsize=13, fontweight='bold')
    ax4.set_ylabel('Peak Retraction Force (N)', fontsize=13, fontweight='bold')
    ax4.set_title('Peak Retraction Force vs. Speed', fontsize=14, fontweight='bold')
    ax4.grid(True, alpha=0.3)
    ax4.legend(fontsize=10, loc='best')
    
    plt.tight_layout()
    
    # Save
    if output_path is None:
        output_path = Path(master_folder) / "MASTER_speed_analysis.png"
    
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    print(f"\nMaster plot saved to: {output_path}")
    
    return fig


def main():
    if len(sys.argv) < 2:
        print("Usage: python plot_master_speed_analysis.py <path_to_V17Tests_folder>")
        return
    
    master_folder = sys.argv[1]
    plot_master_analysis(master_folder)


if __name__ == "__main__":
    main()
