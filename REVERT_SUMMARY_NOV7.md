# Decimation Revert and Selective Recovery Summary
**Date**: November 7, 2025  
**Action**: Selective git revert to remove decimation while preserving adhesion improvements

---

## Problem Analysis

### Issue: Timing Mismatch Causing Repeated Force Values
- **Symptom**: Force values repeating 5 consecutive times (~80ms) in CSV files
- **Root Cause**: PositionLogger actual loop time ~16ms (due to Zaber position read + file I/O) vs decimation output every ~8ms
- **Result**: Queue often empty when PositionLogger samples → previous force value repeated
- **Attempted Fixes**:
  - Changed decimation factor from 12 to 8 (didn't help)
  - Set PositionLogger to 8ms rate (loop still ran at 16ms actual)
  - Removed debug logging (minimal improvement)
- **Final Decision**: **ABANDON decimation completely, revert to pre-decimation state**

---

## Git Strategy: Selective Revert

### Target Commit
**e8daea1** - "Merge remote threading/DLP fixes with local Oct 16 adhesion improvements" (Nov 5-6, 2025)
- Contains Oct 16 adhesion improvements (10% threshold, simplified boundary detection)
- Does NOT contain any decimation work
- Safe restoration point

### Command Used
```bash
git checkout e8daea1 -- support_modules/ForceGaugeManager.py
git checkout e8daea1 -- support_modules/SensorDataWindow.py
git checkout e8daea1 -- support_modules/PositionLogger.py
```

---

## Changes Made

### Commit 1: Revert Decimation Work (1017219)
**Files Reverted**:
- `support_modules/ForceGaugeManager.py` - Removed decimation buffer, triple cell mode, bridge gain controls
- `support_modules/SensorDataWindow.py` - Removed bridge gain UI, aggressive plot cleanup

**Removed Features**:
- ❌ Decimation (factor=8, ~120Hz output, 2.83× noise reduction)
- ❌ Triple load cell mode extensions
- ❌ Bridge gain UI controls (dropdown, apply button)
- ❌ Aggressive matplotlib cleanup (5min periodic)
- ❌ MAX_PLOT_POINTS reduction (2000 → restored to 5000)
- ❌ Decimation buffer management and averaging logic

**Restored Features**:
- ✅ Simple voltage ratio callback (no averaging)
- ✅ Single load cell mode (channel 2)
- ✅ Standard plot management (5000 points)
- ✅ Bridge gain fixed at 1×
- ✅ Clean GUI without decimation controls

### Commit 2: Preserve Adhesion Improvements (1bf1c3b)
**Files Committed**:
- `support_modules/adhesion_metrics_calculator.py`
- `support_modules/PeakForceLogger.py`
- `post_print_analyzer.py`
- `post-processing/RawData_Processor.py`
- `post-processing/analysis_plotter.py`
- `Prince_Segmented.py`

**Added Features**:
- ✅ **Phase-Aware Pre-Initiation Detection**
  - Added `lifting_start_idx` parameter to prevent searching before lifting phase
  - PeakForceLogger tracks phase events and motion start index
  - Ensures accurate pre-initiation timing for Sandwich/Pause phases
  
- ✅ **Improved Propagation End Detection**
  - Changed from 2nd derivative to 1st derivative prominent peak method
  - Finds steepest downward slope (most prominent negative peak)
  - Searches forward to where slope returns to 10% of maximum
  - More robust detection of propagation completion

- ✅ **Post-Processing Integration**
  - Prince_Segmented.py triggers post-processing after print completion
  - RawData_Processor.py handles batch CSV analysis
  - analysis_plotter.py generates visualization plots
  - post_print_analyzer.py coordinates automated analysis

### Commit 3: Documentation (e809e7c)
**Added Documentation**:
- `PHASE_AWARE_ADHESION_DESIGN.md` - Architecture and design rationale
- `PHASE_AWARE_IMPLEMENTATION_SUMMARY.md` - Implementation details
- `PHASE_AWARE_TESTING_GUIDE.md` - Testing procedures
- `POST_PROCESSING_IMPROVEMENTS.md` - Post-processing features

**Removed Documentation**:
- `DECIMATION_FIX.md` (obsolete)
- `SAMPLING_RATE_DISPLAY.md` (obsolete)
- `INTEGRATION_SUCCESS_NOV6.md` (obsolete)

---

## Verification Checklist

### Before Testing
- ✅ Git revert executed successfully
- ✅ Decimation code completely removed from ForceGaugeManager.py
- ✅ Adhesion improvements preserved (no decimation dependencies)
- ✅ All commits pushed to GitHub

### Testing Required (Before Using System)
Before running any prints, you should verify:

1. **Force Gauge Connection**
   - [ ] Start Prince application
   - [ ] Force gauge connects without errors
   - [ ] No console errors about decimation or missing methods

2. **Live Readout Test**
   - [ ] Start live readout with standard sampling rate (e.g., 25ms)
   - [ ] Force values in GUI update smoothly
   - [ ] No console errors about queue or timing

3. **CSV Recording Test**
   - [ ] Record short test CSV (10-15 seconds)
   - [ ] Open CSV in Excel/text editor
   - [ ] **CRITICAL**: Verify force values DON'T repeat 5× in a row
   - [ ] Check timing intervals match GUI setting (e.g., 25ms → ~40Hz)

4. **Adhesion Metrics Test**
   - [ ] Run a test print with 1-2 layers
   - [ ] Verify adhesion metrics calculation completes
   - [ ] Check phase-aware pre-initiation works correctly
   - [ ] Verify post-processing generates plots

---

## Expected System Behavior After Revert

### Force Data Acquisition
- **Sampling Rate**: User-controlled via GUI (default 25ms = 40Hz)
- **No Averaging**: Each sample is independent (no decimation buffer)
- **CSV Output**: Each row should have unique force value (no 5× repeats)
- **Timing**: Consistent with GUI setting (±2ms jitter acceptable)

### Calibration
- **Single Load Cell**: Channel 2 only
- **Bridge Gain**: Fixed at 1× (no UI control)
- **Calibration Process**: Standard 2-point (zero, known force)

### Adhesion Metrics
- **Pre-Initiation**: Phase-aware (respects lifting_start_idx boundary)
- **Propagation End**: First derivative prominent peak method
- **Post-Processing**: Automated after print completion

---

## Repository Status

### Commits Pushed to GitHub
1. **1017219** - "Revert decimation work: restore ForceGaugeManager and SensorDataWindow to pre-decimation state"
2. **1bf1c3b** - "Add phase-aware adhesion metrics and post-processing enhancements"
3. **e809e7c** - "Add documentation for phase-aware adhesion and post-processing features"

### Branch Status
- Branch: `main`
- Commits ahead of origin: **0** (all pushed)
- Working directory: **Clean** (no uncommitted changes)

### Files Preserved (Untracked Test Files)
The following test files remain in your workspace but are NOT tracked by git:
- `check_phases.py`, `check_sandwich_phase.py`
- `test_*.py` (various test scripts)
- `test_*.csv` (test data files)
- `test_*.png` (test plots)
- `SPOOFED_TESTING_README.md`, `SPOOF_TEST_RESULTS_NOV7.md`

You can delete these if no longer needed, or add them to `.gitignore` if you want to keep them locally.

---

## What's Different Now?

### Before (With Decimation)
```python
# ForceGaugeManager.py
USE_DECIMATION = True
decimation_factor = 8
decimation_buffer = deque(maxlen=100)

def _onVoltageRatioChange(self, phidget, voltageRatio):
    # Buffer and average 8 samples
    self.decimation_buffer.append(voltageRatio)
    if self.decimation_counter >= 8:
        averaged = sum(buffer) / len(buffer)
        queue.put(averaged)  # Every ~8ms
```

### After (No Decimation)
```python
# ForceGaugeManager.py
# Decimation removed - simple callback

def _onVoltageRatioChange(self, phidget, voltageRatio):
    # Just queue the raw sample
    self.raw_data_queue.put_nowait((timestamp, voltageRatio))
```

### Timing Behavior Change
- **Before**: Decimation output every ~8ms, PositionLogger sampled every ~16ms → **5× repeated values**
- **After**: No decimation, PositionLogger samples at configured rate (e.g., 25ms) → **unique values each sample**

---

## Next Steps

1. **Immediate**: Run the testing checklist above to verify system works without decimation
2. **Short-term**: Monitor force data quality in real prints to ensure noise levels are acceptable
3. **Long-term**: If noise is an issue, consider software-side filtering (moving average, Gaussian) AFTER data collection

---

## Lessons Learned

1. **Hardware Timing Constraints**: PositionLogger's actual rate is limited by I/O operations (Zaber read + file write), not just the configured interval
2. **Queue Mismatch**: When producer (decimation) runs faster than consumer (PositionLogger), queue can be empty at sample time → repeated values
3. **Selective Revert Strategy**: `git checkout <commit> -- <file>` allows surgical file restoration without affecting other work
4. **Phase-Aware Independence**: Adhesion improvements (phase awareness, post-processing) had zero dependencies on decimation → safe to preserve

---

## Contact
For questions about this revert or the preserved features, refer to:
- `PHASE_AWARE_IMPLEMENTATION_SUMMARY.md` - Phase-aware adhesion details
- `POST_PROCESSING_IMPROVEMENTS.md` - Post-processing architecture
- Git commit messages for detailed change descriptions
