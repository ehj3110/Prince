"""
Standalone script to run scaling analysis on ScalingTests processed data
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Add post-processing to path
sys.path.insert(0, str(Path(__file__).parent / "post-processing"))
from advanced_metrics import AdvancedMetricsCalculator

def run_scaling_analysis():
    """Run comprehensive scaling analysis on processed ScalingTests data"""
    
    results_dir = Path(__file__).parent / "post-processing" / "scaling_tests_results"
    
    # Load all result files
    result_files = list(results_dir.glob("results_*.csv"))
    
    if not result_files:
        print("Error: No result files found!")
        return
    
    print(f"\n{'='*80}")
    print("LOADING PROCESSED DATA")
    print(f"{'='*80}")
    
    dfs = []
    for file in result_files:
        print(f"Loading {file.name}...")
        df = pd.read_csv(file)
        dfs.append(df)
    
    combined_df = pd.concat(dfs, ignore_index=True)
    print(f"\nCombined: {len(combined_df)} measurements")
    print(f"Conditions: {sorted(combined_df['condition_label'].unique())}")
    
    # Separate cone and pyramid data
    cone_df = combined_df[combined_df['model'] == 'Cone'].copy()
    pyramid_df = combined_df[combined_df['model'] == 'Pyramid'].copy()
    
    print(f"\nCone measurements: {len(cone_df)}")
    print(f"Pyramid measurements: {len(pyramid_df)}")
    
    # Calculate radius for all data
    combined_df['part_radius_mm'] = np.sqrt(combined_df['area_mm2'] / np.pi)
    cone_df['part_radius_mm'] = np.sqrt(cone_df['area_mm2'] / np.pi)
    pyramid_df['part_radius_mm'] = np.sqrt(pyramid_df['area_mm2'] / np.pi)
    
    # Create calculator
    calc = AdvancedMetricsCalculator()
    
    # Create output directories
    cone_output = results_dir / "scaling_analysis_cones"
    pyramid_output = results_dir / "scaling_analysis_pyramids"
    combined_output = results_dir / "scaling_analysis_combined"
    
    for dir in [cone_output, pyramid_output, combined_output]:
        dir.mkdir(exist_ok=True)
    
    # ===== CONE ANALYSIS =====
    if len(cone_df) > 0:
        print(f"\n{'='*80}")
        print("CONE (CYLINDER) SCALING ANALYSIS")
        print(f"{'='*80}")
        print("\nTheoretical prediction: Force ~ Radius^0.5")
        
        # Force vs Radius
        print("\n1. Fitting Force vs Radius (comparing to n=0.5)...")
        results = calc.fit_scaling_laws_by_condition(cone_df, 'peak_force_N', 'part_radius_mm')
        results.to_csv(cone_output / "scaling_force_vs_radius.csv", index=False)
        print(results[['condition', 'exponent', 'exponent_stderr', 'r_squared']].to_string(index=False))
        calc.plot_scaling_analysis(cone_df, 'peak_force_N', 'part_radius_mm', 
                                   cone_output / "scaling_force_vs_radius.png")
        
        # Force vs Area
        print("\n2. Fitting Force vs Area...")
        results = calc.fit_scaling_laws_by_condition(cone_df, 'peak_force_N', 'area_mm2')
        results.to_csv(cone_output / "scaling_force_vs_area.csv", index=False)
        print(results[['condition', 'exponent', 'exponent_stderr', 'r_squared']].to_string(index=False))
        calc.plot_scaling_analysis(cone_df, 'peak_force_N', 'area_mm2',
                                   cone_output / "scaling_force_vs_area.png")
        
        # Work vs Radius
        print("\n3. Fitting Work vs Radius...")
        results = calc.fit_scaling_laws_by_condition(cone_df, 'work_of_adhesion_mJ', 'part_radius_mm')
        results.to_csv(cone_output / "scaling_work_vs_radius.csv", index=False)
        print(results[['condition', 'exponent', 'exponent_stderr', 'r_squared']].to_string(index=False))
        calc.plot_scaling_analysis(cone_df, 'work_of_adhesion_mJ', 'part_radius_mm',
                                   cone_output / "scaling_work_vs_radius.png")
    
    # ===== PYRAMID ANALYSIS =====
    if len(pyramid_df) > 0:
        print(f"\n{'='*80}")
        print("PYRAMID SCALING ANALYSIS")
        print(f"{'='*80}")
        print("\nExploratory analysis for pyramid geometry")
        
        # Force vs Radius
        print("\n1. Fitting Force vs Radius...")
        results = calc.fit_scaling_laws_by_condition(pyramid_df, 'peak_force_N', 'part_radius_mm')
        results.to_csv(pyramid_output / "scaling_force_vs_radius.csv", index=False)
        print(results[['condition', 'exponent', 'exponent_stderr', 'r_squared']].to_string(index=False))
        calc.plot_scaling_analysis(pyramid_df, 'peak_force_N', 'part_radius_mm',
                                   pyramid_output / "scaling_force_vs_radius.png")
        
        # Force vs Area
        print("\n2. Fitting Force vs Area...")
        results = calc.fit_scaling_laws_by_condition(pyramid_df, 'peak_force_N', 'area_mm2')
        results.to_csv(pyramid_output / "scaling_force_vs_area.csv", index=False)
        print(results[['condition', 'exponent', 'exponent_stderr', 'r_squared']].to_string(index=False))
        calc.plot_scaling_analysis(pyramid_df, 'peak_force_N', 'area_mm2',
                                   pyramid_output / "scaling_force_vs_area.png")
        
        # Work vs Radius
        print("\n3. Fitting Work vs Radius...")
        results = calc.fit_scaling_laws_by_condition(pyramid_df, 'work_of_adhesion_mJ', 'part_radius_mm')
        results.to_csv(pyramid_output / "scaling_work_vs_radius.csv", index=False)
        print(results[['condition', 'exponent', 'exponent_stderr', 'r_squared']].to_string(index=False))
        calc.plot_scaling_analysis(pyramid_df, 'work_of_adhesion_mJ', 'part_radius_mm',
                                   pyramid_output / "scaling_work_vs_radius.png")
    
    # ===== COMBINED ANALYSIS =====
    print(f"\n{'='*80}")
    print("COMBINED SCALING ANALYSIS (All Geometries)")
    print(f"{'='*80}")
    
    # Force vs Radius
    print("\n1. Fitting Force vs Radius...")
    results = calc.fit_scaling_laws_by_condition(combined_df, 'peak_force_N', 'part_radius_mm')
    results.to_csv(combined_output / "scaling_force_vs_radius.csv", index=False)
    print(results[['condition', 'exponent', 'exponent_stderr', 'r_squared']].to_string(index=False))
    calc.plot_scaling_analysis(combined_df, 'peak_force_N', 'part_radius_mm',
                               combined_output / "scaling_force_vs_radius.png")
    
    # Force vs Area
    print("\n2. Fitting Force vs Area...")
    results = calc.fit_scaling_laws_by_condition(combined_df, 'peak_force_N', 'area_mm2')
    results.to_csv(combined_output / "scaling_force_vs_area.csv", index=False)
    print(results[['condition', 'exponent', 'exponent_stderr', 'r_squared']].to_string(index=False))
    calc.plot_scaling_analysis(combined_df, 'peak_force_N', 'area_mm2',
                               combined_output / "scaling_force_vs_area.png")
    
    # Work vs Radius
    print("\n3. Fitting Work vs Radius...")
    results = calc.fit_scaling_laws_by_condition(combined_df, 'work_of_adhesion_mJ', 'part_radius_mm')
    results.to_csv(combined_output / "scaling_work_vs_radius.csv", index=False)
    print(results[['condition', 'exponent', 'exponent_stderr', 'r_squared']].to_string(index=False))
    calc.plot_scaling_analysis(combined_df, 'work_of_adhesion_mJ', 'part_radius_mm',
                               combined_output / "scaling_work_vs_radius.png")
    
    # Save combined dataset
    combined_csv = results_dir / "MASTER_scaling_tests_all_data.csv"
    combined_df.to_csv(combined_csv, index=False)
    print(f"\n✓ Saved combined dataset: {combined_csv}")
    
    print(f"\n{'='*80}")
    print("COMPLETE!")
    print(f"{'='*80}")
    print(f"\nAll outputs saved to: {results_dir}")
    print(f"\nOutput directories:")
    print(f"  - Cone analysis: {cone_output}")
    print(f"  - Pyramid analysis: {pyramid_output}")
    print(f"  - Combined analysis: {combined_output}")


if __name__ == "__main__":
    run_scaling_analysis()
