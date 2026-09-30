# Camera System Setup — Printer Computer (Vimba X / vmbpy)

The printer PC must have **Vimba X** installed before the Prince Camera View works.

## 1. Install Allied Vision Vimba X

1. Download Vimba X from Allied Vision:
   https://www.alliedvision.com/en/products/software/vimba-x-sdk/
2. Install SDK, drivers, and Vimba Viewer.
3. Reboot if prompted.
4. Plug in the Alvium (USB3), open **Vimba Viewer**, confirm the camera streams.

If Viewer fails, fix USB/power/drivers before debugging Python.

## 2. Install Python bindings

From the Prince repo (conda env used for Prince):

```bash
pip install -r calibration_modules/camera_requirements.txt
```

Check:

```bash
.\.conda\python.exe -c "from vmbpy import VmbSystem; print('vmbpy OK')"
```

Do **not** install the legacy `vimba` package.

## 3. Hardware smoke tests

```bash
.\.conda\python.exe calibration_modules\hardware_connection_test_vmbpy.py
.\.conda\python.exe calibration_modules\stream_smoke_test_vmbpy.py
```

Expect `SUCCESS` and a saved PNG. After exit, reopen the camera in Vimba Viewer
to confirm clean release.

## 4. Use from Prince

1. Run `Prince_Segmented.py`
2. Click **Camera View**
3. Adjust exposure/gain; use Fit / 1:1 / scroll-zoom / drag-pan
4. **Save Snapshot** writes the raw frame

Standalone (no Prince):

```bash
.\.conda\python.exe -m calibration_modules.CameraViewWindow
```

## Troubleshooting

| Symptom | Action |
|---------|--------|
| `No module named 'vmbpy'` | `pip install vmbpy` in the Prince conda env |
| No physical cameras | Check Viewer, USB3 port, cable, power |
| Camera locked after crash | Close Prince / Python; reopen Viewer; unplug/replug if needed |
| Import works, stream fails | Run `stream_smoke_test_vmbpy.py` and read console errors |

## Files transferred with Prince

- `calibration_modules/vmb_camera_worker.py`
- `calibration_modules/zoom_pan_canvas.py`
- `calibration_modules/CameraViewWindow.py`
- `calibration_modules/stream_smoke_test_vmbpy.py`
- `calibration_modules/vmb_worker_harness.py`
- `calibration_modules/hardware_connection_test_vmbpy.py`
- `calibration_modules/camera_requirements.txt`
