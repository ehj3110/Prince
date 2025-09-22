"""
Adhesion Metrics Plotter
========================

Dedicated plotting module for adhesion metrics visualization.
Takes pre-calculated metrics from AdhesionMetricsCalculator and creates
professional visualizations with shaded bands and event markers.

This module is purely for visualization - all metric calculations
should be done by AdhesionMetricsCalculator before calling these functions.

Author: Cheng Sun Lab Team
Date: September 19, 2025
"""

import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Optional, Tuple, Union
from pathlib import Path


class AdhesionMetricsPlotter:
    """
    Dedicated plotter for adhesion metrics visualization.
    """
    
    def __init__(self, figure_size=(24, 18), dpi=300, style='default'):
        """
        Initialize the plotter with visualization settings.
        
        Args:
            figure_size: Tuple of (width, height) in inches
            dpi: Resolution for saved plots
            style: Matplotlib style to use
        """
        self.figure_size = figure_size
        self.dpi = dpi
        self.style = style
        
        # Color scheme for layers
        self.layer_colors = ['red', 'blue', 'green', 'orange', 'purple', 'brown']
        
        # Plotting style settings
        self.raw_force_style = {'color': 'black', 'linewidth': 1, 'alpha': 0.4}
        self.smoothed_force_style = {'linewidth': 3.5, 'alpha': 0.95, 'zorder': 3}
        self.peak_marker_style = {'marker': 'o', 'markersize': 14, 'zorder': 5, 
                                'markeredgecolor': 'black', 'markeredgewidth': 2}
        self.prop_end_marker_style = {'marker': 's', 'color': 'purple', 'markersize': 10, 
                                    'zorder': 5, 'markeredgecolor': 'black', 'markeredgewidth': 1}
        
        # Shaded band settings
        self.pre_initiation_color = 'lightblue'
        self.propagation_color = 'lightcoral'
        self.post_propagation_color = 'lightyellow'
        self.band_alpha = 0.5
        
    def plot_comprehensive_analysis(self, 
                                  time_data: np.ndarray,
                                  force_data: np.ndarray,
                                  smoothed_force: np.ndarray,
                                  layer_metrics: List[Dict],
                                  title: str = "Adhesion Analysis",
                                  save_path: Optional[Union[str, Path]] = None) -> plt.Figure:
        """
        Create comprehensive 4-subplot analysis plot.
        
        Args:
            time_data: Time array (seconds)
            force_data: Raw force array (N)
            smoothed_force: Smoothed force array (N) 
            layer_metrics: List of dictionaries containing metrics for each layer
            title: Main title for the plot
            save_path: Path to save the plot (optional)
            
        Returns:
            matplotlib Figure object
        """
        plt.style.use(self.style)
        fig = plt.figure(figsize=self.figure_size)
        
        # Create 2x2 grid layout
        gs = fig.add_gridspec(2, 2, height_ratios=[1, 1], width_ratios=[1, 1])
        
        # Subplot 1: Complete Overview (Top-Left)
        ax_overview = fig.add_subplot(gs[0, 0])
        self._plot_overview(ax_overview, time_data, force_data, smoothed_force, layer_metrics)
        
        # Subplots 2-4: Individual Layer Details
        subplot_positions = [gs[0, 1], gs[1, 0], gs[1, 1]]
        
        for i, layer_metric in enumerate(layer_metrics[:3]):  # Limit to first 3 layers
            if i < len(subplot_positions):
                ax = fig.add_subplot(subplot_positions[i])
                self._plot_individual_layer(ax, time_data, force_data, smoothed_force, layer_metric, i)
        
        # Main title and layout
        fig.suptitle(f'{title}:\nPeeling Stages with Shaded Bands and Event Markers', 
                     fontsize=20, fontweight='bold', y=0.98)
        
        plt.tight_layout()
        plt.subplots_adjust(top=0.92, hspace=0.3, wspace=0.3)
        
        if save_path:
            plt.savefig(save_path, dpi=self.dpi, bbox_inches='tight', facecolor='white')
            print(f"Plot saved as: {save_path}")
            
        return fig
    
    def _plot_overview(self, ax, time_data, force_data, smoothed_force, layer_metrics):
        """
        Plot the complete overview subplot.
        """
        # Plot force data
        ax.plot(time_data, force_data, label='Raw Force Data', **self.raw_force_style)
        ax.plot(time_data, smoothed_force, color='navy', label='Smoothed Force (Analysis)', 
                linewidth=2.5, alpha=0.9)
        
        # Add layer annotations and markers
        for i, layer_metric in enumerate(layer_metrics):
            color = self.layer_colors[i % len(self.layer_colors)]
            
            # Peak markers and lines
            peak_time = layer_metric['peak_force_time']
            peak_force = layer_metric['peak_force']
            
            ax.plot(peak_time, peak_force, color=color, **self.peak_marker_style)
            ax.axvline(x=peak_time, color=color, linestyle='--', linewidth=3, alpha=0.8, zorder=3)
            
            # Baseline line
            baseline = layer_metric['baseline_force']
            pre_init_time = layer_metric['pre_initiation_time']
            prop_end_time = layer_metric['propagation_end_time']
            
            ax.plot([pre_init_time, prop_end_time], [baseline, baseline], 
                   color=color, linestyle='-', linewidth=3, alpha=0.9, zorder=2)
            
            # Propagation end line
            ax.axvline(x=prop_end_time, color='purple', linestyle=':', linewidth=2, alpha=0.8, zorder=3)
            
            # Layer number annotation
            layer_num = layer_metric.get('layer_number', i + 1)
            ax.annotate(f'L{layer_num}', 
                       xy=(peak_time, peak_force),
                       xytext=(peak_time, peak_force + 0.02),
                       ha='center', va='bottom', fontsize=12, fontweight='bold',
                       color=color, zorder=6)
        
        ax.set_xlabel('Time (s)', fontsize=14, fontweight='bold')
        ax.set_ylabel('Force (N)', fontsize=14, fontweight='bold')
        ax.set_title('Complete Force Profile - Multiple Layers', fontsize=16, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=11, loc='upper right')
    
    def _plot_individual_layer(self, ax, time_data, force_data, smoothed_force, layer_metric, layer_index):
        """
        Plot an individual layer detail subplot with shaded bands.
        """
        color = self.layer_colors[layer_index % len(self.layer_colors)]
        layer_num = layer_metric.get('layer_number', layer_index + 1)
        
        # Extract timing data
        pre_init_time = layer_metric['pre_initiation_time']
        peak_time = layer_metric['peak_force_time']
        prop_end_time = layer_metric['propagation_end_time']
        peak_force = layer_metric['peak_force']
        baseline = layer_metric['baseline_force']
        
        # Define window around the peeling event
        buffer_time = max(0.5, (prop_end_time - pre_init_time) * 0.3)
        window_start_time = pre_init_time - buffer_time
        window_end_time = prop_end_time + buffer_time
        
        # Find indices for windowing
        window_mask = (time_data >= window_start_time) & (time_data <= window_end_time)
        window_time = time_data[window_mask]
        window_force = force_data[window_mask]
        window_smoothed = smoothed_force[window_mask]
        
        # Plot force data
        ax.plot(window_time, window_force, label='Raw Force', **self.raw_force_style)
        ax.plot(window_time, window_smoothed, color=color, label='Smoothed Force (Analysis)', 
                **self.smoothed_force_style)
        
        # Shaded bands for peeling stages
        ax.axvspan(pre_init_time, peak_time, color=self.pre_initiation_color, 
                  alpha=self.band_alpha, label='Pre-Initiation', zorder=1)
        ax.axvspan(peak_time, prop_end_time, color=self.propagation_color, 
                  alpha=self.band_alpha, label='Propagation', zorder=1)
        
        # Post-propagation shading if visible
        if prop_end_time < window_time.max():
            ax.axvspan(prop_end_time, window_time.max(), color=self.post_propagation_color, 
                      alpha=0.3, zorder=1)
        
        # Vertical event markers
        ax.axvline(x=peak_time, color=color, linestyle='--', linewidth=4, zorder=4)
        ax.plot(peak_time, peak_force, color=color, 
               label=f'Peak: {peak_force:.4f}N', **self.peak_marker_style)
        
        ax.axvline(x=prop_end_time, color='purple', linestyle=':', linewidth=4, zorder=4)
        
        # Baseline line
        ax.axhline(y=baseline, color='gray', linestyle='--', linewidth=3, alpha=0.6,
                  label=f'Baseline: {baseline:.4f}N', zorder=2)
        
        # Annotations
        self._add_layer_annotations(ax, layer_metric, color)
        
        # Formatting
        ax.set_xlabel('Time (s)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Force (N)', fontsize=12, fontweight='bold')
        ax.set_title(f'Layer {layer_num} - Peeling Stages with Shaded Bands', 
                    fontsize=14, fontweight='bold', color=color)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=10, loc='upper left', ncol=1, framealpha=0.9, 
                 fancybox=True, shadow=True)
        
        # Set appropriate limits
        y_margin = (peak_force - baseline) * 0.2
        ax.set_ylim(baseline - y_margin, peak_force + y_margin * 0.5)
        
        x_margin = (prop_end_time - pre_init_time) * 0.3
        ax.set_xlim(pre_init_time - x_margin, prop_end_time + x_margin)
    
    def _add_layer_annotations(self, ax, layer_metric, color):
        """
        Add measurement annotations to layer plot.
        """
        peak_time = layer_metric['peak_force_time']
        prop_end_time = layer_metric['propagation_end_time']
        pre_init_time = layer_metric['pre_initiation_time']
        peak_force = layer_metric['peak_force']
        baseline = layer_metric['baseline_force']
        
        # Force range arrow
        force_range = peak_force - baseline
        force_range_x = peak_time + (prop_end_time - peak_time) * 0.7
        
        ax.annotate('', xy=(force_range_x, peak_force), 
                   xytext=(force_range_x, baseline),
                   arrowprops=dict(arrowstyle='<->', color='black', lw=3))
        ax.text(force_range_x + (prop_end_time - peak_time) * 0.1, 
               (peak_force + baseline)/2, 
               f'ΔF = {force_range:.4f}N', 
               rotation=90, va='center', fontsize=11, fontweight='bold',
               bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
        
        # Time duration annotations
        y_annotation = baseline - force_range * 0.15
        
        # Pre-initiation duration
        pre_init_duration = layer_metric['pre_initiation_duration']
        ax.annotate('', xy=(peak_time, y_annotation), 
                   xytext=(pre_init_time, y_annotation),
                   arrowprops=dict(arrowstyle='<->', color='blue', lw=3))
        ax.text((peak_time + pre_init_time)/2, y_annotation - force_range * 0.08, 
               f't_pre = {pre_init_duration:.2f}s', 
               ha='center', fontsize=10, color='blue', fontweight='bold',
               bbox=dict(boxstyle='round,pad=0.2', facecolor='lightblue', alpha=0.8))
        
        # Propagation duration
        y_annotation2 = baseline - force_range * 0.30
        prop_duration = layer_metric['propagation_duration']
        ax.annotate('', xy=(prop_end_time, y_annotation2), 
                   xytext=(peak_time, y_annotation2),
                   arrowprops=dict(arrowstyle='<->', color='red', lw=3))
        
        text_x_position = prop_end_time + (prop_end_time - peak_time) * 0.1
        ax.text(text_x_position, y_annotation2 - force_range * 0.08, 
               f't_prop = {prop_duration:.2f}s', 
               ha='left', fontsize=10, color='red', fontweight='bold',
               bbox=dict(boxstyle='round,pad=0.2', facecolor='lightcoral', alpha=0.8))
    
    def plot_single_layer(self, 
                         time_data: np.ndarray,
                         force_data: np.ndarray,
                         smoothed_force: np.ndarray,
                         layer_metric: Dict,
                         title: str = "Single Layer Analysis",
                         save_path: Optional[Union[str, Path]] = None) -> plt.Figure:
        """
        Create a focused plot for a single layer.
        
        Args:
            time_data: Time array (seconds)
            force_data: Raw force array (N)
            smoothed_force: Smoothed force array (N) 
            layer_metric: Dictionary containing metrics for the layer
            title: Title for the plot
            save_path: Path to save the plot (optional)
            
        Returns:
            matplotlib Figure object
        """
        plt.style.use(self.style)
        fig, ax = plt.subplots(figsize=(16, 10))
        
        self._plot_individual_layer(ax, time_data, force_data, smoothed_force, layer_metric, 0)
        
        layer_num = layer_metric.get('layer_number', 1)
        ax.set_title(f'{title} - Layer {layer_num}', fontsize=16, fontweight='bold')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=self.dpi, bbox_inches='tight', facecolor='white')
            print(f"Single layer plot saved as: {save_path}")
            
        return fig
    
    def plot_overview_only(self,
                          time_data: np.ndarray,
                          force_data: np.ndarray,
                          smoothed_force: np.ndarray,
                          layer_metrics: List[Dict],
                          title: str = "Force Overview",
                          save_path: Optional[Union[str, Path]] = None) -> plt.Figure:
        """
        Create overview plot only (no individual layer details).
        
        Args:
            time_data: Time array (seconds)
            force_data: Raw force array (N)
            smoothed_force: Smoothed force array (N) 
            layer_metrics: List of dictionaries containing metrics for each layer
            title: Title for the plot
            save_path: Path to save the plot (optional)
            
        Returns:
            matplotlib Figure object
        """
        plt.style.use(self.style)
        fig, ax = plt.subplots(figsize=(16, 8))
        
        self._plot_overview(ax, time_data, force_data, smoothed_force, layer_metrics)
        ax.set_title(title, fontsize=16, fontweight='bold')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=self.dpi, bbox_inches='tight', facecolor='white')
            print(f"Overview plot saved as: {save_path}")
            
        return fig
    
    def print_metrics_summary(self, layer_metrics: List[Dict]):
        """
        Print a comprehensive summary of the calculated metrics.
        
        Args:
            layer_metrics: List of dictionaries containing metrics for each layer
        """
        print("\n" + "="*100)
        print("ADHESION METRICS SUMMARY")
        print("="*100)
        
        print(f"{'Layer':<8} {'Peak Force':<12} {'Baseline':<12} {'Force Range':<12} {'Pre-Init':<12} {'Propagation':<12} {'Work':<12}")
        print(f"{'':8} {'(N)':<12} {'(N)':<12} {'(N)':<12} {'Time (s)':<12} {'Time (s)':<12} {'(mJ)':<12}")
        print("-" * 100)
        
        for layer_metric in layer_metrics:
            layer_num = layer_metric.get('layer_number', 'N/A')
            peak_force = layer_metric.get('peak_force', 0.0)
            baseline = layer_metric.get('baseline_force', 0.0)
            force_range = peak_force - baseline
            pre_init_duration = layer_metric.get('pre_initiation_duration', 0.0)
            prop_duration = layer_metric.get('propagation_duration', 0.0)
            work = layer_metric.get('work_of_adhesion_corrected_mJ', 0.0)
            
            print(f"{layer_num:<8} {peak_force:<12.6f} {baseline:<12.6f} "
                  f"{force_range:<12.6f} {pre_init_duration:<12.3f} "
                  f"{prop_duration:<12.3f} {work:<12.3f}")
        
        print("\n" + "="*100)


# Example usage function
def example_usage():
    """
    Example of how to use the AdhesionMetricsPlotter with AdhesionMetricsCalculator.
    """
    # This would typically be called after calculating metrics
    print("Example Usage of AdhesionMetricsPlotter:")
    print("="*50)
    print("""
    # Step 1: Calculate metrics using AdhesionMetricsCalculator
    from adhesion_metrics_calculator import AdhesionMetricsCalculator
    
    calculator = AdhesionMetricsCalculator()
    
    # For CSV file
    layer_48_metrics = calculator.calculate_from_csv("autolog_L48-L50.csv", layer_number=48)
    layer_49_metrics = calculator.calculate_from_csv("autolog_L48-L50.csv", layer_number=49)
    layer_50_metrics = calculator.calculate_from_csv("autolog_L48-L50.csv", layer_number=50)
    
    layer_metrics = [layer_48_metrics, layer_49_metrics, layer_50_metrics]
    
    # Step 2: Load data for plotting
    import pandas as pd
    df = pd.read_csv("autolog_L48-L50.csv")
    time_data = df['Time'].values
    force_data = df['Force'].values
    
    # Apply same smoothing as calculator
    from scipy.signal import savgol_filter
    smoothed_force = savgol_filter(force_data, window_length=11, polyorder=2)
    
    # Step 3: Create plots
    plotter = AdhesionMetricsPlotter()
    
    # Comprehensive 4-subplot analysis
    fig = plotter.plot_comprehensive_analysis(
        time_data, force_data, smoothed_force, layer_metrics,
        title="L48-L50 Adhesion Analysis",
        save_path="L48_L50_analysis.png"
    )
    
    # Print summary
    plotter.print_metrics_summary(layer_metrics)
    """)


if __name__ == "__main__":
    example_usage()
