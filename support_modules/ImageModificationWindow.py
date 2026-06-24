
"""
Image Modification Window

GUI for SLA image processing: edge enhancement, global blur enhancement,
padding normalization. Provides Preview and Build functionality.
"""

import os
import re
import glob
import csv
import math
import shutil
import threading
from pathlib import Path
from datetime import datetime

from tkinter import Toplevel, Frame, Label, Entry, Button, Checkbutton, BooleanVar, StringVar, Radiobutton, Canvas, Text
from tkinter import ttk, filedialog, messagebox, font as tkFont

# Ensure project root is on sys.path so 'support_modules' is importable
# whether this file is run directly or imported as a module.
import sys as _sys
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in _sys.path:
    _sys.path.insert(0, _project_root)

import cv2
import numpy as np

import support_modules.image_modification.processor as _im_processor
from support_modules.z_compensation import compute_layer_factors
try:
    from support_modules.image_modification.feature_depth import build_feature_depth_map
    HAS_FEATURE_DEPTH = True
except ImportError:
    HAS_FEATURE_DEPTH = False

try:
    from support_modules.DefinitionsWindow import DefinitionsWindow
    HAS_DEFINITIONS = True
except ImportError:
    HAS_DEFINITIONS = False

PREVIEW_MAX_SIZE = (640, 400)  # Full image downscaled to fit; preserves aspect ratio
CONE_OUTPUT_WIDTH = 2560
CONE_OUTPUT_HEIGHT = 1600
CONE_UM_PER_PIXEL = 7.607


process_single_for_preview = _im_processor.process_single_for_preview
process_folder = _im_processor.process_folder


def _local_generate_cone_images(input_folder: str,
                                initial_radius_um: float,
                                ending_radius_um: float,
                                height_um: float,
                                layer_height_um: float,
                                progress_callback=None) -> str:
    """Fallback cone generator used if processor symbol is temporarily unavailable."""
    if not input_folder:
        raise ValueError("An output folder must be selected for cone generation")
    if height_um <= 0:
        raise ValueError("Height must be greater than zero")
    if layer_height_um <= 0:
        raise ValueError("Layer height must be greater than zero")
    if initial_radius_um < 0 or ending_radius_um < 0:
        raise ValueError("Cone radii must be non-negative")

    layer_count = max(1, int(math.ceil(float(height_um) / float(layer_height_um))))
    if layer_count == 1:
        radii = [float(ending_radius_um)]
    else:
        radii = [
            float(initial_radius_um) + (
                (float(ending_radius_um) - float(initial_radius_um)) * (layer_index / float(layer_count - 1))
            )
            for layer_index in range(layer_count)
        ]

    max_radius_um = max(float(initial_radius_um), float(ending_radius_um))
    max_fit_radius_px = min((CONE_OUTPUT_WIDTH - 4) / 2.0, (CONE_OUTPUT_HEIGHT - 4) / 2.0)
    max_fit_radius_um = max_fit_radius_px * CONE_UM_PER_PIXEL
    if max_radius_um > max_fit_radius_um:
        raise ValueError(
            f"Cone radius {max_radius_um:g} um exceeds the printable field for {CONE_UM_PER_PIXEL:g} um/px "
            f"on a {CONE_OUTPUT_WIDTH}x{CONE_OUTPUT_HEIGHT} frame. Maximum safe radius is {max_fit_radius_um:.1f} um."
        )

    def _format_um_tag(value: float) -> str:
        return str(round(float(value), 2)).replace('.', '_')

    output_folder_name = (
        f"Cone_R{_format_um_tag(initial_radius_um)}_To{_format_um_tag(ending_radius_um)}"
        f"_H{_format_um_tag(height_um)}_LH{_format_um_tag(layer_height_um)}"
    )
    output_folder = os.path.join(input_folder, output_folder_name)
    os.makedirs(output_folder, exist_ok=True)

    if progress_callback:
        progress_callback(0, layer_count, "Generating cone images...")

    for index, radius_um in enumerate(radii, start=1):
        image = np.zeros((CONE_OUTPUT_HEIGHT, CONE_OUTPUT_WIDTH), dtype=np.uint8)
        draw_radius = max(0, int(round(float(radius_um) / CONE_UM_PER_PIXEL)))
        cv2.circle(
            image,
            (CONE_OUTPUT_WIDTH // 2, CONE_OUTPUT_HEIGHT // 2),
            draw_radius,
            255,
            thickness=-1,
            lineType=cv2.LINE_8,
        )
        output_path = os.path.join(output_folder, f"{index}.png")
        cv2.imwrite(output_path, image)
        if progress_callback:
            progress_callback(index, layer_count, f"Generated layer {index}/{layer_count}")

    return output_folder


generate_cone_images = getattr(_im_processor, 'generate_cone_images', _local_generate_cone_images)


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
    if max_size is not None and (w > max_size[0] or h > max_size[1]):
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
        self.zoom_level = 1.0  # Track zoom level (1.0 = fit to preview)
        self.current_image_array = None  # Store original image for zoom
        self.preview_width = 640  # Fixed preview dimensions
        self.preview_height = 400
        self.preview_canvas = None
        self.preview_canvas_image = None
        self.instruction_file_path = None

        self.window = Toplevel(master_window)
        self.window.title("Image Modification")
        self.window.geometry("800x700")
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

        control_font = tkFont.Font(family="Helvetica", size=11)
        title_font = tkFont.Font(family="Helvetica", size=20, weight="bold")

        # --- Create scrollable canvas ---
        canvas = Canvas(self.window)
        scrollbar = ttk.Scrollbar(self.window, orient="vertical", command=canvas.yview)
        scrollable_frame = Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack the canvas and a right-side control column (up button, scrollbar, down button)
        right_col = Frame(self.window)
        right_col.pack(side="right", fill="y")

        up_btn = Button(right_col, text="▲", width=2, command=lambda: canvas.yview_scroll(-3, "units"))
        up_btn.pack(side="top", pady=(10, 2))
        scrollbar.pack(in_=right_col, side="top", fill="y", expand=True)
        down_btn = Button(right_col, text="▼", width=2, command=lambda: canvas.yview_scroll(3, "units"))
        down_btn.pack(side="top", pady=(2, 10))

        canvas.pack(side="left", fill="both", expand=True)
        
        # Bind mousewheel/scroll events (platform-aware, bind on enter/leave)
        def _on_mousewheel_windows(event):
            # Windows and macOS (event.delta in multiples of 120)
            try:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except Exception:
                pass

        def _on_mousewheel_unix(event):
            # X11 systems: use Button-4 (up) and Button-5 (down)
            try:
                if event.num == 4:
                    canvas.yview_scroll(-1, "units")
                elif event.num == 5:
                    canvas.yview_scroll(1, "units")
            except Exception:
                pass

        def _bind_mousewheel(widget):
            # Attach all reasonable bindings while the cursor is over the frame
            widget.bind_all("<MouseWheel>", _on_mousewheel_windows)
            widget.bind_all("<Button-4>", _on_mousewheel_unix)
            widget.bind_all("<Button-5>", _on_mousewheel_unix)

        def _unbind_mousewheel(widget):
            try:
                widget.unbind_all("<MouseWheel>")
            except Exception:
                pass
            try:
                widget.unbind_all("<Button-4>")
                widget.unbind_all("<Button-5>")
            except Exception:
                pass

        # Bind when the cursor enters/leaves the scrollable area so bindings are scoped
        scrollable_frame.bind("<Enter>", lambda e: _bind_mousewheel(canvas))
        scrollable_frame.bind("<Leave>", lambda e: _unbind_mousewheel(canvas))

        # Focus and keyboard bindings to improve accessibility (Up/Down/PageUp/PageDown)
        def _bind_keyboard_nav():
            scrollable_frame.bind_all("<Up>", lambda e: canvas.yview_scroll(-1, "units"))
            scrollable_frame.bind_all("<Down>", lambda e: canvas.yview_scroll(1, "units"))
            scrollable_frame.bind_all("<Prior>", lambda e: canvas.yview_scroll(-1, "pages"))
            scrollable_frame.bind_all("<Next>", lambda e: canvas.yview_scroll(1, "pages"))

        def _unbind_keyboard_nav():
            try:
                scrollable_frame.unbind_all("<Up>")
                scrollable_frame.unbind_all("<Down>")
                scrollable_frame.unbind_all("<Prior>")
                scrollable_frame.unbind_all("<Next>")
            except Exception:
                pass

        scrollable_frame.bind("<Enter>", lambda e: _bind_keyboard_nav())
        scrollable_frame.bind("<Leave>", lambda e: _unbind_keyboard_nav())

        # Ensure the scrollable area gets focus when window opens
        try:
            self.window.after(100, lambda: (scrollable_frame.focus_set(), _bind_mousewheel(canvas)))
        except Exception:
            pass

        # --- Header ---
        top_frame = Frame(scrollable_frame)
        top_frame.pack(side="top", fill="x", padx=10, pady=(5, 0))

        Label(top_frame, text="Image Modification", font=title_font).pack(side="left", padx=(0, 10))
        if HAS_DEFINITIONS:
            Button(top_frame, text="Definitions",
                   command=self._open_definitions,
                   font=tkFont.Font(family="Helvetica", size=9)).pack(side="left", padx=(0, 10))
        credit = "Professor Cheng Sun, Evan Jones"
        Label(top_frame, text=credit, font=tkFont.Font(family="Helvetica", size=7)).pack(side="right")

        # --- File path ---
        path_frame = Frame(scrollable_frame)
        path_frame.pack(side="top", fill="x", padx=10, pady=(10, 5))
        Label(path_frame, text="Folder:", font=control_font).pack(side="left", padx=(0, 5))
        self.folder_entry = Entry(path_frame, font=control_font)
        self.folder_entry.pack(side="left", expand=True, fill="x", padx=(0, 5))
        self.folder_entry.bind("<Return>", lambda e: self._load_layer())
        Button(path_frame, text="Browse", command=self._browse_folder, font=control_font).pack(side="left")

        # --- Layer number + Load ---
        layer_frame = Frame(scrollable_frame)
        layer_frame.pack(side="top", fill="x", padx=10, pady=(2, 5))
        Label(layer_frame, text="Layer:", font=control_font).pack(side="left", padx=(0, 5))
        self.layer_var = StringVar(value="1")
        self.layer_entry = Entry(layer_frame, textvariable=self.layer_var, width=6, font=control_font)
        self.layer_entry.pack(side="left", padx=(0, 5))
        self.layer_entry.bind("<Return>", lambda e: self._load_layer())
        self.layer_count_label = Label(layer_frame, text="(1-N)", font=control_font)
        self.layer_count_label.pack(side="left", padx=(0, 10))
        Button(layer_frame, text="Load", command=self._load_layer, font=control_font).pack(side="left")

        # --- Image preview with zoom/pan controls ---
        preview_frame = Frame(scrollable_frame, relief="groove", borderwidth=2)
        preview_frame.pack(side="top", padx=10, pady=(5, 10))
        
        # Zoom controls
        zoom_frame = Frame(preview_frame)
        zoom_frame.pack(side="top", padx=5, pady=(5, 0))
        Button(zoom_frame, text="-", command=self._zoom_out, width=3, font=control_font).pack(side="left", padx=2)
        self.zoom_label = Label(zoom_frame, text="Fit", width=8, font=control_font)
        self.zoom_label.pack(side="left", padx=5)
        Button(zoom_frame, text="+", command=self._zoom_in, width=3, font=control_font).pack(side="left", padx=2)
        Button(zoom_frame, text="Reset", command=self._zoom_fit, width=6, font=control_font).pack(side="left", padx=2)
        
        preview_view = Frame(preview_frame)
        preview_view.pack(side="top", padx=5, pady=5)

        self.preview_canvas = Canvas(
            preview_view,
            width=self.preview_width,
            height=self.preview_height,
            bg="#333",
            highlightthickness=0,
        )
        self.preview_canvas.grid(row=0, column=0, sticky="nsew")

        y_scroll = ttk.Scrollbar(preview_view, orient="vertical", command=self.preview_canvas.yview)
        y_scroll.grid(row=0, column=1, sticky="ns")

        x_scroll = ttk.Scrollbar(preview_view, orient="horizontal", command=self.preview_canvas.xview)
        x_scroll.grid(row=1, column=0, sticky="ew")

        preview_view.grid_rowconfigure(0, weight=1)
        preview_view.grid_columnconfigure(0, weight=1)

        self.preview_canvas.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        self.preview_canvas.create_text(
            self.preview_width // 2,
            self.preview_height // 2,
            text="No image loaded",
            fill="white",
        )

        # --- Section 1: Edge Enhancement ---
        ee_frame = ttk.LabelFrame(scrollable_frame, text="Edge Enhancement", padding=(10, 5))
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
        ge_frame = ttk.LabelFrame(scrollable_frame, text="Global Blur Enhancement", padding=(10, 5))
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
        ttk.Checkbutton(ge_row2, text="Asymmetric (angular sectors, per-ray furthest white)", variable=self.ge_asymmetric_var).pack(side="left", padx=(0, 15))
        Label(ge_row2, text="Slice (°):", font=control_font).pack(side="left", padx=(0, 5))
        self.ge_sector_angle_var = StringVar(value="90")
        Entry(ge_row2, textvariable=self.ge_sector_angle_var, width=5, font=control_font).pack(side="left", padx=(0, 10))
        Label(ge_row2, text="Smooth (sectors):", font=control_font).pack(side="left", padx=(0, 5))
        self.ge_sector_smoothing_var = StringVar(value="0")
        Entry(ge_row2, textvariable=self.ge_sector_smoothing_var, width=5, font=control_font).pack(side="left", padx=(0, 10))
        Label(ge_row2, text="Blend (°):", font=control_font).pack(side="left", padx=(0, 5))
        self.blend_angle_var = StringVar(value="20")
        Entry(ge_row2, textvariable=self.blend_angle_var, width=5, font=control_font).pack(side="left")

        # --- Section 3: Padding ---
        pad_frame = ttk.LabelFrame(scrollable_frame, text="Image Padding", padding=(10, 5))
        pad_frame.pack(side="top", fill="x", padx=10, pady=(0, 5))
        self.pad_var = BooleanVar(value=False)
        ttk.Checkbutton(pad_frame, text="Insert black padding after each image ({x}_1.png)", variable=self.pad_var).pack(anchor="w")

        # --- Section 4: Feature Depth Correction (experimental – local only) ---
        # Initialise all FD vars unconditionally so _get_params() always works;
        # the UI frame is only created when feature_depth.py is present.
        self.fd_var = BooleanVar(value=False)
        self.fd_strength_var = StringVar(value="0.4")
        self.fd_smooth_var   = StringVar(value="10")
        self.fd_mode_var     = StringVar(value="distance")
        self.fd_decay_var    = StringVar(value="50")
        self.fd_conductivity_var = StringVar(value="100")
        self.fd_sink_var     = StringVar(value="0.1")

        if HAS_FEATURE_DEPTH:
            fd_frame = ttk.LabelFrame(scrollable_frame, text="Feature Depth Correction  (overcuring compensation)", padding=(10, 5))
            fd_frame.pack(side="top", fill="x", padx=10, pady=(0, 5))
            # Row 1: enable + strength
            fd_row1 = ttk.Frame(fd_frame)
            fd_row1.pack(side="top", fill="x")
            ttk.Checkbutton(fd_row1, text="Enable", variable=self.fd_var).pack(side="left", padx=(0, 15))
            Label(fd_row1, text="Strength:", font=control_font).pack(side="left", padx=(0, 5))
            Entry(fd_row1, textvariable=self.fd_strength_var, width=5, font=control_font).pack(side="left", padx=(0, 15))
            Label(fd_row1, text="Smooth (px):", font=control_font).pack(side="left", padx=(0, 5))
            Entry(fd_row1, textvariable=self.fd_smooth_var, width=5, font=control_font).pack(side="left")
            # Row 2: mode selector
            fd_row2 = ttk.Frame(fd_frame)
            fd_row2.pack(side="top", fill="x", pady=(5, 0))
            Label(fd_row2, text="Mode:", font=control_font).pack(side="left", padx=(0, 8))
            Radiobutton(fd_row2, text="Distance (fast)", variable=self.fd_mode_var,
                        value="distance", font=control_font).pack(side="left", padx=(0, 15))
            Radiobutton(fd_row2, text="Pressure / PDE  (physics model)",
                        variable=self.fd_mode_var, value="pressure",
                        font=control_font).pack(side="left")
            # Row 3: Distance-mode params  |  Pressure-mode params
            fd_row3 = ttk.Frame(fd_frame)
            fd_row3.pack(side="top", fill="x", pady=(4, 0))
            Label(fd_row3, text="Channel decay (px):", font=control_font).pack(side="left", padx=(0, 5))
            Entry(fd_row3, textvariable=self.fd_decay_var, width=6, font=control_font).pack(side="left", padx=(0, 20))
            Label(fd_row3, text="Conductivity:", font=control_font).pack(side="left", padx=(0, 5))
            Entry(fd_row3, textvariable=self.fd_conductivity_var, width=6, font=control_font).pack(side="left", padx=(0, 20))
            Label(fd_row3, text="Sink:", font=control_font).pack(side="left", padx=(0, 5))
            Entry(fd_row3, textvariable=self.fd_sink_var, width=5, font=control_font).pack(side="left")

        # --- Section 5: Axial Z Compensation (experimental) ---
        zc_frame = ttk.LabelFrame(scrollable_frame, text="Axial Z Compensation  (simplified overcuring model)", padding=(10, 5))
        zc_frame.pack(side="top", fill="x", padx=10, pady=(0, 5))
        self.zc_var = BooleanVar(value=False)
        self.zc_layer_thickness_var = StringVar(value="50")
        self.zc_penetration_depth_var = StringVar(value="120")
        self.zc_strength_var = StringVar(value="1.0")
        self.zc_min_factor_var = StringVar(value="0.25")
        self.zc_factor_preview_var = StringVar(value="Preview factor: 1.000")

        zc_row1 = ttk.Frame(zc_frame)
        zc_row1.pack(side="top", fill="x")
        ttk.Checkbutton(zc_row1, text="Enable", variable=self.zc_var).pack(side="left", padx=(0, 15))
        Label(zc_row1, text="Layer thickness (um):", font=control_font).pack(side="left", padx=(0, 5))
        Entry(zc_row1, textvariable=self.zc_layer_thickness_var, width=6, font=control_font).pack(side="left", padx=(0, 12))
        Label(zc_row1, text="Penetration depth Dp (um):", font=control_font).pack(side="left", padx=(0, 5))
        Entry(zc_row1, textvariable=self.zc_penetration_depth_var, width=6, font=control_font).pack(side="left")

        zc_row2 = ttk.Frame(zc_frame)
        zc_row2.pack(side="top", fill="x", pady=(5, 0))
        Label(zc_row2, text="Strength (0-1):", font=control_font).pack(side="left", padx=(0, 5))
        Entry(zc_row2, textvariable=self.zc_strength_var, width=6, font=control_font).pack(side="left", padx=(0, 12))
        Label(zc_row2, text="Min factor:", font=control_font).pack(side="left", padx=(0, 5))
        Entry(zc_row2, textvariable=self.zc_min_factor_var, width=6, font=control_font).pack(side="left", padx=(0, 12))
        Label(zc_row2, textvariable=self.zc_factor_preview_var, font=control_font).pack(side="left", padx=(8, 0))

        # --- Section 6: Scattering Compensation ---
        sc_frame = ttk.LabelFrame(scrollable_frame, text="Scattering Compensation", padding=(10, 5))
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

        # --- Section 7: Cone Generator ---
        cone_frame = ttk.LabelFrame(scrollable_frame, text="Cone Generator", padding=(10, 5))
        cone_frame.pack(side="top", fill="x", padx=10, pady=(0, 5))

        cone_row1 = ttk.Frame(cone_frame)
        cone_row1.pack(side="top", fill="x")
        Label(cone_row1, text="Output base folder:", font=control_font).pack(side="left", padx=(0, 5))
        self.cone_output_entry = Entry(cone_row1, font=control_font)
        self.cone_output_entry.pack(side="left", expand=True, fill="x", padx=(0, 5))
        self.cone_output_entry.insert(0, os.getcwd())
        Button(cone_row1, text="Browse", command=self._browse_cone_output_folder, font=control_font).pack(side="left")

        cone_row2 = ttk.Frame(cone_frame)
        cone_row2.pack(side="top", fill="x", pady=(5, 0))
        Label(cone_row2, text="Initial radius (um):", font=control_font).pack(side="left", padx=(0, 5))
        self.cone_initial_radius_var = StringVar(value="0")
        Entry(cone_row2, textvariable=self.cone_initial_radius_var, width=7, font=control_font).pack(side="left", padx=(0, 10))
        Label(cone_row2, text="Ending radius (um):", font=control_font).pack(side="left", padx=(0, 5))
        self.cone_ending_radius_var = StringVar(value="500")
        Entry(cone_row2, textvariable=self.cone_ending_radius_var, width=7, font=control_font).pack(side="left", padx=(0, 10))
        Label(cone_row2, text="Height (um):", font=control_font).pack(side="left", padx=(0, 5))
        self.cone_height_var = StringVar(value="1000")
        Entry(cone_row2, textvariable=self.cone_height_var, width=7, font=control_font).pack(side="left", padx=(0, 10))
        Label(cone_row2, text="Layer height (um):", font=control_font).pack(side="left", padx=(0, 5))
        self.cone_layer_height_var = StringVar(value="50")
        Entry(cone_row2, textvariable=self.cone_layer_height_var, width=7, font=control_font).pack(side="left")

        cone_row3 = ttk.Frame(cone_frame)
        cone_row3.pack(side="top", fill="x", pady=(6, 0))
        self.cone_generate_btn = Button(cone_row3, text="Generate Cone", command=self._generate_cone, font=control_font)
        self.cone_generate_btn.pack(side="left")
        self.cone_status_label = Label(cone_row3, text="", font=control_font)
        self.cone_status_label.pack(side="left", padx=(15, 0))

        # --- Section 8: Instruction Ramping ---
        ramp_frame = ttk.LabelFrame(scrollable_frame, text="Instruction Ramping", padding=(10, 5))
        ramp_frame.pack(side="top", fill="x", padx=10, pady=(0, 5))

        ramp_row1 = ttk.Frame(ramp_frame)
        ramp_row1.pack(side="top", fill="x")
        Label(ramp_row1, text="Instruction file:", font=control_font).pack(side="left", padx=(0, 5))
        self.ramp_instruction_entry = Entry(ramp_row1, font=control_font)
        self.ramp_instruction_entry.pack(side="left", expand=True, fill="x", padx=(0, 5))
        Button(ramp_row1, text="Browse", command=self._browse_instruction_file, font=control_font).pack(side="left")

        ramp_row2 = ttk.Frame(ramp_frame)
        ramp_row2.pack(side="top", fill="x", pady=(5, 0))
        Label(ramp_row2, text="Ramp mode:", font=control_font).pack(side="left", padx=(0, 5))
        self.ramp_mode_var = StringVar(value="linear")
        Radiobutton(ramp_row2, text="Linear", variable=self.ramp_mode_var, value="linear", font=control_font).pack(side="left", padx=(0, 10))
        Radiobutton(ramp_row2, text="Exponential", variable=self.ramp_mode_var, value="exponential", font=control_font).pack(side="left", padx=(0, 15))
        Label(ramp_row2, text="Power at first control layer:", font=control_font).pack(side="left", padx=(0, 5))
        self.ramp_first_power_var = StringVar(value="255")
        Entry(ramp_row2, textvariable=self.ramp_first_power_var, width=7, font=control_font).pack(side="left")

        ramp_row3 = ttk.Frame(ramp_frame)
        ramp_row3.pack(side="top", fill="both", pady=(5, 0))
        Label(ramp_row3, text="Control layers (one per line: layer, exposure_s):", font=control_font).pack(anchor="w")
        self.ramp_control_text = Text(ramp_row3, height=5, width=60, font=control_font)
        self.ramp_control_text.pack(side="top", fill="x")
        self.ramp_control_text.insert("end", "1, 9.0\n10, 0.25\n20, 0.25")

        ramp_row4 = ttk.Frame(ramp_frame)
        ramp_row4.pack(side="top", fill="x", pady=(6, 0))
        self.ramp_generate_btn = Button(ramp_row4, text="Generate Ramp", command=self._generate_instruction_ramp, font=control_font)
        self.ramp_generate_btn.pack(side="left")
        self.ramp_status_label = Label(ramp_row4, text="", font=control_font)
        self.ramp_status_label.pack(side="left", padx=(15, 0))

        # --- Preview and Build buttons ---
        btn_frame = Frame(scrollable_frame)
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

    def _zoom_in(self):
        """Increase zoom level."""
        if self.current_image_array is None:
            return
        self.zoom_level = min(self.zoom_level * 1.25, 8.0)
        self._update_zoom_display()

    def _zoom_out(self):
        """Decrease zoom level."""
        if self.current_image_array is None:
            return
        self.zoom_level = max(self.zoom_level / 1.25, 1.0)
        self._update_zoom_display()

    def _zoom_fit(self):
        """Reset to fit view."""
        self.zoom_level = 1.0
        self._update_zoom_display()

    def _update_zoom_display(self):
        """Update the preview with current zoom level and scrollbar pan."""
        if self.current_image_array is None:
            return

        img = self.current_image_array
        h, w = img.shape[:2]

        fit_scale = min(self.preview_width / w, self.preview_height / h)
        scale = fit_scale * self.zoom_level
        disp_w = max(1, int(w * scale))
        disp_h = max(1, int(h * scale))
        img_display = cv2.resize(img, (disp_w, disp_h), interpolation=cv2.INTER_LINEAR)

        self.current_photo = _cv2_to_photoimage(img_display, max_size=None)
        if self.current_photo is None or self.preview_canvas is None:
            return

        self.preview_canvas.delete("all")
        self.preview_canvas_image = self.preview_canvas.create_image(0, 0, image=self.current_photo, anchor="nw")
        self.preview_canvas.config(scrollregion=(0, 0, disp_w, disp_h))
        self.zoom_label.config(text="Fit" if self.zoom_level == 1.0 else f"{int(self.zoom_level * 100)}%")

    def _display_image(self, path, processed_array=None, preserve_view=False):
        """Display image from path or from processed numpy array."""
        if processed_array is not None:
            img = processed_array
        else:
            img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            if self.preview_canvas is not None:
                self.preview_canvas.delete("all")
                self.preview_canvas.create_text(
                    self.preview_width // 2,
                    self.preview_height // 2,
                    text="Could not load image",
                    fill="white",
                )
            self.current_image_array = None
            return
        
        # Store original for zoom operations
        self.current_image_array = img.copy()
        if not preserve_view:
            self.zoom_level = 1.0
        
        self._update_zoom_display()

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
            ge_sector_angle = float(self.ge_sector_angle_var.get().strip() or "90")
        except ValueError:
            ge_sector_angle = 90.0
        try:
            ge_sector_smoothing = int(self.ge_sector_smoothing_var.get().strip() or "0")
        except ValueError:
            ge_sector_smoothing = 0

        if ge_sector_angle <= 0:
            ge_sector_angle = 90.0
        ge_sector_angle = min(180.0, ge_sector_angle)
        if ge_sector_smoothing < 0:
            ge_sector_smoothing = 0
        if blend_angle < 0:
            blend_angle = 0.0
        if blend_angle > ge_sector_angle:
            blend_angle = ge_sector_angle
        try:
            fd_strength = float(self.fd_strength_var.get().strip() or "0.4")
        except ValueError:
            fd_strength = 0.4
        try:
            fd_decay = float(self.fd_decay_var.get().strip() or "50")
        except ValueError:
            fd_decay = 50.0
        try:
            fd_smooth = float(self.fd_smooth_var.get().strip() or "10")
        except ValueError:
            fd_smooth = 10.0
        try:
            fd_conductivity = float(self.fd_conductivity_var.get().strip() or "100")
        except ValueError:
            fd_conductivity = 100.0
        try:
            fd_sink = float(self.fd_sink_var.get().strip() or "0.1")
        except ValueError:
            fd_sink = 0.1
        fd_mode = self.fd_mode_var.get()
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
            ee_min = float(self.min_var.get().strip() or "100")
        except ValueError:
            ee_min = 100.0
        try:
            ee_max = float(self.max_var.get().strip() or "255")
        except ValueError:
            ee_max = 255.0
        try:
            sc_falloff = int(self.sc_falloff_var.get().strip() or "61")
        except ValueError:
            sc_falloff = 61

        try:
            zc_layer_thickness = float(self.zc_layer_thickness_var.get().strip() or "50")
        except ValueError:
            zc_layer_thickness = 50.0
        try:
            zc_penetration_depth = float(self.zc_penetration_depth_var.get().strip() or "120")
        except ValueError:
            zc_penetration_depth = 120.0
        try:
            zc_strength = float(self.zc_strength_var.get().strip() or "1.0")
        except ValueError:
            zc_strength = 1.0
        try:
            zc_min_factor = float(self.zc_min_factor_var.get().strip() or "0.25")
        except ValueError:
            zc_min_factor = 0.25

        return (
            blur,
            globe,
            sigma,
            blend_angle,
            ge_sector_angle,
            ge_sector_smoothing,
            fd_strength,
            fd_decay,
            fd_smooth,
            fd_mode,
            fd_conductivity,
            fd_sink,
            sc_width,
            sc_min,
            sc_max,
            ee_falloff,
            sc_falloff,
            zc_layer_thickness,
            zc_penetration_depth,
            zc_strength,
            zc_min_factor,
            ee_min,
            ee_max,
        )

    def _do_preview(self):
        if not self.current_image_path or not os.path.isfile(self.current_image_path):
            messagebox.showwarning("Preview", "Load an image first (set folder and click Load).", parent=self.window)
            return
        blur, globe, sigma, blend_angle, ge_sector_angle, ge_sector_smoothing, fd_strength, fd_decay, fd_smooth, fd_mode, fd_conductivity, fd_sink, sc_width, sc_min, sc_max, ee_falloff, sc_falloff, zc_layer_thickness, zc_penetration_depth, zc_strength, zc_min_factor, ee_min, ee_max = self._get_params()
        try:
            axial_factor = 1.0
            if self.zc_var.get() and self.image_files:
                layer_idx = max(1, min(len(self.image_files), int(self.layer_var.get().strip() or "1"))) - 1
                factors = compute_layer_factors(
                    num_layers=len(self.image_files),
                    layer_thickness_um=zc_layer_thickness,
                    penetration_depth_um=zc_penetration_depth,
                    strength=zc_strength,
                    min_factor=zc_min_factor,
                )
                if 0 <= layer_idx < len(factors):
                    axial_factor = factors[layer_idx]
            self.zc_factor_preview_var.set(f"Preview factor: {axial_factor:.3f}")

            result = process_single_for_preview(
                self.current_image_path,
                edge_enabled=self.ee_var.get(),
                blurring=blur,
                global_enabled=self.ge_var.get(),
                globe=globe,
                sigma=sigma,
                global_asymmetric=self.ge_asymmetric_var.get(),
                blend_angle=blend_angle,
                ge_sector_angle=ge_sector_angle,
                ge_sector_smoothing=ge_sector_smoothing,
                depth_enabled=self.fd_var.get(),
                depth_strength=fd_strength,
                depth_decay_sigma=fd_decay,
                depth_smooth_sigma=fd_smooth,
                depth_mode=fd_mode,
                pressure_conductivity=fd_conductivity,
                pressure_sink=fd_sink,
                scatter_enabled=self.sc_var.get(),
                scatter_width=sc_width,
                scatter_min_val=sc_min,
                scatter_max_val=sc_max,
                axial_factor=axial_factor,
                ee_falloff=ee_falloff,
                scatter_falloff=sc_falloff,
                ee_min=ee_min,
                ee_max=ee_max,
            )
            self._display_image(None, processed_array=result, preserve_view=True)
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
        blur, globe, sigma, blend_angle, ge_sector_angle, ge_sector_smoothing, fd_strength, fd_decay, fd_smooth, fd_mode, fd_conductivity, fd_sink, sc_width, sc_min, sc_max, ee_falloff, sc_falloff, zc_layer_thickness, zc_penetration_depth, zc_strength, zc_min_factor, ee_min, ee_max = self._get_params()

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
                    ge_sector_angle=ge_sector_angle,
                    ge_sector_smoothing=ge_sector_smoothing,
                    depth_enabled=self.fd_var.get(),
                    depth_strength=fd_strength,
                    depth_decay_sigma=fd_decay,
                    depth_smooth_sigma=fd_smooth,
                    depth_mode=fd_mode,
                    pressure_conductivity=fd_conductivity,
                    pressure_sink=fd_sink,
                    scatter_enabled=self.sc_var.get(),
                    scatter_width=sc_width,
                    scatter_min_val=sc_min,
                    scatter_max_val=sc_max,
                    axial_enabled=self.zc_var.get(),
                    layer_thickness_um=zc_layer_thickness,
                    penetration_depth_um=zc_penetration_depth,
                    axial_strength=zc_strength,
                    axial_min_factor=zc_min_factor,
                    ee_falloff=ee_falloff,
                    scatter_falloff=sc_falloff,
                    ee_min=ee_min,
                    ee_max=ee_max,
                )
                self.window.after(0, lambda: self._build_done(output, None))
            except Exception as e:
                self.window.after(0, lambda: self._build_done(None, str(e)))

        self._build_thread = threading.Thread(target=run_build, daemon=True)
        self._build_thread.start()

    def _browse_cone_output_folder(self):
        path = filedialog.askdirectory(title="Select base folder for cone images")
        if path:
            self.cone_output_entry.delete(0, "end")
            self.cone_output_entry.insert(0, path)

    def _browse_instruction_file(self):
        path = filedialog.askopenfilename(
            title="Select instruction file",
            filetypes=[("Instruction files", "*.txt"), ("All files", "*.*")],
        )
        if path:
            self.instruction_file_path = path
            self.ramp_instruction_entry.delete(0, "end")
            self.ramp_instruction_entry.insert(0, path)

    def _parse_control_layers(self):
        raw_text = self.ramp_control_text.get("1.0", "end").strip()
        control_points = []
        for line in raw_text.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = [part.strip() for part in re.split(r"[,\t ]+", line) if part.strip()]
            if len(parts) < 2:
                raise ValueError(f"Invalid control layer line: '{line}'")
            layer_num = int(float(parts[0]))
            exposure_s = float(parts[1])
            if layer_num < 1:
                raise ValueError("Control layer numbers must be 1 or greater")
            if exposure_s <= 0:
                raise ValueError("Control layer exposure times must be greater than zero")
            control_points.append((layer_num, exposure_s))
        if len(control_points) < 2:
            raise ValueError("Enter at least two control layers")
        control_points.sort(key=lambda item: item[0])
        for idx in range(1, len(control_points)):
            if control_points[idx][0] <= control_points[idx - 1][0]:
                raise ValueError("Control layer numbers must be strictly increasing")
        return control_points

    def _read_instruction_rows(self, instruction_path):
        with open(instruction_path, "r", newline="", encoding="utf-8") as handle:
            reader = csv.reader(handle, delimiter="\t")
            rows = [row for row in reader if row]
        if len(rows) < 2:
            raise ValueError("Instruction file does not contain any layer rows")
        header = rows[0]
        if len(header) < 10:
            raise ValueError("Instruction file must have the standard 10-column header")

        parsed_rows = []
        for row in rows[1:]:
            if len(row) < 10:
                row_text = "\t".join(row)
                raise ValueError(f"Invalid instruction row: {row_text}")
            parsed_rows.append({
                "layer": int(float(row[0])),
                "file": row[1],
                "thickness": row[2],
                "time": float(row[3]),
                "intensity": float(row[4]),
                "step_speed": row[5],
                "overstep": row[6],
                "acceleration": row[7],
                "pause": row[8],
                "sandwich_speed": row[9],
            })

        parsed_rows.sort(key=lambda item: item["layer"])
        for expected, row in enumerate(parsed_rows, start=1):
            if row["layer"] != expected:
                raise ValueError("Instruction file layers must be sequential starting at 1")
        return header, parsed_rows

    def _interpolate_exposure(self, left_layer, left_exposure, right_layer, right_exposure, current_layer, mode):
        if right_layer <= left_layer:
            return left_exposure
        t = (current_layer - left_layer) / float(right_layer - left_layer)
        if mode == "exponential" and left_exposure > 0 and right_exposure > 0:
            if abs(left_exposure - right_exposure) < 1e-12:
                return left_exposure
            return left_exposure * ((right_exposure / left_exposure) ** t)
        return left_exposure + ((right_exposure - left_exposure) * t)

    def _generate_controlled_ramp(self, source_path, control_points, mode, first_power):
        header, rows = self._read_instruction_rows(source_path)
        total_layers = len(rows)
        if control_points[0][0] > total_layers or control_points[-1][0] > total_layers:
            raise ValueError("Control layer numbers cannot exceed the number of layers in the instruction file")

        if len(control_points) == 2:
            boundaries = [(control_points[0], control_points[1])]
        else:
            boundaries = list(zip(control_points[:-1], control_points[1:]))

        exposure_by_layer = [0.0] * total_layers
        for layer_index in range(1, total_layers + 1):
            if layer_index <= control_points[0][0]:
                exposure_by_layer[layer_index - 1] = control_points[0][1]
                continue
            if layer_index >= control_points[-1][0]:
                exposure_by_layer[layer_index - 1] = control_points[-1][1]
                continue
            for left, right in boundaries:
                if left[0] <= layer_index <= right[0]:
                    exposure_by_layer[layer_index - 1] = self._interpolate_exposure(
                        left[0], left[1], right[0], right[1], layer_index, mode
                    )
                    break

        anchor_exposure = control_points[0][1]
        anchor_power = float(first_power)
        anchor_dose = anchor_power * anchor_exposure

        output_rows = []
        for row, exposure in zip(rows, exposure_by_layer):
            if exposure <= 0:
                raise ValueError("Interpolated exposure time became non-positive")
            power = anchor_dose / exposure
            power = max(0.0, min(255.0, power))
            output_rows.append([
                str(row["layer"]),
                row["file"],
                row["thickness"],
                f"{exposure:.6f}",
                f"{power:.6f}",
                row["step_speed"],
                row["overstep"],
                row["acceleration"],
                row["pause"],
                row["sandwich_speed"],
            ])

        source_folder = Path(source_path).resolve().parent
        source_folder_name = source_folder.name
        output_folder = source_folder.parent / f"{source_folder_name}_ramped_{mode}"
        output_folder.mkdir(parents=True, exist_ok=True)

        for row in rows:
            source_image = source_folder / row["file"]
            if source_image.exists():
                shutil.copy2(source_image, output_folder / row["file"])

        output_txt = output_folder / f"{output_folder.name}.txt"
        with open(output_txt, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, delimiter="\t")
            writer.writerow(header[:10])
            writer.writerows(output_rows)

        return output_folder, output_txt

    def _generate_instruction_ramp(self):
        source_path = self.ramp_instruction_entry.get().strip()
        if not source_path or not os.path.isfile(source_path):
            messagebox.showerror("Instruction Ramping", "Select a valid instruction file first.", parent=self.window)
            return

        try:
            control_points = self._parse_control_layers()
            first_power = float(self.ramp_first_power_var.get().strip() or "255")
            if first_power < 0:
                raise ValueError("Power at the first control layer must be non-negative")
            mode = self.ramp_mode_var.get().strip().lower()
            if mode not in {"linear", "exponential"}:
                mode = "linear"

            self.ramp_generate_btn.config(state="disabled")
            self.ramp_status_label.config(text="Generating...")
            output_folder, output_txt = self._generate_controlled_ramp(source_path, control_points, mode, first_power)
            self.ramp_status_label.config(text="Done")
            self.update_status(f"Instruction ramp generated: {output_txt}")
            messagebox.showinfo("Instruction Ramping Complete", f"Output folder:\n{output_folder}", parent=self.window)
        except Exception as e:
            self.ramp_status_label.config(text="Failed")
            messagebox.showerror("Instruction Ramping Failed", str(e), parent=self.window)
            self.update_status(f"Instruction ramping failed: {e}", error=True)
        finally:
            self.ramp_generate_btn.config(state="normal")

    def _get_cone_params(self):
        try:
            initial_radius = float(self.cone_initial_radius_var.get().strip() or "0")
        except ValueError:
            initial_radius = 0.0
        try:
            ending_radius = float(self.cone_ending_radius_var.get().strip() or "500")
        except ValueError:
            ending_radius = 500.0
        try:
            height_um = float(self.cone_height_var.get().strip() or "1000")
        except ValueError:
            height_um = 1000.0
        try:
            layer_height_um = float(self.cone_layer_height_var.get().strip() or "50")
        except ValueError:
            layer_height_um = 50.0
        return initial_radius, ending_radius, height_um, layer_height_um

    def _generate_cone(self):
        base_folder = self.cone_output_entry.get().strip()
        if not base_folder or not os.path.isdir(base_folder):
            messagebox.showerror("Cone Generator", "Select a valid base folder first.", parent=self.window)
            return

        initial_radius, ending_radius, height_um, layer_height_um = self._get_cone_params()

        def run_generation():
            try:
                self.cone_status_label.config(text="Generating...")
                self.cone_generate_btn.config(state="disabled")
                output_folder = generate_cone_images(
                    base_folder,
                    initial_radius_um=initial_radius,
                    ending_radius_um=ending_radius,
                    height_um=height_um,
                    layer_height_um=layer_height_um,
                )
                self.window.after(0, lambda: self._cone_generation_done(output_folder, None))
            except Exception as e:
                self.window.after(0, lambda: self._cone_generation_done(None, str(e)))

        self._build_thread = threading.Thread(target=run_generation, daemon=True)
        self._build_thread.start()

    def _cone_generation_done(self, output_folder, error):
        self.cone_generate_btn.config(state="normal")
        if error:
            self.cone_status_label.config(text="Failed")
            messagebox.showerror("Cone Generator Failed", error, parent=self.window)
            self.update_status(f"Cone generation failed: {error}", error=True)
        else:
            self.cone_status_label.config(text="Done")
            self.update_status(f"Cone generation complete: {output_folder}")
            messagebox.showinfo("Cone Generator Complete", f"Output saved to:\n{output_folder}", parent=self.window)

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

        try:
            self._write_processing_summary(output_folder, error)
        except Exception as summary_error:
            self.update_status(f"Build logging failed: {summary_error}", error=True)

    def _resolve_build_session_dir(self, folder, create_if_missing=True):
        main_image_dir = os.path.abspath(os.path.dirname(folder))
        if self.prince_main_app_ref and hasattr(self.prince_main_app_ref, 'reserve_print_session_for_conditions'):
            try:
                if getattr(self.prince_main_app_ref, 'current_print_session_log_dir', None):
                    return self.prince_main_app_ref.current_print_session_log_dir
                return self.prince_main_app_ref.reserve_print_session_for_conditions()
            except Exception:
                pass

        if not create_if_missing:
            return None

        try:
            from support_modules.PrintSessionUtils import ensure_print_session
            session_info = ensure_print_session(main_image_dir)
            return session_info['print_dir']
        except Exception:
            return None

    def _write_processing_summary(self, output_folder, error):
        if not output_folder:
            return

        folder = self.folder_entry.get().strip()
        session_dir = self._resolve_build_session_dir(folder) if folder and os.path.isdir(folder) else None
        blur, globe, sigma, blend_angle, ge_sector_angle, ge_sector_smoothing, fd_strength, fd_decay, fd_smooth, fd_mode, fd_conductivity, fd_sink, sc_width, sc_min, sc_max, ee_falloff, sc_falloff, zc_layer_thickness, zc_penetration_depth, zc_strength, zc_min_factor, ee_min, ee_max = self._get_params()

        summary_rows = [
            ("timestamp", datetime.now().isoformat(timespec="seconds")),
            ("source_folder", folder),
            ("output_folder", output_folder),
            ("session_dir", session_dir or ""),
            ("status", "error" if error else "success"),
            ("error_message", error or ""),
            ("edge_enabled", self.ee_var.get()),
            ("blurring", blur),
            ("global_enabled", self.ge_var.get()),
            ("globe", globe),
            ("sigma", sigma),
            ("padding_enabled", self.pad_var.get()),
            ("global_asymmetric", self.ge_asymmetric_var.get()),
            ("blend_angle", blend_angle),
            ("ge_sector_angle", ge_sector_angle),
            ("ge_sector_smoothing", ge_sector_smoothing),
            ("depth_enabled", self.fd_var.get()),
            ("depth_strength", fd_strength),
            ("depth_decay_sigma", fd_decay),
            ("depth_smooth_sigma", fd_smooth),
            ("depth_mode", fd_mode),
            ("pressure_conductivity", fd_conductivity),
            ("pressure_sink", fd_sink),
            ("scatter_enabled", self.sc_var.get()),
            ("scatter_width", sc_width),
            ("scatter_min_val", sc_min),
            ("scatter_max_val", sc_max),
            ("axial_enabled", self.zc_var.get()),
            ("layer_thickness_um", zc_layer_thickness),
            ("penetration_depth_um", zc_penetration_depth),
            ("axial_strength", zc_strength),
            ("axial_min_factor", zc_min_factor),
            ("ee_falloff", ee_falloff),
            ("scatter_falloff", sc_falloff),
            ("ee_min", ee_min),
            ("ee_max", ee_max),
        ]

        os.makedirs(output_folder, exist_ok=True)
        summary_path = os.path.join(output_folder, "processing_summary.csv")
        with open(summary_path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["field", "value"])
            writer.writerows(summary_rows)

        if session_dir:
            os.makedirs(session_dir, exist_ok=True)
            session_log_path = os.path.join(session_dir, "image_build_log.csv")
            write_header = not os.path.exists(session_log_path)
            with open(session_log_path, "a", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                if write_header:
                    writer.writerow(["timestamp", "source_folder", "output_folder", "summary_path", "status", "error_message"])
                writer.writerow([
                    datetime.now().isoformat(timespec="seconds"),
                    folder,
                    output_folder,
                    summary_path,
                    "error" if error else "success",
                    error or "",
                ])

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
