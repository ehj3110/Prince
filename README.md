# Prince Segmented 3D Printer Control Software

## Project Overview

This repository contains the control software for a custom-built resin 3D printer. The printer utilizes a DLP (Digital Light Processing) projector to cure photopolymer resin and a Zaber linear stage for precise Z-axis control.

A key feature of this system is its advanced instrumentation for scientific research. It is equipped with a Phidgets force gauge to measure and record the adhesion and peeling forces between the newly printed layer and the FEP film of the resin vat. The software is designed not just for 3D printing, but as a platform for materials science research and process optimization.

The application provides a graphical user interface (GUI) built with Tkinter that allows for:
- Full manual and automated control of the printing process.
- Real-time monitoring and plotting of sensor data (position and force).
- Sophisticated, automated data logging and in-depth analysis of adhesion metrics.

## Core Components

### Main Application
- **`Prince_Segmented.py`**: The main entry point of the application. It builds and runs the Tkinter GUI, handles user input, and orchestrates the overall printing and data logging workflow.

### Support Modules (`/support_modules`)
- **Hardware Control:**
    - `pycrafter9000.py`: A low-level controller for the Texas Instruments DLP LightCrafter, managing USB communication to project images.
    - `AutoHomeRoutine.py`: Implements an automated homing sequence for the Z-axis by using the force gauge to detect the build plate or resin surface.
    - `ForceGaugeManager.py`: Manages the Phidgets force gauge, handling device connection, calibration, and high-frequency data acquisition in a separate thread.
    - `USBCoordinator.py` & `dlp_phidget_coordinator.py`: Utilities to prevent USB resource conflicts between the DLP projector and the Phidgets force gauge during critical operations.

- **Data Logging & Analysis:**
    - `SensorDataWindow.py`: Powers the secondary "Sensor Data & Logging" window, which provides real-time plotting of force and position.
    - `PositionLogger.py`: A threaded logger that records Z-axis position and force data to a CSV file at a defined sampling rate.
    - `AutomatedLayerLogger.py`: Manages automated logging sessions for specific layer ranges, as defined in a `logging_windows.csv` file.
    - `PeakForceLogger.py`: Analyzes force data for each layer to calculate key adhesion metrics like peak force and work of adhesion.
    - `adhesion_metrics_calculator.py`: The core scientific engine that performs the detailed calculations for adhesion metrics from raw data.
    - `two_step_baseline_analyzer.py`: A refined analysis module that implements a "2-step baseline" method for highly accurate adhesion data analysis.

- **Helper Libraries:**
    - `libs.py` & `Libs_Evan.py`: Contain helper classes and functions, primarily for parsing print instruction files (`.txt`) and generating image sequences.

### How to Run the Application
To run the software, execute the main file from the command line:
```bash
python Prince_Segmented.py
```
Ensure all required libraries (Tkinter, OpenCV, Zaber-Motion, Phidget22, etc.) are installed in your Python environment.

## Project Organization

### Directory Structure
```
Prince_Segmented_20250926/
├── Prince_Segmented.py          # Main printing application
├── batch_processors/            # Batch data processing scripts
│   ├── batch_process_universal.py    # Universal processor (recommended)
│   ├── batch_process_v4_data.py      # Legacy V4 processor
│   ├── batch_process_v5_data.py      # Legacy V5 processor
│   └── README.md                     # Batch processor guide
├── support_modules/             # Core libraries and utilities
│   ├── adhesion_metrics_calculator.py  # Unified adhesion analysis
│   ├── ForceGaugeManager.py           # Force gauge control
│   ├── AutoHomeRoutine.py             # Homing sequences
│   └── ...
├── post-processing/             # Analysis and plotting tools
│   ├── master_plotter.py              # Master comparison plots
│   ├── analysis_plotter.py            # Individual analysis plots
│   ├── hybrid_adhesion_plotter.py     # Hybrid analysis system
│   └── ...
├── ui_components/               # GUI components
└── documentation/               # All documentation and guides
    ├── UNIVERSAL_PROCESSOR_GUIDE.md   # Universal processor guide
    ├── TESTING_GUIDE.md               # Testing and validation
    ├── DEPLOYMENT_GUIDE.md            # Setup instructions
    └── ...
```

### Documentation - Workflow Guides

**New Comprehensive Guides (December 2025):**
- **Pre-Print Setup**: [documentation/PRE_PRINT_SETUP_GUIDE.md](documentation/PRE_PRINT_SETUP_GUIDE.md) - Hardware setup, camera calibration, force gauge, verification checklist
- **Printing Process**: [documentation/PRINTING_PROCESS_GUIDE.md](documentation/PRINTING_PROCESS_GUIDE.md) - Print flow, phases, logging systems, sandwich routine, real-time metrics
- **Post-Processing**: [documentation/POST_PROCESSING_GUIDE.md](documentation/POST_PROCESSING_GUIDE.md) - Batch processing, analysis tools, master plots, statistical analysis

**Additional Resources:**
- **Troubleshooting**: See [TroubleshootingIdeas.md](TroubleshootingIdeas.md)
- **GitHub Setup**: See [GITHUB_SETUP_GUIDE.md](GITHUB_SETUP_GUIDE.md)
- **Deployment**: See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- **Legacy Documentation**: See [archive/legacy_docs/](archive/legacy_docs/) (archived Dec 2025)

## Recent Changes

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
