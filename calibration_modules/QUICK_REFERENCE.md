# Camera Preview — Quick Reference (Phase 1)

## From Prince

1. Launch `Prince_Segmented.py`
2. Click **Camera View** (next to Reconnect DLP)
3. Scroll to zoom (cursor-anchored), drag to pan, double-click to Fit
4. Hardware: Exposure (µs), Gain (dB) — debounced
5. Display-only: Contrast, Brightness, Gamma, crosshair
6. **Save Snapshot** → raw PNG/TIFF/JPEG

## Standalone

```bash
.\.conda\python.exe -m calibration_modules.CameraViewWindow
.\.conda\python.exe calibration_modules\zoom_pan_canvas.py
.\.conda\python.exe calibration_modules\stream_smoke_test_vmbpy.py
.\.conda\python.exe calibration_modules\vmb_worker_harness.py
```

## Code entry points

```python
from calibration_modules import CameraViewWindow, VmbCameraWorker, ZoomPanCanvas

# Popup (parent = Tk / Toplevel owner)
win = CameraViewWindow(parent=root)
```

## Layout of package

```
calibration_modules/
├── CameraViewWindow.py          # Tk popup
├── vmb_camera_worker.py         # Threaded vmbpy worker
├── zoom_pan_canvas.py           # Pan/zoom viewport
├── stream_smoke_test_vmbpy.py   # CLI smoke test
├── vmb_worker_harness.py        # CLI worker harness
├── hardware_connection_test_vmbpy.py
├── camera_requirements.txt      # vmbpy + opencv + Pillow
└── README.md
```

## SDK

- System: **Vimba X** (not legacy Vimba)
- Python: **`vmbpy`** (not `vimba`)
