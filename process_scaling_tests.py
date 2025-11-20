"""
Process All ScalingTests Folders and Run Comprehensive Scaling Analysis
========================================================================

Processes all data in the ScalingTests directory including both Cone and Pyramid geometries,
then performs scaling analysis to validate theoretical predictions:
- Cones/Cylinders: Force ~ Radius^0.5 (perimeter-dominated)
- Pyramids: Need to analyze (area vs radius relationship)

Usage:
    python process_scaling_tests.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
import subprocess

# Add support modules to path
sys.path.insert(0, str(Path(__file__).parent / 'support_modules'))
sys.path.insert(0, str(Path(__file__).parent / 'post-processing'))


def process_all_folders():
    """Process all folders in ScalingTests directory"""
    
    scaling_dir = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\ScalingTests")
    output_dir = Path(__file__).parent / "post-processing" / "scaling_tests_results"
    output_dir.mkdir(exist_ok=True)
    
    # Get all folders
    folders = sorted([f for f in scaling_dir.iterdir() if f.is_dir()])
    
    print("="*80)
    print("PROCESSING SCALING TESTS DATA")
    print("="*80)
    print(f"\nFound {len(folders)} folders:")
    for folder in folders:
        print(f"  - {folder.name}")
    
    # Process each folder
    processor_script = Path(__file__).parent / "process_single_v4_folder.py"
    
    for folder in folders:
        folder_name = folder.name
        output_csv = output_dir / f"results_{folder_name}.csv"
        
        print(f"\n{'='*80}")
        print(f"Processing: {folder_name}")
        print(f"{'='*80}")
        
        # Run processing script with absolute folder path
        cmd = [
            "python",
            str(processor_script),
            str(folder),  # Use absolute path
            str(output_csv)
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"✓ Successfully processed {folder_name}")
            print(f"  Output: {output_csv}")
        else:
            print(f"✗ Error processing {folder_name}")
            print(f"  Error: {result.stderr}")
    
    return output_dir


def run_scaling_analysis(results_dir: Path):
    """Run comprehensive scaling analysis on processed data"""
    
    from advanced_metrics import AdvancedMetricsCalculator
    
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
        results = calc.fit_scaling_laws_by_condition(cone_df, 'peak_force_N', 'part_radius_mm')
        results.to_csv(cone_output / "scaling_force_vs_radius.csv", index=False)
        calc.plot_scaling_analysis(cone_df, 'peak_force_N', 'part_radius_mm', 
                                   cone_output / "scaling_force_vs_radius.png")
        
        # Force vs Area
        results = calc.fit_scaling_laws_by_condition(cone_df, 'peak_force_N', 'area_mm2')
        results.to_csv(cone_output / "scaling_force_vs_area.csv", index=False)
        calc.plot_scaling_analysis(cone_df, 'peak_force_N', 'area_mm2',
                                   cone_output / "scaling_force_vs_area.png")
        
        # Work vs Radius
        results = calc.fit_scaling_laws_by_condition(cone_df, 'work_of_adhesion_mJ', 'part_radius_mm')
        results.to_csv(cone_output / "scaling_work_vs_radius.csv", index=False)
        calc.plot_scaling_analysis(cone_df, 'work_of_adhesion_mJ', 'part_radius_mm',
                                   cone_output / "scaling_work_vs_radius.png")
    
    # ===== PYRAMID ANALYSIS =====
    if len(pyramid_df) > 0:
        print(f"\n{'='*80}")
        print("PYRAMID SCALING ANALYSIS")
        print(f"{'='*80}")
        print("\nExploratory analysis for pyramid geometry")
        
        # Force vs Radius
        results = calc.fit_scaling_laws_by_condition(pyramid_df, 'peak_force_N', 'part_radius_mm')
        results.to_csv(pyramid_output / "scaling_force_vs_radius.csv", index=False)
        calc.plot_scaling_analysis(pyramid_df, 'peak_force_N', 'part_radius_mm',
                                   pyramid_output / "scaling_force_vs_radius.png")
        
        # Force vs Area
        results = calc.fit_scaling_laws_by_condition(pyramid_df, 'peak_force_N', 'area_mm2')
        results.to_csv(pyramid_output / "scaling_force_vs_area.csv", index=False)
        calc.plot_scaling_analysis(pyramid_df, 'peak_force_N', 'area_mm2',
                                   pyramid_output / "scaling_force_vs_area.png")
        
        # Work vs Radius
        results = calc.fit_scaling_laws_by_condition(pyramid_df, 'work_of_adhesion_mJ', 'part_radius_mm')
        results.to_csv(pyramid_output / "scaling_work_vs_radius.csv", index=False)
        calc.plot_scaling_analysis(pyramid_df, 'work_of_adhesion_mJ', 'part_radius_mm',
                                   pyramid_output / "scaling_work_vs_radius.png")
    
    # ===== COMBINED ANALYSIS =====
    print(f"\n{'='*80}")
    print("COMBINED SCALING ANALYSIS (All Geometries)")
    print(f"{'='*80}")
    
    # Force vs Radius
    results = calc.fit_scaling_laws_by_condition(combined_df, 'peak_force_N', 'part_radius_mm')
    results.to_csv(combined_output / "scaling_force_vs_radius.csv", index=False)
    calc.plot_scaling_analysis(combined_df, 'peak_force_N', 'part_radius_mm',
                               combined_output / "scaling_force_vs_radius.png")
    
    # Force vs Area
    results = calc.fit_scaling_laws_by_condition(combined_df, 'peak_force_N', 'area_mm2')
    results.to_csv(combined_output / "scaling_force_vs_area.csv", index=False)
    calc.plot_scaling_analysis(combined_df, 'peak_force_N', 'area_mm2',
                               combined_output / "scaling_force_vs_area.png")
    
    # Work vs Radius
    results = calc.fit_scaling_laws_by_condition(combined_df, 'work_of_adhesion_mJ', 'part_radius_mm')
    results.to_csv(combined_output / "scaling_work_vs_radius.csv", index=False)
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


def main():
    """Main execution"""
    
    # Process all folders
    results_dir = process_all_folders()
    
    # Run scaling analysis
    run_scaling_analysis(results_dir)


if __name__ == "__main__":
    main()
