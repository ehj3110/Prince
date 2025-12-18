import os
import csv
import datetime
import traceback
# For potential future use, e.g. unique filenames

class LayerLogger:
    def __init__(self, status_callback, sensor_data_window_ref):
        self.status_callback = status_callback
        self.sensor_data_window_ref = sensor_data_window_ref

        self.is_configured_for_run = False # Renamed from is_enabled_for_run for clarity
        self.logging_windows_filepath = None # Full path to logging_windows.csv
        self.base_log_directory = None       # Directory where autolog_L...csv files will be saved (e.g., .../Printing_Logs/YYYY-MM-DD/)
        self.active_logging_windows = []
        
        self.current_auto_log_filepath = None
        self.is_current_session_active = False
        self.current_session_start_layer = -1
        self.current_session_end_layer = -1
        self.status_callback("AutomatedLayerLogger initialized.")

    def configure_run(self, print_run_number, base_log_directory, logging_windows_filepath): # Removed enabled and date_str
        self.status_callback(f"AutomatedLayerLogger: Configuring run for Print {print_run_number}...")
        self.base_log_directory = base_log_directory
        self.logging_windows_filepath = logging_windows_filepath
        self.active_logging_windows = []
        self.current_auto_log_filepath = None
        self.is_current_session_active = False
        self.current_session_start_layer = -1
        self.current_session_end_layer = -1
        self.is_configured_for_run = False # Default to not configured until checks pass

        if not self.base_log_directory or not os.path.isdir(self.base_log_directory):
            self.status_callback(f"AutomatedLayerLogger: Invalid base_log_directory: {self.base_log_directory}", error=True)
            return False
        
        if not self.logging_windows_filepath or not os.path.exists(self.logging_windows_filepath):
            self.status_callback(f"AutomatedLayerLogger: Logging windows file not found: {self.logging_windows_filepath}", error=True)
            return False

        try:
            with open(self.logging_windows_filepath, 'r', newline='') as f:
                reader = csv.reader(f)
                header = next(reader, None)
                if header is None or [h.strip().lower() for h in header] != ["startlayer", "endlayer"]:
                    self.status_callback(f"AutomatedLayerLogger: Invalid header in {os.path.basename(self.logging_windows_filepath)}. Expected 'StartLayer,EndLayer'.", error=True)
                    return False

                for row in reader:
                    if len(row) == 2:
                        try:
                            start_layer, end_layer = int(row[0]), int(row[1])
                            if start_layer > 0 and end_layer >= start_layer:
                                self.active_logging_windows.append((start_layer, end_layer))
                            else:
                                self.status_callback(f"AutomatedLayerLogger: Invalid layer range in windows file: {row}. Skipping.", error=True)
                        except ValueError:
                            self.status_callback(f"AutomatedLayerLogger: Non-integer layer in windows file: {row}. Skipping.", error=True)
            
            self.status_callback(f"AutomatedLayerLogger: Loaded {len(self.active_logging_windows)} logging windows from {os.path.basename(self.logging_windows_filepath)}.")
            if not self.active_logging_windows:
                 self.status_callback("AutomatedLayerLogger: No valid logging windows loaded. Auto-logging will not occur for specific layers.", warning=True)
            
            self.is_configured_for_run = True # Configuration successful
            return True
        except Exception as e:
            self.status_callback(f"AutomatedLayerLogger: Error reading {os.path.basename(self.logging_windows_filepath)}: {e}", error=True)
            detailed_error = traceback.format_exc()
            print(f"Traceback for AutomatedLayerLogger configure_run error:\\n{detailed_error}")
            return False

    def _start_new_auto_log_session(self, start_layer, end_layer):
        if not self.is_configured_for_run: # Check if configured
            self.status_callback("AutomatedLayerLogger: Cannot start session, run not configured or configuration failed.", error=True)
            return

        if self.is_current_session_active:
            self.status_callback("AutomatedLayerLogger: Tried to start a new session while one is active. Stopping current first.", warning=True)
            self._stop_current_auto_log_session()

        if not self.base_log_directory:
            self.status_callback("AutomatedLayerLogger: Base log directory not set. Cannot start session.", error=True)
            return

        try:
            # base_log_directory is already the date-specific directory (e.g., .../Printing_Logs/YYYY-MM-DD/)
            # So, autolog files are saved directly into it.
            os.makedirs(self.base_log_directory, exist_ok=True) # Ensure it still exists
            
            filename_only = f"autolog_L{start_layer}-L{end_layer}.csv"
            self.current_auto_log_filepath = os.path.join(self.base_log_directory, filename_only)

            self.status_callback(f"AutomatedLayerLogger: Attempting to start recording for L{start_layer}-L{end_layer} to {os.path.basename(self.current_auto_log_filepath)}")

            if self.sensor_data_window_ref:
                recording_started = self.sensor_data_window_ref.start_recording(
                    filepath_override=self.current_auto_log_filepath,
                    called_by_auto_logger=True
                )
                if recording_started:
                    self.is_current_session_active = True
                    self.current_session_start_layer = start_layer
                    self.current_session_end_layer = end_layer
                    self.status_callback(f"Automated recording started for L{start_layer}-L{end_layer} to {os.path.basename(self.current_auto_log_filepath)}.")
                else:
                    self.status_callback(f"AutomatedLayerLogger: SensorDataWindow failed to start recording for {os.path.basename(self.current_auto_log_filepath)}.", error=True)
                    self.current_auto_log_filepath = None
            else:
                self.status_callback("AutomatedLayerLogger: SensorDataWindow reference not available.", error=True)

        except Exception as e:
            self.status_callback(f"AutomatedLayerLogger: Error starting new log session: {e}", error=True)
            detailed_error = traceback.format_exc()
            print(f"Traceback for AutomatedLayerLogger _start_new_auto_log_session error:\\n{detailed_error}")
            self.current_auto_log_filepath = None
            self.is_current_session_active = False

    def _stop_current_auto_log_session(self):
        if not self.is_current_session_active:
            return

        if not self.sensor_data_window_ref:
            self.status_callback("AutomatedLayerLogger: Cannot stop auto-log, SensorDataWindow reference not set.", error=True)
            return

        try:
            self.status_callback(f"AutomatedLayerLogger: Attempting to stop recording for L{self.current_session_start_layer}-L{self.current_session_end_layer}")
            self.sensor_data_window_ref.stop_recording(called_by_auto_logger=True)
            self.status_callback(f"Automated recording stopped for L{self.current_session_start_layer}-L{self.current_session_end_layer}.")
        except Exception as e:
            self.status_callback(f"AutomatedLayerLogger: Error stopping log session: {e}", error=True)
            detailed_error = traceback.format_exc()
            print(f"Traceback for AutomatedLayerLogger _stop_current_auto_log_session error:\\n{detailed_error}")
        finally:
            self.is_current_session_active = False
            # Do not reset current_session_start_layer and current_session_end_layer here,
            # they are useful for the status message just before this block.
            # Reset them after the status message or if a new session starts.
            # self.current_session_start_layer = -1 # Keep for reference until next session or clear explicitly
            # self.current_session_end_layer = -1
            self.current_auto_log_filepath = None


    # --- Public methods to be called by SensorDataWindow or MyWindow ---

    def update_current_layer(self, current_layer_num, current_z_mm):
        """
        Called by SensorDataWindow (which is called by MyWindow's print_t) for each layer.
        Determines if a logging session needs to start or stop.
        """
        if not self.is_configured_for_run or not self.active_logging_windows: # Check if configured and has windows
            return

        # Check if the current layer falls into any defined logging window
        should_be_logging_now = False
        target_start_layer = -1
        target_end_layer = -1

        for start_layer, end_layer in self.active_logging_windows:
            if start_layer <= current_layer_num <= end_layer:
                should_be_logging_now = True
                target_start_layer = start_layer
                target_end_layer = end_layer
                break
        
        if should_be_logging_now and not self.is_current_session_active:
            self._start_new_auto_log_session(target_start_layer, target_end_layer)
        elif not should_be_logging_now and self.is_current_session_active:
            if not (self.current_session_start_layer <= current_layer_num <= self.current_session_end_layer):
                 self._stop_current_auto_log_session()
        elif should_be_logging_now and self.is_current_session_active:
            if not (self.current_session_start_layer == target_start_layer and self.current_session_end_layer == target_end_layer):
                self.status_callback(f"AutomatedLayerLogger: Transitioning from L{self.current_session_start_layer}-L{self.current_session_end_layer} to L{target_start_layer}-L{target_end_layer}.")
                self._stop_current_auto_log_session()
                self._start_new_auto_log_session(target_start_layer, target_end_layer)


    def stop_all_logging_sessions(self):
        self.status_callback("AutomatedLayerLogger: stop_all_logging_sessions called.")
        if self.is_current_session_active:
            self.status_callback("AutomatedLayerLogger: Active session found, stopping it.")
            self._stop_current_auto_log_session()
        else:
            self.status_callback("AutomatedLayerLogger: No active session to stop.")
        self.is_configured_for_run = False # Mark as no longer configured for the current run

    def notify_external_stop(self):
        """
        Called by SensorDataWindow if manual recording is stopped while an auto-log session *might* be active.
        This ensures the state of AutomatedLayerLogger is consistent.
        """
        if self.is_current_session_active:
            self.status_callback(f"AutomatedLayerLogger: Notified of external stop during L{self.current_session_start_layer}-L{self.current_session_end_layer} session. Updating state.")
            # The actual file closing is handled by SensorDataWindow.stop_recording()
            # We just need to update our internal state.
            self.is_current_session_active = False
            # self.current_session_start_layer = -1 # Keep for reference
            # self.current_session_end_layer = -1
            self.current_auto_log_filepath = None
            # Do not call _stop_current_auto_log_session() again as it would re-trigger stop_recording in SensorDataWindow
        else:
            self.status_callback("AutomatedLayerLogger: Notified of external stop, but no auto-session was marked active by AutomatedLayerLogger.")