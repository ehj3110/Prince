"""
Generalized Batch Processor for SteppedCone Adhesion Data
=========================================================

Universal batch processor that works with any SteppedCone test folder (V2, V3, V4, etc.)
by accepting the data directory as a command-line argument.

Usage:
    python batch_process_steppedcone_generalized.py --folder V3
    python batch_process_steppedcone_generalized.py --folder V4
    python batch_process_steppedcone_generalized.py --folder "C:/path/to/custom/folder"
    
    # With optional flags:
    python batch_process_steppedcone_generalized.py --folder V3 --skip-plots  # Skip individual plots
    python batch_process_steppedcone_generalized.py --folder V3 --csv-only    # Only generate CSV

Author: Cheng Sun Lab Team
Date: October 28, 2025
"""

import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend to avoid Windows crashes
import matplotlib.pyplot as plt
import sys
import argparse

# Add support_modules and post-processing to path (go up to parent directory)
sys.path.insert(0, str(Path(__file__).parent.parent / 'support_modules'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'post-processing'))
from adhesion_metrics_calculator import AdhesionMetricsCalculator
from RawData_Processor import RawDataProcessor
from analysis_plotter import AnalysisPlotter
from master_plotter import MasterPlotter
from advanced_metrics import AdvancedMetricsCalculator


class SteppedConeBatchProcessor:
    """
    Universal batch processor for SteppedCone adhesion tests with area-based analysis.
    Works with any folder structure as long as it contains:
    - LayerToArea.txt file (layer number to contact area mapping)
    - Subfolders with SteppedCone test data
    - autolog_*.csv files in each subfolder
    """
    
    def __init__(self, data_directory, area_mapping_file=None, output_directory=None, 
                 skip_individual_plots=False):
        """
        Initialize the processor
        
        Args:
            data_directory: Path to the directory containing SteppedCone test folders
            area_mapping_file: Path to LayerToArea.txt file (auto-detected if None)
            output_directory: Directory to save outputs (defaults to data_directory)
            skip_individual_plots: If True, skip generating individual layer plots
        """
        self.data_directory = Path(data_directory)
        self.skip_individual_plots = skip_individual_plots
        
        # Auto-detect area mapping file if not provided
        if area_mapping_file is None:
            area_mapping_file = self.data_directory / "LayerToArea.txt"
            if not area_mapping_file.exists():
                raise FileNotFoundError(
                    f"Could not find LayerToArea.txt in {self.data_directory}. "
                    f"Please provide the path explicitly."
                )
        
        self.area_mapping_file = Path(area_mapping_file)
        self.output_directory = Path(output_directory) if output_directory else self.data_directory
        
        # Validate paths
        if not self.data_directory.exists():
            raise FileNotFoundError(f"Data directory not found: {self.data_directory}")
        if not self.area_mapping_file.exists():
            raise FileNotFoundError(f"Area mapping file not found: {self.area_mapping_file}")
        
        # Load area mapping
        self.area_map = self._load_area_mapping()
        
        # Initialize calculator, processor, and plotter
        self.calculator = AdhesionMetricsCalculator()
        self.processor = RawDataProcessor(self.calculator)
        self.plotter = AnalysisPlotter(figure_size=(16, 12), dpi=150)
        
        # Storage for all results
        self.all_results = []
        
    def _load_area_mapping(self):
        """Load the layer-to-area mapping from LayerToArea.txt"""
        print(f"\nLoading area mapping from: {self.area_mapping_file}")
        
        area_df = pd.read_csv(self.area_mapping_file, sep='\t')
        area_dict = dict(zip(area_df['Layer_Number'], area_df['Area']))
        
        print(f"Loaded area mapping for {len(area_dict)} layers")
        print(f"Area range: {min(area_dict.values()):.2f} - {max(area_dict.values()):.2f} mm²")
        
        return area_dict
    
    def parse_folder_name(self, folder_name):
        """
        Parse the folder name to extract fluid type, gap, and optionally speed
        
        Args:
            folder_name: Name of the folder
                        Format examples:
                        - '2p5PEO_1mm_SteppedCone_BPAGDA' (original)
                        - 'Water_1mm_SteppedCone_BPAGDA_1000' (with speed)
                        - 'ACF_5mm_SteppedCone_BPAGDA_200' (ACF with speed)
                        - 'Water_1mm_SandwichCone_BPAGDA_1000' (sandwich variant)
            
        Returns:
            Tuple of (fluid_type, gap_mm, speed_um_s or None)
        """
        parts = folder_name.split('_')
        
        # Extract fluid type (e.g., '2p5PEO', 'Water', 'ACF', 'TEMPOV2')
        fluid_type = parts[0]
        
        # Check if this is a SandwichCone test - modify fluid_type label
        if 'SandwichCone' in folder_name or 'Sandwich' in folder_name or 'SandwichedCone' in folder_name:
            fluid_type = f"{fluid_type}_Sandwich"
        
        # Extract gap (e.g., '1mm' or '5mm')
        gap_str = parts[1]
        gap_mm = float(gap_str.replace('mm', ''))
        
        # Check if there's a speed suffix (last part is a number or ends with 'umps')
        speed_um_s = None
        last_part = parts[-1]
        if last_part.isdigit():
            speed_um_s = int(last_part)
        elif 'umps' in last_part.lower():
            # Extract numeric part from strings like '6000umps'
            speed_str = last_part.lower().replace('umps', '')
            if speed_str.isdigit():
                speed_um_s = int(speed_str)
        
        return fluid_type, gap_mm, speed_um_s
    
    def extract_layer_number(self, filename):
        """
        Extract layer number from autolog filename
        
        Args:
            filename: e.g., 'autolog_L100-L105.csv'
            
        Returns:
            First layer number in the range
        """
        # Extract the part between 'L' and '-'
        if 'L' in filename and '-' in filename:
            start_str = filename.split('L')[1].split('-')[0]
            return int(start_str)
        return None
    
    def process_single_folder(self, folder_path):
        """
        Process all autolog files in a single folder
        
        Args:
            folder_path: Path to the folder containing autolog files
            
        Returns:
            List of result dictionaries
        """
        folder_path = Path(folder_path)
        folder_name = folder_path.name
        
        print(f"\nProcessing folder: {folder_name}")
        
        # Parse folder name
        fluid_type, gap_mm, speed_um_s = self.parse_folder_name(folder_name)
        
        # Create condition label
        if speed_um_s:
            condition_label = f"{fluid_type}_{int(gap_mm)}mm_{speed_um_s}um_s"
            print(f"  Fluid Type: {fluid_type}")
            print(f"  Gap: {gap_mm} mm")
            print(f"  Speed: {speed_um_s} um/s")
        else:
            condition_label = f"{fluid_type}_{int(gap_mm)}mm"
            print(f"  Fluid Type: {fluid_type}")
            print(f"  Gap: {gap_mm} mm")
        
        # Create plots directory for this folder (only if generating plots)
        plots_dir = folder_path / 'plots'
        if not self.skip_individual_plots:
            plots_dir.mkdir(exist_ok=True)
            print(f"  Plots will be saved to: {plots_dir}")
        
        # Find all autolog files
        autolog_files = sorted(folder_path.glob('autolog_*.csv'))
        print(f"  Found {len(autolog_files)} autolog files")
        
        results = []
        
        for file in autolog_files:
            try:
                # Extract layer number
                layer_num = self.extract_layer_number(file.name)
                if layer_num is None:
                    print(f"    Warning: Could not extract layer number from {file.name}")
                    continue
                
                # Get area for this layer
                area_mm2 = self.area_map.get(layer_num)
                if area_mm2 is None:
                    print(f"    Warning: No area mapping for layer {layer_num}")
                    continue
                
                # Create title with area information
                plot_title = f"{condition_label} - Layers {layer_num}-{layer_num+5} (Area: {area_mm2:.2f} mm²)"
                plot_save_path = plots_dir / f"{file.stem}_analysis.png"
                
                # Process CSV using RawData_Processor
                layers = self.processor.process_csv(
                    csv_filepath=str(file),
                    title=plot_title,
                    save_path=None  # Plotting handled separately below
                )
                
                # Generate individual plot with AnalysisPlotter (if not skipped)
                if layers:
                    print(f"    Processed {len(layers)} layers from {file.name}")
                    
                    if not self.skip_individual_plots:
                        try:
                            # Load the raw data for plotting
                            df = pd.read_csv(file)
                            time_data = df['Elapsed Time (s)'].to_numpy()
                            force_data = df['Force (N)'].to_numpy()
                            
                            # Apply smoothing for the plot
                            smoothed_force = self.calculator._apply_smoothing(force_data)
                            
                            # Generate the plot
                            self.plotter.create_plot(
                                time_data=time_data,
                                force_data=force_data,
                                smoothed_force=smoothed_force,
                                layers=layers,
                                title=plot_title,
                                save_path=plot_save_path
                            )
                            print(f"    Saved plot: {plot_save_path.name}")
                        except Exception as plot_error:
                            print(f"    Warning: Could not generate plot for {file.name}: {plot_error}")
                
                if layers:
                    # Extract metrics from each layer
                    for layer_obj in layers:
                        # Extract metrics from nested metrics dictionary
                        metrics_dict = layer_obj.get('metrics', {})
                        
                        # Store results
                        result = {
                            'folder_name': folder_name,
                            'layer_number': layer_num,
                            'condition_label': condition_label,
                            'fluid_type': fluid_type,
                            'gap_mm': gap_mm,
                            'speed_um_s': speed_um_s,  # Will be None if not present
                            'area_mm2': area_mm2,
                            'peak_force_N': layer_obj.get('peak_force_corrected', None),
                            'work_of_adhesion_mJ': layer_obj.get('work_of_adhesion_mJ', None),
                            'peel_distance_mm': metrics_dict.get('total_peel_distance', None),
                            'peak_retraction_force_N': layer_obj.get('peak_retraction_force', None),
                            'distance_to_peak_mm': metrics_dict.get('pre_initiation_distance', None),
                            'propagation_distance_mm': metrics_dict.get('propagation_distance', None),
                            'effective_stiffness_N_per_mm': metrics_dict.get('effective_stiffness_N_per_mm', None),
                            'stiffness_r_squared': metrics_dict.get('stiffness_r_squared', None),
                            'total_peel_time_s': metrics_dict.get('total_peel_duration', None),
                            'pre_initiation_time_s': metrics_dict.get('pre_initiation_time', None)
                        }
                        
                        results.append(result)
                
            except Exception as e:
                print(f"    Error processing {file.name}: {str(e)}")
                continue
        
        print(f"  Successfully processed {len(results)} layers")
        
        return results
    
    def process_all_folders(self):
        """Process all folders in the data directory"""
        print(f"\n{'='*60}")
        print(f"Starting SteppedCone Batch Processing")
        print(f"{'='*60}")
        print(f"Data directory: {self.data_directory}")
        
        # Find all folders containing test data (look for 'Cone' or 'SteppedCone' in name, or any folder with autolog files)
        potential_folders = [f for f in self.data_directory.iterdir() if f.is_dir()]
        
        # Filter to folders that either have 'Cone' in name OR contain autolog files
        folders = []
        for f in potential_folders:
            if 'Cone' in f.name or 'SteppedCone' in f.name:
                folders.append(f)
            elif any(f.glob('autolog_*.csv')):
                # Folder has autolog files but doesn't have Cone in name
                folders.append(f)
        
        if len(folders) == 0:
            print("\nWARNING: No test folders found!")
            print("Please ensure folder names contain 'Cone' or have autolog_*.csv files")
            return []
        
        print(f"Found {len(folders)} test folders to process")
        
        for folder in sorted(folders):
            results = self.process_single_folder(folder)
            self.all_results.extend(results)
        
        print(f"\n{'='*60}")
        print(f"Processing Complete")
        print(f"Total layers processed: {len(self.all_results)}")
        print(f"{'='*60}")
        
        return self.all_results
    
    def save_master_csv(self):
        """Save all results to a master CSV file"""
        if not self.all_results:
            print("\nNo results to save!")
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame(self.all_results)
        
        # Save to both filenames for compatibility
        # MASTER_all_metrics.csv - standard name used by other plotting scripts
        standard_csv = self.output_directory / "MASTER_all_metrics.csv"
        df.to_csv(standard_csv, index=False)
        
        # MASTER_steppedcone_metrics.csv - descriptive name for clarity
        steppedcone_csv = self.output_directory / "MASTER_steppedcone_metrics.csv"
        df.to_csv(steppedcone_csv, index=False)
        
        print(f"\n{'='*60}")
        print(f"Processing Complete")
        print(f"Total layers processed: {len(df)}")
        print(f"{'='*60}\n")
        
        print(f"Saved master CSV to: {standard_csv}")
        print(f"Also saved as: {steppedcone_csv}")
        print(f"Total rows: {len(df)}")
        
        # Print summary by condition
        print(f"\n{'='*60}")
        print(f"Summary by Condition:")
        print(f"{'='*60}\n")
        
        for condition in sorted(df['condition_label'].unique()):
            condition_data = df[df['condition_label'] == condition]
            print(f"{condition}:")
            print(f"  Layers: {len(condition_data)}")
            print(f"  Area range: {condition_data['area_mm2'].min():.2f} - {condition_data['area_mm2'].max():.2f} mm²")
            print(f"  Peak Force: {condition_data['peak_force_N'].mean():.4f} ± {condition_data['peak_force_N'].std():.4f} N")
            print(f"  Work of Adhesion: {condition_data['work_of_adhesion_mJ'].mean():.4f} ± {condition_data['work_of_adhesion_mJ'].std():.4f} mJ\n")
        
        return df
    
    def generate_master_plots(self):
        """Generate all master plots using MasterPlotter"""
        if not self.all_results:
            print("\nNo results to plot!")
            return
        
        # Convert to DataFrame
        df = pd.DataFrame(self.all_results)
        
        # Create MasterPlotter instance
        master_plotter = MasterPlotter(output_directory=self.output_directory, dpi=300)
        
        # Generate comprehensive plot set (like V7)
        print("\n" + "="*60)
        print("Generating Master Plots")
        print("="*60)
        
        # 1. Area-based plots (area analysis, area ratio, distance)
        master_plotter.generate_standard_plots(df)
        
        # 2. Radius-based analysis plots
        master_plotter.generate_standard_radius_plots(df)
        
        # 3. Stiffness analysis plot
        master_plotter.generate_stiffness_analysis_plot(df)
        
        # 4. Absolute peak force plot (if baseline_force_N column exists)
        if 'baseline_force_N' in df.columns and 'absolute_peak_force_N' not in df.columns:
            df['absolute_peak_force_N'] = df['peak_force_N'] - df['baseline_force_N']
        
        if 'absolute_peak_force_N' in df.columns:
            master_plotter.generate_absolute_force_plot(df)
        else:
            print("\nSkipping absolute force plot (baseline_force_N not available)")
    
    def perform_scaling_analysis(self):
        """Perform power law scaling analysis on the data"""
        if not self.all_results:
            print("\nNo results for scaling analysis!")
            return
        
        # Convert to DataFrame
        df = pd.DataFrame(self.all_results)
        
        # Calculate radius from area (radius = sqrt(area/π))
        df['radius_mm'] = np.sqrt(df['area_mm2'] / np.pi)
        
        # Create AdvancedMetricsCalculator instance
        advanced = AdvancedMetricsCalculator()
        
        print("\n" + "="*60)
        print("Performing Scaling Analysis (Power Law)")
        print("="*60)
        print("\nThe power law fit: y = A * r^n")
        print("  - A is the coefficient (proportionality constant)")
        print("  - n is the scaling exponent")
        print("  - For adhesion with uniform stress: Force ~ Area ~ r^2, so n ~= 2")
        print("  - For line peeling or edge effects: n ~= 1 (force scales with perimeter)")
        print("="*60)
        
        # Metrics to analyze (using radius instead of area)
        metrics_to_analyze = [
            ('peak_force_N', 'radius_mm', 'Peak Force'),
            ('work_of_adhesion_mJ', 'radius_mm', 'Work of Adhesion'),
            ('peel_distance_mm', 'radius_mm', 'Peel Distance'),
            ('effective_stiffness_N_per_mm', 'radius_mm', 'Effective Stiffness')
        ]
        
        all_scaling_results = []
        
        for y_metric, x_metric, metric_name in metrics_to_analyze:
            if y_metric not in df.columns:
                print(f"\nSkipping {metric_name} (column not found)")
                continue
            
            print(f"\n{metric_name} vs Contact Area:")
            print("-" * 60)
            
            # Fit scaling law for each condition
            results_df = advanced.fit_scaling_laws_by_condition(
                df, 
                y_metric=y_metric,
                x_metric=x_metric,
                condition_column='condition_label'
            )
            
            # Add metric name to results
            results_df['metric_name'] = metric_name
            results_df['y_metric'] = y_metric
            results_df['x_metric'] = x_metric
            
            all_scaling_results.append(results_df)
            
            # Generate scaling plot
            plot_path = self.output_directory / f"MASTER_scaling_{y_metric}.png"
            advanced.plot_scaling_analysis(
                df,
                y_metric=y_metric,
                x_metric=x_metric,
                output_path=plot_path
            )
        
        # Combine all results
        if all_scaling_results:
            combined_results = pd.concat(all_scaling_results, ignore_index=True)
            
            # Save to CSV
            csv_path = self.output_directory / "MASTER_scaling_analysis.csv"
            combined_results.to_csv(csv_path, index=False)
            print(f"\n{'='*60}")
            print(f"Scaling analysis results saved to:")
            print(f"  {csv_path}")
            print(f"{'='*60}\n")
            
            # Print summary
            print("\nScaling Analysis Summary:")
            print("="*60)
            for metric_name in combined_results['metric_name'].unique():
                metric_data = combined_results[combined_results['metric_name'] == metric_name]
                print(f"\n{metric_name}:")
                for _, row in metric_data.iterrows():
                    if row['condition'] != 'All data':
                        print(f"  {row['condition']:<25} n = {row['exponent']:.3f} ± {row['exponent_stderr']:.3f}, R² = {row['r_squared']:.4f}")
            print("="*60)


def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description='Batch process SteppedCone adhesion test data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process V3 folder (assumes base directory structure)
  python batch_process_steppedcone_generalized.py --folder V3
  
  # Process V4 folder
  python batch_process_steppedcone_generalized.py --folder V4
  
  # Process custom path
  python batch_process_steppedcone_generalized.py --folder "C:/CustomPath/MyData"
  
  # Skip individual plots (faster processing)
  python batch_process_steppedcone_generalized.py --folder V3 --skip-plots
  
  # CSV only (no plots at all)
  python batch_process_steppedcone_generalized.py --folder V3 --csv-only
        """
    )
    
    parser.add_argument(
        '--folder', '-f',
        required=True,
        help='Folder name (e.g., V3, V4) or full path to data directory'
    )
    
    parser.add_argument(
        '--base-dir', '-b',
        default=r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests",
        help='Base directory containing test folders (default: standard lab location)'
    )
    
    parser.add_argument(
        '--area-mapping', '-a',
        default=None,
        help='Path to LayerToArea.txt file (auto-detected if not provided)'
    )
    
    parser.add_argument(
        '--output-dir', '-o',
        default=None,
        help='Output directory for results (defaults to data directory)'
    )
    
    parser.add_argument(
        '--skip-plots',
        action='store_true',
        help='Skip generating individual layer plots (faster processing)'
    )
    
    parser.add_argument(
        '--csv-only',
        action='store_true',
        help='Only generate CSV file, skip all plotting'
    )
    
    return parser.parse_args()


def main():
    """Main execution function"""
    
    # Parse command-line arguments
    args = parse_arguments()
    
    # Determine data directory
    if Path(args.folder).is_absolute():
        # User provided full path
        data_directory = Path(args.folder)
    else:
        # User provided folder name (e.g., 'V3', 'V4')
        data_directory = Path(args.base_dir) / args.folder
    
    # Print configuration
    print("\n" + "="*60)
    print("SteppedCone Batch Processor - Configuration")
    print("="*60)
    print(f"Data directory: {data_directory}")
    print(f"Area mapping: {'Auto-detect' if args.area_mapping is None else args.area_mapping}")
    print(f"Output directory: {'Same as data' if args.output_dir is None else args.output_dir}")
    print(f"Individual plots: {'Disabled' if args.skip_plots or args.csv_only else 'Enabled'}")
    print(f"Master plots: {'Disabled' if args.csv_only else 'Enabled'}")
    print("="*60 + "\n")
    
    # Create processor
    try:
        processor = SteppedConeBatchProcessor(
            data_directory=data_directory,
            area_mapping_file=args.area_mapping,
            output_directory=args.output_dir,
            skip_individual_plots=args.skip_plots or args.csv_only
        )
    except FileNotFoundError as e:
        print(f"\nERROR: {e}")
        print("\nPlease check your paths and try again.")
        sys.exit(1)
    
    # Process all folders
    processor.process_all_folders()
    
    # Save master CSV
    master_df = processor.save_master_csv()
    
    # Generate plots (unless CSV-only mode)
    if not args.csv_only and master_df is not None:
        processor.generate_master_plots()
        processor.perform_scaling_analysis()
    
    print("\n" + "="*60)
    print("SteppedCone Batch Processing Complete!")
    print("="*60)


if __name__ == "__main__":
    main()
