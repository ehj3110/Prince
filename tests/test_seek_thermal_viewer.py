#!/usr/bin/env python3
"""
Test suite for Seek Thermal InspectionCAM standalone viewer and acquisition worker.
File: tests/test_seek_thermal_viewer.py

Run with::
    .\\.conda\\python.exe tests\\test_seek_thermal_viewer.py
"""

from __future__ import annotations

import os
import queue
import sys
import tempfile
import time
import unittest
from pathlib import Path

import numpy as np

# Ensure repository root is on sys.path
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from calibration_modules.seek_thermal_worker import (
    SeekThermalWorker,
    generate_synthetic_thermal_frame,
)
from calibration_modules.seek_thermal_canvas import COLORMAP_DICT, SeekThermalCanvas


class TestSeekThermalWorker(unittest.TestCase):
    """Test synthetic radiometric frame generation and worker acquisition loop."""

    def test_synthetic_frame_generator(self):
        frame = generate_synthetic_thermal_frame(0)
        self.assertEqual(frame.shape, (240, 320))
        self.assertEqual(frame.dtype, np.float32)
        # Temperatures should be realistic room/vat temperatures (15 to 60 °C)
        self.assertGreaterEqual(float(np.min(frame)), 15.0)
        self.assertLessEqual(float(np.max(frame)), 65.0)

    def test_worker_mock_streaming(self):
        q = queue.Queue(maxsize=1)
        worker = SeekThermalWorker(q, fallback_to_mock=True)
        worker.start()

        # Collect at least 3 frames
        frames = []
        deadline = time.perf_counter() + 2.5
        while time.perf_counter() < deadline and len(frames) < 3:
            try:
                f = q.get(timeout=0.2)
                frames.append(f)
            except queue.Empty:
                continue

        worker.stop(join_timeout=2.0)

        self.assertGreaterEqual(len(frames), 2)
        self.assertEqual(frames[0].shape, (240, 320))
        self.assertFalse(worker.is_alive())
        self.assertGreater(worker.max_temp_c, worker.min_temp_c)


class TestSeekThermalCanvas(unittest.TestCase):
    """Test radiometric thermal canvas transformations and spot probing."""

    def setUp(self):
        import tkinter as tk
        self.root = tk.Tk()
        self.root.withdraw()
        self.canvas = SeekThermalCanvas(self.root)
        self.canvas.pack()

    def tearDown(self):
        self.root.destroy()

    def test_palettes(self):
        sample = generate_synthetic_thermal_frame(0)
        self.canvas.set_radiometric_frame(sample)

        for palette_name in COLORMAP_DICT.keys():
            self.canvas.set_palette(palette_name)
            self.root.update()
            self.assertEqual(self.canvas.palette_name, palette_name)

    def test_sensor_canvas_mapping(self):
        sample = generate_synthetic_thermal_frame(0)
        self.canvas.set_radiometric_frame(sample)
        self.canvas.pan_x = 20.0
        self.canvas.pan_y = 10.0
        self.canvas.zoom_scale = 2.0

        # Sensor center (160, 120)
        cx, cy = self.canvas._sensor_to_canvas(160, 120)
        self.assertEqual(cx, int(20.0 + 160 * 2.0))
        self.assertEqual(cy, int(10.0 + 120 * 2.0))

        # Reverse canvas to sensor
        sensor_pt = self.canvas._canvas_to_sensor(cx, cy)
        self.assertIsNotNone(sensor_pt)
        self.assertEqual(sensor_pt, (160, 120))


class TestSeekThermalViewerUI(unittest.TestCase):
    """Test full Tkinter viewer lifecycle, controls, and data export."""

    def test_window_headless_lifecycle_and_export(self):
        import tkinter as tk
        from calibration_modules.SeekThermalViewerWindow import SeekThermalViewerWindow

        root = tk.Tk()
        root.withdraw()

        app = SeekThermalViewerWindow(parent=root, fallback_to_mock=True)

        # Pump events to allow frame receipt and canvas rendering
        for _ in range(12):
            root.update()
            time.sleep(0.04)

        self.assertIsNotNone(app.latest_temp_array)
        self.assertEqual(app.latest_temp_array.shape, (240, 320))

        # Test changing palette and scale
        app.palette_var.set("Turbo")
        app.canvas.set_palette("Turbo")
        app.scale_mode_var.set("fixed")
        app.manual_min_var.set("22.0")
        app.manual_max_var.set("45.0")
        app._on_scale_mode_change()

        for _ in range(5):
            root.update()
            time.sleep(0.03)

        # Test CSV export
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp_csv:
            tmp_csv_path = tmp_csv.name
        try:
            np.savetxt(tmp_csv_path, app.latest_temp_array, delimiter=",", fmt="%.2f")
            loaded = np.loadtxt(tmp_csv_path, delimiter=",")
            self.assertEqual(loaded.shape, (240, 320))
        finally:
            if os.path.exists(tmp_csv_path):
                os.remove(tmp_csv_path)

        # Test NPY export
        with tempfile.NamedTemporaryFile(suffix=".npy", delete=False) as tmp_npy:
            tmp_npy_path = tmp_npy.name
        try:
            np.save(tmp_npy_path, app.latest_temp_array)
            loaded_npy = np.load(tmp_npy_path)
            self.assertEqual(loaded_npy.shape, (240, 320))
            self.assertEqual(loaded_npy.dtype, np.float32)
        finally:
            if os.path.exists(tmp_npy_path):
                os.remove(tmp_npy_path)

        # Clean teardown
        app.on_closing()
        root.destroy()


def run_tests():
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())
