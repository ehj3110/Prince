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
from AutoHomeRoutine import AutoHomer
from support_modules.motion_controller import MotionController
from support_modules.PatternBatchController import PatternBatchController


class MyWindow:
    def __init__(self, win):
        instruction = '''Pattern Mode - Check list:
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

        self.cache_clear_layer = 100000
        self.time1 = 1000

        # --- Existing Canvases and Labels (adjust placement if they conflict with new frames) ---
        self.canvas1 = Canvas(win, height=200, width=270, bg="#FFEFD5")
        self.canvas1.place(x=70, y=390)
        
        self.canvas2 = Canvas(win, height=200, width=500, bg="#FFEFD5")
        self.canvas2.place(x=370, y=390)

        # Prince header with purple background box
        self.header_frame = tk.Frame(win, bg='#834bd0', relief='solid', borderwidth=3, highlightbackground='#834bd0', highlightthickness=0)
        self.header_frame.place(x=405, y=26, width=270, height=71)
        self.lbl0 = tk.Label(self.header_frame, text='Prince\nPattern Mode', font='Helvetica 22 bold', bg='#834bd0', fg='white')
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

        # COLUMN 2: Step Speed, Pause
        column2_x = 550
        self.lbl16.place(x=column2_x, y=420)
        self.t16 = Entry(win)
        self.t16.place(x=column2_x, y=440)
        self.t16.insert(END, "50") # Default Step Speed
        
        self.lbl17.place(x=column2_x, y=460)
        self.t17 = Entry(win)
        self.t17.place(x=column2_x, y=480)
        self.t17.insert(END, "1") # Default Pause

        # --- Existing Layer Logger instantiation removed ---
        
        # --- Define Entry Widgets ---
        self.t1 = Entry(width=140)
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
        self.t1.place(x=180, y=150)

        self.lbl4.place(x=50, y=230) # Moved up from 260
        self.t4.place(x=50, y=250) # Moved up from 280
        self.lbl5.place(x=600, y=180)
        self.lbl6.place(x=840, y=0)
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
        self.b4 = Button(win, text='Stop', command=self.stop)
        self.b2 = Button(win, text='Set Home', command=self.set_home)
        self.b3 = Button(win, text='Get Position', command=self.get_position)
        self.b5 = Button(win, text='Move Down', command=self.movedown)
        self.b6 = Button(win, text='Move Up', command=self.moveup)
        self.b7 = Button(win, text='Simple input txt generator', command=self.simple_txt)
        self.b_pre_encode = Button(win, text='Pre-Encode Patterns', command=self.pre_encode_patterns)

        # Run buttons and Stop button aligned with right side buttons at y=95
        self.b1.place(x=50, y=95)
        self.b10.place(x=140, y=95)
        self.b4.place(x=230, y=95)  # Stop moved to where Set Direct was
        
        # Z-Axis controls back at original position
        self.b2.place(x=50, y=200)
        self.b3.place(x=140, y=200)
        
        # Move Up/Down buttons stay in stage control area
        self.b5.place(x=100, y=500)
        self.b6.place(x=200, y=500)
        self.b7.place(x=400, y=550)
        self.b_pre_encode.place(x=560, y=550)  # Next to txt generator

        # --- Initialize active_logging_windows_filepath AFTER t1 and status_message_var are created ---
        # self.active_logging_windows_filepath = None
        # self._check_default_logging_windows_file() # MOVED HERE, now status_message_var exists

        # --- Controller, Application, Zaber Setup ---
        self.controller = pycrafter9000.dmd()
        self.application = libs.Application()
        self.controller.wakeup()  # Ensure DLP is not in standby mode
        time.sleep(0.1)  # Allow wakeup to complete
        self.controller.stopsequence()
        self.controller.power(current=0)  # Set power to 0 BEFORE video mode to prevent flash
        time.sleep(0.1)  # Small delay to ensure power is off
        self.controller.changemode(3)
        self.controller.hdmi()
        self.update_status_message("DLP initialized: Woken up, Power=0, Video Mode, HDMI input")

        Library.enable_device_db_store()
        connection = Connection.open_serial_port("COM3")
        device_list = connection.detect_devices()
        device = device_list[0]
        self.axis = device.get_axis(1)
        self.axis.home(wait_until_idle=False)
        
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

        self.update_status_message("System Ready.") # Example of setting initial status
    
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
                
                # Calculate remaining movement time (lift + retract)
                remaining_movement_time = 0.0
                
                # Get default parameters from GUI (fallbacks)
                default_overstep = float(self.t19.get()) if hasattr(self, 't19') and self.t19.get() else 0.0
                default_speed = float(self.t16.get()) if hasattr(self, 't16') and self.t16.get() else 1000.0
                
                # Calculate movement time for each remaining layer
                for layer_idx in range(current_layer_index, total_layers):
                    # Get layer-specific parameters
                    layer_overstep = self.overstep_distance_list[layer_idx] if hasattr(self, 'overstep_distance_list') and layer_idx < len(self.overstep_distance_list) else default_overstep
                    layer_speed = self.step_speed_list[layer_idx] if hasattr(self, 'step_speed_list') and layer_idx < len(self.step_speed_list) else default_speed
                    
                    # Lift time calculation
                    lift_time = (layer_overstep / layer_speed) if layer_speed > 0 else 0
                    
                    # Retract time calculation
                    retract_time = (layer_overstep / layer_speed) if layer_speed > 0 else 0
                    
                    # Additional overhead per layer
                    # Based on empirical testing (7s observed vs 5.2s calculated):
                    # - Stage acceleration/deceleration and idle transitions: ~0.5-1.0s
                    # - Image loading and display (cv2.imshow + waitKey): ~0.2-0.5s
                    # - DLP power changes (2x per layer): ~0.2-0.4s
                    # - Diagnostics and force readings (pre-peel, pre-return): ~0.1-0.3s
                    # - Phase changes, GUI updates, communications: ~0.2s
                    layer_overhead = 1.8  # Total empirical overhead per layer
                    
                    # Add to total movement time
                    remaining_movement_time += lift_time + retract_time + layer_overhead
                
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

            overstep_um_gui = 0.0  # Overstep removed from pattern mode GUI

            step_type_val_mms2 = 100.0  # Hardcoded acceleration: 100 mm/s²
            
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

            overstep_um_gui = 0.0  # Overstep removed from pattern mode GUI

            step_type_val_mms2 = 100.0  # Hardcoded acceleration: 100 mm/s²

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
        if not os.path.exists(date_specific_log_dir):
            return 1
        
        existing_prints = [d for d in os.listdir(date_specific_log_dir) 
                          if os.path.isdir(os.path.join(date_specific_log_dir, d)) and d.startswith("Print ")]
        
        if not existing_prints:
            return 1
        
        print_numbers = []
        for dirname in existing_prints:
            try:
                num = int(dirname.replace("Print ", ""))
                print_numbers.append(num)
            except ValueError:
                continue
        
        return max(print_numbers) + 1 if print_numbers else 1

    def start_print_thread(self, dlp_power, step_speed_um_s, layer_pause_s, overstep_um_gui, step_type_val_mms2, print_mode): # PARAM RENAMED
        # The try block should start here, encompassing all setup and thread starting
        try:
            self.update_status_message(f"Starting {print_mode} Print Setup...")
            
            path = str(self.t1.get())
            if not path or not os.path.isdir(path):
                self.update_status_message("Error: Image directory not set or invalid.", error=True)
                messagebox.showerror("Setup Error", "Please set a valid image directory first.", parent=self.win)
                return

            # Automated logging removed for pattern mode
            
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
            # Cleanup placeholder - all sensor and logging functionality removed
            pass
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
            cv2.waitKey(1)
            self.update_status_message("OpenCV window initialized.")

            # DLP setup for pattern projection
            if hasattr(self, 'controller'):
                self.controller.power(current=0)  # Set power to 0 BEFORE mode change to prevent flash
                time.sleep(0.1)
                self.controller.changemode(0) # Switch to pattern sequence mode
                time.sleep(2.0) # Crucial delay for mode change to take effect
                self.controller.power(current=dlp_power) 
                self.update_status_message(f"DLP set to pattern mode, power: {dlp_power}.")
            else:
                self.update_status_message("DLP controller not available. Cannot control DLP.", error=True)
                # Decide if print should abort if DLP is not available
                # For now, it will continue, but images won't project.
            
            # Initialize Pattern Batch Controller for firmware pattern loading
            pattern_batch_controller = PatternBatchController(
                dlp_controller=self.controller,
                status_callback=lambda msg: self.update_status_message(msg)
            )
            self.update_status_message("Pattern Batch Controller initialized.")

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

                # DLP power setting removed from here - now handled within each mode (stepped/continuous)
                # to avoid setting power before exposure is ready

                # --- TARGET Z CALCULATION for current layer i ---
                current_target_z_microns = (self.reference * 1000) - sum(self.thickness[k] for k in range(i + 1) if k < len(self.thickness))

                # --- MODE-SPECIFIC OPERATIONS ---
                if print_mode == "continuous":
                    # PATTERN BATCH MODE - Process in batches of up to 400 patterns
                    
                    # Check if this is the start of a new batch
                    if i == 0:
                        self.update_status_message(f"DEBUG: batch_size = {pattern_batch_controller.batch_size}")
                    
                    if i % pattern_batch_controller.batch_size == 0:
                        batch_num = i // pattern_batch_controller.batch_size
                        start_idx = i
                        end_idx = min(i + pattern_batch_controller.batch_size, num_layers)
                        num_patterns_in_batch = end_idx - start_idx
                        is_first_batch = (batch_num == 0)
                        
                        self.update_status_message(f"\n{'='*60}")
                        self.update_status_message(f"BATCH {batch_num + 1}: Uploading patterns {start_idx + 1} to {end_idx}")
                        self.update_status_message(f"{'='*60}\n")
                        
                        # Check for pre-encoded file
                        from support_modules.PatternPreEncoder import PatternPreEncoder
                        pre_encoder = PatternPreEncoder(status_callback=self.update_status_message)
                        
                        encoded_file_path = self.active_instruction_file_path.replace('.txt', '.encoded')
                        use_pre_encoded = os.path.exists(encoded_file_path)
                        
                        if use_pre_encoded:
                            self.update_status_message(f"✓ Found pre-encoded file: {os.path.basename(encoded_file_path)}")
                            self.update_status_message("  Loading pre-encoded batch (FAST MODE)...")
                            
                            # Load pre-encoded data
                            encoded_data = pre_encoder.load_pre_encoded_batch(encoded_file_path)
                            
                            # Get exposure times from encoded data
                            batch_exposures = encoded_data['exposure_times']
                            
                            # Upload pre-encoded batch
                            upload_result = pattern_batch_controller.upload_pre_encoded_batch(
                                encoded_data=encoded_data,
                                is_first_batch=is_first_batch
                            )
                        else:
                            self.update_status_message("  No pre-encoded file found. Encoding on-the-fly...")
                            
                            # Get batch image paths and exposure times
                            batch_images = self.image_list[start_idx:end_idx]
                            batch_exposures = [self.exposure_time[j] if j < len(self.exposure_time) else 0.1 
                                              for j in range(start_idx, end_idx)]
                            
                            # Upload batch to DLP firmware (slow path - encoding on-the-fly)
                            upload_result = pattern_batch_controller.upload_batch(
                                image_paths=batch_images,
                                exposure_times=batch_exposures,
                                is_first_batch=is_first_batch
                            )
                        
                        # Start DLP sequence
                        pattern_batch_controller.start_sequence()
                        
                        # For first pattern in batch (pattern 0), expose stationary (base layer)
                        if is_first_batch:
                            base_exposure_time = batch_exposures[0]
                            self.update_status_message(f"\nBASE LAYER (Pattern 0): Exposing {base_exposure_time:.2f}s STATIONARY")
                            
                            # Set DLP power for base layer
                            if hasattr(self, 'controller'):
                                try:
                                    base_layer_power = int(self.intensity_list[0] if len(self.intensity_list) > 0 else dlp_power)
                                    self.controller.power(current=base_layer_power)
                                    self.update_status_message(f"Base Layer: DLP power set to {base_layer_power}")
                                except Exception as e:
                                    self.update_status_message(f"Base Layer: Could not set DLP power: {e}", error=True)
                            
                            # Wait for base layer exposure to complete
                            self.update_status_message(f"DEBUG: Sleeping {base_exposure_time:.2f}s for base layer exposure")
                            time.sleep(base_exposure_time)
                            
                            self.update_status_message(f"Base Layer: Exposure complete. Starting continuous motion...\n")
                            self.update_status_message(f"DEBUG: DLP should now be on pattern 1 (index 1)")
                            
                            # Calculate ONE continuous move for all remaining layers
                            # Assumption: All layers (except base) have same exposure time and thickness
                            remaining_layers = num_layers - 1
                            total_distance_um = sum(self.thickness[j] for j in range(1, num_layers))
                            total_time_s = sum(self.exposure_time[j] for j in range(1, num_layers))
                            continuous_velocity = total_distance_um / total_time_s
                            
                            # Get current position and calculate final position
                            current_position_mm = self.axis.get_position(Units.LENGTH_MILLIMETRES)
                            current_position_um = current_position_mm * 1000
                            final_position_um = current_position_um - total_distance_um
                            
                            self.update_status_message(f"\nCONTINUOUS MOTION:")
                            self.update_status_message(f"  Current position: {current_position_mm:.4f} mm")
                            self.update_status_message(f"  Layers: {remaining_layers}")
                            self.update_status_message(f"  Total distance: {total_distance_um} µm")
                            self.update_status_message(f"  Total time: {total_time_s:.2f} s")
                            self.update_status_message(f"  Velocity: {continuous_velocity:.2f} µm/s")
                            self.update_status_message(f"  Final position: {final_position_um/1000:.4f} mm")
                            self.update_status_message(f"  Starting continuous move NOW...\n")
                            
                            # Issue ONE continuous move for entire print
                            self.axis.move_absolute(
                                position=final_position_um,
                                unit=Units.LENGTH_MICROMETRES,
                                wait_until_idle=False,
                                velocity=continuous_velocity,
                                velocity_unit=Units.VELOCITY_MICROMETRES_PER_SECOND,
                                acceleration=actual_acceleration_to_set_um_s2,
                                acceleration_unit=Units.ACCELERATION_MICROMETRES_PER_SECOND_SQUARED
                            )
                            
                            # Wait for motion and DLP sequence to complete
                            # We know exactly how long this should take based on exposure times
                            self.update_status_message(f"  Print running for {total_time_s:.2f}s...")
                            self.update_status_message(f"  (Stage moving continuously, DLP advancing patterns)")
                            
                            # Sleep for the expected duration plus 1 second safety margin
                            time.sleep(total_time_s + 1.0)
                            
                            # Ensure stage motion is fully complete
                            self.update_status_message(f"  Verifying stage reached final position...")
                            self.axis.wait_until_idle()
                            
                            # Print complete
                            final_pos = self.axis.get_position(Units.LENGTH_MILLIMETRES)
                            self.update_status_message(f"\n✓ Continuous motion complete!")
                            self.update_status_message(f"  Final position: {final_pos:.4f} mm")
                            self.update_status_message(f"  Expected: {final_position_um/1000:.4f} mm")
                            self.update_status_message(f"  Error: {abs(final_pos - final_position_um/1000)*1000:.2f} µm")
                            
                            # Stop sequence
                            pattern_batch_controller.stop_sequence()
                            self.update_status_message(f"\nBatch complete.\n")
                            
                            # Break out of layer loop - print is done!
                            break
                        else:
                            # For subsequent batches (>400 layers), start motion immediately
                            # TODO: Implement multi-batch continuous motion
                            pass

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

                    # 2. Exposure
                    if current_exposure_s > 0:
                        time.sleep(current_exposure_s)
                    else:
                        self.update_status_message(f"L{current_layer_num_for_display} (Stepped): Zero exposure time.", error=True)

                    # 3. Show black image after exposure for stepped mode
                    cv2.imshow(self.window_name, self.black_image)
                    cv2.waitKey(1)
                    
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
                    
                    # PRE-MOVEMENT DIAGNOSTICS (force gauge removed)
                    try:
                        current_pos = self.axis.get_position(unit=Units.LENGTH_MICROMETRES)
                        self.update_status_message(f"PRE-PEEL L{current_layer_num_for_display}: Pos={current_pos/1000.0:.4f}mm")
                    except Exception as diag_e:
                        self.update_status_message(f"DEBUG L{current_layer_num_for_display}: Pre-movement diagnostics failed: {diag_e}")
                    
                    # Get current position
                    current_pos_um = self.axis.get_position(unit=Units.LENGTH_MICROMETRES)
                    
                    self.update_status_message(f"Stepped L{current_layer_num_for_display}: Peeling up to {z_peel_peak / 1000.0:.4f} mm (Speed: {actual_step_speed_um_s} um/s, Accel: {actual_acceleration_to_set_um_s2} µm/s²)")
                    
                    try:
                        # Use MotionController for lift
                        lift_result = self.motion_controller.execute_lift(
                            start_pos_um=current_pos_um,
                            target_pos_um=z_peel_peak,
                            base_velocity_um_s=actual_step_speed_um_s,
                            base_acceleration_um_s2=actual_acceleration_to_set_um_s2,
                            smooth_enabled=False,
                            smart_peel_enabled=False
                        )
                        
                        if lift_result['success']:
                            self.update_status_message(f"SUCCESS L{current_layer_num_for_display}: Peel movement completed")
                        else:
                            raise Exception(lift_result.get('error', 'Unknown lift error'))
                            
                    except Exception as peel_error:
                        self.update_status_message(f"ERROR L{current_layer_num_for_display}: Peel movement failed: {peel_error}", error=True)
                        # Log detailed diagnostics (force gauge removed)
                        try:
                            fault_status = self.axis.warnings.get_flags()
                            pos_after_fail = self.axis.get_position(unit=Units.LENGTH_MICROMETRES)
                            self.update_status_message(f"DIAGNOSTICS L{current_layer_num_for_display}: Fault={fault_status}, Pos={pos_after_fail/1000.0:.4f}mm", error=True)
                        except:
                            pass
                        raise  # Re-raise to trigger print abort

                    z_return_pos = z_peel_peak + actual_overstep_microns
                    
                    # PRE-RETURN DIAGNOSTICS (force gauge removed)
                    try:
                        current_pos = self.axis.get_position(unit=Units.LENGTH_MICROMETRES)
                        self.update_status_message(f"PRE-RETURN L{current_layer_num_for_display}: Pos={current_pos/1000.0:.4f}mm")
                    except Exception as diag_e:
                        self.update_status_message(f"DEBUG L{current_layer_num_for_display}: Pre-return diagnostics failed: {diag_e}")
                    
                    self.update_status_message(f"Stepped L{current_layer_num_for_display}: Returning to {z_return_pos / 1000.0:.4f} mm (Target for next layer, Accel: {actual_acceleration_to_set_um_s2} µm/s²)")
                    
                    # Get current position
                    current_pos_um = self.axis.get_position(unit=Units.LENGTH_MICROMETRES)
                    
                    try:
                        # Use MotionController for retraction
                        retraction_result = self.motion_controller.execute_retraction(
                            start_pos_um=current_pos_um,
                            target_pos_um=z_return_pos,
                            base_velocity_um_s=actual_step_speed_um_s,
                            base_acceleration_um_s2=actual_acceleration_to_set_um_s2,
                            smooth_enabled=False
                        )
                        
                        if retraction_result['success']:
                            self.update_status_message(f"SUCCESS L{current_layer_num_for_display}: Return movement completed")
                        else:
                            raise Exception(retraction_result.get('error', 'Unknown retraction error'))
                        
                    except Exception as return_error:
                        self.update_status_message(f"ERROR L{current_layer_num_for_display}: Return movement failed: {return_error}", error=True)
                        
                        # Failure logging removed - pattern mode only
                        self.update_status_message(f"STOPPING L{current_layer_num_for_display}: Halting print due to return error.", error=True)
                        
                        # Log detailed diagnostics (force gauge removed)
                        try:
                            fault_status = self.axis.warnings.get_flags()
                            pos_after_fail = self.axis.get_position(unit=Units.LENGTH_MICROMETRES)
                            self.update_status_message(f"DIAGNOSTICS L{current_layer_num_for_display}: Fault={fault_status}, Pos={pos_after_fail/1000.0:.4f}mm", error=True)
                            
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
                # Auto-logging removed for pattern mode

                if actual_layer_pause_s > 0:
                    time.sleep(actual_layer_pause_s)
                                
                progress_val = (i + 1) * 100 / num_layers 
                self.win.after(0, lambda p=progress_val, nl=num_layers, ci=i: self._update_gui_progress(p, nl, ci))

            # --- END OF LOOP ---
            if not self.flag: 
                 self.update_status_message("Print completed successfully.")
                 
                 # Stop DLP pattern sequence in pattern mode (already stopped in continuous mode)
                 if print_mode == "continuous":
                     # Already stopped in the batch complete section
                     pass
                 
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

            # Auto-logging removed for pattern mode

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

                # Instruction file saving logic removed for pattern mode\n            \n            self.update_status_message("Print thread finished.")

            # Clean up resources
            self._cleanup_print_resources()
            if hasattr(self, 'b1'): self.b1.config(state=NORMAL)
            if hasattr(self, 'b10'): self.b10.config(state=NORMAL)
            if hasattr(self, 'b4'): self.b4.config(state=DISABLED)
            self.print_thread = None

    def set_home(self):
        self.reference = float(self.t4.get())
        # Update the Z-axis position display to show home position (0.0)
        self.t4.delete(0, 'end')
        self.t4.insert(END, "0.0")
        self.update_status_message("Home Set") # Use update_status_message instead of direct t8 manipulation

    def get_position(self):
        self.t4.delete(0, 'end')
        # Get absolute position
        absolute_position = self.axis.get_position(unit=Units.LENGTH_MILLIMETRES)
        self.t4.insert(END, str(absolute_position))

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
            # Unpack instruction file (7 columns: no step_type, no sandwich_speed)
            (
                self.image_list, 
                self.exposure_time,
                self.thickness,
                self.step_speed_list,
                self.overstep_distance_list,
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

            if not self.image_list:
                self.update_status_message("No image data loaded from instruction file.")
                messagebox.showwarning("File Info", f"No image data was loaded from the instruction file in:\n{path}")
            else:
                self.update_status_message(f"Loaded {len(self.image_list)} layers from instruction file.")

        except ValueError as e:
            self.update_status_message(f"Error processing instruction file: {e}. Check file format and content.")
            messagebox.showerror("File Error", f"Could not process the instruction file in '{path}'.\nDetails: {e}\nEnsure it matches the expected format (7 columns, tab-separated) and numeric values are correct.")
            # Clear lists to prevent using old/corrupted data
            self.image_list = []
            self.exposure_time = []
            self.thickness = []
            self.step_speed_list = []
            self.overstep_distance_list = []
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
        path = str(self.t1.get())
        thickness = str(self.t10.get())
        base = str(self.t11_2.get())
        time_val = str(self.t11.get())
        intensity = str(self.t14.get())
        step_speed = str(self.t16.get())
        pause = str(self.t17.get())
        
        self.application.generate_instructions(
            path=path, 
            thickness=thickness, 
            base=base, 
            time=time_val, 
            intensity=intensity, 
            step_speed=step_speed, 
            overstep_distance="0",  # No overstep in pattern mode
            pause=pause
        )
        
        # Automatically load the generated instruction file
        self.input_directory()
    
    def pre_encode_patterns(self):
        """Pre-encode patterns from current instruction file for faster printing."""
        if not hasattr(self, 'active_instruction_file_path') or not self.active_instruction_file_path:
            messagebox.showerror("Error", "Please load an instruction file first!")
            return
        
        if not self.image_list or not self.exposure_time:
            messagebox.showerror("Error", "No patterns loaded. Load instruction file first!")
            return
        
        # Ask user to confirm
        response = messagebox.askyesno(
            "Pre-Encode Patterns",
            f"Pre-encode {len(self.image_list)} patterns?\n\n"
            f"This will take 1-2 minutes but makes future prints ~10x faster.\n\n"
            f"Continue?"
        )
        
        if not response:
            return
        
        self.update_status_message("Starting pre-encoding process...")
        
        try:
            from support_modules.PatternPreEncoder import PatternPreEncoder
            
            # Generate output filename
            base = os.path.splitext(self.active_instruction_file_path)[0]
            output_file = f"{base}.encoded"
            
            # Check if file already exists
            if os.path.exists(output_file):
                overwrite = messagebox.askyesno(
                    "File Exists",
                    f"Pre-encoded file already exists:\n{output_file}\n\nOverwrite?"
                )
                if not overwrite:
                    self.update_status_message("Pre-encoding cancelled.")
                    return
            
            # Create pre-encoder and encode
            pre_encoder = PatternPreEncoder(status_callback=self.update_status_message)
            
            result = pre_encoder.pre_encode_batch(
                image_paths=self.image_list,
                exposure_times=self.exposure_time,
                output_file=output_file
            )
            
            # Show success message
            messagebox.showinfo(
                "Pre-Encoding Complete!",
                f"✓ Pre-encoded {result['num_patterns']} patterns\n"
                f"✓ Saved to: {os.path.basename(output_file)}\n"
                f"✓ File size: {result['file_size_mb']:.2f} MB\n"
                f"✓ Encoding time: {result['encoding_time_s']:.1f}s\n\n"
                f"Future prints will automatically use this file\n"
                f"and upload ~10x faster!"
            )
            
        except Exception as e:
            self.update_status_message(f"Pre-encoding failed: {e}", error=True)
            messagebox.showerror("Pre-Encoding Error", f"Failed to pre-encode patterns:\n{e}")
            traceback.print_exc()
    
    def update_status_message(self, message, error=False):
        """Updates the status message label and logs to console."""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        
        # Terminal output
        if error:
            print(f"ERROR: {log_message}")
        else:
            print(f"Status: {log_message}")
        
        # Update status label
        try:
            if self.win.winfo_exists():
                self.status_message_var.set(message)
                self.win.update_idletasks()
        except:
            pass

    def on_closing(self):
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
    window.title('Prince Pattern Mode')
    window.geometry("1080x630+10+10")
    window.protocol("WM_DELETE_WINDOW", mywin.on_closing)
    window.mainloop()