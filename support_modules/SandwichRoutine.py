import time
import threading
from zaber_motion import Units

class SandwichRoutine(threading.Thread):
    """
    Performs a 'sandwich' step: moves down until hitting glass window at a force threshold,
    then retracts back up to the proper layer height.
    
    This prevents punching through the glass window while ensuring good contact.
    """
    
    def __init__(self, zaber_axis, force_gauge_manager, 
                 target_layer_height, estimated_glass_gap,
                 contact_force_threshold,
                 status_callback, result_callback):
        """
        Initialize the sandwich routine.
        
        Args:
            zaber_axis: Zaber motor axis object
            force_gauge_manager: ForceGaugeManager instance
            target_layer_height: The final position where the stage should end up (mm)
            estimated_glass_gap: Your guess for how far the glass is below target (mm, positive value)
            contact_force_threshold: Force value to detect glass contact (N, negative value like -0.05)
            status_callback: Function to call with status messages
            result_callback: Function to call when complete (success_flag, message)
        """
        super().__init__()
        self.daemon = True
        self.zaber_axis = zaber_axis
        self.force_gauge_manager = force_gauge_manager
        self.target_layer_height = target_layer_height
        self.estimated_glass_gap = estimated_glass_gap
        self.contact_force_threshold = contact_force_threshold
        self.status_callback = status_callback
        self.result_callback = result_callback
        
        # Configurable parameters
        self.approach_speed = 0.5  # mm/s - slow approach to glass
        self.retract_speed = 1.0   # mm/s - speed to retract back up
        self.max_travel_beyond_estimate = 0.5  # mm - safety limit beyond estimated gap
        self.force_check_interval = 0.02  # seconds between force readings
        
        self._stop_event = threading.Event()
        self.log_to_terminal = True
        
        # Store results
        self.glass_contact_position = None
        self.actual_glass_gap = None
    
    def _log(self, message):
        """Helper for conditional logging to terminal."""
        if self.log_to_terminal:
            print(f"SandwichRoutine: {message}")
        if self.status_callback:
            self.status_callback(message)
    
    def stop(self):
        """Stop the sandwich routine."""
        self._stop_event.set()
    
    def _get_force(self):
        """Get current force reading."""
        if self.force_gauge_manager:
            force = self.force_gauge_manager.get_latest_calibrated_force()
            return force
        return None
    
    def run(self):
        """Execute the sandwich routine."""
        try:
            self._log("=== Sandwich Routine Started ===")
            
            # Validate force gauge is ready
            if not self.force_gauge_manager or not self.force_gauge_manager.is_calibrated():
                self._log("ERROR: Force gauge not calibrated.")
                if self.result_callback:
                    self.result_callback(False, "Force gauge not calibrated.")
                return
            
            # Get current position
            current_pos = self.zaber_axis.get_position(Units.LENGTH_MILLIMETRES)
            self._log(f"Current position: {current_pos:.4f} mm")
            self._log(f"Target layer height: {self.target_layer_height:.4f} mm")
            self._log(f"Estimated glass gap: {self.estimated_glass_gap:.3f} mm")
            
            if self._stop_event.is_set():
                return
            
            # Calculate where we expect the glass to be
            # (Remember: negative is up, so glass is at target_layer_height + estimated_glass_gap)
            expected_glass_position = self.target_layer_height + self.estimated_glass_gap
            max_down_position = expected_glass_position + self.max_travel_beyond_estimate
            
            self._log(f"Expected glass position: ~{expected_glass_position:.4f} mm")
            self._log(f"Will search down to: {max_down_position:.4f} mm (safety limit)")
            
            # Get baseline force
            time.sleep(0.2)  # Brief pause to stabilize
            baseline_force = self._get_force()
            if baseline_force is None:
                self._log("ERROR: Could not get baseline force reading.")
                if self.result_callback:
                    self.result_callback(False, "Could not read force gauge.")
                return
            
            self._log(f"Baseline force: {baseline_force:.4f} N")
            self._log(f"Contact threshold: {self.contact_force_threshold:.4f} N")
            
            if self._stop_event.is_set():
                return
            
            # ===== PHASE 1: MOVE DOWN TO GLASS =====
            self._log(f"Phase 1: Moving down at {self.approach_speed} mm/s to find glass...")
            
            # Start moving down slowly
            self.zaber_axis.move_absolute(
                max_down_position, 
                Units.LENGTH_MILLIMETRES, 
                wait_until_idle=False,
                velocity=self.approach_speed, 
                velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND
            )
            
            contact_detected = False
            contact_position = None
            
            # Monitor force while moving
            while self.zaber_axis.is_busy():
                if self._stop_event.is_set():
                    self.zaber_axis.stop()
                    self._log("Sandwich routine cancelled during approach.")
                    if self.result_callback:
                        self.result_callback(False, "Cancelled by user.")
                    return
                
                current_force = self._get_force()
                current_position = self.zaber_axis.get_position(Units.LENGTH_MILLIMETRES)
                
                if current_force is not None:
                    # Check if we've hit the force threshold
                    if current_force <= self.contact_force_threshold:
                        # Glass contact detected!
                        self._log(f"CONTACT! Force: {current_force:.4f} N at position {current_position:.4f} mm")
                        self.zaber_axis.stop()
                        
                        # Wait for motion to stop
                        while self.zaber_axis.is_busy():
                            time.sleep(0.01)
                        
                        contact_detected = True
                        contact_position = self.zaber_axis.get_position(Units.LENGTH_MILLIMETRES)
                        self.glass_contact_position = contact_position
                        self.actual_glass_gap = contact_position - self.target_layer_height
                        
                        self._log(f"Glass contact confirmed at {contact_position:.4f} mm")
                        self._log(f"Actual glass gap: {self.actual_glass_gap:.3f} mm")
                        break
                
                time.sleep(self.force_check_interval)
            
            # Check if we found the glass
            if not contact_detected:
                final_pos = self.zaber_axis.get_position(Units.LENGTH_MILLIMETRES)
                self._log(f"WARNING: Reached safety limit at {final_pos:.4f} mm without detecting glass.")
                self._log("Glass may be further than estimated, or force threshold may be too low.")
                if self.result_callback:
                    self.result_callback(False, "Glass contact not detected within safety limit.")
                return
            
            if self._stop_event.is_set():
                return
            
            # Brief pause at glass contact
            time.sleep(0.1)
            
            # ===== PHASE 2: RETRACT TO TARGET LAYER HEIGHT =====
            self._log(f"Phase 2: Retracting to target layer height at {self.retract_speed} mm/s...")
            
            retract_distance = abs(contact_position - self.target_layer_height)
            self._log(f"Retracting {retract_distance:.3f} mm to reach {self.target_layer_height:.4f} mm")
            
            # Move back up to target layer height
            self.zaber_axis.move_absolute(
                self.target_layer_height,
                Units.LENGTH_MILLIMETRES,
                wait_until_idle=True,
                velocity=self.retract_speed,
                velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND
            )
            
            final_position = self.zaber_axis.get_position(Units.LENGTH_MILLIMETRES)
            final_force = self._get_force()
            
            self._log(f"=== Sandwich Complete ===")
            self._log(f"Final position: {final_position:.4f} mm")
            self._log(f"Final force: {final_force:.4f} N" if final_force is not None else "Final force: N/A")
            self._log(f"Glass was found {self.actual_glass_gap:.3f} mm below target")
            
            if self.result_callback:
                self.result_callback(True, f"Sandwich complete. Glass gap: {self.actual_glass_gap:.3f} mm")
        
        except Exception as e:
            self._log(f"CRITICAL ERROR during sandwich routine: {e}")
            import traceback
            traceback.print_exc()
            if self.result_callback:
                self.result_callback(False, f"Exception: {e}")
        
        finally:
            self._log("SandwichRoutine thread finished.")


def perform_sandwich_step_blocking(zaber_axis, force_gauge_manager,
                                   target_layer_height, estimated_glass_gap,
                                   contact_force_threshold,
                                   status_callback=None, timeout=30):
    """
    Convenience function to perform sandwich step and wait for completion.
    
    Args:
        zaber_axis: Zaber motor axis object
        force_gauge_manager: ForceGaugeManager instance
        target_layer_height: Final position where stage should end up (mm)
        estimated_glass_gap: Estimated distance to glass below target (mm, positive)
        contact_force_threshold: Force to detect glass contact (N, negative like -0.05)
        status_callback: Optional function for status messages
        timeout: Maximum time to wait in seconds
    
    Returns:
        Tuple of (success: bool, message: str, glass_gap: float or None)
    """
    result = {'success': False, 'message': '', 'glass_gap': None}
    
    def result_callback(success, message):
        result['success'] = success
        result['message'] = message
    
    # Create and start sandwich routine
    sandwich = SandwichRoutine(
        zaber_axis=zaber_axis,
        force_gauge_manager=force_gauge_manager,
        target_layer_height=target_layer_height,
        estimated_glass_gap=estimated_glass_gap,
        contact_force_threshold=contact_force_threshold,
        status_callback=status_callback,
        result_callback=result_callback
    )
    
    sandwich.start()
    sandwich.join(timeout=timeout)
    
    if sandwich.is_alive():
        sandwich.stop()
        sandwich.join(timeout=5)
        return False, "Sandwich routine timed out.", None
    
    return result['success'], result['message'], sandwich.actual_glass_gap
