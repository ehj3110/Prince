# Prince Segmented 3D Printer Control Software

## Project Overview

This repository contains the control software for a custom-built resin 3D printer. The printer utilizes a DLP (Digital Light Processing) projector to cure photopolymer resin and a Zaber linear stage for precise Z-axis control.

A key feature of this system is its advanced instrumentation for scientific research. It is equipped with a Phidgets force gauge to measure and record the adhesion and peeling forces between the newly printed layer and the FEP film of the resin vat. The software is designed not just for 3D printing, but as a platform for materials science research and process optimization.

The application provides a graphical user interface (GUI) built with Tkinter that allows for:
- Full manual and automated control of the printing process.
- Real-time monitoring and plotting of sensor data (position and force).
- Sophisticated, automated data logging and in-depth analysis of adhesion metrics.

## Core Components

### Main Applications & GUIs
- **`Prince_Modern.py`** *(Current Operator UI)*: Modern PySide6 shell with dark-purple card aesthetic (`#19202A`/`#8870A3`), Inter typography, real-time system log, slice preview with on-demand generation, and satellite tool launchers. Operates through an asynchronous bridge to a withdrawn Unified print engine backend. See [documentation/PRINCE_MODERN_GUI.md](documentation/PRINCE_MODERN_GUI.md). Launch with `.\.conda\python.exe Prince_Modern.py` or `Launch_Prince_Modern.bat`.
- **`Prince_Segmented_Unified.py`** *(Stable Tkinter Baseline)*: Dual-mode Projection Mode Switcher toggling between 60 Hz HDMI Video mode and 30 Hz HDMI Video Pattern LUT mode with adaptive Light/Dark UI theming and thread-safe post-print survey logging. See [documentation/PRINCE_UNIFIED_GUI.md](documentation/PRINCE_UNIFIED_GUI.md).
- **`Prince_Segmented.py`**: Legacy application for standard 60 Hz video projection with inline Camera View and Monitoring Suite hooks.
- **`Prince_Segmented_VideoPattern.py`**: Legacy application for 30 Hz video pattern projection.

### Live Sensor Suite & Monitoring (`/calibration_modules`)
- **`monitoring_dashboard/`**: Independent PySide6 multi-sensor dashboard running in an isolated process (`close_fds=True`). Features live optical machine vision, radiometric thermal imaging, 40 Hz triple load-cell summed force, and Thorlabs PM100A expected UV power line. See [documentation/MONITORING_DASHBOARD_GUIDE.md](documentation/MONITORING_DASHBOARD_GUIDE.md).
- **`CameraViewWindow.py`**: Allied Vision Alvium 1800 U-511m monochrome optical camera viewer via Vimba X (`vmbpy`) with cursor-anchored zoom/pan, crosshair reticle, debounced exposure/gain sliders, and snapshot export.
- **`SeekThermalViewerWindow.py`**: Seek Thermal InspectionCAM (Model IQ-AAA, 320×240, 9 Hz, 4 cm macro) infrared radiometric viewer for in-situ photopolymerization exotherm tracking, spot temperature probing (°C), false-color palettes, and radiometric CSV/NPY export.
- **`thorlabs_pm100a.py` & `power_density_calibration.py`**: Thorlabs PM100A optical power meter driver (NI-VISA/USBTMC at 385 nm) with two-point UV power density calibration and real-time expected power tracking.

### In-Situ Viscosity Monitoring Subsystem (`/support_modules`)
- **`viscosity_analyzer.py`**: Core mathematical engine implementing linearized Stefan squeeze-flow regression ($F^{-1/3}\text{ vs } z$) for simultaneous viscosity $\mu$ and zero-datum $z_0$ extraction, elastohydrodynamic membrane compliance decoupling, and multi-speed power-law rheology solvers.
- **`ViscosityMonitorWindow.py`**: Dedicated dual-plot UI window for real-time squeeze curve plotting, relative solvent evaporation drift tracking ($\Delta \mu\%$), baseline management, and pre-print dry touch checks.
- **`reference_fluids_db.py`**: Temperature-dependent viscosity database for standard reference calibration fluids (PEG 400, Glycerol-Water mixtures, Propylene Glycol).
- **Handover & Theory Docs**: See [documentation/technical/IN_SITU_VISCOSITY_DRIFT_HANDOVER.md](documentation/technical/IN_SITU_VISCOSITY_DRIFT_HANDOVER.md) and [documentation/technical/RESIN_VISCOSITY_SQUEEZE_FLOW_PHYSICS.md](documentation/technical/RESIN_VISCOSITY_SQUEEZE_FLOW_PHYSICS.md).

### Support Modules (`/support_modules`)
- **Hardware Control:**
    - `pycrafter9000.py`: Low-level USB controller for Texas Instruments DLP LightCrafter (DLP9000/DLPC900).
    - `AutoHomeRoutine.py`: Automated homing routine for Zaber Z-axis using load-cell contact detection.
    - `ForceGaugeManager.py`: Phidgets load-cell bridge manager for high-frequency data acquisition.
    - `USBCoordinator.py` & `dlp_phidget_coordinator.py`: USB bus coordinators preventing hardware endpoint contention.

- **Data Logging & Analysis:**
    - `SensorDataWindow.py`: Secondary sensor window with real-time force and position plotting.
    - `PositionLogger.py`: Threaded CSV logger recording stage position and force at high acquisition rates.
    - `AutomatedLayerLogger.py`: Automated logging sessions for target layer intervals.
    - `PeakForceLogger.py`: Layer-by-layer adhesion metrics and peak force calculations.
    - `adhesion_metrics_calculator.py`: Authoritative scientific calculation engine for adhesion metrics.
    - `two_step_baseline_analyzer.py`: Two-step baseline detection module for accurate adhesion analysis.

- **Session Management:**
    - `SessionManager.py`: Centralized session log initialization, print numbering, state persistence, and analysis delegation.

### How to Run the Application

```powershell
# Recommended Modern Operator Interface (PySide6)
.\.conda\python.exe Prince_Modern.py

# Live Multi-Sensor Monitoring Dashboard (Independent Process)
.\.conda\python.exe -m calibration_modules.monitoring_dashboard

# Stable Tkinter Baseline (Unified Dual Projection Modes)
.\.conda\python.exe Prince_Segmented_Unified.py
```

Check syntax and compile test:
```powershell
.\.conda\python.exe -m py_compile Prince_Modern.py
```

Run test suite:
```powershell
.\.conda\python.exe tests/run_all_tests.py
```

## Project Organization

### Directory Structure
```
Prince_CurrentWorkingVersion/
├── Prince_Modern.py                 # Current PySide6 operator UI
├── Launch_Prince_Modern.bat         # One-click Windows launcher
├── prince_modern/                   # Modern UI components, controller, theme, bundled fonts
│   ├── main_window.py               # Main window layout and cards
│   ├── controller.py                # Asynchronous Qt-Tk bridge to print engine
│   ├── theme.py                     # Custom stylesheet palette
│   └── fonts/                       # Bundled Inter fonts (SIL OFL)
├── prince_modern_unified_source.py  # Withdrawn backend print engine for Modern
├── Prince_Segmented_Unified.py      # Tkinter baseline with dual projection modes
├── Prince_Segmented.py              # Legacy 60 Hz video printing application
├── Prince_Segmented_VideoPattern.py # Legacy 30 Hz video pattern application
├── README.md                        # Project overview and reference
├── DOCUMENTATION_INDEX.md           # Master documentation index
├── START_HERE_FOR_AI.md             # Developer & AI assistant handoff guide
├── graphite/                        # Graphite geometry & slicing pipeline
│   └── slicing/                     # Mesh separation, tip tagging, top disconnection
│       └── support_separator.py     # Multi-shell support separator & CLI
├── tests/                           # Comprehensive test suite (57 tests)
│   ├── run_all_tests.py             # Master test suite runner
│   ├── test_support_separator.py    # Support separator & tip tagging unit tests
│   ├── test_experimental_conditions_logging.py # Instruction copy & exp conditions tests
│   ├── test_viscosity_analyzer.py   # Stefan squeeze-flow & rheology unit tests
│   ├── test_camera_viewer_robustness.py # Allied Vision optical viewer tests
│   ├── test_seek_thermal_viewer.py  # Seek Thermal radiometric viewer tests
│   ├── test_ramped_cylinder.py      # Cone slicing and exposure ramping tests
│   ├── test_session_manager.py      # SessionManager unit tests
│   ├── test_adhesion_metrics.py     # AdhesionMetricsCalculator unit tests
│   └── test_peak_force_logger.py    # PeakForceLogger unit tests
├── batch_processors/                # Batch data processing scripts
│   ├── batch_process_universal.py   # Universal processor (recommended)
│   └── ...
├── support_modules/                 # Core libraries, hardware control, and math solvers
│   ├── viscosity_analyzer.py        # Squeeze-flow viscosity engine
│   ├── ViscosityMonitorWindow.py    # Dual-plot real-time viscosity UI
│   ├── reference_fluids_db.py       # Reference fluid calibration models
│   ├── adhesion_metrics_calculator.py # Authoritative adhesion engine
│   ├── ForceGaugeManager.py         # Phidget force gauge acquisition
│   ├── SessionManager.py            # Session management and state persistence
│   ├── pycrafter9000.py             # DLP projector control
│   └── image_modification/          # Image processing and slicing helpers
├── calibration_modules/             # Vision, thermography, radiometry, and monitoring
│   ├── monitoring_dashboard/        # PySide6 multi-sensor dashboard
│   ├── CameraViewWindow.py          # Allied Vision optical viewer
│   ├── SeekThermalViewerWindow.py   # Seek Thermal radiometric viewer
│   ├── thorlabs_pm100a.py           # Thorlabs PM100A power meter driver
│   └── power_density_calibration.py # UV power density calibration
├── data/                            # Calibration curves, print state, and logs
│   ├── uv_power_calibration.json    # 2-point UV power density calibration
│   ├── monitor_print_state.json     # IPC state shared between Prince and Dashboard
│   └── force_gauge_calibration_*.txt# Load-cell calibration data
└── documentation/                   # All technical guides and specifications
```

### Documentation - Key Workflow Guides
- **AI & Developer Handoff**: [START_HERE_FOR_AI.md](START_HERE_FOR_AI.md) - Critical entry points, hardware invariants, and launch commands.
- **Deployment & PC Clone**: [documentation/DEPLOYMENT_GUIDE.md](documentation/DEPLOYMENT_GUIDE.md) - Moving printer software to a new PC without copying `.conda`.
- **Monitoring Dashboard**: [documentation/MONITORING_DASHBOARD_GUIDE.md](documentation/MONITORING_DASHBOARD_GUIDE.md) - Real-time sensors, triple force, UV expected power.
- **Viscosity Handover**: [documentation/technical/IN_SITU_VISCOSITY_DRIFT_HANDOVER.md](documentation/technical/IN_SITU_VISCOSITY_DRIFT_HANDOVER.md) - In-situ relative viscosity and evaporation drift tracking.
- **Pre-Print Setup**: [documentation/PRE_PRINT_SETUP_GUIDE.md](documentation/PRE_PRINT_SETUP_GUIDE.md) - Hardware verification, optical alignment, force tare.
- **Documentation Master Index**: [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md) - Complete index of all guides and specifications.

## Recent Changes

### November 2026 - Graphite Slicing Pipeline, SIMD Vectorization & Instruction Logging

**Graphite Multi-Shell Support Separator (graphite/slicing/support_separator.py):**
- Decouples combined multi-shell STL files containing printed parts and slicer supports into co-registered meshes while preserving world coordinates.
- Supports reference-guided KDTree classification (sub-millimeter precision) and autonomous heuristic classification based on vertical aspect ratio, thickness, and volume.
- Contact tip proximity extraction tagging support tips with reduced grayscale intensity ({\\text{tip}} = 128$) to reduce peel forces and overcuring.
- Pillar clustering in XY with modular top-shell extraction or clean planar cuts.
- CLI interface and full unit test suite (	ests/test_support_separator.py, 12 tests, 100% passing).

**High-Throughput SIMD Image Processing Vectorization:**
- edge_enhancement.py: Converted internal pipeline to single-precision float32 SIMD operations with OpenCV cv2.minMaxLoc(), eliminating large boolean mask allocations during high-layer-count slicing.
- scattering_compensation.py: Vectorized Gaussian boundary dimming with float32 SIMD and linear scale-offset fusion.

**Print Instruction File Persistence Across Print Lifecycle:**
- Guaranteed instruction .txt file copy into session log directories at print start whenever experimental conditions logging is enabled (ExperimentalConditionsWindow.py).
- Automatic candidate discovery from image directories and persistence across session folder renames.
- Unit tested in 	ests/test_experimental_conditions_logging.py.

---

### October 2026 - Prince Modern Control Shell, Sensor Suite & System Monitoring

**Prince Modern PySide6 Interface (`Prince_Modern.py` + `prince_modern/`):**
- Modern operator GUI featuring dark purple card styling (`#19202A`/`#8870A3`), bundled Inter typography, real-time system log, and satellite tool integration.
- Operates via an asynchronous Qt-Tk bridge to a withdrawn Unified print engine backend (`prince_modern_unified_source.py`), ensuring complete hardware and printing reliability while upgrading UX.
- Slice preview with on-demand **Generate visualization** generation, eliminating layout growth bugs.
- One-click launcher: `Launch_Prince_Modern.bat`.

**PySide6 System Monitoring Dashboard (`calibration_modules/monitoring_dashboard/`):**
- Standalone multi-sensor monitoring process launched with `close_fds=True` to prevent DLP HID device lockouts.
- Live 2×2 layout with independent cards: Allied Vision Alvium optical machine vision, Seek Thermal radiometric thermography, Phidget triple-load cell force, Thorlabs PM100A optical power, and slice geometry tracking via `data/monitor_print_state.json`.
- Strict hardware safety: Gray "unavailable" covers when hardware is disconnected (no synthetic data spoofing during production).

**Thorlabs PM100A Optical Power & UV Calibration:**
- NI-VISA SCPI instrument driver (`thorlabs_pm100a.py`) operating at 385 nm with software auto-up-ranging at 75% full scale.
- Two-point UV power density calibration at LED commands 10 and 100 on `Power_255.png` saved to `data/uv_power_calibration.json`.
- Real-time expected power calculation ($P_{\text{exp}} = \text{density} \times \text{area}$) rendered as a dashed reference line on the live power plot.
- Validation scripts: `power_density_calibration.py`, `power_expected_stress_test.py`, and `power_range_sweep.py`.

**Triple Load-Cell Force System:**
- Full support for Phidget 4x Bridge ports 0, 1, and 2 summed at 40 Hz (25 ms interval) when `MODE=TRIPLE` is specified.
- SensorDataWindow-style Calibrate and Tare dialogs with proportional total-force distribution calculation and optional export to `data/`.
- Monospace 3-decimal display with sign stability to eliminate layout jitter.

**Printer-PC Deployment Checklist & AI Assistant Handoff:**
- Comprehensive deployment guide in `documentation/DEPLOYMENT_GUIDE.md` for cloning the repository to a new desktop without copying machine-locked `.conda` or `__pycache__` artifacts.
- New developer and AI assistant guide in `START_HERE_FOR_AI.md` detailing current entry points, hardware invariants, exclusive device ownership, and outdated docs.

---

### September 2026 - In-Situ Resin Viscosity & Solvent Evaporation Drift Monitoring

**Stefan Squeeze-Flow Rheology Engine (`support_modules/viscosity_analyzer.py`):**
- Linearized Stefan regression converting force curves to $F^{-1/3}\text{ vs } z$, extracting the slope $m = (32 / (3\pi D^4 \mu v))^{1/3}$.
- Mathematical datum-shift invariance: Decouples zero-gap position $z_0$ and chassis thermal expansion ($10\text{--}25\ \mu\text{m}$) from fluid viscosity $\mu$.
- Lumped elastohydrodynamic compliance solver separating FEP membrane elasticity from viscosity.
- Multi-speed power-law rheology solver for characterizing shear-thinning resin behaviors.

**Relative Viscosity & Evaporation Drift Tracking:**
- Self-referencing morning baseline system: Computes $\Delta \mu\% = [(m_0/m_k)^3 - 1] \times 100\%$ across printing runs.
- Tracks volatile diluent/solvent evaporation (ethanol, acetone, reactive diluents) throughout multi-hour print sessions without external calibration oils.
- Automated descent sampling hook in `Prince_Segmented.py` before Layer 1 exposure, complete with safety alert thresholds ($>20\%$ warning, $>25\%$ critical).
- Baseline persistence: Automatic same-day baseline storage in `config/daily_viscosity_baseline.json`.

**Dedicated Viscosity Monitor Window (`support_modules/ViscosityMonitorWindow.py`):**
- Tkinter + Matplotlib dual-plot GUI displaying raw hydrodynamic force-position curves alongside linearized Stefan fits ($R^2$, slope, $z_0$).
- Pre-print dry membrane touch checks, automated reference fluid precalibration, and baseline reset controls.

**Reference Fluids Database (`support_modules/reference_fluids_db.py`):**
- Temperature-dependent Arrhenius viscosity models for lab calibration standards: PEG 400, Glycerol-Water mixtures (85%, 90%), and Propylene Glycol.

**Scientific & Technical Handover Documentation:**
- Physics and fluid mechanics: `documentation/technical/RESIN_VISCOSITY_SQUEEZE_FLOW_PHYSICS.md`.
- Mathematical solvers and algorithms: `documentation/technical/VISCOSITY_DATA_ANALYSIS_METHODS.md`.
- Developer and agent handover guide: `documentation/technical/IN_SITU_VISCOSITY_DRIFT_HANDOVER.md`.

---

### September 2026 - Prince Unified GUI & Multi-Spectral Camera Viewers

**Prince Unified Control GUI (`Prince_Segmented_Unified.py`):**
- Unified dual projection mode architecture porting Rush design to Prince.
- Dynamic mode switcher supporting 60 Hz HDMI Video mode and 30 Hz Video Pattern LUT mode with adaptive Light/Dark UI theming.
- Rush-aligned clean visual overhaul: centered unboxed header, dynamic geometry (`1200x680`), clutter removal, and dual sensor panel mutual exclusion.
- Thread-safe post-print survey queue preventing cross-thread Tkinter crashes.

**Allied Vision Alvium 1800 U-511m Machine Vision (`calibration_modules/CameraViewWindow.py`):**
- High-resolution ($2464 \times 2064$) monochrome optical camera preview using Vimba X (`vmbpy`).
- Non-blocking Tkinter popup with cursor-anchored zoom/pan, crosshair alignment reticle, debounced exposure/gain sliders, display contrast/brightness/gamma filters, and raw snapshot capture.
- Thread-isolated worker (`vmb_camera_worker.py`) with auto-reconnection recovery loop and rolling telemetry.

**Seek Thermal InspectionCAM Infrared Thermography (`calibration_modules/SeekThermalViewerWindow.py`):**
- Radiometric thermal imaging ($320 \times 240$, 9 Hz, 4 cm macro focus) using `seekcamera-python` for in-situ photopolymerization exotherm tracking.
- Interactive canvas with dynamic hover spot temperature probe (°C), pinned spot markers, min/max thermal trackers, false-color palettes (Inferno, Turbo, Viridis), and CSV/NPY radiometric data export.
- Graceful synthetic exotherm simulation fallback when physical camera is absent.

---

### August 2026 - Hardware Standardizations & Instruction Logging

- **Standardized Pixel Pitch**: Updated projector pixel pitch to 4.005 µm across all scripts, calculations, and documentation.
- **Unconditional Instruction Logging**: Ensures print instruction TXT file is unconditionally saved whenever any logging mode is active.

---

### June 2026 - Image Modification Utilities Added

**Cone Generator (Image Modification window):**
- Added direct cone stack generation from geometric inputs:
  - initial radius (µm)
  - ending radius (µm)
  - total height (µm)
  - layer height (µm)
- Writes a new output folder with sequential layer images (`1.png` → `N.png`).

**Instruction Ramping (Image Modification window):**
- Added instruction-file ramp helper with user-defined control layers (`layer, exposure`).
- Supports both linear and exponential interpolation between control layers.
- Exposure scheduling behavior:
  - before first control: fixed at first control exposure
  - between controls: interpolated
  - after last control: fixed at last control exposure
- Recomputes per-layer power to keep dosage constant using first control layer anchor:
  - `dose = power_first × exposure_first`
  - `power_i = dose / exposure_i` (clipped to 0-255)
- Produces a new ramped output folder containing copied images and a new tab-delimited instruction file.

### March 2026 - Image Modification GUI Overhaul

**Scattering Compensation (SC) — full rewrite:**
- Fixed the core algorithm: changed from `blurred − original` to `original − blurred` with inverted normalisation, matching the Edge Enhancement signal direction. This produces a correct boundary→dim interior→bright gradient.
- Unified the SC parameter API with Edge Enhancement: replaced the single `strength` parameter with explicit `min_val` / `max_val` intensity controls.

**Falloff parameter added to Edge Enhancement and Scattering Compensation:**
- New `Falloff` field in the GUI for both EE and SC controls the Gaussian kernel size independently of `Blur` (sigma).
- `Falloff = 0` auto-computes as `4×Blur+1` (preserves old default behaviour).
- Setting a smaller Falloff with a large Blur prevents the kernel from spanning across multiple struts in dense lattice geometries, eliminating cross-strut interference artifacts.
- Propagated through `scattering_compensation.py`, `processor.py`, and both `ImageModificationWindow.py` files (local + export).

**Export packaging — `ImageModificationGUI_export/`:**
- Feature Depth Correction removed from the export GUI (experimental, local only).
- "Padding Normalization" section renamed to "Image Padding".
- `DefinitionsWindow.py` added to export `support_modules/` so the Definitions tab appears on the printer computer.
- Standalone `ImageModificationGUI.exe` built with PyInstaller — no Python installation required on the printer computer.
- PIL/Pillow import made lazy (deferred until first image display) to fix a PyInstaller initialisation ordering bug that caused the "Install Pillow" message.
- `build_temp/`, `__pycache__/`, and orphaned `feature_depth.py` removed from export folder.

**DefinitionsWindow updates:**
- Added `Falloff` parameter documentation in both the Edge Enhancement and Scattering Compensation tabs, with worked examples for lattice use cases.

### January 2026 - Code Cleanup & Modularization
- **SessionManager Module**: Extracted session management logic from `Prince_Segmented.py` into new `SessionManager.py` module
  - Handles session log initialization, print numbering, GUI state persistence, post-print analysis
  - Reduced main script by 212 lines (-9.9%)
  - Improved code organization and testability
- **Project Cleanup**: Archived 8 obsolete modules to `archive/obsolete_modules_jan2026/`
  - Removed old backup files, superseded implementations, legacy UI components
  - Organized test scripts into `/tests` directory
  - Cleaned up __pycache__ directories
- **Documentation Updates**: Updated README to reflect new architecture and organization

### December 2025 - Documentation Consolidation
- **Three Comprehensive Guides**: Consolidated 28+ fragmented documentation files into 3 workflow-based guides
  - Pre-print setup (hardware, calibration, verification)
  - Printing process (print loop, logging, sandwich routine, metrics)
  - Post-processing (batch processing, analysis tools, master plots, statistics)
- **Improved Navigation**: Clear workflow-based organization eliminates redundancy
- **Legacy Docs Archived**: All redundant documentation moved to `archive/legacy_docs/` with content preserved

### November 2025 - Universal Batch Processor
- **Universal Processing System**: New `batch_process_universal.py` works with any test version (V4, V5, V6, ...) without code changes
- **Organized Structure**: Moved all documentation to `documentation/` and batch processors to `batch_processors/`
- **Future-Proof**: No need to write new batch_process_vX scripts for each test series

### September 2025 - Unified Analysis Pipeline
- **Unified Analysis Engine**: The `adhesion_metrics_calculator.py` is now the single, authoritative source for all adhesion calculations
- **Upgraded Peak Force Logger**: `PeakForceLogger.py` was completely rewritten to use the new unified calculator
- **Hybrid Adhesion System**: New "Hybrid Adhesion Analysis System" (`hybrid_adhesion_plotter.py`) for streamlined post-print analysis
- **Validation**: System validated against multiple datasets to confirm accuracy
- **Documentation**: Comprehensive documentation in `documentation/` folder
