"""
Stiffness Analysis for Presentation Data
=========================================

Analyze material stiffness characteristics for each condition:
1. Dual-regime stiffness detection (rigid vs compliant)
2. Transition point identification
3. Stiffness comparison across conditions
4. Individual condition stiffness plots

Usage:
    python analyze_presentation_stiffness.py
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

# Add support modules
sys.path.insert(0, str(Path(__file__).parent / 'support_modules'))
sys.path.insert(0, str(Path(__file__).parent / 'post-processing'))
from material_stiffness_analyzer import MaterialStiffnessAnalyzer


def analyze_condition_stiffness(df, condition_name, output_dir):
    """
    Analyze stiffness for a single condition
    
    Args:
        df: DataFrame with layer data for this condition
        condition_name: Name of the condition
        output_dir: Directory to save plots
        
    Returns:
        dict with stiffness metrics
    """
    print(f"\n  Analyzing: {condition_name}")
    print(f"    Measurements: {len(df)}")
    
    # Check if we have necessary columns
    required_cols = ['radius_mm', 'peak_force', 'cross_sectional_area_mm2']
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        print(f"    [X] Missing columns: {missing}")
        return None
    
    # Remove invalid data
    valid_mask = (df['peak_force'] > 0) & (df['radius_mm'] > 0)
    df_valid = df[valid_mask].copy()
    
    if len(df_valid) < 5:
        print(f"    [X] Insufficient valid data ({len(df_valid)} points)")
        return None
    
    print(f"    Valid measurements: {len(df_valid)}")
    
    # Initialize stiffness analyzer
    analyzer = MaterialStiffnessAnalyzer()
    
    # Perform stiffness analysis
    try:
        stiffness_results = analyzer.analyze_stiffness(df_valid, condition_name)
        
        if stiffness_results:
            print(f"    Regime detected: {stiffness_results.get('regime_type', 'Unknown')}")
            
            if stiffness_results['regime_type'] == 'dual':
                print(f"      Rigid stiffness: {stiffness_results['rigid_stiffness']:.2f} N/mm")
                print(f"      Compliant stiffness: {stiffness_results['compliant_stiffness']:.2f} N/mm")
                print(f"      Transition radius: {stiffness_results['transition_radius']:.3f} mm")
            else:
                print(f"      Single stiffness: {stiffness_results.get('stiffness', 'N/A')} N/mm")
        
        # Generate stiffness plot
        plot_path = output_dir / f"{condition_name}_stiffness_analysis.png"
        analyzer.plot_stiffness_analysis(df_valid, condition_name, str(plot_path))
        print(f"    [OK] Saved stiffness plot")
        
        return stiffness_results
        
    except Exception as e:
        print(f"    [X] Error in stiffness analysis: {str(e)}")
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
            result['condition'] = condition
            all_results.append(result)
    
    # Save summary results
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
            regime = row['regime_type']
            condition = row['condition'][:35]
            
            if regime == 'dual':
                rigid = f"{row['rigid_stiffness']:.2f}"
                compliant = f"{row['compliant_stiffness']:.2f}"
            else:
                rigid = f"{row.get('stiffness', 'N/A')}"
                compliant = "-"
            
            print(f"{condition:<35} {regime:<10} {rigid:<15} {compliant:<15}")
    
    print("\n" + "="*80)
    print("STIFFNESS ANALYSIS COMPLETE")
    print("="*80)
    print(f"\nGenerated files in: {output_dir}")
    print("  - Individual stiffness plots for each condition")
    print("  - stiffness_summary.csv")


if __name__ == "__main__":
    main()
