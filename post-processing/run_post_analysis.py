"""
Run Post-Print Analysis
=======================

This script is the master controller for post-print analysis. It is designed
to be run automatically after a print job completes.

Workflow:
1. Finds the most recent print session's log data directory.
2. For each CSV log file in that session, it uses the RawDataProcessor.
3. The RawDataProcessor handles all calculation and plotting, creating one
   analysis image per CSV.

Author: Cheng Sun Lab Team
Date: September 20, 2025
"""

import os
import sys
from pathlib import Path
import argparse

# Add the parent directory to the path to allow sibling imports
sys.path.append(str(Path(__file__).resolve().parent.parent))

from RawData_Processor import RawDataProcessor

class AutomatedAnalyzer:
    """
    Automates post-print analysis by finding the most recent print data
    and processing it with the RawDataProcessor.
    """

    def __init__(self, base_log_dir="C:\\Users\\cheng sun\\BoyuanSun\\Slicing\\Calibration\\Power_Grayscale\\Printing_Logs"):
        """
        Initializes the analyzer.

        Args:
            base_log_dir (str): The root directory where all print logs are stored.
        """
        self.base_log_dir = Path(base_log_dir)
        from adhesion_metrics_calculator import AdhesionMetricsCalculator
        from analysis_plotter import AnalysisPlotter
        
        calculator = AdhesionMetricsCalculator()
        plotter = AnalysisPlotter()
        self.processor = RawDataProcessor(calculator, plotter)

    def find_most_recent_session(self):
        """
        Finds the most recent print session directory containing 'autolog' CSV files.

        Returns:
            A dictionary with session info, or None if no sessions are found.
        """
        latest_session = None
        latest_time = 0

        if not self.base_log_dir.exists():
            print(f"Error: Base log directory not found at '{self.base_log_dir}'")
            return None

        # Iterate through all 'Print X' directories
        for print_dir in self.base_log_dir.rglob("Print *"):
            if not print_dir.is_dir():
                continue

            csv_files = list(print_dir.glob("autolog_*.csv"))
            if not csv_files:
                continue

            # Find the most recently modified CSV in this directory
            most_recent_csv = max(csv_files, key=lambda f: f.stat().st_mtime)
            mod_time = most_recent_csv.stat().st_mtime

            if mod_time > latest_time:
                latest_time = mod_time
                latest_session = {
                    'path': print_dir,
                    'date': print_dir.parent.name,
                    'print_number': print_dir.name,
                    'csv_files': sorted(csv_files, key=lambda f: f.name)
                }

        return latest_session

    def analyze_session(self, session):
        """
        Analyzes all CSV files in a given session.

        Args:
            session (dict): A dictionary containing session information.
        """
        if not session:
            print("No session provided to analyze.")
            return

        results = []
        print(f"\n--- Analyzing Session: {session['date']} / {session['print_number']} ---")

        for csv_file in session['csv_files']:
            try:
                print(f"  Processing file: {csv_file.name}")

                # Define a unique output path for the plot
                output_filename = csv_file.stem.replace('autolog_', 'analysis_') + '.png'
                output_path = csv_file.parent / output_filename

                # Use the RawDataProcessor to handle everything
                self.processor.process_csv(
                    csv_filepath=csv_file,
                    save_path=output_path,
                    title=f"Analysis for {session['print_number']} - {csv_file.stem}"
                )

                results.append({'csv_file': csv_file, 'plot_path': output_path, 'status': 'processed'})

            except Exception as e:
                print(f"  [ERROR] Failed to analyze {csv_file.name}: {e}")
                results.append({'csv_file': csv_file, 'status': 'error', 'reason': str(e)})

        print(f"--- Session Analysis Complete ---")
        return results

    def run(self):
        """
        Finds and analyzes the most recent print session.
        """
        print("Searching for the most recent print session...")
        most_recent_session = self.find_most_recent_session()

        if most_recent_session:
            self.analyze_session(most_recent_session)
        else:
            print("No recent print sessions with 'autolog' data found to analyze.")

def main():
    parser = argparse.ArgumentParser(description="Automated Post-Print Analysis")
    parser.add_argument(
        '--log-dir',
        default="C:\\Users\\cheng sun\\BoyuanSun\\Slicing\\Calibration\\Power_Grayscale\\Printing_Logs",
        help='The root directory where all print logs are stored.'
    )
    parser.add_argument(
        '--file',
        help='Path to a specific CSV file to analyze, bypassing the session search.'
    )
    args = parser.parse_args()

    analyzer = AutomatedAnalyzer(base_log_dir=args.log_dir)

    if args.file:
        # Logic to handle a single file analysis
        file_path = Path(args.file)
        
        # --- Robust Path Checking ---
        # If the file is not found at the given path, check if it exists inside the 'post-processing' directory.
        if not file_path.exists():
            print(f"Error: Specified file not found at '{file_path}'")
            # Construct a path relative to this script's location
            script_dir = Path(__file__).parent
            alternative_path = script_dir / file_path.name
            if alternative_path.exists():
                file_path = alternative_path
            else:
                print(f"Error: Specified file not found at '{file_path}' or within the script's directory.")
                return

        print(f"--- Analyzing Single File: {file_path.name} ---")
        output_filename = file_path.stem.replace('autolog_', 'analysis_') + '.png'
        output_path = file_path.parent / output_filename

        layers = analyzer.processor.process_csv(
            csv_filepath=file_path,
            save_path=output_path,
            title=f"Analysis for {file_path.stem}"
        )
        analyzer.processor.plotter.print_metrics_summary(layers)
        print("--- Single File Analysis Complete ---")
    else:
        # Default behavior: find and analyze the most recent session
        analyzer.run()

if __name__ == "__main__":
    main()