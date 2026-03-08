"""
Simple Batch Processor Wrapper
==============================

Universal processor for ANY version of test data.
Just point it at a folder (V4, V5, V6, V7, ...) and it processes everything.

Usage:
    python process_folder.py V6
    python process_folder.py V5
    python process_folder.py "path/to/any/folder"

Author: Cheng Sun Lab Team
Date: December 2, 2025
"""

import sys
from pathlib import Path

# Add batch_processors to path
sys.path.insert(0, str(Path(__file__).parent / 'batch_processors'))
from batch_process_universal import UniversalBatchProcessor

# Base path for test data
BASE_PATH = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests")


def main():
    if len(sys.argv) < 2:
        print("="*80)
        print("SIMPLE BATCH PROCESSOR")
        print("="*80)
        print("\nUsage:")
        print("  python process_folder.py <folder_name>")
        print("\nExamples:")
        print("  python process_folder.py V6")
        print("  python process_folder.py V5")
        print("  python process_folder.py \"C:\\path\\to\\folder\"")
        print("\nThis will:")
        print("  1. Process all autolog files in the folder")
        print("  2. Generate individual analysis plots")
        print("  3. Create master CSV with all metrics")
        print("  4. Generate master comparison plots")
        return
    
    # Get folder path
    folder_arg = sys.argv[1]
    
    # Check if it's a full path or just a folder name
    if Path(folder_arg).exists():
        folder_path = Path(folder_arg)
    else:
        # Try appending to base path
        folder_path = BASE_PATH / folder_arg
    
    if not folder_path.exists():
        print(f"ERROR: Folder not found: {folder_path}")
        print(f"\nSearched for:")
        print(f"  1. {folder_arg}")
        print(f"  2. {BASE_PATH / folder_arg}")
        return
    
    print("="*80)
    print("PROCESSING FOLDER")
    print("="*80)
    print(f"Target: {folder_path}")
    print()
    
    # Create processor and run
    processor = UniversalBatchProcessor(str(folder_path))
    processor.process_all_folders()
    processor.save_combined_csv()
    processor.generate_master_plots()
    
    print("\n" + "="*80)
    print("PROCESSING COMPLETE!")
    print("="*80)
    print(f"\nAll outputs saved to: {folder_path}")


if __name__ == '__main__':
    main()
