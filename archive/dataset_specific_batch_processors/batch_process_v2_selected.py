#!/usr/bin/env python3
"""
Batch processor for selected V2 adhesion test data (2p5PEO and Water_1000).
Generates master plots similar to the TEMPO Picker analysis format.

Author: Cheng Sun Lab Team  
Date: January 20, 2026
"""

import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np

# Add support_modules to path
parent_dir = Path(__file__).parent
sys.path.insert(0, str(parent_dir))
sys.path.insert(0, str(parent_dir / "support_modules"))
sys.path.insert(0, str(parent_dir / "post-processing"))

from adhesion_metrics_calculator import AdhesionMetricsCalculator
from RawData_Processor import RawDataProcessor


def find_autolog_files(folder_path):
    """Find all autolog CSV files in the given folder, excluding metrics files."""
    pattern = "autolog*.csv"
    files = list(Path(folder_path).glob(pattern))
    # Filter out metrics files
    files = [f for f in files if 'metrics' not in f.name.lower()]
    files.sort()
    return files


def process_folder(folder_path, calculator):
    """Process all autolog files in a folder."""
    folder_path = Path(folder_path)
    print(f"\n{'='*80}")
    print(f"Processing folder: {folder_path.name}")
    print(f"{'='*80}")
    
    # Find all autolog files
    autolog_files = find_autolog_files(folder_path)
    
    if not autolog_files:
        print(f"No autolog files found in {folder_path}")
        return []
    
    print(f"Found {len(autolog_files)} autolog file(s)")
    
    # Initialize processor for this folder
    processor = RawDataProcessor(calculator)
    
    all_layers = []
    
    # Process each autolog file
    for csv_file in autolog_files:
        print(f"\nProcessing: {csv_file.name}")
        
        try:
            # Process the CSV file (data processing only, no plotting)
            layers = processor.process_csv(
                csv_filepath=str(csv_file)
            )
            
            if layers:
                print(f"  ✓ Successfully processed {len(layers)} layer(s)")
                
                # Add folder name to each layer's metrics
                for layer in layers:
                    layer['metrics']['folder'] = folder_path.name
                
                all_layers.extend(layers)
                
            else:
                print(f"  ✗ No layers detected in {csv_file.name}")
                
        except Exception as e:
            print(f"  ✗ Error processing {csv_file.name}: {e}")
    
    # Export folder-level metrics
    if all_layers:
        metrics_list = [layer['metrics'] for layer in all_layers]
        folder_metrics_df = pd.DataFrame(metrics_list)
        
        folder_csv_path = folder_path / "autolog_metrics.csv"
        folder_metrics_df.to_csv(folder_csv_path, index=False)
        print(f"\n✓ Exported {len(folder_metrics_df)} metrics to {folder_csv_path.name}")
    
    return all_layers


def generate_summary_statistics(all_metrics_df, output_path):
    """Generate summary statistics by folder."""
    print("\n" + "="*80)
    print("GENERATING SUMMARY STATISTICS")
    print("="*80)
    
    summary_stats = []
    
    for folder in all_metrics_df['folder'].unique():
        folder_data = all_metrics_df[all_metrics_df['folder'] == folder]
        
        stats = {
            'folder': folder,
            'num_layers': len(folder_data),
            'peak_force_mean': folder_data['peak_force'].mean(),
            'peak_force_std': folder_data['peak_force'].std(),
            'peak_force_median': folder_data['peak_force'].median(),
            'work_mean': folder_data['work_of_adhesion_corrected_mJ'].mean(),
            'work_std': folder_data['work_of_adhesion_corrected_mJ'].std(),
            'work_median': folder_data['work_of_adhesion_corrected_mJ'].median(),
            'pre_init_duration_mean': folder_data['pre_initiation_duration'].mean(),
            'pre_init_duration_std': folder_data['pre_initiation_duration'].std(),
            'prop_duration_mean': folder_data['propagation_duration'].mean(),
            'prop_duration_std': folder_data['propagation_duration'].std(),
        }
        summary_stats.append(stats)
    
    summary_df = pd.DataFrame(summary_stats)
    summary_df.to_csv(output_path, index=False)
    print(f"✓ Summary statistics saved to {output_path}")
    
    # Print summary table
    print("\n" + "="*80)
    print("SUMMARY BY FOLDER")
    print("="*80)
    print(f"{'Folder':<50} {'Layers':<8} {'Peak Force (N)':<20} {'Work (mJ)':<20}")
    print(f"{'':50} {'':8} {'Mean ± Std':<20} {'Mean ± Std':<20}")
    print("-"*80)
    for _, row in summary_df.iterrows():
        print(f"{row['folder']:<50} {row['num_layers']:<8} "
              f"{row['peak_force_mean']:.4f} ± {row['peak_force_std']:.4f}     "
              f"{row['work_mean']:.3f} ± {row['work_std']:.3f}")
    print("="*80)
    
    return summary_df


def main():
    """Main batch processing function for selected V2 datasets."""
    # Define the master folder path
    master_folder = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V2")
    
    if not master_folder.exists():
        print(f"Error: Master folder not found: {master_folder}")
        return
    
    # Define which folders to process
    target_folders = [
        "2p5PEO_1mm_SteppedCone_BPAGDA_1000",
        "Water_1mm_SteppedCone_BPAGDA_1000"
    ]
    
    print("="*80)
    print("BATCH PROCESSING SELECTED V2 ADHESION TEST DATA")
    print("="*80)
    print(f"Master folder: {master_folder}")
    print(f"Target datasets:")
    for folder in target_folders:
        print(f"  - {folder}")
    print()
    
    # Initialize calculator
    print("Initializing analysis components...")
    calculator = AdhesionMetricsCalculator()
    print("✓ Components initialized\n")
    
    # Process each target folder
    all_layers = []
    
    for folder_name in target_folders:
        folder_path = master_folder / folder_name
        
        if not folder_path.exists():
            print(f"✗ Folder not found: {folder_path}")
            continue
        
        folder_layers = process_folder(folder_path, calculator)
        all_layers.extend(folder_layers)
    
    # Generate master CSV with all metrics
    if all_layers:
        print("\n" + "="*80)
        print("EXPORTING MASTER METRICS")
        print("="*80)
        
        # Convert all layer metrics to DataFrame
        metrics_list = [layer['metrics'] for layer in all_layers]
        all_metrics_df = pd.DataFrame(metrics_list)
        
        # Save to master CSV
        master_csv_path = master_folder / "MASTER_v2_selected_metrics.csv"
        all_metrics_df.to_csv(master_csv_path, index=False)
        print(f"✓ Exported {len(all_metrics_df)} total layer metrics to {master_csv_path.name}")
        
        # Generate summary statistics
        summary_path = master_folder / "MASTER_v2_selected_summary.csv"
        generate_summary_statistics(all_metrics_df, summary_path)
        
        # Print overall summary
        print("\n" + "="*80)
        print("BATCH PROCESSING COMPLETE")
        print("="*80)
        print(f"Total folders processed: {len(target_folders)}")
        print(f"Total layers analyzed: {len(all_layers)}")
        print()
        print("Outputs generated:")
        print("  - autolog_metrics.csv in each folder")
        print(f"  - {master_csv_path.name} (combined metrics)")
        print(f"  - {summary_path.name} (summary statistics)")
        print()
        print("✓ Ready to generate master plots!")
        print("="*80)
    else:
        print("\n✗ No layers were successfully processed")


if __name__ == "__main__":
    main()
