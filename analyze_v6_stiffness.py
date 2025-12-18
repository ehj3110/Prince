"""
V6 Stiffness Analysis Script
=============================

Reprocesses V6 data with material stiffness analysis and generates scaling plots.

Usage:
    python analyze_v6_stiffness.py
"""

import sys
from pathlib import Path
import pandas as pd

# Add paths
sys.path.insert(0, str(Path(__file__).parent / 'batch_processors'))
sys.path.insert(0, str(Path(__file__).parent / 'post-processing'))

from batch_process_universal import UniversalBatchProcessor
from stiffness_scaling_analyzer import StiffnessScalingAnalyzer

# V6 data location
V6_DIR = Path(r'C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V6')

def main():
    print("="*80)
    print("V6 STIFFNESS ANALYSIS")
    print("="*80)
    print(f"\nProcessing folder: {V6_DIR}")
    
    # Step 1: Reprocess V6 with stiffness calculations
    print("\n" + "="*80)
    print("STEP 1: Batch Processing with Stiffness Analysis")
    print("="*80)
    
    processor = UniversalBatchProcessor(str(V6_DIR))
    processor.process_all_folders()
    
    # Save the CSV with stiffness data
    csv_path = processor.save_combined_csv()
    processor.generate_master_plots()
    
    # Step 2: Load results
    print("\n" + "="*80)
    print("STEP 2: Loading Results")
    print("="*80)
    
    if not csv_path or not csv_path.exists():
        print(f"ERROR: CSV not generated properly")
        return
    
    df = pd.read_csv(csv_path)
    print(f"\nLoaded {len(df)} measurements")
    print(f"Columns: {len(df.columns)}")
    
    # Check stiffness columns
    stiffness_cols = [col for col in df.columns if 'stiffness' in col.lower()]
    print(f"\nStiffness columns: {len(stiffness_cols)}")
    for col in stiffness_cols:
        print(f"  - {col}")
    
    # Step 3: Stiffness scaling analysis
    print("\n" + "="*80)
    print("STEP 3: Stiffness Scaling Analysis")
    print("="*80)
    
    analyzer = StiffnessScalingAnalyzer(output_dir=str(V6_DIR))
    
    # Analyze scaling
    results = analyzer.analyze_stiffness_scaling(
        df=df,
        stiffness_col='material_stiffness_N_per_mm',
        area_col='area_mm2',
        condition_col='detailed_condition',
        min_r_squared=0.5  # Only include well-fit data
    )
    
    if not results:
        print("\nWARNING: No valid stiffness data found")
        print("This could mean:")
        print("  1. Stiffness calculation failed for all measurements")
        print("  2. R² threshold is too high")
        print("  3. Data format issue")
        return
    
    # Step 4: Generate plots
    print("\n" + "="*80)
    print("STEP 4: Generating Plots")
    print("="*80)
    
    analyzer.plot_stiffness_vs_area(results)
    analyzer.plot_stiffness_vs_radius(results)
    
    # Step 5: Generate report
    print("\n" + "="*80)
    print("STEP 5: Generating Report")
    print("="*80)
    
    analyzer.generate_summary_report(results)
    
    # Step 6: Summary statistics
    print("\n" + "="*80)
    print("SUMMARY STATISTICS")
    print("="*80)
    
    for condition, data in results.items():
        print(f"\n{condition}:")
        print(f"  n = {data['n_measurements']}")
        print(f"  Stiffness: {data['stiffness_mean_N_per_mm']:.3f} ± {data['stiffness_std_N_per_mm']:.3f} N/mm")
        print(f"  Area exponent: {data['area_scaling']['n']:.3f} (95% CI: [{data['area_scaling']['n_ci_95'][0]:.3f}, {data['area_scaling']['n_ci_95'][1]:.3f}])")
        print(f"  Radius exponent: {data['radius_scaling']['n']:.3f} (95% CI: [{data['radius_scaling']['n_ci_95'][0]:.3f}, {data['radius_scaling']['n_ci_95'][1]:.3f}])")
    
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    print(f"\nResults saved to: {V6_DIR}")
    print("\nGenerated files:")
    print("  - MASTER_all_metrics.csv (with stiffness columns)")
    print("  - stiffness_vs_area_scaling.png")
    print("  - stiffness_vs_radius_scaling.png")
    print("  - stiffness_scaling_report.txt")

if __name__ == "__main__":
    main()
