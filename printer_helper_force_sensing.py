#!/usr/bin/env python
# coding: utf-8

"""
RED Lab Printer Control Software - Force Sensing Integration
Enhanced version with Phidget on Port 2

CONFIGURATION:
- SPOOF_PHIDGET = False (using REAL Phidget hardware on port 2)
- ENABLE_DLP = False     (set to True when ready to test light engine)

All other hardware (Zaber, OpenCV) is REAL
"""

import logging
import sys
import socket
import threading
import math
import re
import glob
import time
import traceback 
import os
import queue

from pathlib import Path
from itertools import cycle
from datetime import datetime

if sys.version_info[0] == 2:
    import Tkinter
    tkinter = Tkinter
    from Tkinter import *
    from Tkinter.ttk import *
    from Tkinter import filedialog 
    from Tkinter import messagebox
else:
    import tkinter
    from tkinter import *
    from tkinter.ttk import *
    from tkinter import filedialog
    from tkinter import messagebox

# ========== HARDWARE CONFIGURATION ==========
SPOOF_PHIDGET = False  # Set to True for testing without Phidget
ENABLE_DLP = True      # ? ENABLED - Full system test
PHIDGET_HUB_PORT = 2   # Force gauge is on port 2
DEBUG_MODE = False     # Disable verbose debug for cleaner output
# ============================================

# Check if running python 3
if sys.version_info[0] != 3:
    raise SystemExit("Please set kernel to Python 3.x.x")

if DEBUG_MODE:
    print("=" * 80)
    print("DEBUG MODE ENABLED - Verbose output active")
    print("=" * 80)

if SPOOF_PHIDGET:
    print("=" * 70)
    print("??  PHIDGET SPOOFING MODE - Testing without Phidget hardware")
    print("=" * 70)
else:
    print("=" * 70)
    print(f"? REAL PHIDGET MODE - Force gauge on Hub Port {PHIDGET_HUB_PORT}")
    print("=" * 70)

if not ENABLE_DLP:
    print("??  DLP DISABLED - Skipping light engine for force gauge testing")
    print("=" * 70)

# Debug: Check for Phidget22 library
if DEBUG_MODE:
    print("\n[DEBUG] Checking for Phidget22 library...")
    try:
        import Phidget22
        print(f"[DEBUG] ? Phidget22 library found - Version: {Phidget22.__version__ if hasattr(Phidget22, '__version__') else 'unknown'}")
        print(f"[DEBUG] ? Phidget22 location: {Phidget22.__file__}")
    except ImportError as e:
        print(f"[DEBUG] ? Phidget22 library NOT FOUND!")
        print(f"[DEBUG] Error: {e}")
        print(f"[DEBUG] Please install with: pip install Phidget22")
    print()

# Real imports for hardware that's available
if DEBUG_MODE:
    print("[DEBUG] Importing real hardware libraries...")
    
import cv2
if DEBUG_MODE:
    print("[DEBUG] ? cv2 (OpenCV) imported")
    
import screeninfo
if DEBUG_MODE:
    print("[DEBUG] ? screeninfo imported")
    
import numpy as np
if DEBUG_MODE:
    print("[DEBUG] ? numpy imported")
    
from PIL import Image, ImageTk
if DEBUG_MODE:
    print("[DEBUG] ? PIL imported")
    
from zaber_motion import Units, Library
from zaber_motion.ascii import Connection
if DEBUG_MODE:
    print("[DEBUG] ? zaber_motion imported")
    
import usb.core
import usb.util
if DEBUG_MODE:
    print("[DEBUG] ? usb (pyusb) imported")

if ENABLE_DLP:
    import dinglab_printer
    if DEBUG_MODE:
        print("[DEBUG] ? dinglab_printer imported")
else:
    if DEBUG_MODE:
        print("[DEBUG] ??  dinglab_printer import skipped (DLP disabled)")

# Phidget mock classes for testing without hardware
if SPOOF_PHIDGET:
    print("Creating Phidget mock classes...")
    
    # Mock Phidget22 module structure
    class MockPhidgetException(Exception):
        pass
    
    class MockErrorCode:
        EPHIDGET_OK = 0
        EPHIDGET_TIMEOUT = 1
        EPHIDGET_NOTATTACHED = 2
    
    class MockVoltageRatioInput:
        def __init__(self):
            self._attached = False
            self._voltage_ratio = 0.0
            self._data_interval = 250
            self._voltage_ratio_change_trigger = 0.0
            self._on_voltage_ratio_change_handler = None
            self._on_attach_handler = None
            self._on_detach_handler = None
            self._running = False
            self._thread = None
            self._hub_port = -1
            print("Mock VoltageRatioInput created")
        
        def setOnVoltageRatioChangeHandler(self, handler):
            self._on_voltage_ratio_change_handler = handler
        
        def setOnAttachHandler(self, handler):
            self._on_attach_handler = handler
        
        def setOnDetachHandler(self, handler):
            self._on_detach_handler = handler
        
        def setHubPort(self, port):
            """Set hub port for Phidget - mock implementation"""
            self._hub_port = port
            print(f"Mock: Hub port set to {port}")
        
        def openWaitForAttachment(self, timeout_ms):
            print(f"Mock: Opening VoltageRatioInput (timeout={timeout_ms}ms)")
            time.sleep(0.1)  # Simulate connection delay
            self._attached = True
            if self._on_attach_handler:
                self._on_attach_handler(self)
            self._start_simulation()
            print("Mock: VoltageRatioInput attached successfully")
        
        def close(self):
            print("Mock: Closing VoltageRatioInput")
            self._running = False
            if self._thread:
                self._thread.join(timeout=1.0)
            self._attached = False
        
        def getAttached(self):
            return self._attached
        
        def setDataInterval(self, interval_ms):
            self._data_interval = interval_ms
        
        def getDataInterval(self):
            return self._data_interval
        
        def setVoltageRatioChangeTrigger(self, trigger):
            self._voltage_ratio_change_trigger = trigger
        
        def getVoltageRatioChangeTrigger(self):
            return self._voltage_ratio_change_trigger
        
        def getVoltageRatio(self):
            # Simulate realistic force sensor readings with small noise
            base_reading = 0.0001  # Small baseline offset
            noise = (np.random.random() - 0.5) * 0.00002  # ±10µV/V noise
            return base_reading + noise
        
        def _start_simulation(self):
            """Start background thread to simulate data callbacks"""
            self._running = True
            self._thread = threading.Thread(target=self._simulation_loop, daemon=True)
            self._thread.start()
        
        def _simulation_loop(self):
            """Simulate periodic voltage ratio change callbacks"""
            while self._running:
                if self._on_voltage_ratio_change_handler and self._attached:
                    voltage_ratio = self.getVoltageRatio()
                    self._on_voltage_ratio_change_handler(self, voltage_ratio)
                time.sleep(self._data_interval / 1000.0)
    
    # Create mock module structure
    class MockPhidget22:
        ErrorCode = MockErrorCode
        PhidgetException = MockPhidgetException
        
        class Phidget:
            pass
        
        class Devices:
            class VoltageRatioInput:
                VoltageRatioInput = MockVoltageRatioInput
    
    # Inject mock into sys.modules
    sys.modules['Phidget22'] = MockPhidget22
    sys.modules['Phidget22.Phidget'] = MockPhidget22.Phidget
    sys.modules['Phidget22.Devices'] = MockPhidget22.Devices
    sys.modules['Phidget22.Devices.VoltageRatioInput'] = MockPhidget22.Devices.VoltageRatioInput
    
    print("? Phidget mock modules injected into sys.modules")

# Add support_modules to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'support_modules'))

if DEBUG_MODE:
    print(f"\n[DEBUG] Added support_modules to Python path")
    print(f"[DEBUG] support_modules location: {os.path.join(os.path.dirname(__file__), 'support_modules')}")
    print(f"[DEBUG] Importing force sensing modules...")

# Import force sensing modules
try:
    from ForceGaugeManager import ForceGaugeManager
    if DEBUG_MODE:
        print("[DEBUG] ? ForceGaugeManager imported")
        
    from SensorDataWindow import SensorDataWindow
    if DEBUG_MODE:
        print("[DEBUG] ? SensorDataWindow imported")
        
    from PositionLogger import PositionLogger
    if DEBUG_MODE:
        print("[DEBUG] ? PositionLogger imported")
        
    from AutomatedLayerLogger import LayerLogger
    if DEBUG_MODE:
        print("[DEBUG] ? AutomatedLayerLogger imported")
        
    from ExperimentalConditionsWindow import ExperimentalConditionsWindow
    if DEBUG_MODE:
        print("[DEBUG] ? ExperimentalConditionsWindow imported")
        
    from AutoHomeRoutine import AutoHomer
    if DEBUG_MODE:
        print("[DEBUG] ? AutoHomeRoutine imported")
        
    FORCE_SENSING_AVAILABLE = True
    print("? Force sensing modules loaded successfully")
except ImportError as e:
    print(f"? Force sensing modules not available: {e}")
    if DEBUG_MODE:
        traceback.print_exc()
    FORCE_SENSING_AVAILABLE = False


def print_result(operation, result):
    """Helper to print operation results"""
    if result.getSuccess():
        print(f"Operation {operation} Success")
        return True
    else:
        print(f"Failed!! {operation}: {result.getMessage()}.")
        return False


class ZaberMotor:
    """Zaber stage controller - REAL hardware"""
    def __init__(self):
        self.init = None
        self.connection = None

    def get_zaber_motor(self):
        self.connection = Connection.open_serial_port("COM3")
        self.connection.enable_alerts()
        device_list = self.connection.detect_devices()
        print("Found {} devices".format(len(device_list)))
        device = device_list[0]
        axis = device.get_axis(1)
        return axis
    
    def disconnect(self):
        if self.connection:
            self.connection.close()


class OutputGrabber(object):
    """
    Class used to grab standard output or another stream.
    """
    escape_char = "\b"

    def __init__(self, stream=None, threaded=False):
        self.origstream = stream
        self.threaded = threaded
        if self.origstream is None:
            self.origstream = sys.stdout
        self.origstreamfd = self.origstream.fileno()
        self.capturedtext = ""
        self.pipe_out, self.pipe_in = os.pipe()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, type, value, traceback):
        self.stop()

    def start(self):
        """Start capturing the stream data."""
        self.capturedtext = ""
        self.streamfd = os.dup(self.origstreamfd)
        os.dup2(self.pipe_in, self.origstreamfd)
        if self.threaded:
            self.workerThread = threading.Thread(target=self.readOutput)
            self.workerThread.start()
            time.sleep(0.01)

    def stop(self):
        """Stop capturing the stream data and save the text in `capturedtext`."""
        self.origstream.write(self.escape_char)
        self.origstream.flush()
        if self.threaded:
            self.workerThread.join()
        else:
            self.readOutput()
        os.close(self.pipe_in)
        os.close(self.pipe_out)
        os.dup2(self.streamfd, self.origstreamfd)
        os.close(self.streamfd)

    def readOutput(self):
        """Read the stream data (one byte at a time) and save the text in `capturedtext`."""
        while True:
            char = os.read(self.pipe_out, 1)
            if not char or self.escape_char in char:
                break
            self.capturedtext += char


class Application():
    """Application logic for print job management"""
    def __init__(self):
        self.init = None
         
    def set_image_directory(self, txt_path=''):
        '''
        Parse print job file format:
        Layer	File	Thickness	Pause	Material	time	Intensity
        '''
        path = os.path.dirname(txt_path)
        image_list = []
        exposure_time_list = []
        thickness_list = []
        
        with open(txt_path) as f:
            lines = f.readlines()
            for line in lines[1:]:
                elements = line.split()
                count, image_path, exposure_time, thickness = elements[0], elements[1], elements[2], elements[3]
                exposure_time_list.append(float(exposure_time))
                thickness_list.append(float(thickness))
                image_list.append(path + '\\' + image_path)
        return image_list, exposure_time_list, thickness_list
    
    def generate_debug_txt(self, path='', thickness='5', pause='0', material='1', time='1', intensity='0'):
        """Generate simple print job file from image folder"""
        txt_name = path.split('\\')[-1] + '.txt'
        txt_path = path + '\\' + txt_name
        image_paths = Path(path).glob("*[!.txt]")
        file_pattern = re.compile(r'.*?(\d+).*?')
        
        def get_order(file):
            match = file_pattern.match(Path(file).name)
            if not match:
                return math.inf
            return int(match.groups()[-1])
        
        image_paths = sorted(image_paths, key=get_order)
        try:
            with open(txt_path, 'w') as f:
                f.write('Layer	File	Thickness	Pause	Material	Time	Intensity\n')
                layer = 1
                while image_paths:
                    image_name = str(image_paths.pop(0)).split('\\')[-1]
                    line = str(layer) + '   ' + image_name + '  ' + thickness \
                           + '  ' + pause + '  ' + material + '  ' + time + '  ' + intensity + '\n'
                    f.write(line)
                    layer += 1
        except FileNotFoundError:
            print("The directory does not exist for creating the text file.")


class MyWindow:
    def __init__(self, win):
        instruction = '''
Check List:
0. Make sure that Windows is projecting to second screen
1. Make sure the DLP Lightcrafter GUI is closed.
2. Connect Zaber stage on COM3
3. Connect Phidget force gauge (when available)

Trouble Shooting:
1. USB Input/output error: Close DLP Lightcrafter GUI.
2. Reconnect stage with Zaber Motion app.
3. Force gauge: Check SPOOF_PHIDGET setting
'''
        credit = '''
Boyuan Sun, boyuansun2026@u.northwestern.edu
Evan Jones, evanjones2026@u.northwestern.edu
Edwin Clement, eclement@wpi.edu
'''
        self.reference = 20
        self.image_list = []
        self.enable_device = True
        self.exposure_time = []
        self.thickness = []
        self.win = win
        self.flag = False
        self.offset = -25
        
        # Force sensing components
        self.sensor_data_window_instance = None
        self.force_gauge_manager = None
        self.exp_conditions_window = None
        self.auto_home_thread = None
        
        win.protocol("WM_DELETE_WINDOW", lambda: self.cleanup())
        print("Starting up the connection")
        
        # Canvas elements
        self.canvas1 = Canvas(win, height=200, width=270, bg="#FFEFD5")
        self.canvas1.place(x=70, y=520)
        self.canvas2 = Canvas(win, height=200, width=270, bg="#FFEFD5")
        self.canvas2.place(x=370, y=520)
        
        # Labels
        self.label_title = Label(win, text='RED Printer Manager', font='Helvetica 40 bold')
        self.label_directory_of_images = Label(win, text='Directory of Images')
        self.label_z_axis_position = Label(win, text='Z Axis Position (mm)')
        self.label_instruction = Label(win, text=instruction, font='Helvetica 10', foreground='purple')
        self.label_credit = Label(win, text=credit, font='Helvetica 7')
        self.label_printing_progress = Label(win, text='Printing Progress')
        self.label_system_message = Label(win, text='System Message:')
        self.lbl9 = Label(win, text='Move distance(mm)')
        self.lbl10 = Label(win, text='Layer thickness(um)')
        self.lbl11 = Label(win, text='Exposure time(s)')
        self.lbl12 = Label(win, text='Stage Control', font='Helvetica 12 bold')
        self.lbl13 = Label(win, text='Simple Txt File Generator', font='Helvetica 12 bold')
        self.label_led_power = Label(win, text='LED Power(0.0-2.5')
        self.label_resin_filling_time = Label(win, text='Resin Filling Time(s)')
        self.label_first_layer = Label(win, text='First Layer Exposure Time(s)')

        # Entry widgets
        self.z_axis_position = Entry(win, text='Press "Get Position"')
        self.first_layer_exposure_time = Entry()
        self.t8 = Entry()
        self.t9 = Entry()
        self.t10 = Entry()
        self.t11 = Entry()
        self.led_power = Entry()
        self.resin_filling_time = Entry()
        
        # Place labels
        self.label_title.place(x=450, y=50)
        self.label_directory_of_images.place(x=50, y=150)
        self.label_z_axis_position.place(x=50, y=260)
        self.z_axis_position.place(x=50, y=280) 
        self.label_instruction.place(x=700, y=270)
        self.label_credit.place(x=950, y=0)
        self.t8.place(x=500, y=280)
        self.label_system_message.place(x=500, y=260)
        self.t9.place(x=140, y=580)
        self.lbl9.place(x=140, y=560)
        self.t10.place(x=400, y=580)
        self.lbl10.place(x=400, y=560)
        self.t11.place(x=400, y=620)
        self.lbl11.place(x=400, y=600)
        self.lbl12.place(x=150, y=500)
        self.lbl13.place(x=410, y=500)
        self.label_led_power.place(x=240, y=260)
        self.resin_filling_time.place(x=500, y=370)
        self.label_resin_filling_time.place(x=500, y=350)
        self.label_first_layer.place(x=240, y=310)
        self.first_layer_exposure_time.place(x=240, y=330)
        
        # Initialize entry values
        self.t8.delete(0, 'end')
        self.t9.delete(0, 'end')
        self.t10.delete(0, 'end')
        self.t11.delete(0, 'end')
        self.led_power.delete(0, 'end')
        self.first_layer_exposure_time.delete(0, 'end')
        
        self.t8.insert(END, str("Stage connected"))
        self.t9.insert(END, str("25"))
        self.t10.insert(END, str("5"))
        self.t11.insert(END, str("1.5"))
        self.led_power.insert(END, str("0.5"))
        self.resin_filling_time.insert(END, str("0.2"))
        self.first_layer_exposure_time.insert(END, str("2"))
        self.z_axis_position.delete(0, 'end')
        self.z_axis_position.insert(END, str(self.reference))

        # Stepwise checkbox
        def checkbutton_change():
            if (not self.checkbutton_value.get()):
                self.resin_filling_time.config(state="disabled")
            else:
                self.resin_filling_time.config(state="enabled")
        
        self.checkbutton_value = BooleanVar()
        self.checkbutton = Checkbutton(text="Step-wise Print", variable=self.checkbutton_value, command=checkbutton_change)
        self.checkbutton.place(x=500, y=320)
        self.checkbutton_value.set(True)

        # Progress bar
        self.progress = Progressbar(win, orient=HORIZONTAL, length=500, mode='determinate')
        self.progress.place(x=50, y=430)
        self.label_printing_progress.place(x=250, y=400)

        # File selection
        def setFilePath():
            file_selected = filedialog.askopenfilename(filetypes=(("3D Slices Info", '*.txt'),))
            self.filePath.set(os.path.normpath(file_selected))
            self.input_directory()
            avg_exp = sum(self.exposure_time)/len(self.exposure_time)
            avg_thk = sum(self.thickness)/len(self.thickness)
            self.printJobDetails.set(f'Cnt: {len(self.image_list)} Avg. Exp {round(avg_exp,2)}, Avg. Thk {round(avg_thk,2)}')
            
        self.filePath = StringVar()
        self.printJobDetails = StringVar()
        self.entPath = Entry(win, width=120, textvariable=self.filePath)
        self.btnFind = Button(win, text="Select File", command=setFilePath)
        self.loaded_image_info = Label(win, textvariable=self.printJobDetails)
        self.printJobDetails.set('Print Job Details')

        self.entPath.place(x=180, y=150)
        self.btnFind.place(x=180+730+10, y=150)      
        self.loaded_image_info.place(x=180+740+70+10, y=150)     
        self.entPath.insert(END, r"E:\MC\_Animal_Study_Stent_ADJ3_Henry_50um\sent_50um 200.txt")
        
        # Compatibility property for SensorDataWindow automated logging
        # SensorDataWindow expects prince_main_app_ref.t1.get() but RED Lab uses entPath
        # This property provides compatibility without modifying SensorDataWindow
        self.t1 = self.entPath  # Direct reference for .get() access

        # === FORCE SENSING BUTTONS (NEW) ===
        if FORCE_SENSING_AVAILABLE:
            # Auto-Home Controls Frame
            auto_home_frame = LabelFrame(win, text="Auto-Home Control", padding=(10, 10))
            auto_home_frame.place(x=700, y=400, width=450)
            
            lbl_auto_home_guess = Label(auto_home_frame, text='Guess (mm):')
            lbl_auto_home_guess.grid(row=0, column=0, padx=5, pady=5, sticky=W)
            self.t_auto_home_guess = Entry(auto_home_frame, width=10)
            self.t_auto_home_guess.grid(row=0, column=1, padx=5, pady=5)
            self.t_auto_home_guess.insert(END, "10.0")
            
            lbl_contact_threshold_abs = Label(auto_home_frame, text='Abs. Force (N):')
            lbl_contact_threshold_abs.grid(row=0, column=2, padx=5, pady=5, sticky=W)
            self.t_contact_threshold_abs = Entry(auto_home_frame, width=10)
            self.t_contact_threshold_abs.grid(row=0, column=3, padx=5, pady=5)
            self.t_contact_threshold_abs.insert(END, "0.005")
            
            lbl_contact_threshold_delta = Label(auto_home_frame, text='Delta Force (N):')
            lbl_contact_threshold_delta.grid(row=1, column=0, padx=5, pady=5, sticky=W)
            self.t_contact_threshold_delta = Entry(auto_home_frame, width=10)
            self.t_contact_threshold_delta.grid(row=1, column=1, padx=5, pady=5)
            self.t_contact_threshold_delta.insert(END, "0.002")
            
            self.b_auto_home = Button(auto_home_frame, text="Auto-Home Surface", 
                                     command=self.start_auto_home_sequence, state=DISABLED)
            self.b_auto_home.grid(row=1, column=2, columnspan=2, padx=5, pady=5, sticky=EW)
            
            # Sensor panel and exp conditions buttons
            self.b_sensor_panel = Button(win, text='Open Sensor Panel', command=self.open_sensor_panel)
            self.b_sensor_panel.place(x=700, y=530)
            
            self.b_exp_conditions = Button(win, text='Exp. Conditions', command=self.open_exp_conditions_window)
            self.b_exp_conditions.place(x=825, y=530)

        # Control buttons
        self.b1 = Button(win, text='Run', command=self.run)
        self.b2 = Button(win, text='Go to Home', command=self.set_home)
        self.b3 = Button(win, text='Get Position', command=self.get_position)
        self.button_set_position = Button(win, text='Set Position', command=self.set_position)
        self.b4 = Button(win, text='Stop', command=self.stop)
        self.b5 = Button(win, text='Move Down', command=self.movedown)
        self.b6 = Button(win, text='Move Up', command=self.moveup)
        self.b7 = Button(win, text='Simple input txt generator', command=self.simple_txt)
        
        self.b1.place(x=70, y=200)
        self.b2.place(x=50, y=310)
        self.button_set_position.place(x=130, y=340)
        self.b3.place(x=130, y=310)
        self.b4.place(x=170, y=200)
        self.b5.place(x=100, y=630)
        self.b6.place(x=200, y=630)
        self.b7.place(x=440, y=660)

        self.application = Application()
        
        # Initialize hardware
        if self.enable_device:
            # Initialize DLP controller (optional - skip for force gauge testing)
            if ENABLE_DLP:
                self.controller = dinglab_printer.Controller()
                r = self.controller.check_connection()
                print_result("Check Connection", r)
                r = self.controller.initialize()
                print_result("Initialize Printer", r)
                r = self.controller.change_mode_to_displayport()
                print_result("Change Mode to DP", r)
            else:
                print("??  Skipping DLP initialization (ENABLE_DLP = False)")
                # Create dummy controller for compatibility
                class DummyController:
                    def set_amplitude(self, value): pass
                    def led_activate(self): pass
                    def led_deactivate(self): pass
                    def disconnect(self): pass
                self.controller = DummyController()

            # Initialize Zaber stage (REAL)
            Library.enable_device_db_store()
            self.zaber_motor = ZaberMotor()
            self.axis = self.zaber_motor.get_zaber_motor()
            
            # Initialize force gauge (REAL or SPOOFED depending on SPOOF_PHIDGET)
            if FORCE_SENSING_AVAILABLE:
                if SPOOF_PHIDGET:
                    print("??  Force gauge initialization with SPOOFED Phidget")
                else:
                    print(f"? Initializing REAL Phidget force gauge on Hub Port {PHIDGET_HUB_PORT}...")
                self.initialize_force_gauge()
        
        # Screen setup (REAL)
        screen_id = 0
        self.screen = screeninfo.get_monitors()[screen_id]
        print("Screen info:")
        print(screeninfo.get_monitors())
        
        self.window_name = 'show'
        self.black_image = np.zeros((1080, 1920))
        
        status_msg = "RED Printer initialized successfully"
        if SPOOF_PHIDGET:
            status_msg += " (Phidget SPOOFED)"
        self.update_system_message(status_msg)

    def initialize_force_gauge(self):
        """Initialize Phidget force gauge manager (real or spoofed)"""
        if DEBUG_MODE:
            print("\n[DEBUG] ===== FORCE GAUGE INITIALIZATION =====")
            print(f"[DEBUG] SPOOF_PHIDGET: {SPOOF_PHIDGET}")
            print(f"[DEBUG] PHIDGET_HUB_PORT: {PHIDGET_HUB_PORT}")
            
        try:
            self.force_data_queue = queue.Queue()
            
            # Create dummy UI elements for ForceGaugeManager
            dummy_frame = Frame(self.win)
            gain_label = Label(dummy_frame, text="Gain: N/A")
            offset_label = Label(dummy_frame, text="Offset: N/A")
            force_status_label = Label(dummy_frame, text="Force: 0.000 N")
            large_force_readout = Label(dummy_frame, text="0.000 N")
            
            self.force_gauge_manager = ForceGaugeManager(
                gain_label=gain_label,
                offset_label=offset_label,
                force_status_label=force_status_label,
                large_force_readout_label=large_force_readout,
                output_force_queue=self.force_data_queue,
                parent_window=self.win,
                sensor_window_ref=None
            )
            
            # Wait for initialization
            if not SPOOF_PHIDGET and hasattr(self.force_gauge_manager, 'initialization_thread'):
                self.force_gauge_manager.initialization_thread.join(timeout=10.0)
            
            mode = "SPOOFED" if SPOOF_PHIDGET else "REAL"
            if DEBUG_MODE:
                print(f"[DEBUG] Force gauge manager initialized ({mode} mode)")
                print(f"[DEBUG] ===== FORCE GAUGE INITIALIZATION COMPLETE =====\n")
                
            print(f"? Force gauge manager initialized ({mode} mode)")
            self.update_system_message(f"Force gauge connected ({mode}) on Port {PHIDGET_HUB_PORT}")
        except Exception as e:
            print(f"? Error initializing force gauge: {e}")
            if DEBUG_MODE:
                traceback.print_exc()
            self.force_gauge_manager = None
            self.update_system_message("Force gauge not available")

    def open_sensor_panel(self):
        """Open the sensor data and logging window"""
        if not FORCE_SENSING_AVAILABLE:
            messagebox.showerror("Error", "Force sensing modules not available")
            return
            
        if self.sensor_data_window_instance and self.sensor_data_window_instance.sensor_window.winfo_exists():
            self.sensor_data_window_instance.sensor_window.lift()
            return
        
        try:
            print(f"Opening Sensor Panel - Passing existing ForceGaugeManager: {self.force_gauge_manager is not None}")
            self.sensor_data_window_instance = SensorDataWindow(
                master_window=self.win,
                zaber_axis_ref=self.axis,
                main_app_status_callback=self.update_system_message,
                prince_main_app_ref=self,
                existing_force_gauge_manager=self.force_gauge_manager  # PASS EXISTING MANAGER!
            )
            print("Sensor panel opened successfully")
            self.update_auto_home_button_state()
        except Exception as e:
            print(f"Error opening sensor panel: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to open sensor panel: {str(e)}")
    
    def open_exp_conditions_window(self):
        """Open experimental conditions documentation window"""
        if not FORCE_SENSING_AVAILABLE:
            messagebox.showerror("Error", "Experimental conditions module not available")
            return
            
        if self.exp_conditions_window:
            try:
                if self.exp_conditions_window.window.winfo_exists():
                    self.exp_conditions_window.window.lift()
                    return
            except:
                self.exp_conditions_window = None
        
        try:
            self.exp_conditions_window = ExperimentalConditionsWindow(
                parent_window=self.win,
                update_status_callback=self.update_system_message
            )
            self.exp_conditions_window.show_window()
            print("Experimental conditions window opened successfully")
            self.update_system_message("Experimental conditions window opened")
        except Exception as e:
            print(f"Error opening experimental conditions window: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to open exp conditions: {str(e)}")
    
    def update_auto_home_button_state(self):
        """Enable/disable auto-home button based on force gauge calibration"""
        if not FORCE_SENSING_AVAILABLE or not hasattr(self, 'b_auto_home'):
            return
            
        if (self.sensor_data_window_instance and 
            hasattr(self.sensor_data_window_instance, 'force_gauge_is_calibrated') and
            self.sensor_data_window_instance.force_gauge_is_calibrated):
            self.b_auto_home.config(state=NORMAL)
        else:
            self.b_auto_home.config(state=DISABLED)
    
    def start_auto_home_sequence(self):
        """Start the auto-home routine to find surface contact"""
        if self.auto_home_thread and self.auto_home_thread.is_alive():
            self.update_system_message("Auto-Home is already in progress")
            return
        
        try:
            initial_guess = float(self.t_auto_home_guess.get())
            contact_threshold_abs = float(self.t_contact_threshold_abs.get())
            contact_threshold_delta = float(self.t_contact_threshold_delta.get())
        except ValueError:
            self.update_system_message("Invalid input for Auto-Home parameters", error=True)
            messagebox.showerror("Input Error", "Auto-Home parameters must be numbers.")
            return
        
        if not (self.sensor_data_window_instance and 
                hasattr(self.sensor_data_window_instance, 'force_gauge_manager') and
                self.sensor_data_window_instance.force_gauge_manager):
            self.update_system_message("Sensor panel or force gauge manager not available", error=True)
            return
        
        if not self.sensor_data_window_instance.force_gauge_is_calibrated:
            self.update_system_message("Force gauge is not calibrated. Please calibrate from Sensor Panel.", error=True)
            messagebox.showwarning("Calibration Needed", "Force gauge must be calibrated before Auto-Home.")
            return
        
        self.update_system_message("Starting Auto-Home...")
        self.b_auto_home.config(state=DISABLED)
        
        self.auto_home_thread = AutoHomer(
            zaber_axis=self.axis,
            force_gauge_manager=self.sensor_data_window_instance.force_gauge_manager,
            initial_guess=initial_guess,
            contact_threshold_absolute=contact_threshold_abs,
            contact_threshold_delta=contact_threshold_delta,
            status_callback=self.update_system_message,
            result_callback=self.handle_auto_home_result,
            parent_gui=self.win
        )
        self.auto_home_thread.start()
    
    def handle_auto_home_result(self, new_home_position, message):
        """Callback when auto-home completes"""
        self.update_system_message(message)
        if new_home_position is not None:
            self.reference = new_home_position
            self.z_axis_position.delete(0, 'end')
            self.z_axis_position.insert(END, f"{new_home_position:.4f}")
            self.update_system_message(f"New Home set to: {new_home_position:.4f} mm")
            messagebox.showinfo("Auto-Home Complete", f"New home position set to: {new_home_position:.4f} mm")
        else:
            messagebox.showerror("Auto-Home Failed", message)
        
        self.update_auto_home_button_state()
    
    def update_system_message(self, message, error=False, warning=False):
        """Update the system message display"""
        self.t8.delete(0, 'end')
        self.t8.insert(END, str(message))
        if error:
            self.t8.config(foreground='red')
        elif warning:
            self.t8.config(foreground='orange')
        else:
            self.t8.config(foreground='black')
        self.win.update()

    def run(self):
        """Perform a print - REAL hardware"""
        sys.setrecursionlimit(500000)
        self.set_power()
        self.input_directory()
        self.set_position()
        self.flag = True
        
        cv2.startWindowThread()
        cv2.namedWindow(self.window_name, cv2.WND_PROP_FULLSCREEN)
        cv2.imshow(self.window_name, self.black_image)
        cv2.moveWindow(self.window_name, self.screen.x + 1439, self.screen.y - 1)
        cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        cv2.waitKey(1)
            
        while self.axis.is_busy():
            time.sleep(0.2)
        
        print("The window has opened")
        
        # Configure automated logging if enabled
        if self.sensor_data_window_instance and hasattr(self.sensor_data_window_instance, 'auto_log_enabled_var'):
            if self.sensor_data_window_instance.auto_log_enabled_var.get():
                # Get the image directory
                image_dir = os.path.dirname(self.entPath.get())
                date_str = datetime.now().strftime('%Y-%m-%d')
                log_dir = os.path.join(image_dir, "Printing_Logs", date_str, "Print_001")
                
                # Configure logging for this print run
                try:
                    os.makedirs(log_dir, exist_ok=True)
                    self.sensor_data_window_instance.configure_automated_layer_logging(
                        main_image_dir=image_dir,
                        print_number=1,
                        date_str_for_dir=date_str,
                        log_directory=log_dir
                    )
                    print("? Automated layer logging configured for this print")
                    self.update_system_message("Automated logging: ACTIVE")
                except Exception as e:
                    print(f"?? Could not configure automated logging: {e}")
                    traceback.print_exc()
        
        self._(0)
        self.controller.set_amplitude(0)
        self.axis.move_relative(max(0, self.offset), Units.LENGTH_MILLIMETRES, True)
        
        # Stop and save automated logging after print
        if self.sensor_data_window_instance and hasattr(self.sensor_data_window_instance, 'stop_and_save_automated_logs'):
            try:
                self.sensor_data_window_instance.stop_and_save_automated_logs()
                print("? Automated logging stopped and saved")
                self.update_system_message("Automated logging: SAVED")
            except Exception as e:
                print(f"?? Could not stop automated logging: {e}")
                traceback.print_exc()
        
        self.t8.delete(0, 'end')
        self.t8.insert(END, str("Print Done"))

    def show_image(self, image_data, exposure_time, is_continous):
        """Display image and control LED - REAL hardware"""
        print("show_image: Started showing image")
        cv2.imshow(self.window_name, image_data)
        if not is_continous:
            self.controller.led_activate()
        wait_time_ms = int(exposure_time * 1000)
        print(f"show_image: will wait for {wait_time_ms}")
        
        if not is_continous:
            if cv2.waitKey(wait_time_ms) & 0xFF == ord('q'):
                cv2.destroyAllWindows()
            self.controller.led_deactivate()
        else:
            cv2.waitKey(wait_time_ms)
        
        print("show_image: done showing image")
    
    def move_zaber(self, thickness, exposure_time, is_continous):
        """Move Zaber stage - REAL hardware"""
        print("move_zaber: Started moving")
        if is_continous:
            velocity = abs(thickness / exposure_time)
            print(f"move_zaber: velocity {velocity}")
            self.axis.move_relative(thickness, Units.LENGTH_MILLIMETRES, True, velocity, Units.VELOCITY_MILLIMETRES_PER_SECOND)
        else:
            self.axis.move_relative(thickness, Units.LENGTH_MILLIMETRES, True, 9, Units.VELOCITY_MILLIMETRES_PER_SECOND)
        print("move_zaber: done moving")

    def _(self, idx):
        """Recursive print layer function"""
        if not self.flag:
            return
        
        image = cv2.imread(self.image_list[idx].replace('\\', '\\\\'), cv2.IMREAD_GRAYSCALE)
        cv2.imshow(self.window_name, image)
        cv2.waitKey(1)
        e_time = float(self.exposure_time[idx])
        if idx == 0:
            e_time = float(self.first_layer_exposure_time.get())

        thickness = (self.thickness[idx] * -1) / 1000
        image_path_display = self.image_list[idx].replace('\\', '\\\\')
        print(f"run_: Image path {image_path_display}")
        print(f"exposure time {e_time}, index {idx}")
        print(f"Thickness: {thickness}")
        
        if self.checkbutton_value.get() == True:
            # Stepwise mode
            show_thread = threading.Thread(target=self.show_image, args=(image, e_time, False))
            move_thread = threading.Thread(target=self.move_zaber, args=(thickness, e_time, False))
        
            print("run_: Show")
            show_thread.start()
            show_thread.join()
            print("run_: Done Showing")
            time.sleep(float(self.resin_filling_time.get()))
            print("run_: Done waiting")
            
            move_thread.start()
            move_thread.join()
            print("run_: done Moving")
        else:
            # Continuous mode
            if idx == 0:
                self.controller.led_activate()
            elif idx == len(self.exposure_time):
                self.controller.led_deactivate()

            move_thread = threading.Thread(target=self.move_zaber, args=(thickness, e_time, True))
            show_thread = threading.Thread(target=self.show_image, args=(image, e_time, True))

            print("run_: Printing in continous mode")
            print("run_: Starting show")
            show_thread.start()
            print("run_: Started moving")
            if idx != 0:
                move_thread.start()
            
            print("run_: Waiting for move")
            if idx != 0:
                move_thread.join()

            print("run_: Waiting for show")
            show_thread.join()
            if idx == 0:
                move_thread = threading.Thread(target=self.move_zaber, args=(thickness, e_time, False))
                move_thread.start()
                move_thread.join()
        
        # Update automated logger with current layer
        layer_number = idx + 1  # Layer numbers are 1-indexed
        if self.sensor_data_window_instance and hasattr(self.sensor_data_window_instance, 'update_auto_logger_current_layer'):
            try:
                current_z_pos = float(self.axis.get_position(Units.LENGTH_MILLIMETRES))
                self.sensor_data_window_instance.update_auto_logger_current_layer(
                    layer_number, 
                    current_z_pos,
                    image_path=self.image_list[idx]
                )
                print(f"? Layer {layer_number} logged at Z={current_z_pos:.4f}mm")
            except Exception as e:
                print(f"?? Could not log layer {layer_number}: {e}")
        
        idx += 1
        self.progress['value'] = 100 / len(self.exposure_time) * idx
        if idx >= len(self.exposure_time):
            self.flag = False
            print("done printing")
            self.set_home()
            cv2.destroyAllWindows()
            
        if self.flag:
            self.win.update()
            self.win.after(1, self._(idx))
            
    def set_home(self):
        """Set the position to home"""
        try:
            self.reference = float(self.z_axis_position.cget("text"))
            print(f"Label data: {self.reference}")
        except:
            pass
        self.axis.move_min(True)
        self.t8.delete(0, 'end')
        self.t8.insert(END, str("Home Set"))
        
    def get_position(self):
        """Update Current Z Position"""
        reference = float(self.axis.get_position(Units.LENGTH_MILLIMETRES))
        print(f"reference {reference}") 
        self.z_axis_position.delete(0, 'end')
        self.z_axis_position.insert(END, str(reference))
        
    def set_position(self):
        """Update Current Z Position"""
        self.reference = float(self.z_axis_position.get())
        self.axis.move_absolute(self.reference, unit=Units.LENGTH_MILLIMETRES)
  
    def stop(self):
        """User Interruption"""
        self.flag = False
        self.progress['value'] = 0
        cv2.destroyAllWindows()
        
    def initialize_stage(self):
        self.axis.move_min(True)
        
    def input_directory(self):
        """Input all images from txt"""
        path = str(self.entPath.get())
        print("setting image dir")
        self.image_list, self.exposure_time, self.thickness = self.application.set_image_directory(path)
        
    def moveup(self):
        """Move up by distance(mm) given"""
        self.axis.move_relative((float(self.t9.get()) * -1), Units.LENGTH_MILLIMETRES, False)
        
    def movedown(self):
        """Move down by distance(mm) given"""
        self.axis.move_relative((float(self.t9.get())), Units.LENGTH_MILLIMETRES, False)
        
    def simple_txt(self):
        """Generator txt with given exposure time and layer thickness"""
        path = str(self.entPath.get())
        thickness = str(self.t10.get())
        time_val = str(self.t11.get())
        self.application.generate_debug_txt(path=path, thickness=thickness, time=time_val)
        
    def set_power(self):
        """Set LED power"""
        power = float(self.led_power.get())
        if power > 2.5:
            power = 2.5
        self.controller.set_amplitude(power)
        
    def cleanup(self):
        """Clean up resources before closing"""
        print("Cleaning up resources")
        if self.enable_device:
            self.zaber_motor.disconnect()
            self.controller.disconnect()
        
        # Close force sensing windows
        if self.sensor_data_window_instance:
            try:
                self.sensor_data_window_instance.sensor_window.destroy()
            except:
                pass
        
        if self.exp_conditions_window:
            try:
                self.exp_conditions_window.window.destroy()
            except:
                pass
        
        self.win.destroy()


if __name__ == "__main__":
    mode_str = "PHIDGET SPOOFED" if SPOOF_PHIDGET else "FULL HARDWARE"
    print(f"\n???  RED Printer - Force Sensing Enabled ({mode_str})\n")
    
    window = Tk()
    mywin = MyWindow(window)
    title = 'RED Printer - Force Sensing'
    if SPOOF_PHIDGET:
        title += ' [PHIDGET SPOOFED]'
    window.title(title)
    window.geometry("1200x800+10+10")
    window.mainloop()
