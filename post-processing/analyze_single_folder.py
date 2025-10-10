#!/usr/bin/env python3
"""
Analyze a single test folder and generate both individual layer plots and speed analysis.

Usage:
    python analyze_single_folder.py <folder_path>
    
Example:
    python analyze_single_folder.py "C:\Path\to\Water_1mm_Constant_BPAGDA"
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir / "support_modules"))
sys.path.insert(0, str(Path(__file__).parent))

from batch_v17_analysis import V17TestBatchProcessor


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_single_folder.py <folder_path>")
        print("\nExample:")
        print('  python analyze_single_folder.py "C:\\Path\\to\\Water_1mm_Constant_BPAGDA"')
        return 1
    
    folder_path = Path(sys.argv[1])
    
    if not folder_path.exists():
        print(f"Error: Folder does not exist: {folder_path}")
        return 1
    
    if not folder_path.is_dir():
        print(f"Error: Path is not a directory: {folder_path}")
        return 1
    
    print("="*80)
    print("SINGLE FOLDER ANALYSIS")
    print("="*80)
    print(f"Target folder: {folder_path}\n")
    
    try:
        # Create processor with the parent folder as master
        processor = V17TestBatchProcessor(folder_path.parent)
        
        # Process just this folder
        processor.process_single_folder(folder_path)
        
        print("\n" + "="*80)
        print("ANALYSIS COMPLETE")
        print("="*80)
        print(f"\nGenerated outputs in: {folder_path}")
        print("  - Individual layer plots: *.png")
        print("  - Combined metrics: autolog_metrics.csv")
        print("  - Speed analysis: speed_analysis.png")
        
    except Exception as e:
        print(f"\nError during analysis: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
