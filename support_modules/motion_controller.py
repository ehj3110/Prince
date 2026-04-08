"""
Motion Controller for 3D Printing Operations

Handles specialized motion control strategies for peel and retraction movements:
- Smooth lifting: Multi-stage velocity ramping to ease hydrodynamic lock
- Smooth retraction: Low acceleration to prevent stage stalls
- Smart peeling: Force-based detection of peel completion (future)

Author: GitHub Copilot
Date: January 10, 2026
"""

from zaber_motion import Units
from typing import Optional, Dict, Tuple
import time


class MotionController:
    """
    Coordinates specialized motion control strategies for 3D printing.
    
    Provides smooth lifting (ramped velocity) and smooth retraction (gentle acceleration)
    to prevent mechanical issues during printing.
    """
    
    def __init__(self, axis, force_gauge_manager=None):
        """
        Initialize the motion controller.
        
        Args:
            axis: Zaber axis object for stage control
            force_gauge_manager: Optional force gauge for smart peeling (future feature)
        """
        self.axis = axis
        self.force_gauge = force_gauge_manager
        
        # Default configuration for smooth lifting (2-stage)
        # Inverted stage: target_pos < start_pos (moving to lower position values = upward in real space)
        self.smooth_lift_config = {
            'stage1_distance_um': 50,       # First segment: 50µm
            'stage1_velocity_um_s': 100,    # At 100µm/s (gentle initial break)
            # Stage 2: Remaining distance at base velocity
        }
        
        # Default configuration for smooth retraction (2-stage, symmetric to lifting)
        # Inverted stage: target_pos > start_pos (moving to higher position values = downward in real space)
        self.smooth_retraction_config = {
            'stage1_distance_um': 200,      # First segment: 200µm
            'stage1_velocity_um_s': 100,    # At 100µm/s (gentle approach to window)
            # Stage 2: Remaining distance at base velocity
        }
    
    def execute_lift(self, 
                    start_pos_um: float,
                    target_pos_um: float, 
                    base_velocity_um_s: float,
                    base_acceleration_um_s2: float,
                    smooth_enabled: bool = False,
                    smart_peel_enabled: bool = False,
                    phase_callback = None) -> Dict:
        """
        Execute peel/lift movement with optional smoothing and smart detection.
        
        Args:
            start_pos_um: Starting position in micrometers
            target_pos_um: Target position in micrometers (lower value for upward motion)
            base_velocity_um_s: Base velocity for normal/final segment
            base_acceleration_um_s2: Acceleration for movement
            smooth_enabled: Enable multi-stage velocity ramping
            smart_peel_enabled: Enable force-based early termination (not yet implemented)
            phase_callback: Optional callback function to report phase changes (e.g., "Lift-Stage1", "Lift-Stage2", "Lift-Stage3")
            
        Returns:
            Dict with movement results:
                - 'success': bool
                - 'final_position_um': float
                - 'movement_time_s': float
                - 'early_stop': bool (if smart peel triggered)
                - 'segments_completed': int
        """
        start_time = time.time()
        
        if not smooth_enabled:
            # Standard single-stage lift
            return self._single_stage_lift(
                target_pos_um, base_velocity_um_s, base_acceleration_um_s2, start_time, phase_callback
            )
        else:
            # Multi-stage smooth lift
            return self._smooth_multi_stage_lift(
                start_pos_um, target_pos_um, base_velocity_um_s, 
                base_acceleration_um_s2, smart_peel_enabled, start_time, phase_callback
            )
    
    def execute_retraction(self,
                          start_pos_um: float,
                          target_pos_um: float,
                          base_velocity_um_s: float,
                          base_acceleration_um_s2: float,
                          smooth_enabled: bool = False,
                          phase_callback = None) -> Dict:
        """
        Execute retraction/return movement with optional 2-stage velocity ramping.
        Symmetric to smooth lifting but in reverse direction.
        
        Args:
            start_pos_um: Starting position in micrometers
            target_pos_um: Target position in micrometers (higher value for downward motion on inverted stage)
            base_velocity_um_s: Velocity for normal/initial segment
            base_acceleration_um_s2: Acceleration for movement
            smooth_enabled: Enable 2-stage velocity ramping (slow final approach)
            phase_callback: Optional callback to report phase changes
            
        Returns:
            Dict with movement results:
                - 'success': bool
                - 'final_position_um': float
                - 'movement_time_s': float
                - 'segments_completed': int
        """
        start_time = time.time()
        
        if not smooth_enabled:
            # Standard single-stage retraction
            return self._single_stage_retraction(
                target_pos_um, base_velocity_um_s, base_acceleration_um_s2, start_time, phase_callback
            )
        else:
            # Multi-stage smooth retraction (symmetric to lifting)
            return self._smooth_multi_stage_retraction(
                start_pos_um, target_pos_um, base_velocity_um_s,
                base_acceleration_um_s2, start_time, phase_callback
            )
    
    def _single_stage_lift(self, target_pos_um, velocity_um_s, 
                          acceleration_um_s2, start_time, phase_callback=None) -> Dict:
        """Execute standard single-stage lift movement."""
        try:
            # Report phase as "Lift" for standard single-stage
            if phase_callback:
                phase_callback("Lift")
            
            self.axis.move_absolute(
                position=target_pos_um,
                unit=Units.LENGTH_MICROMETRES,
                wait_until_idle=True,
                velocity=velocity_um_s,
                velocity_unit=Units.VELOCITY_MICROMETRES_PER_SECOND,
                acceleration=acceleration_um_s2,
                acceleration_unit=Units.ACCELERATION_MICROMETRES_PER_SECOND_SQUARED
            )
            
            final_pos = self.axis.get_position(unit=Units.LENGTH_MICROMETRES)
            elapsed_time = time.time() - start_time
            
            return {
                'success': True,
                'final_position_um': final_pos,
                'movement_time_s': elapsed_time,
                'early_stop': False,
                'segments_completed': 1
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'movement_time_s': time.time() - start_time,
                'segments_completed': 0
            }
    
    def _smooth_multi_stage_lift(self, start_pos_um, target_pos_um, 
                                base_velocity_um_s, base_acceleration_um_s2,
                                smart_peel_enabled, start_time, phase_callback=None) -> Dict:
        """
        Execute 2-stage lift with velocity ramping.
        Inverted stage: target_pos < start_pos (moving to lower position values = upward in real space)
        
        Stage 1: 0-50µm at 100µm/s (gentle initial break of hydrodynamic lock)
        Stage 2: 50µm+ at base_velocity (normal peel speed)
        """
        config = self.smooth_lift_config
        segments_completed = 0
        
        try:
            # Calculate segment positions
            # For inverted stage: target_pos < start_pos (moving to lower values = upward)
            total_distance = abs(target_pos_um - start_pos_um)
            
            # Stage 1: First 50µm at 100µm/s
            seg1_distance = min(config['stage1_distance_um'], total_distance)
            seg1_pos = start_pos_um - seg1_distance  # Moving upward (lower position value)
            
            # Stage 1: Gentle initial break (0-50µm at 100µm/s)
            if seg1_distance > 0:
                # Report phase as "Lift-Stage1"
                if phase_callback:
                    phase_callback("Lift-Stage1")
                
                self.axis.move_absolute(
                    position=seg1_pos,
                    unit=Units.LENGTH_MICROMETRES,
                    wait_until_idle=True,
                    velocity=config['stage1_velocity_um_s'],
                    velocity_unit=Units.VELOCITY_MICROMETRES_PER_SECOND,
                    acceleration=base_acceleration_um_s2,
                    acceleration_unit=Units.ACCELERATION_MICROMETRES_PER_SECOND_SQUARED
                )
                segments_completed = 1
                
                # Check if smart peel detected completion
                if smart_peel_enabled and self._check_peel_complete():
                    final_pos = self.axis.get_position(unit=Units.LENGTH_MICROMETRES)
                    return {
                        'success': True,
                        'final_position_um': final_pos,
                        'movement_time_s': time.time() - start_time,
                        'early_stop': True,
                        'segments_completed': segments_completed
                    }
            
            # Stage 2: Normal prescribed speed (50µm+ at base_velocity)
            remaining_distance = abs(target_pos_um - seg1_pos)
            if remaining_distance > 0:
                # Report phase as "Lift-Stage2" (prescribed speed)
                if phase_callback:
                    phase_callback("Lift-Stage2")
                
                self.axis.move_absolute(
                    position=target_pos_um,
                    unit=Units.LENGTH_MICROMETRES,
                    wait_until_idle=True,
                    velocity=base_velocity_um_s,
                    velocity_unit=Units.VELOCITY_MICROMETRES_PER_SECOND,
                    acceleration=base_acceleration_um_s2,
                    acceleration_unit=Units.ACCELERATION_MICROMETRES_PER_SECOND_SQUARED
                )
                segments_completed = 2
            
            final_pos = self.axis.get_position(unit=Units.LENGTH_MICROMETRES)
            elapsed_time = time.time() - start_time
            
            return {
                'success': True,
                'final_position_um': final_pos,
                'movement_time_s': elapsed_time,
                'early_stop': False,
                'segments_completed': segments_completed
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'movement_time_s': time.time() - start_time,
                'segments_completed': 0
            }
    
    def _single_stage_retraction(self, target_pos_um, velocity_um_s,
                                acceleration_um_s2, start_time, phase_callback=None) -> Dict:
        """Execute standard single-stage retraction movement."""
        try:
            # Report phase as "Retract" for standard single-stage
            if phase_callback:
                phase_callback("Retract")
            
            self.axis.move_absolute(
                position=target_pos_um,
                unit=Units.LENGTH_MICROMETRES,
                wait_until_idle=True,
                velocity=velocity_um_s,
                velocity_unit=Units.VELOCITY_MICROMETRES_PER_SECOND,
                acceleration=acceleration_um_s2,
                acceleration_unit=Units.ACCELERATION_MICROMETRES_PER_SECOND_SQUARED
            )
            
            final_pos = self.axis.get_position(unit=Units.LENGTH_MICROMETRES)
            elapsed_time = time.time() - start_time
            
            return {
                'success': True,
                'final_position_um': final_pos,
                'movement_time_s': elapsed_time,
                'segments_completed': 1
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'movement_time_s': time.time() - start_time,
                'segments_completed': 0
            }
    
    def _smooth_multi_stage_retraction(self, start_pos_um, target_pos_um,
                                      base_velocity_um_s, base_acceleration_um_s2,
                                      start_time, phase_callback=None) -> Dict:
        """
        Execute 2-stage retraction with velocity ramping (symmetric to lifting).
        Inverted stage: target_pos > start_pos (moving to higher position values = downward in real space)
        
        Stage 1: Most of distance at base_velocity (fast approach)
        Stage 2: Last 200µm at 100µm/s (gentle approach to window)
        """
        config = self.smooth_retraction_config
        segments_completed = 0
        
        try:
            # Calculate segment positions
            # For inverted stage: target_pos > start_pos (moving to higher values = downward)
            total_distance = abs(target_pos_um - start_pos_um)
            
            # Stage 2 (final) will be the last 200µm at slow speed
            seg2_distance = min(config['stage1_distance_um'], total_distance)
            seg2_start_pos = target_pos_um - seg2_distance  # 200µm before target
            
            # Stage 1: Fast approach (all but last 200µm at base_velocity)
            seg1_distance = total_distance - seg2_distance
            if seg1_distance > 0:
                # Report phase as "Retract-Stage1"
                if phase_callback:
                    phase_callback("Retract-Stage1")
                
                self.axis.move_absolute(
                    position=seg2_start_pos,
                    unit=Units.LENGTH_MICROMETRES,
                    wait_until_idle=True,
                    velocity=base_velocity_um_s,
                    velocity_unit=Units.VELOCITY_MICROMETRES_PER_SECOND,
                    acceleration=base_acceleration_um_s2,
                    acceleration_unit=Units.ACCELERATION_MICROMETRES_PER_SECOND_SQUARED
                )
                segments_completed = 1
            
            # Stage 2: Gentle final approach (last 200µm at 100µm/s)
            if seg2_distance > 0:
                # Report phase as "Retract-Stage2"
                if phase_callback:
                    phase_callback("Retract-Stage2")
                
                self.axis.move_absolute(
                    position=target_pos_um,
                    unit=Units.LENGTH_MICROMETRES,
                    wait_until_idle=True,
                    velocity=config['stage1_velocity_um_s'],
                    velocity_unit=Units.VELOCITY_MICROMETRES_PER_SECOND,
                    acceleration=base_acceleration_um_s2,
                    acceleration_unit=Units.ACCELERATION_MICROMETRES_PER_SECOND_SQUARED
                )
                segments_completed = 2
            
            final_pos = self.axis.get_position(unit=Units.LENGTH_MICROMETRES)
            elapsed_time = time.time() - start_time
            
            return {
                'success': True,
                'final_position_um': final_pos,
                'movement_time_s': elapsed_time,
                'segments_completed': segments_completed
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'movement_time_s': time.time() - start_time,
                'segments_completed': 0
            }
    
    def _check_peel_complete(self) -> bool:
        """
        Check if peel is complete based on force signature.
        
        Returns:
            True if peel detected as complete, False otherwise
            
        Note: Not yet implemented - placeholder for smart peeling feature
        """
        # TODO: Implement smart peel detection
        # - Monitor force level and rate of change
        # - Return True when force drops below threshold
        # - Or when force decay rate slows (propagation complete)
        return False
    
    def configure_smooth_lift(self, 
                             stage1_distance_um: Optional[int] = None,
                             stage1_velocity_um_s: Optional[int] = None):
        """
        Configure smooth lift parameters for 2-stage ramping.
        
        Args:
            stage1_distance_um: Distance for gentle initial segment (default: 50µm)
            stage1_velocity_um_s: Velocity for first segment (default: 100µm/s)
        """
        if stage1_distance_um is not None:
            self.smooth_lift_config['stage1_distance_um'] = stage1_distance_um
        if stage1_velocity_um_s is not None:
            self.smooth_lift_config['stage1_velocity_um_s'] = stage1_velocity_um_s
    
    def configure_smooth_retraction(self, 
                                   stage1_distance_um: Optional[int] = None,
                                   stage1_velocity_um_s: Optional[int] = None):
        """
        Configure smooth retraction parameters for 2-stage ramping.
        
        Args:
            stage1_distance_um: Distance for gentle final segment (default: 200µm)
            stage1_velocity_um_s: Velocity for final segment (default: 100µm/s)
        """
        if stage1_distance_um is not None:
            self.smooth_retraction_config['stage1_distance_um'] = stage1_distance_um
        if stage1_velocity_um_s is not None:
            self.smooth_retraction_config['stage1_velocity_um_s'] = stage1_velocity_um_s


# Example usage and testing
if __name__ == '__main__':
    from support_modules.DebugSupport import debug_print

    debug_print("MotionController module loaded successfully.", force=True)
    debug_print("\nDefault configurations:", force=True)
    
    controller = MotionController(axis=None)
    
    debug_print("\nSmooth Lift Config:", force=True)
    for key, value in controller.smooth_lift_config.items():
        debug_print(f"  {key}: {value}", force=True)
    
    debug_print("\nSmooth Retraction Config:", force=True)
    for key, value in controller.smooth_retraction_config.items():
        debug_print(f"  {key}: {value}", force=True)
    
    debug_print("\nMotion profiles (2-stage symmetric):", force=True)
    debug_print("  Lift Stage 1: 0-50µm at 100µm/s (gentle hydrodynamic break)", force=True)
    debug_print("  Lift Stage 2: 50µm+ at base velocity (normal peel)", force=True)
    debug_print("  Retraction Stage 1: Most distance at base velocity (fast approach)", force=True)
    debug_print("  Retraction Stage 2: Last 200µm at 100µm/s (gentle approach to window)", force=True)
