"""
Monitoring Suite — one Prince window for optical camera, thermal camera,
force readout, and a reserved Thorlabs power-meter slot.

Optical and thermal views reuse CameraViewWindow and SeekThermalViewerWindow
embedded in notebook tabs. Force is read from the existing Sensor Panel
ForceGaugeManager (this window does not open a second Phidget).
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

try:
    from .CameraViewWindow import CameraViewWindow
    from .SeekThermalViewerWindow import SeekThermalViewerWindow
except ImportError:
    from CameraViewWindow import CameraViewWindow
    from SeekThermalViewerWindow import SeekThermalViewerWindow


class MonitoringSuiteWindow:
    """Tabbed monitoring window launched from Prince_Segmented."""

    POLL_MS = 200

    def __init__(self, parent, prince_app=None, optical_mock: bool = False):
        self.parent = parent
        self.prince_app = prince_app
        self.optical_mock = optical_mock
        self.window = tk.Toplevel(parent)
        self.window.title("Monitoring Suite")
        self.window.geometry("1400x900")
        self.window.minsize(1000, 700)
        self._closing = False
        self._poll_after_id = None

        self.force_var = tk.StringVar(value="Force: —")
        self.thermal_var = tk.StringVar(value="Thermal: —")
        self.optical_var = tk.StringVar(value="Optical: —")
        self.power_var = tk.StringVar(value="Power: not connected")

        self._build_ui()
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        self._poll_readouts()

    def _build_ui(self) -> None:
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(1, weight=1)

        strip = ttk.Frame(self.window, padding=(8, 6))
        strip.grid(row=0, column=0, sticky="ew")
        for col, (var, width) in enumerate(
            (
                (self.force_var, 28),
                (self.thermal_var, 42),
                (self.optical_var, 36),
                (self.power_var, 32),
            )
        ):
            ttk.Label(strip, textvariable=var, width=width, anchor=tk.W).grid(
                row=0, column=col, padx=8, sticky=tk.W
            )

        notebook = ttk.Notebook(self.window)
        self.notebook = notebook
        notebook.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))

        optical_tab = ttk.Frame(notebook)
        thermal_tab = ttk.Frame(notebook)
        sensors_tab = ttk.Frame(notebook)
        notebook.add(optical_tab, text="Optical camera")
        notebook.add(thermal_tab, text="Thermal camera")
        notebook.add(sensors_tab, text="Force and power")

        optical_tab.columnconfigure(0, weight=1)
        optical_tab.rowconfigure(0, weight=1)
        thermal_tab.columnconfigure(0, weight=1)
        thermal_tab.rowconfigure(0, weight=1)
        sensors_tab.columnconfigure(0, weight=1)

        optical_host = ttk.Frame(optical_tab)
        optical_host.grid(row=0, column=0, sticky="nsew")
        thermal_host = ttk.Frame(thermal_tab)
        thermal_host.grid(row=0, column=0, sticky="nsew")

        self.optical = CameraViewWindow(
            parent=self.window, embed_in=optical_host, fallback_to_mock=self.optical_mock
        )
        self.thermal = SeekThermalViewerWindow(
            parent=self.window, fallback_to_mock=True, embed_in=thermal_host
        )

        self._build_sensors_tab(sensors_tab)

    def _build_sensors_tab(self, parent) -> None:
        force_box = ttk.LabelFrame(parent, text="Force gauge", padding=12)
        force_box.grid(row=0, column=0, sticky="ew", padx=12, pady=12)
        ttk.Label(
            force_box,
            textvariable=self.force_var,
            font=("Segoe UI", 16),
        ).pack(anchor=tk.W)
        ttk.Label(
            force_box,
            text=(
                "Live force comes from the Sensor Panel Phidget connection. "
                "Open Sensor Panel and calibrate or tare there. This suite does not open a second gauge."
            ),
            wraplength=720,
        ).pack(anchor=tk.W, pady=(6, 0))

        power_box = ttk.LabelFrame(parent, text="Thorlabs power meter", padding=12)
        power_box.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 12))
        ttk.Label(
            power_box,
            textvariable=self.power_var,
            font=("Segoe UI", 16),
        ).pack(anchor=tk.W)
        ttk.Label(
            power_box,
            text=(
                "Reserved for a Thorlabs USB optical power meter. "
                "No driver is connected yet, so this readout stays offline until that instrument is added."
            ),
            wraplength=720,
        ).pack(anchor=tk.W, pady=(6, 0))

    def _force_gauge(self):
        app = self.prince_app
        if app is None:
            return None
        panel = getattr(app, "sensor_data_window_instance", None)
        if panel is None:
            return None
        return getattr(panel, "force_gauge_manager", None)

    def _poll_readouts(self) -> None:
        if self._closing:
            return
        try:
            if not self.window.winfo_exists():
                return
        except tk.TclError:
            return

        gauge = self._force_gauge()
        if gauge is None:
            self.force_var.set("Force: open Sensor Panel")
        else:
            try:
                newtons = float(gauge.get_force_N())
                calibrated = "cal" if gauge.is_calibrated() else "uncal"
                self.force_var.set(f"Force: {newtons:.3f} N ({calibrated})")
            except Exception:
                self.force_var.set("Force: read error")

        thermal_worker = getattr(self.thermal, "worker", None)
        if thermal_worker is not None and thermal_worker.connected:
            self.thermal_var.set(
                f"Thermal: max {thermal_worker.max_temp_c:.1f} °C  "
                f"mean {thermal_worker.mean_temp_c:.1f} °C  {thermal_worker.fps:.0f} FPS"
            )
        else:
            self.thermal_var.set("Thermal: connecting")

        optical_worker = getattr(self.optical, "worker", None)
        if optical_worker is not None and optical_worker.connected:
            self.optical_var.set(
                f"Optical: {optical_worker.fps:.1f} FPS  mean {optical_worker.mean_intensity:.0f}"
            )
        else:
            self.optical_var.set("Optical: connecting")

        try:
            self._poll_after_id = self.window.after(self.POLL_MS, self._poll_readouts)
        except tk.TclError:
            self._poll_after_id = None

    def on_closing(self) -> None:
        if self._closing:
            return
        self._closing = True
        if self._poll_after_id is not None:
            try:
                self.window.after_cancel(self._poll_after_id)
            except Exception:
                pass
            self._poll_after_id = None
        try:
            self.optical.on_closing()
        except Exception as exc:
            print(f"Monitoring suite: optical close error: {exc}")
        try:
            self.thermal.on_closing()
        except Exception as exc:
            print(f"Monitoring suite: thermal close error: {exc}")
        try:
            self.window.destroy()
        except tk.TclError:
            pass
