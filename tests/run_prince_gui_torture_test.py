#!/usr/bin/env python3
"""Automated GUI torture test for Prince_Segmented_VideoPattern.

This script launches the real Prince GUI class with fake hardware backends so
we can verify the startup path, instruction-file parsing, sensor panel flow,
and a short 5-layer print run without needing live stage/DLP/force hardware.
"""

from __future__ import annotations

import argparse
import math
import os
import queue
import sys
import tempfile
import threading
import time
import types
from pathlib import Path

import cv2
import numpy as np
import tkinter as tk
from tkinter import messagebox

from projection_presence_checker import ProjectionPresenceChecker


ROOT = Path(__file__).resolve().parent.parent
TESTS_DIR = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))


class _Monitor:
    def __init__(self, width=1280, height=720, x=0, y=0, is_primary=True):
        self.width = width
        self.height = height
        self.x = x
        self.y = y
        self.is_primary = is_primary


class _FakeSettings:
    def __init__(self):
        self._values = {"accel": 100000}

    def get(self, name, unit=None):
        return self._values.get(name, 0)

    def set(self, name, value, unit=None):
        self._values[name] = value


class _FakeWarnings:
    def get_flags(self):
        return 0


class _FakeAxis:
    def __init__(self):
        self.position_um = 0.0
        self.settings = _FakeSettings()
        self.warnings = _FakeWarnings()
        self.move_absolute_calls: list[tuple] = []
        self.move_relative_calls: list[tuple] = []

    def home(self, wait_until_idle=True):
        self.position_um = 0.0

    def get_position(self, unit=None):
        if unit is None:
            return self.position_um
        if getattr(unit, "name", "") == "LENGTH_MILLIMETRES" or str(unit).endswith("LENGTH_MILLIMETRES"):
            return self.position_um / 1000.0
        return self.position_um

    def move_absolute(self, *args, **kwargs):
        position = kwargs.get("position", args[0] if args else 0.0)
        unit = kwargs.get("unit")
        if getattr(unit, "name", "") == "LENGTH_MILLIMETRES" or str(unit).endswith("LENGTH_MILLIMETRES"):
            self.position_um = float(position) * 1000.0
        else:
            self.position_um = float(position)
        self.move_absolute_calls.append((args, kwargs, self.position_um))

    def move_relative(self, *args, **kwargs):
        position = kwargs.get("position", args[0] if args else 0.0)
        unit = kwargs.get("unit")
        if getattr(unit, "name", "") == "LENGTH_MILLIMETRES" or str(unit).endswith("LENGTH_MILLIMETRES"):
            delta_um = float(position) * 1000.0
        else:
            delta_um = float(position)
        self.position_um += delta_um
        self.move_relative_calls.append((args, kwargs, self.position_um))

    def wait_until_idle(self):
        return None

    def stop(self):
        return None

    def is_busy(self):
        return False


class _FakeDevice:
    def __init__(self, axis):
        self.name = "Fake Zaber Device"
        self._axis = axis

    def get_axis(self, index):
        return self._axis


class _FakeConnection:
    def __init__(self, axis):
        self._axis = axis

    def detect_devices(self):
        return [_FakeDevice(self._axis)]

    def close(self):
        return None


class _FakeController:
    def __init__(self):
        self.calls: list[tuple] = []
        self.power_level = 0
        self.mode = 0x03
        self.input_source = 0
        self.sequence_state = 0

    def power(self, current=0):
        self.power_level = int(current)
        self.calls.append(("power", self.power_level))

    def stopsequence(self):
        self.sequence_state = 0
        self.calls.append(("stopsequence",))

    def changemode(self, mode):
        self.mode = mode
        self.calls.append(("changemode", mode))

    def hdmi(self):
        self.input_source = 1
        self.calls.append(("hdmi",))

    def configurelut(self, *args, **kwargs):
        self.calls.append(("configurelut", args, kwargs))

    def definepattern(self, *args, **kwargs):
        self.calls.append(("definepattern", args, kwargs))

    def startsequence(self):
        self.sequence_state = 2
        self.calls.append(("startsequence",))

    def standby(self):
        self.calls.append(("standby",))

    def get_display_mode(self):
        return self.mode

    def get_input_source(self):
        return self.input_source

    def get_sequence_state(self):
        return self.sequence_state

    def get_led_current(self):
        return self.power_level

    def get_status_snapshot(self):
        return {
            "mode": self.get_display_mode(),
            "input_source": self.get_input_source(),
            "sequence_state": self.get_sequence_state(),
            "led_current": self.get_led_current(),
        }

    def display_static_pattern(self, *args, **kwargs):
        self.calls.append(("display_static_pattern", args, kwargs))


class _FakeVoltageRatioInput:
    def __init__(self, manager):
        self._manager = manager

    def getAttached(self):
        return True

    def getVoltageRatio(self):
        return self._manager.OFFSET + (self._manager._current_force_n / self._manager.GAIN)


class _FakeForceGaugeManager:
    def __init__(self, gain_label, offset_label, force_status_label, large_force_readout_label,
                 output_force_queue, parent_window, sensor_window_ref):
        self.gain_label = gain_label
        self.offset_label = offset_label
        self.force_status_label = force_status_label
        self.large_force_readout_label = large_force_readout_label
        self.output_force_queue = output_force_queue
        self.parent_window = parent_window
        self.sensor_window_ref = sensor_window_ref
        self.GAIN = 0.001
        self.OFFSET = 0.0
        self._calibrated = True
        self._current_force_n = 0.0
        self._interval_s = 0.05
        self._t0 = time.time()
        self._stop_event = threading.Event()
        self._thread = None
        self.voltage_ratio_input = _FakeVoltageRatioInput(self)
        self.gain_label.config(text=f"Gain: {self.GAIN:.6f}")
        self.offset_label.config(text=f"Offset: {self.OFFSET:.6f}")
        self._start_force_thread()

    def _start_force_thread(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        while not self._stop_event.is_set():
            t = time.time() - self._t0
            self._current_force_n = 0.05 * math.sin(2.0 * math.pi * 0.7 * t) + 0.15 * math.sin(2.0 * math.pi * 0.11 * t)
            try:
                self.force_status_label.config(text=f"Force: {self._current_force_n:+.4f} N")
                self.large_force_readout_label.config(text=f"Force: {self._current_force_n:+.4f} N")
                self.output_force_queue.put_nowait(("force", self._current_force_n))
            except queue.Full:
                pass
            except Exception:
                break
            time.sleep(self._interval_s)

    def set_data_interval(self, interval_ms):
        try:
            self._interval_s = max(0.001, float(interval_ms) / 1000.0)
            return True
        except Exception:
            return False

    def quick_calibrate_force_gauge(self):
        self._calibrated = True
        self.force_status_label.config(text="Force: CALIBRATED")

    def calibrate_force_gauge(self):
        self._calibrated = True
        self.force_status_label.config(text="Force: CALIBRATED")

    def is_calibrated(self):
        return self._calibrated

    def get_latest_calibrated_force(self):
        return self._current_force_n

    def stop_force_reading_thread(self):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)


def _install_stubs() -> None:
    # Avoid blocking modal dialogs during automated runs.
    messagebox.showerror = lambda *args, **kwargs: print(f"[MESSAGEBOX:error] {args[:2]}")
    messagebox.showwarning = lambda *args, **kwargs: print(f"[MESSAGEBOX:warning] {args[:2]}")
    messagebox.showinfo = lambda *args, **kwargs: print(f"[MESSAGEBOX:info] {args[:2]}")

    # Keep OpenCV window calls from requiring a real projector window during the test.
    cv2.namedWindow = lambda *args, **kwargs: None
    cv2.moveWindow = lambda *args, **kwargs: None
    cv2.setWindowProperty = lambda *args, **kwargs: None
    cv2.imshow = lambda *args, **kwargs: None
    cv2.waitKey = lambda *args, **kwargs: -1
    cv2.destroyWindow = lambda *args, **kwargs: None
    cv2.destroyAllWindows = lambda *args, **kwargs: None

    # Minimal screeninfo stub.
    screeninfo = types.ModuleType("screeninfo")
    screeninfo.get_monitors = lambda: [_Monitor()]
    sys.modules["screeninfo"] = screeninfo

    # Minimal zaber_motion stub.
    zaber_motion = types.ModuleType("zaber_motion")

    class _Units:
        LENGTH_MILLIMETRES = "LENGTH_MILLIMETRES"
        LENGTH_MICROMETRES = "LENGTH_MICROMETRES"
        VELOCITY_MILLIMETRES_PER_SECOND = "VELOCITY_MILLIMETRES_PER_SECOND"
        VELOCITY_MICROMETRES_PER_SECOND = "VELOCITY_MICROMETRES_PER_SECOND"
        ACCELERATION_MICROMETRES_PER_SECOND_SQUARED = "ACCELERATION_MICROMETRES_PER_SECOND_SQUARED"
        ACCELERATION_MILLIMETRES_PER_SECOND_SQUARED = "ACCELERATION_MILLIMETRES_PER_SECOND_SQUARED"

    class _Library:
        @staticmethod
        def enable_device_db_store():
            return None

    zaber_motion.Library = _Library
    zaber_motion.Units = _Units
    zaber_motion.__path__ = []
    sys.modules["zaber_motion"] = zaber_motion

    zaber_ascii = types.ModuleType("zaber_motion.ascii")
    _shared_axis = _FakeAxis()
    zaber_ascii.Connection = types.SimpleNamespace(open_serial_port=lambda *_args, **_kwargs: _FakeConnection(_shared_axis))
    sys.modules["zaber_motion.ascii"] = zaber_ascii

    zaber_exceptions = types.ModuleType("zaber_motion.exceptions")

    class _MovementFailedException(Exception):
        pass

    zaber_exceptions.MovementFailedException = _MovementFailedException
    sys.modules["zaber_motion.exceptions"] = zaber_exceptions

    # Top-level project imports used by the GUI.
    pycrafter9000 = types.ModuleType("pycrafter9000")
    pycrafter9000.dmd = lambda: _FakeController()
    sys.modules["pycrafter9000"] = pycrafter9000

    # Force-gauge backend used by SensorDataWindow.
    force_gauge_module = types.ModuleType("ForceGaugeManager")
    force_gauge_module.ForceGaugeManager = _FakeForceGaugeManager
    sys.modules["ForceGaugeManager"] = force_gauge_module

    # Optional analytics dependencies used during import by PeakForceLogger.
    pandas = types.ModuleType("pandas")
    pandas.DataFrame = type("DataFrame", (), {})
    pandas.Series = object
    pandas.read_csv = lambda *args, **kwargs: None
    sys.modules["pandas"] = pandas

    scipy = types.ModuleType("scipy")
    scipy.__path__ = []
    scipy_integrate = types.ModuleType("scipy.integrate")
    scipy_integrate.simps = lambda y, x=None, dx=1.0, axis=-1, even="avg": 0.0
    scipy_signal = types.ModuleType("scipy.signal")
    scipy_signal.savgol_filter = lambda values, *args, **kwargs: values
    scipy_signal.medfilt = lambda values, *args, **kwargs: values
    scipy.integrate = scipy_integrate
    scipy.signal = scipy_signal
    sys.modules["scipy"] = scipy
    sys.modules["scipy.integrate"] = scipy_integrate
    sys.modules["scipy.signal"] = scipy_signal

    # Phidget22 is imported by the legacy force-gauge module path.
    phidget_root = types.ModuleType("Phidget22")
    phidget_root.__path__ = []
    sys.modules["Phidget22"] = phidget_root
    for module_name in ["Phidget", "Net", "ErrorCode", "BridgeGain", "PhidgetException", "Devices", "Devices.VoltageRatioInput"]:
        full_name = f"Phidget22.{module_name}"
        module = types.ModuleType(full_name)
        sys.modules[full_name] = module


def _wait_until(predicate, timeout_s=10.0, poll_s=0.05, root=None, label="condition"):
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if predicate():
            return True
        if root is not None:
            try:
                root.update()
            except tk.TclError:
                break
        time.sleep(poll_s)
    raise TimeoutError(f"Timed out waiting for {label}")


def _write_test_images(image_dir: Path) -> None:
    image_dir.mkdir(parents=True, exist_ok=True)
    for index in range(5):
        image = np.zeros((1600, 2560), dtype=np.uint8)
        cv2.putText(
            image,
            f"Layer {index + 1}",
            (200, 800),
            cv2.FONT_HERSHEY_SIMPLEX,
            4,
            255,
            8,
        )
        cv2.circle(image, (1280, 800), 120 + index * 25, 255, -1)
        cv2.imwrite(str(image_dir / f"{index}.png"), image)


def _configure_entries(window, *, thickness, exposure, dlp_power, step_speed, overstep, accel, pause, sandwich_speed):
    entries = {
        window.t10: thickness,
        window.t11: exposure,
        window.t14: dlp_power,
        window.t16: step_speed,
        window.t19: overstep,
        window.t21: accel,
        window.t17: pause,
        window.t_sandwich_speed: sandwich_speed,
    }
    for entry, value in entries.items():
        entry.delete(0, tk.END)
        entry.insert(0, str(value))


def _run_instruction_torture(window, image_dir: Path) -> None:
    print("[1/4] Instruction-file torture test")
    window.t1.delete(0, tk.END)
    window.t1.insert(0, str(image_dir))

    _configure_entries(
        window,
        thickness="three",
        exposure="0",
        dlp_power="-5",
        step_speed="0.0",
        overstep="0",
        accel="-5",
        pause="0",
        sandwich_speed="three",
    )

    window.simple_txt()
    if window.image_list:
        raise RuntimeError("Malformed instruction file should not have loaded image data")
    print("  malformed instruction file was rejected as expected")

    _configure_entries(
        window,
        thickness=5,
        exposure=0.2,
        dlp_power=50,
        step_speed=1000,
        overstep=500,
        accel=5.0,
        pause=0.0,
        sandwich_speed=500,
    )

    window.simple_txt()
    if len(window.image_list) != 5:
        raise RuntimeError(f"Expected 5 loaded layers, got {len(window.image_list)}")
    print("  valid instruction file loaded 5 layers")


def _run_sensor_window_test(window, root) -> None:
    print("[2/4] Sensor data window calibration and 10-point logging")
    window.open_sensor_panel()
    sensor_window = window.sensor_data_window_instance
    if sensor_window is None:
        raise RuntimeError("Sensor window did not open")

    sensor_window.start_live_readout()
    sensor_window.force_gauge_manager.quick_calibrate_force_gauge()

    _wait_until(
        lambda: len(sensor_window.plot_data_x) >= 10,
        timeout_s=12.0,
        poll_s=0.05,
        root=root,
        label="10 sensor points",
    )

    print(f"  logged {len(sensor_window.plot_data_x)} point(s)")
    sensor_window.stop_live_readout()
    sensor_window.on_sensor_window_close()


def _controller_status_snapshot(controller) -> dict:
    if controller is None:
        return {}
    if hasattr(controller, "get_status_snapshot"):
        try:
            snapshot = controller.get_status_snapshot()
            if isinstance(snapshot, dict):
                return snapshot
        except Exception:
            pass

    status = {}
    for getter_name, key in [
        ("get_display_mode", "mode"),
        ("get_input_source", "input_source"),
        ("get_sequence_state", "sequence_state"),
        ("get_led_current", "led_current"),
    ]:
        if hasattr(controller, getter_name):
            try:
                status[key] = int(getattr(controller, getter_name)())
            except Exception:
                status[key] = None

    if not status and hasattr(controller, "mode"):
        status["mode"] = int(getattr(controller, "mode"))
    if "led_current" not in status and hasattr(controller, "power_level"):
        status["led_current"] = int(getattr(controller, "power_level"))
    return status


def _validate_dlp_arm_state(status: dict) -> None:
    mode = status.get("mode")
    sequence_state = status.get("sequence_state")
    led_current = status.get("led_current")

    if mode is None:
        raise RuntimeError("DLP mode readback unavailable")
    if int(mode) != 0x02:
        raise RuntimeError(f"Expected DLP mode 0x02 after arming, got {mode}")

    if sequence_state is not None and int(sequence_state) != 2:
        raise RuntimeError(f"Expected sequence_state=2 after arming, got {sequence_state}")

    if led_current is not None and int(led_current) <= 0:
        raise RuntimeError(f"Expected LED current > 0 after arming, got {led_current}")


def _run_projection_verification(window, args) -> None:
    print("[3/4] DLP mode and projection verification")
    controller = getattr(window, "controller", None)
    if controller is None:
        raise RuntimeError("No DLP controller attached")

    # Enter known dark idle then arm with the production wake sequence.
    window._enter_dark_pattern_idle()
    window._arm_dlp_silent_wakeup()

    status_after_arm = _controller_status_snapshot(controller)
    print(f"  DLP status after arm: {status_after_arm}")
    if not args.skip_dlp_mode_check:
        _validate_dlp_arm_state(status_after_arm)

    if args.verify_light_camera:
        checker = ProjectionPresenceChecker(
            sdk_priority=[part.strip() for part in args.camera_sdk_priority.split(",") if part.strip()],
            require_physical_hardware=args.camera_require_physical,
        )
        if not checker.connect():
            raise RuntimeError("Camera projection check requested but no Allied Vision camera backend connected")

        try:
            window._set_dlp_power(0)
            time.sleep(0.2)
            baseline_mean = checker.sample_mean(sample_count=args.camera_baseline_frames)

            window._set_dlp_power(args.camera_test_power)
            verification = checker.verify_projection(
                baseline_frames=max(1, args.camera_baseline_frames // 2),
                lit_frames=args.camera_lit_frames,
                intensity_margin=args.camera_intensity_margin,
                dark_threshold=args.camera_dark_threshold,
                settle_s=args.camera_settle_s,
            )
            verification["baseline_mean"] = baseline_mean
            print(f"  Camera projection check: {verification}")
            if not verification.get("light_detected", False):
                raise RuntimeError(
                    "Camera did not detect projected light "
                    f"(baseline={verification['baseline_mean']:.2f}, lit={verification['lit_mean']:.2f}, threshold={verification['threshold']:.2f})"
                )
        finally:
            window._set_dlp_power(0)
            checker.disconnect()

    # Reset to safe idle before entering the regular print step.
    window.cleanup_dlp_safe_state()


def _run_print_test(window, root) -> None:
    print("[4/4] Five-layer print run")
    _configure_entries(
        window,
        thickness=5,
        exposure=0.2,
        dlp_power=50,
        step_speed=1000,
        overstep=500,
        accel=5.0,
        pause=0.0,
        sandwich_speed=500,
    )

    window.run_Stepped()

    _wait_until(
        lambda: getattr(window, "print_thread", None) is None or not window.print_thread.is_alive(),
        timeout_s=45.0,
        poll_s=0.05,
        root=root,
        label="five-layer print completion",
    )

    print(f"  print thread completed; layer display shows {window.current_layer_num_var.get()}")

    controller = getattr(window, "controller", None)
    axis = getattr(window, "axis", None)
    if controller is not None and len(getattr(controller, "calls", [])) == 0:
        raise RuntimeError("Fake DLP controller did not receive any calls")
    if axis is not None and len(getattr(axis, "move_absolute_calls", [])) == 0:
        raise RuntimeError("Fake stage axis did not receive any movement calls")


def main() -> int:
    parser = argparse.ArgumentParser(description="Launch Prince GUI and run the torture test sequence.")
    parser.add_argument("--hold-after", type=float, default=0.0, help="Keep the GUI visible for N seconds after the test completes.")
    parser.add_argument("--real-hardware", action="store_true", help="Run against real hardware stack instead of stubs.")
    parser.add_argument("--skip-dlp-mode-check", action="store_true", help="Skip strict DLP mode/state verification after arming.")
    parser.add_argument("--verify-light-camera", action="store_true", help="Use Allied Vision camera to verify projected light turns on.")
    parser.add_argument("--camera-sdk-priority", default="vmbpy,vimbax", help="Comma-separated camera backend priority list.")
    parser.add_argument("--camera-require-physical", action="store_true", help="Require a physical (non-simulator) Allied Vision camera.")
    parser.add_argument("--camera-baseline-frames", type=int, default=8, help="Frame count for baseline dark-intensity sampling.")
    parser.add_argument("--camera-lit-frames", type=int, default=10, help="Frame count for lit-intensity sampling.")
    parser.add_argument("--camera-intensity-margin", type=float, default=35.0, help="Required lit-vs-baseline mean-intensity margin.")
    parser.add_argument("--camera-dark-threshold", type=float, default=40.0, help="Minimum absolute mean-intensity threshold for light detection.")
    parser.add_argument("--camera-settle-s", type=float, default=0.25, help="Settling delay before lit frame sampling.")
    parser.add_argument("--camera-test-power", type=int, default=120, help="Temporary DLP power used for camera projection check.")
    args = parser.parse_args()

    if not args.real_hardware:
        _install_stubs()

    import Prince_Segmented_VideoPattern as prince

    prince.winsound.Beep = lambda *args, **kwargs: None

    root = tk.Tk()
    root.title("Prince GUI Torture Tester")

    window = prince.MyWindow(root)

    with tempfile.TemporaryDirectory(prefix="prince_gui_torture_") as temp_dir:
        image_dir = Path(temp_dir) / "five_layer_job"
        _write_test_images(image_dir)

        def _run_all_steps():
            try:
                _run_instruction_torture(window, image_dir)
                _run_sensor_window_test(window, root)
                _run_projection_verification(window, args)
                _run_print_test(window, root)
                print("ALL GUI TORTURE TEST STEPS PASSED")

                if args.hold_after > 0:
                    root.after(int(args.hold_after * 1000), root.quit)
                else:
                    root.after(250, root.quit)
            except Exception as exc:
                print(f"GUI TORTURE TEST FAILED: {exc}")
                root.after(250, root.quit)

        root.after(500, _run_all_steps)
        try:
            root.mainloop()
        finally:
            try:
                root.destroy()
            except Exception:
                pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())