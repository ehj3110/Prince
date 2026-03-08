# -*- coding: utf-8 -*-
"""
Image Modification Window

GUI for SLA image processing: edge enhancement, global blur enhancement,
padding normalization. Provides Preview and Build functionality.
"""

import os
import re
import glob
import threading
from pathlib import Path

from tkinter import Toplevel, Frame, Label, Entry, Button, Checkbutton, BooleanVar, StringVar, Radiobutton
from tkinter import ttk, filedialog, messagebox, font as tkFont

# Ensure project root is on sys.path so 'support_modules' is importable
# whether this file is run directly or imported as a module.
import sys as _sys
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in _sys.path:
    _sys.path.insert(0, _project_root)

import cv2
import numpy as np

from support_modules.image_modification.processor import (
    process_single_for_preview,
    process_folder,
)
try:
    from support_modules.DefinitionsWindow import DefinitionsWindow
    HAS_DEFINITIONS = True
except ImportError:
    HAS_DEFINITIONS = False

PREVIEW_MAX_SIZE = (640, 400)  # Full image downscaled to fit; preserves aspect ratio


def _natural_sort_key(filepath):
    match = re.search(r'\d+', os.path.basename(filepath))
    return int(match.group()) if match else 0


def _get_sorted_images(folder_path):
    """Get PNG files sorted naturally, excluding *_1.png padding outputs."""
    if not folder_path or not os.path.isdir(folder_path):
        return []
    pattern = os.path.join(folder_path, '*.png')
    files = glob.glob(pattern)
    # Exclude padding-style files (e.g., 5_1.png)
    files = [f for f in files if not (re.match(r'.*\d+_\d+\.png$', f))]
    return sorted(files, key=_natural_sort_key)


def _cv2_to_photoimage(img_bgr_or_gray, max_size=PREVIEW_MAX_SIZE):
    """Convert cv2 image to tkinter PhotoImage. Uses cv2+base64 (no PIL needed)."""
    import base64
    import tkinter as _tk
    if img_bgr_or_gray is None:
        return None
    if len(img_bgr_or_gray.shape) == 2:
        img_bgr = cv2.cvtColor(img_bgr_or_gray, cv2.COLOR_GRAY2BGR)
    else:
        img_bgr = img_bgr_or_gray

    h, w = img_bgr.shape[:2]
    if w > max_size[0] or h > max_size[1]:
        scale = min(max_size[0] / w, max_size[1] / h)
        img_bgr = cv2.resize(img_bgr, (int(w * scale), int(h * scale)),
                             interpolation=cv2.INTER_AREA)
    try:
        _, buf = cv2.imencode('.png', img_bgr)
        b64 = base64.b64encode(buf.tobytes())
        return _tk.PhotoImage(data=b64)
    except Exception:
        return None


class ImageModificationWindow:
    def __init__(self, master_window, update_status_callback=None, prince_main_app_ref=None):
        self.master = master_window
        self.update_status = update_status_callback or (lambda msg, err=False: print(msg))
        self.prince_main_app_ref = prince_main_app_ref

        self.image_files = []
        self.current_image_path = None
        self.current_photo = None  # Keep reference to prevent GC
        self._build_thread = None

        self.window = Toplevel(master_window)
        self.window.title("Image Modification")
        self.window.geometry("750x970")
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

        control_font = tkFont.Font(family="Helvetica", size=11)
        title_font = tkFont.Font(family="Helvetica", size=20, weight="bold")

        # --- Header ---
        top_frame = Frame(self.window)
        top_frame.pack(side="top", fill="x", padx=10, pady=(5, 0))

        Label(top_frame, text="Image Modification", font=title_font).pack(side="left", padx=(0, 10))
        if HAS_DEFINITIONS:
            Button(top_frame, text="Definitions",
                   command=self._open_definitions,
                   font=tkFont.Font(family="Helvetica", size=9)).pack(side="left", padx=(0, 10))
        credit = "Professor Cheng Sun, Evan Jones"
        Label(top_frame, text=credit, font=tkFont.Font(family="Helvetica", size=7)).pack(side="right")

        # --- File path ---
        path_frame = Frame(self.window)
        path_frame.pack(side="top", fill="x", padx=10, pady=(10, 5))
        Label(path_frame, text="Folder:", font=control_font).pack(side="left", padx=(0, 5))
        self.folder_entry = Entry(path_frame, font=control_font)
        self.folder_entry.pack(side="left", expand=True, fill="x", padx=(0, 5))
        self.folder_entry.bind("<Return>", lambda e: self._load_layer())
        Button(path_frame, text="Browse", command=self._browse_folder, font=control_font).pack(side="left")

        # --- Layer number + Load ---
        layer_frame = Frame(self.window)
        layer_frame.pack(side="top", fill="x", padx=10, pady=(2, 5))
        Label(layer_frame, text="Layer:", font=control_font).pack(side="left", padx=(0, 5))
        self.layer_var = StringVar(value="1")
        self.layer_entry = Entry(layer_frame, textvariable=self.layer_var, width=6, font=control_font)
        self.layer_entry.pack(side="left", padx=(0, 5))
        self.layer_entry.bind("<Return>", lambda e: self._load_layer())
        self.layer_count_label = Label(layer_frame, text="(1-N)", font=control_font)
        self.layer_count_label.pack(side="left", padx=(0, 10))
        Button(layer_frame, text="Load", command=self._load_layer, font=control_font).pack(side="left")

        # --- Image preview ---
        preview_frame = Frame(self.window, relief="groove", borderwidth=2)
        preview_frame.pack(side="top", padx=10, pady=(5, 10))
        # No width/height on Label - it sizes to the image; char units would clip the display
        self.preview_label = Label(preview_frame, text="No image loaded",
                                   bg="#333", fg="white", font=control_font)
        self.preview_label.pack(padx=5, pady=5)

        # --- Section 1: Edge Enhancement ---
        ee_frame = ttk.LabelFrame(self.window, text="Edge Enhancement", padding=(10, 5))
        ee_frame.pack(side="top", fill="x", padx=10, pady=(0, 5))
        self.ee_var = BooleanVar(value=True)
        ttk.Checkbutton(ee_frame, text="Enable", variable=self.ee_var).pack(side="left", padx=(0, 15))
        Label(ee_frame, text="Blur:", font=control_font).pack(side="left", padx=(0, 5))
        self.blur_var = StringVar(value="25")
        Entry(ee_frame, textvariable=self.blur_var, width=6, font=control_font).pack(side="left", padx=(0, 10))
        Label(ee_frame, text="Falloff:", font=control_font).pack(side="left", padx=(0, 5))
        self.ee_falloff_var = StringVar(value="101")
        Entry(ee_frame, textvariable=self.ee_falloff_var, width=6, font=control_font).pack(side="left", padx=(0, 10))
        Label(ee_frame, text="Min:", font=control_font).pack(side="left", padx=(10, 5))
        self.min_var = StringVar(value="100")
        Entry(ee_frame, textvariable=self.min_var, width=5, font=control_font).pack(side="left", padx=(0, 5))
        Label(ee_frame, text="Max:", font=control_font).pack(side="left", padx=(5, 5))
        self.max_var = StringVar(value="255")
        Entry(ee_frame, textvariable=self.max_var, width=5, font=control_font).pack(side="left")

        # --- Section 2: Global Enhancement ---
        ge_frame = ttk.LabelFrame(self.window, text="Global Blur Enhancement", padding=(10, 5))
        ge_frame.pack(side="top", fill="x", padx=10, pady=(0, 5))
        ge_row1 = ttk.Frame(ge_frame)
        ge_row1.pack(side="top", fill="x")
        self.ge_var = BooleanVar(value=False)
        ttk.Checkbutton(ge_row1, text="Enable", variable=self.ge_var).pack(side="left", padx=(0, 15))
        Label(ge_row1, text="Globe ratio:", font=control_font).pack(side="left", padx=(0, 5))
        self.globe_var = StringVar(value="0.8")
        Entry(ge_row1, textvariable=self.globe_var, width=6, font=control_font).pack(side="left", padx=(0, 10))
        Label(ge_row1, text="Sigma:", font=control_font).pack(side="left", padx=(10, 5))
        self.sigma_var = StringVar(value="6.0")
        Entry(ge_row1, textvariable=self.sigma_var, width=6, font=control_font).pack(side="left")
        ge_row2 = ttk.Frame(ge_frame)
        ge_row2.pack(side="top", fill="x", pady=(5, 0))
        self.ge_asymmetric_var = BooleanVar(value=False)
        ttk.Checkbutton(ge_row2, text="Asymmetric (4 quadrants, per-ray furthest white)", variable=self.ge_asymmetric_var).pack(side="left", padx=(0, 15))
        Label(ge_row2, text="Blend (°):", font=control_font).pack(side="left", padx=(0, 5))
        self.blend_angle_var = StringVar(value="20")
        Entry(ge_row2, textvariable=self.blend_angle_var, width=5, font=control_font).pack(side="left")

        # --- Section 3: Padding ---
        pad_frame = ttk.LabelFrame(self.window, text="Image Padding", padding=(10, 5))
        pad_frame.pack(side="top", fill="x", padx=10, pady=(0, 5))
        self.pad_var = BooleanVar(value=False)
        ttk.Checkbutton(pad_frame, text="Insert black padding after each image ({x}_1.png)", variable=self.pad_var).pack(anchor="w")

        # --- Section 5: Scattering Compensation ---
        sc_frame = ttk.LabelFrame(self.window, text="Scattering Compensation", padding=(10, 5))
        sc_frame.pack(side="top", fill="x", padx=10, pady=(0, 5))
        sc_row = ttk.Frame(sc_frame)
        sc_row.pack(side="top", fill="x")
        self.sc_var = BooleanVar(value=False)
        ttk.Checkbutton(sc_row, text="Enable", variable=self.sc_var).pack(side="left", padx=(0, 15))
        Label(sc_row, text="Blur:", font=control_font).pack(side="left", padx=(0, 5))
        self.sc_width_var = StringVar(value="15")
        Entry(sc_row, textvariable=self.sc_width_var, width=6, font=control_font).pack(side="left", padx=(0, 10))
        Label(sc_row, text="Falloff:", font=control_font).pack(side="left", padx=(0, 5))
        self.sc_falloff_var = StringVar(value="61")
        Entry(sc_row, textvariable=self.sc_falloff_var, width=6, font=control_font).pack(side="left", padx=(0, 10))
        Label(sc_row, text="Min:", font=control_font).pack(side="left", padx=(10, 5))
        self.sc_min_var = StringVar(value="127")
        Entry(sc_row, textvariable=self.sc_min_var, width=5, font=control_font).pack(side="left", padx=(0, 5))
        Label(sc_row, text="Max:", font=control_font).pack(side="left", padx=(5, 5))
        self.sc_max_var = StringVar(value="255")
        Entry(sc_row, textvariable=self.sc_max_var, width=5, font=control_font).pack(side="left")

        # --- Preview and Build buttons ---
        btn_frame = Frame(self.window)
        btn_frame.pack(side="top", padx=10, pady=(15, 10))
        self.preview_btn = Button(btn_frame, text="Preview", command=self._do_preview, font=control_font)
        self.preview_btn.pack(side="left", padx=(0, 10))
        self.build_btn = Button(btn_frame, text="Build", command=self._do_build, font=control_font)
        self.build_btn.pack(side="left", padx=(0, 10))
        self.status_label = Label(btn_frame, text="", font=control_font)
        self.status_label.pack(side="left", padx=(20, 0))

    def _open_definitions(self):
        DefinitionsWindow(self.window)

    def _browse_folder(self):
        path = filedialog.askdirectory(title="Select image folder")
        if path:
            self.folder_entry.delete(0, "end")
            self.folder_entry.insert(0, path)
            self._refresh_image_list()
            self._load_layer()

    def _refresh_image_list(self):
        folder = self.folder_entry.get().strip()
        self.image_files = _get_sorted_images(folder)
        n = len(self.image_files)
        self.layer_count_label.config(text=f"(1-{n})" if n > 0 else "(no images)")

    def _load_layer(self):
        self._refresh_image_list()
        if not self.image_files:
            self.update_status("No images found in folder.", error=True)
            messagebox.showerror("Error", "No PNG images found in folder.", parent=self.window)
            return
        try:
            layer = int(self.layer_var.get().strip())
        except ValueError:
            layer = 1
        if layer < 1:
            layer = 1
        if layer > len(self.image_files):
            layer = len(self.image_files)
        self.layer_var.set(str(layer))
        path = self.image_files[layer - 1]
        self.current_image_path = path
        self._display_image(path)

    def _display_image(self, path, processed_array=None):
        """Display image from path or from processed numpy array."""
        if processed_array is not None:
            img = processed_array
        else:
            img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            self.preview_label.config(image="", text="Could not load image")
            return
        self.current_photo = _cv2_to_photoimage(img)
        if self.current_photo is not None:
            self.preview_label.config(image=self.current_photo, text="")
        else:
            self.preview_label.config(image="", text="Install Pillow for image preview")

    def _get_params(self):
        """Get current params, with validation."""
        try:
            blur = float(self.blur_var.get().strip() or "25")
        except ValueError:
            blur = 25.0
        try:
            globe = float(self.globe_var.get().strip() or "0.8")
        except ValueError:
            globe = 0.8
        try:
            sigma = float(self.sigma_var.get().strip() or "6.0")
        except ValueError:
            sigma = 6.0
        try:
            blend_angle = float(self.blend_angle_var.get().strip() or "20")
        except ValueError:
            blend_angle = 20.0
        try:
            sc_width = float(self.sc_width_var.get().strip() or "15")
        except ValueError:
            sc_width = 15.0
        try:
            sc_min = float(self.sc_min_var.get().strip() or "127")
        except ValueError:
            sc_min = 127.0
        try:
            sc_max = float(self.sc_max_var.get().strip() or "255")
        except ValueError:
            sc_max = 255.0
        try:
            ee_falloff = int(self.ee_falloff_var.get().strip() or "101")
        except ValueError:
            ee_falloff = 101
        try:
            sc_falloff = int(self.sc_falloff_var.get().strip() or "61")
        except ValueError:
            sc_falloff = 61
        return blur, globe, sigma, blend_angle, sc_width, sc_min, sc_max, ee_falloff, sc_falloff

    def _do_preview(self):
        if not self.current_image_path or not os.path.isfile(self.current_image_path):
            messagebox.showwarning("Preview", "Load an image first (set folder and click Load).", parent=self.window)
            return
        blur, globe, sigma, blend_angle, sc_width, sc_min, sc_max, ee_falloff, sc_falloff = self._get_params()
        try:
            result = process_single_for_preview(
                self.current_image_path,
                edge_enabled=self.ee_var.get(),
                blurring=blur,
                global_enabled=self.ge_var.get(),
                globe=globe,
                sigma=sigma,
                global_asymmetric=self.ge_asymmetric_var.get(),
                blend_angle=blend_angle,
                scatter_enabled=self.sc_var.get(),
                scatter_width=sc_width,
                scatter_min_val=sc_min,
                scatter_max_val=sc_max,
                ee_falloff=ee_falloff,
                scatter_falloff=sc_falloff,
            )
            self._display_image(None, processed_array=result)
            self.update_status("Preview updated.")
        except Exception as e:
            messagebox.showerror("Preview Error", str(e), parent=self.window)
            self.update_status(f"Preview failed: {e}", error=True)

    def _do_build(self):
        folder = self.folder_entry.get().strip()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror("Build", "Select a valid folder first.", parent=self.window)
            return
        self._refresh_image_list()
        if not self.image_files:
            messagebox.showerror("Build", "No PNG images found in folder.", parent=self.window)
            return
        blur, globe, sigma, blend_angle, sc_width, sc_min, sc_max, ee_falloff, sc_falloff = self._get_params()

        def run_build():
            try:
                self.status_label.config(text="Processing...")
                self.preview_btn.config(state="disabled")
                self.build_btn.config(state="disabled")
                output = process_folder(
                    folder,
                    edge_enabled=self.ee_var.get(),
                    blurring=blur,
                    global_enabled=self.ge_var.get(),
                    globe=globe,
                    sigma=sigma,
                    padding_enabled=self.pad_var.get(),
                    global_asymmetric=self.ge_asymmetric_var.get(),
                    blend_angle=blend_angle,
                    scatter_enabled=self.sc_var.get(),
                    scatter_width=sc_width,
                    scatter_min_val=sc_min,
                    scatter_max_val=sc_max,
                    ee_falloff=ee_falloff,
                    scatter_falloff=sc_falloff,
                )
                self.window.after(0, lambda: self._build_done(output, None))
            except Exception as e:
                self.window.after(0, lambda: self._build_done(None, str(e)))

        self._build_thread = threading.Thread(target=run_build, daemon=True)
        self._build_thread.start()

    def _build_done(self, output_folder, error):
        self.preview_btn.config(state="normal")
        self.build_btn.config(state="normal")
        if error:
            self.status_label.config(text="Failed")
            messagebox.showerror("Build Failed", error, parent=self.window)
            self.update_status(f"Build failed: {error}", error=True)
        else:
            self.status_label.config(text="Done")
            self.update_status(f"Build complete: {output_folder}")
            messagebox.showinfo("Build Complete", f"Output saved to:\n{output_folder}", parent=self.window)

    def _on_close(self):
        if self.prince_main_app_ref and hasattr(self.prince_main_app_ref, 'image_modification_window'):
            self.prince_main_app_ref.image_modification_window = None
        self.window.destroy()


if __name__ == "__main__":
    import tkinter as tk

    root = tk.Tk()
    root.withdraw()  # Hide the root window; ImageModificationWindow uses a Toplevel
    app = ImageModificationWindow(root)
    app.window.protocol("WM_DELETE_WINDOW", root.quit)
    root.mainloop()
