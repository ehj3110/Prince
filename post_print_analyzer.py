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
        # Use corrected light smoothing settings
        self.calculator = AdhesionMetricsCalculator(
            smoothing_sigma=0.5,
            baseline_threshold_factor=0.002,
            min_peak_height=0.01,
            min_peak_distance=50
        )
        
        # Use AnalysisPlotter (same as batch processing)
        self.plotter = AnalysisPlotter()
        
        # Initialize RawDataProcessor (handles all analysis and plotting)
        self.processor = RawDataProcessor(self.calculator, self.plotter)
        
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
            
            if layers and plot_path.exists():
                print(f"    📊 Plot saved: {plot_path.name}")
                print(f"    ✅ Analysis complete - {len(layers)} layers processed")
                
                return {
                    'csv_file': csv_file,
                    'plot_path': plot_path,
                    'layers': layers,
                    'data_points': len(layers),  # Number of layers
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
