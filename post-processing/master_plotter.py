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
    
    def _bin_areas(self, df: pd.DataFrame, area_col: str = 'area_mm2', tolerance: float = 0.05):
        """
        Bin areas that are within tolerance % of each other.
        Replaces similar area values with their mean.
        
        Args:
            df: DataFrame with area column
            area_col: Name of area column
            tolerance: Fractional tolerance (0.05 = 5%)
        
        Returns:
            DataFrame with binned areas
        """
        df = df.copy()
        unique_areas = sorted(df[area_col].unique())
        area_bins = {}
        
        for area in unique_areas:
            # Check if this area fits into an existing bin
            binned = False
            for bin_center in area_bins.keys():
                if abs(area - bin_center) / bin_center <= tolerance:
                    area_bins[bin_center].append(area)
                    binned = True
                    break
            
            # Create new bin if needed
            if not binned:
                area_bins[area] = [area]
        
        # Create mapping from original areas to bin means
        area_mapping = {}
        for bin_areas in area_bins.values():
            bin_mean = np.mean(bin_areas)
            for area in bin_areas:
                area_mapping[area] = bin_mean
        
        # Apply mapping
        df[area_col] = df[area_col].map(area_mapping)
        
        # Report binning results
        n_original = len(unique_areas)
        n_binned = len(area_bins)
        if n_binned < n_original:
            print(f"  Binned {n_original} unique areas into {n_binned} bins (±{tolerance*100:.0f}% tolerance)")
        
        return df
        
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
            df: DataFrame with columns: membrane_type, tank_type, area_mm2, [metric columns]
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
        
        # Create detailed condition label: Membrane + Tank
        if 'detailed_condition' not in df.columns:
            df['detailed_condition'] = df['membrane_type'] + ' + ' + df['tank_type']
        
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
        conditions = sorted(df['detailed_condition'].unique())
        colors = plt.cm.tab10(np.linspace(0, 1, len(conditions)))
        color_map = dict(zip(conditions, colors))
        
        # Plot each metric
        for idx, (metric_col, ylabel) in enumerate(metrics):
            ax = axes[idx]
            
            for condition in conditions:
                condition_data = df[df['detailed_condition'] == condition].copy()
                color = color_map[condition]
                
                # Apply absolute value if requested
                if apply_abs and metric_col in apply_abs:
                    condition_data[metric_col] = condition_data[metric_col].abs()
                
                # Bin similar areas together (within 5%)
                condition_data = self._bin_areas(condition_data, 'area_mm2', tolerance=0.05)
                
                # Group by area and calculate mean, std, count
                grouped = condition_data.groupby('area_mm2')[metric_col].agg(['mean', 'std', 'count']).reset_index()
                areas = grouped['area_mm2'].values
                means = grouped['mean'].values
                stds = grouped['std'].values
                counts = grouped['count'].values
                
                # Calculate SEM (Standard Error of Mean)
                sems = stds / np.sqrt(counts)
                # Replace NaN (from single-sample groups) with 0
                sems = np.nan_to_num(sems, nan=0.0)
                
                # Debug: Print SEM stats for first condition
                if idx == 0 and conditions.index(condition) == 0:
                    print(f"    SEM range for {condition}: {sems[sems>0].min():.6f} to {sems[sems>0].max():.6f}" if any(sems>0) else f"    No SEM (all single samples) for {condition}")
                
                # Add filled SEM error region (only where SEM > 0)
                ax.fill_between(areas, means - sems, means + sems, color=color, alpha=0.2, zorder=1)
                
                # Plot means as markers only (no connecting line)
                ax.plot(areas, means, 'o', color=color, markersize=4, 
                       alpha=0.8, label=condition, zorder=3)
                
                # Add polynomial trendline through the means
                if add_trendlines and len(areas) > 2:
                    try:
                        # Fit polynomial to grouped means
                        z = np.polyfit(areas, means, 2)
                        p = np.poly1d(z)
                        
                        # Create smooth x-axis for plotting trendline
                        area_smooth = np.linspace(areas.min(), areas.max(), 100)
                        trendline = p(area_smooth)
                        
                        # Plot trendline (dotted)
                        ax.plot(area_smooth, trendline, ':', color=color, linewidth=1, alpha=0.7, zorder=2)
                    except Exception as e:
                        pass  # Skip trendline if fitting fails
            
            # Format subplot (V4 style)
            ax.set_xlabel('Contact Area (mm²)', fontsize=12, fontweight='bold')
            ax.set_ylabel(ylabel, fontsize=12, fontweight='bold')
            ax.legend(fontsize=10, loc='best')
            ax.grid(True, alpha=0.3)
            
            # Set y-axis to start at 0 if all values are positive
            if len(axes) > idx:  # Safety check
                y_data = []
                for condition in conditions:
                    condition_data = df[df['detailed_condition'] == condition].copy()
                    if apply_abs and metric_col in apply_abs:
                        condition_data[metric_col] = condition_data[metric_col].abs()
                    grouped = condition_data.groupby('area_mm2')[metric_col].mean()
                    y_data.extend(grouped.values)
                if len(y_data) > 0 and min(y_data) >= 0:
                    ax.set_ylim(bottom=0)
        
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
            add_trendlines=True,
            figsize=(16, 6)  # Match subplot dimensions: 1x2 layout with same height/width as 2x2
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
    
    def generate_area_ratio_analysis_plot(self,
                                          df: pd.DataFrame,
                                          plot_name: str = 'MASTER_area_ratio_analysis.png'):
        """
        Generate area ratio-based metrics plot.
        X-axis shows layer_area / membrane_area ratio.
        
        Args:
            df: DataFrame with batch processing results
            plot_name: Filename for saved plot
        
        Returns:
            Path to saved plot file
        """
        print(f"  Creating {plot_name}...")
        
        # Create detailed condition label: Membrane + Tank
        if 'detailed_condition' not in df.columns:
            df['detailed_condition'] = df['membrane_type'] + ' + ' + df['tank_type']
        
        # Create figure with 2x2 subplots
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('Master Area Ratio Analysis', fontsize=16, fontweight='bold')
        axes = axes.flatten()
        
        # Define color map for conditions
        conditions = sorted(df['detailed_condition'].unique())
        colors = plt.cm.tab10(np.linspace(0, 1, len(conditions)))
        color_map = dict(zip(conditions, colors))
        
        # Metrics to plot
        metrics = [
            ('peak_force_N', 'Peak Force (N)'),
            ('work_of_adhesion_mJ', 'Work of Adhesion (mJ)'),
            ('pre_initiation_distance_mm', 'Pre-Initiation Distance (mm)'),
            ('total_peel_time_s', 'Total Peel Time (s)')
        ]
        
        # Plot each metric
        for idx, (metric_col, ylabel) in enumerate(metrics):
            ax = axes[idx]
            
            for condition in conditions:
                condition_data = df[df['detailed_condition'] == condition].copy()
                color = color_map[condition]
                
                # Apply absolute value for distance metric
                if metric_col == 'pre_initiation_distance_mm':
                    condition_data[metric_col] = condition_data[metric_col].abs()
                
                # Bin similar area_ratios together (within 5%)
                condition_data = self._bin_areas(condition_data, 'area_ratio', tolerance=0.05)
                
                # Group by area_ratio and calculate mean, std, count
                grouped = condition_data.groupby('area_ratio')[metric_col].agg(['mean', 'std', 'count']).reset_index()
                ratios = grouped['area_ratio'].values
                means = grouped['mean'].values
                stds = grouped['std'].values
                counts = grouped['count'].values
                
                # Calculate SEM (Standard Error of Mean)
                sems = stds / np.sqrt(counts)
                # Replace NaN (from single-sample groups) with 0
                sems = np.nan_to_num(sems, nan=0.0)
                
                # Add filled SEM error region (only where SEM > 0)
                ax.fill_between(ratios, means - sems, means + sems, color=color, alpha=0.2, zorder=1)
                
                # Plot means as markers only (no connecting line)
                ax.plot(ratios, means, 'o', color=color, markersize=4, 
                       alpha=0.8, label=condition, zorder=3)
                
                # Add polynomial trendline through the means
                if len(ratios) > 2:
                    try:
                        # Fit polynomial to grouped means
                        z = np.polyfit(ratios, means, 2)
                        p = np.poly1d(z)
                        
                        # Create smooth x-axis for plotting trendline
                        ratio_smooth = np.linspace(ratios.min(), ratios.max(), 100)
                        trendline = p(ratio_smooth)
                        
                        # Plot trendline (dotted)
                        ax.plot(ratio_smooth, trendline, ':', color=color, linewidth=1, alpha=0.7, zorder=2)
                    except Exception as e:
                        pass  # Skip trendline if fitting fails
            
            # Format subplot (V4 style)
            ax.set_xlabel('Area Ratio (Layer / Membrane)', fontsize=12, fontweight='bold')
            ax.set_ylabel(ylabel, fontsize=12, fontweight='bold')
            ax.legend(fontsize=10, loc='best')
            ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Save figure
        output_file = self.output_directory / plot_name
        plt.savefig(output_file, dpi=self.dpi, bbox_inches='tight')
        print(f"    Saved: {output_file}")
        
        plt.close()
        
        return output_file
    
    def generate_standard_plots(self, df: pd.DataFrame):
        """
        Generate the standard set of master plots.
        
        Creates:
        1. Modified area analysis (Force, Work, Distance, Peel Time) - by absolute area
        2. Area ratio analysis (Force, Work, Distance, Peel Time) - by area ratio
        3. Distance analysis (Pre-init distance, Propagation distance) - by absolute area
        
        Args:
            df: DataFrame with batch processing results
        
        Returns:
            List of paths to generated plot files
        """
        print(f"\n{'='*60}")
        print(f"Generating Master Plots")
        print(f"{'='*60}\n")
        
        output_files = []
        
        # 1. Modified area analysis plot (with peel time)
        metrics_modified = [
            ('peak_force_N', 'Peak Force (N)'),
            ('work_of_adhesion_mJ', 'Work of Adhesion (mJ)'),
            ('pre_initiation_distance_mm', 'Pre-Initiation Distance (mm)'),
            ('total_peel_time_s', 'Total Peel Time (s)')
        ]
        
        output_files.append(
            self.generate_area_analysis_plot(
                df=df,
                metrics=metrics_modified,
                plot_name='MASTER_area_analysis.png',
                title='Master Area Analysis',
                apply_abs=['pre_initiation_distance_mm']
            )
        )
        
        # 2. Area ratio analysis plot
        output_files.append(self.generate_area_ratio_analysis_plot(df))
        
        # 3. Distance analysis plot
        output_files.append(self.generate_distance_analysis_plot(df))
        
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
        
        # Bin areas first (to handle slight measurement variations)
        df_with_radius = self._bin_areas(df_with_radius, area_col='area_mm2', tolerance=0.05)
        
        # Calculate radius from binned areas
        df_with_radius['radius_mm'] = np.sqrt(df_with_radius['area_mm2'] / np.pi)
        
        # Create detailed condition label: Membrane + Tank
        if 'detailed_condition' not in df_with_radius.columns:
            df_with_radius['detailed_condition'] = df_with_radius['membrane_type'] + ' + ' + df_with_radius['tank_type']
        
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
        conditions = sorted(df_with_radius['detailed_condition'].unique())
        colors = plt.cm.tab10(np.linspace(0, 1, len(conditions)))
        color_map = dict(zip(conditions, colors))
        
        # Plot each metric
        for idx, (metric_col, ylabel) in enumerate(metrics):
            ax = axes[idx]
            
            for condition in conditions:
                condition_data = df_with_radius[df_with_radius['detailed_condition'] == condition].copy()
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
    
    def generate_force_per_radius_plot(self, 
                                       df: pd.DataFrame,
                                       plot_name: str = 'MASTER_force_per_radius.png',
                                       force_col: str = 'peak_force_N',
                                       area_col: str = 'area_mm2',
                                       condition_col: str = 'detailed_condition'):
        """
        Generate Force/Radius vs Radius plot to analyze edge effects.
        
        This plot helps answer: Does force scale with perimeter (edge effect) 
        or does the force per unit perimeter change with size?
        
        Args:
            df: DataFrame with data
            plot_name: Output filename
            force_col: Column name for force values
            area_col: Column name for area values
            condition_col: Column for grouping conditions
        
        Returns:
            Path to saved plot
        """
        print(f"  Creating {plot_name}...")
        
        # Calculate radius and force per radius
        df_plot = df.copy()
        df_plot['radius_mm'] = np.sqrt(df_plot[area_col] / np.pi)
        df_plot['force_per_radius_N_per_mm'] = df_plot[force_col] / df_plot['radius_mm']
        
        # Bin areas for consistent grouping
        df_plot = self._bin_areas(df_plot, area_col=area_col, tolerance=0.05)
        
        # Recalculate radius from binned areas
        df_plot['radius_mm'] = np.sqrt(df_plot[area_col] / np.pi)
        df_plot['force_per_radius_N_per_mm'] = df_plot[force_col] / df_plot['radius_mm']
        
        # Get unique conditions
        conditions = df_plot[condition_col].unique()
        colors = plt.cm.Set2(np.linspace(0, 1, len(conditions)))
        
        # Create figure
        fig, ax = plt.subplots(1, 1, figsize=(10, 8))
        
        for idx, condition in enumerate(conditions):
            df_cond = df_plot[df_plot[condition_col] == condition]
            
            # Group by radius and calculate mean ± SEM
            grouped = df_cond.groupby('radius_mm')['force_per_radius_N_per_mm'].agg(['mean', 'sem', 'count'])
            radii = grouped.index.values
            means = grouped['mean'].values
            sems = grouped['sem'].values
            
            color = colors[idx]
            
            # Plot data points with error bars
            ax.errorbar(radii, means, yerr=sems, 
                       fmt='o', markersize=8, capsize=5, capthick=2,
                       color=color, label=condition, alpha=0.7)
            
            # Add polynomial trendline
            if len(radii) >= 3:
                try:
                    z = np.polyfit(radii, means, deg=2)
                    p = np.poly1d(z)
                    x_smooth = np.linspace(radii.min(), radii.max(), 100)
                    y_smooth = p(x_smooth)
                    ax.plot(x_smooth, y_smooth, '--', color=color, linewidth=2, alpha=0.6)
                except:
                    pass
        
        # Formatting
        ax.set_xlabel('Contact Radius (mm)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Force / Radius (N/mm)', fontsize=12, fontweight='bold')
        ax.set_title('Peak Force per Unit Radius vs Contact Radius\n(Edge Effect Analysis)', 
                    fontsize=14, fontweight='bold', pad=20)
        ax.legend(fontsize=10, loc='best')
        ax.grid(True, alpha=0.3)
        
        # Add interpretation text
        textstr = ('Interpretation:\n'
                  '• Constant F/r → Force scales with perimeter (edge-dominated)\n'
                  '• Increasing F/r → Bulk effects dominate at larger sizes\n'
                  '• Decreasing F/r → Edge effects more important at small sizes')
        ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=9,
               verticalalignment='top', bbox=dict(boxstyle='round', 
               facecolor='wheat', alpha=0.3))
        
        plt.tight_layout()
        
        # Save
        output_file = self.output_directory / plot_name
        plt.savefig(output_file, dpi=self.dpi, bbox_inches='tight')
        print(f"    Saved: {output_file}")
        
        plt.close()
        
        return output_file
