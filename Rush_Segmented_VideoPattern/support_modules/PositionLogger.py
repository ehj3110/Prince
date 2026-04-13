import threading
import time
import csv
import os
import queue
from zaber_motion import Units
import traceback # Make sure traceback is imported

class PositionLogger(threading.Thread):
    """
    A class that runs as a separate thread to log Zaber axis position and
    optionally Phidgets force data to a CSV file. It also sends position
    data to a queue for real-time plotting.
    """
    def __init__(self, axis_obj, stop_event, log_file_name="sensor_log.csv",
                 log_interval_ms=200, position_plot_queue=None, force_data_queue_ref=None,
                 csv_logging_initially_enabled=False):
        super().__init__()
        self.axis = axis_obj
        self.stop_event = stop_event
        self.log_file_name = log_file_name  # This can be updated externally
        self.log_interval_s = log_interval_ms / 1000.0
        self.position_plot_queue = position_plot_queue
        self.force_data_queue_ref = force_data_queue_ref
        self.csv_logging_enabled = csv_logging_initially_enabled  # This can be updated externally
        
        self._writer = None
        self._log_file_handle = None  # Stores the open file object
        self._current_open_log_file_name = None  # Tracks the name of the file that is currently open
        # self._csv_header_written_for_current_file = False # Replaced by checking file size in _open_log_file
        self._csv_logging_session_start_time = None # Start time for the current logging session/file

        # Phase detection attributes
        self._previous_position = None
        self._stationary_count = 0  # How many consecutive readings with no motion
        self._current_phase = "Pause"  # Start with Pause (stage stationary at beginning)
        self._POSITION_CHANGE_THRESHOLD = 0.002  # mm - below this is considered stationary
        self._STATIONARY_THRESHOLD_COUNT = 3  # How many stationary readings before declaring Pause
        self._SANDWICH_DISTANCE_THRESHOLD = 1.0  # mm - small motions < 1mm might be sandwich
        self._position_at_motion_start = None  # Track position when motion begins

        self.daemon = True # Thread will exit when main program exits

    def set_phase(self, phase_name):
        """
        Explicitly set the current phase from Prince_Segmented.
        This overrides movement-based phase detection.
        
        Args:
            phase_name: One of "Exposure", "Lift", "Lift-Stage1", "Lift-Stage2", 
                        "Retract", "Retract-Stage1", "Retract-Stage2", "Pause", "Sandwich"
        """
        self._current_phase = phase_name

    def _open_log_file(self):
        """
        Opens the log file specified by self.log_file_name.
        Writes a header if the file is new or empty.
        Returns True on success, False on failure.
        """
        try:
            # Ensure the directory for the log file exists
            log_dir = os.path.dirname(self.log_file_name)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            # Open the file in append mode ('a')
            self._log_file_handle = open(self.log_file_name, 'a', newline='')
            self._writer = csv.writer(self._log_file_handle)
            self._current_open_log_file_name = self.log_file_name # Track which file is open
            
            # Check if the file is empty to decide whether to write a header
            self._log_file_handle.seek(0, os.SEEK_END) # Go to the end of the file
            if self._log_file_handle.tell() == 0: # If position is 0, file is empty
                self._writer.writerow(['Elapsed Time (s)', 'Position (mm)', 'Force (N)', 'Phase'])
                self._log_file_handle.flush() # Ensure header is written immediately
            
            self._csv_logging_session_start_time = time.time() # Reset start time for this new file/session
            print(f"PositionLogger: Opened log file: {self.log_file_name}")
            return True
        except Exception as e:
            print(f"PositionLogger: Error opening log file {self.log_file_name}: {e}")
            traceback.print_exc()
            self._close_log_file() # Ensure cleanup if open failed (will nullify handles)
            return False

    def _close_log_file(self):
        """Closes the current log file if it's open and resets related attributes."""
        if self._log_file_handle:
            try:
                if not self._log_file_handle.closed:
                    self._log_file_handle.close()
                print(f"PositionLogger: Closed log file: {self._current_open_log_file_name}")
            except Exception as e:
                print(f"PositionLogger: Error closing log file {self._current_open_log_file_name}: {e}")
                traceback.print_exc()
        # Reset attributes regardless of whether close succeeded or if it was already closed
        self._log_file_handle = None
        self._writer = None
        self._current_open_log_file_name = None
        self._csv_logging_session_start_time = None
        # Reset phase tracking when closing file
        self._previous_position = None
        self._stationary_count = 0
        self._current_phase = "Pause"  # Reset to Pause (not Unknown)
        self._position_at_motion_start = None

    def _determine_phase(self, current_position):
        """
        Determines the current phase based on stage position changes.
        
        Phases:
        - Lift: Stage moving DOWN (position decreasing) by significant amount (>1mm total)
        - Lift-Stage1: First 50µm of smooth lifting (100 µm/s gentle break)
        - Lift-Stage2: Remaining lift at prescribed speed (normal peel)
        - Retract: Stage moving UP (position increasing) by significant amount (>1mm total)
        - Retract-Stage1: Most of retraction at prescribed speed (fast approach)
        - Retract-Stage2: Last 200µm of smooth retraction (100 µm/s gentle approach)
        - Pause: Stage stationary
        - Sandwich: Small downward motion (<1mm total)
        - Exposure: Stationary after retract (future enhancement - currently labeled as Pause)
        
        Args:
            current_position: Current stage position in mm
            
        Returns:
            str: Phase name
        """
        if current_position is None or not isinstance(current_position, (int, float)):
            return "Unknown"
        
        # First reading - initialize
        if self._previous_position is None:
            self._previous_position = current_position
            self._position_at_motion_start = current_position
            self._current_phase = "Pause"  # Assume starting stationary
            return self._current_phase
        
        # Calculate position change
        position_change = current_position - self._previous_position
        abs_change = abs(position_change)
        
        # Check if stationary (below threshold)
        if abs_change < self._POSITION_CHANGE_THRESHOLD:
            self._stationary_count += 1
            
            # If stationary for enough readings, declare Pause
            if self._stationary_count >= self._STATIONARY_THRESHOLD_COUNT:
                # Reset motion start position when becoming stationary
                if self._current_phase not in ["Pause", "Unknown"]:
                    self._position_at_motion_start = current_position
                self._current_phase = "Pause"
        else:
            # Motion detected - reset stationary counter
            self._stationary_count = 0
            
            # Track start of motion if coming from pause
            if self._current_phase in ["Pause", "Unknown"]:
                self._position_at_motion_start = self._previous_position
            
            # Calculate total distance traveled since motion started
            total_distance_traveled = abs(current_position - self._position_at_motion_start) if self._position_at_motion_start is not None else 0
            
            # Determine direction and classify phase
            if position_change < 0:  # Moving down (decreasing position)
                # Check if it's a small motion (sandwich) or large motion (lift)
                if total_distance_traveled < self._SANDWICH_DISTANCE_THRESHOLD:
                    self._current_phase = "Sandwich"
                else:
                    self._current_phase = "Lift"
            else:  # Moving up (increasing position)
                self._current_phase = "Retract"
        
        # Update previous position for next iteration
        self._previous_position = current_position
        
        return self._current_phase

    def run(self):
        print(f"PositionLogger: Thread started. Plotting enabled. CSV logging initially: {self.csv_logging_enabled}")
        latest_force_value_for_log = None # Persists across loops if no new force data comes in

        try:
            while not self.stop_event.is_set():
                current_loop_time = time.time()

                # --- Data Acquisition ---
                position = None 
                try:
                    if self.axis:
                        position = self.axis.get_position(unit=Units.LENGTH_MILLIMETRES)
                except Exception as e:
                    # print(f"PositionLogger: Error getting Zaber position: {e}") # Can be noisy
                    position = None # Ensure position is None on error

                if self.force_data_queue_ref:
                    try:
                        # Process all items in queue to get the latest
                        while not self.force_data_queue_ref.empty(): 
                            data_type, value = self.force_data_queue_ref.get_nowait()
                            # Assuming 'force' or 'force_calibrated' is the key for the value
                            if isinstance(data_type, str) and 'force' in data_type.lower():
                                latest_force_value_for_log = value
                    except queue.Empty:
                        pass # No new force data, keep using latest_force_value_for_log
                    except Exception as e:
                        print(f"PositionLogger: Error reading from force queue: {e}")
                        # latest_force_value_for_log remains unchanged

                # --- Plotting ---
                if self.position_plot_queue:
                    try:
                        # Ensure data is a tuple: (timestamp, position, force)
                        self.position_plot_queue.put_nowait((current_loop_time, position, latest_force_value_for_log))
                    except queue.Full:
                        # print("PositionLogger: Plot queue is full. Data point for plot lost.") # Can be noisy
                        pass
                    except Exception as e:
                        print(f"PositionLogger: Error putting data to plot queue: {e}")


                # --- CSV Logging Logic ---
                if self.csv_logging_enabled:
                    # Check if we need to open a new file or switch files
                    if self._log_file_handle is None or self.log_file_name != self._current_open_log_file_name:
                        self._close_log_file() # Close previous if any
                        if not self._open_log_file(): # Try to open the new/specified file
                            # If opening fails, it will try again in the next loop 
                            # if self.csv_logging_enabled is still true.
                            # No data will be written to CSV in this iteration if open fails.
                            pass 
                    
                    # If file is open and writer is available
                    if self._writer and self._csv_logging_session_start_time is not None:
                        elapsed_time_for_csv = current_loop_time - self._csv_logging_session_start_time
                        
                        # Use phase explicitly set by Prince_Segmented via set_phase()
                        # (No longer using movement-based phase detection)
                        
                        pos_str = f"{position:.4f}" if isinstance(position, (int, float)) else "N/A"
                        force_str = f"{latest_force_value_for_log:.6f}" if isinstance(latest_force_value_for_log, (int, float)) else "N/A"
                        
                        row_data = [
                            f"{elapsed_time_for_csv:.3f}",
                            pos_str,
                            force_str,
                            self._current_phase  # Use explicitly set phase from Prince_Segmented
                        ]
                        try:
                            self._writer.writerow(row_data)
                            if self._log_file_handle and not self._log_file_handle.closed:
                                self._log_file_handle.flush() # Ensure data is written to disk
                        except Exception as e:
                            print(f"PositionLogger: Error writing to CSV {self._current_open_log_file_name}: {e}")
                            traceback.print_exc()
                            self._close_log_file() # Close problematic file, will attempt reopen next cycle if still enabled

                else: # CSV logging is disabled
                    if self._log_file_handle is not None: # If a file is open, close it
                        self._close_log_file()

                # --- Loop Timing ---
                # Calculate time taken for the loop and sleep for the remaining interval
                elapsed_loop_time = time.time() - current_loop_time
                sleep_time = self.log_interval_s - elapsed_loop_time
                if sleep_time > 0:
                    self.stop_event.wait(sleep_time) # Use wait on the event for responsiveness
                # If sleep_time is negative, the loop took longer than the interval.
                # Consider logging this if it happens frequently, as it means you're not meeting the desired sample rate.

        except Exception as e: # Catch any unexpected errors in the main loop
            print(f"PositionLogger: Unhandled error in run loop: {e}")
            traceback.print_exc()
        finally:
            # This block executes whether the loop exits normally or due to an exception
            self._close_log_file() # Ensure the log file is closed properly
            print("PositionLogger: Thread stopped.")
    
    def save_failure_log(self, layer_num, error_message="Unknown error"):
        """
        Save all current live plot data to a failure log CSV file when a stall/fault occurs.
        
        Args:
            layer_num: The layer number where the fault occurred
            error_message: Description of the error
            
        Returns:
            Path to the saved failure log file, or None if no data available
        """
        try:
            # Get all data from the position plot queue (non-destructive read)
            if not self.position_plot_queue:
                print("PositionLogger: No position plot queue available for failure log")
                return None
            
            # Collect all data points from the queue
            data_points = []
            temp_queue = queue.Queue()
            
            # Extract all items from the queue
            while not self.position_plot_queue.empty():
                try:
                    data = self.position_plot_queue.get_nowait()
                    data_points.append(data)
                    temp_queue.put(data)  # Keep for re-adding
                except queue.Empty:
                    break
            
            # Put data back into original queue
            while not temp_queue.empty():
                try:
                    self.position_plot_queue.put_nowait(temp_queue.get_nowait())
                except queue.Full:
                    break
            
            if not data_points:
                print("PositionLogger: No data points available in position plot queue")
                return None
            
            # Generate failure log filename
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            failure_log_dir = os.path.dirname(self.log_file_name) if self.log_file_name else "."
            failure_log_filename = os.path.join(failure_log_dir, f"Failure_Log_L{layer_num}_{timestamp}.csv")
            
            # Write failure log
            with open(failure_log_filename, 'w', newline='') as f:
                writer = csv.writer(f)
                
                # Write header with metadata
                writer.writerow(['# Failure Log'])
                writer.writerow(['# Layer:', layer_num])
                writer.writerow(['# Timestamp:', time.strftime("%Y-%m-%d %H:%M:%S")])
                writer.writerow(['# Error:', error_message])
                writer.writerow(['# Data Points:', len(data_points)])
                writer.writerow([])  # Blank line
                
                # Write data header
                writer.writerow(['Elapsed Time (s)', 'Position (mm)', 'Force (N)', 'Phase'])
                
                # Write all data points
                for data in data_points:
                    if len(data) >= 3:  # Ensure we have at least time, position, force
                        writer.writerow(data)
            
            print(f"PositionLogger: Failure log saved with {len(data_points)} data points to {failure_log_filename}")
            return failure_log_filename
            
        except Exception as e:
            print(f"PositionLogger: Error saving failure log: {e}")
            traceback.print_exc()
            return None