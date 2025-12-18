"""
V7 Data Analysis Script
=======================

Processes V7 data with material stiffness analysis and generates:
- Master plots for radius and area (no area fraction plots)
- Individual summary plots for each test folder

Usage:
    python analyze_v7.py
"""

import sys
from pathlib import Path
import pandas as pd

# Add paths
sys.path.insert(0, str(Path(__file__).parent / 'batch_processors'))
sys.path.insert(0, str(Path(__file__).parent / 'post-processing'))

from batch_process_universal import UniversalBatchProcessor
from master_plotter import MasterPlotter

# V7 data location
V7_DIR = Path(r'C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V7')

def main():
    print("="*80)
    print("V7 DATA ANALYSIS")
    print("="*80)
    print(f"\nProcessing folder: {V7_DIR}")
    print(f"\nNew folder naming convention:")
    print("  Membrane_Gap_Tank_Model_Speed_Date_Iteration")
    print("  Example: USWTEMPO_2mm_V23_Cone_1000_1209_V1")
    
    # Step 1: Batch process all V7 folders
    print("\n" + "="*80)
    print("STEP 1: Batch Processing with Stiffness Analysis")
    print("="*80)
    
    processor = UniversalBatchProcessor(str(V7_DIR))
    processor.process_all_folders()
    
    # Step 2: Save combined CSV
    print("\n" + "="*80)
    print("STEP 2: Saving Combined Results")
    print("="*80)
    
    csv_path = processor.save_combined_csv()
    
    if not csv_path or not csv_path.exists():
        print(f"ERROR: CSV not generated properly")
        return
    
    print(f"\nSaved: {csv_path.name}")
    
    # Step 3: Load results and check data
    print("\n" + "="*80)
    print("STEP 3: Validating Results")
    print("="*80)
    
    df = pd.read_csv(csv_path)
    print(f"\nTotal measurements: {len(df)}")
    print(f"Total columns: {len(df.columns)}")
    
    # Check for required columns
    if 'condition_label' in df.columns:
        print(f"\nConditions found:")
        for condition in df['condition_label'].unique():
            count = len(df[df['condition_label'] == condition])
            print(f"  - {condition}: {count} measurements")
    
    # Check stiffness columns
    stiffness_cols = [col for col in df.columns if 'stiffness' in col.lower()]
    if stiffness_cols:
        print(f"\nStiffness columns: {len(stiffness_cols)}")
        print(f"  Primary: material_stiffness_N_per_mm")
        print(f"  Mean: {df['material_stiffness_N_per_mm'].mean():.3f} N/mm")
        print(f"  Std: {df['material_stiffness_N_per_mm'].std():.3f} N/mm")
    
    # Step 4: Generate master plots
    print("\n" + "="*80)
    print("STEP 4: Generating Master Plots")
    print("="*80)
    
    # Ensure detailed_condition exists
    if 'detailed_condition' not in df.columns:
        df['detailed_condition'] = df['condition_label'] + ' + ' + df['tank_type']
    
    # Initialize MasterPlotter (correct way)
    plotter = MasterPlotter(output_directory=str(V7_DIR), dpi=300)
    
    print("\nGenerating RADIUS-based master plots...")
    try:
        plotter.generate_standard_radius_plots(df)
        print("  ✓ Radius-based plots generated")
    except Exception as e:
        print(f"  Warning: Radius plots failed - {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\nGenerating AREA-based master plots...")
    try:
        # Generate standard area plots (but not area fraction plots)
        plotter.generate_standard_plots(df)
        print("  ✓ Area-based plots generated")
    except Exception as e:
        print(f"  Warning: Area plots failed - {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Step 5: Summary
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    print(f"\nResults saved to: {V7_DIR}")
    print("\nGenerated files:")
    print("  CSV:")
    print("    - MASTER_all_metrics.csv")
    print("\n  Master Plots (Radius-based):")
    print("    - MASTER_radius_analysis.png")
    print("    - MASTER_work_vs_radius.png")
    print("    - MASTER_stiffness_vs_radius.png")
    print("\n  Master Plots (Area-based):")
    print("    - MASTER_area_analysis.png")
    print("    - MASTER_work_vs_area.png")
    print("    - MASTER_stiffness_vs_area.png")
    print("\n  Individual Summary Plots:")
    print("    - <folder_name>/summary_plot.png (in each test folder)")
    print("\nNote: Area fraction plots NOT generated (as requested)")


if __name__ == "__main__":
    main()
