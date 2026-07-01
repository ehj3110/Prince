# Calibration Modules Folder Index

## Purpose

The calibration_modules folder contains the camera-based setup and alignment workflow for the resin tank and projector system.
It covers live camera viewing, focus and tilt analysis, ChArUco pattern generation, and automated calibration orchestration.

## What This Folder Owns

1. Allied Vision camera connection and streaming.
2. ChArUco-based focus and tilt analysis.
3. Calibration GUI windows and operator controls.
4. Pattern generation and projector display tests.
5. Hardware bring-up validation scripts.

## Core Functional Path

1. Connect to the camera.
2. Stream frames and inspect focus/tilt.
3. Project a ChArUco pattern.
4. Adjust camera exposure and gain if needed.
5. Save calibration state and restore DLP output.

## Major Modules

### `AlliedVisionCameraManager.py`

Camera interface and streaming manager.
It owns camera connection, frame callbacks, exposure and gain control, and ChArUco-calibration hookups.

### `ChArucoCalibrator.py`

The core focus/tilt analysis engine.
It generates patterns, computes focus scores, estimates tilt, and can render detection overlays.

### `CameraViewWindow.py`

GUI front end for camera view, capture, and calibration operations.

### `CalibrationWorkflow.py`

Automated calibration orchestration.
It handles pattern preparation, projection, camera optimization, live guidance, and DLP restore behavior.

### `test_camera.py`

Basic camera connection and capture validation.

### `test_pattern_generation.py`

Verifies ChArUco pattern generation.

### `test_dlp_pattern_display.py`

Checks projector display behavior for calibration patterns.

### `live_stream_test.py`

Interactive camera live-stream test that combines streaming and calibration analysis.

### `hardware_connection_test_vmbpy.py` and `hardware_connection_test_vimbax.py`

Minimal vendor SDK connection tests for Allied Vision hardware paths.

### `__init__.py`

Package export layer for the calibration module set.

## Inputs

1. Allied Vision camera hardware.
2. ChArUco projector patterns.
3. Camera intrinsics when absolute tilt is desired.
4. Projector/DLP state during calibration.

## Outputs

1. Focus scores.
2. Relative or absolute tilt estimates.
3. Calibration data snapshots.
4. Pattern image files and validation logs.

## Dependencies

1. `opencv-contrib-python`
2. `numpy`
3. Allied Vision Vimba SDK or Vimba X tooling, depending on script path
4. `tkinter`
5. `support_modules.DebugSupport` and shared DLP coordination paths where integrated

## Failure Modes

1. Camera SDK not installed or wrong package variant.
2. No camera detected or wrong camera selected.
3. Projection path mismatch during calibration display.
4. Stale documentation or UI labels not matching implemented behavior.

## Documentation Notes

The calibration folder already has a substantial README and technical docs.
This round-2 index is the folder-level guide for codebase documentation and should be kept aligned with the current implemented workflow.
