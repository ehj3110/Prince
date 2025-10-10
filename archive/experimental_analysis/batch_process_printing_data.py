#!/usr/bin/env python3
"""
Batch Processing Script for Printing Data Analysis
==================================================

This script processes all printing data folders in a master directory, analyzing
autolog CSV files and generating comprehensive peeling analysis plots for each
dataset. It uses the enhanced adhesion metrics and the proven plotting approach
to create detailed visualizations of layer peeling behavior.

Author: Created for comprehensive printing data analysis
Date: September 18, 2025
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks, savgol_filter
import re
import warnings
from pathlib import Path

# Replace EnhancedAdhesionAnalyzer with AdhesionMetricsCalculator
from adhesion_metrics_calculator import AdhesionMetricsCalculator

warnings.filterwarnings('ignore')

class BatchPrintingDataProcessor:
    """
    Processes multiple printing data folders and generates analysis plots
    """
    
    def __init__(self, master_folder_path):
        """
        Initialize the batch processor
        
        Args:
            master_folder_path (str): Path to master folder containing all print data folders
        """
        self.master_folder = Path(master_folder_path)
        self.analyzer = AdhesionMetricsCalculator()

        if not self.master_folder.exists():
            raise ValueError(f"Master folder does not exist: {master_folder_path}")
    
    def parse_folder_name(self, folder_name):
        """
        Parse folder name to extract resin, offset, liquid, and schedule information
        Expected format: "Resin_Offset_Liquid_Schedule"
        
        Args:
            folder_name (str): Name of the folder
            
        Returns:
            dict: Parsed information
        """
        parts = folder_name.split('_')
        
        # Try to identify components
        parsed = {
            'resin': 'Unknown',
            'offset': 'Unknown', 
            'liquid': 'Unknown',
            'schedule': 'Unknown',
            'full_name': folder_name
        }
        
        if len(parts) >= 4:
            parsed['resin'] = parts[0]
            parsed['offset'] = parts[1] 
            parsed['liquid'] = parts[2]
            parsed['schedule'] = '_'.join(parts[3:])  # In case schedule has underscores
        elif len(parts) >= 2:
            # Fallback for shorter names
            parsed['resin'] = parts[0]
            parsed['liquid'] = parts[-1]
            if len(parts) >= 3:
                parsed['offset'] = parts[1]
        
        return parsed
    
    def parse_csv_filename(self, filename):
        """
        Parse CSV filename to extract layer range
        Expected format: "autolog_LX-LY.csv" 
        
        Args:
            filename (str): CSV filename
            
        Returns:
            dict: Layer information or None if not matching pattern
        """
        pattern = r'autolog_L(\d+)-L(\d+)\.csv$'
        match = re.match(pattern, filename)
        
        if match:
            start_layer = int(match.group(1))
            end_layer = int(match.group(2))
            return {
                'start_layer': start_layer,
                'end_layer': end_layer,
                'layer_range': f"L{start_layer}-L{end_layer}"
            }
        return None
    
    def load_and_prepare_data(self, csv_path):
        """
        Load CSV data and prepare for analysis
        
        Args:
            csv_path (Path): Path to CSV file
            
        Returns:
            pandas.DataFrame: Prepared data or None if error
        """
        try:
            print(f"  Loading: {csv_path.name}")
            df = pd.read_csv(csv_path)
            
            # Standardize column names (handle different formats)
            column_mapping = {
                'Elapsed Time (s)': 'Time',
                'Position (mm)': 'Position', 
                'Force (N)': 'Force',
                'Time': 'Time',
                'Position': 'Position',
                'Force': 'Force'
            }
            
            for old_name, new_name in column_mapping.items():
                if old_name in df.columns:
                    df = df.rename(columns={old_name: new_name})
            
            # Verify required columns exist
            required_cols = ['Time', 'Position', 'Force']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                print(f"    Warning: Missing columns {missing_cols} in {csv_path.name}")
                return None
            
            # Remove NaN values
            df = df.dropna(subset=required_cols)
            
            if len(df) < 10:
                print(f"    Warning: Insufficient data in {csv_path.name} ({len(df)} points)")
                return None
            
            print(f"    Loaded {len(df)} data points")
            return df
            
        except Exception as e:
            print(f"    Error loading {csv_path.name}: {e}")
            return None
    
    def analyze_layer_timing(self, df, peak_indices):
        """
        Analyze timing phases for each layer - adapted from final_layer_visualization.py
        """
        time_data = df['Time'].values
        force_data = df['Force'].values
        position_data = df['Position'].values
        
        # Minimal smoothing to preserve peak timing and magnitude (exact from final_layer_visualization.py)
        # This prevents issues with underdamped oscillations after propagation
        if len(df) < 3:
            smoothed_force = force_data
        else:
            # Use minimal smoothing: window_length=3, polyorder=1 
            smoothed_force = savgol_filter(force_data, window_length=3, polyorder=1)
        
        def detect_propagation_end(peak_idx):
            """Simple propagation end detection"""
            # Look for where force returns close to baseline after peak
            peak_force = smoothed_force[peak_idx]
            
            # Search after peak for stabilization
            search_start = peak_idx + 10  # Start 10 points after peak
            search_end = min(len(smoothed_force), peak_idx + 500)  # Search up to 500 points after
            
            if search_start >= len(smoothed_force):
                return len(smoothed_force) - 1
            
            # Find where force stabilizes (standard deviation becomes small)
            window_size = 25
            for i in range(search_start, search_end - window_size):
                window = smoothed_force[i:i+window_size]
                if np.std(window) < 0.005:  # Small variation indicates stabilization
                    return i
            
            # Fallback: 70% of the way to next peak or end
            if len(peak_indices) > 1:
                next_peaks = [p for p in peak_indices if p > peak_idx]
                if next_peaks:
                    next_peak = next_peaks[0]
                    return peak_idx + int(0.7 * (next_peak - peak_idx))
            
            return min(len(smoothed_force) - 1, peak_idx + 200)
        
        def calculate_baseline(prop_end_idx):
            """Calculate baseline from propagation end region"""
            window_size = min(25, len(smoothed_force) - prop_end_idx)
            if window_size <= 0:
                return 0.0
            
            end_idx = min(prop_end_idx + window_size, len(smoothed_force))
            baseline_region = smoothed_force[prop_end_idx:end_idx]
            return np.mean(baseline_region)
        
        def find_pre_initiation(peak_idx, baseline):
            """Find when force starts rising above baseline"""
            # Search backwards from peak
            search_start = max(0, peak_idx - 300)  # Search up to 300 points before peak
            
            threshold = baseline + 0.002  # Small threshold above baseline
            
            for i in range(peak_idx - 1, search_start, -1):
                if smoothed_force[i] <= threshold:
                    return i + 1  # Return first point above threshold
            
            return search_start
        
        # Process each peak to create layer timing data
        layers = []
        colors = ['red', 'blue', 'green', 'orange', 'purple']
        
        for i, peak_idx in enumerate(peak_indices):
            # Detect timing phases
            prop_end_idx = detect_propagation_end(peak_idx)
            baseline = calculate_baseline(prop_end_idx)
            pre_init_idx = find_pre_initiation(peak_idx, baseline)
            
            # Calculate times
            peak_time = time_data[peak_idx]
            pre_init_time = time_data[pre_init_idx]
            prop_end_time = time_data[prop_end_idx]
            
            layer = {
                'peak_idx': peak_idx,
                'pre_init_idx': pre_init_idx,
                'prop_end_idx': prop_end_idx,
                'peak_time': peak_time,
                'pre_init_time': pre_init_time,
                'prop_end_time': prop_end_time,
                'peak_force': force_data[peak_idx],
                'baseline': baseline,
                'color': colors[i % len(colors)],
                'pre_init_duration': peak_time - pre_init_time,
                'prop_duration': prop_end_time - peak_time
            }
            
            layers.append(layer)
        
        return layers, smoothed_force
    
    def detect_force_peaks(self, df, min_peak_height=0.01, min_peak_distance=200):
        """
        Detect force peaks corresponding to layer peeling events
        
        Args:
            df: DataFrame with Time, Position, Force columns
            min_peak_height: Minimum force threshold for peak detection (N)
            min_peak_distance: Minimum distance between peaks (data points)
            
        Returns:
            tuple: (peak_indices, peak_info, smoothed_force)
        """
        # Smooth the force data for peak detection
        if len(df) < 11:
            smoothed_force = df['Force'].values
        else:
            window_length = min(11, len(df) // 2)
            if window_length % 2 == 0:
                window_length -= 1  # Must be odd
            smoothed_force = savgol_filter(df['Force'].values, window_length=window_length, polyorder=2)
        
        # Find peaks
        peak_indices, peak_properties = find_peaks(
            smoothed_force,
            height=min_peak_height,
            distance=min_peak_distance,
            prominence=0.005
        )
        
        # Analyze each peak
        peak_info = []
        for i, peak_idx in enumerate(peak_indices):
            if peak_idx < len(df):
                peak_time = df['Time'].iloc[peak_idx]
                peak_position = df['Position'].iloc[peak_idx]
                peak_force = df['Force'].iloc[peak_idx]
                peak_smoothed_force = smoothed_force[peak_idx]
                
                peak_info.append({
                    'index': peak_idx,
                    'time': peak_time,
                    'position': peak_position,
                    'force': peak_force,
                    'smoothed_force': peak_smoothed_force
                })
        
        return peak_indices, peak_info, smoothed_force
        """
        Detect force peaks corresponding to layer peeling events
        
        Args:
            df: DataFrame with Time, Position, Force columns
            min_peak_height: Minimum force threshold for peak detection (N)
            min_peak_distance: Minimum distance between peaks (data points)
            
        Returns:
            tuple: (peak_indices, peak_info, smoothed_force)
        """
        # Smooth the force data for peak detection
        if len(df) < 11:
            smoothed_force = df['Force'].values
        else:
            window_length = min(11, len(df) // 2)
            if window_length % 2 == 0:
                window_length -= 1  # Must be odd
            smoothed_force = savgol_filter(df['Force'].values, window_length=window_length, polyorder=2)
        
        # Find peaks
        peak_indices, peak_properties = find_peaks(
            smoothed_force,
            height=min_peak_height,
            distance=min_peak_distance,
            prominence=0.005
        )
        
        # Analyze each peak
        peak_info = []
        for i, peak_idx in enumerate(peak_indices):
            if peak_idx < len(df):
                peak_time = df['Time'].iloc[peak_idx]
                peak_position = df['Position'].iloc[peak_idx]
                peak_force = df['Force'].iloc[peak_idx]
                peak_smoothed_force = smoothed_force[peak_idx]
                
                peak_info.append({
                    'index': peak_idx,
                    'time': peak_time,
                    'position': peak_position,
                    'force': peak_force,
                    'smoothed_force': peak_smoothed_force
                })
        
        return peak_indices, peak_info, smoothed_force
    
    def create_analysis_plot(self, df, peak_indices, peak_info, smoothed_force, 
                           title_info, output_path, window_size=5.0):
        """
        Create comprehensive 4-subplot analysis plot with shaded regions - EXACT style from final_layer_visualization.py
        
        Args:
            df: DataFrame with force data
            peak_indices: Array of peak indices
            peak_info: List of peak information dictionaries
            smoothed_force: Smoothed force data
            title_info: Dictionary with title information
            output_path: Path for saving the plot
            window_size: Time window around peaks (seconds)
        """
        # Analyze layer timing to get shaded regions
        layers, analysis_force = self.analyze_layer_timing(df, peak_indices)
        
        # Create figure with 4 subplots - matching final_layer_visualization layout
        fig = plt.figure(figsize=(24, 18))
        gs = fig.add_gridspec(2, 2, height_ratios=[1, 1], width_ratios=[1, 1])
        
        # ============================================================================
        # SUBPLOT 1: Complete Overview (Top-Left)
        # ============================================================================
        ax_overview = fig.add_subplot(gs[0, 0])
        
        # Plot raw and smoothed data
        ax_overview.plot(df['Time'], df['Force'], 'k-', linewidth=1, alpha=0.4, label='Raw Force Data')
        ax_overview.plot(df['Time'], analysis_force, 'navy', linewidth=2.5, alpha=0.9, label='Smoothed Force (Analysis)')
        
        # Add layer annotations and markers
        for i, layer in enumerate(layers):
            color = layer['color']
            layer_num = title_info['layer_range'].split('-')[0].replace('L', '')
            actual_layer = int(layer_num) + i
            
            # Peak force marker and line
            ax_overview.plot(layer['peak_time'], layer['peak_force'], 'o', color=color, 
                            markersize=12, zorder=5, markeredgecolor='black', markeredgewidth=2)
            ax_overview.axvline(x=layer['peak_time'], color=color, linestyle='--', 
                               linewidth=3, alpha=0.8, zorder=3)
            
            # Add layer number annotations
            ax_overview.annotate(f'L{actual_layer}', 
                                xy=(layer['peak_time'], layer['peak_force']),
                                xytext=(layer['peak_time'], layer['peak_force'] + 0.02),
                                ha='center', va='bottom', fontsize=12, fontweight='bold',
                                color=color, zorder=6)
        
        ax_overview.set_xlabel('Time (s)', fontsize=14, fontweight='bold')
        ax_overview.set_ylabel('Force (N)', fontsize=14, fontweight='bold')
        ax_overview.set_title(f'Complete Force Profile - Three Layers ({title_info["layer_range"]})', 
                             fontsize=16, fontweight='bold')
        ax_overview.grid(True, alpha=0.3)
        ax_overview.legend(fontsize=11, loc='upper right')
        
        # ============================================================================
        # SUBPLOTS 2-4: Individual Layer Details with Shaded Regions
        # ============================================================================
        subplot_positions = [gs[0, 1], gs[1, 0], gs[1, 1]]
        
        for i, layer in enumerate(layers[:3]):  # Only first 3 layers
            ax = fig.add_subplot(subplot_positions[i])
            color = layer['color']
            
            # Calculate layer number
            layer_num = title_info['layer_range'].split('-')[0].replace('L', '')
            actual_layer = int(layer_num) + i
            
            # Define focused window around the peeling event
            buffer_time = 1.0  # 1 second buffer
            window_start_time = layer['pre_init_time'] - buffer_time
            window_end_time = layer['prop_end_time'] + buffer_time
            
            # Filter data for window
            window_mask = (df['Time'] >= window_start_time) & (df['Time'] <= window_end_time)
            window_df = df[window_mask].copy()
            
            if len(window_df) == 0:
                ax.text(0.5, 0.5, f'No data in window\\nfor Layer {actual_layer}', 
                       ha='center', va='center', transform=ax.transAxes)
                ax.set_title(f'Layer {actual_layer}: No Data')
                continue
            
            # Get corresponding analysis data for window
            window_indices = np.where(window_mask)[0]
            if len(window_indices) > 0:
                window_analysis_force = analysis_force[window_indices]
            else:
                window_analysis_force = []
            
            # Plot force data - emphasizing smoothed for analysis
            ax.plot(window_df['Time'], window_df['Force'], 'k-', linewidth=1, alpha=0.4, label='Raw Force')
            if len(window_analysis_force) == len(window_df):
                ax.plot(window_df['Time'], window_analysis_force, color=color, linewidth=3.5, alpha=0.95, 
                       label='Smoothed Force (Analysis)', zorder=3)
            
            # ========================================================================
            # SHADED BANDS FOR PEELING STAGES (exact from final_layer_visualization.py)
            # ========================================================================
            
            # Stage 1: Pre-Initiation (Elastic Loading) - Light Blue Shading
            ax.axvspan(layer['pre_init_time'], layer['peak_time'], 
                      color='lightblue', alpha=0.5, 
                      label='Pre-Initiation', zorder=1)
            
            # Stage 2: Propagation (Crack Growth) - Light Coral Shading  
            ax.axvspan(layer['peak_time'], layer['prop_end_time'], 
                      color='lightcoral', alpha=0.5, 
                      label='Propagation', zorder=1)
            
            # Stage 3: Post-Propagation (if visible in window) - Light Yellow Shading
            if layer['prop_end_time'] < window_df['Time'].max():
                ax.axvspan(layer['prop_end_time'], window_df['Time'].max(), 
                          color='lightyellow', alpha=0.3, zorder=1)
            
            # ========================================================================
            # VERTICAL LINES AND MARKERS
            # ========================================================================
            
            # Peak force location (initiation moment)
            ax.axvline(x=layer['peak_time'], color=color, linestyle='--', linewidth=4, zorder=4)
            ax.plot(layer['peak_time'], layer['peak_force'], 'o', color=color, 
                   markersize=14, zorder=5, markeredgecolor='black', markeredgewidth=2,
                   label=f'Peak: {layer["peak_force"]:.4f}N')
            
            # Propagation end location
            ax.axvline(x=layer['prop_end_time'], color='purple', linestyle=':', linewidth=4, zorder=4)
            prop_end_force = analysis_force[layer['prop_end_idx']] if layer['prop_end_idx'] < len(analysis_force) else layer['baseline']
            ax.plot(layer['prop_end_time'], prop_end_force, 's', 
                   color='purple', markersize=10, zorder=5, markeredgecolor='black', markeredgewidth=1,
                   label='Prop End')
            
            # ========================================================================
            # HORIZONTAL BASELINE LINE
            # ========================================================================
            
            # Baseline from propagation end region
            ax.axhline(y=layer['baseline'], color='gray', linestyle='--', linewidth=3, alpha=0.6,
                      label=f'Baseline: {layer["baseline"]:.4f}N', zorder=2)
            
            # ========================================================================
            # MEASUREMENT ANNOTATIONS
            # ========================================================================
            
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
            ax.text((layer['prop_end_time'] + layer['peak_time'])/2, y_annotation2 - 0.008, 
                   f't_prop = {layer["prop_duration"]:.2f}s', 
                   ha='center', fontsize=10, color='red', fontweight='bold',
                   bbox=dict(boxstyle='round,pad=0.2', facecolor='lightcoral', alpha=0.8))
            
            # ========================================================================
            # SUBPLOT FORMATTING
            # ========================================================================
            
            ax.set_xlabel('Time (s)', fontsize=12, fontweight='bold')
            ax.set_ylabel('Force (N)', fontsize=12, fontweight='bold')
            ax.set_title(f'Layer {actual_layer} - Peeling Stages with Shaded Bands', 
                        fontsize=14, fontweight='bold', color=color)
            ax.grid(True, alpha=0.3)
            
            # Legend
            ax.legend(fontsize=10, loc='upper left', ncol=1, framealpha=0.9, 
                     fancybox=True, shadow=True)
            
            # Set appropriate limits for clear visualization
            y_min = layer['baseline'] - 0.045
            y_max = layer['peak_force'] + 0.015
            ax.set_ylim(y_min, y_max)
            
            # X-limits to focus on the peeling event
            x_margin = (layer['prop_end_time'] - layer['pre_init_time']) * 0.3
            ax.set_xlim(layer['pre_init_time'] - x_margin, layer['prop_end_time'] + x_margin)
            
            # Print layer analysis
            print(f"    Layer {actual_layer} Timing Analysis:")
            print(f"      Pre-initiation: {layer['pre_init_time']:.2f}s to {layer['peak_time']:.2f}s ({layer['pre_init_duration']:.2f}s)")
            print(f"      Propagation: {layer['peak_time']:.2f}s to {layer['prop_end_time']:.2f}s ({layer['prop_duration']:.2f}s)")
            print(f"      Peak Force: {layer['peak_force']:.4f}N, Baseline: {layer['baseline']:.4f}N")
        
        # ============================================================================
        # FINAL LAYOUT AND SAVE
        # ============================================================================
        
        # Main figure title
        fig.suptitle(f'{title_info["resin"]} - {title_info["liquid"]} - {title_info["layer_range"]}\\nPeeling Stages with Shaded Bands and Event Markers', 
                     fontsize=20, fontweight='bold', y=0.98)
        
        # Adjust layout
        plt.tight_layout()
        plt.subplots_adjust(top=0.92, hspace=0.3, wspace=0.3)
        
        # Save the plot
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()  # Close to free memory
        
        print(f"    Plot saved: {output_path.name}")
    
    def process_single_folder(self, folder_path):
        """
        Process a single printing data folder
        
        Args:
            folder_path (Path): Path to the folder containing CSV files
        """
        print(f"\\nProcessing folder: {folder_path.name}")
        
        # Parse folder information
        folder_info = self.parse_folder_name(folder_path.name)
        print(f"  Resin: {folder_info['resin']}, Liquid: {folder_info['liquid']}")
        
        # Find all autolog CSV files (skip PeakForce_Log_PrintX files)
        csv_files = []
        for file in folder_path.iterdir():
            if (file.suffix.lower() == '.csv' and 
                file.name.startswith('autolog_L') and
                not file.name.startswith('PeakForce_Log_Print')):
                csv_files.append(file)
        
        if not csv_files:
            print(f"  No autolog CSV files found in {folder_path.name}")
            return
        
        print(f"  Found {len(csv_files)} autolog CSV files")
        
        # Process each CSV file
        for csv_file in csv_files:
            # Parse layer information
            layer_info = self.parse_csv_filename(csv_file.name)
            if not layer_info:
                print(f"  Skipping {csv_file.name} (doesn't match expected pattern)")
                continue
            
            # Load and prepare data
            df = self.load_and_prepare_data(csv_file)
            if df is None:
                continue
            
            # Detect peaks
            peak_indices, peak_info, smoothed_force = self.detect_force_peaks(df)
            
            if len(peak_info) == 0:
                print(f"    No peaks detected in {csv_file.name}")
                continue
            
            print(f"    Found {len(peak_info)} peaks")
            
            # Create title information
            title_info = {
                'resin': folder_info['resin'],
                'liquid': folder_info['liquid'],
                'layer_range': layer_info['layer_range'],
                'offset': folder_info['offset'],
                'schedule': folder_info['schedule']
            }
            
            # Generate output filename
            output_filename = f"analysis_{folder_info['resin']}_{folder_info['liquid']}_{layer_info['layer_range']}.png"
            output_path = folder_path / output_filename
            
            # Create and save plot with correct window size
            self.create_analysis_plot(df, peak_indices, peak_info, smoothed_force,
                                    title_info, output_path, window_size=5.0)
    
    def process_all_folders(self):
        """
        Process all folders in the master directory
        """
        print(f"Starting batch processing of: {self.master_folder}")
        print(f"Master folder exists: {self.master_folder.exists()}")
        
        # Find all subdirectories
        folders = [f for f in self.master_folder.iterdir() if f.is_dir()]
        
        if not folders:
            print("No subdirectories found in master folder")
            return
        
        print(f"Found {len(folders)} folders to process")
        
        # Process each folder
        for folder in folders:
            try:
                self.process_single_folder(folder)
            except Exception as e:
                print(f"Error processing folder {folder.name}: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"\\n=== Batch processing complete ===")
        print(f"Processed {len(folders)} folders")

def main():
    """
    Main function to run the batch processing
    """
    # Master folder path (as specified by user)
    master_folder_path = r"C:\Users\cheng sun\BoyuanSun\Slicing\Evan\5mmDiameterCylinder_SpeedTest_V3\Printing_Logs\DataToExport"
    
    print("=== Batch Printing Data Analysis ===")
    print(f"Target directory: {master_folder_path}")
    
    try:
        # Create processor and run
        processor = BatchPrintingDataProcessor(master_folder_path)
        processor.process_all_folders()
        
    except Exception as e:
        print(f"Error in batch processing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
