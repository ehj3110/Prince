"""
Continuous Motion Post-Processing Analyzer (overstep=0)
=======================================================

Post-processes autolog CSV files from continuous motion prints where overstep=0.
In this mode:
- No retraction phase (stage moves directly to layer height and stops)
- Peak force occurs at END of lift or DURING pause
- Analysis includes full Lift + Pause window

This script:
1. Loads autolog CSV files from a folder
2. Detects layer boundaries based on exposure phases
3. Analyzes each layer's full cycle (Exposure → Lift → Pause)
4. Calculates adhesion metrics using the same calculator as live analysis
5. Generates plots showing force profiles with detected peaks

Usage:
    python continuous_motion_analyzer.py --folder "path/to/autolog_folder"
    
    Or interactively:
    python continuous_motion_analyzer.py

Author: Cheng Sun Lab Team
Date: February 5, 2026
"""

import os
import sys
from pathlib import Path
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import List, Dict, Tuple
from scipy.signal import find_peaks

# Add parent directory to path to import support_modules
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from support_modules.adhesion_metrics_calculator import AdhesionMetricsCalculator


class ContinuousMotionAnalyzer:
    """
    Analyzes continuous motion print data (overstep=0) where there is no retraction phase.
    Identifies peaks across full Lift + Pause window for each layer.
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
        
    def process_folder(self, folder_path: str, output_dir: str = None):
        """
        Process all autolog CSV files in a folder.
        
        Args:
            folder_path: Path to folder containing autolog CSV files
            output_dir: Directory to save output plots (default: same as input folder)
        """
        folder = Path(folder_path)
        
        if not folder.exists():
            print(f"ERROR: Folder not found: {folder}")
            return
        
        # Find all autolog CSV files
        csv_files = sorted(folder.glob("autolog_*.csv"))
        
        if not csv_files:
            print(f"No autolog CSV files found in {folder}")
            return
        
        print(f"\nFound {len(csv_files)} autolog file(s):")
        for f in csv_files:
            print(f"  - {f.name}")
        
        # Set output directory
        if output_dir is None:
            output_dir = folder / "continuous_motion_analysis"
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(exist_ok=True)
        print(f"\nOutput directory: {output_dir}")
        
        # Process each file
        all_results = []
        for csv_file in csv_files:
            print(f"\n{'='*70}")
            print(f"Processing: {csv_file.name}")
            print('='*70)
            
            results = self.process_csv_file(csv_file)
            
            if results:
                all_results.extend(results)
                
                # Generate plot for this file
                plot_path = output_dir / f"{csv_file.stem}_analysis.png"
                self.plot_layer_analysis(csv_file, results, plot_path)
        
        # Generate summary CSV
        if all_results:
            summary_path = output_dir / "adhesion_metrics_summary.csv"
            self.save_summary_csv(all_results, summary_path)
            print(f"\n✓ Summary saved to: {summary_path}")
        
        print(f"\n{'='*70}")
        print(f"Analysis complete! Processed {len(all_results)} layers.")
        print(f"Results saved to: {output_dir}")
        print('='*70)
    
    def process_csv_file(self, csv_path: Path) -> List[Dict]:
        """
        Process a single autolog CSV file.
        
        Args:
            csv_path: Path to autolog CSV file
            
        Returns:
            List of layer result dictionaries
        """
        # Load CSV
        try:
            df = pd.read_csv(csv_path)
        except Exception as e:
            print(f"ERROR loading CSV: {e}")
            return []
        
        # Verify required columns
        required_cols = ['Elapsed Time (s)', 'Force (N)', 'Position (mm)']
        if not all(col in df.columns for col in required_cols):
            print(f"ERROR: Missing required columns. Found: {df.columns.tolist()}")
            return []
        
        # Extract data
        time_data = df['Elapsed Time (s)'].to_numpy()
        force_data = df['Force (N)'].to_numpy()
        position_data = df['Position (mm)'].to_numpy()
        
        # Check for Phase column (preferred method)
        has_phase = 'Phase' in df.columns
        phase_data = df['Phase'].to_numpy() if has_phase else None
        
        print(f"Loaded {len(time_data)} data points")
        print(f"Time range: {time_data[0]:.2f}s to {time_data[-1]:.2f}s")
        print(f"Phase column: {'Found' if has_phase else 'Not found'}")
        
        # Detect layer boundaries
        if has_phase:
            boundaries = self._detect_boundaries_from_phases(phase_data)
        else:
            boundaries = self._detect_boundaries_from_motion(position_data, force_data)
        
        print(f"Detected {len(boundaries)} layer(s)")
        
        # Extract layer numbers from filename
        layer_numbers = self._extract_layer_numbers_from_filename(csv_path.name)
        
        # Analyze each layer
        results = []
        for i, boundary in enumerate(boundaries):
            layer_num = layer_numbers[i] if i < len(layer_numbers) else i + 1
            
            print(f"\n--- Layer {layer_num} ---")
            print(f"  Analysis window: indices {boundary['start']} to {boundary['end']}")
            
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
                
                result = {
                    'file': csv_path.name,
                    'layer_number': layer_num,
                    'start_idx': start_idx,
                    'end_idx': end_idx,
                    'peak_idx': peak_idx_global,
                    'peak_force_N': metrics.get('peak_force', np.nan),
                    'peak_time_s': layer_time[peak_idx_in_layer],
                    'peak_position_mm': layer_pos[peak_idx_in_layer],
                    'work_of_adhesion_mJ': metrics.get('work_of_adhesion_mJ', np.nan),
                    'pre_initiation_distance_mm': metrics.get('pre_initiation_distance', np.nan),
                    'propagation_distance_mm': metrics.get('propagation_distance', np.nan),
                    'total_peel_distance_mm': metrics.get('total_peel_distance', np.nan),
                    'pre_initiation_time_s': metrics.get('pre_initiation_time', np.nan),
                    'propagation_duration_s': metrics.get('propagation_duration', np.nan),
                    'total_peel_duration_s': metrics.get('total_peel_duration', np.nan),
                }
                
                results.append(result)
                
                print(f"  ✓ Peak force: {result['peak_force_N']:.4f} N at t={result['peak_time_s']:.2f}s")
                print(f"    Work of adhesion: {result['work_of_adhesion_mJ']:.4f} mJ")
                print(f"    Peel distance: {result['total_peel_distance_mm']:.3f} mm")
                
            except Exception as e:
                print(f"  ✗ ERROR calculating metrics: {e}")
                import traceback
                traceback.print_exc()
        
        return results
    
    def _extract_layer_numbers_from_filename(self, filename: str) -> List[int]:
        """
        Extract layer numbers from filename pattern autolog_L{start}-L{end}.csv
        Returns list of layer numbers.
        """
        import re
        match = re.search(r'L(\d+)-L(\d+)', filename)
        if match:
            start = int(match.group(1))
            end = int(match.group(2))
            return list(range(start, end + 1))
        
        # Try single layer pattern autolog_L{num}.csv
        match = re.search(r'L(\d+)', filename)
        if match:
            return [int(match.group(1))]
        
        # No pattern found, return sequential numbers
        return list(range(1, 1000))  # Arbitrarily large range
    
    def _detect_boundaries_from_phases(self, phase_data: np.ndarray) -> List[Dict]:
        """
        Detect layer boundaries using Phase column.
        Each layer starts at 'Exposure' and ends before next 'Exposure'.
        
        Args:
            phase_data: Array of phase strings
            
        Returns:
            List of boundary dicts with 'start' and 'end' indices
        """
        # Clean phase data
        phase_clean = pd.Series(phase_data).fillna('').astype(str).values
        
        # Find all Exposure phase starts
        exposure_indices = []
        for i, phase in enumerate(phase_clean):
            if phase == 'Exposure':
                # Check if this is the start of an exposure block (not middle of one)
                if i == 0 or phase_clean[i-1] != 'Exposure':
                    exposure_indices.append(i)
        
        print(f"Found {len(exposure_indices)} exposure event(s) at indices: {exposure_indices}")
        
        # Create boundaries: each layer is from one exposure to the next
        boundaries = []
        for i in range(len(exposure_indices) - 1):
            start = exposure_indices[i]
            end = exposure_indices[i + 1] - 1  # Stop before next exposure
            boundaries.append({'start': start, 'end': end})
        
        # Add final layer (from last exposure to end of data)
        if exposure_indices:
            boundaries.append({
                'start': exposure_indices[-1],
                'end': len(phase_clean) - 1
            })
        
        return boundaries
    
    def _detect_boundaries_from_motion(self, position_data: np.ndarray, 
                                      force_data: np.ndarray) -> List[Dict]:
        """
        Detect layer boundaries from motion profile (fallback when no Phase column).
        Looks for upward motion (stage moving away = peeling) followed by pause.
        
        Args:
            position_data: Position array (mm)
            force_data: Force array (N)
            
        Returns:
            List of boundary dicts with 'start' and 'end' indices
        """
        # Calculate velocity (derivative of position)
        velocity = np.gradient(position_data)
        velocity_smooth = np.convolve(velocity, np.ones(10)/10, mode='same')
        
        # Find motion starts: where velocity becomes significantly negative (moving up/peeling)
        motion_threshold = -0.005  # mm/sample (negative = moving up in z)
        is_moving = velocity_smooth < motion_threshold
        
        # Find transitions from stationary to moving
        motion_starts = []
        for i in range(1, len(is_moving)):
            if is_moving[i] and not is_moving[i-1]:
                # Start of motion - go back a bit to capture baseline
                start = max(0, i - 50)
                motion_starts.append(start)
        
        print(f"Detected {len(motion_starts)} motion start(s)")
        
        # Create boundaries: from each motion start to next motion start
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
    
    def plot_layer_analysis(self, csv_path: Path, results: List[Dict], 
                           output_path: Path):
        """
        Generate comprehensive plot showing all layers with detected peaks.
        
        Args:
            csv_path: Path to CSV file
            results: List of layer result dictionaries
            output_path: Path to save plot
        """
        if not results:
            print("No results to plot")
            return
        
        # Load data
        df = pd.read_csv(csv_path)
        time_data = df['Elapsed Time (s)'].to_numpy()
        force_data = df['Force (N)'].to_numpy()
        position_data = df['Position (mm)'].to_numpy()
        
        # Create figure
        fig, axes = plt.subplots(2, 1, figsize=(14, 10), sharex=True)
        
        # Plot 1: Force over time with layer boundaries and peaks
        ax1 = axes[0]
        ax1.plot(time_data, force_data, 'k-', linewidth=0.8, alpha=0.6, label='Raw force')
        
        # Smooth force for visualization
        smoothed_force = self.calculator._apply_smoothing(force_data)
        ax1.plot(time_data, smoothed_force, 'b-', linewidth=1.5, alpha=0.8, label='Smoothed force')
        
        # Mark layer boundaries and peaks
        for i, result in enumerate(results):
            layer_num = result['layer_number']
            start_idx = result['start_idx']
            end_idx = result['end_idx']
            peak_idx = result['peak_idx']
            
            # Shade layer region
            ax1.axvspan(time_data[start_idx], time_data[end_idx], 
                       alpha=0.1, color=f'C{i % 10}')
            
            # Mark peak
            ax1.plot(time_data[peak_idx], force_data[peak_idx], 
                    'r*', markersize=15, markeredgecolor='darkred', 
                    markeredgewidth=1.5, zorder=10)
            
            # Label layer
            mid_time = (time_data[start_idx] + time_data[end_idx]) / 2
            ax1.text(mid_time, ax1.get_ylim()[1] * 0.95, f'L{layer_num}',
                    ha='center', va='top', fontsize=9, fontweight='bold')
        
        ax1.set_ylabel('Force (N)', fontsize=12, fontweight='bold')
        ax1.set_title(f'Continuous Motion Analysis: {csv_path.name}', 
                     fontsize=14, fontweight='bold')
        ax1.legend(loc='upper right')
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Position over time
        ax2 = axes[1]
        ax2.plot(time_data, position_data, 'g-', linewidth=1.2, label='Stage position')
        
        # Mark layer boundaries
        for i, result in enumerate(results):
            start_idx = result['start_idx']
            end_idx = result['end_idx']
            peak_idx = result['peak_idx']
            
            # Shade layer region
            ax2.axvspan(time_data[start_idx], time_data[end_idx], 
                       alpha=0.1, color=f'C{i % 10}')
            
            # Mark peak position
            ax2.plot(time_data[peak_idx], position_data[peak_idx], 
                    'r*', markersize=12, markeredgecolor='darkred', 
                    markeredgewidth=1.5, zorder=10)
        
        ax2.set_xlabel('Time (s)', fontsize=12, fontweight='bold')
        ax2.set_ylabel('Z Position (mm)', fontsize=12, fontweight='bold')
        ax2.legend(loc='upper right')
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"✓ Plot saved: {output_path}")
    
    def save_summary_csv(self, results: List[Dict], output_path: Path):
        """
        Save summary of all layers to CSV.
        
        Args:
            results: List of layer result dictionaries
            output_path: Path to save CSV
        """
        df = pd.DataFrame(results)
        
        # Reorder columns for clarity
        col_order = [
            'file', 'layer_number',
            'peak_force_N', 'peak_time_s', 'peak_position_mm',
            'work_of_adhesion_mJ',
            'pre_initiation_distance_mm', 'propagation_distance_mm', 'total_peel_distance_mm',
            'pre_initiation_time_s', 'propagation_duration_s', 'total_peel_duration_s',
            'start_idx', 'end_idx', 'peak_idx'
        ]
        
        # Only keep columns that exist
        col_order = [col for col in col_order if col in df.columns]
        df = df[col_order]
        
        df.to_csv(output_path, index=False)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Analyze continuous motion print data (overstep=0)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process folder with autolog files
  python continuous_motion_analyzer.py --folder "C:/PrintLogs/MyPrint"
  
  # Specify custom output directory
  python continuous_motion_analyzer.py --folder "C:/PrintLogs/MyPrint" --output "C:/Analysis"
  
  # Interactive mode (prompts for folder)
  python continuous_motion_analyzer.py
        """
    )
    
    parser.add_argument('--folder', '-f', type=str,
                       help='Folder containing autolog CSV files')
    parser.add_argument('--output', '-o', type=str,
                       help='Output directory for plots and summary (default: creates subfolder in input folder)')
    
    args = parser.parse_args()
    
    # Get folder path
    if args.folder:
        folder_path = args.folder
    else:
        # Interactive mode
        print("\n" + "="*70)
        print("Continuous Motion Analyzer (overstep=0)")
        print("="*70)
        folder_path = input("\nEnter folder path containing autolog CSV files: ").strip('"')
    
    if not folder_path:
        print("ERROR: No folder path provided")
        return 1
    
    # Create analyzer and process
    analyzer = ContinuousMotionAnalyzer()
    analyzer.process_folder(folder_path, args.output)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
