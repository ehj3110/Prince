"""
Batch Process TEMPO Picker V2 Data
===================================

Process all subdirectories in TEMPO Picker V2 folder and generate master plots.

Author: Cheng Sun Lab Team
Date: January 20, 2026
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
import os

# Add post-processing to path
sys.path.insert(0, str(Path(__file__).parent / "post-processing"))

# Import the analyzer
from analyze_single_folder import process_single_autolog

def process_folder(folder_path):
    """Process a single TEMPO Picker folder and collect metrics"""
    
    print(f"\n{'='*80}")
    print(f"Processing: {folder_path.name}")
    print(f"{'='*80}")
    
    # Find all autolog files
    autolog_files = sorted(folder_path.glob("autolog_*.csv"))
    
    if not autolog_files:
        print(f"  WARNING: No autolog files found in {folder_path.name}")
        return None
    
    print(f"  Found {len(autolog_files)} autolog files")
    
    all_layers = []
    
    for autolog_file in autolog_files:
        print(f"\n  Processing: {autolog_file.name}")
        
        try:
            # Process the file
            layer_data = process_single_autolog(
                autolog_file=autolog_file,
                area_file=None,  # TEMPO Picker has area in automated_work_of_adhesion.csv
                create_plots=False  # Skip plotting for now
            )
            
            if layer_data is not None and len(layer_data) > 0:
                print(f"    Detected {len(layer_data)} layers")
                
                # Add folder name to each layer
                layer_data['folder'] = folder_path.name
                layer_data['autolog_file'] = autolog_file.stem
                
                all_layers.append(layer_data)
            else:
                print(f"    No layers detected")
                
        except Exception as e:
            print(f"    ERROR: {e}")
            continue
    
    if all_layers:
        df = pd.DataFrame(all_layers)
        
        # Save metrics to folder
        output_file = folder_path / "autolog_metrics.csv"
        df.to_csv(output_file, index=False)
        print(f"\n  Saved {len(df)} layers to {output_file.name}")
        
        return df
    else:
        print(f"  No data collected from {folder_path.name}")
        return None


def main():
    """Main processing function"""
    
    # Path to TEMPO Picker V2 directory
    v2_dir = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\TEMPO Picker\V2")
    
    print("="*80)
    print("TEMPO PICKER V2 BATCH PROCESSOR")
    print("="*80)
    print(f"Master Directory: {v2_dir}\n")
    
    if not v2_dir.exists():
        print(f"ERROR: Directory not found: {v2_dir}")
        return
    
    # Find all subdirectories
    subdirs = [d for d in v2_dir.iterdir() if d.is_dir()]
    subdirs.sort()
    
    print(f"Found {len(subdirs)} subdirectories:")
    for d in subdirs:
        print(f"  - {d.name}")
    
    # Process each folder
    all_data = []
    
    for subdir in subdirs:
        df = process_folder(subdir)
        if df is not None:
            all_data.append(df)
    
    # Combine all data
    if all_data:
        print(f"\n{'='*80}")
        print("COMBINING DATA")
        print(f"{'='*80}")
        
        combined_df = pd.concat(all_data, ignore_index=True)
        
        # Save combined metrics
        output_file = v2_dir / "MASTER_tempopicker_v2_metrics.csv"
        combined_df.to_csv(output_file, index=False)
        print(f"\nSaved {len(combined_df)} total layers to {output_file.name}")
        
        # Print summary
        print(f"\n{'='*80}")
        print("SUMMARY")
        print(f"{'='*80}")
        for folder in combined_df['folder'].unique():
            count = len(combined_df[combined_df['folder'] == folder])
            print(f"  {folder}: {count} layers")
        
        print(f"\nTotal: {len(combined_df)} layers")
        
    else:
        print("\nERROR: No data collected from any folder!")


if __name__ == "__main__":
    main()
