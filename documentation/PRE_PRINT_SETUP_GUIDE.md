# Pre-Print Setup Guide

**Complete guide for hardware setup, GUI operation, and system verification before printing**

Last Updated: December 18, 2025

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Hardware Setup](#hardware-setup)
3. [Software Installation](#software-installation)
4. [GUI Components](#gui-components)
5. [Camera Calibration System](#camera-calibration-system)
6. [Pre-Print Verification](#pre-print-verification)
7. [Troubleshooting](#troubleshooting)

---

## System Overview

### What is Prince?

Prince is a custom DLP resin 3D printer control system designed for **scientific research on adhesion and peeling forces**. The system combines:

- **DLP Projector** - Texas Instruments LightCrafter for UV curing
- **Zaber Linear Stage** - Precise Z-axis control
- **Phidgets Force Gauge** - High-frequency force measurement (1200 Hz)
- **Allied Vision Camera** - Resin tank focus and alignment (ChArUco calibration)

### Key Features

✅ **Real-time force monitoring** during printing  
✅ **Automated adhesion metrics** calculation  
✅ **Camera-based tank calibration** (focus and tilt detection)  
✅ **High-frequency data logging** with dynamic decimation  
✅ **Post-print analysis** pipeline

---

## Hardware Setup

### Required Components

#### 1. Force Gauge (Phidgets)
- **Model:** Phidgets VoltageRatioInput (Bridge Interface)
- **Connection:** USB to computer
- **Sampling Rate:** Hardware maximum 1200 Hz (1 ms intervals)
- **Data Rate:** User-configurable 25-100 ms with dynamic decimation

#### 2. DLP Projector
- **Model:** Texas Instruments DLP LightCrafter
- **Connection:** USB for control + HDMI for display
- **Resolution:** 1920×1080 pixels
- **Control:** pycrafter9000.py module

#### 3. Zaber Linear Stage
- **Purpose:** Z-axis (build platform) control
- **Units:** Millimeters
- **Connection:** USB or RS232

#### 4. Allied Vision Camera (Optional)
- **Purpose:** Tank focus and tilt calibration
- **Connection:** USB 3.0 (blue port)
- **SDK Required:** Vimba SDK from Allied Vision
- **Features:** ChArUco pattern analysis, real-time calibration

### Physical Connections

```
Computer USB Ports:
├── Port 1 (USB 3.0) → Allied Vision Camera
├── Port 2 → Phidgets Force Gauge
├── Port 3 → DLP Projector (control)
└── Port 4 → Zaber Stage

HDMI Output:
└── HDMI → DLP Projector (image display)
```

**Important:** Use USB 3.0 port (blue) for camera to ensure adequate bandwidth.

### USB Resource Management

The system includes **USB coordinators** to prevent conflicts between DLP and Phidgets:

- `USBCoordinator.py` - Manages resource locking
- `dlp_phidget_coordinator.py` - DLP/Phidget specific coordination

These ensure the force gauge doesn't interfere with DLP operations during critical timing.

---

## Software Installation

### Python Environment

**Required Python Version:** 3.8 or higher

### Core Dependencies

```powershell
# Install core packages
pip install tkinter matplotlib numpy pandas scipy opencv-contrib-python

# Hardware interfaces
pip install zaber-motion Phidget22

# Camera (if using Allied Vision)
pip install vimba pillow
```

**Critical:** Use `opencv-contrib-python` (not `opencv-python`) for ChArUco/ArUco marker detection!

### Allied Vision Vimba X (Camera View)

**Only required if using the Camera View popup:**

1. Download **Vimba X** from https://www.alliedvision.com/en/products/software/vimba-x-sdk/
2. Run installer as Administrator (SDK, drivers, Vimba Viewer)
3. Restart if prompted
4. Confirm the Alvium streams in Vimba Viewer
5. Install Python bindings: `pip install -r calibration_modules/camera_requirements.txt`

**Verify Installation:**
```powershell
.\.conda\python.exe -c "from vmbpy import VmbSystem; print('vmbpy OK')"
.\.conda\python.exe calibration_modules\stream_smoke_test_vmbpy.py
```

Do **not** use the legacy `vimba` package.

### File Structure

```
Prince_CurrentWorkingVersion/
├── Prince_Segmented.py          # Main application - START HERE
├── support_modules/             # Core system modules
│   ├── ForceGaugeManager.py
│   ├── SensorDataWindow.py
│   ├── pycrafter9000.py
│   └── ...
├── calibration_modules/         # Allied Vision live preview (optional)
│   ├── CameraViewWindow.py      # Camera GUI (also from Prince "Camera View")
│   ├── vmb_camera_worker.py
│   ├── zoom_pan_canvas.py
│   └── stream_smoke_test_vmbpy.py
└── documentation/               # All guides and docs
```

---

## GUI Components

### Main Application (Prince_Segmented.py)

**How to Start:**
```powershell
cd "C:\path\to\Prince_Segmented_20250926"
python Prince_Segmented.py
```

**Main Window Features:**
- Print control (Start/Stop/Pause)
- Stage position controls
- DLP projector settings
- File loading (.txt print files)
- Tools menu (Camera, Sensor Window)

### Sensor Data Window

**Purpose:** Real-time monitoring and data logging during prints

**How to Open:**
- From main GUI: `Tools` → `Sensor Data & Logging`
- Or automatically opens when starting print (if enabled)

**Features:**

#### Real-Time Display
- **Position Readout:** Current stage position (mm)
- **Force Readout:** Current force measurement (N)
- **Live Plot:** Time-series graph of position and force

#### Force Gauge Controls
- **Connect/Disconnect:** Phidgets force gauge
- **Calibrate:** Set gain and offset
- **Sampling Rate:** Adjust data interval (25-100 ms)

#### Data Logging
- **Start/Stop Logging:** Manual CSV recording
- **Sampling Rate Control:** User-configurable (25 ms default)
- **Phase Detection:** Automatic detection of print phases
- **Auto-logging:** Layer-specific data capture

#### Advanced Features
- **Peak Force Logging:** Automatic adhesion metrics per layer
- **Layer Logger:** Automated logging for layer ranges
- **Plot Controls:** Clear, zoom, pan

### ForceGaugeManager (Background)

**Purpose:** High-performance force data acquisition

**Architecture:**
```
Hardware (1200 Hz @ 1ms)
    ↓
Callback: _onVoltageRatioChange()
    → Collects samples
    → Averages based on decimation factor
    ↓
Processing Thread: _data_processing_loop()
    → Applies calibration (Force = GAIN × voltage + OFFSET)
    → Pushes to output queue
    ↓
PositionLogger/SensorDataWindow
    → Reads from queue every 25ms
    → Logs to CSV / Updates GUI
```

**Dynamic Decimation:**
- Hardware samples at maximum speed (1 ms intervals)
- Software averages N samples before output
- User controls output rate (25-100 ms typical)
- Example: 25 ms rate = average 25 hardware samples
- Benefit: √25 = 5× noise reduction

**Configuration:**
- `USE_DECIMATION = True` (enabled by default)
- `user_sampling_interval_ms = 25` (default)
- Decimation factor calculated automatically

### Experimental Conditions Window

**Purpose:** Configure print parameters for metadata

**Access:** Tools menu in main GUI

**Settings:**
- Resin type
- Layer thickness
- Exposure time
- Peel speed
- Temperature
- Other experimental parameters

These are saved with print data for analysis tracking.

---

## Camera View (Allied Vision / Vimba X)

### Overview

Phase 1 provides a live Alvium preview for resin-tank alignment (pan/zoom,
exposure/gain, display filters, snapshot). Automated ChArUco focus/tilt
calibration is not included.

### Quick Start

1. Ensure Vimba X + `vmbpy` are installed (see above).
2. In `Prince_Segmented`, click **Camera View**.
3. Stream starts automatically when a physical camera is found.
4. Scroll to zoom, drag to pan, use **Fit View** / **1:1**.
5. Adjust **Exposure** / **Gain**; optional display contrast/brightness/gamma.
6. **Save Snapshot** writes the raw camera frame.

Standalone:

```powershell
.\.conda\python.exe -m calibration_modules.CameraViewWindow
.\.conda\python.exe calibration_modules\stream_smoke_test_vmbpy.py
```

### Typical starting settings

| Use case | Exposure | Gain |
|----------|----------|------|
| Bright tank / alignment | 5000–20000 µs | 0 dB |
| Dark / low light | 20000–50000 µs | 5–10 dB |

---

## Pre-Print Verification

### Essential Checklist

Before starting any print, verify these systems are functional:

#### 1. Hardware Connections

- [ ] Force gauge connected (USB)
- [ ] DLP projector connected (USB + HDMI)
- [ ] Zaber stage connected and powered
- [ ] Camera connected (if using calibration)

#### 2. Software Status

- [ ] Prince_Segmented.py launched successfully
- [ ] All support modules loaded (check console for errors)
- [ ] No import errors in status window

#### 3. Force Gauge Calibration

- [ ] Open Sensor Data Window
- [ ] Click **"Connect"** for force gauge
- [ ] Verify stable readings (not erratic)
- [ ] Click **"Calibrate"** button
- [ ] Enter GAIN and OFFSET values
- [ ] Verify readings in Newtons (not voltage)
- [ ] Test: Apply known force, verify reading

**Typical Calibration Values:**
- GAIN: ~200-500 (depends on load cell)
- OFFSET: Adjust so zero load reads ~0.0 N

#### 4. Stage Homing

- [ ] Stage responds to jog commands
- [ ] Run auto-home sequence (if available)
- [ ] Verify stage position reads correctly
- [ ] Check stage limits (software/hardware)

#### 5. DLP Functionality

- [ ] DLP showing HDMI input (not black screen)
- [ ] Test pattern projection
- [ ] Verify UV output (use test card)
- [ ] Check DLP power setting (0-255)

#### 6. Camera Calibration (if available)

- [ ] Camera window opens
- [ ] Live stream functional
- [ ] Run automated calibration workflow
- [ ] Verify `🎯 CALIBRATION OPTIMAL` achieved
- [ ] Accept calibration

#### 7. Data Logging Setup

- [ ] Choose logging directory
- [ ] Verify CSV files can be created
- [ ] Check disk space available
- [ ] Enable Peak Force Logging (if desired)

#### 8. Print File Loaded

- [ ] .txt print file selected
- [ ] Preview images generated
- [ ] Layer count verified
- [ ] Exposure times set correctly

### Quick Test Print (3 Layers)

**Purpose:** Verify all systems before long print

1. Load test print file (3-5 layers)
2. Enable Sensor Data Window
3. Enable Peak Force Logging
4. Start print
5. Monitor real-time force plot
6. Verify layer completion messages
7. Check CSV files created after print

**Success Indicators:**
- ✅ Force plot shows peel peaks
- ✅ Stage moves smoothly
- ✅ DLP projects images
- ✅ CSV files contain data
- ✅ No error messages

### System Status Messages

**Watch for these during printing:**

**Normal Operation (Stepped Mode):**
```
L48: DLP power=0 (background light off)
Stepped L48: Peeling up to 60.5999 mm
SUCCESS L48: Return movement completed
L48: DLP power restored to 255
```

**Print Completion:**
```
Print thread finished.
PeakForceLogger shut down.
Plot queue cleared.
DLP reset to safe state (video mode, power=0)
```

**After Stop Button:**
```
DLP reset to safe state (video mode, power=0)
```

### Data Flow Verification

Verify this sequence occurs during printing:

```
1. Hardware samples at 1200 Hz (1 ms)
    ↓
2. ForceGaugeManager averages 25 samples → outputs at 25 ms rate
    ↓
3. PositionLogger reads queue → writes CSV
    ↓
4. SensorDataWindow reads queue → updates plot
    ↓
5. PeakForceLogger buffers data during layer
    ↓
6. Layer completes → adhesion metrics calculated → saved to layer CSV
```

---

## Troubleshooting

### Force Gauge Issues

#### Problem: "No force gauge found"

**Solutions:**
1. Check USB connection
2. Verify Phidget22 library installed: `pip install Phidget22`
3. Try different USB port
4. Check Windows Device Manager for Phidget device
5. Restart application

#### Problem: Force readings erratic/noisy

**Solutions:**
1. Verify decimation enabled: `USE_DECIMATION = True`
2. Increase sampling interval (50 ms instead of 25 ms)
3. Check for electrical interference
4. Verify load cell connections tight
5. Re-calibrate force gauge

#### Problem: Force gauge disconnects during print

**Solutions:**
1. Check USB cable quality
2. Disable USB power management in Windows
3. Verify USB coordinator enabled
4. Use dedicated USB controller (not shared with DLP)

### DLP Issues

#### Problem: DLP stuck in pattern mode (black screen after print)

**Solutions:**
1. Check for "DLP reset to safe state" message after print
2. Verify `cleanup_dlp_safe_state()` is called
3. Manually reset: Stop print, click DLP reset button
4. Power cycle DLP if necessary (should rarely be needed)

#### Problem: Background light visible between exposures

**Solutions:**
1. Verify running in stepped mode (not segmented)
2. Check for "DLP power=0" messages after exposure
3. Verify power restoration: "DLP power restored to X"
4. Update to latest version with power=0 fix

#### Problem: DLP not projecting images

**Solutions:**
1. Verify HDMI connection
2. Check DLP mode (should be video mode for printing)
3. Verify images generated from print file
4. Check DLP power setting (should be 0-255, not 0 always)
5. Test with DLP viewer application

### Camera Issues

#### Problem: "No cameras found"

**Solutions:**
1. Verify Vimba SDK installed (not just pip package)
2. Check USB 3.0 connection (use blue port)
3. Test with Vimba Viewer application
4. Restart computer after SDK installation
5. Check Device Manager for camera device

#### Problem: ChArUco markers not detected

**Solutions:**
1. Increase exposure time (try 15000 µs)
2. Increase gain (try 10 dB)
3. Check DLP projecting pattern (power = 10-20)
4. Verify opencv-contrib-python installed (not opencv-python)
5. Clean camera lens
6. Adjust focus manually

#### Problem: Camera streaming slow/choppy

**Solutions:**
1. Use USB 3.0 port (blue port)
2. Reduce exposure time (try 5000 µs)
3. Close other applications
4. Don't use USB hub - connect directly
5. Check camera bandwidth in Vimba Viewer

### GUI Issues

#### Problem: GUI freezes when clicking "Clear Plot"

**Solutions:**
1. Verify PeakForceLogger shutdown message appears after print
2. Check `_cleanup_print_resources()` is called
3. Update to latest version with thread cleanup fixes
4. Wait for print to fully complete before clearing

#### Problem: Sensor window won't open

**Solutions:**
1. Check console for error messages
2. Verify support_modules folder exists
3. Check all imports successful
4. Try restarting main application
5. Verify matplotlib installed: `pip install matplotlib`

#### Problem: Can't start new print after previous print

**Solutions:**
1. Verify "Print thread finished" message appears
2. Check DLP reset message appears
3. Wait 2-3 seconds after previous print
4. Check for stage stall prevention (should auto-clear)
5. Restart application if issue persists

### Stage Issues

#### Problem: Stage stalls during print

**Solutions:**
1. Verify stage acceleration limits appropriate
2. Check for mechanical binding
3. Reduce peel speed in print parameters
4. Verify stage not hitting software limits
5. Check for USB communication errors

#### Problem: Stage position reads incorrectly

**Solutions:**
1. Re-home stage
2. Verify units set to millimeters
3. Check Zaber stage settings (microsteps, etc.)
4. Power cycle stage
5. Verify USB communication stable

### Data Logging Issues

#### Problem: CSV files not created

**Solutions:**
1. Check logging directory has write permissions
2. Verify disk space available
3. Check for invalid characters in filename
4. Verify PositionLogger initialized correctly
5. Check console for file write errors

#### Problem: CSV files missing force data

**Solutions:**
1. Verify force gauge connected before logging starts
2. Check force gauge calibrated
3. Verify output_force_queue has data
4. Check sampling interval not too fast
5. Review PositionLogger queue reading logic

#### Problem: Adhesion metrics not calculated

**Solutions:**
1. Verify PeakForceLogger enabled
2. Check layer monitoring started
3. Verify adhesion_metrics_calculator imported
4. Check for errors in console
5. Verify sufficient data points collected during layer

---

## Quick Reference Summary

### Essential Pre-Print Steps

1. **Connect Hardware** → Force gauge, DLP, Stage, Camera
2. **Launch Software** → `python Prince_Segmented.py`
3. **Calibrate Force Gauge** → Open Sensor Window → Connect → Calibrate
4. **Calibrate Camera** → Camera View → Start Calibration → Follow guidance
5. **Home Stage** → Run auto-home or manual home
6. **Test DLP** → Project test pattern, verify UV output
7. **Load Print File** → Select .txt file, verify layers
8. **Start Print** → Monitor sensor window, verify data logging

### Critical Success Indicators

✅ Force gauge reading stable values  
✅ Camera calibration shows `🎯 CALIBRATION OPTIMAL`  
✅ Stage responds to commands  
✅ DLP projects clear images  
✅ CSV files created with data  
✅ Real-time plot shows force peaks during peel  
✅ Status messages show normal operation sequence  
✅ No error messages in console

### Emergency Procedures

**If Print Fails:**
1. Click **Stop** button immediately
2. Verify "DLP reset to safe state" message
3. Check stage position (don't crash into limits)
4. Review error messages in console
5. Check CSV logs for data before failure

**If GUI Hangs:**
1. Wait 10 seconds (may be processing)
2. Check console for thread errors
3. Force quit if necessary (Ctrl+C in console)
4. Restart application
5. Check logs for cause

**If Hardware Disconnects:**
1. Stop print immediately
2. Check physical connections
3. Check Device Manager for hardware
4. Restart application
5. Re-connect and re-calibrate before resuming

---

## Additional Resources

### Documentation Files

- **Main README:** Project overview and quick start
- **DEPLOYMENT_GUIDE:** Detailed deployment instructions
- **TESTING_GUIDE:** Test procedures and validation
- **Camera Documentation:** calibration_modules/README.md
- **Troubleshooting:** TroubleshootingIdeas.md

### Support Modules Documentation

See inline documentation in:
- `ForceGaugeManager.py` - Force gauge architecture
- `SensorDataWindow.py` - GUI components
- `PositionLogger.py` - Data logging
- `PeakForceLogger.py` - Adhesion metrics
- `pycrafter9000.py` - DLP control

### Contact Information

**Professor Cheng Sun**  
Email: c-sun@northwestern.edu

**Evan Jones**  
Email: evanjones2026@u.northwestern.edu

---

**Last Updated:** December 18, 2025  
**Software Version:** Prince Segmented 3D Printer Control Software  
**Guide Version:** 1.0 (Consolidated from multiple sources)
