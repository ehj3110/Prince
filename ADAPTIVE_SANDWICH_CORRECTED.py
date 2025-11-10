# CORRECTED ADAPTIVE SANDWICH ROUTINE
# Key fixes:
# 1. Proper handling of adaptive stop/resume within the monitoring loop
# 2. Correct force relaxation check (less negative = more relaxed)
# 3. Proper loop structure to avoid re-entering completed movements

# This code replaces lines ~1020-1257 in Prince_Segmented.py

                                    # Get pause time from this layer
                                    actual_pause = self.pause_list[i] if i < len(self.pause_list) else 0.0
                                    
                                    # ========== ADAPTIVE SANDWICH PARAMETERS ==========
                                    # Check if we have adaptive speed override from previous layer
                                    if hasattr(self, 'adaptive_sandwich_speed_um_s') and self.adaptive_sandwich_speed_um_s is not None:
                                        base_sandwich_speed = self.adaptive_sandwich_speed_um_s
                                        self.update_status_message(f"L{current_layer_num_for_display}: Using ADAPTIVE speed: {base_sandwich_speed:.0f}µm/s (adjusted from previous layer)")
                                    else:
                                        base_sandwich_speed = actual_sandwich_speed_um_s
                                    
                                    # Calculate 3-tier speeds (divide by 3 and 9, not 2 and 4)
                                    speed_tier1 = base_sandwich_speed        # 0-33% of gap
                                    speed_tier2 = base_sandwich_speed / 3.0  # 33-67% of gap  
                                    speed_tier3 = base_sandwich_speed / 9.0  # 67-100% of gap (slowest)
                                    
                                    # 75% force threshold for adaptive behavior
                                    adaptive_force_threshold = contact_force_threshold * 0.75  # More negative = closer to limit
                                    relaxation_force_threshold = contact_force_threshold * 0.5  # Less negative = more relaxed
                                    
                                    # Calculate waypoint positions for 3-TIER DESCENT
                                    waypoint_33pct_um = current_pos_um + (gap_um * 0.33)
                                    waypoint_67pct_um = current_pos_um + (gap_um * 0.67)
                                    
                                    self.update_status_message(f"L{current_layer_num_for_display}: ADAPTIVE SANDWICH - 3-Tier Ramping")
                                    self.update_status_message(f"L{current_layer_num_for_display}: Speeds: {speed_tier1:.0f}/{speed_tier2:.0f}/{speed_tier3:.0f}µm/s, Gap:{measured_gap:.3f}mm")
                                    self.update_status_message(f"L{current_layer_num_for_display}: Force thresholds: Adaptive=75% ({abs(adaptive_force_threshold):.3f}N), Relax=50% ({abs(relaxation_force_threshold):.3f}N)")
                                    
                                    # ========== ADAPTIVE DESCENT PHASE ==========
                                    speed_was_reduced = False
                                    final_tier3_speed = speed_tier3
                                    
                                    # Define descent segments
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
                                        
                                        self.update_status_message(f"L{current_layer_num_for_display}: [DESCENT SEG {seg_label}] {segment_start_pos/1000.0:.4f}mm → {segment_target_um/1000.0:.4f}mm @ {current_seg_speed:.0f}µm/s ({seg_range})")
                                        
                                        # Move toward segment target with adaptive behavior
                                        while not reached_glass:
                                            current_position = self.axis.get_position(Units.LENGTH_MICROMETRES)
                                            
                                            # Check if we've reached segment target
                                            if abs(current_position - segment_target_um) < 5.0:  # Within 5µm
                                                self.update_status_message(f"L{current_layer_num_for_display}: [DESCENT SEG {seg_label} DONE] Reached: {current_position/1000.0:.4f}mm")
                                                break
                                            
                                            # Start movement to segment target
                                            self.axis.move_absolute(
                                                position=segment_target_um,
                                                unit=Units.LENGTH_MICROMETRES,
                                                wait_until_idle=False,
                                                velocity=current_seg_speed / 1000.0,
                                                velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND,
                                                acceleration=1000.0,
                                                acceleration_unit=Units.ACCELERATION_MILLIMETRES_PER_SECOND_SQUARED
                                            )
                                            
                                            # Monitor force during movement
                                            adaptive_stop_triggered = False
                                            while self.axis.is_busy():
                                                if self.flag:
                                                    self.axis.stop()
                                                    raise Exception("User stopped print during sandwich descent")
                                                
                                                current_force = force_gauge.get_latest_calibrated_force()
                                                
                                                # Check for 75% threshold (ADAPTIVE STOP)
                                                if current_force <= adaptive_force_threshold:
                                                    self.axis.stop()
                                                    while self.axis.is_busy():
                                                        time.sleep(0.01)
                                                    
                                                    adaptive_stop_triggered = True
                                                    stopped_pos = self.axis.get_position(Units.LENGTH_MICROMETRES)
                                                    self.update_status_message(f"L{current_layer_num_for_display}: *** ADAPTIVE STOP *** Force={current_force:.4f}N at {stopped_pos/1000.0:.4f}mm", error=False)
                                                    break
                                                
                                                time.sleep(0.02)
                                            
                                            if self.flag:
                                                raise Exception("User stopped print")
                                            
                                            # If adaptive stop was triggered
                                            if adaptive_stop_triggered:
                                                # WAIT for force relaxation or 3 seconds
                                                self.update_status_message(f"L{current_layer_num_for_display}: Waiting for force relaxation (target: ≥{relaxation_force_threshold:.3f}N or 3s)...")
                                                wait_start = time.time()
                                                final_force = current_force
                                                
                                                while time.time() - wait_start < 3.0:
                                                    final_force = force_gauge.get_latest_calibrated_force()
                                                    # Force is negative, so >= means less compression (more relaxed)
                                                    if final_force >= relaxation_force_threshold:
                                                        self.update_status_message(f"L{current_layer_num_for_display}: Force relaxed to {final_force:.4f}N after {time.time()-wait_start:.2f}s")
                                                        break
                                                    time.sleep(0.1)
                                                
                                                if final_force < relaxation_force_threshold:
                                                    self.update_status_message(f"L{current_layer_num_for_display}: 3s timeout reached, force={final_force:.4f}N")
                                                
                                                # REDUCE SPEED by 50%
                                                current_seg_speed = current_seg_speed * 0.5
                                                final_tier3_speed = current_seg_speed  # Track final speed used
                                                speed_was_reduced = True
                                                self.update_status_message(f"L{current_layer_num_for_display}: Speed reduced to {current_seg_speed:.0f}µm/s (50% reduction)")
                                                
                                                # Continue loop - will start new movement at reduced speed
                                                continue
                                            
                                            # If no adaptive stop, movement completed normally
                                            # Check if we reached target glass position
                                            final_pos = self.axis.get_position(Units.LENGTH_MICROMETRES)
                                            if abs(final_pos - target_glass_um) < 5.0:  # Within 5µm of glass
                                                reached_glass = True
                                                self.update_status_message(f"L{current_layer_num_for_display}: Reached glass position at {final_pos/1000.0:.4f}mm")
                                                break
                                            
                                            # Otherwise continue to next iteration (shouldn't normally reach here)
                                            break
                                    
                                    final_descent_pos_um = self.axis.get_position(Units.LENGTH_MICROMETRES)
                                    self.update_status_message(f"L{current_layer_num_for_display}: [DESCENT COMPLETE] Final position: {final_descent_pos_um/1000.0:.4f}mm")
                                    
                                    # ========== SPEED ADAPTATION FOR FUTURE LAYERS ==========
                                    if speed_was_reduced:
                                        # Calculate new base speed so final tier3 equals our final speed
                                        # new_base / 9 = final_tier3_speed  =>  new_base = final_tier3_speed * 9
                                        new_base_speed = final_tier3_speed * 9.0
                                        self.adaptive_sandwich_speed_um_s = new_base_speed
                                        self.update_status_message(f"L{current_layer_num_for_display}: *** SPEED ADAPTED *** New base speed for future layers: {new_base_speed:.0f}µm/s (Tier3={final_tier3_speed:.0f}µm/s)")
                                    
                                    # ========== SIMPLIFIED ASCENT PHASE ==========
                                    # Use final speeds from descent (respecting any adaptive changes)
                                    if speed_was_reduced:
                                        ascent_tier1 = final_tier3_speed * 9.0
                                        ascent_tier2 = final_tier3_speed * 3.0
                                        ascent_tier3 = final_tier3_speed
                                    else:
                                        ascent_tier1 = speed_tier1
                                        ascent_tier2 = speed_tier2
                                        ascent_tier3 = speed_tier3
                                    
                                    # Calculate ascent waypoints: 0→33% at tier3, 33→50% at tier2, PAUSE, 50→100% at tier1
                                    waypoint_33pct_up_um = final_descent_pos_um - (gap_um * 0.33)  # 33% up from glass
                                    waypoint_50pct_up_um = final_descent_pos_um - (gap_um * 0.5)   # 50% up from glass (PAUSE HERE)
                                    
                                    self.update_status_message(f"L{current_layer_num_for_display}: ========== STARTING ASCENT ==========")
                                    self.update_status_message(f"L{current_layer_num_for_display}: Ascent speeds: {ascent_tier3:.0f}→{ascent_tier2:.0f}µm/s, PAUSE, then {ascent_tier1:.0f}µm/s")
                                    
                                    # Segment 1: 0→33% at tier3 (slowest, leaving glass)
                                    self.update_status_message(f"L{current_layer_num_for_display}: [ASCENT SEG 1/3] {final_descent_pos_um/1000.0:.4f}mm → {waypoint_33pct_up_um/1000.0:.4f}mm @ {ascent_tier3:.0f}µm/s")
                                    self.axis.move_absolute(
                                        position=waypoint_33pct_up_um,
                                        unit=Units.LENGTH_MICROMETRES,
                                        wait_until_idle=True,
                                        velocity=ascent_tier3 / 1000.0,
                                        velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND,
                                        acceleration=1000.0,
                                        acceleration_unit=Units.ACCELERATION_MILLIMETRES_PER_SECOND_SQUARED
                                    )
                                    
                                    # Segment 2: 33→50% at tier2
                                    self.update_status_message(f"L{current_layer_num_for_display}: [ASCENT SEG 2/3] {waypoint_33pct_up_um/1000.0:.4f}mm → {waypoint_50pct_up_um/1000.0:.4f}mm @ {ascent_tier2:.0f}µm/s")
                                    self.axis.move_absolute(
                                        position=waypoint_50pct_up_um,
                                        unit=Units.LENGTH_MICROMETRES,
                                        wait_until_idle=True,
                                        velocity=ascent_tier2 / 1000.0,
                                        velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND,
                                        acceleration=1000.0,
                                        acceleration_unit=Units.ACCELERATION_MILLIMETRES_PER_SECOND_SQUARED
                                    )
                                    
                                    # PAUSE at 50% point
                                    if actual_pause > 0:
                                        self.update_status_message(f"L{current_layer_num_for_display}: [ASCENT PAUSE] Pausing {actual_pause}s at 50% point")
                                        time.sleep(actual_pause)
                                        self.update_status_message(f"L{current_layer_num_for_display}: [ASCENT PAUSE DONE] Resuming")
                                    
                                    # Segment 3: 50→100% (to layer position) at tier1 (fastest)
                                    self.update_status_message(f"L{current_layer_num_for_display}: [ASCENT SEG 3/3] {waypoint_50pct_up_um/1000.0:.4f}mm → {sandwich_target_position_um/1000.0:.4f}mm @ {ascent_tier1:.0f}µm/s")
                                    self.axis.move_absolute(
                                        position=sandwich_target_position_um,
                                        unit=Units.LENGTH_MICROMETRES,
                                        wait_until_idle=True,
                                        velocity=ascent_tier1 / 1000.0,
                                        velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND,
                                        acceleration=1000.0,
                                        acceleration_unit=Units.ACCELERATION_MILLIMETRES_PER_SECOND_SQUARED
                                    )
                                    
                                    final_pos = self.axis.get_position(Units.LENGTH_MICROMETRES)
                                    self.update_status_message(f"L{current_layer_num_for_display}: [ASCENT COMPLETE] Sandwich complete at {final_pos/1000.0:.4f}mm")
                                    self.update_status_message(f"L{current_layer_num_for_display}: ========== SANDWICH ROUTINE COMPLETE ==========")
