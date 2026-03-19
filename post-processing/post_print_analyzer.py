"""
Post-Print Analysis and Plotting System
=======================================

This script automatically processes data from completed prints and generates
comprehensive adhesion analysis plots using the RawData_Processor workflow.

Workflow:
1. Detect completed prints from AutomatedLayerLogger CSV files
2. Process data through RawDataProcessor (same as batch processing)
3. Generate comprehensive layer-by-layer plots
4. Create summary analysis

Author: Cheng Sun Lab Team
Date: October 9, 2025
"""

import os
import sys
from pathlib import Path
import argparse
from datetime import datetime
import threading

# Configure matplotlib for thread-safe operation before importing plotting modules
import matplotlib
if threading.current_thread() != threading.main_thread():
    matplotlib.use('Agg')  # Non-interactive backend for background threads

# Add parent directory to path so we can import support_modules
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

# Add post-processing directory to path for local imports
post_processing_dir = Path(__file__).parent
sys.path.insert(0, str(post_processing_dir))

# Import our analysis tools using RawData_Processor workflow
from support_modules.adhesion_metrics_calculator import AdhesionMetricsCalculator
from RawData_Processor import RawDataProcessor
from analysis_plotter import AnalysisPlotter

class PostPrintAnalyzer:
    """
    Automated post-processing for 3D printing adhesion data.
    Uses RawDataProcessor workflow for consistency with batch processing.
    """
    
    def __init__(self):
        # Use corrected light smoothing settings
        self.calculator = AdhesionMetricsCalculator(
            median_kernel=5,
            savgol_window=9,
            savgol_order=2,
            baseline_threshold_factor=0.002,
            min_peak_height=0.01,
            min_peak_distance=50
        )
        
        # Use AnalysisPlotter (same as batch processing)
        self.plotter = AnalysisPlotter()
        
        # Initialize RawDataProcessor (handles all analysis and plotting)
        self.processor = RawDataProcessor(self.calculator)
        
    def find_current_session_in_daily_dir(self, daily_dir):
        """
        Find the most recent print session within a specific daily directory.
        
        Args:
            daily_dir: Daily directory path (e.g., "2025-09-21")
            
        Returns:
            Most recent print session in that daily directory or None
        """
        print(f"Scanning for current session in daily dir: {daily_dir}")
        
        daily_path = Path(daily_dir)
        
        if not daily_path.exists():
            print(f"Warning: Daily directory {daily_dir} does not exist")
            return None
        
        latest_session = None
        latest_time = 0
        
        # Look for print directories (Print 1, Print 2, etc.)
        for print_dir in daily_path.iterdir():
            if not print_dir.is_dir() or not print_dir.name.startswith("Print "):
                continue
            
            # Look for AutomatedLayerLogger CSV files
            csv_files = list(print_dir.glob("autolog_*.csv"))
            
            if csv_files:
                # Get the modification time of the most recent CSV file
                csv_mod_times = [f.stat().st_mtime for f in csv_files]
                session_time = max(csv_mod_times)
                
                if session_time > latest_time:
                    latest_time = session_time
                    latest_session = {
                        'path': print_dir,
                        'date': daily_path.name,
                        'print_number': print_dir.name,
                        'csv_files': csv_files
                    }
        
        if latest_session:
            print(f"  Current session in daily dir: {latest_session['date']}/{latest_session['print_number']} ({len(latest_session['csv_files'])} CSV files)")
        else:
            print("  No sessions found in daily directory")
            
        return latest_session
        
    def find_current_session(self, base_log_dir):
        """
        Find the most recent (current) print session with AutomatedLayerLogger data.
        
        Args:
            base_log_dir: Base directory containing date folders with print sessions
            
        Returns:
            Most recent print session or None if not found
        """
        print(f"Scanning for current session in: {base_log_dir}")
        
        base_path = Path(base_log_dir)
        
        if not base_path.exists():
            print(f"Warning: Base directory {base_log_dir} does not exist")
            return None
        
        latest_session = None
        latest_time = 0
        
        # Look for date directories (YYYY-MM-DD format)
        for date_dir in base_path.iterdir():
            if not date_dir.is_dir():
                continue
                
            # Look for print directories (Print 1, Print 2, etc.)
            for print_dir in date_dir.iterdir():
                if not print_dir.is_dir() or not print_dir.name.startswith("Print "):
                    continue
                
                # Look for AutomatedLayerLogger CSV files
                csv_files = list(print_dir.glob("autolog_*.csv"))
                
                if csv_files:
                    # Get the modification time of the most recent CSV file
                    csv_mod_times = [f.stat().st_mtime for f in csv_files]
                    session_time = max(csv_mod_times)
                    
                    if session_time > latest_time:
                        latest_time = session_time
                        latest_session = {
                            'path': print_dir,
                            'date': date_dir.name,
                            'print_number': print_dir.name,
                            'csv_files': csv_files
                        }
        
        if latest_session:
            print(f"  Current session: {latest_session['date']}/{latest_session['print_number']} ({len(latest_session['csv_files'])} CSV files)")
        else:
            print("  No sessions found")
            
        return latest_session
        
    def find_print_sessions(self, base_log_dir):
        """
        Find all completed print sessions with AutomatedLayerLogger data.
        
        Args:
            base_log_dir: Base directory containing date folders with print sessions
            
        Returns:
            List of print session paths with CSV data
        """
        print(f"Scanning for print sessions in: {base_log_dir}")
        
        sessions = []
        base_path = Path(base_log_dir)
        
        if not base_path.exists():
            print(f"Warning: Base directory {base_log_dir} does not exist")
            return sessions
        
        # Look for date directories (YYYY-MM-DD format)
        for date_dir in base_path.iterdir():
            if not date_dir.is_dir():
                continue
                
            # Look for print directories (Print 1, Print 2, etc.)
            for print_dir in date_dir.iterdir():
                if not print_dir.is_dir() or not print_dir.name.startswith("Print "):
                    continue
                
                # Look for AutomatedLayerLogger CSV files
                csv_files = list(print_dir.glob("autolog_*.csv"))
                
                if csv_files:
                    sessions.append({
                        'path': print_dir,
                        'date': date_dir.name,
                        'print_number': print_dir.name,
                        'csv_files': csv_files
                    })
                    print(f"  Found: {date_dir.name}/{print_dir.name} ({len(csv_files)} CSV files)")
        
        print(f"Total sessions found: {len(sessions)}")
        return sessions
    
    def analyze_print_session(self, session):
        """
        Analyze a single print session and generate plots.
        
        Args:
            session: Dictionary with session information
        """
        print(f"\n{'='*60}")
        print(f"ANALYZING {session['date']}/{session['print_number']}")
        print(f"{'='*60}")
        
        session_path = session['path']
        analysis_results = []
        
        for csv_file in session['csv_files']:
            # Skip the problematic L50-L53 file as requested
            if 'L50-L53' in csv_file.name or 'L50_L53' in csv_file.name:
                print(f"\nSkipping: {csv_file.name} (excluded as requested)")
                continue
                
            print(f"\nProcessing: {csv_file.name}")
            
            try:
                # Load and analyze the CSV data
                result = self._analyze_csv_file(csv_file, session_path)
                
                if result:
                    analysis_results.append(result)
                    print(f"  [OK] Analysis complete - {len(result['layers'])} layers processed")
                else:
                    print(f"  [X] Analysis failed")
                    
            except Exception as e:
                print(f"  [X] Error analyzing {csv_file.name}: {e}")
                import traceback
                traceback.print_exc()
        
        # Generate session summary
        if analysis_results:
            self._generate_session_summary(session, analysis_results)
            
        # Generate master plot with work of adhesion data if available
        self._generate_master_plot(session)
        
        return analysis_results
    
    def _analyze_csv_file(self, csv_file, output_dir):
        """
        Analyze a single CSV file using RawDataProcessor and generate plots.
        """
        print(f"    Processing: {csv_file.name}")
        
        # Generate plot path
        plot_title = f"Post-Print Analysis - {csv_file.stem}"
        plot_path = output_dir / f"{csv_file.stem}_analysis.png"
        
        try:
            # Load data for plotting
            import pandas as pd
            df = pd.read_csv(csv_file)
            time_data = df['Elapsed Time (s)'].to_numpy()
            force_data = df['Force (N)'].to_numpy()
            
            # Use RawDataProcessor to analyze data
            layers = self.processor.process_csv(str(csv_file))
            
            if not layers or len(layers) == 0:
                print(f"    [X] Analysis failed - no layers detected")
                return None
            
            # Get smoothed force from calculator
            smoothed_force = self.calculator._apply_smoothing(force_data)
            
            # Now generate the plot using AnalysisPlotter
            try:
                self.plotter.create_plot(
                    time_data=time_data,
                    force_data=force_data,
                    smoothed_force=smoothed_force,
                    layers=layers,
                    title=plot_title,
                    save_path=str(plot_path)
                )
                print(f"    [PLOT] Plot saved: {plot_path.name}")
            except Exception as plot_err:
                print(f"    [!] Warning: Plot generation failed: {plot_err}")
                import traceback
                traceback.print_exc()
                # Continue even if plotting fails - we still have the data
            
            print(f"    [OK] Analysis complete - {len(layers)} layers processed")
            
            return {
                'csv_file': csv_file,
                'plot_path': plot_path if plot_path.exists() else None,
                'layers': layers,
                'data_points': len(layers),  # Number of layers
                'time_range': f"Processed {len(layers)} layers"
            }
            
        except Exception as e:
            print(f"    [X] Error during processing: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _generate_session_summary(self, session, analysis_results):
        """
        Generate a summary report for the print session.
        """
        summary_path = session['path'] / "POST_PROCESSING_SUMMARY.md"
        
        with open(summary_path, 'w') as f:
            f.write(f"# Post-Print Analysis Summary\n")
            f.write(f"**Session:** {session['date']} / {session['print_number']}\n")
            f.write(f"**Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Processing Method:** RawDataProcessor (same as batch processing)\n\n")
            
            f.write(f"## Files Processed\n")
            for result in analysis_results:
                f.write(f"- **{result['csv_file'].name}**\n")
                f.write(f"  - {result['time_range']}\n")
                if result['plot_path']:
                    f.write(f"  - Plot: {result['plot_path'].name}\n")
                f.write(f"\n")
            
            f.write(f"## Notes\n")
            f.write(f"- Analysis performed with RawDataProcessor workflow\n")
            f.write(f"- Consistent with batch processing methodology\n")
            f.write(f"- Automatic layer detection and segmentation\n")
        
        print(f"  [SUMMARY] Summary saved: {summary_path.name}")
    
    def _generate_master_plot(self, session):
        """
        Generate a master plot combining all work of adhesion data for the session.
        Uses radius (calculated from area) as X-axis, matching batch processing style.
        
        Args:
            session: Dictionary with session information
        """
        import pandas as pd
        import matplotlib.pyplot as plt
        import numpy as np
        
        session_path = session['path']
        
        # Find the automated work of adhesion CSV file
        woa_files = list(session_path.glob("automated_work_of_adhesion*.csv"))
        
        if not woa_files:
            print("  [INFO] No work of adhesion data found for master plot")
            return
        
        woa_file = woa_files[0]  # Use the first one found
        print(f"\n  [PLOT] Generating master plot with work of adhesion data from: {woa_file.name}")
        
        try:
            # Load work of adhesion data
            df = pd.read_csv(woa_file)
            
            if df.empty or len(df) == 0:
                print("    [!] Work of adhesion file is empty")
                return
            
            # Remove the last row (often incomplete/corrupted)
            if len(df) > 1:
                df = df.iloc[:-1]
                print(f"    [INFO] Removed last row, processing {len(df)} layers")
            
            # Required columns for master plot
            required_cols = ['Peak_Force_N', 'Work_of_Adhesion_mJ', 'Cross_Sectional_Area_mm2']
            layer_col = 'Layer_Number' if 'Layer_Number' in df.columns else 'Layer'
            
            if not all(col in df.columns for col in required_cols):
                print(f"    [!] Missing required columns in work of adhesion file")
                print(f"    Required: {required_cols}")
                print(f"    Available: {df.columns.tolist()}")
                return
            
            if layer_col not in df.columns:
                print(f"    [!] No layer column found (expected 'Layer' or 'Layer_Number')")
                return
            
            # Calculate radius from area (r = sqrt(A/π))
            df['radius_mm'] = np.sqrt(df['Cross_Sectional_Area_mm2'] / np.pi)
            
            # Remove the first radius data point (edge case, outside normal conditions)
            if len(df) > 1:
                min_radius = df['radius_mm'].min()
                df = df[df['radius_mm'] > min_radius]
                print(f"    [INFO] Excluded smallest radius ({min_radius:.3f} mm) as edge case, {len(df)} layers remaining")
            
            # Check if we have varying radii (expanding cone) or constant radius (cylinder)
            unique_radii = df['radius_mm'].nunique()
            radius_range = df['radius_mm'].max() - df['radius_mm'].min()
            
            print(f"    [INFO] Found {unique_radii} unique radii, range: {radius_range:.3f} mm")
            
            if unique_radii < 3 or radius_range < 0.1:
                print(f"    [!] Insufficient radius variation for master plot (need expanding cone data)")
                print(f"    [!] Skipping master plot generation")
                return
            
            # Prepare metrics for plotting
            metrics = [
                ('Peak_Force_N', 'Peak Force (N, baseline-corrected)'),
                ('Work_of_Adhesion_mJ', 'Work of Adhesion (mJ)')
            ]
            
            # Add optional metrics if available
            if 'Total_Peel_Distance_mm' in df.columns:
                metrics.append(('Total_Peel_Distance_mm', 'Peel Distance (mm)'))
            if 'Peak_Retraction_Force_N' in df.columns:
                metrics.append(('Peak_Retraction_Force_N', 'Peak Retraction Force (N)'))
            
            # Determine subplot layout based on number of metrics
            n_metrics = len(metrics)
            if n_metrics == 1:
                nrows, ncols = 1, 1
            elif n_metrics == 2:
                nrows, ncols = 1, 2
            elif n_metrics <= 4:
                nrows, ncols = 2, 2
            else:
                nrows, ncols = 2, 3
            
            # Create figure
            fig, axes = plt.subplots(nrows, ncols, figsize=(16, 12))
            if n_metrics == 1:
                axes = np.array([axes])
            else:
                axes = axes.flatten()
            
            # Color scheme - single condition (this print session)
            color = '#2E86AB'  # Primary blue
            
            # Plot each metric vs radius
            for idx, (metric_col, ylabel) in enumerate(metrics):
                print(f"    [DEBUG] Plotting metric {idx+1}/{n_metrics}: {ylabel}")
                ax = axes[idx]
                
                # Group by radius and calculate mean ± SEM using pandas built-in
                print(f"    [DEBUG] Grouping by radius...")
                grouped = df.groupby('radius_mm')[metric_col].agg(['mean', 'sem'])
                grouped_radii = grouped.index.values
                means = grouped['mean'].values
                sems = grouped['sem'].values
                print(f"    [DEBUG] Grouped into {len(grouped_radii)} radius bins")
                
                # Add SEM shaded region
                print(f"    [DEBUG] Adding SEM shaded region...")
                ax.fill_between(grouped_radii, means - sems, means + sems, 
                               color=color, alpha=0.2)
                
                # Plot mean with markers on TOP of shaded region
                print(f"    [DEBUG] Plotting mean markers...")
                ax.plot(grouped_radii, means, 'o', color=color, markersize=5, alpha=0.8, zorder=3)
                
                # Add power-law trendline (y = a * x^b)
                r_squared = 0
                fit_equation = ""
                if len(grouped_radii) > 2:
                    try:
                        print(f"    [DEBUG] Fitting power-law trendline (y = a * x^b)...")
                        # Fit power law: log(y) = log(a) + b*log(x)
                        log_radii = np.log(grouped_radii)
                        log_means = np.log(means)
                        coeffs = np.polyfit(log_radii, log_means, 1)
                        b = coeffs[0]  # power
                        log_a = coeffs[1]  # log of coefficient
                        a = np.exp(log_a)
                        
                        # Generate smooth curve
                        radius_smooth = np.linspace(grouped_radii.min(), grouped_radii.max(), 100)
                        fit_smooth = a * (radius_smooth ** b)
                        ax.plot(radius_smooth, fit_smooth, '-', color=color, 
                               linewidth=2, alpha=0.9, zorder=2)
                        
                        # Calculate R-squared
                        predicted = a * (grouped_radii ** b)
                        ss_res = np.sum((means - predicted) ** 2)
                        ss_tot = np.sum((means - np.mean(means)) ** 2)
                        r_squared = 1 - (ss_res / ss_tot)
                        
                        fit_equation = f"y = {a:.4f} × x$^{{{b:.3f}}}$\nR² = {r_squared:.4f}"
                        print(f"    [DEBUG] Power-law fit: y = {a:.4f} * x^{b:.4f}, R² = {r_squared:.4f}")
                    except Exception as e:
                        print(f"    [!] Could not fit power-law trendline: {e}")
                
                # Add text box with equation and R²
                if fit_equation:
                    # Determine placement based on data distribution
                    # If data is higher on left, place text on right; otherwise on left
                    left_mean = np.mean(means[:len(means)//3])
                    right_mean = np.mean(means[-len(means)//3:])
                    
                    if left_mean > right_mean:
                        # Data higher on left, place text on right
                        text_x = 0.95
                        ha = 'right'
                    else:
                        # Data higher on right or equal, place text on left
                        text_x = 0.05
                        ha = 'left'
                    
                    ax.text(text_x, 0.95, fit_equation, 
                           transform=ax.transAxes, fontsize=11,
                           verticalalignment='top', horizontalalignment=ha,
                           bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
                
                # Format subplot
                print(f"    [DEBUG] Formatting subplot...")
                ax.set_xlabel('Contact Radius (mm)', fontsize=13, fontweight='bold')
                ax.set_ylabel(ylabel, fontsize=13, fontweight='bold')
                ax.set_title(ylabel, fontsize=14, fontweight='bold')
                ax.tick_params(labelsize=11)
                ax.grid(True, alpha=0.3)
                
                # Set y-axis to start at 0 for positive metrics
                if np.all(means >= 0):
                    ax.set_ylim(bottom=0)
                print(f"    [DEBUG] Metric {ylabel} complete")
            
            # Hide unused subplots
            print(f"    [DEBUG] Hiding unused subplots...")
            for idx in range(n_metrics, len(axes)):
                axes[idx].axis('off')
            
            # Overall title (matching batch processing style)
            print(f"    [DEBUG] Adding title and adjusting layout...")
            fig.suptitle(f'{session["date"]} / {session["print_number"]}\nMaster Radius Analysis - Work of Adhesion',
                        fontsize=16, fontweight='bold')
            
            # Adjust layout
            plt.tight_layout()
            plt.subplots_adjust(top=0.94)
            
            # Save plot
            print(f"    [DEBUG] Saving plot...")
            master_plot_path = session_path / "MASTER_work_of_adhesion_analysis.png"
            plt.savefig(master_plot_path, dpi=300, bbox_inches='tight', facecolor='white')
            plt.close()
            print(f"    [DEBUG] Plot closed")
            
            print(f"    [OK] Master plot saved: {master_plot_path.name}")
            
        except Exception as e:
            print(f"    [X] Error generating master plot: {e}")
            import traceback
            traceback.print_exc()


def main():
    """
    Main entry point for post-processing script.
    """
    parser = argparse.ArgumentParser(description='Post-print adhesion analysis')
    parser.add_argument('--log-dir', 
                       default=r"C:\\Users\\cheng sun\\Desktop\\Evan_AdhesionTests",
                       help='Base directory containing print logs')
    parser.add_argument('--session', 
                       help='Specific session to analyze (format: YYYY-MM-DD/Print N)')
    parser.add_argument('--current-only', action='store_true',
                       help='Analyze only the most recent session')
    
    args = parser.parse_args()
    
    analyzer = PostPrintAnalyzer()
    
    print("POST-PRINT ADHESION ANALYSIS")
    print("="*50)
    print("Using corrected light smoothing settings")
    print("Generating plots with accurate propagation end times")
    print("="*50)
    
    if args.session:
        # Analyze specific session
        session_path = Path(args.log_dir) / args.session
        if session_path.exists():
            csv_files = list(session_path.glob("autolog_*.csv"))
            if csv_files:
                session = {
                    'path': session_path,
                    'date': session_path.parent.name,
                    'print_number': session_path.name,
                    'csv_files': csv_files
                }
                analyzer.analyze_print_session(session)
            else:
                print(f"No CSV files found in {session_path}")
        else:
            print(f"Session not found: {session_path}")
    elif args.current_only:
        # Analyze only the current/latest session
        current_session = analyzer.find_current_session(args.log_dir)
        if current_session:
            analyzer.analyze_print_session(current_session)
        else:
            print("No current session found!")
    else:
        # Find and analyze all sessions
        sessions = analyzer.find_print_sessions(args.log_dir)
        
        if not sessions:
            print("No print sessions found!")
            return
        
        for session in sessions:
            analyzer.analyze_print_session(session)
    
    print("\\nPost-processing complete!")


if __name__ == "__main__":
    main()
