# DETAILED FILE CATEGORIZATION LIST
**Date**: September 21, 2025  
**Workspace**: Prince_Segmented_20250915  
**Purpose**: Exact file-by-file categorization for cleanup decisions

---

## 🖨️ **PRINTER OPERATION ESSENTIALS** (14 files)
*Files needed for normal 3D printer operation and live data collection*

### Main Directory (1 file):
- `Prince_Segmented.py`

### support_modules/ (13 files):
- `AutoHomeRoutine.py`
- `AutomatedLayerLogger.py`
- `dlp_phidget_coordinator.py`
- `ForceGaugeManager.py`
- `libs.py`
- `Libs_Evan.py`
- `PeakForceLogger.py`
- `PositionLogger.py`
- `prints_layergenerator.py`
- `pycrafter9000.py`
- `SensorDataWindow.py`
- `USBCoordinator.py`
- `enhanced_adhesion_metrics.py`

### ui_components/ (1 file):
- `automated_logging_frame.py`

---

## 📊 **CURRENT BATCH PROCESSING SYSTEM** (8 files)
*Files needed for post-print adhesion analysis (our new hybrid system)*

### Main Directory (6 files):
- `hybrid_adhesion_plotter.py` ⭐ **PRIMARY SYSTEM**
- `adhesion_metrics_calculator.py` ⭐ **PRIMARY SYSTEM**
- `WORK_OF_ADHESION_METRICS_DEFINITIONS.md`
- `batch_process_printing_data.py`
- `autolog_L48-L50.csv` (validated test data)
- `autolog_L198-L200.csv` (additional test data)

### support_modules/ (1 file):
- `two_step_baseline_analyzer.py`

### Test Data (1 file):
- `test_two_step_integration.csv`

---

## 🗑️ **REDUNDANT/SUPERSEDED FILES** (13 files)
*Files replaced by hybrid system or no longer needed - SAFE TO DELETE*

### Main Directory (13 files):
- `adhesion_metrics_plotter.py` ❌ *Replaced by hybrid_adhesion_plotter.py*
- `final_layer_visualization.py` ❌ *Functionality integrated into hybrid system*
- `analyze_single_file.py` ❌ *Replaced by hybrid system*
- `test_calculator_and_plotter.py` ❌ *Old integration test*
- `comprehensive_diagnostic.py` ❌ *Debug tool no longer needed*
- `debug_position.py` ❌ *Debug tool completed*
- `test_columns.py` ❌ *One-time validation*
- `test_L48_L50.py` ❌ *Replaced by hybrid testing*
- `test_propagation_end.py` ❌ *Functionality integrated*
- `test_shaded_plot.py` ❌ *Functionality integrated*
- `test_two_step_integration.py` ❌ *Integration completed*
- `troubleshoot_original_method.py` ❌ *Troubleshooting completed*
- `troubleshoot_single_file.py` ❌ *Issues resolved*

---

## 📈 **PLOTS & GRAPHS - ARCHIVE** (12 files)
*Generated visualization files - can be regenerated, safe to archive*

### Main Directory (12 files):
- `test_display.png` 📊 *Display test output*
- `test_plot.png` 📊 *Simple test plot*
- `test_shaded_regions_L148.png` 📊 *Development test*
- `diagnostic_L198-L200_derivatives_SMOOTHED_CORRECTED.png` 📊 *Development diagnostic*
- `diagnostic_L48-L50_derivatives_SMOOTHED_CORRECTED.png` 📊 *Development diagnostic*
- `final_L198-L200_peeling_analysis_SMOOTHED.png` 📊 *Old analysis method*
- `final_L48-L50_peeling_analysis_SMOOTHED.png` 📊 *Old analysis method*
- `L298-L300_analysis.png` 📊 *Old analysis*
- `L298-L300_DERIVATIVE_ANALYSIS.png` 📊 *Old analysis*
- `L298-L300_FINAL_ANALYSIS.png` 📊 *Old analysis*
- `L298-L300_FINAL_LAYER_VISUALIZATION.png` 📊 *Old analysis*
- `L48_L50_corrected_analysis.png` 📊 *Old analysis*
- `position_analysis.png` 📊 *Development diagnostic*
- `troubleshoot_L298-L300_analysis_ORIGINAL_METHOD.png` 📊 *Troubleshooting*
- `troubleshoot_L298-L300_derivatives_ORIGINAL_METHOD.png` 📊 *Troubleshooting*
- `troubleshoot_L298-L300_method_comparison.png` 📊 *Troubleshooting*

---

## 📈 **PLOTS & GRAPHS - KEEP** (1 file)
*Current validation plots - keep for reference*

### Main Directory (1 file):
- `hybrid_L48_L50_test.png` ✅ *Current system validation*

---

## 📚 **DOCUMENTATION - KEEP** (4 files)
*Current project documentation and progress tracking*

### Main Directory (4 files):
- `HYBRID_SYSTEM_SUCCESS_REPORT.md` ✅ *Complete project report*
- `HYBRID_SYSTEM_BACKUP_MANIFEST.md` ✅ *Backup documentation*
- `PROJECT_UPDATE_HYBRID_SYSTEM.md` ✅ *System update guide*
- `FILE_ORGANIZATION_ANALYSIS.md` ✅ *This analysis document*

---

## 📚 **DOCUMENTATION - ARCHIVE** (5 files)
*Legacy documentation - can be archived*

### Main Directory (5 files):
- `ATTRIBUTEERROR_FIX_20250917.md` 📄 *Fixed issue documentation*
- `AUTOMATED_LOGGING_FIX_20250917.md` 📄 *Fixed issue documentation*
- `BACKUP_SUMMARY_20250917.md` 📄 *Old backup summary*
- `INTEGRATION_PLAN_2STEP_BASELINE.md` 📄 *Completed integration plan*
- `INTEGRATION_SUMMARY.md` 📄 *Old integration summary*

---

## 🧪 **CURRENT TESTING FILES** (2 files)
*Files for ongoing system testing and validation - KEEP*

### Main Directory (2 files):
- `test_hybrid_plotter.py` ✅ *Current system testing*
- `test_plot_visibility.py` ✅ *Display testing utility*

---

## ❓ **UNCERTAIN/NEED YOUR DECISION** (4 items)

### Log Files (1 file):
- `batch_output.log` ❓ *May contain useful debug info or can be deleted*

### Backup Folders (2 folders):
- `backup_complete_system_20250921/` ✅ *Today's backup - KEEP*
- `backup_hybrid_system_20250919/` ❓ *Previous backup - Archive or delete?*

### Archive Folder (1 folder):
- `archive_experimental/` ❓ *30+ experimental files - Keep, compress, or delete?*

---

## 🗑️ **ALWAYS SAFE TO DELETE** (Multiple folders)
*Python cache files - regenerate automatically*

### Cache Folders:
- `__pycache__/` (main directory)
- `support_modules/__pycache__/`
- `archive_experimental/__pycache__/`
- Any other `__pycache__/` folders found

---

## 📊 **EXACT COUNT SUMMARY**

| Category | Exact Count | Action |
|----------|-------------|---------|
| **Printer Essentials** | 14 files | ✅ KEEP |
| **Batch Processing** | 8 files | ✅ KEEP |
| **Current Testing** | 2 files | ✅ KEEP |
| **Current Documentation** | 4 files | ✅ KEEP |
| **Current Plots** | 1 file | ✅ KEEP |
| **Redundant Scripts** | 13 files | ❌ DELETE |
| **Old Plots** | 12 files | 📦 ARCHIVE |
| **Legacy Docs** | 5 files | 📦 ARCHIVE |
| **Cache Folders** | Multiple | ❌ DELETE |
| **Need Decision** | 4 items | ❓ YOUR CHOICE |

### **TOTAL ESSENTIAL FILES TO KEEP: 29 files**
### **TOTAL FILES TO CLEAN UP: 30+ files**

---

**Ready for specific cleanup actions based on your decisions!**
