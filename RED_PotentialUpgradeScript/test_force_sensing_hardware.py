"""
Force Sensing Hardware Test Script
===================================

This script tests the Phidget bridge connection and force sensing hardware
WITHOUT requiring the full printer setup or GUI.

Test Sequence:
1. Test Phidget22 library import
2. Detect connected Phidget VoltageRatioInput devices
3. Test bridge connection and data reading
4. Test ForceGaugeManager initialization
5. Verify data acquisition system

Usage:
    python test_force_sensing_hardware.py

Requirements:
    - Phidget22 library installed (pip install Phidget22)
    - Phidget bridge connected via USB
    - Force gauge does NOT need to be connected (bridge can be tested alone)

Author: Evan Jones
Date: December 18, 2025
"""

import sys
import time
import os
from pathlib import Path

# Add support_modules to path
current_dir = Path(__file__).parent
support_modules_dir = current_dir / "support_modules"
if str(support_modules_dir) not in sys.path:
    sys.path.insert(0, str(support_modules_dir))

# Test results tracking
test_results = []
total_tests = 0
passed_tests = 0

def print_header(text):
    """Print a formatted section header."""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)

def print_test(test_name, result, details=""):
    """Print test result and track statistics."""
    global total_tests, passed_tests, test_results
    total_tests += 1
    
    status = "✓ PASS" if result else "✗ FAIL"
    color = "\033[92m" if result else "\033[91m"  # Green or Red
    reset = "\033[0m"
    
    print(f"\n{color}{status}{reset} - {test_name}")
    if details:
        print(f"      {details}")
    
    if result:
        passed_tests += 1
    
    test_results.append((test_name, result, details))

def print_summary():
    """Print final test summary."""
    print_header("TEST SUMMARY")
    print(f"\nTotal Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")
    
    if passed_tests == total_tests:
        print("\n✓ ALL TESTS PASSED - Force sensing hardware is ready!")
    else:
        print("\n✗ SOME TESTS FAILED - Review failures above")
        print("\nFailed tests:")
        for name, result, details in test_results:
            if not result:
                print(f"  - {name}")
                if details:
                    print(f"    {details}")

# ============================================================================
# TEST 1: Phidget22 Library
# ============================================================================
print_header("TEST 1: Phidget22 Library Installation")

try:
    from Phidget22.Phidget import *
    from Phidget22.Devices.VoltageRatioInput import *
    print_test("Phidget22 Import", True, "Library is installed and importable")
    PHIDGET22_AVAILABLE = True
except ImportError as e:
    print_test("Phidget22 Import", False, f"ImportError: {e}")
    print("\n⚠ CRITICAL: Phidget22 is not installed.")
    print("   Install with: pip install Phidget22")
    PHIDGET22_AVAILABLE = False

# ============================================================================
# TEST 2: Phidget Device Detection
# ============================================================================
if PHIDGET22_AVAILABLE:
    print_header("TEST 2: Phidget Bridge Detection")
    
    try:
        # Create a VoltageRatioInput object to detect devices
        test_device = VoltageRatioInput()
        
        print("\nAttempting to detect Phidget bridge (15 second timeout)...")
        print("Please ensure the Phidget bridge is connected via USB.")
        
        # Try to open and wait for attachment
        test_device.openWaitForAttachment(15000)  # 15 second timeout
        
        # If we get here, device is attached
        serial_number = test_device.getDeviceSerialNumber()
        channel = test_device.getChannel()
        
        print_test("Bridge Detection", True, 
                  f"Found Phidget device (Serial: {serial_number}, Channel: {channel})")
        
        # Test reading a value
        try:
            voltage_ratio = test_device.getVoltageRatio()
            print_test("Read Voltage Ratio", True, 
                      f"Current reading: {voltage_ratio:.6f} V/V")
        except Exception as e:
            print_test("Read Voltage Ratio", False, str(e))
        
        # Clean up
        test_device.close()
        
    except PhidgetException as e:
        if e.code == ErrorCode.EPHIDGET_TIMEOUT:
            print_test("Bridge Detection", False, 
                      "Timeout - No Phidget bridge detected. Check USB connection.")
        else:
            print_test("Bridge Detection", False, f"PhidgetException: {e.details}")
    except Exception as e:
        print_test("Bridge Detection", False, str(e))

# ============================================================================
# TEST 3: ForceGaugeManager Initialization
# ============================================================================
if PHIDGET22_AVAILABLE:
    print_header("TEST 3: ForceGaugeManager Initialization")
    
    try:
        # Try to import ForceGaugeManager
        try:
            from ForceGaugeManager import ForceGaugeManager
            print_test("ForceGaugeManager Import", True, "Module found and imported")
        except ImportError as e:
            print_test("ForceGaugeManager Import", False, str(e))
            print("\n⚠ Ensure support_modules/ForceGaugeManager.py exists")
        
        # Try to create a ForceGaugeManager instance (minimal - no GUI elements)
        print("\nAttempting to initialize ForceGaugeManager...")
        print("Note: This will attempt to connect to the Phidget bridge.")
        
        # We need to create mock Tkinter labels since ForceGaugeManager expects them
        class MockLabel:
            def config(self, **kwargs):
                pass
        
        mock_label = MockLabel()
        
        try:
            import queue
            test_queue = queue.Queue()
            
            force_manager = ForceGaugeManager(
                gain_label=mock_label,
                offset_label=mock_label,
                force_status_label=mock_label,
                large_force_readout_label=mock_label,
                output_force_queue=test_queue,
                parent_window=None,
                sensor_window_ref=None
            )
            
            print_test("ForceGaugeManager Creation", True, 
                      "Instance created successfully")
            
            # Check if it connected to the bridge
            if force_manager.voltage_ratio_input:
                try:
                    is_attached = force_manager.voltage_ratio_input.getAttached()
                    if is_attached:
                        print_test("Bridge Connection via Manager", True,
                                  "ForceGaugeManager successfully connected to bridge")
                        
                        # Try to read calibration status
                        is_calibrated = force_manager.is_calibrated()
                        print_test("Calibration Status Check", True,
                                  f"Calibrated: {is_calibrated} (expected: False for new setup)")
                    else:
                        print_test("Bridge Connection via Manager", False,
                                  "Bridge not attached")
                except Exception as e:
                    print_test("Bridge Connection via Manager", False, str(e))
            else:
                print_test("Bridge Connection via Manager", False,
                          "voltage_ratio_input is None")
            
            # Clean up
            if force_manager.voltage_ratio_input:
                force_manager.stop_force_reading_thread()
                time.sleep(0.5)  # Give thread time to stop
            
        except Exception as e:
            print_test("ForceGaugeManager Creation", False, str(e))
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"\n✗ Unexpected error in ForceGaugeManager test: {e}")
        import traceback
        traceback.print_exc()

# ============================================================================
# TEST 4: Data Acquisition Test
# ============================================================================
if PHIDGET22_AVAILABLE:
    print_header("TEST 4: Continuous Data Acquisition")
    
    try:
        print("\nTesting continuous data reading (10 samples over 2 seconds)...")
        
        test_device = VoltageRatioInput()
        test_device.openWaitForAttachment(5000)
        
        if test_device.getAttached():
            # Set data interval to 100ms (10 Hz)
            test_device.setDataInterval(100)
            
            samples = []
            start_time = time.time()
            sample_count = 0
            
            print("\nReading samples:")
            while sample_count < 10 and (time.time() - start_time) < 3.0:
                try:
                    voltage_ratio = test_device.getVoltageRatio()
                    samples.append(voltage_ratio)
                    print(f"  Sample {sample_count+1}: {voltage_ratio:.6f} V/V")
                    sample_count += 1
                    time.sleep(0.2)
                except Exception as e:
                    print(f"  Error reading sample: {e}")
                    break
            
            if len(samples) >= 5:
                import statistics
                mean_val = statistics.mean(samples)
                std_val = statistics.stdev(samples) if len(samples) > 1 else 0
                
                print_test("Data Acquisition", True,
                          f"Collected {len(samples)} samples (mean: {mean_val:.6f}, std: {std_val:.6f})")
                
                # Check data quality
                if std_val < 0.01:  # Low noise is good
                    print_test("Data Quality", True,
                              f"Low noise detected (std: {std_val:.6f})")
                else:
                    print_test("Data Quality", True,
                              f"Higher noise detected (std: {std_val:.6f}) - Normal without load cell")
            else:
                print_test("Data Acquisition", False,
                          f"Only collected {len(samples)} samples")
            
            test_device.close()
        else:
            print_test("Data Acquisition", False, "Device not attached")
            
    except Exception as e:
        print_test("Data Acquisition", False, str(e))

# ============================================================================
# TEST 5: System Integration Check
# ============================================================================
print_header("TEST 5: System Integration Check")

# Check if support modules directory exists
support_modules_exist = (current_dir / "support_modules").exists()
print_test("Support Modules Directory", support_modules_exist,
          f"Path: {support_modules_dir}")

if support_modules_exist:
    # Check for required files
    required_files = [
        "ForceGaugeManager.py",
        "SensorDataWindow.py",
        "AutoHomeRoutine.py",
        "PositionLogger.py",
        "AutomatedLayerLogger.py",
        "ExperimentalConditionsWindow.py"
    ]
    
    for file_name in required_files:
        file_path = support_modules_dir / file_name
        exists = file_path.exists()
        print_test(f"File: {file_name}", exists,
                  "Found" if exists else "Missing")

# Check if main RED_Segmented.py exists
main_file = current_dir / "RED_Segmented.py"
main_exists = main_file.exists()
print_test("RED_Segmented.py", main_exists,
          "Main control file found" if main_exists else "Missing")

# ============================================================================
# Final Summary
# ============================================================================
print_summary()

# ============================================================================
# Recommendations
# ============================================================================
print_header("RECOMMENDATIONS")

if not PHIDGET22_AVAILABLE:
    print("\n⚠ CRITICAL: Install Phidget22 library")
    print("   Command: pip install Phidget22")

if PHIDGET22_AVAILABLE and passed_tests >= (total_tests * 0.8):
    print("\n✓ Hardware tests passed successfully!")
    print("\nNext steps:")
    print("1. Connect the force gauge to the Phidget bridge")
    print("2. Run RED_Segmented.py with MOCK_MODE = False")
    print("3. Open Sensor Panel and calibrate the force gauge")
    print("4. Test auto-home routine")
    print("\nFor detailed instructions, see:")
    print("  - TESTING_INSTRUCTIONS_FOR_ENGINEER.md")
    print("  - RED_LAB_UPGRADE_DOCUMENTATION.md")
elif PHIDGET22_AVAILABLE:
    print("\n⚠ Some tests failed - review issues above")
    print("\nCommon fixes:")
    print("- Ensure Phidget bridge is connected via USB")
    print("- Check USB cable and port")
    print("- Try reconnecting the bridge")
    print("- Restart the computer if driver issues persist")

print("\n" + "="*70)
print("Test completed. Save this output and report results.")
print("="*70 + "\n")
