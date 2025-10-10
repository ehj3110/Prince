#!/usr/bin/env python3
"""
Test script for batch_v17_analysis.py
Tests the updated batch processor on a single folder first
"""

import sys
from pathlib import Path

# Import the batch processor
from batch_v17_analysis import V17TestBatchProcessor

def main():
    """
    Test the batch processor on a single folder.
    """
    # For testing, you can specify a single test folder path as the first argv
    # Or default to the full master folder
    master_folder = r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\V17Tests"
    single_folder_arg = None
    if len(sys.argv) > 1:
        single_folder_arg = sys.argv[1]
    
    print("="*80)
    print("TESTING BATCH V17 ANALYSIS (UPDATED VERSION)")
    print("="*80)
    print(f"Master folder: {master_folder}\n")
    
    # Check if folder exists
    if not Path(master_folder).exists():
        print(f"ERROR: Master folder does not exist: {master_folder}")
        print("\nPlease update the master_folder path in this test script.")
        return 1
    
    try:
        # Create processor
        processor = V17TestBatchProcessor(master_folder)

        # If a single folder argument was provided, process only that folder
        if single_folder_arg:
            test_folder = Path(single_folder_arg)
            if not test_folder.is_absolute():
                test_folder = Path(master_folder) / single_folder_arg

            if test_folder.exists() and test_folder.is_dir():
                print(f"\nRunning batch processor on single folder: {test_folder}")
                processor.process_single_folder(test_folder)
            else:
                print(f"Test folder not found or not a directory: {test_folder}")
                return 1
        else:
            # Default: process all folders
            processor.process_all_folders()
        
        print("\n[OK] Test completed successfully!")
        return 0
        
    except Exception as e:
        print(f"\n[ERROR] Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
