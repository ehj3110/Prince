"""
Process Single V4 Folder
========================

Processes a single V4 test folder and saves results to CSV.
This script is designed to be called by the unified batch processor.

Usage:
    python process_single_v4_folder.py <folder_path> <output_csv>
    
Example:
    python process_single_v4_folder.py "V4/100umPDMS_500um_TankV19_BPAGDA_Pyramid_1000" "results_100umPDMS.csv"

Author: Cheng Sun Lab Team
Date: November 18, 2025
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import List, Dict
import matplotlib
matplotlib.use('Agg')

# Add support modules to path
sys.path.insert(0, str(Path(__file__).parent / 'support_modules'))
sys.path.insert(0, str(Path(__file__).parent / 'post-processing'))
from adhesion_metrics_calculator import AdhesionMetricsCalculator
from RawData_Processor import RawDataProcessor
from analysis_plotter import AnalysisPlotter


class V4FolderProcessor:
    """Processes a single V4 test folder"""
    
    def __init__(self, folder_path: Path):
        self.folder_path = Path(folder_path)
        self.folder_name = self.folder_path.name
        
        # Parse folder name
        self._parse_folder_name()
        
        # Initialize tools
        self.calculator = AdhesionMetricsCalculator()
        self.processor = RawDataProcessor(self.calculator)
        self.plotter = AnalysisPlotter(figure_size=(16, 12), dpi=150)
        
        # Determine data source and load area mapping
        self._setup_area_mapping()
        
    def _parse_folder_name(self):
        """Parse folder name: MembraneType_Height_TankType_Resin_Model_Speed"""
        parts = self.folder_name.split('_')
        
        if len(parts) < 5:
            raise ValueError(f"Invalid folder name format: {self.folder_name}")
        
        self.membrane_type = parts[0]  # e.g., '100umPDMS', 'ACF'
        self.height = parts[1]  # e.g., '500um', '5mm'
        self.tank_type = parts[2]  # e.g., 'TankV19'
        
        # Check if this is a Cone folder (has 'Cone' in name)
        # IMPORTANT: Check this FIRST before assigning model/resin
        is_cone = 'Cone' in self.folder_name
        
        if is_cone:
            # Format: MembraneType_Height_TankType_Cone_Resin_Speed
            # Find which part says "Cone"
            cone_idx = next(i for i, p in enumerate(parts) if 'Cone' in p)
            self.model = parts[cone_idx]  # e.g., 'Cone' or 'SteppedCone'
            self.resin = parts[cone_idx + 1] if cone_idx + 1 < len(parts) else 'BPAGDA'
            self.speed = parts[cone_idx + 2] if cone_idx + 2 < len(parts) else '1000'
        else:
            # Format: MembraneType_Height_TankType_Resin_Pyramid_Speed or
            #         MembraneType_Height_TankType_Resin_Speed (default to Pyramid)
            self.resin = parts[3]
            self.model = parts[4] if len(parts) > 4 and not parts[4].isdigit() else 'Pyramid'
            self.speed = parts[5] if len(parts) > 5 else (parts[4] if len(parts) > 4 and parts[4].isdigit() else '1000')
        
        # Create membrane label for grouping (include tank type to separate V19/V20)
        self.membrane_label = self.membrane_type.replace('um', 'um ')  # Keep 'um' for console compatibility
        
        # Calculate total membrane area based on tank type (rectangular membranes)
        # V19: 31.75mm × 19.05mm = 604.84 mm²
        # V20: 21.64mm × 13.522mm = 292.62 mm²
        if 'V20' in self.tank_type:
            self.total_membrane_area = 21.64 * 13.522  # 292.62 mm²
        else:  # V19 or other
            self.total_membrane_area = 31.75 * 19.05  # 604.84 mm²
        
        print(f"Folder: {self.folder_name}")
        print(f"  Membrane: {self.membrane_label}")
        print(f"  Height: {self.height}, Tank: {self.tank_type}")
        print(f"  Model: {self.model}, Resin: {self.resin}, Speed: {self.speed}")
    
    def _setup_area_mapping(self):
        """
        Setup area mapping with universal fallback approach.
        Primary: Try automated_work_of_adhesion.csv for Pyramid folders
        Fallback: Use LayerToArea.txt (V3 universal approach)
        """
        self.is_cone = 'Cone' in self.model
        self.is_pyramid = not self.is_cone
        self.area_map = {}
        
        # Primary: Try Pyramid-specific CSV if this is a Pyramid folder
        if self.is_pyramid:
            csv_file = self.folder_path / "automated_work_of_adhesion.csv"
            if csv_file.exists():
                try:
                    print(f"  Trying pyramid area data from {csv_file.name}")
                    df = pd.read_csv(csv_file)
                    
                    # Check for required columns
                    area_col = None
                    if 'Cross_Sectional_Area_mm2' in df.columns:
                        area_col = 'Cross_Sectional_Area_mm2'
                    elif 'Area' in df.columns:
                        area_col = 'Area'
                    
                    layer_col = None
                    if 'Layer_Number' in df.columns:
                        layer_col = 'Layer_Number'
                    elif 'Layer' in df.columns:
                        layer_col = 'Layer'
                    
                    # If columns found, build mapping
                    if area_col and layer_col:
                        for _, row in df.iterrows():
                            if pd.isna(row[layer_col]) or pd.isna(row[area_col]):
                                continue
                            layer_num = int(row[layer_col])
                            area = float(row[area_col])
                            self.area_map[layer_num] = area
                        
                        if len(self.area_map) > 0:
                            print(f"  Successfully loaded {len(self.area_map)} pyramid area mappings")
                            return  # Success - don't need fallback
                        else:
                            print(f"  Pyramid CSV had no valid data, trying fallback...")
                    else:
                        print(f"  Pyramid CSV missing required columns, trying fallback...")
                
                except Exception as e:
                    print(f"  Could not use pyramid CSV ({e}), trying fallback...")
        
        # FALLBACK: Universal LayerToArea.txt approach (like V3)
        # Try in folder first, then parent directory
        area_file = self.folder_path / "LayerToArea.txt"
        if not area_file.exists():
            area_file = self.folder_path.parent / "LayerToArea.txt"
        
        if area_file.exists():
            print(f"  Using LayerToArea.txt fallback from {area_file}")
            area_df = pd.read_csv(area_file, sep='\t')
            # Simple V3-style mapping - dict(zip()) approach
            self.area_map = dict(zip(area_df['Layer_Number'], area_df['Area']))
            print(f"  Loaded {len(self.area_map)} layer-to-area mappings from fallback")
        else:
            raise FileNotFoundError(f"No area mapping available - LayerToArea.txt not found in {self.folder_path} or {self.folder_path.parent}")
        
        print(f"  Final area mapping has {len(self.area_map)} entries")
    
    def process_folder(self) -> List[Dict]:
        """
        Process all autolog files in the folder
        
        Returns:
            List of result dictionaries
        """
        print(f"\n{'='*80}")
        print(f"Processing: {self.folder_name}")
        print(f"{'='*80}")
        
        # Find autolog files
        autolog_files = sorted(self.folder_path.glob("autolog*.csv"))
        print(f"Found {len(autolog_files)} autolog files")
        
        if not autolog_files:
            print("No autolog files found!")
            return []
        
        # Create timestamped plot directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        plots_dir = self.folder_path / "plots" / f"plots_{timestamp}"
        plots_dir.mkdir(parents=True, exist_ok=True)
        print(f"Saving plots to: plots_{timestamp}")
        
        results = []
        
        # Process each autolog file
        for autolog_file in autolog_files:
            # Skip the metrics CSV file
            if autolog_file.name == "autolog_metrics.csv":
                print(f"\n  Skipping: {autolog_file.name} (metrics file)")
                continue
            
            print(f"\n  Processing: {autolog_file.name}")
            
            # Extract layer range from filename (e.g., "autolog_L100-L105.csv" -> layers 100-105)
            import re
            match = re.search(r'L(\d+)-L(\d+)', autolog_file.name)
            if match:
                start_layer = int(match.group(1))
                end_layer = int(match.group(2))
                expected_layers = list(range(start_layer, end_layer + 1))
                print(f"    Expected layers from filename: {start_layer}-{end_layer}")
            else:
                print(f"    WARNING: Could not parse layer range from filename")
                expected_layers = None
            
            # Load raw data
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
            
            # Map detected layers to actual layer numbers from filename
            if expected_layers and len(layers) == len(expected_layers):
                for i, layer in enumerate(layers):
                    layer['number'] = expected_layers[i]
                print(f"    Mapped to actual layers: {expected_layers}")
            
            # Generate individual plot
            plot_path = plots_dir / f"{autolog_file.stem}_analysis.png"
            self.plotter.create_plot(
                time_data=time_data,
                force_data=force_data,
                smoothed_force=smoothed_force,
                layers=layers,
                title=f"{self.folder_name} - {autolog_file.stem}",
                save_path=str(plot_path)
            )
            print(f"    Saved plot: {plot_path.name}")
            
            # Extract metrics
            for layer in layers:
                layer_num = layer['number']
                metrics = layer['metrics']
                
                # Get contact area - Universal V3 approach
                contact_area = self.area_map.get(layer_num)
                
                if contact_area is None:
                    print(f"    WARNING: No area data for Layer {layer_num}, skipping...")
                    continue
                
                # Calculate area ratio
                area_ratio = contact_area / self.total_membrane_area
                
                # Create result dictionary
                result = {
                    # Metadata
                    'folder': self.folder_name,
                    'condition_label': f"{self.membrane_label} {self.tank_type}",
                    'membrane_type': self.membrane_label,
                    'height': self.height,
                    'tank_type': self.tank_type,
                    'resin': self.resin,
                    'model': self.model,
                    'speed_um_s': int(self.speed) if self.speed.isdigit() else 0,
                    'layer_number': layer_num,
                    
                    # Area data
                    'area_mm2': contact_area,
                    'contact_area_mm2': contact_area,
                    'total_membrane_area_mm2': self.total_membrane_area,
                    'area_ratio': area_ratio,
                    
                    # Key metrics (standard names for MasterPlotter)
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
                    'effective_stiffness_N_per_mm': metrics.get('effective_stiffness', 0),
                }
                
                results.append(result)
        
        print(f"\n  Processed {len(results)} layer measurements")
        return results


def main():
    """Main execution"""
    if len(sys.argv) < 3:
        print("Usage: python process_single_v4_folder.py <folder_path> <output_csv>")
        print("Example: python process_single_v4_folder.py 'V4/100umPDMS_500um_TankV19_BPAGDA_Pyramid_1000' 'results_100umPDMS.csv'")
        sys.exit(1)
    
    folder_path = Path(sys.argv[1])
    output_csv = Path(sys.argv[2])
    
    if not folder_path.exists():
        print(f"ERROR: Folder not found: {folder_path}")
        sys.exit(1)
    
    # Process the folder
    processor = V4FolderProcessor(folder_path)
    results = processor.process_folder()
    
    if results:
        # Save to CSV
        df = pd.DataFrame(results)
        df.to_csv(output_csv, index=False)
        print(f"\n{'='*80}")
        print(f"SAVED: {output_csv}")
        print(f"  Rows: {len(df)}")
        print(f"{'='*80}")
    else:
        print(f"\nNo results to save!")
        sys.exit(1)


if __name__ == "__main__":
    main()
