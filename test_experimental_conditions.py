"""
Test script for ExperimentalConditionsWindow and PrintFailureDetector integration.

This script validates:
1. ExperimentalConditionsWindow imports correctly
2. PrintFailureDetector logic works as expected
3. CSV writing functionality
4. Folder renaming logic
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add support_modules to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'support_modules'))

def test_print_failure_detector():
    """Test the PrintFailureDetector class logic."""
    print("\n" + "="*60)
    print("TEST 1: PrintFailureDetector Logic")
    print("="*60)
    
    from support_modules.ExperimentalConditionsWindow import PrintFailureDetector
    
    detector = PrintFailureDetector()
    
    # Test normal increasing forces (should not trigger failure)
    print("\n1.1 Testing normal increasing forces...")
    forces = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0, 20.0]
    for i, force in enumerate(forces, start=1):
        result = detector.check_layer(i, force)
        if result:
            print(f"   ✗ FAIL: Unexpected failure at layer {i}")
            return False
    print("   ✓ PASS: No failure detected for increasing forces")
    
    # Reset for next test
    detector.reset()
    
    # Test 10 consecutive decreases (should trigger failure on layer 11)
    # Layer 1 = baseline, layers 2-11 = 10 decreases
    print("\n1.2 Testing 10 consecutive decreasing forces...")
    forces = [100.0, 95.0, 90.0, 85.0, 80.0, 75.0, 70.0, 65.0, 60.0, 55.0, 50.0]
    failure_triggered = False
    failure_layer = None
    
    for i, force in enumerate(forces, start=1):
        result = detector.check_layer(i, force)
        if result:
            failure_triggered = True
            failure_layer = i
            print(f"   Failure detected at layer {i}")
            break
    
    if failure_triggered and failure_layer == 11:
        print("   ✓ PASS: Failure correctly detected at layer 11 (baseline + 10 decreases)")
    else:
        print(f"   ✗ FAIL: Expected failure at layer 11, got: {failure_layer}")
        return False
    
    # Reset for next test
    detector.reset()
    
    # Test less than 10 consecutive decreases (should not trigger)
    print("\n1.3 Testing 9 consecutive decreases (should not trigger)...")
    forces = [100.0, 95.0, 90.0, 85.0, 80.0, 75.0, 70.0, 65.0, 60.0, 55.0]  # Only 9 decreases
    for i, force in enumerate(forces, start=1):
        result = detector.check_layer(i, force)
        if result:
            print(f"   ✗ FAIL: Unexpected failure at layer {i}")
            return False
    print("   ✓ PASS: No failure for 9 consecutive decreases")
    
    # Reset for next test
    detector.reset()
    
    # Test interrupted decrease sequence (should not trigger)
    print("\n1.4 Testing interrupted decrease sequence...")
    forces = [100.0, 95.0, 90.0, 85.0, 80.0, 85.0, 80.0, 75.0, 70.0, 65.0, 60.0]  # Interrupted at position 5
    for i, force in enumerate(forces, start=1):
        result = detector.check_layer(i, force)
        if result:
            print(f"   ✗ FAIL: Unexpected failure at layer {i}")
            return False
    print("   ✓ PASS: No failure for interrupted sequence")
    
    print("\n" + "="*60)
    print("PrintFailureDetector: ALL TESTS PASSED ✓")
    print("="*60)
    return True


def test_experimental_conditions_window():
    """Test ExperimentalConditionsWindow CSV and folder operations."""
    print("\n" + "="*60)
    print("TEST 2: ExperimentalConditionsWindow File Operations")
    print("="*60)
    
    from support_modules.ExperimentalConditionsWindow import ExperimentalConditionsWindow
    import tkinter as tk
    
    # Create a temporary directory for testing
    temp_dir = tempfile.mkdtemp(prefix="prince_test_")
    print(f"\nUsing temp directory: {temp_dir}")
    
    try:
        # Create test print directory
        test_print_dir = os.path.join(temp_dir, "Print 1")
        os.makedirs(test_print_dir)
        print(f"Created test print directory: {test_print_dir}")
        
        # Create a hidden root window for testing
        print("\n2.1 Testing window instantiation...")
        root = tk.Tk()
        root.withdraw()  # Hide the root window
        
        window = ExperimentalConditionsWindow(parent_window=root)
        window.window.withdraw()  # Hide the conditions window
        print("   ✓ PASS: Window created successfully")
        
        # Test CSV creation
        print("\n2.2 Testing CSV creation...")
        window.start_new_print(test_print_dir)
        csv_path = os.path.join(test_print_dir, "experimental_conditions.csv")
        
        if os.path.exists(csv_path):
            print(f"   ✓ PASS: CSV created at {csv_path}")
            
            # Read and verify CSV header
            with open(csv_path, 'r') as f:
                content = f.read()
                lines = content.strip().split('\n')
                
                if len(lines) < 2:
                    print(f"   ✗ FAIL: CSV should have at least header + 1 data row, got {len(lines)} lines")
                    print(f"   Content: {content}")
                    return False
                
                header = lines[0]
                expected_cols = ["Print_Date_Time", "User", "Printer", "Membrane_Type", "TEMPO_Pattern", 
                               "Oil", "Fluid_Type", "Fluid_Gap_mm", "Tank", "Resin", "Build_Platform", 
                               "Print_Status"]
                if all(col in header for col in expected_cols):
                    print("   ✓ PASS: CSV header contains all required columns")
                else:
                    print(f"   ✗ FAIL: CSV header missing columns")
                    print(f"   Header: {header}")
                    print(f"   Expected: {expected_cols}")
                    return False
        else:
            print("   ✗ FAIL: CSV not created")
            return False
        
        # Test layer force updates
        print("\n2.3 Testing layer force updates...")
        window.update_layer_force(1, 10.0)
        window.update_layer_force(2, 11.0)
        window.update_layer_force(3, 12.0)
        print("   ✓ PASS: Layer force updates accepted")
        
        # Test folder renaming - Complete
        print("\n2.4 Testing folder rename: Complete...")
        window.end_print(success=True)
        expected_complete_name = "Print 1 - Complete"
        expected_complete_path = os.path.join(temp_dir, expected_complete_name)
        
        if os.path.exists(expected_complete_path):
            print(f"   ✓ PASS: Folder renamed to '{expected_complete_name}'")
        else:
            print(f"   ✗ FAIL: Expected folder '{expected_complete_name}' not found")
            print(f"   Current contents of {temp_dir}:")
            for item in os.listdir(temp_dir):
                print(f"      - {item}")
            return False
        
        # Test folder renaming - Stopped
        print("\n2.5 Testing folder rename: Stopped...")
        test_print_dir_2 = os.path.join(temp_dir, "Print 2")
        os.makedirs(test_print_dir_2)
        window.start_new_print(test_print_dir_2)
        window.end_print(success=False)
        expected_stopped_name = "Print 2 - Stopped"
        expected_stopped_path = os.path.join(temp_dir, expected_stopped_name)
        
        if os.path.exists(expected_stopped_path):
            print(f"   ✓ PASS: Folder renamed to '{expected_stopped_name}'")
        else:
            print(f"   ✗ FAIL: Expected folder '{expected_stopped_name}' not found")
            return False
        
        # Test folder renaming - Possible Failure
        print("\n2.6 Testing folder rename: Possible Failure...")
        test_print_dir_3 = os.path.join(temp_dir, "Print 3")
        os.makedirs(test_print_dir_3)
        window.start_new_print(test_print_dir_3)
        
        # Simulate failure detection
        forces = [100.0, 95.0, 90.0, 85.0, 80.0, 75.0, 70.0, 65.0, 60.0, 55.0, 50.0]
        for i, force in enumerate(forces, start=1):
            window.update_layer_force(i, force)
        
        window.end_print(success=True)
        expected_failure_name = "Print 3 - Possible Failure"
        expected_failure_path = os.path.join(temp_dir, expected_failure_name)
        
        if os.path.exists(expected_failure_path):
            print(f"   ✓ PASS: Folder renamed to '{expected_failure_name}'")
        else:
            print(f"   ✗ FAIL: Expected folder '{expected_failure_name}' not found")
            return False
        
        # Cleanup
        try:
            window.window.destroy()
            root.destroy()
        except:
            pass
        
        print("\n" + "="*60)
        print("ExperimentalConditionsWindow: ALL TESTS PASSED ✓")
        print("="*60)
        return True
        
    finally:
        # Clean up temp directory
        try:
            shutil.rmtree(temp_dir)
            print(f"\nCleaned up temp directory: {temp_dir}")
        except Exception as e:
            print(f"\nWarning: Could not clean up temp directory: {e}")


def test_imports():
    """Test that all required modules import correctly."""
    print("\n" + "="*60)
    print("TEST 3: Module Import Tests")
    print("="*60)
    
    modules_to_test = [
        ('support_modules.ExperimentalConditionsWindow', 'ExperimentalConditionsWindow'),
        ('support_modules.ExperimentalConditionsWindow', 'PrintFailureDetector'),
        ('support_modules.PeakForceLogger', 'PeakForceLogger'),
        ('support_modules.SensorDataWindow', 'SensorDataWindow'),
    ]
    
    all_passed = True
    for module_name, class_name in modules_to_test:
        try:
            module = __import__(module_name, fromlist=[class_name])
            getattr(module, class_name)
            print(f"   ✓ PASS: {module_name}.{class_name}")
        except Exception as e:
            print(f"   ✗ FAIL: {module_name}.{class_name} - {e}")
            all_passed = False
    
    if all_passed:
        print("\n" + "="*60)
        print("Module Imports: ALL TESTS PASSED ✓")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("Module Imports: SOME TESTS FAILED ✗")
        print("="*60)
    
    return all_passed


def main():
    """Run all tests."""
    print("\n" + "#"*60)
    print("# Experimental Conditions System - Integration Test Suite")
    print("#"*60)
    
    results = {
        "Module Imports": test_imports(),
        "PrintFailureDetector": test_print_failure_detector(),
        "ExperimentalConditionsWindow": test_experimental_conditions_window()
    }
    
    print("\n" + "#"*60)
    print("# FINAL TEST RESULTS")
    print("#"*60)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("#"*60)
    
    if all_passed:
        print("\n🎉 ALL TESTS PASSED! System is ready for production use.")
        return 0
    else:
        print("\n⚠️  SOME TESTS FAILED. Please review errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
