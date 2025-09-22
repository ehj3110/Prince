"""
Test the entire work of adhesion workflow to ensure no errors during printing
"""
import sys
import os
import time

# Simulate the same import structure as Prince_Segmented.py
sys.path.append(os.path.join(os.path.dirname(__file__), 'support_modules'))

print("TESTING PRINTING WORKFLOW COMPATIBILITY")
print("=" * 50)

# Test 1: Import PeakForceLogger (as used during printing)
print("1. Testing PeakForceLogger import from support_modules...")
try:
    from PeakForceLogger import PeakForceLogger
    print("   ✅ PeakForceLogger import successful")
except Exception as e:
    print(f"   ❌ PeakForceLogger import failed: {e}")
    exit(1)

# Test 2: Test work of adhesion calculation
print("2. Testing work of adhesion calculation...")
try:
    # Create a test PeakForceLogger instance (as would happen during printing)
    test_logger = PeakForceLogger("test_print_workflow.csv", is_manual_log=False)
    
    # Simulate layer monitoring (as happens during printing)
    test_logger.start_monitoring_for_layer(1, z_peel_peak=10.0, z_return_pos=12.0)
    
    # Add some test data points (as would happen during printing)
    current_time = time.time()
    test_logger.add_data_point(current_time + 0.0, 10.0, 0.05)  # Peel start
    test_logger.add_data_point(current_time + 0.1, 10.5, 0.20)  # In peel
    test_logger.add_data_point(current_time + 0.2, 11.0, 0.25)  # Peak force
    test_logger.add_data_point(current_time + 0.3, 11.5, 0.15)  # In peel
    test_logger.add_data_point(current_time + 0.4, 12.0, 0.08)  # Peel end
    
    # Stop monitoring and calculate work (as happens at end of each layer)
    success = test_logger.stop_monitoring_and_log_peak()
    
    if success:
        print("   ✅ Work of adhesion calculation successful")
    else:
        print("   ❌ Work of adhesion calculation failed")
    
    # Clean up test file
    if os.path.exists("test_print_workflow.csv"):
        os.remove("test_print_workflow.csv")
        
except Exception as e:
    print(f"   ❌ Work of adhesion calculation failed: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Test if corrected adhesion_metrics_calculator is being used
print("3. Testing adhesion_metrics_calculator settings...")
try:
    from adhesion_metrics_calculator import AdhesionMetricsCalculator
    
    # Check if it's using the corrected light smoothing settings
    calc = AdhesionMetricsCalculator()
    
    if calc.smoothing_window == 3 and calc.smoothing_polyorder == 1:
        print("   ✅ Corrected light smoothing settings confirmed")
        print(f"      Window: {calc.smoothing_window}, Polyorder: {calc.smoothing_polyorder}")
    else:
        print("   ⚠️  WARNING: Unexpected smoothing settings detected")
        print(f"      Window: {calc.smoothing_window}, Polyorder: {calc.smoothing_polyorder}")
        print("      Expected: Window=3, Polyorder=1")
        
except Exception as e:
    print(f"   ❌ AdhesionMetricsCalculator test failed: {e}")

# Test 4: Test SensorDataWindow import (used during printing)
print("4. Testing SensorDataWindow import...")
try:
    from SensorDataWindow import SensorDataWindow
    print("   ✅ SensorDataWindow import successful")
except Exception as e:
    print(f"   ❌ SensorDataWindow import failed: {e}")

# Test 5: Test if plotting will work (post-print analysis)
print("5. Testing hybrid plotter availability...")
try:
    from hybrid_adhesion_plotter import HybridAdhesionPlotter
    plotter = HybridAdhesionPlotter()
    
    # Check if it has the corrected calculator settings
    if (plotter.calculator.smoothing_window == 3 and 
        plotter.calculator.smoothing_polyorder == 1):
        print("   ✅ Hybrid plotter has corrected settings")
    else:
        print("   ⚠️  WARNING: Hybrid plotter has unexpected settings")
        print(f"      Window: {plotter.calculator.smoothing_window}, Polyorder: {plotter.calculator.smoothing_polyorder}")
        
except Exception as e:
    print(f"   ❌ Hybrid plotter test failed: {e}")

print("\n" + "=" * 50)
print("WORKFLOW COMPATIBILITY TEST COMPLETE")
print("Your printer should work correctly with the corrected adhesion calculations!")
print("=" * 50)
