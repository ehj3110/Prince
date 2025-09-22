import time
import traceback
import queue
import threading
from collections import deque
from tkinter import messagebox, simpledialog
from Phidget22.Phidget import *
from Phidget22.Devices.VoltageRatioInput import *
from Phidget22.Net import *
from Phidget22.PhidgetException import PhidgetException
from Phidget22.ErrorCode import ErrorCode
from Phidget22.BridgeGain import BridgeGain

# Import USB coordinator for safe operations
try:
    from USBCoordinator import usb_coordinator
    USB_COORDINATOR_AVAILABLE = True
except ImportError:
    print("Warning: USBCoordinator not available. Force gauge may interfere with DLP operations.")
    USB_COORDINATOR_AVAILABLE = False
    usb_coordinator = None

class ForceGaugeManager:
    def __init__(self, gain_label, offset_label, force_status_label, large_force_readout_label, output_force_queue, parent_window, sensor_window_ref):
        self.gain_label = gain_label
        self.offset_label = offset_label
        self.force_status_label = force_status_label
        self.large_force_readout_label = large_force_readout_label
        self.output_force_queue = output_force_queue
        self.parent_window = parent_window
        self.sensor_window_ref = sensor_window_ref

        self.GAIN = None
        self.OFFSET = None
        self.voltage_ratio_input = None
        self.latest_calibrated_force = 0.0 # Initialize to a default float value
        self.calibrated_once = False
        
        # === HIGH-PERFORMANCE MULTI-THREADING ARCHITECTURE ===
        
        # Raw data queue for ultra-fast data capture
        self.raw_data_queue = queue.Queue(maxsize=2000)  # Large buffer for raw sensor data
        
        # Processed data for GUI updates
        self.gui_update_queue = queue.Queue(maxsize=100)  # GUI update commands
        
        # Threading control
        self.running = True
        self.threads = []
        
        # High-frequency data buffering (thread-safe)
        self.high_freq_buffer = deque(maxlen=1000)  # Buffer for high-freq data
        self.buffer_lock = threading.Lock()
        
        # Performance monitoring
        self.data_rate_counter = 0
        self.last_rate_check = time.time()
        self.actual_sample_rate = 0.0
        
        # GUI update control (now handled by dedicated thread)
        self.last_gui_update = 0
        self.gui_update_interval = 0.05  # Update GUI max every 50ms
        self.last_queue_push = 0
        self.queue_push_interval = 0.025  # Push to logger queue every 25ms
        
        # Force-based change detection
        self.force_change_trigger_N = 0.001  # 1 millinewton trigger when calibrated
        self.last_displayed_force = None  # Track last force sent to GUI
        self.use_force_based_trigger = False  # Enable after calibration
        
        # High-frequency logging control
        self.high_freq_logging_enabled = True  # Log all data points by default
        
        # Start dedicated processing threads
        self._start_processing_threads()
        
        # Initialize Phidget in background to prevent GUI freezing
        self.initialization_thread = threading.Thread(target=self.initialize_phidget_background, daemon=True)
        self.initialization_thread.start()

    def _start_processing_threads(self):
        """Start dedicated threads for data processing."""
        
        # Thread 1: Data Processing (handles all calculations and logging)
        data_processor = threading.Thread(target=self._data_processing_loop, daemon=True)
        data_processor.start()
        self.threads.append(data_processor)
        
        # Thread 2: GUI Updates (handles all GUI operations safely)
        gui_updater = threading.Thread(target=self._gui_update_loop, daemon=True)
        gui_updater.start()
        self.threads.append(gui_updater)
        
        # Thread 3: Performance Monitor (tracks actual sample rate)
        monitor = threading.Thread(target=self._performance_monitor_loop, daemon=True)
        monitor.start()
        self.threads.append(monitor)
        
        print("Multi-threaded data processing system started")

    def _data_processing_loop(self):
        """Dedicated thread for processing raw sensor data - optimized for high throughput."""
        print("Data processing thread started")
        
        # Process data in batches for better efficiency
        batch_size = 10
        raw_data_batch = []
        
        while self.running:
            try:
                # Collect a batch of data points
                batch_timeout = 0.01  # 10ms timeout for batch collection
                batch_start_time = time.time()
                
                while len(raw_data_batch) < batch_size and (time.time() - batch_start_time) < batch_timeout:
                    try:
                        timestamp, voltage_ratio = self.raw_data_queue.get(timeout=0.001)
                        raw_data_batch.append((timestamp, voltage_ratio))
                        self.data_rate_counter += 1
                    except queue.Empty:
                        break  # No more data available right now
                
                # Process the batch
                if raw_data_batch:
                    # Store all data points in buffer efficiently
                    with self.buffer_lock:
                        self.high_freq_buffer.extend(raw_data_batch)
                    
                    # Process only the latest data point for GUI/logging
                    latest_timestamp, latest_voltage_ratio = raw_data_batch[-1]
                    
                    # Force calculation for latest point
                    if self.GAIN is not None and self.OFFSET is not None:
                        force = (latest_voltage_ratio - self.OFFSET) * self.GAIN
                        self.latest_calibrated_force = force
                        
                        # Check if we should update GUI (force-based triggering)
                        should_update_gui = True
                        if self.use_force_based_trigger and self.last_displayed_force is not None:
                            force_change = abs(force - self.last_displayed_force)
                            should_update_gui = force_change >= self.force_change_trigger_N
                        
                        # Rate-limited GUI updates
                        current_time = time.time()
                        if should_update_gui and (current_time - self.last_gui_update > self.gui_update_interval):
                            self.last_gui_update = current_time
                            self.last_displayed_force = force
                            
                            # Send GUI update command (non-blocking)
                            gui_command = ("update_force", f"Force: {force:.6f} N")
                            try:
                                self.gui_update_queue.put_nowait(gui_command)
                            except queue.Full:
                                pass  # Skip GUI update if queue is full
                        
                        # High-frequency logging queue pushes - push every data point from batch
                        if self.output_force_queue:
                            for timestamp, voltage_ratio in raw_data_batch:
                                if self.GAIN is not None and self.OFFSET is not None:
                                    batch_force = (voltage_ratio - self.OFFSET) * self.GAIN
                                    try:
                                        self.output_force_queue.put_nowait(("force_calibrated", batch_force))
                                    except queue.Full:
                                        # Only log queue full warning occasionally
                                        if int(current_time) % 5 == 0:  # Every 5 seconds
                                            print("Warning: Output force queue full, dropping data")
                                        break  # Stop processing batch if queue is full
                                        
                    else:
                        # Not calibrated - update GUI with latest voltage ratio
                        current_time = time.time()
                        if current_time - self.last_gui_update > self.gui_update_interval:
                            self.last_gui_update = current_time
                            
                            voltage_text = f"Voltage Ratio: {latest_voltage_ratio:.8f} (Calibration needed)"
                            gui_command = ("update_voltage", voltage_text)
                            try:
                                self.gui_update_queue.put_nowait(gui_command)
                            except queue.Full:
                                pass
                    
                    # Clear the batch
                    raw_data_batch.clear()
                    
            except Exception as e:
                print(f"Error in data processing loop: {e}")
                raw_data_batch.clear()  # Clear batch on error
                time.sleep(0.001)  # Brief pause on error

    def _gui_update_loop(self):
        """Dedicated thread for updating GUI elements safely."""
        print("GUI update thread started")
        
        while self.running:
            try:
                # Get GUI update command with timeout
                command, data = self.gui_update_queue.get(timeout=0.1)
                
                # Schedule GUI update on main thread (thread-safe)
                if self.parent_window:
                    if command == "update_force":
                        self.parent_window.after_idle(self._safe_update_force_labels, data)
                    elif command == "update_voltage":
                        self.parent_window.after_idle(self._safe_update_voltage_labels, data)
                
            except queue.Empty:
                continue  # Timeout is normal
            except Exception as e:
                print(f"Error in GUI update loop: {e}")
                time.sleep(0.01)

    def _performance_monitor_loop(self):
        """Monitor actual data acquisition performance."""
        print("Performance monitor thread started")
        
        while self.running:
            try:
                time.sleep(1.0)  # Check every second
                
                current_time = time.time()
                elapsed = current_time - self.last_rate_check
                
                if elapsed >= 1.0:
                    self.actual_sample_rate = self.data_rate_counter / elapsed
                    
                    # Print performance info every 10 seconds (DISABLED for cleaner debug output)
                    # if int(current_time) % 10 == 0:
                    #     print(f"Force gauge: {self.actual_sample_rate:.1f} Hz actual rate, "
                    #           f"Queue: {self.raw_data_queue.qsize()}/{self.raw_data_queue.maxsize}")
                    
                    self.data_rate_counter = 0
                    self.last_rate_check = current_time
                    
            except Exception as e:
                print(f"Error in performance monitor: {e}")
                time.sleep(1.0)

    def _safe_update_force_labels(self, text):
        """Safely update force labels on main thread."""
        try:
            if self.force_status_label and hasattr(self.force_status_label, 'winfo_exists') and self.force_status_label.winfo_exists():
                self.force_status_label.config(text=text)
        except Exception as e:
            self.force_status_label = None
            
        try:
            if self.large_force_readout_label and hasattr(self.large_force_readout_label, 'winfo_exists') and self.large_force_readout_label.winfo_exists():
                self.large_force_readout_label.config(text=text)
        except Exception as e:
            self.large_force_readout_label = None

    def _safe_update_voltage_labels(self, text):
        """Safely update voltage labels on main thread."""
        try:
            if self.force_status_label and hasattr(self.force_status_label, 'winfo_exists') and self.force_status_label.winfo_exists():
                self.force_status_label.config(text=text)
        except Exception as e:
            self.force_status_label = None
            
        try:
            if self.large_force_readout_label and hasattr(self.large_force_readout_label, 'winfo_exists') and self.large_force_readout_label.winfo_exists():
                self.large_force_readout_label.config(text="Force: --- N (Calibrate)")
        except Exception as e:
            self.large_force_readout_label = None

    def initialize_phidget_background(self):
        """Initialize Phidget in background thread to prevent GUI freezing."""
        try:
            self.initialize_phidget()
        except Exception as e:
            print(f"Background Phidget initialization failed: {e}")
            # Schedule error display on main thread
            if hasattr(self, 'parent_window') and self.parent_window:
                self.parent_window.after(10, lambda: messagebox.showerror(
                    "Phidget Error", 
                    f"Failed to initialize Phidget: {e}", 
                    parent=self.parent_window
                ))

    def check_device_connection(self):
        """Check if the Phidget device is connected and accessible."""
        try:
            # Create a temporary VoltageRatioInput to test connection
            test_device = VoltageRatioInput()
            test_device.setChannel(2)
            
            # Try to open with a short timeout just to test
            print("Testing device connection...")
            test_device.openWaitForAttachment(2000)  # 2 second timeout
            
            # If we get here, device is accessible
            test_device.close()
            print("Device connection test: SUCCESS")
            return True
            
        except PhidgetException as ex:
            print(f"Device connection test: FAILED - {ex.description}")
            return False
        except Exception as e:
            print(f"Device connection test: ERROR - {e}")
            return False

    def retry_connection(self):
        """Manually retry the Phidget connection."""
        print("Manual connection retry requested...")
        
        # Close existing connection if any
        try:
            if hasattr(self, 'voltage_ratio_input') and self.voltage_ratio_input:
                self.voltage_ratio_input.close()
                time.sleep(1)  # Wait for clean closure
        except:
            pass
        
        # Try to reconnect
        self.initialize_phidget()

    def initialize_phidget(self):
        try:
            print("Initializing VoltageRatioInput (ForceGaugeManager)...")
            print("Device detected in Windows: 4x Bridge Phidget (VID_06C2&PID_003B)")
            
            # Create the VoltageRatioInput object
            self.voltage_ratio_input = VoltageRatioInput()
            
            # Set device parameters
            print("Setting device parameters...")
            self.voltage_ratio_input.setHubPort(-1)  # Direct USB connection
            self.voltage_ratio_input.setChannel(2)   # Channel 2 for force sensor
            
            # Set event handlers
            self.voltage_ratio_input.setOnVoltageRatioChangeHandler(self._onVoltageRatioChange)
            self.voltage_ratio_input.setOnAttachHandler(self._onAttach)
            self.voltage_ratio_input.setOnDetachHandler(self._onDetach)
            self.voltage_ratio_input.setOnErrorHandler(self._onError)
            
            # Try connection with reasonable timeout
            print("Attempting connection with 8s timeout...")
            self.voltage_ratio_input.openWaitForAttachment(8000)
            
            print("Phidget connected successfully (ForceGaugeManager)!")
            
        except PhidgetException as ex:
            if ex.code == 3:  # Timeout error
                print("Connection timed out. Trying alternative channels...")
                # Try other channels if channel 2 fails
                for alt_channel in [0, 1, 3]:
                    try:
                        print(f"Trying channel {alt_channel}...")
                        
                        # Clean up previous attempt
                        try:
                            if hasattr(self, 'voltage_ratio_input'):
                                self.voltage_ratio_input.close()
                        except:
                            pass
                        
                        # Create new connection
                        self.voltage_ratio_input = VoltageRatioInput()
                        self.voltage_ratio_input.setHubPort(-1)
                        self.voltage_ratio_input.setChannel(alt_channel)
                        self.voltage_ratio_input.setOnVoltageRatioChangeHandler(self._onVoltageRatioChange)
                        self.voltage_ratio_input.setOnAttachHandler(self._onAttach)
                        self.voltage_ratio_input.setOnDetachHandler(self._onDetach)
                        self.voltage_ratio_input.setOnErrorHandler(self._onError)
                        
                        self.voltage_ratio_input.openWaitForAttachment(5000)
                        print(f"Success with channel {alt_channel}!")
                        return
                        
                    except PhidgetException:
                        print(f"Channel {alt_channel} also failed")
                        continue
            
            # If we get here, all attempts failed
            traceback.print_exc()
            error_msg = f"PhidgetException {ex.code} ({ex.description}): {ex.details}\n\n"
            error_msg += "Troubleshooting steps:\n"
            error_msg += "1. Unplug and reconnect the USB cable\n"
            error_msg += "2. Close any Phidget Control Panel applications\n"
            error_msg += "3. Restart the application\n"
            error_msg += "4. Check Device Manager for device status"
            print(f"PhidgetException {ex.code} ({ex.description}): {ex.details}")
            raise  # Re-raise for background thread handling
            
        except Exception as e:
            traceback.print_exc()
            print(f"Unexpected error in initialize_phidget (ForceGaugeManager): {e}")
            raise  # Re-raise for background thread handling

    def _onAttach(self, phidget):
        print("Phidget device attached (ForceGaugeManager).")
        try:
            # Do minimal configuration in the callback to avoid blocking
            print("Setting basic bridge configuration...")
            
            # Set bridge gain
            phidget.setBridgeGain(BridgeGain.BRIDGE_GAIN_1)
            
            # Set a reasonable default data interval (will be updated later)
            phidget.setDataInterval(25)  # 40Hz default
            
            # Enable bridge if available
            if hasattr(phidget, 'setBridgeEnabled'):
                phidget.setBridgeEnabled(True)
                print("Bridge mode enabled")
            
            # Start with continuous updates
            if hasattr(phidget, 'setVoltageRatioChangeTrigger'):
                phidget.setVoltageRatioChangeTrigger(0.0)
                print("Change trigger set to 0 for continuous updates")
                
            print("Basic Phidget configuration complete")
            
            # Schedule GUI sampling rate update for later (thread-safe)
            if hasattr(self, 'parent_window') and self.parent_window:
                self.parent_window.after(100, self._update_sampling_rate_from_gui_safe)
            
        except Exception as e:
            print(f"Warning: Could not configure Phidget settings: {e}")

    def _update_sampling_rate_from_gui_safe(self):
        """Thread-safe method to update sampling rate from GUI."""
        try:
            if (self.voltage_ratio_input and 
                self.sensor_window_ref and 
                hasattr(self.sensor_window_ref, 'sampling_rate_entry')):
                
                gui_sampling_rate_str = self.sensor_window_ref.sampling_rate_entry.get()
                if gui_sampling_rate_str and gui_sampling_rate_str.isdigit():
                    sampling_interval_ms = int(gui_sampling_rate_str)
                    print(f"Updating sampling rate from GUI: {sampling_interval_ms}ms")
                    self.voltage_ratio_input.setDataInterval(sampling_interval_ms)
                    print(f"Hardware sampling rate updated to {1000/sampling_interval_ms:.1f}Hz")
        except Exception as e:
            print(f"Could not update sampling rate from GUI: {e}")

    def _onDetach(self, phidget):
        print("Phidget device detached (ForceGaugeManager).")
        # Update status label, disable calibration buttons, etc.

    def _onError(self, phidget, errorCode, errorString):
        print(f"Phidget Error (ForceGaugeManager): {errorString} (Code: {errorCode})")
        # Potentially show a messagebox or update a status label

    def _onVoltageRatioChange(self, phidget, voltageRatio):
        """Ultra-fast callback - just capture data and queue it."""
        try:
            # Just capture timestamp and voltage ratio - minimize processing in callback
            timestamp = time.time()
            
            # Push to raw data queue (non-blocking)
            try:
                self.raw_data_queue.put_nowait((timestamp, voltageRatio))
            except queue.Full:
                # If queue is full, we're getting data faster than we can process
                # This is actually good - means we're not losing the high frequency data
                pass
                
        except Exception as e:
            # Minimal error handling to avoid slowing down the callback
            print(f"Error in voltage ratio callback: {e}")

    def set_high_frequency_logging(self, enabled=True):
        """Enable/disable high-frequency logging to output queue."""
        self.high_freq_logging_enabled = enabled
        if enabled:
            print("High-frequency logging enabled - all data points will be logged")
        else:
            print("High-frequency logging disabled - rate-limited logging active")

    def get_performance_stats(self):
        """Get current performance statistics."""
        return {
            'actual_sample_rate': self.actual_sample_rate,
            'raw_queue_size': self.raw_data_queue.qsize(),
            'raw_queue_max': self.raw_data_queue.maxsize,
            'gui_queue_size': self.gui_update_queue.qsize(),
            'buffer_size': len(self.high_freq_buffer),
            'high_freq_logging': getattr(self, 'high_freq_logging_enabled', True)
        }

    def close(self):
        """Properly close the ForceGaugeManager and all threads."""
        print("Closing ForceGaugeManager...")
        
        # Stop processing threads
        self.stop_processing()
        
        # Close Phidget connection
        try:
            if self.voltage_ratio_input:
                self.voltage_ratio_input.close()
                print("Phidget connection closed")
        except Exception as e:
            print(f"Error closing Phidget: {e}")

    def stop_processing(self):
        """Clean shutdown of processing threads."""
        print("Stopping force gauge processing...")
        self.running = False
        
        # Wait for threads to finish
        for thread in self.threads:
            if thread.is_alive():
                thread.join(timeout=1.0)
        
        print("Force gauge processing stopped")

    def get_latest_calibrated_force(self):
        """Returns the latest calibrated force reading."""
        return self.latest_calibrated_force

    def get_force_N(self):
        """
        Returns the latest calibrated force reading in Newtons.
        Provides direct access to the latest calibrated force.
        """
        # self.latest_calibrated_force is initialized to 0.0 and updated with float values.
        return self.latest_calibrated_force

    def get_buffered_force_data(self, time_window_seconds=None):
        """
        Retrieve high-frequency buffered force data.
        
        Args:
            time_window_seconds: If specified, only return data from the last N seconds
            
        Returns:
            List of (timestamp, voltage_ratio) tuples
        """
        with self.buffer_lock:
            if time_window_seconds is None:
                return list(self.high_freq_buffer)
            else:
                current_time = time.time()
                cutoff_time = current_time - time_window_seconds
                return [(t, v) for t, v in self.high_freq_buffer if t >= cutoff_time]
    
    def get_buffer_stats(self):
        """Get statistics about the buffering performance."""
        with self.buffer_lock:
            buffer_len = len(self.high_freq_buffer)
            if buffer_len < 2:
                return {"length": buffer_len, "rate_hz": 0, "time_span": 0}
            
            oldest_time = self.high_freq_buffer[0][0]
            newest_time = self.high_freq_buffer[-1][0]
            time_span = newest_time - oldest_time
            rate_hz = buffer_len / time_span if time_span > 0 else 0
            
            return {
                "length": buffer_len,
                "rate_hz": rate_hz,
                "time_span": time_span,
                "oldest_timestamp": oldest_time,
                "newest_timestamp": newest_time
            }

    def is_calibrated(self):
        """Returns true if the gauge has been calibrated at least once."""
        return self.calibrated_once

    def calibrate_force_gauge(self):
        try:
            print("Starting calibration (ForceGaugeManager)...")
            if not self.voltage_ratio_input or not self.voltage_ratio_input.getAttached():
                messagebox.showerror("Calibration Error", "Force sensor not attached.", parent=self.parent_window)
                return

            messagebox.showinfo("Calibration Step 1", "Please ensure the load cell is at zero force, then click OK.", parent=self.parent_window)
            time.sleep(0.5) # Allow sensor to stabilize if needed, though getVoltageRatio should be current
            zero_force_voltage_ratio = self.voltage_ratio_input.getVoltageRatio()
            self.OFFSET = zero_force_voltage_ratio
            print(f"Zero force voltage ratio (OFFSET): {self.OFFSET:.8f}")

            known_force_str = simpledialog.askstring("Calibration Step 2", "Enter the known force in Newtons (N):", parent=self.parent_window)
            if known_force_str is None: # User cancelled
                print("Calibration cancelled by user at known force input.")
                return 
            
            try:
                known_force = float(known_force_str)
            except ValueError:
                messagebox.showerror("Calibration Error", "Invalid force value entered. Please enter a number.", parent=self.parent_window)
                return

            messagebox.showinfo("Calibration Step 2", f"Please apply the known force of {known_force:.4f} N to the load cell, then click OK.", parent=self.parent_window)
            time.sleep(0.5) 
            known_force_voltage_ratio = self.voltage_ratio_input.getVoltageRatio()

            if abs(known_force_voltage_ratio - self.OFFSET) < 1e-9: # Check for significant change
                messagebox.showerror("Calibration Error", "Voltage ratio did not change significantly. Check applied force or sensor connection.", parent=self.parent_window)
                return

            self.GAIN = known_force / (known_force_voltage_ratio - self.OFFSET)
            print(f"Voltage ratio with known force: {known_force_voltage_ratio:.8f}")
            print(f"Calibration complete. GAIN: {self.GAIN:.4f}, OFFSET: {self.OFFSET:.8f}")

            if self.gain_label:
                self.gain_label.config(text=f"Gain: {self.GAIN:.4f}")
            if self.offset_label:
                self.offset_label.config(text=f"Offset: {self.OFFSET:.8f}")
            
            if self.GAIN is not None and self.OFFSET is not None:
                self.calibrated_once = True
                
                # Enable force-based change detection after successful calibration
                self.use_force_based_trigger = True
                self.last_displayed_force = None  # Reset for first force reading
                print(f"Force-based change detection enabled with trigger: {self.force_change_trigger_N} N")
                
                if self.sensor_window_ref:
                    self.sensor_window_ref.update_calibration_status_for_main_app(True)
                messagebox.showinfo("Calibration Complete", 
                    f"Calibration successful.\nGain: {self.GAIN:.4f}\nOffset: {self.OFFSET:.8f}\n\n"
                    f"Smart update mode enabled:\n"
                    f"GUI will update when force changes by ≥{self.force_change_trigger_N} N", 
                    parent=self.parent_window)
            else:
                if self.sensor_window_ref:
                    self.sensor_window_ref.update_calibration_status_for_main_app(False)

        except PhidgetException as pe:
            print(f"Phidget error during calibration (ForceGaugeManager): {pe}")
            messagebox.showerror("Calibration Error", f"Phidget error: {pe.description}", parent=self.parent_window)
        except Exception as e:
            print(f"Error during calibration (ForceGaugeManager): {e}")
            messagebox.showerror("Calibration Error", f"An error occurred during calibration: {e}", parent=self.parent_window)
            traceback.print_exc()

    def quick_calibrate_force_gauge(self):
        """Quick calibration using values from the most recent saved calibration file."""
        import os
        import glob
        
        # Default values as fallback
        default_gain = 10118.0739
        default_offset = -0.00000914
        
        try:
            # Look for the most recent calibration file
            current_dir = os.getcwd()
            calibration_files = glob.glob(os.path.join(current_dir, "force_gauge_calibration_*.txt"))
            
            if calibration_files:
                # Get the most recent file by modification time
                latest_file = max(calibration_files, key=os.path.getmtime)
                print(f"Loading calibration from: {latest_file}")
                
                # Read the calibration values
                with open(latest_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('GAIN='):
                            self.GAIN = float(line.split('=')[1])
                        elif line.startswith('OFFSET='):
                            self.OFFSET = float(line.split('=')[1])
                
                message = f"Calibration loaded from file:\n{os.path.basename(latest_file)}"
                print(f"Loaded GAIN: {self.GAIN:.4f}, OFFSET: {self.OFFSET:.8f}")
                
            else:
                # No saved files found, use defaults
                self.GAIN = default_gain
                self.OFFSET = default_offset
                message = "No saved calibration found.\nUsing default values."
                print("No calibration files found, using default values")
                
        except Exception as e:
            # Error reading file, use defaults
            print(f"Error reading calibration file: {e}")
            self.GAIN = default_gain
            self.OFFSET = default_offset
            message = f"Error reading calibration file.\nUsing default values.\nError: {e}"
        
        # Update UI
        if self.gain_label:
            self.gain_label.config(text=f"Gain: {self.GAIN:.4f}")
        if self.offset_label:
            self.offset_label.config(text=f"Offset: {self.OFFSET:.8f}")
        
        self.calibrated_once = True
        
        # Enable force-based change detection after successful quick calibration
        self.use_force_based_trigger = True
        self.last_displayed_force = None  # Reset for first force reading
        print(f"Force-based change detection enabled with trigger: {self.force_change_trigger_N} N")
        
        if self.sensor_window_ref:
            self.sensor_window_ref.update_calibration_status_for_main_app(True)
        
        print(f"Quick calibration applied. GAIN: {self.GAIN:.4f}, OFFSET: {self.OFFSET:.8f}")
        
        enhanced_message = (f"{message}\n\n"
                           f"Smart update mode enabled:\n"
                           f"GUI will update when force changes by ≥{self.force_change_trigger_N} N")
        messagebox.showinfo("Quick Calibration", enhanced_message, parent=self.parent_window)

    def set_force_change_trigger(self, trigger_force_N):
        """
        Set the force change trigger threshold.
        
        Args:
            trigger_force_N: Force change threshold in Newtons. 
                           Set to 0 for continuous updates.
                           Typical values: 0.001N (1mN) for sensitive, 0.01N for less sensitive
        """
        old_trigger = self.force_change_trigger_N
        self.force_change_trigger_N = max(0.0, float(trigger_force_N))
        
        if self.force_change_trigger_N == 0:
            self.use_force_based_trigger = False
            print(f"Force-based triggering disabled (continuous updates)")
        else:
            if self.calibrated_once:
                self.use_force_based_trigger = True
                print(f"Force change trigger updated: {old_trigger} N → {self.force_change_trigger_N} N")
            else:
                print(f"Force change trigger set to {self.force_change_trigger_N} N (will activate after calibration)")
        
        # Reset last displayed force to ensure immediate update
        self.last_displayed_force = None

    def get_force_change_trigger(self):
        """Get the current force change trigger threshold in Newtons."""
        return self.force_change_trigger_N

    def is_using_force_trigger(self):
        """Check if force-based triggering is currently active."""
        return self.use_force_based_trigger and self.calibrated_once

    def stop_force_reading_thread(self):
        """Stops the force reading by closing the Phidget device."""
        print("ForceGaugeManager: stop_force_reading_thread called, invoking close_phidget.")
        self.close_phidget()

    def close_phidget(self):
        print("Closing Phidget connection (ForceGaugeManager)...")
        if self.voltage_ratio_input and self.voltage_ratio_input.getAttached():
            try:
                self.voltage_ratio_input.close()
                print("Phidget connection closed successfully (ForceGaugeManager).")
            except PhidgetException as ex:
                print(f"PhidgetException during close: {ex.description}")
        elif self.voltage_ratio_input:
             print("Phidget was initialized but not attached or already closed.")
        else:
            print("No Phidget to close.")

    def update_position_cache(self, position):
        """Cache the latest position for high-frequency force logging."""
        # Simple position caching - can be enhanced later if needed
        pass

    def set_peak_force_logger(self, peak_force_logger):
        """Set the PeakForceLogger instance for high-frequency logging."""
        # Simple interface - can be enhanced later if needed
        pass

    def set_data_interval(self, interval_ms):
        """Set the data interval for the force gauge sensor."""
        try:
            if self.voltage_ratio_input and self.voltage_ratio_input.getAttached():
                self.voltage_ratio_input.setDataInterval(interval_ms)
                print(f"ForceGaugeManager: Data interval set to {interval_ms}ms ({1000/interval_ms:.1f}Hz)")
                return True
            else:
                print("ForceGaugeManager: Cannot set data interval - device not attached")
                return False
        except PhidgetException as pe:
            print(f"ForceGaugeManager: Error setting data interval: {pe}")
            return False

    def update_sampling_rate_from_gui(self):
        """Update hardware sampling rate based on current GUI setting."""
        if (self.sensor_window_ref and 
            hasattr(self.sensor_window_ref, 'sampling_rate_entry')):
            try:
                gui_sampling_rate_str = self.sensor_window_ref.sampling_rate_entry.get()
                if gui_sampling_rate_str and gui_sampling_rate_str.isdigit():
                    sampling_interval_ms = int(gui_sampling_rate_str)
                    success = self.set_data_interval(sampling_interval_ms)
                    if success:
                        print(f"Hardware sampling rate updated from GUI: {sampling_interval_ms}ms ({1000/sampling_interval_ms:.1f}Hz)")
                    return success
                else:
                    print(f"Invalid GUI sampling rate value: '{gui_sampling_rate_str}'")
                    return False
            except Exception as e:
                print(f"Error updating sampling rate from GUI: {e}")
                return False
        else:
            print("GUI sampling rate entry not available")
            return False