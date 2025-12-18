"""
Master Stiffness Plot Generator
================================

Generates master stiffness plots showing Layer vs Stiffness and Radius vs Stiffness
for all conditions in a dataset.

Author: Cheng Sun Lab Team
Date: December 10, 2025
"""

import matplotlib
matplotlib.use('Agg')

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from scipy.optimize import curve_fit
from scipy import stats
import sys


def power_law_func(x, a, b):
    """Power law function: y = a * x^b"""
    return a * np.power(x, b)


def fit_power_law(x, y):
    """Fit power law with error handling"""
    try:
        # Filter positive values
        mask = (x > 0) & (y > 0)
        if np.sum(mask) < 3:
            return None, None
        
        x_valid = x[mask]
        y_valid = y[mask]
        
        popt, _ = curve_fit(power_law_func, x_valid, y_valid, 
                           p0=[y_valid.mean(), 1.0],
                           maxfev=5000,
                           bounds=([0, -np.inf], [np.inf, np.inf]))
        
        # Calculate R²
        y_pred = power_law_func(x_valid, *popt)
        ss_res = np.sum((y_valid - y_pred) ** 2)
        ss_tot = np.sum((y_valid - np.mean(y_valid)) ** 2)
        r_squared = 1 - (ss_res / ss_tot)
        
        return popt, r_squared
    except:
        return None, None


def generate_master_stiffness_plot(csv_path: Path, output_dir: Path):
    """
    Generate master stiffness plot with Layer vs Stiffness and Radius vs Stiffness
    
    Args:
        csv_path: Path to MASTER_all_metrics.csv
        output_dir: Directory to save plot
    """
    # Read data
    df = pd.read_csv(csv_path)
    
    # Check for required columns
    if 'material_stiffness_N_per_mm' not in df.columns:
        print("ERROR: material_stiffness_N_per_mm column not found")
        return
    
    if 'layer_number' not in df.columns:
        print("ERROR: layer_number column not found")
        return
    
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
    
    # Filter out zero/invalid stiffness
    df = df[df['material_stiffness_N_per_mm'] > 0].copy()
    
    print(f"\nGenerating Master Stiffness Plot")
    print(f"  Total measurements: {len(df)}")
    print(f"  Conditions: {df[condition_col].nunique()}")
    
    # Create 1x2 subplot figure
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7))
    fig.suptitle('Master Stiffness Analysis', fontsize=16, fontweight='bold', y=0.98)
    
    # Color scheme - one color per condition
    conditions = df[condition_col].unique()
    colors = plt.cm.Set2(np.linspace(0, 1, len(conditions)))
    
    # ============================================
    # Plot 1: Layer vs Stiffness
    # ============================================
    for idx, condition in enumerate(conditions):
        df_cond = df[df[condition_col] == condition]
        
        x = df_cond['layer_number'].values
        y = df_cond['material_stiffness_N_per_mm'].values
        
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
    ax1.set_ylabel('Material Stiffness (N/mm)', fontsize=13, fontweight='bold')
    ax1.set_title('Layer vs Material Stiffness', fontsize=14, fontweight='bold', pad=10)
    ax1.grid(True, alpha=0.3, linestyle='--')
    ax1.legend(fontsize=9, loc='best', framealpha=0.9)
    
    # ============================================
    # Plot 2: Radius vs Stiffness
    # ============================================
    for idx, condition in enumerate(conditions):
        df_cond = df[df[condition_col] == condition]
        
        x = df_cond['radius_mm'].values
        y = df_cond['material_stiffness_N_per_mm'].values
        
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
    
    ax2.set_xlabel('Contact Radius (mm)', fontsize=13, fontweight='bold')
    ax2.set_ylabel('Material Stiffness (N/mm)', fontsize=13, fontweight='bold')
    ax2.set_title('Radius vs Material Stiffness', fontsize=14, fontweight='bold', pad=10)
    ax2.grid(True, alpha=0.3, linestyle='--')
    ax2.legend(fontsize=9, loc='best', framealpha=0.9)
    
    # Adjust layout and save
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    
    output_path = output_dir / "MASTER_stiffness_analysis.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"\n✓ Saved: {output_path}")
    return output_path


def main():
    """Main execution"""
    if len(sys.argv) < 2:
        print("Usage: python generate_master_stiffness_plot.py <MASTER_all_metrics.csv>")
        return
    
    csv_path = Path(sys.argv[1])
    if not csv_path.exists():
        print(f"ERROR: File not found: {csv_path}")
        return
    
    output_dir = csv_path.parent
    generate_master_stiffness_plot(csv_path, output_dir)


if __name__ == "__main__":
    main()
