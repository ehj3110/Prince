import os
import datetime
import usb.core
import pycrafter9000
import libs
import traceback
import numpy as np
import screeninfo
import threading
import shutil
import winsound # Added winsound import

from tkinter import *
from tkinter.ttk import *
import cv2
import time
import queue
from zaber_motion import Library
from zaber_motion.ascii import Connection
from zaber_motion import Units
import csv

from tkinter import messagebox
from SensorDataWindow import SensorDataWindow
from AutoHomeRoutine import AutoHomer
from PeakForceLogger import PeakForceLogger


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
        self.peak_force_logger = None

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

        column2_x = 550
        self.lbl16.place(x=column2_x, y=550)
        self.t16 = Entry(win)
        self.t16.place(x=column2_x, y=570)
        self.t16.insert(END, "1000") # Default Step Speed
        
        self.lbl19.place(x=column2_x, y=590)
        self.t19 = Entry(win)
        self.t19.place(x=column2_x, y=610)
        self.t19.insert(END, "500") # Default Overstep in µm
        
        self.lbl17.place(x=column2_x, y=630)
        self.t17 = Entry(win)
        self.t17.place(x=column2_x, y=650)
        self.t17.insert(END, "0") # Default Pause
        
        column3_x = 700
        self.lbl21.place(x=column3_x, y=550)
        self.t21 = Entry(win)
        self.t21.place(x=column3_x, y=570)
        self.t21.insert(END, "5") # Default Acceleration in mm/s² (e.g., 5.0 mm/s²)

        # --- Auto-Home Control Box ---
        frame_auto_home_y_start = 730 # Adjust this Y-coordinate as needed
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

        # Add the stiffness display label within the Auto-Home frame
        self.stiffness_var = StringVar() 
        self.stiffness_var.set("Stiffness: --- N/m") # Default text also includes N/m
        self.lbl_stiffness_display_in_frame = Label(self.frame_auto_home, textvariable=self.stiffness_var, font='Helvetica 10 bold')
        self.lbl_stiffness_display_in_frame.grid(row=0, column=7, padx=10, pady=2, sticky=W)

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
        try:
            self.controller = pycrafter9000.dmd()
            self.application = libs.Application()
            self.controller.stopsequence() # Stop any existing sequence first
            self.controller.changemode(3) # Pattern on the fly mode
            # self.controller.hdmi() # Not needed if using pattern on the fly and not projecting video
        except usb.core.USBError as e:
            self.update_status_message(f"USBError initializing DLP: {e}. Check DLP connection and power. Printing may fail.", error=True)
            self.controller = None # Ensure controller is None if init fails
            # Optionally, re-raise or handle more gracefully if DLP is critical for all operations
        except Exception as e:
            self.update_status_message(f"Error initializing DLP controller: {e}. Printing may fail.", error=True)
            self.controller = None # Ensure controller is None if init fails
            traceback.print_exc()

        Library.enable_device_db_store()
        try:
            connection = Connection.open_serial_port("COM3")
            device_list = connection.detect_devices()
            if not device_list:
                self.update_status_message("Zaber device not found on COM3. Stage control will fail.", error=True)
                self.axis = None # Ensure axis is None
                # Consider if the application should exit or prevent operations requiring Zaber
            else:
                device = device_list[0]
                self.axis = device.get_axis(1)
                self.axis.home()
        except Exception as e:
            self.update_status_message(f"Error initializing Zaber stage: {e}. Stage control will fail.", error=True)
            self.axis = None # Ensure axis is None
            traceback.print_exc()
        
        # Set default acceleration for the Zaber stage upon initialization
        if self.axis: # Only if axis was successfully initialized
            try:
                desired_startup_accel_physical_ums2 = 100000 # µm/s² (equivalent to 100 mm/s²)
                
                # Get current acceleration setting value for diagnostics
                current_accel_val_before = self.axis.settings.get("accel")

                # Set the "accel" setting, explicitly providing the unit of the value
                self.axis.settings.set(
                    "accel", 
                    desired_startup_accel_physical_ums2, 
                    unit=Units.ACCELERATION_MICROMETRES_PER_SECOND_SQUARED
                )
                
                # Verify by getting the setting again, explicitly requesting µm/s²
                current_accel_val_after = self.axis.settings.get("accel", unit=Units.ACCELERATION_MICROMETRES_PER_SECOND_SQUARED)

                if abs(current_accel_val_after - desired_startup_accel_physical_ums2) > 1: # Allow for small rounding
                     self.update_status_message(f"WARNING: Readback acceleration {current_accel_val_after} µm/s² differs from desired {desired_startup_accel_physical_ums2} µm/s².", error=True)

            except Exception as e:
                self.update_status_message(f"Error setting default stage acceleration: {e}", error=True)
                traceback.print_exc() 
        else:
            self.update_status_message("Zaber axis not available, skipping acceleration setup.", warning=True)

        # --- Initial t.insert values ---
        self.t1.delete(0, 'end')
        self.t1.insert(END, "C:\\Users\\cheng sun\\BoyuanSun\\Slicing\\Calibration\\Power_Grayscale")
        self.t4.delete(0, 'end')
        self.t4.insert(END, "0")
        self.t9.delete(0, 'end')
        self.t9.insert(END, "0")
        self.t10.delete(0, 'end')
        self.t10.insert(END, "5")
        self.t11.delete(0, 'end')
        self.t11.insert(END, "1")
        self.t11_2.delete(0, 'end')
        self.t11_2.insert(END, "1")
        self.t14.delete(0, 'end')
        self.t14.insert(END, "1")

        # --- Screeninfo, window_name, black_image ---
        screen_id = 0
        self.screen = screeninfo.get_monitors()[screen_id]
        self.window_name = 'show'
        self.black_image = np.zeros((1600, 2560))

        self.update_auto_home_button_state()
        self.update_status_message("System Ready.")

        # Stiffness display setup
        self.stiffness_var = StringVar() 
        self.stiffness_var.set("Stiffness: --- N/m") # Default text also includes N/m
        self.lbl_stiffness_display_in_frame = Label(self.frame_auto_home, textvariable=self.stiffness_var, font='Helvetica 10 bold')
        self.lbl_stiffness_display_in_frame.grid(row=0, column=7, padx=10, pady=2, sticky=W)

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

    # IMPORTANT: Ensure input_directory method sets self.active_instruction_file_path
    # Example:
    # def input_directory(self):
    #     # ...
    #     # After determining instruction_file_actual_path:
    #     self.active_instruction_file_path = instruction_file_actual_path
    #     self.t2.delete(0, END)
    #     self.t2.insert(0, self.active_instruction_file_path)
    #     # ...
    #     # The call to self.sensor_data_window_instance.configure_automated_layer_logging
    #     # should ideally be removed from here and handled in start_print_thread if it's per-print session.
    #     # If it remains, SensorDataWindow needs to be robust to re-configuration.

    # IMPORTANT: Ensure generate_instruction_file method sets self.active_instruction_file_path
    # Example:
    # def generate_instruction_file(self):
    #     # ...
    #     # After file_path = filedialog.asksaveasfilename(...) and file is saved:
    #     if file_path:
    #         self.active_instruction_file_path = file_path
    #         self.t2.delete(0, END)
    #         self.t2.insert(0, self.active_instruction_file_path)
    #     # ...

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
        try:
            self.initilze_stage() 
            self.input_directory() 
            if not self.image_list:
                self.update_status_message("No images found or directory not set. Aborting print.")
                messagebox.showerror("Print Error", "Image directory not set or no images found.")
                return

            # --- Start Debug Prints ---
            val_t14 = self.t14.get()
            dlp_power = int(val_t14)

            val_t16 = self.t16.get()
            step_speed_um_s = float(val_t16) if val_t16 else 1000.0

            val_t17 = self.t17.get()
            layer_pause_s = float(val_t17) if val_t17 else 0.0

            val_t19 = self.t19.get()
            overstep_um_gui = float(val_t19) if val_t19 else 0.0

            val_t21 = self.t21.get()
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
        try:
            self.initilze_stage() 
            self.input_directory() 
            if not self.image_list:
                self.update_status_message("No images found or directory not set. Aborting print.")
                messagebox.showerror("Print Error", "Image directory not set or no images found.")
                return

            # --- Start Debug Prints ---
            val_t14 = self.t14.get()
            dlp_power = int(val_t14)

            val_t16 = self.t16.get()
            step_speed_um_s = float(val_t16) if val_t16 else 1000.0

            val_t17 = self.t17.get()
            layer_pause_s = float(val_t17) if val_t17 else 0.0

            val_t19 = self.t19.get()
            overstep_um_gui = float(val_t19) if val_t19 else 0.0 # RENAMED and now in µm

            val_t21 = self.t21.get()
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

    def start_print_thread(self, dlp_power, step_speed_um_s, layer_pause_s, overstep_um_gui, step_type_val_mms2, print_mode): # PARAM RENAMED
        try:
            if not self.image_list:
                self.update_status_message("Image list is empty. Cannot start print.", error=True)
                messagebox.showerror("Print Error", "Image list is empty. Please load images first.")
                if hasattr(self, 'b1'): self.b1.config(state=NORMAL)
                if hasattr(self, 'b10'): self.b10.config(state=NORMAL)
                return

            if not self.initilze_stage(): # Assuming initilze_stage returns True on success, False on failure
                self.update_status_message("Stage initialization failed. Cannot start print.", error=True)
                messagebox.showerror("Print Error", "Stage initialization failed.")
                if hasattr(self, 'b1'): self.b1.config(state=NORMAL)
                if hasattr(self, 'b10'): self.b10.config(state=NORMAL)
                return

            # --- Logging Directory Setup ---
            main_img_dir = self.t1.get() 
            if not main_img_dir or not os.path.isdir(main_img_dir):
                self.update_status_message(f"Invalid image directory: {main_img_dir}. Cannot start print.", error=True)
                messagebox.showerror("Print Error", f"Invalid image directory selected: {main_img_dir}")
                if hasattr(self, 'b1'): self.b1.config(state=NORMAL)
                if hasattr(self, 'b10'): self.b10.config(state=NORMAL)
                return

            self.current_print_log_base_dir = os.path.join(main_img_dir, "Printing_Logs")
            current_date_str = datetime.datetime.now().strftime("%Y-%m-%d")
            self.current_print_date_dir = os.path.join(self.current_print_log_base_dir, current_date_str)
            self.current_print_number = self._get_next_print_number(self.current_print_date_dir)
            
            self.current_print_session_log_dir = os.path.join(self.current_print_date_dir, f"Print {self.current_print_number}")

            os.makedirs(self.current_print_session_log_dir, exist_ok=True)
            self.update_status_message(f"Log directory created: {self.current_print_session_log_dir}")

            # --- Initialize PeakForceLogger for this print run ---
            try:
                # Define the specific CSV filename for this print run's peak force log
                peak_force_log_filename = f"PeakForce_Log_Print{self.current_print_number}.csv"
                peak_force_log_filepath = os.path.join(self.current_print_session_log_dir, peak_force_log_filename)

                self.peak_force_logger_instance = PeakForceLogger(
                    output_csv_filepath=peak_force_log_filepath, 
                    is_manual_log=False
                )
                self.update_status_message(f"PeakForceLogger initialized. Logging to: {peak_force_log_filepath}")
                # Pass this PFL instance to SensorDataWindow
                if hasattr(self, 'sensor_data_window_instance') and self.sensor_data_window_instance:
                    self.sensor_data_window_instance.set_peak_force_logger_for_print_run(self.peak_force_logger_instance)
                    self.update_status_message("PeakForceLogger instance passed to SensorDataWindow.")

                # Configure AutomatedLayerLogger via SensorDataWindow
                if hasattr(self, 'sensor_data_window_instance') and self.sensor_data_window_instance:
                    if main_img_dir: # Check the local variable main_img_dir from earlier in the function
                        self.sensor_data_window_instance.configure_automated_layer_logging(
                            main_image_dir=main_img_dir, # Use local variable
                            print_number=self.current_print_number,
                            date_str_for_dir=current_date_str, # Use local variable
                            log_directory=self.current_print_session_log_dir
                        )
                        self.update_status_message(f"AutomatedLayerLogger configured for print {self.current_print_number}.")
                    else:
                        self.update_status_message("Error: Main image directory (from t1) not set or invalid. Cannot configure AutomatedLayerLogger.", error=True)
                else:
                    self.update_status_message("SensorDataWindow not available. Cannot configure AutomatedLayerLogger.", error=True)
            except Exception as e:
                self.update_status_message(f"Critical Error initializing loggers: {e}. Print aborted.", error=True)
                traceback.print_exc()
                messagebox.showerror("Initialization Error", f"Failed to initialize logging components: {e}\nThe print process cannot start.")
                # Reset button states to allow user to try again or fix issue
                if hasattr(self, 'b1'): self.b1.config(state=NORMAL)    # Run-Cont.
                if hasattr(self, 'b10'): self.b10.config(state=NORMAL)   # Run-Step
                if hasattr(self, 'b4') and self.b4: self.b4.config(state=DISABLED) # Stop button
                return # IMPORTANT: Do not proceed to start the print_t thread

            # --- Start the actual print process in a new thread ---
            self.print_thread = threading.Thread(target=self.print_t, args=(
                dlp_power, 
                step_speed_um_s, 
                layer_pause_s, 
                overstep_um_gui, 
                step_type_val_mms2, 
                print_mode
            ))
            self.print_thread.daemon = True 
            self.print_thread.start()
            self.update_status_message(f"{print_mode.capitalize()} print thread started.")


        except Exception as e:
            self.update_status_message(f"An unexpected error occurred in start_print_thread: {e}", error=True)
            traceback.print_exc()
            messagebox.showerror("Critical Error", f"An unexpected error occurred: {e}")
            if hasattr(self, 'b1'): self.b1.config(state=NORMAL)
            if hasattr(self, 'b10'): self.b10.config(state=NORMAL)

    def print_t(self, dlp_power, step_speed_um_s, layer_pause_s, overstep_um_gui, step_type_val_mms2, print_mode): # PARAM RENAMED
        self.print_thread_exception_occurred = False # Initialize flag
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

                    # 3. Start Z-axis movement (non-blocking)
                    self.update_status_message(f"L{current_layer_num_for_display} (Cont.): Moving to {current_target_z_microns / 1000.0:.4f} mm at {calculated_continuous_velocity_um_s:.2f} um/s, Accel: {actual_acceleration_to_set_um_s2} µm/s²")
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

                    # 2. Exposure
                    if current_exposure_s > 0:
                        time.sleep(current_exposure_s)
                    else:
                        self.update_status_message(f"L{current_layer_num_for_display} (Stepped): Zero exposure time.", error=True)

                    # 3. Show black image after exposure for stepped mode
                    cv2.imshow(self.window_name, self.black_image)
                    cv2.waitKey(1)

                    # 4. Z-Axis Movement (Peel and Return)
                    self.update_status_message(f"Layer {current_layer_num_for_display} (Stepped): Starting peel sequence.")
                    z_exposure_pos_current_layer_i = (self.reference * 1000) - sum(self.thickness[k] for k in range(i) if k < len(self.thickness))
                    # actual_overstep_microns is now directly available

                    # --- Calculate z_peel_peak and z_return_pos ---
                    thickness_of_next_layer_microns = 0.0
                    if i < num_layers - 1: # If not the last layer
                        if (i + 1) < len(self.thickness):
                            thickness_of_next_layer_microns = float(self.thickness[i+1])
                        else:
                            self.update_status_message(f"Warning: Thickness for next layer {i+2} not found. Using 0 for peel calc.", error=True)
                            thickness_of_next_layer_microns = 0.0 
                    # For the last layer, thickness_of_next_layer_microns remains 0.
                    
                    total_peel_lift_microns = thickness_of_next_layer_microns + actual_overstep_microns
                    z_peel_peak = current_target_z_microns - total_peel_lift_microns
                    z_return_pos = current_target_z_microns - thickness_of_next_layer_microns
                    # Original calculation for z_return_pos based on z_peel_peak:
                    # z_return_pos_alt = z_peel_peak + actual_overstep_microns 
                    # This should yield the same as current_target_z_microns - thickness_of_next_layer_microns
                    # Using the direct calculation for z_return_pos for clarity.

                    self.update_status_message(f"Layer {current_layer_num_for_display} (Stepped): Peel Peak Target: {z_peel_peak/1000.0:.4f} mm, Return Target: {z_return_pos/1000.0:.4f} mm")

                    # --- Start monitoring for peak force and work ---
                    if self.peak_force_logger_instance and \
                       self.sensor_data_window_instance and \
                       self.sensor_data_window_instance.sensor_window.winfo_exists():
                        # Check if the PFL instance in SensorDataWindow is the one for this print run
                        # This check might be redundant if set_peak_force_logger_for_print_run correctly manages the instance.
                        # However, it's a safeguard.
                        if self.sensor_data_window_instance.peak_force_logger == self.peak_force_logger_instance:
                            z_peel_peak_mm = z_peel_peak / 1000.0
                            z_return_pos_mm = z_return_pos / 1000.0
                            # Call start_monitoring_for_layer directly on the instance we know is for the print run
                            self.peak_force_logger_instance.start_monitoring_for_layer(
                                current_layer_num_for_display,
                                z_peel_peak_mm,
                                z_return_pos_mm
                            )
                            self.update_status_message(f"PFL monitoring started for L{current_layer_num_for_display}")
                        else:
                            self.update_status_message(f"PFL instance mismatch in print_t for L{current_layer_num_for_display}. Shading/PFL log might be incorrect.", warning=True)
                    # --- Z-Axis Movement (Peel and Return) ---
                    self.axis.move_absolute(
                        position=z_peel_peak, # Now z_peel_peak is defined
                        unit=Units.LENGTH_MICROMETRES,
                        wait_until_idle=True,
                        velocity=actual_step_speed_um_s,
                        velocity_unit=Units.VELOCITY_MICROMETRES_PER_SECOND,
                        acceleration=actual_acceleration_to_set_um_s2, 
                        acceleration_unit=Units.ACCELERATION_MICROMETRES_PER_SECOND_SQUARED
                    )

                    z_return_pos = z_peel_peak + actual_overstep_microns
                    self.update_status_message(f"Stepped L{current_layer_num_for_display}: Returning to {z_return_pos / 1000.0:.4f} mm (Target for next layer, Accel: {actual_acceleration_to_set_um_s2} µm/s²)")
                    self.axis.move_absolute(
                        position=z_return_pos, 
                        unit=Units.LENGTH_MICROMETRES,
                        wait_until_idle=True, 
                        velocity=actual_step_speed_um_s,
                        velocity_unit=Units.VELOCITY_MICROMETRES_PER_SECOND,
                        acceleration=actual_acceleration_to_set_um_s2, 
                        acceleration_unit=Units.ACCELERATION_MICROMETRES_PER_SECOND_SQUARED
                    )
                    z_at_previous_exposure_microns = z_return_pos

                    # --- Stop monitoring and log peak/work ---
                    if self.peak_force_logger_instance and \
                       self.sensor_data_window_instance and \
                       self.sensor_data_window_instance.sensor_window.winfo_exists():
                        # Similar to starting, ensure we're acting on the correct PFL instance.
                        if self.sensor_data_window_instance.peak_force_logger == self.peak_force_logger_instance:
                            self.peak_force_logger_instance.stop_monitoring_and_log_peak() # Removed argument
                            self.update_status_message(f"PFL monitoring stopped and logged for L{current_layer_num_for_display}")
                        else:
                            self.update_status_message(f"PFL instance mismatch on stop in print_t for L{current_layer_num_for_display}. PFL log might be affected.", warning=True)

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
            self.print_thread_exception_occurred = True # Set flag
        finally:
            self.update_status_message("Print thread finishing...")
            if hasattr(self, 'win') and self.win.winfo_exists(): # Ensure window exists before cv2 operations
                cv2.destroyAllWindows() # Close OpenCV windows
            
            if hasattr(self, 'controller') and self.controller:
                try:
                    if hasattr(self.controller, 'stopsequence'):
                        self.controller.stopsequence()
                    else:
                        self.update_status_message("Warning: controller has no stopsequence method.", warning=True)
                    
                    # Replace projectblack with changemode(3) and power(0)
                    if hasattr(self.controller, 'changemode') and hasattr(self.controller, 'power'):
                        self.controller.changemode(3) # Pattern on the fly
                        self.controller.power(current=0) # LED off
                        self.update_status_message("DLP set to pattern on the fly mode, LED off.")
                    else:
                        self.update_status_message("Info: controller missing changemode/power for final DLP state.", warning=True)
                except Exception as e_dlp_final:
                    self.update_status_message(f"Error during final DLP cleanup: {e_dlp_final}", error=True)
            else:
                self.update_status_message("Warning: controller not available for final cleanup.", warning=True)
            
            # Update status file to "stopped" or "completed" or "error"
            status_to_write = "stopped" # Default if stopped by user
            if self.print_thread_exception_occurred:
                status_to_write = "error"
            elif not self.flag: # If flag is still false, it means it completed normally
                status_to_write = "completed"
            
            if self.current_print_session_log_dir:
                status_file_path = os.path.join(self.current_print_session_log_dir, "print_status.txt")
                try:
                    with open(status_file_path, 'w') as sf:
                        sf.write(status_to_write)
                    self.update_status_message(f"Print status '{status_to_write}' written to {status_file_path}", success=True)
                except Exception as e_stat:
                    self.update_status_message(f"Error writing final print status: {e_stat}", warning=True)

            # Resetting UI elements - scheduled to run in the main Tkinter thread
            def _reset_ui_on_main_thread():
                if hasattr(self, 'b1'): self.b1.config(state=NORMAL)
                if hasattr(self, 'b10'): self.b10.config(state=NORMAL)
                if hasattr(self, 'b4'): self.b4.config(state=DISABLED)
                
                # Assuming b_pause_resume might exist, as per previous structure
                if hasattr(self, 'b_pause_resume'): 
                    self.b_pause_resume.config(text="Pause Print", state=DISABLED)
                
                # Reset progress bar and layer count
                if hasattr(self, 'p1'): self.p1['value'] = 0
                if hasattr(self, 'current_layer_num_var'): self.current_layer_num_var.set("Layer: 0/0")
                if hasattr(self, 'lbl15'): self.lbl15.config(text='Estimate Time: ---')
                
                self.update_status_message("Print UI elements reset.")

            if hasattr(self, 'win') and self.win.winfo_exists():
                self.win.after(0, _reset_ui_on_main_thread)
            else:
                # If window doesn't exist, try to run directly (might not be safe, but last resort)
                # This case should ideally not happen if UI elements are still being accessed.
                try:
                    _reset_ui_on_main_thread()
                except Exception as e_direct_reset:
                    print(f"Error during direct UI reset (window might be gone): {e_direct_reset}")

            # Add stage return logic using relative offset
            try:
                if hasattr(self, 'axis') and self.axis:
                    # Move the stage by a relative offset
                    self.update_status_message(f"Print finished/stopped. Moving stage by offset: {self.offset} mm.")
                    self.axis.move_relative(
                        position=self.offset, # Use the offset defined in __init__
                        unit=Units.LENGTH_MILLIMETRES,
                        wait_until_idle=True # Wait for the move to complete
                    )
                    current_pos_after_offset = self.axis.get_position(unit=Units.LENGTH_MILLIMETRES)
                    self.update_status_message(f"Stage moved by offset. Current position: {current_pos_after_offset:.4f} mm.")
                else:
                    self.update_status_message("Zaber axis not available for final relative move.", warning=True)
            except Exception as e_stage_return:
                self.update_status_message(f"Error during final stage relative move: {e_stage_return}", error=True)
                traceback.print_exc()

            self.flag = False # Reset flag for next print
            self.pause_flag = False # Reset pause flag

    def set_home(self):
        self.reference = float(self.t4.get())
        # self.axis.move_relative(position=self.offset, unit=Units.LENGTH_MILLIMETERS, # Assuming self.offset is a relative move
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
        self.pause_flag = False # Ensure pause is also cleared on stop
        
        # Attempt to stop DLP sequence and set to pattern on the fly, LED off
        if hasattr(self, 'controller') and self.controller:
            try:
                if hasattr(self.controller, 'stopsequence'):
                    self.controller.stopsequence()
                else:
                    self.update_status_message("Warning: controller has no stopsequence method during stop.", warning=True)
                
                # Replace projectblack with changemode(3) and power(0)
                if hasattr(self.controller, 'changemode') and hasattr(self.controller, 'power'):
                    self.controller.changemode(3) # Pattern on the fly
                    self.controller.power(current=0) # LED off
                    self.update_status_message("DLP set to pattern on the fly mode, LED off on stop.")
                else:
                    self.update_status_message("Info: controller missing changemode/power for DLP stop state.", warning=True)
            except Exception as e:
                self.update_status_message(f"Error during DLP stop: {e}", error=True)
        else:
            self.update_status_message("DLP controller not available, cannot send stop/cleanup commands.", warning=True)

        # Disable the stop button itself once clicked, re-enabled when print finishes/resets
        if hasattr(self, 'b4'): 
            self.b4.config(state=DISABLED)
        
        # Note: Re-enabling b1 and b10 should happen in the print_t finally block
        # to ensure the thread has fully terminated before allowing a new print to start.
        # Disable the auto-home button during stop
        if hasattr(self, 'b_auto_home'):
            self.b_auto_home.config(state=DISABLED)

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
            (
                self.image_list, 
                self.exposure_time,  # Corresponds to exposure_time_list
                self.thickness,      # Corresponds to thickness_list
                self.step_speed_list,
                self.overstep_distance_list,
                self.step_type_list,  # This will hold the 'Acceleration' values from the file
                self.pause_list,
                self.intensity_list
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

            # Attempt to update SensorDataWindow logging paths
            if self.sensor_data_window_instance and hasattr(self.sensor_data_window_instance, 'attempt_logging_path_setup'):
                self.sensor_data_window_instance.attempt_logging_path_setup()

            print(f"DEBUG: MyWindow.input_directory AFTER set_image_directory. MyWindow.image_list length: {len(self.image_list)}, Application.image_list length: {len(self.application.image_list)}") # Add this

            if not self.image_list:
                self.update_status_message("No image data loaded from instruction file.")
                messagebox.showwarning("File Info", f"No image data was loaded from the instruction file in:\\n{path}")
            else:
                self.update_status_message(f"Loaded {len(self.image_list)} layers from instruction file.")

        except ValueError as e:
            self.update_status_message(f"Error processing instruction file: {e}. Check file format and content.")
            messagebox.showerror("File Error", f"Could not process the instruction file in '{path}'.\\nDetails: {e}\\nEnsure it matches the expected format (9 columns, tab-separated) and numeric values are correct.")
            self.active_instruction_file_path = None # Clear on error
            # Clear lists to prevent using old/corrupted data
            self.image_list = []
            self.exposure_time = []
            self.thickness = []
            self.step_speed_list = []
            self.overstep_distance_list = []
            self.step_type_list = []
            self.pause_list = []
            self.intensity_list = []
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
        path = str(self.t1.get()) # This is the directory for slices, e.g., "C:\\Slices\\MyPrint"
        thickness = str(self.t10.get())
        base = str(self.t11_2.get())
        time_val = str(self.t11.get())
        intensity = str(self.t14.get())
        step_speed = str(self.t16.get())
        overstep_distance = str(self.t19.get())
        acceleration_val = str(self.t21.get())
        pause = str(self.t17.get())
        
        # Call the application's method to generate instructions.
        # We will ignore its return value, assuming it prints its own status and creates the file.
        self.application.generate_instructions(
            path=path, 
            thickness=thickness, 
            base=base, 
            time=time_val, 
            intensity=intensity, 
            step_speed=step_speed, 
            overstep_distance=overstep_distance, 
            step_type=acceleration_val, 
            pause=pause
        )
        
        # Now, Prince_Segmented_06042025.py will construct the expected path itself.
        # The instruction file is expected to be named after the directory 'path' and be inside it.
        expected_instruction_filename = os.path.basename(os.path.normpath(path)) + ".txt"
        constructed_instruction_file_path = os.path.join(path, expected_instruction_filename)

        if os.path.exists(constructed_instruction_file_path):
            self.active_instruction_file_path = constructed_instruction_file_path
            # The message from libs.py ("Instruction file generated: ...") should cover the generation part.
            # This message confirms Prince_Segmented sees it and sets it as active.
            self.update_status_message(f"Instruction file found at {self.active_instruction_file_path} and set as active.", success=True)
        else:
            # This message indicates that after libs.py was called, the file wasn't found where expected.
            self.update_status_message(f"Instruction file generation was called by Prince_Segmented, but file not found at expected path: {constructed_instruction_file_path}.", error=True)
            self.active_instruction_file_path = None

        # Attempt to update SensorDataWindow logging paths
        if self.sensor_data_window_instance and hasattr(self.sensor_data_window_instance, 'attempt_logging_path_setup'):
            self.sensor_data_window_instance.attempt_logging_path_setup()

    def update_status_message(self, message, error=False, warning=False, success=False): # Added success parameter
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
        elif warning:
            print(f"WARNING: {log_message}")
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
            result_callback=self.handle_auto_home_result, # This now expects to be called with 2 args
            parent_gui=self.win
        )
        self.auto_home_thread.start()

    def handle_auto_home_result(self, new_home_position, message): # REVERTED: definition takes 2 args + self
        self.update_status_message(message)
        retrieved_stiffness = None # Initialize
        if self.auto_home_thread and hasattr(self.auto_home_thread, 'calculated_stiffness'):
            retrieved_stiffness = self.auto_home_thread.calculated_stiffness

        if new_home_position is not None:
            self.reference = new_home_position
            self.t4.delete(0, 'end')
            self.t4.insert(END, f"{new_home_position:.4f}")
            self.update_status_message(f"New Home set to: {new_home_position:.4f} mm")
            
            if retrieved_stiffness is not None: # Check the retrieved stiffness
                # Only update the value, keep the "Stiffness: " prefix
                self.stiffness_var.set(f"{retrieved_stiffness:.2f} N/m")
            else:
                self.stiffness_var.set("--- N/m (not calculated)")
            messagebox.showinfo("Auto-Home Complete", f"New home position set to: {new_home_position:.4f} mm")
        else:
            self.stiffness_var.set("--- N/m (failed)")
            messagebox.showerror("Auto-Home Failed", message)
        
        self.update_auto_home_button_state()

    def on_closing(self):
        if self.auto_home_thread and self.auto_home_thread.is_alive():
            self.update_status_message("Attempting to stop Auto-Home routine...")
            self.auto_home_thread.stop()
            self.auto_home_thread.join(timeout=2.0)
            if self.auto_home_thread.is_alive():
                print("Warning: Auto-Home thread did not terminate cleanly.")

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


if __name__ == '__main__':
    Library.enable_device_db_store()
    window = Tk()
    mywin = MyWindow(window)
    window.title('Prince - Main Window')
    window.geometry("1200x800+10+10")
    window.protocol("WM_DELETE_WINDOW", mywin.on_closing)
    window.mainloop()