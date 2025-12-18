#!/usr/bin/env python
# coding: utf-8

"""
RED Lab Printer Control Software - Force Sensing Upgrade
Based on original printer_helper.py with Prince force sensing capabilities

SET MOCK_MODE = False when deploying to RED lab with actual hardware
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

# ========== MOCK MODE TOGGLE ==========
MOCK_MODE = True  # Set to False on actual RED lab system
# ======================================

# Check if running python 3
if sys.version_info[0] != 3:
    raise SystemExit("Please set kernel to Python 3.x.x")

if MOCK_MODE:
    print("=" * 70)
    print("MOCK MODE ENABLED - Running without hardware for GUI testing")
    print("=" * 70)
    
    # Mock OpenCV
    class MockCV2:
        IMREAD_GRAYSCALE = 0
        WND_PROP_FULLSCREEN = 0
        WINDOW_FULLSCREEN = 1
        
        @staticmethod
        def imread(path, flags=None):
            return None
        @staticmethod
        def imshow(window_name, image):
            pass
        @staticmethod
        def waitKey(delay):
            return -1
        @staticmethod
        def destroyAllWindows():
            pass
        @staticmethod
        def startWindowThread():
            pass
        @staticmethod
        def namedWindow(name, flags=None):
            pass
        @staticmethod
        def moveWindow(name, x, y):
            pass
        @staticmethod
        def setWindowProperty(name, prop, value):
            pass
    
    cv2 = MockCV2()
    
    # Mock screeninfo
    class MockMonitor:
        x, y = 0, 0
        width, height = 1920, 1080
    
    class MockScreenInfo:
        @staticmethod
        def get_monitors():
            return [MockMonitor()]
    
    screeninfo = MockScreenInfo()
    
    # Mock numpy
    try:
        import numpy as np
    except ImportError:
        class MockNumpy:
            @staticmethod
            def zeros(shape):
                return None
        np = MockNumpy()
    
    # Mock PIL
    try:
        from PIL import Image, ImageTk
    except ImportError:
        class MockImage:
            pass
        class MockImageTk:
            pass
        Image = MockImage()
        ImageTk = MockImageTk()
    
    # Mock dinglab_printer
    class MockResult:
        def getSuccess(self):
            return True
        def getMessage(self):
            return "Mock OK"
    
    class MockController:
        def check_connection(self):
            return MockResult()
        def initialize(self):
            return MockResult()
        def change_mode_to_displayport(self):
            return MockResult()
        def set_amplitude(self, value):
            pass
        def led_activate(self):
            pass
        def led_deactivate(self):
            pass
        def disconnect(self):
            pass
    
    class MockDinglabPrinter:
        Controller = MockController
    
    dinglab_printer = MockDinglabPrinter()
    
    # Mock Zaber
    class MockZaberAxis:
        def __init__(self):
            self._position = 10.0
            self._busy = False
        
        def move_absolute(self, position, unit=None, wait_until_idle=True, 
                         velocity=None, velocity_unit=None, 
                         acceleration=None, acceleration_unit=None):
            self._busy = True
            self._position = position if unit is None else position
            if wait_until_idle:
                time.sleep(0.05)
                self._busy = False
        
        def move_relative(self, distance, unit=None, wait_until_idle=True,
                         velocity=None, velocity_unit=None):
            self._busy = True
            self._position += distance
            if wait_until_idle:
                time.sleep(0.05)
                self._busy = False
        
        def move_min(self, wait_until_idle=True):
            self._busy = True
            self._position = 0.0
            if wait_until_idle:
                time.sleep(0.05)
                self._busy = False
        
        def get_position(self, unit=None):
            return self._position
        
        def is_busy(self):
            return self._busy
        
        def stop(self):
            self._busy = False
    
    class MockConnection:
        @staticmethod
        def open_serial_port(port):
            return MockConnection()
        def enable_alerts(self):
            pass
        def detect_devices(self):
            return [MockZaberDevice()]
        def close(self):
            pass
    
    class MockZaberDevice:
        def get_axis(self, num):
            return MockZaberAxis()
    
    class MockLibrary:
        @staticmethod
        def enable_device_db_store():
            pass
    
    class MockUnits:
        LENGTH_MILLIMETRES = "mm"
        LENGTH_MICROMETRES = "um"
        VELOCITY_MILLIMETRES_PER_SECOND = "mm/s"
        VELOCITY_MICROMETRES_PER_SECOND = "um/s"
        ACCELERATION_MILLIMETRES_PER_SECOND_SQUARED = "mm/s2"
    
    Library = MockLibrary
    Units = MockUnits()
    Connection = MockConnection
    
    # Mock USB (for imports)
    class MockUSB:
        class core:
            @staticmethod
            def find(*args, **kwargs):
                return None
        class util:
            pass
    usb = MockUSB()
    
else:
    # Real imports for actual hardware
    import cv2
    import screeninfo
    import numpy as np
    from PIL import Image, ImageTk
    from zaber_motion import Units
    from zaber_motion.ascii import Connection
    from zaber_motion import Library
    import usb.core
    import usb.util 
    import dinglab_printer

from pprint import pprint

# Add support_modules to Python path for force gauge integration
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'support_modules'))

# Make mock modules available to support modules in MOCK_MODE
if MOCK_MODE:
    import sys
    # Inject mock modules into sys.modules so support_modules can import them
    sys.modules['cv2'] = cv2
    sys.modules['numpy'] = np
    sys.modules['screeninfo'] = screeninfo
    sys.modules['zaber_motion'] = type('MockModule', (), {
        'Units': Units,
        'Library': Library,
        'exceptions': type('MockExceptions', (), {'MovementFailedException': Exception})()
    })()
    sys.modules['zaber_motion.ascii'] = type('MockModule', (), {'Connection': Connection})()
    sys.modules['Phidget22'] = type('MockModule', (), {})()
    sys.modules['Phidget22.Phidget'] = type('MockModule', (), {})()
    sys.modules['Phidget22.Devices'] = type('MockModule', (), {})()
    sys.modules['Phidget22.Devices.VoltageRatioInput'] = type('MockModule', (), {'VoltageRatioInput': type('VoltageRatioInput', (), {})})()
    sys.modules['usb'] = usb
    sys.modules['usb.core'] = usb.core
    sys.modules['usb.util'] = usb.util

# Import Prince force sensing modules
try:
    from ForceGaugeManager import ForceGaugeManager
    from SensorDataWindow import SensorDataWindow
    from PositionLogger import PositionLogger
    from AutomatedLayerLogger import LayerLogger
    from ExperimentalConditionsWindow import ExperimentalConditionsWindow
    from AutoHomeRoutine import AutoHomer
    FORCE_SENSING_AVAILABLE = True
    print("✓ Force sensing modules loaded")
except ImportError as e:
    print(f"⚠ Force sensing modules not available: {e}")
    traceback.print_exc()
    FORCE_SENSING_AVAILABLE = False


class ZaberMotor:
    def __init__(self):
        self.init = None
        self.connection = None

    def get_zaber_motor(self):
        if MOCK_MODE:
            print("MOCK: Creating mock Zaber axis")
            return MockZaberAxis()
        
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


def print_result(operation, result):
    if result.getSuccess():
        print(f"Operation {operation} Success")
        return True
    else:
        print(f"Failed!! {operation}: {result.getMessage()}.")
        return False


class Application():
    def __init__(self):
        self.init = None
         
    def set_image_directory(self, txt_path=''):
        '''
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
                image_list.append(path +'\\' + image_path)
        return image_list, exposure_time_list, thickness_list
    
    def generate_debug_txt(self, path='', thickness='5', pause='0', material='1', time='1', intensity='0'):
        txt_name = path.split('\\')[-1] + '.txt'
        txt_path = path + '\\'+ txt_name
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
3. Connect Phidget force gauge (optional)

Trouble Shooting:
1. USB Input/output error: Close DLP Lightcrafter GUI.
2. Reconnect stage with Zaber Motion app.
3. Force gauge: Check Phidget Control Panel
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
        
        win.protocol("WM_DELETE_WINDOW", lambda : self.cleanup())
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
        self.led_power.place(x=240, y=280)
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
            print("Checkbutton")
            print(self.checkbutton_value)
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
            print("setting the editbox")
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
            
            # Sensor panel and exp conditions buttons below auto-home frame
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
        self.b8 = Button(win, text='Set Power', command=self.set_power)
        
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
            if MOCK_MODE:
                print("MOCK: Initializing mock DLP controller")
                self.controller = MockController()
            else:
                self.controller = dinglab_printer.Controller()
            
            r = self.controller.check_connection()
            print_result("Check Connection", r)
            r = self.controller.initialize()
            print_result("Initialize Printer", r)
            r = self.controller.change_mode_to_displayport()
            print_result("Change Mode to DP", r)

            if not MOCK_MODE:
                Library.enable_device_db_store()
            self.zaber_motor = ZaberMotor()
            self.axis = self.zaber_motor.get_zaber_motor()
            
            # Initialize force gauge if available (skip in mock mode)
            if FORCE_SENSING_AVAILABLE and not MOCK_MODE:
                self.initialize_force_gauge()
            elif MOCK_MODE and FORCE_SENSING_AVAILABLE:
                print("MOCK: Force gauge initialization skipped")
        
        if MOCK_MODE:
            class MockScreen:
                x, y = 0, 0
                width, height = 1920, 1080
            self.screen = MockScreen()
            print("MOCK: Using mock screen")
        else:
            screen_id = 0
            self.screen = screeninfo.get_monitors()[screen_id]
            print("Screen info")
            print(screeninfo.get_monitors())
        
        self.window_name = 'show'
        if not MOCK_MODE:
            self.black_image = np.zeros((1080, 1920))
        
        print("RED Printer system initialized successfully")

    def initialize_force_gauge(self):
        """Initialize Phidget force gauge manager"""
        try:
            self.force_data_queue = queue.Queue()
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
            print("Force gauge manager initialized successfully")
            self.update_system_message("Force gauge connected")
        except Exception as e:
            print(f"Warning: Could not initialize force gauge: {e}")
            self.force_gauge_manager = None
            self.update_system_message("Force gauge not available")
    
    def open_sensor_panel(self):
        """Open the sensor data and logging window"""
        if not FORCE_SENSING_AVAILABLE:
            print("Force sensing modules not available")
            return
            
        if self.sensor_data_window_instance and self.sensor_data_window_instance.sensor_window.winfo_exists():
            self.sensor_data_window_instance.sensor_window.lift()
            return
        
        try:
            self.sensor_data_window_instance = SensorDataWindow(
                master_window=self.win,
                zaber_axis_ref=self.axis,
                main_app_status_callback=self.update_system_message,
                prince_main_app_ref=self
            )
            print("Sensor panel opened successfully")
            self.update_auto_home_button_state()
        except Exception as e:
            print(f"Error opening sensor panel: {e}")
            traceback.print_exc()
    
    def open_exp_conditions_window(self):
        """Open experimental conditions documentation window"""
        if not FORCE_SENSING_AVAILABLE:
            print("Experimental conditions module not available")
            return
            
        if self.exp_conditions_window:
            try:
                if self.exp_conditions_window.window.winfo_exists():
                    self.exp_conditions_window.window.lift()
                    return
            except:
                # Window was destroyed, create new one
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
            self.update_system_message(f"Error opening exp conditions: {e}", error=True)
    
    def update_auto_home_button_state(self):
        """Enable/disable auto-home button based on force gauge calibration status"""
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
    
    def update_system_message(self, message, error=False):
        """Update the system message display"""
        self.t8.delete(0, 'end')
        self.t8.insert(END, str(message))
        if error:
            self.t8.config(foreground='red')
        else:
            self.t8.config(foreground='black')
        self.win.update()

    def run(self):
        """Perform a print"""
        if MOCK_MODE:
            self.update_system_message("MOCK MODE: Print simulation not available")
            print("MOCK: Run command called - would start print")
            return
        
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
        self._(0)
        self.controller.set_amplitude(0)
        self.axis.move_relative(max(0, self.offset), Units.LENGTH_MILLIMETRES, True)
        
        self.t8.delete(0, 'end')
        self.t8.insert(END, str("Print Done"))
    
    def show_image(self, image_data, exposure_time, is_continous):
        '''
        @image_data np array of image
        @param exposure_time: time in seconds 
        '''
        if MOCK_MODE:
            print(f"MOCK: show_image called - exposure={exposure_time}s, continuous={is_continous}")
            time.sleep(exposure_time * 0.1)
            return
        
        print("show_image: Started showing image")
        cv2.imshow(self.window_name, image_data)
        if not is_continous:
            self.controller.led_activate()
        wait_time_ms = int(exposure_time*1000)
        print("show_image: will wait for " + str(wait_time_ms))
        
        if not is_continous:
            if cv2.waitKey(wait_time_ms) & 0xFF == ord('q'):
                cv2.destroyAllWindows()
            self.controller.led_deactivate()
        else:
            cv2.waitKey(wait_time_ms)
        
        print("show_image: done showing image")
    
    def move_zaber(self, thickness, exposure_time, is_continous):
        print("move_zaber: Started moving")
        if is_continous:
            velocity = abs(thickness / exposure_time)
            print("move_zaber: velocity", velocity)
            self.axis.move_relative(thickness, Units.LENGTH_MILLIMETRES, True, velocity, Units.VELOCITY_MILLIMETRES_PER_SECOND)
        else:
            self.axis.move_relative(thickness, Units.LENGTH_MILLIMETRES, True, 9, Units.VELOCITY_MILLIMETRES_PER_SECOND)
        print("move_zaber: done moving")

    def _(self, idx):
        """Recursive print layer function"""
        if not self.flag:
            return
        
        image = cv2.imread(self.image_list[idx].replace('\\','\\\\'), cv2.IMREAD_GRAYSCALE)
        cv2.imshow(self.window_name, image)
        cv2.waitKey(1)
        e_time = float(self.exposure_time[idx])
        if idx == 0:
            e_time = float(self.first_layer_exposure_time.get())

        thickness = (self.thickness[idx]*-1)/1000
        print("run_: Image path", self.image_list[idx].replace('\\','\\\\'))
        print("exposure time", e_time, ' index ', idx)
        print("Thickness: ", thickness)
        
        if self.checkbutton_value.get() == True:
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
        
        idx += 1
        self.progress['value'] = 100/len(self.exposure_time)*idx
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
            print("Label data:", self.reference)
        except:
            pass
        self.axis.move_min(True)
        self.t8.delete(0, 'end')
        self.t8.insert(END, str("Home Set"))
        
    def get_position(self):
        """Update Current Z Position"""
        reference = float(self.axis.get_position(Units.LENGTH_MILLIMETRES))
        print("reference", reference) 
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
        self.axis.move_relative((float(self.t9.get())*-1), Units.LENGTH_MILLIMETRES, False)
        
    def movedown(self):
        """Move down by distance(mm) given"""
        self.axis.move_relative((float(self.t9.get())), Units.LENGTH_MILLIMETRES, False)
        
    def simple_txt(self):
        """Generator txt with given exposure time and layer thickness"""
        path = str(self.entPath.get())
        thickness = str(self.t10.get())
        time = str(self.t11.get())
        self.application.generate_debug_txt(path=path, thickness=thickness, time=time)
        
    def set_power(self):
        """Set LED power"""
        power = float(self.led_power.get())
        if power > 2.5:
            power = 2.5
        self.controller.set_amplitude(power)
        
    def cleanup(self):
        """Clean up resources before closing"""
        print("Cleaning up resources")
        if self.enable_device and not MOCK_MODE:
            self.zaber_motor.disconnect()
            self.controller.disconnect()
        elif MOCK_MODE:
            print("MOCK: Cleanup called")
        
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
    if MOCK_MODE:
        print("\n🎭 MOCK MODE - GUI Testing Without Hardware\n")
    else:
        print("\n🖨️  RED Printer - Force Sensing Enabled\n")
    
    window = Tk()
    mywin = MyWindow(window)
    window.title('RED Printer - Force Sensing Integration' + (' [MOCK MODE]' if MOCK_MODE else ''))
    window.geometry("1200x800+10+10")
    window.mainloop()
