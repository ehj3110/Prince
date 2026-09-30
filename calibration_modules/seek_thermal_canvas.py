"""
Interactive Radiometric Thermal Canvas for Seek Thermal InspectionCAM.
File: calibration_modules/seek_thermal_canvas.py

Features:
- Cursor-anchored Zoom & Pan
- Real-time spot temperature probing under cursor
- Pinned spot marker with temperature readout
- Min / Max thermal point tracking
- False-color palette mapping (Inferno, Turbo, Viridis, Plasma, Jet, etc.)
- Vertical temperature colorbar legend
"""

from __future__ import annotations

import tkinter as tk
from typing import Callable, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageTk


COLORMAP_DICT = {
    "Inferno": cv2.COLORMAP_INFERNO,
    "Turbo": cv2.COLORMAP_TURBO,
    "Viridis": cv2.COLORMAP_VIRIDIS,
    "Plasma": cv2.COLORMAP_PLASMA,
    "Jet": cv2.COLORMAP_JET,
    "Hot": cv2.COLORMAP_HOT,
    "White Hot": None,
    "Black Hot": "INVERTED_GRAY",
}


class SeekThermalCanvas(tk.Canvas):
    """
    Tkinter Canvas specialized for radiometric thermal imagery.
    Takes 2D float32 arrays in Celsius and renders interactive colorized frames.
    """

    def __init__(self, parent, on_probe_update: Optional[Callable[[float, int, int], None]] = None, **kwargs):
        kwargs.setdefault("bg", "#0d0d0d")
        kwargs.setdefault("highlightthickness", 0)
        super().__init__(parent, **kwargs)

        self.on_probe_update = on_probe_update
        self.raw_temp_c: Optional[np.ndarray] = None
        self.display_photo: Optional[ImageTk.PhotoImage] = None
        self.colorbar_photo: Optional[ImageTk.PhotoImage] = None

        # Transformation
        self.zoom_scale = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._view_initialized = False

        # Display Options
        self.palette_name = "Inferno"
        self.auto_scale = True
        self.manual_t_min = 20.0
        self.manual_t_max = 50.0

        # Overlays
        self.show_min_max = True
        self.show_center_crosshair = False
        self.show_colorbar = True
        self.hover_probe_active = True

        # Pinned probe coordinate on sensor (px, py)
        self.pinned_probe: Optional[Tuple[int, int]] = None
        self.cursor_probe_temp: Optional[float] = None
        self.cursor_sensor_pos: Optional[Tuple[int, int]] = None

        # Mouse Bindings
        self.bind("<ButtonPress-1>", self._on_mouse_down)
        self.bind("<B1-Motion>", self._on_pan_drag)
        self.bind("<Motion>", self._on_mouse_motion)
        self.bind("<MouseWheel>", self._on_zoom_wheel)
        self.bind("<Button-4>", self._on_zoom_wheel)
        self.bind("<Button-5>", self._on_zoom_wheel)
        self.bind("<Double-Button-1>", lambda _e: self.reset_view())
        self.bind("<ButtonPress-3>", self._on_right_click_pin)  # Right click to drop/clear pinned probe
        self.bind("<Configure>", self._on_configure)

    def set_palette(self, name: str) -> None:
        if name in COLORMAP_DICT:
            self.palette_name = name
            self.redraw()

    def set_scale_range(self, auto: bool, t_min: float = 20.0, t_max: float = 50.0) -> None:
        self.auto_scale = auto
        self.manual_t_min = float(t_min)
        self.manual_t_max = float(t_max)
        self.redraw()

    def set_radiometric_frame(self, temp_c: np.ndarray) -> None:
        """Receive new 2D float32 temperature frame."""
        self.raw_temp_c = temp_c
        if not self._view_initialized:
            self.reset_view()
            self._view_initialized = True
        else:
            self.redraw()

    def reset_view(self) -> None:
        if self.raw_temp_c is None:
            return
        cw = max(1, self.winfo_width())
        ch = max(1, self.winfo_height())
        # Account for colorbar space on right (60px)
        eff_cw = max(1, cw - (70 if self.show_colorbar else 0))
        ih, iw = self.raw_temp_c.shape[:2]

        scale = min(eff_cw / iw, ch / ih) * 0.92
        self.zoom_scale = scale
        self.pan_x = (eff_cw - iw * scale) / 2.0
        self.pan_y = (ch - ih * scale) / 2.0
        self.redraw()

    def set_one_to_one(self) -> None:
        if self.raw_temp_c is None:
            return
        cw = max(1, self.winfo_width())
        ch = max(1, self.winfo_height())
        eff_cw = max(1, cw - (70 if self.show_colorbar else 0))
        ih, iw = self.raw_temp_c.shape[:2]

        self.zoom_scale = 1.0
        self.pan_x = (eff_cw - iw) / 2.0
        self.pan_y = (ch - ih) / 2.0
        self.redraw()

    def _on_configure(self, _e) -> None:
        if not self._view_initialized and self.raw_temp_c is not None:
            self.reset_view()
            self._view_initialized = True
        else:
            self.redraw()

    def _on_mouse_down(self, event):
        self._drag_start_x = event.x
        self._drag_start_y = event.y

    def _on_pan_drag(self, event):
        dx = event.x - self._drag_start_x
        dy = event.y - self._drag_start_y
        self.pan_x += dx
        self.pan_y += dy
        self._drag_start_x = event.x
        self._drag_start_y = event.y
        self.redraw()

    def _on_zoom_wheel(self, event):
        if self.raw_temp_c is None:
            return

        factor = 0.85 if (event.num == 5 or getattr(event, "delta", 0) < 0) else 1.15
        new_scale = max(0.2, min(self.zoom_scale * factor, 25.0))
        actual_k = new_scale / self.zoom_scale

        mx, my = event.x, event.y
        self.pan_x = mx - actual_k * (mx - self.pan_x)
        self.pan_y = my - actual_k * (my - self.pan_y)
        self.zoom_scale = new_scale
        self.redraw()

    def _canvas_to_sensor(self, cx: int, cy: int) -> Optional[Tuple[int, int]]:
        """Map canvas screen coordinate to sensor pixel coordinate."""
        if self.raw_temp_c is None or self.zoom_scale <= 0:
            return None
        sx = int((cx - self.pan_x) / self.zoom_scale)
        sy = int((cy - self.pan_y) / self.zoom_scale)
        ih, iw = self.raw_temp_c.shape[:2]
        if 0 <= sx < iw and 0 <= sy < ih:
            return (sx, sy)
        return None

    def _sensor_to_canvas(self, sx: float, sy: float) -> Tuple[int, int]:
        """Map sensor pixel coordinate to canvas screen coordinate."""
        cx = int(self.pan_x + sx * self.zoom_scale)
        cy = int(self.pan_y + sy * self.zoom_scale)
        return (cx, cy)

    def _on_mouse_motion(self, event):
        if self.raw_temp_c is None:
            return
        sensor_pt = self._canvas_to_sensor(event.x, event.y)
        if sensor_pt is not None:
            sx, sy = sensor_pt
            temp_val = float(self.raw_temp_c[sy, sx])
            self.cursor_probe_temp = temp_val
            self.cursor_sensor_pos = (sx, sy)
            if self.on_probe_update:
                self.on_probe_update(temp_val, sx, sy)
        else:
            self.cursor_probe_temp = None
            self.cursor_sensor_pos = None

    def _on_right_click_pin(self, event):
        """Pin or unpin spot probe with right click."""
        sensor_pt = self._canvas_to_sensor(event.x, event.y)
        if sensor_pt is not None:
            if self.pinned_probe == sensor_pt:
                self.pinned_probe = None
            else:
                self.pinned_probe = sensor_pt
            self.redraw()

    def clear_pinned_probe(self):
        self.pinned_probe = None
        self.redraw()

    def redraw(self) -> None:
        if self.raw_temp_c is None:
            return

        cw = self.winfo_width()
        ch = self.winfo_height()
        if cw < 20 or ch < 20:
            return

        temp = self.raw_temp_c
        ih, iw = temp.shape[:2]

        # Determine temperature scale bounds
        if self.auto_scale:
            t_min = float(np.min(temp))
            t_max = float(np.max(temp))
            if t_max - t_min < 1.0:
                t_max = t_min + 1.0
        else:
            t_min = self.manual_t_min
            t_max = max(self.manual_t_min + 1.0, self.manual_t_max)

        # 1. Normalize temperature into 0-255 uint8
        norm = np.clip((temp - t_min) / (t_max - t_min) * 255.0, 0, 255).astype(np.uint8)

        # 2. Apply False Color Palette
        palette_mode = COLORMAP_DICT.get(self.palette_name, cv2.COLORMAP_INFERNO)
        if palette_mode is None:
            color_img = cv2.cvtColor(norm, cv2.COLOR_GRAY2RGB)
        elif palette_mode == "INVERTED_GRAY":
            color_img = cv2.cvtColor(255 - norm, cv2.COLOR_GRAY2RGB)
        else:
            color_bgr = cv2.applyColorMap(norm, palette_mode)
            color_img = cv2.cvtColor(color_bgr, cv2.COLOR_BGR2RGB)

        # 3. Viewport ROI Slicing
        x0_img = int(max(0, -self.pan_x / self.zoom_scale))
        y0_img = int(max(0, -self.pan_y / self.zoom_scale))
        x1_img = int(min(iw, (cw - self.pan_x) / self.zoom_scale))
        y1_img = int(min(ih, (ch - self.pan_y) / self.zoom_scale))

        if x1_img <= x0_img or y1_img <= y0_img:
            self.delete("all")
            return

        roi = color_img[y0_img:y1_img, x0_img:x1_img]
        out_w = max(1, int((x1_img - x0_img) * self.zoom_scale))
        out_h = max(1, int((y1_img - y0_img) * self.zoom_scale))

        interp = cv2.INTER_NEAREST if self.zoom_scale > 2.0 else cv2.INTER_LINEAR
        resized_roi = cv2.resize(roi, (out_w, out_h), interpolation=interp)

        dest_x = int(self.pan_x + x0_img * self.zoom_scale)
        dest_y = int(self.pan_y + y0_img * self.zoom_scale)

        pil_img = Image.fromarray(resized_roi)
        self.display_photo = ImageTk.PhotoImage(pil_img)

        self.delete("all")
        self.create_image(dest_x, dest_y, anchor=tk.NW, image=self.display_photo)

        # 4. Min/Max Markers
        if self.show_min_max:
            # Hot spot
            max_idx = np.unravel_index(np.argmax(temp), temp.shape)
            hot_cx, hot_cy = self._sensor_to_canvas(max_idx[1] + 0.5, max_idx[0] + 0.5)
            hot_t = float(temp[max_idx])
            self._draw_reticle(hot_cx, hot_cy, f"MAX {hot_t:.1f}°C", color="#FF3333")

            # Cold spot
            min_idx = np.unravel_index(np.argmin(temp), temp.shape)
            cold_cx, cold_cy = self._sensor_to_canvas(min_idx[1] + 0.5, min_idx[0] + 0.5)
            cold_t = float(temp[min_idx])
            self._draw_reticle(cold_cx, cold_cy, f"MIN {cold_t:.1f}°C", color="#3399FF")

        # 5. Pinned Probe
        if self.pinned_probe is not None:
            px, py = self.pinned_probe
            if 0 <= px < iw and 0 <= py < ih:
                pin_cx, pin_cy = self._sensor_to_canvas(px + 0.5, py + 0.5)
                pin_t = float(temp[py, px])
                self._draw_reticle(pin_cx, pin_cy, f"PIN: {pin_t:.1f}°C ({px},{py})", color="#FFDD00")

        # 6. Center Crosshair
        if self.show_center_crosshair:
            center_x, center_y = self._sensor_to_canvas(iw / 2.0, ih / 2.0)
            self.create_line(center_x - 20, center_y, center_x + 20, center_y, fill="#00FF66", width=1)
            self.create_line(center_x, center_y - 20, center_x, center_y + 20, fill="#00FF66", width=1)

        # 7. Vertical Temperature Colorbar
        if self.show_colorbar:
            self._draw_colorbar(cw, ch, t_min, t_max, palette_mode)

    def _draw_reticle(self, cx: int, cy: int, label: str, color: str) -> None:
        r = 6
        self.create_line(cx - r - 3, cy, cx + r + 3, cy, fill=color, width=2)
        self.create_line(cx, cy - r - 3, cx, cy + r + 3, fill=color, width=2)
        self.create_oval(cx - r, cy - r, cx + r, cy + r, outline=color, width=2)
        # Text label background and text
        self.create_text(cx + 12, cy - 2, text=label, fill=color, anchor=tk.W, font=("Arial", 9, "bold"))

    def _draw_colorbar(self, cw: int, ch: int, t_min: float, t_max: float, palette_mode) -> None:
        bar_w = 18
        bar_h = min(ch - 60, 320)
        if bar_h < 50:
            return

        bar_x = cw - 65
        bar_y = (ch - bar_h) // 2

        # Generate gradient column (t_max at top to t_min at bottom)
        grad = np.linspace(255, 0, bar_h, dtype=np.uint8).reshape((bar_h, 1))
        grad_bar = np.repeat(grad, bar_w, axis=1)

        if palette_mode is None:
            cbar_img = cv2.cvtColor(grad_bar, cv2.COLOR_GRAY2RGB)
        elif palette_mode == "INVERTED_GRAY":
            cbar_img = cv2.cvtColor(255 - grad_bar, cv2.COLOR_GRAY2RGB)
        else:
            cbar_bgr = cv2.applyColorMap(grad_bar, palette_mode)
            cbar_img = cv2.cvtColor(cbar_bgr, cv2.COLOR_BGR2RGB)

        pil_bar = Image.fromarray(cbar_img)
        self.colorbar_photo = ImageTk.PhotoImage(pil_bar)
        self.create_image(bar_x, bar_y, anchor=tk.NW, image=self.colorbar_photo)
        self.create_rectangle(bar_x - 1, bar_y - 1, bar_x + bar_w + 1, bar_y + bar_h + 1, outline="#555", width=1)

        # Labels
        self.create_text(bar_x + bar_w + 5, bar_y, text=f"{t_max:.1f}°C", fill="#FFFFFF", anchor=tk.NW, font=("Arial", 8))
        self.create_text(bar_x + bar_w + 5, bar_y + bar_h // 2, text=f"{(t_min + t_max) / 2.0:.1f}°C", fill="#AAAAAA", anchor=tk.W, font=("Arial", 8))
        self.create_text(bar_x + bar_w + 5, bar_y + bar_h, text=f"{t_min:.1f}°C", fill="#FFFFFF", anchor=tk.SW, font=("Arial", 8))
