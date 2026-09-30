"""
Seek Thermal InspectionCAM Viewer Window — Standalone & Prince Pop-up.
File: calibration_modules/SeekThermalViewerWindow.py

Supports:
- Seek Thermal InspectionCAM (Model IQ-AAA, 320x240, 9 Hz)
- Cursor-anchored Zoom & Pan
- Real-time spot temperature probing under cursor & pinned markers
- Live Max (Hotspot) and Min (Coldspot) temperature tracking reticles
- False-color palettes: Inferno, Turbo, Viridis, Plasma, Jet, Hot, Grayscale
- Temperature scale adjustment (Auto vs Fixed Range for SLA resin)
- Radiometric CSV/NPY temperature grid export and PNG snapshot
- Realistic synthetic thermal simulation mode for offline development

Run standalone::
    .\\.conda\\python.exe -m calibration_modules.SeekThermalViewerWindow [--mock]
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
import numpy as np

try:
    from .seek_thermal_canvas import COLORMAP_DICT, SeekThermalCanvas
    from .seek_thermal_worker import SeekThermalWorker
except ImportError:
    _HERE = Path(__file__).resolve().parent
    if str(_HERE) not in sys.path:
        sys.path.insert(0, str(_HERE))
    from seek_thermal_canvas import COLORMAP_DICT, SeekThermalCanvas
    from seek_thermal_worker import SeekThermalWorker


class SeekThermalViewerWindow:
    """Standalone / Pop-up viewer for Seek Thermal InspectionCAM."""

    POLL_MS = 40  # ~25 Hz GUI poll for 9 Hz sensor stream

    def __init__(self, parent=None, fallback_to_mock: bool = True):
        self.parent = parent
        self.fallback_to_mock = fallback_to_mock
        self.window = tk.Toplevel(parent) if parent is not None else tk.Tk()
        self.window.title("Seek Thermal InspectionCAM (IQ-AAA) — Radiometric Thermography")
        self.window.geometry("1300x850")
        self.window.minsize(900, 600)

        self.frame_queue: queue.Queue = queue.Queue(maxsize=1)
        self.worker: Optional[SeekThermalWorker] = None
        self._poll_after_id = None
        self._closing = False
        self._ui_initialized = False

        self.latest_temp_array: Optional[np.ndarray] = None

        self._build_ui()
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)

        self._start_worker()
        self._poll_camera_frames()

    def _start_worker(self) -> None:
        if self.worker is not None:
            self.worker.stop(join_timeout=2.0)
            self.worker = None

        self.worker = SeekThermalWorker(self.frame_queue, fallback_to_mock=self.fallback_to_mock)
        self.worker.start()
        self.status_var.set("Connecting to Seek Thermal InspectionCAM...")

    def reconnect_camera(self) -> None:
        self.status_var.set("Re-initializing Seek Thermal connection...")
        self._start_worker()

    def _on_probe_update(self, temp_c: float, sx: int, sy: int) -> None:
        """Callback from canvas when mouse hovers over thermal pixels."""
        if hasattr(self, "probe_val_lbl"):
            self.probe_val_lbl.config(text=f"{temp_c:.1f} °C ({sx},{sy})")

    def _build_ui(self) -> None:
        self.window.columnconfigure(0, weight=4)  # Canvas
        self.window.columnconfigure(1, weight=1)  # Controls
        self.window.rowconfigure(0, weight=1)

        # Left Canvas
        canvas_frame = ttk.Frame(self.window)
        canvas_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.canvas = SeekThermalCanvas(canvas_frame, on_probe_update=self._on_probe_update)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Right Control Panel
        control_panel = ttk.Frame(self.window, padding=8)
        control_panel.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        # Section 1: Thermography Readout Card
        readout_box = ttk.LabelFrame(control_panel, text="Live Thermography", padding=8)
        readout_box.pack(fill=tk.X, pady=4)

        t_grid = ttk.Frame(readout_box)
        t_grid.pack(fill=tk.X)

        # Hotspot
        ttk.Label(t_grid, text="Max (Hotspot):", font=("Arial", 9, "bold")).grid(row=0, column=0, sticky=tk.W, pady=2)
        self.max_temp_lbl = ttk.Label(t_grid, text="-- °C", font=("Arial", 11, "bold"), foreground="#D92027")
        self.max_temp_lbl.grid(row=0, column=1, sticky=tk.E, pady=2)

        # Coldspot
        ttk.Label(t_grid, text="Min (Coldspot):", font=("Arial", 9, "bold")).grid(row=1, column=0, sticky=tk.W, pady=2)
        self.min_temp_lbl = ttk.Label(t_grid, text="-- °C", font=("Arial", 11, "bold"), foreground="#1E90FF")
        self.min_temp_lbl.grid(row=1, column=1, sticky=tk.E, pady=2)

        # Mean Vat Temp
        ttk.Label(t_grid, text="Mean (Vat Avg):", font=("Arial", 9)).grid(row=2, column=0, sticky=tk.W, pady=2)
        self.mean_temp_lbl = ttk.Label(t_grid, text="-- °C", font=("Arial", 10))
        self.mean_temp_lbl.grid(row=2, column=1, sticky=tk.E, pady=2)

        # Probe Readout
        ttk.Label(t_grid, text="Cursor / Pin Probe:", font=("Arial", 9)).grid(row=3, column=0, sticky=tk.W, pady=2)
        self.probe_val_lbl = ttk.Label(t_grid, text="-- °C", font=("Arial", 10, "italic"), foreground="#E67E22")
        self.probe_val_lbl.grid(row=3, column=1, sticky=tk.E, pady=2)

        ttk.Button(readout_box, text="Clear Pinned Probe", command=self.canvas.clear_pinned_probe).pack(fill=tk.X, pady=(6, 2))

        # Section 2: Viewport & Reticles
        nav_box = ttk.LabelFrame(control_panel, text="Viewport & Overlays", padding=8)
        nav_box.pack(fill=tk.X, pady=4)

        nav_btns = ttk.Frame(nav_box)
        nav_btns.pack(fill=tk.X, pady=2)
        ttk.Button(nav_btns, text="Fit View", command=self.canvas.reset_view).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        ttk.Button(nav_btns, text="1:1 (320x240)", command=self.canvas.set_one_to_one).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        self.minmax_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(nav_box, text="Track Max / Min Hotspots", variable=self.minmax_var, command=self._toggle_minmax).pack(anchor=tk.W, pady=2)

        self.crosshair_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(nav_box, text="Show Center Reticle", variable=self.crosshair_var, command=self._toggle_crosshair).pack(anchor=tk.W, pady=2)

        self.colorbar_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(nav_box, text="Show Temperature Colorbar", variable=self.colorbar_var, command=self._toggle_colorbar).pack(anchor=tk.W, pady=2)

        # Section 3: Palette & Temperature Scale
        scale_box = ttk.LabelFrame(control_panel, text="Colormap & Scaling", padding=8)
        scale_box.pack(fill=tk.X, pady=4)

        ttk.Label(scale_box, text="Palette:").pack(anchor=tk.W)
        self.palette_var = tk.StringVar(value="Inferno")
        palette_combo = ttk.Combobox(scale_box, textvariable=self.palette_var, values=list(COLORMAP_DICT.keys()), state="readonly")
        palette_combo.pack(fill=tk.X, pady=2)
        palette_combo.bind("<<ComboboxSelected>>", lambda _e: self.canvas.set_palette(self.palette_var.get()))

        # Scale Mode
        self.scale_mode_var = tk.StringVar(value="auto")
        ttk.Radiobutton(scale_box, text="Auto Span (Min-Max)", variable=self.scale_mode_var, value="auto", command=self._on_scale_mode_change).pack(anchor=tk.W, pady=(6, 2))
        ttk.Radiobutton(scale_box, text="Fixed Span (SLA Resin Range)", variable=self.scale_mode_var, value="fixed", command=self._on_scale_mode_change).pack(anchor=tk.W, pady=2)

        span_frame = ttk.Frame(scale_box)
        span_frame.pack(fill=tk.X, pady=4)

        ttk.Label(span_frame, text="Min °C:").grid(row=0, column=0, sticky=tk.W)
        self.manual_min_var = tk.StringVar(value="20.0")
        self.manual_min_entry = ttk.Entry(span_frame, textvariable=self.manual_min_var, width=7)
        self.manual_min_entry.grid(row=0, column=1, padx=4)
        self.manual_min_entry.bind("<Return>", lambda _e: self._on_scale_mode_change())

        ttk.Label(span_frame, text="Max °C:").grid(row=0, column=2, sticky=tk.W, padx=(8, 0))
        self.manual_max_var = tk.StringVar(value="55.0")
        self.manual_max_entry = ttk.Entry(span_frame, textvariable=self.manual_max_var, width=7)
        self.manual_max_entry.grid(row=0, column=3, padx=4)
        self.manual_max_entry.bind("<Return>", lambda _e: self._on_scale_mode_change())

        # Section 4: Capture & Export
        exp_box = ttk.LabelFrame(control_panel, text="Capture & Radiometric Export", padding=8)
        exp_box.pack(fill=tk.X, pady=4)

        ttk.Button(exp_box, text="📸 Save Colorized PNG", command=self.save_png_snapshot).pack(fill=tk.X, pady=2)
        ttk.Button(exp_box, text="💾 Export Temperature Grid (CSV)", command=self.export_csv_matrix).pack(fill=tk.X, pady=2)
        ttk.Button(exp_box, text="💾 Export Radiometric (NPY)", command=self.export_npy_array).pack(fill=tk.X, pady=2)

        # Section 5: Hardware Management
        hw_box = ttk.LabelFrame(control_panel, text="Camera Hardware", padding=8)
        hw_box.pack(fill=tk.X, pady=4)

        ttk.Button(hw_box, text="🔄 Reconnect InspectionCAM", command=self.reconnect_camera).pack(fill=tk.X, pady=2)

        # Status Bar
        self.status_var = tk.StringVar(value="Connecting...")
        status_bar = ttk.Label(self.window, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, padding=4)
        status_bar.grid(row=1, column=0, columnspan=2, sticky="ew")

        self._ui_initialized = True

    def _toggle_minmax(self) -> None:
        self.canvas.show_min_max = self.minmax_var.get()
        self.canvas.redraw()

    def _toggle_crosshair(self) -> None:
        self.canvas.show_center_crosshair = self.crosshair_var.get()
        self.canvas.redraw()

    def _toggle_colorbar(self) -> None:
        self.canvas.show_colorbar = self.colorbar_var.get()
        self.canvas.redraw()

    def _on_scale_mode_change(self) -> None:
        is_auto = (self.scale_mode_var.get() == "auto")
        try:
            t_min = float(self.manual_min_var.get())
            t_max = float(self.manual_max_var.get())
        except ValueError:
            t_min, t_max = 20.0, 50.0

        self.canvas.set_scale_range(is_auto, t_min, t_max)

    def save_png_snapshot(self) -> None:
        if self.canvas.display_photo is None or self.latest_temp_array is None:
            messagebox.showwarning("Snapshot", "No thermal frame available to save.", parent=self.window)
            return

        default_name = f"seek_thermal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = filedialog.asksaveasfilename(
            parent=self.window,
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png")],
            initialfile=default_name,
        )
        if filepath:
            # Render a high-resolution export of the colorized map with colorbar
            norm = np.clip((self.latest_temp_array - np.min(self.latest_temp_array)) / max(1.0, np.ptp(self.latest_temp_array)) * 255.0, 0, 255).astype(np.uint8)
            pal = COLORMAP_DICT.get(self.canvas.palette_name, cv2.COLORMAP_INFERNO)
            colored = cv2.applyColorMap(norm, pal) if pal is not None else cv2.cvtColor(norm, cv2.COLOR_GRAY2BGR)
            cv2.imwrite(filepath, colored)
            self.status_var.set(f"Saved PNG snapshot: {os.path.basename(filepath)}")

    def export_csv_matrix(self) -> None:
        """Export the exact 320x240 float matrix of temperatures in Celsius to CSV."""
        if self.latest_temp_array is None:
            messagebox.showwarning("Export", "No radiometric temperature data available.", parent=self.window)
            return

        default_name = f"radiometric_temps_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = filedialog.asksaveasfilename(
            parent=self.window,
            defaultextension=".csv",
            filetypes=[("CSV Temperature Matrix", "*.csv")],
            initialfile=default_name,
        )
        if filepath:
            np.savetxt(filepath, self.latest_temp_array, delimiter=",", fmt="%.2f")
            self.status_var.set(f"Exported temperature CSV: {os.path.basename(filepath)}")

    def export_npy_array(self) -> None:
        """Export raw float32 NumPy array for scientific processing."""
        if self.latest_temp_array is None:
            messagebox.showwarning("Export", "No radiometric temperature data available.", parent=self.window)
            return

        default_name = f"radiometric_temps_{datetime.now().strftime('%Y%m%d_%H%M%S')}.npy"
        filepath = filedialog.asksaveasfilename(
            parent=self.window,
            defaultextension=".npy",
            filetypes=[("NumPy Array", "*.npy")],
            initialfile=default_name,
        )
        if filepath:
            np.save(filepath, self.latest_temp_array)
            self.status_var.set(f"Exported NumPy array: {os.path.basename(filepath)}")

    def _poll_camera_frames(self) -> None:
        if self._closing:
            return
        try:
            if not self.window.winfo_exists():
                return
        except tk.TclError:
            return

        try:
            temp_c = self.frame_queue.get_nowait()
            self.latest_temp_array = temp_c
            self.canvas.set_radiometric_frame(temp_c)

            if self.worker and self.worker.connected:
                # Update telemetry readouts
                self.max_temp_lbl.config(text=f"{self.worker.max_temp_c:.1f} °C")
                self.min_temp_lbl.config(text=f"{self.worker.min_temp_c:.1f} °C")
                self.mean_temp_lbl.config(text=f"{self.worker.mean_temp_c:.1f} °C")

                mode_str = "[MOCK SIMULATION] " if getattr(self.worker, "is_mock", False) else ""
                self.status_var.set(
                    f"{mode_str}Seek {self.worker.cam_model} ({self.worker.cam_id}) | "
                    f"Sensor: {temp_c.shape[1]}x{temp_c.shape[0]} | {self.worker.fps} FPS | "
                    f"Max: {self.worker.max_temp_c:.1f}°C | Min: {self.worker.min_temp_c:.1f}°C | "
                    f"Zoom: {self.canvas.zoom_scale:.2f}x"
                )
        except queue.Empty:
            if self.worker is not None and not self.worker.connected and not self.worker.is_alive():
                self.status_var.set("Seek Thermal InspectionCAM disconnected or not found.")

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

        if self.worker is not None:
            self.worker.stop(join_timeout=3.0)
            self.worker = None

        try:
            self.window.destroy()
        except tk.TclError:
            pass

    def run(self) -> None:
        if self.parent is None:
            self.window.mainloop()


def main() -> int:
    parser = argparse.ArgumentParser(description="Seek Thermal InspectionCAM Standalone Viewer")
    parser.add_argument("--mock", action="store_true", help="Force synthetic thermal simulation stream")
    args = parser.parse_args()

    app = SeekThermalViewerWindow(parent=None, fallback_to_mock=True)
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
