# Prince 3D Printer System — Documentation Master Index

Welcome to the comprehensive documentation index for the **Prince Resin DLP 3D Printer Control Software** (`Prince_CurrentWorkingVersion`). This index organizes all technical guides, architectural specifications, operator manuals, and scientific references across the codebase.

---

## 🚀 Quick Navigation & Getting Started

| Document | Description | Target Audience |
| :--- | :--- | :--- |
| **[`START_HERE_FOR_AI.md`](START_HERE_FOR_AI.md)** | **Handoff for AI & Developers** — Current GUI entry points, hardware invariants, launch commands, and outdated docs. | Developers, AI Agents |
| **[`README.md`](README.md)** | Project overview, core components, architecture, and recent changes. | Everyone |
| **[`documentation/DEPLOYMENT_GUIDE.md`](documentation/DEPLOYMENT_GUIDE.md)** | **New PC Clone & Setup Guide** — Environment recreation (`.conda`), hardware drivers, SDK installations, and production deployment checklist. | Operators, Developers |
| **[`documentation/PRE_PRINT_SETUP_GUIDE.md`](documentation/PRE_PRINT_SETUP_GUIDE.md)** | Hardware setup, camera focus, optical alignment, force gauge calibration, resin vat prep, and pre-flight checklist. | Operators |
| **[`documentation/QUICK_REFERENCE_CARD.md`](documentation/QUICK_REFERENCE_CARD.md)** | Quick printable cheatsheet for daily printing operations. | Operators |
| **[`documentation/PROJECT_ORGANIZATION.md`](documentation/PROJECT_ORGANIZATION.md)** | Directory tree map and component responsibilities. | Everyone |
| **[`documentation/CHANGELOG.md`](documentation/CHANGELOG.md)** | Complete chronological history of releases and codebase improvements. | Everyone |

---

## 🖥️ Graphical User Interfaces (GUIs)

The Prince platform features multiple GUI interfaces for different operational workflows:

| Document | Application / Module | Description |
| :--- | :--- | :--- |
| **[`documentation/PRINCE_MODERN_GUI.md`](documentation/PRINCE_MODERN_GUI.md)** | `Prince_Modern.py`<br>`prince_modern/` | **Current Operator UI** — PySide6 shell with modern dark purple card styling (`#19202A`/`#8870A3`), Inter typography, live system log, asynchronous bridge to Unified print backend, and satellite launchers. |
| **[`documentation/PRINCE_UNIFIED_GUI.md`](documentation/PRINCE_UNIFIED_GUI.md)** | `Prince_Segmented_Unified.py` | **Tkinter Stable Baseline** — Dual projection mode switcher (60 Hz HDMI Video vs 30 Hz HDMI Video Pattern LUT), Rush-aligned clean UI, dynamic geometry, and thread-safe post-print survey. |
| Legacy Applications | `Prince_Segmented.py`<br>`Prince_Segmented_VideoPattern.py` | Standalone Tkinter applications for legacy video mode and pattern LUT projection mode. |

---

## 🔬 Multi-Spectral Vision & Live Sensor Suite

Real-time monitoring, alignment, thermography, and force acquisition during printing:

| Document | Subsystem / Files | Key Capabilities |
| :--- | :--- | :--- |
| **[`documentation/MONITORING_DASHBOARD_GUIDE.md`](documentation/MONITORING_DASHBOARD_GUIDE.md)** | `calibration_modules/monitoring_dashboard/`<br>`calibration_modules/MonitoringSuiteWindow.py` | **PySide6 System Monitoring Dashboard** — Independent process displaying live optical machine vision, radiometric thermal imaging, 40 Hz triple-load-cell summed force, and Thorlabs PM100A expected UV power line. |
| **[`calibration_modules/CALIBRATION_FOLDER_INDEX.md`](calibration_modules/CALIBRATION_FOLDER_INDEX.md)** | `calibration_modules/` | Comprehensive architecture map and setup guide for calibration, cameras, power meters, and dashboard workers. |
| **[`documentation/CAMERA_VIEWER_POPUP_SPEC.md`](documentation/CAMERA_VIEWER_POPUP_SPEC.md)** | `calibration_modules/CameraViewWindow.py`<br>`vmb_camera_worker.py`<br>`zoom_pan_canvas.py` | **Optical Machine Vision** — Allied Vision Alvium 1800 U-511m monochrome camera via Vimba X (`vmbpy`). Non-blocking popup with cursor-anchored zoom/pan, crosshair reticle, manual exposure/gain, and snapshot capture. |
| **[`documentation/technical/SEEK_THERMAL_INSPECTION_CAMERA_INTEGRATION.md`](documentation/technical/SEEK_THERMAL_INSPECTION_CAMERA_INTEGRATION.md)** | `calibration_modules/SeekThermalViewerWindow.py`<br>`seek_thermal_worker.py`<br>`seek_thermal_canvas.py` | **Infrared Thermography** — Seek Thermal InspectionCAM (Model IQ-AAA, 320×240, 9 Hz, 4 cm macro). Real-time photopolymerization exotherm tracking, hover spot probe (°C), false-color palettes, and radiometric CSV/NPY export. |
| **[`documentation/TRIPLE_FORCE_GAUGE_GUIDE.md`](documentation/TRIPLE_FORCE_GAUGE_GUIDE.md)** | `support_modules/ForceGaugeManager.py`<br>`calibration_modules/monitoring_dashboard/workers.py` | **Triple Load Cell System** — Phidget 4x Bridge ports 0, 1, 2 summed at 40 Hz (25 ms interval). Proportional force calibration and session tare. |
| **[`calibration_modules/thorlabs_pm100a.py`](calibration_modules/thorlabs_pm100a.py)** | `thorlabs_pm100a.py`<br>`power_density_calibration.py` | **Optical Power Meter** — Thorlabs PM100A over NI-VISA/USBTMC at 385 nm. Two-point UV power density calibration and real-time expected power tracking ($P_{\text{exp}} = \text{density} \times \text{area}$). |

---

## 🧪 In-Situ Resin Viscosity & Solvent Evaporation Drift

Hydrodynamic squeeze-flow viscometry for monitoring resin thickening and solvent/diluent evaporation:

| Document | Subsystem / Files | Key Capabilities |
| :--- | :--- | :--- |
| **[`documentation/technical/IN_SITU_VISCOSITY_DRIFT_HANDOVER.md`](documentation/technical/IN_SITU_VISCOSITY_DRIFT_HANDOVER.md)** | Developer Handover Guide | Complete implementation architecture, daily baseline management, pre-print descent scan hook in `Prince_Segmented.py`, and operator alert thresholds. |
| **[`documentation/technical/RESIN_VISCOSITY_SQUEEZE_FLOW_PHYSICS.md`](documentation/technical/RESIN_VISCOSITY_SQUEEZE_FLOW_PHYSICS.md)** | Physics & Fluid Mechanics | Classical Stefan squeeze flow for $\varnothing 12.7\text{ mm}$ aluminum plate, elastohydrodynamic compliance, membrane flex decoupling, and mathematical proof of datum-shift invariance. |
| **[`documentation/technical/VISCOSITY_DATA_ANALYSIS_METHODS.md`](documentation/technical/VISCOSITY_DATA_ANALYSIS_METHODS.md)** | Analysis Algorithms | Linearized regression ($F^{-1/3}\text{ vs } z$), multi-speed power-law rheology solvers, and Arrhenius temperature compensation models. |
| Core Code Modules | `support_modules/viscosity_analyzer.py`<br>`support_modules/ViscosityMonitorWindow.py`<br>`support_modules/reference_fluids_db.py` | Core mathematical engine, dual-plot real-time UI, and certified reference fluids library (PEG 400, Glycerol/Water, Propylene Glycol). |

---

## ⚙️ Printing Mechanics & Adhesion Science

Core physical modeling and stage movement algorithms for DLP stereolithography:

| Document | Topic | Description |
| :--- | :--- | :--- |
| **[`documentation/PRINTING_PROCESS_GUIDE.md`](documentation/PRINTING_PROCESS_GUIDE.md)** | Printing Workflow | Complete layer cycle, stage movement phases, data logging sequences, and error mitigation. |
| **[`documentation/SANDWICH_ROUTINE_GUIDE.md`](documentation/SANDWICH_ROUTINE_GUIDE.md)** | Peeling Routine | Multi-tier sandwich ascent profile designed to minimize peel stress and prevent vat suction delamination. |
| **[`documentation/SANDWICH_SPEED_FLOOR_MODIFICATIONS.md`](documentation/SANDWICH_SPEED_FLOOR_MODIFICATIONS.md)** | Speed Floors | Minimum velocity constraints and smooth deceleration curves for stage motion. |
| **[`documentation/STAGE_STALL_PREVENTION.md`](documentation/STAGE_STALL_PREVENTION.md)** | Motion Control | Zaber linear stage acceleration quantization, microstep tolerances, and stall mitigation. |
| **[`documentation/technical/WORK_OF_ADHESION_METRICS_DEFINITIONS.md`](documentation/technical/WORK_OF_ADHESION_METRICS_DEFINITIONS.md)** | Adhesion Science | Formal mathematical definitions for peak force, work of adhesion, separation point, and baseline detection. |
| **[`documentation/Z_COMPENSATION_CALIBRATION_PROTOCOL.md`](documentation/Z_COMPENSATION_CALIBRATION_PROTOCOL.md)** | Axial Compensation | Calibration protocol for compensating axial overcure and print-through errors. |

---

## 📐 Graphite Geometry & Support Separator Pipeline

Advanced geometry tools for multi-shell mesh separation, support structure classification, and contact tip tagging:

| Document | Subsystem / Files | Description |
| :--- | :--- | :--- |
| **Support Separator** | graphite/slicing/support_separator.py | Multi-shell STL decoupling separating printed parts from supports retaining exact world coordinates. Supports Mode A (reference guided KDTree) and Mode B (autonomous aspect-ratio and volume classification). |
| **Contact Tip Tagging** | graphite/slicing/support_separator.py | Identifies contact tips within sub-millimeter proximity of part surfaces, applying reduced grayscale intensity ({\\text{tip}} = 128$) to reduce peel forces. |
| **Pillar Top Disconnection** | graphite/slicing/support_separator.py | Spatial clustering of support pillars in XY to cleanly disconnect modular heads or make horizontal planar cuts below detected peaks. |
| **Python API & CLI** | SupportedMeshSeparator | Unified Python class and command-line toolchain for automated STL processing pipelines. |

---

## 🖼️ Image Modification & Slicing Pre-Processing

Pre-processing toolchain for mask generation, scattering compensation, and exposure scheduling:

| Document | Subsystem / Files | Description |
| :--- | :--- | :--- |
| **[`documentation/IMAGE_MODIFICATION_MODULE.md`](documentation/IMAGE_MODIFICATION_MODULE.md)** | `support_modules/ImageModificationWindow.py`<br>`image_modification/` | Full guide to SLA image pre-processing including Edge Enhancement, Scattering Compensation, and pixel padding. |
| **Cone Generator** | `image_modification/ramped_cylinder.py` | Parametric layer stack generation for stepped/smooth conical test geometries. |
| **Instruction Ramping** | `image_modification/ramped_cylinder.py` | Automatic exposure and power ramp scheduling between user-defined control layers with dosage preservation. |
| **Standalone Executable** | `ImageModificationGUI_export/` | PyInstaller-compiled standalone GUI (`ImageModificationGUI.exe`) requiring no local Python installation. |
| **Feature Depth Correction** | `image_modification/feature_depth.py` | Physics-based macro overcuring compensation: physical scale normalization ($1 - e^{-\text{depth}/D_{\text{char}}}$), normalized convolution, and dual distance / Poisson pressure solvers. |
| **3D Axial Z Compensation** | `support_modules/z_compensation.py` | 3D voxel energy model ($D_p, E_c, E_0/E_c$) with backward lookahead single-array streaming and downward overhang dimming. |
| **Pipeline Stage Reordering** | `ImageModificationWindow.py` | Interactive listbox for custom stage execution order (`axial`, `edge`, `global`, `depth`, `scatter`) and custom output tagging. |

---

## 📊 Post-Processing, Batch Analytics & Data Pipelines

Tools for processing adhesion force curves, generating summary statistics, and cross-print comparisons:

| Document | Subsystem / Files | Description |
| :--- | :--- | :--- |
| **[`documentation/POST_PROCESSING_GUIDE.md`](documentation/POST_PROCESSING_GUIDE.md)** | Post-Print Analytics | Guide to batch data processing, layer force curve extraction, and master comparison plotting. |
| **[`documentation/UNIVERSAL_PROCESSOR_GUIDE.md`](documentation/UNIVERSAL_PROCESSOR_GUIDE.md)** | `batch_processors/batch_process_universal.py` | Unified processor compatible with all print log formats (V4, V5, V6+) without script modifications. |
| **[`documentation/POST_PROCESSING_FOLDER_INDEX.md`](documentation/POST_PROCESSING_FOLDER_INDEX.md)** | `post-processing/` | Directory map for master plotters, hybrid adhesion analysis, and summary table generators. |

---

## 🧪 Testing, Verification & Quality Assurance

Automated test suites ensuring regression-free hardware control and data integrity:

| Test Suite | File | Coverage |
| :--- | :--- | :--- |
| **Full Suite Runner** | **[`tests/run_all_tests.py`](tests/run_all_tests.py)** | Master runner for all unit and integration tests across subsystems. |
| **Viscosity Rheology** | **[`tests/test_viscosity_analyzer.py`](tests/test_viscosity_analyzer.py)** | Linearized Stefan regression, zero-datum recovery, reference fluid database, and synthetic curve simulation. |
| **Optical Vision** | **[`tests/test_camera_viewer_robustness.py`](tests/test_camera_viewer_robustness.py)** | Allied Vision zoom/pan coordinate math, gamma lookup tables, worker thread lifecycle, and frame streaming. |
| **Thermal Radiometry** | **[`tests/test_seek_thermal_viewer.py`](tests/test_seek_thermal_viewer.py)** | Seek Thermal frame generation, colormap palettes, spot probe mapping, CSV/NPY export, and mock fallback. |
| **Ramped Geometry** | **[`tests/test_ramped_cylinder.py`](tests/test_ramped_cylinder.py)** | Cone slicing, exposure/power ramping interpolation, and instruction file formatting. |
| **Session Management** | **[`tests/test_session_manager.py`](tests/test_session_manager.py)** | Session logger initialization, print numbering, state persistence, and directory path validation. |
| **Adhesion Calculations** | **[`tests/test_adhesion_metrics.py`](tests/test_adhesion_metrics.py)** | Savitzky-Golay and median filtering, second-derivative propagation detection, and work integration. |

---

## 🔒 Critical Hardware Constraints Summary

For quick reference, operators and developers must keep these hardware rules in mind:
1. **Never call DLP `standby()`**: Release the projector using HDMI video mode and `close()`.
2. **Exclusive DLP HID**: Close TI DLPC900REF-GUI before launching any Prince script or power calibration.
3. **Phidget Bridge Single Ownership**: The Monitoring Dashboard and Prince Sensor Panel cannot query the Phidget bridge simultaneously.
4. **Monitoring Dashboard Process Isolation**: Always launch the dashboard as an independent process with `close_fds=True`.
5. **No Faked Sensor Feeds in Production**: Use gray covers for disconnected hardware; never spoof live force or camera feeds in production.
6. **Alvium Exposure Cap**: Keep ExposureAuto disabled and limit manual exposure to 0.5 s ($500{,}000\ \mu\text{s}$).
7. **Process State Bridge**: The dashboard reads layer and print state strictly via `data/monitor_print_state.json`.
