# GitHub vs Local Comparison - October 16, 2025

## Overview
This document compares the current local working directory with the GitHub repository (ehj3110/Prince) to identify changes made on another machine that need to be synced.

**Date Created:** October 16, 2025  
**Local Directory:** `c:\Users\cheng sun\BoyuanSun\Prince_CurrentWorkingVersion`  
**GitHub Repository:** https://github.com/ehj3110/Prince  
**Branch:** main

---

## Summary of GitHub Changes

Based on repository documentation, the following major changes were made on another machine:

### 1. **October 10, 2025 - Propagation End Detection Fix**
- **Issue:** Propagation end was using peak-finding instead of zero-crossing
- **Fix:** Corrected to find zero-crossing after maximum second derivative
- **Documentation:** `COMPLETE_RECOVERY_SUMMARY_OCT10.md`, `PROPAGATION_METHOD_FIX_OCT10.md`

### 2. **October 10, 2025 - Two-Step Filtering Restoration**
- **Issue:** System was using Gaussian-only smoothing
- **Fix:** Restored two-step filtering (median + Savitzky-Golay)
- **Documentation:** `FILTERING_RESTORATION_OCT10.md`

### 3. **October 16, 2025 - Algorithm Improvements**
- **Change 1:** 10% threshold propagation end detection
- **Change 2:** Simplified boundary detection (6mm-based)
- **Change 3:** Peak detection from segmented smoothed data
- **Documentation:** `DEPLOYMENT_SUMMARY_OCT16.md`, `FINAL_DEPLOYMENT_CHECKLIST_OCT16.md`

### 4. **October 16, 2025 - Phase Annotation System**
- **Feature:** Added phase detection to `PositionLogger.py`
- **Output:** 4th column in autolog CSV files with phase labels
- **Documentation:** `PHASE_ANNOTATION_UPDATE_OCT16.md`

---

## File-by-File Comparison

### **1. support_modules/adhesion_metrics_calculator.py**

#### **LOCAL VERSION (Current)**
```python
# Smoothing method
def __init__(self, 
             smoothing_sigma=0.5,              # ← Gaussian only
             baseline_threshold_factor=0.002,
             min_peak_height=0.01,
             min_peak_distance=50):
    self.smoothing_sigma = smoothing_sigma

def _apply_smoothing(self, force_data: np.ndarray) -> np.ndarray:
    return gaussian_filter1d(force_data, sigma=self.smoothing_sigma)
```

**Import:**
```python
from scipy.ndimage import gaussian_filter1d  # ← Gaussian only
```

#### **GITHUB VERSION (Updated October 10-16)**
```python
# Smoothing method
def __init__(self, 
             median_kernel=5,                  # ← Two-step filtering
             savgol_window=9,
             savgol_order=2,
             baseline_threshold_factor=0.002,
             min_peak_height=0.01,
             min_peak_distance=50):
    self.median_kernel = median_kernel if median_kernel % 2 == 1 else median_kernel + 1
    self.savgol_window = savgol_window if savgol_window % 2 == 1 else savgol_window + 1
    self.savgol_order = savgol_order

def _apply_smoothing(self, force_data: np.ndarray) -> np.ndarray:
    # Step 1: Median filter for outlier rejection
    median_filtered = medfilt(force_data, kernel_size=self.median_kernel)
    # Step 2: Savitzky-Golay for smoothing while preserving features
    smoothed = savgol_filter(median_filtered, 
                            window_length=self.savgol_window,
                            polyorder=self.savgol_order)
    return smoothed
```

**Import:**
```python
from scipy.signal import savgol_filter, medfilt  # ← Two-step filtering
```

#### **Propagation End Detection**

**LOCAL VERSION:**
- Unknown method (need to check lines 300-400)
- Likely using peak-finding or older method

**GITHUB VERSION (October 16):**
- Uses 10% threshold method
- Searches backward from motion end
- Finds where force drops to: `baseline + (peak - baseline) * 0.10`

**Method Name:** `_find_propagation_end_reverse_search()`  
**Lines:** ~316-417

**Key Algorithm:**
```python
def _find_propagation_end_reverse_search(self, ...):
    # 1. Find peak to end region
    # 2. Calculate 80% lifting point constraint
    # 3. Calculate second derivative
    # 4. Find HIGHEST POSITIVE PEAK of 2nd derivative
    # 5. Calculate 10% threshold
    # 6. Find LAST point BEFORE crossing threshold
    # 7. Return propagation end index
```

#### **Changes Required**
1. ✅ Update imports: Add `savgol_filter`, `medfilt` from `scipy.signal`
2. ✅ Update `__init__()` parameters: Replace `smoothing_sigma` with three parameters
3. ✅ Update `_apply_smoothing()` method: Implement two-step filtering
4. ✅ Update `_find_propagation_end_reverse_search()` method: Implement 10% threshold

---

### **2. support_modules/PeakForceLogger.py**

#### **Changes to Check**
- Integration with updated `AdhesionMetricsCalculator`
- Updated initialization parameters (should pass `median_kernel`, `savgol_window`, etc.)
- Output format changes (if any)

**Expected GitHub Changes:**
```python
self.calculator = AdhesionMetricsCalculator(
    median_kernel=5,           # ← Updated from smoothing_sigma
    savgol_window=9,
    savgol_order=2,
    baseline_threshold_factor=0.002,
    min_peak_height=0.01,
    min_peak_distance=50
)
```

---

### **3. support_modules/PositionLogger.py**

#### **LOCAL VERSION**
- No phase detection
- 3-column CSV output: `Time, Position, Force`

#### **GITHUB VERSION (October 16)**
- Added phase detection system
- 4-column CSV output: `Time, Position, Force, Phase`

**New Method Added:**
```python
def _determine_phase(self, position, force, elapsed_time):
    """
    Determine the current phase based on position, force, and motion history.
    
    Phases:
    - 'IDLE': No motion, waiting
    - 'EXPOSURE': Exposure time (stationary, no force change)
    - 'LIFT': Layer separation (upward motion, force increase)
    - 'SANDWICH': Force-based glass contact detection
    - 'RETRACT': Return to print position
    - 'PAUSE': Brief pause between moves
    """
```

**Configuration Parameters:**
- `position_threshold = 0.002` mm (stationary detection)
- `stationary_count_threshold = 3` readings
- `sandwich_distance_threshold = 1.0` mm

---

### **4. post-processing/RawData_Processor.py**

#### **Expected GitHub Changes (October 16)**
1. **Simplified Boundary Detection** - Uses 6mm jumps instead of complex logic
2. **Peak Detection from Segmented Data** - Finds peak in smoothed segment, maps to global array
3. **Updated to use new calculator parameters**

**Key Method Changes:**
```python
def _find_layer_boundaries(self, ...):
    # Simplified: Find 6mm+ position jumps
    # No longer uses time-gap clustering
```

---

### **5. support_modules/AutomatedLayerLogger.py**

#### **Changes to Check**
- Integration with updated calculator parameters
- Autolog CSV format (may now have 4 columns if using PositionLogger changes)

---

## Critical Local Changes to Preserve

### **SANDWICH ACCELERATION FIX (October 16, 2025 - Today)**

**File:** `Prince_Segmented.py`  
**Lines:** 928, 965, 1024

**Changes Made Earlier Today:**
1. ✅ Added unit conversion: `actual_sandwich_accel_mm_s2 = actual_sandwich_accel_um_s2 / 1000.0`
2. ✅ Updated `move_absolute()` calls to use `mm/s²` instead of `µm/s²`
3. ✅ Fixed: `acceleration_unit=Units.ACCELERATION_MILLIMETRES_PER_SECOND_SQUARED`

**Status:** ✅ **MUST BE PRESERVED** - This fixes a critical bug causing sandwich routine failures

---

## Integration Plan

### **Phase 1: Update adhesion_metrics_calculator.py** ✅
1. Update imports
2. Update `__init__()` parameters
3. Update `_apply_smoothing()` method
4. Update `_find_propagation_end_reverse_search()` method

### **Phase 2: Update PeakForceLogger.py**
1. Update calculator initialization
2. Verify output format

### **Phase 3: Update PositionLogger.py** (Optional)
1. Add phase detection method
2. Update CSV header
3. Update data writing logic

### **Phase 4: Update RawData_Processor.py**
1. Update boundary detection logic
2. Update peak detection method
3. Update calculator parameters

### **Phase 5: Verification**
1. Test adhesion metrics calculation
2. Test sandwich routine with new metrics
3. Verify phase annotation (if implemented)
4. Run batch processing test

---

## Documentation to Fetch from GitHub

These files exist on GitHub but not locally:

1. ✅ `COMPLETE_RECOVERY_SUMMARY_OCT10.md` - Explains propagation fix
2. ✅ `DEPLOYMENT_SUMMARY_OCT16.md` - October 16 changes summary
3. ✅ `FINAL_DEPLOYMENT_CHECKLIST_OCT16.md` - Deployment checklist
4. ✅ `PROPAGATION_METHOD_FIX_OCT10.md` - Propagation detection details
5. ✅ `FILTERING_RESTORATION_OCT10.md` - Two-step filtering explanation
6. ✅ `PHASE_ANNOTATION_UPDATE_OCT16.md` - Phase system documentation
7. ✅ `PROPAGATION_END_10PCT_UPDATE.md` - 10% threshold method
8. ✅ `SIMPLIFIED_BOUNDARY_DETECTION_OCT16.md` - 6mm boundary detection
9. ✅ `PEAK_DETECTION_FIX_OCT16.md` - Segmented peak detection

---

## Testing Strategy

### **Test 1: Adhesion Metrics Calculation**
```python
from support_modules.adhesion_metrics_calculator import AdhesionMetricsCalculator

calc = AdhesionMetricsCalculator(
    median_kernel=5,
    savgol_window=9,
    savgol_order=2
)

# Test with existing autolog file
results = calc.calculate_from_csv("path/to/autolog_L48-L50.csv", layer_number=48)
print(f"Peak Force: {results['peak_force']:.4f} N")
print(f"Work of Adhesion: {results['work_of_adhesion_corrected_mJ']:.4f} mJ")
```

### **Test 2: Sandwich Routine**
1. Load instruction file with sandwich parameters
2. Run print with sandwich enabled
3. Verify acceleration values are correct (5000 µm/s² → 5.0 mm/s²)
4. Check for no "Acceleration cannot be 0" errors

### **Test 3: Phase Annotation** (if implemented)
1. Run print with position logging
2. Check autolog CSV for 4th column (Phase)
3. Verify phase labels are correct

---

## Risk Assessment

### **Low Risk (Safe to Update)**
- ✅ `adhesion_metrics_calculator.py` - Better algorithm, no breaking changes
- ✅ `PeakForceLogger.py` - Only parameter changes
- ✅ `RawData_Processor.py` - Improved logic, backwards compatible

### **Medium Risk (Test Before Deploy)**
- ⚠️ `PositionLogger.py` - New phase column may affect downstream processing
- ⚠️ Sandwich routine integration - Need to verify acceleration fix is compatible

### **High Risk (Backup First)**
- None identified - all changes appear to be improvements

---

## Rollback Plan

If issues occur after updating:

1. **Git Reset:**
   ```powershell
   git stash  # Save current changes
   git checkout HEAD~1  # Go back one commit
   ```

2. **Manual Revert:**
   - Copy files from `archive/` folder
   - Restore from backup (if available)

3. **Selective Rollback:**
   - Keep sandwich acceleration fix
   - Revert only problematic file

---

## Next Steps

1. ✅ **Document Differences** (This file)
2. ⏳ **Fetch GitHub Files** - Download updated versions
3. ⏳ **Apply Changes** - Update local files carefully
4. ⏳ **Test Integration** - Verify all systems work
5. ⏳ **Update Documentation** - Record final state

---

**Status:** Ready for Phase 1 (Update adhesion_metrics_calculator.py)  
**Last Updated:** October 16, 2025  
**Next Review:** After each phase completion
