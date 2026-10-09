# Calibration Modules — Multi-Spectral Vision, Alignment & Monitoring

Live camera preview, alignment, thermal inspection, and the printer **System Monitoring** dashboard:
1. **Allied Vision Alvium 1800 U-511m (Optical)**: High-resolution ($2464 \times 2064$) monochrome preview using **Vimba X** (`vmbpy`).
2. **Seek Thermal InspectionCAM (Model IQ-AAA, Infrared)**: Macro radiometric thermal imaging ($320 \times 240$, 4 cm macro focus) using `seekcamera-python` for in-situ photopolymerization exotherm tracking.
3. **Monitoring dashboard**: PySide6 process with optical + thermal + triple Phidget force + Thorlabs PM100A (expected UV power). Operator guide: [`documentation/MONITORING_DASHBOARD_GUIDE.md`](../documentation/MONITORING_DASHBOARD_GUIDE.md).

---

## Requirements

### 1. Optical Camera (Allied Vision)
- Allied Vision **Vimba X** system install (drivers + transport layers)
- Python package: `vmbpy` (already installed in `.conda`)
- Test installation:
  ```powershell
  .\.conda\python.exe -c "from vmbpy import VmbSystem; print('vmbpy OK')"
  ```

### 2. Infrared Thermal Camera (Seek Thermal InspectionCAM)
- Hardware: Seek Thermal InspectionCAM (Model IQ-AAA, 320x240, 9 Hz, 4 cm macro lens)
- Python package: `seekcamera-python` (already installed in `.conda`)
- Test installation:
  ```powershell
  .\.conda\python.exe -c "import seekcamera; print('seekcamera OK')"
  ```

### 3. Monitoring dashboard extras
- PySide6, Phidget22, pyvisa / NI-VISA (see `monitoring_requirements.txt`)
- Thorlabs PM100A switched to USBTMC via Thorlabs Driver Switcher
- Optional: newest `data/force_gauge_calibration_*.txt` with `MODE=TRIPLE` for summed force on channels 0–2

---

## Quick Start & Testing

### 1. Launch System Monitoring Dashboard
```powershell
.\.conda\python.exe -m calibration_modules.monitoring_dashboard
```
- Or click **Monitoring Suite** in `Prince_Segmented.py` (uses `.conda\python.exe`, `close_fds=True`).
- Keep **Sensor Panel** closed while the dashboard owns the force gauge.
- Force defaults to **40 Hz**; **Calibrate** / **Tare** are on the force card when triple-calibrated.

### 2. Launch Seek Thermal InspectionCAM Viewer (Standalone)
```powershell
.\.conda\python.exe -m calibration_modules.SeekThermalViewerWindow
```
- If physical camera is connected: streams live radiometric thermal data.
- If physical camera is not connected: automatically runs synthetic resin photopolymerization exotherm simulation.
- Supports cursor-hover spot temperature probing (°C), pinned spot markers, min/max hot/cold tracking, colormaps (Inferno, Turbo, Viridis, etc.), and CSV/NPY raw temperature export.

### 3. Launch Allied Vision Optical Viewer (Standalone)
```powershell
.\.conda\python.exe -m calibration_modules.CameraViewWindow
```
- Connects to the connected Alvium 1800 U-511m.
- Full cursor-anchored pan/zoom, crosshair overlay, hardware exposure/gain sliders, display contrast/brightness/gamma, and snapshot capture.

### 4. UV power density calibration
```powershell
.\.conda\python.exe -u -m calibration_modules.power_density_calibration
.\.conda\python.exe -u -m calibration_modules.power_expected_stress_test
```
- Close the TI DLPC900REF-GUI first. Saves `data/uv_power_calibration.json` (LED 10 and 100 at 385 nm).

### 5. Run Automated Test Suites
```powershell
# Optical Camera Robustness Suite (7 tests)
.\.conda\python.exe tests/test_camera_viewer_robustness.py

# Seek Thermal Viewer Suite (5 tests)
.\.conda\python.exe tests/test_seek_thermal_viewer.py
```

---

## File Architecture

| File | Subsystem | Description |
|------|-----------|-------------|
| `monitoring_dashboard/` | Monitor | PySide6 dashboard (window, workers, theme) |
| `thorlabs_pm100a.py` | Power | NI-VISA SCPI for PM100A |
| `power_density_calibration.py` | Power | Project square at LED 10/100; save densities |
| `power_expected_stress_test.py` | Power | Stent-layer expected vs measured check |
| `power_range_sweep.py` | Power | Explicit meter-range comparison |
| `print_monitor_state.py` | Monitor | Layer/power JSON for live print follow |
| `CameraViewWindow.py` | Optical | Tkinter pop-up viewer for Allied Vision Alvium |
| `vmb_camera_worker.py` | Optical | Threaded `vmbpy` acquisition with auto-reconnection and telemetry |
| `zoom_pan_canvas.py` | Optical | Interactive Canvas with cursor-anchored zoom/pan & display filters |
| `SeekThermalViewerWindow.py` | Thermal | Standalone / Pop-up viewer for Seek Thermal InspectionCAM |
| `seek_thermal_worker.py` | Thermal | 9 Hz radiometric acquisition thread with exotherm simulation |
| `seek_thermal_canvas.py` | Thermal | Radiometric Canvas with spot probing, min/max tracking, and colorbar |
| `stream_smoke_test_vmbpy.py` | CLI | Rapid optical stream smoke test |
| `vmb_worker_harness.py` | CLI | Optical worker CLI harness testing parameter changes |
| `hardware_connection_test_vmbpy.py` | CLI | Minimal single-frame connection check |

---

## Prince Integration

- **Monitoring Suite:** In `Prince_Segmented.py`, **Monitoring Suite** launches the PySide6 dashboard in its own process.
- **Optical Camera:** **Camera View** still opens the Tk Alvium popup when used separately.
- **Seek Thermal Camera:** Can be launched standalone or imported via:
  ```python
  from calibration_modules import SeekThermalViewerWindow
  viewer = SeekThermalViewerWindow(parent=my_main_window)
  ```
