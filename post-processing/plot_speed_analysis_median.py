#!/usr/bin/env python3
"""
Generate speed vs. metrics analysis plots from autolog_metrics.csv
Uses MEDIAN instead of MEAN for averaging.
"""

import sys
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import numpy as np


def calculate_median_values(df, speed_col, value_col):
    """
    Calculate MEDIAN values for each unique speed.
    
    Args:
        df: DataFrame with the data
        speed_col: Column name for speeds
        value_col: Column name for values to average
        
    Returns:
        unique_speeds: Sorted array of unique speeds
        median_values: Array of median values for each speed
        std_values: Array of standard deviations for each speed
        all_speeds: Array of all individual speed values (for scatter plot)
        all_values: Array of all individual values (for scatter plot)
    """
    # Get all individual data points
    all_speeds = df[speed_col].values
    all_values = df[value_col].values
    
    # Group by speed and calculate statistics
    grouped = df.groupby(speed_col)[value_col].agg(['median', 'std', 'count'])
    unique_speeds = grouped.index.values
    median_values = grouped['median'].values
    std_values = grouped['std'].fillna(0).values  # Replace NaN with 0 for single samples
    
    # Sort by speed
    sort_idx = np.argsort(unique_speeds)
    unique_speeds = unique_speeds[sort_idx]
    median_values = median_values[sort_idx]
    std_values = std_values[sort_idx]
    
    return unique_speeds, median_values, std_values, all_speeds, all_values


def create_polynomial_fit(x, y, degree=2):
    """
    Create a 2nd order polynomial fit through the data points.
    
    Args:
        x: X values (must be sorted)
        y: Y values
        degree: Polynomial degree (default=2 for quadratic)
        
    Returns:
        x_fit: X values for the fit line
        y_fit: Y values for the fit line
        coeffs: Polynomial coefficients
    """
    if len(x) < degree + 1:
        # Not enough points for polynomial, return line
        return x, y, None
    
    # Fit polynomial
    coeffs = np.polyfit(x, y, degree)
    poly_func = np.poly1d(coeffs)
    
    # Create smooth x values for plotting
    x_fit = np.linspace(x.min(), x.max(), 100)
    y_fit = poly_func(x_fit)
    
    return x_fit, y_fit, coeffs


def plot_speed_analysis(csv_path, output_path=None):
    """
    Create a 4-subplot figure showing speed vs various metrics.
    Calculates MEDIAN values for each speed and plots with polynomial fits.
    
    Args:
        csv_path: Path to autolog_metrics.csv file
        output_path: Optional path to save the figure
    """
    # Read the CSV file
    df = pd.read_csv(csv_path)
    
    # Print available columns for debugging
    print(f"Available columns: {df.columns.tolist()}")
    
    # Determine column names - handle different naming conventions
    speed_col = None
    if 'Speed_um_s' in df.columns:
        # Convert µm/s to mm/min for plotting
        df['speed_mm_min'] = df['Speed_um_s'] / 1000.0 * 60.0
        speed_col = 'speed_mm_min'
    elif 'speed_mm_min' in df.columns:
        speed_col = 'speed_mm_min'
    else:
        raise ValueError(f"Could not find speed column. Available columns: {df.columns.tolist()}")
    
    # Determine other column names
    peak_force_col = 'Peak_Force_N' if 'Peak_Force_N' in df.columns else 'peak_force_N'
    woa_col = 'Work_of_Adhesion_mJ' if 'Work_of_Adhesion_mJ' in df.columns else 'work_of_adhesion_mJ'
    retraction_col = 'Peak_Retraction_Force_N' if 'Peak_Retraction_Force_N' in df.columns else 'peak_retraction_force_N'
    peel_dist_col = 'Total_Peel_Distance_mm' if 'Total_Peel_Distance_mm' in df.columns else 'peel_distance_mm'
    
    # Calculate median values for each metric
    print("\nCalculating MEDIAN values for each speed...")
    
    # Peak Force
    speeds_pf, median_pf, std_pf, all_speeds_pf, all_pf = calculate_median_values(df, speed_col, peak_force_col)
    print(f"  Peak Force: {len(speeds_pf)} unique speeds")
    
    # Work of Adhesion
    speeds_woa, median_woa, std_woa, all_speeds_woa, all_woa = calculate_median_values(df, speed_col, woa_col)
    print(f"  Work of Adhesion: {len(speeds_woa)} unique speeds")
    
    # Peel Distance
    speeds_pd, median_pd, std_pd, all_speeds_pd, all_pd = calculate_median_values(df, speed_col, peel_dist_col)
    print(f"  Peel Distance: {len(speeds_pd)} unique speeds")
    
    # Peak Retraction (take absolute value)
    df['abs_retraction'] = np.abs(df[retraction_col])
    speeds_pr, median_pr, std_pr, all_speeds_pr, all_pr = calculate_median_values(df, speed_col, 'abs_retraction')
    print(f"  Peak Retraction: {len(speeds_pr)} unique speeds")
    
    # Define consistent colors for each metric (used across all plots)
    color_scheme = {
        'peak_force': '#2E86AB',      # Blue
        'work_adhesion': '#A23B72',   # Purple
        'peel_distance': '#F18F01',   # Orange
        'retraction': '#C73E1D'       # Red
    }
    
    # Create 2nd order polynomial fits for each metric
    x_fit_pf, y_fit_pf, coeffs_pf = create_polynomial_fit(speeds_pf, median_pf, degree=2)
    x_fit_woa, y_fit_woa, coeffs_woa = create_polynomial_fit(speeds_woa, median_woa, degree=2)
    x_fit_pd, y_fit_pd, coeffs_pd = create_polynomial_fit(speeds_pd, median_pd, degree=2)
    x_fit_pr, y_fit_pr, coeffs_pr = create_polynomial_fit(speeds_pr, median_pr, degree=2)
    
    # Create figure with 4 subplots (2x2 grid)
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Speed Analysis - Adhesion Metrics vs. Peel Speed (MEDIAN)', fontsize=16, fontweight='bold')
    
    # Plot 1: Speed vs Peak Force
    ax1 = axes[0, 0]
    # Individual data points (transparent)
    ax1.scatter(all_speeds_pf, all_pf, c=color_scheme['peak_force'], alpha=0.1, s=50, 
                edgecolors='none', label='Individual layers')
    # Median values (more visible)
    ax1.scatter(speeds_pf, median_pf, c=color_scheme['peak_force'], alpha=0.6, s=100, 
                edgecolors='black', linewidth=1, label='Median values', zorder=5)
    # Polynomial fit line
    if coeffs_pf is not None:
        ax1.plot(x_fit_pf, y_fit_pf, color=color_scheme['peak_force'], linewidth=2.5, 
                 label='2nd order fit', zorder=4, linestyle='--')
    ax1.set_xlabel('Speed (mm/min)', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Peak Force (N)', fontsize=12, fontweight='bold')
    ax1.set_title('Peak Force vs. Speed', fontsize=13)
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=9, loc='best')
    
    # Plot 2: Speed vs Work of Adhesion
    ax2 = axes[0, 1]
    # Individual data points (transparent)
    ax2.scatter(all_speeds_woa, all_woa, c=color_scheme['work_adhesion'], alpha=0.1, s=50,
                edgecolors='none', label='Individual layers')
    # Median values (more visible)
    ax2.scatter(speeds_woa, median_woa, c=color_scheme['work_adhesion'], alpha=0.6, s=100,
                edgecolors='black', linewidth=1, label='Median values', zorder=5)
    # Polynomial fit line
    if coeffs_woa is not None:
        ax2.plot(x_fit_woa, y_fit_woa, color=color_scheme['work_adhesion'], linewidth=2.5,
                 label='2nd order fit', zorder=4, linestyle='--')
    ax2.set_xlabel('Speed (mm/min)', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Work of Adhesion (mJ)', fontsize=12, fontweight='bold')
    ax2.set_title('Work of Adhesion vs. Speed', fontsize=13)
    ax2.grid(True, alpha=0.3)
    ax2.legend(fontsize=9, loc='best')
    
    # Plot 3: Speed vs Total Peel Distance
    ax3 = axes[1, 0]
    # Individual data points (transparent)
    ax3.scatter(all_speeds_pd, all_pd, c=color_scheme['peel_distance'], alpha=0.1, s=50,
                edgecolors='none', label='Individual layers')
    # Median values (more visible)
    ax3.scatter(speeds_pd, median_pd, c=color_scheme['peel_distance'], alpha=0.6, s=100,
                edgecolors='black', linewidth=1, label='Median values', zorder=5)
    # Polynomial fit line
    if coeffs_pd is not None:
        ax3.plot(x_fit_pd, y_fit_pd, color=color_scheme['peel_distance'], linewidth=2.5,
                 label='2nd order fit', zorder=4, linestyle='--')
    ax3.set_xlabel('Speed (mm/min)', fontsize=12, fontweight='bold')
    ax3.set_ylabel('Total Peel Distance (mm)', fontsize=12, fontweight='bold')
    ax3.set_title('Peel Distance vs. Speed', fontsize=13)
    ax3.grid(True, alpha=0.3)
    ax3.legend(fontsize=9, loc='best')
    
    # Plot 4: Speed vs Peak Retraction Force
    ax4 = axes[1, 1]
    # Individual data points (transparent)
    ax4.scatter(all_speeds_pr, all_pr, c=color_scheme['retraction'], alpha=0.1, s=50,
                edgecolors='none', label='Individual layers')
    # Median values (more visible)
    ax4.scatter(speeds_pr, median_pr, c=color_scheme['retraction'], alpha=0.6, s=100,
                edgecolors='black', linewidth=1, label='Median values', zorder=5)
    # Polynomial fit line
    if coeffs_pr is not None:
        ax4.plot(x_fit_pr, y_fit_pr, color=color_scheme['retraction'], linewidth=2.5,
                 label='2nd order fit', zorder=4, linestyle='--')
    ax4.set_xlabel('Speed (mm/min)', fontsize=12, fontweight='bold')
    ax4.set_ylabel('Peak Retraction Force (N)', fontsize=12, fontweight='bold')
    ax4.set_title('Peak Retraction Force vs. Speed', fontsize=13)
    ax4.grid(True, alpha=0.3)
    ax4.legend(fontsize=9, loc='best')
    
    plt.tight_layout()
    
    # Save or show
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"\nSpeed analysis plot (MEDIAN) saved to: {output_path}")
    else:
        plt.show()
    
    return fig


def main():
    if len(sys.argv) < 2:
        print("Usage: python plot_speed_analysis_median.py <path_to_autolog_metrics.csv>")
        return
    
    csv_path = Path(sys.argv[1])
    
    if not csv_path.exists():
        print(f"Error: File not found: {csv_path}")
        return
    
    # Generate output path in the same directory
    output_path = csv_path.parent / "speed_analysis_MEDIAN.png"
    
    plot_speed_analysis(csv_path, output_path)


if __name__ == "__main__":
    main()
