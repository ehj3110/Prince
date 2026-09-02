from tkinter import *
from tkinter.ttk import *
from tkinter import filedialog, messagebox
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
import timeit
import threading
import csv
import datetime
import queue
import traceback

# Add support_modules to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'support_modules'))

import pycrafter9000
import libs


class MyWindow:
    # Updated 22 Power settings routine for energy output testing
    POWER_SEQUENCE = [
        255, 225, 200, 175, 150, 125, 100, 75, 60, 50,
        45, 40, 35, 30, 25, 20, 15, 10, 7, 5,
        1, 0
    ]

    def __init__(self, win):
        self.win = win
        self.flag = False
        self.pause_flag = False
        self.print_thread = None

        self.image_list = []
        self.exposure_time = []
        self.thickness = []
        self.step_speed_list = []
        self.overstep_distance_list = []
        self.step_type_list = []
        self.pause_list = []
        self.intensity_list = []
        self.sandwich_speed_list = []

        self.status_message_var = StringVar()
        self.status_message_var.set("System Initializing...")

        # Progress header & bar
        self.lbl_progress_header = Label(win, text='Progress', font='Helvetica 12 bold')
        self.lbl_progress_header.place(x=50, y=285)

        self.p1 = Progressbar(win, orient=HORIZONTAL, length=550, mode='determinate')
        style = Style()
        style.configure('Tall.Horizontal.TProgressbar', thickness=24)
        self.p1.configure(style='Tall.Horizontal.TProgressbar')
        self.p1.place(x=50, y=310)

        self.current_layer_num_var = StringVar()
        self.current_layer_num_var.set("Step: 0/0")
        self.lbl_current_layer = Label(win, textvariable=self.current_layer_num_var, font='Helvetica 9')
        self.lbl_current_layer.place(x=400, y=287)

        self.lbl15_var = StringVar()
        self.lbl15_var.set("Est: N/A")
        self.lbl15_inside = Label(win, textvariable=self.lbl15_var, font='Helvetica 9')
        self.lbl15_inside.place(x=480, y=287)

        # Header Frame
        self.header_frame = tk.Frame(win, bg='#834bd0', relief='solid', borderwidth=3)
        self.header_frame.place(x=50, y=35, width=700, height=95)
        self.lbl0 = tk.Label(self.header_frame, text='Prince - Energy Test', font='Helvetica 36 bold', bg='#834bd0', fg='white')
        self.lbl0.place(x=20, y=15)

        # Controls & Labels
        self.lbl1 = Label(win, text='Directory of Images')
        self.lbl1.place(x=50, y=150)
        self.t1 = Entry(win, width=65)
        self.t1.place(x=50, y=170)
        self.t1.insert(END, r"C:\Users\cheng sun\BoyuanSun\Slicing\Calibration\Power_Grayscale")

        self.b_browse = Button(win, text='Browse...', command=self.browse_directory)
        self.b_browse.place(x=470, y=168)

        self.b_load = Button(win, text='Load Folder', command=self.input_directory)
        self.b_load.place(x=560, y=168)

        self.lbl_exp = Label(win, text='Exposure time (s):')
        self.lbl_exp.place(x=50, y=205)
        self.t_exp = Entry(win, width=15)
        self.t_exp.place(x=170, y=205)
        self.t_exp.insert(END, "5.0")

        self.lbl8 = Label(win, text='System Message:')
        self.lbl8.place(x=50, y=240)
        self.t8 = Label(win, textvariable=self.status_message_var, width=65, relief="sunken", anchor="w", justify=LEFT)
        self.t8.place(x=170, y=240)

        # Start / Stop buttons
        self.b1 = tk.Button(win, text='START ENERGY TEST', bg='#28a745', fg='white', font=('Helvetica', 12, 'bold'), padx=10, pady=5, command=self.run_Stepped)
        self.b1.place(x=50, y=360)

        self.b4 = tk.Button(win, text='STOP', bg='#dc3545', fg='white', font=('Helvetica', 12, 'bold'), padx=10, pady=5, state=DISABLED, command=self.stop)
        self.b4.place(x=240, y=360)

        # Text Log Area
        self.txt_log = Text(win, height=10, width=80, bg='#1E1E1E', fg='#D4D4D4', font=('Consolas', 9))
        self.txt_log.place(x=50, y=420)

        # Controller & Application Setup (Exact code from Prince_Segmented.py)
        try:
            self.controller = pycrafter9000.dmd()
            self.application = libs.Application()
            self.controller.stopsequence()
            self.controller.power(current=0)
            time.sleep(0.1)
            self.controller.changemode(3)
            self.controller.hdmi()
            self.update_status_message("DLP initialized: Power=0, Video Mode, HDMI input")
        except Exception as e:
            self.update_status_message(f"Error connecting to DLP: {e}", error=True)

        # Screeninfo & Window setup (Exact code from Prince_Segmented.py)
        screen_id = 0
        try:
            self.screen = screeninfo.get_monitors()[screen_id]
        except Exception:
            self.screen = None
        self.window_name = 'show'
        self.black_image = np.zeros((1600, 2560))

        self.update_status_message("System Ready.")

    def browse_directory(self):
        path = filedialog.askdirectory(title="Select Image Directory")
        if path:
            self.t1.delete(0, END)
            self.t1.insert(0, path)
            self.input_directory()

    def update_status_message(self, message, error=False):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        prefix = "ERROR: " if error else "Status: "
        full_msg = f"[{timestamp}] {prefix}{message}"
        
        print(full_msg)
        self.status_message_var.set(message)
        
        if hasattr(self, 'txt_log') and self.txt_log:
            try:
                self.txt_log.insert(END, full_msg + "\n")
                self.txt_log.see(END)
            except Exception:
                pass

    def input_directory(self):
        path = str(self.t1.get()).strip()
        if not path or not os.path.isdir(path):
            self.update_status_message("Invalid directory path.", error=True)
            return

        expected_instruction_filename = os.path.basename(os.path.normpath(path)) + ".txt"
        potential_instruction_file_path = os.path.join(path, expected_instruction_filename)

        try:
            if os.path.exists(potential_instruction_file_path):
                (
                    self.image_list,
                    self.exposure_time,
                    self.thickness,
                    self.step_speed_list,
                    self.overstep_distance_list,
                    self.step_type_list,
                    self.pause_list,
                    self.intensity_list,
                    self.sandwich_speed_list
                ) = self.application.set_image_directory(path)
            else:
                valid_exts = ('.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff')
                files = [f for f in os.listdir(path) if f.lower().endswith(valid_exts)]

                def sort_key(filename):
                    base = os.path.splitext(filename)[0]
                    parts = base.replace('_', ' ').split()
                    return [int(c) if c.isdigit() else c.lower() for c in parts]

                files.sort(key=sort_key)
                self.image_list = [os.path.join(path, f) for f in files]

            if not self.image_list:
                self.update_status_message("No images found in specified directory.", error=True)
                messagebox.showwarning("File Info", f"No image files found in:\n{path}")
            else:
                total_steps = max(len(self.POWER_SEQUENCE), len(self.image_list))
                self.update_status_message(f"Loaded {len(self.image_list)} image(s) from directory ({total_steps} power steps).")

        except Exception as e:
            self.update_status_message(f"Error loading directory: {e}", error=True)

    def initilze_stage(self):
        """Resets DLP to known HDMI state before starting."""
        self.update_status_message("Initializing DLP for energy test...")
        if hasattr(self, 'controller') and self.controller:
            try:
                self.controller.stopsequence()
                self.controller.power(current=0)
                time.sleep(0.1)
                self.controller.changemode(3)
                self.controller.hdmi()
                time.sleep(0.5)
                self.update_status_message("DLP reset to HDMI mode.")
            except Exception as e:
                self.update_status_message(f"Error initializing DLP: {e}", error=True)
        return True

    def run_Stepped(self):
        self.flag = False
        self.pause_flag = False
        self.update_status_message("Starting Energy Test Setup...")

        try:
            self.initilze_stage()
            self.input_directory()

            if not self.image_list:
                self.update_status_message("No images found. Aborting test.", error=True)
                messagebox.showerror("Print Error", "Image directory not set or no images found.")
                return

            try:
                exp_time_val = float(self.t_exp.get().strip())
                if exp_time_val <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Input Error", "Please enter a valid positive exposure time.")
                return

            self.b1.config(state=DISABLED)
            self.b4.config(state=NORMAL)

            self.print_thread = threading.Thread(target=self.print_t, args=(exp_time_val,))
            self.print_thread.daemon = True
            self.print_thread.start()

        except Exception as e:
            self.update_status_message(f"Error during test setup: {e}", error=True)
            self.b1.config(state=NORMAL)
            self.b4.config(state=DISABLED)

    def print_t(self, exp_time_s):
        """Thread loop that runs through the 22 power settings (Matches Prince_Segmented.py logic)."""
        try:
            self.update_status_message("Energy test thread started.")

            # Create full screen OpenCV window (Exact code from Prince_Segmented.py)
            cv2.namedWindow(self.window_name, cv2.WND_PROP_FULLSCREEN)
            if self.screen:
                cv2.moveWindow(self.window_name, self.screen.x + 1439, self.screen.y - 1)
            cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
            cv2.imshow(self.window_name, self.black_image)

            for _ in range(10):
                cv2.waitKey(50)
            self.win.update_idletasks()
            self.win.update()
            self.update_status_message("OpenCV projection window initialized.")

            # Exact DLP setup sequence from Prince_Segmented.py print_t
            if hasattr(self, 'controller') and self.controller:
                self.controller.power(current=0)
                time.sleep(0.1)
                self.controller.changemode(0)  # Switch to pattern sequence mode
                self.controller.power(current=0)
                time.sleep(2.0)  # Crucial delay for mode change to take effect
                initial_power = self.POWER_SEQUENCE[0]
                self.controller.power(current=initial_power)
                self.update_status_message(f"DLP set to pattern mode, initial power: {initial_power}.")
            else:
                self.update_status_message("DLP controller not available.", error=True)

            total_steps = max(len(self.POWER_SEQUENCE), len(self.image_list))
            last_commanded_dlp_power = -1

            for i in range(total_steps):
                if self.flag:
                    self.update_status_message("Energy test stopped by user.")
                    break

                current_step_num = i + 1
                current_power = self.POWER_SEQUENCE[i] if i < len(self.POWER_SEQUENCE) else 0
                image_path = self.image_list[i % len(self.image_list)]

                # 0. Set DLP power for this step
                if hasattr(self, 'controller') and self.controller:
                    try:
                        if current_power != last_commanded_dlp_power:
                            self.controller.power(current=current_power)
                            last_commanded_dlp_power = current_power
                            self.update_status_message(f"Step {current_step_num}/{total_steps}: DLP power set to {current_power}")
                    except Exception as e:
                        self.update_status_message(f"Step {current_step_num}: Could not set DLP power: {e}", error=True)

                # 1. Display image
                image_to_show = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
                if image_to_show is None:
                    self.update_status_message(f"Error loading image {image_path}. Showing black.", error=True)
                    cv2.imshow(self.window_name, self.black_image)
                else:
                    cv2.imshow(self.window_name, image_to_show)
                cv2.waitKey(1)

                # 2. Exposure delay
                if exp_time_s > 0:
                    time.sleep(exp_time_s)

                # 3. Blackout image
                cv2.imshow(self.window_name, self.black_image)
                cv2.waitKey(1)

                # 3b. Turn off DLP power during inter-step pause
                if hasattr(self, 'controller') and self.controller:
                    try:
                        self.controller.power(current=0)
                    except Exception as e:
                        pass

                time.sleep(0.1)

                # Update progress bar
                progress_val = (i + 1) * 100 / total_steps
                rem_sec = (total_steps - (i + 1)) * exp_time_s
                self.win.after(0, lambda p=progress_val, ts=total_steps, ci=i, rm=rem_sec: self._update_gui_progress(p, ts, ci, rm))

            if not self.flag:
                self.update_status_message("Energy test completed successfully.")
                cv2.imshow(self.window_name, self.black_image)
                cv2.waitKey(1)
                winsound.Beep(440, 1000)

        except Exception as e:
            self.update_status_message(f"CRITICAL Error during energy test: {e}", error=True)
            traceback.print_exc()
        finally:
            self.update_status_message("Finalizing test sequence...")
            if hasattr(self, 'controller') and self.controller:
                try:
                    self.controller.stopsequence()
                    self.controller.power(current=0)
                    self.controller.changemode(3)
                    self.update_status_message("DLP sequence stopped, LEDs off, set to HDMI mode.")
                except Exception as dlp_e:
                    self.update_status_message(f"Error during DLP cleanup: {dlp_e}", error=True)

            if hasattr(self, 'window_name') and self.window_name:
                try:
                    cv2.imshow(self.window_name, self.black_image)
                    cv2.waitKey(1)
                    cv2.destroyWindow(self.window_name)
                    cv2.waitKey(1)
                    self.update_status_message("OpenCV window closed.")
                except Exception:
                    pass

            self.win.after(0, self._reset_buttons)

    def _update_gui_progress(self, progress_value, total_steps, current_step_index, remaining_sec):
        if hasattr(self, 'p1'):
            self.p1['value'] = progress_value
        if hasattr(self, 'current_layer_num_var'):
            self.current_layer_num_var.set(f"Step: {current_step_index + 1}/{total_steps}")
        if hasattr(self, 'lbl15_var'):
            self.lbl15_var.set(f"Est: {remaining_sec / 60.0:.1f} min")
        self.win.update_idletasks()

    def _reset_buttons(self):
        self.b1.config(state=NORMAL)
        self.b4.config(state=DISABLED)

    def stop(self):
        self.flag = True
        self.update_status_message("Stopping energy test...")

    def on_closing(self):
        if self.print_thread and self.print_thread.is_alive():
            self.flag = True
            self.print_thread.join(timeout=2.0)

        if hasattr(self, 'controller') and self.controller:
            try:
                self.controller.stopsequence()
                self.controller.power(current=0)
                self.controller.changemode(3)
            except Exception:
                pass

        self.win.destroy()


if __name__ == '__main__':
    window = Tk()
    mywin = MyWindow(window)
    window.title('Prince - Energy Test')
    window.geometry("800x600+10+10")
    window.protocol("WM_DELETE_WINDOW", mywin.on_closing)
    window.mainloop()
