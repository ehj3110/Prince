"""
Universal Batch Processor for SteppedCone Adhesion Tests
========================================================

Automatically processes any version of test data (V4, V5, V6, ...) by:
1. Detecting folder naming conventions
2. Identifying data types (cone, pyramid, cylinder, etc.)
3. Extracting metadata from folder names
4. Generating individual plots and master plots

Usage:
    python batch_process_universal.py "path/to/master/folder"
    
    Or configure the MASTER_DATA_PATH below and run:
    python batch_process_universal.py

Features:
- Works with any version (V4, V5, V6, ...)
- Handles cone, pyramid, cylinder models
- Supports LayerToArea.txt (global or per-folder)
- Generates individual plots per autolog
- Creates master comparison plots
- Handles duplicate layer numbers automatically

Author: Cheng Sun Lab Team
Date: November 28, 2025
"""

import matplotlib
matplotlib.use('Agg')  # Force non-interactive backend

import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
import sys
import math
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Add support modules to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'support_modules'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'post-processing'))
from adhesion_metrics_calculator import AdhesionMetricsCalculator
from RawData_Processor import RawDataProcessor
from analysis_plotter import AnalysisPlotter
from master_plotter import MasterPlotter
from material_stiffness_analyzer import MaterialStiffnessAnalyzer
from summary_plot_generator import SummaryPlotGenerator

# ============================================================================
# CONFIGURATION
# ============================================================================

# Set your master data path here, or pass as command line argument
MASTER_DATA_PATH = r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests"

# Known tank specifications (add new tanks as needed)
TANK_SPECS = {
    'V19': {'type': 'circular', 'diameter_mm': 2 * 6.765},  # π × 6.765² = 143.78 mm²
    'V22': {'type': 'circular', 'diameter_mm': 2 * 6.765},  # π × 6.765² = 143.78 mm²
    'V22p1': {'type': 'circular', 'diameter_mm': 2 * 6.765},
    'V22p2': {'type': 'circular', 'diameter_mm': 2 * 6.765},
    'V22p3': {'type': 'circular', 'diameter_mm': 2 * 6.765},
    'V23': {'type': 'circular', 'diameter_mm': 2 * 6.765},  # Same as V22
}

# ============================================================================
# FOLDER INFO PARSER
# ============================================================================

class FolderInfo:
    """Parses test folder names and extracts metadata"""
    
    def __init__(self, folder_path: Path):
        self.folder_path = folder_path
        self.folder_name = folder_path.name
        self.version = self._detect_version()
        
        # Parse folder name components
        self._parse_folder_name()
        
        # Calculate tank area
        self.total_membrane_area = self._calculate_tank_area()
        
    def _detect_version(self) -> str:
        """Detect version from parent folder name (V4, V5, V6, etc.)"""
        parent_name = self.folder_path.parent.name
        match = re.search(r'V(\d+)', parent_name, re.IGNORECASE)
        if match:
            return f"V{match.group(1)}"
        return "Unknown"
    
    def _parse_folder_name(self):
        """Parse folder name to extract metadata
        
        Supports multiple naming conventions:
        - Old: Membrane_Gap_Tank_Model_Resin_Speed (e.g., ACF_5mm_V19_Cone_BPAGDA_200)
        - New: Membrane_Gap_Tank_Model_Speed_Date_Iteration (e.g., USWTEMPO_2mm_V23_Cone_1000_1209_V0)
        """
        parts = self.folder_name.split('_')
        
        # Initialize attributes
        self.membrane_type = None
        self.membrane_thickness = None
        self.height = None
        self.tank_type = None
        self.model = None
        self.resin = None
        self.speed = None
        self.date = None
        self.iteration = None
        
        # Common patterns
        for i, part in enumerate(parts):
            part_lower = part.lower()
            
            # Membrane type (PDMS, ACF, TEMPO, FlatPDMS, USWTEMPO, etc.)
            if 'flatpdms' in part_lower:
                self.membrane_type = "Flat PDMS"
            elif 'uswtempo' in part_lower:
                # USW prefix for ultra-soft-wall TEMPO
                self.membrane_type = "USW TEMPO"
            elif 'uswacf' in part_lower:
                self.membrane_type = "USW ACF"
            elif 'uswpdms' in part_lower:
                self.membrane_type = "USW PDMS"
            elif 'pdms' in part_lower:
                # Extract thickness if present (e.g., "100umPDMS" or "PDMS100um")
                thickness_match = re.search(r'(\d+)um', part, re.IGNORECASE)
                if thickness_match:
                    self.membrane_thickness = thickness_match.group(1) + "um"
                    self.membrane_type = "PDMS"
                else:
                    self.membrane_type = "PDMS"
            elif 'acf' in part_lower:
                self.membrane_type = "ACF"
            elif 'tempo' in part_lower:
                self.membrane_type = "TEMPO"
            
            # Height (e.g., "1mm", "2mm")
            if re.match(r'\d+mm$', part_lower):
                self.height = part
            
            # Tank type (e.g., "V19", "V22p1", "V23", "TankV19")
            if 'tank' in part_lower or re.match(r'v\d+', part_lower):
                self.tank_type = part.replace('Tank', 'Tank') if 'tank' not in part else part
                # Normalize to standard format
                if not self.tank_type.startswith('Tank'):
                    self.tank_type = 'Tank' + self.tank_type
            
            # Model type (Cone, Pyramid, Cylinder)
            if 'cone' in part_lower:
                self.model = "Cone"
            elif 'pyramid' in part_lower:
                self.model = "Pyramid"
            elif 'cylinder' in part_lower:
                self.model = "Cylinder"
            
            # Resin type (e.g., "BPAGDA") - may not be present in new format
            if part.upper() in ['BPAGDA', 'IBOA', 'HDDA']:
                self.resin = part.upper()
            
            # Date (e.g., "1209" for Dec 9) - 4 digits MMDD
            if re.match(r'\d{4}$', part) and i > 0:
                # Check if this looks like a date (not a speed)
                # Dates are typically in positions after model
                if int(part) <= 1231 and int(part) >= 101:  # Valid month/day range
                    self.date = part
                    continue
            
            # Iteration (e.g., "V0", "V1") - appears at end
            if re.match(r'v\d+$', part_lower) and i == len(parts) - 1:
                self.iteration = part
                continue
            
            # Speed (e.g., "1000", "500") - digits >= 100
            if part.isdigit() and int(part) >= 100:
                # If we haven't found a date yet and this could be a speed
                if self.date is None or int(part) > 1231:
                    self.speed = part
        
        # Create membrane label
        if self.membrane_thickness:
            self.membrane_label = f"{self.membrane_type}, {self.membrane_thickness}"
        elif self.height:
            # For materials like "ACF, 5mm" or "Flat PDMS, 1mm"
            self.membrane_label = f"{self.membrane_type}, {self.height}"
        else:
            self.membrane_label = self.membrane_type or "Unknown"
    
    def _calculate_tank_area(self) -> float:
        """Calculate total membrane area based on tank type"""
        if not self.tank_type:
            return 0.0
        
        # Normalize tank type
        tank_key = self.tank_type.replace('Tank', '')
        
        # Check if we have specs for this tank
        for known_tank, specs in TANK_SPECS.items():
            if tank_key in known_tank or known_tank in tank_key:
                if specs['type'] == 'circular':
                    radius = specs['diameter_mm'] / 2
                    return math.pi * radius * radius
        
        print(f"WARNING: Unknown tank type '{self.tank_type}', using area = 0")
        return 0.0
    
    def __repr__(self):
        return (f"Folder({self.membrane_label}, {self.height}, "
                f"{self.tank_type}, {self.model}, {self.version})")


# ============================================================================
# UNIVERSAL BATCH PROCESSOR
# ============================================================================

class UniversalBatchProcessor:
    """Processes any version of test data automatically"""
    
    def __init__(self, master_directory: str):
        self.master_dir = Path(master_directory)
        self.all_results = []
        
        # Try to load global LayerToArea.txt if it exists
        self.global_layer_to_area = self._load_global_layer_to_area()
        
        # Initialize processors
        self.calculator = AdhesionMetricsCalculator()
        self.processor = RawDataProcessor(self.calculator)
        self.plotter = AnalysisPlotter(figure_size=(16, 12), dpi=150)
        self.stiffness_analyzer = MaterialStiffnessAnalyzer()
        
    def _load_global_layer_to_area(self) -> Optional[Dict[int, float]]:
        """Load global LayerToArea.txt if it exists in master directory or parent"""
        # Check master directory first
        global_path = self.master_dir / "LayerToArea.txt"
        if global_path.exists():
            print(f"\nLoading global LayerToArea.txt from {global_path}")
            return self._load_layer_to_area(global_path)
        
        # Check parent directory (e.g., SteppedConeTests if master_dir is V6)
        parent_global_path = self.master_dir.parent / "LayerToArea.txt"
        if parent_global_path.exists():
            print(f"\nLoading global LayerToArea.txt from {parent_global_path}")
            return self._load_layer_to_area(parent_global_path)
        
        return None
    
    def _load_layer_to_area(self, file_path: Path) -> Dict[int, float]:
        """Load LayerToArea.txt and handle duplicates"""
        try:
            df = pd.read_csv(file_path, sep='\t')
            
            # Handle duplicate layer numbers - keep the last occurrence
            if 'Layer_Number' in df.columns:
                duplicates = df['Layer_Number'].duplicated()
                if duplicates.any():
                    print(f"  WARNING: Found {duplicates.sum()} duplicate layer numbers")
                    print(f"  Keeping last occurrence of each duplicate")
                    df = df.drop_duplicates(subset='Layer_Number', keep='last')
            
            # Create mapping dictionary - handle both 'Area_mm2' and 'Area' column names
            area_col = 'Area_mm2' if 'Area_mm2' in df.columns else 'Area'
            layer_to_area = dict(zip(df['Layer_Number'], df[area_col]))
            print(f"  Loaded {len(layer_to_area)} layer-to-area mappings")
            return layer_to_area
            
        except Exception as e:
            print(f"  ERROR loading LayerToArea.txt: {e}")
            return {}
    
    def _get_layer_to_area_for_folder(self, folder_info: FolderInfo) -> Dict[int, float]:
        """Get layer-to-area mapping for a specific folder"""
        # Check for folder-specific LayerToArea.txt
        folder_layer_file = folder_info.folder_path / "LayerToArea.txt"
        if folder_layer_file.exists():
            print(f"  Using folder-specific LayerToArea.txt")
            return self._load_layer_to_area(folder_layer_file)
        
        # Use global if available
        if self.global_layer_to_area:
            print(f"  Using global LayerToArea.txt")
            return self.global_layer_to_area
        
        # Fall back to automated_work_of_adhesion.csv
        automated_csv = folder_info.folder_path / "automated_work_of_adhesion.csv"
        if automated_csv.exists():
            print(f"  Using automated_work_of_adhesion.csv for area mapping")
            try:
                df = pd.read_csv(automated_csv)
                if 'Layer_Number' in df.columns and 'Cross_Sectional_Area_mm2' in df.columns:
                    return dict(zip(df['Layer_Number'], df['Cross_Sectional_Area_mm2']))
            except Exception as e:
                print(f"  WARNING: Could not load automated CSV: {e}")
        
        # Final fallback: Calculate areas from cone geometry for all layers in autolog files
        if folder_info.model == 'Cone':
            print(f"  Using calculated cone geometry (0.05mm layer height)")
            autolog_files = list(folder_info.folder_path.glob('autolog_*.csv'))
            layer_numbers = set()
            for file in autolog_files:
                # Extract layer numbers from filename
                match = re.search(r'L(\d+)(?:-L(\d+))?', file.stem)
                if match:
                    start = int(match.group(1))
                    end = int(match.group(2)) if match.group(2) else start
                    mid = (start + end) // 2
                    layer_numbers.add(mid)
            
            # Calculate cone areas using proper geometry
            # Standard cone: radius = 1mm at layer 1 (0.05mm from tip)
            # Area = π * r² where r = layer_number * layer_height * (base_radius / base_height)
            layer_height = 0.05  # mm per layer
            base_radius = 1.0  # mm (radius at first layer)
            base_height = 0.05  # mm (height of first layer)
            
            layer_to_area = {}
            for layer_num in layer_numbers:
                # Radius scales linearly with height from tip
                height_from_tip = layer_num * layer_height
                radius_at_layer = (height_from_tip / base_height) * base_radius
                area = math.pi * radius_at_layer * radius_at_layer
                layer_to_area[layer_num] = area
            
            print(f"  Calculated areas for {len(layer_to_area)} layers")
            print(f"  Example: Layer 100 → Area {layer_to_area.get(100, 0):.2f} mm²")
            return layer_to_area
        
        print(f"  WARNING: No layer-to-area mapping found!")
        return {}
    
    def find_test_folders(self) -> List[FolderInfo]:
        """Find all test folders in master directory and subdirectories"""
        test_folders = []
        
        # Search for folders containing autolog files
        for folder in self.master_dir.rglob('*'):
            if folder.is_dir():
                # Check if folder contains autolog files
                autolog_files = list(folder.glob('autolog_*.csv'))
                if autolog_files:
                    try:
                        folder_info = FolderInfo(folder)
                        test_folders.append(folder_info)
                        print(f"Found: {folder_info}")
                    except Exception as e:
                        print(f"WARNING: Could not parse folder {folder.name}: {e}")
        
        return test_folders
    
    def process_folder(self, folder_info: FolderInfo) -> List[Dict]:
        """Process a single test folder"""
        print(f"\n{'='*80}")
        print(f"Processing: {folder_info.folder_name}")
        print(f"  Version: {folder_info.version}")
        print(f"  Type: {folder_info.membrane_label}, {folder_info.model}")
        print(f"  Tank: {folder_info.tank_type} (Area: {folder_info.total_membrane_area:.2f} mm²)")
        print(f"{'='*80}")
        
        # Get layer-to-area mapping
        layer_to_area_map = self._get_layer_to_area_for_folder(folder_info)
        if not layer_to_area_map:
            print(f"  ERROR: No layer-to-area mapping available, skipping folder")
            return []
        
        # Find all autolog files
        autolog_files = sorted(folder_info.folder_path.glob('autolog_*.csv'))
        print(f"Found {len(autolog_files)} autolog files")
        
        # Create plots subdirectory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        plots_dir = folder_info.folder_path / "plots" / f"plots_{timestamp}"
        plots_dir.mkdir(parents=True, exist_ok=True)
        print(f"  Saving plots to: {plots_dir.name}")
        
        folder_results = []
        
        # Process each autolog file
        for autolog_file in autolog_files:
            print(f"\n  Processing: {autolog_file.name}")
            
            try:
                # Load raw data for plotting and stiffness analysis
                df = pd.read_csv(autolog_file)
                time_data = df['Elapsed Time (s)'].to_numpy()
                force_data = df['Force (N)'].to_numpy()
                position_data = df['Position (mm)'].to_numpy()
                
                # Apply smoothing
                smoothed_force = self.calculator._apply_smoothing(force_data)
                
                # Process to get layers
                layers = self.processor.process_csv(str(autolog_file))
                
                if not layers:
                    print(f"    WARNING: No layers detected")
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
                    area_ratio = contact_area / folder_info.total_membrane_area if folder_info.total_membrane_area > 0 else 0
                    
                    # Calculate material stiffness using multiple fit models
                    lifting_start = layer['start_idx']
                    lifting_end = layer['end_idx']
                    pre_init_idx = layer.get('pre_init_idx', lifting_start)
                    peak_idx = layer.get('peak_idx', lifting_start)
                    
                    # Extract lifting phase data
                    lifting_disp = position_data[lifting_start:lifting_end+1]
                    lifting_force = force_data[lifting_start:lifting_end+1]
                    
                    # Calculate stiffness with multiple models (relative to pre-initiation start)
                    stiffness_result = self.stiffness_analyzer.analyze_stiffness(
                        displacement=lifting_disp,
                        force=lifting_force,
                        baseline_idx=pre_init_idx - lifting_start,  # Make relative to segment
                        peak_idx=peak_idx - lifting_start,  # Make relative to segment
                        auto_crop=True
                    )
                    
                    # Create result dictionary (standard format for MasterPlotter)
                    result = {
                        # Metadata
                        'folder': folder_info.folder_name,
                        'version': folder_info.version,
                        'condition_label': folder_info.membrane_label,
                        'membrane_type': folder_info.membrane_label,
                        'membrane_label': folder_info.membrane_label,
                        'height': folder_info.height,
                        'tank_type': folder_info.tank_type,
                        'resin': folder_info.resin,
                        'model': folder_info.model,
                        'speed_um_s': int(folder_info.speed) if folder_info.speed and folder_info.speed.isdigit() else 0,
                        'layer_number': layer_num,
                        'detailed_condition': f"{folder_info.membrane_label} + {folder_info.tank_type}",
                        
                        # Area data
                        'area_mm2': contact_area,
                        'contact_area_mm2': contact_area,
                        'total_membrane_area_mm2': folder_info.total_membrane_area,
                        'area_ratio': area_ratio,
                        
                        # Key metrics
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
                        
                        # Retraction metrics
                        'peak_retraction_force_N': metrics.get('peak_retraction_force', 0),
                        
                        # Stiffness (existing effective stiffness from calculator)
                        'effective_stiffness_N_per_mm': metrics.get('effective_stiffness_N_per_mm', 0),
                        
                        # Material stiffness (new multi-model analysis)
                        'material_stiffness_N_per_mm': stiffness_result.get('best_stiffness_N_per_mm', 0),
                        'material_stiffness_model': stiffness_result.get('best_model', 'none'),
                        'material_stiffness_r_squared': stiffness_result.get('best_r_squared', 0),
                        'material_stiffness_cropped': stiffness_result.get('cropped', False),
                        'material_stiffness_n_points': stiffness_result.get('n_points_used', 0),
                        
                        # Individual model stiffnesses
                        'stiffness_linear_N_per_mm': stiffness_result['linear'].get('stiffness_N_per_mm', 0),
                        'stiffness_linear_r_squared': stiffness_result['linear'].get('r_squared', 0),
                        'stiffness_exponential_N_per_mm': stiffness_result['exponential'].get('stiffness_N_per_mm', 0),
                        'stiffness_exponential_r_squared': stiffness_result['exponential'].get('r_squared', 0),
                        'stiffness_logarithmic_N_per_mm': stiffness_result['logarithmic'].get('stiffness_N_per_mm', 0),
                        'stiffness_logarithmic_r_squared': stiffness_result['logarithmic'].get('r_squared', 0),
                        'stiffness_power_law_N_per_mm': stiffness_result['power_law'].get('stiffness_N_per_mm', 0),
                        'stiffness_power_law_r_squared': stiffness_result['power_law'].get('r_squared', 0),
                        'stiffness_power_law_exponent': stiffness_result['power_law'].get('parameters', {}).get('n', 0),
                    }
                    
                    folder_results.append(result)
                
            except Exception as e:
                print(f"    ERROR processing {autolog_file.name}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"\n  Processed {len(folder_results)} layer measurements")
        
        # Generate summary plot for this folder
        self._generate_summary_plot(folder_info)
        
        return folder_results
    
    def _generate_summary_plot(self, folder_info: FolderInfo):
        """Generate 4-panel summary plot for the folder"""
        # Look for automated_work_of_adhesion.csv
        csv_path = folder_info.folder_path / "automated_work_of_adhesion.csv"
        
        if not csv_path.exists():
            print(f"  Note: No automated_work_of_adhesion.csv found, skipping summary plot")
            return
        
        # Look for MASTER CSV for stiffness data
        master_csv_path = self.master_dir / "MASTER_all_metrics.csv"
        
        try:
            print(f"\n  Generating summary plot...")
            generator = SummaryPlotGenerator(output_dir=folder_info.folder_path)
            generator.generate_summary_plot(csv_path, master_csv_path=master_csv_path, output_filename="summary_plot.png")
        except Exception as e:
            print(f"  Warning: Could not generate summary plot: {e}")
    
    def process_all_folders(self):
        """Find and process all test folders"""
        print("\n" + "="*80)
        print("UNIVERSAL BATCH PROCESSOR - STARTING")
        print("="*80)
        
        # Find all test folders
        test_folders = self.find_test_folders()
        
        if not test_folders:
            print("\nNo test folders found!")
            return
        
        print(f"\nTotal folders found: {len(test_folders)}")
        
        # Process each folder
        for folder_info in test_folders:
            results = self.process_folder(folder_info)
            self.all_results.extend(results)
        
        print(f"\n{'='*80}")
        print(f"Processing complete: {len(self.all_results)} total measurements")
        print("="*80)
    
    def save_combined_csv(self, output_name: str = "MASTER_all_metrics.csv"):
        """Save all results to a combined CSV"""
        if not self.all_results:
            print("No results to save!")
            return
        
        csv_file = self.master_dir / output_name
        df = pd.DataFrame(self.all_results)
        
        # detailed_condition should already be set in results, but ensure it exists
        if 'detailed_condition' not in df.columns:
            df['detailed_condition'] = df['membrane_type'] + ' + ' + df['tank_type']
        
        # Save CSV
        df.to_csv(csv_file, index=False)
        print(f"\n{'='*80}")
        print(f"Master CSV saved: {csv_file}")
        print(f"Total measurements: {len(df)}")
        print(f"Conditions: {df['detailed_condition'].unique().tolist()}")
        
        # Show summary by condition
        print("\nSummary by condition:")
        for condition, group in df.groupby('detailed_condition'):
            print(f"  {condition}: {len(group)} measurements")
        
        return csv_file
    
    def generate_master_plots(self):
        """Generate master comparison plots"""
        if not self.all_results:
            print("No results to plot!")
            return
        
        print("\n" + "="*80)
        print("GENERATING MASTER PLOTS")
        print("="*80)
        
        df = pd.DataFrame(self.all_results)
        
        # Ensure detailed_condition exists
        if 'detailed_condition' not in df.columns:
            df['detailed_condition'] = df['membrane_type'] + ' + ' + df['tank_type']
        
        # Initialize MasterPlotter
        master_plotter = MasterPlotter(output_directory=str(self.master_dir), dpi=300)
        
        # Generate all standard plots
        master_plotter.generate_standard_plots(df)
        
        # Generate radius-based plots
        master_plotter.generate_standard_radius_plots(df)
        
        print("\n" + "="*80)
        print("MASTER PLOTS COMPLETE")
        print("="*80)


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main execution"""
    
    # Get master directory from command line or use default
    if len(sys.argv) > 1:
        master_path = sys.argv[1]
    else:
        master_path = MASTER_DATA_PATH
    
    master_path = Path(master_path)
    
    if not master_path.exists():
        print(f"ERROR: Master path not found: {master_path}")
        print("\nUsage:")
        print(f"  python {Path(__file__).name} <master_folder_path>")
        print(f"\nOr configure MASTER_DATA_PATH in the script")
        return
    
    print("="*80)
    print("UNIVERSAL BATCH PROCESSOR")
    print("="*80)
    print(f"Master Directory: {master_path}")
    print()
    
    # Create processor
    processor = UniversalBatchProcessor(str(master_path))
    
    # Process all folders
    processor.process_all_folders()
    
    # Save combined CSV
    processor.save_combined_csv()
    
    # Generate master plots
    processor.generate_master_plots()
    
    print("\n" + "="*80)
    print("UNIVERSAL PROCESSING COMPLETE")
    print("="*80)


if __name__ == '__main__':
    main()
