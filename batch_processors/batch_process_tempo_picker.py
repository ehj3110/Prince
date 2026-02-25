"""
TEMPO Picker Batch Processor for Adhesion Data Analysis
========================================================

Specialized batch processor for the TEMPO Picker dataset with:
1. Distance-based peak filtering (ignore first 200um)
2. Two-regime stiffness detection (500-1000um transition)
3. Mean and median master plots
4. Comprehensive scaling and stiffness analysis

Usage:
    python batch_process_tempo_picker.py

Author: Cheng Sun Lab Team
Date: January 18, 2026
"""

import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import sys
from datetime import datetime
from scipy import stats

# Add support_modules to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'support_modules'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'post-processing'))
from adhesion_metrics_calculator import AdhesionMetricsCalculator
from RawData_Processor import RawDataProcessor
from analysis_plotter import AnalysisPlotter
from master_plotter import MasterPlotter
from advanced_metrics import AdvancedMetricsCalculator


class TEMPOPickerProcessor:
    """
    Batch processor for TEMPO Picker sequential dataset analysis
    """
    
    def __init__(self, base_directory, skip_individual_plots=False):
        """
        Initialize the TEMPO Picker processor
        
        Args:
            base_directory: Path to TEMPO Picker folder
            skip_individual_plots: If True, skip individual layer plots
        """
        self.base_directory = Path(base_directory)
        self.skip_individual_plots = skip_individual_plots
        
        # Validate path
        if not self.base_directory.exists():
            raise FileNotFoundError(f"TEMPO Picker directory not found: {self.base_directory}")
        
        # Configuration for this dataset
        # Distance-based peak filtering: ignore first 200um
        self.skip_initial_distance_um = 200
        
        # Two-regime stiffness transition range (500-1000um)
        self.stiffness_transition_range_um = (500, 1000)
        
        # Storage for all results
        self.all_results = []
        self.folder_metadata = {}
        self.membrane_label_counter = {}  # Track counts for each membrane type
        
        print(f"\n{'='*70}")
        print(f"TEMPO Picker Batch Processor Initialized")
        print(f"{'='*70}")
        print(f"Base directory: {self.base_directory}")
        print(f"Peak filtering: Skip first {self.skip_initial_distance_um} um")
        print(f"Stiffness transition: {self.stiffness_transition_range_um[0]}-{self.stiffness_transition_range_um[1]} um")
        print(f"{'='*70}\n")
    
    def get_subfolder_list(self):
        """Get list of numbered subfolders (1, 2, 3, etc.)"""
        # FILTERED: Only process folders 1, 2, 5, 6, 7 (lowest 3 TEMPO + 2 PDMS)
        selected_folders = ['1', '2', '5', '6', '7']
        subfolders = []
        for item in sorted(self.base_directory.iterdir()):
            if item.is_dir() and item.name in selected_folders:
                subfolders.append(item)
        return subfolders
    
    def load_experimental_conditions(self, folder_path):
        """
        Load experimental conditions from CSV file
        
        Args:
            folder_path: Path to subfolder
            
        Returns:
            dict with experimental parameters
        """
        exp_file = folder_path / "experimental_conditions.csv"
        if not exp_file.exists():
            print(f"  Warning: No experimental_conditions.csv found in {folder_path.name}")
            return {}
        
        try:
            df = pd.read_csv(exp_file)
            if len(df) > 0:
                # Get the most recent complete entry
                complete_rows = df[df['Print_Status'] == 'Complete']
                if len(complete_rows) > 0:
                    row = complete_rows.iloc[-1]
                else:
                    row = df.iloc[-1]
                
                return {
                    'membrane_type': row['Membrane_Type'],
                    'tempo_pattern': row['TEMPO_Pattern'],
                    'oil': row['Oil'],
                    'fluid_type': row['Fluid_Type'],
                    'fluid_gap_mm': float(row['Fluid_Gap_mm'].replace('um', '')) / 1000 if 'um' in str(row['Fluid_Gap_mm']) else 0,
                    'tank': row['Tank'],
                    'resin': row['Resin'],
                    'print_date': row['Print_Date_Time']
                }
        except Exception as e:
            print(f"  Warning: Could not parse experimental_conditions.csv: {e}")
            return {}
    
    def load_area_mapping(self, folder_path):
        """
        Load layer area and distance mapping from automated_work_of_adhesion.csv
        
        Args:
            folder_path: Path to subfolder
            
        Returns:
            dict mapping layer_number to dict with area and distance data:
            {
                layer_num: {
                    'area_mm2': float,
                    'distance_to_peak_mm': float,
                    'distance_to_propagate_mm': float,
                    'total_peel_distance_mm': float
                }
            }
        """
        area_file = folder_path / "automated_work_of_adhesion.csv"
        if not area_file.exists():
            print(f"  Warning: No automated_work_of_adhesion.csv found in {folder_path.name}")
            return {}
        
        try:
            df = pd.read_csv(area_file)
            
            # Check for required columns
            if 'Layer_Number' not in df.columns:
                print(f"  Warning: Layer_Number column not found in automated_work_of_adhesion.csv")
                return {}
            
            # Build mapping dictionary
            mapping = {}
            for _, row in df.iterrows():
                layer_num = row['Layer_Number']
                layer_data = {}
                
                # Add area if available
                if 'Cross_Sectional_Area_mm2' in df.columns:
                    layer_data['area_mm2'] = row['Cross_Sectional_Area_mm2']
                
                # Add distance columns if available
                if 'Distance_to_Peak_mm' in df.columns:
                    layer_data['distance_to_peak_mm'] = row['Distance_to_Peak_mm']
                if 'Distance_to_Propagate_mm' in df.columns:
                    layer_data['distance_to_propagate_mm'] = row['Distance_to_Propagate_mm']
                if 'Total_Peel_Distance_mm' in df.columns:
                    layer_data['total_peel_distance_mm'] = row['Total_Peel_Distance_mm']
                
                mapping[layer_num] = layer_data
            
            print(f"  Loaded area/distance data for {len(mapping)} layers")
            return mapping
            
        except Exception as e:
            print(f"  Warning: Could not parse automated_work_of_adhesion.csv: {e}")
            return {}
    
    def extract_layer_numbers_from_filename(self, filename):
        """Extract layer numbers from autolog filename (e.g., 'autolog_L107-L111.csv')"""
        if 'L' in filename and '-' in filename:
            try:
                parts = filename.replace('autolog_', '').replace('.csv', '').split('-')
                start_layer = int(parts[0].replace('L', ''))
                end_layer = int(parts[1].replace('L', ''))
                return list(range(start_layer, end_layer + 1))
            except:
                pass
        return []
    
    def process_single_folder(self, folder_path):
        """
        Process all autolog files in a single numbered subfolder
        
        Args:
            folder_path: Path to the subfolder
            
        Returns:
            List of result dictionaries
        """
        folder_path = Path(folder_path)
        folder_name = folder_path.name
        
        print(f"\n{'='*70}")
        print(f"Processing Folder: {folder_name}")
        print(f"{'='*70}")
        
        # Load experimental conditions
        exp_conditions = self.load_experimental_conditions(folder_path)
        self.folder_metadata[folder_name] = exp_conditions
        
        if exp_conditions:
            print(f"  Membrane: {exp_conditions.get('membrane_type', 'Unknown')}")
            print(f"  Fluid: {exp_conditions.get('fluid_type', 'Unknown')}")
            print(f"  Gap: {exp_conditions.get('fluid_gap_mm', 0)*1000:.0f} um")
        
        # Load area and distance mapping from automated_work_of_adhesion.csv
        area_distance_map = self.load_area_mapping(folder_path)
        
        # Find all autolog CSV files
        autolog_files = sorted(folder_path.glob("autolog_*.csv"))
        print(f"  Found {len(autolog_files)} autolog files")
        
        if len(autolog_files) == 0:
            print(f"  No autolog files found, skipping...")
            return []
        
        # Create plots directory with timestamp
        plots_dir = folder_path / "plots"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        timestamped_plots_dir = plots_dir / timestamp
        
        if not self.skip_individual_plots:
            timestamped_plots_dir.mkdir(parents=True, exist_ok=True)
            print(f"  Plots will be saved to: {timestamped_plots_dir}")
        
        # Initialize calculator with distance-based filtering
        calculator = AdhesionMetricsCalculator(
            skip_initial_distance_um=self.skip_initial_distance_um
        )
        processor = RawDataProcessor(calculator)
        
        # Process each autolog file
        folder_results = []
        
        for autolog_file in autolog_files:
            print(f"\n  Processing: {autolog_file.name}")
            
            try:
                # Extract layer numbers
                layer_numbers = self.extract_layer_numbers_from_filename(autolog_file.name)
                
                # Process the file
                layers_data = processor.process_csv(str(autolog_file))
                
                if not layers_data or len(layers_data) == 0:
                    print(f"    Warning: No layers extracted")
                    continue
                
                print(f"    Successfully processed {len(layers_data)} layers")
                
                # Add metadata to each layer
                for i, layer_obj in enumerate(layers_data):
                    # Extract metrics from layer object
                    metrics = layer_obj.get('metrics', {})
                    
                    # Get membrane type for this folder (use last entry as label)
                    base_membrane_type = exp_conditions.get('membrane_type', folder_name) if exp_conditions else folder_name
                    
                    # Create label using membrane type and folder number
                    membrane_label = f"{base_membrane_type} - {folder_name}"
                    
                    # Create flat dictionary for CSV export
                    layer_record = {
                        'folder': folder_name,
                        'membrane_label': membrane_label,
                        'autolog_file': autolog_file.name,
                        'layer_number': layer_obj.get('number', layer_numbers[i] if i < len(layer_numbers) else None)
                    }
                    
                    # Add all metrics
                    layer_record.update(metrics)
                    
                    # Add area and distance data if available
                    layer_num = layer_record['layer_number']
                    if layer_num in area_distance_map:
                        area_mm2 = area_distance_map[layer_num].get('area_mm2')
                        if area_mm2 is not None:
                            layer_record['cross_sectional_area_mm2'] = area_mm2
                            layer_record['radius_mm'] = np.sqrt(area_mm2 / np.pi)
                        
                        # ONLY add distance data if NOT already calculated by metrics
                        # The calculated metrics respect the 200μm skip, the CSV values don't
                        if 'distance_to_peak_mm' not in layer_record and 'distance_to_peak_mm' in area_distance_map[layer_num]:
                            layer_record['raw_distance_to_peak_mm'] = area_distance_map[layer_num]['distance_to_peak_mm']
                        if 'distance_to_propagate_mm' not in layer_record and 'distance_to_propagate_mm' in area_distance_map[layer_num]:
                            layer_record['raw_distance_to_propagate_mm'] = area_distance_map[layer_num]['distance_to_propagate_mm']
                        if 'total_peel_distance_mm' not in layer_record and 'total_peel_distance_mm' in area_distance_map[layer_num]:
                            layer_record['raw_total_peel_distance_mm'] = area_distance_map[layer_num]['total_peel_distance_mm']
                    
                    # Add experimental conditions
                    for key, value in exp_conditions.items():
                        layer_record[key] = value
                    
                    folder_results.append(layer_record)
                
                # Create individual plot if requested
                if not self.skip_individual_plots:
                    # Need to reload the full dataset for plotting
                    # The processor returns layer objects, but plotting needs raw arrays
                    import pandas as pd
                    csv_df = pd.read_csv(str(autolog_file))
                    time_data = csv_df['Elapsed Time (s)'].to_numpy()
                    force_data = csv_df['Force (N)'].to_numpy()
                    
                    # Apply smoothing for plot
                    smoothed_force = calculator._apply_smoothing(force_data)
                    
                    # Create title with layer range
                    if layer_numbers:
                        min_layer = min(layer_numbers)
                        max_layer = max(layer_numbers)
                        
                        membrane_str = exp_conditions.get('membrane_type', 'Unknown')
                        fluid_str = exp_conditions.get('fluid_type', 'Unknown')
                        gap_str = f"{exp_conditions.get('fluid_gap_mm', 0)*1000:.0f}um"
                        
                        title = f"Folder {folder_name}: {membrane_str}, {fluid_str}, {gap_str} - Layers {min_layer} -> {max_layer}"
                    else:
                        title = f"Folder {folder_name} - {autolog_file.stem}"
                    
                    # Generate plot using raw data and layer objects
                    plotter = AnalysisPlotter(figure_size=(16, 12), dpi=150)
                    plot_path = timestamped_plots_dir / f"{autolog_file.stem}_analysis.png"
                    
                    plotter.create_plot(
                        time_data=time_data,
                        force_data=force_data,
                        smoothed_force=smoothed_force,
                        layers=layers_data,
                        title=title,
                        save_path=str(plot_path)
                    )
                    print(f"    Plot saved: {plot_path.name}")
                
            except Exception as e:
                print(f"    Error processing {autolog_file.name}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"\n  Folder {folder_name} Summary:")
        print(f"    Total layers processed: {len(folder_results)}")
        
        if len(folder_results) > 0:
            # Calculate folder statistics
            peak_forces = [r['peak_force_corrected'] for r in folder_results if r['peak_force_corrected'] > 0]
            if peak_forces:
                print(f"    Peak force range: {min(peak_forces):.4f} - {max(peak_forces):.4f} N")
                print(f"    Mean peak force: {np.mean(peak_forces):.4f} N")
            
            # Check for two-regime stiffness detection
            two_regime_count = sum(1 for r in folder_results if r.get('two_regime_detected', False))
            if two_regime_count > 0:
                print(f"    Two-regime stiffness detected in {two_regime_count}/{len(folder_results)} layers")
        
        return folder_results
    
    def process_all_folders(self):
        """Process all numbered subfolders in the TEMPO Picker directory"""
        subfolders = self.get_subfolder_list()
        
        print(f"\nFound {len(subfolders)} numbered folders to process")
        
        for folder in subfolders:
            results = self.process_single_folder(folder)
            self.all_results.extend(results)
        
        print(f"\n{'='*70}")
        print(f"All Folders Processed")
        print(f"{'='*70}")
        print(f"Total layers across all folders: {len(self.all_results)}")
        
        return self.all_results
    
    def export_master_csv(self, output_path=None):
        """
        Export all results to a master CSV file
        
        Args:
            output_path: Path for output CSV (default: base_directory/MASTER_all_metrics.csv)
        """
        if len(self.all_results) == 0:
            print("No results to export")
            return
        
        if output_path is None:
            output_path = self.base_directory / "MASTER_all_metrics.csv"
        
        df = pd.DataFrame(self.all_results)
        
        # Add column mappings for plotter compatibility (create _mm versions)
        if 'total_peel_distance' in df.columns and 'peel_distance_mm' not in df.columns:
            df['peel_distance_mm'] = df['total_peel_distance']
        if 'pre_initiation_distance' in df.columns and 'distance_to_peak_mm' not in df.columns:
            df['distance_to_peak_mm'] = df['pre_initiation_distance']
        if 'propagation_distance' in df.columns and 'propagation_distance_mm' not in df.columns:
            df['propagation_distance_mm'] = df['propagation_distance']
        
        # Create detailed_condition for master plotter using membrane_label
        if 'membrane_label' in df.columns:
            df['detailed_condition'] = df['membrane_label']
        
        df.to_csv(output_path, index=False)
        
        print(f"\nMaster CSV exported: {output_path}")
        print(f"  Total rows: {len(df)}")
        print(f"  Columns: {len(df.columns)}")
    
    def generate_master_plots(self):
        """Generate mean and median master plots for all data using MasterPlotter"""
        if len(self.all_results) == 0:
            print("No results to plot")
            return
        
        print(f"\n{'='*70}")
        print(f"Generating Master Plots with Style Guide Compliance")
        print(f"{'='*70}")
        
        df = pd.DataFrame(self.all_results)
        
        # Add condition label for plotting
        if 'membrane_type' in df.columns:
            df['condition_label'] = 'Folder ' + df['folder'].astype(str)
        
        # Calculate radius from area if available (for scaling)
        # Note: radius_mm is already calculated during processing from cross_sectional_area_mm2
        if 'cross_sectional_area_mm2' in df.columns and 'radius_mm' not in df.columns:
            df['radius_mm'] = np.sqrt(df['cross_sectional_area_mm2'] / np.pi)
        elif 'radius_mm' not in df.columns:
            # Generate synthetic area based on layer number if not available
            print("  Warning: No area data available, generating synthetic areas")
            df['cross_sectional_area_mm2'] = 10.0 + df['layer_number'] * 0.1  # Placeholder
            df['radius_mm'] = np.sqrt(df['cross_sectional_area_mm2'] / np.pi)
        
        # For backward compatibility, also create area_mm2 alias
        if 'cross_sectional_area_mm2' in df.columns:
            df['area_mm2'] = df['cross_sectional_area_mm2']
        
        # Rename columns to match MasterPlotter expectations
        column_mapping = {
            'peak_force_corrected': 'peak_force_N',
            'work_of_adhesion_corrected_mJ': 'work_of_adhesion_mJ',
            'total_work_of_adhesion_mJ': 'work_of_adhesion_mJ',  # Alternative name
            'propagation_distance': 'propagation_distance_mm',  # TEMPO uses propagation_distance
            'distance_to_propagate_mm': 'propagation_distance_mm',  # Also map this variant
            'pre_initiation_distance': 'distance_to_peak_mm',  # Map pre-initiation distance
            'effective_stiffness_N_per_mm': 'effective_stiffness_N_per_mm'
        }
        
        for old_col, new_col in column_mapping.items():
            if old_col in df.columns and new_col not in df.columns:
                df[new_col] = df[old_col]
        
        # Add peel_distance_mm if it doesn't exist (use total_peel_distance if available)
        if 'peel_distance_mm' not in df.columns:
            if 'total_peel_distance' in df.columns:
                df['peel_distance_mm'] = df['total_peel_distance']
            elif 'total_peel_distance_mm' in df.columns:
                df['peel_distance_mm'] = df['total_peel_distance_mm']
            else:
                print("  Note: peel_distance_mm not available (post-processing metric)")
                # Create dummy column to avoid errors
                df['peel_distance_mm'] = 0.0
        
        # Create detailed_condition for master plotter using membrane_label
        if 'membrane_label' in df.columns:
            df['detailed_condition'] = df['membrane_label']
        # Add total_peel_time_s if it doesn't exist (optional metric for TEMPO data)
        if 'total_peel_time_s' not in df.columns:
            print("  Note: total_peel_time_s not available (TEMPO data structure)")
            # Create dummy column to avoid errors
            df['total_peel_time_s'] = 0.0
        
        # Create organized folders
        master_plots_dir = self.base_directory / "MASTER_plots"
        mean_folder = master_plots_dir / "Mean_plots"
        median_folder = master_plots_dir / "Median_plots"
        loglog_folder = master_plots_dir / "Log-Log_plots"
        
        for folder in [mean_folder, median_folder, loglog_folder]:
            folder.mkdir(parents=True, exist_ok=True)
        
        # Set Times New Roman font (from style guide)
        plt.rcParams['font.family'] = 'Times New Roman'
        plt.rcParams['font.size'] = 12
        
        # Generate MEAN plots
        print("\n--- Mean Plots (with SEM error bars) ---")
        try:
            master_plotter = MasterPlotter(output_directory=mean_folder, dpi=300)
            master_plotter.generate_standard_radius_plots(df)
            if 'effective_stiffness_N_per_mm' in df.columns:
                master_plotter.generate_stiffness_analysis_plot(df)
            master_plotter.generate_distance_analysis_plot(df)
            print("  ✓ Mean plots generated successfully")
        except Exception as e:
            print(f"  Warning: Error generating mean plots: {e}")
            import traceback
            traceback.print_exc()
        
        # Generate MEDIAN plots
        print("\n--- Median Plots (with MAD error bars) ---")
        try:
            master_plotter_median = MasterPlotter(output_directory=median_folder, dpi=300)
            master_plotter_median.generate_standard_radius_plots_median(df)
            print("  ✓ Median plots generated successfully")
        except Exception as e:
            print(f"  Warning: Error generating median plots: {e}")
            import traceback
            traceback.print_exc()
        
        # Generate LOG-LOG plots
        print("\n--- Log-Log Plots (Power Law Analysis) ---")
        try:
            master_plotter_loglog = MasterPlotter(output_directory=loglog_folder, dpi=300)
            master_plotter_loglog.generate_standard_radius_plots_loglog(df)
            print("  ✓ Log-Log plots generated successfully")
        except Exception as e:
            print(f"  Warning: Error generating log-log plots: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"\n  All master plots saved to: {master_plots_dir}")
        
        # Generate comparison plots by folder
        self._generate_folder_comparison_plots(df, master_plots_dir)
    
    def perform_scaling_analysis(self):
        """Perform power law scaling analysis"""
        if len(self.all_results) == 0:
            print("No results for scaling analysis")
            return
        
        print(f"\n{'='*70}")
        print(f"Performing Scaling Analysis")
        print(f"{'='*70}")
        
        df = pd.DataFrame(self.all_results)
        
        # Add condition label and radius
        if 'membrane_type' in df.columns:
            df['condition_label'] = 'Folder ' + df['folder'].astype(str)
        
        # Check for area data (use cross_sectional_area_mm2 or area_mm2)
        if 'cross_sectional_area_mm2' not in df.columns and 'area_mm2' not in df.columns:
            print("  Warning: No area data available for scaling analysis")
            return
        
        # Calculate radius if not already present
        if 'radius_mm' not in df.columns:
            if 'cross_sectional_area_mm2' in df.columns:
                df['radius_mm'] = np.sqrt(df['cross_sectional_area_mm2'] / np.pi)
            else:
                df['radius_mm'] = np.sqrt(df['area_mm2'] / np.pi)
        
        # Create area_mm2 alias for compatibility
        if 'cross_sectional_area_mm2' in df.columns and 'area_mm2' not in df.columns:
            df['area_mm2'] = df['cross_sectional_area_mm2']
        
        # Rename columns to match expectations
        column_mapping = {
            'peak_force_corrected': 'peak_force_N',
            'work_of_adhesion_corrected_mJ': 'work_of_adhesion_mJ',
            'peel_distance_mm': 'peel_distance_mm',
            'effective_stiffness_N_per_mm': 'effective_stiffness_N_per_mm'
        }
        
        for old_col, new_col in column_mapping.items():
            if old_col in df.columns and new_col not in df.columns:
                df[new_col] = df[old_col]
        
        # Create AdvancedMetricsCalculator
        advanced = AdvancedMetricsCalculator()
        
        # Metrics to analyze
        metrics_to_analyze = [
            ('peak_force_N', 'radius_mm', 'Peak Force'),
            ('work_of_adhesion_mJ', 'radius_mm', 'Work of Adhesion'),
        ]
        
        if 'peel_distance_mm' in df.columns:
            metrics_to_analyze.append(('peel_distance_mm', 'radius_mm', 'Peel Distance'))
        
        if 'effective_stiffness_N_per_mm' in df.columns:
            metrics_to_analyze.append(('effective_stiffness_N_per_mm', 'radius_mm', 'Effective Stiffness'))
        
        scaling_dir = self.base_directory / "MASTER_plots" / "Scaling_Analysis"
        scaling_dir.mkdir(parents=True, exist_ok=True)
        
        for y_metric, x_metric, metric_name in metrics_to_analyze:
            try:
                # Check if columns exist and have valid data
                if y_metric not in df.columns or df[y_metric].isna().all():
                    print(f"  Skipping {metric_name}: No valid data")
                    continue
                
                # Fit scaling laws
                results_df = advanced.fit_scaling_laws_by_condition(
                    df, y_metric, x_metric, 'condition_label'
                )
                
                # Save results
                csv_path = scaling_dir / f"scaling_{y_metric}_vs_{x_metric}.csv"
                results_df.to_csv(csv_path, index=False)
                print(f"\n  Scaling results: {csv_path.name}")
                
                # Generate plots
                for scale in ['linear', 'log']:
                    plot_path = scaling_dir / f"scaling_{y_metric}_vs_{x_metric}_{scale}.png"
                    advanced.plot_scaling_analysis(
                        df, results_df, y_metric, x_metric, 
                        'condition_label', metric_name,
                        save_path=plot_path,
                        log_scale=(scale == 'log')
                    )
                    print(f"    ✓ {scale.capitalize()} plot: {plot_path.name}")
                    
            except Exception as e:
                print(f"  Warning: Could not perform scaling analysis for {metric_name}: {e}")
        
        print(f"\n  Scaling analysis saved to: {scaling_dir}")
    
    def _generate_folder_comparison_plots(self, df, output_dir):
        """Generate comparison plots across folders (bar charts)"""
        print("\n--- Folder Comparison Plots ---")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        
        folders = sorted(df['folder'].unique(), key=lambda x: int(x))
        
        # Calculate statistics per folder
        mean_forces = []
        median_forces = []
        sem_forces = []
        mad_forces = []
        
        for folder in folders:
            folder_data = df[df['folder'] == folder]['peak_force_corrected']
            folder_data = folder_data[folder_data > 0]  # Exclude invalid
            
            if len(folder_data) > 0:
                mean_forces.append(folder_data.mean())
                median_forces.append(folder_data.median())
                sem_forces.append(folder_data.sem())
                mad_forces.append(np.median(np.abs(folder_data - folder_data.median())))
            else:
                mean_forces.append(0)
                median_forces.append(0)
                sem_forces.append(0)
                mad_forces.append(0)
        
        x = np.arange(len(folders))
        
        # Mean plot
        ax1.bar(x, mean_forces, yerr=sem_forces, capsize=5, alpha=0.7, color='steelblue', edgecolor='black')
        ax1.set_xlabel('Folder Number', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Peak Force (N)', fontsize=14, fontweight='bold')
        ax1.set_title('Mean Peak Force by Folder', fontsize=16, fontweight='bold')
        ax1.set_xticks(x)
        ax1.set_xticklabels(folders)
        ax1.grid(alpha=0.3)
        
        # Median plot
        ax2.bar(x, median_forces, yerr=mad_forces, capsize=5, alpha=0.7, color='coral', edgecolor='black')
        ax2.set_xlabel('Folder Number', fontsize=14, fontweight='bold')
        ax2.set_ylabel('Peak Force (N)', fontsize=14, fontweight='bold')
        ax2.set_title('Median Peak Force by Folder', fontsize=16, fontweight='bold')
        ax2.set_xticks(x)
        ax2.set_xticklabels(folders)
        ax2.grid(alpha=0.3)
        
        plt.tight_layout()
        output_path = output_dir / f"{timestamp}_peak_force_comparison.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"  ✓ Peak force comparison saved: {output_path.name}")
        
        # Stiffness comparison
        if 'effective_stiffness_N_per_mm' in df.columns:
            self._plot_stiffness_by_folder(df, output_dir, timestamp)
        
        # Work of adhesion comparison
        work_col = None
        if 'work_of_adhesion_mJ' in df.columns:
            work_col = 'work_of_adhesion_mJ'
        elif 'work_of_adhesion_corrected_mJ' in df.columns:
            work_col = 'work_of_adhesion_corrected_mJ'
        elif 'total_work_of_adhesion_mJ' in df.columns:
            work_col = 'total_work_of_adhesion_mJ'
        
        if work_col:
            self._plot_work_of_adhesion_by_folder(df, output_dir, timestamp, work_col)
        
        # Two-regime stiffness
        if 'two_regime_detected' in df.columns and df['two_regime_detected'].sum() > 0:
            self._plot_two_regime_stiffness(df, output_dir, timestamp)
    
    def _plot_stiffness_by_folder(self, df, output_dir, timestamp):
        """Plot stiffness comparison across folders - scatter plot with radius vs stiffness"""
        # Check if stiffness column exists
        if 'effective_stiffness_N_per_mm' not in df.columns:
            print("  Warning: No stiffness data available, skipping stiffness plot")
            return
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
        
        folders = sorted(df['folder'].unique(), key=lambda x: int(x))
        colors = plt.cm.viridis(np.linspace(0, 1, len(folders)))
        
        # Determine if we have radius data
        use_radius = 'radius_mm' in df.columns and df['radius_mm'].notna().any()
        x_label = 'Contact Radius (mm)' if use_radius else 'Layer Number (Increasing Radius)'
        
        # Left plot: Single-regime stiffness (all layers)
        for i, folder in enumerate(folders):
            folder_data = df[df['folder'] == folder]
            # Filter valid stiffness data
            valid_data = folder_data[folder_data['effective_stiffness_N_per_mm'] > 0]
            
            if len(valid_data) > 0:
                # Use radius if available, otherwise layer number
                if use_radius:
                    x_values = valid_data['radius_mm'].values
                else:
                    x_values = valid_data['layer_number'].values
                stiffness = valid_data['effective_stiffness_N_per_mm'].values
                
                ax1.scatter(x_values, stiffness, alpha=0.6, s=50, c=[colors[i]], 
                           label=f'Folder {folder}', edgecolors='black', linewidths=0.5)
        
        ax1.set_xlabel(x_label, fontsize=14, fontweight='bold')
        ax1.set_ylabel('Stiffness (N/mm)', fontsize=14, fontweight='bold')
        ax1.set_title('Effective Stiffness vs Radius', fontsize=16, fontweight='bold')
        ax1.grid(alpha=0.3)
        ax1.legend(loc='best', fontsize=10)
        
        # Right plot: Two-regime stiffness (if detected)
        two_regime_df = df[df['two_regime_detected'] == True]
        
        if len(two_regime_df) > 0:
            for i, folder in enumerate(folders):
                folder_data = two_regime_df[two_regime_df['folder'] == folder]
                
                if len(folder_data) > 0:
                    if use_radius:
                        x_values = folder_data['radius_mm'].values
                    else:
                        x_values = folder_data['layer_number'].values
                    regime1_stiff = folder_data['regime1_stiffness_N_per_mm'].values
                    regime2_stiff = folder_data['regime2_stiffness_N_per_mm'].values
                    
                    # Dotted line for low stiffness (start)
                    ax2.plot(x_values, regime1_stiff, linestyle=':', linewidth=2, 
                            color=colors[i], alpha=0.7, label=f'Folder {folder} - Start')
                    
                    # Solid line for high stiffness (peel)
                    ax2.plot(x_values, regime2_stiff, linestyle='-', linewidth=2, 
                            color=colors[i], alpha=0.9, label=f'Folder {folder} - Peel')
            
            ax2.set_xlabel(x_label, fontsize=14, fontweight='bold')
            ax2.set_ylabel('Stiffness (N/mm)', fontsize=14, fontweight='bold')
            ax2.set_title('Two-Regime Stiffness (Solid=Peel, Dotted=Start)', fontsize=16, fontweight='bold')
            ax2.grid(alpha=0.3)
            ax2.legend(loc='best', fontsize=8, ncol=2)
        else:
            # If no two-regime data, show mean stiffness by folder
            for i, folder in enumerate(folders):
                folder_data = df[df['folder'] == folder]
                valid_data = folder_data[folder_data['effective_stiffness_N_per_mm'] > 0]
                
                if len(valid_data) > 0:
                    if use_radius:
                        x_values = valid_data['radius_mm'].values
                    else:
                        x_values = valid_data['layer_number'].values
                    stiffness = valid_data['effective_stiffness_N_per_mm'].values
                    
                    # Calculate moving average for trend
                    from scipy.ndimage import uniform_filter1d
                    if len(stiffness) > 5:
                        sorted_idx = np.argsort(x_values)
                        sorted_x = x_values[sorted_idx]
                        sorted_stiff = stiffness[sorted_idx]
                        smoothed = uniform_filter1d(sorted_stiff, size=min(5, len(stiffness)//2))
                        ax2.plot(sorted_x, smoothed, linestyle='-', linewidth=2,
                                color=colors[i], alpha=0.9, label=f'Folder {folder}')
            
            ax2.set_xlabel(x_label, fontsize=14, fontweight='bold')
            ax2.set_ylabel('Stiffness (N/mm)', fontsize=14, fontweight='bold')
            ax2.set_title('Stiffness Trends by Folder', fontsize=16, fontweight='bold')
            ax2.grid(alpha=0.3)
            ax2.legend(loc='best', fontsize=10)
        
        plt.tight_layout()
        output_path = output_dir / f"{timestamp}_stiffness_scatter.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"  ✓ Stiffness scatter plot saved: {output_path.name}")
    
    def _plot_work_of_adhesion_by_folder(self, df, output_dir, timestamp, work_col='work_of_adhesion_mJ'):
        """Plot work of adhesion comparison"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        
        folders = sorted(df['folder'].unique(), key=lambda x: int(x))
        
        mean_work = []
        median_work = []
        sem_work = []
        
        for folder in folders:
            folder_data = df[df['folder'] == folder][work_col]
            folder_data = folder_data[folder_data > 0]
            
            if len(folder_data) > 0:
                mean_work.append(folder_data.mean())
                median_work.append(folder_data.median())
                sem_work.append(folder_data.sem())
            else:
                mean_work.append(0)
                median_work.append(0)
                sem_work.append(0)
        
        x = np.arange(len(folders))
        
        # Mean
        ax1.bar(x, mean_work, yerr=sem_work, capsize=5, alpha=0.7, color='purple', edgecolor='black')
        ax1.set_xlabel('Folder Number', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Work of Adhesion (J)', fontsize=14, fontweight='bold')
        ax1.set_title('Mean Work of Adhesion by Folder', fontsize=16, fontweight='bold')
        ax1.set_xticks(x)
        ax1.set_xticklabels(folders)
        ax1.grid(alpha=0.3)
        
        # Median
        ax2.bar(x, median_work, alpha=0.7, color='teal', edgecolor='black')
        ax2.set_xlabel('Folder Number', fontsize=14, fontweight='bold')
        ax2.set_ylabel('Work of Adhesion (J)', fontsize=14, fontweight='bold')
        ax2.set_title('Median Work of Adhesion by Folder', fontsize=16, fontweight='bold')
        ax2.set_xticks(x)
        ax2.set_xticklabels(folders)
        ax2.grid(alpha=0.3)
        
        plt.tight_layout()
        output_path = output_dir / f"{timestamp}_work_of_adhesion_comparison.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"  ✓ Work of adhesion comparison saved: {output_path.name}")
    
    def _plot_two_regime_stiffness(self, df, output_dir, timestamp):
        """Plot two-regime stiffness analysis"""
        # Check if two-regime detection column exists
        if 'two_regime_detected' not in df.columns:
            print("  Warning: No two-regime stiffness data available")
            return
        
        # Filter for layers with two-regime detection
        two_regime_df = df[df['two_regime_detected'] == True].copy()
        
        if len(two_regime_df) == 0:
            return
        
        print(f"\n  Analyzing two-regime stiffness ({len(two_regime_df)} layers detected)")
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        
        folders = sorted(two_regime_df['folder'].unique(), key=lambda x: int(x))
        colors = plt.cm.viridis(np.linspace(0, 1, len(folders)))
        
        # Determine if we have radius data
        use_radius = 'radius_mm' in two_regime_df.columns and two_regime_df['radius_mm'].notna().any()
        x_label = 'Contact Radius (mm)' if use_radius else 'Layer Number (Increasing Radius)'
        
        # Subplot 1: Radius vs Stiffness with solid (peel) and dotted (start) lines
        for i, folder in enumerate(folders):
            folder_data = two_regime_df[two_regime_df['folder'] == folder]
            
            if len(folder_data) > 0:
                if use_radius:
                    x_values = folder_data['radius_mm'].values
                else:
                    x_values = folder_data['layer_number'].values
                regime1_stiff = folder_data['regime1_stiffness_N_per_mm'].values  # Start (low)
                regime2_stiff = folder_data['regime2_stiffness_N_per_mm'].values  # Peel (high)
                
                # Dotted line for low stiffness (start)
                ax1.plot(x_values, regime1_stiff, linestyle=':', linewidth=2, 
                        color=colors[i], alpha=0.7, label=f'Folder {folder} - Start')
                
                # Solid line for high stiffness (peel)
                ax1.plot(x_values, regime2_stiff, linestyle='-', linewidth=2.5, 
                        color=colors[i], alpha=0.9, label=f'Folder {folder} - Peel')
        
        ax1.set_xlabel(x_label, fontsize=14, fontweight='bold')
        ax1.set_ylabel('Stiffness (N/mm)', fontsize=14, fontweight='bold')
        ax1.set_title('Two-Regime Stiffness: Solid=Peel, Dotted=Start', fontsize=16, fontweight='bold')
        ax1.grid(alpha=0.3)
        ax1.legend(loc='best', fontsize=9, ncol=2)
        
        # Stiffness ratio distribution
        ax2.hist(two_regime_df['stiffness_ratio'], bins=20, alpha=0.7, color='steelblue', edgecolor='black')
        ax2.set_xlabel('Stiffness Ratio (Regime 2 / Regime 1)', fontsize=14, fontweight='bold')
        ax2.set_ylabel('Count', fontsize=14, fontweight='bold')
        ax2.set_title('Stiffness Ratio Distribution', fontsize=16, fontweight='bold')
        ax2.grid(alpha=0.3)
        
        # Transition position distribution
        ax3.hist(two_regime_df['transition_position_um'], bins=20, alpha=0.7, color='coral', edgecolor='black')
        ax3.set_xlabel('Transition Position (μm)', fontsize=14, fontweight='bold')
        ax3.set_ylabel('Count', fontsize=14, fontweight='bold')
        ax3.set_title('Stiffness Transition Position Distribution', fontsize=16, fontweight='bold')
        ax3.grid(alpha=0.3)
        
        # Regime 1 vs Regime 2 scatter
        ax4.scatter(two_regime_df['regime1_stiffness_N_per_mm'], 
                   two_regime_df['regime2_stiffness_N_per_mm'],
                   alpha=0.6, s=50, c=two_regime_df['folder'].astype(int), cmap='viridis')
        ax4.set_xlabel('Regime 1 Stiffness (N/mm)', fontsize=14, fontweight='bold')
        ax4.set_ylabel('Regime 2 Stiffness (N/mm)', fontsize=14, fontweight='bold')
        ax4.set_title('Regime 1 vs Regime 2 Stiffness', fontsize=16, fontweight='bold')
        ax4.grid(alpha=0.3)
        
        # Add diagonal line
        lims = [
            np.min([ax4.get_xlim(), ax4.get_ylim()]),
            np.max([ax4.get_xlim(), ax4.get_ylim()]),
        ]
        ax4.plot(lims, lims, 'k--', alpha=0.3, zorder=0)
        
        plt.tight_layout()
        output_path = output_dir / f"{timestamp}_two_regime_stiffness_analysis.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"  ✓ Two-regime stiffness analysis saved: {output_path.name}")


def main():
    """Main execution function"""
    import sys
    
    # Check for --skip-individual flag
    skip_individual = '--skip-individual' in sys.argv
    
    # TEMPO Picker directory
    tempo_picker_dir = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\TEMPO Picker")
    
    # Initialize processor
    processor = TEMPOPickerProcessor(
        base_directory=tempo_picker_dir,
        skip_individual_plots=skip_individual
    )
    
    # Process all folders
    results = processor.process_all_folders()
    
    # Export master CSV
    processor.export_master_csv()
    
    # Generate master plots (mean, median, log-log)
    processor.generate_master_plots()
    
    # Perform scaling analysis
    processor.perform_scaling_analysis()
    
    print(f"\n{'='*70}")
    print(f"TEMPO Picker Processing Complete!")
    print(f"{'='*70}")
    print(f"Total layers processed: {len(results)}")
    print(f"\nResults saved to: {tempo_picker_dir}")
    print(f"  - Master CSV: MASTER_all_metrics.csv")
    print(f"  - Master Plots: MASTER_plots/")
    print(f"    • Mean plots/ (with SEM)")
    print(f"    • Median plots/ (with MAD)")
    print(f"    • Log-Log plots/ (power law)")
    print(f"    • Scaling_Analysis/ (CSV + plots)")
    print(f"  - Individual plots: [folder]/plots/[timestamp]/")


if __name__ == "__main__":
    main()
