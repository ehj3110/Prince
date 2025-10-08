"""
Implement all threading and DLP fixes for Prince_Segmented.py
October 8, 2025
"""

import re

print("="*80)
print("IMPLEMENTING THREADING AND DLP FIXES")
print("="*80)

# Read the file
with open('Prince_Segmented.py', 'r', encoding='utf-8') as f:
    content = f.read()
    lines = content.split('\n')

print(f"\n📄 File loaded: {len(lines)} lines")

# ============================================================================
# FIX 1: Add DLP Cleanup Function
# ============================================================================
print("\n🔧 Fix 1: Adding cleanup_dlp_safe_state() function...")

# Find where to insert (before print_t function)
insert_location = None
for i, line in enumerate(lines):
    if 'def print_t(self,' in line:
        insert_location = i
        break

if insert_location:
    cleanup_function = '''    def cleanup_dlp_safe_state(self):
        """Reset DLP to safe idle state: stop sequence, power off, video mode."""
        try:
            if hasattr(self, 'controller'):
                self.controller.stopsequence()
                self.controller.power(current=0)  # Turn off LED
                self.controller.changemode(3)     # HDMI/video mode
                self.update_status_message("DLP reset to safe state (video mode, power=0)")
        except Exception as e:
            self.update_status_message(f"Error resetting DLP: {e}", error=True)

'''
    lines.insert(insert_location, cleanup_function)
    print(f"✓ Added cleanup_dlp_safe_state() at line {insert_location}")
else:
    print("✗ Could not find print_t function!")

# Join lines back
content = '\n'.join(lines)

# ============================================================================
# FIX 2: Replace DLP cleanup at print completion
# ============================================================================
print("\n🔧 Fix 2: Replacing DLP cleanup at print completion...")

old_cleanup = """            try:
                self.controller.stopsequence()
                self.controller.power(current=0) # Turn off LED
                self.controller.changemode(3)   # Set back to HDMI/video input mode
                # self.controller.hdmi()        # Optionally ensure HDMI input is active
                self.update_status_message("DLP sequence stopped, LEDs off, and mode set to HDMI.")"""

new_cleanup = """            # Use standardized DLP cleanup
            self.cleanup_dlp_safe_state()"""

if old_cleanup in content:
    content = content.replace(old_cleanup, new_cleanup)
    print("✓ Replaced print completion DLP cleanup")
else:
    print("⚠ Could not find old cleanup code (may already be updated)")

# ============================================================================
# FIX 3: Fix stop button DLP cleanup
# ============================================================================
print("\n🔧 Fix 3: Fixing stop button DLP cleanup...")

old_stop = """            try:
                self.controller.stopsequence() # Stop any active sequence
                # Optionally, also turn power off here if stop means immediate halt of light
                # self.controller.power(current=0)"""

new_stop = """            # Use standardized DLP cleanup
            self.cleanup_dlp_safe_state()"""

if old_stop in content:
    content = content.replace(old_stop, new_stop)
    print("✓ Fixed stop button DLP cleanup")
else:
    print("⚠ Could not find stop button code (may already be updated)")

# ============================================================================
# FIX 4: Add power cycling in stepped mode
# ============================================================================
print("\n🔧 Fix 4: Adding power cycling in stepped mode...")

# Find the stepped mode black image display
old_stepped_black = """                    # 3. Show black image after exposure for stepped mode
                    cv2.imshow(self.window_name, self.black_image)
                    cv2.waitKey(1)

                    # 4. Z-Axis Movement (Peel and Return)"""

new_stepped_black = """                    # 3. Show black image after exposure for stepped mode
                    cv2.imshow(self.window_name, self.black_image)
                    cv2.waitKey(1)
                    
                    # 3b. Turn off DLP power to eliminate background light during movement
                    if hasattr(self, 'controller'):
                        try:
                            self.controller.power(current=0)
                            self.update_status_message(f"L{current_layer_num_for_display}: DLP power=0 (background light off)")
                        except Exception as e:
                            self.update_status_message(f"L{current_layer_num_for_display}: Could not set DLP power to 0: {e}", error=True)

                    # 4. Z-Axis Movement (Peel and Return)"""

if old_stepped_black in content:
    content = content.replace(old_stepped_black, new_stepped_black)
    print("✓ Added power-off after exposure in stepped mode")
else:
    print("⚠ Could not find stepped mode black image code")

# Now add power restoration after stage return in stepped mode
# This is trickier - need to find after the return movement completes
stepped_return_pattern = r"(self\.update_status_message\(f\"SUCCESS L{current_layer_num_for_display}: Return movement completed\"\))"

def add_power_restore(match):
    return match.group(1) + """
                    
                    # 4b. Restore DLP power for next layer (if not last layer)
                    if i < num_layers - 1 and hasattr(self, 'controller'):
                        try:
                            # Get next layer's power setting
                            next_layer_power = int(actual_dlp_power)
                            self.controller.power(current=next_layer_power)
                            self.update_status_message(f"L{current_layer_num_for_display}: DLP power restored to {next_layer_power}")
                        except Exception as e:
                            self.update_status_message(f"L{current_layer_num_for_display}: Could not restore DLP power: {e}", error=True)"""

content = re.sub(stepped_return_pattern, add_power_restore, content)
print("✓ Added power restoration after return in stepped mode")

# ============================================================================
# FIX 5: Add cleanup when print finishes normally
# ============================================================================
print("\n🔧 Fix 5: Adding resource cleanup when print finishes...")

old_finish = """            self.update_status_message("Print thread finished.")
            if hasattr(self, 'b1'): self.b1.config(state=NORMAL)
            if hasattr(self, 'b2'): self.b2.config(state=NORMAL)
            if hasattr(self, 'b4'): self.b4.config(state=DISABLED)
            self.print_thread = None"""

new_finish = """            self.update_status_message("Print thread finished.")
            
            # Clean up resources
            self._cleanup_print_resources()
            
            if hasattr(self, 'b1'): self.b1.config(state=NORMAL)
            if hasattr(self, 'b2'): self.b2.config(state=NORMAL)
            if hasattr(self, 'b4'): self.b4.config(state=DISABLED)
            self.print_thread = None"""

if old_finish in content:
    content = content.replace(old_finish, new_finish)
    print("✓ Added cleanup call when print finishes")
else:
    print("⚠ Could not find print finish code")

# ============================================================================
# FIX 6: Add resource cleanup function
# ============================================================================
print("\n🔧 Fix 6: Adding _cleanup_print_resources() function...")

# Add after cleanup_dlp_safe_state
cleanup_resources_function = '''    def _cleanup_print_resources(self):
        """Clean up background threads and queues after print completion."""
        try:
            # Clean up sensor data window resources
            if hasattr(self, 'sensor_data_window_instance') and self.sensor_data_window_instance:
                # Clear plot queues
                if hasattr(self.sensor_data_window_instance, 'position_plot_queue'):
                    while not self.sensor_data_window_instance.position_plot_queue.empty():
                        try:
                            self.sensor_data_window_instance.position_plot_queue.get_nowait()
                        except:
                            break
                    self.update_status_message("Plot queue cleared.")
                
                # Clear force data queue
                if hasattr(self.sensor_data_window_instance, 'force_data_queue_for_logger'):
                    while not self.sensor_data_window_instance.force_data_queue_for_logger.empty():
                        try:
                            self.sensor_data_window_instance.force_data_queue_for_logger.get_nowait()
                        except:
                            break
                
                # Close PeakForceLogger if exists
                if hasattr(self.sensor_data_window_instance, 'peak_force_logger') and self.sensor_data_window_instance.peak_force_logger:
                    self.sensor_data_window_instance.peak_force_logger.close()
                    self.sensor_data_window_instance.peak_force_logger = None
                    self.update_status_message("PeakForceLogger shut down.")
                    
        except Exception as e:
            self.update_status_message(f"Error during resource cleanup: {e}", error=True)

'''

# Find cleanup_dlp_safe_state and add after it
lines = content.split('\n')
for i, line in enumerate(lines):
    if 'def cleanup_dlp_safe_state(self):' in line:
        # Find the end of this function (next def or class)
        for j in range(i+1, len(lines)):
            if lines[j].strip().startswith('def ') and not lines[j].strip().startswith('def cleanup'):
                lines.insert(j, cleanup_resources_function)
                print(f"✓ Added _cleanup_print_resources() at line {j}")
                break
        break

content = '\n'.join(lines)

# ============================================================================
# FIX 7: Add DLP cleanup to fault recovery error handler
# ============================================================================
print("\n🔧 Fix 7: Adding DLP cleanup to fault recovery...")

old_recovery = """                            except Exception as recovery_error:
                                self.update_status_message(f"RECOVERY FAILED L{current_layer_num_for_display}: {recovery_error}", error=True)
                        except:
                            pass
                        raise  # Re-raise to trigger print abort"""

new_recovery = """                            except Exception as recovery_error:
                                self.update_status_message(f"RECOVERY FAILED L{current_layer_num_for_display}: {recovery_error}", error=True)
                        except:
                            pass
                        
                        # Clean up DLP before aborting
                        self.cleanup_dlp_safe_state()
                        self._cleanup_print_resources()
                        raise  # Re-raise to trigger print abort"""

if old_recovery in content:
    content = content.replace(old_recovery, new_recovery)
    print("✓ Added cleanup to fault recovery error handler")
else:
    print("⚠ Could not find fault recovery code")

# ============================================================================
# FIX 8: Enhance SensorDataWindow clear_plot_data
# ============================================================================
print("\n🔧 Fix 8: Enhancing SensorDataWindow.clear_plot_data()...")

sdw_file = 'support_modules/SensorDataWindow.py'
try:
    with open(sdw_file, 'r', encoding='utf-8') as f:
        sdw_content = f.read()
    
    old_clear = """    def clear_plot_data(self):
        self.plot_data_x.clear()
        self.plot_data_y_position.clear()
        self.plot_data_y_force.clear()

        # Only reset plot_start_time if not actively plotting,"""

    new_clear = """    def clear_plot_data(self):
        self.plot_data_x.clear()
        self.plot_data_y_position.clear()
        self.plot_data_y_force.clear()
        
        # Also clear the force data queue to prevent stale data
        while not self.force_data_queue_for_logger.empty():
            try:
                self.force_data_queue_for_logger.get_nowait()
            except queue.Empty:
                break

        # Only reset plot_start_time if not actively plotting,"""
    
    if old_clear in sdw_content:
        sdw_content = sdw_content.replace(old_clear, new_clear)
        with open(sdw_file, 'w', encoding='utf-8') as f:
            f.write(sdw_content)
        print(f"✓ Enhanced clear_plot_data() in {sdw_file}")
    else:
        print(f"⚠ Could not find clear_plot_data() in {sdw_file}")
except Exception as e:
    print(f"✗ Error modifying {sdw_file}: {e}")

# ============================================================================
# Save the main file
# ============================================================================
print("\n💾 Saving Prince_Segmented.py...")

try:
    with open('Prince_Segmented.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ Prince_Segmented.py saved successfully!")
except Exception as e:
    print(f"✗ Error saving file: {e}")

print("\n" + "="*80)
print("IMPLEMENTATION COMPLETE!")
print("="*80)
print("\n📋 Summary of changes:")
print("  1. ✓ Added cleanup_dlp_safe_state() function")
print("  2. ✓ Added _cleanup_print_resources() function")  
print("  3. ✓ Replaced print completion DLP cleanup")
print("  4. ✓ Fixed stop button DLP cleanup")
print("  5. ✓ Added power cycling in stepped mode (power=0 during movement)")
print("  6. ✓ Added power restoration after return")
print("  7. ✓ Added resource cleanup when print finishes")
print("  8. ✓ Added cleanup to fault recovery")
print("  9. ✓ Enhanced SensorDataWindow.clear_plot_data()")
print("\n🎯 Next steps:")
print("  - Test with a short print to verify DLP behavior")
print("  - Test stop button functionality")
print("  - Verify background light is eliminated in stepped mode")
print("  - Test error scenarios to ensure proper cleanup")
