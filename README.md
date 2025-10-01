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

## Recent Changes (September 2025)

The project recently underwent a significant refactoring to unify the adhesion analysis pipeline, ensuring consistent and accurate results across all parts of the system.

- **Unified Analysis Engine**: The `adhesion_metrics_calculator.py` is now the single, authoritative source for all adhesion calculations.
- **Upgraded Peak Force Logger**: `PeakForceLogger.py` was completely rewritten to use the new unified calculator, replacing a system where multiple, inconsistent analysis methods were used.
- **Hybrid Adhesion System**: A new "Hybrid Adhesion Analysis System" (`hybrid_adhesion_plotter.py`) was introduced for streamlined, one-command post-print analysis and visualization.
- **Validation**: The new unified system was validated against `autolog_L48-L50.csv` and `autolog_L198-L200.csv` datasets to confirm its accuracy.
- **Documentation**: Markdown files like `UNIFIED_CALCULATOR_IMPLEMENTATION.md` and `PROJECT_UPDATE_HYBRID_SYSTEM.md` were created to document these changes.

This effort resolved inconsistencies in data analysis and has made the system more robust, maintainable, and accurate.
