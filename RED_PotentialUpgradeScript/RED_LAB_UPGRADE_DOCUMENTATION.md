# RED Lab Printer Upgrade - Force Sensing Integration

**Date:** December 18, 2025  
**Author:** Evan Jones (evanjones2026@u.northwestern.edu)  
**Purpose:** Integration of Prince system's force sensing capabilities into RED lab's DLP printer

---

## Executive Summary

This upgrade adds force sensing and automated data logging capabilities from the Prince 3D printing system to the RED lab's DLP printer. The integration is modular and preserves all existing RED lab functionality while adding:

1. Real-time force sensing with data visualization
2. Automated surface detection (auto-home routine)
3. Layer-by-layer data logging
4. Experimental conditions tracking

**Key Design Decision:** Mock mode capability allows complete GUI testing without hardware, enabling development and verification before deployment.

---

## What Was Changed

### 1. Main Control File: RED_Segmented.py (1048 lines)

**Created from:** `printer_helper.py` (original RED lab control file)

**Major Additions:**
- **Mock Mode System (lines 43-264):**
  - Toggle variable `MOCK_MODE = True/False` (line 43)
  - Mock classes for all hardware dependencies (cv2, numpy, dinglab_printer, Zaber, Phidget22)
  - sys.modules injection for support_modules compatibility
  - Allows GUI testing without any hardware connected

- **Force Sensing Integration:**
  - ForceGaugeManager initialization and control
  - SensorDataWindow integration for real-time plotting
  - Auto-Home Control frame with configurable thresholds
  - Buttons for Sensor Panel and Experimental Conditions

- **Preserved Functionality:**
  - All original RED lab DLP control (KPDLP660 chipset)
  - Zaber stage control via COM3
  - LED power management
  - Stepwise print flow with resin_filling_time
  - All existing buttons and controls

**Key Lines:**
- Line 43: `MOCK_MODE = True` - **MUST SET TO FALSE FOR DEPLOYMENT**
- Lines 605-609: Force sensing buttons (Sensor Panel, Exp Conditions)
- Lines 577-604: Auto-Home Control frame
- Lines 709-797: Force sensing methods

### 2. Support Modules Added (10 files in support_modules/)

All modules copied from Prince system with modifications for compatibility:

#### ForceGaugeManager.py (974 lines)
- **Purpose:** Phidget VoltageRatioInput control with decimation (1200Hz → 40Hz)
- **Modifications:**
  - Added Phidget22 mock classes (lines 14-62) for testing without hardware
  - Mock VoltageRatioInput includes getAttached() method to prevent errors
- **Hardware:** Phidget bridge amplifier with load cell

#### SensorDataWindow.py (1232 lines)
- **Purpose:** Real-time force plotting, calibration, and data logging
- **Modifications:**
  - Removed "Work of Adhesion" checkbox (not needed for RED lab)
  - Updated credits to Evan Jones only
- **Features:**
  - Live force vs time plotting
  - Force gauge calibration (tare, apply known force)
  - Position logging with CSV export
  - Integration with AutomatedLayerLogger

#### AutoHomeRoutine.py (226 lines)
- **Purpose:** Automated surface detection using force feedback
- **Features:**
  - Configurable approach parameters (guess distance, force thresholds)
  - Two-phase approach (fast then slow)
  - Stiffness calculation from force-displacement data
  - Safe movement with force monitoring

#### AutomatedLayerLogger.py (203 lines)
- **Purpose:** Layer-by-layer adhesion force logging
- **Features:**
  - CSV export with timestamp, layer, position, peak force
  - Integration with experimental conditions
  - Automatic file naming with date/time

#### ExperimentalConditionsWindow.py (474 lines)
- **Purpose:** Test documentation and metadata tracking
- **Modifications:**
  - Removed 6 fields not relevant to RED lab (TEMPO pattern, Oil, Fluid type, Fluid gap, Tank, Build platform)
  - Added "Notes" text box for flexible documentation
- **Kept Fields:** User, Membrane Type, Resin, Notes
- **Features:**
  - CSV logging of conditions
  - Print failure detection
  - Status tracking

#### Supporting Files:
- **PositionLogger.py:** Continuous position/force logging thread
- **PeakForceLogger.py:** Peak force detection per layer
- **adhesion_metrics_calculator.py:** Post-processing calculations
- **USBCoordinator.py:** USB device conflict management
- **two_step_baseline_analyzer.py:** Baseline force analysis

---

## Why These Changes Were Made

### Design Rationale

1. **Mock Mode System:**
   - **Problem:** Cannot test GUI on development machine without all hardware
   - **Solution:** Comprehensive mock classes simulate all hardware behavior
   - **Benefit:** Complete GUI testing, development iteration, and debugging without hardware access

2. **Modular Architecture:**
   - **Problem:** Original RED lab file was 826-line monolith
   - **Solution:** Integrate proven modular components from Prince system
   - **Benefit:** Easier maintenance, testing, and future updates

3. **Hardware Compatibility:**
   - **Problem:** Different DLP chipsets between systems (DLPC900 vs KPDLP660)
   - **Solution:** Keep RED lab's existing DLP control, only add force sensing
   - **Benefit:** Zero risk to existing print functionality

4. **Simplified UI:**
   - **Problem:** Prince system has many experiment-specific fields
   - **Solution:** Remove unused fields, add flexible Notes box
   - **Benefit:** Cleaner interface focused on RED lab's needs

### Scope Decision

**Explicitly Included:**
- SensorDataWindow (force plotting and calibration)
- Auto-Home Routine (surface detection)
- AutomatedLayerLogger (layer data logging)
- ExperimentalConditionsWindow (test documentation)

**Explicitly Excluded:**
- Sandwich routine (Prince-specific)
- Post-processing scripts (separate analysis)
- Adhesion metrics calculation during print (post-processing only)

---

## Deployment Steps for RED Lab Computer

### Prerequisites

**Hardware Required:**
- RED lab DLP printer with KPDLP660 controller
- Zaber stage (already installed, COM3)
- Phidget VoltageRatioInput bridge amplifier
- Load cell (compatible with Phidget bridge input)
- USB connections for all devices

**Software Required:**
- Python 3.x (already installed)
- All existing RED lab dependencies (dinglab_printer, numpy, PIL, etc.)
- **NEW:** Phidget22 Python library

---

### Step-by-Step Deployment

#### 1. Transfer Files to RED Lab Computer

Copy the following to the RED lab system:

```
RED_PotentialUpgradeScript/
├── RED_Segmented.py (main control file)
└── support_modules/
    ├── ForceGaugeManager.py
    ├── SensorDataWindow.py
    ├── AutoHomeRoutine.py
    ├── PositionLogger.py
    ├── AutomatedLayerLogger.py
    ├── ExperimentalConditionsWindow.py
    ├── PeakForceLogger.py
    ├── adhesion_metrics_calculator.py
    ├── USBCoordinator.py
    └── two_step_baseline_analyzer.py
```

**Keep existing files:**
- `dinglab_printer/` (DLP control library)
- `dinglab_printer_notebook/` (reference)
- Any existing print job files

#### 2. Install Phidget22 Library

Open PowerShell or Command Prompt:

```powershell
pip install Phidget22
```

**Verify installation:**
```powershell
python -c "import Phidget22; print('Phidget22 installed successfully')"
```

If you see any errors, Phidget22 may need the full installer from phidgets.com.

#### 3. Connect Hardware

**Physical Connections:**
1. Connect Phidget bridge amplifier to USB port
2. Connect load cell to bridge amplifier (follow wiring diagram)
3. Verify Zaber stage on COM3
4. Verify DLP on DisplayPort

**Test Connections:**
- Open Phidget Control Panel (if installed) to verify bridge amplifier detected
- Zaber should already be working from existing setup

#### 4. Configure RED_Segmented.py for Hardware

**CRITICAL:** Edit `RED_Segmented.py` line 43:

```python
# Change from:
MOCK_MODE = True

# To:
MOCK_MODE = False
```

**Save the file after making this change.**

#### 5. Initial Hardware Test

Launch the control software:

```powershell
cd RED_PotentialUpgradeScript
python RED_Segmented.py
```

**Expected startup messages:**
```
✓ Force sensing modules loaded
Operation Check Connection Success
Operation Initialize Printer Success
Operation Change Mode to DP Success
Zaber axis initialized on COM3
Force gauge initialization skipped (no calibration yet)
RED Printer system initialized successfully
```

**If you see errors:**
- Check that `MOCK_MODE = False`
- Verify USB connections
- Check COM3 for Zaber stage
- Ensure dinglab_printer library is in the correct location

#### 6. Force Gauge Calibration

**Before first use, calibrate the force gauge:**

1. Click **"Open Sensor Panel"** button
2. SensorDataWindow opens with real-time force plot
3. Click **"Calibrate Force Gauge"**
4. Follow on-screen instructions:
   - Click "Tare" with no load applied
   - Apply known force (calibration weight)
   - Enter force value in Newtons
   - Click "Apply Calibration"
5. Verify force reading with test weights
6. Save calibration (automatically stored)

**Calibration must be done before using auto-home routine.**

#### 7. Auto-Home Configuration

**Set auto-home parameters in the Auto-Home Control frame:**

**Recommended Starting Values:**
- **Guess Distance:** 10 mm (adjust based on your typical build height)
- **Abs Threshold:** 0.005 N (absolute force to detect contact)
- **Delta Threshold:** 0.002 N (change in force to confirm contact)

**These values may need tuning based on your membrane stiffness.**

#### 8. Test Auto-Home Routine

**Safety first:**
1. Ensure build plate is clear
2. Stage should be at safe height above membrane
3. Sensor Panel window must be open

**Run auto-home:**
1. Enter guess distance (10 mm is good starting point)
2. Click **"Start Auto-Home"**
3. Watch force plot in Sensor Panel
4. Stage will approach membrane and detect surface
5. System message shows final position and stiffness

**If auto-home fails:**
- Check force gauge calibration
- Adjust thresholds (may need higher/lower values)
- Verify stage movement direction (should move down)

#### 9. Test Print with Logging

**Prepare a simple test print:**

1. Load print job txt file (existing RED lab format)
2. Click **"Open Exp Conditions"** button
3. Fill in test metadata:
   - User name
   - Membrane type
   - Resin type
   - Notes (any relevant info)
4. Enable logging checkbox
5. Return to main window
6. Open Sensor Panel
7. Enable logging in Sensor Panel

**Run test print:**
1. Click "Run" to start print
2. Monitor force in real-time (Sensor Panel)
3. Check that CSV logs are being created

**Expected log files in `Position_Logs/` folder:**
- `Position_Log_YYYYMMDD_HHMMSS.csv` (continuous force/position data)
- `Autolog_LXXX-LYYY_YYYYMMDD_HHMMSS.csv` (layer-by-layer data)
- `Experimental_Conditions_YYYYMMDD_HHMMSS.csv` (test metadata)

#### 10. Verify Logging Data

**Check CSV files contain expected data:**

**Position_Log.csv should have:**
- Timestamp
- Elapsed_Time_s
- Z_Position_mm
- Force_N
- Print_Phase

**Autolog.csv should have:**
- Layer
- Peak_Force_N
- Z_Position_Start_mm
- Z_Position_End_mm
- Timestamp

**Experimental_Conditions.csv should have:**
- Print_Date_Time
- User
- Membrane_Type
- Resin
- Notes
- Print_Status

---

## Operational Guide

### Starting a Print with Force Sensing

1. **Initialize System:**
   - Launch RED_Segmented.py
   - Click "Open Sensor Panel"
   - Verify force gauge reading (should be near zero)

2. **Surface Detection:**
   - Raise stage to safe height
   - Enter guess distance in Auto-Home Control
   - Click "Start Auto-Home"
   - Wait for surface detection (watch force plot)
   - Note final Z position shown in system message

3. **Configure Experimental Conditions:**
   - Click "Open Exp Conditions"
   - Fill in user, membrane type, resin, notes
   - Enable logging checkbox
   - Close window

4. **Enable Data Logging:**
   - In Sensor Panel, enable logging options:
     - Real-time position logging (if desired)
     - Automated layer logging (recommended)
   - Leave Sensor Panel open during print

5. **Load Print Job:**
   - Click "Input Directory"
   - Select folder with txt print job file
   - Verify layer count and parameters

6. **Run Print:**
   - Click "Run"
   - Monitor force in Sensor Panel
   - System will log data automatically
   - Wait for completion

7. **Post-Print:**
   - Stop any active logging
   - Save force plot (optional)
   - Close Sensor Panel
   - CSV files saved in Position_Logs/

### Emergency Stop

**If something goes wrong during print:**
1. Click **"Stop"** button immediately
2. Stage will halt
3. Close all logging windows
4. Use manual controls to move stage to safe position
5. Investigate issue before resuming

### Troubleshooting

**Force gauge not responding:**
- Check USB connection
- Verify Phidget22 installed: `python -c "import Phidget22"`
- Restart application
- Check Phidget Control Panel (if available)

**Auto-home fails to find surface:**
- Increase guess distance
- Adjust thresholds (try 0.01 N absolute, 0.005 N delta)
- Check force gauge calibration
- Verify stage moving in correct direction

**No CSV logs created:**
- Check logging enabled in both Sensor Panel and Exp Conditions
- Verify write permissions in Position_Logs/ folder
- Check system messages for errors

**DLP not displaying patterns:**
- This should work exactly as before
- Check dinglab_printer library
- Verify DisplayPort connection
- This upgrade does not change DLP control

---

## Configuration Reference

### MOCK_MODE Toggle

**Location:** RED_Segmented.py, line 43

```python
MOCK_MODE = True   # For testing GUI without hardware
MOCK_MODE = False  # For actual printer operation
```

**When MOCK_MODE = True:**
- All hardware calls are simulated
- GUI functions normally
- No actual device connections needed
- Window title shows "[MOCK MODE]"
- Useful for training, GUI development, testing

**When MOCK_MODE = False:**
- Real hardware control
- Requires all devices connected
- Force gauge must be calibrated
- Production mode for actual printing

### Auto-Home Parameters

**Guess Distance (mm):**
- How far to move down from current position
- Start with 10 mm, adjust based on typical build height
- Too small: Won't reach surface
- Too large: Stage may crash if starting position wrong

**Absolute Force Threshold (N):**
- Minimum force to detect contact
- Default: 0.005 N (5 mN)
- Increase if false triggers from noise
- Decrease if failing to detect soft membranes

**Delta Force Threshold (N):**
- Required change in force to confirm contact
- Default: 0.002 N (2 mN)
- Confirms contact vs noise
- Should be smaller than absolute threshold

### Force Gauge Decimation

**Configured in ForceGaugeManager.py:**
- Raw sampling: 1200 Hz
- Decimated output: 40 Hz (30:1 ratio)
- Reduces data volume while maintaining responsiveness
- Adjustable if needed (line 100-110 of ForceGaugeManager.py)

---

## File Structure Reference

```
RED_PotentialUpgradeScript/
│
├── RED_Segmented.py              # Main control file (SET MOCK_MODE = False)
│
├── support_modules/               # Force sensing modules
│   ├── ForceGaugeManager.py      # Phidget bridge control
│   ├── SensorDataWindow.py       # Real-time plotting GUI
│   ├── AutoHomeRoutine.py        # Surface detection
│   ├── PositionLogger.py         # Continuous data logging
│   ├── AutomatedLayerLogger.py   # Layer-by-layer logging
│   ├── ExperimentalConditionsWindow.py  # Test metadata
│   ├── PeakForceLogger.py        # Peak force detection
│   ├── adhesion_metrics_calculator.py   # Post-processing
│   ├── USBCoordinator.py         # USB device management
│   └── two_step_baseline_analyzer.py    # Baseline analysis
│
├── dinglab_printer/              # Existing DLP control (DO NOT MODIFY)
│
├── Position_Logs/                # Created automatically, CSV logs stored here
│
└── printer_helper.py             # Original RED lab file (backup reference)
```

---

## Important Notes

### Hardware Compatibility

**DLP Controllers:**
- RED lab: KPDLP660.dll → TI DLP6600 chipset
- Prince: DLPC900 → TI DLPC900 chipset
- **These are different and NOT interchangeable**
- RED_Segmented.py uses RED lab's existing DLP control

**Zaber Stage:**
- Same hardware in both systems (COM3)
- Fully compatible, no changes needed

**Force Gauge:**
- NEW hardware for RED lab
- Phidget VoltageRatioInput bridge amplifier
- Requires calibration before use

### Print Flow Differences

**RED Lab Print Sequence (preserved):**
1. Display pattern (LED on)
2. Wait for cure time
3. Turn off LED
4. **Wait for resin_filling_time** (RED-specific delay)
5. Move stage up
6. Next layer

**This sequence is preserved exactly in RED_Segmented.py** - no changes to print timing or flow.

### Data Storage

**All logs saved to:** `Position_Logs/` folder (created automatically)

**File naming convention:**
- `Position_Log_YYYYMMDD_HHMMSS.csv`
- `Autolog_LXXX-LYYY_YYYYMMDD_HHMMSS.csv`
- `Experimental_Conditions_YYYYMMDD_HHMMSS.csv`

**Backup important data regularly** - logs can grow large with continuous position logging.

### Safety Considerations

1. **Always test auto-home with build plate clear first**
2. **Monitor first few layers of any new print**
3. **Keep "Stop" button accessible**
4. **Calibrate force gauge regularly** (weekly or after any hardware changes)
5. **Verify stage direction before auto-home** (should move down toward membrane)

---

## Credits

**Original Prince System Development:**
- Evan Jones (evanjones2026@u.northwestern.edu)
- Northwestern University, Mirkin Lab

**RED Lab Integration:**
- Evan Jones (evanjones2026@u.northwestern.edu)
- December 2025

**Force Sensing Architecture:**
- Based on Prince 3D printing system force sensing implementation
- Adapted for RED lab's KPDLP660-based printer

---

## Support and Questions

For issues, questions, or improvements:
- Contact: Evan Jones (evanjones2026@u.northwestern.edu)
- Reference this documentation file
- Include error messages and terminal output
- Note hardware configuration and MOCK_MODE setting

---

## Revision History

**v1.0 - December 18, 2025:**
- Initial integration of force sensing into RED lab printer
- Mock mode system for hardware-less testing
- Simplified experimental conditions window for RED lab needs
- Comprehensive deployment documentation
