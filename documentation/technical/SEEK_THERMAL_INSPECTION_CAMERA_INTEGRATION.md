# Seek Thermal Inspection Camera Integration Guide

**System:** Prince SLA / DLP Stereolithography & In-situ Viscometry Platform  
**Target Applications:** In-situ photopolymerization exotherm tracking, resin vat temperature monitoring, optical + thermal multi-spectral alignment  
**Author:** Cheng Sun Lab  
**Date:** September 2026  

---

## 1. Executive Summary & Value Proposition

Integrating an infrared thermal inspection camera alongside the primary high-resolution Allied Vision optical camera provides essential physical insights during resin stereolithography:

1. **Photopolymerization Exotherm Kinetics:** Acrylic and methacrylic radical photopolymerization is strongly exothermic. During UV/DLP pattern projection, the localized temperature rises by $5^\circ\text{C}$ to $35^\circ\text{C}$ depending on photoinitiator concentration, exposure intensity, and layer thickness. Monitoring peak temperature ($\Delta T_{\text{exotherm}}$) provides real-time validation of cure completion and reaction kinetics.
2. **Resin Viscosity Thermal Correction:** As documented in [RESIN_VISCOSITY_SQUEEZE_FLOW_PHYSICS.md](RESIN_VISCOSITY_SQUEEZE_FLOW_PHYSICS.md), resin dynamic viscosity drops significantly with temperature (typically $2-5\%$ per $^\circ\text{C}$). Tracking the bulk resin vat temperature allows the squeeze-flow model to dynamically adjust viscosity baseline estimates.
3. **Thermal Stress & Delamination Prevention:** Uneven heat dissipation across large cross-sectional exposures induces thermal shrinkage stresses, which are a primary cause of part warping and detachment from the build plate.
4. **Machine Health Diagnostics:** Continuous monitoring of the UV DLP LED engine heat dissipation and Z-axis motor temperature.

---

## 2. Hardware Architecture & Camera Options

### Supported Seek Thermal Hardware

| Model | Resolution | Framerate | Spectral Range | Interface | Primary Advantage |
|-------|------------|-----------|----------------|-----------|-------------------|
| **Seek Compact** | $206 \times 156$ (32k px) | 9 Hz | $7.5 - 14\ \mu\text{m}$ VOx | USB-C / Micro-USB | Low cost, compact form factor |
| **Seek CompactPRO** | $320 \times 240$ (76.8k px) | 9 Hz | $7.5 - 14\ \mu\text{m}$ VOx | USB-C / Micro-USB | High thermal resolution, adjustable focus |
| **Seek Mosaic Core / MicroCore** | $206 \times 156$ / $320 \times 240$ | Up to 30 Hz | $7.5 - 14\ \mu\text{m}$ VOx | SPI / USB OEM header | Embedded integration, higher framerates |

> [!NOTE]
> All commercial Seek Thermal cameras are restricted to **9 Hz (or 8.6 Hz)** framerates unless export licenses are in place (ITAR/EAR compliance). A 9 Hz capture rate is more than sufficient for 3D printing exotherms, where thermal time constants are on the order of $0.5 - 5.0$ seconds.

---

## 3. Python SDK & Driver Landscape on Windows

### Option A: Official `seekcamera-python` (Recommended)

Seek Thermal provides official Python bindings wrapping `seekcamera.dll` on Windows:

```powershell
# In Prince Conda environment:
.\.conda\python.exe -m pip install seekcamera-python
```

#### Key Architecture of `seekcamera-python`:
- **`SeekCameraManager`**: Discovers connected USB cameras and manages lifecycle events.
- **`SeekCameraFrameFormat.THERMOGRAPHY_FLOAT`**: Outputs a 2D NumPy array of floating-point temperatures in **degrees Celsius** directly for each pixel (essential for quantitative analysis).
- **`SeekCameraFrameFormat.COLOR_ARGB_8888`**: Outputs pre-colorized 32-bit preview frames for immediate rendering.
- **`SeekCameraColorPalette`**: Hardware/SDK colormaps (`SPECTRA`, `IRON`, `WHITE_HOT`, `BLACK_HOT`, `AMBER`).

### Option B: PyUSB / `libseek-thermal` (Alternative / Open-Source)

If working with custom USB firmware or older Compact units without vendor SDK licensing:
- Uses `pyusb` (`pip install pyusb`) with the WinUSB or LibUSB-Win32 driver installed via Zadig.
- Directly decodes raw 14-bit microbolometer readout counts, applies Non-Uniformity Correction (NUC) with shutter frames, and converts counts to temperature via sensor calibration equations.

---

## 4. End-to-End Software Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                          Prince_Segmented.py                           │
│                                                                        │
│  [Open Sensor Panel]  [Exp. Conditions]  [Dual Camera View (Opt/IR)]   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ opens
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   DualCameraViewerWindow (Tkinter)                     │
│                                                                        │
│   ┌──────────────────────────────────┐┌──────────────────────────────┐ │
│   │ Optical View (Allied Vision)     ││ Thermal View (Seek Thermal)  │ │
│   │ 2464 x 2064 Monochrome           ││ 320 x 240 Radiometric IR     │ │
│   │                                  ││                              │ │
│   │ • Meniscus & Part Alignment      ││ • Exotherm False-Color Map   │ │
│   │ • Pan & Zoom Reticle             ││ • Spot Probe: T=34.2 °C      │ │
│   │ • Exposure / Gain Controls       ││ • Palette: Inferno / Iron    │ │
│   └──────────────────────────────────┘└──────────────────────────────┘ │
│                                                                        │
│   Status: Optical: 7.1 FPS | Thermal: 8.9 FPS | Vat Peak: 28.4 °C      │
└───────────────────▲──────────────────────────────▲─────────────────────┘
                    │                              │
       queue.Queue(maxsize=1)         queue.Queue(maxsize=1)
                    │                              │
┌───────────────────┴──────────────┐┌──────────────┴─────────────────────┐
│  VmbCameraWorker (Allied Vision) ││ SeekThermalWorker (Seek Thermal)   │
│  • vmbpy C-API                   ││ • seekcamera-python SDK            │
│  • Alvium 1800 U-511m            ││ • Compact / CompactPRO Core        │
│  • High-res machine vision       ││ • Radiometric float arrays (°C)    │
└──────────────────────────────────┘└────────────────────────────────────┘
```

---

## 5. Reference Implementation: `SeekThermalWorker`

The following production-ready module can be placed in `calibration_modules/seek_thermal_worker.py`:

```python
"""
Seek Thermal Camera Worker for Prince Platform.
File: calibration_modules/seek_thermal_worker.py
"""

from __future__ import annotations

import queue
import threading
import time
from typing import Optional, Tuple
import cv2
import numpy as np

try:
    from seekcamera import (
        SeekCameraManager,
        SeekCameraManagerEvent,
        SeekCameraFrameFormat,
        SeekCameraColorPalette,
        SeekCameraIOType,
    )
    SEEK_AVAILABLE = True
except ImportError:
    SEEK_AVAILABLE = False


class SeekThermalWorker(threading.Thread):
    """
    Dedicated acquisition worker for Seek Thermal USB cameras.
    Provides:
    - 2D float32 array in degrees Celsius for thermography.
    - 2D/3D uint8 false-color image for live Tkinter display.
    - Spot and regional temperature telemetry (min, max, mean).
    """

    def __init__(self, frame_queue: queue.Queue, palette_name: str = "INFERNO"):
        super().__init__(daemon=True, name="SeekThermalWorker")
        self.frame_queue = frame_queue
        self.palette_name = palette_name
        self._running = False
        self.connected = False
        self.cam_id: str = "Unknown"
        self.last_error: Optional[str] = None

        # Telemetry
        self.fps: float = 0.0
        self.min_temp_c: float = 0.0
        self.max_temp_c: float = 0.0
        self.mean_temp_c: float = 0.0

        self._camera = None
        self._manager = None
        self._last_fps_time = time.perf_counter()
        self._fps_frame_count = 0

    def stop(self, timeout: float = 3.0):
        self._running = False
        if self.is_alive() and threading.current_thread() is not self:
            self.join(timeout=timeout)

    def _on_frame_available(self, _camera, camera_frame, _user_data):
        if not self._running:
            return

        try:
            # 1. Extract raw radiometric temperature array (in Celsius)
            temp_frame = camera_frame.thermography_float
            temp_c_data = np.frombuffer(temp_frame.data, dtype=np.float32).reshape(
                (temp_frame.height, temp_frame.width)
            ).copy()

            # 2. Compute temperature telemetry
            self.min_temp_c = float(np.min(temp_c_data))
            self.max_temp_c = float(np.max(temp_c_data))
            self.mean_temp_c = float(np.mean(temp_c_data))

            # 3. Create display colormap (Normalized to min/max or fixed printing range)
            t_min = max(15.0, self.min_temp_c)
            t_max = min(60.0, max(t_min + 5.0, self.max_temp_c))
            norm = np.clip((temp_c_data - t_min) / (t_max - t_min) * 255.0, 0, 255).astype(np.uint8)
            color_img = cv2.applyColorMap(norm, cv2.COLORMAP_INFERNO)

            # 4. Telemetry FPS calculation
            self._fps_frame_count += 1
            now = time.perf_counter()
            elapsed = now - self._last_fps_time
            if elapsed >= 1.0:
                self.fps = round(self._fps_frame_count / elapsed, 1)
                self._fps_frame_count = 0
                self._last_fps_time = now

            # 5. Non-blocking enqueue: payload is (temperature_array_c, color_image_bgr)
            payload = (temp_c_data, color_img)
            if self.frame_queue.full():
                try:
                    self.frame_queue.get_nowait()
                except queue.Empty:
                    pass
            self.frame_queue.put_nowait(payload)

        except Exception as exc:
            self.last_error = str(exc)

    def _on_camera_event(self, _camera_manager, camera, event_type, _user_data):
        if event_type == SeekCameraManagerEvent.CONNECT:
            print(f"Seek Thermal connected: {camera.chipid}")
            self.cam_id = str(camera.chipid)
            self._camera = camera
            self.connected = True
            # Request thermography mode
            camera.capture_session_start(SeekCameraFrameFormat.THERMOGRAPHY_FLOAT)
        elif event_type == SeekCameraManagerEvent.DISCONNECT:
            print(f"Seek Thermal disconnected: {camera.chipid}")
            self.connected = False
            self._camera = None

    def run(self):
        if not SEEK_AVAILABLE:
            self.last_error = "seekcamera-python not installed"
            print(f"ERROR: {self.last_error}")
            return

        self._running = True
        try:
            with SeekCameraManager(SeekCameraIOType.USB) as manager:
                self._manager = manager
                manager.register_event_callback(self._on_camera_event)
                manager.register_frame_available_callback(self._on_frame_available)

                while self._running:
                    time.sleep(0.1)

                if self._camera:
                    self._camera.capture_session_stop()
        except Exception as exc:
            self.last_error = str(exc)
            print(f"SeekThermalWorker error: {exc}")
        finally:
            self.connected = False
            self._running = False
```

---

## 6. Real-Time Spot Temperature Probing

When displaying the thermal canvas in Tkinter, operators can hover over any feature (e.g. vat boundary, curing cross-section, LED hot spot) to inspect the exact temperature.

```python
def on_thermal_canvas_hover(self, event):
    """Calculate and display exact temperature under cursor."""
    if self.latest_temp_array is None:
        return

    # Map canvas coordinate (event.x, event.y) to thermal sensor pixel (px, py)
    canvas_w = self.thermal_canvas.winfo_width()
    canvas_h = self.thermal_canvas.winfo_height()
    th_h, th_w = self.latest_temp_array.shape[:2]

    px = int(event.x * (th_w / canvas_w))
    py = int(event.y * (th_h / canvas_h))

    if 0 <= px < th_w and 0 <= py < th_h:
        temp_c = self.latest_temp_array[py, px]
        self.probe_label.config(text=f"Spot T: {temp_c:.1f} °C (X:{px}, Y:{py})")
```

---

## 7. Automated Layer Exotherm Logging in Prince

During printing, `Prince_Segmented.py` manages exposure sequences. The thermal camera worker can be linked into `SessionManager` and `PeakForceLogger` to log thermal data per layer.

### Logged Parameters in Session CSV (`SessionLogs/Session_<date>_thermal.csv`)

| Column Name | Unit | Description |
|-------------|------|-------------|
| `Layer_Number` | int | Current printing layer index |
| `Timestamp` | ISO 8601 | Start of exposure timestamp |
| `T_baseline_C` | $^\circ\text{C}$ | Vat temperature 0.5s before DLP exposure starts |
| `T_peak_C` | $^\circ\text{C}$ | Maximum temperature recorded during exposure |
| `Delta_T_exotherm` | $^\circ\text{C}$ | $T_{\text{peak}} - T_{\text{baseline}}$ (cure exotherm intensity) |
| `T_mean_vat_C` | $^\circ\text{C}$ | Average temperature across resin bath |
| `Exotherm_Energy_J` | J | Integrated thermal response over exposure window |

### Workflow Hook in `Prince_Segmented.py`:

```python
# Before DLP light trigger:
t_pre = thermal_worker.mean_temp_c

# Trigger pattern on DLP:
self.controller.startsequence()

# Monitor exotherm peak during exposure window:
peak_temp = 0.0
start_time = time.perf_counter()
while time.perf_counter() - start_time < layer_exposure_time:
    peak_temp = max(peak_temp, thermal_worker.max_temp_c)
    time.sleep(0.05)

# Record exotherm metric:
delta_t = peak_temp - t_pre
self.session_manager.log_layer_thermal_metric(layer_idx, t_pre, peak_temp, delta_t)
```

---

## 8. Summary of Next Integration Steps

When physical Seek Thermal hardware is procured and connected:

1. **Install SDK:**
   ```powershell
   .\.conda\python.exe -m pip install seekcamera-python
   ```
2. **Deploy Worker:** Add `calibration_modules/seek_thermal_worker.py` based on Section 5.
3. **Extend Pop-up Window:** Update `CameraViewWindow.py` to add a "Thermal View" tab or dual side-by-side view with false-color colormaps and cursor temperature probing.
4. **Link into Print Session:** Connect exotherm peak metrics into `support_modules/SessionManager.py`.
