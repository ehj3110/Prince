"""
V4 Data Batch Processor for SteppedCone Tests
=============================================

Processes V4 adhesion test data with new naming convention:
MembraneType_Height_TankType_Resin_Model_Speed

Features:
- Handles both Cone (LayerToArea.txt) and Pyramid (automated_work_of_adhesion area column)
- Generates individual plots for each autolog file
- Creates master plots with:
  * Contact area as X-axis
  * Contact area ratio (part area / total membrane area) as X-axis
- Proper legend labels for membrane types

Usage:
    python batch_process_v4_data.py

Author: Cheng Sun Lab Team
Date: November 18, 2025
"""

import matplotlib
matplotlib.use('Agg')  # Force non-interactive backend

import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import sys
import re
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# Add support modules to path
sys.path.insert(0, str(Path(__file__).parent / 'support_modules'))
sys.path.insert(0, str(Path(__file__).parent / 'post-processing'))
from adhesion_metrics_calculator import AdhesionMetricsCalculator
from RawData_Processor import RawDataProcessor
from analysis_plotter import AnalysisPlotter
from master_plotter import MasterPlotter


class V4FolderInfo:
    """Stores parsed information about a V4 test folder"""
    
    def __init__(self, folder_path: Path):
        self.folder_path = folder_path
        self.folder_name = folder_path.name
        
        # Parse folder name - handle two formats:
        # Format A: MembraneType_Height_TankType_Resin_Model_Speed (pyramids)
        # Format B: MembraneType_Height_TankType_Model_Resin_Speed (cones)
        parts = self.folder_name.split('_')
        
        # Extract components (always same)
        self.membrane_type = parts[0] if len(parts) > 0 else "Unknown"
        self.height = parts[1] if len(parts) > 1 else "Unknown"
        self.tank_type = parts[2] if len(parts) > 2 else "Unknown"
        
        # Determine which format by checking if part[3] is "Cone" or "Pyramid"
        if len(parts) > 3 and parts[3] in ["Cone", "Pyramid"]:
            # Format B: Model at index 3, Resin at index 4
            self.model = parts[3]
            self.resin = parts[4] if len(parts) > 4 else "Unknown"
            self.speed = parts[5] if len(parts) > 5 else "Unknown"
        else:
            # Format A: Resin at index 3, Model at index 4
            self.resin = parts[3] if len(parts) > 3 else "Unknown"
            self.model = parts[4] if len(parts) > 4 else "Unknown"
            self.speed = parts[5] if len(parts) > 5 else "Unknown"
        
        # Format membrane label for plots
        self.membrane_label = self._format_membrane_label()
        
        # Determine tank total area (mm²)
        self.total_membrane_area = self._get_tank_area()
        
        # Check if Cone or Pyramid model
        self.is_cone = "Cone" in self.model
        self.is_pyramid = "Pyramid" in self.model
        
    def _format_membrane_label(self) -> str:
        """Format membrane type for plot legends"""
        if "100umPDMS" in self.membrane_type or "100um" in self.membrane_type:
            return "PDMS, 100um"
        elif "200umPDMS" in self.membrane_type or "200um" in self.membrane_type:
            return "PDMS, 200um"
        elif "ACF" in self.membrane_type:
            return "ACF"
        else:
            return self.membrane_type
    
    def _get_tank_area(self) -> float:
        """Get total membrane area based on tank type"""
        if "V19" in self.tank_type:
            return 31.75 * 19.05  # 604.8375 mm²
        elif "V20" in self.tank_type:
            return 21.64 * 13.522  # 292.65608 mm²
        elif "V22" in self.tank_type:
            import math
            return math.pi * 6.765**2  # 143.78 mm² (circular tank, r=6.765mm)
        else:
            # Default fallback
            return 600.0
    
    def __str__(self):
        return (f"V4Folder({self.membrane_label}, {self.height}, {self.tank_type}, "
                f"{self.model}, {self.speed} µm/s)")


class V4BatchProcessor:
    """Batch processor for V4 SteppedCone test data"""
    
    def __init__(self, v4_directory: str):
        """
        Initialize processor
        
        Args:
            v4_directory: Path to V4 main directory
        """
        self.v4_dir = Path(v4_directory)
        
        if not self.v4_dir.exists():
            raise FileNotFoundError(f"V4 directory not found: {self.v4_dir}")
        
        # Check for LayerToArea.txt
        self.layer_to_area_file = self.v4_dir / "LayerToArea.txt"
        print(f"DEBUG: Looking for LayerToArea.txt at: {self.layer_to_area_file}")
        print(f"DEBUG: File exists: {self.layer_to_area_file.exists()}")
        if self.layer_to_area_file.exists():
            self.layer_to_area_map = self._load_layer_to_area()
            print(f"DEBUG: Loaded {len(self.layer_to_area_map)} layer-to-area mappings")
        else:
            self.layer_to_area_map = {}
            print("WARNING: LayerToArea.txt not found. Will use pyramid area data only.")
        
        # Initialize processors
        self.calculator = AdhesionMetricsCalculator()
        self.processor = RawDataProcessor(self.calculator)
        self.plotter = AnalysisPlotter(figure_size=(16, 12), dpi=150)
        
        # Storage for all results
        self.all_results = []
        
    def _load_layer_to_area(self) -> Dict[int, float]:
        """Load LayerToArea.txt mapping"""
        print(f"Loading LayerToArea.txt from {self.layer_to_area_file}")
        df = pd.read_csv(self.layer_to_area_file, sep='\t')
        area_map = dict(zip(df['Layer_Number'], df['Area']))
        print(f"  Loaded {len(area_map)} layer-to-area mappings")
        return area_map
    
    def find_test_folders(self) -> List[V4FolderInfo]:
        """Find all test folders in V4 directory"""
        folders = []
        # Sort items by name for consistent processing order
        for item in sorted(self.v4_dir.iterdir(), key=lambda x: x.name):
            if item.is_dir():
                folder_info = V4FolderInfo(item)
                folders.append(folder_info)
                print(f"Found: {folder_info}")
        
        print(f"\nTotal folders found: {len(folders)}")
        print("Folders will be processed in this order:")
        for i, f in enumerate(folders, 1):
            print(f"  {i}. {f.folder_name}")
        return folders
    
    def process_folder(self, folder_info: V4FolderInfo) -> List[Dict]:
        """
        Process a single test folder
        
        Args:
            folder_info: V4FolderInfo object
            
        Returns:
            List of result dictionaries with metrics and metadata
        """
        print(f"\n{'='*80}")
        print(f"Processing: {folder_info.folder_name}")
        print(f"{'='*80}")
        
        # Find autolog files (exclude autolog_metrics.csv)
        autolog_files = [f for f in sorted(folder_info.folder_path.glob("autolog_*.csv")) 
                        if f.name != "autolog_metrics.csv"]
        print(f"Found {len(autolog_files)} autolog files")
        
        if len(autolog_files) == 0:
            print("  No autolog files found, skipping...")
            return []
        
        # Load area data from appropriate CSV file
        automated_data = None
        
        # For Pyramid folders: Use automated_work_of_adhesion.csv (has Cross_Sectional_Area_mm2)
        if folder_info.is_pyramid:
            automated_csv = folder_info.folder_path / "automated_work_of_adhesion.csv"
            if automated_csv.exists():
                print(f"Loading automated_work_of_adhesion.csv (Pyramid data)")
                automated_data = pd.read_csv(automated_csv)
                if 'Cross_Sectional_Area_mm2' in automated_data.columns:
                    print(f"  Found Cross_Sectional_Area_mm2 column")
        
        # For Cone folders: We'll use LayerToArea.txt mapping (loaded in __init__)
        
        # Create timestamped plots subdirectory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        plots_dir = folder_info.folder_path / "plots" / f"plots_{timestamp}"
        plots_dir.mkdir(parents=True, exist_ok=True)
        print(f"  Saving plots to: {plots_dir.name}")
        
        folder_results = []
        
        # Process each autolog file
        for autolog_file in autolog_files:
            print(f"\n  Processing: {autolog_file.name}")
            
            # Load raw data for plotting
            df = pd.read_csv(autolog_file)
            time_data = df['Elapsed Time (s)'].to_numpy()
            force_data = df['Force (N)'].to_numpy()
            
            # Apply smoothing
            smoothed_force = self.calculator._apply_smoothing(force_data)
            
            # Process to get layers
            layers = self.processor.process_csv(str(autolog_file))
            
            if not layers:
                print(f"    No layers detected, skipping...")
                continue
            
            print(f"    Detected {len(layers)} layers")
            
            # Generate individual plot
            plot_path = plots_dir / f"{autolog_file.stem}_analysis.png"
            self.plotter.create_plot(
                time_data=time_data,
                force_data=force_data,
                smoothed_force=smoothed_force,
                layers=layers,
                title=f"{folder_info.folder_name} - {autolog_file.stem}",
                save_path=str(plot_path)
            )
            print(f"    Saved plot: {plot_path.name}")
            
            # Extract metrics and add metadata
            for layer in layers:
                layer_num = layer['number']
                metrics = layer['metrics']
                
                # Determine contact area
                contact_area = None
                if folder_info.is_cone:
                    # Cone model: Use LayerToArea.txt
                    print(f"    DEBUG: Checking cone layer {layer_num}, map has {len(self.layer_to_area_map)} entries")
                    if layer_num in self.layer_to_area_map:
                        contact_area = self.layer_to_area_map[layer_num]
                        print(f"    DEBUG: Found area={contact_area} for layer {layer_num}")
                    else:
                        print(f"    WARNING: Layer {layer_num} not found in LayerToArea.txt (map keys: {list(self.layer_to_area_map.keys())[:5]}...), skipping...")
                        continue
                elif folder_info.is_pyramid and automated_data is not None:
                    # Pyramid model: Use Cross_Sectional_Area_mm2 from automated CSV
                    matching_rows = automated_data[automated_data['Layer_Number'] == layer_num]
                    if len(matching_rows) > 0:
                        contact_area = matching_rows.iloc[0]['Cross_Sectional_Area_mm2']
                    else:
                        print(f"    WARNING: Layer {layer_num} not found in automated CSV, skipping...")
                        continue
                else:
                    print(f"    WARNING: No area data source available for Layer {layer_num}, skipping...")
                    continue
                
                # Calculate area ratio
                area_ratio = contact_area / folder_info.total_membrane_area
                
                # Create result dictionary (standard format for MasterPlotter)
                result = {
                    # Metadata
                    'folder': folder_info.folder_name,
                    'condition_label': folder_info.membrane_label,  # For MasterPlotter grouping
                    'membrane_type': folder_info.membrane_label,
                    'height': folder_info.height,
                    'tank_type': folder_info.tank_type,
                    'resin': folder_info.resin,
                    'model': folder_info.model,
                    'speed_um_s': int(folder_info.speed) if folder_info.speed.isdigit() else 0,
                    'layer_number': layer_num,
                    
                    # Area data (MasterPlotter expects 'area_mm2')
                    'area_mm2': contact_area,
                    'contact_area_mm2': contact_area,
                    'total_membrane_area_mm2': folder_info.total_membrane_area,
                    'area_ratio': area_ratio,
                    
                    # Key metrics (standard MasterPlotter names)
                    'peak_force_N': metrics['peak_force_corrected'],
                    'peak_force_corrected_N': metrics['peak_force_corrected'],
                    'baseline_force_N': metrics['baseline_force'],
                    'work_of_adhesion_mJ': metrics['work_of_adhesion_corrected_mJ'],
                    
                    # Time metrics (standard names)
                    'pre_initiation_duration_s': metrics['pre_initiation_duration'],
                    'propagation_duration_s': metrics['propagation_duration'],
                    'total_peel_time_s': metrics['total_peel_duration'],  # Standard name
                    'total_peel_duration_s': metrics['total_peel_duration'],
                    
                    # Distance metrics (standard names)
                    'distance_to_peak_mm': metrics['pre_initiation_distance'],
                    'pre_initiation_distance_mm': metrics['pre_initiation_distance'],
                    'propagation_distance_mm': metrics['propagation_distance'],
                    'peel_distance_mm': metrics['total_peel_distance'],  # Standard name
                    'total_peel_distance_mm': metrics['total_peel_distance'],
                    
                    # Retraction force
                    'peak_retraction_force_N': layer.get('peak_retraction_force', 0),
                    
                    # Stiffness (if available)
                    'effective_stiffness_N_per_mm': metrics.get('effective_stiffness_N_per_mm', 0),
                    'stiffness_r_squared': metrics.get('stiffness_r_squared', 0),
                }
                
                folder_results.append(result)
        
        print(f"\n  Processed {len(folder_results)} layer measurements")
        return folder_results
    
    def process_all_folders(self):
        """Process all folders in V4 directory"""
        print("\n" + "="*80)
        print("V4 BATCH PROCESSOR - STARTING")
        print("="*80)
        
        # Find all test folders
        folders = self.find_test_folders()
        
        if len(folders) == 0:
            print("ERROR: No test folders found!")
            return
        
        # Process each folder
        for folder_info in folders:
            folder_results = self.process_folder(folder_info)
            self.all_results.extend(folder_results)
        
        print("\n" + "="*80)
        print(f"PROCESSING COMPLETE - {len(self.all_results)} total measurements")
        print("="*80)
        
        # Save combined CSV
        self._save_master_csv()
        
        # Generate master plots
        self._generate_master_plots()
    
    def _save_master_csv(self):
        """Save all results to master CSV"""
        if not self.all_results:
            print("No results to save!")
            return
        
        df = pd.DataFrame(self.all_results)
        csv_path = self.v4_dir / "MASTER_V4_all_metrics.csv"
        df.to_csv(csv_path, index=False)
        print(f"\nSaved master CSV: {csv_path}")
        print(f"  Total rows: {len(df)}")
    
    def _generate_master_plots(self):
        """Generate master comparison plots using MasterPlotter standard format"""
        if not self.all_results:
            print("No results to plot!")
            return
        
        print("\n" + "="*80)
        print("GENERATING MASTER PLOTS")
        print("="*80)
        
        df = pd.DataFrame(self.all_results)
        
        # Create MasterPlotter instance
        master_plotter = MasterPlotter(output_directory=self.v4_dir, dpi=300)
        
        # Use the standard plotting function (same as V3)
        # This generates the 4 standard plots:
        # 1. MASTER_area_analysis.png (Force, Work, Distance, Retraction Force)
        # 2. MASTER_distance_analysis.png (detailed distance breakdown)
        # 3. MASTER_stiffness_analysis.png
        # 4. MASTER_Modified_area_analysis.png (with peel time)
        master_plotter.generate_standard_plots(df)
        
        print("\nMaster plots complete!")
    
    def _create_area_plots(self, df: pd.DataFrame, x_col: str, 
                          x_label: str, filename_suffix: str):
        """
        Create master plots with specified X-axis variable
        
        Args:
            df: DataFrame with all results
            x_col: Column name to use for X-axis ('contact_area_mm2' or 'area_ratio')
            x_label: Label for X-axis
            filename_suffix: Suffix for output filenames
        """
        print(f"\nCreating plots with X-axis: {x_label}")
        
        # Group by membrane type and area
        grouped = df.groupby(['membrane_type', x_col]).agg({
            'peak_force_corrected_N': ['mean', 'std', 'count'],
            'work_of_adhesion_mJ': ['mean', 'std', 'count'],
            'total_peel_distance_mm': ['mean', 'std', 'count'],
            'peak_retraction_force_N': ['mean', 'std', 'count']
        }).reset_index()
        
        # Flatten column names
        grouped.columns = ['_'.join(col).strip('_') for col in grouped.columns.values]
        
        # Create figure with 4 subplots
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(f'V4 Adhesion Test Results vs {x_label}', 
                    fontsize=16, fontweight='bold')
        
        # Plot 1: Peak Force
        ax1 = axes[0, 0]
        self._plot_metric(ax1, grouped, x_col, 'peak_force_corrected_N',
                         'Peak Force (N)', x_label)
        
        # Plot 2: Work of Adhesion
        ax2 = axes[0, 1]
        self._plot_metric(ax2, grouped, x_col, 'work_of_adhesion_mJ',
                         'Work of Adhesion (mJ)', x_label)
        
        # Plot 3: Peel Distance
        ax3 = axes[1, 0]
        self._plot_metric(ax3, grouped, x_col, 'total_peel_distance_mm',
                         'Total Peel Distance (mm)', x_label)
        
        # Plot 4: Retraction Force
        ax4 = axes[1, 1]
        self._plot_metric(ax4, grouped, x_col, 'peak_retraction_force_N',
                         'Peak Retraction Force (N)', x_label)
        
        plt.tight_layout()
        
        # Save plot
        plot_path = self.v4_dir / f"MASTER_V4_analysis{filename_suffix}.png"
        fig.savefig(plot_path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        print(f"  Saved: {plot_path.name}")
    
    def _plot_metric(self, ax, grouped_df, x_col, metric_col, 
                    y_label, x_label):
        """Plot a single metric with error bars for each membrane type"""
        
        # Define colors for each membrane type
        colors = {
            'PDMS, 100um': '#1f77b4',  # Blue
            'PDMS, 200um': '#ff7f0e',  # Orange
            'ACF': '#2ca02c'            # Green
        }
        
        markers = {
            'PDMS, 100um': 'o',
            'PDMS, 200um': 's',
            'ACF': '^'
        }
        
        # Get unique membrane types
        membrane_types = grouped_df['membrane_type'].unique()
        
        for membrane in membrane_types:
            data = grouped_df[grouped_df['membrane_type'] == membrane]
            
            x = data[x_col]
            y_mean = data[f'{metric_col}_mean']
            y_std = data[f'{metric_col}_std']
            n = data[f'{metric_col}_count']
            
            # Calculate SEM (Standard Error of Mean)
            y_sem = y_std / np.sqrt(n)
            
            # Plot with error bars
            ax.errorbar(x, y_mean, yerr=y_sem,
                       label=membrane,
                       color=colors.get(membrane, 'gray'),
                       marker=markers.get(membrane, 'o'),
                       markersize=8,
                       linewidth=2,
                       capsize=5,
                       capthick=2,
                       alpha=0.8)
        
        ax.set_xlabel(x_label, fontsize=12, fontweight='bold')
        ax.set_ylabel(y_label, fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=10, loc='best')
        
        # Set y-axis to start at 0 if all values are positive
        if y_mean.min() >= 0:
            ax.set_ylim(bottom=0)


def main():
    """Main execution function"""
    
    # V4 directory path
    v4_directory = r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V4"
    
    # Initialize processor
    processor = V4BatchProcessor(v4_directory)
    
    # Process all folders
    processor.process_all_folders()
    
    print("\n" + "="*80)
    print("BATCH PROCESSING COMPLETE!")
    print("="*80)
    print(f"\nOutputs saved to: {v4_directory}")
    print("  - Individual plots in each folder's plots/plots_TIMESTAMP/ subdirectories")
    print("  - MASTER_V4_all_metrics.csv")
    print("  - MASTER_V4_force_and_adhesion.png")
    print("  - MASTER_V4_distance_analysis.png")
    print("  - MASTER_V4_time_analysis.png")
    print("  - MASTER_V4_retraction_force.png")
    print("  - MASTER_V4_force_and_adhesion_by_ratio.png (Area Ratio X-axis)")


if __name__ == "__main__":
    main()
