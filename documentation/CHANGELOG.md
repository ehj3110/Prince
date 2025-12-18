# Changelog - Prince 3D Printer Control Software

## [2025-10-05] - Hybrid Signal Filtering Integration

### 🎯 Signal Processing Enhancement

#### **INTEGRATION STATUS: ✅ COMPLETE**
New hybrid Median-Savitzky-Golay filter chain integrated into adhesion analysis.

---

### Filter Optimization (October 2025)

#### **Hybrid Two-Stage Filter Implementation**
**STATUS:** ✅ Production-Ready

**What Changed:**
- Replaced single Gaussian filter (σ=0.5) with hybrid two-stage filter chain
- Stage 1: Median filter (kernel=5) for outlier/spike rejection
- Stage 2: Savitzky-Golay filter (window=9, order=2) for polynomial smoothing

**Why It Matters:**
- **90.1% improvement in smoothness** (validated on test data)
- Better spike/outlier rejection from non-linear median filter
- Preserves sharp edges better than Gaussian-only approach
- More accurate baseline and peak detection

**Quantitative Optimization:**
- 30+ filter combinations tested via parameter grid search
- Combined Score metric: SSR + λ * Roughness
- Median(k=5) → Savitzky-Golay(w=9, o=2) scored 0.02124 (2nd best)
- Lambda value: 1.0 (balanced fidelity-smoothness tradeoff)

**Technical Implementation:**
```python
# Stage 1: Median filter for spike rejection
median_filtered = median_filter(force_data, size=5)

# Stage 2: Savitzky-Golay for polynomial smoothing  
smoothed = savgol_filter(median_filtered, window_length=9, 
                        polyorder=2, mode='nearest')
```

**Files Updated:**
- `support_modules/adhesion_metrics_calculator.py` - New `_apply_smoothing()` method
- `support_modules/PeakForceLogger.py` - Updated calculator initialization
- Added parameters: `median_kernel`, `savgol_window`, `savgol_order`
- Deprecated: `smoothing_sigma` (kept for backward compatibility)

**Validation:**
- Test file: autolog_L48-L50.csv (2,260 data points)
- Metrics calculated correctly (Peak: 0.26N, WoA: 0.28mJ)
- Smoothness improvement: 90.1% vs old filter
- Comparison plot: `filter_integration_test_results.png`

**Research Documentation:**
- Full methodology: `archive/filtering_experimentation/README.md`
- Test results: `archive/filtering_experimentation/full_results_table.txt`
- Analysis summary: `CLEANUP_AND_FILTERING_SUMMARY.md`

---

## [2025-10-03] - Major Adhesion Analysis System Overhaul

### 🔬 Critical Changes - Adhesion Metrics Calculation

#### **INTEGRATION STATUS: ✅ VERIFIED**
All changes have been integrated into the live printing system and post-processing pipeline.

---

### Core Algorithm Improvements

#### 1. **Time-Based Derivative Analysis** (adhesion_metrics_calculator.py)
**STATUS:** ✅ Production-Ready

**What Changed:**
- Replaced position-based derivatives with time-based derivatives for baseline detection
- Added Gaussian smoothing (σ=0.5) to reduce noise sensitivity
- Implemented baseline intersection verification to prevent false positives

**Why It Matters:**
- Eliminates false baseline detection from random force spikes
- More robust to varying peel speeds and stage acceleration profiles
- Correctly identifies end of crack propagation using physics-based criteria

**Technical Details:**
```python
# Old Method (Position-based - REMOVED):
dx = np.diff(position_data)
dy = np.diff(force_data)
first_derivative = dy / dx  # Sensitive to stage speed variations

# New Method (Time-based - ACTIVE):
dt = np.diff(time_data)
dy = np.diff(smoothed_force)
first_derivative = dy / dt  # Consistent regardless of stage speed
second_derivative = np.diff(first_derivative) / dt[:-1]
```

**Validation:**
- Tested on L111 (previously showed false baseline at ~14s spike)
- Tested on L48-L50, L198-L200 datasets
- All layers now correctly identify baseline

---

#### 2. **Layer Boundary Detection** (RawData_Processor.py)
**STATUS:** ✅ Production-Ready

**What Changed:**
- Replaced position-based layer detection with time-gap clustering
- Uses 8-second threshold to separate distinct peel events
- Creates non-overlapping boundaries for each layer

**Why It Matters:**
- Fixes critical bug where only 1 layer was detected instead of 5 in multi-layer files
- Handles variable layer timing and peel durations automatically
- Prevents data loss from incorrect layer segmentation

**Technical Details:**
```python
# Time-gap clustering algorithm
peak_times = time_data[peaks]
time_diffs = np.diff(peak_times)
gap_threshold = 8.0  # seconds between layers
layer_transitions = np.where(time_diffs > gap_threshold)[0]
```

**Validation:**
- L50-L54: Now correctly detects 5 layers (was 1)
- L65-L69: Now correctly detects 5 layers (was 1)
- L47-L49: Now correctly detects 3 layers (was 1)

---

### Integration Points

#### **Real-Time Analysis (During Printing)**

1. **PeakForceLogger.py** → **adhesion_metrics_calculator.py**
   - Status: ✅ Integrated
   - Used when: Printing with peak force logging enabled
   - Data flow:
     ```
     Prince_Segmented.py (print loop)
       → SensorDataWindow.py (sensor monitoring)
         → PeakForceLogger.py (per-layer analysis)
           → adhesion_metrics_calculator.py (metrics calculation)
     ```
   - Output: Real-time CSV with 13 metrics per layer

2. **Automated Layer Logger** → **PeakForceLogger**
   - Status: ✅ Integrated
   - Used when: Auto-logging enabled for specific layer ranges
   - Configuration: `logging_windows.csv` in print session folder
   - Output: `autolog_L##-L##.csv` files

#### **Post-Print Analysis**

1. **Manual Analysis** → **RawData_Processor.py** → **adhesion_metrics_calculator.py**
   - Status: ✅ Integrated
   - Used when: Analyzing existing CSV files
   - Scripts:
     - `post-processing/RawData_Processor.py` (single file analysis)
     - `post-processing/batch_v17_analysis.py` (folder batch processing)
   - Output: `autolog_metrics.csv` with enhanced metrics

2. **Automated Post-Print Analysis** → **post_print_analyzer.py**
   - Status: ✅ Integrated
   - Used when: Automatically triggered after print completion
   - Called by: `Prince_Segmented.py._trigger_post_print_analysis()`
   - Output: Analysis plots in session folder

---

### New Features

#### 1. **Speed-Dependent Analysis Plots**
**Files Created:**
- `plot_speed_analysis.py` (mean values, 4 metrics)
- `plot_speed_analysis_median.py` (median values, 4 metrics)
- `plot_master_speed_analysis.py` (mean, all conditions combined)
- `plot_master_speed_analysis_median.py` (median, all conditions)
- `plot_master_distance_analysis.py` (median, distance-focused 2 plots)

**Metrics Analyzed:**
- Peak Force vs. Speed
- Work of Adhesion vs. Speed
- Total Peel Distance vs. Speed
- Peak Retraction Force vs. Speed
- Distance to Peak vs. Speed
- Propagation Distance vs. Speed

**Statistical Methods:**
- Mean with standard deviation
- Median (robust to outliers)
- 2nd order polynomial trend lines
- Multi-transparency visualization (individual points 5-10%, averaged 25%)

**Usage:**
```bash
# Individual folder analysis (mean)
python plot_speed_analysis.py "path/to/folder/autolog_metrics.csv"

# Master comparison (median, all test conditions)
python plot_master_speed_analysis_median.py "path/to/V17Tests"

# Distance-focused analysis
python plot_master_distance_analysis.py "path/to/V17Tests"
```

#### 2. **Enhanced CSV Output Format**
**New Columns Added:**
- `Propagation_Start_Time_s` - When crack initiation begins
- `Propagation_End_Time_s` - When crack propagation completes
- `Propagation_Duration_s` - Time spent in active propagation
- `Distance_to_Peak_mm` - Pre-initiation distance (substrate travel before crack starts)
- `Propagation_Distance_mm` - Distance during active crack growth
- `Total_Peel_Distance_mm` - Sum of above two distances

**Old Columns (Still Present):**
- `Layer_Number`
- `Peak_Force_N`
- `Work_of_Adhesion_mJ`
- `Peak_Retraction_Force_N`
- `Peak_Position_mm`

---

### Testing & Validation

#### Test Dataset: V17Tests (9 Conditions, 451 Layers)

**Test Conditions:**
1. 2p5PEO_1mm_Ramped_BPAGDA_0928 (32 layers)
2. 2p5PEO_1mm_Ramped_BPAGDA_Old (108 layers)
3. 2p5PEO_5mm_Constant_BPAGDA (21 layers)
4. 2p5PEO_5mm_RampedFaster_BPAGDA (21 layers)
5. 2p5PEO_5mm_Ramped_BPAGDA (21 layers)
6. Water_1mm_Constant_BPAGDA (108 layers)
7. Water_1mm_Ramped_BPAGDA (98 layers)
8. Water_5mm_RampedFaster_BPAGDA (21 layers)
9. Water_5mm_Ramped_BPAGDA (21 layers)

**Validation Results:**
- ✅ All 451 layers processed successfully
- ✅ Layer boundary detection: 100% accuracy
- ✅ Baseline detection: No false positives
- ✅ Metrics consistency: Mean and median values align
- ✅ Speed analysis: 22 unique speeds detected and analyzed

---

### Configuration Parameters

#### adhesion_metrics_calculator.py
```python
# Current Production Settings
smoothing_sigma = 0.5              # Gaussian smoothing for noise reduction
baseline_threshold_factor = 0.002  # Relative threshold for baseline detection
min_peak_height = 0.01             # Minimum peak force (N)
min_peak_distance = 50             # Minimum distance between peaks (samples)
```

#### RawData_Processor.py
```python
# Layer Detection Settings
gap_threshold = 8.0                # Time gap (seconds) between layers
sampling_rate = 50                 # Hz (20ms per sample)
```

---

### File Changes Summary

#### Modified Files
1. ✅ `support_modules/adhesion_metrics_calculator.py`
   - Updated: `_find_propagation_end_reverse_search()` method
   - Added: Time-based derivative calculations
   - Added: Baseline intersection verification

2. ✅ `support_modules/PeakForceLogger.py`
   - Integration: Now uses `AdhesionMetricsCalculator` by default
   - Parameter: `use_corrected_calculator=True` (default)
   - Output: Enhanced CSV format with 13 metrics

3. ✅ `post-processing/RawData_Processor.py`
   - Updated: `_find_layer_boundaries()` method
   - Changed: Position-based → Time-gap clustering

#### Created Files
1. ✅ `post-processing/plot_speed_analysis.py`
2. ✅ `post-processing/plot_speed_analysis_median.py`
3. ✅ `post-processing/plot_master_speed_analysis.py`
4. ✅ `post-processing/plot_master_speed_analysis_median.py`
5. ✅ `post-processing/plot_master_distance_analysis.py`
6. ✅ `post-processing/batch_v17_analysis.py`
7. ✅ `post-processing/analyze_single_folder.py`
8. ✅ `post-processing/test_baseline_detection.py` (debugging tool)

#### Documentation Files
1. ✅ `CHANGELOG.md` (this file)
2. ✅ `documentation/LAYER_BOUNDARY_DETECTION.md`
3. ✅ `post-processing/BATCH_V17_UPDATE_NOTES.md`
4. ✅ `post-processing/PEO_OLD_TEST_RESULTS.md`

---

### Backward Compatibility

#### ✅ Existing Functionality Preserved
- All existing Prince_Segmented.py functions work unchanged
- Old CSV files can still be processed
- Manual logging and automated logging both use new calculator
- No changes required to user workflow

#### ⚠️ CSV Format Changes
- **Impact:** New CSV files have additional columns
- **Compatibility:** Old analysis scripts may ignore new columns (safe)
- **Recommendation:** Update analysis scripts to leverage new metrics

---

### Deployment Checklist

#### Before Deploying to Production Printer:

1. ✅ **Code Integration Verified**
   - PeakForceLogger uses new calculator
   - RawData_Processor uses time-gap clustering
   - Post-print analysis uses updated modules

2. ✅ **Testing Completed**
   - 451 layers analyzed successfully
   - Layer detection validated
   - Baseline detection validated

3. 🔲 **File Cleanup** (See DEPLOYMENT_NOTES.md)
   - Remove test files
   - Archive old versions
   - Clean __pycache__ directories

4. 🔲 **Documentation Updated**
   - README.md updated
   - CHANGELOG.md completed
   - User guide created

5. 🔲 **Backup Current System**
   - Archive current working directory
   - Document current software versions
   - Save example output files

---

### Known Issues & Limitations

#### None Critical
All known issues from previous versions have been resolved:
- ✅ False baseline detection → FIXED
- ✅ Layer boundary detection → FIXED
- ✅ Inconsistent analysis between real-time and post-processing → FIXED

#### Recommendations for Future Work
1. **Adaptive Smoothing:** Consider speed-dependent smoothing sigma
2. **Multi-Material Support:** Test with different resin formulations
3. **Real-Time Feedback:** Add live baseline detection visualization
4. **Machine Learning:** Explore ML-based baseline detection for edge cases

---

### Support & Contact

**For Technical Issues:**
- Evan Jones: evanjones2026@u.northwestern.edu
- Professor Cheng Sun: c-sun@northwestern.edu

**Documentation:**
- `/documentation/` folder contains detailed technical docs
- `README.md` for general overview
- `STAGE_STALL_PREVENTION.md` for mechanical troubleshooting

---

### Version History

**Version 2025.10.03:**
- Time-based derivative baseline detection
- Time-gap layer clustering
- Speed analysis visualization suite
- Enhanced metrics output (13 columns)

**Version 2025.09.XX (Previous):**
- Initial unified calculator implementation
- Hybrid adhesion analysis system
- Position-based analysis (deprecated)

---

**END OF CHANGELOG**
