"""
V6 Scaling Analysis
===================

Analyzes how adhesion metrics scale with contact area for V6 data.
Compares different membrane materials (ACF, Flat PDMS, TEMPO).

Features:
- Power law fitting (Force ~ Area^n)
- Linear scaling analysis
- Comparison across materials
- Statistical analysis

Usage:
    python analyze_v6_scaling.py

Author: Cheng Sun Lab Team
Date: December 2, 2025
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from scipy import stats
from scipy.optimize import curve_fit
import matplotlib

matplotlib.use('Agg')  # Non-interactive backend


def power_law(x, a, b):
    """Power law function: y = a * x^b"""
    return a * np.power(x, b)


def analyze_scaling(df, metric_name, metric_col, output_dir, apply_log=False):
    """
    Analyze scaling of a metric with contact area.
    
    Args:
        df: DataFrame with measurements
        metric_name: Display name for metric
        metric_col: Column name in DataFrame
        output_dir: Where to save plots
        apply_log: Whether to apply log-log scaling
    """
    print(f"\n{'='*80}")
    print(f"SCALING ANALYSIS: {metric_name}")
    print(f"{'='*80}")
    
    # Create figure
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    
    # Get unique conditions
    conditions = df['detailed_condition'].unique()
    colors = plt.cm.tab10(np.linspace(0, 1, len(conditions)))
    
    # Left plot: Linear scale
    ax_linear = axes[0]
    # Right plot: Log-log scale
    ax_log = axes[1]
    
    # Store results for summary
    results = []
    
    for condition, color in zip(conditions, colors):
        # Filter data for this condition
        condition_df = df[df['detailed_condition'] == condition].copy()
        
        # Get areas and metric values
        areas = condition_df['area_mm2'].values
        values = condition_df[metric_col].values
        
        # Remove any NaN or infinite values
        valid_mask = np.isfinite(areas) & np.isfinite(values) & (values > 0) & (areas > 0)
        areas = areas[valid_mask]
        values = values[valid_mask]
        
        if len(areas) < 3:
            print(f"  {condition}: Insufficient data ({len(areas)} points)")
            continue
        
        # Sort by area
        sort_idx = np.argsort(areas)
        areas = areas[sort_idx]
        values = values[sort_idx]
        
        print(f"\n  {condition}:")
        print(f"    Data points: {len(areas)}")
        print(f"    Area range: {areas.min():.1f} - {areas.max():.1f} mm²")
        print(f"    {metric_name} range: {values.min():.4f} - {values.max():.4f}")
        
        # Linear plot
        ax_linear.scatter(areas, values, label=condition, color=color, s=80, alpha=0.7)
        
        # Log-log plot
        ax_log.scatter(areas, values, label=condition, color=color, s=80, alpha=0.7)
        
        # Fit power law: F = a * A^b
        try:
            # Initial guess: a = mean(F)/mean(A), b = 1 (linear scaling)
            p0 = [values.mean() / areas.mean(), 1.0]
            
            # Fit power law
            popt, pcov = curve_fit(power_law, areas, values, p0=p0, maxfev=10000)
            a_fit, b_fit = popt
            perr = np.sqrt(np.diag(pcov))
            a_err, b_err = perr
            
            # Calculate R²
            values_pred = power_law(areas, a_fit, b_fit)
            ss_res = np.sum((values - values_pred)**2)
            ss_tot = np.sum((values - values.mean())**2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            
            print(f"    Power law fit: F = {a_fit:.6f} ± {a_err:.6f} * A^({b_fit:.3f} ± {b_err:.3f})")
            print(f"    R² = {r_squared:.4f}")
            
            # Plot fit lines
            area_fit = np.linspace(areas.min(), areas.max(), 100)
            values_fit = power_law(area_fit, a_fit, b_fit)
            
            ax_linear.plot(area_fit, values_fit, '--', color=color, alpha=0.7, linewidth=2)
            ax_log.plot(area_fit, values_fit, '--', color=color, alpha=0.7, linewidth=2,
                       label=f'{condition}\n$n={b_fit:.2f}±{b_err:.2f}$, $R^2={r_squared:.3f}$')
            
            # Store results
            results.append({
                'Condition': condition,
                'Exponent_b': b_fit,
                'Exponent_err': b_err,
                'Coefficient_a': a_fit,
                'Coefficient_err': a_err,
                'R_squared': r_squared,
                'N_points': len(areas)
            })
            
        except Exception as e:
            print(f"    Error fitting: {str(e)}")
            continue
    
    # Format linear plot
    ax_linear.set_xlabel('Contact Area (mm²)', fontsize=12, fontweight='bold')
    ax_linear.set_ylabel(metric_name, fontsize=12, fontweight='bold')
    ax_linear.set_title(f'{metric_name} vs Contact Area\n(Linear Scale)', fontsize=14, fontweight='bold')
    ax_linear.legend(fontsize=10)
    ax_linear.grid(True, alpha=0.3)
    ax_linear.set_ylim(bottom=0)
    
    # Format log-log plot
    ax_log.set_xlabel('Contact Area (mm²)', fontsize=12, fontweight='bold')
    ax_log.set_ylabel(metric_name, fontsize=12, fontweight='bold')
    ax_log.set_title(f'{metric_name} vs Contact Area\n(Log-Log Scale with Power Law Fits)', fontsize=14, fontweight='bold')
    ax_log.set_xscale('log')
    ax_log.set_yscale('log')
    ax_log.legend(fontsize=9, loc='best')
    ax_log.grid(True, alpha=0.3, which='both')
    
    plt.tight_layout()
    
    # Save plot
    plot_filename = f"V6_scaling_{metric_col}.png"
    plot_path = output_dir / plot_filename
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"\n  Saved: {plot_filename}")
    
    # Save results to CSV
    if results:
        results_df = pd.DataFrame(results)
        csv_filename = f"V6_scaling_{metric_col}_results.csv"
        csv_path = output_dir / csv_filename
        results_df.to_csv(csv_path, index=False)
        print(f"  Saved results: {csv_filename}")
    
    return results


def create_comparison_plot(all_results, output_dir):
    """Create a comparison plot of scaling exponents across metrics"""
    
    print(f"\n{'='*80}")
    print("CREATING SCALING EXPONENT COMPARISON")
    print(f"{'='*80}")
    
    if not all_results:
        print("No results to plot")
        return
    
    # Organize data by metric
    metrics = list(all_results.keys())
    conditions = []
    
    # Get all unique conditions
    for metric_results in all_results.values():
        for result in metric_results:
            if result['Condition'] not in conditions:
                conditions.append(result['Condition'])
    
    # Create figure
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # Bar width and positions
    n_metrics = len(metrics)
    n_conditions = len(conditions)
    bar_width = 0.8 / n_conditions
    x = np.arange(n_metrics)
    
    colors = plt.cm.tab10(np.linspace(0, 1, n_conditions))
    
    # Plot bars for each condition
    for i, condition in enumerate(conditions):
        exponents = []
        errors = []
        
        for metric in metrics:
            # Find this condition's result for this metric
            metric_results = all_results[metric]
            found = False
            for result in metric_results:
                if result['Condition'] == condition:
                    exponents.append(result['Exponent_b'])
                    errors.append(result['Exponent_err'])
                    found = True
                    break
            if not found:
                exponents.append(0)
                errors.append(0)
        
        # Plot bars
        offset = (i - n_conditions/2 + 0.5) * bar_width
        ax.bar(x + offset, exponents, bar_width, label=condition, 
               color=colors[i], alpha=0.7, yerr=errors, capsize=5)
    
    # Add reference line for linear scaling (exponent = 1)
    ax.axhline(y=1.0, color='red', linestyle='--', linewidth=2, alpha=0.7, label='Linear Scaling (n=1)')
    
    # Format plot
    ax.set_xlabel('Metric', fontsize=14, fontweight='bold')
    ax.set_ylabel('Scaling Exponent (n)', fontsize=14, fontweight='bold')
    ax.set_title('Power Law Scaling Exponents\n$F = a \\times A^n$', fontsize=16, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(metrics, rotation=45, ha='right')
    ax.legend(fontsize=10, loc='best')
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_ylim(0, max(2.0, ax.get_ylim()[1]))
    
    plt.tight_layout()
    
    # Save plot
    plot_path = output_dir / "V6_scaling_exponents_comparison.png"
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"\n  Saved: V6_scaling_exponents_comparison.png")


def main():
    """Main analysis function"""
    
    # Define paths
    v6_dir = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V6")
    csv_path = v6_dir / "MASTER_all_metrics.csv"
    
    print("="*80)
    print("V6 SCALING ANALYSIS")
    print("="*80)
    print(f"Data: {csv_path}")
    print()
    
    # Load data
    if not csv_path.exists():
        print(f"ERROR: Master CSV not found at {csv_path}")
        return
    
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} measurements")
    print(f"Conditions: {df['detailed_condition'].unique().tolist()}")
    
    # Metrics to analyze
    metrics_to_analyze = [
        ('Peak Force', 'peak_force_N'),
        ('Work of Adhesion', 'work_of_adhesion_mJ'),
        ('Pre-Initiation Distance', 'pre_initiation_distance_mm'),
        ('Propagation Distance', 'propagation_distance_mm'),
    ]
    
    # Analyze each metric
    all_results = {}
    for metric_name, metric_col in metrics_to_analyze:
        if metric_col in df.columns:
            results = analyze_scaling(df, metric_name, metric_col, v6_dir)
            if results:
                all_results[metric_name] = results
        else:
            print(f"\nWARNING: Column '{metric_col}' not found in data")
    
    # Create comparison plot
    if all_results:
        create_comparison_plot(all_results, v6_dir)
    
    print(f"\n{'='*80}")
    print("SCALING ANALYSIS COMPLETE")
    print(f"{'='*80}")
    print(f"\nAll plots and results saved to: {v6_dir}")


if __name__ == "__main__":
    main()
