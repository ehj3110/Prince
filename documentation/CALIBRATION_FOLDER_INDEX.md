# Calibration Modules Folder Index

## Purpose

Multi-spectral vision, live inspection, and the PySide6 **System Monitoring** dashboard for the Prince platform:
1. **Allied Vision Alvium 1800 U-511m (Optical Machine Vision)**: Live camera preview for resin-tank alignment, build-plate leveling, and meniscus inspection using **Vimba X** (`vmbpy`) with an interactive Tk popup (`CameraViewWindow` + `ZoomPanCanvas`).
2. **Seek Thermal InspectionCAM (Model IQ-AAA, Infrared Thermography)**: Live radiometric thermal inspection for in-situ photopolymerization exotherm tracking and resin vat temperature monitoring (`SeekThermalViewerWindow` + `seek_thermal_canvas` + `seek_thermal_worker`).
3. **Monitoring dashboard** (`monitoring_dashboard/`): Separate PySide6 process with optical + thermal + triple Phidget force + Thorlabs PM100A expected UV power (see `documentation/MONITORING_DASHBOARD_GUIDE.md`).

## What This Folder Owns

1. Allied Vision camera connection and streaming (`vmbpy`).
2. Seek Thermal InspectionCAM connection, radiometric acquisition, and thermal colormapping (`seekcamera-python`).
3. Interactive preview GUIs with cursor-anchored zoom/pan, spot temperature probing, and reticles.
4. CLI hardware bring-up and verification harnesses.
5. Monitoring dashboard workers, Thorlabs PM100A driver, UV density calibration scripts, and print-layer state I/O.

## Core Functional Paths

### Path A: Allied Vision (Optical Alignment)
1. Install Vimba X + `vmbpy` on the printer PC.
2. Run `stream_smoke_test_vmbpy.py` (or click **Camera View** in Prince).
3. Adjust exposure/gain; pan/zoom for alignment; save raw snapshots.

### Path B: Seek Thermal InspectionCAM (Thermal Exotherm)
1. Install `seekcamera-python` in the project environment (`pip install seekcamera-python`).
2. Run `SeekThermalViewerWindow.py` (standalone or via pop-up).
3. Inspect live exotherm heating, spot temperatures, hot/cold spots, and export radiometric CSV/NPY grids.

### Path C: System Monitoring Dashboard
1. From Prince click **Monitoring Suite**, or run `.\.conda\python.exe -m calibration_modules.monitoring_dashboard`.
2. Confirm cameras, triple force (`MODE=TRIPLE` cal file), and PM100A at 385 nm.
3. Optional: force **Calibrate** / **Tare**; UV density via `power_density_calibration.py`.

## Major Modules

### Allied Vision Optical Subsystem
- **`vmb_camera_worker.py`**: Dedicated thread for `vmbpy` acquisition, auto-reconnection recovery loop, rolling FPS telemetry, and synthetic mock generator.
- **`zoom_pan_canvas.py`**: Tk canvas with cursor-anchored zoom, pan, Fit / 1:1, reticle, and ROI-first contrast/brightness/gamma.
- **`CameraViewWindow.py`**: Optical preview popup; launched from `Prince_Segmented` via **Camera View** or run standalone.
- **`stream_smoke_test_vmbpy.py`**: CLI stream smoke test (FPS, PNG, clean release).
- **`vmb_worker_harness.py`**: CLI harness for worker + mid-stream exposure/gain + unlock proof.
- **`hardware_connection_test_vmbpy.py`**: Minimal single-frame connection test.

### Seek Thermal InspectionCAM Subsystem
- **`seek_thermal_worker.py`**: Dedicated 9 Hz acquisition thread wrapping `seekcamera-python` for `SeekCameraFrameFormat.THERMOGRAPHY_FLOAT` (°C) acquisition with automatic fallback to synthetic exotherm simulation.
- **`seek_thermal_canvas.py`**: Interactive radiometric canvas with cursor-anchored zoom/pan, dynamic hover spot probe (°C), pinned spot probe reticle, min/max thermal trackers, false-color palettes, and vertical temperature scale bar.
- **`SeekThermalViewerWindow.py`**: Standalone / pop-up viewer with thermography readouts ($T_{\max}, T_{\min}, T_{\text{mean}}, T_{\text{probe}}$), colormap selection (Inferno, Turbo, Viridis, etc.), Auto/Fixed scale bounds, and CSV/NPY radiometric data export.

### Monitoring Dashboard & Power / Force Calibration
- **`monitoring_dashboard/`**: PySide6 UI (`window.py`), acquisition threads (`workers.py`), theme.
- **`thorlabs_pm100a.py`**: NI-VISA SCPI for PM100A; 75% software up-range.
- **`power_density_calibration.py`**: Project `Power_255` at LED 10/100; save densities to `data/uv_power_calibration.json`.
- **`power_expected_stress_test.py`** / **`power_range_sweep.py`**: Validation helpers.
- **`print_monitor_state.py`**: Layer/power state file shared with Prince during a print.
- **`monitoring_requirements.txt`**: `pyvisa`, `pyvisa-py`.

### Package Exports (`__init__.py`)
Exports `CameraViewWindow`, `VmbCameraWorker`, `ZoomPanCanvas`, `VMBPY_AVAILABLE`, `SeekThermalViewerWindow`, `SeekThermalWorker`, `SeekThermalCanvas`, `MonitoringSuiteWindow`.

## Test Suites (in `tests/`)
- `tests/test_camera_viewer_robustness.py`: 7-test suite verifying zoom/pan math, gamma LUT, mock streaming, physical Alvium acquisition, and UI lifecycle.
- `tests/test_seek_thermal_viewer.py`: 5-test suite verifying radiometric generation, worker streaming, colormap transforms, coordinate mapping, and CSV/NPY export.

## Related Documentation
- `calibration_modules/README.md`
- `documentation/MONITORING_DASHBOARD_GUIDE.md`
- `documentation/CAMERA_VIEWER_POPUP_SPEC.md`
- `documentation/technical/SEEK_THERMAL_INSPECTION_CAMERA_INTEGRATION.md`
- `documentation/TRIPLE_FORCE_GAUGE_GUIDE.md`
- `DOCUMENTATION_INDEX.md`
