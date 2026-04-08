#!/usr/bin/env python3
"""Launch SensorDataWindow_ExtendedWindow with spoofed stage and force data."""

import argparse
import math
import queue
import random
import threading
import time
import tkinter as tk

from zaber_motion import Units

import SensorDataWindow_ExtendedWindow as sensor_window_mod


class FakeStageAxis:
    """Simple simulated stage axis returning a drifting sinusoid position in mm."""

    def __init__(self) -> None:
        self._t0 = time.time()

    def get_position(self, unit=Units.LENGTH_MILLIMETRES):
        t = time.time() - self._t0
        pos_mm = 12.0 + 0.45 * math.sin(2.0 * math.pi * 0.22 * t) + random.uniform(-0.01, 0.01)
        return pos_mm


class _FakeVoltageRatioInput:
    def __init__(self, mgr_ref):
        self._mgr = mgr_ref

    def getAttached(self):
        return True

    def getVoltageRatio(self):
        # Tie tare/readback to the current simulated force baseline.
        return self._mgr._current_force_n / self._mgr.GAIN + self._mgr.OFFSET


class FakeForceGaugeManager:
    """Drop-in stand-in for ForceGaugeManager that emits random-noise force data."""

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
        self._stop_event = threading.Event()
        self._thread = None
        self._interval_s = 0.05
        self._t0 = time.time()
        self._current_force_n = 0.0

        self.voltage_ratio_input = _FakeVoltageRatioInput(self)

        self.gain_label.config(text=f"Gain: {self.GAIN:.6f}")
        self.offset_label.config(text=f"Offset: {self.OFFSET:.6f}")

        self._start_force_reading_thread()

    def _start_force_reading_thread(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_force_loop, daemon=True)
        self._thread.start()

    def _run_force_loop(self):
        while not self._stop_event.is_set():
            t = time.time() - self._t0
            # Rough peel-like waveform + noise
            base = 0.05 * math.sin(2.0 * math.pi * 0.5 * t)
            pulse = 0.18 * math.sin(2.0 * math.pi * 0.08 * t)
            noise = random.uniform(-0.03, 0.03)
            self._current_force_n = base + pulse + noise

            try:
                self.force_status_label.config(text=f"Force: {self._current_force_n:+.4f} N")
                self.large_force_readout_label.config(text=f"Force: {self._current_force_n:+.4f} N")
            except Exception:
                # UI is likely closing; end spoof loop quietly.
                break

            try:
                self.output_force_queue.put_nowait(("force", self._current_force_n))
            except queue.Full:
                pass

            time.sleep(self._interval_s)

    def set_data_interval(self, interval_ms):
        try:
            interval_ms = float(interval_ms)
            if interval_ms <= 0:
                return False
            self._interval_s = max(0.001, interval_ms / 1000.0)
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

    def stop_force_reading_thread(self):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)


class _FakeMainAppRef:
    def __init__(self):
        self.sensor_data_window_instance = None

    def update_auto_home_button_state(self):
        pass


def status_callback(msg, error=False, warning=False, success=False):
    level = "INFO"
    if error:
        level = "ERROR"
    elif warning:
        level = "WARN"
    elif success:
        level = "OK"
    print(f"[{level}] {msg}")


def main():
    parser = argparse.ArgumentParser(description="Run spoofed extended sensor window.")
    parser.add_argument("--duration", type=float, default=0.0, help="Auto-close after N seconds (0 = manual close).")
    args = parser.parse_args()

    # Monkeypatch the module so the window uses spoofed force manager.
    sensor_window_mod.ForceGaugeManager = FakeForceGaugeManager

    root = tk.Tk()
    root.withdraw()

    stage = FakeStageAxis()
    fake_main = _FakeMainAppRef()

    window = sensor_window_mod.SensorDataWindow(
        master_window=root,
        zaber_axis_ref=stage,
        main_app_status_callback=status_callback,
        prince_main_app_ref=fake_main,
    )
    fake_main.sensor_data_window_instance = window

    window.start_live_readout()

    if args.duration > 0:
        def _shutdown():
            try:
                window.on_sensor_window_close()
            finally:
                try:
                    root.quit()
                except Exception:
                    pass
                try:
                    root.destroy()
                except Exception:
                    pass

        root.after(int(args.duration * 1000), _shutdown)

    root.mainloop()


if __name__ == "__main__":
    main()
