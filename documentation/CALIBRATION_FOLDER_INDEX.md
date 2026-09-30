# Calibration Modules Folder Index

## Purpose

Live Allied Vision camera preview for resin-tank alignment in Prince.
Phase 1 uses **Vimba X** (`vmbpy`) with a Tk popup (pan/zoom, exposure/gain,
display filters, snapshot). Focus/tilt / ChArUco workflows were removed
(never validated).

## What This Folder Owns

1. Allied Vision camera connection and streaming (`vmbpy`).
2. Interactive preview GUI (`CameraViewWindow` + `ZoomPanCanvas`).
3. CLI hardware bring-up scripts (smoke test, worker harness).

## Core Functional Path

1. Install Vimba X + `vmbpy` on the printer PC.
2. Run `stream_smoke_test_vmbpy.py` (or open **Camera View** in Prince).
3. Adjust exposure/gain; pan/zoom for alignment.
4. Optionally save a raw snapshot.

## Major Modules

### `vmb_camera_worker.py`

Threaded acquisition: `get_frame_generator`, drop-oldest queue, pending
exposure/gain applied on the camera thread, joinable stop.

### `zoom_pan_canvas.py`

Tk canvas with cursor-anchored zoom, pan, Fit / 1:1, crosshair, and
ROI-first contrast/brightness/gamma.

### `CameraViewWindow.py`

Operator popup; also launched from `Prince_Segmented` via **Camera View**.

### `stream_smoke_test_vmbpy.py`

CLI stream smoke test (FPS, PNG, clean release).

### `vmb_worker_harness.py`

CLI harness for worker + mid-stream exposure/gain + unlock proof.

### `hardware_connection_test_vmbpy.py`

Minimal single-frame connection test.

### `__init__.py`

Exports `CameraViewWindow`, `VmbCameraWorker`, `ZoomPanCanvas`, `VMBPY_AVAILABLE`.

## Inputs

1. Allied Vision Alvium (USB3) + Vimba X drivers.
2. Optional static PNG for offline canvas demo.

## Outputs

1. Live preview for alignment.
2. Snapshot images (raw frames).
3. Smoke-test PNG / FPS logs.

## Related Docs

- `calibration_modules/README.md`
- `calibration_modules/SETUP_ON_PRINTER_COMPUTER.md`
- `calibration_modules/QUICK_REFERENCE.md`
- `documentation/CAMERA_VIEWER_POPUP_SPEC.md`
