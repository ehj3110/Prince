us"""
Test Post-Print Analysis Pipeline
==================================

This test simulates the complete end-of-print workflow using real CSV data.
Tests the full chain: RawDataProcessor -> AnalysisPlotter -> PostPrintAnalyzer

Author: Cheng Sun Lab Team
Date: January 8, 2026
"""

import unittest
import sys
import os
from pathlib import Path
import shutil
import tempfile

# Add project directories to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "post-processing"))
sys.path.insert(0, str(project_root / "support_modules"))

# Import modules under test
from RawData_Processor import RawDataProcessor
from analysis_plotter import AnalysisPlotter
from post_print_analyzer import PostPrintAnalyzer
from adhesion_metrics_calculator import AdhesionMetricsCalculator


class TestPostPrintAnalysis(unittest.TestCase):
    """Test the complete post-print analysis workflow."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures once for all tests."""
        # Path to real test data (from your print session)
        cls.test_data_dir = Path("c:/Users/cheng sun/BoyuanSun/Slicing/Evan/ExpandingCone_V2_10mmto100mm_50umLayers/Printing_Logs/2026-01-07/Print 10 - Complete")
        
        # Create temporary output directory for test results
        cls.temp_dir = Path(tempfile.mkdtemp(prefix="test_postprint_"))
        print(f"\n{'='*70}")
        print(f"Test Post-Print Analysis Pipeline")
        print(f"{'='*70}")
        print(f"Test data source: {cls.test_data_dir}")
        print(f"Temporary output: {cls.temp_dir}")
        print(f"{'='*70}\n")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test fixtures after all tests."""
        # Keep temporary directory for inspection
        print(f"\n{'='*70}")
        print(f"Test Results Location: {cls.temp_dir}")
        print(f"{'='*70}\n")
        # Uncomment to delete temp directory:
        # if cls.temp_dir.exists():
        #     shutil.rmtree(cls.temp_dir)
    
    def setUp(self):
        """Set up each test."""
        # Initialize components
        self.calculator = AdhesionMetricsCalculator(
            median_kernel=5,
            savgol_window=9,
            savgol_order=2
        )
        self.processor = RawDataProcessor(self.calculator)
        self.plotter = AnalysisPlotter()
        self.analyzer = PostPrintAnalyzer()
    
    def test_01_raw_data_processor(self):
        """Test RawDataProcessor can load and analyze CSV files."""
        print("\n" + "="*70)
        print("TEST 1: RawDataProcessor - Load and Analyze CSV")
        print("="*70)
        
        # Find a test CSV file
        csv_files = list(self.test_data_dir.glob("autolog_L*.csv"))
        self.assertGreater(len(csv_files), 0, "No CSV files found in test data directory")
        
        test_csv = csv_files[0]
        print(f"Testing with: {test_csv.name}")
        
        # Process the CSV
        layers = self.processor.process_csv(str(test_csv))
        
        # Verify results
        self.assertIsNotNone(layers, "Processor returned None")
        self.assertIsInstance(layers, list, "Processor should return a list")
        self.assertGreater(len(layers), 0, "No layers detected in CSV")
        
        print(f"[OK] Successfully processed {len(layers)} layers")
        
        # Verify layer structure
        first_layer = layers[0]
        required_keys = ['number', 'peak_force', 'work_of_adhesion_mJ', 'peak_idx']
        for key in required_keys:
            self.assertIn(key, first_layer, f"Layer missing key: {key}")
        
        print(f"[OK] Layer data structure validated")
        print(f"   Layer {first_layer['number']}: Peak Force = {first_layer['peak_force']:.4f} N")
        print(f"   Work of Adhesion = {first_layer['work_of_adhesion_mJ']:.4f} mJ")
    
    def test_02_analysis_plotter(self):
        """Test AnalysisPlotter can generate plots from layer data."""
        print("\n" + "="*70)
        print("TEST 2: AnalysisPlotter - Generate Plots")
        print("="*70)
        
        # Get layer data from processor
        import pandas as pd
        csv_files = list(self.test_data_dir.glob("autolog_L*.csv"))
        test_csv = csv_files[0]
        print(f"Processing: {test_csv.name}")
        
        # Load CSV data for plotting
        df = pd.read_csv(test_csv)
        time_data = df['Elapsed Time (s)'].to_numpy()
        force_data = df['Force (N)'].to_numpy()
        
        # Process data
        layers = self.processor.process_csv(str(test_csv))
        self.assertIsNotNone(layers, "No layer data to plot")
        
        # Get smoothed force
        smoothed_force = self.calculator._apply_smoothing(force_data)
        
        # Generate plot
        output_path = self.temp_dir / f"{test_csv.stem}_test_plot.png"
        print(f"Generating plot: {output_path.name}")
        
        self.plotter.create_plot(
            time_data=time_data,
            force_data=force_data,
            smoothed_force=smoothed_force,
            layers=layers,
            title=f"Test Plot - {test_csv.stem}",
            save_path=str(output_path)
        )
        
        # Verify plot was created
        self.assertTrue(output_path.exists(), f"Plot file not created: {output_path}")
        self.assertGreater(output_path.stat().st_size, 0, "Plot file is empty")
        
        print(f"[OK] Plot generated successfully: {output_path.name}")
        print(f"   File size: {output_path.stat().st_size / 1024:.1f} KB")
    
    def test_03_process_all_csv_files(self):
        """Test processing all CSV files in the session."""
        print("\n" + "="*70)
        print("TEST 3: Process All CSV Files")
        print("="*70)
        
        csv_files = sorted(self.test_data_dir.glob("autolog_L*.csv"))
        print(f"Found {len(csv_files)} CSV files to process")
        
        results = []
        for csv_file in csv_files:
            print(f"\nProcessing: {csv_file.name}")
            
            try:
                # Load CSV data
                df = pd.read_csv(csv_file)
                time_data = df['Elapsed Time (s)'].to_numpy()
                force_data = df['Force (N)'].to_numpy()
                
                # Process CSV
                layers = self.processor.process_csv(str(csv_file))
                
                if layers and len(layers) > 0:
                    # Get smoothed force
                    smoothed_force = self.calculator._apply_smoothing(force_data)
                    
                    # Generate plot
                    plot_path = self.temp_dir / f"{csv_file.stem}_analysis.png"
                    self.plotter.create_plot(
                        time_data=time_data,
                        force_data=force_data,
                        smoothed_force=smoothed_force,
                        layers=layers,
                        title=f"Analysis - {csv_file.stem}",
                        save_path=str(plot_path)
                    )
                    
                    results.append({
                        'csv': csv_file.name,
                        'layers': len(layers),
                        'plot': plot_path.exists()
                    })
                    print(f"  [OK] {len(layers)} layers, plot: {plot_path.exists()}")
                else:
                    print(f"  [X] No layers detected")
                    
            except Exception as e:
                print(f"  [X] Error: {e}")
                import traceback
                traceback.print_exc()
        
        # Summary
        print(f"\n{'='*70}")
        print(f"SUMMARY: Processed {len(results)}/{len(csv_files)} files successfully")
        total_layers = sum(r['layers'] for r in results)
        plots_created = sum(1 for r in results if r['plot'])
        print(f"Total layers: {total_layers}")
        print(f"Plots created: {plots_created}")
        print(f"{'='*70}")
        
        self.assertGreater(len(results), 0, "No files processed successfully")
    
    def test_04_post_print_analyzer(self):
        """Test the complete PostPrintAnalyzer workflow."""
        print("\n" + "="*70)
        print("TEST 4: PostPrintAnalyzer - Complete Workflow")
        print("="*70)
        
        # Create a mock session structure
        session = {
            'path': self.test_data_dir,
            'date': '2026-01-07',
            'print_number': 'Print 10 - Complete',
            'csv_files': sorted(self.test_data_dir.glob("autolog_L*.csv"))
        }
        
        print(f"Analyzing session: {session['date']}/{session['print_number']}")
        print(f"CSV files: {len(session['csv_files'])}")
        
        # Run analysis
        results = self.analyzer.analyze_print_session(session)
        
        # Verify results
        self.assertIsNotNone(results, "Analyzer returned None")
        self.assertIsInstance(results, list, "Analyzer should return a list")
        
        print(f"\n{'='*70}")
        print(f"PostPrintAnalyzer Results:")
        print(f"  Files analyzed: {len(results)}")
        for result in results:
            print(f"  - {result['csv_file'].name}: {result['data_points']} layers")
        print(f"{'='*70}")
        
        # Check for summary file
        summary_file = self.test_data_dir / "POST_PROCESSING_SUMMARY.md"
        if summary_file.exists():
            print(f"[OK] Summary file created: {summary_file.name}")
        
        # Check for plots
        plot_files = list(self.test_data_dir.glob("autolog_L*_analysis.png"))
        print(f"[OK] Plots generated: {len(plot_files)}")
    
    def test_05_check_phase_column(self):
        """Test that Phase column exists and contains valid phases."""
        print("\n" + "="*70)
        print("TEST 5: Verify Phase Column in CSV Data")
        print("="*70)
        
        import pandas as pd
        
        csv_files = list(self.test_data_dir.glob("autolog_L*.csv"))
        test_csv = csv_files[0]
        print(f"Checking: {test_csv.name}")
        
        # Load CSV
        df = pd.read_csv(test_csv)
        
        # Check for Phase column
        self.assertIn('Phase', df.columns, "Phase column not found in CSV")
        print(f"[OK] Phase column exists")
        
        # Check phase values
        unique_phases = df['Phase'].unique()
        print(f"Unique phases found: {unique_phases}")
        
        valid_phases = {'Exposure', 'Lift', 'Retract', 'Pause', 'Sandwich', 'Unknown'}
        for phase in unique_phases:
            self.assertIn(phase, valid_phases, f"Invalid phase value: {phase}")
        
        # Count Unknown phases
        unknown_count = (df['Phase'] == 'Unknown').sum()
        total_count = len(df)
        unknown_percent = (unknown_count / total_count) * 100
        
        print(f"[OK] Phase values validated")
        print(f"   Total rows: {total_count}")
        print(f"   Unknown phases: {unknown_count} ({unknown_percent:.1f}%)")
        
        if unknown_count > 0:
            # Find where Unknown phases occur
            unknown_indices = df[df['Phase'] == 'Unknown'].index.tolist()
            print(f"   Unknown at indices: {unknown_indices[:10]}{'...' if len(unknown_indices) > 10 else ''}")
            
            if unknown_indices[0] < 10:
                print(f"   [!] Unknown phases detected at start of CSV (likely initialization)")


def run_tests(verbose=False):
    """Run all tests."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestPostPrintAnalysis)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
    result = runner.run(suite)
    
    return result


if __name__ == "__main__":
    print("\n" + "="*70)
    print("Post-Print Analysis Test Suite")
    print("="*70)
    print("This test validates the complete post-print analysis pipeline")
    print("using real data from your print session.")
    print("="*70 + "\n")
    
    # Run tests with verbose output
    result = run_tests(verbose=True)
    
    # Print summary
    print("\n" + "="*70)
    if result.wasSuccessful():
        print("[PASS] ALL TESTS PASSED")
    else:
        print("[FAIL] SOME TESTS FAILED")
        print(f"Failures: {len(result.failures)}")
        print(f"Errors: {len(result.errors)}")
    print("="*70 + "\n")
    
    sys.exit(0 if result.wasSuccessful() else 1)
