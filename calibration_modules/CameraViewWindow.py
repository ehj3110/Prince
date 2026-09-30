"""
Camera View Window — Allied Vision Alvium live preview for Prince.

vmbpy-based popup: live stream, pan/zoom, exposure/gain, display filters, snapshot.
Includes rolling telemetry (FPS, intensity), auto-reconnect, and synthetic fallback mode.
Runnable standalone without Prince::

    .\\.conda\\python.exe -m calibration_modules.CameraViewWindow [--mock]
"""

from __future__ import annotations

import argparse
import os
import queue
import sys
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import cv2

try:
    from .vmb_camera_worker import VMBPY_AVAILABLE, VmbCameraWorker
    from .zoom_pan_canvas import ZoomPanCanvas
except ImportError:
    _HERE = Path(__file__).resolve().parent
    if str(_HERE) not in sys.path:
        sys.path.insert(0, str(_HERE))
    from vmb_camera_worker import VMBPY_AVAILABLE, VmbCameraWorker
    from zoom_pan_canvas import ZoomPanCanvas


class CameraViewWindow:
    """Pop-up Toplevel: Allied Vision preview, zoom/pan, hardware + display controls."""

    POLL_MS = 30
    DEBOUNCE_MS = 150

    def __init__(self, parent=None, fallback_to_mock: bool = False):
        self.parent = parent
        self.fallback_to_mock = fallback_to_mock
        self.window = tk.Toplevel(parent) if parent is not None else tk.Tk()
        self.window.title("Allied Vision Alvium Preview & Alignment")
        self.window.geometry("1300x850")
        self.window.minsize(900, 600)

        self.frame_queue: queue.Queue = queue.Queue(maxsize=1)
        self.worker: VmbCameraWorker | None = None
        self._poll_after_id = None
        self._closing = False
        self._exp_debounce_id = None
        self._gain_debounce_id = None
        self._hw_limits_applied = False
        self._ui_initialized = False

        self._build_ui()
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)

        if not VMBPY_AVAILABLE and not self.fallback_to_mock:
            self.status_var.set("ERROR: vmbpy not installed. Install Vimba X + vmbpy.")
            messagebox.showerror(
                "Camera Error",
                "vmbpy is not available.\nInstall Allied Vision Vimba X and pip install vmbpy.",
                parent=self.window,
            )
        else:
            self._start_worker()
            self._poll_camera_frames()

    def _start_worker(self) -> None:
        """Start or restart the acquisition worker thread."""
        if self.worker is not None:
            self.worker.stop(join_timeout=3.0)
            self.worker = None

        self._hw_limits_applied = False
        self.worker = VmbCameraWorker(self.frame_queue, fallback_to_mock=self.fallback_to_mock)
        self.worker.start()
        self.status_var.set("Connecting to camera...")

    def reconnect_camera(self) -> None:
        """Manual trigger to re-initialize camera connection."""
        self.status_var.set("Re-initializing camera connection...")
        self._start_worker()

    def _build_ui(self) -> None:
        self.window.columnconfigure(0, weight=4)
        self.window.columnconfigure(1, weight=1)
        self.window.rowconfigure(0, weight=1)

        canvas_frame = ttk.Frame(self.window)
        canvas_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.canvas = ZoomPanCanvas(canvas_frame)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        control_panel = ttk.Frame(self.window, padding=10)
        control_panel.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        # Section 1: Viewport & Navigation
        nav_box = ttk.LabelFrame(control_panel, text="Viewport & Zoom", padding=8)
        nav_box.pack(fill=tk.X, pady=5)
        btn_row = ttk.Frame(nav_box)
        btn_row.pack(fill=tk.X, pady=2)
        ttk.Button(btn_row, text="Fit View", command=self.canvas.reset_view).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=2
        )
        ttk.Button(btn_row, text="1:1 (100%)", command=self.canvas.set_one_to_one).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=2
        )
        self.crosshair_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            nav_box,
            text="Show Center Crosshair",
            variable=self.crosshair_var,
            command=self._toggle_crosshair,
        ).pack(anchor=tk.W, pady=4)

        # Section 2: Hardware Settings
        hw_box = ttk.LabelFrame(control_panel, text="Hardware Controls", padding=8)
        hw_box.pack(fill=tk.X, pady=5)

        ttk.Label(hw_box, text="Exposure (µs):").pack(anchor=tk.W)
        self.exp_var = tk.StringVar(value="20000")
        exp_row = ttk.Frame(hw_box)
        exp_row.pack(fill=tk.X, pady=2)
        self.exp_slider = ttk.Scale(
            exp_row, from_=100, to=200000, orient=tk.HORIZONTAL, command=self._on_exposure_slider
        )
        self.exp_slider.set(20000)
        self.exp_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.exp_entry = ttk.Entry(exp_row, textvariable=self.exp_var, width=8)
        self.exp_entry.pack(side=tk.LEFT, padx=5)
        self.exp_entry.bind("<Return>", lambda _e: self._on_exposure_entry())

        ttk.Label(hw_box, text="Gain (dB):").pack(anchor=tk.W, pady=(8, 0))
        self.gain_var = tk.StringVar(value="0.0")
        gain_row = ttk.Frame(hw_box)
        gain_row.pack(fill=tk.X, pady=2)
        self.gain_slider = ttk.Scale(
            gain_row, from_=0, to=24, orient=tk.HORIZONTAL, command=self._on_gain_slider
        )
        self.gain_slider.set(0)
        self.gain_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.gain_entry = ttk.Entry(gain_row, textvariable=self.gain_var, width=8)
        self.gain_entry.pack(side=tk.LEFT, padx=5)
        self.gain_entry.bind("<Return>", lambda _e: self._on_gain_entry())

        ttk.Button(hw_box, text="🔄 Reconnect Camera", command=self.reconnect_camera).pack(
            fill=tk.X, pady=(10, 2)
        )

        # Section 3: Software Processing
        sw_box = ttk.LabelFrame(control_panel, text="Display / Image Adjustments", padding=8)
        sw_box.pack(fill=tk.X, pady=5)

        ttk.Label(sw_box, text="Contrast (Alpha):").pack(anchor=tk.W)
        self.contrast_slider = ttk.Scale(
            sw_box, from_=0.2, to=3.0, orient=tk.HORIZONTAL, command=self._update_software_filters
        )
        self.contrast_slider.set(1.0)
        self.contrast_slider.pack(fill=tk.X, pady=2)

        ttk.Label(sw_box, text="Brightness (Offset):").pack(anchor=tk.W, pady=(6, 0))
        self.brightness_slider = ttk.Scale(
            sw_box, from_=-100, to=100, orient=tk.HORIZONTAL, command=self._update_software_filters
        )
        self.brightness_slider.set(0)
        self.brightness_slider.pack(fill=tk.X, pady=2)

        ttk.Label(sw_box, text="Gamma:").pack(anchor=tk.W, pady=(6, 0))
        self.gamma_slider = ttk.Scale(
            sw_box, from_=0.2, to=3.0, orient=tk.HORIZONTAL, command=self._update_software_filters
        )
        self.gamma_slider.set(1.0)
        self.gamma_slider.pack(fill=tk.X, pady=2)

        ttk.Button(sw_box, text="Reset Image Filters", command=self._reset_filters).pack(
            fill=tk.X, pady=6
        )

        # Section 4: Capture & Save
        act_box = ttk.LabelFrame(control_panel, text="Capture", padding=8)
        act_box.pack(fill=tk.X, pady=5)
        ttk.Button(act_box, text="📸 Save Snapshot", command=self.save_snapshot).pack(fill=tk.X, pady=3)

        # Status Bar
        self.status_var = tk.StringVar(value="Connecting to camera...")
        status_bar = ttk.Label(
            self.window, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, padding=4
        )
        status_bar.grid(row=1, column=0, columnspan=2, sticky="ew")
        self._ui_initialized = True

    def _toggle_crosshair(self) -> None:
        self.canvas.show_crosshair = self.crosshair_var.get()
        self.canvas.redraw()

    def _apply_hw_limits_once(self) -> None:
        if self._hw_limits_applied or self.worker is None or not self.worker.connected:
            return
        lo_e, hi_e = self.worker.exposure_range
        lo_g, hi_g = self.worker.gain_range
        self.exp_slider.configure(from_=lo_e, to=hi_e)
        self.gain_slider.configure(from_=lo_g, to=hi_g)
        if self.worker.current_exposure is not None:
            self.exp_slider.set(self.worker.current_exposure)
            self.exp_var.set(str(int(round(self.worker.current_exposure))))
        if self.worker.current_gain is not None:
            self.gain_slider.set(self.worker.current_gain)
            self.gain_var.set(f"{self.worker.current_gain:.1f}")
        self._hw_limits_applied = True

    def _schedule_exposure(self, value: float) -> None:
        if self._exp_debounce_id is not None:
            try:
                self.window.after_cancel(self._exp_debounce_id)
            except Exception:
                pass

        def apply():
            self._exp_debounce_id = None
            if self.worker:
                self.worker.request_exposure(value)

        self._exp_debounce_id = self.window.after(self.DEBOUNCE_MS, apply)

    def _schedule_gain(self, value: float) -> None:
        if self._gain_debounce_id is not None:
            try:
                self.window.after_cancel(self._gain_debounce_id)
            except Exception:
                pass

        def apply():
            self._gain_debounce_id = None
            if self.worker:
                self.worker.request_gain(value)

        self._gain_debounce_id = self.window.after(self.DEBOUNCE_MS, apply)

    def _on_exposure_slider(self, val_str: str) -> None:
        if not getattr(self, "_ui_initialized", False):
            return
        val = round(float(val_str))
        self.exp_var.set(str(val))
        self._schedule_exposure(val)

    def _on_exposure_entry(self) -> None:
        try:
            val = float(self.exp_var.get())
            if self.worker:
                lo, hi = self.worker.exposure_range
                val = max(lo, min(val, hi))
            self.exp_slider.set(val)
            self.exp_var.set(str(int(round(val))))
            self._schedule_exposure(val)
        except ValueError:
            pass

    def _on_gain_slider(self, val_str: str) -> None:
        if not getattr(self, "_ui_initialized", False):
            return
        val = round(float(val_str), 1)
        self.gain_var.set(f"{val:.1f}")
        self._schedule_gain(val)

    def _on_gain_entry(self) -> None:
        try:
            val = float(self.gain_var.get())
            if self.worker:
                lo, hi = self.worker.gain_range
                val = max(lo, min(val, hi))
            self.gain_slider.set(val)
            self.gain_var.set(f"{val:.1f}")
            self._schedule_gain(val)
        except ValueError:
            pass

    def _update_software_filters(self, _val_str: str | None = None) -> None:
        if not getattr(self, "_ui_initialized", False):
            return
        alpha = float(self.contrast_slider.get())
        beta = int(float(self.brightness_slider.get()))
        gamma = float(self.gamma_slider.get())
        self.canvas.set_contrast_brightness(alpha, beta)
        self.canvas.set_gamma(gamma)

    def _reset_filters(self) -> None:
        self.contrast_slider.set(1.0)
        self.brightness_slider.set(0)
        self.gamma_slider.set(1.0)
        self.canvas.contrast_alpha = 1.0
        self.canvas.brightness_beta = 0
        self.canvas.set_gamma(1.0)

    def save_snapshot(self) -> None:
        if self.canvas.raw_image is None:
            messagebox.showwarning("Snapshot", "No frame available to save.", parent=self.window)
            return

        default_name = f"camera_snap_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = filedialog.asksaveasfilename(
            parent=self.window,
            defaultextension=".png",
            filetypes=[
                ("PNG Image", "*.png"),
                ("TIFF Image", "*.tiff"),
                ("JPEG Image", "*.jpg"),
            ],
            initialfile=default_name,
        )
        if filepath:
            if not cv2.imwrite(filepath, self.canvas.raw_image):
                messagebox.showerror("Snapshot", f"Failed to write {filepath}", parent=self.window)
                return
            self.status_var.set(f"Saved snapshot: {os.path.basename(filepath)}")

    def _poll_camera_frames(self) -> None:
        if self._closing:
            return
        try:
            if not self.window.winfo_exists():
                return
        except tk.TclError:
            return

        self._apply_hw_limits_once()

        try:
            frame = self.frame_queue.get_nowait()
            self.canvas.set_raw_frame(frame)
            if self.worker and self.worker.connected:
                mode_str = "[MOCK] " if getattr(self.worker, "is_mock", False) else ""
                self.status_var.set(
                    f"{mode_str}Streaming | {self.worker.cam_model} ({self.worker.cam_id}) | "
                    f"{frame.shape[1]}x{frame.shape[0]} | {self.worker.fps} FPS | "
                    f"Mean: {self.worker.mean_intensity:.0f} | Zoom: {self.canvas.zoom_scale:.2f}x"
                )
        except queue.Empty:
            if self.worker is not None:
                if self.worker.last_error and not self.worker.connected and not self.worker.is_alive():
                    self.status_var.set(f"Camera error: {self.worker.last_error}")
                elif not self.worker.connected and not self.worker.is_alive():
                    self.status_var.set("Camera disconnected or not found.")
                elif not self.worker.connected:
                    self.status_var.set("Connecting to camera (retrying)...")

        try:
            self._poll_after_id = self.window.after(self.POLL_MS, self._poll_camera_frames)
        except tk.TclError:
            self._poll_after_id = None

    def on_closing(self) -> None:
        self._closing = True
        if self._poll_after_id is not None:
            try:
                self.window.after_cancel(self._poll_after_id)
            except Exception:
                pass
            self._poll_after_id = None
        for debounce_id in (self._exp_debounce_id, self._gain_debounce_id):
            if debounce_id is not None:
                try:
                    self.window.after_cancel(debounce_id)
                except Exception:
                    pass
        if self.worker is not None:
            self.worker.stop(join_timeout=5.0)
            self.worker = None
        try:
            self.window.destroy()
        except tk.TclError:
            pass

    def run(self) -> None:
        """Run mainloop when launched without a parent."""
        if self.parent is None:
            self.window.mainloop()


def main() -> int:
    parser = argparse.ArgumentParser(description="CameraViewWindow standalone preview")
    parser.add_argument("--mock", action="store_true", help="Force synthetic mock camera stream")
    args = parser.parse_args()

    app = CameraViewWindow(parent=None, fallback_to_mock=args.mock)
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
