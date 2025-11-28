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

# Add post-processing directory to path so we can import from it
post_processing_dir = Path(__file__).parent / "post-processing"
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
        # Use corrected two-step filtering settings (matches current AdhesionMetricsCalculator)
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
        
        # Initialize RawDataProcessor (handles data processing only, not plotting)
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
                    print(f"  ✅ Analysis complete - {len(result['layers'])} layers processed")
                else:
                    print(f"  ❌ Analysis failed")
                    
            except Exception as e:
                print(f"  ❌ Error analyzing {csv_file.name}: {e}")
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
        Analyze a single CSV file using RawDataProcessor (same as batch processing).
        """
        print(f"    Processing: {csv_file.name}")
        
        # Generate plot using RawDataProcessor
        plot_title = f"Post-Print Analysis - {csv_file.stem}"
        plot_path = output_dir / f"{csv_file.stem}_analysis.png"
        
        try:
            # Use RawDataProcessor to handle everything (analysis + plotting)
            layers = self.processor.process_csv(
                str(csv_file),
                title=plot_title,
                save_path=str(plot_path)
            )
            
            # RawDataProcessor now returns only layers (no plotting)
            if layers and len(layers) > 0:
                print(f"    ✅ Analysis complete - {len(layers)} layers processed")
                
                # Generate plot using the plotter
                try:
                    # Load the CSV data for plotting
                    import pandas as pd
                    df = pd.read_csv(csv_file)
                    time_data = df['Elapsed Time (s)'].to_numpy()
                    force_data = df['Force (N)'].to_numpy()
                    
                    # Apply smoothing for plotting (consistent with processor)
                    from adhesion_metrics_calculator import AdhesionMetricsCalculator
                    calculator = AdhesionMetricsCalculator()
                    smoothed_force = calculator._apply_smoothing(force_data)
                    
                    # Use create_plot method with proper arguments
                    self.plotter.create_plot(
                        time_data=time_data,
                        force_data=force_data,
                        smoothed_force=smoothed_force,
                        layers=layers,
                        title=plot_title,
                        save_path=str(plot_path)
                    )
                    if plot_path.exists():
                        print(f"    📊 Plot saved: {plot_path.name}")
                except Exception as e:
                    print(f"    ⚠️  Plot generation failed: {e}")
                    import traceback
                    traceback.print_exc()
                
                return {
                    'csv_file': csv_file,
                    'plot_path': plot_path if plot_path.exists() else None,
                    'layers': layers,
                    'data_points': len(layers),
                    'time_range': f"Processed {len(layers)} layers"
                }
            else:
                print(f"    ❌ Analysis failed - no layers detected")
                return None
            
        except Exception as e:
            print(f"    ❌ Error during processing: {e}")
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
        
        print(f"  📋 Summary saved: {summary_path.name}")
    
    def _generate_master_plot(self, session):
        """
        Generate a master plot combining all work of adhesion data for the session.
        Similar to batch processor master plots but for a single print session.
        
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
            print("  ℹ️  No work of adhesion data found for master plot")
            return
        
        woa_file = woa_files[0]  # Use the first one found
        print(f"\n  📊 Generating master plot with work of adhesion data from: {woa_file.name}")
        
        try:
            # Load work of adhesion data
            df = pd.read_csv(woa_file)
            
            if df.empty or len(df) == 0:
                print("    ⚠️  Work of adhesion file is empty")
                return
            
            # Check for required columns (try both naming conventions)
            if 'layer_number' in df.columns:
                layer_col = 'layer_number'
                force_col = 'peak_force_N'
                woa_col = 'work_of_adhesion_mJ'
            elif 'Layer' in df.columns:
                layer_col = 'Layer'
                force_col = 'Peak_Force_N'
                woa_col = 'Work_of_Adhesion_mJ'
            else:
                print(f"    ⚠️  Missing required columns in work of adhesion file")
                print(f"    Available columns: {list(df.columns)}")
                return
            
            # Verify all required columns exist
            if not all(col in df.columns for col in [layer_col, force_col, woa_col]):
                print(f"    ⚠️  Missing required columns in work of adhesion file")
                print(f"    Available columns: {list(df.columns)}")
                return
            
            # Create figure with 3 subplots (Peak Force, Work of Adhesion, Duration)
            fig, axes = plt.subplots(3, 1, figsize=(12, 14))
            
            layers = df[layer_col].values
            peak_force = df[force_col].values
            work_of_adhesion = df[woa_col].values
            
            # Plot 1: Peak Force vs Layer
            axes[0].plot(layers, peak_force, 'o-', color='#2E86AB', linewidth=2, markersize=8,
                        markerfacecolor='#A23B72', markeredgecolor='white', markeredgewidth=1.5)
            axes[0].set_xlabel('Layer Number', fontsize=12, fontweight='bold')
            axes[0].set_ylabel('Peak Force (N)', fontsize=12, fontweight='bold')
            axes[0].set_title('Peak Adhesion Force by Layer', fontsize=14, fontweight='bold')
            axes[0].grid(True, alpha=0.3)
            
            # Add mean line
            mean_force = np.mean(peak_force)
            axes[0].axhline(y=mean_force, color='red', linestyle='--', linewidth=2, alpha=0.7,
                           label=f'Mean: {mean_force:.4f} N')
            axes[0].legend(fontsize=10)
            
            # Plot 2: Work of Adhesion vs Layer
            axes[1].plot(layers, work_of_adhesion, 's-', color='#F18F01', linewidth=2, markersize=8,
                        markerfacecolor='#C73E1D', markeredgecolor='white', markeredgewidth=1.5)
            axes[1].set_xlabel('Layer Number', fontsize=12, fontweight='bold')
            axes[1].set_ylabel('Work of Adhesion (mJ)', fontsize=12, fontweight='bold')
            axes[1].set_title('Work of Adhesion by Layer', fontsize=14, fontweight='bold')
            axes[1].grid(True, alpha=0.3)
            
            # Add mean line
            mean_woa = np.mean(work_of_adhesion)
            axes[1].axhline(y=mean_woa, color='red', linestyle='--', linewidth=2, alpha=0.7,
                           label=f'Mean: {mean_woa:.4f} mJ')
            axes[1].legend(fontsize=10)
            
            # Plot 3: Pre-initiation and Propagation Duration (if available)
            if 'Pre_Initiation_Time_s' in df.columns and 'Propagation_Duration_s' in df.columns:
                pre_init = df['Pre_Initiation_Time_s'].values
                prop_duration = df['Propagation_Duration_s'].values
                
                x = np.arange(len(layers))
                width = 0.35
                
                axes[2].bar(x - width/2, pre_init, width, label='Pre-Initiation', 
                           color='#5BC0EB', edgecolor='white', linewidth=1.5)
                axes[2].bar(x + width/2, prop_duration, width, label='Propagation',
                           color='#FDE74C', edgecolor='white', linewidth=1.5)
                
                axes[2].set_xlabel('Layer Number', fontsize=12, fontweight='bold')
                axes[2].set_ylabel('Time (s)', fontsize=12, fontweight='bold')
                axes[2].set_title('Peeling Phase Durations by Layer', fontsize=14, fontweight='bold')
                axes[2].set_xticks(x)
                axes[2].set_xticklabels(layers)
                axes[2].legend(fontsize=10)
                axes[2].grid(True, alpha=0.3, axis='y')
            else:
                # If duration data not available, show total duration or a message
                axes[2].text(0.5, 0.5, 'Duration data not available in work of adhesion file',
                            ha='center', va='center', fontsize=12, transform=axes[2].transAxes)
                axes[2].set_xlim(0, 1)
                axes[2].set_ylim(0, 1)
                axes[2].axis('off')
            
            # Overall title
            fig.suptitle(f'{session["date"]} / {session["print_number"]} - Master Analysis\nWork of Adhesion Summary',
                        fontsize=16, fontweight='bold', y=0.995)
            
            # Adjust layout
            plt.tight_layout()
            plt.subplots_adjust(top=0.96, hspace=0.3)
            
            # Save plot
            master_plot_path = session_path / "MASTER_work_of_adhesion_analysis.png"
            plt.savefig(master_plot_path, dpi=300, bbox_inches='tight', facecolor='white')
            plt.close()
            
            print(f"    ✅ Master plot saved: {master_plot_path.name}")
            
        except Exception as e:
            print(f"    ❌ Error generating master plot: {e}")
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
