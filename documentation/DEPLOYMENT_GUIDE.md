# Deployment Guide - Prince 3D Printer System

## 🚀 Transfer to Production Printer Computer

### Pre-Deployment Checklist

#### ✅ System Verification
- [x] All core modules tested and validated (451 layers processed successfully)
- [x] PeakForceLogger integration confirmed
- [x] Post-print analysis pipeline working
- [x] Layer boundary detection verified
- [x] Baseline detection validated

---

## Critical Files for Deployment

### 🔴 ESSENTIAL - Core System Files (MUST COPY)

#### Main Application
```
Prince_Segmented.py                    # Main GUI and print control
```

#### Support Modules Directory (`support_modules/`)
```
adhesion_metrics_calculator.py        # ✅ UPDATED - Core analysis engine
PeakForceLogger.py                     # ✅ UPDATED - Uses new calculator
SensorDataWindow.py                    # Sensor panel GUI and logging
ForceGaugeManager.py                   # Force gauge control
AutomatedLayerLogger.py                # Layer-specific data logging
PositionLogger.py                      # Position/force data recording
AutoHomeRoutine.py                     # Auto-homing sequence
pycrafter9000.py                       # DLP projector control
libs.py                                # Print file parsing
Libs_Evan.py                           # Additional utilities
USBCoordinator.py                      # USB device coordination
dlp_phidget_coordinator.py             # DLP/Phidget coordination
```

#### Post-Processing Directory (`post-processing/`)
```
post_print_analyzer.py                 # Automated post-print analysis
RawData_Processor.py                   # ✅ UPDATED - Layer boundary detection
analysis_plotter.py                    # Plot generation
```

#### Documentation
```
README.md                              # ✅ UPDATED - System overview
CHANGELOG.md                           # ✅ NEW - All recent changes
STAGE_STALL_PREVENTION.md              # Mechanical troubleshooting
```

---

### 🟡 OPTIONAL - Analysis & Visualization Tools

These files are useful for post-print analysis on the development computer but not required on the printer computer:

#### Batch Analysis Scripts (`post-processing/`)
```
batch_v17_analysis.py                  # Batch folder processing
analyze_single_folder.py               # Single folder analysis
plot_speed_analysis.py                 # Speed analysis (mean)
plot_speed_analysis_median.py          # Speed analysis (median)
plot_master_speed_analysis.py          # Master comparison (mean)
plot_master_speed_analysis_median.py   # Master comparison (median)
plot_master_distance_analysis.py       # Distance-focused analysis
```

**Recommendation:** Copy these to a separate analysis folder on a development computer, NOT the printer computer.

---

### 🟢 SAFE TO DELETE - Test and Debug Files

#### Root Directory Test Files
```
test_adhesion_calculator.py            # DELETE - Development testing
test_adhesion_calculator_with_derivatives.py  # DELETE - Development testing
test_peak_force_logger.py              # DELETE - Development testing
test_peakforce_logger.py               # DELETE - Duplicate test file
test_post_print_analysis.py            # DELETE - Development testing
test_sensor_data_window.py             # DELETE - Development testing
test_output.csv                        # DELETE - Test output
test_peak_force_output.csv             # DELETE - Test output
unified_peak_force_test.csv            # DELETE - Test output
```

#### Post-Processing Test Files
```
post-processing/test_baseline_detection.py      # DELETE - Debug tool
post-processing/test_batch_v17.py               # DELETE - Development testing
post-processing/test_enhanced_plotter.py        # DELETE - Development testing
post-processing/verify_new_method.py            # DELETE - Validation script
post-processing/compare_baseline_methods.py     # DELETE - Method comparison
post-processing/debug_derivative_plotter.py     # DELETE - Debug visualization
```

#### Test Output Images (post-processing/)
```
baseline_test_L111.png                 # DELETE - Debug output
layer_boundaries_debug.png             # DELETE - Debug output
analysis_L48_L50_corrected.png         # DELETE - Test output
autolog_L110-L114_analysis.png         # DELETE - Test output
autolog_L330-L334_analysis.png         # DELETE - Test output
autolog_L47-L49_analysis.png           # DELETE - Test output
autolog_L48-L50_analysis.png           # DELETE - Test output
autolog_L50-L54_analysis.png           # DELETE - Test output
autolog_L65-L69_analysis.png           # DELETE - Test output
```

#### Test CSV Files (post-processing/)
```
autolog_L347-L349.csv                  # DELETE - Test data
autolog_L365-L370.csv                  # DELETE - Test data
autolog_L48-L50.csv                    # DELETE - Test data
```

#### Python Cache Directories
```
__pycache__/                           # DELETE - All Python cache folders
post-processing/__pycache__/           # DELETE
support_modules/__pycache__/           # DELETE
```

---

## 📋 Detailed Integration Status

### Real-Time Analysis (During Printing)

#### Flow Diagram:
```
User starts print in Prince_Segmented.py
    ↓
Opens SensorDataWindow (if enabled)
    ↓
For each layer:
    ├── Stage moves to peel position
    ├── ForceGaugeManager records force data
    ├── SensorDataWindow monitors sensors
    └── If PeakForceLogger enabled:
        ├── PeakForceLogger.start_monitoring_for_layer()
        ├── Data collected during peel
        ├── PeakForceLogger.stop_monitoring_and_log_peak()
        └── adhesion_metrics_calculator.calculate_from_arrays()
            └── Writes to CSV: autolog_metrics.csv
    ↓
Print completes
    ↓
_trigger_post_print_analysis() called
    ↓
post_print_analyzer.py generates plots
```

#### ✅ Integration Confirmed:
1. **PeakForceLogger.py** imports and uses `AdhesionMetricsCalculator`
   - Line 14: `from support_modules.adhesion_metrics_calculator import AdhesionMetricsCalculator`
   - Line 26: `use_corrected_calculator=True` (default parameter)
   - Line 34-40: Calculator initialized with production settings

2. **SensorDataWindow.py** creates and manages PeakForceLogger
   - Line 26: `from PeakForceLogger import PeakForceLogger`
   - Line 337: Creates `automated_peak_force_logger` instance
   - Line 347: Calls `start_monitoring_for_layer()` for each layer
   - Line 391: Calls `stop_monitoring_and_log_peak()` after peel

3. **Prince_Segmented.py** triggers post-print analysis
   - Line 941: `self._trigger_post_print_analysis()`
   - Line 1218-1286: Complete post-print analysis method

### Post-Processing Analysis

#### Flow Diagram:
```
User analyzes existing CSV file
    ↓
Runs RawData_Processor.py or batch_v17_analysis.py
    ↓
RawData_Processor loads CSV data
    ↓
_find_layer_boundaries() using time-gap clustering
    ↓
For each detected layer:
    └── adhesion_metrics_calculator.calculate_from_arrays()
    ↓
Outputs autolog_metrics.csv with enhanced metrics
    ↓
Optional: Generate speed analysis plots
```

#### ✅ Integration Confirmed:
1. **RawData_Processor.py** uses updated layer detection
   - Time-gap clustering algorithm (8-second threshold)
   - Non-overlapping layer boundaries
   - Calls `AdhesionMetricsCalculator` for each layer

2. **batch_v17_analysis.py** processes entire test folders
   - Iterates through all subfolders
   - Processes each `autolog_L##-L##.csv` file
   - Generates `autolog_metrics.csv` for each

---

## 🔧 Configuration Settings

### Critical Parameters in adhesion_metrics_calculator.py

```python
# Production Settings (DO NOT CHANGE without testing)
smoothing_sigma = 0.5                  # Gaussian filter strength
baseline_threshold_factor = 0.002      # Baseline detection sensitivity
min_peak_height = 0.01                 # Minimum peak force (N)
min_peak_distance = 50                 # Minimum samples between peaks
```

**When to adjust:**
- Different resin formulations: May need different smoothing
- Different peel speeds: May need different baseline threshold
- Low adhesion materials: May need lower min_peak_height

### Critical Parameters in RawData_Processor.py

```python
# Layer Detection Settings
gap_threshold = 8.0                    # Seconds between layers
sampling_rate = 50                     # Hz (force gauge sample rate)
```

**When to adjust:**
- Faster printing: Reduce gap_threshold to 5-6 seconds
- Slower printing: Increase gap_threshold to 10-12 seconds
- Different force gauge: Update sampling_rate to match

---

## 🧪 Testing the Deployment

### Step 1: Verify File Transfer
```bash
# On printer computer, check all critical files exist
python -c "import support_modules.adhesion_metrics_calculator; print('✅ Calculator found')"
python -c "import support_modules.PeakForceLogger; print('✅ PeakForceLogger found')"
python -c "import support_modules.SensorDataWindow; print('✅ SensorDataWindow found')"
```

### Step 2: Test Print with Logging
1. Open Prince_Segmented.py
2. Load a simple test print (5-10 layers)
3. Open Sensor Panel
4. Enable "Record Peak Force" checkbox
5. Run print
6. Verify CSV file created with correct format:
   - Should have 13 columns (not 7-8 old format)
   - Layer_Number, Peak_Force_N, Work_of_Adhesion_mJ, etc.

### Step 3: Test Post-Print Analysis
1. After print completes, check for auto-generated plots
2. Look in print session folder for analysis plots
3. Verify no error messages in console

### Step 4: Manual Post-Processing Test
```bash
# Navigate to post-processing directory
cd post-processing

# Test on existing CSV file
python RawData_Processor.py "path/to/autolog_L48-L50.csv"

# Check output
# Should create: autolog_metrics.csv with proper layer detection
```

---

## 🐛 Troubleshooting

### Issue: "Module not found" errors
**Solution:**
```python
# Check Python path includes support_modules
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'support_modules'))
```

### Issue: Old CSV format (7-8 columns instead of 13)
**Cause:** PeakForceLogger using old analysis method

**Solution:**
1. Check PeakForceLogger.py line 26: `use_corrected_calculator=True`
2. Verify adhesion_metrics_calculator.py exists in support_modules
3. Delete __pycache__ folders and restart

### Issue: Only 1 layer detected in multi-layer file
**Cause:** Old RawData_Processor.py still in use

**Solution:**
1. Verify RawData_Processor.py has `_find_layer_boundaries()` with time-gap clustering
2. Look for: `gap_threshold = 8.0` in the code
3. If not present, re-copy from development computer

### Issue: False baseline detection (random spikes)
**Cause:** Old adhesion calculator still in use

**Solution:**
1. Check adhesion_metrics_calculator.py for time-based derivatives
2. Look for: `dt = np.diff(time_data)` in `_find_propagation_end_reverse_search()`
3. Verify smoothing is enabled: `smoothing_sigma=0.5`

---

## 📊 Expected Output Format

### Real-Time CSV (During Print)
**Filename:** `autolog_metrics.csv` or `autolog_L##-L##.csv`

**Columns (13 total):**
```
Layer_Number
Peak_Force_N
Work_of_Adhesion_mJ
Initiation_Time_s
Propagation_End_Time_s
Total_Duration_s
Distance_to_Peak_mm
Distance_to_Propagate_mm
Total_Peel_Distance_mm
Peak_Retraction_Force_N
Peak_Position_mm
Propagation_Start_Time_s
Propagation_Duration_s
```

### Post-Print Plots
**Generated automatically in print session folder:**
- Layer-by-layer force vs. time plots
- Annotated with peak detection, baseline detection
- Shaded regions showing peel window

---

## 🔒 Backup Strategy

### Before Deployment
1. **Archive current working system:**
   ```bash
   # On printer computer
   cd "C:\PrinterSoftware"
   # Rename current folder
   ren Prince_Segmented Prince_Segmented_BACKUP_2025-10-03
   ```

2. **Document current versions:**
   - Python version
   - Library versions (Phidget22, zaber-motion, opencv-python, etc.)
   - Working example CSV files

3. **Test rollback procedure:**
   - Verify backup can be restored
   - Ensure all hardware still works with backup

### After Deployment
1. **Keep development computer synced:**
   - Copy all production files back to dev computer
   - Maintain version control
   - Document any field modifications

2. **Regular backups:**
   - Weekly: Copy entire Prince_Segmented folder to external drive
   - After major prints: Save session folder with all CSV/plots
   - Monthly: Archive to cloud storage

---

## 📁 Recommended Folder Structure on Printer Computer

```
C:\PrinterSoftware\
├── Prince_Segmented\              # Main application
│   ├── Prince_Segmented.py
│   ├── README.md
│   ├── CHANGELOG.md
│   ├── support_modules\
│   ├── post-processing\
│   │   ├── post_print_analyzer.py
│   │   ├── RawData_Processor.py
│   │   └── analysis_plotter.py
│   └── documentation\
│
├── PrintingLogs\                  # Active print logs (created by software)
│   └── YYYY-MM-DD\
│       └── Print_##\
│
└── Backups\                       # Manual backups
    └── Prince_Segmented_BACKUP_YYYY-MM-DD\
```

---

## ✅ Final Deployment Checklist

- [ ] Backup current system on printer computer
- [ ] Copy all ESSENTIAL files (see list above)
- [ ] Copy OPTIONAL post-processing files to dev computer
- [ ] Delete all test files from transferred copy
- [ ] Delete all __pycache__ directories
- [ ] Run test print with logging enabled
- [ ] Verify CSV output has 13 columns
- [ ] Verify post-print analysis generates plots
- [ ] Test manual post-processing on old CSV file
- [ ] Document deployment date and version
- [ ] Update README.md with deployment info
- [ ] Save example outputs for reference

---

## 📞 Support

**If you encounter issues during deployment:**

1. **Check this guide first** - Most common issues are documented
2. **Review CHANGELOG.md** - Understand what changed
3. **Check console output** - Python error messages are informative
4. **Contact:**
   - Evan Jones: evanjones2026@u.northwestern.edu
   - Professor Cheng Sun: c-sun@northwestern.edu

---

**Document Version:** 2025-10-03  
**Last Updated:** October 3, 2025  
**Prepared By:** AI Assistant with Evan Jones

---
