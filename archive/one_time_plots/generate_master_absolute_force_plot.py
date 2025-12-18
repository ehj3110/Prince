"""
Generate Master Absolute Peak Force Plot
=========================================

Creates a master plot showing absolute peak force (peak force - baseline force)
vs layer number and radius, similar to the first subplot of the master radius analysis
but using the full force magnitude from the negative baseline.

Author: Cheng Sun Lab
Date: December 10, 2025
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from scipy.optimize import curve_fit
import sys


def power_law_func(x, a, b):
    """Power law function: y = a * x^b"""
    return a * np.power(x, b)


def fit_power_law(x, y):
    """Fit power law with error handling"""
    try:
        # Filter positive values
        mask = (x > 0) & (y > 0)
        x_clean, y_clean = x[mask], y[mask]
        
        if len(x_clean) < 3:
            return None, None
        
        # Initial guess
        p0 = [np.mean(y_clean), 1.0]
        
        # Fit
        popt, _ = curve_fit(power_law_func, x_clean, y_clean, p0=p0, 
                           bounds=([0, -np.inf], [np.inf, np.inf]), maxfev=10000)
        
        # Calculate R-squared
        y_pred = power_law_func(x_clean, *popt)
        ss_res = np.sum((y_clean - y_pred) ** 2)
        ss_tot = np.sum((y_clean - np.mean(y_clean)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        return popt, r_squared
    except:
        return None, None


def generate_master_absolute_force_plot(csv_path: Path, output_dir: Path):
    """
    Generate master absolute peak force plot with Layer vs Force and Radius vs Force
    
    Args:
        csv_path: Path to MASTER_all_metrics.csv
        output_dir: Directory to save plot
    """
    # Read data
    df = pd.read_csv(csv_path)
    
    # Check for required columns
    if 'peak_force_N' not in df.columns:
        print("ERROR: peak_force_N column not found")
        return
    
    if 'baseline_force_N' not in df.columns:
        print("ERROR: baseline_force_N column not found")
        return
    
    if 'layer_number' not in df.columns:
        print("ERROR: layer_number column not found")
        return
    
    # Calculate absolute peak force (peak - baseline)
    df['absolute_peak_force_N'] = df['peak_force_N'] - df['baseline_force_N']
    
    # Calculate radius from area if needed
    if 'radius_mm' not in df.columns and 'area_mm2' in df.columns:
        df['radius_mm'] = np.sqrt(df['area_mm2'] / np.pi)
    
    if 'radius_mm' not in df.columns:
        print("ERROR: Cannot calculate radius - area_mm2 column not found")
        return
    
    # Get condition column - prioritize detailed_condition to keep datasets separate
    condition_col = None
    for col in ['detailed_condition', 'folder', 'condition_label', 'membrane_type']:
        if col in df.columns:
            condition_col = col
            break
    
    if condition_col is None:
        print("ERROR: No condition column found")
        return
    
    # Filter out invalid forces
    df = df[df['absolute_peak_force_N'] > 0].copy()
    
    print(f"\nGenerating Master Absolute Peak Force Plot")
    print(f"  Total measurements: {len(df)}")
    print(f"  Conditions: {df[condition_col].nunique()}")
    print(f"  Absolute peak force range: {df['absolute_peak_force_N'].min():.4f} - {df['absolute_peak_force_N'].max():.4f} N")
    
    # Create 1x2 subplot figure
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7))
    fig.suptitle('Master Absolute Peak Force Analysis\n(Peak Force - Baseline Force)', 
                 fontsize=16, fontweight='bold', y=0.98)
    
    # Color scheme - one color per condition
    conditions = sorted(df[condition_col].unique())
    colors = plt.cm.Set2(np.linspace(0, 1, len(conditions)))
    
    # ============================================
    # Plot 1: Layer vs Absolute Peak Force
    # ============================================
    for idx, condition in enumerate(conditions):
        df_cond = df[df[condition_col] == condition]
        
        x = df_cond['layer_number'].values
        y = df_cond['absolute_peak_force_N'].values
        
        # Remove NaN
        mask = ~(np.isnan(x) | np.isnan(y))
        x_clean, y_clean = x[mask], y[mask]
        
        if len(x_clean) < 3:
            continue
        
        color = colors[idx]
        
        # Plot individual points with transparency
        ax1.scatter(x_clean, y_clean, alpha=0.4, s=40, color=color, 
                   label=f'{condition} (n={len(x_clean)})')
        
        # Fit power law
        popt, r_squared = fit_power_law(x_clean, y_clean)
        
        if popt is not None:
            x_fit = np.linspace(x_clean.min(), x_clean.max(), 100)
            y_fit = power_law_func(x_fit, *popt)
            
            ax1.plot(x_fit, y_fit, '-', color=color, linewidth=2.5, alpha=0.8)
            
            # Add equation to legend label
            eq_text = f'  [{popt[0]:.3f} × x^{popt[1]:.3f}, R²={r_squared:.3f}]'
            
            # Update legend entry
            handles, labels = ax1.get_legend_handles_labels()
            if handles:
                labels[-1] = labels[-1] + eq_text
                ax1.legend(handles, labels, fontsize=9, loc='best', framealpha=0.9)
    
    ax1.set_xlabel('Layer Number', fontsize=13, fontweight='bold')
    ax1.set_ylabel('Absolute Peak Force (N)', fontsize=13, fontweight='bold')
    ax1.set_title('Layer vs Absolute Peak Force', fontsize=14, fontweight='bold', pad=10)
    ax1.grid(True, alpha=0.3, linestyle='--')
    ax1.legend(fontsize=9, loc='best', framealpha=0.9)
    
    # ============================================
    # Plot 2: Radius vs Absolute Peak Force
    # ============================================
    for idx, condition in enumerate(conditions):
        df_cond = df[df[condition_col] == condition]
        
        x = df_cond['radius_mm'].values
        y = df_cond['absolute_peak_force_N'].values
        
        # Remove NaN
        mask = ~(np.isnan(x) | np.isnan(y))
        x_clean, y_clean = x[mask], y[mask]
        
        if len(x_clean) < 3:
            continue
        
        color = colors[idx]
        
        # Plot individual points with transparency
        ax2.scatter(x_clean, y_clean, alpha=0.4, s=40, color=color,
                   label=f'{condition} (n={len(x_clean)})')
        
        # Fit power law
        popt, r_squared = fit_power_law(x_clean, y_clean)
        
        if popt is not None:
            x_fit = np.linspace(x_clean.min(), x_clean.max(), 100)
            y_fit = power_law_func(x_fit, *popt)
            
            ax2.plot(x_fit, y_fit, '-', color=color, linewidth=2.5, alpha=0.8)
            
            # Add equation to legend label
            eq_text = f'  [{popt[0]:.3f} × x^{popt[1]:.3f}, R²={r_squared:.3f}]'
            
            # Update legend entry
            handles, labels = ax2.get_legend_handles_labels()
            if handles:
                labels[-1] = labels[-1] + eq_text
                ax2.legend(handles, labels, fontsize=9, loc='best', framealpha=0.9)
    
    ax2.set_xlabel('Radius (mm)', fontsize=13, fontweight='bold')
    ax2.set_ylabel('Absolute Peak Force (N)', fontsize=13, fontweight='bold')
    ax2.set_title('Radius vs Absolute Peak Force', fontsize=14, fontweight='bold', pad=10)
    ax2.grid(True, alpha=0.3, linestyle='--')
    ax2.legend(fontsize=9, loc='best', framealpha=0.9)
    
    # Adjust layout and save
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    
    output_path = output_dir / "MASTER_absolute_peak_force_analysis.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"\n✓ Saved: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_master_absolute_force_plot.py <path_to_MASTER_all_metrics.csv>")
        sys.exit(1)
    
    csv_path = Path(sys.argv[1])
    
    if not csv_path.exists():
        print(f"ERROR: File not found: {csv_path}")
        sys.exit(1)
    
    output_dir = csv_path.parent
    generate_master_absolute_force_plot(csv_path, output_dir)
