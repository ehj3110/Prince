#!/usr/bin/env python3
"""Rush-specific hardware checklist runner.

This script performs safe, staged hardware checks for:
- DLP connection and safe idle transition
- A3200 stage connection (optional motion probe)
- Phidget force-gauge attachment

It is designed for the Rush_Segmented_VideoPattern environment and avoids
changing root project dependencies or files.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
import time
import traceback
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Callable, Optional


@dataclass
class CheckResult:
    name: str
    passed: bool
    details: str
    duration_s: float


def _run_check(name: str, fn: Callable[[], str]) -> CheckResult:
    start = time.time()
    try:
        details = fn()
        return CheckResult(name=name, passed=True, details=details, duration_s=time.time() - start)
    except Exception as exc:  # noqa: BLE001
        short = f"{type(exc).__name__}: {exc}"
        tb = traceback.format_exc(limit=3)
        return CheckResult(name=name, passed=False, details=f"{short}\n{tb}", duration_s=time.time() - start)


def _insert_rush_root(rush_root: Path) -> None:
    if str(rush_root) not in sys.path:
        sys.path.insert(0, str(rush_root))


def _check_imports(rush_root: Path) -> str:
    _insert_rush_root(rush_root)
    required = [
        "Rush_Segmented_VideoPattern",
        "support_modules.pycrafter9000",
        "support_modules.hardware.stage.a3200_stage_adapter",
        "support_modules.motion_controller",
        "support_modules.StageSequencer",
        "support_modules.DLPLightController",
    ]
    missing = []
    for mod in required:
        try:
            importlib.import_module(mod)
        except Exception:
            missing.append(mod)
    if missing:
        raise RuntimeError("Missing imports: " + ", ".join(missing))
    return "All Rush modules import successfully"


def _check_dlp(rush_root: Path) -> str:
    _insert_rush_root(rush_root)
    pycrafter9000 = importlib.import_module("support_modules.pycrafter9000")

    dmd = pycrafter9000.dmd()
    snapshot_before = None
    snapshot_after = None

    if hasattr(dmd, "get_status_snapshot"):
        try:
            snapshot_before = dmd.get_status_snapshot()
        except Exception:
            snapshot_before = "unavailable"

    # Safe sequence: stop -> power off -> video idle.
    dmd.stopsequence()
    time.sleep(0.05)
    dmd.power(current=0)
    time.sleep(0.05)
    dmd.changemode(0x03)
    time.sleep(0.05)

    if hasattr(dmd, "get_status_snapshot"):
        try:
            snapshot_after = dmd.get_status_snapshot()
        except Exception:
            snapshot_after = "unavailable"

    return f"DLP reachable; safe idle command sequence completed; before={snapshot_before}; after={snapshot_after}"


def _check_stage(rush_root: Path, host: str, port: int, axis_name: str, enable_motion: bool, motion_um: float) -> str:
    _insert_rush_root(rush_root)
    stage_mod = importlib.import_module("support_modules.hardware.stage.a3200_stage_adapter")
    adapter_cls = getattr(stage_mod, "A3200StageAdapter")

    stage = adapter_cls(host=host, port=port, axis_name=axis_name)
    stage.connect()
    try:
        position_before_um = float(stage.get_position_um())
        position_after_um = position_before_um

        if enable_motion:
            stage.move_relative_um(motion_um, velocity_um_s=300.0, wait_until_idle=True)
            stage.move_relative_um(-motion_um, velocity_um_s=300.0, wait_until_idle=True)
            position_after_um = float(stage.get_position_um())

        if enable_motion:
            return (
                "Stage connected; non-destructive motion probe completed "
                f"(start={position_before_um:.3f}um, end={position_after_um:.3f}um)"
            )
        return f"Stage connected; position read OK at {position_before_um:.3f}um (motion disabled)"
    finally:
        stage.disconnect()


def _check_phidget(channel: int, timeout_ms: int) -> str:
    from Phidget22.Devices.VoltageRatioInput import VoltageRatioInput

    vri = VoltageRatioInput()
    vri.setHubPort(-1)
    vri.setChannel(channel)
    vri.openWaitForAttachment(timeout_ms)
    try:
        try:
            ratio = vri.getVoltageRatio()
        except Exception:
            ratio = "n/a"
        return f"Phidget attached on channel {channel}; voltage ratio sample={ratio}"
    finally:
        vri.close()


def _print_manual_checklist() -> None:
    lines = [
        "Manual GUI checklist:",
        "1. Launch Rush_Segmented_VideoPattern.py and confirm 'System Ready'.",
        "2. Open Sensor Panel (Logging), verify force readout updates, then close panel.",
        "3. Open Image Modification window and load a test image folder.",
        "4. Use stage controls for a tiny jog up/down and verify position readback.",
        "5. Trigger DLP dark-idle then arm sequence through normal workflow.",
        "6. Confirm graceful shutdown resets DLP power to 0 and closes stage session.",
    ]
    print("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Rush-specific hardware checklist")
    parser.add_argument(
        "--rush-root",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "Rush_Segmented_VideoPattern",
        help="Path to Rush_Segmented_VideoPattern folder",
    )
    parser.add_argument("--skip-imports", action="store_true", help="Skip module import checks")
    parser.add_argument("--skip-dlp", action="store_true", help="Skip DLP check")
    parser.add_argument("--skip-stage", action="store_true", help="Skip stage check")
    parser.add_argument("--skip-phidget", action="store_true", help="Skip Phidget check")
    parser.add_argument("--enable-motion", action="store_true", help="Enable tiny stage motion probe")
    parser.add_argument("--motion-um", type=float, default=50.0, help="Stage motion distance in um (for probe)")
    parser.add_argument("--stage-host", default="localhost", help="A3200 host")
    parser.add_argument("--stage-port", type=int, default=8000, help="A3200 port")
    parser.add_argument("--stage-axis", default="Z", help="A3200 axis name")
    parser.add_argument("--phidget-channel", type=int, default=0, help="Phidget channel")
    parser.add_argument("--phidget-timeout-ms", type=int, default=8000, help="Phidget attach timeout")
    parser.add_argument("--json-out", type=Path, default=None, help="Optional JSON output path")
    parser.add_argument("--plan-only", action="store_true", help="Only print manual checklist; no hardware calls")
    args = parser.parse_args()

    rush_root = args.rush_root.resolve()
    if not rush_root.exists():
        print(f"ERROR: rush root does not exist: {rush_root}")
        return 2

    if args.plan_only:
        print(f"Rush root: {rush_root}")
        _print_manual_checklist()
        return 0

    checks: list[CheckResult] = []

    if not args.skip_imports:
        checks.append(_run_check("imports", lambda: _check_imports(rush_root)))
    if not args.skip_dlp:
        checks.append(_run_check("dlp", lambda: _check_dlp(rush_root)))
    if not args.skip_stage:
        checks.append(
            _run_check(
                "stage",
                lambda: _check_stage(
                    rush_root,
                    host=args.stage_host,
                    port=args.stage_port,
                    axis_name=args.stage_axis,
                    enable_motion=args.enable_motion,
                    motion_um=args.motion_um,
                ),
            )
        )
    if not args.skip_phidget:
        checks.append(_run_check("phidget", lambda: _check_phidget(args.phidget_channel, args.phidget_timeout_ms)))

    print("Rush hardware checklist results")
    print("=" * 36)
    failures = 0
    for result in checks:
        status = "PASS" if result.passed else "FAIL"
        print(f"[{status}] {result.name} ({result.duration_s:.2f}s)")
        print(f"  {result.details}")
        if not result.passed:
            failures += 1

    _print_manual_checklist()

    if args.json_out is not None:
        payload = {
            "rush_root": str(rush_root),
            "checks": [asdict(item) for item in checks],
            "failures": failures,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"\nWrote report: {args.json_out}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
