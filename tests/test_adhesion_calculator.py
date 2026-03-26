"""
Mode-aware validation script for AdhesionMetricsCalculator.

Supports:
- modern mode: second-derivative zero-crossing propagation end
- legacy mode: two-step max-second-derivative + two-step baseline averaging
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from support_modules.adhesion_metrics_calculator import AdhesionMetricsCalculator


def _resolve_default_csv_path() -> str:
    """Resolve an existing CSV in this workspace for test execution."""
    workspace_root = Path(__file__).resolve().parent
    candidates = [
        workspace_root / "archive" / "autolog_L48.csv",
        workspace_root / "archive" / "autolog_L48-L50.csv",
        workspace_root / "autolog_L48.csv",
        workspace_root / "autolog_L48-L50.csv",
    ]
    for path in candidates:
        if path.exists():
            return str(path)

    raise FileNotFoundError(
        "Could not find a default autolog CSV. Provide one via --csv."
    )


def _build_calculator(mode: str) -> AdhesionMetricsCalculator:
    """Create calculator configured for modern or legacy comparison mode."""
    normalized = mode.lower()
    if normalized == "legacy":
        return AdhesionMetricsCalculator(
            prop_end_mode="two_step_max_second_derivative",
            baseline_mode="two_step",
            baseline_window_points=25,
            prop_end_local_window_seconds=1.0,
        )

    return AdhesionMetricsCalculator(
        prop_end_mode="second_derivative_zero_crossing",
        baseline_mode="prop_end_point",
    )


def test_with_real_data(mode: str = "modern", csv_path: str | None = None) -> bool:
    """Run end-to-end metric calculation for one CSV in the selected mode."""
    print("=" * 80)
    print(f"Testing AdhesionMetricsCalculator with real data (mode={mode})")
    print("=" * 80)

    print("\n1. Loading dataset...")
    csv_path = csv_path or _resolve_default_csv_path()
    data = pd.read_csv(csv_path)
    print(f"   Loaded {len(data)} data points from: {csv_path}")

    times = data["Elapsed Time (s)"].values
    positions = data["Position (mm)"].values
    forces = data["Force (N)"].values

    print("\n2. Data summary:")
    print(f"   Time range: {times[0]:.3f} to {times[-1]:.3f} seconds")
    print(f"   Position range: {positions.min():.3f} to {positions.max():.3f} mm")
    print(f"   Force range: {forces.min():.6f} to {forces.max():.6f} N")

    print("\n3. Initializing AdhesionMetricsCalculator...")
    calculator = _build_calculator(mode)

    print("\n4. Calling calculate_from_arrays()...")
    try:
        results = calculator.calculate_from_arrays(
            time_data=times,
            position_data=positions,
            force_data=forces,
            layer_number=48,
            motion_end_idx=len(times) - 1,
        )

        print("\n5. Results:")
        print("   SUCCESS! Metrics calculated.")
        print("\n   Key metrics:")
        print(f"   - Layer number: {results.get('layer_number', 'N/A')}")
        print(f"   - Peak force: {results.get('peak_force', 0.0):.6f} N")
        print(f"   - Peak force (corrected): {results.get('peak_force_corrected', 0.0):.6f} N")
        print(f"   - Baseline force: {results.get('baseline_force', 0.0):.6f} N")
        print(f"   - Peak force position: {results.get('peak_force_position', 0.0):.3f} mm")
        print(f"   - Peak force time: {results.get('peak_force_time', 0.0):.3f} s")

        print("\n   Propagation metrics:")
        print(f"   - Propagation end position: {results.get('propagation_end_position', 0.0):.3f} mm")
        print(f"   - Propagation end time: {results.get('propagation_end_time', 0.0):.3f} s")
        print(f"   - Propagation distance: {results.get('propagation_distance', 0.0):.6f} mm")
        print(f"   - Propagation duration: {results.get('propagation_duration', 0.0):.3f} s")

        print("\n" + "=" * 80)
        print("TEST PASSED: All metrics calculated successfully!")
        print("=" * 80)
        return True

    except Exception as e:
        print(f"\n   ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

        print("\n" + "=" * 80)
        print("TEST FAILED")
        print("=" * 80)
        return False


def test_internal_methods(mode: str = "modern", csv_path: str | None = None) -> None:
    """Smoke-test mode-dependent internal methods."""
    print("\n" + "=" * 80)
    print(f"Testing internal calculator methods (mode={mode})")
    print("=" * 80)

    csv_path = csv_path or _resolve_default_csv_path()
    data = pd.read_csv(csv_path)

    times = data["Elapsed Time (s)"].values
    positions = data["Position (mm)"].values
    forces = data["Force (N)"].values

    calculator = _build_calculator(mode)

    print("\n1. Testing force smoothing...")
    smoothed = calculator._apply_smoothing(forces)
    print(f"   Original force range: {forces.min():.6f} to {forces.max():.6f} N")
    print(f"   Smoothed force range: {smoothed.min():.6f} to {smoothed.max():.6f} N")

    print("\n2. Testing peak force detection...")
    peak_idx, peak_force = calculator._find_peak_force(smoothed)
    print(f"   Peak index: {peak_idx}")
    print(f"   Peak force: {peak_force:.6f} N")

    print("\n3. Testing baseline calculation...")
    mode_name = str(getattr(calculator, "prop_end_mode", "second_derivative_zero_crossing")).lower()
    if mode_name == "two_step_max_second_derivative":
        prop_end_idx = calculator._find_propagation_end_two_step_max_second_derivative(
            times, smoothed, peak_idx, len(times) - 1
        )
    elif mode_name == "second_derivative_zero_crossing_unsmoothed":
        prop_end_idx = calculator._find_propagation_end_second_derivative_zero_crossing_unsmoothed(
            smoothed, peak_idx, len(times) - 1
        )
    else:
        prop_end_idx = calculator._find_propagation_end_second_derivative_zero_crossing(
            smoothed, peak_idx, len(times) - 1
        )

    baseline = calculator._calculate_baseline(smoothed, prop_end_idx)
    print(f"   Propagation end index: {prop_end_idx}")
    print(f"   Baseline: {baseline:.6f} N")

    print("\n" + "=" * 80)
    print("Internal methods test complete")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run AdhesionMetricsCalculator validation.")
    parser.add_argument(
        "--mode",
        choices=["modern", "legacy"],
        default="modern",
        help="modern=zero crossing; legacy=two-step max second derivative",
    )
    parser.add_argument(
        "--csv",
        default=None,
        help="Optional path to autolog CSV; defaults to local workspace candidate files",
    )
    args = parser.parse_args()

    print("\n" + "=" * 80)
    print("ADHESION CALCULATOR TEST SUITE")
    print("Purpose: Validate modern and legacy propagation/baseline modes")
    print("=" * 80)

    success = test_with_real_data(mode=args.mode, csv_path=args.csv)
    if success:
        test_internal_methods(mode=args.mode, csv_path=args.csv)

    print("\n" + "=" * 80)
    print("TEST SUITE COMPLETE")
    print("=" * 80)
