"""
Seek Thermal InspectionCAM Worker Thread.
File: calibration_modules/seek_thermal_worker.py

Supports:
1. Official seekcamera-python SDK (if installed & seekcamera.dll present)
2. Synthetic Radiometric Mock Stream (320x240 @ 9 Hz) simulating SLA resin photopolymerization exotherm
"""

from __future__ import annotations

import os
import queue
import threading
import time
from typing import Optional, Tuple
import cv2
import numpy as np

# Check for official seekcamera SDK
try:
    import seekcamera
    SEEK_SDK_AVAILABLE = True
except ImportError:
    SEEK_SDK_AVAILABLE = False


def generate_synthetic_thermal_frame(frame_idx: int, width: int = 320, height: int = 240) -> np.ndarray:
    """
    Generate realistic 320x240 radiometric temperature frame (in degrees Celsius).
    Simulates a laboratory resin vat with DLP exposure exotherm.
    """
    # Base ambient room temperature ~22.0 °C
    t_ambient = 22.0
    
    # Slight thermal gradient across chassis
    y, x = np.ogrid[:height, :width]
    temp = t_ambient + 0.5 * (x / width) - 0.3 * (y / height)
    
    # Resin Vat pool (circular/rectangular basin ~24.5 °C)
    cx, cy = width // 2, height // 2
    vat_dist_sq = ((x - cx) / 1.3) ** 2 + ((y - cy) / 1.0) ** 2
    vat_mask = vat_dist_sq <= 85 ** 2
    temp[vat_mask] += 2.5
    
    # Photopolymerization exotherm hotspot (simulating active DLP curing pattern)
    # Exotherm cycles with a period of ~120 frames (~13 seconds)
    cycle_phase = (frame_idx % 120) / 120.0
    if cycle_phase < 0.6:
        # Curing active: temperature rises rapidly then plateaus
        exotherm_power = np.sin((cycle_phase / 0.6) * (np.pi / 2)) * 14.5
    else:
        # Cooling phase after exposure ends
        decay = (cycle_phase - 0.6) / 0.4
        exotherm_power = 14.5 * np.exp(-3.5 * decay)
        
    hotspot_dist_sq = (x - cx) ** 2 + (y - cy) ** 2
    gaussian_spot = np.exp(-hotspot_dist_sq / (2 * (32 ** 2)))
    temp += exotherm_power * gaussian_spot
    
    # Electronics driver heat spot in top-right corner (~31.0 °C)
    driver_dist_sq = (x - (width - 40)) ** 2 + (y - 35) ** 2
    temp += 7.0 * np.exp(-driver_dist_sq / (2 * (25 ** 2)))
    
    # Microbolometer sensor noise (NETD ~ 0.05 °C)
    noise = np.random.normal(0.0, 0.06, size=(height, width))
    temp += noise
    
    return temp.astype(np.float32)


class SeekThermalWorker(threading.Thread):
    """
    Dedicated background worker for Seek Thermal InspectionCAM.
    Manages USB connection, frame acquisition, and telemetry calculation.
    """

    def __init__(
        self,
        frame_queue: queue.Queue,
        fallback_to_mock: bool = True,
        poll_interval_s: float = 0.1,  # 9 Hz native
    ):
        super().__init__(daemon=True, name="SeekThermalWorker")
        self.frame_queue = frame_queue
        self.fallback_to_mock = fallback_to_mock
        self.poll_interval_s = max(0.03, float(poll_interval_s))

        self._running = False
        self.connected = False
        self.is_mock = False
        self.cam_id: str = "Unknown"
        self.cam_model: str = "InspectionCAM (IQ-AAA)"
        self.last_error: Optional[str] = None

        # Telemetry
        self.fps: float = 0.0
        self.min_temp_c: float = 0.0
        self.max_temp_c: float = 0.0
        self.mean_temp_c: float = 0.0
        self.frame_count: int = 0
        self.dropped_frames: int = 0

        self._last_fps_time = time.perf_counter()
        self._fps_frame_count = 0

    @property
    def running(self) -> bool:
        return self._running

    def stop(self, join_timeout: float = 3.0) -> None:
        """Stop worker cleanly and join thread."""
        self._running = False
        if self.is_alive() and threading.current_thread() is not self:
            self.join(timeout=join_timeout)

    def _enqueue_radiometric_frame(self, temp_c: np.ndarray) -> None:
        """Enqueue 2D float32 array of temperatures and update telemetry."""
        self.frame_count += 1
        self._fps_frame_count += 1
        now = time.perf_counter()
        elapsed = now - self._last_fps_time
        if elapsed >= 1.0:
            self.fps = round(self._fps_frame_count / elapsed, 1)
            self._fps_frame_count = 0
            self._last_fps_time = now

        self.min_temp_c = float(np.min(temp_c))
        self.max_temp_c = float(np.max(temp_c))
        self.mean_temp_c = float(np.mean(temp_c))

        if self.frame_queue.full():
            try:
                self.frame_queue.get_nowait()
                self.dropped_frames += 1
            except queue.Empty:
                pass
        try:
            self.frame_queue.put_nowait(temp_c)
        except queue.Full:
            self.dropped_frames += 1

    def _run_mock_loop(self) -> None:
        """Run synthetic 9 Hz thermal acquisition loop."""
        self.is_mock = True
        self.connected = True
        self.cam_id = "SYNTHETIC_MOCK_IQ_AAA"
        self.cam_model = "Seek InspectionCAM Simulation"
        print("SeekThermalWorker: Running in synthetic simulation mode.")

        idx = 0
        while self._running:
            start_t = time.perf_counter()
            frame_c = generate_synthetic_thermal_frame(idx)
            self._enqueue_radiometric_frame(frame_c)
            idx += 1

            # Sleep to match ~9 Hz native framerate
            elapsed = time.perf_counter() - start_t
            sleep_time = max(0.005, (1.0 / 9.0) - elapsed)
            time.sleep(sleep_time)

        self.connected = False
        print("SeekThermalWorker: Mock stream stopped cleanly.")

    def run(self) -> None:
        self._running = True
        self.last_error = None

        # Check if Seek Thermal SDK can be used
        use_hardware = False
        manager = None

        if SEEK_SDK_AVAILABLE:
            try:
                manager = seekcamera.SeekCameraManager(seekcamera.SeekCameraIOType.USB)
                use_hardware = True
            except Exception as e:
                self.last_error = f"Seek SDK runtime error: {e}"
                print(f"SeekThermalWorker: {self.last_error}")

        if not use_hardware:
            if self.fallback_to_mock:
                self._run_mock_loop()
                return
            else:
                self._running = False
                self.connected = False
                return

        # Hardware execution with seekcamera SDK
        try:
            with manager:
                def on_frame(_cam, camera_frame, _data):
                    if not self._running:
                        return
                    try:
                        th_frame = camera_frame.thermography_float
                        data = np.frombuffer(th_frame.data, dtype=np.float32).reshape(
                            (th_frame.height, th_frame.width)
                        ).copy()
                        self._enqueue_radiometric_frame(data)
                    except Exception as err:
                        self.last_error = str(err)

                def on_event(_mgr, camera, event_type, _data):
                    if event_type == seekcamera.SeekCameraManagerEvent.CONNECT:
                        self.cam_id = str(camera.chipid)
                        self.connected = True
                        camera.capture_session_start(seekcamera.SeekCameraFrameFormat.THERMOGRAPHY_FLOAT)
                    elif event_type == seekcamera.SeekCameraManagerEvent.DISCONNECT:
                        self.connected = False

                manager.register_event_callback(on_event)
                manager.register_frame_available_callback(on_frame)

                while self._running:
                    time.sleep(0.1)

        except Exception as exc:
            self.last_error = str(exc)
            print(f"SeekThermalWorker exception: {exc}")
            if self.fallback_to_mock and self._running:
                print("Falling back to synthetic mock stream...")
                self._run_mock_loop()
        finally:
            self.connected = False
            self._running = False
            print("SeekThermalWorker: stopped.")
