"""
Test script for AdhesionMetricsCalculator to debug distance_to_peak issues.
This script tests the calculator with real data from autolog_L48.csv.
"""
import sys
import os

# Add the workspace directory to the Python path
workspace_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, workspace_dir)

import numpy as np
import pandas as pd
from support_modules.adhesion_metrics_calculator import AdhesionMetricsCalculator

def test_with_real_data():
    """Test the calculator with real data from autolog_L48.csv"""
    print("="*80)
    print("Testing AdhesionMetricsCalculator with real data")
    print("="*80)
    
    # Load the dataset
    print("\n1. Loading dataset...")
    csv_path = "c:\\Users\\cheng sun\\BoyuanSun\\Prince_Segmented_20250926\\archive\\autolog_L48.csv"
    data = pd.read_csv(csv_path)
    print(f"   Loaded {len(data)} data points")
    
    # Extract data
    times = data['Elapsed Time (s)'].values
    positions = data['Position (mm)'].values
    forces = data['Force (N)'].values
    
    print(f"\n2. Data summary:")
    print(f"   Time range: {times[0]:.3f} to {times[-1]:.3f} seconds")
    print(f"   Position range: {positions.min():.3f} to {positions.max():.3f} mm")
    print(f"   Force range: {forces.min():.6f} to {forces.max():.6f} N")
    
    # Initialize calculator
    print("\n3. Initializing AdhesionMetricsCalculator...")
    calculator = AdhesionMetricsCalculator()
    
    # Test the calculate_from_arrays method (the public API)
    print("\n4. Calling calculate_from_arrays()...")
    try:
        results = calculator.calculate_from_arrays(
            time_data=times,
            position_data=positions,
            force_data=forces,
            layer_number=48,
            motion_end_idx=len(times) - 1
        )
        
        print("\n5. Results:")
        print("   SUCCESS! Metrics calculated.")
        print("\n   Key metrics:")
        print(f"   - Layer number: {results.get('layer_number', 'N/A')}")
        print(f"   - Peak force: {results.get('peak_force', 'N/A'):.6f} N")
        print(f"   - Peak force (corrected): {results.get('peak_force_corrected', 'N/A'):.6f} N")
        print(f"   - Baseline force: {results.get('baseline_force', 'N/A'):.6f} N")
        print(f"   - Peak force position: {results.get('peak_force_position', 'N/A'):.3f} mm")
        print(f"   - Peak force time: {results.get('peak_force_time', 'N/A'):.3f} s")
        
        print(f"\n   Pre-initiation metrics:")
        print(f"   - Pre-initiation position: {results.get('pre_initiation_position', 'N/A'):.3f} mm")
        print(f"   - Pre-initiation time: {results.get('pre_initiation_time', 'N/A'):.3f} s")
        print(f"   - Pre-initiation distance: {results.get('pre_initiation_distance', 'N/A'):.6f} mm")
        print(f"   - Pre-initiation duration: {results.get('pre_initiation_duration', 'N/A'):.3f} s")
        
        print(f"\n   Propagation metrics:")
        print(f"   - Propagation end position: {results.get('propagation_end_position', 'N/A'):.3f} mm")
        print(f"   - Propagation end time: {results.get('propagation_end_time', 'N/A'):.3f} s")
        print(f"   - Propagation distance: {results.get('propagation_distance', 'N/A'):.6f} mm")
        print(f"   - Propagation duration: {results.get('propagation_duration', 'N/A'):.3f} s")
        
        print(f"\n   Total peel metrics:")
        print(f"   - Total peel distance: {results.get('total_peel_distance', 'N/A'):.6f} mm")
        print(f"   - Total peel duration: {results.get('total_peel_duration', 'N/A'):.3f} s")
        
        print(f"\n   Work metrics:")
        total_work = results.get('total_work', None)
        pre_init_work = results.get('pre_initiation_work', None)
        prop_work = results.get('propagation_work', None)
        
        if total_work is not None:
            print(f"   - Total work: {total_work:.6f} J")
        else:
            print(f"   - Total work: N/A")
            
        if pre_init_work is not None:
            print(f"   - Pre-initiation work: {pre_init_work:.6f} J")
        else:
            print(f"   - Pre-initiation work: N/A")
            
        if prop_work is not None:
            print(f"   - Propagation work: {prop_work:.6f} J")
        else:
            print(f"   - Propagation work: N/A")
        
        # Check for the distance_to_peak issue
        print("\n6. Checking for distance_to_peak in results...")
        if 'distance_to_peak' in results:
            print(f"   WARNING: Old 'distance_to_peak' key found: {results['distance_to_peak']}")
        else:
            print("   OK: No 'distance_to_peak' key (this is expected with new calculator)")
            print("   Note: Use 'pre_initiation_distance' instead")
        
        print("\n" + "="*80)
        print("TEST PASSED: All metrics calculated successfully!")
        print("="*80)
        
        return True
        
    except Exception as e:
        print(f"\n   ERROR: {type(e).__name__}: {e}")
        print("\n   This is the error that occurs during printing!")
        import traceback
        traceback.print_exc()
        
        print("\n" + "="*80)
        print("TEST FAILED")
        print("="*80)
        return False

def test_internal_methods():
    """Test internal methods of the calculator"""
    print("\n" + "="*80)
    print("Testing internal calculator methods")
    print("="*80)
    
    # Load the dataset
    csv_path = "c:\\Users\\cheng sun\\BoyuanSun\\Prince_Segmented_20250926\\archive\\autolog_L48.csv"
    data = pd.read_csv(csv_path)
    
    times = data['Elapsed Time (s)'].values
    positions = data['Position (mm)'].values
    forces = data['Force (N)'].values
    
    calculator = AdhesionMetricsCalculator()
    
    # Test smoothing
    print("\n1. Testing force smoothing...")
    smoothed = calculator._apply_smoothing(forces)
    print(f"   Original force range: {forces.min():.6f} to {forces.max():.6f} N")
    print(f"   Smoothed force range: {smoothed.min():.6f} to {smoothed.max():.6f} N")
    
    # Test peak finding
    print("\n2. Testing peak force detection...")
    peak_idx, peak_force = calculator._find_peak_force(smoothed)
    print(f"   Peak index: {peak_idx}")
    print(f"   Peak force: {peak_force:.6f} N")
    print(f"   Peak position: {positions[peak_idx]:.3f} mm")
    print(f"   Peak time: {times[peak_idx]:.3f} s")
    
    # Test baseline calculation
    print("\n3. Testing baseline calculation...")
    baseline = calculator._calculate_baseline(smoothed)
    print(f"   Baseline: {baseline:.6f} N")
    
    # Test pre-initiation finding
    print("\n4. Testing pre-initiation detection...")
    pre_init_idx = calculator._find_pre_initiation(smoothed, peak_idx, baseline)
    print(f"   Pre-initiation index: {pre_init_idx}")
    print(f"   Pre-initiation position: {positions[pre_init_idx]:.3f} mm")
    print(f"   Pre-initiation time: {times[pre_init_idx]:.3f} s")
    print(f"   Pre-initiation force: {smoothed[pre_init_idx]:.6f} N")
    
    # Calculate distance from pre-initiation to peak
    print("\n5. Calculating distance from pre-initiation to peak...")
    distance = positions[peak_idx] - positions[pre_init_idx]
    print(f"   Distance: {distance:.6f} mm")
    print(f"   This is what 'pre_initiation_distance' should be")
    
    print("\n" + "="*80)
    print("Internal methods test complete")
    print("="*80)

if __name__ == "__main__":
    print("\n" + "="*80)
    print("ADHESION CALCULATOR TEST SUITE")
    print("Purpose: Debug distance_to_peak calculation issues")
    print("="*80)
    
    # Test with real data
    success = test_with_real_data()
    
    # Test internal methods for detailed analysis
    if success:
        test_internal_methods()
    
    print("\n" + "="*80)
    print("TEST SUITE COMPLETE")
    print("="*80)
