# Camera System Setup - Printer Computer

**Important:** The printer runs on a different computer. Follow these steps when transferring the camera system.

## Transfer Checklist

### 1. Copy Files to Printer Computer

Copy the entire `calibration_modules/` folder to the printer computer:

```
Source: Prince_Segmented_20250926/calibration_modules/
Destination: [Printer computer Prince folder]/calibration_modules/
```

**Files to transfer:**
- ✅ AlliedVisionCameraManager.py
- ✅ CameraViewWindow.py
- ✅ __init__.py
- ✅ test_camera.py
- ✅ camera_requirements.txt
- ✅ All documentation (.md files)

### 2. Install Allied Vision Vimba SDK

**CRITICAL:** Must be done on the printer computer before camera will work.

1. **Download Vimba SDK:**
   - Website: https://www.alliedvision.com/en/products/vimba-sdk/
   - Get the latest version for Windows
   - Save installer to desktop

2. **Install Vimba SDK:**
   - Run the installer as Administrator
   - Follow installation wizard
   - **Important:** Install to default location
   - Install all components (SDK, drivers, viewer)

3. **Restart Computer:**
   - Required for drivers to load properly
   - Do NOT skip this step

4. **Test with Vimba Viewer:**
   - Open "Vimba Viewer" from Start menu
   - Connect camera via USB
   - Verify camera appears in device list
   - Try capturing an image
   - If camera works in Vimba Viewer, SDK is installed correctly

### 3. Install Python Dependencies

On the printer computer, open PowerShell and run:

```powershell
cd "C:\[path to Prince folder]\calibration_modules"
pip install -r camera_requirements.txt
```

This installs:
- `vimba` - Allied Vision Python bindings
- `opencv-contrib-python` - Image processing with ArUco/ChArUco support
- `Pillow` - Image display in Tkinter

**IMPORTANT:** Must use `opencv-contrib-python` (not `opencv-python`) for ChArUco marker detection!

**Verify Installation:**
```powershell
python -c "from vimba import Vimba; print('Vimba SDK installed successfully')"
python -c "import cv2; print('OpenCV version:', cv2.__version__); print('ArUco module:', hasattr(cv2, 'aruco'))"
```

If these print success messages and `ArUco module: True`, you're ready to go!

### 4. Connect Camera Hardware

1. **Plug in Camera:**
   - Use USB 3.0 port (blue USB port)
   - Directly to computer (not through hub if possible)
   - Wait for Windows to detect device

2. **Check Device Manager:**
   - Open Device Manager (Win+X → Device Manager)
   - Look under "Imaging Devices" or "Allied Vision Cameras"
   - Camera should appear without yellow warning icon
   - If warning icon: Re-install Vimba SDK drivers

3. **Check Camera Power:**
   - Some Allied Vision cameras need external power
   - Verify power cable connected if required
   - Check camera LED (if present) is lit

### 5. Test Camera System

Run the test suite to verify everything works:

```powershell
cd "C:\[path to Prince folder]\calibration_modules"

# Test 1: Camera discovery
python test_camera.py --discovery

# Test 2: Connection test
python test_camera.py --connection

# Test 3: Frame capture
python test_camera.py --capture

# Test 4: Full test suite
python test_camera.py
```

**Expected Results:**
- ✅ Discovery test finds your camera
- ✅ Connection test connects successfully
- ✅ Capture test saves `test_camera_frame.png`
- ✅ Window test opens and shows live video

### 6. Integrate with Main GUI

Once tests pass, integrate camera into Prince_Segmented.py:

1. **Open Prince_Segmented.py** on printer computer

2. **Add Import** (at top of file):
   ```python
   from calibration_modules import CameraViewWindow
   ```

3. **Add Camera Window Reference** (in `__init__` method):
   ```python
   self.camera_window = None
   ```

4. **Add Menu Item** (follow INTEGRATION_GUIDE.md):
   ```python
   # In create_menus() or similar
   camera_menu = tk.Menu(menubar, tearoff=0)
   camera_menu.add_command(
       label="Open Camera View",
       command=self.open_camera_window
   )
   menubar.add_cascade(label="Camera", menu=camera_menu)
   ```

5. **Add Open Method:**
   ```python
   def open_camera_window(self):
       """Open camera viewing window"""
       if self.camera_window is not None:
           if self.camera_window.window.winfo_exists():
               self.camera_window.window.lift()
               return
       self.camera_window = CameraViewWindow(parent=self.root)
   ```

6. **Test Integration:**
   - Run Prince_Segmented.py
   - Click Camera menu → Open Camera View
   - Verify window opens and camera connects

## Quick Troubleshooting

### Problem: "No module named 'vimba'"
**Solution:**
```powershell
pip install vimba
```

### Problem: "No cameras found"
**Solutions:**
1. Check USB connection (use USB 3.0 port)
2. Restart computer after Vimba SDK installation
3. Verify camera works in Vimba Viewer first
4. Check Device Manager for camera device

### Problem: "Vimba SDK installed but camera not accessible"
**Solution:**
- Install **full Vimba SDK** from Allied Vision (not just pip package)
- SDK download: https://www.alliedvision.com/en/products/vimba-sdk/

### Problem: Import error when opening camera from main GUI
**Solution:**
- Verify `calibration_modules/` folder exists
- Check `__init__.py` is present in folder
- Verify import path is correct

### Problem: Camera connects but streaming is slow
**Solutions:**
1. Use USB 3.0 port (blue port, not black USB 2.0)
2. Reduce exposure time (try 5000 µs)
3. Close other applications
4. Don't use USB hub - connect directly to computer

## ChArUco Calibration Workflow

Once system is working, follow this workflow:

### 1. Generate ChArUco Pattern
1. Open camera window
2. Click **"Generate ChArUco Pattern"**
3. Enter your projector resolution (e.g., 1920×1080)
4. Save pattern as PNG
5. Project pattern onto resin tank

### 2. Adjust Camera Settings

**For ChArUco Detection:**
- **Exposure:** 5000-15000 µs (5-15 ms)
  - Too low: Markers not visible
  - Too high: Pattern washed out
- **Gain:** 0-10 dB
  - Start at 0 dB, increase if pattern too dark
- **Focus:** Adjust manually until pattern edges are sharp

### 3. Analyze Calibration

**Focus Measurement:**
- Click **"Calculate Focus"** 
- Target: Score > 500 (good), > 1000 (excellent)
- Adjust resin tank Z-position to maximize score

**Tilt Measurement:**
- Click **"Calculate Tilt"**
- Target: Both angles < 1° (excellent), < 3° (good)
- Adjust tank leveling screws to minimize angles

**Combined Analysis:**
- Click **"Analyze Frame (Both)"** for simultaneous measurement
- Single image captures both focus and tilt
- Most efficient method

### 4. Document Optimal Settings

Once calibrated, record:
- Camera exposure: _____________ µs
- Camera gain: _____________ dB
- Focus score: _____________
- Tilt X: _____________°
- Tilt Y: _____________°
- Date: _____________

## Recommended Camera Settings by Use Case

### For Initial Pattern Detection
- **Exposure:** 10000 µs (10 ms)
- **Gain:** 5 dB
- **Purpose:** See pattern clearly, detect markers

### For Focus Optimization
- **Exposure:** 5000 µs (5 ms) - faster to reduce blur
- **Gain:** 0 dB - minimize noise
- **Purpose:** Maximize focus score

### For Tilt Measurement
- **Exposure:** 10000-15000 µs (10-15 ms)
- **Gain:** 0-5 dB
- **Purpose:** Clear marker detection for pose estimation

## Post-Setup Testing

After setup is complete, test these workflows:

1. **Basic Operation:**
   - [ ] Open Prince application
   - [ ] Open Camera View from menu
   - [ ] Connect to camera
   - [ ] Start streaming
   - [ ] Adjust exposure/gain
   - [ ] Capture snapshot
   - [ ] Close window cleanly

2. **Pre-Print Workflow:**
   - [ ] Start new print job
   - [ ] Open camera view
   - [ ] Check resin tank alignment
   - [ ] Verify focus looks good
   - [ ] Close camera
   - [ ] Proceed with print

3. **Documentation:**
   - [ ] Capture snapshot of good alignment
   - [ ] Save to reference folder
   - [ ] Document optimal settings

## Reference Documents

After setup, refer to these documents:

- **README.md** - Complete documentation and features
- **QUICK_REFERENCE.md** - Quick commands and settings
- **INTEGRATION_GUIDE.md** - Detailed GUI integration
- **IMPLEMENTATION_SUMMARY.md** - System overview

## Support

If you encounter issues:

1. **Run test suite:** `python test_camera.py`
2. **Check Vimba Viewer:** Does camera work there?
3. **Verify imports:** Can you import vimba in Python?
4. **Check documentation:** See README.md and guides

## Camera Model Information

**Record your camera details here for reference:**

- Camera Model: ________________________
- Camera ID: ________________________
- USB Port Used: ________________________
- Optimal Exposure: ________________________
- Optimal Gain: ________________________
- Notes: ________________________

---

## Summary: Setup Steps on Printer Computer

1. ✅ Copy `calibration_modules/` folder
2. ✅ Download and install Vimba SDK
3. ✅ Restart computer
4. ✅ Test camera in Vimba Viewer
5. ✅ Install Python dependencies (`pip install -r camera_requirements.txt`)
6. ✅ Connect camera to USB 3.0 port
7. ✅ Run test suite (`python test_camera.py`)
8. ✅ Integrate with Prince_Segmented.py (see INTEGRATION_GUIDE.md)
9. ✅ Test camera opens from main GUI
10. ✅ Document optimal settings

**Estimated Setup Time:** 30-45 minutes (including SDK installation and restart)

---

**Last Updated:** November 28, 2025  
**Status:** Ready for deployment to printer computer
