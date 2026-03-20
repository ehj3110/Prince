"""Analysis plotting utilities for post-processing autolog datasets.

This module is intentionally plotting-only and expects precomputed layers and
metrics from upstream processors.
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
        
        # Style guide default typography.
        plt.rcParams['font.family'] = 'Times New Roman'
        plt.rcParams['font.size'] = 12

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

        base_title_size, base_label_size = (24, 14)
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
        fig.suptitle(title,
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
            is_incomplete = bool(layer.get('incomplete_peeling', False))
            color = 'dimgray' if is_incomplete else layer['color']
            if is_incomplete:
                ax.axvspan(
                    time_data[layer['start_idx']],
                    time_data[layer['end_idx']],
                    facecolor='white',
                    edgecolor='black',
                    hatch='xx',
                    alpha=0.35,
                    zorder=0,
                )
            else:
                ax.axvspan(time_data[layer['start_idx']], time_data[layer['end_idx']],
                           alpha=0.08, color=color)
            ax.plot(layer['peak_time'], layer['peak_force'], 'o', color=color,
                    markersize=12, zorder=5, markeredgecolor='black', markeredgewidth=2)
            ax.axvline(x=layer['peak_time'], color=color, linestyle='--', linewidth=3, alpha=0.8, zorder=3)
            ax.plot([layer['pre_init_time'], layer['prop_end_time']],
                    [layer['baseline'], layer['baseline']],
                    color=color, linestyle='-', linewidth=3, alpha=0.9, zorder=2)
            ax.axvline(x=layer['prop_end_time'], color='purple', linestyle=':', linewidth=2, alpha=0.8, zorder=3)
            layer_label = f'L{layer["number"]}' if not is_incomplete else f'L{layer["number"]}*'
            ax.annotate(layer_label, (layer['peak_time'], layer['peak_force']),
                        xytext=(0, 5), textcoords='offset points', ha='center', va='bottom',
                        fontsize=font_size + 2, fontweight='bold', color=color, zorder=6)

        ax.set_xlabel('Time (s)', fontsize=font_size + 4, fontweight='bold')
        ax.set_ylabel('Force (N)', fontsize=font_size + 4, fontweight='bold')
        ax.set_title('Complete Force Profile', fontsize=font_size + 6, fontweight='bold')
        ax.tick_params(axis='both', which='major', labelsize=font_size + 4)
        ax.locator_params(axis='both', nbins=6)  # Reduce number of tick marks
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=font_size - 1, loc='lower right', framealpha=0.9)
        
        # Set axis limits to show all layers with margins
        if layers:
            x_margin = (time_data[-1] - time_data[0]) * 0.05  # 5% margin
            # Use symmetric 15% padding around the plotted y-range.
            y_data_min = float(np.min(force_data))
            y_data_max = float(np.max(force_data))
            y_span = max(y_data_max - y_data_min, 1e-6)
            y_padding = y_span * 0.15
            y_min = y_data_min - y_padding
            y_max = y_data_max + y_padding
            
            # Use actual data range with margins
            start_time = time_data[min([layer['start_idx'] for layer in layers])] - x_margin
            end_time = time_data[max([layer['end_idx'] for layer in layers])] + x_margin
            
            ax.set_xlim(start_time, end_time)
            ax.set_ylim(y_min, y_max)

    def _plot_individual_layer(self, ax, time_data, force_data, smoothed_force, layer, font_size=10):
        """Plots a single detailed layer subplot."""
        is_incomplete = bool(layer.get('incomplete_peeling', False))
        # Use grayscale styling for incomplete peeling layers.
        color = 'dimgray' if is_incomplete else layer['color']
        
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

        # Shaded regions for fracture stages.
        if is_incomplete:
            ax.axvspan(
                layer['pre_init_time'],
                layer['peak_time'],
                facecolor='white',
                edgecolor='black',
                hatch='///',
                alpha=0.35,
                label='Pre-Initiation',
                zorder=1,
            )
            ax.axvspan(
                layer['peak_time'],
                layer['prop_end_time'],
                facecolor='white',
                edgecolor='black',
                hatch='xx',
                alpha=0.35,
                label='Propagation',
                zorder=1,
            )
            if layer['prop_end_time'] < window_time.max():
                ax.axvspan(
                    layer['prop_end_time'],
                    window_time.max(),
                    facecolor='white',
                    edgecolor='black',
                    hatch='..',
                    alpha=0.30,
                    zorder=1,
                )
        else:
            ax.axvspan(layer['pre_init_time'], layer['peak_time'], color='lightblue', alpha=0.3, label='Pre-Initiation', zorder=1)
            ax.axvspan(layer['peak_time'], layer['prop_end_time'], color='lightcoral', alpha=0.3, label='Propagation', zorder=1)
            if layer['prop_end_time'] < window_time.max():
                ax.axvspan(layer['prop_end_time'], window_time.max(), color='lightyellow', alpha=0.3, zorder=1)

        # Vertical lines and markers
        ax.axvline(x=layer['peak_time'], color=color, linestyle='--', linewidth=3, alpha=0.8, zorder=4, label='Peak Force')
        ax.plot(layer['peak_time'], layer['peak_force'], 'o', color=color, markersize=12, zorder=5,
                markeredgecolor='black', markeredgewidth=2)
        ax.axvline(x=layer['prop_end_time'], color='purple', linestyle=':', linewidth=3, alpha=0.8, zorder=4, label='Prop End')
        ax.plot(layer['prop_end_time'], smoothed_force[layer['prop_end_idx']], 's', color='purple',
                markersize=9, zorder=5, markeredgecolor='black', markeredgewidth=1.5)

        # Baseline
        ax.axhline(y=layer['baseline'], color='gray', linestyle='--', linewidth=2, alpha=0.6,
                   label=f'Baseline: {layer["baseline"]:.4f}N', zorder=2)

        # Calculate appropriate margins for y-axis.
        force_range = layer['peak_force'] - layer['baseline']
        y_margin = force_range * 0.2  # 20% margin
        y_min = min(layer['baseline'] - y_margin, np.min(window_force))
        y_max = max(layer['peak_force'] + y_margin, np.max(window_force))

        # Peak-force annotation text uses corrected value when available.
        relative_force = layer.get('peak_force_corrected', layer['peak_force'] - layer['baseline'])
        x_range = layer['prop_end_time'] - layer['pre_init_time']
        annotation_x = layer['peak_time'] + x_range * 0.15
        # Keep annotation adaptive to the peak while constraining it to a safe in-axis band.
        y_span = max(y_max - y_min, 1e-6)
        annotation_y_min = y_min + y_span * 0.15
        annotation_y_max = y_max - y_span * 0.15
        annotation_y = float(np.clip(layer['peak_force'], annotation_y_min, annotation_y_max))
        ax.text(annotation_x, annotation_y,
            f"Peak: {layer['peak_force']:.4f}N\nNet: {relative_force:.4f}N",
                ha='left', va='center', fontsize=font_size, fontweight='bold', 
                color=color, bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor=color, alpha=0.9))
        
        # Duration annotations in title
        duration_text = f"Pre-init: {layer['pre_init_duration']:.2f}s | Prop: {layer['prop_duration']:.2f}s"
        status_text = " | INCOMPLETE PEELING" if is_incomplete else ""
        
        ax.set_xlabel('Time (s)', fontsize=font_size + 4, fontweight='bold')
        ax.set_ylabel('Force (N)', fontsize=font_size + 4, fontweight='bold')
        ax.set_title(f'Layer {layer["number"]} - {duration_text}{status_text}', fontsize=font_size + 2, fontweight='bold', color='black')
        ax.tick_params(axis='both', which='major', labelsize=font_size + 4)
        ax.locator_params(axis='both', nbins=6)  # Reduce number of tick marks
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=font_size - 2, loc='upper left', framealpha=0.9, ncol=2)

        ax.set_ylim(y_min, y_max)

        # X-limits with 50% margin on each side to show more pre-initiation
        x_margin = (layer['prop_end_time'] - layer['pre_init_time']) * 0.5
        ax.set_xlim(layer['pre_init_time'] - x_margin, layer['prop_end_time'] + x_margin)



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