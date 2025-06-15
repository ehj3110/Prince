import time
import threading
from zaber_motion import Units

class AutoHomer(threading.Thread):
    def __init__(self, zaber_axis, force_gauge_manager, initial_guess,
                 contact_threshold_absolute, contact_threshold_delta,
                 status_callback, result_callback, parent_gui):
        super().__init__()
        self.daemon = True
        self.zaber_axis = zaber_axis
        self.force_gauge_manager = force_gauge_manager
        self.initial_guess = initial_guess
        self.contact_threshold_absolute = contact_threshold_absolute
        self.contact_threshold_delta = contact_threshold_delta
        self.status_callback = status_callback
        self.result_callback = result_callback # This will now be called with 2 args
        self.parent_gui = parent_gui

        self.scan_range = 5.0
        self.lift_distance = 1.0
        self.num_measurements = 5
        self.slow_approach_speed = 0.1
        self.scan_speed = 1.0 # mm/s

        self._stop_event = threading.Event()
        self.log_to_terminal = True
        self.calculated_stiffness = None # Ensure it's initialized

    def _log(self, message):
        """Helper for conditional logging to terminal."""
        if self.log_to_terminal:
            print(f"AutoHomer_DEBUG: {message}")
        self.status_callback(message) # Also send to GUI status

    def stop(self):
        self._stop_event.set()

    def _get_force(self):
        if self.force_gauge_manager:
            force = self.force_gauge_manager.get_latest_calibrated_force()
            return force
        return None

    def _find_surface_contact(self, start_pos, end_pos, speed, direction_is_down=True):
        self._log(f"Scanning from {start_pos:.3f}mm to {end_pos:.3f}mm at {speed}mm/s. AbsThresh={self.contact_threshold_absolute:.3f}N, DeltaThresh={self.contact_threshold_delta:.3f}N")
        
        self.zaber_axis.move_absolute(start_pos, Units.LENGTH_MILLIMETRES, wait_until_idle=True)
        time.sleep(0.5) 
        baseline_force = self._get_force()

        if baseline_force is None:
            self._log("Error: Could not get baseline force reading for scan.")
            return None, None
        self._log(f"Baseline force at {start_pos:.3f}mm: {baseline_force:.4f}N")

        self.zaber_axis.move_absolute(end_pos, Units.LENGTH_MILLIMETRES, wait_until_idle=False,
                                      velocity=speed, velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND)
        
        contact_detected_flag = False
        contact_pos = None
        min_force_seen_in_scan = float('inf') 
        max_force_seen_in_scan = -float('inf')

        # --- For stiffness calculation ---
        scan_positions = []
        scan_forces = []

        while self.zaber_axis.is_busy():
            if self._stop_event.is_set():
                self.zaber_axis.stop()
                self._log("Auto-home cancelled during scan.")
                return None, None

            current_pos_while_moving = self.zaber_axis.get_position(Units.LENGTH_MILLIMETRES)
            current_force = self._get_force() 

            # --- Record for stiffness ---
            if current_force is not None:
                scan_positions.append(current_pos_while_moving)
                scan_forces.append(current_force)

                if current_force < min_force_seen_in_scan: 
                    min_force_seen_in_scan = current_force
                if current_force > max_force_seen_in_scan: 
                    max_force_seen_in_scan = current_force
                
                delta_force = current_force - baseline_force
                
                if direction_is_down: 
                    if current_force < (baseline_force - self.contact_threshold_delta):
                        contact_detected_flag = True
                        self._log(f"Negative Delta contact: F={current_force:.4f}N < (Baseline {baseline_force:.4f}N - DeltaThresh {self.contact_threshold_delta:.3f}N). ΔF={delta_force:.4f}N at ~{current_pos_while_moving:.3f}mm.")
                    elif current_force < -self.contact_threshold_absolute: 
                        contact_detected_flag = True
                        self._log(f"Negative Absolute contact: F={current_force:.4f}N < {-self.contact_threshold_absolute:.3f}N at ~{current_pos_while_moving:.3f}mm.")

                if contact_detected_flag:
                    self.zaber_axis.stop() 
                    while self.zaber_axis.is_busy(): time.sleep(0.01) 
                    contact_pos = self.zaber_axis.get_position(Units.LENGTH_MILLIMETRES) 
                    self._log(f"Contact confirmed at {contact_pos:.4f}mm. MinF: {min_force_seen_in_scan:.4f}N, MaxF: {max_force_seen_in_scan:.4f}N")
                    break
            else:
                pass

            time.sleep(0.02)

        # --- Stiffness Calculation ---
        stiffness = None
        if scan_forces and contact_pos is not None:
            # Find where force first deviates from baseline by more than a small threshold (e.g., 2x noise or 2% of threshold)
            noise_threshold = max(0.02 * abs(self.contact_threshold_delta), 0.001)  # 2% of delta or 1 mN
            start_index = None
            for i, f in enumerate(scan_forces):
                if abs(f - baseline_force) > noise_threshold:
                    start_index = i
                    break
            if start_index is not None:
                start_pos_stiff = scan_positions[start_index]
                force_at_contact = scan_forces[-1]  # Last force recorded (at contact)
                pos_at_contact = scan_positions[-1]
                delta_f = abs(force_at_contact - baseline_force)
                delta_x = abs(pos_at_contact - start_pos_stiff)
                if delta_x > 0:
                    stiffness = delta_f / (delta_x / 1000.0)  # N/m (convert mm to m)
                    self._log(f"Estimated stiffness: ΔF={delta_f:.4f}N, Δx={delta_x:.4f}mm, k={stiffness:.2f} N/m")
                else:
                    self._log("Stiffness calculation: Δx is zero, cannot compute stiffness.")
            else:
                self._log("Stiffness calculation: No significant force rise detected.")

        final_pos = self.zaber_axis.get_position(Units.LENGTH_MILLIMETRES)
        if not contact_detected_flag:
            self._log(f"Scan segment finished. Reached {final_pos:.3f}mm without contact. Baseline: {baseline_force:.4f}N. MinF: {min_force_seen_in_scan:.4f}N, MaxF: {max_force_seen_in_scan:.4f}N")
            return None, None
        return contact_pos, stiffness

    def run(self):
        try:
            self.calculated_stiffness = None # Reset at the start of a run
            self._log("AutoHomer thread started.")
            if self._stop_event.is_set(): return

            if not self.force_gauge_manager or not self.force_gauge_manager.is_calibrated():
                self._log("Error: Force gauge not calibrated.")
                self.result_callback(None, "Force gauge not calibrated.")
                return

            scan_start_initial_phase = self.initial_guess - self.scan_range
            scan_end_initial_phase = self.initial_guess + self.scan_range
            
            safe_start_pos = scan_start_initial_phase - self.lift_distance 
            self._log(f"Initial coarse scan phase. Target range: {scan_start_initial_phase:.3f} to {scan_end_initial_phase:.3f}mm. Starting from {safe_start_pos:.3f}mm.")

            measured_stiffness_values = [] # List to store all valid stiffness measurements

            first_contact_pos, first_stiffness_val = self._find_surface_contact(safe_start_pos, scan_end_initial_phase, self.scan_speed, direction_is_down=True)
            
            # if first_stiffness_val is not None:
            #     measured_stiffness_values.append(first_stiffness_val)
            # We will set self.calculated_stiffness later with the average

            if first_contact_pos is None:
                self._log("Initial surface contact NOT found after coarse scan.")
                self.result_callback(None, "Initial surface contact not found.")
                return
            
            if self._stop_event.is_set(): return

            measured_positions = [first_contact_pos]
            current_contact_estimate = first_contact_pos
            self._log(f"Initial contact found at {first_contact_pos:.4f}mm. Proceeding to refine.")

            for i in range(self.num_measurements - 1):
                if self._stop_event.is_set(): return
                self._log(f"Refinement measurement {i+1}/{self.num_measurements-1}...")

                lift_to_pos = current_contact_estimate - 1.0
                if self._stop_event.is_set(): return

                refined_search_start = lift_to_pos
                refined_search_end = current_contact_estimate + self.lift_distance * 0.5

                contact_pos, refinement_stiffness = self._find_surface_contact(refined_search_start, refined_search_end, self.slow_approach_speed, direction_is_down=True)

                if refinement_stiffness is not None:
                    measured_stiffness_values.append(refinement_stiffness)

                if contact_pos is None:
                    self._log(f"Contact not found during refinement {i+1}. Using previous estimate: {current_contact_estimate:.4f}mm")
                    measured_positions.append(current_contact_estimate) # Still add the estimate to positions - FIXED
                else:
                    measured_positions.append(contact_pos)
                    current_contact_estimate = contact_pos
                    self._log(f"Refined contact {i+1} at {contact_pos:.4f}mm.")

                time.sleep(0.2) 

            if not measured_positions:
                self._log("No valid measurements obtained for position.")
                self.result_callback(None, "No valid position measurements obtained.")
                return

            average_home_pos = sum(measured_positions) / len(measured_positions)
            self._log(f"Auto-Home complete. All measured positions: {[f'{p:.4f}' for p in measured_positions]}")
            self._log(f"New home calculated: {average_home_pos:.4f} mm")

            if measured_stiffness_values: # Check if list is not empty
                average_stiffness = sum(measured_stiffness_values) / len(measured_stiffness_values)
                self.calculated_stiffness = average_stiffness # Store the average stiffness
                self._log(f"Average stiffness calculated: {self.calculated_stiffness:.2f} N/m from {len(measured_stiffness_values)} measurements.")
            else:
                self.calculated_stiffness = None # No valid stiffness values found
                self._log("No valid stiffness values recorded to calculate average.")
            
            self.result_callback(average_home_pos, "Auto-Home successful.")

        except Exception as e:
            self._log(f"CRITICAL Error during Auto-Home: {e}")
            import traceback
            traceback.print_exc()
            self.result_callback(None, f"Exception: {e}")
        finally:
            self._log("AutoHomer thread finished.")
            # self.status_callback("Auto-Home routine finished.") # Optionally