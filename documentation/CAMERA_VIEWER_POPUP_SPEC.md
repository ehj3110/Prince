# Implementation Specification: Allied Vision Camera Viewer Pop-Up Window for `Prince_Segmented`

**Target Audience:** Autonomous Coding Agent / Software Engineer  
**Host Application:** `Prince_Segmented.py` (Tkinter GUI, Python 3.14 / Conda environment)  
**Hardware:** Allied Vision Alvium 1800 U-511m (Monochrome USB3 Machine Vision Camera)  
**SDK / Driver:** Allied Vision Vimba X (`vmbpy` v1.2.1)  
**Date:** September 2026  

---

## 1. Executive Summary & Objective

The objective is to implement a non-blocking pop-up window in `Prince_Segmented.py` allowing operators to view a real-time stream from the Allied Vision camera, pan and zoom interactively, and manipulate both hardware parameters (exposure time, gain) and software post-processing filters (contrast, gamma, brightness, alignment crosshairs).

### Key Architectural Constraints
1. **Tkinter GUI Thread Safety:** Tkinter is not thread-safe. Camera frames acquired asynchronously in a background thread must be delivered to the main GUI thread via a non-blocking queue (`queue.Queue(maxsize=1)`) and scheduled via `widget.after()`.
2. **Modern SDK (`vmbpy`):** Use Vimba X's `vmbpy` package (`from vmbpy import VmbSystem, Camera, Frame`). Do **not** use the legacy `vimba` package. The environment already has `vmbpy` installed in `.conda\Lib\site-packages\vmbpy`.
3. **High Resolution & Zero Lag:** The Alvium 1800 U-511m outputs $2464 \times 2064$ mono frames (~5.1 MP). To maintain 30+ FPS without UI stutter, software image adjustments (gamma, contrast) must use precomputed lookup tables (`cv2.LUT`), and viewport rendering must avoid expensive full-frame resizes on every tick.
4. **Clean Resource Lifecycle:** Vimba X transport layers and camera instances must be safely released when the pop-up window closes or when the application terminates to prevent device locking or driver segfaults.

---

## 2. Subsystem Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Prince_Segmented.py                              │
│                                                                             │
│  [Open Sensor Panel] [Exp. Conditions] [Image Modification] [Camera View]   │
└──────────────────────────────────────────────────────┬──────────────────────┘
                                                       │ clicks "Camera View"
                                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                CameraViewerWindow (tk.Toplevel Modal / Window)              │
│                                                                             │
│  ┌───────────────────────────────────────┐  ┌────────────────────────────┐  │
│  │ Interactive Viewport (tk.Canvas)      │  │ Control Panel              │  │
│  │                                       │  ├────────────────────────────┤  │
│  │  • Smooth Pan (Click & Drag)          │  │ Hardware Controls (vmbpy)  │  │
│  │  • Center-anchored Zoom (Scroll Wheel)│  │  • Exposure Time (µs)      │  │
│  │  • Alignment Crosshair Overlay        │  │  • Hardware Gain (dB)      │  │
│  │  • 1:1 / Fit-to-Window Reset          │  ├────────────────────────────┤  │
│  │                                       │  │ Software Adjustments       │  │
│  │                                       │  │  • Contrast (Alpha)        │  │
│  │                                       │  │  • Brightness (Beta)       │  │
│  │                                       │  │  • Gamma (cv2.LUT)         │  │
│  │                                       │  ├────────────────────────────┤  │
│  │                                       │  │ Actions                    │  │
│  │                                       │  │  • Snapshot (.png)         │  │
│  │                                       │  │  • Fit / Reset View        │  │
│  └───────────────────────────────────────┘  └────────────────────────────┘  │
└───────────────────────────────────▲─────────────────────────────────────────┘
                                    │ consumes newest frame
                       ┌────────────┴─────────────┐
                       │   queue.Queue(maxsize=1) │
                       └────────────▲─────────────┘
                                    │ puts newest frame (drops stale)
┌───────────────────────────────────┴─────────────────────────────────────────┐
│                    CameraStreamWorker (threading.Thread)                    │
│                                                                             │
│  • Manages VmbSystem.get_instance() context                                 │
│  • Discovers physical Alvium 1800 U-511m (filters simulators)               │
│  • Executes synchronous/streaming frame acquisition                         │
│  • Dispatches raw NumPy arrays to the frame queue                           │
│  • Applies runtime hardware adjustments (Exposure, Gain)                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Detailed Component Implementation

### Component A: Camera Driver & Worker (`calibration_modules/vmb_camera_worker.py`)

Create or update `calibration_modules/vmb_camera_worker.py` to isolate the `vmbpy` lifecycle from the GUI.

```python
"""
Vimba X Camera Worker for Allied Vision Cameras
File: calibration_modules/vmb_camera_worker.py
"""

import queue
import threading
import time
from typing import Optional, Tuple
import cv2
import numpy as np

try:
    from vmbpy import VmbSystem, Camera, Frame, VmbCameraError, VmbFeatureError
    VMBPY_AVAILABLE = True
except ImportError:
    VMBPY_AVAILABLE = False


class VmbCameraWorker(threading.Thread):
    """
    Dedicated worker thread for camera communication and continuous streaming.
    Ensures Vimba X C-API calls remain on a single thread and off the GUI loop.
    """

    def __init__(self, frame_queue: queue.Queue):
        super().__init__(daemon=True)
        self.frame_queue = frame_queue
        self.running = False
        self.connected = False
        self.cam_id: Optional[str] = None
        self.cam_model: str = "Unknown"

        # Hardware parameter requests (handled inside camera thread)
        self._pending_exposure: Optional[float] = None
        self._pending_gain: Optional[float] = None
        self._lock = threading.Lock()

        # Cached hardware limits
        self.exposure_range: Tuple[float, float] = (100.0, 1000000.0)
        self.gain_range: Tuple[float, float] = (0.0, 24.0)

    def request_exposure(self, exposure_us: float):
        with self._lock:
            self._pending_exposure = float(exposure_us)

    def request_gain(self, gain_db: float):
        with self._lock:
            self._pending_gain = float(gain_db)

    def stop(self):
        self.running = False

    def run(self):
        if not VMBPY_AVAILABLE:
            print("ERROR: vmbpy is not installed in the active environment.")
            return

        self.running = True
        try:
            with VmbSystem.get_instance() as vmb:
                # 1. Discover physical camera
                cameras = vmb.get_all_cameras()
                physical_cameras = [
                    c for c in cameras if "Simulator" not in c.get_model() and "Simulator" not in c.get_id()
                ]

                if not physical_cameras:
                    print("ERROR: No physical Allied Vision cameras detected.")
                    return

                cam: Camera = physical_cameras[0]
                with cam:
                    self.cam_id = cam.get_id()
                    self.cam_model = cam.get_model()
                    self.connected = True
                    print(f"Connected to {self.cam_model} ({self.cam_id})")

                    # Read supported hardware limits
                    try:
                        feat_exp = cam.get_feature_by_name("ExposureTime")
                        self.exposure_range = feat_exp.get_range()
                    except Exception as e:
                        print(f"Warning: Could not read ExposureTime range: {e}")

                    try:
                        feat_gain = cam.get_feature_by_name("Gain")
                        self.gain_range = feat_gain.get_range()
                    except Exception as e:
                        print(f"Warning: Could not read Gain range: {e}")

                    # 2. Continuous acquisition loop
                    while self.running:
                        # Apply pending hardware changes
                        with self._lock:
                            if self._pending_exposure is not None:
                                try:
                                    exp_clamped = max(self.exposure_range[0], min(self._pending_exposure, self.exposure_range[1]))
                                    cam.get_feature_by_name("ExposureTime").set(exp_clamped)
                                except Exception as e:
                                    print(f"Failed to set ExposureTime: {e}")
                                self._pending_exposure = None

                            if self._pending_gain is not None:
                                try:
                                    gain_clamped = max(self.gain_range[0], min(self._pending_gain, self.gain_range[1]))
                                    cam.get_feature_by_name("Gain").set(gain_clamped)
                                except Exception as e:
                                    print(f"Failed to set Gain: {e}")
                                self._pending_gain = None

                        # Grab frame (timeout = 2000 ms)
                        try:
                            frame: Frame = cam.get_frame(timeout_ms=2000)
                            image: np.ndarray = frame.as_opencv_image()

                            # Ensure 2D grayscale representation
                            if image.ndim == 3 and image.shape[2] == 1:
                                image = image[:, :, 0]

                            # Non-blocking enqueue (overwrite older frames)
                            if self.frame_queue.full():
                                try:
                                    self.frame_queue.get_nowait()
                                except queue.Empty:
                                    pass
                            self.frame_queue.put_nowait(image)
                        except Exception as e:
                            time.sleep(0.01)
                            continue

        except Exception as exc:
            print(f"CRITICAL: Camera worker encountered exception: {exc}")
        finally:
            self.connected = False
            self.running = False
            print("Camera worker stopped cleanly.")
```

---

### Component B: Interactive Zoom & Pan Viewport (`calibration_modules/zoom_pan_canvas.py`)

Create a dedicated reusable widget extending `tk.Canvas` that manages the transformation between camera image pixels and the UI canvas display coordinates.

#### Coordinate Mapping & Math
Let:
- $I_{W}, I_{H}$ be raw camera image dimensions ($2464 \times 2064$).
- $C_{W}, C_{H}$ be canvas widget pixel dimensions.
- $Z$ be current `zoom_scale` (where $1.0$ is $100\%$ scale).
- $(O_X, O_Y)$ be pan offsets in canvas coordinate space.

**Anchor Zooming on Mouse Cursor $(m_x, m_y)$:**
When the user scrolls the mouse wheel with scale factor $k$:
$$Z_{new} = Z \times k$$
To keep the pixel beneath $(m_x, m_y)$ stationary:
$$O_{X, new} = m_x - k \cdot (m_x - O_X)$$
$$O_{Y, new} = m_y - k \cdot (m_y - O_Y)$$

```python
"""
Interactive Zoom and Pan Canvas
File: calibration_modules/zoom_pan_canvas.py
"""

import tkinter as tk
import cv2
import numpy as np
from PIL import Image, ImageTk


class ZoomPanCanvas(tk.Canvas):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg="#1a1a1a", highlightthickness=0, **kwargs)

        self.raw_image: Optional[np.ndarray] = None
        self.display_photo: Optional[ImageTk.PhotoImage] = None

        # Viewport transformation parameters
        self.zoom_scale = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self._drag_start_x = 0
        self._drag_start_y = 0

        # Software Filter Parameters
        self.contrast_alpha = 1.0   # [0.2 to 3.0]
        self.brightness_beta = 0    # [-100 to 100]
        self.gamma_val = 1.0        # [0.2 to 3.0]
        self.show_crosshair = True
        self._gamma_lut = self._build_gamma_lut(1.0)

        # Bindings for mouse interactions
        self.bind("<ButtonPress-1>", self._on_pan_start)
        self.bind("<B1-Motion>", self._on_pan_drag)
        self.bind("<MouseWheel>", self._on_zoom_wheel)  # Windows
        self.bind("<Button-4>", self._on_zoom_wheel)    # Linux scroll up
        self.bind("<Button-5>", self._on_zoom_wheel)    # Linux scroll down
        self.bind("<Double-Button-1>", lambda e: self.reset_view())
        self.bind("<Configure>", lambda e: self.redraw())

    def _build_gamma_lut(self, gamma: float) -> np.ndarray:
        inv_gamma = 1.0 / max(0.01, gamma)
        table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
        return table

    def set_gamma(self, gamma: float):
        self.gamma_val = gamma
        self._gamma_lut = self._build_gamma_lut(gamma)
        self.redraw()

    def set_contrast_brightness(self, alpha: float, beta: int):
        self.contrast_alpha = alpha
        self.brightness_beta = beta
        self.redraw()

    def set_raw_frame(self, image: np.ndarray):
        """Called upon receipt of a new camera frame."""
        self.raw_image = image
        if self.zoom_scale == 1.0 and self.pan_x == 0.0 and self.pan_y == 0.0:
            self.reset_view()
        else:
            self.redraw()

    def reset_view(self):
        """Fit raw image into current canvas dimensions."""
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

    def set_one_to_one(self):
        """Set zoom scale to 1:1 pixel view centered."""
        if self.raw_image is None:
            return
        cw = max(1, self.winfo_width())
        ch = max(1, self.winfo_height())
        ih, iw = self.raw_image.shape[:2]

        self.zoom_scale = 1.0
        self.pan_x = (cw - iw) / 2.0
        self.pan_y = (ch - ih) / 2.0
        self.redraw()

    def _on_pan_start(self, event):
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
        if self.raw_image is None:
            return

        # Determine wheel delta
        if event.num == 5 or event.delta < 0:
            factor = 0.85  # Zoom out
        else:
            factor = 1.15  # Zoom in

        # Clamp zoom limits: 0.05x to 15x
        new_scale = max(0.05, min(self.zoom_scale * factor, 15.0))
        actual_k = new_scale / self.zoom_scale

        # Zoom centered on mouse pointer
        mx, my = event.x, event.y
        self.pan_x = mx - actual_k * (mx - self.pan_x)
        self.pan_y = my - actual_k * (my - self.pan_y)
        self.zoom_scale = new_scale
        self.redraw()

    def redraw(self):
        if self.raw_image is None:
            return

        cw = self.winfo_width()
        ch = self.winfo_height()
        if cw < 10 or ch < 10:
            return

        # 1. Apply Fast Image Adjustments (Contrast, Brightness, Gamma)
        proc = self.raw_image
        if self.contrast_alpha != 1.0 or self.brightness_beta != 0:
            proc = cv2.convertScaleAbs(proc, alpha=self.contrast_alpha, beta=self.brightness_beta)
        if self.gamma_val != 1.0:
            proc = cv2.LUT(proc, self._gamma_lut)

        # 2. Viewport Slicing (ROI) to avoid resizing giant textures unnecessarily
        ih, iw = proc.shape[:2]
        x0_img = int(max(0, -self.pan_x / self.zoom_scale))
        y0_img = int(max(0, -self.pan_y / self.zoom_scale))
        x1_img = int(min(iw, (cw - self.pan_x) / self.zoom_scale))
        y1_img = int(min(ih, (ch - self.pan_y) / self.zoom_scale))

        if x1_img <= x0_img or y1_img <= y0_img:
            return

        roi = proc[y0_img:y1_img, x0_img:x1_img]

        # Target dimensions for sliced ROI on canvas
        out_w = int((x1_img - x0_img) * self.zoom_scale)
        out_h = int((y1_img - y0_img) * self.zoom_scale)

        if out_w <= 0 or out_h <= 0:
            return

        interp = cv2.INTER_NEAREST if self.zoom_scale > 1.5 else cv2.INTER_LINEAR
        resized = cv2.resize(roi, (out_w, out_h), interpolation=interp)

        # Canvas coordinates where ROI starts
        dest_x = int(self.pan_x + x0_img * self.zoom_scale)
        dest_y = int(self.pan_y + y0_img * self.zoom_scale)

        pil_img = Image.fromarray(resized)
        self.display_photo = ImageTk.PhotoImage(pil_img)

        self.delete("all")
        self.create_image(dest_x, dest_y, anchor=tk.NW, image=self.display_photo)

        # 3. Optional Center Crosshair Overlay
        if self.show_crosshair:
            center_x = int(self.pan_x + (iw / 2.0) * self.zoom_scale)
            center_y = int(self.pan_y + (ih / 2.0) * self.zoom_scale)
            cross_size = 30
            self.create_line(center_x - cross_size, center_y, center_x + cross_size, center_y, fill="#00FF66", width=1)
            self.create_line(center_x, center_y - cross_size, center_x, center_y + cross_size, fill="#00FF66", width=1)
            self.create_oval(center_x - 10, center_y - 10, center_x + 10, center_y + 10, outline="#00FF66", width=1)
```

---

### Component C: Pop-Up Window UI (`calibration_modules/CameraViewWindow.py`)

Replace or modernize `calibration_modules/CameraViewWindow.py` to integrate the worker thread, the zoomable canvas, and comprehensive controls.

```python
"""
Camera View Window Pop-up
File: calibration_modules/CameraViewWindow.py
"""

import os
import queue
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import cv2
import numpy as np

from .vmb_camera_worker import VmbCameraWorker
from .zoom_pan_canvas import ZoomPanCanvas


class CameraViewWindow:
    """
    Pop-up Toplevel window allowing full camera preview, zoom/pan,
    hardware parameter tuning, and image post-processing.
    """

    def __init__(self, parent):
        self.parent = parent
        self.window = tk.Toplevel(parent)
        self.window.title("Allied Vision Alvium Preview & Alignment")
        self.window.geometry("1300x850")
        self.window.minsize(900, 600)

        # Threading queue & worker
        self.frame_queue = queue.Queue(maxsize=1)
        self.worker = VmbCameraWorker(self.frame_queue)

        # UI Setup
        self._build_ui()

        # Handle window close
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Start Camera Stream
        self.worker.start()
        self._poll_camera_frames()

    def _build_ui(self):
        # Master grid layout
        self.window.columnconfigure(0, weight=4)  # Canvas area
        self.window.columnconfigure(1, weight=1)  # Controls area
        self.window.rowconfigure(0, weight=1)
        self.window.rowconfigure(1, weight=0)      # Status bar

        # Left: Canvas
        canvas_frame = ttk.Frame(self.window)
        canvas_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.canvas = ZoomPanCanvas(canvas_frame)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Right: Control Panel
        control_panel = ttk.Frame(self.window, padding=10)
        control_panel.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        # Section 1: Navigation / Zoom Controls
        nav_box = ttk.LabelFrame(control_panel, text="Viewport & Zoom", padding=8)
        nav_box.pack(fill=tk.X, pady=5)

        btn_row = ttk.Frame(nav_box)
        btn_row.pack(fill=tk.X, pady=2)
        ttk.Button(btn_row, text="Fit View", command=self.canvas.reset_view).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        ttk.Button(btn_row, text="1:1 (100%)", command=self.canvas.set_one_to_one).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        self.crosshair_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(nav_box, text="Show Center Crosshair", variable=self.crosshair_var, command=self._toggle_crosshair).pack(anchor=tk.W, pady=4)

        # Section 2: Hardware Settings
        hw_box = ttk.LabelFrame(control_panel, text="Hardware Controls", padding=8)
        hw_box.pack(fill=tk.X, pady=5)

        # Exposure
        ttk.Label(hw_box, text="Exposure (µs):").pack(anchor=tk.W)
        exp_row = ttk.Frame(hw_box)
        exp_row.pack(fill=tk.X, pady=2)
        self.exp_slider = ttk.Scale(exp_row, from_=100, to=200000, orient=tk.HORIZONTAL, command=self._on_exposure_slider)
        self.exp_slider.set(20000)
        self.exp_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.exp_var = tk.StringVar(value="20000")
        self.exp_entry = ttk.Entry(exp_row, textvariable=self.exp_var, width=8)
        self.exp_entry.pack(side=tk.LEFT, padx=5)
        self.exp_entry.bind("<Return>", lambda e: self._on_exposure_entry())

        # Gain
        ttk.Label(hw_box, text="Gain (dB):").pack(anchor=tk.W, pady=(8, 0))
        gain_row = ttk.Frame(hw_box)
        gain_row.pack(fill=tk.X, pady=2)
        self.gain_slider = ttk.Scale(gain_row, from_=0, to=24, orient=tk.HORIZONTAL, command=self._on_gain_slider)
        self.gain_slider.set(0)
        self.gain_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.gain_var = tk.StringVar(value="0.0")
        self.gain_entry = ttk.Entry(gain_row, textvariable=self.gain_var, width=8)
        self.gain_entry.pack(side=tk.LEFT, padx=5)
        self.gain_entry.bind("<Return>", lambda e: self._on_gain_entry())

        # Section 3: Software Processing
        sw_box = ttk.LabelFrame(control_panel, text="Display / Image Adjustments", padding=8)
        sw_box.pack(fill=tk.X, pady=5)

        # Contrast
        ttk.Label(sw_box, text="Contrast (Alpha):").pack(anchor=tk.W)
        self.contrast_slider = ttk.Scale(sw_box, from_=0.2, to=3.0, orient=tk.HORIZONTAL, command=self._update_software_filters)
        self.contrast_slider.set(1.0)
        self.contrast_slider.pack(fill=tk.X, pady=2)

        # Brightness
        ttk.Label(sw_box, text="Brightness (Offset):").pack(anchor=tk.W, pady=(6, 0))
        self.brightness_slider = ttk.Scale(sw_box, from_=-100, to=100, orient=tk.HORIZONTAL, command=self._update_software_filters)
        self.brightness_slider.set(0)
        self.brightness_slider.pack(fill=tk.X, pady=2)

        # Gamma
        ttk.Label(sw_box, text="Gamma:").pack(anchor=tk.W, pady=(6, 0))
        self.gamma_slider = ttk.Scale(sw_box, from_=0.2, to=3.0, orient=tk.HORIZONTAL, command=self._update_software_filters)
        self.gamma_slider.set(1.0)
        self.gamma_slider.pack(fill=tk.X, pady=2)

        ttk.Button(sw_box, text="Reset Image Filters", command=self._reset_filters).pack(fill=tk.X, pady=6)

        # Section 4: Capture & Save
        act_box = ttk.LabelFrame(control_panel, text="Capture", padding=8)
        act_box.pack(fill=tk.X, pady=5)
        ttk.Button(act_box, text="📸 Save Snapshot", command=self.save_snapshot).pack(fill=tk.X, pady=3)

        # Status Bar
        self.status_var = tk.StringVar(value="Connecting to camera...")
        status_bar = ttk.Label(self.window, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, padding=4)
        status_bar.grid(row=1, column=0, columnspan=2, sticky="ew")

    def _toggle_crosshair(self):
        self.canvas.show_crosshair = self.crosshair_var.get()
        self.canvas.redraw()

    def _on_exposure_slider(self, val):
        val = round(float(val))
        self.exp_var.set(str(val))
        self.worker.request_exposure(val)

    def _on_exposure_entry(self):
        try:
            val = float(self.exp_var.get())
            self.exp_slider.set(val)
            self.worker.request_exposure(val)
        except ValueError:
            pass

    def _on_gain_slider(self, val):
        val = round(float(val), 1)
        self.gain_var.set(str(val))
        self.worker.request_gain(val)

    def _on_gain_entry(self):
        try:
            val = float(self.gain_var.get())
            self.gain_slider.set(val)
            self.worker.request_gain(val)
        except ValueError:
            pass

    def _update_software_filters(self, _=None):
        alpha = float(self.contrast_slider.get())
        beta = int(float(self.brightness_slider.get()))
        gamma = float(self.gamma_slider.get())
        self.canvas.contrast_alpha = alpha
        self.canvas.brightness_beta = beta
        self.canvas.set_gamma(gamma)

    def _reset_filters(self):
        self.contrast_slider.set(1.0)
        self.brightness_slider.set(0)
        self.gamma_slider.set(1.0)
        self._update_software_filters()

    def save_snapshot(self):
        if self.canvas.raw_image is None:
            messagebox.showwarning("Snapshot", "No frame available to save.")
            return

        default_name = f"camera_snap_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = filedialog.asksaveasfilename(
            parent=self.window,
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("TIFF Image", "*.tiff"), ("JPEG Image", "*.jpg")],
            initialfile=default_name
        )
        if filepath:
            cv2.imwrite(filepath, self.canvas.raw_image)
            self.status_var.set(f"Saved snapshot: {os.path.basename(filepath)}")

    def _poll_camera_frames(self):
        """Poll the frame queue on Tkinter's event loop every 30ms (~33 FPS)."""
        if not self.window.winfo_exists():
            return

        try:
            frame = self.frame_queue.get_nowait()
            self.canvas.set_raw_frame(frame)
            if self.worker.connected:
                self.status_var.set(f"Streaming | Camera: {self.worker.cam_model} ({self.worker.cam_id}) | Frame: {frame.shape[1]}x{frame.shape[0]} | Zoom: {self.canvas.zoom_scale:.2f}x")
        except queue.Empty:
            if not self.worker.connected and not self.worker.running:
                self.status_var.set("Camera disconnected or not found.")
        finally:
            self.window.after(30, self._poll_camera_frames)

    def on_closing(self):
        """Release camera and cleanly destroy window."""
        self.worker.stop()
        self.window.destroy()
```

---

## 4. Main GUI Integration (`Prince_Segmented.py`)

In `Prince_Segmented.py`, add the button and opening logic following the exact pattern of `open_image_modification_window` and `open_sensor_panel`.

### Step 1: Add import at top of `Prince_Segmented.py`
```python
from calibration_modules.CameraViewWindow import CameraViewWindow
```

### Step 2: Initialize attribute in `MyWindow.__init__`
```python
self.camera_view_window = None
```

### Step 3: Add button in button cluster (around lines 125–130)
In `MyWindow.__init__`, place the new button next to `self.b_viscosity_monitor`:
```python
self.b_camera_view = Button(win, text="Camera View", command=self.open_camera_view_window)
self.b_camera_view.place(x=1340, y=60)  # Next to Viscosity Monitor (x=1205, y=60)
```

### Step 4: Add opening and single-instance management method
In `MyWindow` methods (around lines 2240–2260):
```python
def open_camera_view_window(self):
    """Open or focus the Camera View pop-up window."""
    if (self.camera_view_window is None or
            not (hasattr(self.camera_view_window, 'window') and
                 self.camera_view_window.window.winfo_exists())):
        try:
            self.camera_view_window = CameraViewWindow(self.win)
            self.update_status_message("Camera View window opened.")
        except Exception as e:
            self.update_status_message(f"Failed to open Camera View: {e}", error=True)
            messagebox.showerror("Camera Error", f"Could not launch camera window:\n{e}")
    else:
        self.camera_view_window.window.lift()
        self.camera_view_window.window.focus_force()
```

### Step 5: Application shutdown protocol
Ensure that if the user closes the main `Prince_Segmented` window, any open camera window and worker thread are cleanly closed:
```python
# In MyWindow's window-closing handler or on_exit cleanup:
if self.camera_view_window and hasattr(self.camera_view_window, 'window') and self.camera_view_window.window.winfo_exists():
    self.camera_view_window.on_closing()
```

---

## 5. Verification & Testing Checklist for the Implementing Agent

| # | Step / Action | Expected Result |
|---|---------------|-----------------|
| 1 | **Test Driver in Isolation**<br>`.\.conda\python.exe calibration_modules/hardware_connection_test_vmbpy.py` | Exits with `code 0`, reports `SUCCESS: camera=1800 U-511m`. |
| 2 | **Test Standalone Viewer**<br>Run `CameraViewWindow.py` directly under `if __name__ == '__main__':` | Pop-up window opens, video stream displays smoothly with green crosshair. |
| 3 | **Test Zoom & Pan Interaction** | • Scrolling up zooms in centered on cursor.<br>• Scrolling down zooms out.<br>• Left-click drag pans smoothly.<br>• Double-click or "Fit View" centers and resets full image. |
| 4 | **Test Hardware Parameter Controls** | • Modifying Exposure slider or entry immediately updates image brightness.<br>• Modifying Gain slider updates sensitivity/noise without crashes. |
| 5 | **Test Software Image Controls** | • Adjusting Contrast modifies dynamic range.<br>• Adjusting Brightness shifts black level.<br>• Adjusting Gamma brightens shadows without clipping highlights. |
| 6 | **Test Snapshot** | Clicking "Save Snapshot" prompts file dialog and saves accurate uncompressed PNG. |
| 7 | **Test Single Instance Behavior** | Clicking "Camera View" in `Prince_Segmented.py` multiple times brings existing window to front instead of launching duplicates. |
| 8 | **Test Clean Disconnection** | Closing pop-up window terminates the worker thread without freezing `Prince_Segmented.py` or causing Vimba X resource leaks. |
