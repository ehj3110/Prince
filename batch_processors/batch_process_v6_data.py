"""
V6 Data Batch Processor for SteppedCone Tests
=============================================

Processes V6 adhesion test data with various material combinations.

Features:
- Handles cone data with LayerToArea calculations
- Generates individual plots for each autolog file
- Creates master plots with area binning
- Performs scaling analysis

Usage:
    python batch_process_v6_data.py

Author: Cheng Sun Lab Team
Date: December 2, 2025
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


class V6FolderInfo:
    """Stores parsed information about a V6 test folder"""
    
    def __init__(self, folder_path: Path):
        self.folder_path = folder_path
        self.folder_name = folder_path.name
        
        # Parse folder name
        # ACF_5mm_V19_Cone_BPAGDA_200
        # FlatPDMS_1mm_V22_Cone_BPAGDA_1000
        # TEMPO_1mm_V22p1_Cone_BPAGDA_1000
        parts = self.folder_name.split('_')
        
        # Extract material/membrane type
        if parts[0] == 'ACF':
            self.membrane_type = 'ACF, 5mm'
            self.tank_type = 'TankV19'
        elif parts[0] == 'FlatPDMS':
            self.membrane_type = 'Flat PDMS, 1mm'
            self.tank_type = 'TankV22'
        elif parts[0] == 'TEMPO':
            self.membrane_type = 'TEMPO, 1mm'
            # Check for p1/p2/p3
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
        else:
            self.membrane_type = parts[0]
            self.tank_type = 'TankV22'
        
        # Extract height
        self.height = parts[1] if len(parts) > 1 else "Unknown"
        
        # Find model (Cone/Pyramid)
        self.model = 'Cone'  # Default
        for part in parts:
            if part.lower() == 'cone':
                self.model = 'Cone'
            elif part.lower() == 'pyramid':
                self.model = 'Pyramid'
        
        # Extract resin
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
        if "V19" in self.tank_type:
            return math.pi * 6.765**2  # 143.78 mm² (circular tank)
        elif "V22" in self.tank_type:
            return math.pi * 6.765**2  # 143.78 mm² (circular tank)
        return 143.78  # Default
    
    def __str__(self):
        return (f"V6Folder({self.membrane_label}, {self.height}, {self.tank_type}, "
                f"{self.model}, {self.speed} µm/s)")


def calculate_layer_area(layer_num: int, model: str = 'Cone') -> float:
    """
    Calculate contact area for a given layer number.
    Uses same geometry as V5 processing.
    
    Args:
        layer_num: Layer number (1-indexed)
        model: 'Cone' or 'Pyramid'
        
    Returns:
        Contact area in mm²
    """
    # Layer height
    layer_height = 0.05  # mm
    
    # Base parameters (same as V5)
    base_radius_mm = 1.0  # mm (radius at top of cone)
    
    # Calculate height from tip
    height_from_tip = layer_num * layer_height
    
    # Cone angle (assumed from geometry)
    # tan(angle) = radius / height
    # Using base_radius at layer 1
    cone_angle = math.atan(base_radius_mm / layer_height)
    
    # Radius at this layer
    radius_at_layer = height_from_tip * math.tan(cone_angle)
    
    # Area
    if model == 'Cone':
        area = math.pi * radius_at_layer**2
    else:  # Pyramid
        side_length = 2 * radius_at_layer
        area = side_length**2
    
    return area


def process_autolog_file(autolog_path: Path, folder_info: V6FolderInfo, 
                         output_folder: Path, calculator, processor, plotter) -> pd.DataFrame:
    """
    Process a single autolog file and generate plots.
    
    Args:
        autolog_path: Path to autolog CSV file
        folder_info: Parsed folder information
        output_folder: Where to save output plots
        calculator: AdhesionMetricsCalculator instance
        processor: RawDataProcessor instance
        plotter: AnalysisPlotter instance
        
    Returns:
        DataFrame with metrics for this test
    """
    print(f"\nProcessing: {autolog_path.name}")
    
    # Extract layer numbers from filename (e.g., "autolog_L100-L105.csv")
    filename = autolog_path.stem
    if 'L' in filename:
        layer_parts = filename.split('_')[-1]  # "L100-L105"
        layer_range = layer_parts.replace('L', '').split('-')
        start_layer = int(layer_range[0])
        end_layer = int(layer_range[1]) if len(layer_range) > 1 else start_layer
        mid_layer = (start_layer + end_layer) // 2
    else:
        mid_layer = 100  # Default
    
    # Calculate area for this layer
    layer_area_mm2 = calculate_layer_area(mid_layer, folder_info.model)
    
    # Load raw data for plotting
    df = pd.read_csv(autolog_path)
    time_data = df['Elapsed Time (s)'].to_numpy()
    force_data = df['Force (N)'].to_numpy()
    
    # Apply smoothing
    smoothed_force = calculator._apply_smoothing(force_data)
    
    # Process to get layers
    layers = processor.process_csv(str(autolog_path))
    
    if not layers:
        print(f"  No layers detected, skipping...")
        return None
    
    print(f"  Detected {len(layers)} layers")
    
    # Generate individual plot
    plot_output_dir = output_folder / folder_info.folder_name
    plot_output_dir.mkdir(parents=True, exist_ok=True)
    
    plot_path = plot_output_dir / f"{autolog_path.stem}_analysis.png"
    plotter.create_plot(
        time_data=time_data,
        force_data=force_data,
        smoothed_force=smoothed_force,
        layers=layers,
        title=f"{folder_info.folder_name} - {autolog_path.stem}",
        save_path=str(plot_path)
    )
    print(f"  Saved plot: {plot_path.name}")
    
    # Extract metrics from first layer (these are multi-layer tests)
    if not layers:
        return None
        
    layer = layers[0]  # Use first layer for metrics
    metrics = layer['metrics']
    
    # Create results row
    result = {
        'folder': folder_info.folder_name,
        'test_file': autolog_path.name,
        'membrane_type': folder_info.membrane_type,
        'membrane_label': folder_info.membrane_label,
        'tank_type': folder_info.tank_type,
        'model': folder_info.model,
        'speed_um_s': int(folder_info.speed),
        'layer_number': mid_layer,
        'area_mm2': layer_area_mm2,
        'total_membrane_area_mm2': folder_info.total_membrane_area,
        'area_ratio': layer_area_mm2 / folder_info.total_membrane_area,
        'detailed_condition': f"{folder_info.membrane_label} + {folder_info.tank_type}",
        
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
    
    return pd.DataFrame([result])


def process_all_v6_data():
    """Main processing function for V6 data"""
    
    # Define paths
    v6_base_path = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V6")
    output_path = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V6")
    
    print("="*80)
    print("V6 DATA BATCH PROCESSOR")
    print("="*80)
    print(f"Input directory: {v6_base_path}")
    print(f"Output directory: {output_path}")
    print()
    
    # Initialize processors
    calculator = AdhesionMetricsCalculator()
    processor = RawDataProcessor(calculator)
    plotter = AnalysisPlotter(figure_size=(16, 12), dpi=150)
    
    # Find all autolog files
    autolog_files = list(v6_base_path.glob("*/autolog_*.csv"))
    print(f"Found {len(autolog_files)} autolog files\n")
    
    if not autolog_files:
        print("ERROR: No autolog files found!")
        return
    
    # Process each file
    all_results = []
    
    for autolog_path in sorted(autolog_files):
        folder_info = V6FolderInfo(autolog_path.parent)
        
        try:
            result_df = process_autolog_file(autolog_path, folder_info, output_path, 
                                            calculator, processor, plotter)
            if result_df is not None:
                all_results.append(result_df)
                print(f"  [OK] Success: {folder_info.membrane_label}, Layer {result_df['layer_number'].values[0]}, "
                      f"Area {result_df['area_mm2'].values[0]:.2f} mm²")
        except Exception as e:
            print(f"  [ERROR] Error processing {autolog_path.name}: {str(e)}")
            import traceback
            traceback.print_exc()
            continue
    
    # Combine all results
    if not all_results:
        print("\nERROR: No data processed successfully!")
        return
    
    master_df = pd.concat(all_results, ignore_index=True)
    
    # Save master CSV
    csv_output = output_path / "MASTER_V6_all_metrics.csv"
    master_df.to_csv(csv_output, index=False)
    print(f"\n{'='*80}")
    print(f"Master CSV saved: {csv_output}")
    print(f"Total measurements: {len(master_df)}")
    print(f"Conditions: {master_df['detailed_condition'].unique().tolist()}")
    
    # Generate master plots
    print(f"\n{'='*80}")
    print("GENERATING MASTER PLOTS")
    print("="*80)
    
    plotter = MasterPlotter(output_directory=str(output_path))
    plotter.generate_standard_plots(master_df)
    
    print("\n" + "="*80)
    print("V6 BATCH PROCESSING COMPLETE")
    print("="*80)


if __name__ == "__main__":
    process_all_v6_data()
