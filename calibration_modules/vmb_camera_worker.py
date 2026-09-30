"""
Vimba X (vmbpy) camera worker for Allied Vision cameras.

Runs all VmbSystem / Camera API calls on a dedicated daemon thread.
Frames are delivered via a drop-oldest queue.Queue(maxsize=1).
Hardware exposure/gain changes are applied only on the camera thread.
Includes auto-reconnect recovery, rolling FPS telemetry, and optional synthetic fallback mode.
"""

from __future__ import annotations

import queue
import threading
import time
from typing import Optional, Tuple

import numpy as np

try:
    from vmbpy import VmbSystem, PixelFormat

    VMBPY_AVAILABLE = True
except ImportError:
    VMBPY_AVAILABLE = False


def _is_physical(cam) -> bool:
    model = (cam.get_model() or "").lower()
    cam_id = (cam.get_id() or "").lower()
    return "simulator" not in model and "simulator" not in cam_id


def _normalize_frame(image: np.ndarray) -> np.ndarray:
    """Return a contiguous 2D uint8 copy safe to hold after Vimba reuses buffers."""
    if image.ndim == 3 and image.shape[2] == 1:
        image = image[:, :, 0]
    elif image.ndim == 3 and image.shape[2] == 3:
        # Caller paths that produce BGR should convert before here. Keep as luminance.
        image = image[:, :, 0]
    image = np.ascontiguousarray(image)
    if image.dtype != np.uint8:
        info_max = float(np.iinfo(image.dtype).max) if np.issubdtype(image.dtype, np.integer) else float(image.max() or 1.0)
        image = (image.astype(np.float32) * (255.0 / max(info_max, 1.0))).clip(0, 255).astype(np.uint8)
    return image.copy()


def generate_synthetic_frame(frame_idx: int, width: int = 1280, height: int = 1024) -> np.ndarray:
    """Generate a realistic synthetic test pattern with moving alignment target and grid."""
    img = np.zeros((height, width), dtype=np.uint8)
    
    # Grid lines every 64 pixels
    img[::64, :] = 40
    img[:, ::64] = 40
    
    # Concentric circles in center
    cx, cy = width // 2, height // 2
    y, x = np.ogrid[:height, :width]
    dist_sq = (x - cx) ** 2 + (y - cy) ** 2
    
    for r in [50, 100, 150, 200, 300, 400]:
        mask = (dist_sq >= (r - 2) ** 2) & (dist_sq <= (r + 2) ** 2)
        img[mask] = 120
        
    # Moving dot across a circle
    angle = (frame_idx % 120) * (2 * np.pi / 120)
    orbit_r = 150
    ox = int(cx + orbit_r * np.cos(angle))
    oy = int(cy + orbit_r * np.sin(angle))
    odot_sq = (x - ox) ** 2 + (y - oy) ** 2
    img[odot_sq <= 12 ** 2] = 230
    
    # Text / resolution indicator bar at bottom
    img[height - 30:, :] = 70
    
    return img


class VmbCameraWorker(threading.Thread):
    """
    Dedicated worker thread for Allied Vision acquisition.
    Features:
    - Thread-isolated VmbSystem context
    - Automatic reconnection loop upon physical disconnect
    - Rolling FPS and frame telemetry
    - Hardware parameter clamping and debounced queue dispatch
    - Synthetic mock mode fallback for testing without hardware
    """

    def __init__(
        self,
        frame_queue: queue.Queue,
        fallback_to_mock: bool = False,
        reconnect_interval_s: float = 2.0,
    ):
        super().__init__(daemon=True, name="VmbCameraWorker")
        self.frame_queue = frame_queue
        self.fallback_to_mock = fallback_to_mock
        self.reconnect_interval_s = max(0.5, float(reconnect_interval_s))

        self._running = False
        self.connected = False
        self.is_mock = False
        self.cam_id: Optional[str] = None
        self.cam_model: str = "Unknown"
        self.last_error: Optional[str] = None

        self._pending_exposure: Optional[float] = None
        self._pending_gain: Optional[float] = None
        self._lock = threading.Lock()

        self.exposure_range: Tuple[float, float] = (100.0, 1_000_000.0)
        self.gain_range: Tuple[float, float] = (0.0, 24.0)
        self.current_exposure: Optional[float] = None
        self.current_gain: Optional[float] = None

        # Telemetry
        self.fps: float = 0.0
        self.frame_count: int = 0
        self.dropped_frames: int = 0
        self.mean_intensity: float = 0.0
        self._last_fps_time = time.perf_counter()
        self._fps_frame_count = 0

    @property
    def running(self) -> bool:
        return self._running

    def request_exposure(self, exposure_us: float) -> None:
        with self._lock:
            self._pending_exposure = float(exposure_us)

    def request_gain(self, gain_db: float) -> None:
        with self._lock:
            self._pending_gain = float(gain_db)

    def stop(self, join_timeout: float = 3.0) -> None:
        """Signal stop and wait for the thread to leave VmbSystem context."""
        self._running = False
        if self.is_alive() and threading.current_thread() is not self:
            self.join(timeout=join_timeout)

    def _apply_pending_features(self, cam) -> None:
        with self._lock:
            exp = self._pending_exposure
            gain = self._pending_gain
            self._pending_exposure = None
            self._pending_gain = None

        if exp is not None:
            lo, hi = self.exposure_range
            clamped = max(lo, min(exp, hi))
            try:
                cam.get_feature_by_name("ExposureTime").set(clamped)
                self.current_exposure = clamped
            except Exception as exc:
                print(f"VmbCameraWorker: failed to set ExposureTime: {exc}")

        if gain is not None:
            lo, hi = self.gain_range
            clamped = max(lo, min(gain, hi))
            try:
                cam.get_feature_by_name("Gain").set(clamped)
                self.current_gain = clamped
            except Exception as exc:
                print(f"VmbCameraWorker: failed to set Gain: {exc}")

    def _enqueue_frame(self, image: np.ndarray) -> None:
        # Telemetry update
        self.frame_count += 1
        self._fps_frame_count += 1
        now = time.perf_counter()
        elapsed = now - self._last_fps_time
        if elapsed >= 1.0:
            self.fps = round(self._fps_frame_count / elapsed, 1)
            self._fps_frame_count = 0
            self._last_fps_time = now
            # Light telemetry: estimate mean intensity every second
            self.mean_intensity = float(np.mean(image[::8, ::8]))

        if self.frame_queue.full():
            try:
                self.frame_queue.get_nowait()
                self.dropped_frames += 1
            except queue.Empty:
                pass
        try:
            self.frame_queue.put_nowait(image)
        except queue.Full:
            self.dropped_frames += 1

    def _run_mock_stream(self) -> None:
        """Fallback synthetic generator when no hardware is available."""
        self.is_mock = True
        self.connected = True
        self.cam_id = "MOCK_SYNTHETIC_01"
        self.cam_model = "Synthetic Alvium Pattern"
        self.current_exposure = 10000.0
        self.current_gain = 0.0
        print("VmbCameraWorker: Running in synthetic mock mode.")

        idx = 0
        while self._running:
            with self._lock:
                if self._pending_exposure is not None:
                    self.current_exposure = self._pending_exposure
                    self._pending_exposure = None
                if self._pending_gain is not None:
                    self.current_gain = self._pending_gain
                    self._pending_gain = None

            frame = generate_synthetic_frame(idx)
            self._enqueue_frame(frame)
            idx += 1
            time.sleep(0.033)  # ~30 FPS

        self.connected = False
        print("VmbCameraWorker: Mock stream stopped.")

    def run(self) -> None:
        if not VMBPY_AVAILABLE:
            self.last_error = "vmbpy is not installed"
            print(f"ERROR: {self.last_error}")
            if self.fallback_to_mock:
                self._running = True
                self._run_mock_stream()
                return
            self._running = False
            self.connected = False
            return

        self._running = True
        self.last_error = None

        while self._running:
            try:
                print("VmbCameraWorker: opening VmbSystem...")
                with VmbSystem.get_instance() as vmb:
                    if not self._running:
                        break

                    cameras = vmb.get_all_cameras()
                    physical = [c for c in cameras if _is_physical(c)]
                    if not physical:
                        self.last_error = "No physical Allied Vision cameras detected"
                        if self.fallback_to_mock:
                            print(f"{self.last_error} -> falling back to synthetic mock stream.")
                            self._run_mock_stream()
                            break

                        print(f"VmbCameraWorker: {self.last_error}. Retrying in {self.reconnect_interval_s}s...")
                        # Wait before retry, checking self._running
                        sleep_ticks = int(self.reconnect_interval_s / 0.1)
                        for _ in range(sleep_ticks):
                            if not self._running:
                                break
                            time.sleep(0.1)
                        continue

                    cam = physical[0]
                    with cam:
                        if not self._running:
                            break
                        self.cam_id = cam.get_id()
                        self.cam_model = cam.get_model()
                        self.connected = True
                        self.is_mock = False
                        self.last_error = None
                        print(f"VmbCameraWorker: connected to {self.cam_model} ({self.cam_id})")

                        try:
                            cam.set_pixel_format(PixelFormat.Mono8)
                        except Exception as exc:
                            print(f"VmbCameraWorker: Mono8 not set ({exc})")

                        try:
                            feat_exp = cam.get_feature_by_name("ExposureTime")
                            self.exposure_range = tuple(feat_exp.get_range())
                            self.current_exposure = float(feat_exp.get())
                            # Cap long initial exposure for responsive preview
                            if self.current_exposure > 20000.0:
                                feat_exp.set(10000.0)
                                self.current_exposure = 10000.0
                        except Exception as exc:
                            print(f"VmbCameraWorker: ExposureTime range unavailable: {exc}")

                        try:
                            feat_gain = cam.get_feature_by_name("Gain")
                            self.gain_range = tuple(feat_gain.get_range())
                            self.current_gain = float(feat_gain.get())
                        except Exception as exc:
                            print(f"VmbCameraWorker: Gain range unavailable: {exc}")

                        for frame in cam.get_frame_generator(limit=None, timeout_ms=2000):
                            if not self._running:
                                break
                            try:
                                self._apply_pending_features(cam)
                                image = _normalize_frame(frame.as_opencv_image())
                                self._enqueue_frame(image)
                            except Exception as exc:
                                time.sleep(0.01)
                                if not self._running:
                                    break
                                continue

            except Exception as exc:
                self.last_error = str(exc)
                self.connected = False
                print(f"VmbCameraWorker: connection interrupted ({exc}).")
                if self._running:
                    print(f"VmbCameraWorker: attempting reconnection in {self.reconnect_interval_s}s...")
                    sleep_ticks = int(self.reconnect_interval_s / 0.1)
                    for _ in range(sleep_ticks):
                        if not self._running:
                            break
                        time.sleep(0.1)

        self.connected = False
        self._running = False
        print("VmbCameraWorker: stopped cleanly.")
