"""
Batch Process Final Presentation Data WITH CROSS-SECTIONAL AREAS
=================================================================

This version extracts layer numbers from autolog filenames and assigns
cross-sectional areas based on the FEP reference mapping.

Usage:
    python batch_process_final_with_areas.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
import shutil
import re

# Add support modules to path
sys.path.insert(0, str(Path(__file__).parent / 'support_modules'))
sys.path.insert(0, str(Path(__file__).parent / 'post-processing'))
from adhesion_metrics_calculator import AdhesionMetricsCalculator
from RawData_Processor import RawDataProcessor


# Reference layer-to-area mapping extracted from FEP data
# These represent the cross-sectional area at different layer heights
LAYER_TO_AREA_MAP = {
    50: 7.50,
    75: 12.08,
    100: 14.78,
    125: 17.84,
    150: 21.83,
    175: 26.33,
    200: 32.25,
    225: 38.90,
    250: 47.64,
    275: 57.46,
    300: 70.38,
    325: 84.89
}


def extract_layer_from_filename(filename):
    """
    Extract the starting layer number from autolog filename.
    
    Example: "autolog_L101-L105.csv" -> 101
    
    Args:
        filename: Name of the autolog file
        
    Returns:
        Layer number (int) or None if not found
    """
    match = re.search(r'L(\d+)', filename)
    if match:
        return int(match.group(1))
    return None


def assign_area_from_layer(layer_num):
    """
    Assign cross-sectional area based on layer number.
    
    Uses the nearest mapped layer value (rounded to nearest 25).
    
    Args:
        layer_num: Layer number extracted from filename
        
    Returns:
        Cross-sectional area in mm² or NaN if layer is None
    """
    if layer_num is None or pd.isna(layer_num):
        return np.nan
    
    # Round to nearest 25 to match our mapping
    layer_range = round(layer_num / 25) * 25
    
    # Clamp to available range
    layer_range = max(50, min(325, layer_range))
    
    return LAYER_TO_AREA_MAP.get(layer_range, np.nan)


def process_folder_with_analysis(folder_path, skip_distance_um=200):
    """
    Process all autolog files in a folder with hydrodynamic locking mitigation
    AND assign cross-sectional areas based on layer numbers.
    
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
        return False
    
    print(f"    Found {len(autolog_files)} autolog files")
    
    # Process each file
    all_results = []
    
    for autolog_file in autolog_files:
        try:
            # Extract layer number from filename
            layer_from_filename = extract_layer_from_filename(autolog_file.name)
            
            # Process the CSV file
            layers_data = processor.process_csv(str(autolog_file))
            
            # Extract metrics from each layer
            for layer_obj in layers_data:
                layer_num = layer_obj.get('layer_number', 0)
                metrics = layer_obj.get('metrics', {})
                
                # Use filename layer if processor returns 0
                effective_layer = layer_num if layer_num != 0 else layer_from_filename
                
                # Add metadata
                metrics['layer_number'] = effective_layer
                metrics['source_file'] = autolog_file.name
                metrics['condition'] = folder_path.name
                
                # Assign cross-sectional area based on layer
                metrics['cross_sectional_area_mm2'] = assign_area_from_layer(effective_layer)
                
                all_results.append(metrics)
                
        except Exception as e:
            print(f"    [!] Error processing {autolog_file.name}: {e}")
            continue
    
    if not all_results:
        print(f"    [X] No valid results")
        return False
    
    # Convert to DataFrame
    df_results = pd.DataFrame(all_results)
    
    # Standardize column names
    column_mapping = {
        'peak_force': 'Peak_Force_N',
        'work_of_adhesion_corrected_mJ': 'Work_of_Adhesion_mJ',
        'total_peel_distance': 'Total_Peel_Distance_mm',
        'peak_retraction_force_N': 'Peak_Retraction_Force_N',
        'layer_number': 'Layer_Number',
        'source_file': 'Source_File',
        'condition': 'Condition',
        'cross_sectional_area_mm2': 'Cross_Sectional_Area_mm2'
    }
    
    # Rename columns that exist
    rename_dict = {old: new for old, new in column_mapping.items() if old in df_results.columns}
    df_results = df_results.rename(columns=rename_dict)
    
    # Check if existing CSV exists for backup
    output_csv = folder_path / "automated_work_of_adhesion.csv"
    
    if output_csv.exists():
        # Backup existing file
        backup_csv = folder_path / "automated_work_of_adhesion_backup.csv"
        shutil.copy2(output_csv, backup_csv)
        print(f"    [OK] Backed up existing CSV")
    
    # Save results
    df_results.to_csv(output_csv, index=False, encoding='utf-8')
    print(f"    [OK] Saved {len(df_results)} layer measurements")
    
    # Print summary statistics
    if 'Peak_Force_N' in df_results.columns:
        print(f"    Peak Force: {df_results['Peak_Force_N'].mean():.4f} ± {df_results['Peak_Force_N'].std():.4f} N")
    if 'Total_Peel_Distance_mm' in df_results.columns:
        print(f"    Total Peel Distance: {df_results['Total_Peel_Distance_mm'].mean():.3f} ± {df_results['Total_Peel_Distance_mm'].std():.3f} mm")
    if 'Cross_Sectional_Area_mm2' in df_results.columns:
        valid_areas = df_results['Cross_Sectional_Area_mm2'].dropna()
        if len(valid_areas) > 0:
            print(f"    Cross-Sectional Area: {valid_areas.min():.2f} - {valid_areas.max():.2f} mm² ({len(valid_areas)}/{len(df_results)} valid)")
    
    return True


def main():
    """Process all folders in the Final directory"""
    
    final_dir = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\Presentation data\Final")
    
    print("="*80)
    print("REPROCESSING FINAL PRESENTATION DATA WITH CROSS-SECTIONAL AREAS")
    print("="*80)
    print(f"\nProcessing folder: {final_dir}")
    print("Hydrodynamic mitigation: 200 micrometers skip")
    print("Peel distance: Using ABSOLUTE VALUES (always positive)")
    print("Cross-sectional area: Assigned from layer-to-area mapping")
    
    # Show the layer-to-area mapping
    print("\nLayer-to-Area Reference Map:")
    for layer, area in sorted(LAYER_TO_AREA_MAP.items()):
        print(f"  Layer ~{layer}: {area:.2f} mm²")
    
    # Find all subdirectories
    subdirs = [d for d in final_dir.iterdir() if d.is_dir()]
    subdirs = sorted(subdirs, key=lambda x: x.name)
    
    print(f"\nFound {len(subdirs)} folders to process:")
    for subdir in subdirs:
        print(f"  - {subdir.name}")
    
    print("\n" + "="*80)
    print("PROCESSING")
    print("="*80)
    
    # Process each folder
    success_count = 0
    for subdir in subdirs:
        success = process_folder_with_analysis(subdir, skip_distance_um=200)
        if success:
            success_count += 1
    
    print("\n" + "="*80)
    print("PROCESSING COMPLETE")
    print("="*80)
    print(f"\nSuccessfully processed: {success_count}/{len(subdirs)} folders")
    
    if success_count == len(subdirs):
        print("\n[OK] All folders processed successfully!")
        print("\n[NEXT STEP] Run: python generate_final_progressive_plots.py")
    else:
        print(f"\n[!] {len(subdirs) - success_count} folders had issues")


if __name__ == "__main__":
    main()
