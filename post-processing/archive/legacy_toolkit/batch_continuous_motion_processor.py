"""
Batch Continuous Motion Processor
==================================

Batch processes multiple folders of continuous motion print data (overstep=0).
Recursively searches through a root directory and processes all autolog CSV files,
generating individual plots in the style of post_print_analyzer.

For continuous motion (overstep=0):
- No retraction phase
- Peak force at end of lift or during pause
- Analysis window includes full Lift + Pause

Usage:
    python batch_continuous_motion_processor.py --root "C:/path/to/ToProcess"
    
    Or interactively:
    python batch_continuous_motion_processor.py

Author: Cheng Sun Lab Team
Date: February 5, 2026
"""

import os
import sys
from pathlib import Path
import argparse
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple

# Add parent directory to path to import support_modules
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

# Add post-processing directory to path for local imports
post_processing_dir = Path(__file__).parent
sys.path.insert(0, str(post_processing_dir))

# Import our analysis tools
from support_modules.adhesion_metrics_calculator import AdhesionMetricsCalculator
from analysis_plotter import AnalysisPlotter


class BatchContinuousMotionProcessor:
    """
    Batch processes continuous motion print data from multiple folders.
    Generates individual plots using the AnalysisPlotter style.
    """
    
    def __init__(self):
        """Initialize with same calculator settings as live analysis"""
        self.calculator = AdhesionMetricsCalculator(
            median_kernel=5,
            savgol_window=9,
            savgol_order=2,
            baseline_threshold_factor=0.002,
            min_peak_height=0.01,
            min_peak_distance=50
        )
        
        self.plotter = AnalysisPlotter(figure_size=(16, 12), dpi=150)
        self.layer_colors = ['red', 'blue', 'green', 'orange', 'purple', 'brown']
    
    def process_root_folder(self, root_path: str):
        """
        Recursively process all subfolders containing autolog CSV files.
        
        Args:
            root_path: Root directory to search for autolog files
        """
        root = Path(root_path)
        
        if not root.exists():
            print(f"ERROR: Root folder not found: {root}")
            return
        
        print(f"\n{'='*80}")
        print(f"Batch Continuous Motion Processor")
        print(f"{'='*80}")
        print(f"Root directory: {root}")
        print(f"Searching for autolog CSV files...")
        
        # Find all autolog CSV files recursively
        csv_files = list(root.rglob("autolog_*.csv"))
        
        if not csv_files:
            print(f"\nNo autolog CSV files found in {root}")
            return
        
        # Group files by parent folder
        folders_with_files = {}
        for csv_file in csv_files:
            parent_folder = csv_file.parent
            if parent_folder not in folders_with_files:
                folders_with_files[parent_folder] = []
            folders_with_files[parent_folder].append(csv_file)
        
        print(f"\nFound {len(csv_files)} file(s) in {len(folders_with_files)} folder(s):")
        for folder, files in folders_with_files.items():
            rel_path = folder.relative_to(root)
            print(f"  {rel_path}: {len(files)} file(s)")
        
        # Process each folder
        total_processed = 0
        total_layers = 0
        
        for folder, files in sorted(folders_with_files.items()):
            print(f"\n{'='*80}")
            print(f"Processing folder: {folder.name}")
            print(f"{'='*80}")
            
            for csv_file in sorted(files):
                print(f"\n  File: {csv_file.name}")
                
                layers, summary_data = self.process_csv_file(csv_file)
                
                if layers:
                    # Generate plot using AnalysisPlotter style
                    plot_path = csv_file.parent / f"{csv_file.stem}_analysis.png"
                    self.generate_plot(csv_file, layers, summary_data, plot_path)
                    
                    total_processed += 1
                    total_layers += len(layers)
                    
                    print(f"  [OK] Processed {len(layers)} layer(s)")
                    print(f"  [OK] Plot saved: {plot_path.name}")
        
        print(f"\n{'='*80}")
        print(f"Batch Processing Complete")
        print(f"{'='*80}")
        print(f"Processed: {total_processed} file(s)")
        print(f"Total layers: {total_layers}")
        print(f"{'='*80}\n")
    
    def process_csv_file(self, csv_path: Path) -> Tuple[List[Dict], Dict]:
        """
        Process a single autolog CSV file.
        
        Args:
            csv_path: Path to CSV file
            
        Returns:
            Tuple of (layers list, summary data dict)
        """
        # Load CSV
        try:
            df = pd.read_csv(csv_path)
        except Exception as e:
            print(f"    ERROR loading CSV: {e}")
            return [], {}
        
        # Verify required columns
        required_cols = ['Elapsed Time (s)', 'Force (N)', 'Position (mm)']
        if not all(col in df.columns for col in required_cols):
            print(f"    ERROR: Missing required columns")
            return [], {}
        
        # Extract data
        time_data = df['Elapsed Time (s)'].to_numpy()
        force_data = df['Force (N)'].to_numpy()
        position_data = df['Position (mm)'].to_numpy()
        
        # Check for Phase column
        has_phase = 'Phase' in df.columns
        phase_data = df['Phase'].to_numpy() if has_phase else None
        
        # Smooth force data for visualization
        smoothed_force = self.calculator._apply_smoothing(force_data)
        
        # Detect layer boundaries
        if has_phase:
            boundaries = self._detect_boundaries_from_phases(phase_data)
        else:
            boundaries = self._detect_boundaries_from_motion(position_data, force_data)
        
        # Extract layer numbers from filename
        layer_numbers = self._extract_layer_numbers_from_filename(csv_path.name)
        
        # Analyze each layer
        layers = []
        for i, boundary in enumerate(boundaries):
            if i >= len(layer_numbers):
                break
            
            layer_num = layer_numbers[i]
            
            # Extract layer data
            start_idx = boundary['start']
            end_idx = boundary['end']
            
            layer_time = time_data[start_idx:end_idx+1]
            layer_pos = position_data[start_idx:end_idx+1]
            layer_force = force_data[start_idx:end_idx+1]
            
            # Make time relative to layer start
            layer_time_rel = layer_time - layer_time[0]
            
            # Calculate adhesion metrics
            try:
                metrics = self.calculator.calculate_from_arrays(
                    layer_time_rel,
                    layer_pos,
                    layer_force,
                    layer_number=layer_num
                )
                
                # Find peak index in original data
                peak_time_rel = metrics.get('peak_force_time', 0)
                peak_idx_in_layer = np.argmin(np.abs(layer_time_rel - peak_time_rel))
                peak_idx_global = start_idx + peak_idx_in_layer
                
                # Find pre-initiation index
                pre_init_time_rel = metrics.get('pre_initiation_time', 0)
                pre_init_idx_in_layer = np.argmin(np.abs(layer_time_rel - pre_init_time_rel))
                pre_init_idx_global = start_idx + pre_init_idx_in_layer
                
                # Find propagation end index
                prop_end_time_rel = metrics.get('propagation_end_time', peak_time_rel)
                prop_end_idx_in_layer = np.argmin(np.abs(layer_time_rel - prop_end_time_rel))
                prop_end_idx_global = start_idx + prop_end_idx_in_layer
                
                # Create layer object matching AnalysisPlotter format
                layer_obj = {
                    'number': layer_num,
                    'start_idx': start_idx,
                    'end_idx': end_idx,
                    'peak_idx': peak_idx_global,
                    'pre_init_idx': pre_init_idx_global,
                    'prop_end_idx': prop_end_idx_global,
                    'peak_time': time_data[peak_idx_global],
                    'peak_force': metrics.get('peak_force', np.nan),
                    'pre_init_time': time_data[pre_init_idx_global],
                    'prop_end_time': time_data[prop_end_idx_global],
                    'baseline': metrics.get('baseline_force', 0.0),
                    'pre_init_duration': metrics.get('pre_initiation_duration', 0.0),
                    'prop_duration': metrics.get('propagation_duration', 0.0),
                    'color': self.layer_colors[i % len(self.layer_colors)],
                    'metrics': metrics
                }
                
                layers.append(layer_obj)
                
            except Exception as e:
                print(f"    ERROR analyzing layer {layer_num}: {e}")
        
        # Create summary data dict
        summary_data = {
            'time_data': time_data,
            'force_data': force_data,
            'smoothed_force': smoothed_force,
            'position_data': position_data
        }
        
        return layers, summary_data
    
    def generate_plot(self, csv_path: Path, layers: List[Dict], 
                     summary_data: Dict, output_path: Path):
        """
        Generate comprehensive plot using AnalysisPlotter style.
        
        Args:
            csv_path: Path to CSV file
            layers: List of layer objects
            summary_data: Dictionary with time, force, position data
            output_path: Path to save plot
        """
        if not layers:
            return
        
        # Extract data from summary
        time_data = summary_data['time_data']
        force_data = summary_data['force_data']
        smoothed_force = summary_data['smoothed_force']
        
        # Generate title
        title = f"Continuous Motion Analysis: {csv_path.name}"
        
        # Use AnalysisPlotter to create the plot
        self.plotter.create_plot(
            time_data=time_data,
            force_data=force_data,
            smoothed_force=smoothed_force,
            layers=layers,
            title=title,
            save_path=output_path
        )
    
    def _extract_layer_numbers_from_filename(self, filename: str) -> List[int]:
        """Extract layer numbers from filename pattern autolog_L{start}-L{end}.csv"""
        import re
        match = re.search(r'L(\d+)-L(\d+)', filename)
        if match:
            start = int(match.group(1))
            end = int(match.group(2))
            return list(range(start, end + 1))
        
        # Try single layer pattern
        match = re.search(r'L(\d+)', filename)
        if match:
            return [int(match.group(1))]
        
        # No pattern found
        return list(range(1, 1000))
    
    def _detect_boundaries_from_phases(self, phase_data: np.ndarray) -> List[Dict]:
        """
        Detect layer boundaries using Phase column.
        Each layer starts at 'Exposure' and ends before next 'Exposure'.
        """
        phase_clean = pd.Series(phase_data).fillna('').astype(str).values
        
        # Find all Exposure phase starts
        exposure_indices = []
        for i, phase in enumerate(phase_clean):
            if phase == 'Exposure':
                if i == 0 or phase_clean[i-1] != 'Exposure':
                    exposure_indices.append(i)
        
        # Create boundaries
        boundaries = []
        for i in range(len(exposure_indices) - 1):
            boundaries.append({
                'start': exposure_indices[i],
                'end': exposure_indices[i + 1] - 1
            })
        
        # Add final layer
        if exposure_indices:
            boundaries.append({
                'start': exposure_indices[-1],
                'end': len(phase_clean) - 1
            })
        
        return boundaries
    
    def _detect_boundaries_from_motion(self, position_data: np.ndarray, 
                                      force_data: np.ndarray) -> List[Dict]:
        """
        Detect layer boundaries from motion profile (fallback).
        Looks for upward motion (peeling) followed by pause.
        """
        # Calculate velocity
        velocity = np.gradient(position_data)
        velocity_smooth = np.convolve(velocity, np.ones(10)/10, mode='same')
        
        # Find motion starts (negative velocity = moving up)
        motion_threshold = -0.005  # mm/sample
        is_moving = velocity_smooth < motion_threshold
        
        motion_starts = []
        for i in range(1, len(is_moving)):
            if is_moving[i] and not is_moving[i-1]:
                start = max(0, i - 50)
                motion_starts.append(start)
        
        # Create boundaries
        boundaries = []
        for i in range(len(motion_starts) - 1):
            boundaries.append({
                'start': motion_starts[i],
                'end': motion_starts[i + 1] - 1
            })
        
        # Add final segment
        if motion_starts:
            boundaries.append({
                'start': motion_starts[-1],
                'end': len(position_data) - 1
            })
        
        return boundaries


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Batch process continuous motion print data (overstep=0)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process all subfolders in ToProcess directory
  python batch_continuous_motion_processor.py --root "C:/PrintLogs/ToProcess"
  
  # Interactive mode (prompts for root folder)
  python batch_continuous_motion_processor.py
        """
    )
    
    parser.add_argument('--root', '-r', type=str,
                       help='Root folder to search for autolog CSV files (processes all subfolders)')
    
    args = parser.parse_args()
    
    # Get root path
    if args.root:
        root_path = args.root
    else:
        # Interactive mode
        print("\n" + "="*80)
        print("Batch Continuous Motion Processor (overstep=0)")
        print("="*80)
        print("\nThis will recursively process all autolog CSV files in subfolders.")
        root_path = input("\nEnter root folder path: ").strip('"')
    
    if not root_path:
        print("ERROR: No root path provided")
        return 1
    
    # Create processor and run
    processor = BatchContinuousMotionProcessor()
    processor.process_root_folder(root_path)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
