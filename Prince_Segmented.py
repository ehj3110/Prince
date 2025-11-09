from tkinter import *
from tkinter.ttk import *
import cv2
import numpy as np
import time
import screeninfo
import sys
import os
import winsound
import usb.core

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
from SandwichRoutine import SandwichRoutine, perform_sandwich_step_blocking


class MyWindow:
    def __init__(self, win):
        instruction = '''
Check List:\n
1. Ensure DLP is in pattern on the fly. \n
2. Check that DLP is not on standby and is plugged in. \n
1. Close DLP Lightcrafter GUI.\n
2. Make sure the Zaber GUI is closed.\n
3. Do not open any window on the second screen!!!!!\n
6. Delete any file in your sliced file that is not the slices\n 
or the .txt file! Chitubox makes extra files.\n

'''
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

        # Ensure self.p1 (ttk.Progressbar) is initialized - THIS WILL BE OUR MAIN PROGRESS BAR
        self.p1 = Progressbar(win, orient=HORIZONTAL, length=400, mode='determinate') # Increased length a bit
        # Move p1 to the old progress bar's position
        self.p1.place(x=50, y=430) # Old y was 430

        # Ensure self.current_layer_num_var (StringVar for layer display) is initialized
        self.current_layer_num_var = StringVar()
        self.current_layer_num_var.set("Layer: 0/0")
        self.lbl_current_layer = Label(win, textvariable=self.current_layer_num_var, font='Helvetica 10') # Added font
        # Move lbl_current_layer to where the old "Printing Progress" label was, or similarly above p1
        self.lbl_current_layer.place(x=50, y=400) # Old lbl7 y was 400

        self.win = win
        self.flag = False
        self.flag2 = False
        self.offset = -20
        self.pause_flag = False # Ensure pause_flag is initialized

        # --- Define status_message_var and related label (t8) EARLY ---
        self.status_message_var = StringVar() 
        self.status_message_var.set("System Initializing...") 

        self.b_open_sensor_window = Button(win, text="Open Sensor Panel", command=self.open_sensor_panel)
        self.b_open_sensor_window.place(x=750, y=200) 
        self.sensor_data_window_instance = None
        self.auto_home_thread = None

        self.cache_clear_layer = 100000
        self.time1 = 1000

        # --- Existing Canvases and Labels (adjust placement if they conflict with new frames) ---
        self.canvas1 = Canvas(win, height=200, width=270, bg="#FFEFD5")
        self.canvas1.place(x=70, y=520) # Original: x=70, y=520
        
        self.canvas2 = Canvas(win, height=200, width=500, bg="#FFEFD5")
        self.canvas2.place(x=370, y=520) # Original: x=370, y=520

        self.lbl0 = Label(win, text='Prince', font='Helvetica 50 bold')
        self.lbl1 = Label(win, text='Directory of Images')
        self.lbl4 = Label(win, text='Z Axis Position')
        self.lbl5 = Label(win, text=instruction, font='Helvetica 8', foreground='purple', justify=LEFT)
        self.lbl6 = Label(win, text=credit, font='Helvetica 7')
        self.lbl7 = Label(win, text='Printing Progress')
        self.lbl8 = Label(win, text='System Message:') # Label for the status message
        # Define self.t8 (the status display Label) here, tied to status_message_var
        self.t8 = Label(win, textvariable=self.status_message_var, width=70, relief="sunken", anchor="w", justify=LEFT)
        self.lbl9 = Label(win, text='Move distance(mm)')
        self.lbl10 = Label(win, text='Layer thickness(um)')
        self.lbl11 = Label(win, text='Exposure time(s)')
        self.lbl11_2 = Label(win, text='Base curing time(s)')
        self.lbl12 = Label(win, text='Stage Control', font='Helvetica 12 bold')
        self.lbl13 = Label(win, text='Print Parameters', font='Helvetica 12 bold')
        self.lbl14 = Label(win, text='LED Current(0-255)')
        self.lbl15 = Label(win, text='Estimate Time: ∞ min') # This label might be updated by old logic, review if needed
        
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
        self.lbl16.place(x=column2_x, y=550)
        self.t16 = Entry(win)
        self.t16.place(x=column2_x, y=570)
        self.t16.insert(END, "1000.0") # Default Step Speed
        
        self.lbl19.place(x=column2_x, y=590)
        self.t19 = Entry(win)
        self.t19.place(x=column2_x, y=610)
        self.t19.insert(END, "500") # Default Overstep in µm
        
        self.lbl17.place(x=column2_x, y=630)
        self.t17 = Entry(win)
        self.t17.place(x=column2_x, y=650)
        self.t17.insert(END, "0.0") # Default Pause
        
        # COLUMN 3: Acceleration only
        column3_x = 700
        self.lbl21.place(x=column3_x, y=550)
        self.t21 = Entry(win)
        self.t21.place(x=column3_x, y=570)
        self.t21.insert(END, "5.0") # Default Acceleration in mm/s²

        # --- Auto-Home Control Box ---
        frame_auto_home_y_start = 720 # Positioned above sandwich controls
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
        frame_sandwich_y_start = 790  # Below the Auto-Home frame (70px gap for auto-home height)
        self.frame_sandwich = LabelFrame(win, text="Sandwich Routine (Glass Contact)", padding=(10, 10))
        self.frame_sandwich.place(x=50, y=frame_sandwich_y_start, width=frame_auto_home_width)

        # Row 0: Pre-calibration parameters
        self.lbl_sandwich_gap = Label(self.frame_sandwich, text='Gap Estimate (mm):')
        self.lbl_sandwich_gap.grid(row=0, column=0, padx=2, pady=2, sticky=W)
        self.t_sandwich_gap = Entry(self.frame_sandwich, width=8)
        self.t_sandwich_gap.grid(row=0, column=1, padx=2, pady=2)
        self.t_sandwich_gap.insert(END, "0.5")  # Default gap estimate for pre-calibration
        
        self.lbl_sandwich_force = Label(self.frame_sandwich, text='Max Force (N):')
        self.lbl_sandwich_force.grid(row=0, column=2, padx=2, pady=2, sticky=W)
        self.t_sandwich_force = Entry(self.frame_sandwich, width=8)
        self.t_sandwich_force.grid(row=0, column=3, padx=2, pady=2)
        self.t_sandwich_force.insert(END, "0.2")  # Default max force for pre-calibration
        
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
        self.chk_sandwich_precalib.grid(row=1, column=0, columnspan=6, padx=2, pady=5, sticky=W)

        self.sandwich_thread = None  # Track sandwich routine thread
        
        # Variables to store pre-calibration results
        self.measured_gap_mm = None  # Measured gap distance from pre-calibration
        self.measured_derivative_threshold = None  # Measured force derivative threshold


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
        self.lbl0.place(x=550, y=50)
        self.lbl1.place(x=50, y=150)
        self.t1.place(x=180, y=150) # t1 is now defined before _check_default_logging_windows_file

        self.lbl4.place(x=50, y=260)
        self.t4.place(x=50, y=280)
        self.lbl5.place(x=710, y=270)
        self.lbl6.place(x=950, y=0)
        # self.t8.place(x=500, y=280) # This line will now work as self.t8 is defined
        self.lbl8.place(x=500, y=260) # "System Message:"
        # Ensure self.t8 is placed AFTER self.lbl8 if that's the visual intention
        self.t8.place(x=500, y=280) # Place the actual status message display
        self.t9.place(x=140, y=580)
        self.lbl9.place(x=140, y=560)
        self.t10.place(x=400, y=570)
        self.lbl10.place(x=400, y=550)
        self.t11.place(x=400, y=610)
        self.lbl11.place(x=400, y=590)
        self.t11_2.place(x=400, y=650)
        self.lbl11_2.place(x=400, y=630)
        self.lbl12.place(x=150, y=500)
        self.lbl13.place(x=410, y=500)
        self.t14.place(x=240, y=280)
        self.lbl14.place(x=240, y=260)
        self.lbl15.place(x=250, y=460) # This label should not overlap now

        # self.lbl_current_layer_display = Label(win, textvariable=self.current_layer_num_var, font='Helvetica 10')
        # self.lbl_current_layer_display.place(x=400, y=400) # This was a duplicate, ensure it's removed or commented

        # self.progress = Progressbar(win, orient=HORIZONTAL, length=500, mode='determinate') # This is already commented out
        # self.progress.place(x=50, y=430) # This is already commented out

        self.b1 = Button(win, text='Run-Cont.', command=self.run_Continuous)
        self.b10 = Button(win, text='Run-Step', command=self.run_Stepped)
        self.b2 = Button(win, text='Set Home', command=self.set_home)
        self.b3 = Button(win, text='Get Position', command=self.get_position)
        self.b4 = Button(win, text='Stop', command=self.stop)
        self.b5 = Button(win, text='Move Down', command=self.movedown)
        self.b6 = Button(win, text='Move Up', command=self.moveup)
        self.b7 = Button(win, text='Simple input txt generator', command=self.simple_txt)

        self.b1.place(x=70, y=200)
        self.b10.place(x=170, y=200)
        self.b2.place(x=50, y=310)
        self.b3.place(x=130, y=310)
        self.b4.place(x=270, y=200)
        self.b5.place(x=100, y=630)
        self.b6.place(x=200, y=630)
        self.b7.place(x=400, y=680)

        # --- Initialize active_logging_windows_filepath AFTER t1 and status_message_var are created ---
        # self.active_logging_windows_filepath = None
        # self._check_default_logging_windows_file() # MOVED HERE, now status_message_var exists

        # --- Controller, Application, Zaber Setup ---
        self.controller = pycrafter9000.dmd()
        self.application = libs.Application()
        self.controller.stopsequence()
        self.controller.changemode(3)
        self.controller.hdmi()

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

    def _update_gui_progress(self, progress_value, total_layers, current_layer_index):
        """Updates the progress bar and layer count display."""
        if hasattr(self, 'p1'):
            self.p1['value'] = progress_value
        
        # current_layer_index is 0-based, display is 1-based
        if hasattr(self, 'current_layer_num_var'):
            self.current_layer_num_var.set(f"Layer: {current_layer_index + 1}/{total_layers}")
        
        # Optional: Update estimated time if you have logic for it
        # if hasattr(self, 'exposure_time') and self.exposure_time and current_layer_index < len(self.exposure_time):
        #     remaining_layers = total_layers - (current_layer_index + 1)
        #     if remaining_layers > 0 and len(self.exposure_time) > 0:
        #         # Simplistic estimate: avg exp time of remaining or last known exp time
        #         avg_remaining_exp = sum(self.exposure_time[current_layer_index:]) / len(self.exposure_time[current_layer_index:]) if len(self.exposure_time[current_layer_index:]) > 0 else self.exposure_time[-1]
        #         estimated_time_remaining_seconds = remaining_layers * avg_remaining_exp # Add pause times too if significant
        #         self.lbl15.config(text=f'Estimate Time: {estimated_time_remaining_seconds / 60:.1f} min')
        #     else:
        #         self.lbl15.config(text='Estimate Time: Done')


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

            # --- Start Debug Prints ---
            val_t14 = self.t14.get()
            print(f"DEBUG: Raw value from t14 (DLP Power): '{val_t14}'")
            dlp_power = int(val_t14)

            val_t16 = self.t16.get()
            print(f"DEBUG: Raw value from t16 (Step Speed): '{val_t16}'")
            step_speed_um_s = float(val_t16) if val_t16 else 1000.0

            val_t17 = self.t17.get()
            print(f"DEBUG: Raw value from t17 (Pause): '{val_t17}'")
            layer_pause_s = float(val_t17) if val_t17 else 0.0

            val_t19 = self.t19.get()
            print(f"DEBUG: Raw value from t19 (Overstep µm): '{val_t19}'")
            overstep_um_gui = float(val_t19) if val_t19 else 0.0

            val_t21 = self.t21.get()
            print(f"DEBUG: Raw value from t21 (Acceleration mm/s²): '{val_t21}'") # UNIT CHANGED in debug
            step_type_val_mms2 = float(val_t21) if val_t21 else 0.0 # Now in mm/s², allow float
            # --- End Debug Prints ---
            
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

            # --- Start Debug Prints ---
            val_t14 = self.t14.get()
            print(f"DEBUG: Raw value from t14 (DLP Power): '{val_t14}'")
            dlp_power = int(val_t14)

            val_t16 = self.t16.get()
            print(f"DEBUG: Raw value from t16 (Step Speed): '{val_t16}'")
            step_speed_um_s = float(val_t16) if val_t16 else 1000.0

            val_t17 = self.t17.get()
            print(f"DEBUG: Raw value from t17 (Pause): '{val_t17}'")
            layer_pause_s = float(val_t17) if val_t17 else 0.0

            val_t19 = self.t19.get()
            print(f"DEBUG: Raw value from t19 (Overstep µm): '{val_t19}'") # DEBUG LABEL CHANGED
            overstep_um_gui = float(val_t19) if val_t19 else 0.0 # RENAMED and now in µm

            val_t21 = self.t21.get()
            print(f"DEBUG: Raw value from t21 (Acceleration mm/s²): '{val_t21}'") # DEBUG LABEL CHANGED
            step_type_val_mms2 = float(val_t21) if val_t21 else 0.0 # Now in mm/s², allow float
            # --- End Debug Prints ---

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
        next_print_num = 1
        if os.path.exists(date_specific_log_dir):
            try:
                entries = os.listdir(date_specific_log_dir)
                print_nums = []
                for entry in entries:
                    if os.path.isdir(os.path.join(date_specific_log_dir, entry)) and entry.startswith("Print "):
                        parts = entry.split(" - ")
                        if len(parts) > 0: # Check if split produced at least one part
                            num_part = parts[0].replace("Print ", "").strip()
                            if num_part.isdigit():
                                print_nums.append(int(num_part)) # Added missing append
                if print_nums:
                    next_print_num = max(print_nums) + 1
            except Exception as e:
                self.update_status_message(f"Error determining next print number: {e}", error=True)
                # Fallback to 1 or handle error appropriately, for now, it will return 1
        return next_print_num

    def start_print_thread(self, dlp_power, step_speed_um_s, layer_pause_s, overstep_um_gui, step_type_val_mms2, print_mode): # PARAM RENAMED
        # The try block should start here, encompassing all setup and thread starting
        try:
            self.update_status_message(f"Starting {print_mode} Print Setup...")
            
            path = str(self.t1.get())
            if not path or not os.path.isdir(path):
                self.update_status_message("Error: Image directory not set or invalid.", error=True)
                messagebox.showerror("Setup Error", "Please set a valid image directory first.", parent=self.win)
                return

            # Auto-logging configuration now relies entirely on SensorDataWindow's state
            if self.sensor_data_window_instance and self.sensor_data_window_instance.sensor_window.winfo_exists():
                # Check if the "Enable Automated Logging" checkbox *within SensorDataWindow* is checked
                if self.sensor_data_window_instance.auto_log_enabled_var.get():
                    self.update_status_message("Sensor Panel auto-log is enabled, configuring...")
                    
                    # Set up logging directory structure like backup version
                    main_img_dir = path
                    self.current_print_log_base_dir = os.path.join(main_img_dir, "Printing_Logs")
                    current_date_str = datetime.datetime.now().strftime("%Y-%m-%d")
                    self.current_print_date_dir = os.path.join(self.current_print_log_base_dir, current_date_str)
                    self.current_print_number = self._get_next_print_number(self.current_print_date_dir)
                    self.current_print_session_log_dir = os.path.join(self.current_print_date_dir, f"Print {self.current_print_number}")
                    os.makedirs(self.current_print_session_log_dir, exist_ok=True)
                    self.update_status_message(f"Log directory created: {self.current_print_session_log_dir}")
                    
                    # Configure AutomatedLayerLogger via SensorDataWindow with proper parameters
                    self.sensor_data_window_instance.configure_automated_layer_logging(
                        main_image_dir=main_img_dir,
                        print_number=self.current_print_number,
                        date_str_for_dir=current_date_str,
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

            print(f"DEBUG: print_t STARTING. MyWindow.image_list length: {len(self.image_list)}") 
            self.b1.config(state=DISABLED)
            self.b10.config(state=DISABLED)
            self.b4.config(state=NORMAL)

            self.axis.move_absolute(position=self.reference, unit=Units.LENGTH_MILLIMETRES, wait_until_idle=True)
            self.update_status_message(f"Moved to reference: {self.reference} mm")

            cv2.namedWindow(self.window_name, cv2.WND_PROP_FULLSCREEN)
            cv2.moveWindow(self.window_name, self.screen.x + 1439, self.screen.y - 1) 
            cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
            cv2.imshow(self.window_name, self.black_image)
            cv2.waitKey(1)
            self.update_status_message("OpenCV window initialized.")

            # DLP setup for pattern projection
            if hasattr(self, 'controller'):
                self.controller.changemode(0) # Switch to pattern sequence mode
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
                
                # Get gap estimate and max force from Sandwich Routine GUI boxes
                try:
                    gap_estimate_for_precal = float(self.t_sandwich_gap.get()) if hasattr(self, 't_sandwich_gap') else 0.5
                    max_force_for_precal = float(self.t_sandwich_force.get()) if hasattr(self, 't_sandwich_force') else 0.2
                except ValueError:
                    gap_estimate_for_precal = 0.5
                    max_force_for_precal = 0.2
                    self.update_status_message("Invalid pre-cal parameters, using defaults: Gap=0.5mm, MaxForce=0.2N", error=True)
                
                self.update_status_message(f"Pre-cal settings: Gap estimate={gap_estimate_for_precal:.3f}mm, Max force={max_force_for_precal:.3f}N")
                
                # Store max force for use during printing
                self.precal_max_force = max_force_for_precal
                
                # Run simplified pre-calibration (force threshold only)
                measured_gap = self.perform_precalibration_simple(
                    gap_estimate_mm=gap_estimate_for_precal,
                    contact_force_threshold=max_force_for_precal
                )
                
                if measured_gap is not None:
                    # Store results for use during sandwich routine
                    self.measured_gap_mm = measured_gap
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

                # Update DLP power if it's per-layer and different from the last commanded power
                if hasattr(self, 'controller'):
                    # Convert actual_dlp_power to int for comparison and setting
                    current_layer_target_power = int(actual_dlp_power)
                    if current_layer_target_power != last_commanded_dlp_power:
                        self.controller.power(current=current_layer_target_power)
                        last_commanded_dlp_power = current_layer_target_power # Update last commanded power
                        self.update_status_message(f"Layer {current_layer_num_for_display}: DLP power set to {current_layer_target_power}.")

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
                    if hasattr(self, 'sensor_data_window_instance') and self.sensor_data_window_instance:
                        if hasattr(self.sensor_data_window_instance, 'position_logger_thread'):
                            self.sensor_data_window_instance.position_logger_thread.set_phase("Exposure")

                    # 3. Start Z-axis movement (non-blocking)
                    self.update_status_message(f"L{current_layer_num_for_display} (Cont.): Moving to {current_target_z_microns / 1000.0:.4f} mm at {calculated_continuous_velocity_um_s:.2f} um/s, Accel: {actual_acceleration_to_set_um_s2} µm/s²")
                    
                    # Set phase to Lift (movement starts)
                    if hasattr(self, 'sensor_data_window_instance') and self.sensor_data_window_instance:
                        if hasattr(self.sensor_data_window_instance, 'position_logger_thread'):
                            self.sensor_data_window_instance.position_logger_thread.set_phase("Lift")
                    
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
                    if hasattr(self, 'sensor_data_window_instance') and self.sensor_data_window_instance:
                        if hasattr(self.sensor_data_window_instance, 'position_logger_thread'):
                            self.sensor_data_window_instance.position_logger_thread.set_phase("Exposure")

                    # 2. Exposure
                    if current_exposure_s > 0:
                        time.sleep(current_exposure_s)
                    else:
                        self.update_status_message(f"L{current_layer_num_for_display} (Stepped): Zero exposure time.", error=True)

                    # 3. Show black image after exposure for stepped mode
                    cv2.imshow(self.window_name, self.black_image)
                    cv2.waitKey(1)
                    
                    # Set phase to Pause (blackout period)
                    if hasattr(self, 'sensor_data_window_instance') and self.sensor_data_window_instance:
                        if hasattr(self.sensor_data_window_instance, 'position_logger_thread'):
                            self.sensor_data_window_instance.position_logger_thread.set_phase("Pause")
                    
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
                    
                    self.update_status_message(f"Stepped L{current_layer_num_for_display}: Peeling up to {z_peel_peak / 1000.0:.4f} mm (Speed: {actual_step_speed_um_s} um/s, Accel: {actual_acceleration_to_set_um_s2} µm/s²)")
                    
                    # Set phase to Lift (peel movement starts)
                    if hasattr(self, 'sensor_data_window_instance') and self.sensor_data_window_instance:
                        if hasattr(self.sensor_data_window_instance, 'position_logger_thread'):
                            self.sensor_data_window_instance.position_logger_thread.set_phase("Lift")
                    
                    try:
                        self.axis.move_absolute(
                            position=z_peel_peak,
                            unit=Units.LENGTH_MICROMETRES,
                            wait_until_idle=True,
                            velocity=actual_step_speed_um_s,
                            velocity_unit=Units.VELOCITY_MICROMETRES_PER_SECOND,
                            acceleration=actual_acceleration_to_set_um_s2, 
                            acceleration_unit=Units.ACCELERATION_MICROMETRES_PER_SECOND_SQUARED
                        )
                        self.update_status_message(f"SUCCESS L{current_layer_num_for_display}: Peel movement completed")
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
                    if hasattr(self, 'sensor_data_window_instance') and self.sensor_data_window_instance:
                        if hasattr(self.sensor_data_window_instance, 'position_logger_thread'):
                            self.sensor_data_window_instance.position_logger_thread.set_phase("Pause")
                    
                    # Set phase to Retract (return movement starts)
                    if hasattr(self, 'sensor_data_window_instance') and self.sensor_data_window_instance:
                        if hasattr(self.sensor_data_window_instance, 'position_logger_thread'):
                            self.sensor_data_window_instance.position_logger_thread.set_phase("Retract")
                    
                    try:
                        self.axis.move_absolute(
                            position=z_return_pos, 
                            unit=Units.LENGTH_MICROMETRES,
                            wait_until_idle=True, 
                            velocity=actual_step_speed_um_s,
                            velocity_unit=Units.VELOCITY_MICROMETRES_PER_SECOND,
                            acceleration=actual_acceleration_to_set_um_s2, 
                            acceleration_unit=Units.ACCELERATION_MICROMETRES_PER_SECOND_SQUARED
                        )
                        self.update_status_message(f"SUCCESS L{current_layer_num_for_display}: Return movement completed")
                        
                        # 4a. SANDWICH ROUTINE (FORCE THRESHOLD VERSION)
                        # Only run if pre-calibration was successful (measured_gap_mm is not None)
                        if self.measured_gap_mm is not None:
                            # IMPORTANT: Wait 1 second after retraction to let forces settle
                            self.update_status_message(f"L{current_layer_num_for_display}: Waiting 1s for forces to settle before sandwich...")
                            
                            # Set phase to Pause (settling time)
                            if hasattr(self, 'sensor_data_window_instance') and self.sensor_data_window_instance:
                                if hasattr(self.sensor_data_window_instance, 'position_logger_thread'):
                                    self.sensor_data_window_instance.position_logger_thread.set_phase("Pause")
                            
                            time.sleep(1.0)
                            
                            # Get sandwich parameters
                            actual_sandwich_speed_um_s = self.sandwich_speed_list[i] if i < len(self.sandwich_speed_list) else 500
                            actual_sandwich_touches = 1  # Always 1 touch per layer during printing
                            
                            # Use max force and measured gap from pre-calibration
                            contact_force_threshold = -(self.precal_max_force if hasattr(self, 'precal_max_force') else 0.2)  # Negative for compression
                            measured_gap = self.measured_gap_mm
                            
                            self.update_status_message(f"L{current_layer_num_for_display}: Starting sandwich (Gap:{measured_gap:.3f}mm, ContactForce:{abs(contact_force_threshold):.3f}N, Speed:{actual_sandwich_speed_um_s}µm/s)")
                            
                            # Set phase to Sandwich (sandwich routine starts)
                            if hasattr(self, 'sensor_data_window_instance') and self.sensor_data_window_instance:
                                if hasattr(self.sensor_data_window_instance, 'position_logger_thread'):
                                    self.sensor_data_window_instance.position_logger_thread.set_phase("Sandwich")
                            
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
                                    target_glass_um = current_pos_um + (measured_gap * 1000.0)
                                    gap_um = measured_gap * 1000.0
                                    
                                    # Get pause time from this layer
                                    actual_pause = self.pause_list[i] if i < len(self.pause_list) else 0.0
                                    
                                    # Calculate speed tiers (descent speeds)
                                    # Slower near window, faster away from window
                                    speed_tier1 = actual_sandwich_speed_um_s  # 0-50% of gap (far from window)
                                    speed_tier2 = actual_sandwich_speed_um_s / 2.0  # 50-75% of gap
                                    speed_tier3 = actual_sandwich_speed_um_s / 4.0  # 75-100% of gap (near window)
                                    speed_tier4 = min(50.0, actual_sandwich_speed_um_s / 8.0)  # First/last 100µm
                                    
                                    # Calculate waypoint positions for DESCENT (moving DOWN toward glass)
                                    waypoint_50pct_um = current_pos_um + (gap_um * 0.5)
                                    waypoint_75pct_um = current_pos_um + (gap_um * 0.75)
                                    waypoint_100um_before_glass_um = target_glass_um - 100.0
                                    
                                    self.update_status_message(f"L{current_layer_num_for_display}: DESCENT with ramping (Gap:{measured_gap:.3f}mm, Speeds:{speed_tier1:.0f}/{speed_tier2:.0f}/{speed_tier3:.0f}/{speed_tier4:.0f}µm/s, Pause:{actual_pause}s)")
                                    
                                    # ========== DESCENT PHASE ==========
                                    # Segment 1: 0% to 50% at V_s
                                    self.axis.move_absolute(
                                        position=waypoint_50pct_um,
                                        unit=Units.LENGTH_MICROMETRES,
                                        wait_until_idle=False,
                                        velocity=speed_tier1 / 1000.0,
                                        velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND,
                                        acceleration=1.0,
                                        acceleration_unit=Units.ACCELERATION_MILLIMETRES_PER_SECOND_SQUARED
                                    )
                                    
                                    failsafe_triggered = False
                                    while self.axis.is_busy():
                                        if self.flag:
                                            self.axis.stop()
                                            break
                                        if force_gauge.get_latest_calibrated_force() <= contact_force_threshold:
                                            self.axis.stop()
                                            failsafe_triggered = True
                                            self.update_status_message(f"L{current_layer_num_for_display}: FORCE FAILSAFE during descent segment 1", error=True)
                                            break
                                        time.sleep(0.02)
                                    
                                    if failsafe_triggered or self.flag:
                                        self.update_status_message(f"L{current_layer_num_for_display}: Sandwich aborted, returning to layer position", error=True)
                                        self.axis.move_absolute(sandwich_target_position_um, Units.LENGTH_MICROMETRES, wait_until_idle=True)
                                        continue
                                    
                                    # Segment 2: 50% to 75% at V_s/2
                                    self.axis.move_absolute(
                                        position=waypoint_75pct_um,
                                        unit=Units.LENGTH_MICROMETRES,
                                        wait_until_idle=False,
                                        velocity=speed_tier2 / 1000.0,
                                        velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND,
                                        acceleration=1.0,
                                        acceleration_unit=Units.ACCELERATION_MILLIMETRES_PER_SECOND_SQUARED
                                    )
                                    
                                    while self.axis.is_busy():
                                        if self.flag:
                                            self.axis.stop()
                                            break
                                        if force_gauge.get_latest_calibrated_force() <= contact_force_threshold:
                                            self.axis.stop()
                                            failsafe_triggered = True
                                            self.update_status_message(f"L{current_layer_num_for_display}: FORCE FAILSAFE during descent segment 2", error=True)
                                            break
                                        time.sleep(0.02)
                                    
                                    if failsafe_triggered or self.flag:
                                        self.update_status_message(f"L{current_layer_num_for_display}: Sandwich aborted, returning to layer position", error=True)
                                        self.axis.move_absolute(sandwich_target_position_um, Units.LENGTH_MICROMETRES, wait_until_idle=True)
                                        continue
                                    
                                    # Segment 3: 75% to (100%-100µm) at V_s/4
                                    self.axis.move_absolute(
                                        position=waypoint_100um_before_glass_um,
                                        unit=Units.LENGTH_MICROMETRES,
                                        wait_until_idle=False,
                                        velocity=speed_tier3 / 1000.0,
                                        velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND,
                                        acceleration=1.0,
                                        acceleration_unit=Units.ACCELERATION_MILLIMETRES_PER_SECOND_SQUARED
                                    )
                                    
                                    while self.axis.is_busy():
                                        if self.flag:
                                            self.axis.stop()
                                            break
                                        if force_gauge.get_latest_calibrated_force() <= contact_force_threshold:
                                            self.axis.stop()
                                            failsafe_triggered = True
                                            self.update_status_message(f"L{current_layer_num_for_display}: FORCE FAILSAFE during descent segment 3", error=True)
                                            break
                                        time.sleep(0.02)
                                    
                                    if failsafe_triggered or self.flag:
                                        self.update_status_message(f"L{current_layer_num_for_display}: Sandwich aborted, returning to layer position", error=True)
                                        self.axis.move_absolute(sandwich_target_position_um, Units.LENGTH_MICROMETRES, wait_until_idle=True)
                                        continue
                                    
                                    # Segment 4: Last 100µm at min(50µm/s, V_s/8)
                                    self.axis.move_absolute(
                                        position=target_glass_um,
                                        unit=Units.LENGTH_MICROMETRES,
                                        wait_until_idle=False,
                                        velocity=speed_tier4 / 1000.0,
                                        velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND,
                                        acceleration=1.0,
                                        acceleration_unit=Units.ACCELERATION_MILLIMETRES_PER_SECOND_SQUARED
                                    )
                                    
                                    while self.axis.is_busy():
                                        if self.flag:
                                            self.axis.stop()
                                            break
                                        if force_gauge.get_latest_calibrated_force() <= contact_force_threshold:
                                            self.axis.stop()
                                            failsafe_triggered = True
                                            self.update_status_message(f"L{current_layer_num_for_display}: FORCE FAILSAFE during descent segment 4 (last 100µm)", error=True)
                                            break
                                        time.sleep(0.02)
                                    
                                    if failsafe_triggered or self.flag:
                                        self.update_status_message(f"L{current_layer_num_for_display}: Sandwich aborted, returning to layer position", error=True)
                                        self.axis.move_absolute(sandwich_target_position_um, Units.LENGTH_MICROMETRES, wait_until_idle=True)
                                        continue
                                    
                                    final_descent_pos_um = self.axis.get_position(Units.LENGTH_MICROMETRES)
                                    self.update_status_message(f"L{current_layer_num_for_display}: Reached glass at {final_descent_pos_um/1000.0:.3f}mm")
                                    
                                    # ========== ASCENT PHASE (SYMMETRICAL + PAUSE AT 50%) ==========
                                    # Calculate waypoint positions for ASCENT (moving UP away from glass)
                                    waypoint_100um_after_glass_um = final_descent_pos_um - 100.0
                                    waypoint_75pct_up_um = sandwich_target_position_um + (gap_um * 0.25)  # 75% complete
                                    waypoint_50pct_up_um = sandwich_target_position_um + (gap_um * 0.5)   # 50% complete (PAUSE HERE)
                                    
                                    self.update_status_message(f"L{current_layer_num_for_display}: ASCENT with ramping (symmetric to descent)")
                                    
                                    # Segment 1: First 100µm at min(50µm/s, V_s/8)
                                    self.axis.move_absolute(
                                        position=waypoint_100um_after_glass_um,
                                        unit=Units.LENGTH_MICROMETRES,
                                        wait_until_idle=True,
                                        velocity=speed_tier4 / 1000.0,
                                        velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND,
                                        acceleration=1.0,
                                        acceleration_unit=Units.ACCELERATION_MILLIMETRES_PER_SECOND_SQUARED
                                    )
                                    
                                    # Segment 2: 100µm to 25% (which is 75% from glass) at V_s/4
                                    self.axis.move_absolute(
                                        position=waypoint_75pct_up_um,
                                        unit=Units.LENGTH_MICROMETRES,
                                        wait_until_idle=True,
                                        velocity=speed_tier3 / 1000.0,
                                        velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND,
                                        acceleration=1.0,
                                        acceleration_unit=Units.ACCELERATION_MILLIMETRES_PER_SECOND_SQUARED
                                    )
                                    
                                    # Segment 3: 25% to 50% at V_s/2
                                    self.axis.move_absolute(
                                        position=waypoint_50pct_up_um,
                                        unit=Units.LENGTH_MICROMETRES,
                                        wait_until_idle=True,
                                        velocity=speed_tier2 / 1000.0,
                                        velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND,
                                        acceleration=1.0,
                                        acceleration_unit=Units.ACCELERATION_MILLIMETRES_PER_SECOND_SQUARED
                                    )
                                    
                                    # PAUSE AT 50% POINT
                                    if actual_pause > 0:
                                        self.update_status_message(f"L{current_layer_num_for_display}: Pausing {actual_pause}s at 50% ascent point")
                                        time.sleep(actual_pause)
                                    
                                    # Segment 4: 50% to 0% (layer position) at V_s
                                    self.axis.move_absolute(
                                        position=sandwich_target_position_um,
                                        unit=Units.LENGTH_MICROMETRES,
                                        wait_until_idle=True,
                                        velocity=speed_tier1 / 1000.0,
                                        velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND,
                                        acceleration=1.0,
                                        acceleration_unit=Units.ACCELERATION_MILLIMETRES_PER_SECOND_SQUARED
                                    )
                                    
                                    final_pos = self.axis.get_position(Units.LENGTH_MICROMETRES)
                                    self.update_status_message(f"L{current_layer_num_for_display}: Sandwich complete at {final_pos/1000.0:.3f}mm")
                                    
                            except Exception as sandwich_error:
                                self.update_status_message(f"L{current_layer_num_for_display}: Sandwich routine error: {sandwich_error}", error=True)
                                # Don't abort print on sandwich failure, just log it
                        else:
                            # Pre-calibration was not run or failed, skip sandwich
                            if i == 0:  # Only log once on first layer
                                self.update_status_message(f"L{current_layer_num_for_display}: Sandwich skipped (pre-calibration not available)")

                        
                    except Exception as return_error:
                        self.update_status_message(f"ERROR L{current_layer_num_for_display}: Return movement failed: {return_error}", error=True)
                        # Log detailed diagnostics
                        try:
                            fault_status = self.axis.warnings.get_flags()
                            pos_after_fail = self.axis.get_position(unit=Units.LENGTH_MICROMETRES)
                            force_after_fail = self.force_gauge_manager.get_force() if hasattr(self, 'force_gauge_manager') else 0.0
                            self.update_status_message(f"DIAGNOSTICS L{current_layer_num_for_display}: Fault={fault_status}, Pos={pos_after_fail/1000.0:.4f}mm, Force={force_after_fail:.4f}N", error=True)
                            
                            # RECOVERY ATTEMPT: Clear faults and try gentle movement
                            self.update_status_message(f"RECOVERY L{current_layer_num_for_display}: Attempting to clear faults and recover...", error=True)
                            try:
                                # Clear any faults by sending home command to reset state
                                # Note: Zaber warnings don't have a .clear() method
                                # Instead, we try to reset the axis state
                                self.axis.home(wait_until_idle=False)
                                time.sleep(0.5)
                                self.axis.stop()
                                time.sleep(0.5)
                                
                                # Try a very slow, gentle movement back up
                                recovery_pos = pos_after_fail + 500  # Move up 0.5mm slowly
                                self.axis.move_absolute(
                                    position=recovery_pos,
                                    unit=Units.LENGTH_MICROMETRES,
                                    wait_until_idle=True,
                                    velocity=100,  # Very slow: 100 um/s
                                    velocity_unit=Units.VELOCITY_MICROMETRES_PER_SECOND,
                                    acceleration=10000,  # Lower acceleration
                                    acceleration_unit=Units.ACCELERATION_MICROMETRES_PER_SECOND_SQUARED
                                )
                                self.update_status_message(f"RECOVERY L{current_layer_num_for_display}: Successfully moved to {recovery_pos/1000.0:.4f}mm", error=True)
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
                if self.sensor_data_window_instance and \
                   self.sensor_data_window_instance.sensor_window.winfo_exists() and \
                   hasattr(self.sensor_data_window_instance, 'automated_layer_logger') and \
                   self.sensor_data_window_instance.automated_layer_logger and \
                   self.sensor_data_window_instance.automated_layer_logger.is_configured_for_run:
                    # Corrected method name below
                    self.sensor_data_window_instance.update_auto_logger_current_layer(
                        current_layer_num_for_display,
                        z_at_previous_exposure_microns / 1000.0 
                    )

                if actual_layer_pause_s > 0:
                    # Set phase to Pause (layer pause period before next exposure)
                    if hasattr(self, 'sensor_data_window_instance') and self.sensor_data_window_instance:
                        if hasattr(self.sensor_data_window_instance, 'position_logger_thread'):
                            self.sensor_data_window_instance.position_logger_thread.set_phase("Pause")
                    
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
                    cv2.destroyWindow(self.window_name)
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

                # Save print status file
                status_file_path = os.path.join(self.current_print_session_log_dir, "print_status.txt")
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
                            instruction_filename = os.path.basename(self.active_instruction_file_path)
                            saved_instruction_path = os.path.join(self.current_print_session_log_dir, instruction_filename)
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
        self.reference = float(self.t4.get())
        # self.axis.move_relative(position=self.offset, unit=Units.LENGTH_MILLIMETRES, # Assuming self.offset is a relative move
        #                         wait_until_idle=False) # Consider if you want to wait or not
        # It's usually safer to move to an absolute position after setting a reference if that's the intent.
        # If self.reference is the new "zero", you might not need to move by self.offset here,
        # or if you do, ensure it's to the correct absolute target.
        # For now, just updating the status message:
        self.update_status_message("Home Set") # Use update_status_message instead of direct t8 manipulation

    def get_position(self):
        self.t4.delete(0, 'end')
        self.t4.insert(END, str(self.axis.get_position(unit=Units.LENGTH_MILLIMETRES)))

    def goto_position(self):
        self.axis.move_absolute(position=float(self.t4.get()), unit=Units.LENGTH_MILLIMETRES,
                                wait_until_idle=False)

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
                self.controller.power(current=0)    # Ensure LED is off
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
            
            print(f"DEBUG: MyWindow.input_directory AFTER set_image_directory. MyWindow.image_list length: {len(self.image_list)}, Application.image_list length: {len(self.application.image_list)}") # Add this

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
        self.axis.move_relative(position=float(self.t9.get())*-1, unit=Units.LENGTH_MILLIMETRES,
                                wait_until_idle=False,velocity=10,
                                velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND)

    def movedown(self):
        self.axis.move_relative(position=float(self.t9.get()), unit=Units.LENGTH_MILLIMETRES,
                                wait_until_idle=False,velocity=5,
                                velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND)

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
    
    def update_status_message(self, message, error=False):
        """Updates the status message label and logs to console."""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        # Concatenate for console/text area, but use raw message for status_message_var
        log_message = f"[{timestamp}] {message}" 
        
        try:
            if self.win.winfo_exists():
                 self.status_message_var.set(message) # Set the StringVar for the Label
        except TclError:
            pass 

        if error:
            print(f"ERROR: {log_message}")
        else:
            print(f"Status Update: {log_message}")
        
        if hasattr(self, 'status_text_area') and self.status_text_area:
            try:
                if self.status_text_area.winfo_exists():
                    self.status_text_area.insert(END, log_message + "\n")
                    self.status_text_area.see(END)
            except TclError:
                 pass

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

    # ========== SANDWICH PRE-CALIBRATION AND ADAPTIVE SPEED HELPERS ==========
    
    def calculate_force_derivative(self, force_history, dt=0.02):
        """
        Calculate force derivative (dF/dt) using a sliding window.
        
        Args:
            force_history: List of recent force measurements (most recent last)
            dt: Time interval between measurements in seconds (default 20ms)
            
        Returns:
            Force derivative in N/s, or 0 if insufficient data
        """
        if len(force_history) < 2:
            return 0.0
        
        # Use last 5 samples for smoothing (or fewer if not available)
        window_size = min(5, len(force_history))
        recent_forces = force_history[-window_size:]
        
        # Calculate derivative using first and last point in window
        df = recent_forces[-1] - recent_forces[0]
        time_span = dt * (window_size - 1)
        
        if time_span == 0:
            return 0.0
        
        derivative = df / time_span
        return derivative
    
    def adaptive_speed_move(self, target_position_um, current_position_um, gap_distance_mm, 
                           base_speed_um_s, direction='down', accel_mm_s2=1.0, 
                           force_gauge_manager=None, max_force_threshold=None,
                           derivative_threshold=None, stop_flag_check=None):
        """
        Move to target position using adaptive 3-stage speed control.
        
        Speed profile:
        - First 50% of gap: base_speed
        - Next 25% (50-75%): base_speed / 2
        - Final 25% (75-100%): base_speed / 4
        
        Args:
            target_position_um: Final target position in micrometers
            current_position_um: Starting position in micrometers
            gap_distance_mm: Total gap distance for calculating waypoints
            base_speed_um_s: Initial speed in micrometers/second
            direction: 'down' (moving positive) or 'up' (moving negative)
            accel_mm_s2: Acceleration in mm/s²
            force_gauge_manager: Optional force gauge for monitoring during movement
            max_force_threshold: Optional max force limit (absolute value)
            derivative_threshold: Optional force derivative threshold for contact detection
            stop_flag_check: Optional function that returns True if movement should stop
            
        Returns:
            Dictionary with:
                - 'reached_target': Boolean
                - 'stopped_at_um': Position where movement stopped
                - 'stop_reason': 'complete', 'force_limit', 'derivative', 'user_stop', or 'error'
                - 'contact_detected': Boolean (True if stopped due to force/derivative)
        """
        result = {
            'reached_target': False,
            'stopped_at_um': current_position_um,
            'stop_reason': 'unknown',
            'contact_detected': False
        }
        
        try:
            # Calculate waypoints based on gap distance
            gap_distance_um = gap_distance_mm * 1000.0
            
            if direction == 'down':
                # Moving in positive direction (down toward glass)
                waypoint_50pct = current_position_um + (gap_distance_um * 0.5)
                waypoint_75pct = current_position_um + (gap_distance_um * 0.75)
            else:  # 'up'
                # Moving in negative direction (up away from glass)
                waypoint_50pct = current_position_um - (gap_distance_um * 0.5)
                waypoint_75pct = current_position_um - (gap_distance_um * 0.75)
            
            # Define the three movement segments
            segments = [
                {'target_um': waypoint_50pct, 'speed_um_s': base_speed_um_s},
                {'target_um': waypoint_75pct, 'speed_um_s': base_speed_um_s / 2.0},
                {'target_um': target_position_um, 'speed_um_s': base_speed_um_s / 4.0}
            ]
            
            # Convert acceleration once
            accel_um_s2 = accel_mm_s2 * 1000.0
            
            # Execute each segment with force monitoring
            force_history = []
            
            for i, segment in enumerate(segments):
                segment_target = segment['target_um']
                segment_speed = segment['speed_um_s']
                segment_speed_mm_s = segment_speed / 1000.0
                
                # Start movement
                self.axis.move_absolute(
                    position=segment_target,
                    unit=Units.LENGTH_MICROMETRES,
                    wait_until_idle=False,
                    velocity=segment_speed_mm_s,
                    velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND,
                    acceleration=accel_mm_s2,
                    acceleration_unit=Units.ACCELERATION_MILLIMETRES_PER_SECOND_SQUARED
                )
                
                # Monitor force during movement if available
                if force_gauge_manager:
                    while self.axis.is_busy():
                        # Check user stop flag
                        if stop_flag_check and stop_flag_check():
                            self.axis.stop()
                            while self.axis.is_busy():
                                time.sleep(0.01)
                            result['stopped_at_um'] = self.axis.get_position(Units.LENGTH_MICROMETRES)
                            result['stop_reason'] = 'user_stop'
                            return result
                        
                        # Get current force
                        current_force = force_gauge_manager.get_latest_calibrated_force()
                        force_history.append(current_force)
                        
                        # Keep force history manageable
                        if len(force_history) > 20:
                            force_history.pop(0)
                        
                        # Check absolute force threshold
                        if max_force_threshold and abs(current_force) >= abs(max_force_threshold):
                            self.axis.stop()
                            while self.axis.is_busy():
                                time.sleep(0.01)
                            result['stopped_at_um'] = self.axis.get_position(Units.LENGTH_MICROMETRES)
                            result['stop_reason'] = 'force_limit'
                            result['contact_detected'] = True
                            return result
                        
                        # Check derivative threshold
                        if derivative_threshold and len(force_history) >= 3:
                            current_derivative = self.calculate_force_derivative(force_history)
                            if abs(current_derivative) >= abs(derivative_threshold):
                                self.axis.stop()
                                while self.axis.is_busy():
                                    time.sleep(0.01)
                                result['stopped_at_um'] = self.axis.get_position(Units.LENGTH_MICROMETRES)
                                result['stop_reason'] = 'derivative'
                                result['contact_detected'] = True
                                return result
                        
                        time.sleep(0.02)  # 20ms sampling rate
                else:
                    # No force monitoring, just wait for completion
                    while self.axis.is_busy():
                        if stop_flag_check and stop_flag_check():
                            self.axis.stop()
                            while self.axis.is_busy():
                                time.sleep(0.01)
                            result['stopped_at_um'] = self.axis.get_position(Units.LENGTH_MICROMETRES)
                            result['stop_reason'] = 'user_stop'
                            return result
                        time.sleep(0.02)
            
            # All segments completed successfully
            result['reached_target'] = True
            result['stopped_at_um'] = self.axis.get_position(Units.LENGTH_MICROMETRES)
            result['stop_reason'] = 'complete'
            return result
            
        except Exception as e:
            result['stopped_at_um'] = self.axis.get_position(Units.LENGTH_MICROMETRES)
            result['stop_reason'] = f'error: {str(e)}'
            return result

    def perform_precalibration_simple(self, gap_estimate_mm, contact_force_threshold):
        """
        Simplified pre-calibration routine using force threshold only (no derivative).
        
        This routine:
        1. Moves down at constant speed (500 µm/s) until force threshold hit
        2. Performs 5 touches with 1s pause between each
        3. Records contact position on each descent
        4. Calculates average gap
        5. Returns to starting position with 3s pause before printing
        
        Args:
            gap_estimate_mm: Estimated gap distance (used for search limit)
            contact_force_threshold: Force threshold for contact detection (N, positive value)
            
        Returns:
            average_gap_mm or None on failure
        """
        try:
            self.update_status_message("=== STARTING SIMPLIFIED PRE-CALIBRATION (FORCE THRESHOLD) ===")
            
            # Check force gauge availability
            if not (hasattr(self, 'sensor_data_window_instance') and 
                   self.sensor_data_window_instance and 
                   hasattr(self.sensor_data_window_instance, 'force_gauge_manager') and
                   self.sensor_data_window_instance.force_gauge_manager and
                   self.sensor_data_window_instance.is_force_gauge_calibrated_internally()):
                self.update_status_message("Pre-calibration failed: Force gauge not available/calibrated", error=True)
                return None
            
            force_gauge = self.sensor_data_window_instance.force_gauge_manager
            force_threshold = -abs(contact_force_threshold)  # Negative for compression
            
            # Record starting position
            start_position_um = self.axis.get_position(Units.LENGTH_MICROMETRES)
            start_position_mm = start_position_um / 1000.0
            
            # Calculate expected glass position
            expected_glass_mm = start_position_mm + gap_estimate_mm
            max_search_mm = expected_glass_mm + 0.5  # Safety margin
            max_search_um = max_search_mm * 1000.0
            
            self.update_status_message(f"Pre-cal: Starting at {start_position_mm:.3f}mm, searching to {max_search_mm:.3f}mm")
            self.update_status_message(f"Pre-cal: Contact force threshold: {contact_force_threshold:.3f}N")
            
            contact_positions_um = []
            base_descent_speed_um_s = 500.0  # Base speed for 3-tier ramping
            
            # Calculate 3-tier speeds (no Tier 4 for pre-calibration)
            speed_tier1 = base_descent_speed_um_s        # 0-50%: 500 µm/s
            speed_tier2 = base_descent_speed_um_s / 2.0  # 50-75%: 250 µm/s
            speed_tier3 = base_descent_speed_um_s / 4.0  # 75-100%: 125 µm/s
            
            # Perform 5 touches
            for touch_num in range(5):
                self.update_status_message(f"Pre-cal: Touch {touch_num + 1}/5 - 3-tier descent (500→250→125 µm/s)")
                
                current_pos_um = self.axis.get_position(Units.LENGTH_MICROMETRES)
                gap_um = (max_search_um - current_pos_um)
                
                # Calculate waypoints for 3-tier descent
                waypoint_50pct_um = current_pos_um + (gap_um * 0.5)
                waypoint_75pct_um = current_pos_um + (gap_um * 0.75)
                
                contact_found = False
                contact_pos_um = None
                
                # Segment 1: 0→50% at V_s (500 µm/s)
                self.axis.move_absolute(
                    position=waypoint_50pct_um,
                    unit=Units.LENGTH_MICROMETRES,
                    wait_until_idle=False,
                    velocity=speed_tier1 / 1000.0,
                    velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND,
                    acceleration=1.0,
                    acceleration_unit=Units.ACCELERATION_MILLIMETRES_PER_SECOND_SQUARED
                )
                
                while self.axis.is_busy():
                    if self.flag:
                        self.axis.stop()
                        raise Exception("Pre-calibration stopped by user")
                    
                    current_force = force_gauge.get_latest_calibrated_force()
                    if current_force <= force_threshold:
                        self.axis.stop()
                        while self.axis.is_busy():
                            time.sleep(0.01)
                        contact_found = True
                        contact_pos_um = self.axis.get_position(Units.LENGTH_MICROMETRES)
                        break
                    time.sleep(0.02)
                
                # Segment 2: 50→75% at V_s/2 (250 µm/s) - only if no contact yet
                if not contact_found:
                    self.axis.move_absolute(
                        position=waypoint_75pct_um,
                        unit=Units.LENGTH_MICROMETRES,
                        wait_until_idle=False,
                        velocity=speed_tier2 / 1000.0,
                        velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND,
                        acceleration=1.0,
                        acceleration_unit=Units.ACCELERATION_MILLIMETRES_PER_SECOND_SQUARED
                    )
                    
                    while self.axis.is_busy():
                        if self.flag:
                            self.axis.stop()
                            raise Exception("Pre-calibration stopped by user")
                        
                        current_force = force_gauge.get_latest_calibrated_force()
                        if current_force <= force_threshold:
                            self.axis.stop()
                            while self.axis.is_busy():
                                time.sleep(0.01)
                            contact_found = True
                            contact_pos_um = self.axis.get_position(Units.LENGTH_MICROMETRES)
                            break
                        time.sleep(0.02)
                
                # Segment 3: 75→100% at V_s/4 (125 µm/s) - only if no contact yet
                if not contact_found:
                    self.axis.move_absolute(
                        position=max_search_um,
                        unit=Units.LENGTH_MICROMETRES,
                        wait_until_idle=False,
                        velocity=speed_tier3 / 1000.0,
                        velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND,
                        acceleration=1.0,
                        acceleration_unit=Units.ACCELERATION_MILLIMETRES_PER_SECOND_SQUARED
                    )
                    
                    while self.axis.is_busy():
                        if self.flag:
                            self.axis.stop()
                            raise Exception("Pre-calibration stopped by user")
                        
                        current_force = force_gauge.get_latest_calibrated_force()
                        if current_force <= force_threshold:
                            self.axis.stop()
                            while self.axis.is_busy():
                                time.sleep(0.01)
                            contact_found = True
                            contact_pos_um = self.axis.get_position(Units.LENGTH_MICROMETRES)
                            break
                        time.sleep(0.02)
                
                # Record contact result
                if contact_found:
                    contact_positions_um.append(contact_pos_um)
                    gap_measured = (contact_pos_um - start_position_um) / 1000.0
                    self.update_status_message(f"Pre-cal: Touch {touch_num + 1}/5 - Contact at {contact_pos_um/1000.0:.3f}mm (Gap:{gap_measured:.3f}mm, Force:{force_gauge.get_latest_calibrated_force():.4f}N)")
                else:
                    self.update_status_message(f"Pre-cal: Touch {touch_num + 1}/5 - No contact detected", error=True)
                
                # Retract 200µm before next touch with 3-tier ramping (symmetric ascent)
                if touch_num < 4 and contact_found:  # Don't retract after last touch
                    retract_pos_um = contact_pos_um - 200.0
                    retract_distance_um = 200.0
                    
                    # Calculate symmetric ascent waypoints
                    waypoint_75pct_up_um = contact_pos_um - (retract_distance_um * 0.25)  # 25% up = 75% remaining
                    waypoint_50pct_up_um = contact_pos_um - (retract_distance_um * 0.5)   # 50% up = 50% remaining
                    
                    # Segment 1: First 25% at V_s/4 (slowest near glass)
                    self.axis.move_absolute(
                        position=waypoint_75pct_up_um,
                        unit=Units.LENGTH_MICROMETRES,
                        wait_until_idle=True,
                        velocity=speed_tier3 / 1000.0,
                        velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND,
                        acceleration=1.0,
                        acceleration_unit=Units.ACCELERATION_MILLIMETRES_PER_SECOND_SQUARED
                    )
                    
                    # Segment 2: 25→50% at V_s/2
                    self.axis.move_absolute(
                        position=waypoint_50pct_up_um,
                        unit=Units.LENGTH_MICROMETRES,
                        wait_until_idle=True,
                        velocity=speed_tier2 / 1000.0,
                        velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND,
                        acceleration=1.0,
                        acceleration_unit=Units.ACCELERATION_MILLIMETRES_PER_SECOND_SQUARED
                    )
                    
                    # Segment 3: 50→100% at V_s (fastest away from glass)
                    self.axis.move_absolute(
                        position=retract_pos_um,
                        unit=Units.LENGTH_MICROMETRES,
                        wait_until_idle=True,
                        velocity=speed_tier1 / 1000.0,
                        velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND,
                        acceleration=1.0,
                        acceleration_unit=Units.ACCELERATION_MILLIMETRES_PER_SECOND_SQUARED
                    )
                    
                    self.update_status_message(f"Pre-cal: Pausing 1s before next touch...")
                    time.sleep(1.0)
            
            # Calculate average gap
            if len(contact_positions_um) < 2:
                self.update_status_message("Pre-cal: Insufficient contact data for averaging", error=True)
                self.axis.move_absolute(
                    position=start_position_um,
                    unit=Units.LENGTH_MICROMETRES,
                    wait_until_idle=True,
                    velocity=0.5,
                    velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND
                )
                return None
            
            avg_contact_pos_um = sum(contact_positions_um) / len(contact_positions_um)
            avg_gap_mm = (avg_contact_pos_um - start_position_um) / 1000.0
            
            self.update_status_message(f"Pre-cal: Average gap from {len(contact_positions_um)} contacts: {avg_gap_mm:.3f}mm")
            
            # Return to starting position
            self.update_status_message("Pre-cal: Returning to start position...")
            self.axis.move_absolute(
                position=start_position_um,
                unit=Units.LENGTH_MICROMETRES,
                wait_until_idle=True,
                velocity=0.5,
                velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND,
                acceleration=1.0,
                acceleration_unit=Units.ACCELERATION_MILLIMETRES_PER_SECOND_SQUARED
            )
            
            self.update_status_message("Pre-cal: Pausing 3s before starting print...")
            time.sleep(3.0)
            
            self.update_status_message(f"=== PRE-CALIBRATION COMPLETE: Gap={avg_gap_mm:.3f}mm ===")
            return avg_gap_mm
            
        except Exception as e:
            self.update_status_message(f"Pre-calibration error: {e}", error=True)
            try:
                self.axis.move_absolute(
                    position=start_position_um,
                    unit=Units.LENGTH_MICROMETRES,
                    wait_until_idle=True,
                    velocity=0.5,
                    velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND
                )
            except:
                pass
            return None

    def perform_precalibration(self, gap_estimate_mm, derivative_threshold_initial=0.075):
        """
        Perform pre-calibration routine to measure actual gap and force derivative threshold.
        
        This routine:
        1. Moves down using adaptive speed (500→250→100 µm/s) until derivative threshold hit
        2. Performs 5 oscillations (±100µm) with 1s pause between each
        3. Records contact position on each descent
        4. Calculates average gap and average peak derivative
        5. Returns to starting position with 5s pause before printing
        
        Args:
            gap_estimate_mm: Estimated gap distance (used for adaptive speed calculation)
            derivative_threshold_initial: Initial derivative threshold for first contact (N/s)
            
        Returns:
            Tuple of (average_gap_mm, average_peak_derivative) or (None, None) on failure
        """
        try:
            self.update_status_message("=== STARTING PRE-CALIBRATION ROUTINE ===")
            
            # Check force gauge availability
            if not (hasattr(self, 'sensor_data_window_instance') and 
                   self.sensor_data_window_instance and 
                   hasattr(self.sensor_data_window_instance, 'force_gauge_manager') and
                   self.sensor_data_window_instance.force_gauge_manager and
                   self.sensor_data_window_instance.is_force_gauge_calibrated_internally()):
                self.update_status_message("Pre-calibration failed: Force gauge not available/calibrated", error=True)
                return (None, None)
            
            force_gauge = self.sensor_data_window_instance.force_gauge_manager
            
            # Record starting position
            start_position_um = self.axis.get_position(Units.LENGTH_MICROMETRES)
            start_position_mm = start_position_um / 1000.0
            
            # Calculate expected glass position
            expected_glass_mm = start_position_mm + gap_estimate_mm
            max_search_mm = expected_glass_mm + 0.5  # Safety margin
            max_search_um = max_search_mm * 1000.0
            
            self.update_status_message(f"Pre-cal: Starting at {start_position_mm:.3f}mm, searching to {max_search_mm:.3f}mm")
            self.update_status_message(f"Pre-cal: Using derivative threshold {derivative_threshold_initial:.4f} N/s")
            
            # Phase 1: Initial descent to find first contact
            self.update_status_message("Pre-cal: Phase 1 - Initial descent with adaptive speed...")
            move_result = self.adaptive_speed_move(
                target_position_um=max_search_um,
                current_position_um=start_position_um,
                gap_distance_mm=gap_estimate_mm,
                base_speed_um_s=500.0,  # 500 µm/s base speed
                direction='down',
                accel_mm_s2=1.0,  # Slow acceleration
                force_gauge_manager=force_gauge,
                max_force_threshold=None,  # No force limit, only derivative
                derivative_threshold=derivative_threshold_initial,
                stop_flag_check=lambda: self.flag
            )
            
            if not move_result['contact_detected']:
                self.update_status_message(f"Pre-cal: No contact detected (reason: {move_result['stop_reason']})", error=True)
                # Return to start
                self.axis.move_absolute(
                    position=start_position_um,
                    unit=Units.LENGTH_MICROMETRES,
                    wait_until_idle=True,
                    velocity=0.5,  # 500 µm/s
                    velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND
                )
                return (None, None)
            
            first_contact_um = move_result['stopped_at_um']
            first_contact_mm = first_contact_um / 1000.0
            measured_gap_initial = (first_contact_um - start_position_um) / 1000.0
            
            self.update_status_message(f"Pre-cal: First contact at {first_contact_mm:.3f}mm (gap: {measured_gap_initial:.3f}mm)")
            
            # Phase 2: Oscillation to refine measurement (5 cycles)
            self.update_status_message("Pre-cal: Phase 2 - Performing 5 oscillations for averaging...")
            
            contact_positions_um = [first_contact_um]
            peak_derivatives = []
            
            oscillation_amplitude_um = 100.0  # ±100µm
            oscillation_speed_um_s = 50.0  # 50 µm/s
            oscillation_speed_mm_s = oscillation_speed_um_s / 1000.0
            oscillation_accel_mm_s2 = 1.0
            
            for osc_num in range(5):
                # Move up 100µm from contact
                retract_position_um = first_contact_um - oscillation_amplitude_um
                
                self.update_status_message(f"Pre-cal: Oscillation {osc_num + 1}/5 - Moving up to {retract_position_um/1000.0:.3f}mm")
                self.axis.move_absolute(
                    position=retract_position_um,
                    unit=Units.LENGTH_MICROMETRES,
                    wait_until_idle=True,
                    velocity=oscillation_speed_mm_s,
                    velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND,
                    acceleration=oscillation_accel_mm_s2,
                    acceleration_unit=Units.ACCELERATION_MILLIMETRES_PER_SECOND_SQUARED
                )
                
                # Pause 1 second
                self.update_status_message(f"Pre-cal: Pausing 1s before descent {osc_num + 1}/5...")
                time.sleep(1.0)
                
                # Move back down to detect contact with derivative monitoring
                self.update_status_message(f"Pre-cal: Oscillation {osc_num + 1}/5 - Moving down to find contact...")
                
                # Move down slowly with derivative monitoring
                search_target_um = first_contact_um + 50.0  # Search slightly past expected contact
                force_history = []
                contact_found = False
                contact_pos_um = None
                peak_derivative_this_cycle = 0.0
                
                self.axis.move_absolute(
                    position=search_target_um,
                    unit=Units.LENGTH_MICROMETRES,
                    wait_until_idle=False,
                    velocity=oscillation_speed_mm_s,
                    velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND,
                    acceleration=oscillation_accel_mm_s2,
                    acceleration_unit=Units.ACCELERATION_MILLIMETRES_PER_SECOND_SQUARED
                )
                
                while self.axis.is_busy():
                    if self.flag:
                        self.axis.stop()
                        raise Exception("Pre-calibration stopped by user")
                    
                    current_force = force_gauge.get_latest_calibrated_force()
                    force_history.append(current_force)
                    if len(force_history) > 20:
                        force_history.pop(0)
                    
                    # Calculate derivative
                    if len(force_history) >= 3:
                        current_derivative = self.calculate_force_derivative(force_history)
                        peak_derivative_this_cycle = max(peak_derivative_this_cycle, abs(current_derivative))
                        
                        # Check if derivative threshold exceeded
                        if abs(current_derivative) >= derivative_threshold_initial:
                            self.axis.stop()
                            while self.axis.is_busy():
                                time.sleep(0.01)
                            contact_found = True
                            contact_pos_um = self.axis.get_position(Units.LENGTH_MICROMETRES)
                            break
                    
                    time.sleep(0.02)
                
                if contact_found:
                    contact_positions_um.append(contact_pos_um)
                    peak_derivatives.append(peak_derivative_this_cycle)
                    self.update_status_message(f"Pre-cal: Oscillation {osc_num + 1}/5 - Contact at {contact_pos_um/1000.0:.3f}mm, peak dF/dt={peak_derivative_this_cycle:.4f} N/s")
                else:
                    self.update_status_message(f"Pre-cal: Oscillation {osc_num + 1}/5 - No contact detected", error=True)
            
            # Calculate averages
            if len(contact_positions_um) < 2:
                self.update_status_message("Pre-cal: Insufficient contact data for averaging", error=True)
                # Return to start
                self.axis.move_absolute(
                    position=start_position_um,
                    unit=Units.LENGTH_MICROMETRES,
                    wait_until_idle=True,
                    velocity=0.5,
                    velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND
                )
                return (None, None)
            
            avg_contact_position_um = sum(contact_positions_um) / len(contact_positions_um)
            avg_gap_mm = (avg_contact_position_um - start_position_um) / 1000.0
            
            if len(peak_derivatives) > 0:
                avg_peak_derivative = sum(peak_derivatives) / len(peak_derivatives)
            else:
                avg_peak_derivative = derivative_threshold_initial  # Fallback
            
            self.update_status_message(f"Pre-cal: RESULTS - Avg gap: {avg_gap_mm:.3f}mm, Avg peak dF/dt: {avg_peak_derivative:.4f} N/s")
            self.update_status_message(f"Pre-cal: Contact measurements: {len(contact_positions_um)} samples")
            
            # Phase 3: Return to starting position
            self.update_status_message(f"Pre-cal: Returning to start position {start_position_mm:.3f}mm...")
            self.axis.move_absolute(
                position=start_position_um,
                unit=Units.LENGTH_MICROMETRES,
                wait_until_idle=True,
                velocity=0.5,  # 500 µm/s return speed
                velocity_unit=Units.VELOCITY_MILLIMETRES_PER_SECOND,
                acceleration=5.0,  # Normal acceleration for return
                acceleration_unit=Units.ACCELERATION_MILLIMETRES_PER_SECOND_SQUARED
            )
            
            # Final 5-second pause
            self.update_status_message("Pre-cal: Pausing 5 seconds before starting print...")
            time.sleep(5.0)
            
            self.update_status_message("=== PRE-CALIBRATION COMPLETE ===")
            return (avg_gap_mm, avg_peak_derivative)
            
        except Exception as e:
            self.update_status_message(f"Pre-calibration error: {e}", error=True)
            return (None, None)

    # ========== END PRE-CALIBRATION HELPERS ==========

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
        try:
            self.update_status_message("Starting post-print analysis...")
            
            # Check if we have a valid log directory
            if not hasattr(self, 'current_print_session_log_dir') or not self.current_print_session_log_dir:
                self.update_status_message("No log directory available for post-print analysis.")
                return
            
            if not os.path.exists(self.current_print_session_log_dir):
                self.update_status_message("Log directory does not exist for post-print analysis.")
                return
            
            # Import and run post-print analyzer
            from post_print_analyzer import PostPrintAnalyzer
            from pathlib import Path
            
            analyzer = PostPrintAnalyzer()
            
            # Get the daily log directory (parent of current print session)
            daily_log_dir = os.path.dirname(self.current_print_session_log_dir)
            
            # Find only the current session (most recent) instead of all sessions
            print(f"DEBUG: Looking for current session in daily dir: {daily_log_dir}")
            
            # Use the PostPrintAnalyzer method to find current session in daily directory
            current_session = analyzer.find_current_session_in_daily_dir(daily_log_dir)
            
            if not current_session:
                self.update_status_message("Post-print analysis: No current session found.")
                return
            
            print(f"DEBUG: Current session found: {current_session['date']}/{current_session['print_number']}")
            
            # Analyze the current session and track results
            total_plots = 0
            processed_sessions = 0
            
            try:
                session_results = analyzer.analyze_print_session(current_session)
                if session_results:
                    processed_sessions += 1
                    
                    # Count plots generated
                    plots_count = len([r for r in session_results if r.get('plot_path')])
                    total_plots += plots_count
                    
                    # Count total layers processed across all CSV files in this session
                    total_layers = sum(len(r.get('layers', [])) for r in session_results)
                    
                    if plots_count > 0:
                        session_name = f"{current_session['date']}/{current_session['print_number']}"
                        self.update_status_message(f"  📊 {session_name}: {total_layers} layers → {plots_count} plots")
                        
            except Exception as e:
                print(f"Error analyzing current session {current_session.get('print_number', 'Unknown')}: {e}")
        
            if processed_sessions > 0:
                self.update_status_message(f"Post-print analysis complete: {processed_sessions} session, {total_plots} plots generated.")
            else:
                self.update_status_message("Post-print analysis: No suitable data found for plotting.")
                
        except Exception as e:
            self.update_status_message(f"Error in post-print analysis: {e}")
            print(f"DEBUG: Post-print analysis error: {e}")
            import traceback
            traceback.print_exc()

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