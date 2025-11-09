from tkinter import *
from tkinter import ttk, filedialog, BooleanVar, StringVar # Ensure all are imported
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from tkinter import messagebox, font as tkFont
import queue
import threading
import os
import csv # For add_window_to_active_file
import time
import traceback
import sys
import os
from pathlib import Path

# Add current directory to path for local imports
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from zaber_motion import Units
from PositionLogger import PositionLogger
from ForceGaugeManager import ForceGaugeManager
from AutomatedLayerLogger import LayerLogger # Import LayerLogger
from PeakForceLogger import PeakForceLogger # Import the logger
from datetime import datetime # Add this import
import datetime # Ensure datetime is imported
import os # Ensure os is imported
import tkinter as tk # Ensure tkinter is imported as tk for tk.DISABLED

class SensorDataWindow:
    MAX_PLOT_POINTS = 5000 # Maximum number of data points to keep for plotting

    def __init__(self, master_window, zaber_axis_ref, main_app_status_callback, prince_main_app_ref):
        self.master = master_window
        self.zaber_axis = zaber_axis_ref
        self.update_main_status = main_app_status_callback
        self.prince_main_app_ref = prince_main_app_ref
        self.force_gauge_is_calibrated = False

        self.force_data_queue_for_logger = queue.Queue()

        self.sensor_window = Toplevel(master_window)
        self.sensor_window.title("Sensor Data & Logging")
        self.sensor_window.geometry("800x950") 
        # --- Initialize key BooleanVars and StringVars early ---
        self.record_work_var = BooleanVar(value=False) # Initialize EARLY
        self.auto_log_enabled_var = BooleanVar(value=False)
        self.active_logging_windows_filepath_var = StringVar(value="No windows file active.")
        self.current_window_start_var = StringVar()
        self.current_window_end_var = StringVar()

        # --- Paths for logging ---
        self.print_logs_base_dir = None
        self.date_specific_log_dir_for_windows_file = None # ADDED: To store the YYYY-MM-DD log path
        self.current_logging_windows_file = None # Ensure this is also initialized, though summary says it was

        # --- Define fonts and styles ---
        control_box_font = tkFont.Font(family="Helvetica", size=11) 
        control_box_title_font = tkFont.Font(family="Helvetica", size=11, weight="bold")
        control_box_borderwidth = 3

        # --- Top Banner Frame (for Title and Credit) ---
        top_banner_frame = Frame(self.sensor_window)
        top_banner_frame.pack(side=TOP, fill=X, padx=10, pady=(5, 0))

        title_font = tkFont.Font(family="Helvetica", size=20, weight="bold")
        self.lbl_title = Label(top_banner_frame, text="Sensor Readout Panel", font=title_font)
        self.lbl_title.pack(side=LEFT, padx=(0, 10))

        credit_text = '''
Professor Cheng Sun, c-sun@northwestern.edu
Evan Jones, evanjones2026@u.northwestern.edu
'''
        credit_font = tkFont.Font(family="Helvetica", size=7)
        self.lbl_credit = Label(top_banner_frame, text=credit_text, font=credit_font, justify=LEFT)
        self.lbl_credit.pack(side=RIGHT, padx=(10, 0))

        # --- Large Readouts Frame (for centering) ---
        outer_readout_frame = Frame(self.sensor_window)
        outer_readout_frame.pack(side=TOP, fill=X, padx=10, pady=(15, 5))

        readout_content_frame = Frame(outer_readout_frame)
        readout_content_frame.pack()

        readout_font = tkFont.Font(family="Helvetica", size=14, weight="bold")
        self.lbl_current_position = Label(readout_content_frame, text="Position: --- mm", font=readout_font)
        self.lbl_current_position.pack(side=LEFT, padx=(0, 20))

        self.lbl_current_force = Label(readout_content_frame, text="Force: --- N", font=readout_font)
        self.lbl_current_force.pack(side=LEFT, padx=(20, 0))

        # --- Plot Setup ---
        self.figure = Figure(figsize=(6, 3), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.ax2 = self.ax.twinx()
        self.ax.set_facecolor("white")
        self.ax2.set_facecolor("white")

        self.ax.set_title("Linear Stage Data")
        self.ax.set_xlabel("Elapsed Time (s)")
        self.ax.set_ylabel("Position (mm)", color='b')
        self.ax2.set_ylabel("Force (N)", color='r')

        self.line_position, = self.ax.plot([], [], 'b-', label='Position (mm)')
        self.line_force, = self.ax2.plot([], [], 'r-', label='Force (N)')

        lines = [self.line_position, self.line_force]
        self.ax.legend(lines, [l.get_label() for l in lines], loc='upper left')

        self.ax.tick_params(axis='y', labelcolor='b')
        self.ax2.tick_params(axis='y', labelcolor='r')

        self.canvas = FigureCanvasTkAgg(self.figure, self.sensor_window)
        self.canvas.get_tk_widget().pack(side=TOP, fill=BOTH, expand=True, padx=10, pady=(5, 0))
        self.figure.tight_layout()

        # --- Controls Frame (Below Plot) ---
        controls_main_frame = Frame(self.sensor_window, relief=GROOVE, borderwidth=control_box_borderwidth)
        controls_main_frame.pack(side=TOP, pady=(5, 10), padx=10, fill=X)

        file_path_frame = Frame(controls_main_frame)
        file_path_frame.pack(side=TOP, fill=X, pady=(5, 2), padx=5)
        Label(file_path_frame, text="File Path:", font=control_box_font).pack(side=LEFT, padx=(0, 5))
        self.file_path_entry = Entry(file_path_frame, font=control_box_font)
        self.file_path_entry.insert(0, "C:\\Users\\cheng sun\\Desktop\\Evan_AdhesionTests\\test.csv")
        self.file_path_entry.pack(side=LEFT, expand=True, fill=X)

        buttons_and_sampling_frame = Frame(controls_main_frame)
        buttons_and_sampling_frame.pack(side=TOP, fill=X, pady=(2, 5), padx=5)
        Label(buttons_and_sampling_frame, text="Sampling (ms):", font=control_box_font).pack(side=LEFT, padx=(0, 5))
        self.sampling_rate_entry = Entry(buttons_and_sampling_frame, width=6, font=control_box_font)
        self.sampling_rate_entry.insert(0, "25")
        self.sampling_rate_entry.pack(side=LEFT, padx=(0, 10))

        self.b_clear_plot = Button(buttons_and_sampling_frame, text="Clear Plot", command=self.clear_plot_data, font=control_box_font)
        self.b_clear_plot.pack(side=LEFT, padx=5)
        self.b_live_readout = Button(buttons_and_sampling_frame, text="Start Live Readout", command=self.toggle_live_readout, font=control_box_font)
        self.b_live_readout.pack(side=LEFT, padx=5)
        self.b_start_recording = Button(buttons_and_sampling_frame, text="Start Recording", command=self.toggle_recording, font=control_box_font)
        self.b_start_recording.pack(side=LEFT, padx=5)

        # --- Force Gauge Frame ---
        force_gauge_main_frame = Frame(self.sensor_window, relief=GROOVE, borderwidth=control_box_borderwidth)
        force_gauge_main_frame.pack(side=TOP, pady=(0, 10), padx=10, fill=X)
        
        Label(force_gauge_main_frame, text="Force Gauge Information", font=control_box_title_font).pack(anchor=W, padx=5, pady=(5, 2))

        # Row 1: Calibration Buttons and Force Status
        force_controls_row1 = Frame(force_gauge_main_frame)
        force_controls_row1.pack(fill=X, padx=5, pady=2)

        self.b_quick_calibrate = Button(force_controls_row1, text="Quick Calibrate", command=lambda: self.force_gauge_manager.quick_calibrate_force_gauge(), font=control_box_font)
        self.b_quick_calibrate.pack(side=LEFT, padx=(0, 5))
        
        self.b_calibrate_force_gauge = Button(force_controls_row1, text="Calibrate Force Gauge", command=lambda: self.force_gauge_manager.calibrate_force_gauge(), font=control_box_font)
        self.b_calibrate_force_gauge.pack(side=LEFT, padx=5)

        self.b_tare_force_gauge = Button(force_controls_row1, text="Tare", command=self.tare_force_gauge, font=control_box_font)
        self.b_tare_force_gauge.pack(side=LEFT, padx=5)

        self.b_save_calibration = Button(force_controls_row1, text="Save Calibration", command=self.save_force_gauge_calibration, font=control_box_font)
        self.b_save_calibration.pack(side=LEFT, padx=5)

        self.lbl_force_gauge_status = Label(force_controls_row1, text="Force: N/A", font=control_box_font, anchor=W)
        self.lbl_force_gauge_status.pack(side=LEFT, padx=5)

        # Row 2: Gain and Offset
        force_info_row2 = Frame(force_gauge_main_frame)
        force_info_row2.pack(fill=X, padx=5, pady=2)

        self.lbl_gain = Label(force_info_row2, text="Gain: N/A", font=control_box_font, anchor=W)
        self.lbl_gain.pack(side=LEFT, padx=(0, 10))
        
        self.lbl_offset = Label(force_info_row2, text="Offset: N/A", font=control_box_font, anchor=W)
        self.lbl_offset.pack(side=LEFT, padx=10)

        # Row 3: Record Work Checkbox
        force_controls_row3 = Frame(force_gauge_main_frame)
        force_controls_row3.pack(fill=X, padx=5, pady=2)

        # Instantiate ForceGaugeManager
        self.force_gauge_manager = ForceGaugeManager(
            gain_label=self.lbl_gain,
            offset_label=self.lbl_offset,
            force_status_label=self.lbl_force_gauge_status, # This is the small status label in the box
            large_force_readout_label=self.lbl_current_force, # This is the large readout at the top
            output_force_queue=self.force_data_queue_for_logger,
            parent_window=self.sensor_window,
            sensor_window_ref=self # Pass self to ForceGaugeManager
        )
        
        # --- Automated Logging Control Box (GUI Elements) ---
        self.frame_auto_log = ttk.LabelFrame(self.sensor_window, text="Automated Layer Logging Control", padding=(10, 5))
        self.frame_auto_log.pack(side=TOP, fill=X, padx=10, pady=(10,10))

        auto_log_row0 = Frame(self.frame_auto_log)
        auto_log_row0.pack(side=TOP, fill=X, pady=2)

        self.auto_log_enabled_var = BooleanVar(value=False)
        self.cb_auto_log_enabled = Checkbutton(
            auto_log_row0, text="Enable Automated Logging",
            variable=self.auto_log_enabled_var,
            font=control_box_font,
            command=self.on_auto_log_enable_change # Set command
        )
        self.cb_auto_log_enabled.pack(side=LEFT, padx=(0,10))
        
        self.lbl_current_window_start = Label(auto_log_row0, text="Start L:", font=control_box_font)
        self.lbl_current_window_start.pack(side=LEFT, padx=(5,0))
        self.current_window_start_var = StringVar()
        self.t_current_window_start = Entry(auto_log_row0, textvariable=self.current_window_start_var, width=5, font=control_box_font)
        self.t_current_window_start.pack(side=LEFT, padx=(2,5))

        self.lbl_current_window_end = Label(auto_log_row0, text="End L:", font=control_box_font)
        self.lbl_current_window_end.pack(side=LEFT, padx=(5,0))
        self.current_window_end_var = StringVar()
        self.t_current_window_end = Entry(auto_log_row0, textvariable=self.current_window_end_var, width=5, font=control_box_font)
        self.t_current_window_end.pack(side=LEFT, padx=(2,5))

        self.btn_add_window_to_file = Button(
            auto_log_row0, text="Add Window",
            command=self.add_window_to_active_file, # Set command
            font=control_box_font,
            state=DISABLED # Initially disable the button
        )
        self.btn_add_window_to_file.pack(side=LEFT, padx=(10,0))
        
        auto_log_row1 = Frame(self.frame_auto_log)
        auto_log_row1.pack(side=TOP, fill=X, pady=(5,2))

        self.active_logging_windows_filepath_var = StringVar(value="No windows file active.")
        self.lbl_active_logging_windows_file = Label(auto_log_row1, textvariable=self.active_logging_windows_filepath_var, width=70, relief="sunken", anchor=W, font=control_box_font)
        self.lbl_active_logging_windows_file.pack(side=LEFT, fill=X, expand=True)

        # Initialize variables for plotting and recording (these were already in your reverted version)
        self.plot_data_x = []
        self.plot_data_y_position = []
        self.plot_data_y_force = []
        self.is_live_readout_enabled = False
        self.live_readout_auto_started_by_logging = False  # Track if auto-started by automated logging
        self.is_manual_recording_active = False # Specifically for manual button state
        self.plot_start_time = None
        self.last_y_rescale_time = 0

        self.date_specific_log_dir_for_windows_file = None # ADDED: To store the YYYY-MM-DD log path
        self.current_logging_windows_file = None # Ensure this is also initialized, though summary says it was

        self.position_plot_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.position_logger = None # Will be PositionLogger instance

        self._shading = [] # Add this line

        # --- For Persistent Readouts ---
        self.persistent_readout_active = False
        self.persistent_readout_update_interval_ms = 500 # Update every 500ms

        # --- Automated Logging Setup ---
        self.automated_layer_logger = None
        self.is_automated_logger_configured = False # Tracks if configure_run was successful for a specific print
        # self.base_image_directory_for_logging = None # This seems specific to a print run's autologs
        # self.current_logging_windows_file = None # Now set by _setup_default_logging_paths
        # self.current_log_date_str = None # Can be derived from datetime.now() when needed
        # self.date_specific_autolog_dir = None # This was for the old structure, now use self.date_specific_log_dir_for_windows_file
        self.logging_windows_file_overwritten_this_session = False

        try:
            self.automated_layer_logger = LayerLogger(
                status_callback=self.update_main_status,
                sensor_data_window_ref=self 
            )
        except TypeError as te: # Catch if LayerLogger.__init__ signature is wrong
            self.update_main_status(f"CRITICAL ERROR: LayerLogger init failed: {te}. Automated logging will NOT work.", error=True)
            traceback.print_exc()
            self.automated_layer_logger = None
        except ImportError:
            self.update_main_status("CRITICAL ERROR: Could not import LayerLogger. Automated logging will NOT work.", error=True)
            self.automated_layer_logger = None
        except Exception as e:
            self.update_main_status(f"CRITICAL ERROR: Instantiating LayerLogger: {e}. Automated logging will NOT work.", error=True)
            traceback.print_exc()
            self.automated_layer_logger = None

        # --- New Checkbox for Recording Work of Adhesion ---
        # self.record_work_var = BooleanVar(value=False) # MOVED EARLIER
        self.cb_record_work = Checkbutton(
            force_controls_row3, text="Record Work of Adhesion Information", # Changed parent to force_controls_row3
            variable=self.record_work_var, font=control_box_font,
            command=self.on_record_work_checkbox
        )
        self.cb_record_work.pack(side=LEFT, padx=5)

        self.peak_force_logger = None # Initialize to None

        self.sensor_window.protocol("WM_DELETE_WINDOW", self.on_sensor_window_close)

        # Call to establish paths now that all UI elements are defined
        # self._setup_default_logging_paths() # REMOVED: Path setup is now deferred

        # Start persistent readouts when window is created
        self._start_persistent_readouts()

    def configure_automated_layer_logging(self, main_image_dir, print_number, date_str_for_dir, log_directory):
        """
        Configures the AutomatedLayerLogger for a new print run.
        """
        if hasattr(self, 'automated_layer_logger') and self.automated_layer_logger:
            # Construct the full path to logging_windows.csv
            # This assumes logging_windows.csv is located in the date-specific log folder
            logging_windows_filepath = os.path.join(main_image_dir, "Printing_Logs", date_str_for_dir, "logging_windows.csv")

            if not os.path.exists(logging_windows_filepath):
                # Use self.update_main_status instead of self.status_callback
                self.update_main_status(f"Error: logging_windows.csv not found at {logging_windows_filepath}. Automated layer logging may not work as expected.", error=True)
                # Decide if configuration should proceed or fail if the file is critical
                # For now, we'll let configure_run handle the file not found error if it's critical there.

            # Call the LayerLogger's configure_run method
            # Note: 'log_directory' received by this method is passed as 'base_log_directory'
            # to the AutomatedLayerLogger's configure_run method.
            success = self.automated_layer_logger.configure_run(
                print_run_number=print_number,
                base_log_directory=log_directory, # This is the print-specific directory for other logs
                logging_windows_filepath=logging_windows_filepath
            )

            if success:
                # Use self.update_main_status
                self.update_main_status(f"AutomatedLayerLogger configured via SensorDataWindow for Print {print_number}.")
                
                # Create automated PeakForceLogger for this specific print session
                automated_csv_path = os.path.join(log_directory, "automated_work_of_adhesion.csv")
                
                # Create the automated logger with unified corrected calculator
                self.automated_peak_force_logger = PeakForceLogger(
                    output_csv_filepath=automated_csv_path,
                    is_manual_log=False,  # This is automated logging
                    use_corrected_calculator=True  # Use the unified corrected calculator
                )
                
                self.update_main_status(f"Automated work of adhesion logging configured. Output: {automated_csv_path}")
                
                # Start monitoring for layer 1 immediately (will be updated when actual layer processing begins)
                try:
                    self.automated_peak_force_logger.start_monitoring_for_layer(
                        1,  # Start with layer 1
                        z_peel_peak=1.0,  # Default peel start position
                        z_return_pos=3.0  # Default peel end position
                    )
                    self.update_main_status("Automated peak force monitoring started for initial layer.")
                except Exception as e:
                    self.update_main_status(f"Error starting initial automated monitoring: {e}")
                
                # Automatically start live readout if not already enabled (required for data collection)
                if not self.is_live_readout_enabled:
                    self.update_main_status("Auto-starting live readout for automated logging...")
                    try:
                        self.start_live_readout()
                        self.live_readout_auto_started_by_logging = True  # Remember we auto-started it
                        self.update_main_status("Live readout started automatically for automated logging.")
                    except Exception as e:
                        self.update_main_status(f"Error auto-starting live readout: {e}", error=True)
                        self.update_main_status("Automated logging may not collect data without live readout enabled.", error=True)
                
            else:
                # Use self.update_main_status
                self.update_main_status(f"AutomatedLayerLogger configuration failed via SensorDataWindow for Print {print_number}.", error=True)
        else:
            # Use self.update_main_status
            self.update_main_status("AutomatedLayerLogger instance not found in SensorDataWindow. Cannot configure.", error=True)

    def configure_automated_logging(self, enabled_from_main_app=True, base_image_directory=None):
        """
        Configures automated logging for a print run. This method is called by Prince_Segmented.py.
        
        Args:
            enabled_from_main_app (bool): Whether logging is being enabled from main app
            base_image_directory (str): Base directory for print images and logs
            
        Returns:
            bool: True if configuration successful, False otherwise
        """
        try:
            if not enabled_from_main_app:
                # Disabling automated logging - clean up any existing logger
                if hasattr(self, 'automated_peak_force_logger') and self.automated_peak_force_logger:
                    # Stop any ongoing monitoring
                    if hasattr(self.automated_peak_force_logger, 'stop_monitoring_and_log_peak'):
                        self.automated_peak_force_logger.stop_monitoring_and_log_peak()
                    self.automated_peak_force_logger = None
                self.update_main_status("Automated logging disabled for this print run.")
                return True
                
            if not base_image_directory:
                self.update_main_status("Error: No base directory provided for automated logging.", error=True)
                return False
                
            # Check if auto logging is enabled in the UI
            if not hasattr(self, 'auto_log_enabled_var') or not self.auto_log_enabled_var.get():
                self.update_main_status("Auto logging not enabled in sensor panel.", warning=True)
                return False
                
            # Set up automated work of adhesion logging for the print
            self.update_main_status(f"Configuring automated work of adhesion logging for directory: {base_image_directory}")
            
            # Create automated PeakForceLogger for this print run
            # The file should be saved in the specific print session directory, not the date directory
            # This will be set when the actual print starts and we know the print session directory
            
            self.update_main_status("Automated work of adhesion logging prepared for print session.")
            self.update_main_status("Automated logger will use AdhesionMetricsCalculator for enhanced force analysis.")
            
            return True
            
        except Exception as e:
            self.update_main_status(f"Error configuring automated logging: {str(e)}", error=True)
            import traceback
            traceback.print_exc()
            return False

    def update_logger_current_layer(self, layer_number, z_position_mm):
        """
        Updates the automated layer logger with current layer information.
        This method is called by Prince_Segmented.py after each layer.
        
        Args:
            layer_number (int): Current layer number
            z_position_mm (float): Z position in millimeters
        """
        try:
            # Update any internal tracking if needed
            self.update_main_status(f"Processing layer {layer_number} data at Z={z_position_mm:.3f}mm")
            
            # Handle automated work of adhesion logging
            if hasattr(self, 'automated_peak_force_logger') and self.automated_peak_force_logger:
                # Stop monitoring for previous layer and log the peak force data
                self.automated_peak_force_logger.stop_monitoring_and_log_peak()
                
                # Start monitoring for the new layer
                # Note: For peeling operations, you may need to define peel start/end positions
                # For now, using generic positions - you may need to adjust based on your setup
                peel_start_z = z_position_mm + 1.0  # Example: 1mm above current position
                peel_end_z = z_position_mm + 3.0    # Example: 3mm above current position
                
                self.automated_peak_force_logger.start_monitoring_for_layer(
                    layer_number, 
                    z_peel_peak=peel_start_z, 
                    z_return_pos=peel_end_z
                )
                
                # Feed live force data to the logger (if force gauge is active)
                if hasattr(self, 'force_gauge_manager') and self.force_gauge_manager:
                    # The force data should be automatically fed through the data queue
                    # This happens in the live readout system
                    pass
                    
                self.update_main_status(f"Automated work of adhesion monitoring started for layer {layer_number}")
                
            # Handle automated layer logger (for other data)
            if hasattr(self, 'automated_layer_logger') and self.automated_layer_logger:
                # You may want to call specific methods on the layer logger here
                # For example: self.automated_layer_logger.update_current_layer(layer_number, z_position_mm)
                pass
                
            return True
            
        except Exception as e:
            self.update_main_status(f"Error updating logger for layer {layer_number}: {str(e)}", error=True)
            import traceback
            traceback.print_exc()
            return False

    def attempt_logging_path_setup(self):
        """Public method to allow re-triggering of logging path setup."""
        self.update_main_status("Attempting to re-initialize logging paths for SensorDataWindow...")
        self._setup_default_logging_paths()

    def _setup_default_logging_paths(self):
        print("DEBUG: SensorDataWindow._setup_default_logging_paths called.")
        # Ensure necessary imports are at the top of the file:
        # import os
        # import datetime
        # import csv
        # import traceback
        # import tkinter as tk (or from tkinter import DISABLED, NORMAL)

        if not self.prince_main_app_ref or not hasattr(self.prince_main_app_ref, 't1'):
            self.update_main_status("Cannot set up logging paths: Main application reference or its UI element not available.", warning=True)
            self.current_logging_windows_file = None
            self.date_specific_log_dir_for_windows_file = None
            self.active_logging_windows_filepath_var.set("Error: Main app ref missing/invalid.")
            if hasattr(self, 'btn_add_window_to_file'):
                self.btn_add_window_to_file.config(state=tk.DISABLED)
            return False

        main_app_image_dir_val = self.prince_main_app_ref.t1.get()
        print(f"DEBUG: _setup_default_logging_paths: main_app_image_dir_val = '{main_app_image_dir_val}'")

        if not main_app_image_dir_val or not os.path.isdir(main_app_image_dir_val):
            self.update_main_status(
                f"Main image directory ('{main_app_image_dir_val}') not selected or invalid. Logging paths cannot be set.", 
                warning=True
            )
            self.current_logging_windows_file = None
            self.date_specific_log_dir_for_windows_file = None
            self.active_logging_windows_filepath_var.set("Path error: Main image dir not set/invalid.")
            if hasattr(self, 'btn_add_window_to_file'):
                self.btn_add_window_to_file.config(state=tk.DISABLED)
            return False

        try:
            # Create [main_image_dir]/Printing_Logs/
            printing_logs_base_dir = os.path.join(main_app_image_dir_val, "Printing_Logs")
            os.makedirs(printing_logs_base_dir, exist_ok=True)
            print(f"DEBUG: Ensured base directory exists: {printing_logs_base_dir}")

            # Create [main_image_dir]/Printing_Logs/[YYYY-MM-DD]/
            date_str = datetime.datetime.now().strftime('%Y-%m-%d')
            self.date_specific_log_dir_for_windows_file = os.path.join(printing_logs_base_dir, date_str)
            os.makedirs(self.date_specific_log_dir_for_windows_file, exist_ok=True)
            print(f"DEBUG: Ensured date-specific directory exists: {self.date_specific_log_dir_for_windows_file}")

            # Path for logging_windows.csv
            logging_windows_csv_path = os.path.join(self.date_specific_log_dir_for_windows_file, "logging_windows.csv")
            print(f"DEBUG: Target logging_windows.csv path: {logging_windows_csv_path}")

            # Create logging_windows.csv with header if it doesn't exist
            if not os.path.exists(logging_windows_csv_path):
                try:
                    with open(logging_windows_csv_path, 'w', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow(["StartLayer", "EndLayer"])
                    self.update_main_status(f"Created: {os.path.basename(logging_windows_csv_path)} in {os.path.basename(self.date_specific_log_dir_for_windows_file)}")
                except IOError as e:
                    self.update_main_status(f"ERROR creating {os.path.basename(logging_windows_csv_path)}: {e}", error=True)
                    self.current_logging_windows_file = None
                    self.date_specific_log_dir_for_windows_file = None # Invalidate path if crucial file fails
                    self.active_logging_windows_filepath_var.set("Error creating windows file.")
                    if hasattr(self, 'btn_add_window_to_file'):
                        self.btn_add_window_to_file.config(state=tk.DISABLED)
                    return False
            
            # Ensure logging_windows_csv_path is defined globally for later use
            self.logging_windows_csv_path = logging_windows_csv_path

            self.current_logging_windows_file = logging_windows_csv_path
            self.active_logging_windows_filepath_var.set(self.current_logging_windows_file)
            self.update_main_status(f"Logging windows file: {self.current_logging_windows_file}")
            
            if hasattr(self, 'btn_add_window_to_file') and hasattr(self, 'auto_log_enabled_var'):
                if self.auto_log_enabled_var.get(): # Only enable "Add Window" if auto-log is also enabled
                    self.btn_add_window_to_file.config(state=tk.NORMAL)
                else:
                    self.btn_add_window_to_file.config(state=tk.DISABLED)
            
            return True

        except Exception as e:
            self.update_main_status(f"CRITICAL ERROR setting up logging paths: {e}", error=True)
            detailed_error = traceback.format_exc()
            print(f"Traceback for logging path setup error:\n{detailed_error}")
            
            self.current_logging_windows_file = None
            self.date_specific_log_dir_for_windows_file = None
            self.active_logging_windows_filepath_var.set("CRITICAL: Error setting up paths.")
            if hasattr(self, 'btn_add_window_to_file'):
                self.btn_add_window_to_file.config(state=tk.DISABLED)
            return False

    def on_sensor_window_close(self):
        """Handles the event when the sensor window is closed."""
        self.update_main_status("Sensor data window closed by user.")
        if hasattr(self, 'is_live_readout_enabled') and self.is_live_readout_enabled:
            self.stop_live_readout()
        
        if hasattr(self, 'force_gauge_manager') and self.force_gauge_manager:
            self.force_gauge_manager.stop_force_reading_thread()

        if hasattr(self, 'persistent_readout_active') and self.persistent_readout_active:
            self._stop_persistent_readouts()

        # --- Clean up PeakForceLogger instances ---
        if hasattr(self, 'peak_force_logger') and self.peak_force_logger:
            print("SensorDataWindow: Closing manual PeakForceLogger.")
            self.peak_force_logger.close()

        if hasattr(self, 'automated_peak_force_logger') and self.automated_peak_force_logger:
            print("SensorDataWindow: Closing automated PeakForceLogger.")
            self.automated_peak_force_logger.close()

        # Clean up AutomatedLayerLogger if it exists and has a shutdown method
        if hasattr(self, 'automated_layer_logger') and self.automated_layer_logger:
            if hasattr(self.automated_layer_logger, 'stop_all_logging_sessions'):
                print("SensorDataWindow: Stopping all logging sessions for AutomatedLayerLogger.")
                self.automated_layer_logger.stop_all_logging_sessions()  # Remove invalid save_data parameter
            elif hasattr(self.automated_layer_logger, 'close'): # Generic fallback
                 print("SensorDataWindow: Closing AutomatedLayerLogger.")
                 self.automated_layer_logger.close()


        if hasattr(self, 'sensor_window') and self.sensor_window.winfo_exists():
            self.sensor_window.destroy()
            
        if hasattr(self, 'prince_main_app_ref') and self.prince_main_app_ref:
            self.prince_main_app_ref.sensor_data_window_instance = None
            if hasattr(self.prince_main_app_ref, 'update_auto_home_button_state'):
                self.prince_main_app_ref.update_auto_home_button_state()

    def _start_persistent_readouts(self):
        """Starts a loop to update non-plot readouts like current position/force labels."""
        if not hasattr(self, 'persistent_readout_active') or not self.persistent_readout_active:
            self.persistent_readout_active = True
            self._update_persistent_readouts() # Start the update loop

    def _update_persistent_readouts(self):
        """Periodically updates the non-plot display elements (current position, force)."""
        if not self.persistent_readout_active or not self.sensor_window.winfo_exists():
            return # Stop if flag is false or window is destroyed

        try:
            # Update position readout
            if hasattr(self, 'zaber_axis') and self.zaber_axis:
                current_pos_mm = self.zaber_axis.get_position(Units.LENGTH_MILLIMETRES)
                if hasattr(self, 'lbl_current_position'):
                    self.lbl_current_position.config(text=f"Position: {current_pos_mm:.4f} mm")
            
            # Force readout is updated by ForceGaugeManager's own loop via lbl_current_force

        except Exception as e:
            print(f"Error in _update_persistent_readouts: {e}")
            # Avoid stopping the loop for minor errors, but log them.

        if self.persistent_readout_active and self.sensor_window.winfo_exists():
            self.sensor_window.after(self.persistent_readout_update_interval_ms, self._update_persistent_readouts)

    def _stop_persistent_readouts(self):
        """Stops the loop that updates non-plot readouts."""
        self.persistent_readout_active = False
        self.update_main_status("Persistent readouts stopped.")


    def toggle_recording(self):
        """Toggles the manual recording state."""
        if self.is_manual_recording_active:
            self.stop_recording() # Will handle is_manual_recording_active = False
        else:
            self.start_recording() # Will handle is_manual_recording_active = True

    def start_recording(self, filepath_override=None, called_by_auto_logger=False):
        """Starts data recording to a CSV file.
        Can be called manually or by AutomatedLayerLogger.
        """
        if not self.is_live_readout_enabled and not called_by_auto_logger: # Auto-logger might not require live readout to be on in UI
            messagebox.showwarning("Warning", "Live readout is not active. Please start live readout first to record data.", parent=self.sensor_window)
            return False

        file_path = filepath_override if filepath_override else self.file_path_entry.get()
        if not file_path:
            messagebox.showerror("Error", "File path cannot be empty.", parent=self.sensor_window)
            return False
        
        # Validate or create directory if it doesn't exist
        try:
            # Ensure the directory for the file_path exists
            log_dir = os.path.dirname(file_path)
            if log_dir: # Check if dirname returned something (it's empty if file_path is just a filename)
                 os.makedirs(log_dir, exist_ok=True)
        except OSError as e:
            messagebox.showerror("Error", f"Could not create directory for log file: {e}", parent=self.sensor_window)
            return False

        if self.position_logger:
            self.position_logger.log_file_name = file_path # MODIFIED
            self.position_logger.csv_logging_enabled = True # MODIFIED
            
            if not called_by_auto_logger: # Only manage manual recording state if not called by auto logger
                self.is_manual_recording_active = True
                self.b_start_recording.config(text="Stop Recording")
            
            self.update_main_status(f"Recording started to: {file_path}{' (Automated)' if called_by_auto_logger else ' (Manual)'}")
            return True # Indicate success
        else:
            messagebox.showerror("Error", "PositionLogger not initialized. Cannot start recording.", parent=self.sensor_window)
            return False # Indicate failure


    def stop_recording(self, called_by_auto_logger=False):
        """Stops data recording.
        Can be called manually or by AutomatedLayerLogger.
        """
        if self.position_logger:
            self.position_logger.csv_logging_enabled = False # MODIFIED # This also closes the file in PositionLogger
        
        if not called_by_auto_logger: # Only manage manual recording state if not called by auto logger
            self.is_manual_recording_active = False
            if hasattr(self, 'b_start_recording'): # Ensure button exists
                self.b_start_recording.config(text="Start Recording")
        
        self.update_main_status(f"Recording stopped{' (Automated)' if called_by_auto_logger else ' (Manual)'}.")
        
        # Notify AutomatedLayerLogger if stop was manual during its session
        if not called_by_auto_logger and hasattr(self, 'automated_layer_logger') and self.automated_layer_logger and \
           hasattr(self.automated_layer_logger, 'is_currently_logging') and self.automated_layer_logger.is_currently_logging() and \
           hasattr(self.automated_layer_logger, 'notify_external_stop'):
            self.automated_layer_logger.notify_external_stop()


    def on_auto_log_enable_change(self):
        """Handles changes to the 'Enable Automated Logging' checkbox."""
        is_enabled_by_checkbox = self.auto_log_enabled_var.get()

        if is_enabled_by_checkbox:
            # Attempt to set up paths first
            paths_setup_successfully = self._setup_default_logging_paths() # This will also update active_logging_windows_filepath_var

            if paths_setup_successfully and self.current_logging_windows_file:
                self.update_main_status(f"Automated logging UI enabled. Define windows in: {os.path.basename(self.current_logging_windows_file)}")
                if hasattr(self, 'btn_add_window_to_file'):
                    self.btn_add_window_to_file.config(state=tk.NORMAL)
            else:
                # Path setup failed or file not resolved. _setup_default_logging_paths already sent a detailed status.
                # self.active_logging_windows_filepath_var is also updated by _setup_default_logging_paths.
                self.update_main_status("Automated logging UI cannot be fully enabled: logging_windows.csv path not resolved. Check main image directory and ensure 'Printing_Logs/YYYY-MM-DD/' subdirectory exists.", warning=True)
                if hasattr(self, 'btn_add_window_to_file'):
                    self.btn_add_window_to_file.config(state=tk.DISABLED)
                # Optionally, uncheck the box if it cannot be actioned, though user preferred not to.
                # self.auto_log_enabled_var.set(False) 
        else:
            self.update_main_status("Automated logging UI disabled.")
            if hasattr(self, 'btn_add_window_to_file'):
                self.btn_add_window_to_file.config(state=tk.DISABLED)
            self.active_logging_windows_filepath_var.set("Automated logging disabled.") # Clear/update path display
            
        # This print is for debugging, can be removed later
        if hasattr(self, 'btn_add_window_to_file'):
            print(f"Auto-log checkbox: {is_enabled_by_checkbox}, current_logging_windows_file: {self.current_logging_windows_file}, Add Window button state: {self.btn_add_window_to_file['state']}")
        else:
            print(f"Auto-log checkbox: {is_enabled_by_checkbox}, current_logging_windows_file: {self.current_logging_windows_file}, Add Window button not found")

    def add_window_to_active_file(self):
        """Adds the current start/end layer window to the logging_windows.csv file."""
        start_layer_str = self.current_window_start_var.get()
        end_layer_str = self.current_window_end_var.get()

        if not self.auto_log_enabled_var.get():
            messagebox.showwarning("Logging Disabled", "Automated logging is not enabled. Cannot add window.", parent=self.sensor_window)
            return

        # Corrected condition: Check if auto_log is enabled and the windows file path is valid and its directory exists.
        if not self.current_logging_windows_file or \
           not os.path.exists(self.current_logging_windows_file) or \
           not os.path.isdir(os.path.dirname(self.current_logging_windows_file)):
            messagebox.showerror("Error", "Automated logging windows file path is not properly set or its directory does not exist. Please ensure 'Enable Automated Logging' is checked and paths are correctly initialized (main image directory must be set).", parent=self.sensor_window)
            # Attempt to re-initialize paths if the "Enable" checkbox is ticked but file/dir is missing.
            if self.auto_log_enabled_var.get():
                self.update_main_status("Attempting to re-initialize logging paths for adding window...", warning=True)
                self._setup_default_logging_paths() # This might resolve the issue if it was a timing problem.
                # Re-check after attempt
                if not self.current_logging_windows_file or \
                   not os.path.exists(self.current_logging_windows_file) or \
                   not os.path.isdir(os.path.dirname(self.current_logging_windows_file)):
                    self.update_main_status("Re-initialization of paths failed or did not resolve the issue for adding window.", error=True)
                    return # Still can't proceed
                else:
                    self.update_main_status("Logging paths re-initialized successfully. You can try adding the window again.", success=True)
            else: # If auto_log_enabled_var is somehow false here, also return.
                return

        try:
            start_layer = int(start_layer_str)
            end_layer = int(end_layer_str)
            if start_layer <= 0 or end_layer <= 0 or start_layer > end_layer: # Corrected condition: start_layer > end_layer
                messagebox.showerror("Invalid Input", "Layer numbers must be positive and start layer must not exceed end layer.", parent=self.sensor_window)
                return
        except ValueError:
            messagebox.showerror("Invalid Input", "Layer numbers must be integers.", parent=self.sensor_window)
            return

        try:
            # The directory for current_logging_windows_file should have been created by _setup_default_logging_paths
            # We already checked its existence above.

            file_exists_and_not_empty = os.path.isfile(self.current_logging_windows_file) and os.path.getsize(self.current_logging_windows_file) > 0
            
            mode = 'a' if file_exists_and_not_empty else 'w' # Append if exists and has content, else write (will create header) 
            
            with open(self.current_logging_windows_file, mode, newline='') as f:
                writer = csv.writer(f)
                if mode == 'w' or not file_exists_and_not_empty: # Write header if new file or empty
                    writer.writerow(["StartLayer", "EndLayer"])
                writer.writerow([start_layer, end_layer])
            
            self.update_main_status(f"Window [{start_layer}-{end_layer}] added to {os.path.basename(self.current_logging_windows_file)}.")
            self.current_window_start_var.set("")
            self.current_window_end_var.set("")

        except Exception as e:
            self.update_main_status(f"Error adding window to file: {e}", error=True)
            traceback.print_exc()
            messagebox.showerror("File Error", f"Could not write to {os.path.basename(self.current_logging_windows_file)}: {e}", parent=self.sensor_window)
        print(f"Add window: Start L: {start_layer_str}, End L: {self.current_logging_windows_file}")

    def clear_plot_data(self):
        self.plot_data_x.clear()
        self.plot_data_y_position.clear()
        self.plot_data_y_force.clear()
        
        # Also clear the force data queue to prevent stale data
        while not self.force_data_queue_for_logger.empty():
            try:
                self.force_data_queue_for_logger.get_nowait()
            except queue.Empty:
                break

        # Only reset plot_start_time if not actively plotting,
        # otherwise, keep the current time reference.
        if not self.is_live_readout_enabled:
            self.plot_start_time = None

        self.line_position.set_data([], [])
        self.line_force.set_data([], [])

        # Reset axes limits
        self.ax.relim()
        self.ax.autoscale_view(True, True, True) # Autoscale x and y
        self.ax2.relim()
        self.ax2.autoscale_view(True, True, True) # Autoscale x and y for twin axis

        self.canvas.draw()
        self.update_main_status("Plot data cleared.") # Changed from print to update_main_status

    def update_calibration_status_for_main_app(self, status):
        """Called by ForceGaugeManager to update calibration status."""
        self.force_gauge_is_calibrated = status
        if self.prince_main_app_ref:
            self.prince_main_app_ref.update_auto_home_button_state()

    def is_force_gauge_calibrated_internally(self):
        """Checks if the force gauge in this window is calibrated."""
        return self.force_gauge_is_calibrated

    def toggle_live_readout(self):
        if self.is_live_readout_enabled:
            self.stop_live_readout()
        else:
            self.start_live_readout()

    def start_live_readout(self):
        try:
            self.last_y_rescale_time = time.time() # Set/reset last rescale time

            self.plot_data_x.clear()
            self.plot_data_y_position.clear()
            self.plot_data_y_force.clear()
            self.plot_start_time = time.time() # Set/reset plot start time

            sampling_rate_str = self.sampling_rate_entry.get()
            if not sampling_rate_str.isdigit() or int(sampling_rate_str) <= 0:
                messagebox.showerror("Error", "Sampling rate must be a positive integer.", parent=self.sensor_window)
                return
            sampling_rate = int(sampling_rate_str)

            # Synchronize force gauge data interval with sampling rate
            if self.force_gauge_manager:
                phidget_interval = sampling_rate  # Use same interval as position logging
                if self.force_gauge_manager.set_data_interval(phidget_interval):
                    print(f"Force gauge data interval synchronized to {phidget_interval}ms")
                else:
                    print("Warning: Could not synchronize force gauge data interval")

            self.stop_event.clear()
            self.position_logger = PositionLogger(
                self.zaber_axis,
                self.stop_event,
                position_plot_queue=self.position_plot_queue,
                force_data_queue_ref=self.force_data_queue_for_logger,
                log_interval_ms=sampling_rate,
                csv_logging_initially_enabled=False # Changed from self.is_recording
            )
            # The following block is removed as start_recording now handles 
            # setting the log file name and enabling CSV logging on the PositionLogger instance.
            # # If recording is already enabled, ensure the logger gets the correct file path
            # if self.is_recording: 
            #     self.position_logger.log_file_name = self.file_path_entry.get()

            self.position_logger.start()
            self.is_live_readout_enabled = True
            self.b_live_readout.config(text="Stop Live Readout")
            self.update_plot() # Start the plot update loop
        except ValueError: # Should be caught by isdigit check now
            messagebox.showerror("Error", "Invalid sampling rate. Please enter a number.", parent=self.sensor_window)
        except Exception as e:
            print(f"Error starting live readout: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"Could not start live readout: {e}", parent=self.sensor_window)
            self.is_live_readout_enabled = False # Ensure state is correct on failure
            self.b_live_readout.config(text="Start Live Readout")


    def stop_live_readout(self):
        self.is_live_readout_enabled = False # Set this first
        if self.position_logger and self.position_logger.is_alive():
            self.stop_event.set()
            self.position_logger.join(timeout=2.0) # Increased timeout slightly
            if self.position_logger.is_alive():
                print("Warning: PositionLogger thread did not terminate in time.")
        self.b_live_readout.config(text="Start Live Readout")
        # Clear the plot queue to prevent old data from appearing if restarted
        while not self.position_plot_queue.empty():
            try:
                self.position_plot_queue.get_nowait()
            except queue.Empty:
                break
        print("Live readout stopped.")

    def update_plot(self):
        try:
            new_data_processed = False
            # Absolute timestamps from the queue
            current_queue_timestamps = []
            current_queue_positions = []
            current_queue_forces = []

            while not self.position_plot_queue.empty():
                time_stamp, position, force = self.position_plot_queue.get_nowait()
                new_data_processed = True

                # Always call pfl_add_data_point. It will internally check which loggers are active.
                self.pfl_add_data_point(time_stamp, position, force)

                if self.plot_start_time is None:
                    self.plot_start_time = time_stamp # Initialize with the first data point's timestamp

                # For the main plot, x-axis is elapsed time from self.plot_start_time
                elapsed_time = time_stamp - self.plot_start_time
                self.plot_data_x.append(elapsed_time)
                self.plot_data_y_position.append(position if position is not None else float('nan'))
                self.plot_data_y_force.append(force if force is not None else float('nan'))

            if new_data_processed:
                # Trim data lists if they exceed MAX_PLOT_POINTS
                if len(self.plot_data_x) > self.MAX_PLOT_POINTS:
                    self.plot_data_x = self.plot_data_x[-self.MAX_PLOT_POINTS:]
                if len(self.plot_data_y_position) > self.MAX_PLOT_POINTS:
                    self.plot_data_y_position = self.plot_data_y_position[-self.MAX_PLOT_POINTS:]
                if len(self.plot_data_y_force) > self.MAX_PLOT_POINTS:
                    self.plot_data_y_force = self.plot_data_y_force[-self.MAX_PLOT_POINTS:]

                min_len = min(len(self.plot_data_x), len(self.plot_data_y_position), len(self.plot_data_y_force)) 
                current_plot_x = self.plot_data_x[-min_len:] if min_len > 0 else []
                current_plot_y_pos = self.plot_data_y_position[-min_len:] if min_len > 0 else []
                current_plot_y_force = self.plot_data_y_force[-min_len:] if min_len > 0 else []

                self.line_position.set_data(current_plot_x, current_plot_y_pos)
                self.line_force.set_data(current_plot_x, current_plot_y_force)

                self.ax.relim()
                self.ax.autoscale_view(True, True, False) 
                self.ax2.relim() # Relim for the force axis as well

                current_time_for_rescale = time.time()
                if current_time_for_rescale - self.last_y_rescale_time >= 1.0: 
                    self.ax.autoscale_view(scalex=False, scaley=True) 
                    self.ax2.autoscale_view(scalex=False, scaley=True) # Autoscale Y for force axis too
                    self.last_y_rescale_time = current_time_for_rescale # Reset timer
                
                # Remove previous shading
                for coll in self._shading:
                    coll.remove() # Correctly remove the collection
                self._shading.clear()

                self.canvas.draw_idle() # Use draw_idle for better performance

        except queue.Empty:
            pass # It's normal for the queue to be empty sometimes
        except Exception as e:
            print(f"Error updating plot: {e}") # Log error
            traceback.print_exc() # Print traceback for debugging
            # Optionally, update a status bar or show a non-modal error
        finally:
            if self.is_live_readout_enabled and self.sensor_window.winfo_exists(): # Check if window still exists
                self.sensor_window.after(max(50, int(self.sampling_rate_entry.get()) // 2), self.update_plot) # Dynamic update rate, min 50ms for GUI
    
    def on_record_work_checkbox(self):
        """Handles the 'Record Work of Adhesion' checkbox state change."""
        # Ensure logging paths are set up before attempting to use them
        if not self._setup_default_logging_paths():
            self.update_main_status("Error: Could not set up default logging paths for manual work recording. Check main image directory.", error=True)
            self.record_work_var.set(False) # Uncheck the box if paths can't be set
            return

        if self.record_work_var.get():
            if not self.date_specific_log_dir_for_windows_file:
                self.update_main_status("Error: Date-specific log directory not set. Cannot start manual work recording.", error=True)
                self.record_work_var.set(False)
                return

            # Determine a unique filename for the manual Work of Adhesion log
            base_filename = "Work of Adhesion.csv"
            output_csv_filepath = os.path.join(self.date_specific_log_dir_for_windows_file, base_filename)
            counter = 1
            while os.path.exists(output_csv_filepath):
                base_filename = f"Work of Adhesion ({counter}).csv"
                output_csv_filepath = os.path.join(self.date_specific_log_dir_for_windows_file, base_filename)
                counter += 1

            try:
                # Instantiate PeakForceLogger for manual logging
                self.peak_force_logger = PeakForceLogger(
                    output_csv_filepath=output_csv_filepath,
                    is_manual_log=True # Explicitly set for manual logging
                )
                # For manual logging, we now explicitly start monitoring.
                # This call is CRUCIAL to reset the data buffers and prevent memory leaks.
                self.peak_force_logger.start_monitoring_for_layer(layer_number=0)

                self.update_main_status(f"Manual Work of Adhesion logging enabled. Data will be saved to: {output_csv_filepath}")
                print(f"DEBUG: Manual PeakForceLogger initialized and started. Output to: {output_csv_filepath}")

                # If live readout is not active, prompt user or start it?
                if not self.is_live_readout_enabled:
                    messagebox.showinfo("Info", "Work of Adhesion recording is enabled, but live readout is not active. Please start live readout to collect data.", parent=self.sensor_window)

            except Exception as e:
                self.update_main_status(f"Error initializing PeakForceLogger for manual recording: {e}", error=True)
                traceback.print_exc()
                self.record_work_var.set(False) # Uncheck if initialization fails
                self.peak_force_logger = None
        else:
            # Checkbox is unchecked - stop monitoring and log data if PFL instance exists
            if self.peak_force_logger:
                try:
                    # For manual logging, stop monitoring and log the data
                    # The method no longer requires current_layer parameter
                    self.peak_force_logger.stop_monitoring_and_log_peak()
                    self.update_main_status(f"Manual Work of Adhesion data saved to: {self.peak_force_logger.output_csv_filepath}")
                    print(f"DEBUG: Manual PeakForceLogger stopped and logged. File: {self.peak_force_logger.output_csv_filepath}")
                except Exception as e:
                    self.update_main_status(f"Error saving manual Work of Adhesion data: {e}", error=True)
                    traceback.print_exc()
                finally:
                    self.peak_force_logger = None # Clear the instance
            else:
                self.update_main_status("Manual Work of Adhesion logging disabled.")
                print("DEBUG: Record Work checkbox unchecked, no PFL instance to stop.")

    def pfl_add_data_point(self, timestamp, position, force):
        """Adds a single data point to the PeakForceLogger(s) if they're active."""
        # Feed data to manual logger if enabled
        if self.record_work_var.get() and self.peak_force_logger:
            try:
                self.peak_force_logger.add_data_point(timestamp, position, force)
            except Exception as e:
                # This could generate many messages, consider logging to console or a file instead of status bar
                # print(f"Error adding data point to manual PFL: {e}")
                pass # Avoid flooding status bar
                
        # Feed data to automated logger if active
        if hasattr(self, 'automated_peak_force_logger') and self.automated_peak_force_logger:
            try:
                # Add debug info to verify data flow
                if hasattr(self.automated_peak_force_logger, '_monitoring') and self.automated_peak_force_logger._monitoring:
                    self.automated_peak_force_logger.add_data_point(timestamp, position, force)
                    # Uncomment for debugging data flow:
                    # print(f"DEBUG: Fed data to automated PFL: t={timestamp:.3f}, pos={position:.3f}, force={force:.4f}")
                elif hasattr(self.automated_peak_force_logger, '_monitoring'):
                    # Uncomment for debugging monitoring state:
                    # print(f"DEBUG: Automated PFL not monitoring, skipping data point")
                    pass
            except Exception as e:
                print(f"Error adding data point to automated PFL: {e}")
                import traceback
                traceback.print_exc()

    def set_peak_force_logger_for_print_run(self, pfl_instance):
        """
        Sets the PeakForceLogger instance to be used for print run related logging and plot shading.
        This is typically called by the main application (Prince_Segmented).
        """
        self.peak_force_logger = pfl_instance
        if pfl_instance:
            self.update_main_status("PeakForceLogger for print run has been set in SensorDataWindow.")
            # Ensure that if a print-run PFL is set, the manual record checkbox reflects a non-active state
            # for its own PFL instance, or that its state is handled appropriately.
            # For now, simply setting the instance. The checkbox will create its own if toggled.
        else:
            self.update_main_status("PeakForceLogger for print run has been cleared from SensorDataWindow.")
            # If the print-run PFL is cleared, and the user had the manual checkbox ticked,
            # they would need to toggle it again to re-create the manual PFL.
            # This behavior is acceptable for now.

    def update_auto_logger_current_layer(self, layer_number, z_position_mm):
        """Called by Prince_Segmented to update the AutomatedLayerLogger with the current layer and Z pos."""
        if self.automated_layer_logger and self.auto_log_enabled_var.get():
            try:
                # Corrected method call to match AutomatedLayerLogger.py
                self.automated_layer_logger.update_current_layer(layer_number, z_position_mm)
                # self.update_main_status(f"AutoLogger: L{layer_number} data processed.") # Optional: can be verbose
            except Exception as e:
                # Corrected status update call to use the main app's status callback
                self.update_main_status(f"Error in AutoLogger processing for L{layer_number}: {e}")
                import traceback
                traceback.print_exc() # It's good to have the traceback for debugging
                
        # Handle automated peak force logger for work of adhesion data
        if hasattr(self, 'automated_peak_force_logger') and self.automated_peak_force_logger:
            try:
                # Stop monitoring for previous layer and log the peak force data (if any)
                if layer_number > 1:  # Don't try to stop for the first layer
                    self.automated_peak_force_logger.stop_monitoring_and_log_peak()
                    self.update_main_status(f"AutoPFL: Layer {layer_number-1} force data saved.")
                
                # Start monitoring for the new layer
                # Note: For peeling operations, you may need to define peel start/end positions
                # For now, using generic positions - you may need to adjust based on your setup
                peel_start_z = z_position_mm + 1.0  # Example: 1mm above current position
                peel_end_z = z_position_mm + 3.0    # Example: 3mm above current position
                
                self.automated_peak_force_logger.start_monitoring_for_layer(
                    layer_number, 
                    z_peel_peak=peel_start_z, 
                    z_return_pos=peel_end_z
                )
                
                self.update_main_status(f"AutoPFL: Started monitoring for layer {layer_number}")
                
            except Exception as e:
                self.update_main_status(f"Error in AutoPFL processing for L{layer_number}: {e}")
                import traceback
                traceback.print_exc()

    def stop_and_save_automated_logs(self):
        """Called when print finishes to save final automated logging data."""
        try:
            # Stop automated layer logger
            if hasattr(self, 'automated_layer_logger') and self.automated_layer_logger:
                if hasattr(self.automated_layer_logger, 'stop_all_logging_sessions'):
                    self.automated_layer_logger.stop_all_logging_sessions()
                    self.update_main_status("Automated layer logging stopped and saved.")
                elif hasattr(self.automated_layer_logger, 'close'):
                    self.automated_layer_logger.close()
                    self.update_main_status("Automated layer logging closed.")
            
            # Stop and save final automated peak force logger data
            if hasattr(self, 'automated_peak_force_logger') and self.automated_peak_force_logger:
                final_save_result = self.automated_peak_force_logger.stop_monitoring_and_log_peak()
                if final_save_result:
                    self.update_main_status("Final automated peak force data saved.")
                else:
                    self.update_main_status("No final automated peak force data to save.")
            
            # If we auto-started live readout for this logging session, stop it
            if hasattr(self, 'live_readout_auto_started_by_logging') and self.live_readout_auto_started_by_logging:
                self.update_main_status("Stopping auto-started live readout (automated logging finished)...")
                try:
                    self.stop_live_readout()
                    self.live_readout_auto_started_by_logging = False
                    self.update_main_status("Auto-started live readout stopped.")
                except Exception as e:
                    self.update_main_status(f"Error stopping auto-started live readout: {e}", error=True)
                    
        except Exception as e:
            self.update_main_status(f"Error stopping automated logs: {e}")
            import traceback
            traceback.print_exc()

    def tare_force_gauge(self):
        """Tare the force gauge by setting the current reading as the new zero point."""
        try:
            # Check if force gauge is available and calibrated
            if not self.force_gauge_manager or not self.force_gauge_manager.is_calibrated():
                messagebox.showerror("Error", "Force gauge must be calibrated before taring.", parent=self.sensor_window)
                return
            
            # Check if force gauge is connected
            if not self.force_gauge_manager.voltage_ratio_input or not self.force_gauge_manager.voltage_ratio_input.getAttached():
                messagebox.showerror("Error", "Force gauge is not connected.", parent=self.sensor_window)
                return
                
            # Get current voltage ratio and set it as the new offset
            current_voltage_ratio = self.force_gauge_manager.voltage_ratio_input.getVoltageRatio()
            
            # Update the offset
            self.force_gauge_manager.OFFSET = current_voltage_ratio
            
            # Update the offset display
            if hasattr(self, 'lbl_offset'):
                self.lbl_offset.config(text=f"Offset: {self.force_gauge_manager.OFFSET:.8f}")
            
            messagebox.showinfo("Tare Complete", f"Force gauge tared successfully.\nNew offset: {self.force_gauge_manager.OFFSET:.8f}", parent=self.sensor_window)
            print(f"Force gauge tared - New offset: {self.force_gauge_manager.OFFSET:.8f}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to tare force gauge: {e}", parent=self.sensor_window)
            print(f"Error during tare operation: {e}")
            traceback.print_exc()

    def save_force_gauge_calibration(self):
        """Save the current force gauge calibration values to a file."""
        try:
            if not self.force_gauge_manager or not self.force_gauge_manager.is_calibrated():
                messagebox.showerror("Error", "Force gauge must be calibrated before saving.", parent=self.sensor_window)
                return
            
            # Create filename with timestamp
            import os
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"force_gauge_calibration_{timestamp}.txt"
            
            # Save to current working directory
            current_dir = os.getcwd()
            file_path = os.path.join(current_dir, filename)
            
            with open(file_path, 'w') as f:
                f.write("# Force Gauge Calibration Data\n")
                f.write(f"# Saved on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"GAIN={self.force_gauge_manager.GAIN}\n")
                f.write(f"OFFSET={self.force_gauge_manager.OFFSET}\n")
            
            messagebox.showinfo("Calibration Saved", f"Calibration saved to:\n{file_path}", parent=self.sensor_window)
            print(f"Calibration saved to: {file_path}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save calibration: {e}", parent=self.sensor_window)
            print(f"Error saving calibration: {e}")
