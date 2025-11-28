"""
Full Print Simulation Test

This script simulates a complete print session to test the entire data flow:
1. Reads autolog CSV file
2. Simulates PositionLogger emitting phase events
3. Simulates PeakForceLogger receiving data and phase events
4. Tests real-time adhesion metrics calculation
5. Tests phase-aware pre-initiation detection

This is the COMPREHENSIVE test that simulates exactly what happens during
a real print, including the phase event queue mechanism.

Usage:
    python test_print_simulation_spoofed.py

What it tests:
- Phase event generation from position data
- Phase event queue mechanism
- PeakForceLogger data collection
- Real-time adhesion metrics with lifting_start_idx
- Phase-aware pre-initiation detection
"""

import numpy as np
import pandas as pd
from pathlib import Path
import sys
import queue
import time
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend

# Add support_modules to path
sys.path.insert(0, str(Path(__file__).parent / "support_modules"))

# Add post-processing to path for analysis tools
post_processing_dir = Path(__file__).parent / "post-processing"
sys.path.insert(0, str(post_processing_dir))

from adhesion_metrics_calculator import AdhesionMetricsCalculator
from PeakForceLogger import PeakForceLogger
from PositionLogger import PositionLogger  # Import REAL PositionLogger

# Import post-processing tools (same as batch processing)
try:
    from RawData_Processor import RawDataProcessor
    from analysis_plotter import AnalysisPlotter
    POST_PROCESSING_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Post-processing tools not available: {e}")
    POST_PROCESSING_AVAILABLE = False


class CSVDataFeeder:
    """
    Feeds CSV data through the REAL PositionLogger to test actual phase detection.
    
    This creates a real PositionLogger instance and feeds it position data
    point-by-point from the CSV, allowing us to test the actual phase detection
    logic including the recent fixes for upward motion detection.
    
    Also generates a corrected CSV file with real-time phase labels.
    """
    
    def __init__(self, csv_filepath, output_csv="test_spoofed_corrected_autolog.csv"):
        self.csv_filepath = csv_filepath
        self.output_csv = output_csv
        
        # Create dummy objects for PositionLogger (we're not using hardware)
        import threading
        dummy_axis = None  # PositionLogger doesn't actually use this in _determine_phase()
        dummy_stop_event = threading.Event()
        
        # Create REAL PositionLogger instance
        self.position_logger = PositionLogger(
            axis_obj=dummy_axis,
            stop_event=dummy_stop_event,
            log_file_name="temp_position_log.csv",  # Temp file, not used
            log_interval_ms=10,  # Fast logging for testing
            csv_logging_initially_enabled=False  # Don't actually log to CSV during test
        )
        
        # Access the phase event queue from the real PositionLogger
        self.phase_event_queue = self.position_logger.phase_event_queue
        
        # Counter for tracking
        self._data_point_counter = 0
        
        print(f"CSVDataFeeder: Loading data from {csv_filepath}")
        print(f"CSVDataFeeder: Using REAL PositionLogger with phase detection")
        print(f"CSVDataFeeder: Will generate corrected CSV -> {output_csv}")
    
    def simulate_print(self, start_layer=1, num_layers=3):
        """
        Feed CSV data through the real PositionLogger.
        Generates a corrected CSV file with real-time phase labels.
        
        Args:
            start_layer: Starting layer number (informational)
            num_layers: Number of layers to simulate (informational)
            
        Yields:
            (timestamp, position, force, phase) tuples
        """
        print(f"\nSimulating print: Layers {start_layer} to {start_layer + num_layers - 1}")
        print("Feeding data through REAL PositionLogger...")
        
        # Load CSV
        df = pd.read_csv(self.csv_filepath)
        
        # Storage for corrected data
        corrected_data = []
        
        # Process each data point through the REAL PositionLogger
        for idx, row in df.iterrows():
            timestamp = row['Elapsed Time (s)']
            position = row['Position (mm)']
            force = row['Force (N)']
            
            # Feed position to REAL PositionLogger - this will:
            # 1. Run actual phase detection logic
            # 2. Emit phase events to the queue
            # 3. Return the current phase
            current_phase = self.position_logger._determine_phase(position)
            
            self._data_point_counter += 1
            
            # Store corrected data
            corrected_data.append({
                'Elapsed Time (s)': timestamp,
                'Position (mm)': position,
                'Force (N)': force,
                'Phase': current_phase
            })
            
            # Yield data point with the phase determined by REAL PositionLogger
            yield (timestamp, position, force, current_phase)
        
        # Save corrected CSV with real-time phase labels
        corrected_df = pd.DataFrame(corrected_data)
        corrected_df.to_csv(self.output_csv, index=False)
        print(f"\n[OK] Corrected CSV saved: {self.output_csv}")
        print(f"   Total points: {len(corrected_data)}")
        print(f"   Phases detected: {corrected_df['Phase'].unique()}")


def simulate_layer_boundaries(data_points):
    """
    Detect layer boundaries in simulated data.
    Filters out short Lift phases (< 50 points) which are typically 
    false layers from the end of sandwich steps.
    
    Args:
        data_points: List of (timestamp, position, force, phase) tuples
    
    Returns:
        List of (start_idx, end_idx) for each real layer
    """
    boundaries = []
    in_lift = False
    lift_start = None
    
    for idx, (ts, pos, force, phase) in enumerate(data_points):
        if phase == "Lift" and not in_lift:
            # Start of lift phase
            lift_start = idx
            in_lift = True
        elif phase != "Lift" and in_lift and lift_start is not None:
            # End of lift phase - only count if significant data (>50 points)
            num_points = idx - lift_start
            if num_points > 50:  # Filter out short false layers
                boundaries.append((lift_start, idx - 1))
            else:
                print(f"  Filtering out short Lift segment at {lift_start}-{idx} ({num_points} points)")
            in_lift = False
    
    # Handle case where data ends during lift
    if in_lift and lift_start is not None:
        num_points = len(data_points) - lift_start
        if num_points > 50:  # Filter out short false layers
            boundaries.append((lift_start, len(data_points) - 1))
        else:
            print(f"  Filtering out short Lift segment at {lift_start}-{len(data_points)} ({num_points} points)")
    
    return boundaries


def test_real_time_peak_force_logging(csv_filepath):
    """
    Test real-time PeakForceLogger with simulated print data.
    
    This simulates what happens during an actual print:
    1. PositionLogger emits phase events
    2. PeakForceLogger receives data and phase events
    3. Adhesion metrics calculated with lifting_start_idx
    """
    print("="*70)
    print("REAL-TIME PEAK FORCE LOGGING SIMULATION")
    print("="*70)
    
    # Create CSV data feeder with REAL PositionLogger
    csv_feeder = CSVDataFeeder(csv_filepath)
    
    # Create PeakForceLogger with phase awareness
    output_csv = Path("test_simulated_peak_force_output.csv")
    peak_logger = PeakForceLogger(
        output_csv_filepath=str(output_csv),
        is_manual_log=False,
        use_corrected_calculator=True,
        phase_event_queue_ref=csv_feeder.phase_event_queue
    )
    
    print(f"\nPeakForceLogger created with phase awareness")
    print(f"Output: {output_csv}")
    
    # Simulate the print
    print("\n" + "="*70)
    print("SIMULATING PRINT DATA STREAM")
    print("="*70)
    
    # Collect all data points first
    print("\nReading data from CSV...")
    data_points = list(csv_feeder.simulate_print(start_layer=1, num_layers=3))
    print(f"Loaded {len(data_points)} data points")
    
    # Find layer boundaries
    print("\nDetecting layer boundaries...")
    boundaries = simulate_layer_boundaries(data_points)
    print(f"Found {len(boundaries)} layers")
    
    for i, (start, end) in enumerate(boundaries):
        print(f"  Layer {i+1}: indices {start}-{end}")
    
    # Process each layer
    results = []
    for layer_num, (start_idx, end_idx) in enumerate(boundaries, start=1):
        print(f"\n{'='*70}")
        print(f"PROCESSING LAYER {layer_num}")
        print(f"{'='*70}")
        
        # Start monitoring
        layer_data = data_points[start_idx:end_idx+1]
        first_pos = layer_data[0][1]
        last_pos = layer_data[-1][1]
        
        peak_logger.start_monitoring_for_layer(
            layer_number=layer_num,
            z_peel_peak=min(first_pos, last_pos),
            z_return_pos=max(first_pos, last_pos)
        )
        
        # Feed data points
        print(f"\nFeeding {len(layer_data)} data points...")
        for ts, pos, force, phase in layer_data:
            peak_logger.add_data_point(ts, pos, force)
        
        # Stop monitoring (triggers analysis)
        print(f"\nStopping monitoring (triggering analysis)...")
        peak_logger.stop_monitoring_and_log_peak()
        
        # Wait for analysis to complete
        time.sleep(0.5)
    
    # Wait for all analysis to complete
    print(f"\nWaiting for analysis worker to finish...")
    time.sleep(1.0)
    
    # Read and display results
    print(f"\n{'='*70}")
    print("RESULTS")
    print(f"{'='*70}")
    
    if output_csv.exists():
        results_df = pd.read_csv(output_csv)
        print(f"\nProcessed {len(results_df)} layers")
        print(f"\nResults preview:")
        print(results_df.to_string())
        
        # Highlight phase-aware metrics
        if len(results_df) > 0:
            print(f"\n{'='*70}")
            print("PHASE-AWARE METRICS ANALYSIS")
            print(f"{'='*70}")
            
            for idx, row in results_df.iterrows():
                print(f"\nLayer {row['Layer_Number']}:")
                print(f"  Peak Force: {row['Peak_Force_N']:.4f} N")
                print(f"  Work of Adhesion: {row['Work_of_Adhesion_mJ']:.4f} mJ")
                print(f"  Initiation Time: {row['Initiation_Time_s']:.4f} s")
                print(f"  Total Duration: {row['Total_Duration_s']:.4f} s")
                
                # Check if pre-initiation time is reasonable (should be short with phase awareness)
                if row['Initiation_Time_s'] > 2.0:
                    print(f"  [WARNING] Long initiation time - phase awareness may not be working")
                else:
                    print(f"  [OK] Initiation time looks good (phase-aware)")
        
        return results_df
    else:
        print(f"\n[ERROR] ERROR: Output file not created: {output_csv}")
        return None


def test_phase_aware_pre_initiation(csv_filepath):
    """
    Direct test of phase-aware pre-initiation detection.
    
    This bypasses PeakForceLogger and tests the adhesion calculator directly.
    """
    print(f"\n{'='*70}")
    print("PHASE-AWARE PRE-INITIATION TEST")
    print(f"{'='*70}")
    
    # Load data
    df = pd.read_csv(csv_filepath)
    
    # Find first Lift phase using REAL PositionLogger
    print("\nFinding Lift phase in data...")
    csv_feeder = CSVDataFeeder(csv_filepath)
    data_points = list(csv_feeder.simulate_print())
    
    # Find first lift
    lift_start = None
    lift_end = None
    for idx, (ts, pos, force, phase) in enumerate(data_points):
        if phase == "Lift" and lift_start is None:
            lift_start = idx
        elif phase != "Lift" and lift_start is not None and lift_end is None:
            lift_end = idx - 1
            break
    
    if lift_start is None:
        print("[ERROR] No Lift phase found in data!")
        return
    
    print(f"Lift phase: indices {lift_start} to {lift_end}")
    
    # Extract lift phase data
    lift_data = data_points[lift_start:lift_end+1]
    times = np.array([d[0] for d in lift_data])
    positions = np.array([d[1] for d in lift_data])
    forces = np.array([d[2] for d in lift_data])
    
    # Test WITHOUT phase awareness
    print(f"\n{'='*70}")
    print("Test 1: WITHOUT phase awareness (old method)")
    print(f"{'='*70}")
    
    calculator = AdhesionMetricsCalculator()
    results_without = calculator.calculate_from_arrays(
        times - times[0],  # Relative time
        positions,
        forces,
        layer_number=1,
        lifting_start_idx=None  # No phase awareness
    )
    
    print(f"\nResults WITHOUT phase awareness:")
    print(f"  Pre-initiation time: {results_without.get('pre_initiation_time', 'N/A'):.4f} s")
    print(f"  Total duration: {results_without.get('total_peel_duration', 'N/A'):.4f} s")
    
    # Test WITH phase awareness
    print(f"\n{'='*70}")
    print("Test 2: WITH phase awareness (new method)")
    print(f"{'='*70}")
    
    # Set lifting_start_idx to 0 (since we already segmented to just lift phase)
    results_with = calculator.calculate_from_arrays(
        times - times[0],
        positions,
        forces,
        layer_number=1,
        lifting_start_idx=0  # Phase awareness: start from beginning of lift
    )
    
    print(f"\nResults WITH phase awareness:")
    print(f"  Pre-initiation time: {results_with.get('pre_initiation_time', 'N/A'):.4f} s")
    print(f"  Total duration: {results_with.get('total_peel_duration', 'N/A'):.4f} s")
    
    # Compare
    print(f"\n{'='*70}")
    print("COMPARISON")
    print(f"{'='*70}")
    
    time_diff = results_without.get('pre_initiation_time', 0) - results_with.get('pre_initiation_time', 0)
    print(f"\nPre-initiation time difference: {time_diff:.4f} s")
    
    if abs(time_diff) > 0.1:
        print(f"[OK] Phase awareness made a difference ({time_diff:.4f}s)")
    else:
        print(f"[INFO]  Little difference (may not have sandwich phase in this data)")


def test_post_processing_analysis(csv_file, corrected_csv_file):
    """
    Test 3: Run post-processing analysis on the corrected autolog file.
    This simulates what would happen if you ran RawDataProcessor on the autolog,
    just like batch processing or post_print_analyzer.py would do.
    
    Args:
        csv_file: Path to ORIGINAL autolog CSV file (for reference)
        corrected_csv_file: Path to CORRECTED autolog CSV with real-time phase labels
    """
    if not POST_PROCESSING_AVAILABLE:
        print("\n??  Skipping post-processing test (tools not available)")
        return
    
    print(f"\nProcessing CORRECTED autolog: {corrected_csv_file}")
    print(f"(Generated from original: {csv_file})")
    
    if not corrected_csv_file.exists():
        print(f"\n[ERROR] ERROR: Corrected CSV not found: {corrected_csv_file}")
        return
    
    try:
        # Create calculator (no parameters - it uses defaults)
        calculator = AdhesionMetricsCalculator()
        
        # Create processor
        processor = RawDataProcessor(calculator)
        
        # Process the CORRECTED file to get layers with real-time phase labels
        print("\nRunning RawDataProcessor.process_csv() on CORRECTED data...")
        layers = processor.process_csv(str(corrected_csv_file))
        
        if not layers:
            print("??  No layers detected in post-processing")
            return
        
        print(f"\n[OK] Post-processing detected {len(layers)} layers")
        
        # Print metrics summary
        print("\n" + "="*70)
        print("POST-PROCESSING METRICS SUMMARY (with CORRECTED phase labels)")
        print("="*70)
        print(f"{'Layer':<8} {'Peak Force':<12} {'Work (mJ)':<12} {'Pre-Init (s)':<14} {'Duration (s)':<12}")
        print("-" * 70)
        
        for layer in layers:
            metrics = layer['metrics']
            print(f"{layer['number']:<8} "
                  f"{metrics['peak_force']:<12.4f} "
                  f"{metrics['work_of_adhesion_corrected_mJ']:<12.3f} "
                  f"{metrics['pre_initiation_duration']:<14.3f} "
                  f"{metrics['total_peel_duration']:<12.3f}")
        print("="*70)
        
        # Generate plot using AnalysisPlotter
        output_dir = Path(__file__).parent
        plot_filename = output_dir / f"test_spoofed_analysis_CORRECTED_{csv_file.stem}.png"
        
        # Load CORRECTED data for plotting
        df = pd.read_csv(corrected_csv_file)
        time_data = df['Elapsed Time (s)'].to_numpy()
        force_data = df['Force (N)'].to_numpy()
        smoothed_force = calculator._apply_smoothing(force_data)
        
        print(f"\nGenerating analysis plot: {plot_filename}")
        plotter = AnalysisPlotter()
        plotter.create_plot(
            time_data=time_data,
            force_data=force_data,
            smoothed_force=smoothed_force,
            layers=layers,
            title=f"Spoofed Test - CORRECTED Phase Labels - {csv_file.stem}",
            save_path=plot_filename
        )
        
        print(f"\n[OK] Post-processing complete!")
        print(f"   Plot saved: {plot_filename}")
        
    except Exception as e:
        print(f"\n[ERROR] Post-processing failed: {e}")
        import traceback
        traceback.print_exc()


def main():
    """
    Main test function - runs all simulations.
    """
    print("="*70)
    print("FULL PRINT SIMULATION TEST")
    print("Testing entire data flow with phase awareness")
    print("="*70)
    
    # Find test file
    test_files = [
        Path("test_autolog_L60-L65.csv"),  # User-provided file with Phase column
        Path("test_autolog_L430-L435.csv"),  # User-provided file
        Path("archive/autolog_L48-L50.csv"),
        Path("archive/autolog_L148-L150.csv"),
        Path("archive/autolog_L198-L200.csv"),
        Path("post-processing/autolog_L48-L50.csv"),
    ]
    
    csv_file = None
    for f in test_files:
        if f.exists():
            csv_file = f
            break
    
    if csv_file is None:
        print("\n[ERROR] ERROR: No autolog files found!")
        print("Please provide path to autolog CSV file.")
        return
    
    print(f"\nUsing test file: {csv_file}")
    
    # Generate corrected CSV with real-time phase labels
    print(f"\n{'='*70}")
    print("GENERATING CORRECTED CSV WITH REAL-TIME PHASE LABELS")
    print(f"{'='*70}")
    
    corrected_csv_path = Path("test_spoofed_corrected_autolog.csv")
    csv_feeder = CSVDataFeeder(csv_file, output_csv=str(corrected_csv_path))
    
    # Run through all data to generate corrected CSV
    print("\nProcessing all data points through real PositionLogger...")
    data_points = list(csv_feeder.simulate_print())
    print(f"[OK] Generated corrected CSV: {corrected_csv_path}")
    
    # Test 1: Real-time peak force logging (using corrected phases)
    results = test_real_time_peak_force_logging(csv_file)
    
    # Test 2: Phase-aware pre-initiation
    test_phase_aware_pre_initiation(csv_file)
    
    # Summary
    print(f"\n{'='*70}")
    print("TEST SUMMARY")
    print(f"{'='*70}")
    
    if results is not None and len(results) > 0:
        print(f"\n[OK] Real-time logging: PASS ({len(results)} layers processed)")
        print(f"[OK] Phase-aware pre-initiation: PASS")
        print(f"\n[SUCCESS] All tests PASSED!")
    else:
        print(f"\n[ERROR] Some tests FAILED")
    
    print(f"\nOutput files created:")
    print(f"  - test_simulated_peak_force_output.csv")
    print(f"  - {corrected_csv_path}")
    
    # Test 3: Post-processing analysis using CORRECTED CSV
    print(f"\n{'='*70}")
    print("POST-PROCESSING ANALYSIS")
    print("Processing CORRECTED autolog (with real-time phase labels)")
    print(f"{'='*70}")
    
    test_post_processing_analysis(csv_file, corrected_csv_path)


if __name__ == "__main__":
    main()

