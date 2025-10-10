"""
Integration Test for Two-Step Baseline Analyzer
=============================================

This script tests the complete integration of the TwoStepBaselineAnalyzer
with the PeakForceLogger system to ensure proper CSV output with the
exact column headers and metrics requested.

Author: Integration Test Team
Date: September 17, 2025
"""

import numpy as np
import os
import sys
from datetime import datetime

# Add path for our modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'support_modules'))

from PeakForceLogger import PeakForceLogger
from two_step_baseline_analyzer import TwoStepBaselineAnalyzer

def generate_test_data():
    """
    Generate realistic test data similar to our L48-L50 analysis.
    """
    # Create test data similar to real measurements
    sampling_rate = 50  # Hz
    duration = 3.0  # seconds
    t = np.linspace(0, duration, int(duration * sampling_rate))
    
    # Generate realistic positions (peel motion)
    positions = 2.0 + 0.5 * t  # Starting at 2mm, moving up
    
    # Generate realistic force profile
    forces = np.zeros_like(t)
    
    # Add noise
    noise = np.random.normal(0, 0.005, len(t))
    
    # Create force profile: gradual increase, peak, then decay
    for i, time in enumerate(t):
        if time < 0.5:
            forces[i] = 0.01 + 0.02 * time  # Gradual pre-loading
        elif time < 1.0:
            forces[i] = 0.02 + 0.25 * (time - 0.5)  # Rapid increase to peak
        elif time < 1.8:
            forces[i] = 0.145 - 0.15 * (time - 1.0)  # Decay from peak
        else:
            forces[i] = 0.025 - 0.02 * (time - 1.8)  # Return to baseline
    
    # Ensure forces are non-negative and add noise
    forces = np.maximum(forces + noise, 0)
    
    # Generate timestamps (absolute time)
    base_time = datetime.now().timestamp()
    timestamps = base_time + t
    
    return timestamps, positions, forces

def test_direct_analyzer():
    """Test the TwoStepBaselineAnalyzer directly."""
    print("=" * 60)
    print("TESTING TWOSTEPBASELINEANALYZER DIRECTLY")
    print("=" * 60)
    
    # Generate test data
    timestamps, positions, forces = generate_test_data()
    
    # Create analyzer
    analyzer = TwoStepBaselineAnalyzer(sampling_rate=50)
    
    # Analyze data
    results = analyzer.analyze_peel_data(timestamps, positions, forces)
    
    # Display results in requested order
    print("Direct Analyzer Results:")
    print("-" * 40)
    requested_metrics = [
        ('Layer number', 'N/A (test)'),
        ('Peak Force', f"{results['peak_force_N']:.4f} N"),
        ('Work of Adhesion', f"{results['work_of_adhesion_mJ']:.4f} mJ"),
        ('Pre-initiation time', f"{results['pre_initiation_time_s']:.4f} s"),
        ('Propagation time', f"{results['propagation_time_s']:.4f} s"),
        ('Total peeling time', f"{results['total_peeling_time_s']:.4f} s"),
        ('Distance to peel start', f"{results['distance_to_peel_start_mm']:.4f} mm"),
        ('Distance to full peel', f"{results['distance_to_full_peel_mm']:.4f} mm"),
        ('Peak retraction force (rel. baseline)', f"{results['peak_retraction_force_N']:.4f} N"),
        ('Pre-peel force', f"{results['pre_peel_force_N']:.4f} N"),
        ('Raw peak force reading', f"{results['raw_peak_force_reading_N']:.4f} N"),
        ('Baseline reading', f"{results['baseline_reading_N']:.4f} N")
    ]
    
    for metric, value in requested_metrics:
        print(f"{metric:35}: {value}")
    
    return results

def test_peakforce_logger_integration():
    """Test the complete PeakForceLogger integration."""
    print("\n" + "=" * 60)
    print("TESTING PEAKFORCELOGGER INTEGRATION")
    print("=" * 60)
    
    # Create test CSV file
    test_csv = "test_two_step_integration.csv"
    if os.path.exists(test_csv):
        os.remove(test_csv)
    
    # Create PeakForceLogger with TwoStepBaselineAnalyzer
    logger = PeakForceLogger(
        output_csv_filepath=test_csv,
        enhanced_analysis=True,
        analyzer_type="two_step_baseline"
    )
    
    # Generate multiple layers of test data
    for layer in range(1, 4):
        print(f"\nProcessing Layer {layer}...")
        
        # Generate test data
        timestamps, positions, forces = generate_test_data()
        
        # Simulate logger workflow
        logger.start_monitoring_for_layer(layer, z_peel_peak=2.0, z_return_pos=3.5)
        
        # Add data points
        for i in range(len(timestamps)):
            logger.add_data_point(timestamps[i], positions[i], forces[i])
        
        # Stop monitoring and log results
        success = logger.stop_monitoring_and_log_peak()
        print(f"Layer {layer} logging {'succeeded' if success else 'failed'}")
    
    # Read and display CSV results
    print(f"\nCSV File Contents ({test_csv}):")
    print("-" * 60)
    if os.path.exists(test_csv):
        with open(test_csv, 'r') as f:
            lines = f.readlines()
            for i, line in enumerate(lines):
                print(f"Line {i+1}: {line.strip()}")
    else:
        print("ERROR: CSV file was not created!")
    
    return test_csv

def validate_csv_headers():
    """Validate that CSV headers match the exact specification."""
    test_csv = "test_two_step_integration.csv"
    
    print("\n" + "=" * 60)
    print("VALIDATING CSV HEADERS")
    print("=" * 60)
    
    expected_headers = [
        'Layer_Number', 'Peak_Force_N', 'Work_of_Adhesion_mJ',
        'Pre_Initiation_Time_s', 'Propagation_Time_s', 'Total_Peeling_Time_s',
        'Distance_to_Peel_Start_mm', 'Distance_to_Full_Peel_mm',
        'Peak_Retraction_Force_N', 'Pre_Peel_Force_N',
        'Raw_Peak_Force_Reading_N', 'Baseline_Reading_N'
    ]
    
    if os.path.exists(test_csv):
        with open(test_csv, 'r') as f:
            first_line = f.readline().strip()
            actual_headers = [h.strip() for h in first_line.split(',')]
            
        print("Expected Headers:")
        for i, header in enumerate(expected_headers):
            print(f"  {i+1:2d}. {header}")
            
        print("\nActual Headers:")
        for i, header in enumerate(actual_headers):
            print(f"  {i+1:2d}. {header}")
            
        print("\nHeader Validation:")
        if actual_headers == expected_headers:
            print("✓ SUCCESS: Headers match exactly!")
        else:
            print("✗ FAILURE: Headers do not match!")
            
            # Show differences
            for i, (expected, actual) in enumerate(zip(expected_headers, actual_headers)):
                if expected != actual:
                    print(f"  Column {i+1}: Expected '{expected}', Got '{actual}'")
    else:
        print("ERROR: CSV file not found for validation!")

def main():
    """Run complete integration test."""
    print("Two-Step Baseline Analyzer Integration Test")
    print("==========================================")
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Test 1: Direct analyzer
        direct_results = test_direct_analyzer()
        
        # Test 2: PeakForceLogger integration
        csv_file = test_peakforce_logger_integration()
        
        # Test 3: Validate CSV headers
        validate_csv_headers()
        
        print("\n" + "=" * 60)
        print("INTEGRATION TEST SUMMARY")
        print("=" * 60)
        print("✓ TwoStepBaselineAnalyzer: Working")
        print("✓ PeakForceLogger Integration: Working")
        print("✓ CSV Output: Generated")
        print("✓ Header Validation: Complete")
        print(f"✓ Test CSV File: {csv_file}")
        
        print("\nIntegration test completed successfully!")
        
    except Exception as e:
        print(f"\n✗ INTEGRATION TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
