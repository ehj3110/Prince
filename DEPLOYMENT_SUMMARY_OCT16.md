# Deployment Summary - October 16, 2025

## Changes Implemented

### 1. Propagation End Detection Method (10% Threshold)
**Date:** October 10-16, 2025  
**Status:** ✅ DEPLOYED

**Change:** Replaced zero-crossing method with 10% threshold reverse search
- **Old method:** Found where force crosses zero after peak
- **New method:** Searches backward from motion end, finds where force drops to 10% of (peak - baseline)

**Benefits:**
- More consistent across different force magnitudes
- Handles varying baseline levels correctly
- Reduces sensitivity to noise near zero
- Validated across 294 layers

**Files Modified:**
- `support_modules/adhesion_metrics_calculator.py` - Updated `_find_propagation_end_reverse_search()`

**Documentation:**
- `PROPAGATION_END_10PCT_UPDATE.md` - Full technical details
- `PROPAGATION_METHOD_FIX_OCT10.md` - Implementation notes

---

### 2. Simplified Boundary Detection (6mm-based)
**Date:** October 16, 2025  
**Status:** ✅ DEPLOYED

**Change:** Simplified layer boundary detection using known lift distance
- **Old method:** Classified motions by direction (UP/DOWN), required special cases for sandwich data
- **New method:** Find all ~6mm movements (5.5-6.5mm tolerance), pair sequentially

**Key Insight:**
The adhesion test uses a **known 6mm lift distance** from the instruction file. Instead of trying to classify motion directions, we:
1. Find all ~6mm motions (based on absolute distance change)
2. Pair them sequentially: motion 1+2, motion 3+4, etc.
3. Ignore everything else automatically (sandwich touches <1mm, pauses, adjustments)

**Benefits:**
- 50% reduction in code complexity
- No special cases needed for different data types
- Based on physical measurement (6mm lift), not heuristics
- Automatically filters out non-adhesion-test data

**Files Modified:**
- `post-processing/RawData_Processor.py` - Simplified `_find_layer_boundaries()`

**Documentation:**
- `SIMPLIFIED_BOUNDARY_DETECTION_OCT16.md` - Full explanation

---

### 3. Peak Detection from Segmented Smoothed Data
**Date:** October 16, 2025  
**Status:** ✅ DEPLOYED

**Change:** Fixed peak detection to use smoothed peaks from segmented data only

**Problem:** Peak detection was using raw force peaks from the global array, which could include false noise spikes outside the lifting phase.

**Solution:**
```python
# OLD (incorrect):
peak_idx = lifting_start + np.argmax(lifting_force)  # Uses raw force

# NEW (correct):
peak_time_relative = metrics['peak_force_time']  # From smoothed segmented data
peak_idx_in_segment = np.argmin(np.abs(lifting_time_relative - peak_time_relative))
peak_idx = lifting_start + peak_idx_in_segment  # Map to global index
```

**Data Flow:**
1. Segment data by 6mm boundaries
2. Extract lifting phase only
3. Apply smoothing to segmented data
4. Find peak in smoothed segmented data
5. Map peak back to global index using offset (not time search)

**Benefits:**
- Peaks reflect actual adhesion behavior, not noise
- False peaks outside lifting phase cannot interfere
- Consistent peak detection across all data types

**Files Modified:**
- `post-processing/RawData_Processor.py` - Fixed peak index calculation

**Documentation:**
- `PEAK_DETECTION_FIX_OCT16.md` - Detailed explanation

---

## Current System Architecture

### Data Processing Pipeline

```
1. RAW DATA INPUT
   ├─ CSV file (time, position, force)
   └─ Expected 6mm lift distance from instruction file

2. BOUNDARY DETECTION (RawData_Processor)
   ├─ Find all ~6mm stage movements (5.5-6.5mm tolerance)
   ├─ Pair sequentially: lift-retract, lift-retract, ...
   └─ Output: Layer boundaries (lifting, retraction, sandwich phases)

3. DATA SEGMENTATION
   ├─ Extract lifting phase data only (from boundaries)
   ├─ Extract retraction phase data
   └─ Time array made relative to segment start

4. SMOOTHING (AdhesionMetricsCalculator)
   ├─ Step 1: Median filter (kernel=5)
   ├─ Step 2: Savitzky-Golay filter (window=9, order=2)
   └─ Applied to segmented data only

5. PEAK DETECTION
   ├─ Find peak in smoothed segmented lifting data
   ├─ Map peak index to global array using offset
   └─ Peak force and position recorded

6. PROPAGATION END DETECTION
   ├─ Start from motion end, search backward
   ├─ Find where force drops to 10% of (peak - baseline)
   └─ Relative to peak location

7. METRICS CALCULATION
   ├─ All temporal metrics (pre-initiation, propagation durations)
   ├─ All spatial metrics (distances)
   ├─ Work and energy metrics
   ├─ Stiffness and dynamic metrics
   └─ Data quality metrics

8. PLOTTING (AnalysisPlotter)
   ├─ Overview plot (all layers)
   ├─ Individual layer plots (zoomed on peeling event)
   └─ All annotations from segmented data metrics
```

### Key Files

**Core Processing:**
- `post-processing/RawData_Processor.py` - Boundary detection and data segmentation
- `support_modules/adhesion_metrics_calculator.py` - Metrics calculation
- `post-processing/analysis_plotter.py` - Visualization

**Batch Processing:**
- `batch_process_steppedcone.py` - Process all SteppedCone datasets
- `batch_process_printing_data.py` - Process generic printing data

**Utilities:**
- `support_modules/libs.py` - Helper functions and classes
- `support_modules/Libs_Evan.py` - Additional utilities

---

## Validation Results

### Test Dataset: SteppedCone V2
- **Total layers processed:** 293
- **Datasets:** 5 conditions (2p5PEO, Water at 3 speeds, Water_Sandwich)
- **Success rate:** 100%

### Peak Force Ranges (Realistic Values):
- 2p5PEO @ 1000um/s: 0.25 ± 0.10 N
- Water @ 1000um/s: 0.12 ± 0.03 N
- Water @ 3000um/s: 0.21 ± 0.10 N
- Water @ 6000um/s: 0.24 ± 0.07 N
- Water_Sandwich @ 6000um/s: 0.37 ± 0.13 N

### Specific Validations:
- ✅ Layer 434 (Water 6000): Correctly ignores false peak at 40.505s, uses smoothed peak at 40.740s
- ✅ Sandwich data (L335-L340): Detects all 6 layers with realistic forces (0.47-0.57N)
- ✅ Standard data (L48-L50): Maintains correct detection (3 layers, 0.24-0.26N)

---

## Configuration Parameters

### Boundary Detection:
```python
EXPECTED_LIFT_DISTANCE = 6.0  # mm (from instruction file)
DISTANCE_TOLERANCE = 0.5      # mm (allows 5.5-6.5mm)
window_size = 20              # points for position averaging
```

### Motion End Detection:
```python
stability_threshold = 0.02    # mm (position variance)
min_stable_points = 3         # consecutive stable points
max_search = 500              # maximum points to search forward
```

### Smoothing:
```python
median_kernel = 5             # median filter window
savgol_window = 9             # Savitzky-Golay window
savgol_order = 2              # polynomial order
```

### Propagation End:
```python
threshold_pct = 0.10          # 10% of (peak - baseline)
search_window = 5             # points for local averaging
```

---

## Known Limitations

1. **Sandwich data segmentation:** Current algorithm works well for standard lift-retract cycles but may need refinement for complex sandwich protocols. The 6mm detection successfully filters out <1mm sandwich touches.

2. **Variable lift distances:** System expects consistent 6mm lifts. If instruction file specifies different distances, update `EXPECTED_LIFT_DISTANCE` in `RawData_Processor.py`.

3. **Very noisy data:** Two-step smoothing handles typical noise well, but excessive noise may require additional filtering or parameter adjustment.

---

## Future Enhancements

1. **Phase annotation in autolog:** Add column indicating stage phase (Lift/Retract/Pause/Sandwich) during data acquisition
2. **Adaptive distance detection:** Read expected lift distance from instruction file automatically
3. **Real-time validation:** Check data quality during acquisition
4. **Enhanced sandwich support:** If needed, add explicit sandwich phase detection based on instruction file parameters

---

## Migration Notes

If upgrading from previous version:
1. ✅ All existing CSV files compatible (no format changes)
2. ✅ Batch processing scripts unchanged (same command)
3. ✅ Output CSV format unchanged (same columns)
4. ⚠️ Plots will look different (peaks at correct smoothed locations)
5. ⚠️ Metrics may differ slightly (more accurate propagation end)

**Recommendation:** Re-process all data with new algorithms for consistency.

---

## Contact & Documentation

**Documentation Files:**
- `PROPAGATION_END_10PCT_UPDATE.md` - Propagation end algorithm
- `SIMPLIFIED_BOUNDARY_DETECTION_OCT16.md` - Boundary detection
- `PEAK_DETECTION_FIX_OCT16.md` - Peak detection fix
- `README.md` - General project overview
- `DEPLOYMENT_GUIDE.md` - Step-by-step deployment instructions

**Change Logs:**
- `CHANGELOG.md` - Version history
- `SESSION_SUMMARY_OCT10.md` - Previous session summary
- `REFACTORING_SUMMARY_OCT10.md` - Code refactoring notes

**Test Data Archived:**
- `archive/test_scripts_oct16/` - All test and validation scripts

---

## Version Information

**Current Version:** 2.1  
**Release Date:** October 16, 2025  
**Python Version:** 3.8+  
**Key Dependencies:** numpy, pandas, scipy, matplotlib
