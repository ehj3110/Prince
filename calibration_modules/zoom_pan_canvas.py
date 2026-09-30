"""
Interactive Zoom and Pan Canvas for camera / static image preview.

ROI-first pipeline: crop visible region → contrast/brightness/gamma → resize.
"""

from __future__ import annotations

import tkinter as tk
from typing import Optional

import cv2
import numpy as np
from PIL import Image, ImageTk


class ZoomPanCanvas(tk.Canvas):
    def __init__(self, parent, **kwargs):
        kwargs.setdefault("bg", "#1a1a1a")
        kwargs.setdefault("highlightthickness", 0)
        super().__init__(parent, **kwargs)

        self.raw_image: Optional[np.ndarray] = None
        self.display_photo: Optional[ImageTk.PhotoImage] = None
        self._image_item: Optional[int] = None
        self._crosshair_items: list = []

        self.zoom_scale = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._view_initialized = False

        self.contrast_alpha = 1.0
        self.brightness_beta = 0
        self.gamma_val = 1.0
        self.show_crosshair = True
        self._gamma_lut = self._build_gamma_lut(1.0)

        self.bind("<ButtonPress-1>", self._on_pan_start)
        self.bind("<B1-Motion>", self._on_pan_drag)
        self.bind("<MouseWheel>", self._on_zoom_wheel)
        self.bind("<Button-4>", self._on_zoom_wheel)
        self.bind("<Button-5>", self._on_zoom_wheel)
        self.bind("<Double-Button-1>", lambda _e: self.reset_view())
        self.bind("<Configure>", self._on_configure)

    @staticmethod
    def _build_gamma_lut(gamma: float) -> np.ndarray:
        inv_gamma = 1.0 / max(0.01, float(gamma))
        table = np.array(
            [((i / 255.0) ** inv_gamma) * 255 for i in range(256)],
            dtype=np.uint8,
        )
        return table

    def set_gamma(self, gamma: float) -> None:
        self.gamma_val = float(gamma)
        self._gamma_lut = self._build_gamma_lut(self.gamma_val)
        self.redraw()

    def set_contrast_brightness(self, alpha: float, beta: int) -> None:
        self.contrast_alpha = float(alpha)
        self.brightness_beta = int(beta)
        self.redraw()

    def set_raw_frame(self, image: np.ndarray) -> None:
        if image is None:
            return
        if image.ndim == 3 and image.shape[2] == 1:
            image = image[:, :, 0]
        self.raw_image = image
        if not self._view_initialized:
            self.reset_view()
            self._view_initialized = True
        else:
            self.redraw()

    def reset_view(self) -> None:
        if self.raw_image is None:
            return
        cw = max(1, self.winfo_width())
        ch = max(1, self.winfo_height())
        ih, iw = self.raw_image.shape[:2]
        scale = min(cw / iw, ch / ih) * 0.95
        self.zoom_scale = scale
        self.pan_x = (cw - iw * scale) / 2.0
        self.pan_y = (ch - ih * scale) / 2.0
        self.redraw()

    def set_one_to_one(self) -> None:
        if self.raw_image is None:
            return
        cw = max(1, self.winfo_width())
        ch = max(1, self.winfo_height())
        ih, iw = self.raw_image.shape[:2]
        self.zoom_scale = 1.0
        self.pan_x = (cw - iw) / 2.0
        self.pan_y = (ch - ih) / 2.0
        self.redraw()

    def _on_configure(self, _event) -> None:
        if self.raw_image is not None:
            self.redraw()

    def _on_pan_start(self, event) -> None:
        self._drag_start_x = event.x
        self._drag_start_y = event.y

    def _on_pan_drag(self, event) -> None:
        dx = event.x - self._drag_start_x
        dy = event.y - self._drag_start_y
        self.pan_x += dx
        self.pan_y += dy
        self._drag_start_x = event.x
        self._drag_start_y = event.y
        self.redraw()

    def _on_zoom_wheel(self, event) -> None:
        if self.raw_image is None:
            return
        if getattr(event, "num", None) == 5 or getattr(event, "delta", 0) < 0:
            factor = 0.85
        else:
            factor = 1.15
        new_scale = max(0.05, min(self.zoom_scale * factor, 15.0))
        actual_k = new_scale / self.zoom_scale if self.zoom_scale else 1.0
        mx, my = event.x, event.y
        self.pan_x = mx - actual_k * (mx - self.pan_x)
        self.pan_y = my - actual_k * (my - self.pan_y)
        self.zoom_scale = new_scale
        self.redraw()

    def _apply_filters(self, roi: np.ndarray) -> np.ndarray:
        proc = roi
        if self.contrast_alpha != 1.0 or self.brightness_beta != 0:
            proc = cv2.convertScaleAbs(proc, alpha=self.contrast_alpha, beta=self.brightness_beta)
        if self.gamma_val != 1.0:
            proc = cv2.LUT(proc, self._gamma_lut)
        return proc

    def redraw(self) -> None:
        if self.raw_image is None:
            return
        cw = self.winfo_width()
        ch = self.winfo_height()
        if cw < 10 or ch < 10:
            return

        ih, iw = self.raw_image.shape[:2]
        z = self.zoom_scale if self.zoom_scale > 1e-9 else 1.0

        x0_img = int(max(0, -self.pan_x / z))
        y0_img = int(max(0, -self.pan_y / z))
        x1_img = int(min(iw, (cw - self.pan_x) / z))
        y1_img = int(min(ih, (ch - self.pan_y) / z))
        if x1_img <= x0_img or y1_img <= y0_img:
            return

        roi = self.raw_image[y0_img:y1_img, x0_img:x1_img]
        proc = self._apply_filters(roi)

        out_w = max(1, int((x1_img - x0_img) * z))
        out_h = max(1, int((y1_img - y0_img) * z))
        # Cap extreme canvas sizes from resize glitches
        out_w = min(out_w, cw * 2)
        out_h = min(out_h, ch * 2)

        interp = cv2.INTER_NEAREST if z > 1.5 else cv2.INTER_LINEAR
        resized = cv2.resize(proc, (out_w, out_h), interpolation=interp)

        dest_x = int(self.pan_x + x0_img * z)
        dest_y = int(self.pan_y + y0_img * z)

        pil_img = Image.fromarray(resized)
        self.display_photo = ImageTk.PhotoImage(pil_img)

        if self._image_item is None:
            self._image_item = self.create_image(dest_x, dest_y, anchor=tk.NW, image=self.display_photo)
        else:
            self.coords(self._image_item, dest_x, dest_y)
            self.itemconfig(self._image_item, image=self.display_photo)

        for item in self._crosshair_items:
            self.delete(item)
        self._crosshair_items.clear()

        if self.show_crosshair:
            center_x = int(self.pan_x + (iw / 2.0) * z)
            center_y = int(self.pan_y + (ih / 2.0) * z)
            cross_size = 30
            self._crosshair_items.append(
                self.create_line(
                    center_x - cross_size, center_y, center_x + cross_size, center_y,
                    fill="#00FF66", width=1,
                )
            )
            self._crosshair_items.append(
                self.create_line(
                    center_x, center_y - cross_size, center_x, center_y + cross_size,
                    fill="#00FF66", width=1,
                )
            )
            self._crosshair_items.append(
                self.create_oval(
                    center_x - 10, center_y - 10, center_x + 10, center_y + 10,
                    outline="#00FF66", width=1,
                )
            )


def _demo_main() -> None:
    """Offline demo: load a static PNG and exercise pan/zoom/filters."""
    import os
    from pathlib import Path
    from tkinter import ttk

    root = tk.Tk()
    root.title("ZoomPanCanvas Offline Demo (Sub-phase 1C)")
    root.geometry("1100x750")

    candidates = [
        Path("physical_hardware_test.png"),
        Path("stream_smoke_test.png"),
        Path(__file__).resolve().parent.parent / "physical_hardware_test.png",
    ]
    img_path = next((p for p in candidates if p.is_file()), None)
    if img_path is None:
        # Synthetic test pattern if no capture available
        yy, xx = np.mgrid[0:2064, 0:2464]
        synth = ((xx // 16) % 2) * 180 + ((yy // 16) % 2) * 40
        synth = np.clip(synth, 0, 255).astype(np.uint8)
        image = synth
        status = "Loaded synthetic 2464x2064 pattern (no PNG found)"
    else:
        image = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise SystemExit(f"Failed to read {img_path}")
        status = f"Loaded {img_path} shape={image.shape}"

    root.columnconfigure(0, weight=4)
    root.columnconfigure(1, weight=1)
    root.rowconfigure(0, weight=1)

    canvas = ZoomPanCanvas(root)
    canvas.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

    panel = ttk.Frame(root, padding=10)
    panel.grid(row=0, column=1, sticky="nsew")

    ttk.Button(panel, text="Fit View", command=canvas.reset_view).pack(fill=tk.X, pady=2)
    ttk.Button(panel, text="1:1 (100%)", command=canvas.set_one_to_one).pack(fill=tk.X, pady=2)

    cross_var = tk.BooleanVar(value=True)

    def toggle_cross():
        canvas.show_crosshair = cross_var.get()
        canvas.redraw()

    ttk.Checkbutton(panel, text="Show Center Crosshair", variable=cross_var, command=toggle_cross).pack(
        anchor=tk.W, pady=6
    )

    ttk.Label(panel, text="Contrast").pack(anchor=tk.W)
    contrast = ttk.Scale(panel, from_=0.2, to=3.0, orient=tk.HORIZONTAL)
    contrast.set(1.0)
    contrast.pack(fill=tk.X)

    ttk.Label(panel, text="Brightness").pack(anchor=tk.W, pady=(8, 0))
    brightness = ttk.Scale(panel, from_=-100, to=100, orient=tk.HORIZONTAL)
    brightness.set(0)
    brightness.pack(fill=tk.X)

    ttk.Label(panel, text="Gamma").pack(anchor=tk.W, pady=(8, 0))
    gamma = ttk.Scale(panel, from_=0.2, to=3.0, orient=tk.HORIZONTAL)
    gamma.set(1.0)
    gamma.pack(fill=tk.X)

    def update_filters(_=None):
        canvas.set_contrast_brightness(float(contrast.get()), int(float(brightness.get())))
        canvas.set_gamma(float(gamma.get()))

    contrast.configure(command=update_filters)
    brightness.configure(command=update_filters)
    gamma.configure(command=update_filters)

    status_var = tk.StringVar(value=status)
    ttk.Label(root, textvariable=status_var, relief=tk.SUNKEN, anchor=tk.W).grid(
        row=1, column=0, columnspan=2, sticky="ew"
    )

    def load_after_map():
        canvas.set_raw_frame(image)
        status_var.set(f"{status} | zoom={canvas.zoom_scale:.2f}x")

    root.after(50, load_after_map)
    root.mainloop()


if __name__ == "__main__":
    _demo_main()
