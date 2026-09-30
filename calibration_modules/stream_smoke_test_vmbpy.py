#!/usr/bin/env python3
"""
Sub-phase 1A: Allied Vision stream smoke test (vmbpy).

Opens the physical Alvium camera, streams for a fixed duration via
get_frame_generator, reports FPS / frame shape, saves one PNG, then releases
VmbSystem so Vimba Viewer can reconnect immediately.

Run (from repo root, printer PC conda env)::

    .\\.conda\\python.exe calibration_modules\\stream_smoke_test_vmbpy.py
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import cv2
import numpy as np

try:
    from vmbpy import VmbSystem
    from vmbpy import PixelFormat
except ImportError:
    print("ERROR: vmbpy is not installed. Install Vimba X + pip install vmbpy.")
    sys.exit(1)


def _is_physical(cam) -> bool:
    model = (cam.get_model() or "").lower()
    cam_id = (cam.get_id() or "").lower()
    return "simulator" not in model and "simulator" not in cam_id


def _to_gray_u8(image: np.ndarray) -> np.ndarray:
    """Normalize OpenCV image to contiguous 2D uint8 grayscale and copy."""
    if image.ndim == 3 and image.shape[2] == 1:
        image = image[:, :, 0]
    elif image.ndim == 3 and image.shape[2] == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    image = np.ascontiguousarray(image)
    if image.dtype != np.uint8:
        image = cv2.normalize(image, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    return image.copy()


def _try_set_mono8(cam) -> None:
    try:
        cam.set_pixel_format(PixelFormat.Mono8)
        print("Pixel format set to Mono8.")
    except Exception as exc:
        print(f"WARNING: Could not set Mono8 ({exc}); continuing with default.")


def run_smoke_test(duration_s: float, output_png: Path) -> int:
    last_image: np.ndarray | None = None
    model = "Unknown"
    cam_id = "Unknown"
    frame_count = 0

    print(f"Streaming for {duration_s:.1f} s (physical cameras only)...")

    with VmbSystem.get_instance() as vmb:
        cameras = vmb.get_all_cameras()
        if not cameras:
            print("ERROR: No cameras found.")
            return 1

        physical = [c for c in cameras if _is_physical(c)]
        if not physical:
            print("ERROR: No physical cameras detected. Check power, cables, Vimba Viewer.")
            return 1

        cam = physical[0]
        with cam:
            model = cam.get_model()
            cam_id = cam.get_id()
            print(f"Connected: {model} ({cam_id})")
            _try_set_mono8(cam)

            # Prefer a short exposure so FPS reflects streaming, not shutter time
            try:
                cam.get_feature_by_name("ExposureTime").set(2000.0)
                print("ExposureTime set to 2000 us for smoke test.")
            except Exception as exc:
                print(f"WARNING: Could not set ExposureTime ({exc})")

            deadline = time.perf_counter() + duration_s
            t0 = time.perf_counter()
            for frame in cam.get_frame_generator(limit=None, timeout_ms=2000):
                image = _to_gray_u8(frame.as_opencv_image())
                last_image = image
                frame_count += 1
                if time.perf_counter() >= deadline:
                    break
            elapsed = max(time.perf_counter() - t0, 1e-6)

    fps = frame_count / elapsed if frame_count else 0.0

    if last_image is None or frame_count == 0:
        print("ERROR: No frames acquired.")
        return 1

    output_png = output_png.resolve()
    if not cv2.imwrite(str(output_png), last_image):
        print(f"ERROR: Failed to save {output_png}")
        return 1

    h, w = last_image.shape[:2]
    print(f"SUCCESS: camera={model} id={cam_id}")
    print(f"  frames={frame_count}  elapsed={elapsed:.2f}s  fps={fps:.1f}")
    print(f"  shape={w}x{h}  dtype={last_image.dtype}")
    print(f"  saved={output_png}")
    print("Camera released. Confirm Vimba Viewer can reopen the device.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Allied Vision vmbpy stream smoke test")
    parser.add_argument(
        "--duration",
        type=float,
        default=8.0,
        help="Stream duration in seconds (default: 8)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("stream_smoke_test.png"),
        help="Output PNG path (default: stream_smoke_test.png in cwd)",
    )
    args = parser.parse_args()
    return run_smoke_test(args.duration, args.output)


if __name__ == "__main__":
    raise SystemExit(main())
