#!/usr/bin/env python3
"""
Generate master speed analysis plot for DISTANCE metrics combining all test conditions.
Uses MEDIAN for averaging data points at each speed.
Shows 2 subplots: Distance to Peak and Propagation Distance vs Speed.
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


def calculate_median_per_condition(df, speed_col, value_col, group_col):
    """Calculate MEDIAN values for each speed within each test condition."""
    results = {}
    
    for condition in df[group_col].unique():
        condition_df = df[df[group_col] == condition]
        
        # Group by speed and calculate median
        grouped = condition_df.groupby(speed_col)[value_col].agg(['median', 'std', 'count'])
        speeds = grouped.index.values
        medians = grouped['median'].values
        stds = grouped['std'].fillna(0).values
        
        # Sort by speed
        sort_idx = np.argsort(speeds)
        
        results[condition] = {
            'speeds': speeds[sort_idx],
            'medians': medians[sort_idx],
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


def plot_distance_analysis(master_folder, output_path=None):
    """Create 2-subplot distance analysis plot using MEDIAN."""
    
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
    
    # Distance columns
    dist_to_peak_col = 'Distance_to_Peak_mm' if 'Distance_to_Peak_mm' in df.columns else 'distance_to_peak_mm'
    prop_dist_col = 'Propagation_Distance_mm' if 'Propagation_Distance_mm' in df.columns else 'propagation_distance_mm'
    
    # Define color scheme for different conditions
    color_map = {
        'Water_1mm': '#1f77b4',      # Blue
        'Water_5mm': '#ff7f0e',      # Orange
        '2p5PEO_1mm': '#2ca02c',     # Green
        '2p5PEO_5mm': '#d62728',     # Red
        'PEO_1mm': '#9467bd',        # Purple
        'PEO_5mm': '#8c564b',        # Brown
    }
    
    # Calculate medians for each condition
    dist_to_peak_data = calculate_median_per_condition(df, speed_col, dist_to_peak_col, 'condition_label')
    prop_dist_data = calculate_median_per_condition(df, speed_col, prop_dist_col, 'condition_label')
    
    # Create figure with 2 subplots (1 row, 2 columns)
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    fig.suptitle('Distance Metrics vs. Speed - All Test Conditions (MEDIAN)', fontsize=18, fontweight='bold')
    
    # Plot 1: Distance to Peak
    ax1 = axes[0]
    for condition, data in dist_to_peak_data.items():
        color = color_map.get(condition, '#808080')
        # Individual points (very transparent)
        ax1.scatter(data['all_speeds'], data['all_values'], c=color, alpha=0.05, s=30, edgecolors='none')
        # Median points (75% transparent = 0.25 alpha)
        ax1.scatter(data['speeds'], data['medians'], c=color, alpha=0.25, s=80, 
                   edgecolors='black', linewidth=1, label=condition, zorder=5)
        # Polynomial fit
        if len(data['speeds']) >= 3:
            x_fit, y_fit, _ = create_polynomial_fit(data['speeds'], data['medians'], degree=2)
            ax1.plot(x_fit, y_fit, color=color, linewidth=2, linestyle='--', alpha=0.8, zorder=4)
    
    ax1.set_xlabel('Speed (mm/min)', fontsize=13, fontweight='bold')
    ax1.set_ylabel('Distance to Peak (mm)', fontsize=13, fontweight='bold')
    ax1.set_title('Distance to Peak vs. Speed', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=10, loc='best')
    
    # Plot 2: Propagation Distance
    ax2 = axes[1]
    for condition, data in prop_dist_data.items():
        color = color_map.get(condition, '#808080')
        ax2.scatter(data['all_speeds'], data['all_values'], c=color, alpha=0.05, s=30, edgecolors='none')
        ax2.scatter(data['speeds'], data['medians'], c=color, alpha=0.25, s=80,
                   edgecolors='black', linewidth=1, label=condition, zorder=5)
        if len(data['speeds']) >= 3:
            x_fit, y_fit, _ = create_polynomial_fit(data['speeds'], data['medians'], degree=2)
            ax2.plot(x_fit, y_fit, color=color, linewidth=2, linestyle='--', alpha=0.8, zorder=4)
    
    ax2.set_xlabel('Speed (mm/min)', fontsize=13, fontweight='bold')
    ax2.set_ylabel('Propagation Distance (mm)', fontsize=13, fontweight='bold')
    ax2.set_title('Propagation Distance vs. Speed', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend(fontsize=10, loc='best')
    
    plt.tight_layout()
    
    # Save
    if output_path is None:
        output_path = Path(master_folder) / "MASTER_distance_analysis_MEDIAN.png"
    
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    print(f"\nDistance analysis plot (MEDIAN) saved to: {output_path}")
    
    return fig


def main():
    if len(sys.argv) < 2:
        print("Usage: python plot_master_distance_analysis.py <path_to_V17Tests_folder>")
        return
    
    master_folder = sys.argv[1]
    plot_distance_analysis(master_folder)


if __name__ == "__main__":
    main()
