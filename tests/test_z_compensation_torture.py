"""Z-compensation torture test suite.

Standalone stress and correctness checks for support_modules/z_compensation.py.

Usage examples:
    c:/Users/cheng sun/BoyuanSun/Prince_CurrentWorkingVersion/.conda/python.exe tests/test_z_compensation_torture.py
    c:/Users/cheng sun/BoyuanSun/Prince_CurrentWorkingVersion/.conda/python.exe tests/test_z_compensation_torture.py --z 224 --height 1024 --width 1024
"""

from __future__ import annotations

import argparse
import tempfile
import time
from pathlib import Path
import sys

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from support_modules.z_compensation import (
    ZCompensationConfig,
    attenuation_per_layer,
    compute_layer_factors,
    estimate_stack_memory,
    format_bytes,
    per_layer_dose_schedule,
    solve_exposure_volume_backward,
)


def _forward_total_dose_1d(exposure_1d: np.ndarray, attenuation: float) -> np.ndarray:
    total = np.zeros_like(exposure_1d, dtype=np.float64)
    total[-1] = exposure_1d[-1]
    for k in range(exposure_1d.size - 2, -1, -1):
        total[k] = exposure_1d[k] + attenuation * total[k + 1]
    return total


def _assert(name: str, condition: bool) -> None:
    if not condition:
        raise AssertionError(name)


def test_layer_factors_random(random_cases: int = 25) -> None:
    rng = np.random.default_rng(42)
    for _ in range(random_cases):
        n = int(rng.integers(2, 400))
        h = float(rng.uniform(5.0, 120.0))
        dp = float(rng.uniform(20.0, 250.0))
        strength = float(rng.uniform(0.0, 1.0))
        min_factor = float(rng.uniform(0.05, 0.7))
        factors = compute_layer_factors(n, h, dp, strength, min_factor)

        _assert("factor_length", len(factors) == n)
        _assert("factor_bounds", all(min_factor - 1e-9 <= f <= 1.0 + 1e-9 for f in factors))
        _assert("last_layer_factor", abs(factors[-1] - 1.0) < 1e-6)


def test_schedule_consistency() -> None:
    n = 120
    h = 50.0
    dp = 120.0
    d_target = 1.0
    attenuation = attenuation_per_layer(h, dp)
    schedule = per_layer_dose_schedule(n, h, dp, d_target)
    total = _forward_total_dose_1d(schedule, attenuation)
    max_err = float(np.max(np.abs(total - d_target)))
    _assert("schedule_forward_consistency", max_err < 1e-5)


def test_volume_solver_small_random() -> None:
    rng = np.random.default_rng(7)
    z, y, x = 28, 96, 80
    mask = (rng.random((z, y, x)) > 0.55).astype(np.uint8)

    cfg = ZCompensationConfig(
        layer_thickness_um=50.0,
        penetration_depth_um=120.0,
        target_dose=1.0,
        work_dtype=np.float32,
    )
    exposure = solve_exposure_volume_backward(mask, cfg)
    _assert("nonnegative_exposure", bool(np.all(exposure >= -1e-7)))

    # Validate one representative pixel trace for correctness.
    py, px = y // 2, x // 2
    attenuation = attenuation_per_layer(cfg.layer_thickness_um, cfg.penetration_depth_um)
    trace = exposure[:, py, px].astype(np.float64)
    active_trace = (mask[:, py, px] > 0)
    target_trace = active_trace.astype(np.float64) * float(cfg.target_dose)
    total_trace = _forward_total_dose_1d(trace, attenuation)
    if np.any(active_trace):
        err = float(np.max(np.abs(total_trace[active_trace] - target_trace[active_trace])))
    else:
        err = 0.0
    _assert("single_trace_reconstruction", err < 2e-4)


def test_memmap_roundtrip() -> None:
    z, y, x = 16, 64, 64
    mask = np.ones((z, y, x), dtype=np.uint8)
    cfg = ZCompensationConfig(layer_thickness_um=50.0, penetration_depth_um=120.0)

    with tempfile.TemporaryDirectory() as td:
        out_path = str(Path(td) / "z_torture_exposure.mmap")
        exposure = solve_exposure_volume_backward(mask, cfg, out_path=out_path)
        _assert("memmap_shape", exposure.shape == (z, y, x))
        _assert("memmap_dtype", exposure.dtype == np.float32)
        _assert("memmap_finite", bool(np.isfinite(exposure).all()))
        exposure.flush()
        del exposure


def test_heavy_memmap(z: int, height: int, width: int) -> None:
    # Heavy case uses all-ones mask to maximize signal path depth and stress I/O.
    mask = np.ones((z, height, width), dtype=np.uint8)
    cfg = ZCompensationConfig(layer_thickness_um=50.0, penetration_depth_um=120.0)

    mem_est = estimate_stack_memory(z, height, width)
    print(f"[heavy] estimated exposure stack: {format_bytes(mem_est['exposure_stack_bytes'])}")
    print(f"[heavy] estimated mask stack: {format_bytes(mem_est['mask_stack_bytes'])}")

    with tempfile.TemporaryDirectory() as td:
        out_path = str(Path(td) / "z_heavy_exposure.mmap")
        t0 = time.perf_counter()
        exposure = solve_exposure_volume_backward(mask, cfg, out_path=out_path)
        elapsed = time.perf_counter() - t0
        print(f"[heavy] solve time: {elapsed:.2f}s")
        _assert("heavy_finite", bool(np.isfinite(exposure).all()))
        _assert("heavy_nonnegative", bool(np.all(exposure >= -1e-7)))

        # Verify trend on a representative voxel trace.
        trace = exposure[:, 0, 0].astype(np.float64)
        _assert("heavy_trace_top_down", bool(trace[0] <= trace[-1] + 1e-6))
        exposure.flush()
        del exposure


def main() -> int:
    parser = argparse.ArgumentParser(description="Torture test for Z compensation module")
    parser.add_argument("--z", type=int, default=160, help="Heavy test layer count")
    parser.add_argument("--height", type=int, default=1024, help="Heavy test height")
    parser.add_argument("--width", type=int, default=1024, help="Heavy test width")
    parser.add_argument("--random-cases", type=int, default=25, help="Randomized layer-factor cases")
    args = parser.parse_args()

    print("[1/5] layer-factor randomized checks")
    test_layer_factors_random(args.random_cases)

    print("[2/5] schedule consistency checks")
    test_schedule_consistency()

    print("[3/5] volume solver small-random checks")
    test_volume_solver_small_random()

    print("[4/5] memmap roundtrip checks")
    test_memmap_roundtrip()

    print("[5/5] heavy memmap torture run")
    test_heavy_memmap(args.z, args.height, args.width)

    print("PASS: all z_compensation torture checks completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
