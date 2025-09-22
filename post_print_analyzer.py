"""
Post-Print Analysis and Plotting System
=======================================

This script automatically processes data from completed prints and generates
comprehensive adhesion analysis plots using the corrected light smoothing settings.

Workflow:
1. Detect completed prints from AutomatedLayerLogger CSV files
2. Process data through corrected adhesion_metrics_calculator  
3. Generate individual layer plots and summary analysis
4. Create hybrid plotter visualizations with accurate propagation end times

Author: Cheng Sun Lab Team
Date: September 21, 2025
"""

import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
import argparse
from datetime import datetime
import threading

# Configure matplotlib for thread-safe operation before importing plotting modules
import matplotlib
if threading.current_thread() != threading.main_thread():
    matplotlib.use('Agg')  # Non-interactive backend for background threads

# Import our corrected analysis tools
from adhesion_metrics_calculator import AdhesionMetricsCalculator
from hybrid_adhesion_plotter import HybridAdhesionPlotter

class PostPrintAnalyzer:
    """
    Automated post-processing for 3D printing adhesion data.
    """
    
    def __init__(self):
        # Use corrected light smoothing settings
        self.calculator = AdhesionMetricsCalculator(
            smoothing_window=3,
            smoothing_polyorder=1,
            baseline_threshold_factor=0.002,
            min_peak_height=0.01,
            min_peak_distance=50
        )
        
        self.plotter = HybridAdhesionPlotter()
        
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
        Analyze a single CSV file using corrected calculator and generate plots.
        """
        # Load data
        try:
            df = pd.read_csv(csv_file)
            
            # Standardize column names
            if 'Elapsed Time (s)' in df.columns:
                df = df.rename(columns={
                    'Elapsed Time (s)': 'Time',
                    'Position (mm)': 'Position', 
                    'Force (N)': 'Force'
                })
            
            if len(df) < 10:
                print(f"    Warning: Only {len(df)} data points - skipping")
                return None
                
        except Exception as e:
            print(f"    Error loading CSV: {e}")
            return None
        
        # Generate plots using corrected hybrid plotter
        plot_title = f"Post-Print Analysis - {csv_file.stem}"
        plot_path = output_dir / f"{csv_file.stem}_corrected_analysis.png"
        
        try:
            fig = self.plotter.plot_from_csv(
                str(csv_file),
                title=plot_title,
                save_path=str(plot_path)
            )
            
            print(f"    📊 Plot saved: {plot_path.name}")
            
        except Exception as e:
            print(f"    Warning: Plot generation failed: {e}")
            plot_path = None
        
        # Extract layer-by-layer analysis (if we can segment the data)
        layer_results = self._extract_layer_analysis(df)
        
        return {
            'csv_file': csv_file,
            'plot_path': plot_path,
            'layers': layer_results,
            'data_points': len(df),
            'time_range': f"{df['Time'].min():.1f} to {df['Time'].max():.1f}s"
        }
    
    def _extract_layer_analysis(self, df):
        """
        Extract individual layer analysis using corrected calculator.
        """
        layers = []
        
        # Simple peak detection to identify layers
        forces = df['Force'].values
        times = df['Time'].values
        positions = df['Position'].values
        
        # Find peaks (simplified - hybrid plotter does this better)
        from scipy.signal import find_peaks
        
        try:
            peaks, _ = find_peaks(forces, height=0.01, distance=50)
            
            for i, peak_idx in enumerate(peaks[:5]):  # Limit to first 5 layers
                # Define layer window around peak
                start_idx = max(0, peak_idx - 100)
                end_idx = min(len(df), peak_idx + 200)
                
                layer_times = times[start_idx:end_idx] - times[start_idx]  # Reset to 0
                layer_positions = positions[start_idx:end_idx] 
                layer_forces = forces[start_idx:end_idx]
                
                if len(layer_times) > 10:
                    # Calculate metrics using corrected calculator
                    metrics = self.calculator.calculate_from_arrays(
                        layer_times, layer_positions, layer_forces, 
                        layer_number=i+1
                    )
                    
                    layers.append({
                        'layer_number': i+1,
                        'peak_force': metrics['peak_force'],
                        'propagation_end_time': metrics['propagation_end_time'],
                        'work_of_adhesion': metrics['work_of_adhesion_corrected_mJ'],
                        'baseline_force': metrics['baseline_force']
                    })
                    
        except Exception as e:
            print(f"    Layer extraction failed: {e}")
        
        return layers
    
    def _generate_session_summary(self, session, analysis_results):
        """
        Generate a summary report for the print session.
        """
        summary_path = session['path'] / "POST_PROCESSING_SUMMARY.md"
        
        with open(summary_path, 'w') as f:
            f.write(f"# Post-Print Analysis Summary\\n")
            f.write(f"**Session:** {session['date']} / {session['print_number']}\\n")
            f.write(f"**Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n")
            f.write(f"**Calculator Settings:** Light smoothing (window=3, polyorder=1)\\n\\n")
            
            f.write(f"## Files Processed\\n")
            for result in analysis_results:
                f.write(f"- **{result['csv_file'].name}**\\n")
                f.write(f"  - Data points: {result['data_points']}\\n")
                f.write(f"  - Time range: {result['time_range']}\\n")
                f.write(f"  - Layers detected: {len(result['layers'])}\\n")
                if result['plot_path']:
                    f.write(f"  - Plot: {result['plot_path'].name}\\n")
                f.write(f"\\n")
            
            f.write(f"## Layer Analysis Summary\\n")
            for result in analysis_results:
                if result['layers']:
                    f.write(f"### {result['csv_file'].name}\\n")
                    for layer in result['layers']:
                        f.write(f"- **Layer {layer['layer_number']}**: ")
                        f.write(f"Peak={layer['peak_force']:.3f}N, ")
                        f.write(f"PropEnd={layer['propagation_end_time']:.3f}s, ")
                        f.write(f"Work={layer['work_of_adhesion']:.3f}mJ\\n")
                    f.write(f"\\n")
            
            f.write(f"## Notes\\n")
            f.write(f"- Analysis performed with corrected light smoothing settings\\n")
            f.write(f"- Propagation end times should be accurate (~11.7s for similar conditions)\\n")
            f.write(f"- All plots generated with corrected hybrid_adhesion_plotter\\n")
        
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
