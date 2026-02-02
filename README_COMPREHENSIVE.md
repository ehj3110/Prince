# Prince: DLP 3D Printer Control & Adhesion Measurement System

## Project Overview

**Prince** is a custom DLP (Digital Light Processing) resin 3D printer control system designed for scientific research on interfacial adhesion and peeling mechanics. The system integrates hardware control, real-time force monitoring, and comprehensive data analysis to study layer-by-layer adhesion forces during the printing process.

### Research Purpose

This system enables quantitative measurement of:
- **Peak adhesion forces** during layer peeling
- **Work of adhesion** (energy dissipation per unit area)
- **Peeling initiation distance** and dynamics
- **Scaling behavior** with contact area
- **Material-specific adhesion characteristics**

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     PRINCE CONTROL SYSTEM                        │
├─────────────────────────────────────────────────────────────────┤
│  Hardware Layer                                                  │
│  ├── DLP Projector (TI LightCrafter 9000)                       │
│  ├── Zaber Linear Stage (Z-axis, 0.1μm resolution)              │
│  ├── Phidgets Force Gauge (1200 Hz acquisition)                 │
│  └── Allied Vision Camera (Tank calibration)                    │
├─────────────────────────────────────────────────────────────────┤
│  Control Software (Prince_Segmented.py)                          │
│  ├── GUI & User Interface                                       │
│  ├── Print Orchestration                                        │
│  ├── Motion Control (2-stage smooth motion)                     │
│  └── Real-time Monitoring                                       │
├─────────────────────────────────────────────────────────────────┤
│  Data Acquisition                                                │
│  ├── Position & Force Logging (Raw CSV)                         │
│  ├── Layer-specific Data (AutoLog CSV)                          │
│  ├── Peak Force Detection                                       │
│  └── Phase Detection & Classification                           │
├─────────────────────────────────────────────────────────────────┤
│  Post-Processing & Analysis                                      │
│  ├── Adhesion Metrics Calculation                               │
│  ├── Visualization & Plotting                                   │
│  ├── Statistical Analysis                                       │
│  └── Batch Processing                                           │
└─────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Main Application (`Prince_Segmented.py`)
The central control interface built with Tkinter. Manages:
- User interface for print control
- Hardware initialization and coordination
- Print orchestration and layer sequencing
- Real-time status monitoring
- Session management and logging

**Key Features:**
- Start/Stop/Pause print control
- Stage positioning controls
- DLP projector settings (power, mode)
- Print file loading (.txt instruction files)
- Sensor panel integration
- Experimental conditions logging
- State save/load functionality

### 2. Support Modules (`support_modules/`)

#### Hardware Control
- **`motion_controller.py`** - Unified motion control with 2-stage symmetric smooth motion profiles
- **`pycrafter9000.py`** - Low-level DLP LightCrafter control via USB
- **`ForceGaugeManager.py`** - Phidgets force gauge management with high-frequency acquisition
- **`AutoHomeRoutine.py`** - Automated Z-axis homing using force feedback
- **`USBCoordinator.py`** & **`dlp_phidget_coordinator.py`** - USB resource conflict management

#### Data Logging & Analysis
- **`SensorDataWindow.py`** - Real-time force/position plotting and logging GUI
- **`PositionLogger.py`** - Threaded CSV data recorder (position, force, time, phase)
- **`AutomatedLayerLogger.py`** - Layer-specific data extraction and organization
- **`PeakForceLogger.py`** - Real-time peak force detection and metrics calculation
- **`adhesion_metrics_calculator.py`** - Comprehensive adhesion analysis engine

#### Routines & Utilities
- **`SandwichRoutines.py`** - Controlled glass contact for platform adhesion
- **`SessionManager.py`** - Session state persistence and logging management
- **`ExperimentalConditionsWindow.py`** - Custom metadata entry for experiments
- **`two_step_baseline_analyzer.py`** - Two-stage baseline detection algorithm
- **`libs.py`** - Print file parsing and instruction generation

#### Image Processing
- **`image_edge_enhancer.py`** - Batch image edge enhancement for improved print quality

### 3. Post-Processing Suite (`post-processing/`)

Complete analysis pipeline for print data:
- **`RawData_Processor.py`** - Layer boundary detection and segmentation
- **`post_print_analyzer.py`** - Automated adhesion analysis
- **`analysis_plotter.py`** - Visualization generation
- **`batch_process_universal.py`** - Batch processing for multiple prints
- Statistical analysis and scaling behavior studies

### 4. Documentation (`documentation/`)

Comprehensive guides and technical documentation:
- **Setup guides** - Hardware setup, software installation, calibration
- **Process guides** - Print workflow, troubleshooting, best practices
- **Technical references** - Architecture, algorithms, data formats
- **Deployment guides** - System deployment and maintenance

## Key Features

### Motion Control System

**2-Stage Symmetric Smooth Motion** (implemented January 2026):

**Smooth Lifting (Layer Peel):**
1. **Stage 1 (Gentle Break):** First 50μm at 100μm/s - controlled separation initiation
2. **Stage 2 (Prescribed Speed):** Remaining distance at user-specified velocity

**Smooth Retraction (Return to Build):**
1. **Stage 1 (Fast Approach):** Most distance at user-specified velocity
2. **Stage 2 (Gentle Landing):** Final 200μm at 100μm/s - controlled touchdown

**Benefits:**
- Reduces peak adhesion forces
- Minimizes print failures
- Improves data consistency
- Symmetric and intuitive control

### Data Acquisition Pipeline

**Three-Tier Logging System:**

1. **Raw Position/Force Data** (`autolog_*.csv`)
   - High-frequency sampling (up to 1200 Hz with decimation)
   - Columns: Time, Position, Force, Phase
   - Complete motion history

2. **Layer-Specific Data** (`autolog_L##-L##.csv`)
   - Extracted segments for individual layers
   - Includes all phases: Exposure, Lift, Retract, Pause, Sandwich
   - Organized by layer number

3. **Adhesion Metrics** (`adhesion_metrics_*.csv`)
   - Peak force, work of adhesion, distances
   - Real-time calculation during print
   - Statistical summaries

### Adhesion Analysis Features

Automated calculation of:
- **Peak Adhesion Force** - Maximum force during peel
- **Work of Adhesion** - Energy dissipation (area under force curve)
- **Peeling Initiation Distance** - Distance from force start to peak
- **Post-Peak Distance** - Distance from peak to baseline
- **Total Adhesion Distance** - Complete peeling displacement
- **Contact Area** - From image dimensions or experimental conditions
- **Normalized Metrics** - Force/area, Work/area

**Analysis Algorithms:**
- Two-step baseline detection
- Derivative-based boundary detection
- Statistical outlier filtering
- Batch processing capabilities

### Print Time Estimation

Calibrated prediction system (updated January 2026):
- Exposure time per layer
- Smooth motion lift/retract times
- Pause and settling times
- **Overhead per layer: 1.8s** (empirically determined)
  - Stage acceleration/deceleration transitions
  - Image loading and display
  - DLP power changes
  - Diagnostics and force readings

**Accuracy:** Predictions match observed print times (±5%)

## Project Organization

### Directory Structure
```
Prince_CurrentWorkingVersion/
├── Prince_Segmented.py                 # Main application
├── README_COMPREHENSIVE.md             # This file
├── README.md                           # Original README
│
├── support_modules/                    # Core libraries
│   ├── README.md                       # Support modules documentation
│   ├── motion_controller.py            # Motion control
│   ├── adhesion_metrics_calculator.py  # Analysis engine
│   ├── SensorDataWindow.py             # Sensor panel GUI
│   ├── ForceGaugeManager.py            # Force gauge control
│   ├── PeakForceLogger.py              # Peak detection
│   ├── PositionLogger.py               # Data logging
│   ├── AutomatedLayerLogger.py         # Layer extraction
│   ├── pycrafter9000.py                # DLP control
│   ├── image_edge_enhancer.py          # Image processing
│   └── [other modules]
│
├── post-processing/                    # Analysis pipeline
│   ├── README.md                       # Post-processing documentation
│   ├── RawData_Processor.py            # Layer detection
│   ├── post_print_analyzer.py          # Adhesion analysis
│   ├── analysis_plotter.py             # Visualization
│   └── [analysis modules]
│
├── ui_components/                      # UI modules
│   ├── README.md                       # UI components documentation
│   └── automated_logging_frame.py      # Logging UI
│
├── documentation/                      # Comprehensive guides
│   ├── README.md                       # Documentation index
│   ├── PRE_PRINT_SETUP_GUIDE.md        # Setup procedures
│   ├── PRINTING_PROCESS_GUIDE.md       # Print workflow
│   ├── DEPLOYMENT_GUIDE.md             # System deployment
│   ├── UNDERGRADUATE_TEAM_GUIDE.md     # Beginner's guide
│   └── technical/                      # Technical references
│
├── archive/                            # Historical files
├── archived_files/                     # Deprecated code
├── PrintingLogs_Backup/                # Example print data
│
└── [test files, utilities, etc.]
```

## Getting Started

### Quick Start (Existing System)

1. **Launch Prince:**
   ```powershell
   cd "c:\Users\cheng sun\BoyuanSun\Prince_CurrentWorkingVersion"
   python Prince_Segmented.py
   ```

2. **Open Sensor Panel:**
   - Click "Open Sensor Panel" button
   - Connect to force gauge
   - Calibrate (zero with no load)

3. **Load Print File:**
   - Click "Browse" under "Directory of Images"
   - Select .txt instruction file
   - Verify layer count and parameters

4. **Start Print:**
   - Set DLP power (LED Current 0-255)
   - Configure motion parameters (speed, overstep, pause)
   - Click "Start Continuous" or "Start Stepped"
   - Monitor real-time force data

### Prerequisites

**Hardware:**
- DLP projector (TI LightCrafter 9000)
- Zaber linear stage (X-LSM series)
- Phidgets force gauge (1200 Hz capable)
- Windows PC with dual monitors

**Software:**
- Python 3.8+
- Required packages: tkinter, opencv-python, numpy, zaber-motion, Phidget22, screeninfo
- Windows PowerShell

**Installation:**
See `documentation/PRE_PRINT_SETUP_GUIDE.md` for detailed setup instructions.

## Workflow Overview

### 1. Pre-Print Setup
- Hardware connections and calibration
- Force gauge zeroing
- Camera calibration (if using)
- Stage homing
- DLP test pattern verification

### 2. Print Execution
- Load instruction file
- Configure parameters
- Enable data logging
- Start print
- Monitor real-time data

### 3. During Print
- Real-time force monitoring
- Phase detection (Exposure, Lift, Retract, etc.)
- Peak force calculation
- Automated data logging

### 4. Post-Processing
- Layer boundary detection
- Adhesion metrics calculation
- Visualization generation
- Statistical analysis
- Batch processing for experiments

## Data Formats

### Raw Data CSV (`autolog_*.csv`)
```csv
Time (s),Position (mm),Force (N),Phase
0.000,10.000,0.015,Exposure
0.001,10.000,0.016,Exposure
...
```

### Layer-Specific CSV (`autolog_L##-L##.csv`)
Same format as raw data, but segmented by layer boundaries.

### Adhesion Metrics CSV (`adhesion_metrics_*.csv`)
```csv
Layer_Number,Peak_Force_N,Work_of_Adhesion_mJ,Peeling_Initiation_Distance_mm,...
1,0.125,0.0234,0.150,...
2,0.132,0.0256,0.148,...
...
```

See `documentation/technical/` for complete data format specifications.

## Recent Updates

### January 2026: Major System Refinements

1. **Motion Control Overhaul**
   - Converted from 3-stage to 2-stage symmetric smooth motion
   - Simplified configuration and improved consistency
   - Updated phase labels throughout system

2. **Print Time Estimation Calibration**
   - Added 1.8s overhead per layer based on empirical data
   - Now accurately predicts print duration
   - Accounts for acceleration, I/O, and communication delays

3. **Post-Processing Fixes**
   - Fixed layer boundary detection for new phase labels
   - Added isolated label detection to prevent false positives
   - Improved robustness of `RawData_Processor.py`

4. **Image Processing Tools**
   - Created `image_edge_enhancer.py` for batch image enhancement
   - Replicates MATLAB edge enhancement algorithm
   - Improves print quality and feature definition

See `CHANGELOG.md` (if exists) or git history for complete version history.

## Troubleshooting

### Common Issues

**Print not starting:**
- Check DLP connection (should show in Device Manager)
- Verify stage is homed
- Ensure force gauge is connected and calibrated

**High/erratic forces:**
- Check stage speed (too fast can cause excessive forces)
- Verify smooth motion is enabled
- Inspect FEP film for damage or contamination

**Data not logging:**
- Ensure Sensor Panel is open before starting print
- Check "Enable Automated Logging" checkbox
- Verify write permissions to log directory

**Plots not generating:**
- Ensure layer data files exist
- Check that `RawData_Processor.py` is using correct phase detection
- Verify Python dependencies are installed

For detailed troubleshooting, see `documentation/PRINTING_PROCESS_GUIDE.md` section on troubleshooting.

## Development Team

**Principal Investigator:**  
Professor Cheng Sun - Northwestern University

**Primary Developers:**
- Boyuan Sun (boyuansun2026@u.northwestern.edu)
- Evan Jones (evanjones2026@u.northwestern.edu)

## Documentation Map

- **`README_COMPREHENSIVE.md`** (this file) - Project overview
- **`support_modules/README.md`** - Support modules documentation
- **`post-processing/README.md`** - Post-processing pipeline guide
- **`ui_components/README.md`** - UI components reference
- **`documentation/README.md`** - Documentation index
- **`documentation/PRE_PRINT_SETUP_GUIDE.md`** - Setup procedures
- **`documentation/PRINTING_PROCESS_GUIDE.md`** - Print workflow and troubleshooting
- **`documentation/DEPLOYMENT_GUIDE.md`** - System deployment
- **`documentation/UNDERGRADUATE_TEAM_GUIDE.md`** - Beginner-friendly guide

## Contributing

When modifying the system:

1. **Document your changes** - Update relevant README files
2. **Test thoroughly** - Verify on actual hardware if possible
3. **Update phase detection** - If changing motion sequences
4. **Maintain backwards compatibility** - For data analysis scripts
5. **Follow naming conventions** - Match existing code style

## License & Citation

This software is developed for research purposes. If you use this system or methodology in your research, please cite:

```
[Citation information to be added - contact Prof. Cheng Sun]
```

## Version Information

**Current Version:** 2.0 (as of January 2026)  
**Python Version:** 3.8+  
**Last Major Update:** January 15, 2026  
**Documentation Updated:** February 2, 2026

---

**For questions, issues, or contributions:**  
Contact: Boyuan Sun (boyuansun2026@u.northwestern.edu) or Evan Jones (evanjones2026@u.northwestern.edu)
