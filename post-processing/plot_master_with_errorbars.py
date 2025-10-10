#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Master Plotting Functions with Error Bars
==========================================

Generates 4 types of master plots:
1. Speed Analysis (Mean + SEM error bars)
2. Speed Analysis (Median + IQR error bars)
3. Distance Analysis (Mean + SEM error bars)
4. Distance Analysis (Median + IQR error bars)

Features:
- No individual data points (clean visualization)
- Smaller marker sizes for mean/median points
- Error bars showing uncertainty
- Polynomial trendlines
- Support for USW (Unsealed Water) fluid type

Author: Cheng Sun Lab Team
Date: October 6, 2025
"""

import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from scipy.stats import sem

# Safe print function that handles encoding errors
def safe_print(msg):
    try:
        print(msg)
    except UnicodeEncodeError:
        # Fallback to ASCII-only
        print(msg.encode('ascii', 'ignore').decode('ascii'))

# Color mapping for different conditions
CONDITION_COLORS = {
    'Water_1mm': '#1f77b4',      # Blue
    'Water_5mm': '#ff7f0e',      # Orange
    'USW_1mm': '#17becf',        # Cyan
    'USW_5mm': '#bcbd22',        # Yellow-green
    '2p5PEO_1mm': '#2ca02c',     # Green
    '2p5PEO_5mm': '#d62728',     # Red
    'PEO_1mm': '#9467bd',        # Purple
    'PEO_5mm': '#8c564b'         # Brown
}

def prepare_data_by_condition(df):
    """Group data by condition (Fluid_Gap combination)."""
    conditions = {}
    
    for _, row in df.iterrows():
        # Check for both capitalized and lowercase column names
        fluid = row.get('fluid_type', row.get('Fluid', 'Unknown'))
        gap = row.get('gap', row.get('Gap', 'Unknown'))
        condition_name = f"{fluid}_{gap}"
        
        if condition_name not in conditions:
            conditions[condition_name] = []
        conditions[condition_name].append(row)
    
    # Convert to DataFrames
    for cond in conditions:
        conditions[cond] = pd.DataFrame(conditions[cond])
    
    return conditions

def calculate_mean_stats(df, speed_col, value_col):
    """
    Calculate mean and SEM for each speed.
    
    Args:
        df: DataFrame for one condition
        speed_col: Column name for speed
        value_col: Column name for metric
        
    Returns:
        Dictionary with speeds, means, and SEM bounds
    """
    # Group by speed and calculate mean and SEM
    grouped = df.groupby(speed_col)[value_col].agg(['mean', sem])
    
    speeds = grouped.index.values
    means = grouped['mean'].values
    sems = grouped['sem'].values
    
    # Sort by speed
    sort_idx = np.argsort(speeds)
    
    return {
        'speeds': speeds[sort_idx],
        'means': means[sort_idx],
        'sems': sems[sort_idx]
    }

def calculate_median_stats(df, speed_col, value_col):
    """
    Calculate median and IQR for each speed.
    
    Args:
        df: DataFrame for one condition
        speed_col: Column name for speed
        value_col: Column name for metric
        
    Returns:
        Dictionary with speeds, medians, and IQR bounds
    """
    # Group by speed and calculate statistics
    grouped = df.groupby(speed_col)[value_col].agg([
        ('median', 'median'),
        ('q1', lambda x: x.quantile(0.25)),
        ('q3', lambda x: x.quantile(0.75))
    ])
    
    speeds = grouped.index.values
    medians = grouped['median'].values
    q1 = grouped['q1'].values
    q3 = grouped['q3'].values
    
    # IQR error bars (distance from median to Q1 and Q3)
    lower_err = medians - q1
    upper_err = q3 - medians
    
    # Sort by speed
    sort_idx = np.argsort(speeds)
    
    return {
        'speeds': speeds[sort_idx],
        'medians': medians[sort_idx],
        'lower_err': lower_err[sort_idx],
        'upper_err': upper_err[sort_idx]
    }

def plot_with_trendline(ax, x, y, color, label, yerr=None, poly_degree=2):
    """
    Plot data points with error bars and polynomial trendline.
    
    Args:
        ax: Matplotlib axis
        x: X data (speeds)
        y: Y data (metric values)
        color: Color for this condition
        label: Label for legend
        yerr: Error bar values (SEM or IQR)
        poly_degree: Degree of polynomial fit
    """
    # Plot mean/median points with error bars
    if yerr is not None:
        ax.errorbar(x, y, yerr=yerr, fmt='o', color=color, label=label,
                   markersize=6, capsize=4, capthick=1.5, elinewidth=1.5, alpha=0.8)
    else:
        ax.plot(x, y, 'o', color=color, label=label, markersize=6, alpha=0.8)
    
    # Add polynomial trendline
    if len(x) > poly_degree:
        coeffs = np.polyfit(x, y, poly_degree)
        poly = np.poly1d(coeffs)
        x_smooth = np.linspace(x.min(), x.max(), 100)
        ax.plot(x_smooth, poly(x_smooth), '-', color=color, alpha=0.5, linewidth=2)

def plot_master_speed_mean(df, output_path):
    """
    Generate master speed analysis plot with MEAN values and SEM error bars.
    
    Creates 4 subplots:
    - Work of Adhesion vs Speed
    - Peak Adhesion Force vs Speed
    - Distance to Peak vs Speed
    - Peel Distance vs Speed
    """
    safe_print("  Generating Speed-Mean plot...")
    
    # Prepare data
    if 'speed_mm_min' not in df.columns and 'Speed_um_s' in df.columns:
        df['speed_mm_min'] = df['Speed_um_s'] / 1000.0 * 60.0
    
    speed_col = 'speed_mm_min'
    
    # Ensure we have absolute retraction force (handle None/NaN values)
    retraction_col = 'Peak_Retraction_Force_N' if 'Peak_Retraction_Force_N' in df.columns else 'peak_retraction_force_N'
    df['abs_retraction'] = df[retraction_col].fillna(0).abs()
    
    # Group by condition
    conditions = prepare_data_by_condition(df)
    
    # Create figure
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Master Speed Analysis - MEAN +/- SEM', fontsize=18, fontweight='bold')
    
    metrics = [
        ('work_of_adhesion_mJ', 'Work_of_Adhesion_mJ', 'Work of Adhesion (mJ)', axes[0, 0]),
        ('abs_retraction', 'abs_retraction', 'Peak Adhesion Force (N)', axes[0, 1]),
        ('distance_to_peak_mm', 'Distance_to_Peak_mm', 'Distance to Peak (mm)', axes[1, 0]),
        ('propagation_distance_mm', 'Peel_Distance_mm', 'Propagation Distance (mm)', axes[1, 1])
    ]
    
    for metric_name, metric_col_alt, ylabel, ax in metrics:
        # Try both column name variations
        if metric_name in df.columns:
            metric_col = metric_name
        elif metric_col_alt in df.columns:
            metric_col = metric_col_alt
        else:
            continue
        
        for cond_name, cond_df in conditions.items():
            # Skip if no valid data
            if cond_df[metric_col].isna().all():
                continue
            
            # Calculate statistics
            stats = calculate_mean_stats(cond_df, speed_col, metric_col)
            
            # Get color
            color = CONDITION_COLORS.get(cond_name, '#808080')
            
            # Plot with error bars
            plot_with_trendline(ax, stats['speeds'], stats['means'], color, 
                              cond_name, yerr=stats['sems'])
        
        ax.set_xlabel('Peel Speed (mm/min)', fontsize=12)
        ax.set_ylabel(ylabel, fontsize=12)
        ax.legend(fontsize=9, loc='best')
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    safe_print(f"  Saved: {Path(output_path).name}")

def plot_master_speed_median(df, output_path):
    """
    Generate master speed analysis plot with MEDIAN values and IQR error bars.
    """
    safe_print("  Generating Speed-Median plot...")
    
    # Prepare data
    if 'speed_mm_min' not in df.columns and 'Speed_um_s' in df.columns:
        df['speed_mm_min'] = df['Speed_um_s'] / 1000.0 * 60.0
    
    speed_col = 'speed_mm_min'
    
    # Ensure we have absolute retraction force (handle None/NaN values)
    retraction_col = 'Peak_Retraction_Force_N' if 'Peak_Retraction_Force_N' in df.columns else 'peak_retraction_force_N'
    df['abs_retraction'] = df[retraction_col].fillna(0).abs()
    
    # Group by condition
    conditions = prepare_data_by_condition(df)
    
    # Create figure
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Master Speed Analysis - MEDIAN +/- IQR', fontsize=18, fontweight='bold')
    
    metrics = [
        ('work_of_adhesion_mJ', 'Work_of_Adhesion_mJ', 'Work of Adhesion (mJ)', axes[0, 0]),
        ('abs_retraction', 'abs_retraction', 'Peak Adhesion Force (N)', axes[0, 1]),
        ('distance_to_peak_mm', 'Distance_to_Peak_mm', 'Distance to Peak (mm)', axes[1, 0]),
        ('propagation_distance_mm', 'Peel_Distance_mm', 'Propagation Distance (mm)', axes[1, 1])
    ]
    
    for metric_name, metric_col_alt, ylabel, ax in metrics:
        # Try both column name variations
        if metric_name in df.columns:
            metric_col = metric_name
        elif metric_col_alt in df.columns:
            metric_col = metric_col_alt
        else:
            continue
        
        for cond_name, cond_df in conditions.items():
            # Skip if no valid data
            if cond_df[metric_col].isna().all():
                continue
            
            # Calculate statistics
            stats = calculate_median_stats(cond_df, speed_col, metric_col)
            
            # Get color
            color = CONDITION_COLORS.get(cond_name, '#808080')
            
            # Plot with IQR error bars
            yerr = np.array([stats['lower_err'], stats['upper_err']])
            plot_with_trendline(ax, stats['speeds'], stats['medians'], color, 
                              cond_name, yerr=yerr)
        
        ax.set_xlabel('Peel Speed (mm/min)', fontsize=12)
        ax.set_ylabel(ylabel, fontsize=12)
        ax.legend(fontsize=9, loc='best')
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    safe_print(f"  Saved: {Path(output_path).name}")

def plot_master_distance_mean(df, output_path):
    """
    Generate master distance analysis plot with MEAN values and SEM error bars.
    
    2 subplots:
    - Distance to Peak vs Speed
    - Propagation Distance vs Speed
    """
    safe_print("  Generating Distance-Mean plot...")
    
    # Prepare data
    if 'speed_mm_min' not in df.columns and 'Speed_um_s' in df.columns:
        df['speed_mm_min'] = df['Speed_um_s'] / 1000.0 * 60.0
    
    speed_col = 'speed_mm_min'
    
    # Check for distance columns
    dist_to_peak_col = 'Distance_to_Peak_mm' if 'Distance_to_Peak_mm' in df.columns else 'distance_to_peak_mm'
    prop_dist_col = 'Propagation_Distance_mm' if 'Propagation_Distance_mm' in df.columns else 'propagation_distance_mm'
    
    # Group by condition
    conditions = prepare_data_by_condition(df)
    
    # Create figure
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    fig.suptitle('Master Distance Analysis - MEAN +/- SEM', fontsize=18, fontweight='bold')
    
    metrics = [
        (dist_to_peak_col, 'Distance to Peak (mm)', axes[0]),
        (prop_dist_col, 'Propagation Distance (mm)', axes[1])
    ]
    
    for metric_col, ylabel, ax in metrics:
        if metric_col not in df.columns:
            continue
        
        for cond_name, cond_df in conditions.items():
            # Skip if no valid data
            if cond_df[metric_col].isna().all():
                continue
            
            # Calculate statistics
            stats = calculate_mean_stats(cond_df, speed_col, metric_col)
            
            # Get color
            color = CONDITION_COLORS.get(cond_name, '#808080')
            
            # Plot with error bars
            plot_with_trendline(ax, stats['speeds'], stats['means'], color, 
                              cond_name, yerr=stats['sems'])
        
        ax.set_xlabel('Peel Speed (mm/min)', fontsize=12)
        ax.set_ylabel(ylabel, fontsize=12)
        ax.legend(fontsize=9, loc='best')
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    safe_print(f"  Saved: {Path(output_path).name}")

def plot_master_distance_median(df, output_path):
    """
    Generate master distance analysis plot with MEDIAN values and IQR error bars.
    """
    safe_print("  Generating Distance-Median plot...")
    
    # Prepare data
    if 'speed_mm_min' not in df.columns and 'Speed_um_s' in df.columns:
        df['speed_mm_min'] = df['Speed_um_s'] / 1000.0 * 60.0
    
    speed_col = 'speed_mm_min'
    
    # Check for distance columns
    dist_to_peak_col = 'Distance_to_Peak_mm' if 'Distance_to_Peak_mm' in df.columns else 'distance_to_peak_mm'
    prop_dist_col = 'Propagation_Distance_mm' if 'Propagation_Distance_mm' in df.columns else 'propagation_distance_mm'
    
    # Group by condition
    conditions = prepare_data_by_condition(df)
    
    # Create figure
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    fig.suptitle('Master Distance Analysis - MEDIAN +/- IQR', fontsize=18, fontweight='bold')
    
    metrics = [
        (dist_to_peak_col, 'Distance to Peak (mm)', axes[0]),
        (prop_dist_col, 'Propagation Distance (mm)', axes[1])
    ]
    
    for metric_col, ylabel, ax in metrics:
        if metric_col not in df.columns:
            continue
        
        for cond_name, cond_df in conditions.items():
            # Skip if no valid data
            if cond_df[metric_col].isna().all():
                continue
            
            # Calculate statistics
            stats = calculate_median_stats(cond_df, speed_col, metric_col)
            
            # Get color
            color = CONDITION_COLORS.get(cond_name, '#808080')
            
            # Plot with IQR error bars
            yerr = np.array([stats['lower_err'], stats['upper_err']])
            plot_with_trendline(ax, stats['speeds'], stats['medians'], color, 
                              cond_name, yerr=yerr)
        
        ax.set_xlabel('Peel Speed (mm/min)', fontsize=12)
        ax.set_ylabel(ylabel, fontsize=12)
        ax.legend(fontsize=9, loc='best')
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    safe_print(f"  Saved: {Path(output_path).name}")

if __name__ == "__main__":
    safe_print("\nMaster plotting module loaded successfully!")
    safe_print("This module provides 4 plotting functions:")
    safe_print("  - plot_master_speed_mean()")
    safe_print("  - plot_master_speed_median()")
    safe_print("  - plot_master_distance_mean()")
    safe_print("  - plot_master_distance_median()")
