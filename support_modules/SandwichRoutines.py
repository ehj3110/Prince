"""
Unified Sandwich Routines Module

This module handles ALL sandwich routines and pre-calibration for resin printing:
1. Linear Area-Scaled Sandwich (with bidirectional correction)
2. Adaptive Force-Responsive Sandwich  
3. Classic 4-Tier Sandwich
4. Pre-Calibration Routine (gap measurement)

ARCHITECTURE:
============
The module is organized into three layers for maintainability and code reuse:

LAYER 1: Core Motion Primitives (Low-Level Building Blocks)
  - _calculate_waypoints(): Calculate position waypoints for ramped motion
  - _move_with_force_monitoring(): Move while monitoring force thresholds
  - _move_segment(): Simple move without force monitoring

LAYER 2: High-Level Motion Routines (Reusable Patterns)
  - perform_3tier_descent(): Standard 3-tier descent with force monitoring
  - perform_3tier_ascent(): Standard 3-tier ascent (symmetric speeds)
  - perform_multitier_ascent(): Flexible N-tier ascent with pause support

LAYER 3: Complete Sandwich Routines (User-Facing Methods)
  - execute_linear_scaled_sandwich(): Area-scaled force with correction loop
  - execute_adaptive_sandwich(): Adaptive speed optimization with 3/4-tier ascent
  - execute_classic_sandwich(): Classic 4-tier sandwich with pause
  - perform_precalibration(): 5-touch gap measurement before printing

BENEFITS:
- DRY principle: No duplicated force monitoring or waypoint calculation code
- Easy to add new sandwich types by composing existing primitives
- Consistent behavior across all sandwich routines and pre-calibration
- Centralized logic for easier maintenance and debugging
- ~950 lines of duplicate code eliminated from main script

All sandwich and pre-calibration logic is centralized here.
"""

import time
from zaber_motion import Units


class SandwichRoutineManager:
    """
    Unified manager for all sandwich routine types.
    
    Features:
    - Modular architecture with reusable motion primitives
    - Universal force monitoring and waypoint calculation
    - Linear area-scaled force thresholds with bidirectional correction
    - Adaptive force-responsive descent with speed optimization
    - Flexible multi-tier ascent (3-tier or 4-tier based on distance)
    - Pressure-based flatness scaling
    """
    
    def __init__(self, axis, force_gauge, update_status_callback, set_phase_callback=None):
        """
        Initialize the sandwich routine manager.
        
        Args:
            axis: Zaber axis object for stage control
            force_gauge: Force gauge object for force readings
            update_status_callback: Function to display status messages
            set_phase_callback: Optional function to set phase for data logging (Lift, Retract, Pause, etc.)
        """
        self.axis = axis
        self.force_gauge = force_gauge
        self.update_status = update_status_callback
        self.set_phase = set_phase_callback  # May be None
        
        # ===== LINEAR SCALED SANDWICH PARAMETERS =====
        self.force_at_max_area = -2.0  # N - Target force at maximum area
        self.max_area = 100.0  # mm² - Reference area for scaling
        self.calibration_force = -0.6  # N - Force used for gap measurement
        self.safety_limit = -4.0  # N - Absolute force limit to stop descent
        self.base_flatness_threshold = 0.025  # N - Base flatness tolerance
        self.base_area_for_flatness = None  # Set on first layer
        self.max_iterations = 3  # Maximum correction cycles
        
        # ===== SMOOTH SANDWICH MODE (EXPERIMENTAL) =====
        self.use_smooth_sandwich = False  # Set to True to skip tiers and use smooth accel/decel
        self.smooth_liftoff_accel_mm_s2 = 1.0  # Gentle liftoff acceleration
        self.smooth_pause_at_contact_s = 0.5  # Pause before liftoff
        
        # ===== ADAPTIVE SANDWICH PARAMETERS =====
        self.adaptive_sandwich_speed_um_s = None  # Adaptive speed from previous layer
        self.sandwich_layer_count = 0  # Track number of sandwich layers processed
        
        # Tier speeds (will be calculated from base sandwich speed)
        self.speed_tier1 = 1000.0  # µm/s - Fast
        self.speed_tier2 = 250.0   # µm/s - Medium
        self.speed_tier3 = 62.5    # µm/s - Slow
    
    def set_speeds_from_base(self, base_speed_um_s, speed_division=4.0):
        """
        Calculate 3-tier speeds from base sandwich speed.
        
        Args:
            base_speed_um_s: Base sandwich speed in µm/s
            speed_division: Division factor for tiers (4.0 for linear, 3.0 for adaptive)
        """
        self.speed_tier1 = base_speed_um_s
        self.speed_tier2 = base_speed_um_s / speed_division
        self.speed_tier3 = base_speed_um_s / (speed_division ** 2)
    
    # ========== CORE MOTION PRIMITIVES ==========
    
    def _calculate_waypoints(self, start_um, target_um, percentages):
        """
        Calculate waypoints for ramped motion.
        
        Args:
            start_um: Starting position in micrometers
            target_um: Target position in micrometers
            percentages: List of percentage points (e.g., [0.33, 0.67] for 3-tier)
        
        Returns:
            List of waypoint positions in micrometers
        """
        distance_um = abs(target_um - start_um)
        direction = 1 if target_um > start_um else -1
        
        waypoints = []
        for pct in percentages:
            waypoint = start_um + (direction * distance_um * pct)
            waypoints.append(waypoint)
        
        return waypoints
    
    def _move_with_force_monitoring(self, target_um, speed_um_s, force_threshold, 
                                    safety_limit, layer_num, tier_label, 
                                    stop_flag_callback=None, acceleration_um_s2=None):
        """
        Move to target position while monitoring force.
        
        Args:
            target_um: Target position in micrometers
            speed_um_s: Speed in µm/s
            force_threshold: Stop if force <= this value
            safety_limit: Emergency stop if force <= this value
            layer_num: Layer number for status messages
            tier_label: Label for this movement tier (e.g., "1/3")
            stop_flag_callback: Optional callback to check if should stop
            acceleration_um_s2: Optional acceleration in µm/s² (default: 1000 mm/s² = 1000000 µm/s²)
        
        Returns:
            Tuple of (stopped_early, final_position_um, stop_reason)
            - stopped_early: True if stopped due to force/safety, False if reached target
            - final_position_um: Final position in micrometers
            - stop_reason: "threshold", "safety", "abort", or None
        """
        # Default to high acceleration if not specified (1000 mm/s² for normal tiered operation)
        if acceleration_um_s2 is None:
            acceleration_um_s2 = 1000000  # 1000 mm/s²
        
        self.update_status(f"L{layer_num}: [DESCENT {tier_label}] @ {speed_um_s:.0f}µm/s, "
                          f"Accel:{acceleration_um_s2/1000.0:.1f}mm/s²")
        
        self.axis.move_absolute(
            target_um, Units.LENGTH_MICROMETRES, wait_until_idle=False,
            velocity=speed_um_s/1000.0, velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND,
            acceleration=acceleration_um_s2/1000.0, acceleration_unit=Units.ACCELERATION_MILLIMETRES_PER_SECOND_SQUARED
        )
        
        while self.axis.is_busy():
            if stop_flag_callback and stop_flag_callback():
                self.axis.stop()
                return (True, self.axis.get_position(Units.LENGTH_MICROMETRES), "abort")
            
            current_force = self.force_gauge.get_latest_calibrated_force()
            
            if current_force <= safety_limit:
                self.axis.stop()
                final_pos = self.axis.get_position(Units.LENGTH_MICROMETRES)
                self.update_status(f"L{layer_num}: SAFETY LIMIT at {current_force:.3f} N", error=True)
                return (True, final_pos, "safety")
            
            if current_force <= force_threshold:
                self.axis.stop()
                final_pos = self.axis.get_position(Units.LENGTH_MICROMETRES)
                self.update_status(f"L{layer_num}: Contact at {current_force:.3f} N (tier {tier_label})")
                return (True, final_pos, "threshold")
            
            time.sleep(0.01)
        
        return (False, self.axis.get_position(Units.LENGTH_MICROMETRES), None)
    
    def _move_segment(self, target_um, speed_um_s, layer_num, label):
        """
        Move to target position at specified speed (no force monitoring).
        
        Args:
            target_um: Target position in micrometers
            speed_um_s: Speed in µm/s
            layer_num: Layer number for status messages
            label: Label for this segment (e.g., "ASCENT 1/3")
        """
        self.axis.move_absolute(
            target_um, Units.LENGTH_MICROMETRES, wait_until_idle=True,
            velocity=speed_um_s/1000.0, velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND,
            acceleration=1000.0, acceleration_unit=Units.ACCELERATION_MILLIMETRES_PER_SECOND_SQUARED
        )
    
    # ========== HIGH-LEVEL MOTION ROUTINES ==========
    
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
        waypoints = self._calculate_waypoints(start_pos_um, target_pos_um, [0.50, 0.85])
        
        # Set phase to Lift (descent starts)
        if self.set_phase:
            self.set_phase("Lift")
        
        self.update_status(f"L{layer_display_num}: Descending with 3-tier ramping: "
                          f"{self.speed_tier1:.0f}/{self.speed_tier2:.0f}/{self.speed_tier3:.0f} µm/s")
        self.update_status(f"L{layer_display_num}: DEBUG - Descent waypoints: {waypoints[0]:.1f}µm (50%), {waypoints[1]:.1f}µm (85%)")
        
        # Define descent tiers
        tiers = [
            (waypoints[0], self.speed_tier1, "1/3"),
            (waypoints[1], self.speed_tier2, "2/3"),
            (target_pos_um, self.speed_tier3, "3/3")
        ]
        
        for target, speed, label in tiers:
            if stop_flag_callback and stop_flag_callback():
                return self.axis.get_position(Units.LENGTH_MICROMETRES)
            
            # Check if force already at threshold before starting tier
            if self.force_gauge.get_latest_calibrated_force() <= force_threshold:
                break
            
            stopped_early, final_pos, reason = self._move_with_force_monitoring(
                target, speed, force_threshold, self.safety_limit,
                layer_display_num, label, stop_flag_callback
            )
            
            if stopped_early:
                return final_pos
        
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
            self.axis.move_absolute(target_pos_um, Units.LENGTH_MICROMETRES, wait_until_idle=True)
            return
        
        waypoints = self._calculate_waypoints(start_pos_um, target_pos_um, [0.50, 0.85])
        
        # Set phase to Retract (ascent starts)
        if self.set_phase:
            self.set_phase("Retract")
        
        self.update_status(f"L{layer_display_num}: [ASCENT] Moving {distance_um:.0f}µm with 3-tier ramp")
        self.update_status(f"L{layer_display_num}: DEBUG - Ascent waypoints: {waypoints[0]:.1f}µm (50%), {waypoints[1]:.1f}µm (85%)")
        
        # Tier 1 (0-50%): Slowest - near glass
        tier1_dist = abs(waypoints[0] - start_pos_um)
        self.update_status(f"L{layer_display_num}: DEBUG - Tier 1: {tier1_dist:.1f}µm @ {self.speed_tier3:.0f}µm/s")
        self._move_segment(waypoints[0], self.speed_tier3, layer_display_num, "ASCENT 1/3")
        
        # Tier 2 (50-85%): Medium speed
        tier2_dist = abs(waypoints[1] - waypoints[0])
        self.update_status(f"L{layer_display_num}: DEBUG - Tier 2: {tier2_dist:.1f}µm @ {self.speed_tier2:.0f}µm/s")
        self._move_segment(waypoints[1], self.speed_tier2, layer_display_num, "ASCENT 2/3")
        
        # Tier 3 (85-100%): Fastest - far from glass
        tier3_dist = abs(target_pos_um - waypoints[1])
        self.update_status(f"L{layer_display_num}: DEBUG - Tier 3: {tier3_dist:.1f}µm @ {self.speed_tier1:.0f}µm/s")
        self._move_segment(target_pos_um, self.speed_tier1, layer_display_num, "ASCENT 3/3")
    
    def perform_smooth_descent_and_liftoff(self, start_pos_um, target_pos_um, target_speed_um_s,
                                          force_threshold, layer_display_num, stop_flag_callback=None,
                                          liftoff_accel_mm_s2=1.0, pause_at_contact_s=0.5):
        """
        Perform smooth single-acceleration descent and gentle liftoff.
        
        This eliminates tiered speed changes and uses smooth acceleration for both
        descent and liftoff. The low liftoff acceleration prevents force spikes when
        reversing direction after contact.
        
        Args:
            start_pos_um: Starting position in micrometers
            target_pos_um: Target position (glass) in micrometers  
            target_speed_um_s: Target descent speed in µm/s
            force_threshold: Stop when force reaches this value (N, negative for compression)
            layer_display_num: Layer number for status messages
            stop_flag_callback: Optional callback to check if should stop
            liftoff_accel_mm_s2: Acceleration for liftoff in mm/s² (default 1.0 = gentle)
            pause_at_contact_s: Pause duration at contact before liftoff (default 0.5s)
        
        Returns:
            Tuple (contact_position_um, liftoff_successful)
        """
        gap_um = start_pos_um - target_pos_um
        
        # Calculate appropriate acceleration for smooth descent
        # Use moderate acceleration (2 mm/s²) to reach target speed smoothly
        descent_accel_mm_s2 = 2.0
        descent_accel_um_s2 = int(descent_accel_mm_s2 * 1000.0)
        liftoff_accel_um_s2 = int(liftoff_accel_mm_s2 * 1000.0)
        
        self.update_status(f"L{layer_display_num}: Smooth descent - Gap:{gap_um:.0f}µm, "
                          f"Speed:{target_speed_um_s:.0f}µm/s, Accel:{descent_accel_mm_s2:.1f}mm/s²")
        
        # Start descent with force monitoring
        stopped_early, contact_pos_um, reason = self._move_with_force_monitoring(
            target_pos_um, target_speed_um_s, force_threshold, self.safety_limit,
            layer_display_num, "SMOOTH", stop_flag_callback,
            acceleration_um_s2=descent_accel_um_s2
        )
        
        if not stopped_early:
            self.update_status(f"L{layer_display_num}: Warning - Reached target without force threshold", error=True)
            return (contact_pos_um, False)
        
        if reason == "SAFETY_LIMIT":
            self.update_status(f"L{layer_display_num}: SAFETY LIMIT HIT during descent!", error=True)
            return (contact_pos_um, False)
        
        # Pause at contact to let forces settle
        if pause_at_contact_s > 0:
            self.update_status(f"L{layer_display_num}: Contact reached, pausing {pause_at_contact_s:.1f}s before liftoff")
            time.sleep(pause_at_contact_s)
        
        # Gentle liftoff with low acceleration to prevent force spike
        self.update_status(f"L{layer_display_num}: [GENTLE LIFTOFF] Accel:{liftoff_accel_mm_s2:.1f}mm/s², "
                          f"Speed:{target_speed_um_s:.0f}µm/s")
        
        # Move back to start position with gentle acceleration
        self.axis.move_absolute(
            position=start_pos_um,
            unit=Units.LENGTH_MICROMETRES,
            wait_until_idle=True,
            velocity=target_speed_um_s,
            velocity_unit=Units.VELOCITY_MICROMETRES_PER_SECOND,
            acceleration=liftoff_accel_um_s2,
            acceleration_unit=Units.ACCELERATION_MICROMETRES_PER_SECOND_SQUARED
        )
        
        self.update_status(f"L{layer_display_num}: Liftoff complete - returned to {start_pos_um/1000.0:.4f}mm")
        
        return (contact_pos_um, True)
    
    def perform_multitier_ascent(self, start_pos_um, target_pos_um, speeds, 
                                waypoint_percentages, pause_at_50pct_s, layer_display_num):
        """
        Perform multi-tier ascent with arbitrary number of tiers and optional pause.
        
        Args:
            start_pos_um: Starting position in micrometers
            target_pos_um: Target position in micrometers
            speeds: List of speeds in µm/s for each tier
            waypoint_percentages: List of waypoint percentages (e.g., [0.10, 0.33, 0.50])
            pause_at_50pct_s: Pause duration at 50% point (0 for no pause)
            layer_display_num: Layer number for status messages
        """
        distance_um = abs(target_pos_um - start_pos_um)
        waypoints = self._calculate_waypoints(start_pos_um, target_pos_um, waypoint_percentages)
        
        num_tiers = len(speeds)
        self.update_status(f"L{layer_display_num}: {num_tiers}-TIER ASCENT")
        
        tier_num = 0
        for i, (waypoint, speed) in enumerate(zip(waypoints, speeds)):
            tier_num += 1
            self.update_status(f"L{layer_display_num}: [ASCENT {tier_num}/{num_tiers}] @ {speed:.0f}µm/s")
            self._move_segment(waypoint, speed, layer_display_num, f"ASCENT {tier_num}/{num_tiers}")
            
            # Check if this waypoint is at 50% and we should pause
            if abs(waypoint_percentages[i] - 0.50) < 0.01 and pause_at_50pct_s > 0:
                self.update_status(f"L{layer_display_num}: [ASCENT PAUSE 1/2] {pause_at_50pct_s:.1f}s at 50%")
                time.sleep(pause_at_50pct_s)
        
        # Final segment to target
        tier_num += 1
        final_speed = speeds[-1]  # Use last speed for final segment
        self.update_status(f"L{layer_display_num}: [ASCENT {tier_num}/{num_tiers}] @ {final_speed:.0f}µm/s")
        self._move_segment(target_pos_um, final_speed, layer_display_num, f"ASCENT {tier_num}/{num_tiers}")
    
    def execute_linear_scaled_sandwich(self, current_area_mm2, layer_height_um, measured_gap_mm, 
                                       layer_display_num, pause_time_s=0.0, stop_flag_callback=None,
                                       layer_thickness_um=50.0):
        """
        Execute linear area-scaled sandwich with bidirectional correction.
        
        Args:
            current_area_mm2: Current layer area in mm²
            layer_height_um: Target layer height in micrometers
            measured_gap_mm: Measured gap from calibration in millimeters
            layer_display_num: Layer number for status messages
            pause_time_s: Final pause time after sandwich completes
            stop_flag_callback: Optional callback to check if should stop
            layer_thickness_um: Current layer thickness in micrometers (default 50.0)
        
        Returns:
            True if sandwich completed successfully, False if aborted
        """
        # Calculate linearly scaled force threshold
        scaled_threshold = self.force_at_max_area * (current_area_mm2 / self.max_area)
        
        # Use fixed flatness threshold (no area scaling)
        scaled_flatness_threshold = self.base_flatness_threshold
        
        self.update_status(f"L{layer_display_num}: Area: {current_area_mm2:.2f} mm², "
                          f"Force threshold: {scaled_threshold:.3f} N, "
                          f"Flatness: ±{scaled_flatness_threshold:.3f}N (fixed)")
        
        # Get current position and calculate target
        current_pos_um = self.axis.get_position(Units.LENGTH_MICROMETRES)
        # Subtract layer thickness from gap to leave clearance between glass and part
        adjusted_gap_mm = measured_gap_mm - (layer_thickness_um / 1000.0)
        target_glass_um = layer_height_um + (adjusted_gap_mm * 1000.0)  # Descend through adjusted gap (higher value = lower position)
        
        # DEBUG: Position and distance info
        descent_distance_um = abs(target_glass_um - current_pos_um)
        self.update_status(f"L{layer_display_num}: DEBUG - Start pos: {current_pos_um:.1f}µm, Glass target: {target_glass_um:.1f}µm")
        self.update_status(f"L{layer_display_num}: DEBUG - Original gap: {measured_gap_mm:.3f}mm, Layer thickness: {layer_thickness_um:.1f}µm, Adjusted gap: {adjusted_gap_mm:.3f}mm")
        self.update_status(f"L{layer_display_num}: DEBUG - Descent distance: {descent_distance_um:.1f}µm")
        self.update_status(f"L{layer_display_num}: DEBUG - Speeds: Tier1={self.speed_tier1:.0f}, Tier2={self.speed_tier2:.0f}, Tier3={self.speed_tier3:.0f} µm/s")
        
        # ========== INITIAL DESCENT ==========
        if self.use_smooth_sandwich:
            # SMOOTH MODE: Single smooth descent and gentle liftoff
            self.update_status(f"L{layer_display_num}: ⚙ SMOOTH SANDWICH MODE ⚙")
            contact_pos_um, success = self.perform_smooth_descent_and_liftoff(
                current_pos_um, target_glass_um, self.speed_tier3,  # Use slowest tier speed
                scaled_threshold, layer_display_num, stop_flag_callback,
                liftoff_accel_mm_s2=self.smooth_liftoff_accel_mm_s2,
                pause_at_contact_s=self.smooth_pause_at_contact_s
            )
            
            if not success:
                return False
            
            if stop_flag_callback and stop_flag_callback():
                return False
            
            # Already returned to starting position, move to layer height
            self.axis.move_absolute(layer_height_um, Units.LENGTH_MICROMETRES, wait_until_idle=True)
            
        else:
            # TIERED MODE: Traditional 3-tier descent
            self.perform_3tier_descent(
                current_pos_um, target_glass_um, scaled_threshold, 
                layer_display_num, stop_flag_callback
            )
            
            if stop_flag_callback and stop_flag_callback():
                return False
            
            # DEBUG: Check where descent stopped
            post_descent_pos_um = self.axis.get_position(Units.LENGTH_MICROMETRES)
            descent_actual_distance_um = abs(post_descent_pos_um - current_pos_um)
            reached_glass = abs(post_descent_pos_um - target_glass_um) < 10.0  # Within 10µm of target
            self.update_status(f"L{layer_display_num}: DEBUG - Descent stopped at: {post_descent_pos_um:.1f}µm")
            self.update_status(f"L{layer_display_num}: DEBUG - Actual descent: {descent_actual_distance_um:.1f}µm, Reached glass: {reached_glass}")
            
            # ========== INITIAL ASCENT TO LAYER HEIGHT ==========
            current_pos_um = self.axis.get_position(Units.LENGTH_MICROMETRES)
            ascent_distance_um = abs(layer_height_um - current_pos_um)
            self.update_status(f"L{layer_display_num}: DEBUG - Ascent distance: {ascent_distance_um:.1f}µm (from {current_pos_um:.1f}µm to {layer_height_um:.1f}µm)")
            self.perform_3tier_ascent(current_pos_um, layer_height_um, layer_display_num)
        
        # ========== AGGRESSIVE PROGRESSIVE BIDIRECTIONAL CORRECTION ==========
        self.update_status(f"L{layer_display_num}: Starting aggressive bidirectional correction (max 5 moves)")
        
        # Record force right after sandwich to determine direction
        time.sleep(0.5)
        force_after_sandwich = self.force_gauge.get_latest_calibrated_force()
        self.update_status(f"L{layer_display_num}: Force after sandwich: {force_after_sandwich:.3f} N")
        
        # Progressive correction parameters
        max_correction_moves = 5
        current_scale = 4.0  # Start at 4× layer height
        previous_direction = None  # Track direction changes ('up' or 'down')
        max_correction_distance_um = adjusted_gap_mm * 1000.0  # Don't exceed sandwich gap
        
        for move_num in range(max_correction_moves):
            # Wait and check force
            time.sleep(1.0)
            current_force = self.force_gauge.get_latest_calibrated_force()
            
            self.update_status(f"L{layer_display_num}: [CORRECTION {move_num+1}/{max_correction_moves}] "
                             f"Force: {current_force:.3f} N, Scale: {current_scale:.1f}×")
            
            # Check if force stabilized within tolerance
            if abs(current_force) <= scaled_flatness_threshold:
                self.update_status(f"L{layer_display_num}: ✓ Force stabilized! "
                                 f"(|{current_force:.3f}N| ≤ {scaled_flatness_threshold:.3f}N)")
                break
            
            # Determine correction direction based on current force
            # INVERTED STAGE: Decreasing position = UP (lift), Increasing position = DOWN (lower)
            # Positive force = too little resin (membrane pulling up) → LIFT stage (decrease position)
            # Negative force = too much resin (membrane pushing down) → LOWER stage (increase position)
            if current_force > scaled_flatness_threshold:
                correction_direction = 'up'
                direction_sign = -1  # Decrease position = LIFT stage
                self.update_status(f"L{layer_display_num}: Too little resin (+{current_force:.3f}N) - LIFTING stage")
            elif current_force < -scaled_flatness_threshold:
                correction_direction = 'down'
                direction_sign = +1  # Increase position = LOWER stage
                self.update_status(f"L{layer_display_num}: Too much resin ({current_force:.3f}N) - LOWERING stage")
            else:
                break  # Within tolerance
            
            # Check if direction changed
            if previous_direction is not None and previous_direction != correction_direction:
                self.update_status(f"L{layer_display_num}: Direction changed! Resetting scale")
                if current_scale <= 4.0:
                    current_scale = 4.0  # Stay at 4× if already there
                else:
                    current_scale = 5.0  # Reset to 5×
            
            # Calculate correction distance (limit to gap distance for safety)
            correction_distance_um = min(current_scale * layer_thickness_um, max_correction_distance_um)
            correction_position_um = layer_height_um + (direction_sign * correction_distance_um)
            
            self.update_status(f"L{layer_display_num}: Moving {correction_direction.upper()} "
                             f"{correction_distance_um:.1f}µm ({current_scale:.1f}× layer height)")
            
            # Perform correction movement at tier 1 speed
            self.axis.move_absolute(
                correction_position_um, Units.LENGTH_MICROMETRES,
                wait_until_idle=True,
                velocity=self.speed_tier1, velocity_unit=Units.VELOCITY_MICROMETRES_PER_SECOND
            )
            
            # Pause at max correction distance for 0.5 seconds
            self.update_status(f"L{layer_display_num}: Pausing 0.5s at max correction distance")
            time.sleep(0.5)
            
            # Return to layer height
            self.update_status(f"L{layer_display_num}: Returning to layer height")
            self.axis.move_absolute(
                layer_height_um, Units.LENGTH_MICROMETRES,
                wait_until_idle=True,
                velocity=self.speed_tier1, velocity_unit=Units.VELOCITY_MICROMETRES_PER_SECOND
            )
            
            # Update tracking variables
            previous_direction = correction_direction
            current_scale = min(current_scale + 1.0, 8.0)  # Increment scale, max 8×
            
        else:
            # Max moves reached without stabilization
            final_force = self.force_gauge.get_latest_calibrated_force()
            self.update_status(f"L{layer_display_num}: ⚠ Max correction moves reached. "
                             f"Final force: {final_force:.3f} N", error=True)
        
        # Ensure we're at layer height
        self.axis.move_absolute(layer_height_um, Units.LENGTH_MICROMETRES, wait_until_idle=True)
        
        # ALWAYS perform upward correction of 4× layer height after sandwich (lift and return)
        upward_correction_um = 4.0 * layer_thickness_um
        corrected_position_um = layer_height_um - upward_correction_um  # Negative Z = up
        self.update_status(f"L{layer_display_num}: [UPWARD CORRECTION] Lifting {upward_correction_um:.1f}µm (4× layer height) @ {self.speed_tier1:.0f}µm/s")
        self.axis.move_absolute(
            corrected_position_um, Units.LENGTH_MICROMETRES, 
            wait_until_idle=True,
            velocity=self.speed_tier1, velocity_unit=Units.VELOCITY_MICROMETRES_PER_SECOND
        )
        
        # Return to layer height after upward correction
        self.update_status(f"L{layer_display_num}: [RETURN TO LAYER HEIGHT] Descending {upward_correction_um:.1f}µm back to layer @ {self.speed_tier1:.0f}µm/s")
        self.axis.move_absolute(
            layer_height_um, Units.LENGTH_MICROMETRES,
            wait_until_idle=True,
            velocity=self.speed_tier1, velocity_unit=Units.VELOCITY_MICROMETRES_PER_SECOND
        )
        
        # Final pause
        if pause_time_s > 0:
            self.update_status(f"L{layer_display_num}: [FINAL PAUSE] {pause_time_s:.1f}s")
            time.sleep(pause_time_s)
        
        self.update_status(f"L{layer_display_num}: ========== LINEAR SCALED SANDWICH COMPLETE ==========")
        return True
    
    def execute_adaptive_sandwich(self, layer_height_um, measured_gap_mm, contact_force_threshold,
                                  base_sandwich_speed_um_s, layer_display_num, pause_time_s=0.0,
                                  stop_flag_callback=None):
        """
        Execute adaptive force-responsive sandwich with speed optimization.
        
        Features:
        - Adaptive speed based on previous layer performance
        - 3-tier descent with force monitoring (divide by 3, 9)
        - Dynamic speed reduction when force threshold approached
        - Force relaxation monitoring
        - 3/4-tier ascent based on distance from glass
        - Speed optimization for next layer
        
        Args:
            layer_height_um: Target layer height in micrometers
            measured_gap_mm: Measured gap from calibration in millimeters
            contact_force_threshold: Force threshold for contact detection
            base_sandwich_speed_um_s: Base sandwich speed in µm/s
            layer_display_num: Layer number for status messages
            pause_time_s: Final pause time after sandwich completes
            stop_flag_callback: Optional callback to check if should stop
        
        Returns:
            True if sandwich completed successfully, False if aborted
        """
        # ========== ADAPTIVE SPEED SELECTION ==========
        # Check if we have adaptive speed from previous layer
        if (self.adaptive_sandwich_speed_um_s is not None and 
            self.sandwich_layer_count > 0):
            base_sandwich_speed = max(30.0, min(2000.0, self.adaptive_sandwich_speed_um_s))
            if base_sandwich_speed != self.adaptive_sandwich_speed_um_s:
                self.update_status(f"L{layer_display_num}: CLAMPED adaptive speed: "
                                 f"{self.adaptive_sandwich_speed_um_s:.0f}µm/s → {base_sandwich_speed:.0f}µm/s")
            else:
                self.update_status(f"L{layer_display_num}: Using ADAPTIVE speed: "
                                 f"{base_sandwich_speed:.0f}µm/s (from previous layer)")
        else:
            base_sandwich_speed = base_sandwich_speed_um_s
            self.update_status(f"L{layer_display_num}: Using USER speed: {base_sandwich_speed:.0f}µm/s")
        
        # Calculate 3-tier speeds (divide by 3 and 9)
        speed_tier1 = base_sandwich_speed
        speed_tier2 = base_sandwich_speed / 3.0
        speed_tier3 = base_sandwich_speed / 9.0
        
        # Force thresholds
        adaptive_force_threshold = contact_force_threshold * 0.75  # 75% - triggers stop
        relaxation_force_threshold = contact_force_threshold * 0.5  # 50% - relaxation target
        hard_failsafe_threshold = -5.0  # Absolute 5N limit
        
        # Calculate positions
        current_pos_um = self.axis.get_position(Units.LENGTH_MICROMETRES)
        gap_um = measured_gap_mm * 1000.0
        target_glass_um = layer_height_um
        
        waypoint_33pct_um = current_pos_um + (gap_um * 0.33)
        waypoint_67pct_um = current_pos_um + (gap_um * 0.67)
        
        self.update_status(f"L{layer_display_num}: ADAPTIVE SANDWICH - 3-Tier Ramping")
        self.update_status(f"L{layer_display_num}: Speeds: {speed_tier1:.0f}/{speed_tier2:.0f}/{speed_tier3:.0f}µm/s, Gap:{measured_gap_mm:.3f}mm")
        self.update_status(f"L{layer_display_num}: Thresholds: Adaptive=75% ({abs(adaptive_force_threshold):.3f}N), "
                         f"Relax=50% ({abs(relaxation_force_threshold):.3f}N), FAILSAFE=5N")
        
        # ========== ADAPTIVE DESCENT PHASE ==========
        speed_was_reduced = False
        final_tier3_speed = speed_tier3
        adaptive_iteration_count = 0
        max_adaptive_iterations = 3
        min_speed_floor = 30.0
        min_speed_floor_lifting = 15.0
        
        descent_segments = [
            (waypoint_33pct_um, speed_tier1, "1/3", "0-33%"),
            (waypoint_67pct_um, speed_tier2, "2/3", "33-67%"),
            (target_glass_um, speed_tier3, "3/3", "67-100%")
        ]
        
        reached_glass = False
        
        for seg_idx, (segment_target_um, initial_seg_speed, seg_label, seg_range) in enumerate(descent_segments):
            if reached_glass:
                break
            
            current_seg_speed = initial_seg_speed
            segment_start_pos = self.axis.get_position(Units.LENGTH_MICROMETRES)
            
            self.update_status(f"L{layer_display_num}: [DESCENT {seg_label}] "
                             f"{segment_start_pos/1000.0:.4f}mm → {segment_target_um/1000.0:.4f}mm "
                             f"@ {current_seg_speed:.0f}µm/s ({seg_range})")
            
            # Move toward segment target with adaptive behavior
            while not reached_glass:
                current_position = self.axis.get_position(Units.LENGTH_MICROMETRES)
                
                # Check if reached segment target
                if abs(current_position - segment_target_um) < 5.0:
                    self.update_status(f"L{layer_display_num}: [DESCENT {seg_label} DONE] "
                                     f"Reached: {current_position/1000.0:.4f}mm")
                    break
                
                # Start movement
                self.axis.move_absolute(
                    segment_target_um, Units.LENGTH_MICROMETRES, wait_until_idle=False,
                    velocity=current_seg_speed/1000.0, velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND,
                    acceleration=1000.0, acceleration_unit=Units.ACCELERATION_MILLIMETRES_PER_SECOND_SQUARED
                )
                
                # Monitor force during movement
                adaptive_stop_triggered = False
                while self.axis.is_busy():
                    if stop_flag_callback and stop_flag_callback():
                        self.axis.stop()
                        return False
                    
                    current_force = self.force_gauge.get_latest_calibrated_force()
                    
                    # Hard failsafe check
                    if current_force <= hard_failsafe_threshold:
                        self.axis.stop()
                        while self.axis.is_busy():
                            time.sleep(0.01)
                        self.update_status(f"L{layer_display_num}: *** HARD FAILSAFE *** "
                                         f"Force={current_force:.4f}N exceeded 5N limit", error=True)
                        return False
                    
                    # Adaptive stop check (75% threshold)
                    if current_force <= adaptive_force_threshold:
                        self.axis.stop()
                        while self.axis.is_busy():
                            time.sleep(0.01)
                        
                        adaptive_stop_triggered = True
                        stopped_pos = self.axis.get_position(Units.LENGTH_MICROMETRES)
                        self.update_status(f"L{layer_display_num}: *** ADAPTIVE STOP *** "
                                         f"Force={current_force:.4f}N at {stopped_pos/1000.0:.4f}mm")
                        break
                    
                    time.sleep(0.02)
                
                if stop_flag_callback and stop_flag_callback():
                    return False
                
                # Handle adaptive stop
                if adaptive_stop_triggered:
                    # Wait for axis to fully stop
                    while self.axis.is_busy():
                        time.sleep(0.01)
                    
                    force_at_stop = current_force
                    
                    # Wait for force relaxation (max 3 seconds)
                    self.update_status(f"L{layer_display_num}: Waiting for relaxation "
                                     f"(target: ≥{relaxation_force_threshold:.3f}N or 3s)...")
                    wait_start = time.time()
                    final_force = current_force
                    
                    while time.time() - wait_start < 3.0:
                        final_force = self.force_gauge.get_latest_calibrated_force()
                        if final_force >= relaxation_force_threshold:
                            self.update_status(f"L{layer_display_num}: Force relaxed to "
                                             f"{final_force:.4f}N after {time.time()-wait_start:.2f}s")
                            break
                        time.sleep(0.1)
                    
                    if final_force < relaxation_force_threshold:
                        self.update_status(f"L{layer_display_num}: 3s timeout, force={final_force:.4f}N")
                    
                    # Check force stability
                    force_change = final_force - force_at_stop
                    force_change_percent = (force_change / abs(force_at_stop)) * 100.0 if force_at_stop != 0 else 0.0
                    
                    self.update_status(f"L{layer_display_num}: Force stability: "
                                     f"{force_at_stop:.4f}N → {final_force:.4f}N (change: {force_change_percent:.1f}%)")
                    
                    # If force stable (<20% change), we're at glass
                    if abs(force_change_percent) < 20.0:
                        self.update_status(f"L{layer_display_num}: *** GLASS REACHED *** "
                                         f"Force stable (<20% change)")
                        reached_glass = True
                        break
                    
                    # Force relaxed significantly, adapt speed
                    adaptive_iteration_count += 1
                    
                    # Failsafe: max iterations reached
                    if adaptive_iteration_count >= max_adaptive_iterations:
                        self.update_status(f"L{layer_display_num}: *** FAILSAFE *** "
                                         f"{max_adaptive_iterations} adaptations reached, assuming glass")
                        reached_glass = True
                        break
                    
                    # Calculate new speed
                    new_speed = current_seg_speed * 0.5
                    if new_speed < min_speed_floor:
                        self.update_status(f"L{layer_display_num}: *** FAILSAFE *** "
                                         f"Speed floor reached ({min_speed_floor:.0f}µm/s), assuming glass")
                        reached_glass = True
                        break
                    
                    # Reduce speed by 50%
                    current_seg_speed = new_speed
                    final_tier3_speed = current_seg_speed
                    speed_was_reduced = True
                    self.update_status(f"L{layer_display_num}: Speed reduced to {current_seg_speed:.0f}µm/s "
                                     f"(iteration {adaptive_iteration_count}/{max_adaptive_iterations})")
                    continue
                
                # Movement completed normally
                final_pos = self.axis.get_position(Units.LENGTH_MICROMETRES)
                
                # Check if reached glass
                if abs(final_pos - target_glass_um) < 5.0:
                    reached_glass = True
                    self.update_status(f"L{layer_display_num}: Reached glass at {final_pos/1000.0:.4f}mm")
                
                break
        
        final_descent_pos_um = self.axis.get_position(Units.LENGTH_MICROMETRES)
        self.update_status(f"L{layer_display_num}: [DESCENT COMPLETE] Final: {final_descent_pos_um/1000.0:.4f}mm")
        
        # ========== SPEED ADAPTATION FOR NEXT LAYER ==========
        if speed_was_reduced:
            new_base_speed = final_tier3_speed * 9.0
            self.adaptive_sandwich_speed_um_s = new_base_speed
            self.update_status(f"L{layer_display_num}: *** SPEED ADAPTED *** "
                             f"New base for next layer: {new_base_speed:.0f}µm/s (Tier3={final_tier3_speed:.0f}µm/s)")
        
        # ========== ASCENT PHASE ==========
        # Use adapted speeds if reduced
        if speed_was_reduced:
            ascent_tier1 = final_tier3_speed * 9.0
            ascent_tier2 = final_tier3_speed * 3.0
            ascent_tier3 = final_tier3_speed
        else:
            ascent_tier1 = speed_tier1
            ascent_tier2 = speed_tier2
            ascent_tier3 = speed_tier3
        
        # Apply minimum speed floors
        ascent_tier3 = max(min_speed_floor_lifting, ascent_tier3)
        ascent_tier2 = max(min_speed_floor, ascent_tier2)
        ascent_tier1 = max(min_speed_floor, ascent_tier1)
        
        distance_from_glass_um = abs(final_descent_pos_um - target_glass_um)
        
        self.update_status(f"L{layer_display_num}: ========== STARTING ASCENT ==========")
        self.update_status(f"L{layer_display_num}: Distance from glass: {distance_from_glass_um:.1f}µm")
        
        # Choose ascent strategy based on distance from glass
        pause_half = pause_time_s / 2.0 if pause_time_s > 0 else 0
        
        if distance_from_glass_um <= 200.0:
            # 4-tier ascent for ultra-close to glass (Stefan adhesion risk)
            ascent_tier4 = max(min_speed_floor_lifting, ascent_tier3 / 2.0)
            speeds = [ascent_tier4, ascent_tier3, ascent_tier2, ascent_tier1]
            waypoints = [0.10, 0.33, 0.50]  # Pause will be at 0.50
            
            self.update_status(f"L{layer_display_num}: Speeds: {ascent_tier4:.0f}→{ascent_tier3:.0f}→"
                             f"{ascent_tier2:.0f}µm/s, PAUSE, then {ascent_tier1:.0f}µm/s")
            
            self.perform_multitier_ascent(
                final_descent_pos_um, layer_height_um, speeds, waypoints,
                pause_half, layer_display_num
            )
        else:
            # 3-tier ascent for standard distance
            speeds = [ascent_tier3, ascent_tier2, ascent_tier1]
            waypoints = [0.33, 0.50]  # Pause will be at 0.50
            
            self.update_status(f"L{layer_display_num}: Speeds: {ascent_tier3:.0f}→{ascent_tier2:.0f}µm/s, "
                             f"PAUSE, then {ascent_tier1:.0f}µm/s")
            
            self.perform_multitier_ascent(
                final_descent_pos_um, layer_height_um, speeds, waypoints,
                pause_half, layer_display_num
            )
        
        self.update_status(f"L{layer_display_num}: [ASCENT COMPLETE] At layer height")
        
        # Pause at layer height (second half of pause)
        if pause_time_s > 0:
            self.update_status(f"L{layer_display_num}: [ASCENT PAUSE 2/2] {pause_half:.1f}s at layer height")
            time.sleep(pause_half)
        
        # Increment layer counter
        self.sandwich_layer_count += 1
        
        self.update_status(f"L{layer_display_num}: ========== ADAPTIVE SANDWICH COMPLETE ==========")
        return True
    
    def execute_classic_sandwich(self, layer_height_um, measured_gap_mm, contact_force_threshold,
                                 base_sandwich_speed_um_s, layer_display_num, pause_time_s=0.0,
                                 stop_flag_callback=None):
        """
        Execute classic 4-tier sandwich routine.
        
        This is the original sandwich implementation with:
        - 4-tier descent: 0-50%, 50-75%, 75-100µm from glass, last 100µm
        - Force monitoring stops descent if threshold reached
        - 4-tier symmetrical ascent with pause at 50%
        
        Args:
            layer_height_um: Target layer height in micrometers
            measured_gap_mm: Measured gap from calibration in millimeters
            contact_force_threshold: Force threshold for contact detection
            base_sandwich_speed_um_s: Base sandwich speed in µm/s
            layer_display_num: Layer number for status messages
            pause_time_s: Pause time at 50% ascent
            stop_flag_callback: Optional callback to check if should stop
        
        Returns:
            True if sandwich completed successfully, False if aborted
        """
        # Calculate 4-tier speeds (divide by 2, 4, 8)
        speed_tier1 = base_sandwich_speed_um_s
        speed_tier2 = base_sandwich_speed_um_s / 2.0
        speed_tier3 = base_sandwich_speed_um_s / 4.0
        speed_tier4 = min(50.0, base_sandwich_speed_um_s / 8.0)  # Last 100µm, capped at 50µm/s
        
        current_pos_um = self.axis.get_position(Units.LENGTH_MICROMETRES)
        gap_um = measured_gap_mm * 1000.0
        target_glass_um = layer_height_um
        
        self.update_status(f"L{layer_display_num}: CLASSIC SANDWICH - 4-Tier Ramping")
        self.update_status(f"L{layer_display_num}: Speeds: {speed_tier1:.0f}/{speed_tier2:.0f}/"
                         f"{speed_tier3:.0f}/{speed_tier4:.0f}µm/s, Gap:{measured_gap_mm:.3f}mm")
        
        # ========== DESCENT PHASE (4 TIERS) ==========
        # Calculate waypoints
        waypoint_50pct_um = current_pos_um + (gap_um * 0.5)
        waypoint_75pct_um = current_pos_um + (gap_um * 0.75)
        waypoint_100um_before_glass_um = target_glass_um - 100.0
        
        descent_segments = [
            (waypoint_50pct_um, speed_tier1, "1/4", "0-50%"),
            (waypoint_75pct_um, speed_tier2, "2/4", "50-75%"),
            (waypoint_100um_before_glass_um, speed_tier3, "3/4", "75-last 100µm"),
            (target_glass_um, speed_tier4, "4/4", "Last 100µm")
        ]
        
        for target, speed, label, desc in descent_segments:
            stopped_early, final_pos, reason = self._move_with_force_monitoring(
                target, speed, contact_force_threshold, contact_force_threshold,
                layer_display_num, label, stop_flag_callback
            )
            
            if reason == "abort":
                return False
            elif reason in ["threshold", "safety"]:
                self.update_status(f"L{layer_display_num}: Contact detected at {final_pos/1000.0:.4f}mm")
                break
        
        final_descent_pos_um = self.axis.get_position(Units.LENGTH_MICROMETRES)
        self.update_status(f"L{layer_display_num}: [DESCENT COMPLETE] At glass: {final_descent_pos_um/1000.0:.4f}mm")
        
        # ========== ASCENT PHASE (4 TIERS WITH PAUSE) ==========
        self.update_status(f"L{layer_display_num}: ========== STARTING ASCENT ==========")
        
        # Calculate ascent waypoints
        waypoint_100um_after_glass_um = final_descent_pos_um - 100.0
        distance_to_layer_um = abs(layer_height_um - final_descent_pos_um)
        waypoint_25pct_up_um = final_descent_pos_um - (distance_to_layer_um * 0.25)
        waypoint_50pct_up_um = final_descent_pos_um - (distance_to_layer_um * 0.5)
        
        # Segment 1: First 100µm from glass (slowest)
        self.update_status(f"L{layer_display_num}: [ASCENT 1/4] @ {speed_tier4:.0f}µm/s")
        self._move_segment(waypoint_100um_after_glass_um, speed_tier4, layer_display_num, "ASCENT 1/4")
        
        # Segment 2: To 25% complete
        self.update_status(f"L{layer_display_num}: [ASCENT 2/4] @ {speed_tier3:.0f}µm/s")
        self._move_segment(waypoint_25pct_up_um, speed_tier3, layer_display_num, "ASCENT 2/4")
        
        # Segment 3: To 50% complete
        self.update_status(f"L{layer_display_num}: [ASCENT 3/4] @ {speed_tier2:.0f}µm/s")
        self._move_segment(waypoint_50pct_up_um, speed_tier2, layer_display_num, "ASCENT 3/4")
        
        # Pause at 50%
        if pause_time_s > 0:
            self.update_status(f"L{layer_display_num}: [PAUSE] {pause_time_s:.1f}s at 50%")
            time.sleep(pause_time_s)
        
        # Segment 4: Final 50% to layer height (fastest)
        self.update_status(f"L{layer_display_num}: [ASCENT 4/4] @ {speed_tier1:.0f}µm/s")
        self._move_segment(layer_height_um, speed_tier1, layer_display_num, "ASCENT 4/4")
        
        self.update_status(f"L{layer_display_num}: [ASCENT COMPLETE] At layer height")
        self.update_status(f"L{layer_display_num}: ========== CLASSIC SANDWICH COMPLETE ==========")
        return True

    # ========================================
    # PRE-CALIBRATION ROUTINE
    # ========================================

    def perform_precalibration(self, gap_estimate_mm, contact_force_threshold, 
                               sandwich_speed_um_s, stop_flag_callback=None):
        """
        Simplified pre-calibration routine using force threshold (no derivative).
        
        Performs 5 touches to measure average gap:
        - First touch: Full 3-tier descent from start position
        - Touches 2-5: Single-speed descent from 200µm above glass
        - 3-tier ascent after each touch (200µm retraction)
        - 1s pause between touches
        
        Args:
            gap_estimate_mm: Estimated gap distance (for search limit and waypoints)
            contact_force_threshold: Force threshold for contact detection (N, positive)
            sandwich_speed_um_s: Base speed matching sandwich routine
            stop_flag_callback: Optional callback that returns True if user stopped
            
        Returns:
            Average gap in mm, or None on failure
        """
        try:
            self.update_status("=== STARTING PRE-CALIBRATION ===")
            
            # Validate force gauge
            if not hasattr(self, 'force_gauge') or self.force_gauge is None:
                self.update_status("Pre-cal failed: No force gauge", error=True)
                return None
            
            force_threshold = -abs(contact_force_threshold)  # Negative for compression
            
            # Record starting position
            start_position_um = self.axis.get_position(Units.LENGTH_MICROMETRES)
            start_position_mm = start_position_um / 1000.0
            
            # Calculate search limits
            expected_glass_mm = start_position_mm + gap_estimate_mm
            max_search_mm = expected_glass_mm + 0.5  # 500µm safety margin
            max_search_um = max_search_mm * 1000.0
            
            self.update_status(f"Pre-cal: Start={start_position_mm:.3f}mm, Search to={max_search_mm:.3f}mm")
            self.update_status(f"Pre-cal: Contact threshold={contact_force_threshold:.3f}N")
            
            # Calculate 3-tier speeds
            speed_tier1 = sandwich_speed_um_s        # 0-50%
            speed_tier2 = sandwich_speed_um_s / 2.0  # 50-75%
            speed_tier3 = sandwich_speed_um_s / 4.0  # 75-100%
            
            self.update_status(f"Pre-cal: Speeds={speed_tier1:.0f}→{speed_tier2:.0f}→{speed_tier3:.0f}µm/s")
            
            contact_positions_um = []
            
            # Perform 5 touches
            for touch_num in range(5):
                if stop_flag_callback and stop_flag_callback():
                    raise Exception("Pre-calibration stopped by user")
                
                current_pos_um = self.axis.get_position(Units.LENGTH_MICROMETRES)
                contact_found = False
                contact_pos_um = None
                
                if touch_num == 0:
                    # First touch: Full 3-tier descent
                    self.update_status(f"Pre-cal: Touch {touch_num + 1}/5 - 3-tier descent")
                    gap_um = gap_estimate_mm * 1000.0
                    
                    # Calculate waypoints
                    waypoint_50pct_um = current_pos_um + (gap_um * 0.5)
                    waypoint_75pct_um = current_pos_um + (gap_um * 0.75)
                    
                    # Segment 1: 0→50%
                    stopped, final_pos, reason = self._move_with_force_monitoring(
                        target_um=waypoint_50pct_um,
                        speed_um_s=speed_tier1,
                        force_threshold=force_threshold,
                        safety_limit=force_threshold * 2.0,  # 200% safety
                        layer_num=0,
                        tier_label="PRE-CAL 1/3",
                        stop_flag_callback=stop_flag_callback
                    )
                    
                    if stopped:
                        if reason == "threshold":
                            contact_found = True
                            contact_pos_um = final_pos
                    
                    # Segment 2: 50→75% (if no contact yet)
                    if not contact_found:
                        stopped, final_pos, reason = self._move_with_force_monitoring(
                            target_um=waypoint_75pct_um,
                            speed_um_s=speed_tier2,
                            force_threshold=force_threshold,
                            safety_limit=force_threshold * 2.0,
                            layer_num=0,
                            tier_label="PRE-CAL 2/3",
                            stop_flag_callback=stop_flag_callback
                        )
                        
                        if stopped:
                            if reason == "threshold":
                                contact_found = True
                                contact_pos_um = final_pos
                    
                    # Segment 3: 75→100% (if no contact yet)
                    if not contact_found:
                        stopped, final_pos, reason = self._move_with_force_monitoring(
                            target_um=max_search_um,
                            speed_um_s=speed_tier3,
                            force_threshold=force_threshold,
                            safety_limit=force_threshold * 2.0,
                            layer_num=0,
                            tier_label="PRE-CAL 3/3",
                            stop_flag_callback=stop_flag_callback
                        )
                        
                        if stopped:
                            if reason == "threshold":
                                contact_found = True
                                contact_pos_um = final_pos
                else:
                    # Subsequent touches: Single-speed descent (already near glass)
                    self.update_status(f"Pre-cal: Touch {touch_num + 1}/5 - Single speed ({speed_tier3:.0f}µm/s)")
                    
                    stopped, final_pos, reason = self._move_with_force_monitoring(
                        target_um=max_search_um,
                        speed_um_s=speed_tier3,
                        force_threshold=force_threshold,
                        safety_limit=force_threshold * 2.0,
                        layer_num=0,
                        tier_label=f"PRE-CAL {touch_num + 1}/5",
                        stop_flag_callback=stop_flag_callback
                    )
                    
                    if stopped and reason == "threshold":
                        contact_found = True
                        contact_pos_um = final_pos
                
                # Record result
                if contact_found:
                    contact_positions_um.append(contact_pos_um)
                    gap_measured = (contact_pos_um - start_position_um) / 1000.0
                    current_force = self.force_gauge.get_latest_calibrated_force()
                    self.update_status(
                        f"Pre-cal: Touch {touch_num + 1}/5 - Contact at {contact_pos_um/1000.0:.3f}mm "
                        f"(Gap={gap_measured:.3f}mm, Force={current_force:.4f}N)"
                    )
                else:
                    self.update_status(f"Pre-cal: Touch {touch_num + 1}/5 - No contact", error=True)
                
                # Retract 200µm with 3-tier ascent (if not last touch)
                if touch_num < 4 and contact_found:
                    retract_pos_um = contact_pos_um - 200.0
                    retract_distance_um = 200.0
                    
                    # Calculate symmetric ascent waypoints
                    waypoint_75pct_up_um = contact_pos_um - (retract_distance_um * 0.25)  # First 25%
                    waypoint_50pct_up_um = contact_pos_um - (retract_distance_um * 0.5)   # To 50%
                    
                    # 3-tier ascent
                    self._move_segment(waypoint_75pct_up_um, speed_tier3, 0, "PRE-CAL ASCENT 1/3")
                    self._move_segment(waypoint_50pct_up_um, speed_tier2, 0, "PRE-CAL ASCENT 2/3")
                    self._move_segment(retract_pos_um, speed_tier1, 0, "PRE-CAL ASCENT 3/3")
                    
                    self.update_status("Pre-cal: Pausing 1s before next touch...")
                    time.sleep(1.0)
            
            # Calculate average gap
            if len(contact_positions_um) < 2:
                self.update_status("Pre-cal: Insufficient contacts for averaging", error=True)
                self.axis.move_absolute(
                    position=start_position_um,
                    unit=Units.LENGTH_MICROMETRES,
                    wait_until_idle=True,
                    velocity=0.5,
                    velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND
                )
                return None
            
            avg_contact_pos_um = sum(contact_positions_um) / len(contact_positions_um)
            avg_gap_mm = (avg_contact_pos_um - start_position_um) / 1000.0
            
            self.update_status(f"Pre-cal: Average gap from {len(contact_positions_um)} contacts = {avg_gap_mm:.3f}mm")
            
            # Return to start
            self.update_status("Pre-cal: Returning to start position...")
            self.axis.move_absolute(
                position=start_position_um,
                unit=Units.LENGTH_MICROMETRES,
                wait_until_idle=True,
                velocity=0.5,
                velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND,
                acceleration=1000.0,
                acceleration_unit=Units.ACCELERATION_MILLIMETRES_PER_SECOND_SQUARED
            )
            
            self.update_status("Pre-cal: Pausing 3s before starting print...")
            time.sleep(3.0)
            
            self.update_status(f"=== PRE-CALIBRATION COMPLETE: Gap={avg_gap_mm:.3f}mm ===")
            return avg_gap_mm
            
        except Exception as e:
            self.update_status(f"Pre-calibration error: {e}", error=True)
            try:
                # Try to return to start on error
                self.axis.move_absolute(
                    position=start_position_um,
                    unit=Units.LENGTH_MICROMETRES,
                    wait_until_idle=True,
                    velocity=0.5,
                    velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND
                )
            except:
                pass
            return None
