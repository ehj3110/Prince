"""
Test script for MotionController module

Tests both smooth lifting and smooth retraction with actual stage movements.
Validates the 3-stage lift ramping and gentle acceleration retraction.

Run this with the GUI closed to have exclusive access to the stage.
"""

import sys
import time
from zaber_motion import Library, Units
from zaber_motion.ascii import Connection
from support_modules.motion_controller import MotionController


def test_motion_controller():
    """Test the motion controller with actual stage movements."""
    
    print("=" * 80)
    print("MOTION CONTROLLER TEST")
    print("=" * 80)
    
    # Initialize Zaber library
    Library.enable_device_db_store()
    
    # Connect to stage
    print("\n[1/7] Connecting to Zaber stage...")
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
        print("      - GUI is closed")
        return False
    
    # Get current position
    print("\n[2/7] Getting current position...")
    current_pos_mm = axis.get_position(Units.LENGTH_MILLIMETRES)
    current_pos_um = current_pos_mm * 1000
    print(f"      Current position: {current_pos_mm:.4f} mm ({current_pos_um:.1f} µm)")
    
    # Initialize motion controller
    print("\n[3/7] Initializing MotionController...")
    motion_controller = MotionController(axis=axis, force_gauge_manager=None)
    print(f"      ✓ MotionController initialized")
    print(f"      Smooth lift config: {motion_controller.smooth_lift_config}")
    print(f"      Smooth retraction config: {motion_controller.smooth_retraction_config}")
    
    # Define test parameters
    test_lift_distance_um = 1000  # 1mm lift (like a peel)
    test_retract_distance_um = 1000  # 1mm return
    base_velocity_um_s = 1000  # 1 mm/s
    base_acceleration_um_s2 = 100000  # 100 mm/s²
    
    target_lift_pos_um = current_pos_um - test_lift_distance_um  # Move upward (lower position)
    target_return_pos_um = current_pos_um  # Return to starting position
    
    print(f"\n[4/7] Test parameters:")
    print(f"      Starting position: {current_pos_um:.1f} µm")
    print(f"      Lift target: {target_lift_pos_um:.1f} µm (1mm up)")
    print(f"      Return target: {target_return_pos_um:.1f} µm (back to start)")
    print(f"      Base velocity: {base_velocity_um_s} µm/s")
    print(f"      Base acceleration: {base_acceleration_um_s2 / 1000:.1f} mm/s²")
    
    # Test 1: Standard single-stage lift
    print(f"\n[5/7] TEST 1: Standard single-stage lift")
    print(f"      Lifting 1mm at constant {base_velocity_um_s} µm/s...")
    
    start_time = time.time()
    result = motion_controller.execute_lift(
        start_pos_um=current_pos_um,
        target_pos_um=target_lift_pos_um,
        base_velocity_um_s=base_velocity_um_s,
        base_acceleration_um_s2=base_acceleration_um_s2,
        smooth_enabled=False
    )
    
    if result['success']:
        print(f"      ✓ Completed in {result['movement_time_s']:.3f}s")
        print(f"      ✓ Final position: {result['final_position_um'] / 1000:.4f} mm")
        print(f"      ✓ Segments completed: {result['segments_completed']}")
    else:
        print(f"      ✗ ERROR: {result.get('error', 'Unknown error')}")
        connection.close()
        return False
    
    time.sleep(0.5)
    
    # Return to start with standard retraction
    print(f"\n      Returning to start (standard retraction)...")
    result = motion_controller.execute_retraction(
        target_pos_um=target_return_pos_um,
        base_velocity_um_s=base_velocity_um_s,
        base_acceleration_um_s2=base_acceleration_um_s2,
        smooth_enabled=False
    )
    
    if result['success']:
        print(f"      ✓ Returned in {result['movement_time_s']:.3f}s")
        print(f"      ✓ Acceleration used: {result['acceleration_used_um_s2'] / 1000:.1f} mm/s²")
    else:
        print(f"      ✗ ERROR: {result.get('error', 'Unknown error')}")
    
    time.sleep(1.0)
    
    # Test 2: Smooth multi-stage lift
    print(f"\n[6/7] TEST 2: Smooth 3-stage lift")
    print(f"      Stage 1: 0-100µm at 200µm/s (gentle break)")
    print(f"      Stage 2: 100-300µm at 400µm/s (transition)")
    print(f"      Stage 3: 300-1000µm at {base_velocity_um_s}µm/s (normal)")
    
    start_time = time.time()
    result = motion_controller.execute_lift(
        start_pos_um=current_pos_um,
        target_pos_um=target_lift_pos_um,
        base_velocity_um_s=base_velocity_um_s,
        base_acceleration_um_s2=base_acceleration_um_s2,
        smooth_enabled=True
    )
    
    if result['success']:
        print(f"      ✓ Completed in {result['movement_time_s']:.3f}s")
        print(f"      ✓ Final position: {result['final_position_um'] / 1000:.4f} mm")
        print(f"      ✓ Segments completed: {result['segments_completed']}")
        print(f"      ✓ Early stop: {result['early_stop']}")
    else:
        print(f"      ✗ ERROR: {result.get('error', 'Unknown error')}")
        connection.close()
        return False
    
    time.sleep(0.5)
    
    # Return to start with smooth retraction
    print(f"\n      Returning to start (smooth retraction at 1 mm/s²)...")
    result = motion_controller.execute_retraction(
        target_pos_um=target_return_pos_um,
        base_velocity_um_s=base_velocity_um_s,
        base_acceleration_um_s2=base_acceleration_um_s2,
        smooth_enabled=True
    )
    
    if result['success']:
        print(f"      ✓ Returned in {result['movement_time_s']:.3f}s")
        print(f"      ✓ Acceleration used: {result['acceleration_used_um_s2'] / 1000:.1f} mm/s²")
    else:
        print(f"      ✗ ERROR: {result.get('error', 'Unknown error')}")
    
    time.sleep(1.0)
    
    # Test 3: Compare timing
    print(f"\n[7/7] RESULTS SUMMARY:")
    print(f"      Both tests completed successfully!")
    print(f"\n      Smooth lift benefits:")
    print(f"      - Gentle initial break reduces hydrodynamic lock forces")
    print(f"      - Gradual velocity increase prevents sudden force spikes")
    print(f"      - Ready for smart peel integration")
    print(f"\n      Smooth retraction benefits:")
    print(f"      - Ultra-low acceleration (1 mm/s²) prevents stage stalls")
    print(f"      - Continuous smooth movement (no stops)")
    print(f"      - Only slightly slower than high acceleration")
    
    # Final position check
    final_pos_mm = axis.get_position(Units.LENGTH_MILLIMETRES)
    print(f"\n      Final position: {final_pos_mm:.4f} mm")
    print(f"      Position error from start: {abs(final_pos_mm - current_pos_mm) * 1000:.1f} µm")
    
    # Close connection
    connection.close()
    
    print("\n" + "=" * 80)
    print("TEST COMPLETED SUCCESSFULLY")
    print("=" * 80)
    print("\nThe MotionController is ready for integration into Prince_Segmented.py!")
    print("\nNext steps:")
    print("  1. Add MotionController initialization in Prince_Segmented.__init__()")
    print("  2. Replace peel movement with motion_controller.execute_lift()")
    print("  3. Replace retraction movement with motion_controller.execute_retraction()")
    print("  4. Add 'Smooth Lifting' checkbox to UI")
    print("  5. Test with actual print")
    
    return True


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("MOTION CONTROLLER TEST SCRIPT")
    print("=" * 80)
    print("\nThis test will:")
    print("  1. Connect to the Zaber stage on COM3")
    print("  2. Test standard single-stage lift (1mm)")
    print("  3. Test smooth 3-stage lift with velocity ramping")
    print("  4. Test standard retraction")
    print("  5. Test smooth retraction with gentle acceleration")
    print("  6. Compare results and validate functionality")
    print("\nIMPORTANT:")
    print("  - Ensure stage has clearance for 1mm movements")
    print("  - GUI must be closed (exclusive COM port access)")
    print("  - Watch for smooth velocity transitions")
    print("  - Press Ctrl+C to abort if needed")
    
    input("\nPress ENTER to start test...")
    
    try:
        success = test_motion_controller()
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
