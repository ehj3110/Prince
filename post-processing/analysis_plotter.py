"""
Analysis Plotter
================

A dedicated plotting module for generating comprehensive a        # Add title and adjust subplots
        title_lines = [title, 'Peeling Stages with Shaded Bands and Event Markers']
        fig.suptitle('\n'.join(title_lines),
                    fontsize=title_size, fontweight='bold', y=1.0)

        # Adjust layout
        plt.tight_layout(rect=[0, 0, 1, 0.95])

        # Fine-tune subplot spacing for better readability
        plt.subplots_adjust(top=0.88, bottom=0.08, hspace=0.4, wspace=0.3)nalysis visualizations.
This module contains the dynamic plotting logic originally developed for the
HybridAdhesionPlotter, but is decoupled from data processing and calculation.

It is designed to be called by a data processor that has already calculated
all necessary metrics and defined the layer objects.

Author: Cheng Sun Lab Team
Date: September 20, 2025
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend to avoid Windows crashes
import matplotlib.pyplot as plt
from typing import Dict, List, Optional, Union
from pathlib import Path

class AnalysisPlotter:
    """
    Generates detailed, multi-panel analysis plots from pre-processed layer data.
    """

    def __init__(self, figure_size=(16, 12), dpi=100):
        """
        Initialize the plotter.

        Args:
            figure_size (tuple): Base size for the figure (width, height) in inches.
            dpi (int): Resolution for the saved plot.
        """
        self.figure_size = figure_size
        self.dpi = dpi
        self.layer_colors = ['red', 'blue', 'green', 'orange', 'purple', 'brown']
        self._configure_matplotlib_backend()

    def _configure_matplotlib_backend(self):
        """Configure matplotlib backend for thread-safe operation."""
        import threading
        if threading.current_thread() != threading.main_thread():
            matplotlib.use('Agg')
        else:
            try:
                matplotlib.use('TkAgg')
            except ImportError:
                matplotlib.use('Agg')

    def create_plot(self,
                    time_data: np.ndarray,
                    force_data: np.ndarray,
                    smoothed_force: np.ndarray,
                    layers: List[Dict],
                    title: str,
                    save_path: Optional[Union[str, Path]] = None):
        """
        Creates and saves the comprehensive analysis plot.

        Args:
            time_data (np.ndarray): The complete time array for the dataset.
            force_data (np.ndarray): The complete raw force array.
            smoothed_force (np.ndarray): The complete smoothed force array.
            layers (List[Dict]): A list of layer objects, each containing metrics and indices.
            title (str): The main title for the plot.
            save_path (Optional[Union[str, Path]]): The path to save the figure.
        """
        num_layers = len(layers)
        if num_layers == 0:
            print("Plotter: No layers provided to plot. Aborting.")
            return

        total_plots = 1 + num_layers
        rows_needed = (total_plots + 1) // 2

        base_title_size, base_label_size = (16, 10)
        if rows_needed <= 2: title_size, label_size = base_title_size, base_label_size
        elif rows_needed <= 3: title_size, label_size = base_title_size - 2, base_label_size - 1
        else: title_size, label_size = base_title_size - 4, base_label_size - 2

        fig_height = self.figure_size[1] * (rows_needed / 2.0)
        fig = plt.figure(figsize=(self.figure_size[0], fig_height), dpi=self.dpi)
        gs = fig.add_gridspec(rows_needed, 2)

        # Plot Overview
        ax_overview = fig.add_subplot(gs[0, 0])
        self._plot_overview(ax_overview, time_data, force_data, smoothed_force, layers, label_size)

        # Plot Individual Layers
        subplot_positions = [gs[0, 1]]
        for row in range(1, rows_needed):
            subplot_positions.append(gs[row, 0])
            if len(subplot_positions) < num_layers:
                subplot_positions.append(gs[row, 1])

        for i, layer in enumerate(layers):
            if i < len(subplot_positions):
                ax = fig.add_subplot(subplot_positions[i])
                self._plot_individual_layer(ax, time_data, force_data, smoothed_force, layer, label_size)

        # Adjust layout first
        plt.tight_layout()

        # Add title and adjust subplots to make room
        fig.suptitle(f'{title}\nPeeling Stages with Shaded Bands and Event Markers',
                     fontsize=title_size, fontweight='bold', y=0.98)

        # Fine-tune subplot spacing
        plt.subplots_adjust(top=0.90, bottom=0.08, hspace=0.4, wspace=0.3)

        if save_path:
            try:
                fig.savefig(save_path, dpi=self.dpi, bbox_inches='tight', facecolor='white')
                print(f"Plotter: Plot saved to {save_path}")
            except Exception as e:
                print(f"Plotter: Error saving plot: {e}")
        
        plt.close(fig)

    def _plot_overview(self, ax, time_data, force_data, smoothed_force, layers, font_size=10):
        """Plots the complete overview subplot."""
        ax.plot(time_data, force_data, 'k-', linewidth=1, alpha=0.4, label='Raw Force')
        ax.plot(time_data, smoothed_force, 'navy', linewidth=2.5, alpha=0.9, label='Smoothed Force')

        for layer in layers:
            color = layer['color']
            ax.axvspan(time_data[layer['start_idx']], time_data[layer['end_idx']],
                       alpha=0.08, color=color)
            ax.plot(layer['peak_time'], layer['peak_force'], 'o', color=color,
                    markersize=12, zorder=5, markeredgecolor='black', markeredgewidth=2)
            ax.axvline(x=layer['peak_time'], color=color, linestyle='--', linewidth=3, alpha=0.8, zorder=3)
            ax.plot([layer['pre_init_time'], layer['prop_end_time']],
                    [layer['baseline'], layer['baseline']],
                    color=color, linestyle='-', linewidth=3, alpha=0.9, zorder=2)
            ax.axvline(x=layer['prop_end_time'], color='purple', linestyle=':', linewidth=2, alpha=0.8, zorder=3)
            ax.annotate(f'L{layer["number"]}', (layer['peak_time'], layer['peak_force']),
                        xytext=(0, 5), textcoords='offset points', ha='center', va='bottom',
                        fontsize=font_size + 2, fontweight='bold', color=color, zorder=6)

        ax.set_xlabel('Time (s)', fontsize=font_size + 2, fontweight='bold')
        ax.set_ylabel('Force (N)', fontsize=font_size + 2, fontweight='bold')
        ax.set_title('Complete Force Profile', fontsize=font_size + 4, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=font_size, loc='upper right')
        
        # Set axis limits to show all layers with margins
        if layers:
            x_margin = (time_data[-1] - time_data[0]) * 0.05  # 5% margin
            y_max = max([layer['peak_force'] for layer in layers]) * 1.1
            y_min = min(0, np.min(force_data)) - 0.02
            
            # Use actual data range with margins
            start_time = time_data[min([layer['start_idx'] for layer in layers])] - x_margin
            end_time = time_data[max([layer['end_idx'] for layer in layers])] + x_margin
            
            ax.set_xlim(start_time, end_time)
            ax.set_ylim(y_min, y_max)

    def _plot_individual_layer(self, ax, time_data, force_data, smoothed_force, layer, font_size=10):
        """Plots a single detailed layer subplot."""
        # Debug print
        print(f"\nPlotting Layer {layer['number']}:")
        print(f"  Peak Time: {layer['peak_time']:.3f}s")
        print(f"  Pre-init Time: {layer['pre_init_time']:.3f}s")
        print(f"  Prop End Time: {layer['prop_end_time']:.3f}s")
        print(f"  Start/End Idx: {layer['start_idx']}-{layer['end_idx']}")
        print(f"  Time Range: {time_data[layer['start_idx']]:.3f}s - {time_data[layer['end_idx']]:.3f}s")
        
        color = layer['color']
        
        # Define focused window around the peeling event with buffer
        buffer_time = 1.0  # 1 second buffer
        window_start_time = layer['pre_init_time'] - buffer_time
        window_end_time = layer['prop_end_time'] + buffer_time
        
        # Find indices for window using exact 1.0s buffer
        window_start = np.argmin(np.abs(time_data - window_start_time))
        window_end = np.argmin(np.abs(time_data - window_end_time))
        
        # Extract windowed data
        window_time = time_data[window_start:window_end+1]
        window_force = force_data[window_start:window_end+1]
        window_smoothed = smoothed_force[window_start:window_end+1]

        ax.plot(window_time, window_force, 'k-', linewidth=1, alpha=0.4, label='Raw Force')
        ax.plot(window_time, window_smoothed, color=color, linewidth=3.5, alpha=0.95,
                label='Smoothed Force', zorder=3)

        # Shaded bands for peeling stages
        ax.axvspan(layer['pre_init_time'], layer['peak_time'], color='lightblue', alpha=0.5, label='Pre-Initiation', zorder=1)
        ax.axvspan(layer['peak_time'], layer['prop_end_time'], color='lightcoral', alpha=0.5, label='Propagation', zorder=1)

        # Vertical lines and markers
        ax.axvline(x=layer['peak_time'], color=color, linestyle='--', linewidth=4, zorder=4)
        ax.plot(layer['peak_time'], layer['peak_force'], 'o', color=color, markersize=14, zorder=5,
                markeredgecolor='black', markeredgewidth=2, label=f'Peak: {layer["peak_force"]:.4f}N')
        ax.axvline(x=layer['prop_end_time'], color='purple', linestyle=':', linewidth=4, zorder=4)
        ax.plot(layer['prop_end_time'], smoothed_force[layer['prop_end_idx']], 's', color='purple',
                markersize=10, zorder=5, markeredgecolor='black', markeredgewidth=1, label='Prop End')

        # Baseline
        ax.axhline(y=layer['baseline'], color='gray', linestyle='--', linewidth=3, alpha=0.6,
                   label=f'Baseline: {layer["baseline"]:.4f}N', zorder=2)

        self._add_layer_annotations(ax, layer, font_size)

        ax.set_xlabel('Time (s)', fontsize=font_size + 1, fontweight='bold')
        ax.set_ylabel('Force (N)', fontsize=font_size + 1, fontweight='bold')
        ax.set_title(f'Layer {layer["number"]} - Peeling Stages', fontsize=font_size + 3, fontweight='bold', color=color)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=font_size - 1, loc='upper left', framealpha=0.9)

        # Calculate appropriate margins for y-axis
        force_range = layer['peak_force'] - layer['baseline']
        y_margin = force_range * 0.2  # 20% margin
        y_min = min(layer['baseline'] - y_margin, np.min(window_force)) 
        y_max = max(layer['peak_force'] + y_margin, np.max(window_force))
        ax.set_ylim(y_min, y_max)

        # X-limits with 30% margin of peeling duration
        x_margin = (layer['prop_end_time'] - layer['pre_init_time']) * 0.3
        ax.set_xlim(layer['pre_init_time'] - x_margin, layer['prop_end_time'] + x_margin)

    def _add_layer_annotations(self, ax, layer, font_size=10):
        """Adds measurement annotations to a layer subplot."""
        # Force range annotation
        force_range_x = layer['peak_time'] + (layer['prop_end_time'] - layer['peak_time']) * 0.7
        ax.annotate('', xy=(force_range_x, layer['peak_force']), xytext=(force_range_x, layer['baseline']),
                    arrowprops=dict(arrowstyle='<->', color='black', lw=3))
        ax.text(force_range_x + 0.3, (layer['peak_force'] + layer['baseline']) / 2,
                f'ΔF = {layer["force_range"]:.4f}N', rotation=90, va='center',
                fontsize=font_size, fontweight='bold', bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))

        # Time duration annotations - further below baseline as in hybrid plotter
        y_annotation = layer['baseline'] - 0.025
        ax.annotate('', xy=(layer['peak_time'], y_annotation), xytext=(layer['pre_init_time'], y_annotation),
                    arrowprops=dict(arrowstyle='<->', color='blue', lw=3))
        ax.text((layer['peak_time'] + layer['pre_init_time']) / 2, y_annotation - 0.008,
                f't_pre = {layer["pre_init_duration"]:.2f}s', ha='center', fontsize=font_size - 1,
                color='blue', fontweight='bold', bbox=dict(boxstyle='round,pad=0.2', facecolor='lightblue', alpha=0.8))

        y_annotation2 = layer['baseline'] - 0.045
        ax.annotate('', xy=(layer['prop_end_time'], y_annotation2), xytext=(layer['peak_time'], y_annotation2),
                    arrowprops=dict(arrowstyle='<->', color='red', lw=3))
        ax.text((layer['prop_end_time'] + layer['peak_time']) / 2, y_annotation2 - 0.008,
                f't_prop = {layer["prop_duration"]:.2f}s', ha='center', fontsize=font_size - 1,
                color='red', fontweight='bold', bbox=dict(boxstyle='round,pad=0.2', facecolor='lightcoral', alpha=0.8))

    def print_metrics_summary(self, layers: List[Dict]):
        """Prints a formatted summary of key metrics for all processed layers."""
        if not layers:
            return

        print("\n" + "=" * 80)
        print("PROCESSED METRICS SUMMARY")
        print("=" * 80)
        print(f"{'Layer':<8} {'Peak Force':<12} {'Baseline':<12} {'Work (mJ)':<12} {'Pre-Init (s)':<14} {'Prop (s)':<12}")
        print("-" * 80)

        for layer in layers:
            metrics = layer['metrics']
            print(f"{layer['number']:<8} "
                  f"{metrics['peak_force']:<12.4f} "
                  f"{metrics['baseline_force']:<12.4f} "
                  f"{metrics['work_of_adhesion_corrected_mJ']:<12.3f} "
                  f"{metrics['pre_initiation_duration']:<14.3f} "
                  f"{metrics['propagation_duration']:<12.3f}")
        print("=" * 80 + "\n")