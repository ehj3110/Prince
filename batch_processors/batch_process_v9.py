"""
V9-Specific Batch Processor for SteppedCone Adhesion Data
==========================================================

Batch processor specifically for V9 data with new naming convention:
Membrane_Gap_Tank_Fluid_Speed (e.g., PDMS_500um_V23Ext_Water_1000)

Usage:
    python batch_process_v9.py

Author: Cheng Sun Lab Team
Date: January 10, 2026
"""

import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import sys
from datetime import datetime

# Add support_modules and post-processing to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'support_modules'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'post-processing'))
from adhesion_metrics_calculator import AdhesionMetricsCalculator
from RawData_Processor import RawDataProcessor
from analysis_plotter import AnalysisPlotter
from master_plotter import MasterPlotter
from advanced_metrics import AdvancedMetricsCalculator


class V9BatchProcessor:
    """
    Batch processor for V9 SteppedCone tests with new naming convention.
    
    Naming format: Membrane_Gap_Tank_Fluid_Speed
    Examples:
        - FEP_500um_V19_Air_400
        - PDMS_0um_V23wExt_Water_1000
        - PDMS_500um_V23Ext_Water_1000
    """
    
    def __init__(self, skip_individual_plots=False):
        """Initialize the V9 processor"""
        # Final presentation data directory
        self.data_directory = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\Presentation data\Final")
        
        # Area mapping will be loaded from each folder's automated_work_of_adhesion.csv
        self.area_mapping_file = None
        
        self.output_directory = self.data_directory
        self.skip_individual_plots = skip_individual_plots
        
        # Validate paths
        if not self.data_directory.exists():
            raise FileNotFoundError(f"V9_New directory not found: {self.data_directory}")
        
        # Area mapping will be loaded per-folder from automated_work_of_adhesion.csv
        self.area_map = {}
        
        # Initialize calculator, processor, and plotter
        # Note: Calculator will be reconfigured per folder if needed
        self.calculator = AdhesionMetricsCalculator()
        self.processor = RawDataProcessor(self.calculator)
        self.plotter = AnalysisPlotter(figure_size=(16, 12), dpi=150)
        
        # Storage for all results
        self.all_results = []
        
    def _load_area_mapping_from_folder(self, folder_path):
        """Load layer-to-area mapping from folder's automated_work_of_adhesion.csv"""
        csv_path = folder_path / "automated_work_of_adhesion.csv"
        
        if not csv_path.exists():
            print(f"  [!] No automated_work_of_adhesion.csv found in {folder_path.name}")
            return {}
        
        try:
            area_df = pd.read_csv(csv_path)
            
            # Check if it has the required columns
            if 'Layer_Number' not in area_df.columns or 'Cross_Sectional_Area_mm2' not in area_df.columns:
                print(f"  [!] automated_work_of_adhesion.csv missing required columns")
                return {}
            
            area_dict = dict(zip(area_df['Layer_Number'], area_df['Cross_Sectional_Area_mm2']))
            
            if area_dict:
                print(f"  [OK] Loaded area mapping for {len(area_dict)} layers")
                print(f"       Area range: {min(area_dict.values()):.2f} - {max(area_dict.values()):.2f} mm²")
            
            return area_dict
            
        except Exception as e:
            print(f"  [!] Error loading area mapping: {e}")
            return {}
    
    def parse_folder_name(self, folder_name):
        """
        Parse V9 folder name to extract test parameters
        
        Format: Membrane_Gap_Tank_Fluid_Speed
        Examples:
            - FEP_500um_V19_Air_400
            - PDMS_0um_V23wExt_Water_1000
            - PDMS_500um_V23Ext_Water_1000
        
        OR simple folder name (e.g., "FEP", "Hybrid", "PDMS")
        
        Returns:
            dict with keys: membrane, gap_mm, tank, fluid, speed_um_s
        """
        parts = folder_name.split('_')
        
        # Handle simple folder names (just membrane name)
        if len(parts) == 1:
            return {
                'membrane': parts[0],
                'gap_mm': 0.0,
                'tank': 'Unknown',
                'fluid': 'Unknown',
                'speed_um_s': None
            }
        elif len(parts) == 2 or len(parts) == 3:
            # Handle names like "Hybrid - Compliant" or "PDMS - Unsealed"
            return {
                'membrane': folder_name,  # Use full name
                'gap_mm': 0.0,
                'tank': 'Unknown',
                'fluid': 'Unknown',
                'speed_um_s': None
            }
        
        # Extract membrane (first part)
        membrane = parts[0]  # FEP, PDMS
        
        # Extract gap (second part, e.g., "500um" or "0um")
        gap_str = parts[1]
        gap_mm = float(gap_str.replace('um', '')) / 1000  # Convert um to mm
        
        # Extract tank (third part, e.g., "V19", "V23Ext", "V23wExt")
        tank = parts[2]
        
        # Extract fluid (fourth part, e.g., "Air", "Water", "USW")
        fluid = parts[3]
        
        # Extract speed (fifth part, e.g., "400", "1000")
        speed_um_s = int(parts[4]) if len(parts) > 4 else None
        
        return {
            'membrane': membrane,
            'gap_mm': gap_mm,
            'tank': tank,
            'fluid': fluid,
            'speed_um_s': speed_um_s
        }
    
    def extract_layer_number(self, filename):
        """
        Extract layer number from autolog filename
        
        Args:
            filename: e.g., 'autolog_L100-L105.csv'
            
        Returns:
            First layer number in the range
        """
        if 'L' in filename and '-' in filename:
            start_str = filename.split('L')[1].split('-')[0]
            return int(start_str)
        return None
    
    def process_single_folder(self, folder_path):
        """
        Process all autolog files in a single V9 folder
        
        Args:
            folder_path: Path to the folder containing autolog files
            
        Returns:
            List of result dictionaries
        """
        folder_path = Path(folder_path)
        folder_name = folder_path.name
        
        print(f"\nProcessing folder: {folder_name}")
        
        # Load area mapping from this folder's automated_work_of_adhesion.csv
        self.area_map = self._load_area_mapping_from_folder(folder_path)
        
        if not self.area_map:
            print(f"  [!] No area mapping available - skipping this folder")
            return []
        
        # Parse folder name
        params = self.parse_folder_name(folder_name)
        
        # Create condition label
        condition_label = f"{params['membrane']}_{int(params['gap_mm']*1000)}um_{params['tank']}_{params['fluid']}_{params['speed_um_s']}"
        
        print(f"  Membrane: {params['membrane']}")
        print(f"  Gap: {params['gap_mm']:.3f} mm ({int(params['gap_mm']*1000)} um)")
        print(f"  Tank: {params['tank']}")
        print(f"  Fluid: {params['fluid']}")
        print(f"  Speed: {params['speed_um_s']} um/s")
        print(f"  Condition Label: {condition_label}")
        
        # Configure calculator for this condition
        speed = params['speed_um_s']
        membrane = params['membrane']
        
        # Skip first 200um to avoid hydrodynamic locking false peaks
        skip_distance_um = 200
        
        # For 400 and 4000 um/s speeds, enable smooth lifting detection
        # These speeds use a slow startup ramp (~200um) before reaching full peel speed
        target_speed = speed if speed in [400, 4000] else None
        
        if skip_distance_um > 0:
            print(f"  [!] Applying {skip_distance_um}um peak detection skip (hydrodynamic locking mitigation)")
        if target_speed is not None:
            print(f"  [*] Enabling smooth lifting detection (target speed: {target_speed} um/s)")
            
        self.calculator = AdhesionMetricsCalculator(
            skip_initial_distance_um=skip_distance_um,
            target_speed_um_s=target_speed
        )
        self.processor = RawDataProcessor(self.calculator)
        
        # Create plots directory (if generating plots)
        plots_dir = folder_path / 'plots'
        
        # Create timestamped subfolder for version control
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        timestamped_plots_dir = plots_dir / timestamp
        
        if not self.skip_individual_plots:
            timestamped_plots_dir.mkdir(parents=True, exist_ok=True)
            print(f"  Plots will be saved to: {timestamped_plots_dir}")
        
        # Find all autolog files
        autolog_files = sorted(folder_path.glob('autolog_*.csv'))
        print(f"  Found {len(autolog_files)} autolog files")
        
        # First pass: collect layer numbers and areas for title
        batch_layers = []
        batch_areas = []
        for file in autolog_files:
            layer_num = self.extract_layer_number(file.name)
            if layer_num is not None:
                area_mm2 = self.area_map.get(layer_num)
                if area_mm2 is not None:
                    batch_layers.append(layer_num)
                    batch_areas.append(area_mm2)
        
        # Create base title with folder name, layer range, and average area
        if batch_layers:
            min_layer = min(batch_layers)
            max_layer = max(batch_layers)
            avg_area = np.mean(batch_areas)
            folder_title = f"{params['membrane']}_{params['gap_mm']*1000:.0f}um_{params['tank']}_{params['fluid']}_{params['speed_um_s']}"
            base_title = f"{folder_title} - Layers {min_layer} -> {max_layer}\\nAverage Area: {avg_area:.2f} mm²"
        else:
            base_title = condition_label
        
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
                
                # Use timestamped plot path
                plot_save_path = timestamped_plots_dir / f"{file.stem}_analysis.png"
                
                # Extract layer range from this specific file
                file_layer_nums = self.processor._extract_layer_numbers_from_filename(str(file))
                if file_layer_nums:
                    file_min_layer = min(file_layer_nums)
                    file_max_layer = max(file_layer_nums)
                    file_avg_area = np.mean([self.area_map.get(ln, 0) for ln in file_layer_nums if self.area_map.get(ln)])
                    folder_title = f"{params['membrane']}_{params['gap_mm']*1000:.0f}um_{params['tank']}_{params['fluid']}_{params['speed_um_s']}"
                    file_title = f"{folder_title} - Layers {file_min_layer} -> {file_max_layer}\nAverage Area: {file_avg_area:.2f} mm²"
                else:
                    file_title = base_title
                
                # Process CSV using RawData_Processor
                layers = self.processor.process_csv(
                    csv_filepath=str(file),
                    title=file_title,
                    save_path=None
                )
                
                # Generate individual plot with AnalysisPlotter (if not skipped)
                if layers:
                    print(f"    Processed {len(layers)} layers from {file.name}")
                    
                    if not self.skip_individual_plots:
                        try:
                            # Load raw data for plotting
                            df = pd.read_csv(file)
                            time_data = df['Elapsed Time (s)'].to_numpy()
                            force_data = df['Force (N)'].to_numpy()
                            
                            # Apply smoothing
                            smoothed_force = self.calculator._apply_smoothing(force_data)
                            
                            # Generate plot
                            self.plotter.create_plot(
                                time_data=time_data,
                                force_data=force_data,
                                smoothed_force=smoothed_force,
                                layers=layers,
                                title=file_title,
                                save_path=plot_save_path
                            )
                            print(f"    Saved plot: {plot_save_path.name}")
                        except Exception as plot_error:
                            print(f"    Warning: Could not generate plot for {file.name}: {plot_error}")
                
                if layers:
                    # Extract metrics from each layer
                    for layer_obj in layers:
                        metrics_dict = layer_obj.get('metrics', {})
                        
                        # Store results
                        result = {
                            'folder_name': folder_name,
                            'source_file': file.stem,  # Track which autolog file this came from
                            'layer_number': layer_num,
                            'condition_label': condition_label,
                            'membrane': params['membrane'],
                            'gap_mm': params['gap_mm'],
                            'tank': params['tank'],
                            'fluid': params['fluid'],
                            'speed_um_s': params['speed_um_s'],
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
                import traceback
                traceback.print_exc()
                continue
        
        print(f"  Successfully processed {len(results)} layers")
        
        return results
    
    def process_all_folders(self):
        """Process all V9 folders"""
        print(f"\n{'='*60}")
        print(f"Starting V9 Batch Processing")
        print(f"{'='*60}")
        print(f"Data directory: {self.data_directory}")
        
        # Get all subfolders (exclude organizational folders)
        excluded_folders = {'data', 'Mean plots', 'Median plots', 'Log-Log plots', 'plots'}
        folders = [f for f in self.data_directory.iterdir() 
                  if f.is_dir() and f.name not in excluded_folders]
        
        if len(folders) == 0:
            print("\nWARNING: No condition folders found in V9 directory!")
            return []
        
        print(f"Found {len(folders)} condition folders to process:")
        for folder in sorted(folders):
            print(f"  - {folder.name}")
        
        for folder in sorted(folders):
            results = self.process_single_folder(folder)
            self.all_results.extend(results)
        
        print(f"\n{'='*60}")
        print(f"Processing Complete")
        print(f"Total layers processed: {len(self.all_results)}")
        print(f"{'='*60}")
        
        return self.all_results
    
    def save_master_csv(self):
        """Save all results to master CSV in data folder"""
        if not self.all_results:
            print("\nNo results to save!")
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame(self.all_results)
        
        # Save CSV to data folder
        data_folder = self.output_directory / "data"
        data_folder.mkdir(exist_ok=True)
        csv_path = data_folder / "MASTER_all_metrics.csv"
        df.to_csv(csv_path, index=False)
        
        print(f"\nSaved master CSV to: {csv_path}")
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
            
            # Check if peak_force_N has valid data
            if condition_data['peak_force_N'].notna().any():
                mean_force = condition_data['peak_force_N'].mean()
                std_force = condition_data['peak_force_N'].std()
                print(f"  Peak Force: {mean_force:.4f} ± {std_force:.4f} N")
            
            # Check if work_of_adhesion_mJ has valid data
            if condition_data['work_of_adhesion_mJ'].notna().any():
                mean_work = condition_data['work_of_adhesion_mJ'].mean()
                std_work = condition_data['work_of_adhesion_mJ'].std()
                print(f"  Work of Adhesion: {mean_work:.4f} ± {std_work:.4f} mJ")
            
            print()
        
        return df
    
    def generate_master_plots(self):
        """Generate master plots using MasterPlotter - saves to organized folders"""
        if not self.all_results:
            print("\nNo results to plot!")
            return
        
        df = pd.DataFrame(self.all_results)
        
        # Add expected column names for MasterPlotter compatibility
        # The 'work_of_adhesion_mJ' column contains baseline-corrected values
        if 'work_of_adhesion_mJ' in df.columns and 'work_of_adhesion_corrected_mJ' not in df.columns:
            df['work_of_adhesion_corrected_mJ'] = df['work_of_adhesion_mJ']
        
        print("\n" + "="*60)
        print("Generating Master Plots")
        print("="*60)
        
        # Create organized folders
        mean_folder = self.output_directory / "Mean plots"
        median_folder = self.output_directory / "Median plots"
        loglog_folder = self.output_directory / "Log-Log plots"
        
        for folder in [mean_folder, median_folder, loglog_folder]:
            folder.mkdir(exist_ok=True)
        
        # Generate MEAN plots
        print("\n--- Mean Plots ---")
        master_plotter = MasterPlotter(output_directory=mean_folder, dpi=300)
        master_plotter.generate_standard_radius_plots(df)
        master_plotter.generate_stiffness_analysis_plot(df)
        master_plotter.generate_distance_analysis_plot(df)
        
        # Generate MEDIAN plots
        print("\n--- Median Plots ---")
        master_plotter_median = MasterPlotter(output_directory=median_folder, dpi=300)
        master_plotter_median.generate_standard_radius_plots_median(df)
        
        # Generate LOG-LOG plots
        print("\n--- Log-Log Plots ---")
        master_plotter_loglog = MasterPlotter(output_directory=loglog_folder, dpi=300)
        master_plotter_loglog.generate_standard_radius_plots_loglog(df)
        
        print("\nMaster plots generated!")
    
    def perform_scaling_analysis(self):
        """Perform power law scaling analysis"""
        if not self.all_results:
            print("\nNo results for scaling analysis!")
            return
        
        df = pd.DataFrame(self.all_results)
        
        # Calculate radius
        df['radius_mm'] = np.sqrt(df['area_mm2'] / np.pi)
        
        # Create AdvancedMetricsCalculator
        advanced = AdvancedMetricsCalculator()
        
        print("\n" + "="*60)
        print("Performing Scaling Analysis")
        print("="*60)
        
        # Metrics to analyze
        metrics_to_analyze = [
            ('peak_force_N', 'radius_mm', 'Peak Force'),
            ('work_of_adhesion_mJ', 'radius_mm', 'Work of Adhesion'),
            ('peel_distance_mm', 'radius_mm', 'Peel Distance'),
            ('effective_stiffness_N_per_mm', 'radius_mm', 'Effective Stiffness')
        ]
        
        for y_metric, x_metric, metric_name in metrics_to_analyze:
            try:
                # Fit scaling laws
                results_df = advanced.fit_scaling_laws_by_condition(
                    df, y_metric, x_metric, 'condition_label'
                )
                
                # Save results
                csv_path = self.output_directory / f"MASTER_scaling_{y_metric}_vs_{x_metric}.csv"
                results_df.to_csv(csv_path, index=False)
                print(f"\nSaved scaling results: {csv_path.name}")
                
                # Generate plots
                for scale in ['linear', 'log']:
                    plot_path = self.output_directory / f"MASTER_scaling_{y_metric}_vs_{x_metric}_{scale}.png"
                    advanced.plot_scaling_analysis(
                        df, results_df, y_metric, x_metric, 
                        'condition_label', metric_name,
                        save_path=plot_path,
                        log_scale=(scale == 'log')
                    )
                    print(f"  Saved plot: {plot_path.name}")
                    
            except Exception as e:
                print(f"\nWarning: Could not perform scaling analysis for {metric_name}: {e}")
        
        print("\nScaling analysis complete!")


def main():
    """Main execution"""
    print("\n" + "="*60)
    print("V9 Batch Processor - Configuration")
    print("="*60)
    print("Mode: Process V9 data with radius-based analysis only")
    print("="*60 + "\n")
    
    # Create processor
    processor = V9BatchProcessor(skip_individual_plots=False)
    
    # Process all folders
    processor.process_all_folders()
    
    # Save master CSV
    master_df = processor.save_master_csv()
    
    # Generate plots
    if master_df is not None:
        processor.generate_master_plots()
        processor.perform_scaling_analysis()
    
    print("\n" + "="*60)
    print("V9 Batch Processing Complete!")
    print("="*60)


if __name__ == "__main__":
    main()
