"""
V5 Data Batch Processor for SteppedCone Tests
=============================================

Processes V5 adhesion test data with naming convention:
MembraneType_Height_TankType_Model_Resin_Speed OR
MembraneType_Height_TankType_Resin_Model_Speed

Features:
- Handles cone data with LayerToArea.txt
- Generates individual plots for each autolog file
- Creates master plots
- Treats p1 and p2 print rounds as separate conditions

Usage:
    python batch_process_v5_data.py

Author: Cheng Sun Lab Team
Date: November 26, 2025
"""

import matplotlib
matplotlib.use('Agg')  # Force non-interactive backend

import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
import sys
import math
from datetime import datetime
from typing import Dict, List

# Add support modules to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'support_modules'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'post-processing'))
from adhesion_metrics_calculator import AdhesionMetricsCalculator
from RawData_Processor import RawDataProcessor
from analysis_plotter import AnalysisPlotter
from master_plotter import MasterPlotter


class V5FolderInfo:
    """Stores parsed information about a V5 test folder"""
    
    def __init__(self, folder_path: Path):
        self.folder_path = folder_path
        self.folder_name = folder_path.name
        
        # Parse folder name
        # Examples: 100umPDMS_1mm_V22p1_BPAGDA_Cone_1000
        #          TEMPO_1mm_V22p2_Cone_BPAGDA_1000
        parts = self.folder_name.split('_')
        
        # Extract membrane type
        if parts[0].startswith('100um') or parts[0].startswith('200um'):
            self.membrane_type = f"PDMS, {parts[0][:5]}"  # "PDMS, 100um"
        elif parts[0] == 'TEMPO':
            self.membrane_type = 'TEMPO'
        else:
            self.membrane_type = parts[0]
        
        # Extract other fields
        self.height = parts[1] if len(parts) > 1 else "Unknown"
        
        # Extract tank type (V22p1, V22p2, V22p3)
        self.tank_type = None
        for part in parts:
            if 'V22' in part.upper():
                tank_part = part.upper().replace('V22', 'V22')
                if 'P1' in tank_part:
                    self.tank_type = 'TankV22p1'
                elif 'P2' in tank_part:
                    self.tank_type = 'TankV22p2'
                elif 'P3' in tank_part:
                    self.tank_type = 'TankV22p3'
                else:
                    self.tank_type = 'TankV22'
                break
        
        if not self.tank_type:
            self.tank_type = 'TankV22'
        
        # Find model (Cone/Pyramid)
        self.model = 'Cone'  # Default
        for part in parts:
            if part.lower() == 'cone':
                self.model = 'Cone'
            elif part.lower() == 'pyramid':
                self.model = 'Pyramid'
        
        # Extract material
        self.resin = 'BPAGDA'  # Default
        for part in parts:
            if part.upper() in ['BPAGDA', 'TEMPO']:
                self.resin = part.upper()
        
        # Extract speed
        self.speed = parts[-1] if parts[-1].isdigit() else '1000'
        
        # Format membrane label for plots
        self.membrane_label = self.membrane_type
        
        # Get tank area
        self.total_membrane_area = self._get_tank_area()
        
        # Check model type
        self.is_cone = "Cone" in self.model
        self.is_pyramid = "Pyramid" in self.model
        
    def _get_tank_area(self) -> float:
        """Get total membrane area based on tank type"""
        # All V22 variants use same tank size
        if "V22" in self.tank_type:
            return math.pi * 6.765**2  # 143.78 mm² (circular tank)
        return 143.78  # Default for V5
    
    def __str__(self):
        return (f"V5Folder({self.membrane_label}, {self.height}, {self.tank_type}, "
                f"{self.model}, {self.speed} µm/s)")


class V5BatchProcessor:
    """Batch processor for V5 SteppedCone test data"""
    
    def __init__(self, v5_directory: str):
        """
        Initialize processor
        
        Args:
            v5_directory: Path to V5 main directory
        """
        self.v5_dir = Path(v5_directory)
        
        if not self.v5_dir.exists():
            raise FileNotFoundError(f"V5 directory not found: {self.v5_dir}")
        
        # Load global LayerToArea.txt if it exists
        self.layer_to_area_file = self.v5_dir / "LayerToArea.txt"
        if self.layer_to_area_file.exists():
            self.layer_to_area_map = self._load_layer_to_area(self.layer_to_area_file)
            print(f"Loaded {len(self.layer_to_area_map)} layer-to-area mappings from global LayerToArea.txt")
        else:
            self.layer_to_area_map = {}
            print("No global LayerToArea.txt found, will check individual folders")
        
        # Initialize processors
        self.calculator = AdhesionMetricsCalculator()
        self.processor = RawDataProcessor(self.calculator)
        self.plotter = AnalysisPlotter(figure_size=(16, 12), dpi=150)
        
        # Storage for all results
        self.all_results = []
        
    def _load_layer_to_area(self, file_path: Path) -> Dict[int, float]:
        """Load LayerToArea.txt mapping"""
        print(f"Loading LayerToArea.txt from {file_path}")
        df = pd.read_csv(file_path, sep='\t')
        
        # Handle duplicate layer numbers - keep the last occurrence
        if 'Layer_Number' in df.columns:
            # Check for duplicates
            duplicates = df['Layer_Number'].duplicated()
            if duplicates.any():
                print(f"  WARNING: Found {duplicates.sum()} duplicate layer numbers")
                print(f"  Keeping last occurrence of each duplicate (assuming first is bad data)")
                # Keep last occurrence of each layer number
                df = df.drop_duplicates(subset='Layer_Number', keep='last')
        
        area_map = dict(zip(df['Layer_Number'], df['Area']))
        print(f"  Loaded {len(area_map)} layer-to-area mappings")
        return area_map
    
    def find_test_folders(self) -> List[V5FolderInfo]:
        """Find all test folders in V5 directory"""
        folders = []
        for item in sorted(self.v5_dir.iterdir(), key=lambda x: x.name):
            if item.is_dir() and not item.name.startswith('.'):
                folder_info = V5FolderInfo(item)
                folders.append(folder_info)
                print(f"Found: {folder_info}")
        
        print(f"\nTotal folders found: {len(folders)}")
        return folders
    
    def _get_layer_to_area_for_folder(self, folder_info: V5FolderInfo) -> Dict[int, float]:
        """Get layer-to-area mapping for a specific folder"""
        # Check for folder-specific LayerToArea.txt
        folder_layer_file = folder_info.folder_path / "LayerToArea.txt"
        
        if folder_layer_file.exists():
            print(f"  Using folder-specific LayerToArea.txt")
            return self._load_layer_to_area(folder_layer_file)
        elif self.layer_to_area_map:
            print(f"  Using global LayerToArea.txt")
            return self.layer_to_area_map
        else:
            # Try automated_work_of_adhesion.csv
            automated_csv = folder_info.folder_path / "automated_work_of_adhesion.csv"
            if automated_csv.exists():
                print(f"  Using automated_work_of_adhesion.csv for area data")
                df = pd.read_csv(automated_csv)
                if 'Cross_Sectional_Area_mm2' in df.columns and 'Layer_Number' in df.columns:
                    # Handle duplicates
                    df = df.drop_duplicates(subset='Layer_Number', keep='last')
                    return dict(zip(df['Layer_Number'], df['Cross_Sectional_Area_mm2']))
            
            print(f"  WARNING: No area data source found")
            return {}
    
    def process_folder(self, folder_info: V5FolderInfo) -> List[Dict]:
        """
        Process a single test folder
        
        Args:
            folder_info: V5FolderInfo object
            
        Returns:
            List of result dictionaries with metrics and metadata
        """
        print(f"\n{'='*80}")
        print(f"Processing: {folder_info.folder_name}")
        print(f"{'='*80}")
        
        # Get layer-to-area mapping for this folder
        layer_to_area_map = self._get_layer_to_area_for_folder(folder_info)
        
        if not layer_to_area_map:
            print("  No area mapping available, skipping folder")
            return []
        
        # Find autolog files
        autolog_files = [f for f in sorted(folder_info.folder_path.glob("autolog_*.csv")) 
                        if f.name != "autolog_metrics.csv"]
        print(f"Found {len(autolog_files)} autolog files")
        
        if len(autolog_files) == 0:
            print("  No autolog files found, skipping...")
            return []
        
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
                
                # Get contact area
                if layer_num not in layer_to_area_map:
                    print(f"    WARNING: Layer {layer_num} not in area mapping, skipping")
                    continue
                
                contact_area = layer_to_area_map[layer_num]
                area_ratio = contact_area / folder_info.total_membrane_area
                
                # Create result dictionary (standard format for MasterPlotter)
                result = {
                    # Metadata
                    'folder': folder_info.folder_name,
                    'condition_label': folder_info.membrane_label,
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
                    
                    # Time metrics
                    'pre_initiation_duration_s': metrics['pre_initiation_duration'],
                    'propagation_duration_s': metrics['propagation_duration'],
                    'total_peel_time_s': metrics['total_peel_duration'],
                    'total_peel_duration_s': metrics['total_peel_duration'],
                    
                    # Distance metrics
                    'distance_to_peak_mm': metrics['pre_initiation_distance'],
                    'pre_initiation_distance_mm': metrics['pre_initiation_distance'],
                    'propagation_distance_mm': metrics['propagation_distance'],
                    'peel_distance_mm': metrics['total_peel_distance'],
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
        """Process all folders in V5 directory"""
        print("\n" + "="*80)
        print("V5 BATCH PROCESSOR - STARTING")
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
        print(f"PROCESSING COMPLETE: {len(self.all_results)} total measurements")
        print("="*80)
    
    def save_combined_csv(self):
        """Save all results to master CSV"""
        if not self.all_results:
            print("No results to save!")
            return
        
        # Create DataFrame
        df = pd.DataFrame(self.all_results)
        
        # Save to CSV
        output_file = self.v5_dir / "MASTER_V5_all_metrics.csv"
        df.to_csv(output_file, index=False)
        print(f"\nSaved master CSV: {output_file}")
        print(f"Total measurements: {len(df)}")
        
        return df
    
    def generate_master_plots(self):
        """Generate master plots using MasterPlotter"""
        if not self.all_results:
            print("No results to plot!")
            return
        
        print("\n" + "="*80)
        print("GENERATING MASTER PLOTS")
        print("="*80)
        
        # Load the saved CSV
        csv_file = self.v5_dir / "MASTER_V5_all_metrics.csv"
        if not csv_file.exists():
            print(f"ERROR: Master CSV not found: {csv_file}")
            return
        
        df = pd.read_csv(csv_file)
        
        # Create detailed_condition for proper grouping (membrane + tank)
        df['detailed_condition'] = df['membrane_type'] + ' + ' + df['tank_type']
        
        # Save updated CSV with detailed_condition
        df.to_csv(csv_file, index=False)
        
        # Initialize MasterPlotter (same as V4)
        print("\nGenerating master plots...")
        master_plotter = MasterPlotter(output_directory=self.v5_dir, dpi=300)
        
        # Generate all standard plots (same as V4)
        master_plotter.generate_standard_plots(df)
        
        print("\nMaster plots saved to V5 directory")


def main():
    """Main execution"""
    
    # V5 data path
    v5_path = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V5")
    
    if not v5_path.exists():
        print(f"ERROR: V5 path not found: {v5_path}")
        return
    
    print("="*80)
    print("V5 BATCH PROCESSOR")
    print("="*80)
    print(f"Processing data from: {v5_path}")
    print()
    
    # Create processor
    processor = V5BatchProcessor(str(v5_path))
    
    # Process all folders
    processor.process_all_folders()
    
    # Save combined CSV
    processor.save_combined_csv()
    
    # Generate master plots
    processor.generate_master_plots()
    
    print("\n" + "="*80)
    print("V5 PROCESSING COMPLETE")
    print("="*80)


if __name__ == '__main__':
    main()
