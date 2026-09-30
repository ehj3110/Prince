#!/usr/bin/env python3
"""
Comprehensive robustness and unit test suite for the Allied Vision Camera Viewer subsystem.

Tests:
1. Gamma LUT computation across range 0.2 to 3.0
2. Zoom and Pan cursor anchoring mathematics
3. Synthetic test pattern generator
4. VmbCameraWorker lifecycle in mock/offline mode
5. VmbCameraWorker live acquisition with physical Alvium camera (if detected)
6. CameraViewWindow Tkinter lifecycle and teardown

Run with::
    .\\.conda\\python.exe tests\\test_camera_viewer_robustness.py
"""

from __future__ import annotations

import os
import queue
import sys
import time
import unittest
from pathlib import Path

import numpy as np

# Ensure repository root is on sys.path
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from calibration_modules.vmb_camera_worker import (
    VMBPY_AVAILABLE,
    VmbCameraWorker,
    generate_synthetic_frame,
    _normalize_frame,
)
from calibration_modules.zoom_pan_canvas import ZoomPanCanvas


class TestZoomPanMath(unittest.TestCase):
    """Test canvas math, coordinate anchoring, and LUT generation."""

    def test_gamma_lut_ranges(self):
        for gamma in [0.2, 0.5, 0.8, 1.0, 1.5, 2.2, 3.0]:
            lut = ZoomPanCanvas._build_gamma_lut(gamma)
            self.assertEqual(len(lut), 256)
            self.assertEqual(lut.dtype, np.uint8)
            self.assertEqual(lut[0], 0)
            self.assertEqual(lut[255], 255)
            # Monotonicity check
            self.assertTrue(np.all(np.diff(lut) >= 0), f"LUT for gamma={gamma} is not monotonic")

    def test_cursor_anchored_zoom(self):
        """Verify that zooming centered on (mx, my) preserves the image coordinate under the cursor."""
        pan_x = 50.0
        pan_y = 30.0
        zoom_scale = 1.0
        mx, my = 400.0, 300.0

        # Current image coordinate under (mx, my):
        img_x = (mx - pan_x) / zoom_scale
        img_y = (my - pan_y) / zoom_scale

        # Zoom by factor k
        k = 1.5
        new_zoom = zoom_scale * k
        new_pan_x = mx - k * (mx - pan_x)
        new_pan_y = my - k * (my - pan_y)

        # Image coordinate under (mx, my) after zoom:
        new_img_x = (mx - new_pan_x) / new_zoom
        new_img_y = (my - new_pan_y) / new_zoom

        self.assertAlmostEqual(img_x, new_img_x, places=5)
        self.assertAlmostEqual(img_y, new_img_y, places=5)

    def test_synthetic_frame_generator(self):
        frame = generate_synthetic_frame(0, width=800, height=600)
        self.assertEqual(frame.shape, (600, 800))
        self.assertEqual(frame.dtype, np.uint8)
        self.assertGreater(frame.max(), 0)
        self.assertLessEqual(frame.max(), 255)

    def test_normalize_frame(self):
        # 3D mono -> 2D
        img3d = np.ones((100, 100, 1), dtype=np.uint8) * 128
        norm = _normalize_frame(img3d)
        self.assertEqual(norm.shape, (100, 100))
        self.assertEqual(norm.dtype, np.uint8)

        # uint16 scaling
        img16 = np.ones((50, 50), dtype=np.uint16) * 32768
        norm16 = _normalize_frame(img16)
        self.assertEqual(norm16.shape, (50, 50))
        self.assertEqual(norm16.dtype, np.uint8)
        self.assertGreaterEqual(norm16.max(), 120)


class TestMockCameraWorker(unittest.TestCase):
    """Test worker thread in mock/offline mode."""

    def test_mock_worker_streaming_and_stop(self):
        q = queue.Queue(maxsize=1)
        worker = VmbCameraWorker(q, fallback_to_mock=True)
        worker._running = True

        # Run mock stream in thread
        import threading
        t = threading.Thread(target=worker._run_mock_stream, daemon=True)
        t.start()

        # Collect frames
        frames = []
        deadline = time.perf_counter() + 2.0
        while time.perf_counter() < deadline and len(frames) < 5:
            try:
                f = q.get(timeout=0.1)
                frames.append(f)
            except queue.Empty:
                continue

        worker.stop(join_timeout=1.0)
        t.join(timeout=1.0)

        self.assertGreaterEqual(len(frames), 5)
        self.assertEqual(frames[0].shape, (1024, 1280))
        self.assertFalse(t.is_alive())


class TestPhysicalCameraWorker(unittest.TestCase):
    """Test worker thread with live physical hardware if vmbpy is available."""

    def test_physical_camera_acquisition(self):
        if not VMBPY_AVAILABLE:
            self.skipTest("vmbpy is not available in current environment")

        q = queue.Queue(maxsize=1)
        worker = VmbCameraWorker(q, fallback_to_mock=False)
        worker.start()

        # Wait up to 5s for camera connection
        deadline = time.perf_counter() + 5.0
        while time.perf_counter() < deadline and not worker.connected:
            time.sleep(0.1)

        if not worker.connected:
            worker.stop()
            self.skipTest(f"Physical camera not connected: {worker.last_error}")

        # Capture at least 3 frames
        frames = []
        deadline = time.perf_counter() + 4.0
        while time.perf_counter() < deadline and len(frames) < 3:
            try:
                f = q.get(timeout=0.2)
                frames.append(f)
            except queue.Empty:
                continue

        # Test parameter change mid-stream
        worker.request_exposure(5000.0)
        worker.request_gain(2.0)
        time.sleep(0.5)

        # Stop worker
        worker.stop(join_timeout=4.0)

        self.assertGreaterEqual(len(frames), 1, "Failed to capture frames from physical camera")
        self.assertEqual(frames[0].shape, (2064, 2464), "Expected Alvium 1800 U-511m resolution")
        self.assertFalse(worker.is_alive(), "Worker thread did not stop cleanly")


class TestCameraViewWindowUI(unittest.TestCase):
    """Test Tkinter CameraViewWindow lifecycle and UI interaction."""

    def test_window_headless_lifecycle(self):
        import tkinter as tk
        from calibration_modules.CameraViewWindow import CameraViewWindow

        root = tk.Tk()
        root.withdraw()

        app = CameraViewWindow(parent=root, fallback_to_mock=True)
        # Pump Tkinter events for 300 ms
        for _ in range(10):
            root.update()
            time.sleep(0.03)

        # Test slider changes
        app.exp_slider.set(15000)
        app._on_exposure_slider("15000")
        app.gain_slider.set(3.5)
        app._on_gain_slider("3.5")
        app.contrast_slider.set(1.4)
        app.gamma_slider.set(1.2)
        app._update_software_filters()

        # Pump events to trigger debounced calls
        for _ in range(10):
            root.update()
            time.sleep(0.03)

        # Close and teardown
        app.on_closing()
        root.destroy()


def run_tests():
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())
