"""
Generate Radius-Based Master Plots
===================================

This script generates master plots using contact RADIUS (instead of area) 
as the X-axis. For circular contacts: radius = sqrt(area / π)

Usage:
    python generate_radius_plots.py
    
    Or specify a custom MASTER CSV:
    python generate_radius_plots.py --csv "path/to/MASTER_steppedcone_metrics.csv"

Author: Cheng Sun Lab Team
Date: October 31, 2025
"""

import pandas as pd
import argparse
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from master_plotter import MasterPlotter


def main():
    """Generate radius-based master plots from MASTER CSV."""
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Generate radius-based master plots from MASTER CSV"
    )
    parser.add_argument(
        '--csv',
        type=str,
        default=None,
        help='Path to MASTER CSV file (optional, defaults to V3/MASTER_steppedcone_metrics.csv)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default=None,
        help='Output directory for plots (optional, defaults to same directory as CSV)'
    )
    
    args = parser.parse_args()
    
    # Determine MASTER CSV path
    if args.csv:
        master_csv = Path(args.csv)
    else:
        # Default to V3 MASTER CSV
        master_csv = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V3\MASTER_steppedcone_metrics.csv")
    
    # Verify CSV exists
    if not master_csv.exists():
        print(f"ERROR: MASTER CSV not found: {master_csv}")
        print("\nPlease specify the correct path:")
        print("  python generate_radius_plots.py --csv \"path/to/MASTER_steppedcone_metrics.csv\"")
        return 1
    
    # Determine output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = master_csv.parent
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 70)
    print("RADIUS-BASED MASTER PLOT GENERATOR")
    print("=" * 70)
    print(f"\nInput CSV: {master_csv}")
    print(f"Output Directory: {output_dir}")
    print()
    
    # Load data
    print("Loading MASTER CSV...")
    df = pd.read_csv(master_csv)
    print(f"  Loaded {len(df)} layers")
    print(f"  Conditions: {', '.join(df['condition_label'].unique())}")
    print()
    
    # Create plotter
    plotter = MasterPlotter(output_directory=output_dir, dpi=300)
    
    # Generate radius-based plots
    print("Generating radius-based plots...")
    print("  (Radius calculated as: r = sqrt(Area / π))")
    print()
    
    output_files = plotter.generate_standard_radius_plots(df)
    
    # Summary
    print()
    print("=" * 70)
    print("GENERATION COMPLETE")
    print("=" * 70)
    print(f"\nGenerated {len(output_files)} plots:")
    for plot_file in output_files:
        print(f"  ✓ {plot_file.name}")
    print(f"\nAll plots saved to: {output_dir}")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
