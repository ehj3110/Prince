#!/usr/bin/env python3
"""
Script to run full adhesion analysis with RawData_Processor
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to import modules
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))
sys.path.insert(0, str(parent_dir / "support_modules"))

# Add current directory first to ensure we use the local analysis_plotter.py
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

try:
    from adhesion_metrics_calculator import AdhesionMetricsCalculator
    from analysis_plotter import AnalysisPlotter
    from RawData_Processor import RawDataProcessor
    
    def main():
        if len(sys.argv) < 2:
            print("Usage: python run_full_analysis.py <csv_file>")
            print("Available CSV files:")
            csv_files = list(Path(".").glob("*.csv"))
            for f in csv_files:
                print(f"  {f}")
            return
        
        csv_file = sys.argv[1]
        if not Path(csv_file).exists():
            print(f"Error: File {csv_file} not found")
            return
        
        print(f"Running full adhesion analysis on {csv_file}")
        print("=" * 50)
        
        # Initialize calculator and plotter
        calculator = AdhesionMetricsCalculator(smoothing_sigma=0.5)
        plotter = AnalysisPlotter()
        processor = RawDataProcessor(calculator, plotter)
        
        # Set output path
        output_path = Path(csv_file).stem + "_analysis.png"
        csv_output_path = Path(csv_file).parent / "autolog_metrics.csv"
        
        # Process the CSV file
        layers = processor.process_csv(
            csv_filepath=csv_file,
            title=f"Adhesion Analysis - {Path(csv_file).stem}",
            save_path=output_path
        )
        
        if layers:
            # Export metrics to CSV
            processor.export_metrics_to_csv(layers, str(csv_output_path))
            
            print(f"\nAnalysis complete! Found {len(layers)} layers:")
            print("=" * 60)
            for layer in layers:
                metrics = layer['metrics']
                print(f"\nLayer {layer['number']}:")
                print(f"  Peak Force: {metrics.get('peak_force', 0):.4f} N")
                print(f"  Baseline Force: {metrics.get('baseline_force', 0):.4f} N")
                print(f"  Work of Adhesion: {metrics.get('work_of_adhesion_corrected_mJ', 0):.3f} mJ")
                print(f"  Pre-initiation Duration: {metrics.get('pre_initiation_duration', 0):.3f} s")
                print(f"  Propagation Duration: {metrics.get('propagation_duration', 0):.3f} s")
                print(f"  Max Derivative: {metrics.get('max_derivative', 0):.4f} N/s")
                print(f"  Failure Rate: {metrics.get('failure_rate', 0):.4f} N/s")
            
            print(f"\nPlot saved to: {output_path}")
        else:
            print("No layers were successfully analyzed.")
    
    if __name__ == "__main__":
        main()
        
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure all required modules are available:")
    print("  - support_modules/adhesion_metrics_calculator.py")
    print("  - hybrid_adhesion_plotter.py")
    print("  - RawData_Processor.py")