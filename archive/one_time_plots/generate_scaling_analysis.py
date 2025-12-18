"""
Generate Scaling Analysis
==========================

Creates scaling analysis plots from MASTER CSV data showing how different
metrics scale with radius and area.

Author: Cheng Sun Lab
Date: December 10, 2025
"""

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


def linear_func(x, a, b):
    """Linear function: y = a * x + b"""
    return a * x + b


def fit_with_stats(x, y, func, func_name):
    """
    Fit data and return parameters with statistics
    
    Returns:
        dict with fit parameters, R², p-value, etc.
    """
    try:
        # Remove NaN and infinite values
        mask = np.isfinite(x) & np.isfinite(y)
        x_clean = x[mask]
        y_clean = y[mask]
        
        if len(x_clean) < 3:
            return None
        
        # For power law, need positive values
        if func_name == 'power_law':
            mask_pos = (x_clean > 0) & (y_clean > 0)
            x_clean = x_clean[mask_pos]
            y_clean = y_clean[mask_pos]
            
            if len(x_clean) < 3:
                return None
        
        # Fit
        if func_name == 'power_law':
            p0 = [np.mean(y_clean), 1.0]
            bounds = ([0, -np.inf], [np.inf, np.inf])
        else:  # linear
            p0 = [1.0, 0.0]
            bounds = (-np.inf, np.inf)
        
        popt, pcov = curve_fit(func, x_clean, y_clean, p0=p0, bounds=bounds, maxfev=10000)
        
        # Calculate R²
        y_pred = func(x_clean, *popt)
        ss_res = np.sum((y_clean - y_pred) ** 2)
        ss_tot = np.sum((y_clean - np.mean(y_clean)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        # Calculate p-value using correlation
        correlation, p_value = stats.pearsonr(y_clean, y_pred)
        
        # Standard errors
        perr = np.sqrt(np.diag(pcov))
        
        return {
            'params': popt,
            'std_err': perr,
            'r_squared': r_squared,
            'p_value': p_value,
            'n_points': len(x_clean),
            'x_range': (x_clean.min(), x_clean.max()),
            'y_range': (y_clean.min(), y_clean.max()),
            'x_data': x_clean,
            'y_data': y_clean
        }
    except Exception as e:
        print(f"    Warning: Fit failed - {e}")
        return None


def generate_scaling_analysis(csv_path: Path, output_dir: Path):
    """
    Generate comprehensive scaling analysis plots
    """
    
    print("\n" + "="*60)
    print("SCALING ANALYSIS")
    print("="*60)
    
    # Read data
    df = pd.read_csv(csv_path)
    print(f"  Loaded {len(df)} measurements")
    
    # Calculate radius if not present
    if 'radius_mm' not in df.columns and 'area_mm2' in df.columns:
        df['radius_mm'] = np.sqrt(df['area_mm2'] / np.pi)
    
    # Define metrics to analyze
    metrics = [
        {
            'x_col': 'radius_mm',
            'y_col': 'peak_force_N',
            'x_label': 'Radius (mm)',
            'y_label': 'Peak Force (N)',
            'title': 'Peak Force vs Radius'
        },
        {
            'x_col': 'radius_mm',
            'y_col': 'work_of_adhesion_mJ',
            'x_label': 'Radius (mm)',
            'y_label': 'Work of Adhesion (mJ)',
            'title': 'Work of Adhesion vs Radius'
        },
        {
            'x_col': 'area_mm2',
            'y_col': 'work_of_adhesion_mJ',
            'x_label': 'Area (mm²)',
            'y_label': 'Work of Adhesion (mJ)',
            'title': 'Work of Adhesion vs Area'
        },
        {
            'x_col': 'area_mm2',
            'y_col': 'distance_to_peak_mm',
            'x_label': 'Area (mm²)',
            'y_label': 'Pre-initiation Distance (mm)',
            'title': 'Pre-initiation Distance vs Area'
        },
        {
            'x_col': 'radius_mm',
            'y_col': 'distance_to_peak_mm',
            'x_label': 'Radius (mm)',
            'y_label': 'Pre-initiation Distance (mm)',
            'title': 'Pre-initiation Distance vs Radius'
        },
        {
            'x_col': 'radius_mm',
            'y_col': 'distance_to_propagate_mm',
            'x_label': 'Radius (mm)',
            'y_label': 'Propagation Distance (mm)',
            'title': 'Propagation Distance vs Radius'
        }
    ]
    
    # Create figure
    fig, axes = plt.subplots(3, 2, figsize=(16, 20))
    axes = axes.flatten()
    
    fig.suptitle('Scaling Analysis - All Measurements', fontsize=16, fontweight='bold', y=0.995)
    
    # Store results for summary
    results = []
    
    for idx, metric in enumerate(metrics):
        ax = axes[idx]
        
        x_col = metric['x_col']
        y_col = metric['y_col']
        
        # Check if columns exist
        if x_col not in df.columns or y_col not in df.columns:
            ax.text(0.5, 0.5, f'Data not available\n({x_col} or {y_col})', 
                   ha='center', va='center', transform=ax.transAxes, fontsize=12)
            ax.set_title(metric['title'], fontweight='bold')
            print(f"\n  ⚠️  {metric['title']}: Missing columns")
            continue
        
        # Get data
        x = df[x_col].values
        y = df[y_col].values
        
        # Remove NaN
        mask = np.isfinite(x) & np.isfinite(y)
        x_clean = x[mask]
        y_clean = y[mask]
        
        if len(x_clean) < 3:
            ax.text(0.5, 0.5, f'Insufficient data (n={len(x_clean)})', 
                   ha='center', va='center', transform=ax.transAxes, fontsize=12)
            ax.set_title(metric['title'], fontweight='bold')
            print(f"\n  ⚠️  {metric['title']}: Only {len(x_clean)} points")
            continue
        
        # Scatter plot
        ax.scatter(x_clean, y_clean, alpha=0.5, s=50, color='steelblue', edgecolors='black', linewidth=0.5)
        
        # Try both power law and linear fits
        fit_power = fit_with_stats(x_clean, y_clean, power_law_func, 'power_law')
        fit_linear = fit_with_stats(x_clean, y_clean, linear_func, 'linear')
        
        # Choose best fit based on R²
        best_fit = None
        best_type = None
        
        if fit_power and fit_linear:
            if fit_power['r_squared'] > fit_linear['r_squared']:
                best_fit = fit_power
                best_type = 'power_law'
            else:
                best_fit = fit_linear
                best_type = 'linear'
        elif fit_power:
            best_fit = fit_power
            best_type = 'power_law'
        elif fit_linear:
            best_fit = fit_linear
            best_type = 'linear'
        
        # Plot best fit
        if best_fit:
            x_fit = np.linspace(best_fit['x_range'][0], best_fit['x_range'][1], 100)
            
            if best_type == 'power_law':
                y_fit = power_law_func(x_fit, *best_fit['params'])
                eq_text = f"y = {best_fit['params'][0]:.4f} × x^{best_fit['params'][1]:.3f}"
            else:
                y_fit = linear_func(x_fit, *best_fit['params'])
                eq_text = f"y = {best_fit['params'][0]:.4f}x + {best_fit['params'][1]:.4f}"
            
            ax.plot(x_fit, y_fit, 'r-', linewidth=2.5, alpha=0.8, label=f'{best_type.replace("_", " ").title()} Fit')
            
            # Add text box with fit info
            textstr = f"{eq_text}\nR² = {best_fit['r_squared']:.4f}\np = {best_fit['p_value']:.2e}\nn = {best_fit['n_points']}"
            props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
            ax.text(0.05, 0.95, textstr, transform=ax.transAxes, fontsize=9,
                   verticalalignment='top', bbox=props, family='monospace')
            
            # Store results
            results.append({
                'x_variable': x_col,
                'y_variable': y_col,
                'fit_type': best_type,
                'r_squared': best_fit['r_squared'],
                'p_value': best_fit['p_value'],
                'n_points': best_fit['n_points'],
                'equation': eq_text,
                'param_a': best_fit['params'][0],
                'param_b': best_fit['params'][1]
            })
            
            print(f"\n  ✓ {metric['title']}: {best_type}, R²={best_fit['r_squared']:.4f}, n={best_fit['n_points']}")
        
        ax.set_xlabel(metric['x_label'], fontsize=11, fontweight='bold')
        ax.set_ylabel(metric['y_label'], fontsize=11, fontweight='bold')
        ax.set_title(metric['title'], fontsize=12, fontweight='bold', pad=10)
        ax.grid(True, alpha=0.3, linestyle='--')
    
    plt.tight_layout(rect=[0, 0, 1, 0.99])
    
    output_path = output_dir / "MASTER_scaling_analysis.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"\n✓ Saved: {output_path}")
    
    # Print summary table
    if results:
        print("\n" + "="*60)
        print("SCALING ANALYSIS SUMMARY")
        print("="*60)
        print(f"{'Y Variable':<30} {'X Variable':<15} {'Fit Type':<12} {'R²':<8} {'p-value':<12} {'n':<5}")
        print("-" * 100)
        for r in results:
            print(f"{r['y_variable']:<30} {r['x_variable']:<15} {r['fit_type']:<12} "
                  f"{r['r_squared']:<8.4f} {r['p_value']:<12.2e} {r['n_points']:<5}")
        print("="*60)
        
        # Save summary to CSV
        df_results = pd.DataFrame(results)
        results_path = output_dir / "MASTER_scaling_analysis_summary.csv"
        df_results.to_csv(results_path, index=False)
        print(f"\n✓ Saved summary: {results_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_scaling_analysis.py <path_to_MASTER_all_metrics.csv>")
        sys.exit(1)
    
    csv_path = Path(sys.argv[1])
    
    if not csv_path.exists():
        print(f"ERROR: File not found: {csv_path}")
        sys.exit(1)
    
    output_dir = csv_path.parent
    generate_scaling_analysis(csv_path, output_dir)
