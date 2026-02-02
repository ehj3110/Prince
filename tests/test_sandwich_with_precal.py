"""
Sandwich Routine Test Script with Pre-Calibration

This script tests the complete sandwich workflow:
1. Move to user-specified membrane position
2. Run pre-calibration (5 touches)
3. Execute bilateral (linear scaled) sandwich routine

Includes extensive debug output to track:
- All position changes
- All speed values used
- Timing of each movement
- Force readings at key points
"""

import time
import sys
from zaber_motion import Units

# Add support_modules to path
sys.path.insert(0, 'support_modules')

from SandwichRoutines import SandwichRoutineManager


class DebugLogger:
    """Logger that prints with timestamps and tracks all movements"""
    
    def __init__(self):
        self.start_time = time.time()
        self.movements = []
        
    def log(self, message, error=False):
        """Log message with timestamp"""
        elapsed = time.time() - self.start_time
        prefix = "[ERROR]" if error else "[INFO] "
        print(f"{prefix} [{elapsed:7.2f}s] {message}")
        
    def log_movement(self, start_pos_um, end_pos_um, speed_um_s, label):
        """Log movement details"""
        distance_um = abs(end_pos_um - start_pos_um)
        direction = "DOWN" if end_pos_um > start_pos_um else "UP"
        duration_s = distance_um / speed_um_s if speed_um_s > 0 else 0
        
        movement = {
            'label': label,
            'start_mm': start_pos_um / 1000.0,
            'end_mm': end_pos_um / 1000.0,
            'distance_um': distance_um,
            'speed_um_s': speed_um_s,
            'direction': direction,
            'duration_s': duration_s
        }
        self.movements.append(movement)
        
        self.log(f">>> MOVEMENT: {label}")
        self.log(f"    Start:    {movement['start_mm']:.4f} mm")
        self.log(f"    End:      {movement['end_mm']:.4f} mm")
        self.log(f"    Distance: {distance_um:.1f} µm ({direction})")
        self.log(f"    Speed:    {speed_um_s:.0f} µm/s")
        self.log(f"    Duration: {duration_s:.2f} s")
        
    def print_movement_summary(self):
        """Print summary of all movements"""
        self.log("=" * 80)
        self.log("MOVEMENT SUMMARY")
        self.log("=" * 80)
        
        # Group by descent and ascent
        descents = [m for m in self.movements if m['direction'] == 'DOWN']
        ascents = [m for m in self.movements if m['direction'] == 'UP']
        
        self.log(f"\nDESCENT MOVEMENTS ({len(descents)}):")
        for i, m in enumerate(descents, 1):
            self.log(f"  {i}. {m['label']:30s} - {m['distance_um']:6.0f}µm @ {m['speed_um_s']:6.0f}µm/s ({m['duration_s']:5.2f}s)")
        
        self.log(f"\nASCENT MOVEMENTS ({len(ascents)}):")
        for i, m in enumerate(ascents, 1):
            self.log(f"  {i}. {m['label']:30s} - {m['distance_um']:6.0f}µm @ {m['speed_um_s']:6.0f}µm/s ({m['duration_s']:5.2f}s)")
        
        # Check for symmetry issues
        self.log("\nSYMMETRY ANALYSIS:")
        if len(descents) > 0 and len(ascents) > 0:
            total_descent_distance = sum(m['distance_um'] for m in descents)
            total_ascent_distance = sum(m['distance_um'] for m in ascents)
            
            self.log(f"  Total descent distance: {total_descent_distance:.0f} µm")
            self.log(f"  Total ascent distance:  {total_ascent_distance:.0f} µm")
            self.log(f"  Difference:             {abs(total_descent_distance - total_ascent_distance):.0f} µm")
            
            # Check speed matching
            self.log("\n  Speed comparison (if segments match):")
            for desc, asc in zip(descents[-3:], ascents[:3]):  # Compare last 3 descents with first 3 ascents
                speed_diff = abs(desc['speed_um_s'] - asc['speed_um_s'])
                match = "✓ MATCH" if speed_diff < 1.0 else f"✗ DIFF: {speed_diff:.0f}µm/s"
                self.log(f"    {desc['label']:20s} ({desc['speed_um_s']:6.0f}µm/s) vs {asc['label']:20s} ({asc['speed_um_s']:6.0f}µm/s) - {match}")


class DebugSandwichManager(SandwichRoutineManager):
    """Extended sandwich manager with movement tracking"""
    
    def __init__(self, axis, force_gauge, logger):
        super().__init__(axis, force_gauge, logger.log)
        self.logger = logger
        
    def _move_with_force_monitoring(self, target_um, speed_um_s, force_threshold, 
                                    safety_limit, layer_num, tier_label, 
                                    stop_flag_callback=None):
        """Override to log movement details"""
        start_pos = self.axis.get_position(Units.LENGTH_MICROMETRES)
        self.logger.log_movement(start_pos, target_um, speed_um_s, f"MONITORED: {tier_label}")
        
        # Call parent implementation
        result = super()._move_with_force_monitoring(
            target_um, speed_um_s, force_threshold, safety_limit,
            layer_num, tier_label, stop_flag_callback
        )
        
        # Log actual end position and result
        actual_end = result[1]
        reason = result[2]
        if result[0]:  # Stopped early
            self.logger.log(f"    ⚠ STOPPED EARLY at {actual_end/1000.0:.4f}mm - Reason: {reason}")
        
        return result
    
    def _move_segment(self, target_um, speed_um_s, layer_num, label):
        """Override to log movement details"""
        start_pos = self.axis.get_position(Units.LENGTH_MICROMETRES)
        self.logger.log_movement(start_pos, target_um, speed_um_s, f"SEGMENT: {label}")
        
        # Call parent implementation
        super()._move_segment(target_um, speed_um_s, layer_num, label)


def test_sandwich_routine():
    """Main test function"""
    
    logger = DebugLogger()
    
    logger.log("=" * 80)
    logger.log("SANDWICH ROUTINE TEST WITH PRE-CALIBRATION")
    logger.log("=" * 80)
    
    # Get user input
    print("\n" + "=" * 80)
    membrane_position_mm = float(input("Enter membrane position (mm): "))
    gap_estimate_mm = float(input("Enter estimated gap (mm, e.g., 0.5): "))
    contact_force_N = float(input("Enter contact force threshold (N, e.g., 0.6): "))
    sandwich_speed_um_s = float(input("Enter sandwich speed (µm/s, e.g., 500): "))
    test_area_mm2 = float(input("Enter test area for bilateral sandwich (mm², e.g., 50): "))
    print("=" * 80 + "\n")
    
    logger.log(f"TEST PARAMETERS:")
    logger.log(f"  Membrane position:    {membrane_position_mm:.3f} mm")
    logger.log(f"  Gap estimate:         {gap_estimate_mm:.3f} mm")
    logger.log(f"  Contact force:        {contact_force_N:.3f} N")
    logger.log(f"  Sandwich speed:       {sandwich_speed_um_s:.0f} µm/s")
    logger.log(f"  Test area:            {test_area_mm2:.2f} mm²")
    
    try:
        # Import Zaber and force gauge
        logger.log("\nInitializing hardware...")
        
        # NOTE: You'll need to uncomment and adapt these imports for your actual setup
        # from your_zaber_module import axis  # Your Zaber axis object
        # from your_force_module import force_gauge  # Your force gauge object
        
        # For now, prompt user to connect
        input("\nPress ENTER after you've initialized axis and force_gauge in your environment...")
        
        # These should be imported from your actual hardware modules
        # This is a placeholder - replace with your actual hardware objects
        try:
            # Try to get axis and force_gauge from the user's environment
            axis = eval(input("Enter variable name for your Zaber axis object (e.g., 'stage.axis'): "))
            force_gauge = eval(input("Enter variable name for your force gauge object: "))
        except:
            logger.log("ERROR: Could not get hardware objects. Make sure they're initialized.", error=True)
            logger.log("You can modify this script to directly import your hardware modules.", error=True)
            return
        
        logger.log("✓ Hardware initialized")
        
        # Create debug sandwich manager
        sandwich_manager = DebugSandwichManager(axis, force_gauge, logger)
        
        # Configure for bilateral sandwich
        sandwich_manager.force_at_max_area = -2.0
        sandwich_manager.max_area = 100.0
        sandwich_manager.calibration_force = -0.6
        sandwich_manager.safety_limit = -4.0
        sandwich_manager.base_flatness_threshold = 0.05
        sandwich_manager.max_iterations = 3
        
        logger.log("\n" + "=" * 80)
        logger.log("STEP 1: MOVE TO MEMBRANE POSITION")
        logger.log("=" * 80)
        
        current_pos_mm = axis.get_position(Units.LENGTH_MILLIMETRES)
        logger.log(f"Current position: {current_pos_mm:.3f} mm")
        logger.log(f"Moving to membrane position: {membrane_position_mm:.3f} mm...")
        
        start_pos_um = axis.get_position(Units.LENGTH_MICROMETRES)
        target_pos_um = membrane_position_mm * 1000.0
        logger.log_movement(start_pos_um, target_pos_um, 500.0, "MOVE TO MEMBRANE")
        
        axis.move_absolute(
            membrane_position_mm, Units.LENGTH_MILLIMETRES,
            wait_until_idle=True, velocity=0.5,
            velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND
        )
        
        final_pos_mm = axis.get_position(Units.LENGTH_MILLIMETRES)
        logger.log(f"✓ At membrane position: {final_pos_mm:.3f} mm")
        
        # Wait and read force
        time.sleep(1.0)
        initial_force = force_gauge.get_latest_calibrated_force()
        logger.log(f"Initial force reading: {initial_force:.4f} N")
        
        logger.log("\n" + "=" * 80)
        logger.log("STEP 2: PRE-CALIBRATION (5 TOUCHES)")
        logger.log("=" * 80)
        
        measured_gap = sandwich_manager.perform_precalibration(
            gap_estimate_mm=gap_estimate_mm,
            contact_force_threshold=contact_force_N,
            sandwich_speed_um_s=sandwich_speed_um_s,
            stop_flag_callback=None
        )
        
        if measured_gap is None:
            logger.log("✗ Pre-calibration FAILED", error=True)
            return
        
        logger.log(f"✓ Pre-calibration SUCCESS: Measured gap = {measured_gap:.3f} mm")
        
        # Wait at membrane position
        time.sleep(2.0)
        
        logger.log("\n" + "=" * 80)
        logger.log("STEP 3: BILATERAL SANDWICH (LINEAR SCALED)")
        logger.log("=" * 80)
        
        # Calculate layer height (membrane position is the target)
        layer_height_um = membrane_position_mm * 1000.0
        
        logger.log(f"Executing bilateral sandwich:")
        logger.log(f"  Area:         {test_area_mm2:.2f} mm²")
        logger.log(f"  Layer height: {layer_height_um:.0f} µm ({membrane_position_mm:.3f} mm)")
        logger.log(f"  Measured gap: {measured_gap:.3f} mm")
        
        success = sandwich_manager.execute_linear_scaled_sandwich(
            current_area_mm2=test_area_mm2,
            layer_height_um=layer_height_um,
            measured_gap_mm=measured_gap,
            layer_display_num=1,
            pause_time_s=1.0,
            stop_flag_callback=None
        )
        
        if success:
            logger.log("✓ Bilateral sandwich COMPLETE")
        else:
            logger.log("✗ Bilateral sandwich FAILED", error=True)
        
        # Final position check
        final_pos_mm = axis.get_position(Units.LENGTH_MILLIMETRES)
        logger.log(f"\nFinal position: {final_pos_mm:.3f} mm")
        
        final_force = force_gauge.get_latest_calibrated_force()
        logger.log(f"Final force: {final_force:.4f} N")
        
        # Print movement summary
        logger.log("\n")
        logger.print_movement_summary()
        
        logger.log("\n" + "=" * 80)
        logger.log("TEST COMPLETE")
        logger.log("=" * 80)
        
    except Exception as e:
        logger.log(f"TEST FAILED: {e}", error=True)
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_sandwich_routine()
