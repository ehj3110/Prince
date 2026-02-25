"""
Scaling Analysis for Presentation Data
=======================================

Analyze scaling relationships between radius and adhesion metrics:
1. Power law fitting (F ~ r^n)
2. Linear fitting
3. R-squared and goodness of fit
4. Individual scaling plots per condition
5. Combined scaling comparison plots

Usage:
    python analyze_presentation_scaling.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import stats
from scipy.optimize import curve_fit
import sys


def power_law(x, A, n):
    """Power law function: y = A * x^n"""
    return A * np.power(x, n)


def fit_power_law(x, y):
    """
    Fit power law to data
    
    Returns:
        dict with fit parameters and statistics
    """
    # Remove invalid data
    mask = (x > 0) & (y > 0) & np.isfinite(x) & np.isfinite(y)
    x_clean = x[mask]
    y_clean = y[mask]
    
    if len(x_clean) < 3:
        return None
    
    try:
        # Fit in log space for initial guess
        log_x = np.log(x_clean)
        log_y = np.log(y_clean)
        slope, intercept, r_value, p_value, std_err = stats.linregress(log_x, log_y)
        
        # Initial guess
        A_guess = np.exp(intercept)
        n_guess = slope
        
        # Fit power law
        popt, pcov = curve_fit(power_law, x_clean, y_clean, p0=[A_guess, n_guess], maxfev=10000)
        A_fit, n_fit = popt
        
        # Calculate R-squared
        y_pred = power_law(x_clean, A_fit, n_fit)
        ss_res = np.sum((y_clean - y_pred) ** 2)
        ss_tot = np.sum((y_clean - np.mean(y_clean)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        return {
            'A': A_fit,
            'n': n_fit,
            'r_squared': r_squared,
            'n_points': len(x_clean)
        }
        
    except Exception as e:
        return None


def fit_linear(x, y):
    """
    Fit linear relationship
    
    Returns:
        dict with fit parameters and statistics
    """
    # Remove invalid data
    mask = np.isfinite(x) & np.isfinite(y)
    x_clean = x[mask]
    y_clean = y[mask]
    
    if len(x_clean) < 3:
        return None
    
    try:
        slope, intercept, r_value, p_value, std_err = stats.linregress(x_clean, y_clean)
        
        return {
            'slope': slope,
            'intercept': intercept,
            'r_squared': r_value**2,
            'p_value': p_value,
            'n_points': len(x_clean)
        }
        
    except Exception as e:
        return None


def analyze_scaling_for_condition(df, condition_name, output_dir):
    """
    Analyze scaling for a single condition
    
    Args:
        df: DataFrame with data for this condition
        condition_name: Name of condition
        output_dir: Directory to save plots
        
    Returns:
        dict with scaling results
    """
    print(f"\n  {condition_name}")
    
    # Metrics to analyze
    metrics = [
        ('peak_force', 'Peak Force (N)'),
        ('work_of_adhesion_corrected_mJ', 'Work of Adhesion (mJ)'),
        ('total_peel_distance', 'Total Peel Distance (mm)'),
        ('peak_retraction_force_N', 'Peak Retraction Force (N)')
    ]
    
    results = {'condition': condition_name}
    
    # Create figure for this condition
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    axes = axes.flatten()
    
    for idx, (metric_col, metric_label) in enumerate(metrics):
        ax = axes[idx]
        
        # Get valid data
        valid_mask = (df['radius_mm'] > 0) & (df[metric_col].notna()) & np.isfinite(df[metric_col])
        x = df.loc[valid_mask, 'radius_mm'].values
        y = df.loc[valid_mask, metric_col].values
        
        if len(x) < 3:
            ax.text(0.5, 0.5, 'Insufficient data', ha='center', va='center', transform=ax.transAxes)
            ax.set_title(metric_label, fontsize=21, fontweight='bold')
            continue
        
        # Plot raw data
        ax.scatter(x, y, alpha=0.5, s=100, label='Data')
        
        # Fit power law
        power_fit = fit_power_law(x, y)
        if power_fit:
            x_fit = np.linspace(x.min(), x.max(), 100)
            y_fit = power_law(x_fit, power_fit['A'], power_fit['n'])
            ax.plot(x_fit, y_fit, 'r-', linewidth=2, 
                   label=f"$y = {power_fit['A']:.3f} x^{{{power_fit['n']:.2f}}}$ ($R^2$={power_fit['r_squared']:.3f})")
            
            # Store results
            results[f'{metric_col}_power_A'] = power_fit['A']
            results[f'{metric_col}_power_n'] = power_fit['n']
            results[f'{metric_col}_power_r2'] = power_fit['r_squared']
        
        # Styling
        ax.set_xlabel('Radius (mm)', fontsize=27, fontweight='bold')
        ax.set_ylabel(metric_label, fontsize=27, fontweight='bold')
        ax.set_title(metric_label, fontsize=21, fontweight='bold')
        ax.tick_params(labelsize=15)
        ax.legend(fontsize=15, loc='best')
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plot_path = output_dir / f"{condition_name}_scaling_analysis.png"
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"    [OK] Saved scaling plot")
    
    return results


def main():
    """Analyze scaling for all Presentation data conditions"""
    
    pres_dir = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\Presentation data")
    
    print("="*80)
    print("PRESENTATION DATA - SCALING ANALYSIS")
    print("="*80)
    
    # Load combined data
    combined_csv = pres_dir / "MASTER_presentation_combined.csv"
    
    if not combined_csv.exists():
        print(f"\n[X] Combined CSV not found: {combined_csv}")
        print("Please run generate_presentation_master_plots.py first")
        return
    
    print(f"\nLoading data from: {combined_csv.name}")
    df = pd.read_csv(combined_csv)
    print(f"Total measurements: {len(df)}")
    
    # Create output directory
    output_dir = pres_dir / "scaling_analysis"
    output_dir.mkdir(exist_ok=True)
    print(f"Output directory: {output_dir}")
    
    # Analyze each condition
    print("\n" + "="*80)
    print("ANALYZING SCALING BY CONDITION")
    print("="*80)
    
    conditions = sorted(df['condition'].unique())
    all_results = []
    
    for condition in conditions:
        condition_data = df[df['condition'] == condition].copy()
        
        result = analyze_scaling_for_condition(
            condition_data,
            condition,
            output_dir
        )
        
        if result:
            all_results.append(result)
    
    # Save results
    if all_results:
        results_df = pd.DataFrame(all_results)
        summary_csv = output_dir / "scaling_summary.csv"
        results_df.to_csv(summary_csv, index=False)
        print(f"\n[OK] Saved scaling summary to: {summary_csv.name}")
        
        # Print summary
        print("\n" + "="*80)
        print("SCALING EXPONENTS (Power Law: y = A * r^n)")
        print("="*80)
        print(f"\n{'Condition':<35} {'Peak Force':<12} {'Work Adhesion':<12} {'Peel Distance':<12}")
        print("-"*80)
        
        for _, row in results_df.iterrows():
            condition = row['condition'][:35]
            pf_n = row.get('peak_force_power_n', np.nan)
            wa_n = row.get('work_of_adhesion_corrected_mJ_power_n', np.nan)
            pd_n = row.get('total_peel_distance_power_n', np.nan)
            
            pf_str = f"n={pf_n:.2f}" if not np.isnan(pf_n) else "N/A"
            wa_str = f"n={wa_n:.2f}" if not np.isnan(wa_n) else "N/A"
            pd_str = f"n={pd_n:.2f}" if not np.isnan(pd_n) else "N/A"
            
            print(f"{condition:<35} {pf_str:<12} {wa_str:<12} {pd_str:<12}")
    
    print("\n" + "="*80)
    print("SCALING ANALYSIS COMPLETE")
    print("="*80)
    print(f"\nGenerated files in: {output_dir}")
    print("  - Individual scaling plots for each condition")
    print("  - scaling_summary.csv with power law exponents")


if __name__ == "__main__":
    main()
