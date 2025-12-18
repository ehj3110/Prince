"""
Simple scaling analysis for old data format
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from scipy.optimize import curve_fit
from scipy import stats
import sys

def power_law_func(x, a, b):
    return a * np.power(x, b)

def linear_func(x, a, b):
    return a * x + b

def fit_with_stats(x, y, func, func_name):
    try:
        mask = np.isfinite(x) & np.isfinite(y)
        x_clean = x[mask]
        y_clean = y[mask]
        
        if len(x_clean) < 3:
            return None
        
        if func_name == 'power_law':
            mask_pos = (x_clean > 0) & (y_clean > 0)
            x_clean = x_clean[mask_pos]
            y_clean = y_clean[mask_pos]
            if len(x_clean) < 3:
                return None
            p0 = [np.mean(y_clean), 1.0]
            bounds = ([0, -np.inf], [np.inf, np.inf])
        else:
            p0 = [1.0, 0.0]
            bounds = (-np.inf, np.inf)
        
        popt, pcov = curve_fit(func, x_clean, y_clean, p0=p0, bounds=bounds, maxfev=10000)
        
        y_pred = func(x_clean, *popt)
        ss_res = np.sum((y_clean - y_pred) ** 2)
        ss_tot = np.sum((y_clean - np.mean(y_clean)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        correlation, p_value = stats.pearsonr(y_clean, y_pred)
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

# Load data
folder_path = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\Automatic Logging\2025-05-19\50umLayers_ACF_UnsealedWater"
folder = Path(folder_path)

df = pd.read_csv(folder / "automated_work_of_adhesion.csv")
print(f"Loaded {len(df)} measurements")

# Note: The old format doesn't have separate distance columns readily available
# We'll work with the columns that are directly available

# Calculate radius from area
df['radius_mm'] = np.sqrt(df['area_mm2'] / np.pi)

# Rename columns to match expected names
df['layer_number'] = df['number']
df['peak_force_N'] = df['peak_force']

# Filter out NaN areas
df_valid = df[df['area_mm2'].notna()].copy()
print(f"Valid measurements with area data: {len(df_valid)}")

if len(df_valid) == 0:
    print("\nERROR: No measurements have valid area data!")
    print("  This may be because the LayerToArea file doesn't contain the tested layers.")
    print(f"  Tested layers: {sorted(df['layer_number'].unique())}")
    sys.exit(1)

# Define scaling relationships to analyze
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
]

# Add distance metrics if available
if 'distance_to_peak_mm' in df_valid.columns:
    metrics.extend([
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
    ])

if 'distance_to_propagate_mm' in df_valid.columns:
    metrics.append({
        'x_col': 'radius_mm',
        'y_col': 'distance_to_propagate_mm',
        'x_label': 'Radius (mm)',
        'y_label': 'Propagation Distance (mm)',
        'title': 'Propagation Distance vs Radius'
    })

# Create plots
n_plots = len(metrics)
n_rows = (n_plots + 1) // 2
fig, axes = plt.subplots(n_rows, 2, figsize=(16, 7*n_rows))
if n_rows == 1:
    axes = axes.reshape(1, -1)
axes = axes.flatten()

fig.suptitle(f'Scaling Analysis - {folder.name}', fontsize=16, fontweight='bold', y=0.995)

results = []

for idx, metric in enumerate(metrics):
    ax = axes[idx]
    
    x_col = metric['x_col']
    y_col = metric['y_col']
    
    if x_col not in df_valid.columns or y_col not in df_valid.columns:
        ax.text(0.5, 0.5, f'Data not available\n({x_col} or {y_col})', 
               ha='center', va='center', transform=ax.transAxes)
        ax.set_title(metric['title'], fontweight='bold')
        continue
    
    x = df_valid[x_col].values
    y = df_valid[y_col].values
    
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
    
    # Try both fits
    fit_power = fit_with_stats(x_clean, y_clean, power_law_func, 'power_law')
    fit_linear = fit_with_stats(x_clean, y_clean, linear_func, 'linear')
    
    # Choose best fit
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
    
    if best_fit:
        x_fit = np.linspace(best_fit['x_range'][0], best_fit['x_range'][1], 100)
        
        if best_type == 'power_law':
            y_fit = power_law_func(x_fit, *best_fit['params'])
            eq_text = f"y = {best_fit['params'][0]:.4f} × x^{best_fit['params'][1]:.3f}"
        else:
            y_fit = linear_func(x_fit, *best_fit['params'])
            eq_text = f"y = {best_fit['params'][0]:.4f}x + {best_fit['params'][1]:.4f}"
        
        ax.plot(x_fit, y_fit, 'r-', linewidth=2.5, alpha=0.8, label=f'{best_type.replace("_", " ").title()} Fit')
        
        textstr = f"{eq_text}\nR² = {best_fit['r_squared']:.4f}\np = {best_fit['p_value']:.2e}\nn = {best_fit['n_points']}"
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
        ax.text(0.05, 0.95, textstr, transform=ax.transAxes, fontsize=9,
               verticalalignment='top', bbox=props, family='monospace')
        
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

# Hide unused subplots
for idx in range(len(metrics), len(axes)):
    axes[idx].set_visible(False)

plt.tight_layout(rect=[0, 0, 1, 0.99])

output_path = folder / "scaling_analysis_corrected.png"
plt.savefig(output_path, dpi=300, bbox_inches='tight')
plt.close()

print(f"\n✓ Saved: {output_path}")

# Print and save summary
print("\nScaling Analysis Summary:")
print("-" * 100)
print(f"{'Y Variable':<30} {'X Variable':<15} {'Fit Type':<12} {'R²':<8} {'p-value':<12} {'n':<5}")
print("-" * 100)
for r in results:
    print(f"{r['y_variable']:<30} {r['x_variable']:<15} {r['fit_type']:<12} "
          f"{r['r_squared']:<8.4f} {r['p_value']:<12.2e} {r['n_points']:<5}")
print("-" * 100)

if results:
    df_results = pd.DataFrame(results)
    results_path = folder / "scaling_analysis_summary_corrected.csv"
    df_results.to_csv(results_path, index=False)
    print(f"\n✓ Saved summary: {results_path}")
