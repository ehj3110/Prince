"""
Test script to simulate PeakForceLogger behavior during printing.
This tests the exact workflow that occurs when a layer is logged.
"""
import sys
import os

# Add the workspace directory to the Python path
workspace_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, workspace_dir)

import numpy as np
import pandas as pd
import time
from support_modules.PeakForceLogger import PeakForceLogger

def test_peakforce_logger_with_real_data():
    """Test PeakForceLogger with real data from autolog_L48.csv"""
    print("="*80)
    print("Testing PeakForceLogger with Real Data")
    print("="*80)
    
    # Load the dataset
    print("\n1. Loading test data...")
    csv_path = "c:\\Users\\cheng sun\\BoyuanSun\\Prince_Segmented_20250926\\archive\\autolog_L48.csv"
    data = pd.read_csv(csv_path)
    print(f"   Loaded {len(data)} data points")
    
    times = data['Elapsed Time (s)'].values
    positions = data['Position (mm)'].values
    forces = data['Force (N)'].values
    
    # Create a test output file
    output_file = "test_peak_force_output.csv"
    if os.path.exists(output_file):
        os.remove(output_file)
        print(f"   Removed existing {output_file}")
    
    # Initialize PeakForceLogger
    print("\n2. Initializing PeakForceLogger...")
    logger = PeakForceLogger(output_file, is_manual_log=False, use_corrected_calculator=True)
    print("   Logger initialized successfully")
    
    # Start monitoring for layer 48
    print("\n3. Starting monitoring for layer 48...")
    logger.start_monitoring_for_layer(48, z_peel_peak=65.0, z_return_pos=66.0)
    
    # Add data points (simulate real-time data acquisition)
    print("\n4. Adding data points...")
    current_time = time.time()
    for i in range(len(times)):
        # Convert elapsed time to absolute timestamp
        timestamp = current_time + times[i]
        logger.add_data_point(timestamp, positions[i], forces[i])
        
        # Print progress every 200 points
        if (i + 1) % 200 == 0:
            print(f"   Added {i+1}/{len(times)} data points...")
    
    print(f"   Added all {len(times)} data points")
    
    # Stop monitoring and trigger analysis
    print("\n5. Stopping monitoring and triggering analysis...")
    logger.stop_monitoring_and_log_peak()
    
    # Wait for analysis to complete
    print("   Waiting for analysis to complete...")
    time.sleep(2)  # Give the worker thread time to process
    
    # Check the output file
    print("\n6. Checking output file...")
    if os.path.exists(output_file):
        print(f"   Output file created: {output_file}")
        result_data = pd.read_csv(output_file)
        print(f"   Number of rows: {len(result_data)}")
        
        if len(result_data) > 0:
            print("\n   Results:")
            for col in result_data.columns:
                val = result_data[col].iloc[0]
                print(f"   - {col}: {val}")
            
            print("\n" + "="*80)
            print("TEST PASSED: PeakForceLogger successfully processed data!")
            print("="*80)
            return True
        else:
            print("\n" + "="*80)
            print("TEST FAILED: No data written to output file")
            print("="*80)
            return False
    else:
        print(f"   ERROR: Output file not created")
        print("\n" + "="*80)
        print("TEST FAILED: Output file not created")
        print("="*80)
        return False

if __name__ == "__main__":
    print("\n" + "="*80)
    print("PEAKFORCELOGGER TEST SUITE")
    print("Purpose: Test the complete logging workflow with real data")
    print("="*80)
    
    success = test_peakforce_logger_with_real_data()
    
    print("\n" + "="*80)
    print("TEST SUITE COMPLETE")
    if success:
        print("Status: SUCCESS")
    else:
        print("Status: FAILED")
    print("="*80)
