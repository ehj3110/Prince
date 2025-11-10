# NEW ADAPTIVE SANDWICH ROUTINE - REPLACEMENT CODE
# Replace lines ~1024-1257 in Prince_Segmented.py with this code

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
                                    adaptive_force_threshold = contact_force_threshold * 0.75  # 75% of max
                                    relaxation_force_threshold = contact_force_threshold * 0.5  # 50% of max for relaxation
                                    
                                    # Calculate waypoint positions for 3-TIER DESCENT
                                    waypoint_33pct_um = current_pos_um + (gap_um * 0.33)
                                    waypoint_67pct_um = current_pos_um + (gap_um * 0.67)
                                    
                                    self.update_status_message(f"L{current_layer_num_for_display}: ADAPTIVE SANDWICH - 3-Tier Ramping")
                                    self.update_status_message(f"L{current_layer_num_for_display}: Speeds: {speed_tier1:.0f}/{speed_tier2:.0f}/{speed_tier3:.0f}µm/s, Gap:{measured_gap:.3f}mm")
                                    self.update_status_message(f"L{current_layer_num_for_display}: Force thresholds: Adaptive=75% ({abs(adaptive_force_threshold):.3f}N), Relax=50% ({abs(relaxation_force_threshold):.3f}N)")
                                    
                                    # ========== ADAPTIVE DESCENT PHASE ==========
                                    speed_was_reduced = False
                                    final_tier3_speed = speed_tier3
                                    current_descent_speed = speed_tier1
                                    segments_completed = 0
                                    
                                    # Define descent segments
                                    descent_segments = [
                                        (waypoint_33pct_um, speed_tier1, "1/3", "0-33%"),
                                        (waypoint_67pct_um, speed_tier2, "2/3", "33-67%"),
                                        (target_glass_um, speed_tier3, "3/3", "67-100%")
                                    ]
                                    
                                    for seg_idx, (target_pos, seg_speed, seg_label, seg_range) in enumerate(descent_segments):
                                        current_descent_speed = seg_speed
                                        current_pos_start = self.axis.get_position(Units.LENGTH_MICROMETRES)
                                        
                                        self.update_status_message(f"L{current_layer_num_for_display}: [DESCENT SEG {seg_label}] {current_pos_start/1000.0:.4f}mm → {target_pos/1000.0:.4f}mm @ {current_descent_speed:.0f}µm/s ({seg_range})")
                                        
                                        # Start movement
                                        self.axis.move_absolute(
                                            position=target_pos,
                                            unit=Units.LENGTH_MICROMETRES,
                                            wait_until_idle=False,
                                            velocity=current_descent_speed / 1000.0,
                                            velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND,
                                            acceleration=1000.0,
                                            acceleration_unit=Units.ACCELERATION_MILLIMETRES_PER_SECOND_SQUARED
                                        )
                                        
                                        # Monitor force during movement with ADAPTIVE behavior
                                        while self.axis.is_busy():
                                            if self.flag:
                                                self.axis.stop()
                                                break
                                            
                                            current_force = force_gauge.get_latest_calibrated_force()
                                            
                                            # Check for 75% threshold (ADAPTIVE STOP)
                                            if current_force <= adaptive_force_threshold:
                                                self.axis.stop()
                                                while self.axis.is_busy():
                                                    time.sleep(0.01)
                                                
                                                stopped_pos = self.axis.get_position(Units.LENGTH_MICROMETRES)
                                                self.update_status_message(f"L{current_layer_num_for_display}: *** ADAPTIVE STOP *** Force={current_force:.4f}N at {stopped_pos/1000.0:.4f}mm", error=False)
                                                
                                                # WAIT for force relaxation or 3 seconds
                                                self.update_status_message(f"L{current_layer_num_for_display}: Waiting for force relaxation (target: ≥{relaxation_force_threshold:.3f}N or 3s)...")
                                                wait_start = time.time()
                                                while time.time() - wait_start < 3.0:
                                                    current_force = force_gauge.get_latest_calibrated_force()
                                                    if current_force >= relaxation_force_threshold:
                                                        self.update_status_message(f"L{current_layer_num_for_display}: Force relaxed to {current_force:.4f}N after {time.time()-wait_start:.2f}s")
                                                        break
                                                    time.sleep(0.1)
                                                
                                                if current_force < relaxation_force_threshold:
                                                    self.update_status_message(f"L{current_layer_num_for_display}: 3s timeout reached, force={current_force:.4f}N")
                                                
                                                # REDUCE SPEED by 50%
                                                current_descent_speed = current_descent_speed * 0.5
                                                final_tier3_speed = current_descent_speed  # Track final speed used
                                                speed_was_reduced = True
                                                self.update_status_message(f"L{current_layer_num_for_display}: Speed reduced to {current_descent_speed:.0f}µm/s (50% reduction)")
                                                
                                                # Continue from current position to segment target at reduced speed
                                                current_pos_after_stop = self.axis.get_position(Units.LENGTH_MICROMETRES)
                                                remaining_distance = target_pos - current_pos_after_stop
                                                
                                                if remaining_distance > 1.0:  # If more than 1µm to go
                                                    self.update_status_message(f"L{current_layer_num_for_display}: Resuming descent at reduced speed: {current_pos_after_stop/1000.0:.4f}mm → {target_pos/1000.0:.4f}mm")
                                                    self.axis.move_absolute(
                                                        position=target_pos,
                                                        unit=Units.LENGTH_MICROMETRES,
                                                        wait_until_idle=False,
                                                        velocity=current_descent_speed / 1000.0,
                                                        velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND,
                                                        acceleration=1000.0,
                                                        acceleration_unit=Units.ACCELERATION_MILLIMETRES_PER_SECOND_SQUARED
                                                    )
                                                    # Continue monitoring in the same while loop
                                                    continue
                                                else:
                                                    break  # Already at target
                                            
                                            time.sleep(0.02)
                                        
                                        if self.flag:
                                            break  # User stopped print
                                        
                                        pos_after_seg = self.axis.get_position(Units.LENGTH_MICROMETRES)
                                        self.update_status_message(f"L{current_layer_num_for_display}: [DESCENT SEG {seg_label} DONE] Reached: {pos_after_seg/1000.0:.4f}mm")
                                        segments_completed += 1
                                        
                                        # Check if we've reached target glass position
                                        if abs(pos_after_seg - target_glass_um) < 5.0:  # Within 5µm
                                            break
                                    
                                    if self.flag:
                                        break  # Exit to main loop
                                    
                                    final_descent_pos_um = self.axis.get_position(Units.LENGTH_MICROMETRES)
                                    self.update_status_message(f"L{current_layer_num_for_display}: [DESCENT COMPLETE] Reached glass at {final_descent_pos_um/1000.0:.4f}mm")
                                    
                                    # ========== SPEED ADAPTATION FOR FUTURE LAYERS ==========
                                    if speed_was_reduced:
                                        # Calculate new base speed so final tier3 equals our final speed
                                        # If final_tier3_speed should be tier3 in new scheme: new_base / 9 = final_tier3_speed
                                        new_base_speed = final_tier3_speed * 9.0
                                        self.adaptive_sandwich_speed_um_s = new_base_speed
                                        self.update_status_message(f"L{current_layer_num_for_display}: *** SPEED ADAPTED *** New base speed for future layers: {new_base_speed:.0f}µm/s (Tier3={final_tier3_speed:.0f}µm/s)")
                                    
                                    # ========== SIMPLIFIED ASCENT PHASE ==========
                                    # Use final speeds from descent (respecting any adaptive changes)
                                    ascent_tier1 = speed_tier1 if not speed_was_reduced else (final_tier3_speed * 9.0)
                                    ascent_tier2 = ascent_tier1 / 3.0
                                    ascent_tier3 = ascent_tier1 / 9.0
                                    
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
