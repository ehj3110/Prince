# Calibration Modules — Allied Vision Live Preview (Phase 1)

Live camera preview and alignment helpers for the Allied Vision Alvium
(USB3) using **Vimba X** (`vmbpy`). Opened from `Prince_Segmented` via
**Camera View**, or run standalone.

## Requirements

1. Allied Vision **Vimba X** system install (drivers + transport layers)
2. Python package: `vmbpy` (see `camera_requirements.txt`)
3. OpenCV + Pillow (already typical for Prince)

```bash
pip install -r calibration_modules/camera_requirements.txt
```

Verify:

```bash
.\.conda\python.exe -c "from vmbpy import VmbSystem; print('vmbpy OK')"
```

## Quick tests (printer PC)

```bash
# 1A — stream smoke test (FPS + PNG + clean release)
.\.conda\python.exe calibration_modules\stream_smoke_test_vmbpy.py

# 1B — worker + exposure/gain harness
.\.conda\python.exe calibration_modules\vmb_worker_harness.py

# 1C — zoom/pan canvas offline (static PNG or synthetic)
.\.conda\python.exe calibration_modules\zoom_pan_canvas.py

# 1D — full popup without Prince
.\.conda\python.exe -m calibration_modules.CameraViewWindow
```

After any camera script exits, confirm **Vimba Viewer** can reopen the device.

## Components

| Module | Role |
|--------|------|
| `vmb_camera_worker.py` | Threaded `vmbpy` acquisition, frame queue, exposure/gain |
| `zoom_pan_canvas.py` | Pan/zoom canvas, ROI-first contrast/brightness/gamma |
| `CameraViewWindow.py` | Tk popup UI + Prince integration entry point |
| `stream_smoke_test_vmbpy.py` | CLI stream smoke test |
| `vmb_worker_harness.py` | CLI worker harness |
| `hardware_connection_test_vmbpy.py` | Single-frame connection check |

## Prince integration

In `Prince_Segmented.py`, click **Camera View** (second control row). The window
is single-instance (second click lifts it). Closing Prince stops the worker and
releases the camera.

## Notes

- Legacy `vimba` package and unvalidated ChArUco calibration code were removed.
- Snapshot saves the **raw** camera frame (display filters are view-only).
- Spec / design notes: `documentation/CAMERA_VIEWER_POPUP_SPEC.md`
