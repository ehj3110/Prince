"""
Scaling Analysis for Cone (Cylinder) Data Only
================================================

Analyzes power-law scaling for cone-shaped parts to validate theoretical prediction:
Force ~ Radius^0.5 (square root relationship)

Theory: For axisymmetric peeling of cylinders, adhesion force scales with perimeter,
which gives F ~ R^0.5 relationship.

Usage:
    python scaling_analysis_cones_only.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Add support modules to path
sys.path.insert(0, str(Path(__file__).parent / 'post-processing'))
from advanced_metrics import AdvancedMetricsCalculator


def main():
    """Run scaling analysis on cone data only"""
    
    # Define paths to cone data only
    base_dir = Path(__file__).parent / "post-processing"
    
    cone_files = [
        base_dir / "results_200umPDMS_1mm_TankV19_Cone_BPAGDA_1000.csv",
        base_dir / "results_ACF_5mm_TankV19_Cone_BPAGDA_200.csv"
    ]
    
    # Load and combine cone data
    dfs = []
    for file in cone_files:
        if file.exists():
            print(f"Loading {file.name}...")
            df = pd.read_csv(file)
            dfs.append(df)
        else:
            print(f"Warning: {file} not found, skipping...")
    
    if not dfs:
        print("Error: No cone data files found!")
        return
    
    cone_df = pd.concat(dfs, ignore_index=True)
    print(f"\nCombined cone data: {len(cone_df)} measurements")
    print(f"Conditions: {sorted(cone_df['condition_label'].unique())}")
    
    # Calculate part radius from area
    # For cone/cylinder: Area = π * r^2, so r = sqrt(Area/π)
    cone_df['part_radius_mm'] = np.sqrt(cone_df['area_mm2'] / np.pi)
    
    print("\nPart radius range:")
    print(f"  Min: {cone_df['part_radius_mm'].min():.3f} mm")
    print(f"  Max: {cone_df['part_radius_mm'].max():.3f} mm")
    
    # Create calculator
    calc = AdvancedMetricsCalculator()
    
    # Output directory
    output_dir = base_dir / "scaling_analysis_cones"
    output_dir.mkdir(exist_ok=True)
    
    print("\n" + "="*80)
    print("SCALING ANALYSIS: CONE/CYLINDER DATA ONLY")
    print("="*80)
    print("\nTheoretical prediction: Force ~ Radius^0.5 (square root scaling)")
    print("This is expected for axisymmetric peeling where crack propagates")
    print("along the perimeter of the circular contact.\n")
    
    # Analyze Force vs Radius (should be ~0.5)
    print("\n" + "="*80)
    print("Analysis 1: Peak Force vs Part Radius")
    print("="*80)
    
    results_force_radius = calc.fit_scaling_laws_by_condition(
        cone_df, 
        y_metric='peak_force_N', 
        x_metric='part_radius_mm'
    )
    
    # Save results
    csv_path = output_dir / "scaling_force_vs_radius.csv"
    results_force_radius.to_csv(csv_path, index=False)
    print(f"Saved: {csv_path}")
    
    # Generate plot
    plot_path = output_dir / "scaling_force_vs_radius.png"
    calc.plot_scaling_analysis(
        cone_df,
        y_metric='peak_force_N',
        x_metric='part_radius_mm',
        output_path=plot_path
    )
    
    # Analyze Force vs Area (should be ~1.0 for comparison)
    print("\n" + "="*80)
    print("Analysis 2: Peak Force vs Contact Area (for comparison)")
    print("="*80)
    
    results_force_area = calc.fit_scaling_laws_by_condition(
        cone_df, 
        y_metric='peak_force_N', 
        x_metric='area_mm2'
    )
    
    # Save results
    csv_path = output_dir / "scaling_force_vs_area.csv"
    results_force_area.to_csv(csv_path, index=False)
    print(f"Saved: {csv_path}")
    
    # Generate plot
    plot_path = output_dir / "scaling_force_vs_area.png"
    calc.plot_scaling_analysis(
        cone_df,
        y_metric='peak_force_N',
        x_metric='area_mm2',
        output_path=plot_path
    )
    
    # Analyze Work vs Radius
    print("\n" + "="*80)
    print("Analysis 3: Work of Adhesion vs Part Radius")
    print("="*80)
    
    results_work_radius = calc.fit_scaling_laws_by_condition(
        cone_df, 
        y_metric='work_of_adhesion_mJ', 
        x_metric='part_radius_mm'
    )
    
    # Save results
    csv_path = output_dir / "scaling_work_vs_radius.csv"
    results_work_radius.to_csv(csv_path, index=False)
    print(f"Saved: {csv_path}")
    
    # Generate plot
    plot_path = output_dir / "scaling_work_vs_radius.png"
    calc.plot_scaling_analysis(
        cone_df,
        y_metric='work_of_adhesion_mJ',
        x_metric='part_radius_mm',
        output_path=plot_path
    )
    
    # Summary comparison
    print("\n" + "="*80)
    print("SUMMARY: Comparison with Theory")
    print("="*80)
    print("\nTheoretical Prediction: Force ~ Radius^0.5")
    print("\nMeasured Exponents (Force vs Radius):")
    for _, row in results_force_radius.iterrows():
        if not np.isnan(row['exponent']):
            deviation = abs(row['exponent'] - 0.5)
            status = "✓ Good" if deviation < 0.15 else "⚠ Check"
            print(f"  {row['condition']:30s}: n = {row['exponent']:.3f} ± {row['exponent_stderr']:.3f}  "
                  f"(R² = {row['r_squared']:.3f})  {status}")
    
    print("\nMeasured Exponents (Force vs Area, expected ~1.0 for uniform adhesion):")
    for _, row in results_force_area.iterrows():
        if not np.isnan(row['exponent']):
            deviation = abs(row['exponent'] - 1.0)
            status = "✓ Good" if deviation < 0.15 else "⚠ Check"
            print(f"  {row['condition']:30s}: n = {row['exponent']:.3f} ± {row['exponent_stderr']:.3f}  "
                  f"(R² = {row['r_squared']:.3f})  {status}")
    
    print("\n" + "="*80)
    print("COMPLETE!")
    print("="*80)
    print(f"\nAll outputs saved to: {output_dir}")
    print("\nFiles created:")
    print("  - scaling_force_vs_radius.csv & .png")
    print("  - scaling_force_vs_area.csv & .png")
    print("  - scaling_work_vs_radius.csv & .png")


if __name__ == "__main__":
    main()
