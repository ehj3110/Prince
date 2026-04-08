#!/usr/bin/env python3
"""Feature-selective test harness for Prince_Segmented_VideoPattern.

This runner exercises selected subsystems without requiring the user to
manually launch the production batch file. It reuses existing smoke tests and
adds small in-process checks for the modular seams touched by recent edits.

Available feature checks:
  - prince-core: validate Prince_Segmented_VideoPattern modular helper seams
  - logging: run the existing logging-related unit suites
  - display: exercise ProjectionFrameManager with a patched cv2 display path
  - stage: exercise the mock stage adapter + StageSequencer
  - dlp: exercise the mock light-engine adapter + DLPLightController
  - sensor: validate the stripped sensor window spoof path
  - modular-hw: run the modular stage/light smoke test
"""

from __future__ import annotations

import argparse
import contextlib
import queue
import subprocess
import sys
import tempfile
import time
import traceback
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

import numpy as np


ROOT = Path(__file__).resolve().parent.parent
TESTS_DIR = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))


_LAUNCH_SENSOR_WINDOW = False
_SENSOR_WINDOW_DURATION_S = 1.0


@dataclass(frozen=True)
class FeatureCheck:
    name: str
    description: str
    runner: Callable[[], str]


@dataclass
class FeatureResult:
    name: str
    passed: bool
    duration_s: float
    details: str
    skipped: bool = False


class _DummyLabel:
    def __init__(self) -> None:
        self.text = ""

    def config(self, **kwargs) -> None:
        if "text" in kwargs:
            self.text = str(kwargs["text"])


class _DummyFrameManager:
    def __init__(self) -> None:
        self.frames_shown = 0
        self.black_shown = 0

    def show_frame(self, _frame) -> None:
        self.frames_shown += 1

    def show_black(self) -> None:
        self.black_shown += 1


@contextlib.contextmanager
def _patched_cv2_display():
    import cv2

    original_imshow = cv2.imshow
    original_wait_key = cv2.waitKey
    calls = {"imshow": 0, "waitKey": 0}

    def fake_imshow(*_args, **_kwargs):
        calls["imshow"] += 1

    def fake_wait_key(_delay=0):
        calls["waitKey"] += 1
        return -1

    cv2.imshow = fake_imshow
    cv2.waitKey = fake_wait_key
    try:
        yield calls
    finally:
        cv2.imshow = original_imshow
        cv2.waitKey = original_wait_key


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _run_logging_suites() -> str:
    import run_all_tests

    suites = ["session"]
    skipped: list[str] = []

    try:
        import pandas  # noqa: F401
    except ImportError:
        skipped.append("peakforce")
    else:
        suites.append("peakforce")

    failures: list[str] = []

    for suite_name in suites:
        ok = run_all_tests.run_all_tests(verbose=False, specific_test=suite_name)
        if not ok:
            failures.append(suite_name)

    if failures:
        raise AssertionError(f"Logging-related suites failed: {', '.join(failures)}")

    if skipped:
        return f"session suite passed; {', '.join(skipped)} skipped because pandas is not installed"

    return "session and peakforce suites passed"


def _run_display_probe() -> str:
    from support_modules.ProjectionFrameManager import ProjectionFrameManager

    with _patched_cv2_display() as calls:
        black = np.zeros((12, 16, 3), dtype=np.uint8)
        frame = np.full((12, 16, 3), 255, dtype=np.uint8)
        manager = ProjectionFrameManager("prince-feature-display", black)
        manager.show_frame(frame)
        manager.show_black()

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            temp_path = Path(temp_file.name)

        try:
            import cv2

            written = cv2.imwrite(str(temp_path), frame)
            _require(written, "Failed to write temporary display probe image")
            _require(manager.show_from_path(str(temp_path)), "show_from_path returned False for a valid image")
        finally:
            temp_path.unlink(missing_ok=True)

        _require(calls["imshow"] >= 3, "Expected ProjectionFrameManager to call cv2.imshow")
        _require(calls["waitKey"] >= 3, "Expected ProjectionFrameManager to call cv2.waitKey")

    return "ProjectionFrameManager display path executed"


def _run_stage_probe() -> str:
    from support_modules.StageSequencer import StageSequencer
    from support_modules.hardware.stage.mock_stage_adapter import MockStageAdapter

    stage = MockStageAdapter()
    stage.connect()
    stage.home()
    sequencer = StageSequencer(stage)

    sequencer.move_continuous_to_target(
        target_um=1200.0,
        velocity_um_s=300.0,
        accel_um_s2=1000.0,
        wait_until_idle=True,
    )
    _require(abs(sequencer.get_position_um() - 1200.0) < 1e-9, "Stage did not reach 1200 um")

    sequencer.execute_stepped_peel_return(
        peel_peak_um=600.0,
        return_um=950.0,
        velocity_um_s=300.0,
        accel_um_s2=1000.0,
    )
    _require(abs(sequencer.get_position_um() - 950.0) < 1e-9, "Stage did not return to 950 um")

    sequencer.stop()
    stage.disconnect()
    _require(not stage.connected, "Mock stage should be disconnected")

    return "Mock stage adapter and StageSequencer executed"


def _run_dlp_probe() -> str:
    from support_modules.DLPLightController import DLPLightController
    from support_modules.hardware.light_engine.mock_light_engine_adapter import MockLightEngineAdapter

    light_engine = MockLightEngineAdapter()
    light_engine.connect()
    controller = DLPLightController(light_engine)

    controller.enter_dark_idle()
    _require(light_engine.mode == "dark_idle", "Expected dark_idle mode")
    _require(light_engine.last_power == 0, "Expected dark idle power 0")

    controller.arm_video_pattern_mode(silent_wake_power=35, settle_s=0.0, color_mask="100")
    _require(light_engine.mode == "video_pattern", "Expected video_pattern mode")
    _require(light_engine.last_power == 35, "Expected silent wake power 35")

    controller.set_exposure_power(80)
    _require(light_engine.last_power == 80, "Expected exposure power 80")

    controller.movement_blackout()
    _require(light_engine.last_power == 0, "Expected blackout power 0")

    controller.restore_next_layer_power(55)
    _require(light_engine.last_power == 55, "Expected restored power 55")

    controller.standby()
    _require(light_engine.mode == "standby", "Expected standby mode")
    light_engine.disconnect()
    _require(not light_engine.connected, "Mock light engine should be disconnected")

    return "Mock light-engine adapter and DLPLightController executed"


def _run_sensor_probe() -> str:
    import support_modules.SensorDataWindow_ExtendedWindow as sensor_window_mod
    import support_modules.test_sensor_window_extended_spoof as spoof_mod

    _require(hasattr(sensor_window_mod, "SensorDataWindow"), "SensorDataWindow class missing")
    _require(hasattr(spoof_mod, "FakeStageAxis"), "FakeStageAxis missing from spoof launcher")
    _require(hasattr(spoof_mod, "FakeForceGaugeManager"), "FakeForceGaugeManager missing from spoof launcher")

    stage = spoof_mod.FakeStageAxis()
    position = stage.get_position()
    _require(isinstance(position, (int, float)), "FakeStageAxis returned a non-numeric position")

    gain_label = _DummyLabel()
    offset_label = _DummyLabel()
    force_status_label = _DummyLabel()
    large_force_readout_label = _DummyLabel()
    output_force_queue: queue.Queue = queue.Queue(maxsize=64)

    manager = spoof_mod.FakeForceGaugeManager(
        gain_label=gain_label,
        offset_label=offset_label,
        force_status_label=force_status_label,
        large_force_readout_label=large_force_readout_label,
        output_force_queue=output_force_queue,
        parent_window=None,
        sensor_window_ref=None,
    )

    try:
        _require(manager.set_data_interval(25), "Expected set_data_interval to accept a positive value")
        manager.quick_calibrate_force_gauge()
        time.sleep(0.15)
    finally:
        manager.stop_force_reading_thread()

    _require(not output_force_queue.empty(), "Expected spoof force manager to emit at least one sample")
    _require(bool(force_status_label.text), "Expected spoof force manager to update status text")
    _require(bool(large_force_readout_label.text), "Expected spoof force manager to update large force text")

    if _LAUNCH_SENSOR_WINDOW:
        script_path = ROOT / "support_modules" / "test_sensor_window_extended_spoof.py"
        command = [sys.executable, str(script_path), "--duration", str(_SENSOR_WINDOW_DURATION_S)]
        completed = subprocess.run(command, capture_output=True, text=True)
        if completed.returncode != 0:
            raise AssertionError(
                "Sensor spoof window launch failed\n"
                f"stdout:\n{completed.stdout}\n"
                f"stderr:\n{completed.stderr}"
            )

    return "Sensor spoof path emitted samples and updated labels"


def _run_prince_core_probe() -> str:
    from support_modules.DLPLightController import DLPLightController
    from support_modules.hardware.light_engine.mock_light_engine_adapter import MockLightEngineAdapter

    def _install_phidget_stubs() -> dict[str, types.ModuleType]:
        created: dict[str, types.ModuleType] = {}

        def _add_module(name: str) -> types.ModuleType:
            module = types.ModuleType(name)
            sys.modules[name] = module
            created[name] = module
            return module

        phidget_root = _add_module("Phidget22")
        phidget_mod = _add_module("Phidget22.Phidget")
        devices_mod = _add_module("Phidget22.Devices")
        voltage_mod = _add_module("Phidget22.Devices.VoltageRatioInput")
        net_mod = _add_module("Phidget22.Net")
        exception_mod = _add_module("Phidget22.PhidgetException")
        error_mod = _add_module("Phidget22.ErrorCode")
        bridge_mod = _add_module("Phidget22.BridgeGain")
        pandas_mod = _add_module("pandas")
        scipy_root = _add_module("scipy")
        scipy_integrate = _add_module("scipy.integrate")
        scipy_signal = _add_module("scipy.signal")

        class _Phidget:
            pass

        class _VoltageRatioInput:
            pass

        class _PhidgetException(Exception):
            pass

        class _ErrorCode:
            pass

        class _BridgeGain:
            pass

        class _DataFrame:
            pass

        def _identity_filter(values, *args, **kwargs):
            return values

        phidget_root.__path__ = []
        devices_mod.__path__ = []
        scipy_root.__path__ = []
        phidget_mod.Phidget = _Phidget
        phidget_mod.__all__ = ["Phidget"]
        voltage_mod.VoltageRatioInput = _VoltageRatioInput
        voltage_mod.__all__ = ["VoltageRatioInput"]
        exception_mod.PhidgetException = _PhidgetException
        error_mod.ErrorCode = _ErrorCode
        bridge_mod.BridgeGain = _BridgeGain
        phidget_root.Phidget = _Phidget
        phidget_root.Devices = devices_mod
        devices_mod.VoltageRatioInput = _VoltageRatioInput
        net_mod.NetEnableServerDiscovery = lambda *_args, **_kwargs: None
        net_mod.NetAddServer = lambda *_args, **_kwargs: None
        pandas_mod.DataFrame = _DataFrame
        pandas_mod.Series = object
        pandas_mod.read_csv = lambda *_args, **_kwargs: None
        scipy_root.integrate = scipy_integrate
        scipy_root.signal = scipy_signal
        scipy_integrate.simps = lambda y, x=None, dx=1.0, axis=-1, even="avg": 0.0
        scipy_signal.savgol_filter = _identity_filter
        scipy_signal.medfilt = _identity_filter
        return created

    created_modules = _install_phidget_stubs()
    try:
        import Prince_Segmented_VideoPattern as prince
    finally:
        for module_name in created_modules:
            sys.modules.pop(module_name, None)

    required_attrs = (
        "MyWindow",
        "HardwareContext",
        "DLPLightController",
        "StageSequencer",
        "ProjectionFrameManager",
        "PrintOrchestrator",
        "PrintOrchestratorDeps",
    )
    missing = [name for name in required_attrs if not hasattr(prince, name)]
    _require(not missing, f"Prince module is missing expected attributes: {', '.join(missing)}")

    for method_name in ("_set_dlp_power", "_restore_next_layer_power", "_show_projection_frame", "_show_black_frame"):
        _require(callable(getattr(prince.MyWindow, method_name, None)), f"MyWindow missing callable {method_name}")

    dummy_window = prince.MyWindow.__new__(prince.MyWindow)
    dummy_window.use_modular_hardware_path = True
    dummy_window.controller = object()
    dummy_window.shadow_light_controller = DLPLightController(MockLightEngineAdapter())
    dummy_window.shadow_frame_manager = _DummyFrameManager()
    dummy_window.window_name = "prince-core-probe"
    dummy_window.black_image = np.zeros((8, 8, 3), dtype=np.uint8)

    dummy_window.shadow_light_controller.light_engine.connect()
    dummy_window._set_dlp_power(0)
    _require(dummy_window.shadow_light_controller.light_engine.last_power == 0, "Expected blackout power 0")

    dummy_window._set_dlp_power(77)
    _require(dummy_window.shadow_light_controller.light_engine.last_power == 77, "Expected exposure power 77")

    dummy_window._restore_next_layer_power(33)
    _require(dummy_window.shadow_light_controller.light_engine.last_power == 33, "Expected restored power 33")

    probe_frame = np.ones((8, 8, 3), dtype=np.uint8)
    dummy_window._show_projection_frame(probe_frame)
    dummy_window._show_black_frame()

    _require(dummy_window.shadow_frame_manager.frames_shown == 1, "Expected exactly one projection frame call")
    _require(dummy_window.shadow_frame_manager.black_shown == 1, "Expected exactly one black-frame call")

    return "Prince modular helper seams executed against mock adapters"


def _run_modular_smoke() -> str:
    import test_modular_stage_light_smoke

    test_modular_stage_light_smoke.run_smoke()
    return "Modular stage/light smoke test passed"


FEATURES: dict[str, FeatureCheck] = {
    "prince-core": FeatureCheck(
        name="prince-core",
        description="Validate the modular helper seams inside Prince_Segmented_VideoPattern.",
        runner=_run_prince_core_probe,
    ),
    "logging": FeatureCheck(
        name="logging",
        description="Run the existing logging-related unit suites.",
        runner=_run_logging_suites,
    ),
    "display": FeatureCheck(
        name="display",
        description="Exercise the projection frame manager with a patched display backend.",
        runner=_run_display_probe,
    ),
    "stage": FeatureCheck(
        name="stage",
        description="Exercise the mock stage adapter and StageSequencer.",
        runner=_run_stage_probe,
    ),
    "dlp": FeatureCheck(
        name="dlp",
        description="Exercise the mock light-engine adapter and DLPLightController.",
        runner=_run_dlp_probe,
    ),
    "sensor": FeatureCheck(
        name="sensor",
        description="Validate the stripped sensor window spoof path.",
        runner=_run_sensor_probe,
    ),
    "modular-hw": FeatureCheck(
        name="modular-hw",
        description="Run the modular stage/light smoke test.",
        runner=_run_modular_smoke,
    ),
}


def _select_features(args: argparse.Namespace) -> list[str]:
    selected = [name for name in FEATURES if getattr(args, name.replace("-", "_"), False)]
    if args.all or not selected:
        return list(FEATURES.keys())
    return selected


def _execute_feature(feature: FeatureCheck, verbose: bool) -> FeatureResult:
    start = time.time()
    try:
        details = feature.runner()
        duration_s = time.time() - start
        skipped = "skipped" in details.lower()
        return FeatureResult(feature.name, True, duration_s, details, skipped=skipped)
    except Exception as exc:
        duration_s = time.time() - start
        details = f"{exc.__class__.__name__}: {exc}"
        if verbose:
            details = f"{details}\n{traceback.format_exc()}"
        return FeatureResult(feature.name, False, duration_s, details)


def _print_header(selected: Iterable[str]) -> None:
    print("=" * 78)
    print("PRINCE FEATURE TEST HARNESS")
    print("=" * 78)
    print(f"Workspace root: {ROOT}")
    print(f"Selected features: {', '.join(selected)}")
    print()


def _print_summary(results: list[FeatureResult]) -> None:
    print()
    print("=" * 78)
    print("FEATURE TEST SUMMARY")
    print("=" * 78)
    for result in results:
        status = "SKIP" if result.skipped else ("PASS" if result.passed else "FAIL")
        print(f"[{status}] {result.name:<12} {result.duration_s:>7.3f}s  {result.details}")
    print("=" * 78)
    passed = sum(1 for result in results if result.passed)
    failed = len(results) - passed
    skipped = sum(1 for result in results if result.skipped)
    print(f"Passed: {passed}  Failed: {failed}  Skipped: {skipped}  Total: {len(results)}")
    print("=" * 78)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run feature-selective tests for Prince_Segmented_VideoPattern.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--all", action="store_true", help="Run all available feature checks.")
    parser.add_argument("--list", action="store_true", help="List available feature checks and exit.")
    parser.add_argument("--verbose", action="store_true", help="Show tracebacks for feature failures.")
    parser.add_argument("--prince-core", action="store_true", dest="prince_core", help="Run the Prince helper seam probe.")
    parser.add_argument("--logging", action="store_true", help="Run logging-related unit suites.")
    parser.add_argument("--display", action="store_true", help="Run the projection display probe.")
    parser.add_argument("--stage", action="store_true", help="Run the stage mock probe.")
    parser.add_argument("--dlp", action="store_true", help="Run the DLP mock probe.")
    parser.add_argument("--sensor", action="store_true", help="Run the sensor spoof probe.")
    parser.add_argument("--modular-hw", action="store_true", dest="modular_hw", help="Run the modular stage/light smoke test.")
    parser.add_argument("--launch-sensor-window", action="store_true", help="Launch the spoofed sensor window after the sensor probe passes.")
    parser.add_argument("--sensor-duration", type=float, default=1.0, help="Auto-close duration in seconds for the spoofed sensor window.")

    args = parser.parse_args()

    global _LAUNCH_SENSOR_WINDOW, _SENSOR_WINDOW_DURATION_S
    _LAUNCH_SENSOR_WINDOW = args.launch_sensor_window
    _SENSOR_WINDOW_DURATION_S = max(0.1, float(args.sensor_duration))

    if args.list:
        print("Available Prince feature checks:")
        for feature in FEATURES.values():
            print(f"  {feature.name:<12} - {feature.description}")
        return 0

    selected = _select_features(args)
    _print_header(selected)

    results = [_execute_feature(FEATURES[name], verbose=args.verbose) for name in selected]
    _print_summary(results)

    return 0 if all(result.passed for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())