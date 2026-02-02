# Obsolete Modules Archive - January 2026

This directory contains modules that have been replaced or are no longer used in the active codebase.

## Archived Files

### Backup Files
- **ForceGaugeManager_SingleCell_Backup.py** - Backup of older single-cell implementation
  - Replaced by: Current `ForceGaugeManager.py`
  - Date Archived: January 6, 2026
  - Reason: Backup file, no active imports found

### Old Versions
- **PeakForceLogger_Old.py** - Previous version of peak force logger
  - Replaced by: Current `PeakForceLogger.py` (unified analysis system)
  - Date Archived: January 6, 2026
  - Reason: Superseded by rewrite using unified adhesion calculator

- **SensorDataWindow_Old.py** - Previous version of sensor data window
  - Replaced by: Current `SensorDataWindow.py`
  - Date Archived: January 6, 2026
  - Reason: Superseded by improved implementation

- **enhanced_adhesion_metrics_Old.py** - Previous adhesion metrics implementation
  - Replaced by: `adhesion_metrics_calculator.py` (unified system)
  - Date Archived: January 6, 2026
  - Reason: Superseded by September 2025 unified analysis pipeline

### Superseded Implementations
- **LinearScaledSandwich.py** - Linear scaled sandwich routine
  - Replaced by: `SandwichRoutines.py` (unified manager)
  - Date Archived: January 6, 2026
  - Reason: Functionality integrated into SandwichRoutineManager

- **derivative_sandwich.py** - Derivative-based sandwich routine
  - Replaced by: `SandwichRoutines.py` (unified manager)
  - Date Archived: January 6, 2026
  - Reason: Functionality integrated into SandwichRoutineManager

- **SandwichRoutine.py** - Original singular sandwich routine
  - Replaced by: `SandwichRoutines.py` (plural, manager-based)
  - Date Archived: January 6, 2026
  - Reason: Superseded by manager-based architecture

### Legacy UI
- **prints_layergenerator.py** - Early UI for layer generation
  - Replaced by: `Prince_Segmented.py` (main application)
  - Date Archived: January 6, 2026
  - Reason: No active imports, superseded by main application

- **Libs_Evan.py** - Helper library (Evan's version)
  - Replaced by: `libs.py` (consolidated version)
  - Date Archived: January 6, 2026
  - Reason: Only dependency was prints_layergenerator.py (also archived)

## Restoration

If you need to restore any of these files, they are preserved in this archive directory. Simply copy them back to `support_modules/` if needed for reference or restoration.

## Archive History

- **January 6, 2026**: Initial archive created during project cleanup
  - Removed 8 obsolete modules from active codebase
  - Organized test scripts into `/tests` directory
  - Added SessionManager.py documentation to README.md
