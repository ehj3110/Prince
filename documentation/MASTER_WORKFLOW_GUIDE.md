# Prince Segmented Complete Workflow Guide

**Master documentation for the Prince DLP 3D printing system - Complete workflow from setup to post-processing**

Last Updated: February 3, 2026

---

## Document Purpose

This is the **master reference** for operating the Prince_Segmented.py DLP printing system. It consolidates all workflow steps, technical details, and operational procedures into one comprehensive guide.

**Who this is for:**
- New users learning the complete workflow
- Experienced users needing quick reference
- Researchers conducting adhesion experiments
- Anyone troubleshooting printing issues

**Related Documentation:**
- `PRE_PRINT_SETUP_GUIDE.md` - Detailed hardware/software setup
- `PRINTING_PROCESS_GUIDE.md` - Technical printing details
- `POST_PROCESSING_GUIDE.md` - Data analysis procedures
- `SANDWICH_ROUTINE_GUIDE.md` - Sandwich mode specifics
- `support_modules/README.md` - Module technical reference

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Quick Start Workflow](#quick-start-workflow)
3. [Pre-Print Setup](#pre-print-setup)
4. [Creating Print Instructions](#creating-print-instructions)
5. [Running a Print](#running-a-print)
6. [Data Logging](#data-logging)
7. [Post-Print Processing](#post-print-processing)
8. [Sandwich Routine](#sandwich-routine)
9. [Troubleshooting](#troubleshooting)
10. [Technical Reference](#technical-reference)

---

## System Overview

### What is Prince_Segmented?

Prince is a custom DLP resin 3D printer designed for **adhesion force research**. Unlike commercial printers, it provides:

- **Real-time force measurement** during peeling (1200 Hz sampling)
- **Automated data logging** with configurable layer windows
- **Phase-aware analysis** (Exposure, Lift, Retract, Sandwich)
- **High-precision motion control** with multi-tier speed ramping
- **Research-grade data** for adhesion mechanics studies

### Hardware Components

```
┌─────────────────────────────────────────────────────────┐
│                  PRINCE SYSTEM ARCHITECTURE              │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Computer (Windows + Python)                             │
│  ├── Prince_Segmented.py (Main Control)                 │
│  ├── SensorDataWindow (Force GUI)                       │
│  └── Data Logging System                                │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  DLP Projector (UV Cure)                         │  │
│  │  - Texas Instruments LightCrafter                │  │
│  │  - 1920×1080 resolution                          │  │
│  │  - USB control + HDMI display                    │  │
│  └──────────────────────────────────────────────────┘  │
│                         ↕                                │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Zaber Linear Stage (Build Platform)             │  │
│  │  - Precision Z-axis control                      │  │
│  │  - Micrometers/second precision                  │  │
│  │  - USB connection                                │  │
│  └──────────────────────────────────────────────────┘  │
│                         ↕                                │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Phidgets Force Gauge (Load Cell)                │  │
│  │  - Bridge interface for force sensing            │  │
│  │  - 1200 Hz sampling rate                         │  │
│  │  - Real-time force monitoring                    │  │
│  └──────────────────────────────────────────────────┘  │
│                         ↕                                │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Allied Vision Camera (Optional)                 │  │
│  │  - Tank focus calibration                        │  │
│  │  - ChArUco pattern detection                     │  │
│  │  - Tilt angle measurement                        │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Software Architecture

```
Prince_Segmented.py (Main GUI)
├── Print Control Thread
│   ├── Image Loading
│   ├── DLP Management (pycrafter9000.py)
│   └── Motion Control (motion_controller.py)
│
├── SensorDataWindow (Force Monitoring)
│   ├── ForceGaugeManager (Hardware Interface)
│   ├── PositionLogger (CSV Writer)
│   ├── AutomatedLayerLogger (Batch Recording)
│   └── Real-time Plotting
│
├── Sandwich Routine (Optional Glass Contact)
│   ├── 3-Tier Descent (Speed ramping)
│   ├── Force Detection (Glass contact)
│   └── 3-Tier Ascent (Controlled liftoff)
│
└── Data Logging System
    ├── Raw Sensor Data (CSV)
    ├── Peak Force Logger (Per-layer metrics)
    └── Automated Work of Adhesion
```

---

## Quick Start Workflow

### Minimal Steps for Experienced Users

```
1. Launch Prince_Segmented.py
2. Open Sensor Panel → Enable Live Readout
3. Click "Generate TXT" for your image folder
4. Click "Load TXT" 
5. Set print parameters (speed, pause, intensity)
6. Click "Stepped Print"
7. Monitor force graph during print
8. Collect autolog CSV files after completion
```

### First-Time Setup Checklist

- [ ] Install Python 3.8+ with required packages
- [ ] Connect all USB devices (DLP, stage, force gauge)
- [ ] Connect HDMI to DLP projector
- [ ] Install Vimba SDK (if using camera)
- [ ] Test hardware connections
- [ ] Run auto-home sequence
- [ ] Calibrate force gauge
- [ ] Verify DLP displays patterns correctly

---

## Pre-Print Setup

### 1. Hardware Connections

**USB Devices (Required):**
1. **Phidgets Force Gauge** → Any USB port
2. **DLP Projector** → USB (control) + HDMI (display)
3. **Zaber Linear Stage** → Any USB port
4. **Allied Vision Camera** → USB 3.0 blue port (optional)

**Verify Connections:**
```
Open Prince_Segmented.py
└── If all devices connected: Status shows "Ready"
└── If missing device: Error message shows which device
```

### 2. Launch Application

```powershell
cd "C:\Users\cheng sun\BoyuanSun\Prince_CurrentWorkingVersion"
python Prince_Segmented.py
```

**Initial GUI Layout:**
```
┌──────────────────────────────────────────────────────┐
│  Prince Segmented - Main Control Window              │
├──────────────────────────────────────────────────────┤
│                                                       │
│  Image Directory: [___________________] [Browse]     │
│  Exposure Time:   [___]  Base Exposure: [___]        │
│  Layer Thickness: [___]  Intensity:     [___]        │
│  Step Speed:      [___]  Overstep:      [___]        │
│  Acceleration:    [___]  Pause:         [___]        │
│  Sandwich Speed:  [___]                              │
│                                                       │
│  [Generate TXT] [Load TXT]                           │
│  [Stepped Print] [Continuous Print]                  │
│  [Auto Home] [Initialize Stage]                      │
│  [Open Sensor Panel] [Open Camera View]              │
│                                                       │
│  Status: Ready                                       │
│  Progress: [========================] 0/0             │
└──────────────────────────────────────────────────────┘
```

### 3. Initialize Force Gauge

**Steps:**
1. Click **"Open Sensor Panel"**
2. SensorDataWindow opens in new window
3. Force gauge automatically connects
4. **Verify:** "Phidget connected successfully!" in status

**Sensor Panel Layout:**
```
┌──────────────────────────────────────────────────────┐
│  Sensor Data Window                                  │
├──────────────────────────────────────────────────────┤
│  Live Force: 0.123 N                                 │
│  Live Position: 50.000 mm                            │
│                                                       │
│  [Start Live Readout] [Stop Live Readout]            │
│  [Start Recording] [Stop Recording]                  │
│                                                       │
│  Auto-Logging: [✓] Enabled                           │
│  Logging Windows: [Browse...] logging_windows.csv    │
│                                                       │
│  ┌────────────────────────────────────────────────┐ │
│  │         Real-Time Force Graph                  │ │
│  │  Force (N)                                     │ │
│  │    ^                                           │ │
│  │    │    /\      /\                             │ │
│  │    │   /  \    /  \                            │ │
│  │    │  /    \  /    \                           │ │
│  │    └─────────────────────> Time                │ │
│  └────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

**Enable Live Readout:**
- Click **"Start Live Readout"**
- Force graph starts updating in real-time
- Current force and position display in GUI
- **Leave this running** during printing

### 4. Home the Stage

**Purpose:** Establish Z-axis reference position for all movements.

**Steps:**
1. In main window, click **"Auto Home"**
2. Stage moves upward until limit switch
3. Status shows: "Homing complete, reference established"
4. **Current position set to 0.0 mm**

**Manual Homing (if auto-home fails):**
1. Click "Initialize Stage"
2. Use manual controls to move stage up
3. Click "Set Home" when at desired position

### 5. Verify DLP Projector

**Test Pattern Display:**
1. DLP should be in **Video Mode** (displays desktop)
2. Move a window to the DLP screen to verify display
3. **Important:** DLP switches to Pattern Mode during printing

**Check DLP Power:**
- Default power: 0 (LEDs off)
- During print: Power set per-layer (0-255)
- After print: Power returns to 0

---

## Creating Print Instructions

### Instruction File Format

Prince_Segmented uses a **tab-delimited TXT file** to define print parameters. Each line represents one layer.

**File Format (10 columns):**
```
Layer	File	Thickness	Time	Intensity	Step Speed	Overstep Distance	Acceleration	Pause	Sandwich Speed
1	layer_001.png	50	9.0	255	500	300	500	0.5	100
2	layer_002.png	50	0.25	255	500	300	500	0.5	100
3	layer_003.png	50	0.25	255	500	300	500	0.5	100
...
```

**Column Definitions:**
- **Layer:** Layer number (integer)
- **File:** Image filename (PNG format)
- **Thickness:** Layer height in micrometers (µm)
- **Time:** Exposure duration in seconds (first layer = base exposure)
- **Intensity:** DLP LED power (0-255, typically 255)
- **Step Speed:** Peel speed in µm/s (e.g., 500)
- **Overstep Distance:** Peel overshoot in µm (e.g., 300)
- **Acceleration:** Stage acceleration in µm/s² (e.g., 500)
- **Pause:** Delay before next layer in seconds (e.g., 0.5)
- **Sandwich Speed:** Sandwich routine speed in µm/s (e.g., 100)

### Generating Instruction File (GUI Method)

**Steps:**
1. In main window, enter **Image Directory** path
2. Set print parameters:
   - **Base Exposure:** First layer time (e.g., 9.0 s)
   - **Exposure Time:** Normal layer time (e.g., 0.25 s)
   - **Layer Thickness:** Height per layer (e.g., 50 µm)
   - **Intensity:** DLP power (e.g., 255)
   - **Step Speed:** Peel speed (e.g., 500 µm/s)
   - **Overstep:** Peel overshoot (e.g., 300 µm)
   - **Acceleration:** Stage accel (e.g., 500 µm/s²)
   - **Pause:** Inter-layer delay (e.g., 0.5 s)
   - **Sandwich Speed:** Sandwich routine speed (e.g., 100 µm/s)
3. Click **"Generate TXT"**
4. File saved as: `<FolderName>.txt` in image directory

**Example:**
```
Image Directory: C:\Slicing\MyPrint_50umLayers\
Generated File:  C:\Slicing\MyPrint_50umLayers\MyPrint_50umLayers.txt
```

### Typical Print Parameters

**Standard Print Settings:**
- Base Exposure: 9.0 s (first layer)
- Layer Exposure: 0.25 s (subsequent layers)
- Layer Thickness: 50 µm
- DLP Intensity: 255 (full power)
- Step Speed: 500 µm/s
- Overstep: 300 µm
- Acceleration: 500 µm/s²
- Pause: 0.5 s
- Sandwich Speed: 100 µm/s

**High-Speed Print (Lower Adhesion):**
- Layer Exposure: 0.2 s
- Step Speed: 1000 µm/s
- Overstep: 200 µm
- Pause: 0.2 s

**High-Adhesion Print (Slower):**
- Layer Exposure: 0.5 s
- Step Speed: 300 µm/s
- Overstep: 500 µm
- Pause: 1.0 s

---

## Running a Print

### 1. Load Instruction File

**Steps:**
1. Click **"Load TXT"** in main window
2. System reads instruction file
3. Status shows: "Loaded X layers"
4. **Verify:** Image count matches expected layers

**What Happens:**
```python
# System parses instruction file
image_list = [...]           # 417 image paths
exposure_time = [...]        # 417 exposure times
thickness = [...]            # 417 thickness values
step_speed_list = [...]      # 417 peel speeds
overstep_distance_list = [...] # 417 overstep values
step_type_list = [...]       # 417 accelerations
pause_list = [...]           # 417 pause times
intensity_list = [...]       # 417 DLP powers
sandwich_speed_list = [...]  # 417 sandwich speeds
```

### 2. Configure Automated Data Logging (Optional)

**Purpose:** Automatically record force/position data for specific layer ranges.

**Setup:**
1. Create `logging_windows.csv` in image directory:
```csv
StartLayer,EndLayer
1,1
48,50
100,102
```

2. In Sensor Panel:
   - Check **"Auto-Logging: Enabled"**
   - Click **"Browse"** → Select `logging_windows.csv`
   - Status shows: "Configured for 3 logging windows"

**During Print:**
- System automatically starts recording when layer enters window
- Saves as: `autolog_L1-L1.csv`, `autolog_L48-L50.csv`, etc.
- **No manual intervention required**

### 3. Start Print

**Stepped Mode (Recommended):**
1. Click **"Stepped Print"** in main window
2. Print thread starts
3. Status updates: "Layer 1/417 printing..."

**Print Sequence Per Layer:**
```
┌─────────────────────────────────────────────────┐
│ LAYER i EXECUTION SEQUENCE                      │
├─────────────────────────────────────────────────┤
│                                                 │
│  1. EXPOSURE PHASE                              │
│     - DLP displays image i                      │
│     - UV LEDs on (power = intensity_list[i])    │
│     - Wait exposure_time[i] seconds             │
│     - Phase detected as "Exposure"              │
│                                                 │
│  2. DLP POWER OFF                               │
│     - DLP power = 0 (prevent background cure)   │
│     - Status: "L48: DLP power=0"                │
│                                                 │
│  3. LIFT PHASE (Peel)                           │
│     - Calculate peel target:                    │
│       z_peak = current_z - overstep_distance[i] │
│     - Move stage UP at step_speed[i]            │
│     - Acceleration = step_type[i]               │
│     - Force spikes recorded                     │
│     - Phase detected as "Lift"                  │
│     - Status: "Stepped L48: Peeling up to..."   │
│                                                 │
│  4. RETRACT PHASE (Return)                      │
│     - Calculate return target:                  │
│       z_final = reference - sum(thickness[0:i]) │
│     - Move stage DOWN to layer position         │
│     - Controlled retract speed                  │
│     - Phase detected as "Retract"               │
│     - Status: "SUCCESS L48: Return completed"   │
│                                                 │
│  5. DLP POWER RESTORE                           │
│     - DLP power = intensity_list[i+1]           │
│     - Status: "L48: DLP power restored to 255"  │
│                                                 │
│  6. SANDWICH ROUTINE (if enabled)               │
│     - Glass contact detection                   │
│     - Gap measurement                           │
│     - Controlled liftoff                        │
│     - See "Sandwich Routine" section            │
│                                                 │
│  7. PAUSE PHASE                                 │
│     - Wait pause_list[i] seconds                │
│     - Resin settles                             │
│     - Phase detected as "Pause"                 │
│                                                 │
│  8. DATA LOGGING                                │
│     - AutomatedLayerLogger checks window        │
│     - If in window: Save data to autolog CSV    │
│     - PeakForceLogger calculates peak force     │
│                                                 │
└─────────────────────────────────────────────────┘
```

### 4. Monitor Print Progress

**Main Window Status:**
```
Status: Layer 48/417 printing...
Progress: [===========>            ] 12%
Estimated Time Remaining: 45 min
```

**Sensor Panel (Real-Time):**
- Force graph shows live force trace
- Lift phases show characteristic force spikes
- Retract phases show force return to baseline
- Sandwich phases (if enabled) show glass contact

**Expected Force Profile:**
```
Force (N)
  ^
  │     LIFT      RETRACT    SANDWICH
  │      /\          │         /\
  │     /  \         │        /  \
  │    /    \        │       /    \
  │___/______\_______│______/______\___
  └────────────────────────────────────> Time
     EXP    LIFT   RET  PAUSE  SAND
```

### 5. Print Completion

**Automatic Cleanup:**
1. All logging stops
2. CSV files closed and saved
3. DLP reset to Video Mode
4. DLP power = 0
5. Stage remains at final position
6. Status: "Print completed successfully"

**Files Generated:**
```
PrintingLogs_Backup/
└── YYYY-MM-DD/
    └── Print 1/
        ├── autolog_L1-L1.csv
        ├── autolog_L48-L50.csv
        ├── autolog_L100-L102.csv
        ├── automated_work_of_adhesion.csv
        └── experimental_conditions.json
```

---

## Data Logging

### Three-Tier Logging System

**1. Real-Time Sensor Data (PositionLogger)**
- **Frequency:** 25 ms intervals (40 Hz)
- **Format:** CSV (Time, Position, Force, Phase)
- **Purpose:** Complete force/position trace

**2. Automated Layer Logging (AutomatedLayerLogger)**
- **Frequency:** User-defined layer windows
- **Format:** CSV per window (e.g., `autolog_L48-L50.csv`)
- **Purpose:** Batch data extraction for specific layers

**3. Peak Force Logging (PeakForceLogger)**
- **Frequency:** One entry per layer
- **Format:** CSV (Layer, Peak_Force, Work_of_Adhesion, Area)
- **Purpose:** Per-layer adhesion metrics

### Automated Layer Logging Setup

**1. Create Logging Windows File:**

File: `logging_windows.csv` (save in image directory)
```csv
StartLayer,EndLayer
1,1
48,50
100,102
200,205
```

**2. Enable in Sensor Panel:**
- Check **"Auto-Logging: Enabled"**
- Browse to `logging_windows.csv`
- Verify: "Configured for 4 logging windows"

**3. During Print:**
```
Layer 1: AutomatedLayerLogger starts recording → autolog_L1-L1.csv
Layer 2-47: No recording
Layer 48: AutomatedLayerLogger starts recording → autolog_L48-L50.csv
Layer 51-99: No recording
Layer 100: AutomatedLayerLogger starts recording → autolog_L100-L102.csv
...
```

### Output Files

**autolog_L48-L50.csv:**
```csv
Time,Position,Force,Phase
0.000,50.500,0.123,Exposure
0.025,50.500,0.124,Exposure
0.250,50.500,0.125,Exposure
1.250,50.600,0.450,Lift
1.275,50.700,0.823,Lift
1.300,50.800,1.245,Lift   <-- Peak force
1.325,50.900,0.967,Lift
1.500,51.000,0.234,Retract
2.000,50.550,0.125,Pause
...
```

**automated_work_of_adhesion.csv:**
```csv
Layer,Peak_Force_N,Work_of_Adhesion_mJ,Cross_Sectional_Area_mm2,Phase_Initiation,Phase_Propagation
1,2.345,15.67,25.0,0.500,1.200
2,1.234,8.45,25.0,0.300,0.800
48,1.567,10.23,25.0,0.450,0.950
...
```

### Phase Detection

**How it works:**
- PositionLogger monitors stage velocity and DLP state
- Automatically labels each data point with current phase
- Phases: Exposure, Lift, Retract, Pause, Sandwich

**Phase Transitions:**
```
Exposure → Lift:      Stage velocity > 10 µm/s (upward)
Lift → Retract:       Stage direction reverses (downward)
Retract → Pause:      Stage velocity < 10 µm/s
Pause → Sandwich:     Sandwich routine starts
Sandwich → Exposure:  Next layer DLP displays image
```

---

## Post-Print Processing

### Automatic Processing

**During print completion:**
1. PeakForceLogger finalizes `automated_work_of_adhesion.csv`
2. All autolog files closed
3. Experimental conditions saved (if enabled)

**No manual processing required** - data ready for analysis!

### Manual Post-Processing (Optional)

**If you need additional analysis:**

**1. Universal Processor:**
```powershell
cd post-processing
python RawData_Processor.py
```

**2. Analysis Plotter:**
```powershell
python analysis_plotter.py
```

**3. Master Plot Generator:**
```powershell
python generate_master_plot_standard_format.py
```

See `POST_PROCESSING_GUIDE.md` for detailed analysis procedures.

---

## Sandwich Routine

### What is Sandwich Mode?

**Purpose:** Measure the gap between build platform and glass substrate by controlled glass contact.

**When to use:**
- Precise gap measurement needed
- Resin thickness calibration
- Research on resin flow dynamics
- Validating layer adhesion

### Enabling Sandwich Mode

**GUI Controls:**
1. In main window, check **"Enable Sandwich"**
2. Set **Sandwich Speed** (e.g., 100 µm/s)
3. Sandwich executes after each layer's retract phase

**Sandwich Modes:**
- **Linear Scaled:** Speed scales with part cross-sectional area
- **Adaptive:** 4-tier speed ramping for large gaps
- **Smooth:** Single-speed descent with controlled liftoff

### Sandwich Execution Sequence

```
┌─────────────────────────────────────────────────┐
│ SANDWICH ROUTINE SEQUENCE                       │
├─────────────────────────────────────────────────┤
│                                                 │
│  1. START POSITION                              │
│     - Current position: Layer height            │
│     - Gap estimate: From previous measurement   │
│                                                 │
│  2. DESCENT (3-Tier Ramping)                    │
│     - Tier 1: Fast descent (50% of gap)         │
│       Speed = sandwich_speed µm/s               │
│     - Tier 2: Medium descent (85% of gap)       │
│       Speed = sandwich_speed / 4                │
│     - Tier 3: Slow approach (100% to glass)     │
│       Speed = sandwich_speed / 16               │
│     - Force monitoring active                   │
│                                                 │
│  3. GLASS CONTACT DETECTION                     │
│     - Force threshold reached                   │
│     - Record exact contact position             │
│     - Measured gap = contact_pos - layer_height │
│                                                 │
│  4. ASCENT (3-Tier Ramping)                     │
│     - Tier 3: Slow liftoff (15% of gap)         │
│       Speed = sandwich_speed / 16               │
│     - Tier 2: Medium ascent (50% of gap)        │
│       Speed = sandwich_speed / 4                │
│     - Tier 1: Fast return (100% to layer)       │
│       Speed = sandwich_speed                    │
│                                                 │
│  5. RETURN TO LAYER HEIGHT                      │
│     - Final position = layer_height             │
│     - Ready for next exposure                   │
│                                                 │
└─────────────────────────────────────────────────┘
```

**Force Profile During Sandwich:**
```
Force (N)
  ^
  │                /\ Contact
  │               /  \
  │              /    \
  │_____________/      \____________
  └────────────────────────────────> Time
     Descent   Contact   Ascent
```

### Sandwich Settings

**Key Parameters:**
- **sandwich_speed_list[i]:** Base sandwich speed (µm/s)
- **contact_force_threshold:** Force to detect glass (N)
- **smooth_pause_at_contact_s:** Hold time at glass (s)

**Typical Values:**
- Sandwich Speed: 100 µm/s
- Contact Threshold: 0.5 N
- Pause at Contact: 0.5 s

See `SANDWICH_ROUTINE_GUIDE.md` for advanced sandwich configurations.

---

## Troubleshooting

### Common Issues

**1. Force Gauge Not Connecting**
- **Symptom:** "Phidget connection failed"
- **Solution:**
  - Check USB connection
  - Verify Phidgets drivers installed
  - Try different USB port
  - Restart application

**2. DLP Not Displaying Images**
- **Symptom:** DLP shows black screen during exposure
- **Solution:**
  - Verify HDMI connection
  - Check DLP is in Video Mode before print
  - Confirm DLP power > 0 during exposure
  - Test with DLP viewer software

**3. Stage Not Homing**
- **Symptom:** "Auto home failed"
- **Solution:**
  - Check stage USB connection
  - Verify stage powered on
  - Use manual home if auto-home fails
  - Check limit switch functionality

**4. Autolog Files Not Created**
- **Symptom:** No CSV files in PrintingLogs
- **Solution:**
  - Verify Auto-Logging enabled in Sensor Panel
  - Check logging_windows.csv exists and correct
  - Confirm Live Readout is running
  - Check file permissions on log directory

**5. Phase Detection Incorrect**
- **Symptom:** Phase labels wrong in CSV
- **Solution:**
  - Verify stage velocity thresholds
  - Check DLP state tracking
  - Review PositionLogger settings
  - Increase sampling rate if phases too short

### Error Messages

**"Not enough values to unpack (expected 9, got 7)"**
- **Cause:** Instruction file has old format
- **Solution:** Regenerate TXT file with current version

**"Image directory not set or invalid"**
- **Cause:** Path not specified or doesn't exist
- **Solution:** Browse to valid directory with images

**"DLP timeout during pattern upload"**
- **Cause:** USB communication issue
- **Solution:** Restart DLP, check USB coordinator

### Performance Issues

**Slow Print Speed:**
- Reduce overstep distance (less travel)
- Increase step speed (faster peel)
- Reduce pause time (less waiting)
- Disable sandwich if not needed

**High Memory Usage:**
- Reduce data logging frequency
- Clear old autolog files
- Close unused GUI windows

**USB Resource Conflicts:**
- Use USB coordinator properly
- Don't access DLP during force reads
- Space out device communications

---

## Technical Reference

### Print Parameters Explained

**Exposure Time (seconds)**
- **Base Exposure:** First layer (e.g., 9.0 s) - ensures strong adhesion to build platform
- **Layer Exposure:** Normal layers (e.g., 0.25 s) - cures current layer
- **Range:** 0.1 - 30 s typical
- **Impact:** Longer = stronger cure, higher adhesion

**Layer Thickness (micrometers)**
- **Typical:** 50 µm (0.05 mm)
- **Range:** 25-100 µm
- **Impact:** Thinner layers = higher resolution, longer prints

**DLP Intensity (0-255)**
- **Typical:** 255 (full power)
- **Range:** 0 (off) to 255 (maximum)
- **Impact:** Higher intensity = faster cure, more polymerization

**Step Speed (µm/s)**
- **Typical:** 500 µm/s
- **Range:** 100-2000 µm/s
- **Impact:** Faster = higher peel forces, shorter print time

**Overstep Distance (µm)**
- **Typical:** 300 µm
- **Range:** 100-1000 µm
- **Purpose:** Extra travel beyond layer height for complete separation
- **Impact:** Larger overstep = more separation margin, longer cycle time

**Acceleration (µm/s²)**
- **Typical:** 500 µm/s²
- **Range:** 100-1000 µm/s²
- **Impact:** Higher = faster acceleration, higher jerk forces

**Pause (seconds)**
- **Typical:** 0.5 s
- **Range:** 0-5 s
- **Purpose:** Allow resin to flow and settle before next layer
- **Impact:** Longer pause = better resin uniformity, longer print time

**Sandwich Speed (µm/s)**
- **Typical:** 100 µm/s
- **Range:** 50-500 µm/s
- **Purpose:** Controlled glass contact speed
- **Impact:** Slower = more accurate gap measurement

### File Locations

**Main Script:**
- `Prince_Segmented.py` - Start here!

**Core Modules:**
- `support_modules/ForceGaugeManager.py` - Force hardware
- `support_modules/SensorDataWindow.py` - Force GUI
- `support_modules/pycrafter9000.py` - DLP control
- `support_modules/motion_controller.py` - Stage control
- `support_modules/PositionLogger.py` - CSV data writer
- `support_modules/AutomatedLayerLogger.py` - Batch recording
- `support_modules/PeakForceLogger.py` - Adhesion metrics
- `support_modules/SandwichRoutines.py` - Sandwich mode
- `support_modules/libs.py` - Instruction file parser

**Print Data:**
- `PrintingLogs_Backup/YYYY-MM-DD/Print #/` - All log files

**Documentation:**
- `documentation/` - All guides (you are here!)

### System Requirements

**Hardware:**
- Windows 10/11 (64-bit)
- 8 GB RAM minimum
- USB 2.0 ports (3 minimum)
- USB 3.0 port (1 for camera, optional)
- HDMI output

**Software:**
- Python 3.8 or higher
- Packages: tkinter, matplotlib, numpy, pandas, scipy, cv2
- Zaber Motion API
- Phidget22 API
- Vimba SDK (optional, for camera)

### Data Flow Diagram

```
┌─────────────┐
│  Hardware   │
│  Sensors    │
└──────┬──────┘
       │ 1 ms
       ↓
┌──────────────────┐
│ ForceGaugeManager│
│ (Dynamic Decim)  │
└──────┬───────────┘
       │ 25 ms
       ↓
┌──────────────────┐
│ PositionLogger   │
│ (Phase Detect)   │
└──────┬───────────┘
       │
       ├─→ autolog_L48-L50.csv (Automated)
       ├─→ Real-time plot (GUI)
       └─→ PeakForceLogger → automated_work_of_adhesion.csv
```

---

## Appendix: Quick Command Reference

### GUI Buttons

| Button | Function |
|--------|----------|
| Generate TXT | Create instruction file from image folder |
| Load TXT | Parse instruction file, load print parameters |
| Stepped Print | Start layer-by-layer print (recommended) |
| Continuous Print | Start continuous motion print (legacy) |
| Auto Home | Move stage to limit switch, set reference |
| Initialize Stage | Connect to stage hardware |
| Open Sensor Panel | Launch force monitoring window |
| Open Camera View | Launch camera calibration (optional) |

### Keyboard Shortcuts

- **Ctrl+S** - Save current settings
- **Ctrl+L** - Load instruction file
- **Ctrl+P** - Start print
- **ESC** - Stop print (emergency)

### File Extensions

- `.png` - Layer images
- `.txt` - Instruction file
- `.csv` - Data logs
- `.json` - Configuration files
- `.md` - Documentation

---

## Document Updates

**Version History:**
- v1.0 - February 3, 2026 - Initial master workflow guide

**Maintained by:** Prince Development Team

**For Technical Support:** See `documentation/README.md` for contact info

---

**End of Master Workflow Guide**
