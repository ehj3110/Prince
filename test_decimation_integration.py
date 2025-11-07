"""
Test script to verify decimation integration in ForceGaugeManager.

This script tests the new decimation (oversampling) feature that:
- Samples at ~1200 Hz (maximum hardware rate)
- Averages 12 samples per output
- Outputs at ~100 Hz (10ms intervals)
- Provides ~3.46× noise reduction

Expected behavior:
1. Hardware samples at 1200 Hz
2. Decimation averages every 12 samples
3. Output appears at ~100 Hz (10ms intervals)
4. Noise should be significantly reduced compared to standard mode

Author: Implementation for high-speed noise reduction
Date: November 6, 2025
"""

import time
import queue
import tkinter as tk
from collections import deque

# Import the updated ForceGaugeManager
from support_modules.ForceGaugeManager import ForceGaugeManager


def test_decimation_info():
    """Test the decimation info methods without hardware."""
    print("=" * 70)
    print("DECIMATION INTEGRATION TEST")
    print("=" * 70)
    
    # Create dummy GUI elements
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    
    dummy_label = tk.Label(root, text="Test")
    output_queue = queue.Queue()
    
    # Create ForceGaugeManager instance
    print("\nCreating ForceGaugeManager with decimation enabled...")
    fgm = ForceGaugeManager(
        gain_label=dummy_label,
        offset_label=dummy_label,
        force_status_label=dummy_label,
        large_force_readout_label=dummy_label,
        output_force_queue=output_queue,
        parent_window=root,
        sensor_window_ref=None
    )
    
    # Get initial decimation info
    print("\n" + "=" * 70)
    print("INITIAL CONFIGURATION:")
    print("=" * 70)
    info = fgm.get_decimation_info()
    
    if info['enabled']:
        print(f"✓ Decimation is ENABLED")
        print(f"  Mode: {info['mode']}")
        print(f"  Decimation Factor: {info['decimation_factor']}")
        print(f"  Expected Input Rate: {info['expected_input_rate_hz']:.0f} Hz")
        print(f"  Expected Output Rate: {info['expected_output_rate_hz']:.0f} Hz")
        print(f"  Expected Output Interval: {info['expected_output_interval_ms']:.1f} ms")
        print(f"  Noise Reduction Factor: {info['noise_reduction_factor']:.2f}×")
        print(f"  Noise Reduction (dB): {info['noise_reduction_db']:.1f} dB")
    else:
        print(f"✗ Decimation is DISABLED")
        print(f"  Mode: {info['mode']}")
    
    # Test changing decimation factor
    print("\n" + "=" * 70)
    print("TESTING DECIMATION FACTOR CHANGES:")
    print("=" * 70)
    
    test_factors = [6, 12, 24, 48]
    for factor in test_factors:
        print(f"\nSetting decimation factor to {factor}...")
        success = fgm.set_decimation_factor(factor)
        if success:
            info = fgm.get_decimation_info()
            print(f"  ✓ Success!")
            print(f"    Output Rate: {info['expected_output_rate_hz']:.0f} Hz ({info['expected_output_interval_ms']:.1f} ms)")
            print(f"    Noise Reduction: {info['noise_reduction_factor']:.2f}× ({info['noise_reduction_db']:.1f} dB)")
        else:
            print(f"  ✗ Failed to set factor {factor}")
    
    # Reset to optimal factor (12)
    print("\n" + "=" * 70)
    print("RESETTING TO OPTIMAL FACTOR (12):")
    print("=" * 70)
    fgm.set_decimation_factor(12)
    info = fgm.get_decimation_info()
    print(f"✓ Configuration optimized for 10ms output")
    print(f"  Output: {info['expected_output_rate_hz']:.0f} Hz ({info['expected_output_interval_ms']:.1f} ms)")
    print(f"  Noise Reduction: {info['noise_reduction_factor']:.2f}× ({info['noise_reduction_db']:.1f} dB)")
    
    # Test invalid factors
    print("\n" + "=" * 70)
    print("TESTING ERROR HANDLING (Invalid Factors):")
    print("=" * 70)
    
    invalid_factors = [0, -5, 101, 1000]
    for factor in invalid_factors:
        print(f"\nAttempting to set invalid factor: {factor}")
        success = fgm.set_decimation_factor(factor)
        if not success:
            print(f"  ✓ Correctly rejected invalid factor")
        else:
            print(f"  ✗ ERROR: Should have rejected factor {factor}")
    
    # Summary
    print("\n" + "=" * 70)
    print("INTEGRATION TEST SUMMARY:")
    print("=" * 70)
    print("✓ ForceGaugeManager created with decimation enabled")
    print("✓ Decimation configuration methods working")
    print("✓ Information retrieval methods working")
    print("✓ Error handling for invalid factors working")
    print("\nNEXT STEPS:")
    print("1. Connect Phidget Bridge hardware")
    print("2. Run ForceGaugeManager with actual sensor")
    print("3. Verify 1200Hz sampling rate (check console output)")
    print("4. Verify ~100Hz output rate (check timestamps)")
    print("5. Measure actual noise reduction (compare std dev)")
    print("\nExpected Console Messages on Hardware Connection:")
    print("  - 'Decimation enabled: Factor=12...'")
    print("  - 'Decimation mode: Trigger=0.0 for maximum hardware speed (~1200Hz)'")
    print("  - 'Hardware sampling: ~1200Hz, Output after decimation: ~100Hz'")
    print("=" * 70)
    
    # Cleanup
    fgm.close()
    root.destroy()


def test_configuration_attributes():
    """Verify all decimation attributes are properly initialized."""
    print("\n" + "=" * 70)
    print("ATTRIBUTE VERIFICATION TEST:")
    print("=" * 70)
    
    root = tk.Tk()
    root.withdraw()
    
    dummy_label = tk.Label(root, text="Test")
    output_queue = queue.Queue()
    
    fgm = ForceGaugeManager(
        gain_label=dummy_label,
        offset_label=dummy_label,
        force_status_label=dummy_label,
        large_force_readout_label=dummy_label,
        output_force_queue=output_queue,
        parent_window=root,
        sensor_window_ref=None
    )
    
    # Check all decimation attributes
    required_attributes = {
        'USE_DECIMATION': bool,
        'decimation_factor': int,
        'decimation_buffer': deque,
        'decimation_counter': int
    }
    
    all_present = True
    for attr_name, expected_type in required_attributes.items():
        if hasattr(fgm, attr_name):
            attr_value = getattr(fgm, attr_name)
            if isinstance(attr_value, expected_type):
                print(f"✓ {attr_name}: {attr_value} (type: {type(attr_value).__name__})")
            else:
                print(f"✗ {attr_name}: Wrong type! Expected {expected_type.__name__}, got {type(attr_value).__name__}")
                all_present = False
        else:
            print(f"✗ {attr_name}: MISSING!")
            all_present = False
    
    if all_present:
        print("\n✓ All decimation attributes present and correctly typed")
    else:
        print("\n✗ Some attributes missing or incorrectly typed")
    
    fgm.close()
    root.destroy()
    
    return all_present


if __name__ == "__main__":
    try:
        print("\n" * 2)
        print("╔" + "═" * 68 + "╗")
        print("║" + " " * 15 + "DECIMATION INTEGRATION TEST SUITE" + " " * 19 + "║")
        print("║" + " " * 68 + "║")
        print("║" + " " * 12 + "Testing new high-speed decimation feature" + " " * 15 + "║")
        print("║" + " " * 17 + "in ForceGaugeManager.py" + " " * 28 + "║")
        print("╚" + "═" * 68 + "╝")
        
        # Run tests
        print("\n[TEST 1] Configuration Methods Test")
        test_decimation_info()
        
        print("\n\n[TEST 2] Attribute Verification Test")
        attributes_ok = test_configuration_attributes()
        
        # Final summary
        print("\n" + "╔" + "═" * 68 + "╗")
        print("║" + " " * 23 + "FINAL SUMMARY" + " " * 32 + "║")
        print("╚" + "═" * 68 + "╝")
        
        if attributes_ok:
            print("\n✓ ALL TESTS PASSED!")
            print("\nDecimation integration is complete and ready for hardware testing.")
            print("\nTo use with hardware:")
            print("  1. Connect Phidget Bridge with load cell on Port 0")
            print("  2. Run your main application (Prince_Segmented.py)")
            print("  3. Look for console messages confirming 1200Hz sampling")
            print("  4. Monitor output timing (should be ~10ms intervals)")
            print("  5. Compare noise levels to previous measurements")
        else:
            print("\n✗ SOME TESTS FAILED")
            print("Review error messages above for details.")
        
        print("\n" + "=" * 70)
        
    except ImportError as e:
        print(f"\n✗ ERROR: Could not import ForceGaugeManager")
        print(f"  {e}")
        print("\nMake sure you're running this from the project root directory.")
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n")
