#!/usr/bin/env python3
"""Camera-based projection presence checker for Allied Vision cameras.

This helper detects whether projected light is physically present by comparing
mean intensity in a central ROI between dark and lit capture windows.
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional

import cv2
import numpy as np


class ProjectionPresenceChecker:
    def __init__(
        self,
        sdk_priority: Optional[List[str]] = None,
        require_physical_hardware: bool = True,
    ):
        self.sdk_priority = sdk_priority or ["vmbpy", "vimbax"]
        self.require_physical_hardware = require_physical_hardware
        self.backend_name = None
        self._system_ctx = None
        self._system = None
        self._camera = None

    def connect(self) -> bool:
        for backend in self.sdk_priority:
            try:
                if backend.lower() == "vmbpy" and self._connect_vmbpy():
                    self.backend_name = "vmbpy"
                    return True
                if backend.lower() == "vimbax" and self._connect_vimbax():
                    self.backend_name = "vimbax"
                    return True
            except Exception:
                self.disconnect()
        return False

    def disconnect(self) -> None:
        if self._camera is not None:
            try:
                self._camera.__exit__(None, None, None)
            except Exception:
                pass
            self._camera = None

        if self._system_ctx is not None:
            try:
                self._system_ctx.__exit__(None, None, None)
            except Exception:
                pass
            self._system_ctx = None
            self._system = None

    def _is_physical(self, camera) -> bool:
        try:
            model = str(camera.get_model()).lower()
            cam_id = str(camera.get_id()).lower()
            return "simulator" not in model and "simulator" not in cam_id
        except Exception:
            return True

    def _connect_vmbpy(self) -> bool:
        try:
            from vmbpy import VmbSystem
        except Exception:
            return False

        self._system_ctx = VmbSystem.get_instance()
        self._system = self._system_ctx.__enter__()
        cameras = self._system.get_all_cameras()
        if self.require_physical_hardware:
            cameras = [cam for cam in cameras if self._is_physical(cam)]
        if not cameras:
            self.disconnect()
            return False

        self._camera = cameras[0]
        self._camera.__enter__()
        return True

    def _connect_vimbax(self) -> bool:
        try:
            from vimbax import VimbaX
        except Exception:
            return False

        self._system_ctx = VimbaX.get_instance()
        self._system = self._system_ctx.__enter__()
        cameras = self._system.get_all_cameras()
        if self.require_physical_hardware:
            cameras = [cam for cam in cameras if self._is_physical(cam)]
        if not cameras:
            self.disconnect()
            return False

        self._camera = cameras[0]
        self._camera.__enter__()
        return True

    def capture_frame(self) -> Optional[np.ndarray]:
        if self._camera is None:
            return None
        frame = self._camera.get_frame()

        if hasattr(frame, "as_opencv_image"):
            image = frame.as_opencv_image()
        elif hasattr(frame, "as_numpy_ndarray"):
            image = frame.as_numpy_ndarray()
        else:
            return None

        if image is None:
            return None

        return np.asarray(image)

    @staticmethod
    def _roi_mean_intensity(image: np.ndarray) -> float:
        if image is None or image.size == 0:
            return 0.0

        if image.ndim == 3:
            if image.shape[2] == 1:
                gray = image[:, :, 0]
            else:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        height, width = gray.shape[:2]
        y0, y1 = int(height * 0.1), int(height * 0.9)
        x0, x1 = int(width * 0.1), int(width * 0.9)
        roi = gray[y0:y1, x0:x1]
        if roi.size == 0:
            return float(np.mean(gray))

        return float(np.mean(roi))

    def sample_mean(self, sample_count: int = 8, sample_interval_s: float = 0.04) -> float:
        values = []
        for _ in range(max(1, sample_count)):
            frame = self.capture_frame()
            if frame is not None:
                values.append(self._roi_mean_intensity(frame))
            time.sleep(max(0.0, sample_interval_s))

        if not values:
            raise RuntimeError("Failed to capture camera frames for projection check")

        return float(np.mean(values))

    def verify_projection(
        self,
        baseline_frames: int,
        lit_frames: int,
        intensity_margin: float,
        dark_threshold: float,
        settle_s: float,
    ) -> Dict[str, object]:
        baseline_mean = self.sample_mean(sample_count=baseline_frames)
        time.sleep(max(0.0, settle_s))
        lit_mean = self.sample_mean(sample_count=lit_frames)

        adaptive_threshold = max(float(dark_threshold), baseline_mean + float(intensity_margin))
        light_detected = lit_mean > adaptive_threshold

        return {
            "backend": self.backend_name,
            "baseline_mean": baseline_mean,
            "lit_mean": lit_mean,
            "threshold": adaptive_threshold,
            "light_detected": light_detected,
        }
