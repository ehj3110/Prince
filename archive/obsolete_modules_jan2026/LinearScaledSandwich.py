"""
Linear Area-Scaled Sandwich Routine with Bidirectional Correction

This module handles the sandwich routine for resin printing with:
- Linear area-scaled force thresholds
- 3-tier ramped descent (fast → medium → slow)
- 3-tier ramped ascent (slow → medium → fast)
- Bidirectional correction loop (up/down adjustments)
- Area-scaled flatness threshold (pressure-based)
"""

import time
from Zaber.zaber_device import Units


class LinearScaledSandwich:
    """
    Manages linear area-scaled sandwich routine with bidirectional correction.
    
    Parameters configured in Prince_Segmented.py:
    - force_at_max_area: Target force at maximum area (e.g., -2.0N at 100mm²)
    - max_area: Reference area for scaling (default: 100mm²)
    - calibration_force: Force used for gap measurement (default: -0.6N)
    - safety_limit: Absolute force limit to stop descent (default: -4.0N)
    - base_flatness_threshold: Base flatness tolerance (default: ±0.05N)
    - max_iterations: Maximum correction cycles (default: 3)
    """
    
    def __init__(self, axis, force_gauge, update_status_callback):
        """
        Initialize the sandwich routine manager.
        
        Args:
            axis: Zaber axis object for stage control
            force_gauge: Force gauge object for force readings
            update_status_callback: Function to display status messages
        """
        self.axis = axis
        self.force_gauge = force_gauge
        self.update_status = update_status_callback
        
        # Configuration parameters (set from outside)
        self.force_at_max_area = -2.0  # N
        self.max_area = 100.0  # mm²
        self.calibration_force = -0.6  # N
        self.safety_limit = -4.0  # N
        self.base_flatness_threshold = 0.05  # N
        self.base_area_for_flatness = None  # Set on first layer
        self.max_iterations = 3
        
        # Tier speeds (will be calculated from base sandwich speed)
        self.speed_tier1 = 1000.0  # µm/s - Fast
        self.speed_tier2 = 250.0   # µm/s - Medium
        self.speed_tier3 = 62.5    # µm/s - Slow
    
    def set_speeds_from_base(self, base_speed_um_s):
        """
        Calculate 3-tier speeds from base sandwich speed.
        
        Args:
            base_speed_um_s: Base sandwich speed in µm/s
        """
        self.speed_tier1 = base_speed_um_s
        self.speed_tier2 = base_speed_um_s / 4.0
        self.speed_tier3 = base_speed_um_s / 16.0
    
    def perform_3tier_descent(self, start_pos_um, target_pos_um, force_threshold, 
                             layer_display_num, stop_flag_callback=None):
        """
        Perform 3-tier ramped descent with force monitoring.
        
        Args:
            start_pos_um: Starting position in micrometers
            target_pos_um: Target position (glass) in micrometers
            force_threshold: Stop when force reaches this value
            layer_display_num: Layer number for status messages
            stop_flag_callback: Optional callback to check if should stop (returns True to abort)
        
        Returns:
            Final position in micrometers after descent completes
        """
        gap_um = start_pos_um - target_pos_um
        
        # Calculate waypoints (moving DOWN, so adding to target position)
        waypoint_33pct_um = target_pos_um + (gap_um * 0.67)  # 33% into descent
        waypoint_67pct_um = target_pos_um + (gap_um * 0.33)  # 67% into descent
        
        self.update_status(f"L{layer_display_num}: Descending with 3-tier ramping: "
                          f"{self.speed_tier1:.0f}/{self.speed_tier2:.0f}/{self.speed_tier3:.0f} µm/s")
        
        # Tier 1: Fast descent (0-33% of gap)
        self.update_status(f"L{layer_display_num}: [DESCENT 1/3] @ {self.speed_tier1:.0f}µm/s")
        self.axis.move_absolute(waypoint_33pct_um, Units.LENGTH_MICROMETRES, wait_until_idle=False,
                               velocity=self.speed_tier1/1000.0, velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND,
                               acceleration=1000.0, acceleration_unit=Units.ACCELERATION_MILLIMETRES_PER_SECOND_SQUARED)
        
        while self.axis.is_busy():
            if stop_flag_callback and stop_flag_callback():
                self.axis.stop()
                return self.axis.get_position(Units.LENGTH_MICROMETRES)
            
            current_force = self.force_gauge.get_latest_calibrated_force()
            if current_force <= force_threshold:
                self.axis.stop()
                self.update_status(f"L{layer_display_num}: Contact at {current_force:.3f} N (tier 1)")
                return self.axis.get_position(Units.LENGTH_MICROMETRES)
            if current_force <= self.safety_limit:
                self.axis.stop()
                self.update_status(f"L{layer_display_num}: SAFETY LIMIT at {current_force:.3f} N", error=True)
                return self.axis.get_position(Units.LENGTH_MICROMETRES)
            time.sleep(0.01)
        
        if stop_flag_callback and stop_flag_callback():
            return self.axis.get_position(Units.LENGTH_MICROMETRES)
        
        # Check if we already hit threshold
        if self.force_gauge.get_latest_calibrated_force() > force_threshold:
            # Tier 2: Medium descent (33-67% of gap)
            self.update_status(f"L{layer_display_num}: [DESCENT 2/3] @ {self.speed_tier2:.0f}µm/s")
            self.axis.move_absolute(waypoint_67pct_um, Units.LENGTH_MICROMETRES, wait_until_idle=False,
                                   velocity=self.speed_tier2/1000.0, velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND,
                                   acceleration=1000.0, acceleration_unit=Units.ACCELERATION_MILLIMETRES_PER_SECOND_SQUARED)
            
            while self.axis.is_busy():
                if stop_flag_callback and stop_flag_callback():
                    self.axis.stop()
                    return self.axis.get_position(Units.LENGTH_MICROMETRES)
                
                current_force = self.force_gauge.get_latest_calibrated_force()
                if current_force <= force_threshold:
                    self.axis.stop()
                    self.update_status(f"L{layer_display_num}: Contact at {current_force:.3f} N (tier 2)")
                    return self.axis.get_position(Units.LENGTH_MICROMETRES)
                if current_force <= self.safety_limit:
                    self.axis.stop()
                    self.update_status(f"L{layer_display_num}: SAFETY LIMIT at {current_force:.3f} N", error=True)
                    return self.axis.get_position(Units.LENGTH_MICROMETRES)
                time.sleep(0.01)
            
            if stop_flag_callback and stop_flag_callback():
                return self.axis.get_position(Units.LENGTH_MICROMETRES)
        
        if self.force_gauge.get_latest_calibrated_force() > force_threshold:
            # Tier 3: Slow descent (67-100% of gap)
            self.update_status(f"L{layer_display_num}: [DESCENT 3/3] @ {self.speed_tier3:.0f}µm/s")
            self.axis.move_absolute(target_pos_um, Units.LENGTH_MICROMETRES, wait_until_idle=False,
                                   velocity=self.speed_tier3/1000.0, velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND,
                                   acceleration=1000.0, acceleration_unit=Units.ACCELERATION_MILLIMETRES_PER_SECOND_SQUARED)
            
            while self.axis.is_busy():
                if stop_flag_callback and stop_flag_callback():
                    self.axis.stop()
                    return self.axis.get_position(Units.LENGTH_MICROMETRES)
                
                current_force = self.force_gauge.get_latest_calibrated_force()
                if current_force <= force_threshold:
                    self.axis.stop()
                    self.update_status(f"L{layer_display_num}: Contact at {current_force:.3f} N (tier 3)")
                    return self.axis.get_position(Units.LENGTH_MICROMETRES)
                if current_force <= self.safety_limit:
                    self.axis.stop()
                    self.update_status(f"L{layer_display_num}: SAFETY LIMIT at {current_force:.3f} N", error=True)
                    return self.axis.get_position(Units.LENGTH_MICROMETRES)
                time.sleep(0.01)
        
        return self.axis.get_position(Units.LENGTH_MICROMETRES)
    
    def perform_3tier_ascent(self, start_pos_um, target_pos_um, layer_display_num):
        """
        Perform 3-tier ramped ascent (reverse of descent speeds).
        
        Args:
            start_pos_um: Starting position in micrometers
            target_pos_um: Target position (layer height) in micrometers
            layer_display_num: Layer number for status messages
        """
        distance_um = abs(target_pos_um - start_pos_um)
        
        if distance_um < 10.0:
            # Already at target, just ensure position
            self.axis.move_absolute(target_pos_um, Units.LENGTH_MICROMETRES, wait_until_idle=True)
            return
        
        # Calculate waypoints for symmetrical ascent
        waypoint_33pct_um = start_pos_um + (distance_um * 0.33)
        waypoint_67pct_um = start_pos_um + (distance_um * 0.67)
        
        self.update_status(f"L{layer_display_num}: [ASCENT] Moving {distance_um:.0f}µm with 3-tier ramp")
        
        # Tier 1 (0-33%): Slowest - near glass
        self.axis.move_absolute(waypoint_33pct_um, Units.LENGTH_MICROMETRES, wait_until_idle=True,
                               velocity=self.speed_tier3/1000.0, velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND,
                               acceleration=1000.0, acceleration_unit=Units.ACCELERATION_MILLIMETRES_PER_SECOND_SQUARED)
        
        # Tier 2 (33-67%): Medium speed
        self.axis.move_absolute(waypoint_67pct_um, Units.LENGTH_MICROMETRES, wait_until_idle=True,
                               velocity=self.speed_tier2/1000.0, velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND,
                               acceleration=1000.0, acceleration_unit=Units.ACCELERATION_MILLIMETRES_PER_SECOND_SQUARED)
        
        # Tier 3 (67-100%): Fastest - far from glass
        self.axis.move_absolute(target_pos_um, Units.LENGTH_MICROMETRES, wait_until_idle=True,
                               velocity=self.speed_tier1/1000.0, velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND,
                               acceleration=1000.0, acceleration_unit=Units.ACCELERATION_MILLIMETRES_PER_SECOND_SQUARED)
    
    def execute_sandwich(self, current_area_mm2, layer_height_um, measured_gap_mm, 
                        layer_display_num, pause_time_s=0.0, stop_flag_callback=None):
        """
        Execute complete sandwich routine with bidirectional correction.
        
        Args:
            current_area_mm2: Current layer area in mm²
            layer_height_um: Target layer height in micrometers
            measured_gap_mm: Measured gap from calibration in millimeters
            layer_display_num: Layer number for status messages
            pause_time_s: Final pause time after sandwich completes
            stop_flag_callback: Optional callback to check if should stop
        
        Returns:
            True if sandwich completed successfully, False if aborted
        """
        # Calculate linearly scaled force threshold
        scaled_threshold = self.force_at_max_area * (current_area_mm2 / self.max_area)
        
        # Calibrate flatness threshold on first layer
        if self.base_area_for_flatness is None:
            self.base_area_for_flatness = current_area_mm2
            self.update_status(f"Flatness threshold calibrated: ±{self.base_flatness_threshold}N @ {current_area_mm2:.2f}mm²")
        
        # Scale flatness threshold linearly by area (force = pressure × area)
        flatness_area_ratio = current_area_mm2 / self.base_area_for_flatness
        scaled_flatness_threshold = self.base_flatness_threshold * flatness_area_ratio
        
        self.update_status(f"L{layer_display_num}: Area: {current_area_mm2:.2f} mm², "
                          f"Force threshold: {scaled_threshold:.3f} N, "
                          f"Flatness: ±{scaled_flatness_threshold:.3f}N")
        
        # Get current position and calculate target
        current_pos_um = self.axis.get_position(Units.LENGTH_MICROMETRES)
        gap_um = measured_gap_mm * 1000.0
        target_glass_um = layer_height_um  # Target is the layer position itself
        
        # ========== INITIAL DESCENT ==========
        final_descent_pos_um = self.perform_3tier_descent(
            current_pos_um, target_glass_um, scaled_threshold, 
            layer_display_num, stop_flag_callback
        )
        
        if stop_flag_callback and stop_flag_callback():
            return False
        
        # ========== INITIAL ASCENT TO LAYER HEIGHT ==========
        current_pos_um = self.axis.get_position(Units.LENGTH_MICROMETRES)
        self.perform_3tier_ascent(current_pos_um, layer_height_um, layer_display_num)
        
        # ========== BIDIRECTIONAL CORRECTION LOOP ==========
        self.update_status(f"L{layer_display_num}: Starting bidirectional correction loop")
        
        for correction_iter in range(self.max_iterations):
            # Wait and check force at layer height
            time.sleep(1.0)
            current_force = self.force_gauge.get_latest_calibrated_force()
            
            self.update_status(f"L{layer_display_num}: [CHECK {correction_iter+1}/{self.max_iterations}] "
                             f"Force at layer height: {current_force:.3f} N")
            
            # Check if flat (within scaled threshold)
            if abs(current_force) <= scaled_flatness_threshold:
                self.update_status(f"L{layer_display_num}: ✓ Membrane flat! "
                                 f"(|{current_force:.3f}N| < {scaled_flatness_threshold:.3f}N)")
                break
            
            if current_force > scaled_flatness_threshold:
                # Positive force = membrane pulling on part (concave)
                # Solution: Pull UP to stretch membrane
                self.update_status(f"L{layer_display_num}: Membrane pulling (+{current_force:.3f}N) - pulling upward")
                
                pull_up_position_um = layer_height_um - 100.0  # Pull up 100µm
                self.axis.move_absolute(pull_up_position_um, Units.LENGTH_MICROMETRES, wait_until_idle=True,
                                       velocity=1.0, velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND)
                
                # Return to layer height
                current_pos_um = self.axis.get_position(Units.LENGTH_MICROMETRES)
                self.perform_3tier_ascent(current_pos_um, layer_height_um, layer_display_num)
                
            elif current_force < -scaled_flatness_threshold:
                # Negative force = resin trapped beneath
                # Solution: Re-sandwich with full descent
                self.update_status(f"L{layer_display_num}: Resin trapped ({current_force:.3f}N) - re-sandwiching")
                
                current_pos_um = self.axis.get_position(Units.LENGTH_MICROMETRES)
                self.perform_3tier_descent(
                    current_pos_um, target_glass_um, scaled_threshold,
                    layer_display_num, stop_flag_callback
                )
                
                if stop_flag_callback and stop_flag_callback():
                    return False
                
                # Ascend back to layer height
                current_pos_um = self.axis.get_position(Units.LENGTH_MICROMETRES)
                self.perform_3tier_ascent(current_pos_um, layer_height_um, layer_display_num)
        else:
            # Max iterations reached without convergence
            final_force = self.force_gauge.get_latest_calibrated_force()
            self.update_status(f"L{layer_display_num}: ⚠ Max iterations reached. "
                             f"Final force: {final_force:.3f} N", error=True)
        
        # Ensure we're at layer height
        self.axis.move_absolute(layer_height_um, Units.LENGTH_MICROMETRES, wait_until_idle=True)
        
        # Final pause
        if pause_time_s > 0:
            self.update_status(f"L{layer_display_num}: [FINAL PAUSE] {pause_time_s:.1f}s")
            time.sleep(pause_time_s)
        
        self.update_status(f"L{layer_display_num}: ========== LINEAR SCALED SANDWICH COMPLETE ==========")
        return True
