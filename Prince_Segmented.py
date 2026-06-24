from tkinter import *
from tkinter.ttk import *
import tkinter as tk
import cv2
import numpy as np
import time
import screeninfo
import sys
import os
import winsound
import usb.core
import json
import json

# Add support_modules to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'support_modules'))

import pycrafter9000
import libs
import timeit
import threading # <--- Add this line
from zaber_motion import Library
from zaber_motion.ascii import Connection
from zaber_motion import Units
from zaber_motion.exceptions import MovementFailedException
import csv
import os
import shutil
import datetime
import queue
import traceback
from tkinter import messagebox
from SensorDataWindow import SensorDataWindow
from AutoHomeRoutine import AutoHomer
from support_modules.ExperimentalConditionsWindow import ExperimentalConditionsWindow
from support_modules.ImageModificationWindow import ImageModificationWindow
from support_modules.SandwichRoutines import SandwichRoutineManager
from support_modules.SessionManager import SessionManager
from support_modules.motion_controller import MotionController
from support_modules.PrintSessionUtils import ensure_print_session, get_today_str


class MyWindow:
    def __init__(self, win):
        instruction = '''Check list:
1) Ensure DLP is on, not on standby, and on "pattern on the fly". Close the Lightcrafter GUI.
2) Close the Zaber GUI
3) Do not open any windows on the second screen.'''
        credit = '''
Professor Cheng Sun
Boyuan Sun, boyuansun2026@u.northwestern.edu
Evan Jones, evanjones2026@u.northwestern.edu
'''
        self.reference = 0

        # Initialize attributes for data loaded from instruction file
        self.image_list = []
        self.exposure_time = []  # This will store exposure_time_list
        self.thickness = []      # This will store thickness_list
        self.step_speed_list = []
        self.overstep_distance_list = []
        self.step_type_list = []  # Corresponds to 'Acceleration' from the file
        self.pause_list = []
        self.intensity_list = []
        self.active_instruction_file_path = None  # Track instruction file for copying
        
        # Initialize session manager and logs
        self.session_log_file = None
        self.detailed_log_file = None
        self.session_manager = SessionManager(self)
        self.session_manager.init_session_log()
        
        # Logging verbosity levels
        self.LOG_MINIMAL = 0   # Only critical errors and major events
        self.LOG_NORMAL = 1    # Standard operation messages (default for terminal)
        self.LOG_DETAILED = 2  # Diagnostic info (detailed log only)
        self.LOG_DEBUG = 3     # Everything including DEBUG statements
        self.terminal_verbosity = self.LOG_NORMAL  # What shows in terminal
        self.file_verbosity = self.LOG_DEBUG       # What goes to detailed log

        # Progress section header
        self.lbl_progress_header = Label(win, text='Progress', font='Helvetica 12 bold')
        self.lbl_progress_header.place(x=50, y=285)
        
        # Progress bar - 20% taller (height ~24px instead of default ~20px)
        self.p1 = Progressbar(win, orient=HORIZONTAL, length=550, mode='determinate')
        # Create style for taller progress bar
        style = Style()
        style.configure('Tall.Horizontal.TProgressbar', thickness=24)
        self.p1.configure(style='Tall.Horizontal.TProgressbar')
        self.p1.place(x=50, y=310) # Below "Progress" header

        # Labels at top right of progress bar
        self.current_layer_num_var = StringVar()
        self.current_layer_num_var.set("Layer: 0/0")
        self.lbl_current_layer = Label(win, textvariable=self.current_layer_num_var, 
                                         font='Helvetica 9') 
        self.lbl_current_layer.place(x=400, y=287) # Top right of progress bar
        
        # Estimate time label at top right of progress bar
        self.lbl15_var = StringVar()
        self.lbl15_var.set("Est: ∞ min")
        self.lbl15_inside = Label(win, textvariable=self.lbl15_var, 
                                     font='Helvetica 9')
        self.lbl15_inside.place(x=500, y=287) # Top right of progress bar, next to layer count

        self.win = win
        self.flag = False
        self.flag2 = False
        self.offset = -20
        self.pause_flag = False # Ensure pause_flag is initialized

        # --- Define status_message_var and related label (t8) EARLY ---
        self.status_message_var = StringVar() 
        self.status_message_var.set("System Initializing...") 

        self.b_open_sensor_window = Button(win, text="Open Sensor Panel", command=self.open_sensor_panel)
        self.b_open_sensor_window.place(x=800, y=60) # Above Directory of Images (y=150)
        
        self.b_exp_conditions = Button(win, text="Exp. Conditions", command=self.open_exp_conditions_window)
        self.b_exp_conditions.place(x=935, y=60) # Next to sensor panel button

        self.b_image_modification = Button(win, text="Image Modification", command=self.open_image_modification_window)
        self.b_image_modification.place(x=1070, y=60) # Next to Exp. Conditions
        
        self.b_reload_script = Button(win, text="Reload Script", command=self.reload_script_modules)
        self.b_reload_script.place(x=800, y=95) # Below sensor panel button
        
        self.b_disconnect_dlp = Button(win, text="Disconnect DLP", command=self.disconnect_dlp)
        self.b_disconnect_dlp.place(x=925, y=95) # Side by side with reload, 125px gap (button width + spacing)
        
        self.b_reconnect_dlp = Button(win, text="Reconnect DLP", command=self.reconnect_dlp, state=DISABLED)
        self.b_reconnect_dlp.place(x=1050, y=95) # Side by side with disconnect, 125px gap
        
        # State save/load buttons
        self.b_save_state = Button(win, text="Save State", command=self.save_gui_state)
        self.b_save_state.place(x=800, y=130) # Below reload script button
        
        self.b_load_state = Button(win, text="Load State", command=self.load_gui_state)
        self.b_load_state.place(x=925, y=130) # Side by side with save state
        
        # State save/load buttons
        self.b_save_state = Button(win, text="Save State", command=self.save_gui_state)
        self.b_save_state.place(x=800, y=130) # Below reload script button
        
        self.b_load_state = Button(win, text="Load State", command=self.load_gui_state)
        self.b_load_state.place(x=925, y=130) # Side by side with save state
        
        self.sensor_data_window_instance = None
        self.exp_conditions_window = None
        self.image_modification_window = None
        self.auto_home_thread = None
        self.current_print_session_log_dir = None
        self.current_print_number = None
        self.current_print_date_dir = None
        self.current_print_log_base_dir = None
        self.reserved_print_session_log_dir = None
        self.reserved_print_number = None
        self.reserved_print_date_str = None
        self.print_session_in_progress = False

        self.cache_clear_layer = 100000
        self.time1 = 1000

        # --- Existing Canvases and Labels (adjust placement if they conflict with new frames) ---
        self.canvas1 = Canvas(win, height=200, width=270, bg="#FFEFD5")
        self.canvas1.place(x=70, y=390)
        
        self.canvas2 = Canvas(win, height=200, width=500, bg="#FFEFD5")
        self.canvas2.place(x=370, y=390)

        # Prince header with purple background box
        self.header_frame = tk.Frame(win, bg='#834bd0', relief='solid', borderwidth=3, highlightbackground='#834bd0', highlightthickness=0)
        self.header_frame.place(x=450, y=35, width=300, height=95)
        self.lbl0 = tk.Label(self.header_frame, text='Prince', font='Helvetica 50 bold', bg='#834bd0', fg='white')
        self.lbl1 = Label(win, text='Directory of Images')
        self.lbl4 = Label(win, text='Z Axis Position')
        self.lbl5 = Label(win, text=instruction, font='Helvetica 8', foreground='purple', justify=LEFT)
        self.lbl6 = Label(win, text=credit, font='Helvetica 7')
        self.lbl7 = Label(win, text='Printing Progress')
        self.lbl8 = Label(win, text='System Message:') # Label for the status message
        # Define self.t8 (the status display Label) here, tied to status_message_var
        self.t8 = Label(win, textvariable=self.status_message_var, width=50, relief="sunken", anchor="w", justify=LEFT)
        self.lbl9 = Label(win, text='Move distance(mm)')
        self.lbl10 = Label(win, text='Layer thickness(um)', background="#FFEFD5")
        self.lbl11 = Label(win, text='Exposure time(s)', background="#FFEFD5")
        self.lbl11_2 = Label(win, text='Base curing time(s)', background="#FFEFD5")
        self.lbl12 = Label(win, text='Stage Control', font='Helvetica 12 bold')
        self.lbl13 = Label(win, text='Print Parameters', font='Helvetica 12 bold')
        self.lbl14 = Label(win, text='LED Current(0-255)')
        self.lbl15 = Label(win, text='Estimate Time: ∞ min') # Old label, now replaced by lbl15_inside
        
        # REMOVE Redundant progress bar and its label from old file
        # self.progress = Progressbar(win, orient=HORIZONTAL, length=500, mode='determinate')
        # self.progress.place(x=50, y=430)
        # self.lbl7 = Label(win, text='Printing Progress')
        # self.lbl7.place(x=250, y=400)


        self.lbl16 = Label(win, text='Step Speed (um/s)', background="#FFEFD5") 
        self.lbl17 = Label(win, text='Pause (s)', background="#FFEFD5") 
        self.lbl19 = Label(win, text='Overstep (µm)', background="#FFEFD5")
        self.lbl21 = Label(win, text='Acceleration (mm/s²)', background="#FFEFD5")  # UNIT CHANGED to mm/s²

        # COLUMN 2: Step Speed, Overstep, Pause
        column2_x = 550
        self.lbl16.place(x=column2_x, y=420)
        self.t16 = Entry(win)
        self.t16.place(x=column2_x, y=440)
        self.t16.insert(END, "1000.0") # Default Step Speed
        
        self.lbl19.place(x=column2_x, y=460)
        self.t19 = Entry(win)
        self.t19.place(x=column2_x, y=480)
        self.t19.insert(END, "500") # Default Overstep in µm
        
        self.lbl17.place(x=column2_x, y=500)
        self.t17 = Entry(win)
        self.t17.place(x=column2_x, y=520)
        self.t17.insert(END, "0.0") # Default Pause
        
        # COLUMN 3: Acceleration only
        column3_x = 700
        self.lbl21.place(x=column3_x, y=420)
        self.t21 = Entry(win)
        self.t21.place(x=column3_x, y=440)
        self.t21.insert(END, "5.0") # Default Acceleration in mm/s²

        # --- Auto-Home Control Box ---
        frame_auto_home_y_start = 590 # Positioned above sandwich controls
        frame_auto_home_width = 750 # Define width for re-use
        self.frame_auto_home = LabelFrame(win, text="Auto-Home Control", padding=(10, 10))
        self.frame_auto_home.place(x=50, y=frame_auto_home_y_start, width=frame_auto_home_width) # Adjust width as needed

        self.lbl_auto_home_guess = Label(self.frame_auto_home, text='Guess (mm):')
        self.lbl_auto_home_guess.grid(row=0, column=0, padx=2, pady=2, sticky=W)
        self.t_auto_home_guess = Entry(self.frame_auto_home, width=8)
        self.t_auto_home_guess.grid(row=0, column=1, padx=2, pady=2)
        self.t_auto_home_guess.insert(END, "10.0") # Default initial guess is 10.0 mm

        self.lbl_contact_threshold_abs = Label(self.frame_auto_home, text='Abs. Force (N):')
        self.lbl_contact_threshold_abs.grid(row=0, column=2, padx=2, pady=2, sticky=W)
        self.t_contact_threshold_abs = Entry(self.frame_auto_home, width=8)
        self.t_contact_threshold_abs.grid(row=0, column=3, padx=2, pady=2)
        self.t_contact_threshold_abs.insert(END, "0.1")

        self.lbl_contact_threshold_delta = Label(self.frame_auto_home, text='Delta Force (N):')
        self.lbl_contact_threshold_delta.grid(row=0, column=4, padx=2, pady=2, sticky=W)
        self.t_contact_threshold_delta = Entry(self.frame_auto_home, width=8)
        self.t_contact_threshold_delta.grid(row=0, column=5, padx=2, pady=2)
        self.t_contact_threshold_delta.insert(END, "0.02")

        self.b_auto_home = Button(self.frame_auto_home, text="Auto-Home Surface", command=self.start_auto_home_sequence, state=DISABLED)
        self.b_auto_home.grid(row=0, column=6, padx=10, pady=2)

        # --- Sandwich Control Box ---
        frame_sandwich_y_start = 660  # Below the Auto-Home frame (70px gap for auto-home height)
        self.frame_sandwich = LabelFrame(win, text="Sandwich Routine (Glass Contact)", padding=(10, 10))
        self.frame_sandwich.place(x=50, y=frame_sandwich_y_start, width=frame_auto_home_width)

        # Row 0: Pre-calibration parameters
        self.lbl_sandwich_gap = Label(self.frame_sandwich, text='Gap Estimate (mm):')
        self.lbl_sandwich_gap.grid(row=0, column=0, padx=2, pady=2, sticky=W)
        self.t_sandwich_gap = Entry(self.frame_sandwich, width=8)
        self.t_sandwich_gap.grid(row=0, column=1, padx=2, pady=2)
        self.t_sandwich_gap.insert(END, "0.5")  # Default gap estimate for pre-calibration
        
        self.lbl_sandwich_force = Label(self.frame_sandwich, text='Target Pressure (Pa):')
        self.lbl_sandwich_force.grid(row=0, column=2, padx=2, pady=2, sticky=W)
        self.t_sandwich_force = Entry(self.frame_sandwich, width=8)
        self.t_sandwich_force.grid(row=0, column=3, padx=2, pady=2)
        self.t_sandwich_force.insert(END, "15790")  # Default: 0.5N / 31.67mm² = 15790 Pa for Ø6.35mm platform
        
        self.lbl_sandwich_speed = Label(self.frame_sandwich, text='Print Speed (µm/s):')
        self.lbl_sandwich_speed.grid(row=0, column=4, padx=2, pady=2, sticky=W)
        self.t_sandwich_speed = Entry(self.frame_sandwich, width=8)
        self.t_sandwich_speed.grid(row=0, column=5, padx=2, pady=2)
        self.t_sandwich_speed.insert(END, "500")  # Default sandwich speed for printing

        # Row 1: Enable checkbox
        self.enable_sandwich_precalib = BooleanVar(value=True)  # Default enabled
        self.chk_sandwich_precalib = Checkbutton(
            self.frame_sandwich, 
            text='Enable Sandwich Routine',
            variable=self.enable_sandwich_precalib
        )
        self.chk_sandwich_precalib.grid(row=1, column=0, columnspan=3, padx=2, pady=5, sticky=W)
        
        # Adaptive sandwich checkbox (next to enable checkbox)
        self.enable_adaptive_sandwich = BooleanVar(value=False)  # Default disabled (use classic)
        self.chk_adaptive_sandwich = Checkbutton(
            self.frame_sandwich,
            text='Use Adaptive Sandwich (Force-Responsive)',
            variable=self.enable_adaptive_sandwich,
            command=self._on_sandwich_mode_change
        )
        self.chk_adaptive_sandwich.grid(row=1, column=3, columnspan=3, padx=2, pady=5, sticky=W)
        
        # Row 2: Force at Max Area input (for bidirectional sandwich)
        self.lbl_max_area_force = Label(self.frame_sandwich, text='Force at Max Area (N):')
        self.lbl_max_area_force.grid(row=2, column=0, padx=2, pady=2, sticky=W)
        self.t_max_area_force = Entry(self.frame_sandwich, width=8)
        self.t_max_area_force.grid(row=2, column=1, padx=2, pady=2)
        self.t_max_area_force.insert(END, "-2.0")  # Default: -2.0N at 100mm²
        
        # Linear area-scaled force sandwich checkbox (row 2, right side)
        self.enable_scaled_force_sandwich = BooleanVar(value=False)  # Linear area-scaled force method
        self.chk_scaled_force_sandwich = Checkbutton(
            self.frame_sandwich,
            text='Use Linear Area-Scaled Sandwich (Bidirectional Correction)',
            variable=self.enable_scaled_force_sandwich,
            command=self._on_sandwich_mode_change
        )
        self.chk_scaled_force_sandwich.grid(row=2, column=3, columnspan=3, padx=2, pady=5, sticky=W)

        self.sandwich_thread = None  # Track sandwich routine thread
        
        # Variables to store pre-calibration results
        self.measured_gap_mm = None  # Measured gap distance from pre-calibration
        self.measured_derivative_threshold = None  # Measured force derivative threshold
        
        # Variables for linear area-scaled force sandwich
        self.scaled_force_max_area = 100.0  # mm² - maximum area for scaling
        # scaled_force_at_max_area will be read from UI field (t_max_area_force)
        self.scaled_force_calibration_force = -0.6  # N - calibration force for gap measurement
        self.scaled_force_safety_limit = -4.0  # N - absolute safety limit
        self.scaled_force_base_flatness_threshold = 0.05  # N - base flatness threshold (calibrated on first layer)
        self.scaled_force_max_iterations = 3  # Maximum correction iterations (reduced from 5)
        
        # Unified sandwich routine manager (initialized later after axis/force gauge are available)
        self.sandwich_manager = None


        # --- Existing Layer Logger instantiation removed ---
        
        # --- Define Entry Widgets (including t1) ---
        self.t1 = Entry(width=160)
        self.t4 = Entry()
        # self.t8 = Entry() # This comment is now misleading as t8 is a Label. Can be removed.
        self.t9 = Entry()
        self.t10 = Entry()
        self.t11 = Entry()
        self.t11_2 = Entry()
        self.t14 = Entry()

        # --- Place Entry Widgets and Labels ---
        self.lbl0.pack(expand=True, fill='both', padx=5, pady=5)  # Pack with padding to show full border
        self.lbl1.place(x=50, y=150)
        self.t1.place(x=180, y=150) # t1 is now defined before _check_default_logging_windows_file

        self.lbl4.place(x=50, y=230) # Moved up from 260
        self.t4.place(x=50, y=250) # Moved up from 280
        self.lbl5.place(x=710, y=180)
        self.lbl6.place(x=950, y=0)
        # self.t8.place(x=500, y=280) # This line will now work as self.t8 is defined
        self.lbl8.place(x=50, y=40) # "System Message:" - aligned slightly above system box
        # System message display box at top, shortened to avoid header overlap
        self.t8.place(x=50, y=60) # Place the actual status message display, aligned with Open Sensor Panel
        self.t9.place(x=140, y=450)
        self.lbl9.place(x=140, y=430)
        self.t10.place(x=400, y=440)
        self.lbl10.place(x=400, y=420)
        self.t11.place(x=400, y=480)
        self.lbl11.place(x=400, y=460)
        self.t11_2.place(x=400, y=520)
        self.lbl11_2.place(x=400, y=500)
        self.lbl12.place(x=150, y=370)
        self.lbl13.place(x=410, y=370)
        self.t14.place(x=250, y=250) # Closer to Z-axis position
        self.lbl14.place(x=250, y=230) # Closer to Z-axis position
        # self.lbl15.place(x=250, y=460) # Removed - now inside progress bar as lbl15_inside

        # self.lbl_current_layer_display = Label(win, textvariable=self.current_layer_num_var, font='Helvetica 10')
        # self.lbl_current_layer_display.place(x=400, y=400) # This was a duplicate, ensure it's removed or commented

        # self.progress = Progressbar(win, orient=HORIZONTAL, length=500, mode='determinate') # This is already commented out
        # self.progress.place(x=50, y=430) # This is already commented out

        self.b1 = Button(win, text='Run-Cont.', command=self.run_Continuous)
        self.b10 = Button(win, text='Run-Step', command=self.run_Stepped)
        self.b_set_dir = Button(win, text='Set Direct.', command=self.input_directory)
        self.b4 = Button(win, text='Stop', command=self.stop)
        self.b2 = Button(win, text='Set Home', command=self.set_home)
        self.b3 = Button(win, text='Get Position', command=self.get_position)
        self.b5 = Button(win, text='Move Down', command=self.movedown)
        self.b6 = Button(win, text='Move Up', command=self.moveup)
        self.b7 = Button(win, text='Simple input txt generator', command=self.simple_txt)

        # Run buttons and Stop button aligned with right side buttons at y=95
        self.b1.place(x=50, y=95)
        self.b10.place(x=140, y=95)
        self.b_set_dir.place(x=230, y=95)
        self.b4.place(x=330, y=95)
        
        # Z-Axis controls back at original position
        self.b2.place(x=50, y=200)
        self.b3.place(x=140, y=200)
        
        # Move Up/Down buttons stay in stage control area
        self.b5.place(x=100, y=500)
        self.b6.place(x=200, y=500)
        self.b7.place(x=400, y=550)
        
        # Smooth motion checkboxes next to Simple input txt generator button
        self.smoother_retraction_var = tk.IntVar(value=0)
        self.chk_smoother_retraction = tk.Checkbutton(
            win, 
            text='Smooth Retraction', 
            variable=self.smoother_retraction_var,
            command=self.toggle_smoother_retraction
        )
        self.chk_smoother_retraction.place(x=580, y=550)
        
        self.smooth_lifting_var = tk.IntVar(value=0)
        self.chk_smooth_lifting = tk.Checkbutton(
            win,
            text='Smooth Lifting',
            variable=self.smooth_lifting_var,
            command=self.toggle_smooth_lifting
        )
        self.chk_smooth_lifting.place(x=720, y=550)

        # --- Initialize active_logging_windows_filepath AFTER t1 and status_message_var are created ---
        # self.active_logging_windows_filepath = None
        # self._check_default_logging_windows_file() # MOVED HERE, now status_message_var exists

        # --- Controller, Application, Zaber Setup ---
        self.controller = pycrafter9000.dmd()
        self.application = libs.Application()
        self.controller.stopsequence()
        self.controller.power(current=0)  # Set power to 0 BEFORE video mode to prevent flash
        time.sleep(0.1)  # Small delay to ensure power is off
        self.controller.changemode(3)
        self.controller.hdmi()
        self.update_status_message("DLP initialized: Power=0, Video Mode, HDMI input")

        Library.enable_device_db_store()
        connection = Connection.open_serial_port("COM3")
        device_list = connection.detect_devices()
        device = device_list[0]
        self.axis = device.get_axis(1)
        self.axis.home()
        
        # Set default acceleration for the Zaber stage upon initialization
        try:
            desired_startup_accel_physical_ums2 = 100000 # µm/s² (equivalent to 100 mm/s²)
            
            # Get current acceleration setting value for diagnostics
            # The library typically returns this in the setting's inherent physical units (µm/s² for "accel")
            current_accel_val_before = self.axis.settings.get("accel")
            self.update_status_message(f"Stage accel BEFORE setting: {current_accel_val_before} µm/s² (assuming library default unit for 'accel')")

            # Set the "accel" setting, explicitly providing the unit of the value
            self.axis.settings.set(
                "accel", 
                desired_startup_accel_physical_ums2, 
                unit=Units.ACCELERATION_MICROMETRES_PER_SECOND_SQUARED
            )
            
            # Verify by getting the setting again, explicitly requesting µm/s²
            current_accel_val_after = self.axis.settings.get("accel", unit=Units.ACCELERATION_MICROMETRES_PER_SECOND_SQUARED)
            self.update_status_message(f"Default stage acceleration SET to: {desired_startup_accel_physical_ums2} µm/s². READ BACK as: {current_accel_val_after} µm/s².")

            if abs(current_accel_val_after - desired_startup_accel_physical_ums2) > 1: # Allow for small rounding
                 self.update_status_message(f"WARNING: Readback acceleration {current_accel_val_after} µm/s² differs from desired {desired_startup_accel_physical_ums2} µm/s².", error=True)

        except Exception as e:
            self.update_status_message(f"Error setting default stage acceleration: {e}", error=True)
            traceback.print_exc() # Print full traceback for debugging
        
        # Initialize MotionController for smooth lifting and retraction
        self.motion_controller = MotionController(axis=self.axis, force_gauge_manager=None)
        self.update_status_message("MotionController initialized")

        # --- Initial t.insert values ---
        self.t1.delete(0, 'end')
        self.t4.delete(0, 'end')
        # self.t8.delete(0, 'end') # Not needed if t8 is a Label with textvariable
        self.t9.delete(0, 'end')
        self.t10.delete(0, 'end')
        self.t11.delete(0, 'end')
        self.t11_2.delete(0, 'end')
        self.t14.delete(0, 'end')
        self.t1.insert(END, str("C:\\Users\\cheng sun\\BoyuanSun\\Slicing\\Calibration\\Power_Grayscale"))
        self.t4.insert(END, str("0"))
        # self.t8.insert(END, str("Stage connected")) # This will be set by update_status_message
        self.t9.insert(END, str("0"))
        self.t10.insert(END, str("5"))
        self.t11.insert(END, str("1"))
        self.t11_2.insert(END, str("1"))
        self.t14.insert(END, str("1"))

        # --- Screeninfo, window_name, black_image ---
        screen_id = 0
        self.screen = screeninfo.get_monitors()[screen_id]
        self.window_name = 'show'
        self.black_image = np.zeros((1600, 2560))

        self.update_auto_home_button_state()
        self.update_status_message("System Ready.") # Example of setting initial status
        
        # Try to auto-load state on startup
        self.win.after(100, self._try_autoload_state)
        
        # Try to auto-load state on startup
        self.win.after(100, self._try_autoload_state)
    
    def _update_gui_progress(self, progress_value, total_layers, current_layer_index):
        """Updates the progress bar and layer count display."""
        if hasattr(self, 'p1'):
            self.p1['value'] = progress_value
        
        # current_layer_index is 0-based, display is 1-based
        if hasattr(self, 'current_layer_num_var'):
            self.current_layer_num_var.set(f"Layer: {current_layer_index + 1}/{total_layers}")
        
        # Update estimated time remaining for stepped printing
        if hasattr(self, 'exposure_time') and self.exposure_time and current_layer_index < len(self.exposure_time):
            remaining_layers = total_layers - (current_layer_index + 1)
            if remaining_layers > 0 and len(self.exposure_time) > 0:
                # Calculate remaining exposure time
                remaining_exposure = sum(self.exposure_time[current_layer_index:]) if current_layer_index < len(self.exposure_time) else 0
                
                # Calculate remaining pause time
                remaining_pauses = sum(self.pause_list[current_layer_index:]) if hasattr(self, 'pause_list') and current_layer_index < len(self.pause_list) else 0
                
                # Calculate remaining movement time (lift + retract + sandwich if enabled)
                remaining_movement_time = 0.0
                
                # Get default parameters from GUI (fallbacks)
                default_overstep = float(self.t19.get()) if hasattr(self, 't19') and self.t19.get() else 0.0
                default_speed = float(self.t16.get()) if hasattr(self, 't16') and self.t16.get() else 1000.0
                default_sandwich_speed = float(self.t_sandwich_speed.get()) if hasattr(self, 't_sandwich_speed') and self.t_sandwich_speed.get() else 500.0
                
                # Calculate movement time for each remaining layer
                for layer_idx in range(current_layer_index, total_layers):
                    # Get layer-specific parameters
                    layer_overstep = self.overstep_distance_list[layer_idx] if hasattr(self, 'overstep_distance_list') and layer_idx < len(self.overstep_distance_list) else default_overstep
                    layer_speed = self.step_speed_list[layer_idx] if hasattr(self, 'step_speed_list') and layer_idx < len(self.step_speed_list) else default_speed
                    layer_sandwich_speed = self.sandwich_speed_list[layer_idx] if hasattr(self, 'sandwich_speed_list') and layer_idx < len(self.sandwich_speed_list) else default_sandwich_speed
                    
                    # Lift time calculation (with smooth lifting if enabled)
                    if self.smooth_lifting_enabled:
                        # 2-stage smooth lifting: 50µm at 100µm/s + remaining at layer_speed
                        stage1_time = 0.05 / 0.1  # 50µm / 100µm/s = 0.5 seconds
                        remaining_distance_mm = layer_overstep - 0.05  # mm
                        stage2_time = (remaining_distance_mm / layer_speed) if layer_speed > 0 and remaining_distance_mm > 0 else 0
                        lift_time = stage1_time + stage2_time
                    else:
                        # Standard single-stage lift
                        lift_time = (layer_overstep / layer_speed) if layer_speed > 0 else 0
                    
                    # Retract time calculation (with smooth retraction if enabled)
                    if self.smoother_retraction_enabled:
                        # 2-stage smooth retraction: most at layer_speed + 200µm at 100µm/s
                        remaining_distance_mm = layer_overstep - 0.2  # mm (200µm = 0.2mm)
                        stage1_time = (remaining_distance_mm / layer_speed) if layer_speed > 0 and remaining_distance_mm > 0 else 0
                        stage2_time = 0.2 / 0.1  # 200µm / 100µm/s = 2.0 seconds
                        retract_time = stage1_time + stage2_time
                    else:
                        # Standard single-stage retraction
                        retract_time = (layer_overstep / layer_speed) if layer_speed > 0 else 0
                    
                    # Sandwich time (if pre-calibration was successful)
                    sandwich_time = 0.0
                    if hasattr(self, 'measured_gap_mm') and self.measured_gap_mm is not None:
                        # Down movement: measured_gap distance at sandwich speed
                        sandwich_down = (self.measured_gap_mm * 1000.0 / layer_sandwich_speed) if layer_sandwich_speed > 0 else 0
                        # Up movement: same distance, same speed
                        sandwich_up = sandwich_down
                        # 1 second settling time after retract
                        sandwich_settling = 1.0
                        sandwich_time = sandwich_down + sandwich_up + sandwich_settling
                    
                    # Additional overhead per layer
                    # Based on empirical testing (7s observed vs 5.2s calculated):
                    # - Stage acceleration/deceleration and idle transitions: ~0.5-1.0s
                    # - Image loading and display (cv2.imshow + waitKey): ~0.2-0.5s
                    # - DLP power changes (2x per layer): ~0.2-0.4s
                    # - Diagnostics and force readings (pre-peel, pre-return): ~0.1-0.3s
                    # - Phase changes, GUI updates, communications: ~0.2s
                    layer_overhead = 1.8  # Total empirical overhead per layer
                    
                    # Add to total movement time
                    remaining_movement_time += lift_time + retract_time + sandwich_time + layer_overhead
                
                # Total estimate
                total_estimated_seconds = remaining_exposure + remaining_pauses + remaining_movement_time
                self.lbl15_var.set(f'Est: {total_estimated_seconds / 60:.1f} min')
            else:
                self.lbl15_var.set('Est: Done')


        self.win.update_idletasks() # Process pending GUI updates

    def run_Continuous(self):
        self.flag = False # Reset stop flag for a new print attempt
        self.pause_flag = False # Reset pause flag as well
        self.update_status_message("Starting Continuous Print Setup...")
        try:
            self.initilze_stage() 
            self.input_directory() 
            if not self.image_list:
                self.update_status_message("No images found or directory not set. Aborting print.")
                messagebox.showerror("Print Error", "Image directory not set or no images found.")
                return

            val_t14 = self.t14.get()
            dlp_power = int(val_t14)

            val_t16 = self.t16.get()
            step_speed_um_s = float(val_t16) if val_t16 else 1000.0

            val_t17 = self.t17.get()
            layer_pause_s = float(val_t17) if val_t17 else 0.0

            val_t19 = self.t19.get()
            overstep_um_gui = float(val_t19) if val_t19 else 0.0

            val_t21 = self.t21.get()
            step_type_val_mms2 = float(val_t21) if val_t21 else 0.0
            
            self.b1.config(state=DISABLED)
            self.b10.config(state=DISABLED)
            self.b4.config(state=NORMAL)

            self.start_print_thread(
                dlp_power=dlp_power,
                step_speed_um_s=step_speed_um_s,
                layer_pause_s=layer_pause_s,
                overstep_um_gui=overstep_um_gui,
                step_type_val_mms2=step_type_val_mms2, # Pass mm/s² value
                print_mode="continuous"
            )
        except ValueError as e: # Catch ValueError specifically
            self.update_status_message(f"Invalid print parameter input: {e}") # Include the error message
            messagebox.showerror("Input Error", f"Please check print parameters. One of them is not a valid number.\nDetails: {e}")
            self.b1.config(state=NORMAL)
            self.b10.config(state=NORMAL)
        except Exception as e:
            self.update_status_message(f"Error during print setup: {e}")
            messagebox.showerror("Setup Error", f"An error occurred: {e}")
            self.b1.config(state=NORMAL)
            self.b10.config(state=NORMAL)

    def run_Stepped(self):
        self.flag = False # Reset stop flag for a new print attempt
        self.pause_flag = False # Reset pause flag as well
        self.update_status_message("Starting Stepped Print Setup...")
        try:
            self.initilze_stage() 
            self.input_directory() 
            if not self.image_list:
                self.update_status_message("No images found or directory not set. Aborting print.")
                messagebox.showerror("Print Error", "Image directory not set or no images found.")
                return

            val_t14 = self.t14.get()
            dlp_power = int(val_t14)

            val_t16 = self.t16.get()
            step_speed_um_s = float(val_t16) if val_t16 else 1000.0

            val_t17 = self.t17.get()
            layer_pause_s = float(val_t17) if val_t17 else 0.0

            val_t19 = self.t19.get()
            overstep_um_gui = float(val_t19) if val_t19 else 0.0

            val_t21 = self.t21.get()
            step_type_val_mms2 = float(val_t21) if val_t21 else 0.0

            self.b1.config(state=DISABLED)
            self.b10.config(state=DISABLED)
            self.b4.config(state=NORMAL)

            self.start_print_thread(
                dlp_power=dlp_power,
                step_speed_um_s=step_speed_um_s,
                layer_pause_s=layer_pause_s,
                overstep_um_gui=overstep_um_gui,
                step_type_val_mms2=step_type_val_mms2, # Pass mm/s² value
                print_mode="stepped"
            )
        except ValueError as e: # Catch ValueError specifically
            self.update_status_message(f"Invalid print parameter input: {e}") # Include the error message
            messagebox.showerror("Input Error", f"Please check print parameters. One of them is not a valid number.\nDetails: {e}")
            self.b1.config(state=NORMAL)
            self.b10.config(state=NORMAL)
        except Exception as e:
            self.update_status_message(f"Error during print setup: {e}")
            messagebox.showerror("Setup Error", f"An error occurred: {e}")
            self.b1.config(state=NORMAL)
            self.b10.config(state=NORMAL)

    def _get_next_print_number(self, date_specific_log_dir):
        """Determines the next print number for a given date directory."""
        return self.session_manager.get_next_print_number(date_specific_log_dir)

    def _allocate_print_session(self, main_img_dir, prefer_reserved=True, mark_active=False):
        today_str = get_today_str()
        preferred = None

        if prefer_reserved and self.reserved_print_session_log_dir and self.reserved_print_date_str == today_str:
            preferred = self.reserved_print_session_log_dir

        session_info = ensure_print_session(main_img_dir, date_str=today_str, preferred_print_dir=preferred)

        self.current_print_log_base_dir = session_info['base_dir']
        self.current_print_date_dir = session_info['date_dir']
        self.current_print_number = session_info['print_number']
        self.current_print_session_log_dir = session_info['print_dir']

        if mark_active:
            self.print_session_in_progress = True
            self.reserved_print_session_log_dir = None
            self.reserved_print_number = None
            self.reserved_print_date_str = None
        else:
            self.reserved_print_session_log_dir = self.current_print_session_log_dir
            self.reserved_print_number = self.current_print_number
            self.reserved_print_date_str = today_str

        return session_info

    def reserve_print_session_for_conditions(self):
        main_img_dir = str(self.t1.get()).strip()
        if not main_img_dir or not os.path.isdir(main_img_dir):
            raise ValueError("Please set a valid image directory before saving conditions.")
        return self._allocate_print_session(main_img_dir, prefer_reserved=True, mark_active=False)['print_dir']

    def ensure_print_session_for_image_processing(self, source_folder):
        main_img_dir = source_folder
        if self.print_session_in_progress and self.current_print_session_log_dir:
            return self.current_print_session_log_dir
        return self._allocate_print_session(main_img_dir, prefer_reserved=True, mark_active=False)['print_dir']

    def start_print_thread(self, dlp_power, step_speed_um_s, layer_pause_s, overstep_um_gui, step_type_val_mms2, print_mode): # PARAM RENAMED
        # The try block should start here, encompassing all setup and thread starting
        try:
            self.update_status_message(f"Starting {print_mode} Print Setup...")
            
            path = str(self.t1.get())
            if not path or not os.path.isdir(path):
                self.update_status_message("Error: Image directory not set or invalid.", error=True)
                messagebox.showerror("Setup Error", "Please set a valid image directory first.", parent=self.win)
                return

            session_info = self._allocate_print_session(path, prefer_reserved=True, mark_active=True)
            self.update_status_message(f"Print session ready: {session_info['print_dir']}")

            if self.exp_conditions_window and self.exp_conditions_window.is_logging_enabled():
                self.exp_conditions_window.start_new_print(self.current_print_session_log_dir)

            # Auto-logging configuration now relies entirely on SensorDataWindow's state
            if self.sensor_data_window_instance and self.sensor_data_window_instance.sensor_window.winfo_exists():
                # Check if the "Enable Automated Logging" checkbox *within SensorDataWindow* is checked
                if self.sensor_data_window_instance.auto_log_enabled_var.get():
                    self.update_status_message("Sensor Panel auto-log is enabled, configuring...")
                    
                    # Configure AutomatedLayerLogger via SensorDataWindow with proper parameters
                    self.sensor_data_window_instance.configure_automated_layer_logging(
                        main_image_dir=path,
                        print_number=self.current_print_number,
                        date_str_for_dir=session_info['date_str'],
                        log_directory=self.current_print_session_log_dir
                    )
                    self.update_status_message(f"AutomatedLayerLogger configured for print {self.current_print_number}.")
                else:
                    self.update_status_message("Sensor Panel auto-log is disabled. Proceeding without automated logging.")
            else:
                self.update_status_message("Sensor Panel not open. Automated logging will not be active.")
            
            # Start the actual print thread
            self.print_thread = threading.Thread(target=self.print_t, args=(
                dlp_power, step_speed_um_s, layer_pause_s, overstep_um_gui, step_type_val_mms2, print_mode # Pass mm/s²
            ))
            self.print_thread.daemon = True
            self.print_thread.start()
            self.update_status_message(f"{print_mode.capitalize()} print thread initiated.")

        except Exception as e:
            self.update_status_message(f"Error in start_print_thread: {e}", error=True)
            traceback.print_exc()
            if hasattr(self, 'b1'): self.b1.config(state=NORMAL)
            if hasattr(self, 'b10'): self.b10.config(state=NORMAL)
            if hasattr(self, 'b4'): self.b4.config(state=DISABLED)

    def reload_script_modules(self):
        """Hot reload script modules without losing calibration."""
        try:
            import importlib
            import sys
            
            self.update_status_message("Reloading script modules...")
            
            # List of modules to reload (add more as needed)
            modules_to_reload = [
                'support_modules.SensorDataWindow',
                # Reload image-modification dependencies before the window class
                # so new symbols (e.g., helper generators) are available.
                'support_modules.image_modification.processor',
                'support_modules.image_modification.edge_enhancement',
                'support_modules.image_modification.global_enhancement',
                'support_modules.image_modification.padding',
                'support_modules.image_modification.scattering_compensation',
                'support_modules.ImageModificationWindow',
                'support_modules.PeakForceLogger',
                'support_modules.adhesion_metrics_calculator',
                'support_modules.enhanced_adhesion_metrics',
                'support_modules.AutomatedLayerLogger',
                'support_modules.PositionLogger',
                'support_modules.ForceGaugeManager',
                'support_modules.AutoHomeRoutine',
                'support_modules.two_step_baseline_analyzer',
                'support_modules.SandwichRoutine',
                'support_modules.SandwichRoutines',  # Added - the new unified sandwich manager
                'post_print_analyzer',
                'support_modules.ExperimentalConditionsWindow'
            ]
            
            reloaded_count = 0
            for module_name in modules_to_reload:
                if module_name in sys.modules:
                    importlib.reload(sys.modules[module_name])
                    reloaded_count += 1

            # Ensure ImageModificationWindow module/class is re-imported and active
            try:
                if 'support_modules.ImageModificationWindow' in sys.modules:
                    importlib.reload(sys.modules['support_modules.ImageModificationWindow'])
                # Import the class into our namespace
                from support_modules.ImageModificationWindow import ImageModificationWindow as _IMWClass
                # If the window is currently open, destroy and recreate it to pick up changes
                if hasattr(self, 'image_modification_window') and self.image_modification_window is not None:
                    old_folder = None
                    old_layer = None
                    try:
                        if hasattr(self.image_modification_window, 'folder_entry'):
                            old_folder = self.image_modification_window.folder_entry.get().strip()
                    except Exception:
                        pass
                    try:
                        if hasattr(self.image_modification_window, 'layer_var'):
                            old_layer = self.image_modification_window.layer_var.get().strip()
                    except Exception:
                        pass
                    try:
                        if hasattr(self.image_modification_window, 'window') and self.image_modification_window.window.winfo_exists():
                            self.image_modification_window.window.destroy()
                    except Exception:
                        pass
                    try:
                        self.image_modification_window = _IMWClass(self.win, self.update_status_message, self)
                        if old_folder:
                            try:
                                self.image_modification_window.folder_entry.delete(0, 'end')
                                self.image_modification_window.folder_entry.insert(0, old_folder)
                                self.image_modification_window._refresh_image_list()
                                if old_layer:
                                    self.image_modification_window.layer_var.set(old_layer)
                                self.image_modification_window._load_layer()
                            except Exception:
                                pass
                        try:
                            self.image_modification_window.window.lift()
                            self.image_modification_window.window.focus_force()
                        except Exception:
                            pass
                        self.update_status_message('Image Modification window reloaded and refreshed')
                    except Exception as e:
                        self.update_status_message(f'Error recreating Image Modification window after reload: {e}', error=True)
            except Exception as e:
                # Non-fatal: continue, but report
                self.update_status_message(f'Warning: could not hot-reload ImageModificationWindow: {e}', error=True)
            
            self.update_status_message(f"Script reload complete: {reloaded_count} modules reloaded")
            self.update_status_message("Note: Changes will take effect for new operations. Hardware connections preserved.")
            
        except Exception as e:
            self.update_status_message(f"Error reloading modules: {e}", error=True)
    
    def disconnect_dlp(self):
        """Disconnect DLP for power cycling."""
        try:
            if hasattr(self, 'controller'):
                self.controller.stopsequence()
                self.controller.power(current=0)
                self.controller.changemode(3)
                del self.controller
                self.update_status_message("DLP disconnected. You can now power cycle the light engine.")
                self.b_disconnect_dlp.config(state=DISABLED)
                self.b_reconnect_dlp.config(state=NORMAL)
            else:
                self.update_status_message("DLP not connected", error=True)
        except Exception as e:
            self.update_status_message(f"Error disconnecting DLP: {e}", error=True)
    
    def reconnect_dlp(self):
        """Reconnect to DLP after power cycling."""
        try:
            self.controller = pycrafter9000.dmd()
            self.controller.stopsequence()
            self.controller.power(current=0)  # Set power to 0 BEFORE video mode
            time.sleep(0.1)
            self.controller.changemode(3)
            self.controller.hdmi()
            self.update_status_message("DLP reconnected: Power=0, Video Mode, HDMI input")
            self.b_disconnect_dlp.config(state=NORMAL)
            self.b_reconnect_dlp.config(state=DISABLED)
        except Exception as e:
            self.update_status_message(f"Error reconnecting DLP: {e}", error=True)
    
    def cleanup_dlp_safe_state(self):
        """Reset DLP to safe idle state: stop sequence, power off, video mode."""
        try:
            if hasattr(self, 'controller'):
                self.controller.stopsequence()
                self.controller.power(current=0)  # Turn off LED
                self.controller.changemode(3)     # HDMI/video mode
                self.update_status_message("DLP reset to safe state (video mode, power=0)")
        except Exception as e:
            self.update_status_message(f"Error resetting DLP: {e}", error=True)
    
    def save_gui_state(self):
        """Save current GUI state to JSON file."""
        self.session_manager.save_gui_state()
    
    def load_gui_state(self):
        """Load GUI state from JSON file."""
        self.session_manager.load_gui_state()
    
    def toggle_smoother_retraction(self):
        """Toggle smoother retraction mode with gentle deceleration."""
        if self.smoother_retraction_var.get() == 1:
            self.update_status_message("Smooth Retraction ENABLED: Using 1 mm/s² gentle acceleration")
        else:
            self.update_status_message("Smooth Retraction DISABLED: Using normal acceleration")
    
    @property
    def smoother_retraction_enabled(self):
        """Property to check if smoother retraction is enabled."""
        return self.smoother_retraction_var.get() == 1
    
    def toggle_smooth_lifting(self):
        """Toggle smooth lifting mode with multi-stage velocity ramping."""
        if self.smooth_lifting_var.get() == 1:
            self.update_status_message("Smooth Lifting ENABLED: Using 3-stage velocity ramp (200→400→1000 µm/s)")
        else:
            self.update_status_message("Smooth Lifting DISABLED: Using constant peel velocity")
    
    @property
    def smooth_lifting_enabled(self):
        """Property to check if smooth lifting is enabled."""
        return self.smooth_lifting_var.get() == 1
    
    def _apply_sensor_settings(self):
        """Apply pending sensor settings if sensor window is open."""
        try:
            if not hasattr(self, '_pending_sensor_settings'):
                return
            
            if not (self.sensor_data_window_instance and self.sensor_data_window_instance.sensor_window.winfo_exists()):
                return
            
            settings = self._pending_sensor_settings
            sdw = self.sensor_data_window_instance
            
            if 'auto_log_enabled' in settings and hasattr(sdw, 'auto_log_enabled_var'):
                sdw.auto_log_enabled_var.set(settings['auto_log_enabled'])
            
            if 'record_work' in settings and hasattr(sdw, 'record_work_var'):
                sdw.record_work_var.set(settings['record_work'])
            
            delattr(self, '_pending_sensor_settings')
            self.update_status_message("Sensor window settings restored")
            
        except Exception as e:
            self.update_status_message(f"Warning: Could not apply sensor settings: {e}")
    
    def _try_autoload_state(self):
        """Try to automatically load state on startup (silent if no state exists)."""
        try:
            state_file = os.path.join(os.path.dirname(__file__), 'prince_gui_state.json')
            if os.path.exists(state_file):
                self.load_gui_state()
        except:
            pass  # Silently fail if autoload doesn't work


    def _set_phase_robust(self, phase_name):
        """Robust helper to set phase in position logger."""
        try:
            if (hasattr(self, 'sensor_data_window_instance') and 
                self.sensor_data_window_instance and
                hasattr(self.sensor_data_window_instance, 'position_logger') and
                self.sensor_data_window_instance.position_logger):
                self.sensor_data_window_instance.position_logger.set_phase(phase_name)
        except Exception as e:
            print(f"Warning: Could not set phase to {phase_name}: {e}")
    
    def _cleanup_print_resources(self):
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


    def print_t(self, dlp_power, step_speed_um_s, layer_pause_s, overstep_um_gui, step_type_val_mms2, print_mode): # PARAM RENAMED
        try:
            self.update_status_message("Print thread started.")
            # Use MyWindow's own image_list to determine if layers are loaded
            if not self.image_list: # Check if self.image_list (populated by input_directory) is empty
                self.update_status_message("Error: No layers loaded. Aborting print.", error=True)
                messagebox.showerror("Print Error", "No layers loaded. Please check instruction file generation and image directory.", parent=self.win)
                self.b1.config(state=NORMAL)
                self.b10.config(state=NORMAL)
                self.b4.config(state=DISABLED)
                self.print_thread = None
                return

            self.b1.config(state=DISABLED)
            self.b10.config(state=DISABLED)
            self.b4.config(state=NORMAL)

            self.axis.move_absolute(position=self.reference, unit=Units.LENGTH_MILLIMETRES, wait_until_idle=True)
            self.update_status_message(f"Moved to reference: {self.reference} mm")

            cv2.namedWindow(self.window_name, cv2.WND_PROP_FULLSCREEN)
            cv2.moveWindow(self.window_name, self.screen.x + 1439, self.screen.y - 1) 
            cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
            cv2.imshow(self.window_name, self.black_image)
            # Pump events longer on the first print to guarantee the black frame reaches the HDMI display buffer
            for _ in range(10):
                cv2.waitKey(50)
            self.win.update_idletasks()
            self.win.update()
            self.update_status_message("OpenCV window initialized.")

            # DLP setup for pattern projection
            if hasattr(self, 'controller'):
                self.controller.power(current=0)  # Set power to 0 BEFORE mode change to prevent flash
                time.sleep(0.1)
                self.controller.changemode(0) # Switch to pattern sequence mode
                self.controller.power(current=0)  # Prevent auto-ignition from mode change

                time.sleep(2.0) # Crucial delay for mode change to take effect
                self.controller.power(current=dlp_power) 
                self.update_status_message(f"DLP set to pattern mode, power: {dlp_power}.")
            else:
                self.update_status_message("DLP controller not available. Cannot control DLP.", error=True)
                # Decide if print should abort if DLP is not available
                # For now, it will continue, but images won't project.

            current_layer_num_for_display = 0
            num_layers = len(self.image_list)
            z_at_previous_exposure_microns = self.reference * 1000 # Z where the "0th" layer or substrate is
            last_commanded_dlp_power = -1 # Initialize to a value that won't match any valid power

            # ========== PRE-CALIBRATION ROUTINE (if enabled) ==========
            if self.enable_sandwich_precalib.get():
                self.update_status_message("Pre-calibration enabled: Starting gap measurement routine...")
                
                # Get gap estimate and target pressure from Sandwich Routine GUI boxes
                # Build platform specs for pressure-to-force conversion
                BUILD_PLATFORM_DIAMETER_MM = 6.35
                BUILD_PLATFORM_AREA_MM2 = 3.14159 * (BUILD_PLATFORM_DIAMETER_MM / 2.0) ** 2  # 31.67mm²
                
                try:
                    gap_estimate_for_precal = float(self.t_sandwich_gap.get()) if hasattr(self, 't_sandwich_gap') else 0.5
                    target_pressure_pa = float(self.t_sandwich_force.get()) if hasattr(self, 't_sandwich_force') else 15790
                except ValueError:
                    gap_estimate_for_precal = 0.5
                    target_pressure_pa = 15790  # Default: 0.5N / 31.67mm²
                    self.update_status_message("Invalid pre-cal parameters, using defaults: Gap=0.5mm, Pressure=15790Pa", error=True)
                
                # Convert pressure (Pa) to force (N) for build platform: Pa = N/mm², so Force = Pressure × Area
                max_force_for_precal = (target_pressure_pa / 1000000.0) * BUILD_PLATFORM_AREA_MM2  # Convert Pa to N/mm² then multiply
                
                self.update_status_message(f"Pre-cal settings: Gap={gap_estimate_for_precal:.3f}mm, Pressure={target_pressure_pa:.0f}Pa (Ø6.35mm)")
                self.update_status_message(f"Pre-cal: Platform force={max_force_for_precal:.3f}N ({target_pressure_pa:.0f}Pa × 31.67mm²)")
                
                # Store pressure for use during printing (will be scaled by layer area)
                self.precal_target_pressure_pa = target_pressure_pa
                self.precal_max_force = max_force_for_precal  # Keep for compatibility
                
                # Get sandwich speed for first layer to use during pre-calibration
                first_layer_sandwich_speed = self.sandwich_speed_list[0] if len(self.sandwich_speed_list) > 0 else 500
                
                # Initialize sandwich manager if needed
                if self.sandwich_manager is None:
                    force_gauge = self.sensor_data_window_instance.force_gauge_manager
                    self.sandwich_manager = SandwichRoutineManager(
                        self.axis, force_gauge, self.update_status_message,
                        set_phase_callback=self._set_phase_robust
                    )
                
                # Run pre-calibration using module
                measured_gap = self.sandwich_manager.perform_precalibration(
                    gap_estimate_mm=gap_estimate_for_precal,
                    contact_force_threshold=max_force_for_precal,
                    sandwich_speed_um_s=first_layer_sandwich_speed,
                    stop_flag_callback=lambda: self.flag
                )
                
                if measured_gap is not None:
                    # Store results for use during sandwich routine
                    self.measured_gap_mm = measured_gap
                    self.adaptive_sandwich_speed_um_s = None  # Will be set if speed needs adjustment
                    self.update_status_message(f"Pre-calibration SUCCESS: Gap={measured_gap:.3f}mm")
                else:
                    self.update_status_message("Pre-calibration FAILED: Will skip sandwich during print", error=True)
                    self.measured_gap_mm = None
                    self.measured_gap_mm = None
                    self.measured_derivative_threshold = None
            else:
                self.update_status_message("Pre-calibration disabled: Sandwich steps will be skipped during print")
                self.measured_gap_mm = None
                self.measured_derivative_threshold = None
            # ========== END PRE-CALIBRATION ==========

            for i in range(num_layers): 
                if self.flag:  
                    self.update_status_message("Print stopped by user.")
                    break
                
                while self.pause_flag: 
                    time.sleep(0.1)
                    if self.flag: 
                        self.update_status_message("Print stopped by user during pause.")
                        break
                if self.flag: break

                current_layer_num_for_display = i + 1

                # --- Fetch Per-Layer Parameters ---
                current_exposure_s = self.exposure_time[i] if i < len(self.exposure_time) else 0.1 
                current_thickness_um = self.thickness[i] if i < len(self.thickness) else 50.0 
                actual_dlp_power = self.intensity_list[i] if i < len(self.intensity_list) else dlp_power
                actual_step_speed_um_s = self.step_speed_list[i] if i < len(self.step_speed_list) else step_speed_um_s
                
                # Overstep is now directly in µm from GUI or file (assuming file also uses µm)
                actual_overstep_microns = self.overstep_distance_list[i] if i < len(self.overstep_distance_list) else overstep_um_gui
                
                # --- Acceleration Calculation (Input is mm/s², Zaber needs µm/s²) ---
                PRACTICAL_MIN_ACCEL_UM_S2 = 800 # UPDATED practical minimum in µm/s²

                current_raw_accel_mms2 = 0.0
                # self.step_type_list is assumed to store acceleration values from file in mm/s²
                # Ensure that when self.application.set_image_directory parses the file,
                # it converts the acceleration column to float.
                if i < len(self.step_type_list) and self.step_type_list[i] is not None:
                    try:
                        current_raw_accel_mms2 = float(self.step_type_list[i])
                    except (ValueError, TypeError):
                        self.update_status_message(f"Warning: Invalid accel value '{self.step_type_list[i]}' in file for L{current_layer_num_for_display}. Using GUI fallback.", error=True)
                        current_raw_accel_mms2 = float(step_type_val_mms2) # step_type_val_mms2 is already float
                else:
                    current_raw_accel_mms2 = float(step_type_val_mms2) # step_type_val_mms2 is already float

                if current_raw_accel_mms2 <= 1e-9: # Effectively zero or negative mm/s²
                    self.update_status_message(f"Info: Acceleration input is {current_raw_accel_mms2:.3f} mm/s². Using practical minimum: {PRACTICAL_MIN_ACCEL_UM_S2} µm/s².")
                    actual_acceleration_to_set_um_s2 = PRACTICAL_MIN_ACCEL_UM_S2
                else: # User provided a positive acceleration in mm/s²
                    requested_accel_ums2 = current_raw_accel_mms2 * 1000.0 # Convert mm/s² to µm/s²
                    if requested_accel_ums2 < PRACTICAL_MIN_ACCEL_UM_S2:
                        self.update_status_message(f"Warning: Requested accel {current_raw_accel_mms2:.3f} mm/s² ({requested_accel_ums2:.0f} µm/s²) is below practical minimum. Using {PRACTICAL_MIN_ACCEL_UM_S2} µm/s².")
                        actual_acceleration_to_set_um_s2 = PRACTICAL_MIN_ACCEL_UM_S2
                    else:
                        actual_acceleration_to_set_um_s2 = requested_accel_ums2
                
                actual_acceleration_to_set_um_s2 = int(round(actual_acceleration_to_set_um_s2)) # Ensure integer, round before int
                
                actual_layer_pause_s = self.pause_list[i] if i < len(self.pause_list) else layer_pause_s

                # DLP power setting removed from here - now handled within each mode (stepped/continuous)
                # to avoid setting power before exposure is ready

                # --- TARGET Z CALCULATION for current layer i ---
                current_target_z_microns = (self.reference * 1000) - sum(self.thickness[k] for k in range(i + 1) if k < len(self.thickness))

                # --- MODE-SPECIFIC OPERATIONS ---
                if print_mode == "continuous":
                    # 1. Calculate continuous velocity for this layer
                    calculated_continuous_velocity_um_s = 0.0
                    if current_exposure_s > 1e-6 and current_thickness_um > 0: # Avoid division by zero or tiny exposure
                        calculated_continuous_velocity_um_s = current_thickness_um / current_exposure_s
                    else:
                        self.update_status_message(f"L{current_layer_num_for_display} (Cont.): Invalid thickness/exposure for velocity. Using default speed.", error=True)
                        calculated_continuous_velocity_um_s = actual_step_speed_um_s # Fallback

                    if calculated_continuous_velocity_um_s <= 1e-6: # Ensure velocity is positive
                        self.update_status_message(f"L{current_layer_num_for_display} (Cont.): Calculated velocity too low. Using default speed.", error=True)
                        calculated_continuous_velocity_um_s = actual_step_speed_um_s # Fallback

                    # 1.5. Ensure DLP power is set correctly for this layer's exposure
                    if hasattr(self, 'controller'):
                        try:
                            current_dlp_power = int(actual_dlp_power)
                            # Only update if different from last commanded value to reduce unnecessary commands
                            if current_dlp_power != last_commanded_dlp_power:
                                self.controller.power(current=current_dlp_power)
                                last_commanded_dlp_power = current_dlp_power
                                self.update_status_message(f"L{current_layer_num_for_display}: DLP power set to {current_dlp_power}")
                        except Exception as e:
                            self.update_status_message(f"L{current_layer_num_for_display}: Could not set DLP power: {e}", error=True)

                    # 2. Display image for layer i
                    image_path = self.image_list[i]
                    image_to_show = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
                    if image_to_show is None:
                        self.update_status_message(f"Error loading image {str(image_path)} for L{current_layer_num_for_display}. Showing black.", error=True)
                        cv2.imshow(self.window_name, self.black_image)
                    else:
                        cv2.imshow(self.window_name, image_to_show)
                    cv2.waitKey(1) # Essential for OpenCV to process imshow
                    
                    # Set phase to Exposure (continuous mode combines exposure + lift)
                    self._set_phase_robust("Exposure")

                    # 3. Start Z-axis movement (non-blocking)
                    self.update_status_message(f"L{current_layer_num_for_display} (Cont.): Moving to {current_target_z_microns / 1000.0:.4f} mm at {calculated_continuous_velocity_um_s:.2f} um/s, Accel: {actual_acceleration_to_set_um_s2} µm/s²")
                    
                    # Set phase to Lift (movement starts)
                    self._set_phase_robust("Lift")
                    
                    self.axis.move_absolute(
                        position=current_target_z_microns,
                        unit=Units.LENGTH_MICROMETRES,
                        wait_until_idle=False, 
                        velocity=calculated_continuous_velocity_um_s,
                        velocity_unit=Units.VELOCITY_MICROMETRES_PER_SECOND,
                        acceleration=actual_acceleration_to_set_um_s2,
                        acceleration_unit=Units.ACCELERATION_MICROMETRES_PER_SECOND_SQUARED
                    )

                    # 4. Exposure time (during which stage is moving)
                    if current_exposure_s > 0:
                        time.sleep(current_exposure_s)
                    else:
                        self.update_status_message(f"L{current_layer_num_for_display} (Cont.): Zero exposure time during move.", error=True)
                        # If exposure is 0, the move might be very fast or effectively skipped depending on thickness.
                        # We still need to ensure the Zaber command completes.

                    # 5. Ensure Z-axis move is complete after exposure time has elapsed
                    self.axis.wait_until_idle()
                    z_at_previous_exposure_microns = current_target_z_microns
                    # For continuous mode, DO NOT show black image here.
                    # The next layer's image will be shown in the next iteration.

                elif print_mode == "stepped":
                    # --- Stepped Mode: Display, Expose, Blackout, then Move ---
                    
                    # 0. Ensure DLP power is set correctly for this layer's exposure
                    if hasattr(self, 'controller'):
                        try:
                            current_dlp_power = int(actual_dlp_power)
                            # Only update if different from last commanded value to reduce unnecessary commands
                            if current_dlp_power != last_commanded_dlp_power:
                                self.controller.power(current=current_dlp_power)
                                last_commanded_dlp_power = current_dlp_power
                                self.update_status_message(f"L{current_layer_num_for_display}: DLP power set to {current_dlp_power}")
                        except Exception as e:
                            self.update_status_message(f"L{current_layer_num_for_display}: Could not set DLP power: {e}", error=True)
                    
                    # 1. Display image for layer i
                    image_path = self.image_list[i]
                    image_to_show = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
                    if image_to_show is None:
                        self.update_status_message(f"Error loading image {str(image_path)} for L{current_layer_num_for_display}. Showing black.", error=True)
                        cv2.imshow(self.window_name, self.black_image)
                    else:
                        cv2.imshow(self.window_name, image_to_show)
                    cv2.waitKey(1)
                    
                    # Set phase to Exposure
                    self._set_phase_robust("Exposure")

                    # 2. Exposure
                    if current_exposure_s > 0:
                        time.sleep(current_exposure_s)
                    else:
                        self.update_status_message(f"L{current_layer_num_for_display} (Stepped): Zero exposure time.", error=True)

                    # 3. Show black image after exposure for stepped mode
                    cv2.imshow(self.window_name, self.black_image)
                    cv2.waitKey(1)
                    
                    # Set phase to Pause (blackout period)
                    self._set_phase_robust("Pause")
                    
                    # 3b. Turn off DLP power to eliminate background light during movement
                    if hasattr(self, 'controller'):
                        try:
                            self.controller.power(current=0)
                            self.update_status_message(f"L{current_layer_num_for_display}: DLP power=0 (background light off)")
                        except Exception as e:
                            self.update_status_message(f"L{current_layer_num_for_display}: Could not set DLP power to 0: {e}", error=True)

                    # 4. Z-Axis Movement (Peel and Return)
                    self.update_status_message(f"Layer {current_layer_num_for_display} (Stepped): Starting peel sequence.")
                    z_exposure_pos_current_layer_i = (self.reference * 1000) - sum(self.thickness[k] for k in range(i) if k < len(self.thickness))
                    # actual_overstep_microns is now directly available

                    # REMOVED: self.axis.settings.set("accel", actual_acceleration_to_set_um_s2)
                    # self.update_status_message(f"Stepped L{current_layer_num_for_display}: Zaber accel set to {actual_acceleration_to_set_um_s2} um/s^2") # No longer setting globally

                    z_peel_peak = z_exposure_pos_current_layer_i - (actual_overstep_microns + current_thickness_um)
                    
                    # PRE-MOVEMENT DIAGNOSTICS
                    try:
                        current_force = self.force_gauge_manager.get_force() if hasattr(self, 'force_gauge_manager') else 0.0
                        current_pos = self.axis.get_position(unit=Units.LENGTH_MICROMETRES)
                        self.update_status_message(f"PRE-PEEL L{current_layer_num_for_display}: Pos={current_pos/1000.0:.4f}mm, Force={current_force:.4f}N")
                        
                        # Check for excessive pre-peel force (could indicate stuck part)
                        if abs(current_force) > 0.5:  # 0.5N threshold - adjust as needed
                            self.update_status_message(f"WARNING L{current_layer_num_for_display}: High pre-peel force detected ({current_force:.4f}N). Part may be stuck!", error=True)
                    except Exception as diag_e:
                        self.update_status_message(f"DEBUG L{current_layer_num_for_display}: Pre-movement diagnostics failed: {diag_e}")
                    
                    # Get current position for smooth lift calculation
                    current_pos_um = self.axis.get_position(unit=Units.LENGTH_MICROMETRES)
                    
                    # Display lifting mode
                    lift_mode = "Smooth 3-stage" if self.smooth_lifting_enabled else "Standard"
                    self.update_status_message(f"Stepped L{current_layer_num_for_display}: Peeling up to {z_peel_peak / 1000.0:.4f} mm ({lift_mode}, Speed: {actual_step_speed_um_s} um/s, Accel: {actual_acceleration_to_set_um_s2} µm/s²)")
                    
                    # Set phase to Lift (peel movement starts)
                    self._set_phase_robust("Lift")
                    
                    try:
                        # Use MotionController for lift with optional smooth ramping
                        lift_result = self.motion_controller.execute_lift(
                            start_pos_um=current_pos_um,
                            target_pos_um=z_peel_peak,
                            base_velocity_um_s=actual_step_speed_um_s,
                            base_acceleration_um_s2=actual_acceleration_to_set_um_s2,
                            smooth_enabled=self.smooth_lifting_enabled,
                            smart_peel_enabled=False,  # Future feature
                            phase_callback=self._set_phase_robust  # Report smooth lifting stages
                        )
                        
                        if lift_result['success']:
                            if self.smooth_lifting_enabled:
                                self.update_status_message(f"SUCCESS L{current_layer_num_for_display}: Peel completed in {lift_result['movement_time_s']:.2f}s ({lift_result['segments_completed']} segments)")
                            else:
                                self.update_status_message(f"SUCCESS L{current_layer_num_for_display}: Peel movement completed")
                        else:
                            raise Exception(lift_result.get('error', 'Unknown lift error'))
                            
                    except Exception as peel_error:
                        self.update_status_message(f"ERROR L{current_layer_num_for_display}: Peel movement failed: {peel_error}", error=True)
                        # Log detailed diagnostics
                        try:
                            fault_status = self.axis.warnings.get_flags()
                            pos_after_fail = self.axis.get_position(unit=Units.LENGTH_MICROMETRES)
                            force_after_fail = self.force_gauge_manager.get_force() if hasattr(self, 'force_gauge_manager') else 0.0
                            self.update_status_message(f"DIAGNOSTICS L{current_layer_num_for_display}: Fault={fault_status}, Pos={pos_after_fail/1000.0:.4f}mm, Force={force_after_fail:.4f}N", error=True)
                        except:
                            pass
                        raise  # Re-raise to trigger print abort

                    z_return_pos = z_peel_peak + actual_overstep_microns
                    
                    # PRE-RETURN DIAGNOSTICS
                    try:
                        current_force = self.force_gauge_manager.get_force() if hasattr(self, 'force_gauge_manager') else 0.0
                        current_pos = self.axis.get_position(unit=Units.LENGTH_MICROMETRES)
                        self.update_status_message(f"PRE-RETURN L{current_layer_num_for_display}: Pos={current_pos/1000.0:.4f}mm, Force={current_force:.4f}N")
                        
                        # Check if force is still high after peel (could indicate adhesion issue)
                        if abs(current_force) > 0.3:  # 0.3N threshold
                            self.update_status_message(f"WARNING L{current_layer_num_for_display}: High post-peel force ({current_force:.4f}N). Return may be difficult!", error=True)
                    except Exception as diag_e:
                        self.update_status_message(f"DEBUG L{current_layer_num_for_display}: Pre-return diagnostics failed: {diag_e}")
                    
                    self.update_status_message(f"Stepped L{current_layer_num_for_display}: Returning to {z_return_pos / 1000.0:.4f} mm (Target for next layer, Accel: {actual_acceleration_to_set_um_s2} µm/s²)")
                    
                    # Set phase to Pause (brief pause at peak before retract)
                    self._set_phase_robust("Pause")
                    
                    # Get current position for smooth retraction calculation
                    current_pos_um = self.axis.get_position(unit=Units.LENGTH_MICROMETRES)
                    
                    try:
                        # Use MotionController for retraction with optional smooth velocity ramping
                        retraction_result = self.motion_controller.execute_retraction(
                            start_pos_um=current_pos_um,
                            target_pos_um=z_return_pos,
                            base_velocity_um_s=actual_step_speed_um_s,
                            base_acceleration_um_s2=actual_acceleration_to_set_um_s2,
                            smooth_enabled=self.smoother_retraction_enabled,
                            phase_callback=self._set_phase_robust  # Report smooth retraction stages
                        )
                        
                        if retraction_result['success']:
                            if self.smoother_retraction_enabled:
                                self.update_status_message(f"SUCCESS L{current_layer_num_for_display}: Return completed in {retraction_result['movement_time_s']:.2f}s ({retraction_result['segments_completed']} segments)")
                            else:
                                self.update_status_message(f"SUCCESS L{current_layer_num_for_display}: Return movement completed")
                        else:
                            raise Exception(retraction_result.get('error', 'Unknown retraction error'))
                        
                        # 4a. SANDWICH ROUTINE (FORCE THRESHOLD VERSION)
                        # Only run if pre-calibration was successful (measured_gap_mm is not None)
                        if self.measured_gap_mm is not None:
                            # IMPORTANT: Wait 1 second after retraction to let forces settle
                            self.update_status_message(f"L{current_layer_num_for_display}: Waiting 1s for forces to settle before sandwich...")
                            
                            # Set phase to Sandwich (entire sandwich routine starts here, including settling)
                            self._set_phase_robust("Sandwich")
                            
                            time.sleep(1.0)
                            
                            # Get sandwich parameters
                            actual_sandwich_speed_um_s = self.sandwich_speed_list[i] if i < len(self.sandwich_speed_list) else 500
                            actual_sandwich_touches = 1  # Always 1 touch per layer during printing
                            
                            # ========== PRESSURE-BASED SANDWICH THRESHOLDS ==========
                            # Build platform area (circle with 6.35mm diameter)
                            BUILD_PLATFORM_DIAMETER_MM = 6.35
                            BUILD_PLATFORM_AREA_MM2 = 3.14159 * (BUILD_PLATFORM_DIAMETER_MM / 2.0) ** 2  # π*r² = 31.67mm²
                            
                            # Get current layer's cross-sectional area from PeakForceLogger
                            layer_area_mm2 = BUILD_PLATFORM_AREA_MM2  # Default to build platform area
                            if (hasattr(self, 'sensor_data_window_instance') and 
                                self.sensor_data_window_instance and
                                hasattr(self.sensor_data_window_instance, 'peak_force_logger') and
                                self.sensor_data_window_instance.peak_force_logger and
                                hasattr(self.sensor_data_window_instance.peak_force_logger, 'current_cross_sectional_area_mm2') and
                                self.sensor_data_window_instance.peak_force_logger.current_cross_sectional_area_mm2 is not None):
                                layer_area_mm2 = self.sensor_data_window_instance.peak_force_logger.current_cross_sectional_area_mm2
                            
                            # Get target pressure from precalibration (stored in Pa)
                            target_pressure_pa = self.precal_target_pressure_pa if hasattr(self, 'precal_target_pressure_pa') else 15790
                            target_pressure_mpa = target_pressure_pa / 1000000.0  # Convert Pa to MPa (N/mm²)
                            
                            # Calculate force threshold based on current layer area and target pressure
                            contact_force_threshold = -(target_pressure_mpa * layer_area_mm2)  # Negative for compression
                            
                            measured_gap = self.measured_gap_mm
                            
                            self.update_status_message(f"L{current_layer_num_for_display}: Starting sandwich (Gap:{measured_gap:.3f}mm)")
                            self.update_status_message(f"L{current_layer_num_for_display}: Pressure mode: {target_pressure_mpa:.6f}MPa × {layer_area_mm2:.2f}mm² = {abs(contact_force_threshold):.3f}N")
                            self.update_status_message(f"L{current_layer_num_for_display}: Speed: {actual_sandwich_speed_um_s}µm/s")
                            
                            # Phase already set to Sandwich during settling period above
                            
                            # Calculate sandwich target position (where we want to end up after sandwich)
                            sandwich_target_position_um = z_return_pos
                            sandwich_target_position_mm = sandwich_target_position_um / 1000.0
                            
                            # Run sandwich routine with simple force threshold
                            try:
                                if not (hasattr(self, 'sensor_data_window_instance') and 
                                       self.sensor_data_window_instance and 
                                       hasattr(self.sensor_data_window_instance, 'force_gauge_manager') and
                                       self.sensor_data_window_instance.force_gauge_manager and
                                       self.sensor_data_window_instance.is_force_gauge_calibrated_internally()):
                                    self.update_status_message(f"L{current_layer_num_for_display}: Sandwich skipped - force gauge not calibrated", error=True)
                                else:
                                    force_gauge = self.sensor_data_window_instance.force_gauge_manager
                                    
                                    # Get current position and calculate waypoints
                                    current_pos_um = self.axis.get_position(Units.LENGTH_MICROMETRES)
                                    # Target is the layer position itself - never go past it
                                    target_glass_um = sandwich_target_position_um
                                    gap_um = measured_gap * 1000.0
                                    
                                    # Get pause time from this layer
                                    actual_pause = self.pause_list[i] if i < len(self.pause_list) else 0.0
                                    
                                    # ========== CHOOSE SANDWICH ROUTINE TYPE ==========
                                    if self.enable_scaled_force_sandwich.get():
                                        # === LINEAR AREA-SCALED FORCE SANDWICH WITH BIDIRECTIONAL CORRECTION ===
                                        self.update_status_message(f"L{current_layer_num_for_display}: Using LINEAR AREA-SCALED sandwich with bidirectional correction")
                                        
                                        # Initialize sandwich manager on first use
                                        if self.sandwich_manager is None:
                                            self.sandwich_manager = SandwichRoutineManager(
                                                self.axis, force_gauge, self.update_status_message,
                                                set_phase_callback=self._set_phase_robust
                                            )
                                            # Configure parameters from UI/settings
                                            self.sandwich_manager.max_area = self.scaled_force_max_area
                                            self.sandwich_manager.calibration_force = self.scaled_force_calibration_force
                                            self.sandwich_manager.safety_limit = self.scaled_force_safety_limit
                                            self.sandwich_manager.base_flatness_threshold = self.scaled_force_base_flatness_threshold
                                            self.sandwich_manager.max_iterations = self.scaled_force_max_iterations
                                            
                                            # ===== SMOOTH SANDWICH MODE (DISABLED) =====
                                            # Set to True to skip tiered ramping and use smooth acceleration
                                            # This eliminates force spikes from direction changes
                                            self.sandwich_manager.use_smooth_sandwich = False  # ← CHANGE TO True FOR SMOOTH MODE
                                            self.sandwich_manager.smooth_liftoff_accel_mm_s2 = 1.0  # Gentle 1mm/s² liftoff
                                            self.sandwich_manager.smooth_pause_at_contact_s = 0.5   # 0.5s pause before liftoff
                                        
                                        # Set speeds from current sandwich speed (divide by 4 for linear scaled)
                                        self.sandwich_manager.set_speeds_from_base(actual_sandwich_speed_um_s, speed_division=4.0)
                                        
                                        # Get force at max area from UI
                                        try:
                                            self.sandwich_manager.force_at_max_area = float(self.t_max_area_force.get())
                                        except:
                                            self.sandwich_manager.force_at_max_area = -2.0
                                            self.update_status_message(f"L{current_layer_num_for_display}: Invalid max area force, using -2.0N", error=True)
                                        
                                        # Pause PeakForceLogger to avoid recording sandwich movements as separate layers
                                        if hasattr(self, 'automated_peak_force_logger') and self.automated_peak_force_logger:
                                            self.automated_peak_force_logger.pause_monitoring()
                                        
                                        # Calculate area directly from current layer image
                                        current_area_mm2 = None
                                        
                                        # Try to calculate from image_list first (always available during print)
                                        if hasattr(self, 'image_list') and i < len(self.image_list):
                                            try:
                                                image_path = self.image_list[i]
                                                img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
                                                
                                                if img is not None:
                                                    # Count white pixels (≥250 threshold)
                                                    white_pixel_count = np.sum(img >= 250)
                                                    
                                                    if white_pixel_count > 0:
                                                        # Calculate area using 7.607µm pixel size (matches PeakForceLogger)
                                                        PIXEL_SIZE_MM = 0.007607  # 7.607µm = 0.007607mm
                                                        PIXEL_AREA_MM2 = PIXEL_SIZE_MM ** 2
                                                        current_area_mm2 = white_pixel_count * PIXEL_AREA_MM2
                                                        self.update_status_message(f"L{current_layer_num_for_display}: Area calculated from image: {current_area_mm2:.2f} mm²")
                                                    else:
                                                        self.update_status_message(f"L{current_layer_num_for_display}: Warning - No white pixels in image", error=True)
                                                else:
                                                    self.update_status_message(f"L{current_layer_num_for_display}: Warning - Could not read image for area calculation", error=True)
                                            except Exception as e:
                                                self.update_status_message(f"L{current_layer_num_for_display}: Error calculating area from image: {e}", error=True)
                                        
                                        # Fallback to img_area_list if image calculation failed
                                        if current_area_mm2 is None:
                                            if hasattr(self, 'img_area_list') and i < len(self.img_area_list):
                                                current_area_mm2 = self.img_area_list[i]
                                                self.update_status_message(f"L{current_layer_num_for_display}: Area from instruction file: {current_area_mm2:.2f} mm²")
                                            else:
                                                current_area_mm2 = 10.0  # Final fallback
                                                self.update_status_message(f"L{current_layer_num_for_display}: Warning - Using default area 10mm²", error=True)
                                        
                                        # Execute sandwich routine using dedicated module
                                        success = self.sandwich_manager.execute_linear_scaled_sandwich(
                                            current_area_mm2=current_area_mm2,
                                            layer_height_um=sandwich_target_position_um,
                                            measured_gap_mm=measured_gap,
                                            layer_display_num=current_layer_num_for_display,
                                            pause_time_s=actual_pause,
                                            stop_flag_callback=lambda: self.flag,
                                            layer_thickness_um=current_thickness_um
                                        )
                                        
                                        # Resume PeakForceLogger after sandwich completes
                                        if hasattr(self, 'automated_peak_force_logger') and self.automated_peak_force_logger:
                                            self.automated_peak_force_logger.resume_monitoring()
                                        
                                        if not success:
                                            # Sandwich was aborted by stop flag
                                            break
                                        
                                        # Note: All old inline sandwich code removed - now handled by LinearScaledSandwich module
                                    
                                    elif self.enable_adaptive_sandwich.get():
                                        # === ADAPTIVE SANDWICH ROUTINE (FORCE-RESPONSIVE) ===
                                        # Execute adaptive sandwich using dedicated module
                                        success = self.sandwich_manager.execute_adaptive_sandwich(
                                            layer_height_um=sandwich_target_position_um,
                                            measured_gap_mm=measured_gap,
                                            contact_force_threshold=contact_force_threshold,
                                            base_sandwich_speed_um_s=actual_sandwich_speed_um_s,
                                            layer_display_num=current_layer_num_for_display,
                                            pause_time_s=actual_pause,
                                            stop_flag_callback=lambda: self.flag
                                        )
                                        
                                        # Resume PeakForceLogger after sandwich completes
                                        if hasattr(self, 'automated_peak_force_logger') and self.automated_peak_force_logger:
                                            self.automated_peak_force_logger.resume_monitoring()
                                        
                                        if not success:
                                            # Sandwich was aborted by stop flag
                                            break
                                    
                                    else:
                                        # === CLASSIC SANDWICH ROUTINE (4-TIER RAMPING) ===
                                        # Execute classic sandwich using dedicated module
                                        success = self.sandwich_manager.execute_classic_sandwich(
                                            layer_height_um=sandwich_target_position_um,
                                            measured_gap_mm=measured_gap,
                                            contact_force_threshold=contact_force_threshold,
                                            base_sandwich_speed_um_s=actual_sandwich_speed_um_s,
                                            layer_display_num=current_layer_num_for_display,
                                            pause_time_s=actual_pause,
                                            stop_flag_callback=lambda: self.flag
                                        )
                                        
                                        if not success:
                                            # Sandwich was aborted by stop flag
                                            break
                                        
                                        # Note: All old inline sandwich code removed - now handled by SandwichRoutines module
                                        
                            except Exception as sandwich_error:
                                self.update_status_message(f"L{current_layer_num_for_display}: Sandwich routine error: {sandwich_error}", error=True)
                                # Don't abort print on sandwich failure (including hard failsafe), just log it and continue
                        else:
                            # Pre-calibration was not run or failed, skip sandwich
                            if i == 0:  # Only log once on first layer
                                self.update_status_message(f"L{current_layer_num_for_display}: Sandwich skipped (pre-calibration not available)")

                        
                    except Exception as return_error:
                        self.update_status_message(f"ERROR L{current_layer_num_for_display}: Return movement failed: {return_error}", error=True)
                        
                        # SAVE LIVE PLOT DATA TO FAILURE LOG
                        try:
                            self.update_status_message(f"SAVING L{current_layer_num_for_display}: Saving live plot data to failure log...", error=True)
                            if self.sensor_data_window_instance and hasattr(self.sensor_data_window_instance, 'position_logger'):
                                failure_log_path = self.sensor_data_window_instance.position_logger.save_failure_log(
                                    layer_num=current_layer_num_for_display,
                                    error_message=str(return_error)
                                )
                                if failure_log_path:
                                    self.update_status_message(f"SAVED L{current_layer_num_for_display}: Failure log saved to {failure_log_path}", error=True)
                                else:
                                    self.update_status_message(f"WARNING L{current_layer_num_for_display}: Could not save failure log (no data available)", error=True)
                            else:
                                self.update_status_message(f"WARNING L{current_layer_num_for_display}: Position logger not available for failure log", error=True)
                        except Exception as save_error:
                            self.update_status_message(f"ERROR L{current_layer_num_for_display}: Failed to save failure log: {save_error}", error=True)
                        
                        # Log detailed diagnostics
                        try:
                            fault_status = self.axis.warnings.get_flags()
                            pos_after_fail = self.axis.get_position(unit=Units.LENGTH_MICROMETRES)
                            force_after_fail = self.force_gauge_manager.get_force() if hasattr(self, 'force_gauge_manager') else 0.0
                            self.update_status_message(f"DIAGNOSTICS L{current_layer_num_for_display}: Fault={fault_status}, Pos={pos_after_fail/1000.0:.4f}mm, Force={force_after_fail:.4f}N", error=True)
                            
                            # RECOVERY ATTEMPT: Re-home stage and return to correct position
                            self.update_status_message(f"RECOVERY L{current_layer_num_for_display}: Re-homing stage to clear fault...", error=True)
                            try:
                                # Re-home the stage to clear fault and re-establish position reference
                                self.axis.home(wait_until_idle=True)
                                self.update_status_message(f"RECOVERY L{current_layer_num_for_display}: Stage re-homed successfully", error=True)
                                
                                # Brief wait for forces to dissipate
                                time.sleep(1.0)
                                
                                # Calculate correct position for this layer
                                # z_return_pos is where we were trying to go
                                target_pos_mm = z_return_pos / 1000.0
                                
                                # Move to target position from home
                                self.update_status_message(f"RECOVERY L{current_layer_num_for_display}: Moving to target position {target_pos_mm:.4f}mm", error=True)
                                self.axis.move_absolute(
                                    position=z_return_pos,
                                    unit=Units.LENGTH_MICROMETRES,
                                    wait_until_idle=True,
                                    velocity=actual_step_speed_um_s,
                                    velocity_unit=Units.VELOCITY_MICROMETRES_PER_SECOND,
                                    acceleration=actual_acceleration_to_set_um_s2,
                                    acceleration_unit=Units.ACCELERATION_MICROMETRES_PER_SECOND_SQUARED
                                )
                                final_pos = self.axis.get_position(unit=Units.LENGTH_MICROMETRES)
                                self.update_status_message(f"RECOVERY L{current_layer_num_for_display}: Successfully recovered, position: {final_pos/1000.0:.4f}mm", error=True)
                                
                                # Recovery successful - don't abort print, continue to next layer
                                continue
                                
                            except Exception as recovery_error:
                                self.update_status_message(f"RECOVERY FAILED L{current_layer_num_for_display}: {recovery_error}", error=True)
                        except:
                            pass
                        
                        # Clean up DLP before aborting
                        self.cleanup_dlp_safe_state()
                        self._cleanup_print_resources()
                        raise  # Re-raise to trigger print abort
                    
                    # 4b. Restore DLP power for next layer (if not last layer)
                    if i < num_layers - 1 and hasattr(self, 'controller'):
                        try:
                            # Get next layer's power setting
                            next_layer_power = int(actual_dlp_power)
                            self.controller.power(current=next_layer_power)
                            self.update_status_message(f"L{current_layer_num_for_display}: DLP power restored to {next_layer_power}")
                        except Exception as e:
                            self.update_status_message(f"L{current_layer_num_for_display}: Could not restore DLP power: {e}", error=True)
                    
                    time.sleep(0.1) # Failsafe delay
                    z_at_previous_exposure_microns = z_return_pos
                
                # --- COMMON POST-LAYER OPERATIONS ---
                # Call update_auto_logger if EITHER layer logger OR peak force logger is active
                if self.sensor_data_window_instance and \
                   self.sensor_data_window_instance.sensor_window.winfo_exists():
                    # Check if either logger is active
                    layer_logger_active = (hasattr(self.sensor_data_window_instance, 'automated_layer_logger') and 
                                          self.sensor_data_window_instance.automated_layer_logger and 
                                          self.sensor_data_window_instance.automated_layer_logger.is_configured_for_run)
                    peak_logger_active = (hasattr(self.sensor_data_window_instance, 'automated_peak_force_logger') and 
                                         self.sensor_data_window_instance.automated_peak_force_logger)
                    
                    if layer_logger_active or peak_logger_active:
                        # Get image path for cross-sectional area calculation
                        current_image_path = self.image_list[i] if i < len(self.image_list) else None
                        
                        # Pass actual peel positions for PeakForceLogger (convert from microns to mm)
                        # These were calculated earlier in the loop
                        peel_peak_mm = z_peel_peak / 1000.0 if 'z_peel_peak' in locals() else None
                        return_pos_mm = z_return_pos / 1000.0 if 'z_return_pos' in locals() else None
                        
                        # Corrected method name below
                        self.sensor_data_window_instance.update_auto_logger_current_layer(
                            current_layer_num_for_display,
                            z_at_previous_exposure_microns / 1000.0,
                            image_path=current_image_path,
                            z_peel_peak_mm=peel_peak_mm,
                            z_return_pos_mm=return_pos_mm
                        )

                if print_mode == "stepped" and actual_layer_pause_s > 0:
                    # Set phase to Pause (layer pause period before next exposure)
                    self._set_phase_robust("Pause")
                    
                    time.sleep(actual_layer_pause_s)
                                
                progress_val = (i + 1) * 100 / num_layers 
                self.win.after(0, lambda p=progress_val, nl=num_layers, ci=i: self._update_gui_progress(p, nl, ci))

            # --- END OF LOOP ---
            if not self.flag: 
                 self.update_status_message("Print completed successfully.")
                 # Ensure black image is shown at the very end, especially if continuous mode was active
                 cv2.imshow(self.window_name, self.black_image)
                 cv2.waitKey(1) # Allow OpenCV to process the final black image
            
            winsound.Beep(440, 1000) 

        except Exception as e:
            self.update_status_message(f"CRITICAL Error during print: {e}", error=True)
            traceback.print_exc()
        finally:
            self.update_status_message("Print finalization sequence started...")
            # DLP Cleanup
            if hasattr(self, 'controller'):
                try:
                    self.controller.stopsequence()
                    self.controller.power(current=0) # Turn off LED
                    self.controller.changemode(3)   # Set back to HDMI/video input mode
                    # self.controller.hdmi()        # Optionally ensure HDMI input is active
                    self.update_status_message("DLP sequence stopped, LEDs off, and mode set to HDMI.")
                except Exception as dlp_e:
                    self.update_status_message(f"Error during DLP cleanup: {dlp_e}", error=True)
            
            # OpenCV window cleanup
            if hasattr(self, 'window_name') and self.window_name: # Check if window_name is not None
                try:
                    if hasattr(self, 'black_image'):
                        cv2.imshow(self.window_name, self.black_image)
                        cv2.waitKey(1)
                    cv2.destroyWindow(self.window_name)
                    cv2.waitKey(1)  # Pump events so Windows properly destroys the window
                    self.update_status_message("OpenCV window closed.")
                except cv2.error as cv_err:
                    # Handle cases where the window might already be destroyed or was never properly created
                    if "NULL window" not in str(cv_err) and "Invalid window name" not in str(cv_err):
                         self.update_status_message(f"Error closing OpenCV window: {cv_err}", error=True)
                    else:
                         self.update_status_message("OpenCV window was likely already closed or not fully initialized.")


            # Zaber stage movement
            if hasattr(self, 'axis') and self.axis:
                try:
                    offset_val_mm = float(self.offset) 
                    self.axis.move_relative(offset_val_mm, Units.LENGTH_MILLIMETRES, wait_until_idle=True)
                    self.get_position() # Call get_position to update t4
                    self.update_status_message(f"Moved Z by offset: {offset_val_mm}mm. Current Z: {self.t4.get()} mm")
                except Exception as zaber_e:
                    self.update_status_message(f"Error moving Zaber by offset: {zaber_e}", error=True) 

            # Save auto-log data via SensorDataWindow
            if self.sensor_data_window_instance and \
               self.sensor_data_window_instance.sensor_window.winfo_exists() and \
               hasattr(self.sensor_data_window_instance, 'automated_layer_logger') and \
               self.sensor_data_window_instance.automated_layer_logger and \
               self.sensor_data_window_instance.automated_layer_logger.is_configured_for_run:
                self.sensor_data_window_instance.stop_and_save_automated_logs()

            # Write print status and save instruction file
            if hasattr(self, 'current_print_session_log_dir') and self.current_print_session_log_dir:
                # Determine print status
                if self.flag:  # If flag is True, it means the print was stopped/aborted
                    status_to_write = "stopped"
                elif not self.flag:  # If flag is still false, it means it completed normally
                    status_to_write = "completed"
                
                # Finalize experimental conditions tracking
                if self.exp_conditions_window:
                    try:
                        success = (status_to_write == "completed")
                        self.exp_conditions_window.end_print(success=success)
                        self.update_status_message(f"Experimental conditions finalized: {status_to_write}")
                    except Exception as exp_err:
                        self.update_status_message(f"Error finalizing experimental conditions: {exp_err}", error=True)

                # Save print status file (use updated directory path after folder rename)
                status_dir = self.current_print_session_log_dir
                if (hasattr(self, 'exp_conditions_window') and self.exp_conditions_window and 
                    hasattr(self.exp_conditions_window, 'current_print_dir') and 
                    self.exp_conditions_window.current_print_dir):
                    status_dir = self.exp_conditions_window.current_print_dir
                
                status_file_path = os.path.join(status_dir, "print_status.txt")
                try:
                    with open(status_file_path, 'w') as sf:
                        sf.write(status_to_write)
                    self.update_status_message(f"Print status '{status_to_write}' written to {status_file_path}")
                except Exception as e_stat:
                    self.update_status_message(f"Error writing final print status: {e_stat}")

                # Save instruction file if work of adhesion or automated logging were enabled
                try:
                    should_save_instruction_file = False
                    
                    # Check if work of adhesion recording was enabled
                    if (hasattr(self, 'sensor_data_window_instance') and self.sensor_data_window_instance and 
                        hasattr(self.sensor_data_window_instance, 'record_work_var') and 
                        self.sensor_data_window_instance.record_work_var.get()):
                        should_save_instruction_file = True
                    
                    # Check if automated logging was enabled
                    if (hasattr(self, 'sensor_data_window_instance') and self.sensor_data_window_instance and
                        hasattr(self.sensor_data_window_instance, 'auto_log_enabled_var') and
                        self.sensor_data_window_instance.auto_log_enabled_var.get()):
                        should_save_instruction_file = True
                    
                    if should_save_instruction_file and hasattr(self, 'active_instruction_file_path') and self.active_instruction_file_path:
                        if os.path.exists(self.active_instruction_file_path):
                            # Get updated directory path from ExperimentalConditionsWindow after folder rename
                            target_dir = self.current_print_session_log_dir
                            if (hasattr(self, 'exp_conditions_window') and self.exp_conditions_window and 
                                hasattr(self.exp_conditions_window, 'current_print_dir') and 
                                self.exp_conditions_window.current_print_dir):
                                target_dir = str(self.exp_conditions_window.current_print_dir)
                            
                            instruction_filename = os.path.basename(self.active_instruction_file_path)
                            saved_instruction_path = os.path.join(target_dir, instruction_filename)
                            shutil.copy2(self.active_instruction_file_path, saved_instruction_path)
                            self.update_status_message(f"Instruction file saved: {instruction_filename}")
                        else:
                            self.update_status_message("Warning: Active instruction file not found, could not save copy.")
                    
                except Exception as e_instr:
                    self.update_status_message(f"Error saving instruction file: {e_instr}")
            
            # Trigger post-print analysis and plot generation
            self._trigger_post_print_analysis()
            
            self.update_status_message("Print thread finished.")

            # Clean up resources
            self._cleanup_print_resources()
            if hasattr(self, 'b1'): self.b1.config(state=NORMAL)
            if hasattr(self, 'b10'): self.b10.config(state=NORMAL)
            if hasattr(self, 'b4'): self.b4.config(state=DISABLED)
            self.print_thread = None

    def set_home(self):
        """Set the position value in the Z axis position box as the new reference (home) for printing."""
        try:
            self.reference = float(self.t4.get())
            self.update_status_message(f"Print Home Set to {self.reference} mm (Absolute)")
        except Exception as e:
            self.update_status_message(f"Error setting home: {e}", error=True)

    def get_position(self):
        """Display current absolute Z-axis position from the hardware."""
        try:
            self.t4.delete(0, 'end')
            absolute_position = self.axis.get_position(unit=Units.LENGTH_MILLIMETRES)
            self.t4.insert(END, str(absolute_position))
        except Exception as e:
            self.update_status_message(f"Error getting position: {e}", error=True)

    def goto_position(self):
        """Move exactly to the absolute position specified in t4."""
        try:
            target_abs_pos = float(self.t4.get())
            self.axis.move_absolute(position=target_abs_pos, unit=Units.LENGTH_MILLIMETRES,
                                    wait_until_idle=False)
        except MovementFailedException:
            # Move went out of range - return to absolute hardware zero and stop
            self.update_status_message("Position out of range! Returning to hardware physical zero...")
            try:
                self.axis.move_absolute(position=0, unit=Units.LENGTH_MILLIMETRES, wait_until_idle=True)
                self.update_status_message("Returned to hardware physical zero")
                self.get_position()
            except Exception as e:
                self.update_status_message(f"Error returning to zero: {e}", error=True)
        except Exception as e:
            self.update_status_message(f"Move error: {e}", error=True)

    def stop(self):
        self.update_status_message("Stop signal received...")
        self.flag = True
        self.pause_flag = False
        if hasattr(self, 'controller'):
            try:
                # Use standardized DLP cleanup
                self.cleanup_dlp_safe_state()
            except Exception as e:
                self.update_status_message(f"Error stopping DLP sequence: {e}")

    def initilze_stage(self):
        """Initializes the stage and resets DLP to a known idle state."""
        self.update_status_message("Initializing stage and DLP for print...")
        if hasattr(self, 'controller'):
            try:
                self.controller.stopsequence()  # Stop any previous sequence
                self.controller.power(current=0)    # Ensure LED is off BEFORE mode change
                time.sleep(0.1)  # Wait for power to be off before changing mode
                self.controller.changemode(3)   # Set to HDMI/video input mode
                self.controller.hdmi()          # Activate HDMI input
                time.sleep(0.5) # Short pause for mode change to settle
                self.update_status_message("DLP reset to HDMI mode.")
            except Exception as e:
                self.update_status_message(f"Error initializing DLP: {e}", error=True)
                # Optionally, decide if this is a fatal error for starting a print
                # return False 
        # Any Zaber stage specific initialization can also go here if needed
        # For now, it mainly focuses on DLP reset.
        return True # Indicate success or readiness

    def input_directory(self):
        path = str(self.t1.get())
        print(f"DEBUG: MyWindow.input_directory called with path: '{path}'") # Add this
        
        # Determine the expected instruction file name based on the directory name
        # This logic should match what application.set_image_directory expects
        expected_instruction_filename = os.path.basename(os.path.normpath(path)) + ".txt"
        potential_instruction_file_path = os.path.join(path, expected_instruction_filename)

        try:
            # UPDATED UNPACKING: New sandwich parameter format
            (
                self.image_list, 
                self.exposure_time,  # Corresponds to exposure_time_list
                self.thickness,      # Corresponds to thickness_list
                self.step_speed_list,
                self.overstep_distance_list,
                self.step_type_list,  # This will hold the 'Acceleration' values from the file
                self.pause_list,
                self.intensity_list,
                self.sandwich_speed_list  # Only sandwich parameter from instruction file
            ) = self.application.set_image_directory(path)

            # If set_image_directory was successful and found the file, update active_instruction_file_path
            if os.path.exists(potential_instruction_file_path):
                self.active_instruction_file_path = potential_instruction_file_path
                self.update_status_message(f"Active instruction file set to: {self.active_instruction_file_path}")
            else:
                # This case should ideally be handled by set_image_directory raising FileNotFoundError
                # but as a fallback:
                self.active_instruction_file_path = None
                self.update_status_message(f"Warning: Instruction file {expected_instruction_filename} not found in {path} after successful image list load.", warning=True)

            if not self.image_list:
                self.update_status_message("No image data loaded from instruction file.")
                messagebox.showwarning("File Info", f"No image data was loaded from the instruction file in:\n{path}")
            else:
                self.update_status_message(f"Loaded {len(self.image_list)} layers from instruction file.")

        except ValueError as e:
            self.update_status_message(f"Error processing instruction file: {e}. Check file format and content.")
            messagebox.showerror("File Error", f"Could not process the instruction file in '{path}'.\nDetails: {e}\nEnsure it matches the expected format (9 columns, tab-separated) and numeric values are correct.")
            # Clear lists to prevent using old/corrupted data
            self.image_list = []
            self.exposure_time = []
            self.thickness = []
            self.step_speed_list = []
            self.overstep_distance_list = []
            self.step_type_list = []
            self.pause_list = []
            self.intensity_list = []
            self.sandwich_speed_list = []
        except FileNotFoundError:
            self.update_status_message(f"Instruction file not found in '{path}'.")
            messagebox.showerror("File Not Found", f"The instruction file (e.g., foldername.txt) was not found in the specified directory:\n{path}")
        except Exception as e:
            self.update_status_message(f"An unexpected error occurred reading directory: {e}")
            messagebox.showerror("Directory Error", f"An unexpected error occurred:\n{e}")
            traceback.print_exc()

    def moveup(self):
        """Move stage upward by distance in t9. If out of range, move to zero and stop."""
        try:
            current_pos = self.axis.get_position(unit=Units.LENGTH_MILLIMETRES)
            move_distance = float(self.t9.get()) * -1  # Negative for up
            target_pos = current_pos + move_distance
            
            # Attempt the move
            self.axis.move_relative(position=move_distance, unit=Units.LENGTH_MILLIMETRES,
                                    wait_until_idle=False, velocity=10,
                                    velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND)
        except MovementFailedException:
            # Move went out of range - return to zero and stop
            self.update_status_message("Move out of range! Returning to zero (home)...")
            try:
                self.axis.move_absolute(position=0, unit=Units.LENGTH_MILLIMETRES, wait_until_idle=True)
                self.update_status_message("Returned to home position (zero)")
                self.get_position()
            except Exception as e:
                self.update_status_message(f"Error returning to home: {e}", error=True)
        except Exception as e:
            self.update_status_message(f"Move error: {e}", error=True)

    def movedown(self):
        """Move stage downward by distance in t9. If out of range, move to zero and stop."""
        try:
            current_pos = self.axis.get_position(unit=Units.LENGTH_MILLIMETRES)
            move_distance = float(self.t9.get())  # Positive for down
            target_pos = current_pos + move_distance
            
            # Attempt the move
            self.axis.move_relative(position=move_distance, unit=Units.LENGTH_MILLIMETRES,
                                    wait_until_idle=False, velocity=5,
                                    velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND)
        except MovementFailedException:
            # Move went out of range - return to zero and stop
            self.update_status_message("Move out of range! Returning to zero (home)...")
            try:
                self.axis.move_absolute(position=0, unit=Units.LENGTH_MILLIMETRES, wait_until_idle=True)
                self.update_status_message("Returned to home position (zero)")
                self.get_position()
            except Exception as e:
                self.update_status_message(f"Error returning to home: {e}", error=True)
        except Exception as e:
            self.update_status_message(f"Move error: {e}", error=True)

    def simple_txt(self):
        path = str(self.t1.get())
        thickness = str(self.t10.get())
        base = str(self.t11_2.get())
        time_val = str(self.t11.get())
        intensity = str(self.t14.get())
        step_speed = str(self.t16.get())
        overstep_distance = str(self.t19.get())
        acceleration_val = str(self.t21.get())
        pause = str(self.t17.get())
        sandwich_speed = str(self.t_sandwich_speed.get())
        
        self.application.generate_instructions(
            path=path, 
            thickness=thickness, 
            base=base, 
            time=time_val, 
            intensity=intensity, 
            step_speed=step_speed, 
            overstep_distance=overstep_distance, 
            step_type=acceleration_val, 
            pause=pause,
            sandwich_speed=sandwich_speed
        )
        
        # Automatically load the generated instruction file
        self.input_directory()
    
    def _on_sandwich_mode_change(self):
        """Ensure only one sandwich mode is selected at a time."""
        # Determine which checkbox was just clicked by checking current states
        # If both are True, we need to disable the one that wasn't just clicked
        if self.enable_adaptive_sandwich.get() and self.enable_scaled_force_sandwich.get():
            # Both are checked - disable scaled force (adaptive was clicked last)
            self.enable_scaled_force_sandwich.set(False)
        
        # Normal mutual exclusion
        if self.enable_adaptive_sandwich.get():
            self.enable_scaled_force_sandwich.set(False)
        elif self.enable_scaled_force_sandwich.get():
            self.enable_adaptive_sandwich.set(False)
    
    def log(self, message, level=None, error=False, category=""):
        """
        Enhanced logging with verbosity control.
        
        Args:
            message: Message to log
            level: Log level (LOG_MINIMAL, LOG_NORMAL, LOG_DETAILED, LOG_DEBUG)
                   If None, defaults to LOG_NORMAL for regular messages, LOG_MINIMAL for errors
            error: Whether this is an error message
            category: Optional category prefix (e.g., "SANDWICH", "FORCE", "POSITION")
        """
        # Default level
        if level is None:
            level = self.LOG_MINIMAL if error else self.LOG_NORMAL
        
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        
        # Build message with optional category
        if category:
            full_message = f"[{category}] {message}"
        else:
            full_message = message
        
        log_message = f"[{timestamp}] {full_message}"
        
        # Terminal output (based on terminal_verbosity)
        if level <= self.terminal_verbosity:
            if error:
                print(f"ERROR: {log_message}")
            else:
                print(f"Status Update: {log_message}")
        
        # GUI text area (based on terminal_verbosity)
        if level <= self.terminal_verbosity:
            if hasattr(self, 'status_text_area') and self.status_text_area:
                try:
                    if self.status_text_area.winfo_exists():
                        self.status_text_area.insert(END, log_message + "\n")
                        self.status_text_area.see(END)
                except TclError:
                    pass
        
        # Update status label for NORMAL or higher priority messages
        if level <= self.LOG_NORMAL:
            try:
                if self.win.winfo_exists():
                    self.status_message_var.set(full_message)
            except TclError:
                pass
        
        # Session log file (mirrors terminal)
        if self.session_log_file and level <= self.terminal_verbosity:
            try:
                with open(self.session_log_file, 'a', encoding='utf-8') as f:
                    prefix = "ERROR: " if error else "Status: "
                    f.write(f"{prefix}{log_message}\n")
            except Exception as e:
                print(f"Warning: Could not write to session log: {e}")
        
        # Detailed log file (includes everything up to file_verbosity)
        if self.detailed_log_file and level <= self.file_verbosity:
            try:
                with open(self.detailed_log_file, 'a', encoding='utf-8') as f:
                    level_names = {0: "MIN", 1: "INFO", 2: "DETAIL", 3: "DEBUG"}
                    level_str = level_names.get(level, "INFO")
                    prefix = "ERROR" if error else level_str
                    f.write(f"[{prefix}] {log_message}\n")
            except Exception as e:
                print(f"Warning: Could not write to detailed log: {e}")
    
    def update_status_message(self, message, error=False):
        """Updates the status message label and logs to console and file.
        
        This method is kept for backward compatibility. 
        New code should use self.log() with appropriate verbosity levels.
        """
        # Route through new logging system at NORMAL level
        self.log(message, level=self.LOG_NORMAL, error=error)

    def update_auto_home_button_state(self):
        if (self.sensor_data_window_instance and
            self.sensor_data_window_instance.sensor_window.winfo_exists() and
            self.sensor_data_window_instance.is_force_gauge_calibrated_internally()):
            self.b_auto_home.config(state=NORMAL)
        else:
            self.b_auto_home.config(state=DISABLED)

    def open_sensor_panel(self):
        if self.sensor_data_window_instance is None or not self.sensor_data_window_instance.sensor_window.winfo_exists():
            if hasattr(self, 'axis') and self.axis:
                # Pass 'self' (MyWindow instance) to SensorDataWindow
                self.sensor_data_window_instance = SensorDataWindow(self.win, self.axis, self.update_status_message, self)
                self.update_auto_home_button_state()
            else:
                # self.t8.delete(0, 'end') # self.t8 is a Label
                # self.t8.insert(END, "Error: Zaber axis not initialized. Cannot open sensor panel.")
                self.update_status_message("Error: Zaber axis not initialized. Cannot open sensor panel.", error=True)
        else:
            self.sensor_data_window_instance.sensor_window.lift()
            self.update_auto_home_button_state()
    
    def open_exp_conditions_window(self):
        """Open or show the experimental conditions window."""
        if self.exp_conditions_window is None:
            self.exp_conditions_window = ExperimentalConditionsWindow(self.win, self.update_status_message)
            self.exp_conditions_window.prince_main_app_ref = self
            self.exp_conditions_window.show_window()
            self.update_status_message("Experimental conditions window opened")
        else:
            self.exp_conditions_window.show_window()

    def open_image_modification_window(self):
        """Open or show the Image Modification window."""
        if (self.image_modification_window is None or
                not (hasattr(self.image_modification_window, 'window') and
                     self.image_modification_window.window.winfo_exists())):
            self.image_modification_window = ImageModificationWindow(
                self.win, self.update_status_message, self)
            self.update_status_message("Image Modification window opened")
        else:
            self.image_modification_window.window.lift()

    def start_auto_home_sequence(self):
        if self.auto_home_thread and self.auto_home_thread.is_alive():
            self.update_status_message("Auto-Home is already in progress.")
            return

        try:
            initial_guess = float(self.t_auto_home_guess.get())
            contact_threshold_abs = float(self.t_contact_threshold_abs.get())
            contact_threshold_delta = float(self.t_contact_threshold_delta.get())
        except ValueError:
            self.update_status_message("Invalid input for Auto-Home parameters.")
            messagebox.showerror("Input Error", "Auto-Home parameters must be numbers.")
            return

        if not (self.sensor_data_window_instance and self.sensor_data_window_instance.force_gauge_manager):
            self.update_status_message("Sensor panel or force gauge manager not available.")
            return
        
        if not self.sensor_data_window_instance.is_force_gauge_calibrated_internally():
            self.update_status_message("Force gauge is not calibrated. Please calibrate from Sensor Panel.")
            messagebox.showwarning("Calibration Needed", "Force gauge must be calibrated before Auto-Home.")
            return

        self.update_status_message("Starting Auto-Home...")
        self.b_auto_home.config(state=DISABLED)

        self.auto_home_thread = AutoHomer(
            zaber_axis=self.axis,
            force_gauge_manager=self.sensor_data_window_instance.force_gauge_manager,
            initial_guess=initial_guess,
            contact_threshold_absolute=contact_threshold_abs,
            contact_threshold_delta=contact_threshold_delta,
            status_callback=self.update_status_message,
            result_callback=self.handle_auto_home_result,
            parent_gui=self.win
        )
        self.auto_home_thread.start()

    def handle_auto_home_result(self, new_home_position, message):
        self.update_status_message(message)
        if new_home_position is not None:
            self.reference = new_home_position
            self.t4.delete(0, 'end')
            self.t4.insert(END, f"{new_home_position:.4f}")
            self.update_status_message(f"New Home set to: {new_home_position:.4f} mm")
            messagebox.showinfo("Auto-Home Complete", f"New home position set to: {new_home_position:.4f} mm")
        else:
            messagebox.showerror("Auto-Home Failed", message)
        
        self.update_auto_home_button_state()

    def start_sandwich_routine(self):
        """Manual sandwich test - removed (use pre-calibration + printing instead)."""
        self.update_status_message("Manual sandwich test removed. Use 'Enable Sandwich Routine' checkbox during printing.")
        messagebox.showinfo("Feature Removed", "Manual sandwich testing has been removed.\n\nTo test sandwich functionality:\n1. Check 'Enable Sandwich Routine'\n2. Start a print\n3. Pre-calibration will run automatically")

    def handle_sandwich_result(self, success, message):
        """Handle the result of the sandwich routine."""
        self.update_status_message(message)
        if success:
            glass_gap = self.sandwich_thread.actual_glass_gap if self.sandwich_thread else None
            if glass_gap is not None:
                result_msg = f"Sandwich complete! Actual glass gap: {glass_gap:.3f} mm"
                self.update_status_message(result_msg)
                messagebox.showinfo("Sandwich Complete", result_msg)
            else:
                messagebox.showinfo("Sandwich Complete", message)
        else:
            messagebox.showerror("Sandwich Failed", message)
        
        self.update_auto_home_button_state()  # Re-enable button


    def on_closing(self):
        if self.auto_home_thread and self.auto_home_thread.is_alive():
            self.update_status_message("Attempting to stop Auto-Home routine...")
            self.auto_home_thread.stop()
            self.auto_home_thread.join(timeout=2.0)
            if self.auto_home_thread.is_alive():
                print("Warning: Auto-Home thread did not terminate cleanly.")

        if self.sandwich_thread and self.sandwich_thread.is_alive():
            self.update_status_message("Attempting to stop Sandwich routine...")
            self.sandwich_thread.stop()
            self.sandwich_thread.join(timeout=2.0)
            if self.sandwich_thread.is_alive():
                print("Warning: Sandwich thread did not terminate cleanly.")

        if self.sensor_data_window_instance and self.sensor_data_window_instance.sensor_window.winfo_exists():
            self.sensor_data_window_instance.on_sensor_window_close()

        if hasattr(self, 'axis') and self.axis:
            try:
                self.axis.stop()
                if hasattr(self.axis, 'device') and hasattr(self.axis.device, 'connection'):
                    self.axis.device.connection.close()
                else:
                    print("Note: Could not determine Zaber connection object directly from axis for closing.")
            except Exception as e:
                print(f"Error stopping/closing Zaber connection: {e}")
        
        if hasattr(self, 'controller'):
            try:
                self.controller.stopsequence()
                self.controller.standby()
            except Exception as e:
                print(f"Error shutting down DLP: {e}")

        self.win.destroy()

    def _trigger_post_print_analysis(self):
        """
        Trigger automated post-print analysis and plot generation.
        This runs whether the print completed successfully or was stopped early.
        """
        self.session_manager.trigger_post_print_analysis()

    def move_with_retries(self, position_mm, retries=3):
        """
        Attempt to move the stage to the specified position with a fixed number of retries.
        Logs detailed diagnostic information in case of failures.
        """
        for attempt in range(1, retries + 1):
            try:
                self.update_status_message(f"Attempting to move stage to {position_mm} mm (Attempt {attempt}/{retries}).")
                self.axis.move_absolute(position_mm, Units.LENGTH_MILLIMETRES)
                self.update_status_message(f"Stage moved to {position_mm} mm successfully.")
                return  # Exit if movement is successful
            except MovementFailedException as e:
                self.update_status_message(f"Attempt {attempt} failed: {e}", error=True)
                self.update_status_message(f"Diagnostic: Current stage position: {self.axis.get_position(Units.LENGTH_MILLIMETRES)} mm.")
                if attempt < retries:
                    self.update_status_message("Retrying movement...")
                    time.sleep(2)  # Wait before retrying
                else:
                    self.update_status_message(f"Critical: Failed to move to {position_mm} mm after {retries} attempts.", error=True)
                    raise  # Re-raise the exception after exhausting retries
            except Exception as e:
                self.update_status_message(f"Unexpected error during movement: {e}", error=True)
                raise

    def save_fault_data(self, attempted_position_mm):
        """
        Save fault data to a CSV file, including the current stage position,
        the attempted position, and a timestamp.
        """
        try:
            current_position_mm = self.axis.get_position(Units.LENGTH_MILLIMETRES)
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            fault_data = [timestamp, current_position_mm, attempted_position_mm]

            # Ensure the fault log file exists
            fault_log_file = "fault_log.csv"
            file_exists = os.path.isfile(fault_log_file)

            with open(fault_log_file, mode="a", newline="") as file:
                writer = csv.writer(file)
                if not file_exists:
                    # Write header if the file is new
                    writer.writerow(["Timestamp", "Current Position (mm)", "Attempted Position (mm)"])
                writer.writerow(fault_data)

            self.update_status_message(f"Fault data saved: {fault_data}")
        except Exception as e:
            self.update_status_message(f"Error saving fault data: {e}", error=True)

if __name__ == '__main__':
    Library.enable_device_db_store()
    window = Tk()
    mywin = MyWindow(window)
    window.title('Prince - Main Window')
    window.geometry("1200x800+10+10")
    window.protocol("WM_DELETE_WINDOW", mywin.on_closing)
    window.mainloop()