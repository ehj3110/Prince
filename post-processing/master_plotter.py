"""
Master Plotter
==============

Generalized plotting module for creating area-based master analysis plots
from batch processing results.

This module creates publication-quality plots with:
- Configurable metrics (choose which metrics to plot)
- Grouped by condition (color-coded)
- Mean ± SEM error bands
- Polynomial trendlines
- Multiple plot layouts (2x2, 1x2, single, etc.)

Author: Cheng Sun Lab Team
Date: October 28, 2025
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from pathlib import Path
from typing import List, Tuple, Optional, Dict


class MasterPlotter:
    """
    Creates master analysis plots from aggregated batch processing results.
    
    Features:
    - Configurable metrics (specify which columns to plot)
    - Automatic color mapping by condition
    - Shaded SEM error regions
    - Polynomial trendlines (optional)
    - Absolute value option for specific metrics
    """
    
    def __init__(self, output_directory: Path, dpi: int = 300):
        """
        Initialize the master plotter.
        
        Args:
            output_directory: Directory to save plots
            dpi: Resolution for saved figures
        """
        self.output_directory = Path(output_directory)
        self.dpi = dpi
        
    def generate_area_analysis_plot(self,
                                    df: pd.DataFrame,
                                    metrics: List[Tuple[str, str]],
                                    plot_name: str,
                                    title: str,
                                    apply_abs: Optional[List[str]] = None,
                                    add_trendlines: bool = True,
                                    figsize: Tuple[int, int] = (16, 12)):
        """
        Generate a master area analysis plot with configurable metrics.
        
        Args:
            df: DataFrame with columns: condition_label, area_mm2, [metric columns]
            metrics: List of (column_name, ylabel) tuples to plot
                    Example: [('peak_force_N', 'Peak Force (N)'),
                             ('work_of_adhesion_mJ', 'Work of Adhesion (mJ)')]
            plot_name: Filename for saved plot (e.g., 'MASTER_area_analysis.png')
            title: Main title for the figure
            apply_abs: List of metric column names to apply absolute value
                      Example: ['peel_distance_mm', 'total_peel_time_s']
            add_trendlines: Whether to add polynomial trendlines
            figsize: Figure size in inches (width, height)
        
        Returns:
            Path to saved plot file
        """
        print(f"  Creating {plot_name}...")
        
        # Determine subplot layout based on number of metrics
        n_metrics = len(metrics)
        if n_metrics == 1:
            nrows, ncols = 1, 1
        elif n_metrics == 2:
            nrows, ncols = 1, 2
        elif n_metrics <= 4:
            nrows, ncols = 2, 2
        elif n_metrics <= 6:
            nrows, ncols = 2, 3
        elif n_metrics <= 9:
            nrows, ncols = 3, 3
        else:
            # For many metrics, use dynamic layout
            ncols = 3
            nrows = (n_metrics + ncols - 1) // ncols
        
        # Create figure
        fig, axes = plt.subplots(nrows, ncols, figsize=figsize)
        fig.suptitle(title, fontsize=16, fontweight='bold')
        
        # Handle single subplot case (axes is not an array)
        if n_metrics == 1:
            axes = np.array([axes])
        else:
            axes = axes.flatten()
        
        # Define color map for conditions
        conditions = sorted(df['condition_label'].unique())
        colors = plt.cm.tab10(np.linspace(0, 1, len(conditions)))
        color_map = dict(zip(conditions, colors))
        
        # Plot each metric
        for idx, (metric_col, ylabel) in enumerate(metrics):
            ax = axes[idx]
            
            for condition in conditions:
                condition_data = df[df['condition_label'] == condition].copy()
                color = color_map[condition]
                
                # Apply absolute value if requested
                if apply_abs and metric_col in apply_abs:
                    condition_data[metric_col] = condition_data[metric_col].abs()
                
                # Group by area and calculate mean + SEM
                grouped = condition_data.groupby('area_mm2')[metric_col].agg(['mean', 'sem'])
                areas = grouped.index.values
                means = grouped['mean'].values
                sems = grouped['sem'].values
                
                # Plot mean with markers
                ax.plot(areas, means, 'o', color=color, markersize=3, alpha=0.7, label=condition)
                
                # Add shaded SEM region
                ax.fill_between(areas, means - sems, means + sems, color=color, alpha=0.2)
                
                # Add polynomial trendline
                if add_trendlines and len(areas) > 2:
                    try:
                        z = np.polyfit(areas, means, 2)
                        p = np.poly1d(z)
                        area_smooth = np.linspace(areas.min(), areas.max(), 100)
                        ax.plot(area_smooth, p(area_smooth), '-', color=color, linewidth=1.5, alpha=0.8)
                    except:
                        pass  # Skip trendline if fitting fails
            
            # Format subplot
            ax.set_xlabel('Contact Area (mm²)', fontsize=11)
            ax.set_ylabel(ylabel, fontsize=11)
            ax.legend(fontsize=8, loc='best')
            ax.grid(True, alpha=0.3)
        
        # Hide unused subplots
        for idx in range(n_metrics, len(axes)):
            axes[idx].axis('off')
        
        plt.tight_layout()
        
        # Save figure
        output_file = self.output_directory / plot_name
        plt.savefig(output_file, dpi=self.dpi, bbox_inches='tight')
        print(f"    Saved: {output_file}")
        
        plt.close()
        
        return output_file
    
    def generate_distance_analysis_plot(self,
                                        df: pd.DataFrame,
                                        plot_name: str = 'MASTER_distance_analysis.png'):
        """
        Generate distance-based metrics plot.
        
        Args:
            df: DataFrame with batch processing results
            plot_name: Filename for saved plot
        
        Returns:
            Path to saved plot file
        """
        metrics = [
            ('distance_to_peak_mm', 'Pre-Initiation Distance (mm)'),
            ('propagation_distance_mm', 'Propagation Distance (mm)')
        ]
        
        return self.generate_area_analysis_plot(
            df=df,
            metrics=metrics,
            plot_name=plot_name,
            title='Master Distance Analysis',
            apply_abs=['distance_to_peak_mm', 'propagation_distance_mm'],
            add_trendlines=True
        )
    
    def generate_stiffness_analysis_plot(self,
                                         df: pd.DataFrame,
                                         plot_name: str = 'MASTER_stiffness_analysis.png'):
        """
        Generate stiffness analysis plot.
        
        Args:
            df: DataFrame with batch processing results
            plot_name: Filename for saved plot
        
        Returns:
            Path to saved plot file
        """
        metrics = [
            ('effective_stiffness_N_per_mm', 'Effective Stiffness (N/mm)')
        ]
        
        return self.generate_area_analysis_plot(
            df=df,
            metrics=metrics,
            plot_name=plot_name,
            title='Master Stiffness Analysis',
            apply_abs=None,
            add_trendlines=True,
            figsize=(10, 8)
        )
    
    def generate_standard_plots(self, df: pd.DataFrame):
        """
        Generate the standard set of master plots.
        
        Creates:
        1. Area analysis (Force, Work, Distance, Retraction Force)
        2. Distance analysis (Pre-init distance, Propagation distance)
        3. Stiffness analysis
        4. Modified area analysis (Force, Work, Distance, Peel Time)
        
        Args:
            df: DataFrame with batch processing results
        
        Returns:
            List of paths to generated plot files
        """
        print(f"\n{'='*60}")
        print(f"Generating Master Plots")
        print(f"{'='*60}\n")
        
        output_files = []
        
        # 1. Standard area analysis plot
        metrics_standard = [
            ('peak_force_N', 'Peak Force (N)'),
            ('work_of_adhesion_mJ', 'Work of Adhesion (mJ)'),
            ('peel_distance_mm', 'Peel Distance (mm)'),
            ('peak_retraction_force_N', 'Peak Retraction Force (N)')
        ]
        
        output_files.append(
            self.generate_area_analysis_plot(
                df=df,
                metrics=metrics_standard,
                plot_name='MASTER_area_analysis.png',
                title='Master Area Analysis',
                apply_abs=['peel_distance_mm']
            )
        )
        
        # 2. Distance analysis plot
        output_files.append(self.generate_distance_analysis_plot(df))
        
        # 3. Stiffness analysis plot
        output_files.append(self.generate_stiffness_analysis_plot(df))
        
        # 4. Modified area analysis plot (with peel time instead of retraction force)
        metrics_modified = [
            ('peak_force_N', 'Peak Force (N)'),
            ('work_of_adhesion_mJ', 'Work of Adhesion (mJ)'),
            ('peel_distance_mm', 'Peel Distance (mm)'),
            ('total_peel_time_s', 'Total Peel Time (s)')
        ]
        
        output_files.append(
            self.generate_area_analysis_plot(
                df=df,
                metrics=metrics_modified,
                plot_name='MASTER_Modified_area_analysis.png',
                title='Master Area Analysis - Modified',
                apply_abs=['peel_distance_mm']
            )
        )
        
        print("\nAll plots generated successfully!")
        
        return output_files
    
    def generate_radius_analysis_plot(self,
                                      df: pd.DataFrame,
                                      metrics: List[Tuple[str, str]],
                                      plot_name: str,
                                      title: str,
                                      apply_abs: Optional[List[str]] = None,
                                      add_trendlines: bool = True,
                                      figsize: Tuple[int, int] = (16, 12)):
        """
        Generate a master radius analysis plot with configurable metrics.
        Uses contact radius (calculated from area) as X-axis instead of area.
        
        For circular contact: Area = π * r²  →  r = sqrt(Area / π)
        
        Args:
            df: DataFrame with columns: condition_label, area_mm2, [metric columns]
            metrics: List of (column_name, ylabel) tuples to plot
                    Example: [('peak_force_N', 'Peak Force (N)'),
                             ('work_of_adhesion_mJ', 'Work of Adhesion (mJ)')]
            plot_name: Filename for saved plot (e.g., 'MASTER_radius_analysis.png')
            title: Main title for the figure
            apply_abs: List of metric column names to apply absolute value
            add_trendlines: Whether to add polynomial trendlines
            figsize: Figure size in inches (width, height)
        
        Returns:
            Path to saved plot file
        """
        print(f"  Creating {plot_name}...")
        
        # Add radius column to dataframe
        df_with_radius = df.copy()
        df_with_radius['radius_mm'] = np.sqrt(df_with_radius['area_mm2'] / np.pi)
        
        # Determine subplot layout based on number of metrics
        n_metrics = len(metrics)
        if n_metrics == 1:
            nrows, ncols = 1, 1
        elif n_metrics == 2:
            nrows, ncols = 1, 2
        elif n_metrics <= 4:
            nrows, ncols = 2, 2
        elif n_metrics <= 6:
            nrows, ncols = 2, 3
        elif n_metrics <= 9:
            nrows, ncols = 3, 3
        else:
            # For many metrics, use dynamic layout
            ncols = 3
            nrows = (n_metrics + ncols - 1) // ncols
        
        # Create figure
        fig, axes = plt.subplots(nrows, ncols, figsize=figsize)
        fig.suptitle(title, fontsize=16, fontweight='bold')
        
        # Handle single subplot case (axes is not an array)
        if n_metrics == 1:
            axes = np.array([axes])
        else:
            axes = axes.flatten()
        
        # Define color map for conditions
        conditions = sorted(df_with_radius['condition_label'].unique())
        colors = plt.cm.tab10(np.linspace(0, 1, len(conditions)))
        color_map = dict(zip(conditions, colors))
        
        # Plot each metric
        for idx, (metric_col, ylabel) in enumerate(metrics):
            ax = axes[idx]
            
            for condition in conditions:
                condition_data = df_with_radius[df_with_radius['condition_label'] == condition].copy()
                color = color_map[condition]
                
                # Apply absolute value if requested
                if apply_abs and metric_col in apply_abs:
                    condition_data[metric_col] = condition_data[metric_col].abs()
                
                # Group by radius and calculate mean + SEM
                grouped = condition_data.groupby('radius_mm')[metric_col].agg(['mean', 'sem'])
                radii = grouped.index.values
                means = grouped['mean'].values
                sems = grouped['sem'].values
                
                # Plot mean with markers
                ax.plot(radii, means, 'o', color=color, markersize=3, alpha=0.7, label=condition)
                
                # Add shaded SEM region
                ax.fill_between(radii, means - sems, means + sems, color=color, alpha=0.2)
                
                # Add polynomial trendline
                if add_trendlines and len(radii) > 2:
                    try:
                        z = np.polyfit(radii, means, 2)
                        p = np.poly1d(z)
                        radius_smooth = np.linspace(radii.min(), radii.max(), 100)
                        ax.plot(radius_smooth, p(radius_smooth), '-', color=color, linewidth=1.5, alpha=0.8)
                    except:
                        pass  # Skip trendline if fitting fails
            
            # Format subplot
            ax.set_xlabel('Contact Radius (mm)', fontsize=11)
            ax.set_ylabel(ylabel, fontsize=11)
            ax.legend(fontsize=8, loc='best')
            ax.grid(True, alpha=0.3)
        
        # Hide unused subplots
        for idx in range(n_metrics, len(axes)):
            axes[idx].axis('off')
        
        plt.tight_layout()
        
        # Save figure
        output_file = self.output_directory / plot_name
        plt.savefig(output_file, dpi=self.dpi, bbox_inches='tight')
        print(f"    Saved: {output_file}")
        
        plt.close()
        
        return output_file
    
    def generate_standard_radius_plots(self, df: pd.DataFrame):
        """
        Generate the standard set of master plots using RADIUS as X-axis.
        
        Creates radius-based versions of:
        1. Area analysis (Force, Work, Distance, Retraction Force)
        2. Modified area analysis (Force, Work, Distance, Peel Time)
        
        Args:
            df: DataFrame with batch processing results
        
        Returns:
            List of paths to generated plot files
        """
        print(f"\n{'='*60}")
        print(f"Generating Master Radius-Based Plots")
        print(f"{'='*60}\n")
        
        output_files = []
        
        # 1. Standard radius analysis plot
        metrics_standard = [
            ('peak_force_N', 'Peak Force (N)'),
            ('work_of_adhesion_mJ', 'Work of Adhesion (mJ)'),
            ('peel_distance_mm', 'Peel Distance (mm)'),
            ('peak_retraction_force_N', 'Peak Retraction Force (N)')
        ]
        
        output_files.append(
            self.generate_radius_analysis_plot(
                df=df,
                metrics=metrics_standard,
                plot_name='MASTER_radius_analysis.png',
                title='Master Radius Analysis',
                apply_abs=['peel_distance_mm']
            )
        )
        
        # 2. Modified radius analysis plot (with peel time instead of retraction force)
        metrics_modified = [
            ('peak_force_N', 'Peak Force (N)'),
            ('work_of_adhesion_mJ', 'Work of Adhesion (mJ)'),
            ('peel_distance_mm', 'Peel Distance (mm)'),
            ('total_peel_time_s', 'Total Peel Time (s)')
        ]
        
        output_files.append(
            self.generate_radius_analysis_plot(
                df=df,
                metrics=metrics_modified,
                plot_name='MASTER_radius_analysis_modified.png',
                title='Master Radius Analysis - Modified',
                apply_abs=['peel_distance_mm']
            )
        )
        
        print("\nAll radius-based plots generated successfully!")
        
        return output_files
