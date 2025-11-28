# Calibration Modules

Camera-based calibration and alignment system for resin tank focus and tilt detection.

## Overview

This module provides real-time camera viewing and calibration capabilities using an Allied Vision USB camera with **ChArUco (Checkerboard + ArUco) pattern analysis**. The system allows you to:

- **View live camera feed** for alignment verification
- **Adjust exposure and gain** to optimize image quality
- **Capture snapshots** for documentation
- **Calculate focus quality** using Laplacian variance (MTF proxy)
- **Detect tank tilt/tip** using ChArUco marker pose estimation
- **Generate ChArUco calibration patterns** for projection
- **Analyze both metrics simultaneously** from single image (double duty)

## Components

### AlliedVisionCameraManager

Hardware interface for Allied Vision USB cameras using Vimba SDK with integrated ChArUco calibration.

**Features:**
- Automatic camera discovery and connection
- Continuous frame streaming with threading
- Single frame capture
- Exposure and gain control
- ChArUco pattern generation for projection
- Focus score calculation (Laplacian variance on ROI)
- Tilt detection (marker pose estimation)
- Double-duty frame analysis (focus + tilt simultaneously)

**Example Usage:**
```python
from calibration_modules import AlliedVisionCameraManager

# Create manager
camera = AlliedVisionCameraManager()

# Connect to camera
if camera.connect():
    # Set exposure
    camera.set_exposure(15000)  # 15ms
    
    # Start streaming
    camera.start_streaming(frame_callback=my_callback)
    
    # Later...
    camera.stop_streaming()
    camera.disconnect()
```

### CameraViewWindow

Real-time camera viewing window with ChArUco calibration controls.

**Features:**
- Live video display with automatic resizing
- Camera connection/disconnection controls
- Exposure and gain adjustment
- ChArUco pattern generation dialog
- Snapshot capture with save dialog
- Focus calculation button (Laplacian variance)
- Tilt calculation button (marker pose estimation)
- Combined analysis button (both metrics)
- Real-time calibration info display
- Status bar with detailed feedback

### ChArucoCalibrator

ChArUco-based focus and tilt detection engine.

**Features:**
- ChArUco pattern generation (customizable grid)
- Focus detection using Laplacian variance (MTF proxy)
- Tilt detection using marker pose estimation
- ROI-based analysis (inner 50% for vignetting)
- Support for camera intrinsics (absolute angles)
- Relative measurements without intrinsics
- Detection overlay visualization

**Example Usage:**
```python
from calibration_modules import CameraViewWindow

# Create window (standalone)
window = CameraViewWindow()
window.run()

# Or create as child of main application
window = CameraViewWindow(parent=main_window)
```

## Installation

### Required Dependencies

```powershell
# Allied Vision Vimba SDK (required for camera interface)
pip install vimba

# Image processing (IMPORTANT: Use opencv-contrib-python for ArUco)
pip install opencv-contrib-python pillow numpy
```

**Note:** Must use `opencv-contrib-python` (not `opencv-python`) for ChArUco/ArUco marker detection.

### Allied Vision Vimba SDK Setup

1. **Download Vimba SDK** from Allied Vision website:
   - https://www.alliedvision.com/en/products/vimba-sdk/

2. **Install Vimba SDK** following Allied Vision instructions

3. **Install Python bindings:**
   ```powershell
   pip install vimba
   ```

4. **Verify installation:**
   ```python
   python -c "from vimba import Vimba; print('Vimba SDK installed')"
   ```

## Quick Start

### Testing Camera Connection

```python
from calibration_modules import list_available_cameras

# List all connected cameras
cameras = list_available_cameras()
print(f"Found cameras: {cameras}")
```

### Opening Camera Window

From the main Prince GUI:
1. Click **"Tools"** → **"Camera View"** (or similar menu)
2. Camera will automatically connect if available
3. Click **"Start Streaming"** to see live video
4. Adjust exposure/gain as needed for your lighting

### Capturing Snapshots

1. With camera streaming, click **"Capture Snapshot"**
2. Choose save location and filename
3. Image will be saved as PNG

## Calibration Features (ChArUco Implementation)

### ChArUco Pattern Generation

**Status:** ✅ Fully Implemented

**How to use:**
1. Click **"Generate ChArUco Pattern"** in camera window
2. Enter projector resolution (e.g., 1920×1080)
3. Save pattern as PNG
4. Project pattern onto resin tank surface

**Pattern Details:**
- 8×6 checkerboard grid
- Unique ArUco markers for identification
- Works with limited FOV (inner 50% due to vignetting)
- Single pattern for both focus AND tilt measurement

### Focus Detection

**Status:** ✅ Fully Implemented

**Method:** Laplacian Variance (MTF Proxy)
- High-contrast ChArUco edges ideal for sharpness detection
- Analyzes only center 50% ROI (avoids vignetting)
- Higher score = sharper image = better focus

**How to use:**
1. Project ChArUco pattern
2. Capture image with camera
3. Click **"Calculate Focus"** to get score
4. Adjust Z-position until score is maximized

**Interpretation:**
- **>1000:** Excellent focus
- **500-1000:** Good focus
- **100-500:** Fair focus
- **<100:** Poor focus - adjust Z-position

### Tilt/Tip Detection

**Status:** ✅ Fully Implemented

**Method:** ChArUco Marker Pose Estimation
- Detects unique marker IDs in center region
- Sub-pixel corner detection for accuracy
- Estimates 3D pose of surface
- Calculates tilt angles from surface normal

**How to use:**
1. Project ChArUco pattern
2. Capture image with camera
3. Click **"Calculate Tilt"** to get X/Y angles
4. Adjust leveling screws until angles near 0°

**Interpretation:**
- **<1°:** Excellent alignment
- **1-3°:** Good alignment
- **3-5°:** Fair alignment
- **>5°:** Poor alignment - adjust leveling

**Note:** Requires camera intrinsics for absolute angles. Without intrinsics, provides relative measurements.

### Double-Duty Analysis

**Status:** ✅ Fully Implemented

**Single Pattern → Both Metrics**

Click **"Analyze Frame (Both)"** to get:
- Focus score (Laplacian variance)
- Tilt X angle (pitch)
- Tilt Y angle (roll)
- Number of markers detected

All from single image capture!

## Integration with Main GUI

To add camera window to Prince_Segmented.py main application:

```python
# In Prince_Segmented.py

from calibration_modules import CameraViewWindow

class MainApplication:
    def __init__(self):
        # ... existing code ...
        
        # Add camera window reference
        self.camera_window = None
        
        # Add menu item or button
        self.create_camera_menu()
    
    def create_camera_menu(self):
        """Add camera menu to toolbar"""
        camera_menu = tk.Menu(self.menubar, tearoff=0)
        camera_menu.add_command(
            label="Open Camera View",
            command=self.open_camera_window
        )
        self.menubar.add_cascade(label="Camera", menu=camera_menu)
    
    def open_camera_window(self):
        """Open camera viewing window"""
        if self.camera_window is None or not self.camera_window.window.winfo_exists():
            self.camera_window = CameraViewWindow(parent=self.root)
        else:
            # Bring existing window to front
            self.camera_window.window.lift()
```

## Troubleshooting

### Camera Not Found

**Problem:** `list_available_cameras()` returns empty list

**Solutions:**
1. **Check USB connection:** Ensure camera is plugged in
2. **Install Vimba SDK:** Camera requires Vimba drivers
3. **Check camera power:** Some cameras need external power
4. **Verify camera compatibility:** Must be Allied Vision camera

### Streaming Issues

**Problem:** Camera connects but streaming doesn't work

**Solutions:**
1. **Check frame rate:** Some cameras have maximum frame rate
2. **Reduce resolution:** Try lower resolution if available
3. **Check USB bandwidth:** Use USB 3.0 port for best performance
4. **Check pixel format:** Ensure compatible pixel format selected

### Import Errors

**Problem:** `ImportError: No module named 'vimba'`

**Solution:**
```powershell
pip install vimba
```

**Problem:** Vimba installs but camera still not accessible

**Solution:** Install Vimba SDK from Allied Vision (not just Python package)

### Performance Issues

**Problem:** Slow frame rate or laggy display

**Solutions:**
1. **Reduce exposure time:** Lower exposure = faster frames
2. **Use smaller image size:** Resize in camera settings if possible
3. **Close other applications:** Free up CPU/USB bandwidth
4. **Check USB port:** Use USB 3.0 for best performance

## File Structure

```
calibration_modules/
├── __init__.py                      # Package initialization
├── AlliedVisionCameraManager.py     # Camera hardware interface
├── CameraViewWindow.py              # GUI viewing window
└── README.md                        # This file
```

## Camera Configuration

### Recommended Settings

**For Alignment Checking:**
- Exposure: 5000-20000 µs (5-20 ms)
- Gain: 0-10 dB
- Resolution: Full sensor size

**For Focus Detection:**
- Exposure: 1000-5000 µs (1-5 ms) - fast to avoid motion blur
- Gain: 0 dB - minimize noise
- Resolution: Full sensor size - maximum detail

**For Tilt Detection:**
- Exposure: 10000-50000 µs (10-50 ms) - longer to see surface reflections
- Gain: 5-15 dB - enhance reflection visibility
- Resolution: Can use reduced size if needed

## Future Enhancements

### Short-term (Next Session)
- [ ] Implement basic focus score calculation (Laplacian variance)
- [ ] Add focus score history plot
- [ ] Add "optimal exposure" finder

### Medium-term
- [ ] Implement tilt detection with calibration target
- [ ] Add auto-focus routine (if camera supports)
- [ ] Save calibration data to file
- [ ] Add multi-camera support

### Long-term
- [ ] Real-time focus tracking during printing
- [ ] Automated tank leveling (with motorized platform)
- [ ] Resin surface quality assessment
- [ ] Integration with print job parameters

## Testing

### Test Camera Manager
```powershell
cd calibration_modules
python AlliedVisionCameraManager.py
```

### Test Camera Window
```powershell
cd calibration_modules
python CameraViewWindow.py
```

## Support

For issues with:
- **Allied Vision camera/SDK:** See Allied Vision documentation
- **Calibration algorithms:** Contact lab team for method recommendations
- **Integration with printer:** See main Prince_Segmented.py documentation

## References

- Allied Vision Vimba SDK: https://www.alliedvision.com/en/products/vimba-sdk/
- Focus detection methods: See lab calibration research notes
- Tilt detection methods: See lab calibration research notes

---

**Last Updated:** November 28, 2025  
**Author:** Cheng Sun Lab Team
