#!/usr/bin/env python3
"""
Batch processor for V2 adhesion test data (TEMPO, TEMPOV2, etc.)
Uses the existing RawData_Processor + AnalysisPlotter system to process all layers.

Author: Cheng Sun Lab Team
Date: October 20, 2025
"""

import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np

# Add parent directory to path to import modules
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))
sys.path.insert(0, str(parent_dir / "support_modules"))

# Add current directory first to ensure we use the local modules
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

try:
    from adhesion_metrics_calculator import AdhesionMetricsCalculator
    from analysis_plotter import AnalysisPlotter
    from RawData_Processor import RawDataProcessor
    
    def find_autolog_files(folder_path):
        """Find all autolog CSV files in the given folder."""
        pattern = "autolog*.csv"
        files = list(Path(folder_path).glob(pattern))
        # Sort by filename
        files.sort()
        return files
    
    def process_folder(folder_path, calculator, plotter):
        """Process all autolog files in a folder and generate plots."""
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
            
            # Set output path for plot
            output_plot = folder_path / f"{csv_file.stem}_analysis.png"
            
            try:
                # Step 1: Process the CSV file (data processing only)
                layers = processor.process_csv(
                    csv_filepath=str(csv_file)
                )
                
                if layers:
                    print(f"  ✓ Successfully processed {len(layers)} layer(s)")
                    
                    # Step 2: Load the data for plotting
                    df = pd.read_csv(csv_file)
                    time_data = df['Elapsed Time (s)'].to_numpy()
                    force_data = df['Force (N)'].to_numpy()
                    
                    # Apply smoothing filter to get smoothed force (use private method like RawDataProcessor does)
                    smoothed_force = calculator._apply_smoothing(force_data)
                    
                    # Step 3: Create the plot using the plotter
                    plotter.create_plot(
                        time_data=time_data,
                        force_data=force_data,
                        smoothed_force=smoothed_force,
                        layers=layers,
                        title=f"{folder_path.name} - {csv_file.stem}",
                        save_path=str(output_plot)
                    )
                    
                    # Add folder name and file name to each layer's metrics
                    for layer in layers:
                        layer['metrics']['folder'] = folder_path.name
                        layer['metrics']['file'] = csv_file.name
                    all_layers.extend(layers)
                else:
                    print(f"  ✗ No layers detected in {csv_file.name}")
                    
            except Exception as e:
                print(f"  ✗ Error processing {csv_file.name}: {e}")
                import traceback
                traceback.print_exc()
        
        # Export combined metrics to CSV for this folder
        if all_layers:
            csv_output = folder_path / "autolog_metrics.csv"
            # Extract metrics from layers and save to CSV
            metrics_list = [layer['metrics'] for layer in all_layers]
            metrics_df = pd.DataFrame(metrics_list)
            metrics_df.to_csv(csv_output, index=False)
            print(f"\n✓ Exported {len(all_layers)} layer metrics to {csv_output.name}")
        
        return all_layers
    
    def generate_summary_statistics(all_metrics_df, output_path):
        """Generate summary statistics for all data."""
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
        print(f"{'Folder':<20} {'Layers':<8} {'Peak Force (N)':<20} {'Work (mJ)':<20}")
        print(f"{'':20} {'':8} {'Mean ± Std':<20} {'Mean ± Std':<20}")
        print("-"*80)
        for _, row in summary_df.iterrows():
            print(f"{row['folder']:<20} {row['num_layers']:<8} "
                  f"{row['peak_force_mean']:.4f} ± {row['peak_force_std']:.4f}     "
                  f"{row['work_mean']:.3f} ± {row['work_std']:.3f}")
        print("="*80)
        
        return summary_df
    
    def main():
        """Main batch processing function."""
        # Define the master folder path
        master_folder = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V2")
        
        if not master_folder.exists():
            print(f"Error: Master folder not found: {master_folder}")
            return
        
        print("="*80)
        print("BATCH PROCESSING V2 ADHESION TEST DATA")
        print("="*80)
        print(f"Master folder: {master_folder}")
        print()
        
        # Initialize calculator and plotter
        print("Initializing analysis components...")
        calculator = AdhesionMetricsCalculator()  # Use default parameters
        plotter = AnalysisPlotter(figure_size=(16, 12), dpi=100)
        
        # Get all subfolders
        subfolders = [f for f in master_folder.iterdir() if f.is_dir()]
        subfolders.sort()
        
        if not subfolders:
            print(f"No subfolders found in {master_folder}")
            return
        
        print(f"Found {len(subfolders)} folder(s) to process:")
        for folder in subfolders:
            print(f"  - {folder.name}")
        
        # Process each folder
        all_layers = []
        
        for folder in subfolders:
            folder_layers = process_folder(folder, calculator, plotter)
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
            master_csv_path = master_folder / "MASTER_all_metrics.csv"
            all_metrics_df.to_csv(master_csv_path, index=False)
            print(f"✓ Exported {len(all_metrics_df)} total layer metrics to {master_csv_path}")
            
            # Generate summary statistics
            summary_path = master_folder / "MASTER_summary_statistics.csv"
            generate_summary_statistics(all_metrics_df, summary_path)
            
            # Print overall summary
            print("\n" + "="*80)
            print("BATCH PROCESSING COMPLETE")
            print("="*80)
            print(f"Total folders processed: {len(subfolders)}")
            print(f"Total layers analyzed: {len(all_layers)}")
            print(f"Total CSV files processed: {len(set([layer['metrics']['file'] for layer in all_layers]))}")
            print()
            print("Outputs generated:")
            print("  - Individual layer analysis plots in each folder")
            print("  - autolog_metrics.csv in each folder")
            print(f"  - {master_csv_path.name} (combined metrics)")
            print(f"  - {summary_path.name} (summary statistics)")
            print()
            print("Next step: Use existing plot_master_*.py scripts to generate master comparison plots")
            print("="*80)
        else:
            print("\n✗ No layers were successfully processed")
    
    if __name__ == "__main__":
        main()
        
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure all required modules are available:")
    print("  - support_modules/adhesion_metrics_calculator.py")
    print("  - analysis_plotter.py")
    print("  - RawData_Processor.py")
    import traceback
    traceback.print_exc()
