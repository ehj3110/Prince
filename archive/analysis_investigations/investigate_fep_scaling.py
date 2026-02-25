"""
Investigate FEP Scaling Discrepancy
===================================

This script investigates why the FEP scaling analysis shows super-linear (n=1.29)
but the visual trendline appears sub-linear.

The discrepancy arises because:
1. Scaling analysis: fits log(y) = n*log(x) on ALL individual data points
2. Visual plots: show polynomial trendline fitted to GROUPED MEANS by radius

Author: Cheng Sun Lab Team
Date: January 10, 2026
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from scipy import stats


def main():
    """Analyze FEP scaling behavior"""
    
    print("="*80)
    print("FEP Scaling Analysis Investigation")
    print("="*80)
    
    # Load V9 data
    v9_dir = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V9")
    df = pd.read_csv(v9_dir / "MASTER_all_metrics.csv")
    
    # Filter FEP data only
    fep_data = df[df['condition_label'] == 'FEP_500um_V19_Air_400'].copy()
    print(f"\nFEP Data: {len(fep_data)} layers")
    
    # Calculate radius
    fep_data['radius_mm'] = np.sqrt(fep_data['area_mm2'] / np.pi)
    
    # 1. Log-log regression on ALL individual points (what scaling analysis does)
    log_r = np.log(fep_data['radius_mm'])
    log_f = np.log(fep_data['peak_force_N'])
    slope, intercept, r_value, p_value, std_err = stats.linregress(log_r, log_f)
    
    print("\n" + "="*80)
    print("1. SCALING ANALYSIS METHOD (log-log fit on all individual points)")
    print("="*80)
    print(f"Number of points: {len(fep_data)}")
    print(f"Exponent (n): {slope:.3f} ± {std_err:.3f}")
    print(f"Coefficient (A): {np.exp(intercept):.4f}")
    print(f"R²: {r_value**2:.4f}")
    print(f"Interpretation: {'Super-linear' if slope > 1.1 else 'Sub-linear' if slope < 0.9 else 'Linear'}")
    
    # 2. Polynomial fit on GROUPED MEANS (what visual plot shows)
    grouped = fep_data.groupby('radius_mm')['peak_force_N'].agg(['mean', 'std', 'count']).reset_index()
    print(f"\n" + "="*80)
    print("2. VISUAL PLOT METHOD (polynomial fit on grouped means)")
    print("="*80)
    print(f"Number of radius bins: {len(grouped)}")
    print(f"Radius range: {grouped['radius_mm'].min():.2f} - {grouped['radius_mm'].max():.2f} mm")
    
    # Fit 2nd degree polynomial to means
    poly_coeffs = np.polyfit(grouped['radius_mm'], grouped['mean'], 2)
    poly_fn = np.poly1d(poly_coeffs)
    
    print(f"\nPolynomial fit (2nd degree): y = {poly_coeffs[0]:.4f}*x² + {poly_coeffs[1]:.4f}*x + {poly_coeffs[2]:.4f}")
    
    # Check if polynomial is concave (sub-linear appearance)
    if poly_coeffs[0] < 0:
        print("Polynomial curvature: CONCAVE (appears sub-linear)")
    elif poly_coeffs[0] > 0:
        print("Polynomial curvature: CONVEX (appears super-linear)")
    else:
        print("Polynomial curvature: LINEAR")
    
    # 3. Calculate effective scaling exponent at different radii
    print(f"\n" + "="*80)
    print("3. EFFECTIVE SCALING EXPONENT (local power law)")
    print("="*80)
    print("Effective exponent = d(log(F))/d(log(r)) at different radii:")
    
    # Calculate derivative of polynomial in log space
    r_test = np.array([2, 3, 4, 5, 6])
    for r in r_test:
        if grouped['radius_mm'].min() <= r <= grouped['radius_mm'].max():
            f = poly_fn(r)
            # df/dr from polynomial
            dpoly = np.polyder(poly_fn)
            df_dr = dpoly(r)
            # Effective exponent: n_eff = (df/dr) * (r/f)
            n_eff = df_dr * r / f
            print(f"  r = {r:.1f} mm: n_eff = {n_eff:.3f}")
    
    # 4. Check for outliers or variance issues
    print(f"\n" + "="*80)
    print("4. DATA QUALITY ASSESSMENT")
    print("="*80)
    
    # Group statistics
    for _, row in grouped.iterrows():
        r = row['radius_mm']
        mean = row['mean']
        std = row['std']
        count = row['count']
        cv = (std / mean * 100) if mean > 0 else 0
        print(f"r = {r:.2f} mm: mean = {mean:.3f} N, std = {std:.3f} N, CV = {cv:.1f}%, n = {int(count)}")
    
    # 5. Create diagnostic plot
    print(f"\n" + "="*80)
    print("5. GENERATING DIAGNOSTIC PLOT")
    print("="*80)
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # Plot 1: Linear scale with both fits
    ax = axes[0, 0]
    ax.scatter(fep_data['radius_mm'], fep_data['peak_force_N'], 
              alpha=0.3, s=20, label='Individual points')
    ax.plot(grouped['radius_mm'], grouped['mean'], 'ro-', 
           markersize=8, linewidth=2, label='Grouped means')
    
    # Power law fit (from scaling analysis)
    r_smooth = np.linspace(fep_data['radius_mm'].min(), fep_data['radius_mm'].max(), 100)
    f_power = np.exp(intercept) * r_smooth ** slope
    ax.plot(r_smooth, f_power, 'b--', linewidth=2, 
           label=f'Power law: F = {np.exp(intercept):.2f}*r^{slope:.2f}')
    
    # Polynomial fit (from visual plot)
    f_poly = poly_fn(r_smooth)
    ax.plot(r_smooth, f_poly, 'g:', linewidth=2,
           label=f'Polynomial (visual)')
    
    ax.set_xlabel('Radius (mm)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Peak Force (N)', fontsize=12, fontweight='bold')
    ax.set_title('Linear Scale: Power Law vs Polynomial', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Plot 2: Log-log scale
    ax = axes[0, 1]
    ax.scatter(fep_data['radius_mm'], fep_data['peak_force_N'], 
              alpha=0.3, s=20, label='Individual points')
    ax.plot(grouped['radius_mm'], grouped['mean'], 'ro', 
           markersize=8, label='Grouped means')
    ax.plot(r_smooth, f_power, 'b--', linewidth=2,
           label=f'n = {slope:.2f}')
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlabel('Radius (mm)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Peak Force (N)', fontsize=12, fontweight='bold')
    ax.set_title('Log-Log Scale: Scaling Analysis View', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3, which='both')
    
    # Plot 3: Residuals from power law
    ax = axes[1, 0]
    f_predicted = np.exp(intercept) * fep_data['radius_mm'] ** slope
    residuals = fep_data['peak_force_N'] - f_predicted
    ax.scatter(fep_data['radius_mm'], residuals, alpha=0.3, s=20)
    ax.axhline(0, color='r', linestyle='--', linewidth=2)
    ax.set_xlabel('Radius (mm)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Residuals (N)', fontsize=12, fontweight='bold')
    ax.set_title('Residuals from Power Law Fit', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    # Plot 4: Distribution of data points per radius
    ax = axes[1, 1]
    ax.bar(grouped['radius_mm'], grouped['count'], width=0.2, alpha=0.7)
    ax.set_xlabel('Radius (mm)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Number of Layers', fontsize=12, fontweight='bold')
    ax.set_title('Data Distribution by Radius', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    
    output_file = v9_dir / "FEP_scaling_investigation.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\nSaved diagnostic plot: {output_file}")
    
    plt.close()
    
    # Summary
    print(f"\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print("\nThe discrepancy occurs because:")
    print("1. Scaling analysis fits power law to ALL individual points (67 layers)")
    print("2. Visual plot shows polynomial fitted to GROUPED MEANS (~10-15 bins)")
    print(f"\nScaling analysis result: n = {slope:.2f} (super-linear)")
    print(f"Visual polynomial: {poly_coeffs[0]:+.4f}*r² {poly_coeffs[1]:+.4f}*r {poly_coeffs[2]:+.4f}")
    
    if poly_coeffs[0] < 0 and slope > 1.1:
        print("\n⚠️ CONFIRMED DISCREPANCY:")
        print("   - Scaling analysis shows SUPER-LINEAR behavior (n > 1)")
        print("   - Visual polynomial is CONCAVE (appears sub-linear)")
        print("\nThis is EXPECTED because:")
        print("   - Power law captures overall trend across all data")
        print("   - Polynomial captures local curvature of grouped means")
        print("   - High variance at large radii can pull power law upward")
        print("\n✓ Both analyses are correct for what they measure!")
    
    print("\n✓ Investigation complete!")


if __name__ == "__main__":
    main()
