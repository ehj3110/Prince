"""
Single Session Master Plot Generator
=====================================

Minimal adaptation of master_plotter.py to generate master plots for a single session.
Uses the exact same plot format as batch processing master plots.

This reads the automated_work_of_adhesion.csv file and creates master plots
showing how metrics change with contact area (geometry) across all layers.
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from pathlib import Path
import argparse


def generate_single_session_master_plot(session_dir, dpi=300):
    """
    Generate master plot for a single session using the standard format.
    
    Args:
        session_dir: Path to session directory containing automated_work_of_adhesion.csv
        dpi: Resolution for saved figure
    """
    session_path = Path(session_dir)
    woa_file = session_path / "automated_work_of_adhesion.csv"
    
    if not woa_file.exists():
        print(f"❌ ERROR: Work of adhesion file not found at: {woa_file}")
        return False
    
    print(f"Loading work of adhesion data from: {woa_file}")
    df_raw = pd.read_csv(woa_file)
    
    # Convert to format expected by master plotter
    # Rename columns to match batch processing format
    df = pd.DataFrame({
        'condition_label': 'Single Session',  # Single condition
        'area_mm2': df_raw['Cross_Sectional_Area_mm2'],
        'peak_force_N': df_raw['Peak_Force_N'],
        'work_of_adhesion_mJ': df_raw['Work_of_Adhesion_mJ'],
        'peel_distance_mm': df_raw['Total_Peel_Distance_mm'],
        'peak_retraction_force_N': df_raw['Peak_Retraction_Force_N'],
        'distance_to_peak_mm': df_raw['Distance_to_Peak_mm'],
        'propagation_distance_mm': df_raw['Distance_to_Propagate_mm'],
        'total_peel_time_s': df_raw['Total_Duration_s']
    })
    
    print(f"Total layers: {len(df)}")
    print(f"Area range: {df['area_mm2'].min():.2f} to {df['area_mm2'].max():.2f} mm²")
    
    # Generate the standard area analysis plot (4 metrics: Force, Work, Distance, Retraction)
    print("\nGenerating master area analysis plot...")
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Master Area Analysis', fontsize=16, fontweight='bold')
    axes = axes.flatten()
    
    # Use single color since we only have one condition
    color = plt.cm.tab10(0)
    
    # Metrics to plot
    metrics = [
        ('peak_force_N', 'Peak Force (N)'),
        ('work_of_adhesion_mJ', 'Work of Adhesion (mJ)'),
        ('peel_distance_mm', 'Peel Distance (mm)'),
        ('peak_retraction_force_N', 'Peak Retraction Force (N)')
    ]
    
    # Plot each metric
    for idx, (metric_col, ylabel) in enumerate(metrics):
        ax = axes[idx]
        
        # Apply absolute value for distance metric
        data_to_plot = df[metric_col].copy()
        if metric_col == 'peel_distance_mm':
            data_to_plot = data_to_plot.abs()
        
        # Group by area and calculate mean + SEM
        df_temp = df.copy()
        df_temp[metric_col] = data_to_plot
        grouped = df_temp.groupby('area_mm2')[metric_col].agg(['mean', 'sem'])
        areas = grouped.index.values
        means = grouped['mean'].values
        sems = grouped['sem'].values
        
        # Plot mean with markers
        ax.plot(areas, means, 'o', color=color, markersize=3, alpha=0.7, label='Single Session')
        
        # Add shaded SEM region
        ax.fill_between(areas, means - sems, means + sems, color=color, alpha=0.2)
        
        # Add polynomial trendline
        if len(areas) > 2:
            try:
                z = np.polyfit(areas, means, 2)
                p = np.poly1d(z)
                area_smooth = np.linspace(areas.min(), areas.max(), 100)
                ax.plot(area_smooth, p(area_smooth), '-', color=color, linewidth=1.5, alpha=0.8)
            except:
                pass  # Skip trendline if fitting fails
        
        # Format subplot
        ax.set_xlabel('Contact Area (mm²)', fontsize=11)
        ax.set_ylabel(ylabel, fontsize=11)
        ax.legend(fontsize=8, loc='best')
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save figure
    output_file = session_path / "MASTER_area_analysis.png"
    plt.savefig(output_file, dpi=dpi, bbox_inches='tight')
    print(f"✅ Saved: {output_file}")
    
    plt.close()
    
    # Generate the modified area analysis plot (4 metrics: Force, Work, Distance, Time)
    print("\nGenerating modified master area analysis plot...")
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Master Area Analysis', fontsize=16, fontweight='bold')
    axes = axes.flatten()
    
    # Metrics to plot (with peel time instead of retraction force)
    metrics_modified = [
        ('peak_force_N', 'Peak Force (N)'),
        ('work_of_adhesion_mJ', 'Work of Adhesion (mJ)'),
        ('peel_distance_mm', 'Peel Distance (mm)'),
        ('total_peel_time_s', 'Total Peel Time (s)')
    ]
    
    # Plot each metric
    for idx, (metric_col, ylabel) in enumerate(metrics_modified):
        ax = axes[idx]
        
        # Apply absolute value for distance metric
        data_to_plot = df[metric_col].copy()
        if metric_col == 'peel_distance_mm':
            data_to_plot = data_to_plot.abs()
        
        # Group by area and calculate mean + SEM
        df_temp = df.copy()
        df_temp[metric_col] = data_to_plot
        grouped = df_temp.groupby('area_mm2')[metric_col].agg(['mean', 'sem'])
        areas = grouped.index.values
        means = grouped['mean'].values
        sems = grouped['sem'].values
        
        # Plot mean with markers
        ax.plot(areas, means, 'o', color=color, markersize=3, alpha=0.7, label='Single Session')
        
        # Add shaded SEM region
        ax.fill_between(areas, means - sems, means + sems, color=color, alpha=0.2)
        
        # Add polynomial trendline
        if len(areas) > 2:
            try:
                z = np.polyfit(areas, means, 2)
                p = np.poly1d(z)
                area_smooth = np.linspace(areas.min(), areas.max(), 100)
                ax.plot(area_smooth, p(area_smooth), '-', color=color, linewidth=1.5, alpha=0.8)
            except:
                pass  # Skip trendline if fitting fails
        
        # Format subplot
        ax.set_xlabel('Contact Area (mm²)', fontsize=11)
        ax.set_ylabel(ylabel, fontsize=11)
        ax.legend(fontsize=8, loc='best')
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save figure (overwrite the previous one with this version)
    output_file = session_path / "MASTER_area_analysis.png"
    plt.savefig(output_file, dpi=dpi, bbox_inches='tight')
    print(f"✅ Saved: {output_file}")
    
    plt.close()
    
    # Generate the distance analysis plot
    print("\nGenerating distance analysis plot...")
    
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    fig.suptitle('Master Distance Analysis', fontsize=16, fontweight='bold')
    
    # Metrics to plot
    metrics_distance = [
        ('distance_to_peak_mm', 'Pre-Initiation Distance (mm)'),
        ('propagation_distance_mm', 'Propagation Distance (mm)')
    ]
    
    # Plot each metric
    for idx, (metric_col, ylabel) in enumerate(metrics_distance):
        ax = axes[idx]
        
        # Apply absolute value
        data_to_plot = df[metric_col].abs()
        
        # Group by area and calculate mean + SEM
        df_temp = df.copy()
        df_temp[metric_col] = data_to_plot
        grouped = df_temp.groupby('area_mm2')[metric_col].agg(['mean', 'sem'])
        areas = grouped.index.values
        means = grouped['mean'].values
        sems = grouped['sem'].values
        
        # Plot mean with markers
        ax.plot(areas, means, 'o', color=color, markersize=3, alpha=0.7, label='Single Session')
        
        # Add shaded SEM region
        ax.fill_between(areas, means - sems, means + sems, color=color, alpha=0.2)
        
        # Add polynomial trendline
        if len(areas) > 2:
            try:
                z = np.polyfit(areas, means, 2)
                p = np.poly1d(z)
                area_smooth = np.linspace(areas.min(), areas.max(), 100)
                ax.plot(area_smooth, p(area_smooth), '-', color=color, linewidth=1.5, alpha=0.8)
            except:
                pass  # Skip trendline if fitting fails
        
        # Format subplot
        ax.set_xlabel('Contact Area (mm²)', fontsize=11)
        ax.set_ylabel(ylabel, fontsize=11)
        ax.legend(fontsize=8, loc='best')
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save figure
    output_file = session_path / "MASTER_distance_analysis.png"
    plt.savefig(output_file, dpi=dpi, bbox_inches='tight')
    print(f"✅ Saved: {output_file}")
    
    plt.close()
    
    print("\n" + "="*70)
    print("✅ COMPLETE - All master plots generated in standard format!")
    print("="*70)
    
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate master plots for a single session in standard format')
    parser.add_argument('session_dir', nargs='?', 
                       default=r"C:\Users\cheng sun\BoyuanSun\Slicing\Evan\SteppedCone_V1_10mm2to100mm2_50umLayers_V2\Printing_Logs\2025-11-29\Print 2 - Complete",
                       help='Path to the print session directory')
    parser.add_argument('--dpi', type=int, default=300, help='Resolution for saved figures (default: 300)')
    
    args = parser.parse_args()
    
    print("="*70)
    print("MASTER PLOT GENERATOR - Single Session (Standard Format)")
    print("="*70)
    print(f"Session: {args.session_dir}")
    print(f"DPI: {args.dpi}")
    print()
    
    generate_single_session_master_plot(args.session_dir, dpi=args.dpi)
