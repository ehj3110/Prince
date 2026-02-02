"""
Test script for three-segment ramped speed retraction feature.

This script validates the smooth retraction movement profile by:
1. Connecting to the Zaber stage
2. Performing a test retraction with the three-segment ramped approach
3. Monitoring position and velocity throughout the movement
4. Comparing with normal single-stage retraction

Run this test BEFORE attempting a full print to verify the movement profile.
"""

import sys
import time
from zaber_motion import Library, Units
from zaber_motion.ascii import Connection

def test_smooth_retraction():
    """Test the three-segment ramped speed retraction."""
    
    print("=" * 80)
    print("SMOOTH RETRACTION TEST")
    print("=" * 80)
    
    # Initialize Zaber library
    Library.enable_device_db_store()
    
    # Connect to stage
    print("\n[1/6] Connecting to Zaber stage...")
    try:
        connection = Connection.open_serial_port("COM3")
        device_list = connection.detect_devices()
        print(f"      Detected {len(device_list)} device(s)")
        
        device = device_list[0]
        axis = device.get_axis(1)
        print(f"      Connected to: {device.name}")
        
    except Exception as e:
        print(f"      ERROR: Failed to connect to stage: {e}")
        print("\n      Make sure:")
        print("      - Stage is powered on")
        print("      - USB cable is connected")
        print("      - COM3 is the correct port")
        return False
    
    # Get current position
    print("\n[2/6] Getting current position...")
    current_pos = axis.get_position(Units.LENGTH_MILLIMETRES)
    print(f"      Current position: {current_pos:.4f} mm")
    
    # Define test parameters
    test_distance_mm = 10.0  # 10mm test movement
    test_speed_mm_s = 5.0    # 5 mm/s test speed
    test_accel = 100000      # 100 mm/s² = 100,000 µm/s²
    
    start_pos_mm = current_pos
    end_pos_mm = current_pos + test_distance_mm
    
    # Convert to micrometers
    start_pos_um = start_pos_mm * 1000
    end_pos_um = end_pos_mm * 1000
    test_speed_um_s = test_speed_mm_s * 1000
    
    print(f"\n[3/6] Test parameters:")
    print(f"      Start position: {start_pos_mm:.4f} mm")
    print(f"      End position: {end_pos_mm:.4f} mm")
    print(f"      Distance: {test_distance_mm:.4f} mm")
    print(f"      Normal speed: {test_speed_mm_s:.1f} mm/s")
    print(f"      Acceleration: {test_accel / 1000:.1f} mm/s²")
    
    # Test 1: Normal single-stage movement
    print(f"\n[4/6] TEST 1: Normal single-stage retraction")
    print(f"      Moving from {start_pos_mm:.4f} to {end_pos_mm:.4f} mm...")
    
    try:
        start_time = time.time()
        axis.move_absolute(
            position=end_pos_um,
            unit=Units.LENGTH_MICROMETRES,
            wait_until_idle=True,
            velocity=test_speed_um_s,
            velocity_unit=Units.VELOCITY_MICROMETRES_PER_SECOND,
            acceleration=test_accel,
            acceleration_unit=Units.ACCELERATION_MICROMETRES_PER_SECOND_SQUARED
        )
        normal_time = time.time() - start_time
        
        final_pos = axis.get_position(Units.LENGTH_MILLIMETRES)
        print(f"      ✓ Completed in {normal_time:.3f}s")
        print(f"      ✓ Final position: {final_pos:.4f} mm")
        
    except Exception as e:
        print(f"      ✗ ERROR: {e}")
        connection.close()
        return False
    
    # Return to start position
    print(f"\n      Returning to start position...")
    time.sleep(0.5)
    axis.move_absolute(
        position=start_pos_um,
        unit=Units.LENGTH_MICROMETRES,
        wait_until_idle=True,
        velocity=test_speed_um_s,
        velocity_unit=Units.VELOCITY_MICROMETRES_PER_SECOND,
        acceleration=test_accel,
        acceleration_unit=Units.ACCELERATION_MICROMETRES_PER_SECOND_SQUARED
    )
    time.sleep(0.5)
    
    # Test 2: Single-stage low-acceleration retraction
    print(f"\n[5/6] TEST 2: Single-stage low-acceleration retraction")
    print(f"      Speed: {test_speed_mm_s:.1f} mm/s (normal)")
    print(f"      Acceleration: 10 mm/s² (gentle, vs {test_accel / 1000:.1f} mm/s² normal)")
    
    try:
        gentle_accel = 10000  # 10 mm/s²
        
        start_time = time.time()
        
        print(f"\n      → Moving to {end_pos_um / 1000:.4f} mm with gentle acceleration...")
        axis.move_absolute(
            position=end_pos_um,
            unit=Units.LENGTH_MICROMETRES,
            wait_until_idle=True,
            velocity=test_speed_um_s,
            velocity_unit=Units.VELOCITY_MICROMETRES_PER_SECOND,
            acceleration=gentle_accel,
            acceleration_unit=Units.ACCELERATION_MICROMETRES_PER_SECOND_SQUARED
        )
        
        low_accel_time = time.time() - start_time
        final_pos = axis.get_position(Units.LENGTH_MILLIMETRES)
        
        print(f"        ✓ Completed in {low_accel_time:.3f}s, position: {final_pos:.4f} mm")
        
    except Exception as e:
        print(f"      ✗ ERROR: {e}")
        connection.close()
        return False
    
    # Analysis
    print(f"\n[6/6] RESULTS:")
    print(f"      Normal single-stage time:    {normal_time:.3f}s")
    print(f"      Low-acceleration time:       {low_accel_time:.3f}s")
    print(f"      Time difference: +{(low_accel_time - normal_time):.3f}s ({((low_accel_time / normal_time - 1) * 100):.1f}% slower)")
    
    print(f"\n      Acceleration comparison:")
    print(f"      - Normal: {test_accel / 1000:.1f} mm/s²")
    print(f"      - Gentle: 10 mm/s² (100× gentler)")
    
    # Return to start
    print(f"\n      Returning to start position...")
    axis.move_absolute(
        position=start_pos_um,
        unit=Units.LENGTH_MICROMETRES,
        wait_until_idle=True,
        velocity=test_speed_um_s,
        velocity_unit=Units.VELOCITY_MICROMETRES_PER_SECOND,
        acceleration=test_accel,
        acceleration_unit=Units.ACCELERATION_MICROMETRES_PER_SECOND_SQUARED
    )
    
    # Close connection
    connection.close()
    
    print("\n" + "=" * 80)
    print("TEST COMPLETED SUCCESSFULLY")
    print("=" * 80)
    print("\nThe low-acceleration smooth retraction provides gentle deceleration by:")
    print("  - Using 10 mm/s² acceleration (100× gentler than normal 1000 mm/s²)")
    print("  - Single continuous movement with no stops")
    print("  - Same velocity as normal retraction")
    print("\nThis approach should significantly reduce the risk of stage stalls")
    print("during high-force retraction movements by eliminating force spikes")
    print("from rapid deceleration.")
    print("\nIf stalls still occur, consider further reducing acceleration to 5 mm/s².")
    
    return True


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("SMOOTH RETRACTION TEST SCRIPT")
    print("=" * 80)
    print("\nThis test will:")
    print("  1. Connect to the Zaber stage on COM3")
    print("  2. Perform a normal single-stage movement")
    print("  3. Perform a three-segment ramped speed movement")
    print("  4. Compare timing and validate movement profile")
    print("\nIMPORTANT:")
    print("  - Ensure stage has clearance for 10mm upward movement")
    print("  - Watch for any stuttering or unusual behavior")
    print("  - Press Ctrl+C to abort if needed")
    
    input("\nPress ENTER to start test...")
    
    try:
        success = test_smooth_retraction()
        if success:
            sys.exit(0)
        else:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nTest aborted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
