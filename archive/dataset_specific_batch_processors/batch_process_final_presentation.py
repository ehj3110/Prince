"""
Batch Process Final Presentation Data
======================================

Reprocess the "Final" folder with corrected peel distance calculations (now positive).
This folder contains renamed versions of the presentation data.

Usage:
    python batch_process_final_presentation.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Add support modules to path
sys.path.insert(0, str(Path(__file__).parent / 'support_modules'))
sys.path.insert(0, str(Path(__file__).parent / 'post-processing'))
from adhesion_metrics_calculator import AdhesionMetricsCalculator
from RawData_Processor import RawDataProcessor


def process_folder_with_analysis(folder_path, skip_distance_um=200):
    """
    Process all autolog files in a folder with hydrodynamic locking mitigation
    
    Args:
        folder_path: Path object to folder containing autolog CSV files
        skip_distance_um: Distance in micrometers to skip for hydrodynamic mitigation
    """
    print(f"\n  Processing: {folder_path.name}")
    
    # Initialize calculator with hydrodynamic skip
    calculator = AdhesionMetricsCalculator(skip_initial_distance_um=skip_distance_um)
    processor = RawDataProcessor(calculator)
    
    # Find all autolog files
    autolog_files = sorted(folder_path.glob("autolog_*.csv"))
    
    if not autolog_files:
        print(f"    [X] No autolog files found")
        return None
    
    print(f"    Found {len(autolog_files)} autolog files")
    
    # Process each file
    all_results = []
    
    for autolog_file in autolog_files:
        try:
            # Extract layer range from filename (e.g., autolog_L46-L50.csv -> 46, 50)
            import re
            match = re.search(r'L(\d+)(?:-L(\d+))?', autolog_file.stem)
            if match:
                start_layer = int(match.group(1))
                end_layer = int(match.group(2)) if match.group(2) else start_layer
            else:
                start_layer = 0
                end_layer = 0
            
            # Process the CSV file
            layers_data = processor.process_csv(str(autolog_file))
            
            # Extract metrics from each layer
            for i, layer_obj in enumerate(layers_data):
                metrics = layer_obj.get('metrics', {})
                
                # Use actual layer number from filename range
                actual_layer_num = start_layer + i
                
                # Add metadata
                metrics['layer_number'] = actual_layer_num
                metrics['source_file'] = autolog_file.name
                metrics['condition'] = folder_path.name
                
                all_results.append(metrics)
                
        except Exception as e:
            print(f"    [!] Error processing {autolog_file.name}: {e}")
            continue
    
    if not all_results:
        print(f"    [X] No valid results")
        return None
    
    # Convert to DataFrame
    df_results = pd.DataFrame(all_results)
    
    # Standardize column names - USE BASELINE-CORRECTED VALUES
    column_mapping = {
        'peak_force_corrected': 'Peak_Force_N',  # Use baseline-corrected force
        'work_of_adhesion_corrected_mJ': 'Work_of_Adhesion_mJ',
        'total_peel_distance': 'Total_Peel_Distance_mm',  # Already absolute value
        'peak_retraction_force_N': 'Peak_Retraction_Force_N',
        'layer_number': 'Layer_Number',
        'source_file': 'Source_File',
        'condition': 'Condition'
    }
    
    # Rename columns that exist
    rename_dict = {old: new for old, new in column_mapping.items() if old in df_results.columns}
    df_results = df_results.rename(columns=rename_dict)
    
    # READ area mapping from existing automated_work_of_adhesion.csv (READ-ONLY - NEVER WRITE TO THIS FILE)
    area_csv = folder_path / "automated_work_of_adhesion.csv"
    
    if area_csv.exists():
        try:
            existing_df = pd.read_csv(area_csv)
            if 'Cross_Sectional_Area_mm2' in existing_df.columns:
                # Create mapping from layer number to area
                area_map = dict(zip(
                    existing_df['Layer_Number'],
                    existing_df['Cross_Sectional_Area_mm2']
                ))
                
                # Map to new dataframe
                if 'Layer_Number' in df_results.columns:
                    df_results['Cross_Sectional_Area_mm2'] = df_results['Layer_Number'].map(area_map)
                    print(f"    [OK] Mapped cross-sectional area from existing file")
        except Exception as e:
            print(f"    [!] Could not load area data: {e}")
    
    print(f"    [OK] Processed {len(df_results)} layer measurements")
    
    # Print summary statistics
    if 'Peak_Force_N' in df_results.columns:
        print(f"    Peak Force: {df_results['Peak_Force_N'].mean():.4f} ± {df_results['Peak_Force_N'].std():.4f} N")
    if 'Total_Peel_Distance_mm' in df_results.columns:
        print(f"    Total Peel Distance: {df_results['Total_Peel_Distance_mm'].mean():.3f} ± {df_results['Total_Peel_Distance_mm'].std():.3f} mm")
    
    return df_results


def main():
    """Process all folders in the Final directory"""
    
    final_dir = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\Presentation data\Final")
    
    print("="*80)
    print("REPROCESSING FINAL PRESENTATION DATA")
    print("="*80)
    print(f"\nProcessing folder: {final_dir}")
    print("Hydrodynamic mitigation: 200 micrometers skip")
    print("Peel distance: Now using ABSOLUTE VALUES (always positive)")
    
    # Find all subdirectories
    subdirs = [d for d in final_dir.iterdir() if d.is_dir()]
    subdirs = sorted(subdirs, key=lambda x: x.name)
    
    print(f"\nFound {len(subdirs)} folders to process:")
    for subdir in subdirs:
        print(f"  - {subdir.name}")
    
    print("\n" + "="*80)
    print("PROCESSING")
    print("="*80)
    
    # Process each folder and collect all results
    all_results = []
    for subdir in subdirs:
        df_results = process_folder_with_analysis(subdir, skip_distance_um=200)
        if df_results is not None and len(df_results) > 0:
            all_results.append(df_results)
    
    print("\n" + "="*80)
    print("SAVING MASTER CSV")
    print("="*80)
    
    if all_results:
        # Combine all results
        master_df = pd.concat(all_results, ignore_index=True)
        
        # Save to MASTER file (NOT to automated_work_of_adhesion.csv!)
        master_csv = final_dir / "MASTER_all_metrics.csv"
        master_df.to_csv(master_csv, index=False)
        print(f"\n[OK] Saved MASTER CSV: {master_csv}")
        print(f"    Total rows: {len(master_df)}")
        print(f"    Conditions: {master_df['Condition'].unique().tolist()}")
    else:
        print("\n[X] No results to save!")
    
    print("\n" + "="*80)
    print("PROCESSING COMPLETE")
    print("="*80)
    print(f"\nSuccessfully processed: {len(all_results)}/{len(subdirs)} folders")


if __name__ == "__main__":
    main()
