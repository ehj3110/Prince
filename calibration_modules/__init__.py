"""
Calibration Modules
===================

Modules for camera-based calibration and alignment of resin tank.

Components:
- AlliedVisionCameraManager: Allied Vision USB camera interface
- CameraViewWindow: Real-time camera viewing window
- ChArucoCalibrator: ChArUco-based focus and tilt detection

Method: Foveated ChArUco Projection
- Single pattern performs "double duty" for focus AND tilt
- Works with limited FOV (inner 50% due to vignetting)
- Laplacian variance for focus (MTF proxy)
- Marker pose estimation for tilt/tip

Author: Cheng Sun Lab Team
Date: November 28, 2025
"""

from .AlliedVisionCameraManager import AlliedVisionCameraManager, list_available_cameras
from .CameraViewWindow import CameraViewWindow
from .ChArucoCalibrator import ChArucoCalibrator, generate_calibration_pattern
from .CalibrationWorkflow import CalibrationWorkflow

__all__ = [
    'AlliedVisionCameraManager',
    'CameraViewWindow',
    'ChArucoCalibrator',
    'CalibrationWorkflow',
    'list_available_cameras',
    'generate_calibration_pattern'
]
