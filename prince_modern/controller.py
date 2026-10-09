"""Bridge Qt Modern shell to the withdrawn Unified Tk backend (print/hardware parity)."""

from __future__ import annotations

import os
import sys
import subprocess
import threading
import traceback
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QMessageBox

if TYPE_CHECKING:
    from .main_window import ModernMainWindow

REPO_ROOT = Path(__file__).resolve().parents[1]


class ModernController(QObject):
    """Owns a hidden Unified MyWindow and syncs it with the Qt shell."""

    log_message = Signal(str)
    progress = Signal(int, int, float, str)  # layer, total, fraction, eta
    z_position = Signal(object)
    printer_state = Signal(str, bool)
    sensor_buttons = Signal(bool, bool)

    def __init__(self, window: ModernMainWindow):
        super().__init__()
        self.window = window
        self.host = None
        self.tk_root = None
        self._monitoring_dashboard_proc = None
        self._tk_pump = QTimer(self)
        self._tk_pump.timeout.connect(self._pump_tk)
        self._z_timer = QTimer(self)
        self._z_timer.timeout.connect(self._poll_z)

        self.log_message.connect(window.append_log)
        self.progress.connect(window.set_progress)
        self.z_position.connect(window.set_z_position)
        self.printer_state.connect(window.set_printer_state)
        self.sensor_buttons.connect(window.set_sensor_button_states)

        window.browse_directory.connect(self.on_browse)
        window.run_continuous.connect(self.on_run_continuous)
        window.run_stepped.connect(self.on_run_stepped)
        window.stop_print.connect(self.on_stop)
        window.move_up.connect(self.on_move_up)
        window.move_down.connect(self.on_move_down)
        window.set_home.connect(self.on_set_home)
        window.get_position.connect(self.on_get_position)
        window.simple_txt.connect(self.on_simple_txt)
        window.open_image_mod.connect(self.on_image_mod)
        window.open_exp_conditions.connect(self.on_exp_conditions)
        window.open_sensor_logging.connect(self.on_sensor_logging)
        window.open_sensor_monitoring.connect(self.on_sensor_monitoring)
        window.open_monitoring_suite.connect(self.on_monitoring_suite)
        window.disconnect_dlp.connect(self.on_disconnect_dlp)
        window.reconnect_dlp.connect(self.on_reconnect_dlp)
        window.open_ramped_cylinder.connect(self.on_ramped_cylinder)
        window.projection_mode_changed.connect(self.on_projection_mode)
        window.field_changed.connect(self.sync_qt_to_host)

    def start(self) -> None:
        """Create withdrawn Unified host (homes stage / opens DLP)."""
        self.log_message.emit("Prince Modern starting — initializing Unified backend (hidden Tk)…")
        try:
            import tkinter as tk

            # Ensure repo + support_modules are importable like Unified.
            repo = str(REPO_ROOT)
            support = str(REPO_ROOT / "support_modules")
            for path in (repo, support):
                if path not in sys.path:
                    sys.path.insert(0, path)

            # Import the copied Unified module under a stable name.
            import importlib.util

            source = REPO_ROOT / "prince_modern_unified_source.py"
            spec = importlib.util.spec_from_file_location("prince_modern_unified_source", source)
            module = importlib.util.module_from_spec(spec)
            assert spec.loader is not None
            spec.loader.exec_module(module)

            self.tk_root = tk.Tk()
            self.tk_root.withdraw()
            self.host = module.MyWindow(self.tk_root)
            self.tk_root.withdraw()
            try:
                self.tk_root.iconify()
            except Exception:
                pass

            self._patch_host_callbacks()
            self._load_fields_from_host()
            self._tk_pump.start(50)
            self._z_timer.start(500)
            self.printer_state.emit("IDLE", False)
            self.log_message.emit("Backend ready. Unified print/hardware path is active behind the Qt shell.")
            self.log_message.emit(
                "Feature note: Monitoring Suite is included here (was missing from Unified). "
                "Sandwich/Auto-Home UI remain deferred; Viscosity Monitor still later."
            )
        except Exception as exc:
            self.log_message.emit(f"Backend init failed: {exc}")
            self.log_message.emit("UI shell will run in stub mode (no hardware).")
            traceback.print_exc()
            self.host = None

    def _patch_host_callbacks(self) -> None:
        host = self.host
        if host is None:
            return
        original_status = host.update_status_message

        def status_bridge(message, error=False, warning=False):
            prefix = "ERROR: " if error else ("WARN: " if warning else "")
            self.log_message.emit(prefix + str(message))
            try:
                original_status(message, error=error, warning=warning)
            except TypeError:
                try:
                    original_status(message)
                except Exception:
                    pass

        host.update_status_message = status_bridge

        original_progress = host._update_gui_progress

        def progress_bridge(*args, **kwargs):
            try:
                original_progress(*args, **kwargs)
            except Exception:
                traceback.print_exc()
            try:
                # Read Unified progress widgets after update.
                layer_text = host.current_layer_num_var.get() if hasattr(host, "current_layer_num_var") else ""
                eta = host.lbl15_var.get() if hasattr(host, "lbl15_var") else "—"
                # layer_text often "Layer: n/N"
                layer, total, frac = 0, 0, 0.0
                if hasattr(host, "p1"):
                    try:
                        frac = float(host.p1["value"]) / 100.0
                    except Exception:
                        frac = 0.0
                if "Layer:" in str(layer_text):
                    parts = str(layer_text).replace("Layer:", "").strip().split("/")
                    if len(parts) == 2:
                        layer = int(float(parts[0]))
                        total = int(float(parts[1]))
                eta_clean = str(eta).replace("Est:", "").strip()
                self.progress.emit(layer, total, frac, eta_clean)
                printing = bool(getattr(host, "print_thread", None) and host.print_thread.is_alive())
                self.printer_state.emit("PRINTING" if printing else "IDLE", printing)
            except Exception:
                pass

        host._update_gui_progress = progress_bridge

        # Keep sensor button mutual exclusion mirrored into Qt.
        if hasattr(host, "_sync_sensor_panel_button_states"):
            original_sync = host._sync_sensor_panel_button_states

            def sync_bridge():
                original_sync()
                logging_open = bool(
                    getattr(host, "sensor_data_window_instance", None)
                    and getattr(host.sensor_data_window_instance, "sensor_window", None)
                )
                monitoring_open = bool(
                    getattr(host, "sensor_data_window_monitoring_instance", None)
                    and getattr(host.sensor_data_window_monitoring_instance, "sensor_window", None)
                )
                try:
                    if logging_open:
                        logging_open = bool(host.sensor_data_window_instance.sensor_window.winfo_exists())
                except Exception:
                    logging_open = False
                try:
                    if monitoring_open:
                        monitoring_open = bool(
                            host.sensor_data_window_monitoring_instance.sensor_window.winfo_exists()
                        )
                except Exception:
                    monitoring_open = False
                self.sensor_buttons.emit(logging_open, monitoring_open)

            host._sync_sensor_panel_button_states = sync_bridge

    def _pump_tk(self) -> None:
        if self.tk_root is None:
            return
        try:
            self.tk_root.update_idletasks()
            self.tk_root.update()
        except Exception:
            pass

    def _poll_z(self) -> None:
        host = self.host
        if host is None or not getattr(host, "axis", None):
            return
        try:
            from zaber_motion import Units

            z = float(host.axis.get_position(Units.LENGTH_MILLIMETRES))
            self.z_position.emit(z)
            # Keep Unified t4 in sync for SessionManager.
            try:
                host.t4.delete(0, "end")
                host.t4.insert(0, f"{z:.3f}")
            except Exception:
                pass
            printing = bool(getattr(host, "print_thread", None) and host.print_thread.is_alive())
            self.printer_state.emit("PRINTING" if printing else "IDLE", printing)
        except Exception:
            pass

    def _load_fields_from_host(self) -> None:
        host = self.host
        if host is None:
            return
        values = {
            "directory": host.t1.get(),
            "led_power": host.t14.get(),
            "move_distance": host.t9.get(),
            "layer_thickness": host.t10.get(),
            "exposure": host.t11.get(),
            "base_cure": host.t11_2.get(),
            "step_speed": host.t16.get() if hasattr(host, "t16") else "1000",
            "pause": host.t17.get() if hasattr(host, "t17") else "0",
            "acceleration": host.t21.get() if hasattr(host, "t21") else "100",
            "overstep": host.t19.get() if hasattr(host, "t19") else "0",
            "video_pattern": "1"
            if getattr(host, "projection_mode_var", None) and host.projection_mode_var.get() == "video_pattern"
            else "0",
        }
        self.window.apply_fields(values)
        self.window.set_slice_directory(values["directory"])
        self.window.set_video_pattern_warning(values["video_pattern"] == "1")

    def sync_qt_to_host(self) -> None:
        host = self.host
        if host is None:
            return
        fields = self.window.collect_fields()

        def _set_entry(entry, value: str) -> None:
            entry.delete(0, "end")
            entry.insert(0, value)

        try:
            _set_entry(host.t1, fields["directory"])
            _set_entry(host.t14, fields["led_power"])
            _set_entry(host.t9, fields["move_distance"])
            _set_entry(host.t10, fields["layer_thickness"])
            _set_entry(host.t11, fields["exposure"])
            _set_entry(host.t11_2, fields["base_cure"])
            if hasattr(host, "t16"):
                _set_entry(host.t16, fields["step_speed"])
            if hasattr(host, "t17"):
                _set_entry(host.t17, fields["pause"])
            if hasattr(host, "t21"):
                _set_entry(host.t21, fields["acceleration"])
            if hasattr(host, "t19"):
                _set_entry(host.t19, fields["overstep"])
            if hasattr(host, "projection_mode_var"):
                mode = "video_pattern" if fields["video_pattern"] == "1" else "video"
                if host.projection_mode_var.get() != mode:
                    host.projection_mode_var.set(mode)
                    if hasattr(host, "_on_projection_mode_change"):
                        host._on_projection_mode_change()
            self.window.set_slice_directory(fields["directory"])
        except Exception as exc:
            self.log_message.emit(f"Field sync failed: {exc}")

    def _require_host(self) -> bool:
        if self.host is None:
            QMessageBox.warning(self.window, "Backend", "Hardware backend is not available.")
            return False
        self.sync_qt_to_host()
        return True

    def on_browse(self) -> None:
        start = self.window.image_dir.text().strip()
        path = self.window.choose_directory(start)
        if path:
            self.window.image_dir.setText(path)
            self.sync_qt_to_host()
            self.window.set_slice_directory(path)
            self.log_message.emit(f"Image directory: {path}")

    def on_run_continuous(self) -> None:
        if not self._require_host():
            return
        self.printer_state.emit("PRINTING", True)
        self.log_message.emit("Starting continuous print…")
        # Must run on the Tk-owning thread (same as Qt main after construction).
        self._call_host("run_Continuous")

    def on_run_stepped(self) -> None:
        if not self._require_host():
            return
        self.printer_state.emit("PRINTING", True)
        self.log_message.emit("Starting stepped print…")
        self._call_host("run_Stepped")

    def on_stop(self) -> None:
        if not self._require_host():
            return
        self.log_message.emit("Stop requested…")
        self._call_host("stop")

    def on_move_up(self) -> None:
        if not self._require_host():
            return
        self._call_host("moveup")

    def on_move_down(self) -> None:
        if not self._require_host():
            return
        self._call_host("movedown")

    def on_set_home(self) -> None:
        if not self._require_host():
            return
        self._call_host("set_home")

    def on_get_position(self) -> None:
        if not self._require_host():
            return
        self._call_host("get_position")
        self._poll_z()

    def on_simple_txt(self) -> None:
        if not self._require_host():
            return
        self._call_host("simple_txt")

    def on_image_mod(self) -> None:
        if not self._require_host():
            return
        self._call_host("open_image_modification_window")

    def on_exp_conditions(self) -> None:
        if not self._require_host():
            return
        self._call_host("open_exp_conditions_window")

    def on_sensor_logging(self) -> None:
        if not self._require_host():
            return
        self._call_host("open_sensor_panel")
        if hasattr(self.host, "_sync_sensor_panel_button_states"):
            self.host._sync_sensor_panel_button_states()

    def on_sensor_monitoring(self) -> None:
        if not self._require_host():
            return
        self._call_host("open_sensor_panel_monitoring")
        if hasattr(self.host, "_sync_sensor_panel_button_states"):
            self.host._sync_sensor_panel_button_states()

    def on_ramped_cylinder(self) -> None:
        if not self._require_host():
            return
        self._call_host("open_ramped_cylinder_window")

    def on_disconnect_dlp(self) -> None:
        if not self._require_host():
            return
        self._call_host("disconnect_dlp")

    def on_reconnect_dlp(self) -> None:
        if not self._require_host():
            return
        self._call_host("reconnect_dlp")

    def on_projection_mode(self, enabled: bool) -> None:
        self.window.set_video_pattern_warning(enabled)
        if not self._require_host():
            return
        mode = "video_pattern" if enabled else "video"
        self.host.projection_mode_var.set(mode)
        if hasattr(self.host, "_on_projection_mode_change"):
            self.host._on_projection_mode_change()
        self.log_message.emit(f"Projection mode → {mode}")

    def on_monitoring_suite(self) -> None:
        """Launch PySide6 monitoring dashboard (feature Unified lacked)."""
        try:
            proc = self._monitoring_dashboard_proc
            if proc is not None and proc.poll() is None:
                self.log_message.emit("Monitoring dashboard is already open.")
                return
            bundled = REPO_ROOT / ".conda" / "python.exe"
            python = str(bundled) if bundled.is_file() else sys.executable
            command = [python, "-m", "calibration_modules.monitoring_dashboard"]
            image_dir = self.window.image_dir.text().strip()
            if image_dir:
                command.extend(["--image-dir", image_dir])
            self._monitoring_dashboard_proc = subprocess.Popen(
                command,
                cwd=str(REPO_ROOT),
                close_fds=True,
            )
            self.log_message.emit("Monitoring Suite opened.")
        except Exception as exc:
            self.log_message.emit(f"Failed to open Monitoring Suite: {exc}")
            QMessageBox.critical(self.window, "Monitoring Suite", str(exc))

    def _call_host(self, method_name: str) -> None:
        host = self.host
        if host is None:
            return
        try:
            method = getattr(host, method_name)
            # Tk UI methods must run on the Tk thread; schedule via after if possible.
            if threading.current_thread() is not threading.main_thread() and self.tk_root is not None:
                self.tk_root.after(0, method)
            else:
                method()
        except Exception as exc:
            self.log_message.emit(f"{method_name} failed: {exc}")
            traceback.print_exc()

    def shutdown(self) -> None:
        self._tk_pump.stop()
        self._z_timer.stop()
        proc = self._monitoring_dashboard_proc
        if proc is not None and proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass
        host = self.host
        if host is not None and hasattr(host, "on_closing"):
            try:
                host.on_closing()
            except Exception:
                traceback.print_exc()
        elif self.tk_root is not None:
            try:
                self.tk_root.destroy()
            except Exception:
                pass
