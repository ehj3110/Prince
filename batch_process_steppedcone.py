"""
Batch processor for SteppedCone adhesion data - Area-based analysis
Processes autolog files from SteppedCone tests and generates area-based plots
"""

import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.legend_handler import HandlerTuple
import sys

# Add support_modules and post-processing to path
sys.path.insert(0, str(Path(__file__).parent / 'support_modules'))
sys.path.insert(0, str(Path(__file__).parent / 'post-processing'))
from adhesion_metrics_calculator import AdhesionMetricsCalculator
from analysis_plotter import AnalysisPlotter
from RawData_Processor import RawDataProcessor


class SteppedConeBatchProcessor:
    """
    Batch processor for SteppedCone adhesion tests with area-based analysis
    """
    
    def __init__(self, data_directory, area_mapping_file, output_directory=None):
        """
        Initialize the processor
        
        Args:
            data_directory: Path to the directory containing SteppedCone test folders
            area_mapping_file: Path to LayerToArea.txt file
            output_directory: Directory to save outputs (defaults to data_directory)
        """
        self.data_directory = Path(data_directory)
        self.area_mapping_file = Path(area_mapping_file)
        self.output_directory = Path(output_directory) if output_directory else self.data_directory
        
        # Load area mapping
        self.area_map = self._load_area_mapping()
        
        # Initialize calculator, plotter, and processor
        self.calculator = AdhesionMetricsCalculator(
            median_kernel=5,
            savgol_window=9,
            savgol_order=2
        )
        self.plotter = AnalysisPlotter(figure_size=(16, 12), dpi=150)
        self.processor = RawDataProcessor(self.calculator, self.plotter)
        
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
        Parse the folder name to extract fluid type and gap
        
        Args:
            folder_name: Name of the folder (e.g., '2p5PEO_1mm_SteppedCone_BPAGDA')
            
        Returns:
            Tuple of (fluid_type, gap_mm)
        """
        parts = folder_name.split('_')
        
        # Extract fluid type (e.g., '2p5PEO')
        fluid_type = parts[0]
        
        # Extract gap (e.g., '1mm')
        gap_str = parts[1]
        gap_mm = float(gap_str.replace('mm', ''))
        
        return fluid_type, gap_mm
    
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
        fluid_type, gap_mm = self.parse_folder_name(folder_name)
        condition_label = f"{fluid_type}_{int(gap_mm)}mm"
        
        print(f"  Fluid Type: {fluid_type}")
        print(f"  Gap: {gap_mm} mm")
        
        # Create plots directory for this folder
        plots_dir = folder_path / 'plots'
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
                
                # Process CSV using RawData_Processor (WITH plot generation)
                # Create title with area information
                plot_title = f"{condition_label} - Layers {layer_num}-{layer_num+5} (Area: {area_mm2:.2f} mm²)"
                plot_save_path = plots_dir / f"{file.stem}_analysis.png"
                
                layers = self.processor.process_csv(
                    csv_filepath=str(file),
                    title=plot_title,
                    save_path=str(plot_save_path)  # Save individual plots
                )
                
                print(f"    Saved plot: {plot_save_path.name}")
                
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
                            'area_mm2': area_mm2,
                            'peak_force_N': layer_obj.get('peak_force', None),
                            'work_of_adhesion_mJ': layer_obj.get('work_of_adhesion_mJ', None),
                            'peel_distance_mm': metrics_dict.get('total_peel_distance', None),
                            'peak_retraction_force_N': metrics_dict.get('peak_force_corrected', None),
                            'distance_to_peak_mm': metrics_dict.get('pre_initiation_distance', None),
                            'propagation_distance_mm': metrics_dict.get('propagation_distance', None)
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
        
        # Find all SteppedCone folders
        folders = [f for f in self.data_directory.iterdir() 
                  if f.is_dir() and 'SteppedCone' in f.name]
        
        print(f"\nFound {len(folders)} SteppedCone folders:")
        for folder in folders:
            print(f"  - {folder.name}")
        
        # Process each folder
        for folder in folders:
            folder_results = self.process_single_folder(folder)
            self.all_results.extend(folder_results)
        
        print(f"\n{'='*60}")
        print(f"Processing Complete")
        print(f"Total layers processed: {len(self.all_results)}")
        print(f"{'='*60}")
        
        return self.all_results
    
    def save_master_csv(self):
        """Save all results to a master CSV file"""
        if not self.all_results:
            print("No results to save!")
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame(self.all_results)
        
        # Sort by condition and area
        df = df.sort_values(['condition_label', 'area_mm2'])
        
        # Save to CSV
        output_file = self.output_directory / 'MASTER_steppedcone_metrics.csv'
        df.to_csv(output_file, index=False)
        
        print(f"\nSaved master CSV to: {output_file}")
        print(f"Total rows: {len(df)}")
        
        # Print summary statistics
        print("\n" + "="*60)
        print("Summary by Condition:")
        print("="*60)
        for condition in df['condition_label'].unique():
            cond_data = df[df['condition_label'] == condition]
            print(f"\n{condition}:")
            print(f"  Layers: {len(cond_data)}")
            print(f"  Area range: {cond_data['area_mm2'].min():.2f} - {cond_data['area_mm2'].max():.2f} mm²")
            print(f"  Peak Force: {cond_data['peak_force_N'].mean():.4f} ± {cond_data['peak_force_N'].std():.4f} N")
            print(f"  Work of Adhesion: {cond_data['work_of_adhesion_mJ'].mean():.4f} ± {cond_data['work_of_adhesion_mJ'].std():.4f} mJ")
        
        return df
    
    def generate_master_plots(self):
        """Generate all master plots"""
        if not self.all_results:
            print("No results to plot!")
            return
        
        df = pd.DataFrame(self.all_results)
        
        # Take absolute value of peel distance (convert negative to positive)
        df['peel_distance_mm'] = df['peel_distance_mm'].abs()
        
        # Define high-contrast color map for conditions (matching V17Tests)
        color_map = {
            '2p5PEO_1mm': '#0000FF',    # Pure Blue (matching V17Tests 2p5PEO_1mm)
            '2p5PEO_5mm': '#FF6600',    # Bright Orange (matching V17Tests 2p5PEO_5mm)
        }
        
        print("\n" + "="*60)
        print("Generating Master Plots")
        print("="*60)
        
        # Generate area-based plots
        self.plot_master_area_analysis_with_errorbars(df, color_map)
        self.plot_master_distance_analysis_with_errorbars(df, color_map)
        
        print("\nAll plots generated successfully!")
    
    def plot_master_area_analysis_with_errorbars(self, df, color_map):
        """
        Create master plot showing all metrics vs area with shaded error regions
        2x2 subplot layout
        """
        print("\n  Creating area analysis plot (with shaded error regions)...")
        
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('Adhesion Metrics vs Contact Area (SteppedCone Tests)', 
                    fontsize=16, fontweight='bold', y=0.995)
        
        # Define metrics and their properties
        metrics = [
            ('peak_force_N', 'Peak Force (N)', axes[0, 0]),
            ('work_of_adhesion_mJ', 'Work of Adhesion (mJ)', axes[0, 1]),
            ('peel_distance_mm', 'Peel Distance (mm)', axes[1, 0]),
            ('peak_retraction_force_N', 'Peak Retraction Force (N)', axes[1, 1])
        ]
        
        # Get unique conditions
        conditions = sorted(df['condition_label'].unique())
        
        for condition in conditions:
            condition_data = df[df['condition_label'] == condition]
            color = color_map.get(condition, '#000000')
            
            # Determine line style based on fluid type
            if '2p5PEO' in condition:
                linestyle = '-'  # Solid for 2p5PEO
            elif 'Water' in condition:
                linestyle = '--'  # Dashed for Water
            elif 'USW' in condition:
                linestyle = ':'  # Dotted for USW
            else:
                linestyle = '-'
            
            # Plot each metric
            for metric_col, metric_label, ax in metrics:
                # Group by area and calculate mean and SEM
                grouped = condition_data.groupby('area_mm2')[metric_col].agg(['mean', 'sem'])
                areas = grouped.index.values
                means = grouped['mean'].values
                sems = grouped['sem'].values
                
                # Plot mean line with markers
                ax.plot(areas, means, 'o', color=color, markersize=3, alpha=0.7, label=condition)
                
                # Add shaded error region (mean ± SEM)
                ax.fill_between(areas, means - sems, means + sems, 
                               color=color, alpha=0.2)
                
                # Add polynomial trendline (degree 2)
                if len(areas) > 2:
                    z = np.polyfit(areas, means, 2)
                    p = np.poly1d(z)
                    area_smooth = np.linspace(areas.min(), areas.max(), 100)
                    ax.plot(area_smooth, p(area_smooth), 
                           color=color, linestyle=linestyle, linewidth=2, alpha=0.8)
                
                # Set labels and grid
                ax.set_xlabel('Contact Area (mm²)', fontsize=13, fontweight='bold')
                ax.set_ylabel(metric_label, fontsize=13, fontweight='bold')
                ax.grid(True, alpha=0.3, linestyle='--')
                ax.tick_params(labelsize=11)
                
                # Add legend to each subplot
                ax.legend(loc='best', fontsize=10, framealpha=0.9)
        
        plt.tight_layout()
        
        # Save figure
        output_file = self.output_directory / 'MASTER_area_analysis.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"    Saved: {output_file}")
        
        plt.close()
    
    def plot_master_distance_analysis_with_errorbars(self, df, color_map):
        """
        Create master plot showing distance metrics vs area with shaded error regions
        1x2 subplot layout
        """
        print("\n  Creating distance analysis plot (with shaded error regions)...")
        
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        fig.suptitle('Distance Metrics vs Contact Area (SteppedCone Tests)', 
                    fontsize=16, fontweight='bold', y=1.00)
        
        # Define metrics and their properties
        metrics = [
            ('distance_to_peak_mm', 'Distance to Peak (mm)', axes[0]),
            ('propagation_distance_mm', 'Propagation Distance (mm)', axes[1])
        ]
        
        # Get unique conditions
        conditions = sorted(df['condition_label'].unique())
        
        for condition in conditions:
            condition_data = df[df['condition_label'] == condition]
            color = color_map.get(condition, '#000000')
            
            # Determine line style based on fluid type
            if '2p5PEO' in condition:
                linestyle = '-'  # Solid for 2p5PEO
            elif 'Water' in condition:
                linestyle = '--'  # Dashed for Water
            elif 'USW' in condition:
                linestyle = ':'  # Dotted for USW
            else:
                linestyle = '-'
            
            # Plot each metric
            for metric_col, metric_label, ax in metrics:
                # Group by area and calculate mean and SEM
                grouped = condition_data.groupby('area_mm2')[metric_col].agg(['mean', 'sem'])
                areas = grouped.index.values
                means = grouped['mean'].values
                sems = grouped['sem'].values
                
                # Plot mean line with markers
                ax.plot(areas, means, 'o', color=color, markersize=3, alpha=0.7, label=condition)
                
                # Add shaded error region (mean ± SEM)
                ax.fill_between(areas, means - sems, means + sems, 
                               color=color, alpha=0.2)
                
                # Add polynomial trendline (degree 2)
                if len(areas) > 2:
                    z = np.polyfit(areas, means, 2)
                    p = np.poly1d(z)
                    area_smooth = np.linspace(areas.min(), areas.max(), 100)
                    ax.plot(area_smooth, p(area_smooth), 
                           color=color, linestyle=linestyle, linewidth=2, alpha=0.8)
                
                # Set labels and grid
                ax.set_xlabel('Contact Area (mm²)', fontsize=13, fontweight='bold')
                ax.set_ylabel(metric_label, fontsize=13, fontweight='bold')
                ax.grid(True, alpha=0.3, linestyle='--')
                ax.tick_params(labelsize=11)
                
                # Add legend to each subplot
                ax.legend(loc='best', fontsize=10, framealpha=0.9)
        
        plt.tight_layout()
        
        # Save figure
        output_file = self.output_directory / 'MASTER_area_distance_analysis.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"    Saved: {output_file}")
        
        plt.close()


def main():
    """Main execution function"""
    
    # Define paths
    data_directory = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests")
    area_mapping_file = data_directory / "LayerToArea.txt"
    
    # Create processor
    processor = SteppedConeBatchProcessor(
        data_directory=data_directory,
        area_mapping_file=area_mapping_file,
        output_directory=data_directory
    )
    
    # Process all folders
    processor.process_all_folders()
    
    # Save master CSV
    master_df = processor.save_master_csv()
    
    # Generate plots
    processor.generate_master_plots()
    
    print("\n" + "="*60)
    print("SteppedCone Batch Processing Complete!")
    print("="*60)


if __name__ == "__main__":
    main()
