"""
Generate Median Master Plots for V9 Data
=========================================

This script generates median-aggregated master plots for V9 SteppedCone data.
Uses MAD-based errors instead of SEM.

Author: Cheng Sun Lab Team
Date: January 10, 2026
"""

import sys
from pathlib import Path
import pandas as pd

# Add support modules to path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir / "post-processing"))
sys.path.insert(0, str(parent_dir / "support_modules"))

from master_plotter import MasterPlotter


def main():
    """Generate median master plots for V9 data"""
    
    print("="*80)
    print("V9 MEDIAN Master Plot Generator")
    print("="*80)
    
    # V9 output directory
    v9_dir = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V9")
    
    # Load the MASTER CSV (created by batch_process_v9.py)
    master_csv = v9_dir / "MASTER_all_metrics.csv"
    
    if not master_csv.exists():
        print(f"ERROR: Master CSV not found: {master_csv}")
        print("Please run batch_process_v9.py first to generate the data.")
        return
    
    print(f"\nLoading data from: {master_csv}")
    df = pd.read_csv(master_csv)
    print(f"Loaded {len(df)} layers")
    
    # Show conditions
    if 'condition_label' in df.columns:
        conditions = sorted(df['condition_label'].unique())
        print(f"\nConditions found: {len(conditions)}")
        for cond in conditions:
            count = len(df[df['condition_label'] == cond])
            print(f"  {cond}: {count} layers")
    
    # Initialize MasterPlotter
    plotter = MasterPlotter(output_directory=v9_dir, dpi=300)
    
    # Generate median plots
    print("\n" + "="*80)
    print("Generating MEDIAN master plots...")
    print("="*80)
    
    output_files = plotter.generate_standard_radius_plots_median(df)
    
    print("\n" + "="*80)
    print("MEDIAN Master Plots Complete!")
    print("="*80)
    print("\nGenerated files:")
    for f in output_files:
        print(f"  - {f.name}")
    
    print("\n✓ Done!")


if __name__ == "__main__":
    main()
