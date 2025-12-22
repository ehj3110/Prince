# Force Sensing System Architecture

**For AI Assistants: Technical Reference**  
**Date:** December 22, 2025  
**Purpose:** Explain how Prince_Segmented, ForceGaugeManager, and SensorDataWindow interact

---

## Hardware Connection Overview

```
Physical Hardware:
┌─────────────────┐
│  Load Cell      │  ← Physical force sensor (bridge configuration)
│  (Force Gauge)  │
└────────┬────────┘
         │ 4-wire connection (Excitation+, Excitation-, Signal+, Signal-)
         ↓
┌─────────────────┐
│ Phidget Bridge  │  ← Phidget VoltageRatioInput (Wheatstone bridge amplifier)
│ Amplifier       │     Model: 1046, DAQ1500, or similar
└────────┬────────┘
         │ USB cable
         ↓
┌─────────────────┐
│   Computer      │  ← Running Prince_Segmented.py
│   (Windows)     │
└─────────────────┘
```

**Key Point for AI:** The force gauge (load cell) is NOT directly connected to the computer. It connects to the Phidget bridge amplifier, which then connects to the computer via USB.

---

## Software Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Prince_Segmented.py                        │
│                    (Main Application / GUI)                     │
│                                                                 │
│  - Creates main window (Tkinter)                              │
│  - Manages DLP projector control                              │
│  - Manages Zaber stage control                                │
│  - Creates "Open Sensor Panel" button                         │
│  - DOES NOT directly interact with Phidget                    │
│  - DOES NOT manage force gauge                                │
│                                                                 │
│  Creates ────────────────────────────────────────────┐         │
│            │                                          ↓         │
└────────────┼──────────────────────────────────────────┼─────────┘
             │                                          │
             │ Creates instance                         │
             │ Passes references                        │
             ↓                                          │
┌─────────────────────────────────────────────────────┐│
│           SensorDataWindow.py                       ││
│        (Force Sensing GUI / Coordinator)            ││
│                                                     ││
│  - Creates separate Toplevel window                ││
│  - Has "Calibrate Force Gauge" button             ││
│  - Creates and owns ForceGaugeManager instance     ││
│  - Manages data plotting (matplotlib)              ││
│  - Manages PositionLogger for CSV logging          ││
│  - Coordinates between stage and force data        ││
│                                                     ││
│  Creates ──────────────────────────────┐           ││
│              │                          ↓           ││
└──────────────┼──────────────────────────┼───────────┘│
               │                          │            │
               │ Creates instance         │            │
               │ Passes GUI references    │            │
               ↓                          │            │
┌──────────────────────────────────────┐ │            │
│    ForceGaugeManager.py              │ │            │
│  (Phidget Hardware Interface)        │ │            │
│                                      │ │            │
│  - Opens Phidget22.VoltageRatioInput│ │            │
│  - Connects to USB device            │ │            │
│  - Manages calibration (gain/offset)│ │            │
│  - Runs reading thread (decimation) │ │            │
│  - Outputs to queue for other modules│ │          │
│                                      │ │            │
│  USB ↓↑ Phidget22 Library            │ │            │
└──────────────────────────────────────┘ │            │
                                         │            │
                                         │            │
     Uses data from ←────────────────────┘            │
                                                      │
     Passes refs to ←──────────────────────────────────┘
```

---

## Component Responsibilities

### 1. Prince_Segmented.py (Main Application)

**Role:** Top-level application controller

**Responsibilities:**
- Create main Tkinter window
- Control DLP projector (via pycrafter9000 or dinglab_printer)
- Control Zaber linear stage (via zaber_motion library)
- Manage print sequence
- Create "Open Sensor Panel" button
- Create SensorDataWindow instance when button is clicked
- Pass references (self, zaber_axis, status_callback) to SensorDataWindow

**DOES NOT:**
- Import Phidget22 library
- Create ForceGaugeManager instance
- Manage force gauge hardware
- Read force data directly

**Key Code Pattern:**
```python
class MyWindow:
    def __init__(self, master):
        # ... setup main GUI ...
        
        # Button to open sensor panel
        self.b_sensor_panel = Button(master, text="Open Sensor Panel", 
                                     command=self.open_sensor_panel)
        
        # Reference to sensor window (created later)
        self.sensor_data_window_instance = None
    
    def open_sensor_panel(self):
        if not self.sensor_data_window_instance:
            # Create SensorDataWindow, passing references
            self.sensor_data_window_instance = SensorDataWindow(
                master_window=self.master,
                zaber_axis_ref=self.axis,  # Pass stage reference
                main_app_status_callback=self.update_system_message,
                prince_main_app_ref=self  # Pass self for callbacks
            )
```

---

### 2. SensorDataWindow.py (Force Sensing Coordinator)

**Role:** Force sensing subsystem GUI and coordinator

**Responsibilities:**
- Create separate Toplevel window (independent from main window)
- Create and own the ForceGaugeManager instance
- Provide GUI controls for force gauge (calibrate, tare, save)
- Create matplotlib plot for real-time force/position display
- Create PositionLogger for CSV data logging
- Coordinate data from both Zaber stage and force gauge
- Manage data queues between components
- Pass label references to ForceGaugeManager for updates

**DOES:**
- Import Phidget22 (for checking if available)
- Create ForceGaugeManager instance in __init__
- Manage the lifecycle of ForceGaugeManager
- Provide GUI elements (labels) for ForceGaugeManager to update

**Key Code Pattern:**
```python
class SensorDataWindow:
    def __init__(self, master_window, zaber_axis_ref, main_app_status_callback, prince_main_app_ref):
        # Create separate window
        self.sensor_window = Toplevel(master_window)
        
        # Store references
        self.zaber_axis = zaber_axis_ref
        self.update_main_status = main_app_status_callback
        self.prince_main_app_ref = prince_main_app_ref
        
        # Create GUI labels that ForceGaugeManager will update
        self.lbl_gain = Label(...)
        self.lbl_offset = Label(...)
        self.lbl_force_gauge_status = Label(...)
        self.lbl_current_force = Label(...)  # Large readout at top
        
        # Create queue for force data
        self.force_data_queue_for_logger = queue.Queue()
        
        # Create ForceGaugeManager instance
        self.force_gauge_manager = ForceGaugeManager(
            gain_label=self.lbl_gain,              # Pass label references
            offset_label=self.lbl_offset,
            force_status_label=self.lbl_force_gauge_status,
            large_force_readout_label=self.lbl_current_force,
            output_force_queue=self.force_data_queue_for_logger,
            parent_window=self.sensor_window,
            sensor_window_ref=self  # Pass self for callbacks
        )
```

---

### 3. ForceGaugeManager.py (Hardware Interface)

**Role:** Low-level Phidget hardware interface

**Responsibilities:**
- Import and use Phidget22 library
- Open connection to Phidget VoltageRatioInput device
- Wait for device attachment (USB connection)
- Set bridge gain and data interval
- Manage calibration (gain and offset values)
- Run background thread to read force data continuously
- Apply decimation (1200 Hz → 40 Hz) to reduce data volume
- Update GUI labels with current force readings
- Put force data into queue for other modules to consume
- Handle disconnection and cleanup

**DOES NOT:**
- Create its own window
- Manage the GUI lifecycle
- Know about the Zaber stage
- Control the print process

**Key Code Pattern:**
```python
class ForceGaugeManager:
    def __init__(self, gain_label, offset_label, force_status_label, 
                 large_force_readout_label, output_force_queue, 
                 parent_window, sensor_window_ref):
        
        # Store GUI references (for updating displays)
        self.lbl_gain = gain_label
        self.lbl_offset = offset_label
        self.lbl_force_status = force_status_label
        self.lbl_large_force_readout = large_force_readout_label
        self.output_force_queue = output_force_queue
        self.parent_window = parent_window
        self.sensor_window_ref = sensor_window_ref
        
        # Try to import Phidget22
        try:
            from Phidget22.Phidget import *
            from Phidget22.Devices.VoltageRatioInput import *
            self.voltage_ratio_input = VoltageRatioInput()
        except ImportError:
            # Use mock if not available
            self.voltage_ratio_input = MockVoltageRatioInput()
        
        # Calibration values
        self.GAIN = 1.0
        self.OFFSET = 0.0
        
        # Try to connect to hardware
        try:
            self.voltage_ratio_input.openWaitForAttachment(5000)
            self.voltage_ratio_input.setBridgeGain(BridgeGain.BRIDGE_GAIN_128)
            self.voltage_ratio_input.setDataInterval(1)  # 1ms = 1000Hz
        except:
            # Handle connection failure
            pass
        
        # Start reading thread
        self.start_force_reading_thread()
    
    def _force_reading_loop(self):
        """Background thread that continuously reads force data"""
        while self.force_reading_active:
            try:
                # Read from Phidget
                voltage_ratio = self.voltage_ratio_input.getVoltageRatio()
                
                # Apply calibration
                force_N = (voltage_ratio - self.OFFSET) * self.GAIN
                
                # Update GUI label
                self.lbl_large_force_readout.config(text=f"Force: {force_N:.4f} N")
                
                # Put in queue for other modules
                self.output_force_queue.put(('force_calibrated', force_N))
                
                # Decimation: only keep 1 out of every 30 samples
                # (reduces 1000Hz to ~33Hz)
                
            except:
                pass
```

---

## Data Flow

### Initialization Sequence:

```
1. User runs Prince_Segmented.py
   ↓
2. Prince_Segmented creates main window
   ↓
3. User clicks "Open Sensor Panel" button
   ↓
4. Prince_Segmented.open_sensor_panel() creates SensorDataWindow
   ↓
5. SensorDataWindow.__init__() creates ForceGaugeManager
   ↓
6. ForceGaugeManager.__init__() connects to Phidget via USB
   ↓
7. ForceGaugeManager starts background reading thread
```

### Real-time Data Flow:

```
Phidget Hardware (1000 Hz)
    ↓
ForceGaugeManager._force_reading_loop()
    ↓
    ├─→ Update GUI label (lbl_large_force_readout)
    └─→ Put data in queue (output_force_queue)
            ↓
            ├─→ PositionLogger reads from queue
            │   ↓
            │   Writes to CSV file
            │
            └─→ PeakForceLogger reads from queue
                ↓
                Calculates work of adhesion
```

### Calibration Sequence:

```
1. User clicks "Calibrate Force Gauge" in SensorDataWindow
   ↓
2. SensorDataWindow calls force_gauge_manager.calibrate_force_gauge()
   ↓
3. ForceGaugeManager shows dialog asking for known force
   ↓
4. ForceGaugeManager calculates GAIN and OFFSET
   ↓
5. ForceGaugeManager updates lbl_gain and lbl_offset
   ↓
6. ForceGaugeManager calls sensor_window_ref.update_calibration_status_for_main_app(True)
   ↓
7. SensorDataWindow calls prince_main_app_ref.update_auto_home_button_state()
   ↓
8. Prince_Segmented enables "Start Auto-Home" button
```

---

## Common Confusion Points for AI Assistants

### ❌ WRONG: "Prince_Segmented manages the force gauge"
**✓ CORRECT:** Prince_Segmented only creates SensorDataWindow. SensorDataWindow manages the force gauge.

### ❌ WRONG: "The force gauge connects directly via USB to the computer"
**✓ CORRECT:** Load cell → Phidget bridge → USB → Computer. The Phidget bridge is the intermediary.

### ❌ WRONG: "ForceGaugeManager creates its own window"
**✓ CORRECT:** SensorDataWindow creates the window. ForceGaugeManager only updates labels passed to it.

### ❌ WRONG: "Prince_Segmented imports Phidget22"
**✓ CORRECT:** Only ForceGaugeManager imports Phidget22. Prince_Segmented never touches Phidget22.

### ❌ WRONG: "ForceGaugeManager knows about the Zaber stage"
**✓ CORRECT:** ForceGaugeManager only knows about force. SensorDataWindow coordinates both force and position.

### ❌ WRONG: "Multiple ForceGaugeManager instances for different purposes"
**✓ CORRECT:** Only ONE ForceGaugeManager instance per SensorDataWindow. It outputs to a queue that multiple consumers read from.

---

## Reference Chain

When force gauge calibration status needs to propagate back to main app:

```
ForceGaugeManager
    ↓ (calls method on)
SensorDataWindow.update_calibration_status_for_main_app(status)
    ↓ (stores internally, then calls method on)
Prince_Segmented.update_auto_home_button_state()
    ↓ (checks)
SensorDataWindow.is_force_gauge_calibrated_internally()
    ↓ (returns boolean)
Prince_Segmented enables/disables auto-home button
```

**Key Point:** The reference chain is:
`ForceGaugeManager → SensorDataWindow → Prince_Segmented`

ForceGaugeManager can access Prince_Segmented by going through:
`self.sensor_window_ref.prince_main_app_ref`

---

## File Locations

```
Prince_Segmented_20250926/
├── Prince_Segmented.py                    ← Main application
├── support_modules/
│   ├── ForceGaugeManager.py              ← Phidget hardware interface
│   ├── SensorDataWindow.py               ← Force sensing GUI/coordinator
│   ├── PositionLogger.py                 ← CSV logging (reads force queue)
│   ├── PeakForceLogger.py                ← Work of adhesion (reads force queue)
│   └── AutoHomeRoutine.py                ← Surface detection using force
│
└── RED_PotentialUpgradeScript/
    ├── RED_Segmented.py                  ← RED lab version (same pattern)
    └── support_modules/                  ← Copies of above modules
        └── (same files, adapted for RED)
```

---

## Mock Mode (for Testing Without Hardware)

Both Prince_Segmented.py and RED_Segmented.py support mock mode:

```python
MOCK_MODE = True  # Line 43 of Prince_Segmented.py or RED_Segmented.py
```

When `MOCK_MODE = True`:
- ForceGaugeManager uses mock Phidget classes
- No actual hardware connection attempted
- GUI still works normally
- Useful for testing without hardware

**ForceGaugeManager handles this internally:**
```python
try:
    from Phidget22.Phidget import *
    from Phidget22.Devices.VoltageRatioInput import *
except ImportError:
    # Create mock classes
    class VoltageRatioInput:
        def getVoltageRatio(self):
            return 0.0  # Mock reading
```

---

## Key Design Principles

1. **Separation of Concerns:**
   - Prince_Segmented = Print control
   - SensorDataWindow = Force sensing coordination
   - ForceGaugeManager = Hardware interface

2. **Single Responsibility:**
   - Only ForceGaugeManager touches Phidget22
   - Only SensorDataWindow creates GUI windows
   - Only Prince_Segmented controls the print sequence

3. **Reference Passing:**
   - References passed down: Prince → SensorDataWindow → ForceGaugeManager
   - Callbacks go up: ForceGaugeManager → SensorDataWindow → Prince

4. **Queue-Based Communication:**
   - ForceGaugeManager outputs to queue
   - Multiple consumers (PositionLogger, PeakForceLogger) read from queue
   - Decouples producer from consumers

5. **Lifecycle Management:**
   - Prince_Segmented owns SensorDataWindow
   - SensorDataWindow owns ForceGaugeManager
   - Cleanup happens in reverse order

---

## Common Operations

### Opening Sensor Panel:
```python
# In Prince_Segmented
def open_sensor_panel(self):
    if not self.sensor_data_window_instance:
        self.sensor_data_window_instance = SensorDataWindow(...)
```

### Reading Force:
```python
# In any module that needs force data
force_data_queue = sensor_window.force_data_queue_for_logger
while not force_data_queue.empty():
    data_type, value = force_data_queue.get_nowait()
    if data_type == 'force_calibrated':
        # Use force value
```

### Calibrating Force Gauge:
```python
# In SensorDataWindow GUI
Button(text="Calibrate Force Gauge", 
       command=self.force_gauge_manager.calibrate_force_gauge)
```

### Checking Calibration Status:
```python
# In Prince_Segmented
if self.sensor_data_window_instance:
    is_calibrated = self.sensor_data_window_instance.is_force_gauge_calibrated_internally()
```

---

## For AI Making Changes

**Before making changes, ask:**

1. **Which component should this change go in?**
   - Hardware changes → ForceGaugeManager
   - GUI changes → SensorDataWindow
   - Print sequence changes → Prince_Segmented

2. **Who owns this object?**
   - Phidget connection → ForceGaugeManager
   - Force gauge manager instance → SensorDataWindow
   - Sensor window instance → Prince_Segmented

3. **How do I access X from Y?**
   - Use the reference chain (see Reference Chain section above)
   - Don't create new global instances

4. **Should I create a new ForceGaugeManager instance?**
   - NO! Only SensorDataWindow creates it, only once

5. **Where should calibration values be stored?**
   - In ForceGaugeManager (GAIN and OFFSET)
   - Loaded from file in ForceGaugeManager.__init__()

---

## Summary for AI

**The force sensing system has three layers:**

1. **Prince_Segmented.py** (top layer)
   - Knows: print control, stage control, DLP control
   - Doesn't know: force gauge hardware, Phidget22

2. **SensorDataWindow.py** (middle layer)
   - Knows: force gauge manager, stage position, data coordination
   - Creates: ForceGaugeManager, PositionLogger
   - Coordinates: data from force and position sources

3. **ForceGaugeManager.py** (bottom layer)
   - Knows: Phidget22 hardware, calibration, data reading
   - Doesn't know: GUI layout, stage control, print sequence

**Data flows DOWN through method calls, UP through callbacks and queues.**

**Each component has ONE owner, ONE instance per session.**

**When in doubt, follow the existing pattern. Don't create new instances of managers or windows.**

---

*Document version: 1.0*  
*Date: December 22, 2025*  
*For AI assistant reference when modifying force sensing code*
