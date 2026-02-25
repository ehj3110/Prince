"""
Reorganize V9 Master Plots and Generate Log-Log Versions
========================================================

This script:
1. Creates organized folder structure (data/, Mean plots/, Median plots/, Log-Log plots/)
2. Moves existing files into appropriate folders
3. Generates new log-log master plots

Author: Cheng Sun Lab Team
Date: January 11, 2026
"""

import sys
from pathlib import Path
import pandas as pd
import shutil

# Add support modules to path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir / "post-processing"))
sys.path.insert(0, str(parent_dir / "support_modules"))

from master_plotter import MasterPlotter


def create_folder_structure(base_dir: Path):
    """Create organized folder structure for master plots"""
    print("\n" + "="*80)
    print("Creating Folder Structure")
    print("="*80)
    
    folders = {
        'data': base_dir / 'data',
        'mean': base_dir / 'Mean plots',
        'median': base_dir / 'Median plots',
        'loglog': base_dir / 'Log-Log plots'
    }
    
    for name, folder in folders.items():
        folder.mkdir(exist_ok=True)
        print(f"  ✓ Created: {folder.name}/")
    
    return folders


def move_existing_files(base_dir: Path, folders: dict):
    """Move existing master plot files into organized folders"""
    print("\n" + "="*80)
    print("Organizing Existing Files")
    print("="*80)
    
    # Define file patterns and destinations
    moves = {
        'data': [
            'MASTER_all_metrics.csv',
            'MASTER_scaling_*.csv',
            'automated_work_all_data.csv'
        ],
        'mean': [
            'MASTER_radius_analysis.png',
            'MASTER_radius_analysis_modified.png',
            'MASTER_distance_analysis.png',
            'MASTER_stiffness_analysis.png',
            'automated_work_mean.png',
            'automated_work_mean_vs_median_comparison.png'
        ],
        'median': [
            'MASTER_radius_analysis_MEDIAN.png',
            'MASTER_radius_analysis_modified_MEDIAN.png',
            'automated_work_median.png'
        ]
    }
    
    for category, patterns in moves.items():
        dest_folder = folders[category]
        for pattern in patterns:
            if '*' in pattern:
                # Handle wildcards
                for file in base_dir.glob(pattern):
                    if file.is_file():
                        try:
                            shutil.move(str(file), str(dest_folder / file.name))
                            print(f"  Moved: {file.name} → {dest_folder.name}/")
                        except Exception as e:
                            print(f"  ⚠ Could not move {file.name}: {e}")
            else:
                # Handle exact filenames
                file = base_dir / pattern
                if file.exists():
                    try:
                        shutil.move(str(file), str(dest_folder / file.name))
                        print(f"  Moved: {file.name} → {dest_folder.name}/")
                    except Exception as e:
                        print(f"  ⚠ Could not move {file.name}: {e}")


def generate_loglog_plots(base_dir: Path, folders: dict):
    """Generate log-log master plots"""
    print("\n" + "="*80)
    print("Generating Log-Log Master Plots")
    print("="*80)
    
    # Check for data CSV
    data_csv = folders['data'] / "MASTER_all_metrics.csv"
    if not data_csv.exists():
        # Try original location
        data_csv_orig = base_dir / "MASTER_all_metrics.csv"
        if data_csv_orig.exists():
            data_csv = data_csv_orig
        else:
            print(f"ERROR: Data CSV not found!")
            return []
    
    print(f"\nLoading data from: {data_csv}")
    df = pd.read_csv(data_csv)
    print(f"Loaded {len(df)} layers")
    
    # Show conditions
    if 'condition_label' in df.columns:
        conditions = sorted(df['condition_label'].unique())
        print(f"\nConditions found: {len(conditions)}")
        for cond in conditions:
            count = len(df[df['condition_label'] == cond])
            print(f"  {cond}: {count} layers")
    
    # Initialize MasterPlotter to save in Log-Log plots folder
    plotter = MasterPlotter(output_directory=folders['loglog'], dpi=300)
    
    # Generate log-log plots
    output_files = plotter.generate_standard_radius_plots_loglog(df)
    
    print(f"\n✓ Generated {len(output_files)} log-log plots")
    
    return output_files


def main():
    """Main execution"""
    print("="*80)
    print("V9 Master Plots Reorganization & Log-Log Generation")
    print("="*80)
    
    # V9 output directory
    v9_dir = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V9")
    
    if not v9_dir.exists():
        print(f"ERROR: V9 directory not found: {v9_dir}")
        return
    
    # Step 1: Create folder structure
    folders = create_folder_structure(v9_dir)
    
    # Step 2: Move existing files
    move_existing_files(v9_dir, folders)
    
    # Step 3: Generate log-log plots
    output_files = generate_loglog_plots(v9_dir, folders)
    
    # Final summary
    print("\n" + "="*80)
    print("COMPLETE!")
    print("="*80)
    print("\nFolder structure:")
    print(f"  {v9_dir.name}/")
    print(f"    ├── data/              (CSV files)")
    print(f"    ├── Mean plots/        (Mean aggregation plots)")
    print(f"    ├── Median plots/      (Median aggregation plots)")
    print(f"    └── Log-Log plots/     (Log-log scale plots)")
    
    if output_files:
        print("\nGenerated log-log plots:")
        for f in output_files:
            print(f"  - {f.name}")
    
    print("\n✓ All done!")


if __name__ == "__main__":
    main()
