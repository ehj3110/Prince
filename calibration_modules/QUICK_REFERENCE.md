# Camera Quick Reference

Quick guide for using the Allied Vision camera system.

## Installation

```powershell
# 1. Install Vimba SDK from Allied Vision website
# 2. Install Python packages
cd calibration_modules
pip install -r camera_requirements.txt

# 3. Test installation
python test_camera.py --discovery
```

## Opening Camera Window

### From Python
```python
from calibration_modules import CameraViewWindow

# Standalone
window = CameraViewWindow()
window.run()

# From main GUI
window = CameraViewWindow(parent=main_window)
```

### From Main Application
```
Menu: Tools → Camera View
Or: Ctrl+K (if keyboard shortcut added)
```

## Basic Operations

### Connect to Camera
1. Click **"Connect Camera"** button
2. Wait for "Camera connected" status
3. Click **"Start Streaming"** to see live video

### Adjust Exposure
1. Enter exposure value in microseconds (e.g., 10000 = 10ms)
2. Click **"Set Exposure"**
3. Recommended range: 5000-20000 µs for alignment

### Adjust Gain
1. Enter gain value in dB (e.g., 0, 5, 10)
2. Click **"Set Gain"**
3. Recommended: Start at 0 dB, increase if image too dark

### Capture Snapshot
1. With camera streaming, click **"Capture Snapshot"**
2. Choose save location and filename
3. Image saved as PNG

## Recommended Settings

### For Alignment Checking
- **Exposure:** 10000 µs (10 ms)
- **Gain:** 0-5 dB
- **Use:** Check resin tank position

### For Focus Detection
- **Exposure:** 1000-5000 µs (1-5 ms)
- **Gain:** 0 dB
- **Use:** Calculate focus score (when implemented)

### For Surface Analysis
- **Exposure:** 20000-50000 µs (20-50 ms)
- **Gain:** 5-15 dB
- **Use:** Detect tilt/tip (when implemented)

## Troubleshooting

### Camera Not Found
- Check USB connection
- Verify Vimba SDK installed
- Try different USB port (use USB 3.0)
- Restart computer

### Poor Image Quality
- Adjust exposure (increase if too dark)
- Adjust gain (increase if too dark)
- Check lighting conditions
- Clean camera lens

### Slow Frame Rate
- Reduce exposure time
- Use USB 3.0 port
- Close other applications
- Check camera bandwidth

### Window Won't Open
- Check if Vimba SDK installed
- Verify imports work
- Check console for errors
- Try test script first

## File Locations

```
calibration_modules/
├── AlliedVisionCameraManager.py  - Hardware interface
├── CameraViewWindow.py           - GUI window
├── test_camera.py                - Test suite
├── README.md                     - Full documentation
├── INTEGRATION_GUIDE.md          - GUI integration
└── IMPLEMENTATION_SUMMARY.md     - Development summary
```

## Testing Commands

```powershell
# Test camera discovery
python test_camera.py --discovery

# Test connection
python test_camera.py --connection

# Test frame capture
python test_camera.py --capture

# Test window (interactive)
python test_camera.py --window

# Run all tests
python test_camera.py
```

## Python API

### Camera Manager
```python
from calibration_modules import AlliedVisionCameraManager

camera = AlliedVisionCameraManager()
camera.connect()
camera.set_exposure(10000)
camera.start_streaming(callback_function)
frame = camera.capture_single_frame()
camera.stop_streaming()
camera.disconnect()
```

### Camera Window
```python
from calibration_modules import CameraViewWindow

# Standalone window
window = CameraViewWindow()
window.run()

# Child window
window = CameraViewWindow(parent=root)
```

## Keyboard Shortcuts (If Implemented)

- **Ctrl+K:** Open camera window
- **ESC:** Close camera window (if implemented)

## Status Indicators

- **"Camera not connected"** - Camera disconnected
- **"Camera connected"** - Camera ready
- **"Streaming active"** - Live video displaying
- **"Streaming stopped"** - Video paused

## Button Functions

| Button | Function |
|--------|----------|
| Connect Camera | Connect/disconnect camera |
| Start Streaming | Start/stop live video |
| Set Exposure | Apply exposure setting |
| Set Gain | Apply gain setting |
| Capture Snapshot | Save current frame |
| Calculate Focus | Run focus detection (placeholder) |
| Calculate Tilt | Run tilt detection (placeholder) |

## Tips

✅ **Do:**
- Use USB 3.0 for best performance
- Start with default settings (exposure=10000, gain=0)
- Close window when not in use to free camera
- Save snapshots for documentation

❌ **Don't:**
- Don't change settings while streaming (stop first)
- Don't use camera with other software simultaneously
- Don't disconnect camera without stopping stream first

## Common Issues

### "Vimba SDK not available"
**Fix:** Install Vimba SDK from Allied Vision website

### "No cameras found"
**Fix:** Check USB connection, verify camera power

### "Frame capture failed"
**Fix:** Check exposure time, verify camera connected

### "Streaming lag"
**Fix:** Reduce exposure, use USB 3.0, close other apps

## Getting Help

1. Check **README.md** for detailed documentation
2. Run test suite: `python test_camera.py`
3. Review **INTEGRATION_GUIDE.md** for GUI integration
4. Check **IMPLEMENTATION_SUMMARY.md** for development notes

---

**Last Updated:** November 28, 2025  
**Quick Help:** Run `python test_camera.py` to verify setup
