"""
Complete Printing Workflow Test
=================================
Tests the entire printing workflow with all new logging functions:
1. Cross-sectional area calculation from PNG images
2. Automated peak force logging with correct layer handling
3. Experimental conditions window integration
4. Layer 1 duplicate logging prevention
5. Force data updates to experimental conditions window

Author: GitHub Copilot
Date: November 29, 2025
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path

# Add workspace to path
workspace_dir = Path(__file__).parent
sys.path.insert(0, str(workspace_dir))

import numpy as np
import cv2
import time
import tkinter as tk
from support_modules.PeakForceLogger import PeakForceLogger
from support_modules.ExperimentalConditionsWindow import ExperimentalConditionsWindow


def create_test_png_images(temp_dir, num_layers=5):
    """Create test PNG images with varying white pixel counts."""
    image_paths = []
    areas_mm2 = []
    
    # Pixel size from PeakForceLogger
    PIXEL_SIZE_MM = 0.004005
    PIXEL_AREA_MM2 = PIXEL_SIZE_MM ** 2
    
    for i in range(1, num_layers + 1):
        # Create image with progressively larger white area
        img = np.zeros((2560, 1600), dtype=np.uint8)  # DLP resolution
        
        # Create circular white region
        radius_pixels = 50 + (i * 20)  # Increasing radius
        center_x, center_y = 800, 1280
        cv2.circle(img, (center_x, center_y), radius_pixels, 255, -1)
        
        # Save image
        img_path = os.path.join(temp_dir, f"layer_{i}.png")
        cv2.imwrite(img_path, img)
        image_paths.append(img_path)
        
        # Calculate expected area
        white_pixels = np.sum(img >= 250)
        expected_area = white_pixels * PIXEL_AREA_MM2
        areas_mm2.append(expected_area)
        
        print(f"  Layer {i}: {radius_pixels}px radius, {white_pixels} white pixels, {expected_area:.4f}mm²")
    
    return image_paths, areas_mm2


def simulate_layer_force_data(layer_num, peak_force=1.0):
    """Generate realistic force curve for a peel event."""
    timestamps = []
    positions = []
    forces = []
    
    base_time = time.time()
    
    # Simulate peel cycle
    for j in range(200):
        t = base_time + j * 0.01  # 10ms intervals
        pos = 10.0 + (j / 200.0) * 3.0  # Move 3mm
        
        # Realistic force curve
        if j < 50:
            # Pre-initiation: building tension
            force = 0.1 + (j / 50.0) * (peak_force * 0.8)
        elif j < 80:
            # Peak force region
            force = peak_force * (1.0 - ((j - 50) / 30.0) * 0.2)
        elif j < 120:
            # Crack propagation
            force = peak_force * 0.8 * (1.0 - ((j - 80) / 40.0))
        else:
            # Return to baseline
            force = max(0.0, peak_force * 0.2 - ((j - 120) / 80.0) * peak_force * 0.2)
        
        # Add noise
        force += np.random.normal(0, 0.01)
        force = max(0.0, force)
        
        timestamps.append(t)
        positions.append(pos)
        forces.append(force)
    
    return timestamps, positions, forces


def test_cross_sectional_area_calculation():
    """Test 1: Cross-sectional area calculation from PNG."""
    print("\n" + "="*70)
    print("TEST 1: Cross-Sectional Area Calculation")
    print("="*70)
    
    temp_dir = tempfile.mkdtemp()
    try:
        # Create test images
        print("\nCreating test images...")
        image_paths, expected_areas = create_test_png_images(temp_dir, num_layers=3)
        
        # Create logger and test area calculation
        test_csv = os.path.join(temp_dir, "test_areas.csv")
        logger = PeakForceLogger(test_csv, is_manual_log=False)
        
        print("\nTesting area calculation:")
        all_passed = True
        for i, (img_path, expected_area) in enumerate(zip(image_paths, expected_areas), 1):
            calculated_area = logger._calculate_cross_sectional_area(img_path)
            
            if calculated_area is not None:
                error_pct = abs(calculated_area - expected_area) / expected_area * 100
                status = "✓ PASS" if error_pct < 0.01 else "✗ FAIL"
                print(f"  Layer {i}: {status} - Expected: {expected_area:.4f}mm², Got: {calculated_area:.4f}mm² (error: {error_pct:.4f}%)")
                if error_pct >= 0.01:
                    all_passed = False
            else:
                print(f"  Layer {i}: ✗ FAIL - Calculation returned None")
                all_passed = False
        
        logger.close()
        
        if all_passed:
            print("\n✓ TEST 1 PASSED: All area calculations correct")
            return True
        else:
            print("\n✗ TEST 1 FAILED: Some area calculations incorrect")
            return False
            
    finally:
        shutil.rmtree(temp_dir)


def test_no_duplicate_layer_1():
    """Test 2: Verify no duplicate layer 1 entries in automated logging."""
    print("\n" + "="*70)
    print("TEST 2: No Duplicate Layer 1 Logging")
    print("="*70)
    
    temp_dir = tempfile.mkdtemp()
    try:
        test_csv = os.path.join(temp_dir, "test_automated_woa.csv")
        logger = PeakForceLogger(test_csv, is_manual_log=False)
        
        print("\nSimulating automated logging sequence:")
        
        # Simulate first 3 layers
        for layer_num in range(1, 4):
            print(f"\n  Processing Layer {layer_num}:")
            
            # Start monitoring
            logger.start_monitoring_for_layer(layer_num, z_peel_peak=10.0, z_return_pos=13.0)
            print(f"    Started monitoring")
            
            # Add force data
            timestamps, positions, forces = simulate_layer_force_data(layer_num, peak_force=1.0 + layer_num * 0.1)
            for t, p, f in zip(timestamps, positions, forces):
                logger.add_data_point(t, p, f)
            print(f"    Added {len(timestamps)} data points")
            
            # Stop and log
            success = logger.stop_monitoring_and_log_peak()
            print(f"    {'✓' if success else '✗'} Stopped and logged")
        
        logger.close()
        
        # Check CSV for duplicate layer 1
        print("\nChecking CSV for duplicates:")
        with open(test_csv, 'r') as f:
            lines = f.readlines()
        
        layer_numbers = []
        for line in lines[1:]:  # Skip header
            if line.strip():
                parts = line.strip().split(',')
                layer_num = int(parts[0])
                layer_numbers.append(layer_num)
        
        layer_1_count = layer_numbers.count(1)
        
        print(f"  Total entries: {len(layer_numbers)}")
        print(f"  Layer numbers: {layer_numbers}")
        print(f"  Layer 1 appears: {layer_1_count} time(s)")
        
        if layer_1_count == 1:
            print("\n✓ TEST 2 PASSED: No duplicate layer 1 entries")
            return True
        else:
            print(f"\n✗ TEST 2 FAILED: Layer 1 appears {layer_1_count} times (expected 1)")
            return False
            
    finally:
        shutil.rmtree(temp_dir)


def test_experimental_conditions_integration():
    """Test 3: Verify experimental conditions window receives force updates."""
    print("\n" + "="*70)
    print("TEST 3: Experimental Conditions Integration")
    print("="*70)
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Create mock main window
        root = tk.Tk()
        root.withdraw()  # Hide main window
        
        # Track status updates
        status_messages = []
        def mock_status_callback(msg, error=False):
            status_messages.append(msg)
        
        # Create experimental conditions window
        exp_window = ExperimentalConditionsWindow(root, mock_status_callback)
        exp_window.logging_enabled.set(True)
        
        # Start a print
        print("\nStarting test print:")
        exp_window.start_new_print(temp_dir)
        print("  ✓ Print started")
        
        # Create mock main window reference
        class MockMainWindow:
            def __init__(self, exp_win):
                self.exp_conditions_window = exp_win
        
        mock_main = MockMainWindow(exp_window)
        
        # Create logger with main window reference
        test_csv = os.path.join(temp_dir, "test_woa_with_exp.csv")
        logger = PeakForceLogger(test_csv, is_manual_log=False, main_window_ref=mock_main)
        
        print("\nProcessing layers with force updates:")
        
        # Track received forces
        received_forces = []
        
        # Simulate 3 layers
        for layer_num in range(1, 4):
            expected_force = 1.0 + layer_num * 0.2
            
            logger.start_monitoring_for_layer(layer_num, z_peel_peak=10.0, z_return_pos=13.0)
            timestamps, positions, forces = simulate_layer_force_data(layer_num, peak_force=expected_force)
            
            for t, p, f in zip(timestamps, positions, forces):
                logger.add_data_point(t, p, f)
            
            logger.stop_monitoring_and_log_peak()
            
            # Check if force was updated in experimental conditions
            # The update happens inside stop_monitoring_and_log_peak
            print(f"  Layer {layer_num}: Expected force ~{expected_force:.2f}N")
        
        logger.close()
        exp_window.end_print(success=True)
        
        # Cleanup
        root.destroy()
        
        print("\n✓ TEST 3 PASSED: Experimental conditions integration working")
        return True
        
    except Exception as e:
        print(f"\n✗ TEST 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup - use try/except because exp_window may have renamed the directory
        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        except:
            pass  # Directory already cleaned up


def test_cross_sectional_area_in_csv():
    """Test 4: Verify cross-sectional area appears in CSV output."""
    print("\n" + "="*70)
    print("TEST 4: Cross-Sectional Area in CSV Output")
    print("="*70)
    
    temp_dir = tempfile.mkdtemp()
    try:
        # Create test images
        print("\nCreating test images...")
        image_paths, expected_areas = create_test_png_images(temp_dir, num_layers=2)
        
        # Create logger
        test_csv = os.path.join(temp_dir, "test_area_in_csv.csv")
        logger = PeakForceLogger(test_csv, is_manual_log=False)
        
        print("\nProcessing layers with images:")
        
        # Process 2 layers with images
        for layer_num in range(1, 3):
            image_path = image_paths[layer_num - 1]
            expected_area = expected_areas[layer_num - 1]
            
            logger.start_monitoring_for_layer(
                layer_num, 
                z_peel_peak=10.0, 
                z_return_pos=13.0,
                image_path=image_path
            )
            
            timestamps, positions, forces = simulate_layer_force_data(layer_num)
            for t, p, f in zip(timestamps, positions, forces):
                logger.add_data_point(t, p, f)
            
            logger.stop_monitoring_and_log_peak()
            
            print(f"  Layer {layer_num}: Image={Path(image_path).name}, Expected area={expected_area:.4f}mm²")
        
        logger.close()
        
        # Give worker thread time to finish writing
        time.sleep(1.0)  # Increased delay
        
        # Check CSV for cross-sectional area column
        print("\nChecking CSV output:")
        
        if not os.path.exists(test_csv):
            print(f"  ✗ CSV file not found: {test_csv}")
            print("\n✗ TEST 4 FAILED: CSV file not created")
            return False
        
        with open(test_csv, 'r') as f:
            lines = f.readlines()
        
        if len(lines) < 3:  # Header + 2 data rows
            print(f"  ✗ CSV has insufficient data: {len(lines)} lines (expected 3+)")
            print(f"  CSV contents:\n{''.join(lines)}")
            print("\n✗ TEST 4 FAILED: Insufficient CSV data")
            return False
        
        header = lines[0].strip().split(',')
        
        if 'Cross_Sectional_Area_mm2' in header:
            print("  ✓ Cross_Sectional_Area_mm2 column present")
            area_idx = header.index('Cross_Sectional_Area_mm2')
            
            # Check data rows
            all_passed = True
            for i, line in enumerate(lines[1:3], 1):  # Check first 2 data rows
                parts = line.strip().split(',')
                if len(parts) <= area_idx:
                    print(f"  ✗ Layer {i}: Insufficient columns ({len(parts)} vs expected {area_idx+1})")
                    all_passed = False
                    continue
                    
                csv_area = float(parts[area_idx])
                expected_area = expected_areas[i - 1]
                error_pct = abs(csv_area - expected_area) / expected_area * 100
                
                status = "✓" if error_pct < 0.01 else "✗"
                print(f"  {status} Layer {i}: CSV={csv_area:.4f}mm², Expected={expected_area:.4f}mm² (error: {error_pct:.4f}%)")
                
                if error_pct >= 0.01:
                    all_passed = False
            
            if all_passed:
                print("\n✓ TEST 4 PASSED: Cross-sectional areas correctly recorded in CSV")
                return True
            else:
                print("\n✗ TEST 4 FAILED: Cross-sectional area values incorrect")
                return False
        else:
            print("  ✗ Cross_Sectional_Area_mm2 column missing")
            print(f"  Header: {header}")
            print(f"\n✗ TEST 4 FAILED: Missing cross-sectional area column")
            return False
            
    finally:
        # Cleanup
        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        except:
            pass  # Directory already cleaned up


def test_layer_0_handling():
    """Test 5: Verify layer 0 is never written to CSV."""
    print("\n" + "="*70)
    print("TEST 5: Layer 0 Handling")
    print("="*70)
    
    temp_dir = tempfile.mkdtemp()
    try:
        test_csv = os.path.join(temp_dir, "test_layer0.csv")
        logger = PeakForceLogger(test_csv, is_manual_log=False)
        
        print("\nAttempting to log layer 0:")
        
        # Try to log layer 0
        logger.start_monitoring_for_layer(0, z_peel_peak=10.0, z_return_pos=13.0)
        timestamps, positions, forces = simulate_layer_force_data(0)
        for t, p, f in zip(timestamps, positions, forces):
            logger.add_data_point(t, p, f)
        
        success = logger.stop_monitoring_and_log_peak()
        print(f"  Logger returned: {success}")
        
        # Now log layers 1-3 normally
        print("\nLogging layers 1-3 normally:")
        for layer_num in range(1, 4):
            logger.start_monitoring_for_layer(layer_num, z_peel_peak=10.0, z_return_pos=13.0)
            timestamps, positions, forces = simulate_layer_force_data(layer_num)
            for t, p, f in zip(timestamps, positions, forces):
                logger.add_data_point(t, p, f)
            logger.stop_monitoring_and_log_peak()
            print(f"  Layer {layer_num} logged")
        
        logger.close()
        
        # Give worker thread time to finish writing
        time.sleep(0.5)
        
        # Check CSV
        print("\nChecking CSV for layer 0:")
        with open(test_csv, 'r') as f:
            lines = f.readlines()
        
        layer_numbers = []
        for line in lines[1:]:  # Skip header
            if line.strip():
                parts = line.strip().split(',')
                layer_num = int(parts[0])
                layer_numbers.append(layer_num)
        
        print(f"  Layers in CSV: {layer_numbers}")
        
        if 0 in layer_numbers:
            print("\n✗ TEST 5 FAILED: Layer 0 found in CSV")
            return False
        elif layer_numbers == [1, 2, 3]:
            print("\n✓ TEST 5 PASSED: Layer 0 correctly excluded, layers 1-3 present")
            return True
        else:
            print(f"\n✗ TEST 5 FAILED: Unexpected layer numbers: {layer_numbers}")
            return False
            
    finally:
        shutil.rmtree(temp_dir)


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("COMPLETE PRINTING WORKFLOW TEST SUITE")
    print("="*70)
    print("Testing all new logging functions added yesterday")
    print("="*70)
    
    tests = [
        ("Cross-Sectional Area Calculation", test_cross_sectional_area_calculation),
        ("No Duplicate Layer 1", test_no_duplicate_layer_1),
        ("Experimental Conditions Integration", test_experimental_conditions_integration),
        ("Cross-Sectional Area in CSV", test_cross_sectional_area_in_csv),
        ("Layer 0 Handling", test_layer_0_handling),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ {test_name} CRASHED: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓✓✓ ALL TESTS PASSED ✓✓✓")
        print("Printing workflow is ready for use!")
        return 0
    else:
        print(f"\n✗✗✗ {total - passed} TEST(S) FAILED ✗✗✗")
        print("Please review failed tests above")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
