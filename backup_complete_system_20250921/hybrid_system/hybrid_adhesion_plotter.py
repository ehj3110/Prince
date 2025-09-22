"""
Hybrid Adhesion Metrics Plotter
===============================

Hybrid approach that combines:
- AdhesionMetricsCalculator for accurate metric calculations
- Original plotting logic for robust peak detection, layer segmentation, and visualization

This plotter automatically finds peaks, segments layers based on position data,
and creates focused time windows around each peeling event while using the
calculator for precise metric computations.

Author: Cheng Sun Lab Team
Date: September 19, 2025
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import find_peaks, savgol_filter
from typing import Dict, List, Optional, Tuple, Union
from pathlib import Path
import re

from adhesion_metrics_calculator import AdhesionMetricsCalculator


class HybridAdhesionPlotter:
    """
    Hybrid plotter that combines automatic layer detection with precise metric calculations.
    """
    
    def __init__(self, 
                 figure_size=(24, 18), 
                 dpi=300,
                 smoothing_window=3,
                 smoothing_polyorder=1):
        """
        Initialize the hybrid plotter.
        
        Args:
            figure_size: Tuple of (width, height) in inches
            dpi: Resolution for saved plots
            smoothing_window: Window for minimal smoothing (peak detection)
            smoothing_polyorder: Polynomial order for minimal smoothing
        """
        self.figure_size = figure_size
        self.dpi = dpi
        self.smoothing_window = smoothing_window
        self.smoothing_polyorder = smoothing_polyorder
        
        # Initialize calculator with our standard settings
        self.calculator = AdhesionMetricsCalculator(
            smoothing_window=11,
            smoothing_polyorder=2,
            baseline_threshold_factor=0.002,
            min_peak_height=0.01,
            min_peak_distance=50
        )
        
        # Color scheme
        self.layer_colors = ['red', 'blue', 'green', 'orange', 'purple', 'brown']
        
    def plot_from_csv(self,
                     csv_filepath: Union[str, Path],
                     title: Optional[str] = None,
                     save_path: Optional[Union[str, Path]] = None) -> plt.Figure:
        """
        Create comprehensive plot directly from CSV file using hybrid approach.
        
        Args:
            csv_filepath: Path to CSV file
            title: Custom title (auto-generated if None)
            save_path: Path to save plot (optional)
            
        Returns:
            matplotlib Figure object
        """
        # Load and prepare data
        df = self._load_and_prepare_data(csv_filepath)
        time_data = df['Time'].values
        force_data = df['Force'].values
        position_data = df['Position'].values
        
        # Extract layer numbers from filename
        layer_numbers = self._extract_layer_numbers(csv_filepath)
        
        # Auto-generate title if not provided
        if title is None:
            title = f"Adhesion Analysis L{layer_numbers[0]}-L{layer_numbers[-1]}"
        
        return self.plot_from_arrays(time_data, position_data, force_data, 
                                   layer_numbers, title, save_path)
    
    def plot_from_arrays(self,
                        time_data: np.ndarray,
                        position_data: np.ndarray,
                        force_data: np.ndarray,
                        layer_numbers: List[int],
                        title: str = "Adhesion Analysis",
                        save_path: Optional[Union[str, Path]] = None) -> plt.Figure:
        """
        Create comprehensive plot from data arrays using hybrid approach.
        
        Args:
            time_data: Time array (seconds)
            position_data: Position array (mm)
            force_data: Force array (N)
            layer_numbers: List of layer numbers
            title: Plot title
            save_path: Path to save plot (optional)
            
        Returns:
            matplotlib Figure object
        """
        print("="*80)
        print("HYBRID ADHESION ANALYSIS AND VISUALIZATION")
        print("="*80)
        
        print(f"Data loaded: {len(time_data)} points")
        print(f"Time range: {time_data.min():.3f} to {time_data.max():.3f} seconds")
        print(f"Force range: {force_data.min():.6f} to {force_data.max():.6f} N")
        
        # Step 1: Apply minimal smoothing for peak detection
        smoothed_force = savgol_filter(force_data, 
                                     window_length=self.smoothing_window, 
                                     polyorder=self.smoothing_polyorder)
        
        # Step 2: Detect peaks using robust method from original
        peaks = self._detect_peaks(force_data, smoothed_force)
        
        if len(peaks) < len(layer_numbers):
            print(f"WARNING: Found {len(peaks)} peaks but expected {len(layer_numbers)} layers")
            # Adjust layer numbers to match found peaks
            layer_numbers = layer_numbers[:len(peaks)]
        
        print(f"Detected peaks at indices: {peaks}")
        for i, peak_idx in enumerate(peaks):
            if i < len(layer_numbers):
                layer_num = layer_numbers[i]
                print(f"  Layer {layer_num}: Peak at {time_data[peak_idx]:.2f}s, Force={smoothed_force[peak_idx]:.6f}N")
        
        # Step 3: Find layer boundaries based on position data
        layer_boundaries = self._find_layer_boundaries(peaks, position_data, time_data, layer_numbers)
        
        # Step 4: Calculate metrics for each layer and create layer objects
        layers = []
        for i, peak_idx in enumerate(peaks):
            if i >= len(layer_numbers):
                break
                
            layer_num = layer_numbers[i]
            start_idx, end_idx = layer_boundaries[i]
            
            print(f"\n--- Processing Layer {layer_num} ---")
            
            # Extract layer segment data
            segment_time = time_data[start_idx:end_idx+1] - time_data[start_idx]  # Reset to start at 0
            segment_position = position_data[start_idx:end_idx+1]
            segment_force = force_data[start_idx:end_idx+1]
            
            # Calculate metrics using our calculator
            try:
                metrics = self.calculator.calculate_from_arrays(
                    segment_time, segment_position, segment_force, layer_number=layer_num
                )
                
                # Convert metrics back to global time indices
                layer_obj = self._create_layer_object(
                    metrics, peak_idx, start_idx, end_idx, time_data, force_data, 
                    smoothed_force, layer_num, i
                )
                
                layers.append(layer_obj)
                
                print(f"  Metrics calculated successfully")
                print(f"    Peak Force: {metrics['peak_force']:.6f} N")
                print(f"    Baseline: {metrics['baseline_force']:.6f} N")
                print(f"    Work of Adhesion: {metrics['work_of_adhesion_corrected_mJ']:.3f} mJ")
                
            except Exception as e:
                print(f"  Error calculating metrics for layer {layer_num}: {e}")
                continue
        
        # Step 5: Create the visualization using original plotting logic
        fig = self._create_comprehensive_plot(time_data, force_data, smoothed_force, layers, title)
        
        # Step 6: Save if requested
        if save_path:
            plt.savefig(save_path, dpi=self.dpi, bbox_inches='tight', facecolor='white')
            print(f"\nPlot saved as: {save_path}")
        
        # Step 7: Display the plot
        plt.show()
        
        return fig
    
    def _load_and_prepare_data(self, csv_filepath: Union[str, Path]) -> pd.DataFrame:
        """Load and standardize CSV data."""
        df = pd.read_csv(csv_filepath)
        
        # Standardize column names
        if 'Elapsed Time (s)' in df.columns:
            df = df.rename(columns={'Elapsed Time (s)': 'Time'})
        if 'Position (mm)' in df.columns:
            df = df.rename(columns={'Position (mm)': 'Position'})
        if 'Force (N)' in df.columns:
            df = df.rename(columns={'Force (N)': 'Force'})
            
        return df
    
    def _extract_layer_numbers(self, csv_filepath: Union[str, Path]) -> List[int]:
        """Extract layer numbers from filename."""
        filename = str(csv_filepath)
        layer_match = re.search(r'L(\d+)-L(\d+)', filename)
        if layer_match:
            start_layer = int(layer_match.group(1))
            end_layer = int(layer_match.group(2))
            layer_numbers = list(range(start_layer, end_layer + 1))
            print(f"Detected layers from filename: {layer_numbers}")
        else:
            layer_numbers = [1, 2, 3]  # Fallback
            print("Using fallback layer numbers: [1, 2, 3]")
        return layer_numbers
    
    def _detect_peaks(self, force_data: np.ndarray, smoothed_force: np.ndarray) -> np.ndarray:
        """Detect peaks using the original's robust method."""
        # Try multiple peak detection strategies (from original)
        peaks_raw, _ = find_peaks(force_data, height=0.08, distance=150, prominence=0.05)
        peaks_smooth, _ = find_peaks(smoothed_force, height=0.08, distance=150, prominence=0.05)
        
        if len(peaks_smooth) >= 3:
            peaks = peaks_smooth
            print("Using smoothed data peaks (better visual presentation)")
        elif len(peaks_raw) >= 3:
            peaks = peaks_raw  
            print("Using raw data peaks (fallback)")
        else:
            # Emergency fallback
            peaks, _ = find_peaks(smoothed_force, height=0.1, distance=200)
            print("Using original smoothed peaks (emergency fallback)")
            
        return peaks
    
    def _find_layer_boundaries(self, peaks: np.ndarray, position_data: np.ndarray, 
                             time_data: np.ndarray, layer_numbers: List[int]) -> List[Tuple[int, int]]:
        """Find layer boundaries based on position data (from original)."""
        boundaries = []
        
        for i, peak_idx in enumerate(peaks):
            if i >= len(layer_numbers):
                break
                
            # Find the start of this layer
            layer_start_idx = 0 if i == 0 else boundaries[i-1][1]  # Start after previous layer
            
            # Search for stable position before this peak
            search_start = max(layer_start_idx, peak_idx - int(15 * 50))  # 15 seconds before peak
            
            if search_start < peak_idx:
                stable_position = position_data[search_start:peak_idx].mean()
                position_threshold = 0.05  # 0.05mm threshold for "stable"
                
                for j in range(search_start, peak_idx):
                    if abs(position_data[j] - stable_position) > position_threshold:
                        layer_start_idx = max(layer_start_idx, j - 50)  # Buffer before movement
                        break
            
            # Find end of this layer
            if i < len(peaks) - 1:
                # Not the last layer - end before next layer starts
                next_peak_idx = peaks[i + 1]
                search_end = min(len(position_data) - 1, peak_idx + int(20 * 50))  # 20 seconds after peak
                search_end = min(search_end, next_peak_idx - int(5 * 50))  # 5 seconds before next peak
            else:
                # Last layer - can go to end
                search_end = min(len(position_data) - 1, peak_idx + int(20 * 50))
            
            layer_end_idx = search_end
            boundaries.append((layer_start_idx, layer_end_idx))
            
            print(f"Layer {layer_numbers[i]} boundaries: indices {layer_start_idx}-{layer_end_idx}, "
                  f"times {time_data[layer_start_idx]:.3f}-{time_data[layer_end_idx]:.3f}s")
        
        return boundaries
    
    def _create_layer_object(self, metrics: Dict, peak_idx: int, start_idx: int, end_idx: int,
                           time_data: np.ndarray, force_data: np.ndarray, smoothed_force: np.ndarray,
                           layer_num: int, color_index: int) -> Dict:
        """Create layer object combining metrics with plotting data."""
        color = self.layer_colors[color_index % len(self.layer_colors)]
        
        # Convert relative times back to global times
        peak_time = time_data[peak_idx]
        peak_force = force_data[peak_idx]
        baseline = metrics['baseline_force']
        
        # Convert metric times to global indices (approximate)
        pre_init_global_time = time_data[start_idx] + metrics['pre_initiation_time']
        prop_end_global_time = time_data[start_idx] + metrics['propagation_end_time']
        
        # Find closest indices
        pre_init_idx = start_idx + np.argmin(np.abs(time_data[start_idx:end_idx+1] - pre_init_global_time))
        prop_end_idx = start_idx + np.argmin(np.abs(time_data[start_idx:end_idx+1] - prop_end_global_time))
        
        layer_obj = {
            'number': layer_num,
            'start_idx': start_idx,
            'end_idx': end_idx,
            'pre_init_idx': pre_init_idx,
            'peak_idx': peak_idx,
            'prop_end_idx': prop_end_idx,
            'color': color,
            'baseline': baseline,
            'peak_time': peak_time,
            'peak_force': peak_force,
            'pre_init_time': time_data[pre_init_idx],
            'prop_end_time': time_data[prop_end_idx],
            'pre_init_duration': metrics['pre_initiation_duration'],
            'prop_duration': metrics['propagation_duration'],
            'force_range': peak_force - baseline,
            'metrics': metrics  # Store full metrics for reference
        }
        
        return layer_obj
    
    def _create_comprehensive_plot(self, time_data: np.ndarray, force_data: np.ndarray, 
                                 smoothed_force: np.ndarray, layers: List[Dict], title: str) -> plt.Figure:
        """Create the comprehensive 4-subplot visualization using original plotting logic."""
        fig = plt.figure(figsize=self.figure_size)
        gs = fig.add_gridspec(2, 2, height_ratios=[1, 1], width_ratios=[1, 1])
        
        # Subplot 1: Complete Overview (Top-Left)
        ax_overview = fig.add_subplot(gs[0, 0])
        self._plot_overview(ax_overview, time_data, force_data, smoothed_force, layers)
        
        # Subplots 2-4: Individual Layer Details
        subplot_positions = [gs[0, 1], gs[1, 0], gs[1, 1]]
        
        for i, layer in enumerate(layers[:3]):  # Limit to first 3 layers
            if i < len(subplot_positions):
                ax = fig.add_subplot(subplot_positions[i])
                self._plot_individual_layer(ax, time_data, force_data, smoothed_force, layer)
        
        # Main title and layout
        fig.suptitle(f'{title}:\nPeeling Stages with Shaded Bands and Event Markers', 
                     fontsize=20, fontweight='bold', y=0.98)
        
        plt.tight_layout()
        plt.subplots_adjust(top=0.92, hspace=0.3, wspace=0.3)
        
        return fig
    
    def _plot_overview(self, ax, time_data, force_data, smoothed_force, layers):
        """Plot the complete overview subplot (from original logic)."""
        # Plot raw and smoothed data
        ax.plot(time_data, force_data, 'k-', linewidth=1, alpha=0.4, label='Raw Force Data')
        ax.plot(time_data, smoothed_force, 'navy', linewidth=2.5, alpha=0.9, label='Smoothed Force (Analysis)')
        
        # Add layer regions and annotations
        for layer in layers:
            color = layer['color']
            
            # Layer boundary shading (very light)
            layer_start_time = time_data[layer['start_idx']]
            layer_end_time = time_data[layer['end_idx']]
            ax.axvspan(layer_start_time, layer_end_time, alpha=0.08, color=color,
                       label=f'Layer {layer["number"]} Region')
            
            # Peak force marker and line
            ax.plot(layer['peak_time'], layer['peak_force'], 'o', color=color, 
                    markersize=12, zorder=5, markeredgecolor='black', markeredgewidth=2)
            ax.axvline(x=layer['peak_time'], color=color, linestyle='--', 
                       linewidth=3, alpha=0.8, zorder=3)
            
            # Baseline horizontal line
            ax.plot([layer['pre_init_time'], layer['prop_end_time']], 
                    [layer['baseline'], layer['baseline']], 
                    color=color, linestyle='-', linewidth=3, alpha=0.9, zorder=2)
            
            # Propagation end marker
            ax.axvline(x=layer['prop_end_time'], color='purple', linestyle=':', 
                       linewidth=2, alpha=0.8, zorder=3)
            
            # Layer number annotation
            ax.annotate(f'L{layer["number"]}', 
                       xy=(layer['peak_time'], layer['peak_force']),
                       xytext=(layer['peak_time'], layer['peak_force'] + 0.02),
                       ha='center', va='bottom', fontsize=12, fontweight='bold',
                       color=color, zorder=6)
        
        ax.set_xlabel('Time (s)', fontsize=14, fontweight='bold')
        ax.set_ylabel('Force (N)', fontsize=14, fontweight='bold')
        ax.set_title('Complete Force Profile - Multiple Layers', fontsize=16, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=11, loc='upper right')
    
    def _plot_individual_layer(self, ax, time_data, force_data, smoothed_force, layer):
        """Plot individual layer detail subplot (from original logic)."""
        color = layer['color']
        
        # Define focused window around the peeling event
        buffer = 100  # Points before and after the peeling event
        window_start = max(layer['start_idx'], layer['pre_init_idx'] - buffer)
        window_end = min(layer['end_idx'], layer['prop_end_idx'] + buffer)
        
        # Extract windowed data
        window_time = time_data[window_start:window_end]
        window_force = force_data[window_start:window_end]
        window_smoothed = smoothed_force[window_start:window_end]
        
        # Plot force data
        ax.plot(window_time, window_force, 'k-', linewidth=1, alpha=0.4, label='Raw Force')
        ax.plot(window_time, window_smoothed, color=color, linewidth=3.5, alpha=0.95, 
               label='Smoothed Force (Analysis)', zorder=3)
        
        # Shaded bands for peeling stages
        ax.axvspan(layer['pre_init_time'], layer['peak_time'], 
                  color='lightblue', alpha=0.5, label='Pre-Initiation', zorder=1)
        ax.axvspan(layer['peak_time'], layer['prop_end_time'], 
                  color='lightcoral', alpha=0.5, label='Propagation', zorder=1)
        
        # Post-propagation shading if visible
        if layer['prop_end_time'] < window_time.max():
            ax.axvspan(layer['prop_end_time'], window_time.max(), 
                      color='lightyellow', alpha=0.3, zorder=1)
        
        # Vertical lines and markers
        ax.axvline(x=layer['peak_time'], color=color, linestyle='--', linewidth=4, zorder=4)
        ax.plot(layer['peak_time'], layer['peak_force'], 'o', color=color, 
               markersize=14, zorder=5, markeredgecolor='black', markeredgewidth=2,
               label=f'Peak: {layer["peak_force"]:.4f}N')
        
        ax.axvline(x=layer['prop_end_time'], color='purple', linestyle=':', linewidth=4, zorder=4)
        ax.plot(layer['prop_end_time'], smoothed_force[layer['prop_end_idx']], 's', 
               color='purple', markersize=10, zorder=5, markeredgecolor='black', markeredgewidth=1,
               label='Prop End')
        
        # Baseline line
        ax.axhline(y=layer['baseline'], color='gray', linestyle='--', linewidth=3, alpha=0.6,
                  label=f'Baseline: {layer["baseline"]:.4f}N', zorder=2)
        
        # Annotations (from original)
        self._add_layer_annotations(ax, layer)
        
        # Formatting
        ax.set_xlabel('Time (s)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Force (N)', fontsize=12, fontweight='bold')
        ax.set_title(f'Layer {layer["number"]} - Peeling Stages with Shaded Bands', 
                    fontsize=14, fontweight='bold', color=color)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=10, loc='upper left', ncol=1, framealpha=0.9, 
                 fancybox=True, shadow=True)
        
        # Set appropriate limits (from original)
        y_min = layer['baseline'] - 0.045
        y_max = layer['peak_force'] + 0.015
        ax.set_ylim(y_min, y_max)
        
        x_margin = (layer['prop_end_time'] - layer['pre_init_time']) * 0.3
        ax.set_xlim(layer['pre_init_time'] - x_margin, layer['prop_end_time'] + x_margin)
    
    def _add_layer_annotations(self, ax, layer):
        """Add measurement annotations (from original logic)."""
        # Force range arrow and annotation
        force_range_x = layer['peak_time'] + (layer['prop_end_time'] - layer['peak_time']) * 0.7
        ax.annotate('', xy=(force_range_x, layer['peak_force']), 
                   xytext=(force_range_x, layer['baseline']),
                   arrowprops=dict(arrowstyle='<->', color='black', lw=3))
        ax.text(force_range_x + 0.3, (layer['peak_force'] + layer['baseline'])/2, 
               f'ΔF = {layer["force_range"]:.4f}N', 
               rotation=90, va='center', fontsize=11, fontweight='bold',
               bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
        
        # Time duration annotations
        y_annotation = layer['baseline'] - 0.015
        
        # Pre-initiation duration
        ax.annotate('', xy=(layer['peak_time'], y_annotation), 
                   xytext=(layer['pre_init_time'], y_annotation),
                   arrowprops=dict(arrowstyle='<->', color='blue', lw=3))
        ax.text((layer['peak_time'] + layer['pre_init_time'])/2, y_annotation - 0.008, 
               f't_pre = {layer["pre_init_duration"]:.2f}s', 
               ha='center', fontsize=10, color='blue', fontweight='bold',
               bbox=dict(boxstyle='round,pad=0.2', facecolor='lightblue', alpha=0.8))
        
        # Propagation duration
        y_annotation2 = layer['baseline'] - 0.030
        ax.annotate('', xy=(layer['prop_end_time'], y_annotation2), 
                   xytext=(layer['peak_time'], y_annotation2),
                   arrowprops=dict(arrowstyle='<->', color='red', lw=3))
        
        text_x_position = layer['prop_end_time'] + (layer['prop_end_time'] - layer['peak_time']) * 0.1
        ax.text(text_x_position, y_annotation2 - 0.008, 
               f't_prop = {layer["prop_duration"]:.2f}s', 
               ha='left', fontsize=10, color='red', fontweight='bold',
               bbox=dict(boxstyle='round,pad=0.2', facecolor='lightcoral', alpha=0.8))
    
    def print_metrics_summary(self, layers: List[Dict]):
        """Print comprehensive metrics summary."""
        print("\n" + "="*100)
        print("HYBRID ANALYSIS METRICS SUMMARY")
        print("="*100)
        
        print(f"{'Layer':<8} {'Peak Force':<12} {'Baseline':<12} {'Force Range':<12} {'Pre-Init':<12} {'Propagation':<12} {'Work':<12}")
        print(f"{'':8} {'(N)':<12} {'(N)':<12} {'(N)':<12} {'Time (s)':<12} {'Time (s)':<12} {'(mJ)':<12}")
        print("-" * 100)
        
        for layer in layers:
            layer_num = layer['number']
            peak_force = layer['peak_force']
            baseline = layer['baseline']
            force_range = layer['force_range']
            pre_init_duration = layer['pre_init_duration']
            prop_duration = layer['prop_duration']
            work = layer['metrics']['work_of_adhesion_corrected_mJ']
            
            print(f"{layer_num:<8} {peak_force:<12.6f} {baseline:<12.6f} "
                  f"{force_range:<12.6f} {pre_init_duration:<12.3f} "
                  f"{prop_duration:<12.3f} {work:<12.3f}")
        
        print("\n" + "="*100)


# Example usage function
def example_usage():
    """Example of how to use the HybridAdhesionPlotter."""
    print("Example Usage of HybridAdhesionPlotter:")
    print("="*50)
    print("""
    # Create plotter instance
    plotter = HybridAdhesionPlotter()
    
    # Method 1: Direct from CSV (recommended)
    fig = plotter.plot_from_csv(
        "autolog_L48-L50.csv",
        title="L48-L50 Hybrid Analysis",
        save_path="hybrid_L48_L50_analysis.png"
    )
    
    # Method 2: From arrays
    import pandas as pd
    df = pd.read_csv("autolog_L48-L50.csv")
    time_data = df['Time'].values
    position_data = df['Position'].values  
    force_data = df['Force'].values
    
    fig = plotter.plot_from_arrays(
        time_data, position_data, force_data,
        layer_numbers=[48, 49, 50],
        title="Custom Analysis",
        save_path="custom_analysis.png"
    )
    
    # The plotter automatically:
    # - Finds peaks in the data
    # - Segments layers based on position
    # - Calculates precise metrics using the calculator
    # - Creates beautiful plots with proper windowing
    """)


if __name__ == "__main__":
    example_usage()
