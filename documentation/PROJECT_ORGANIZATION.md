# Project Organization Guide

## Overview

This document describes the organization of the Prince_Segmented project workspace.

## Directory Structure

### Root Directory
**Contains only essential files:**
- `Prince_Segmented.py` - Main printing application
- `README.md` - Project overview
- `.gitignore` - Git configuration
- `force_gauge_calibration_20251106_144013.txt` - Calibration data

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
**Purpose**: Core libraries and utilities used by the main application

**Key Components:**
- `adhesion_metrics_calculator.py` - Unified adhesion analysis engine
- `ForceGaugeManager.py` - Force gauge control and data acquisition
- `AutoHomeRoutine.py` - Automated homing sequences
- `SensorDataWindow.py` - Real-time sensor data plotting
- `PositionLogger.py` - Data logging threads
- `pycrafter9000.py` - DLP projector control
- Hardware coordinators (USB management)
- Helper libraries (file parsing, image generation)

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
- Tkinter UI widgets
- Custom dialogs and windows
- Interface utilities

### `/documentation/` (17 files)
**Purpose**: All project documentation, guides, and status updates

**User Guides:**
- `UNIVERSAL_PROCESSOR_GUIDE.md` ⭐ **Start here for data processing**
- `QUICK_REFERENCE_CARD.md` - Quick reference for printing
- `TESTING_GUIDE.md` - Testing and validation procedures
- `DEPLOYMENT_GUIDE.md` - Setup and installation
- `CHANGELOG.md` - Version history and changes
- `README.md` - Documentation index

**Feature Guides:**
- `PHASE_AWARE_TESTING_GUIDE.md` - Phase-aware detection
- `SANDWICH_QUICK_REFERENCE.md` - Sandwich routine
- `SANDWICH_ROUTINE_GUIDE.md` - Detailed sandwich guide
- `TRIPLE_FORCE_GAUGE_GUIDE.md` - Triple force gauge setup
- `QUICK_CALIBRATION_GUIDE.md` - Calibration procedures

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
python batch_processors\batch_process_universal.py "C:\path\to\test\data"
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
- Update paths to reflect new locations
- Main application still at root: `Prince_Segmented.py`

---

**Last Updated**: November 28, 2025  
**Organization**: Cheng Sun Lab
