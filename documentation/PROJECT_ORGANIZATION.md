# Project Organization Guide

## Overview

This document describes the organization of the Prince_Segmented project workspace (**Prince_CurrentWorkingVersion**). Use it to find where code, scripts, and documentation live.

## Directory Structure

### Root Directory (`Prince_CurrentWorkingVersion/`)
**Essential files at project root:**
- `Prince_Modern.py` - Current PySide6 printer operator UI (`prince_modern/`, `Launch_Prince_Modern.bat`)
- `Prince_Segmented_Unified.py` - Tk baseline with dual projection modes and identical hardware logic
- `Prince_Segmented.py` - Legacy printing application with Camera View and Monitoring Suite hooks
- `Prince_Segmented_VideoPattern.py` - Legacy 30 Hz pattern projection application
- `README.md` - Project overview and quick start
- `DOCUMENTATION_INDEX.md` - Master documentation index across all subsystems
- `START_HERE_FOR_AI.md` - Handoff guide for AI and incoming developers
- `.gitignore` - Git configuration

### `/prince_modern/`
**Purpose**: Modern PySide6 operator interface package
- `main_window.py` - Main window layout, control cards, stage jog controls, system log, and slice preview
- `controller.py` - Asynchronous Qt-Tk bridge pumping withdrawn Unified print engine
- `theme.py` - Custom dark-purple QSS palette (`#19202A`/`#8870A3`) and font management
- `fonts/` - Bundled Inter fonts (SIL OFL)

### `/batch_processors/` (6 files)
**Purpose**: Batch processing scripts for test data analysis

**Key Files:**
- `batch_process_universal.py` ⭐ **Recommended** - Works with any version (V4, V5, V6, ...)
- `batch_process_v4_data.py` - Legacy V4 processor
- `batch_process_v5_data.py` - Legacy V5 processor
- `batch_process_printing_data.py` - Process raw printing logs
- `batch_process_steppedcone_generalized.py` - Generalized cone processing
- `README.md` - Batch processor documentation

**Quick Start:**
```bash
python batch_processors\batch_process_universal.py "path\to\data"
```

### `/support_modules/` 
**Purpose**: Core libraries, hardware drivers, and mathematical solvers used by the main application

**Key Components:**
- **In-Situ Viscosity Monitoring Subsystem:**
  - `viscosity_analyzer.py` - Squeeze-flow rheology engine: linearized Stefan regression ($F^{-1/3}\text{ vs } z$), zero-datum recovery, elastohydrodynamic membrane compliance, and power-law solvers
  - `ViscosityMonitorWindow.py` - Dedicated dual-plot UI for real-time squeeze-curve monitoring and relative evaporation drift tracking ($\Delta \mu\%$)
  - `reference_fluids_db.py` - Temperature-dependent viscosity models for standard calibration fluids (PEG 400, Glycerol-Water, Propylene Glycol)
- **Adhesion & Force Analysis:**
  - `adhesion_metrics_calculator.py` - Unified adhesion analysis engine
  - `ForceGaugeManager.py` - Force gauge control and high-frequency acquisition
  - `SensorDataWindow.py` - Real-time sensor data plotting
  - `PositionLogger.py` - Data logging threads
  - `PeakForceLogger.py` - Adhesion metrics extraction per layer
- **Hardware Control & Sequencing:**
  - `AutoHomeRoutine.py` - Automated homing sequences
  - `pycrafter9000.py` - Texas Instruments DLP LightCrafter control
  - `USBCoordinator.py` & `dlp_phidget_coordinator.py` - USB endpoint arbitration
  - `SessionManager.py` - Session logging and GUI state persistence
  - Helper libraries (`libs.py`, `Libs_Evan.py`, image generation, file parsing)

### `/post-processing/` (22 files)
**Purpose**: Analysis, plotting, and post-print processing tools

**Key Files:**
- `master_plotter.py` - Master comparison plots
- `analysis_plotter.py` - Individual layer analysis plots
- `RawData_Processor.py` - Raw data processing pipeline
- `hybrid_adhesion_plotter.py` - Hybrid analysis system
- `post_print_analyzer.py` - Post-print analysis utilities
- `generate_summary_table.py` - Summary table generation
- `scaling_analysis_cones_only.py` - Scaling analysis for cones
- `run_scaling_analysis.py` - Scaling analysis runner
- `process_single_v4_folder.py` - Single folder processor
- Analysis configuration and utilities

**Guides:**
- `BATCH_PROCESSING_GUIDE.md` - Technical batch processing details
- `MODULAR_ANALYSIS_README.md` - Modular analysis system
- `QUICK_REFERENCE.md` - Quick reference for analysis tools

### `/ui_components/`
**Purpose**: GUI components for the main application

**Components:**
- `automated_logging_frame.py` - Automated layer logging controls (Sensor Panel)
- Tkinter UI widgets, custom dialogs and windows

### `/calibration_modules/`
**Purpose**: Multi-spectral machine vision, infrared thermography, optical radiometry, and System Monitoring dashboard

**Key Components:**
- **System Monitoring Dashboard (`monitoring_dashboard/`):**
  - PySide6 standalone multi-sensor process (`close_fds=True`)
  - Live feeds: Allied Vision optical, Seek Thermal radiometric, Phidget triple-cell summed force, and Thorlabs PM100A expected UV power line
- **Allied Vision Alvium 1800 U-511m (Optical Machine Vision):**
  - `CameraViewWindow.py` - Live Allied Vision preview (Vimba X / `vmbpy`): pan/zoom, crosshair, exposure/gain, snapshot
  - `vmb_camera_worker.py` - Threaded vmbpy acquisition + auto-reconnection
  - `zoom_pan_canvas.py` - Interactive ROI-first viewport canvas
- **Seek Thermal InspectionCAM (Infrared Thermography):**
  - `SeekThermalViewerWindow.py` - Radiometric thermal viewer for in-situ exotherm tracking
  - `seek_thermal_worker.py` - 9 Hz acquisition thread with synthetic simulation fallback
  - `seek_thermal_canvas.py` - Radiometric canvas with dynamic hover spot probe (°C)
- **Thorlabs PM100A & UV Power Calibration:**
  - `thorlabs_pm100a.py` - NI-VISA SCPI driver at 385 nm
  - `power_density_calibration.py` - 2-point power density calibration saved to `data/uv_power_calibration.json`
  - `print_monitor_state.py` - Shared IPC state between Prince and dashboard
- CLI bring-up tools: `stream_smoke_test_vmbpy.py`, `vmb_worker_harness.py`, `hardware_connection_test_vmbpy.py`
- `README.md` - Calibration setup and usage

### `/tests/`
**Purpose**: Comprehensive unit tests and integration test suites

**Key Files:**
- `run_all_tests.py` - Master unit test runner across all subsystems (42 tests)
- `test_viscosity_analyzer.py` - Squeeze-flow rheology, Stefan regression, and baseline recovery unit tests
- `test_camera_viewer_robustness.py` - Allied Vision zoom/pan math and worker acquisition tests
- `test_seek_thermal_viewer.py` - Seek Thermal radiometric imaging, colormap, and export unit tests
- `test_ramped_cylinder.py` - Cone slicing, exposure ramping, and instruction formatting unit tests
- `test_session_manager.py` - SessionManager unit tests
- `test_adhesion_metrics.py`, `test_peak_force_logger.py` - Adhesion metrics unit tests
- `test_dlp_simple.py`, `test_sandwich_integration.py` - Integration/hardware tests
- `README.md`, `TESTING_GUIDE.md` - Test documentation

### `/documentation/` (guides and references)
**Purpose**: All project documentation, guides, and status updates

**Master Reference:**
- `DOCUMENTATION_INDEX.md` ⭐ **Start here for complete index of all guides**
- `START_HERE_FOR_AI.md` - Critical invariants and developer handoff
- `DEPLOYMENT_GUIDE.md` - Moving the software onto a new PC
- `MONITORING_DASHBOARD_GUIDE.md` - System monitor (cameras, PM100A, triple force calibrate/tare)
- `technical/IN_SITU_VISCOSITY_DRIFT_HANDOVER.md` - Viscosity monitor handover
- `technical/RESIN_VISCOSITY_SQUEEZE_FLOW_PHYSICS.md` - Squeeze flow fluid mechanics
- `technical/VISCOSITY_DATA_ANALYSIS_METHODS.md` - Viscosity data analysis & rheology solvers
- `TRIPLE_FORCE_GAUGE_GUIDE.md` - Triple force gauge setup
- `PRINCE_MODERN_GUI.md` - Prince Modern PySide6 UI guide
- `PRINCE_UNIFIED_GUI.md` - Prince Unified dual projection mode guide

**Technical Guides:**
- `HOW_PROPAGATION_END_IS_MEASURED.md` - Propagation detection
- `STAGE_STALL_PREVENTION.md` - Stage stall handling
- `TroubleshootingIdeas.md` - Common issues and solutions
- `GITHUB_SETUP_GUIDE.md` - Git repository setup
- `UNDERGRADUATE_TEAM_GUIDE.md` - Guide for new team members

**Project Status:**
- `project_status/HYBRID_SYSTEM_SUCCESS_REPORT.md`
- `project_status/PROJECT_UPDATE_HYBRID_SYSTEM.md`
- `project_status/HYBRID_SYSTEM_BACKUP_MANIFEST.md`

**Technical Documentation:**
- `technical/UNIFIED_CALCULATOR_IMPLEMENTATION.md`
- `technical/WORK_OF_ADHESION_METRICS_DEFINITIONS.md`
- `technical/ANALYSIS_RESULTS_COMPARISON.md`
- `technical/POST_PRINT_ANALYSIS_INTEGRATION.md`
- `technical/SANDWICH_ROUTINE.md`
- `LAYER_BOUNDARY_DETECTION.md`

## Common Workflows

### 1. Running a Print Job
```bash
python Prince_Segmented.py
```
See: `documentation/QUICK_REFERENCE_CARD.md`

### 2. Processing Test Data (New)
```bash
# From project root
python batch_processors\batch_process_universal.py "path\to\test\data"
```
See: `documentation/UNIVERSAL_PROCESSOR_GUIDE.md`

### 3. Processing Legacy Data
```bash
# For V4 data
python batch_processors\batch_process_v4_data.py

# For V5 data
python batch_processors\batch_process_v5_data.py
```

### 4. Post-Print Analysis
```bash
python post-processing\hybrid_adhesion_plotter.py
```
See: `post-processing/BATCH_PROCESSING_GUIDE.md`

### 5. Single Folder Analysis
```bash
python post-processing\process_single_v4_folder.py "folder_path"
```

## Finding What You Need

### "I want to print something"
→ `Prince_Segmented.py` + `documentation/QUICK_REFERENCE_CARD.md`

### "I have new test data to process"
→ `batch_processors/batch_process_universal.py` + `documentation/UNIVERSAL_PROCESSOR_GUIDE.md`

### "I need to analyze old data"
→ `batch_processors/` + look for version-specific processor

### "I want to create custom plots"
→ `post-processing/master_plotter.py` or `post-processing/analysis_plotter.py`

### "Something isn't working"
→ `documentation/TroubleshootingIdeas.md` or `documentation/TESTING_GUIDE.md`

### "I'm new to the project"
→ `README.md` + `documentation/UNDERGRADUATE_TEAM_GUIDE.md`

### "I need technical details"
→ `documentation/technical/` folder

### "I want to understand recent changes"
→ `documentation/CHANGELOG.md` + `documentation/project_status/`

## File Naming Conventions

### Batch Processors
- `batch_process_*.py` - Batch processing scripts
- Version-specific: `batch_process_v4_data.py`, `batch_process_v5_data.py`
- Universal: `batch_process_universal.py`

### Documentation
- `*_GUIDE.md` - User guides and tutorials
- `*_REFERENCE*.md` - Quick reference cards
- `CHANGELOG.md` - Version history
- `README.md` - Overview documents

### Post-Processing
- `*_plotter.py` - Plotting utilities
- `*_analyzer.py` - Analysis tools
- `*_processor.py` - Data processors

## Benefits of This Organization

✅ **Clean Root** - Only essential files in root directory  
✅ **Logical Grouping** - Related files together  
✅ **Easy Navigation** - Find what you need quickly  
✅ **Clear Purpose** - Each directory has a specific role  
✅ **Scalable** - Easy to add new features and documentation  
✅ **Maintainable** - Clear structure for updates  

## Migration Notes

**If you have old scripts or notebooks:**
- Update import paths to include folder names:
  ```python
  # Old
  from batch_process_v4_data import *
  
  # New
  from batch_processors.batch_process_v4_data import *
  ```

- Use relative imports or add to path:
  ```python
  import sys
  from pathlib import Path
  sys.path.insert(0, str(Path(__file__).parent / 'batch_processors'))
  ```

**If you have bookmarks or shortcuts:**
- Update paths to reflect new locations (project root: **Prince_CurrentWorkingVersion**)
- Main application still at root: `Prince_Segmented.py`

### Other directories
- **`archive/`** - Obsolete modules (`obsolete_modules_jan2026/`), unused modules, and `legacy_docs/`
- **`PatternMode_Archive/`** - Archived pattern-mode and DLP sequence code (e.g. `Prince_PatternMode.py`)
- **`RED_PotentialUpgradeScript/`** - RED lab force-sensing upgrade scripts and demos (separate from main app)

---

**Last Updated**: February 2026  
**Organization**: Cheng Sun Lab
