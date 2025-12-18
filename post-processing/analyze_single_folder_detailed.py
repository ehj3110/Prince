"""
Detailed Single Folder Analysis
================================

Performs comprehensive analysis on a single test folder including:
1. Normal post-processing
2. Master plots generation (for this folder only)
3. Stiffness analysis
4. Scaling analysis for multiple parameters vs radius/area

Author: Cheng Sun Lab
Date: December 10, 2025
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from post_print_analyzer import PostPrintAnalyzer
from scipy.optimize import curve_fit
from scipy import stats


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
            'y_range': (y_clean.min(), y_clean.max())
        }
    except Exception as e:
        print(f"    Warning: Fit failed - {e}")
        return None


def generate_scaling_analysis_plot(df: pd.DataFrame, output_dir: Path):
    """
    Generate comprehensive scaling analysis plots
    
    Creates a 3x2 subplot figure with:
    1. Peak Force / Radius
    2. Work of Adhesion / Radius
    3. Work of Adhesion / Area
    4. Pre-initiation Distance / Area
    5. Pre-initiation Distance / Radius
    6. Propagation Distance / Radius
    """
    
    print("\n" + "="*60)
    print("SCALING ANALYSIS")
    print("="*60)
    
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
                   ha='center', va='center', transform=ax.transAxes)
            ax.set_title(metric['title'], fontweight='bold')
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
                   ha='center', va='center', transform=ax.transAxes)
            ax.set_title(metric['title'], fontweight='bold')
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
                'equation': eq_text
            })
        
        ax.set_xlabel(metric['x_label'], fontsize=11, fontweight='bold')
        ax.set_ylabel(metric['y_label'], fontsize=11, fontweight='bold')
        ax.set_title(metric['title'], fontsize=12, fontweight='bold', pad=10)
        ax.grid(True, alpha=0.3, linestyle='--')
    
    plt.tight_layout(rect=[0, 0, 1, 0.99])
    
    output_path = output_dir / "scaling_analysis.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"\n✓ Saved: {output_path}")
    
    # Print summary table
    print("\nScaling Analysis Summary:")
    print("-" * 100)
    print(f"{'Y Variable':<30} {'X Variable':<15} {'Fit Type':<12} {'R²':<8} {'p-value':<12} {'n':<5}")
    print("-" * 100)
    for r in results:
        print(f"{r['y_variable']:<30} {r['x_variable']:<15} {r['fit_type']:<12} "
              f"{r['r_squared']:<8.4f} {r['p_value']:<12.2e} {r['n_points']:<5}")
    print("-" * 100)
    
    # Save summary to CSV
    if results:
        df_results = pd.DataFrame(results)
        results_path = output_dir / "scaling_analysis_summary.csv"
        df_results.to_csv(results_path, index=False)
        print(f"\n✓ Saved summary: {results_path}")


def generate_single_folder_master_plots(df: pd.DataFrame, output_dir: Path, folder_name: str):
    """
    Generate master-style plots for a single folder
    """
    print("\n" + "="*60)
    print("GENERATING MASTER PLOTS (SINGLE FOLDER)")
    print("="*60)
    
    # Calculate radius if needed
    if 'radius_mm' not in df.columns and 'area_mm2' in df.columns:
        df['radius_mm'] = np.sqrt(df['area_mm2'] / np.pi)
    
    # Create figure with key metrics
    fig, axes = plt.subplots(2, 2, figsize=(16, 14))
    
    fig.suptitle(f'Master Analysis - {folder_name}', fontsize=16, fontweight='bold', y=0.995)
    
    # Plot 1: Layer vs Peak Force
    ax = axes[0, 0]
    if 'layer_number' in df.columns and 'peak_force_N' in df.columns:
        x = df['layer_number'].values
        y = df['peak_force_N'].values
        mask = np.isfinite(x) & np.isfinite(y)
        ax.scatter(x[mask], y[mask], alpha=0.5, s=50, color='steelblue')
        ax.set_xlabel('Layer Number', fontsize=11, fontweight='bold')
        ax.set_ylabel('Peak Force (N)', fontsize=11, fontweight='bold')
        ax.set_title('Layer vs Peak Force', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
    
    # Plot 2: Radius vs Peak Force
    ax = axes[0, 1]
    if 'radius_mm' in df.columns and 'peak_force_N' in df.columns:
        x = df['radius_mm'].values
        y = df['peak_force_N'].values
        mask = np.isfinite(x) & np.isfinite(y)
        ax.scatter(x[mask], y[mask], alpha=0.5, s=50, color='coral')
        ax.set_xlabel('Radius (mm)', fontsize=11, fontweight='bold')
        ax.set_ylabel('Peak Force (N)', fontsize=11, fontweight='bold')
        ax.set_title('Radius vs Peak Force', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
    
    # Plot 3: Layer vs Work of Adhesion
    ax = axes[1, 0]
    if 'layer_number' in df.columns and 'work_of_adhesion_mJ' in df.columns:
        x = df['layer_number'].values
        y = df['work_of_adhesion_mJ'].values
        mask = np.isfinite(x) & np.isfinite(y)
        ax.scatter(x[mask], y[mask], alpha=0.5, s=50, color='mediumseagreen')
        ax.set_xlabel('Layer Number', fontsize=11, fontweight='bold')
        ax.set_ylabel('Work of Adhesion (mJ)', fontsize=11, fontweight='bold')
        ax.set_title('Layer vs Work of Adhesion', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
    
    # Plot 4: Radius vs Work of Adhesion
    ax = axes[1, 1]
    if 'radius_mm' in df.columns and 'work_of_adhesion_mJ' in df.columns:
        x = df['radius_mm'].values
        y = df['work_of_adhesion_mJ'].values
        mask = np.isfinite(x) & np.isfinite(y)
        ax.scatter(x[mask], y[mask], alpha=0.5, s=50, color='orchid')
        ax.set_xlabel('Radius (mm)', fontsize=11, fontweight='bold')
        ax.set_ylabel('Work of Adhesion (mJ)', fontsize=11, fontweight='bold')
        ax.set_title('Radius vs Work of Adhesion', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout(rect=[0, 0, 1, 0.99])
    
    output_path = output_dir / "single_folder_master_plots.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✓ Saved: {output_path}")


def analyze_single_folder_detailed(folder_path: str):
    """
    Main function to perform comprehensive analysis on a single folder
    """
    folder_path = Path(folder_path)
    
    if not folder_path.exists():
        print(f"ERROR: Folder not found: {folder_path}")
        return
    
    print("="*60)
    print(f"DETAILED ANALYSIS: {folder_path.name}")
    print("="*60)
    print(f"Folder: {folder_path}")
    
    # Step 1: Run normal post-processing
    print("\n" + "="*60)
    print("STEP 1: NORMAL POST-PROCESSING")
    print("="*60)
    
    analyzer = PostPrintAnalyzer()
    
    # Create session structure
    csv_files = list(folder_path.glob("autolog_*.csv"))
    if not csv_files:
        print(f"ERROR: No autolog CSV files found in {folder_path}")
        return
    
    session = {
        'path': folder_path,
        'date': folder_path.parent.name,
        'print_number': folder_path.name,
        'csv_files': csv_files
    }
    
    analyzer.analyze_print_session(session)
    
    # Step 2: Load the generated metrics
    metrics_path = folder_path / "automated_work_of_adhesion.csv"
    
    if not metrics_path.exists():
        print(f"\nERROR: Metrics file not found: {metrics_path}")
        return
    
    df = pd.read_csv(metrics_path)
    print(f"\n✓ Loaded metrics: {len(df)} measurements")
    print(f"  Columns: {list(df.columns)}")
    
    # Step 3: Generate master plots for this folder
    generate_single_folder_master_plots(df, folder_path, folder_path.name)
    
    # Step 4: Generate scaling analysis
    generate_scaling_analysis_plot(df, folder_path)
    
    print("\n" + "="*60)
    print("ANALYSIS COMPLETE")
    print("="*60)
    print(f"\nGenerated files in: {folder_path}")
    print("  - automated_work_of_adhesion.csv (metrics)")
    print("  - single_folder_master_plots.png (overview)")
    print("  - scaling_analysis.png (detailed scaling)")
    print("  - scaling_analysis_summary.csv (fit statistics)")
    print("  - [individual layer plots in subfolders]")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_single_folder_detailed.py <folder_path>")
        print("\nExample:")
        print('  python analyze_single_folder_detailed.py "C:\\Path\\To\\Test\\Folder"')
        sys.exit(1)
    
    folder_path = sys.argv[1]
    analyze_single_folder_detailed(folder_path)
