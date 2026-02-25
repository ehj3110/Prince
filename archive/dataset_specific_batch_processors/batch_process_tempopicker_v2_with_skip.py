"""
Batch Process TEMPO Picker V2 with Hydrodynamic Locking Mitigation
====================================================================

Reprocess all TEMPO Picker V2 folders with distance-based peak filtering
to skip the initial 200um where hydrodynamic locking occurs.

Usage:
    python batch_process_tempopicker_v2_with_skip.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import sys
from datetime import datetime

# Add support modules to path
sys.path.insert(0, str(Path(__file__).parent / 'support_modules'))
sys.path.insert(0, str(Path(__file__).parent / 'post-processing'))
from adhesion_metrics_calculator import AdhesionMetricsCalculator
from RawData_Processor import RawDataProcessor
from analysis_plotter import AnalysisPlotter


def process_folder(folder_path, skip_distance_um=200):
    """
    Process a single TEMPO Picker V2 folder
    
    Args:
        folder_path: Path to folder containing autolog files
        skip_distance_um: Distance to skip at start for peak detection (default 200um)
    """
    folder_path = Path(folder_path)
    folder_name = folder_path.name
    
    print(f"\n{'='*80}")
    print(f"Processing: {folder_name}")
    print(f"{'='*80}")
    print(f"Skip distance: {skip_distance_um} um (hydrodynamic locking mitigation)")
    
    # Find all autolog CSV files
    autolog_files = sorted(folder_path.glob("autolog_*.csv"))
    
    if not autolog_files:
        print(f"  [X] No autolog files found in {folder_path}")
        return None
    
    print(f"Found {len(autolog_files)} autolog files\n")
    
    # Initialize components with distance-based skip
    calculator = AdhesionMetricsCalculator(
        skip_initial_distance_um=skip_distance_um
    )
    processor = RawDataProcessor(calculator)
    
    # Create plots directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    plots_dir = folder_path / f"plots_{timestamp}"
    plots_dir.mkdir(exist_ok=True)
    
    # Process each autolog file
    all_results = []
    
    for i, autolog_file in enumerate(autolog_files, 1):
        print(f"  [{i}/{len(autolog_files)}] Processing: {autolog_file.name}")
        
        try:
            # Process the file - this returns layers with metrics already calculated
            layers_data = processor.process_csv(str(autolog_file))
            
            if not layers_data:
                print(f"    WARNING: No layers detected")
                continue
            
            print(f"    Detected {len(layers_data)} layers")
            
            # Extract results from each layer
            for layer_idx, layer_obj in enumerate(layers_data, 1):
                try:
                    # Get metrics from layer object
                    metrics = layer_obj.get('metrics', {})
                    
                    # Get layer number from file or use sequence
                    # Extract from filename like autolog_L107-L111.csv
                    import re
                    match = re.search(r'L(\d+)-L(\d+)', autolog_file.name)
                    if match:
                        start_layer = int(match.group(1))
                        layer_number = start_layer + layer_idx - 1
                    else:
                        layer_number = layer_obj.get('number', layer_idx)
                    
                    # Create flat record for CSV
                    if metrics:
                        metrics['layer_number'] = layer_number
                        metrics['source_file'] = autolog_file.name
                        all_results.append(metrics)
                        
                except Exception as e:
                    print(f"      Error extracting layer {layer_idx}: {str(e)}")
                    continue
            
            # Generate plot for this autolog file (if layers were found)
            if layers_data:
                try:
                    # Read the data again for plotting
                    df = pd.read_csv(autolog_file)
                    plotter = AnalysisPlotter(df, layers_data)
                    plot_path = plots_dir / f"{autolog_file.stem}_analysis.png"
                    plotter.plot_analysis(str(plot_path))
                    print(f"    [OK] Saved plot: {plot_path.name}")
                except Exception as e:
                    print(f"    Warning: Could not generate plot: {str(e)}")
                
        except Exception as e:
            print(f"    [X] Error processing file: {str(e)}")
            continue
    
    # Save results to CSV
    if all_results:
        df_results = pd.DataFrame(all_results)
        
        # Try to load existing CSV to get area information
        existing_csv = folder_path / "automated_work_of_adhesion_backup_jan18.csv"
        if existing_csv.exists():
            print(f"\n  Loading area information from backup CSV...")
            existing_df = pd.read_csv(existing_csv)
            
            # Merge area information based on layer number
            if 'Cross_Sectional_Area_mm2' in existing_df.columns:
                area_map = dict(zip(
                    existing_df['Layer_Number'],
                    existing_df['Cross_Sectional_Area_mm2']
                ))
                df_results['cross_sectional_area_mm2'] = df_results['layer_number'].map(area_map)
                print(f"  [OK] Mapped area information for {len(df_results)} layers")
        
        # Save to CSV
        output_csv = folder_path / "automated_work_of_adhesion.csv"
        
        # Standardize column names to match expected format
        column_mapping = {
            'layer_number': 'Layer_Number',
            'peak_force': 'Peak_Force_N',
            'work_of_adhesion': 'Work_of_Adhesion_mJ',
            'total_peel_distance': 'Total_Peel_Distance_mm',
            'peak_retraction_force_N': 'Peak_Retraction_Force_N',
            'cross_sectional_area_mm2': 'Cross_Sectional_Area_mm2',
            'pre_initiation_distance': 'Distance_to_Peak_mm',
            'propagation_distance': 'Distance_to_Propagate_mm',
            'initiation_time': 'Initiation_Time_s',
            'propagation_duration': 'Propagation_Duration_s',
            'total_duration': 'Total_Duration_s'
        }
        
        df_results = df_results.rename(columns=column_mapping)
        df_results.to_csv(output_csv, index=False)
        
        print(f"\n  [OK] Saved {len(df_results)} layer measurements to {output_csv.name}")
        
        # Print summary statistics
        print(f"\n  Summary Statistics:")
        print(f"    Total Peel Distance:")
        print(f"      Min:  {df_results['Total_Peel_Distance_mm'].min():.3f} mm")
        print(f"      Max:  {df_results['Total_Peel_Distance_mm'].max():.3f} mm")
        print(f"      Mean: {df_results['Total_Peel_Distance_mm'].mean():.3f} mm")
        
        return df_results
    else:
        print(f"\n  [X] No valid results collected")
        return None


def main():
    """Process all TEMPO Picker V2 folders"""
    
    v2_dir = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\TEMPO Picker\V2")
    
    folders = [
        "10umTEMPO_400umGap",
        "5umTEMPO_200um",
        "5umTEMPO_200umGap",
        "5umTEMPO_400umGap_Good",
        "FlatTEMPO_400umGap",
        "TEMPO_400umGap"
    ]
    
    print("="*80)
    print("TEMPO PICKER V2 BATCH PROCESSOR")
    print("With Hydrodynamic Locking Mitigation (200um skip)")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    success_count = 0
    failed_folders = []
    
    for folder_name in folders:
        folder_path = v2_dir / folder_name
        
        if not folder_path.exists():
            print(f"\n[X] Folder not found: {folder_name}")
            failed_folders.append(folder_name)
            continue
        
        try:
            result = process_folder(folder_path, skip_distance_um=200)
            if result is not None:
                success_count += 1
            else:
                failed_folders.append(folder_name)
        except Exception as e:
            print(f"\n[X] Error processing {folder_name}: {str(e)}")
            failed_folders.append(folder_name)
    
    # Summary
    print("\n" + "="*80)
    print(f"Processing Complete: {success_count}/{len(folders)} folders successful")
    print("="*80)
    
    if failed_folders:
        print("\nFailed folders:")
        for folder in failed_folders:
            print(f"  - {folder}")
    else:
        print("\n[OK] All folders processed successfully!")
        print("\nNext: Run generate_tempopicker_v2_master_plots.py to create master plots")
    
    print(f"\nFinished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)


if __name__ == "__main__":
    main()
