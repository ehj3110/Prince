#!/usr/bin/env python3
"""
Sub-phase 1B harness: exercise VmbCameraWorker without a GUI.

- Starts worker, drains frame queue, reports FPS
- Mid-stream applies exposure and gain changes and saves before/after PNGs
- Stops with join, then optionally starts a second short run to prove unlock

Run (from repo root)::

    .\\.conda\\python.exe calibration_modules\\vmb_worker_harness.py
"""

from __future__ import annotations

import argparse
import queue
import sys
import time
from pathlib import Path

import cv2

# Allow running as a script from repo root or calibration_modules/
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from vmb_camera_worker import VMBPY_AVAILABLE, VmbCameraWorker  # noqa: E402


def _drain_and_count(frame_queue: queue.Queue, duration_s: float) -> tuple[int, object | None]:
    """Drain queue for duration_s; return (frames_received, last_frame)."""
    count = 0
    last = None
    deadline = time.perf_counter() + duration_s
    while time.perf_counter() < deadline:
        try:
            last = frame_queue.get(timeout=0.05)
            count += 1
        except queue.Empty:
            continue
    return count, last


def _save(path: Path, image) -> None:
    if image is None:
        print(f"WARNING: no frame to save for {path}")
        return
    if not cv2.imwrite(str(path), image):
        print(f"ERROR: failed to write {path}")
    else:
        print(f"Saved {path} shape={image.shape}")


def main() -> int:
    parser = argparse.ArgumentParser(description="VmbCameraWorker CLI harness")
    parser.add_argument("--warmup", type=float, default=2.0, help="Warmup stream seconds")
    parser.add_argument("--after", type=float, default=2.0, help="Seconds after parameter change")
    parser.add_argument("--exposure", type=float, default=5000.0, help="Exposure (us) to apply mid-stream")
    parser.add_argument("--gain", type=float, default=5.0, help="Gain (dB) to apply mid-stream")
    parser.add_argument("--outdir", type=Path, default=Path("."), help="Directory for PNG outputs")
    args = parser.parse_args()

    if not VMBPY_AVAILABLE:
        print("ERROR: vmbpy not available")
        return 1

    outdir = args.outdir.resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    frame_queue: queue.Queue = queue.Queue(maxsize=1)
    worker = VmbCameraWorker(frame_queue)
    worker.start()

    # VmbSystem init can take several seconds after a prior process release
    connect_timeout_s = 30.0
    t_wait = time.perf_counter() + connect_timeout_s
    print(f"Waiting up to {connect_timeout_s:.0f}s for camera connect...")
    while time.perf_counter() < t_wait and not worker.connected and worker.is_alive():
        time.sleep(0.05)

    if not worker.connected:
        err = worker.last_error or "connect failed (timeout or worker exited)"
        print(f"ERROR: {err}")
        worker.stop()
        return 1

    print(f"Connected: {worker.cam_model} ({worker.cam_id})")
    print(f"Exposure range: {worker.exposure_range}, Gain range: {worker.gain_range}")

    t0 = time.perf_counter()
    n1, before = _drain_and_count(frame_queue, args.warmup)
    elapsed1 = max(time.perf_counter() - t0, 1e-6)
    print(f"Warmup: frames={n1} fps={n1 / elapsed1:.1f}")
    _save(outdir / "worker_harness_before.png", before)

    print(f"Requesting exposure={args.exposure} us, gain={args.gain} dB")
    worker.request_exposure(args.exposure)
    worker.request_gain(args.gain)

    t1 = time.perf_counter()
    n2, after = _drain_and_count(frame_queue, args.after)
    elapsed2 = max(time.perf_counter() - t1, 1e-6)
    print(f"After change: frames={n2} fps={n2 / elapsed2:.1f}")
    print(f"Worker reports exposure={worker.current_exposure}, gain={worker.current_gain}")
    _save(outdir / "worker_harness_after.png", after)

    worker.stop(join_timeout=5.0)
    if worker.is_alive():
        print("ERROR: worker did not join within timeout")
        return 1
    print("Worker joined cleanly.")

    # Second short run proves camera unlock
    print("Second run (unlock proof)...")
    q2: queue.Queue = queue.Queue(maxsize=1)
    w2 = VmbCameraWorker(q2)
    w2.start()
    t_wait = time.perf_counter() + connect_timeout_s
    while time.perf_counter() < t_wait and not w2.connected and w2.is_alive():
        time.sleep(0.05)
    if not w2.connected:
        print(f"ERROR: second connect failed: {w2.last_error}")
        w2.stop()
        return 1
    n3, _ = _drain_and_count(q2, 1.5)
    w2.stop(join_timeout=5.0)
    print(f"Second run frames={n3}; unlock OK" if n3 > 0 else "ERROR: second run got no frames")
    if n3 <= 0:
        return 1

    print("SUCCESS: VmbCameraWorker harness completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
