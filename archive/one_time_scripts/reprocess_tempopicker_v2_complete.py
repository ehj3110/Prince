"""
Quick Reprocess TEMPO Picker V2 - All Folders
==============================================

Reprocess all 6 TEMPO Picker V2 folders to fix hydrodynamic locking detection issues.
"""

import subprocess
from pathlib import Path
import sys

def main():
    v2_dir = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\TEMPO Picker\V2")
    
    # Get all subdirectories
    folders = [d for d in v2_dir.iterdir() if d.is_dir() and d.name != 'plots']
    folders.sort()
    
    print("="*80)
    print("TEMPO PICKER V2 FULL REPROCESSING")
    print("="*80)
    print(f"\nFound {len(folders)} folders to process:")
    for f in folders:
        print(f"  - {f.name}")
    
    print(f"\n{'='*80}")
    print("RUNNING BATCH PROCESSOR ON PARENT DIRECTORY")
    print(f"{'='*80}\n")
    
    # Run batch processor on the parent V2 directory
    cmd = [
        sys.executable,
        "batch_processors/batch_process_universal.py",
        str(v2_dir)
    ]
    
    print(f"Command: {' '.join(cmd)}\n")
    
    result = subprocess.run(cmd, capture_output=False, text=True)
    
    if result.returncode == 0:
        print(f"\n{'='*80}")
        print("✓ BATCH PROCESSING COMPLETE")
        print(f"{'='*80}")
    else:
        print(f"\n{'='*80}")
        print(f"✗ ERROR: Batch processing failed with code {result.returncode}")
        print(f"{'='*80}")
        return False
    
    # Now regenerate master plots
    print(f"\n{'='*80}")
    print("REGENERATING MASTER PLOTS")
    print(f"{'='*80}\n")
    
    cmd2 = [
        sys.executable,
        "generate_tempopicker_v2_master_plots.py"
    ]
    
    result2 = subprocess.run(cmd2, capture_output=False, text=True)
    
    if result2.returncode == 0:
        print(f"\n{'='*80}")
        print("✓ MASTER PLOTS GENERATED")
        print(f"{'='*80}")
    else:
        print(f"\n{'='*80}")
        print(f"✗ ERROR: Master plot generation failed with code {result2.returncode}")
        print(f"{'='*80}")
        return False
    
    print(f"\n{'='*80}")
    print("✓✓✓ ALL PROCESSING COMPLETE ✓✓✓")
    print(f"{'='*80}")
    print("\nNew files generated:")
    print("  - Updated automated_work_of_adhesion.csv in each folder")
    print("  - New individual plots in plots/ subdirectories")
    print("  - MASTER_tempopicker_v2_combined.csv")
    print("  - MASTER_tempopicker_v2_mean_analysis.png")
    print("  - MASTER_tempopicker_v2_median_analysis.png")
    print("  - MASTER_tempopicker_v2_loglog_analysis.png")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
