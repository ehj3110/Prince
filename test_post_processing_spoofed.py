"""
Test Post-Processing with Existing Autolog Files

This script tests the RawData_Processor and adhesion metrics calculator
using existing autolog CSV files. It tests BOTH detection methods:
1. Adaptive detection (for old files without Phase column)
2. Phase-based detection (after adding Phase column to data)

Usage:
    python test_post_processing_spoofed.py

What it tests:
- RawData_Processor adaptive boundary detection
- RawData_Processor phase-based boundary detection  
- Adhesion metrics calculation
- Backward compatibility with old CSV files
"""

import numpy as np
import pandas as pd
from pathlib import Path
import sys

# Add support_modules to path
sys.path.insert(0, str(Path(__file__).parent / "support_modules"))
sys.path.insert(0, str(Path(__file__).parent / "post-processing"))

from adhesion_metrics_calculator import AdhesionMetricsCalculator
from RawData_Processor import RawDataProcessor


def add_phase_column_to_csv(input_csv, output_csv):
    """
    Add Phase column to an existing autolog CSV file.
    
    Uses the same phase detection logic as PositionLogger to simulate
    what a real print would generate.
    
    Args:
        input_csv: Path to autolog CSV without Phase column
        output_csv: Path to save CSV with Phase column added
    """
    print(f"\n=== Adding Phase Column ===")
    print(f"Input: {input_csv}")
    print(f"Output: {output_csv}")
    
    # Load original data
    df = pd.read_csv(input_csv)
    
    # Phase detection parameters (same as PositionLogger)
    POSITION_CHANGE_THRESHOLD = 0.002  # mm
    STATIONARY_THRESHOLD_COUNT = 3
    SANDWICH_DISTANCE_THRESHOLD = 1.0  # mm
    
    # Initialize phase tracking
    phases = []
    previous_position = None
    stationary_count = 0
    current_phase = "Unknown"
    position_at_motion_start = None
    
    # Determine phase for each data point
    for idx, row in df.iterrows():
        current_position = row['Position (mm)']
        
        # First reading - initialize
        if previous_position is None:
            previous_position = current_position
            position_at_motion_start = current_position
            current_phase = "Pause"
            phases.append(current_phase)
            continue
        
        # Calculate position change
        position_change = current_position - previous_position
        abs_change = abs(position_change)
        
        # Check if stationary
        if abs_change < POSITION_CHANGE_THRESHOLD:
            stationary_count += 1
            
            if stationary_count >= STATIONARY_THRESHOLD_COUNT:
                if current_phase not in ["Pause", "Unknown"]:
                    position_at_motion_start = current_position
                current_phase = "Pause"
        else:
            # Motion detected
            stationary_count = 0
            
            # Track start of motion
            if current_phase in ["Pause", "Unknown"]:
                position_at_motion_start = previous_position
            
            # Calculate total distance traveled
            total_distance_traveled = abs(current_position - position_at_motion_start) if position_at_motion_start is not None else 0
            
            # Classify phase
            if position_change < 0:  # Moving down
                if total_distance_traveled < SANDWICH_DISTANCE_THRESHOLD:
                    current_phase = "Sandwich"
                else:
                    current_phase = "Lift"
            else:  # Moving up
                current_phase = "Retract"
        
        phases.append(current_phase)
        previous_position = current_position
    
    # Add Phase column to dataframe
    df['Phase'] = phases
    
    # Save to new CSV
    df.to_csv(output_csv, index=False)
    
    # Print phase statistics
    phase_counts = df['Phase'].value_counts()
    print(f"\nPhase distribution:")
    for phase, count in phase_counts.items():
        print(f"  {phase}: {count} points")
    
    return output_csv


def test_adaptive_detection(csv_file):
    """
    Test adaptive boundary detection on CSV without Phase column.
    
    This tests backward compatibility with old autolog files.
    """
    print(f"\n{'='*70}")
    print(f"TEST 1: Adaptive Boundary Detection (No Phase Column)")
    print(f"{'='*70}")
    print(f"File: {csv_file}")
    
    # Initialize processor
    calculator = AdhesionMetricsCalculator()
    processor = RawDataProcessor(calculator)
    
    # Process the CSV
    print("\nProcessing with adaptive detection...")
    layers = processor.process_csv(csv_file)
    
    # Print results
    print(f"\n=== Results ===")
    print(f"Layers detected: {len(layers) if layers else 0}")
    
    if layers:
        for i, layer in enumerate(layers[:3]):  # Show first 3 layers
            metrics = layer.get('metrics', {})
            print(f"\nLayer {i+1}:")
            print(f"  Peak Force: {metrics.get('peak_force', 'N/A'):.4f} N")
            print(f"  Work of Adhesion: {metrics.get('work_of_adhesion_mJ', 'N/A'):.4f} mJ")
            print(f"  Pre-initiation Time: {metrics.get('pre_initiation_time', 'N/A'):.4f} s")
            print(f"  Total Duration: {metrics.get('total_peel_duration', 'N/A'):.4f} s")
    
    return layers


def test_phase_based_detection(csv_file):
    """
    Test phase-based boundary detection on CSV with Phase column.
    
    This tests the new phase-aware detection method.
    """
    print(f"\n{'='*70}")
    print(f"TEST 2: Phase-Based Boundary Detection (With Phase Column)")
    print(f"{'='*70}")
    print(f"File: {csv_file}")
    
    # Initialize processor
    calculator = AdhesionMetricsCalculator()
    processor = RawDataProcessor(calculator)
    
    # Process the CSV
    print("\nProcessing with phase-based detection...")
    layers = processor.process_csv(csv_file)
    
    # Print results
    print(f"\n=== Results ===")
    print(f"Layers detected: {len(layers) if layers else 0}")
    
    if layers:
        for i, layer in enumerate(layers[:3]):  # Show first 3 layers
            metrics = layer.get('metrics', {})
            print(f"\nLayer {i+1}:")
            print(f"  Peak Force: {metrics.get('peak_force', 'N/A'):.4f} N")
            print(f"  Work of Adhesion: {metrics.get('work_of_adhesion_mJ', 'N/A'):.4f} mJ")
            print(f"  Pre-initiation Time: {metrics.get('pre_initiation_time', 'N/A'):.4f} s")
            print(f"  Total Duration: {metrics.get('total_peel_duration', 'N/A'):.4f} s")
    
    return layers


def compare_results(adaptive_layers, phase_layers):
    """
    Compare results from adaptive vs phase-based detection.
    """
    print(f"\n{'='*70}")
    print(f"COMPARISON: Adaptive vs Phase-Based Detection")
    print(f"{'='*70}")
    
    adaptive_count = len(adaptive_layers) if adaptive_layers else 0
    phase_count = len(phase_layers) if phase_layers else 0
    
    print(f"\nLayers detected:")
    print(f"  Adaptive:    {adaptive_count}")
    print(f"  Phase-based: {phase_count}")
    
    if adaptive_layers and phase_layers:
        # Compare first layer metrics
        if len(adaptive_layers) > 0 and len(phase_layers) > 0:
            adaptive_metrics = adaptive_layers[0].get('metrics', {})
            phase_metrics = phase_layers[0].get('metrics', {})
            
            print(f"\nLayer 1 Comparison:")
            print(f"  Peak Force:")
            print(f"    Adaptive:    {adaptive_metrics.get('peak_force', 'N/A'):.4f} N")
            print(f"    Phase-based: {phase_metrics.get('peak_force', 'N/A'):.4f} N")
            
            print(f"  Work of Adhesion:")
            print(f"    Adaptive:    {adaptive_metrics.get('work_of_adhesion_mJ', 'N/A'):.4f} mJ")
            print(f"    Phase-based: {phase_metrics.get('work_of_adhesion_mJ', 'N/A'):.4f} mJ")
            
            print(f"  Pre-initiation Time:")
            print(f"    Adaptive:    {adaptive_metrics.get('pre_initiation_time', 'N/A'):.4f} s")
            print(f"    Phase-based: {phase_metrics.get('pre_initiation_time', 'N/A'):.4f} s")


def main():
    """
    Main test function.
    
    Tests post-processing with both adaptive and phase-based detection
    using existing autolog CSV files.
    """
    print("="*70)
    print("POST-PROCESSING SPOOF TEST")
    print("Testing RawData_Processor with existing autolog files")
    print("="*70)
    
    # Find an autolog file to test with
    test_files = [
        Path("test_autolog_L60-L65.csv"),  # User-provided file with Phase column
        Path("archive/autolog_L48-L50.csv"),
        Path("archive/autolog_L148-L150.csv"),
        Path("archive/autolog_L198-L200.csv"),
        Path("post-processing/autolog_L48-L50.csv"),
    ]
    
    autolog_file = None
    for f in test_files:
        if f.exists():
            autolog_file = f
            break
    
    if autolog_file is None:
        print("\n❌ ERROR: No autolog files found!")
        print("Please provide path to autolog CSV file.")
        print("\nSearched locations:")
        for f in test_files:
            print(f"  - {f}")
        return
    
    print(f"\nUsing test file: {autolog_file}")
    
    # Test 1: Adaptive detection (original file without Phase)
    adaptive_layers = test_adaptive_detection(autolog_file)
    
    # Test 2: Add Phase column and test phase-based detection
    output_file = Path("test_output_with_phase.csv")
    csv_with_phase = add_phase_column_to_csv(autolog_file, output_file)
    phase_layers = test_phase_based_detection(csv_with_phase)
    
    # Test 3: Compare results
    compare_results(adaptive_layers, phase_layers)
    
    # Summary
    print(f"\n{'='*70}")
    print("TEST SUMMARY")
    print(f"{'='*70}")
    
    adaptive_ok = adaptive_layers and len(adaptive_layers) > 0
    phase_ok = phase_layers and len(phase_layers) > 0
    
    print(f"\n✅ Adaptive Detection: {'PASS' if adaptive_ok else 'FAIL'}")
    print(f"✅ Phase-Based Detection: {'PASS' if phase_ok else 'FAIL'}")
    print(f"\nOutput file with Phase column: {output_file}")
    print(f"\nAll tests {'PASSED' if adaptive_ok and phase_ok else 'FAILED'}! ✅" if adaptive_ok and phase_ok else "Some tests failed ❌")


if __name__ == "__main__":
    main()
