# Automated Calibration Workflow Guide

## Overview

The automated calibration workflow provides a streamlined, user-friendly process for calibrating the resin tank focus and alignment. It's designed to be the **first step** when opening the Prince GUI each day.

## Workflow Design

### User Experience Flow

```
1. Open Prince GUI
   ↓
2. Click "Camera" menu → "Start Calibration"
   ↓
3. System automatically:
   • Connects to camera
   • Projects ChArUco pattern (DLP power = 10)
   • Optimizes camera exposure/gain
   • Begins real-time measurement
   ↓
4. User sees live guidance:
   "Move tank UP (closer to camera)"
   "Tilt tank left slightly"
   "Tip tank backward"
   ↓
5. User adjusts hardware while watching feedback
   ↓
6. When "🎯 CALIBRATION OPTIMAL" appears:
   Click "Accept Calibration"
   ↓
7. System saves calibration data
   DLP returns to normal operation
   ↓
8. Ready to print!
```

## Features

### ✅ Fully Automated Setup
- **No manual pattern generation** - System creates it automatically
- **Auto-projects pattern** - DLP set to power=10
- **Auto-optimizes camera** - Exposure and gain tuned automatically
- **Auto-starts measurement** - Real-time monitoring begins immediately

### ✅ Continuous Real-Time Guidance
- **Live measurements** - Focus and tilt updated 10 times per second
- **Human-readable instructions** - Clear, actionable guidance
- **Color-coded feedback** - ✓ (good), ⚙️ (adjust), ❌ (critical)
- **Progress indicators** - "Getting better..." when improving

### ✅ Smart Guidance System

**Focus Guidance:**
- `❌ FOCUS: Very poor` - Major adjustment needed
- `⚠️ FOCUS: Poor` - Move stage DOWN (bring surface closer to camera)
- `⚙️ FOCUS: Fair` - Move stage down slightly
- `✓ FOCUS: Good` - Acceptable
- `✓✓ FOCUS: Excellent` - Optimal

*Note: Moving stage UP = surface further away = worse focus*  
*Note: Moving stage DOWN = surface closer = better focus*

**Tilt Guidance (X-axis / Pitch):**
- `❌ TILT X: Tip tank FORWARD` - Large correction
- `⚙️ TILT X: Tip tank forward slightly` - Small correction
- `✓ TILT X: Good` - Acceptable
- `✓✓ TILT X: Excellent` - Optimal

**Tilt Guidance (Y-axis / Roll):**
- `❌ TILT Y: Tilt tank LEFT` - Large correction
- `⚙️ TILT Y: Tilt tank left slightly` - Small correction
- `✓ TILT Y: Good` - Acceptable
- `✓✓ TILT Y: Excellent` - Optimal

**Optimal State:**
- `🎯 CALIBRATION OPTIMAL` - Ready to accept!

### ✅ Automatic Camera Optimization

The system automatically finds optimal camera settings:

**Optimization Strategy:**
1. Start with mid-range exposure (10ms), low gain (0dB)
2. Scan exposure values: 5, 10, 15, 20, 30ms
3. Count ChArUco markers detected at each setting
4. If <4 markers detected, increase gain (5, 10, 15dB)
5. Select settings with maximum marker detection
6. Apply optimal settings

**Typical Results:**
- Exposure: 10000-20000 µs (10-20ms)
- Gain: 0-10 dB
- Markers: 8-12 detected (out of ~24 possible)

### ✅ Data Logging

All calibration sessions are logged to `calibration_logs/calibration_history.txt`:

```
============================================================
Calibration: 2025-11-28T10:30:15
============================================================
Focus Score: 1234.56
Tilt X: +0.12°
Tilt Y: -0.34°
Exposure: 15000 µs
Gain: 5 dB
Markers: 12
Within Tolerance: True
```

## Integration with Main GUI

### Option 1: Quick Start Button (Recommended)

Add prominent "Start Calibration" button to main GUI:

```python
# In Prince_Segmented.py main window

def __init__(self):
    # ... existing init ...
    
    # Add calibration button to toolbar
    cal_button = ttk.Button(
        toolbar,
        text="🎯 Start Calibration",
        command=self.start_calibration_workflow,
        style='Accent.TButton'
    )
    cal_button.pack(side=tk.LEFT, padx=10)

def start_calibration_workflow(self):
    """Open camera window in calibration mode"""
    # Pass DLP controller if available
    camera_window = CameraViewWindow(
        parent=self.root,
        dlp_controller=self.dlp_controller  # Your DLP controller instance
    )
    
    # Auto-connect camera
    if not camera_window.camera_manager.camera:
        camera_window.connect_camera()
    
    # Show calibration panel (already visible by default)
    messagebox.showinfo(
        "Calibration Mode",
        "Click 'Start Calibration' in the camera window.\n\n"
        "Follow the on-screen guidance to adjust tank position.\n\n"
        "Click 'Accept Calibration' when optimal."
    )
```

### Option 2: Menu Item

Add to Tools menu:

```python
tools_menu = tk.Menu(menubar, tearoff=0)
tools_menu.add_command(
    label="Tank Calibration...",
    command=self.start_calibration_workflow,
    accelerator="Ctrl+L"
)
tools_menu.add_separator()
tools_menu.add_command(label="Camera View", command=self.open_camera_window)
```

### Option 3: Startup Dialog

Prompt on application start:

```python
def __init__(self):
    # ... existing init ...
    
    # Schedule calibration prompt after UI loads
    self.root.after(500, self.prompt_calibration)

def prompt_calibration(self):
    """Prompt user to calibrate on startup"""
    response = messagebox.askyesno(
        "Daily Calibration",
        "Run tank calibration before printing?\n\n"
        "Recommended: Yes\n"
        "(Takes ~1-2 minutes)"
    )
    
    if response:
        self.start_calibration_workflow()
```

## DLP Controller Integration

The workflow expects a DLP controller object with these methods:

```python
class DLPController:
    def set_power(self, power: int):
        """Set DLP power (0-100)"""
        pass
    
    def project_image(self, image_path: str):
        """Project an image file"""
        pass
    
    def clear(self):
        """Clear projection (black screen)"""
        pass
```

**If you don't have a DLP controller yet:**

The workflow will still work, but will print warnings:
```python
WARNING: No DLP controller available
Please manually project: calibration_patterns/charuco_calibration.png
Set DLP power to 10
```

You can manually project the pattern and the rest of the workflow continues normally.

## Target Tolerances

**Default Values (configurable):**
- **Focus:** Minimum 500 (excellent >1000)
- **Tilt X/Y:** Maximum ±2° (excellent <1°)

**To Adjust:**
```python
camera_window.calibration_workflow.target_focus_min = 700  # Stricter
camera_window.calibration_workflow.target_tilt_max = 1.5  # Stricter
```

## Typical Calibration Session

### Initial State (Tank Misaligned)
```
⚠️ FOCUS: Poor - Move stage DOWN (bring surface closer)
❌ TILT X: Tip tank FORWARD (+3.5°)
⚙️ TILT Y: Tilt tank left slightly (+2.1°)
```

### After Adjusting Focus
```
✓ FOCUS: Good
❌ TILT X: Tip tank FORWARD (+3.5°)
⚙️ TILT Y: Tilt tank left slightly (+2.1°)

📈 Getting better...
```

### After Adjusting Tilt X
```
✓ FOCUS: Good
✓ TILT X: Good (+1.8°)
⚙️ TILT Y: Tilt tank left slightly (+2.1°)

📈 Getting better...
```

### Final Optimal State
```
✓✓ FOCUS: Excellent
✓✓ TILT X: Excellent (+0.3°)
✓✓ TILT Y: Excellent (-0.1°)

🎯 CALIBRATION OPTIMAL
Click 'Accept Calibration' to save
```

## Troubleshooting

### "No markers detected"

**Causes:**
- Pattern not projected
- Camera not focused enough to see markers
- Exposure too high/low

**Solutions:**
1. Verify pattern is projected
2. Manually adjust camera focus
3. Click "Stop" then "Start" to re-optimize
4. Check DLP projector is on

### "Only 2 markers detected"

**Causes:**
- Pattern partially visible
- Tank severely tilted
- Camera field of view issue

**Solutions:**
1. Adjust tank position (closer to camera)
2. Manually level tank approximately
3. Check camera angle

### "Optimization failed"

**Causes:**
- No camera connected
- Pattern file missing
- DLP not responding

**Solutions:**
1. Check camera connection
2. Manually generate pattern (will auto-create on first run)
3. Check DLP controller

### Measurements jumping around

**Causes:**
- Vibrations
- Tank not secure
- Unstable mounting

**Solutions:**
1. Wait for vibrations to settle
2. Check tank mounting screws
3. System averages 10 samples for stability

## Advanced Configuration

### Measurement Update Rate

Default: 10 Hz (10 measurements per second)

**To Change:**
```python
# In CalibrationWorkflow._calibration_loop()
time.sleep(0.1)  # Change to 0.05 for 20 Hz, or 0.2 for 5 Hz
```

### History Length (Averaging)

Default: 10 samples averaged

**To Change:**
```python
camera_window.calibration_workflow.history_length = 20  # More stable, slower response
```

### Auto-Optimization Range

**Exposure:**
- Min: 5000 µs (5ms)
- Max: 50000 µs (50ms)
- Step: 2000 µs

**Gain:**
- Min: 0 dB
- Max: 20 dB
- Step: 2 dB

**To Change:**
```python
workflow = camera_window.calibration_workflow
workflow.exposure_min = 3000
workflow.exposure_max = 30000
workflow.gain_max = 15
```

## Benefits Over Manual Calibration

| Feature | Manual Method | Automated Workflow |
|---------|---------------|-------------------|
| **Setup Time** | 5-10 min | 30 seconds |
| **Pattern Creation** | Manual | Automatic |
| **Camera Settings** | Trial and error | Auto-optimized |
| **Guidance** | User must interpret numbers | Clear instructions |
| **Real-time Feedback** | Manual re-measurement | Continuous |
| **Data Logging** | Manual notes | Automatic |
| **DLP Control** | Manual adjustment | Automatic |
| **User Experience** | Technical | User-friendly |

## Recommended Daily Workflow

### Morning Startup Procedure

1. **Turn on equipment**
   - Power on computer
   - Power on DLP projector
   - Power on Allied Vision camera
   - Connect force gauge (if using)

2. **Open Prince GUI**
   - Launch Prince_Segmented.py
   - Wait for UI to load

3. **Run Calibration** (1-2 minutes)
   - Click "Start Calibration" button
   - Follow on-screen guidance
   - Adjust tank as directed
   - Click "Accept" when optimal

4. **Begin Printing**
   - Tank is now calibrated
   - Proceed with print jobs
   - Optimal focus and alignment ensured

### When to Re-Calibrate

- **Every morning** - Thermal drift overnight
- **After tank removal** - Position changed
- **After bumping equipment** - Alignment may shift
- **If print quality degrades** - Check calibration
- **After power cycle** - Good practice

## Summary

The automated calibration workflow provides a **streamlined, user-friendly experience** for daily tank calibration:

✅ **One-click start** - No manual setup  
✅ **Auto-optimization** - Camera settings tuned automatically  
✅ **Real-time guidance** - Clear, actionable instructions  
✅ **Continuous monitoring** - Live feedback as you adjust  
✅ **Data logging** - History tracked automatically  
✅ **DLP integration** - Projection handled automatically  
✅ **User-friendly** - No technical knowledge required  

The workflow transforms calibration from a tedious technical task into a quick, guided procedure that anyone can perform successfully.

---

**Recommended Integration:** Add prominent "Start Calibration" button to main GUI toolbar for easy access.

**Time Required:** 1-2 minutes (including adjustments)

**Frequency:** Daily, before first print

**Last Updated:** November 28, 2025
