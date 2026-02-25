"""
Stiffness Analysis for Presentation Data (Simplified Version)
==============================================================

Analyze effective stiffness for each condition:
1. Calculate effective stiffness (peak force / radius)
2. Detect dual-regime behavior (small vs large radius)
3. Generate stiffness plots
4. Create summary CSV

Usage:
    python analyze_presentation_stiffness_v2.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import stats


def analyze_condition_stiffness(df, condition_name, output_dir):
    """
    Analyze stiffness for a single condition using force vs radius scaling
    
    Args:
        df: DataFrame with data for this condition
        condition_name: Name of condition
        output_dir: Directory to save plots
        
    Returns:
        dict with stiffness results
    """
    print(f"\n  Analyzing: {condition_name}")
    print(f"    Measurements: {len(df)}")
    
    # Filter valid data (need cross-sectional area and peak force)
    valid_mask = (
        df['cross_sectional_area_mm2'].notna() &
        (df['cross_sectional_area_mm2'] > 0) &
        df['peak_force'].notna() &
        (df['peak_force'] > 0) &
        df['radius_mm'].notna() &
        (df['radius_mm'] > 0)
    )
    
    df_valid = df[valid_mask].copy()
    print(f"    Valid measurements: {len(df_valid)}")
    
    if len(df_valid) < 3:
        print(f"    [X] Insufficient valid data")
        return None
    
    try:
        # Calculate stiffness as peak force / radius
        # This is an effective stiffness metric for adhesion testing
        df_valid['effective_stiffness'] = df_valid['peak_force'] / df_valid['radius_mm']
        
        # Get statistics
        mean_stiffness = df_valid['effective_stiffness'].mean()
        median_stiffness = df_valid['effective_stiffness'].median()
        std_stiffness = df_valid['effective_stiffness'].std()
        
        print(f"    Mean stiffness: {mean_stiffness:.2f} N/mm")
        print(f"    Median stiffness: {median_stiffness:.2f} N/mm")
        print(f"    Std dev: {std_stiffness:.2f} N/mm")
        
        # Check if dual-regime (look for bimodal distribution by radius bins)
        # Split data into small (< median radius) and large (>= median radius)
        median_radius = df_valid['radius_mm'].median()
        small_radius = df_valid[df_valid['radius_mm'] < median_radius]
        large_radius = df_valid[df_valid['radius_mm'] >= median_radius]
        
        regime_type = 'single'
        rigid_stiffness = np.nan
        compliant_stiffness = np.nan
        transition_radius = np.nan
        
        if len(small_radius) >= 3 and len(large_radius) >= 3:
            small_mean = small_radius['effective_stiffness'].mean()
            large_mean = large_radius['effective_stiffness'].mean()
            
            # If there's >20% difference, consider it dual-regime
            relative_diff = abs(small_mean - large_mean) / max(small_mean, large_mean)
            if relative_diff > 0.20:
                regime_type = 'dual'
                # Assign based on which is stiffer
                if small_mean > large_mean:
                    rigid_stiffness = small_mean
                    compliant_stiffness = large_mean
                else:
                    rigid_stiffness = large_mean
                    compliant_stiffness = small_mean
                transition_radius = median_radius
                print(f"    [Dual regime detected]")
                print(f"    Rigid: {rigid_stiffness:.2f} N/mm")
                print(f"    Compliant: {compliant_stiffness:.2f} N/mm")
                print(f"    Transition: {transition_radius:.3f} mm")
        
        # Generate stiffness plot
        fig, axes = plt.subplots(1, 2, figsize=(16, 6))
        
        # Plot 1: Peak force vs radius
        ax1 = axes[0]
        ax1.scatter(df_valid['radius_mm'], df_valid['peak_force'], 
                   alpha=0.6, s=100, c='blue')
        ax1.set_xlabel('Radius (mm)', fontsize=27, fontweight='bold')
        ax1.set_ylabel('Peak Force (N)', fontsize=27, fontweight='bold')
        ax1.set_title(f'{condition_name}\nPeak Force vs Radius', 
                     fontsize=21, fontweight='bold')
        ax1.tick_params(labelsize=15)
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Effective stiffness histogram
        ax2 = axes[1]
        ax2.hist(df_valid['effective_stiffness'], bins=20, 
                alpha=0.7, color='green', edgecolor='black')
        ax2.axvline(mean_stiffness, color='red', linestyle='--', 
                   linewidth=2, label=f'Mean: {mean_stiffness:.2f} N/mm')
        ax2.axvline(median_stiffness, color='orange', linestyle='--', 
                   linewidth=2, label=f'Median: {median_stiffness:.2f} N/mm')
        ax2.set_xlabel('Effective Stiffness (N/mm)', fontsize=27, fontweight='bold')
        ax2.set_ylabel('Count', fontsize=27, fontweight='bold')
        ax2.set_title(f'{condition_name}\nStiffness Distribution', 
                     fontsize=21, fontweight='bold')
        ax2.tick_params(labelsize=15)
        ax2.legend(fontsize=15)
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plot_path = output_dir / f"{condition_name}_stiffness_analysis.png"
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"    [OK] Saved stiffness plot")
        
        # Return results for summary
        result = {
            'condition': condition_name,
            'regime_type': regime_type,
            'n_measurements': len(df_valid),
            'mean_stiffness_N_per_mm': mean_stiffness,
            'median_stiffness_N_per_mm': median_stiffness,
            'std_stiffness_N_per_mm': std_stiffness
        }
        
        if regime_type == 'dual':
            result['rigid_stiffness_N_per_mm'] = rigid_stiffness
            result['compliant_stiffness_N_per_mm'] = compliant_stiffness
            result['transition_radius_mm'] = transition_radius
        
        return result
        
    except Exception as e:
        print(f"    [X] Error in stiffness analysis: {e}")
        return None


def main():
    """Analyze stiffness for all Presentation data conditions"""
    
    pres_dir = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\Presentation data")
    
    print("="*80)
    print("PRESENTATION DATA - STIFFNESS ANALYSIS")
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
    output_dir = pres_dir / "stiffness_analysis"
    output_dir.mkdir(exist_ok=True)
    print(f"Output directory: {output_dir}")
    
    # Analyze each condition
    print("\n" + "="*80)
    print("ANALYZING STIFFNESS BY CONDITION")
    print("="*80)
    
    conditions = sorted(df['condition'].unique())
    all_results = []
    
    for condition in conditions:
        condition_data = df[df['condition'] == condition].copy()
        
        result = analyze_condition_stiffness(
            condition_data,
            condition,
            output_dir
        )
        
        if result:
            all_results.append(result)
    
    # Save results
    if all_results:
        results_df = pd.DataFrame(all_results)
        summary_csv = output_dir / "stiffness_summary.csv"
        results_df.to_csv(summary_csv, index=False)
        print(f"\n[OK] Saved stiffness summary to: {summary_csv.name}")
        
        # Print summary table
        print("\n" + "="*80)
        print("STIFFNESS SUMMARY")
        print("="*80)
        print(f"\n{'Condition':<35} {'Regime':<10} {'Rigid (N/mm)':<15} {'Compliant (N/mm)':<15}")
        print("-"*80)
        
        for _, row in results_df.iterrows():
            condition = row['condition'][:35]
            regime = row['regime_type']
            
            if regime == 'dual':
                rigid = f"{row['rigid_stiffness_N_per_mm']:.2f}"
                compliant = f"{row['compliant_stiffness_N_per_mm']:.2f}"
            else:
                rigid = f"{row['mean_stiffness_N_per_mm']:.2f}"
                compliant = "---"
            
            print(f"{condition:<35} {regime:<10} {rigid:<15} {compliant:<15}")
    
    print("\n" + "="*80)
    print("STIFFNESS ANALYSIS COMPLETE")
    print("="*80)
    print(f"\nGenerated files in: {output_dir}")
    print("  - Individual stiffness plots for each condition")
    print("  - stiffness_summary.csv")


if __name__ == "__main__":
    main()
