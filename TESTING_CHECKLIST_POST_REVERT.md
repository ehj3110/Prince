# Testing Checklist - Post Decimation Revert
**Date**: November 7, 2025  
**Purpose**: Verify system works correctly after removing decimation

---

## Quick Start
Run through these tests BEFORE doing any real prints to ensure the revert was successful.

---

## Test 1: Force Gauge Connection (1 minute)
**Goal**: Verify basic connectivity without decimation code

### Steps:
1. Launch Prince application
2. Observe console output during startup
3. Force gauge should connect to Channel 2

### Expected Results:
- ✅ "Phidget connected successfully (ForceGaugeManager)!"
- ✅ No errors about missing decimation methods
- ✅ No errors about bridge gain or triple cell mode

### Red Flags:
- ❌ AttributeError about decimation_factor, decimation_buffer, etc.
- ❌ Connection fails completely
- ❌ Errors about missing set_decimation_factor() or similar

---

## Test 2: Live Readout (2 minutes)
**Goal**: Verify force readings update smoothly without decimation

### Steps:
1. Open Sensor Data Window
2. Set sampling rate to **25ms** (40Hz) using the spinbox
3. Click "Start Recording Work" (manual mode)
4. Apply small force to load cell (e.g., press with finger)
5. Watch force values in GUI for 30 seconds
6. Click "Stop Recording"

### Expected Results:
- ✅ Force values update smoothly in GUI
- ✅ Values respond immediately to applied force
- ✅ No console errors about queue empty or timing issues
- ✅ Plot shows smooth force curve

### Red Flags:
- ❌ Force values freeze or update very slowly
- ❌ Console errors about queue.Empty or decimation
- ❌ Force readings seem delayed or unresponsive

---

## Test 3: CSV Recording - NO REPEATS (5 minutes)
**Goal**: CRITICAL - Verify force values don't repeat 5× in CSV

### Steps:
1. Start live readout with 25ms sampling rate
2. Record for 15-20 seconds with varied force (press and release)
3. Stop recording
4. Open the CSV file in Excel or text editor
5. **Examine the Force (N) column carefully**

### Expected Results:
- ✅ Each row has a **unique or nearly-unique** force value
- ✅ Timing intervals are consistent (~25ms = ~40Hz)
- ✅ Force values change smoothly (no sudden jumps except when you change force)
- ✅ No pattern of "same value repeated 5 times in a row"

### Example of GOOD data (no repeats):
```
Time(s), Position(mm), Force(N)
0.000, 10.000, 0.0012
0.025, 10.000, 0.0015  ← Different from previous
0.050, 10.000, 0.0018  ← Different from previous
0.075, 10.000, 0.0021  ← Different from previous
0.100, 10.000, 0.0019  ← Different from previous
```

### Example of BAD data (5× repeats - THIS SHOULD NOT HAPPEN):
```
Time(s), Position(mm), Force(N)
0.000, 10.000, 0.0012
0.016, 10.000, 0.0012  ← REPEAT
0.032, 10.000, 0.0012  ← REPEAT
0.048, 10.000, 0.0012  ← REPEAT
0.064, 10.000, 0.0012  ← REPEAT
0.080, 10.000, 0.0015  ← Finally changed
```

### Red Flags:
- ❌ Force values repeat 5 consecutive times (~80ms)
- ❌ Timing intervals inconsistent or too fast (<10ms)
- ❌ Force column has long runs of identical values

**If you see repeats**: The decimation code may not have been fully removed. Contact for help.

---

## Test 4: Sampling Rate Change (2 minutes)
**Goal**: Verify GUI sampling rate control works

### Steps:
1. Start live readout at **50ms** (20Hz)
2. Record for 10 seconds
3. Stop and check CSV: intervals should be ~50ms
4. Start live readout at **10ms** (100Hz)
5. Record for 10 seconds
6. Stop and check CSV: intervals should be ~10ms

### Expected Results:
- ✅ CSV timing matches GUI setting (±2ms jitter acceptable)
- ✅ No force value repeats at either rate
- ✅ Higher rate (10ms) has more data points per second

### Red Flags:
- ❌ Timing doesn't match GUI setting (e.g., set to 50ms but CSV shows 16ms)
- ❌ Force values repeat at any setting

---

## Test 5: Calibration (3 minutes)
**Goal**: Verify single-cell calibration works

### Steps:
1. Click "Calibrate Force" button
2. Follow two-step calibration:
   - Zero force → Click OK
   - Apply known force (e.g., 0.5N) → Enter value → Click OK
3. Check console for GAIN and OFFSET values

### Expected Results:
- ✅ Calibration completes without errors
- ✅ Console shows: "Calibration complete. GAIN: X.XXXX, OFFSET: X.XXXXXXXX"
- ✅ No references to multiple channels or bridge gain
- ✅ Force readings now show calibrated values

### Red Flags:
- ❌ Errors about missing bridge gain methods
- ❌ References to "Channel 0, 1, 2" or triple cell mode
- ❌ Calibration fails or hangs

---

## Test 6: Short Print Test (10 minutes)
**Goal**: Verify adhesion metrics and post-processing work

### Steps:
1. Load a simple print (e.g., 2-layer test)
2. Run the print with adhesion metrics enabled
3. Observe console output during lifting phase
4. Check for "PFL: Lifting motion detected..." message
5. After print completes, check for post-processing output
6. Verify CSV was created and plots were generated

### Expected Results:
- ✅ Print runs normally with no decimation errors
- ✅ Adhesion metrics calculated for each layer
- ✅ Console shows phase-aware pre-initiation detection
- ✅ Post-processing generates plots automatically
- ✅ CSV file has unique force values (no repeats)

### Red Flags:
- ❌ Errors about missing decimation methods
- ❌ Adhesion calculation fails
- ❌ Post-processing doesn't run
- ❌ Force values repeat in the print CSV

---

## Summary Checklist

Before marking this complete, verify ALL of these:

- [ ] Force gauge connects without decimation errors
- [ ] Live readout works smoothly
- [ ] **CSV force values DON'T repeat 5× (MOST IMPORTANT)**
- [ ] Sampling rate control works correctly
- [ ] Timing intervals match GUI setting
- [ ] Calibration completes successfully
- [ ] Test print runs without errors
- [ ] Adhesion metrics calculate correctly
- [ ] Post-processing generates plots

---

## If Tests Fail

### Force values still repeating?
1. Check `support_modules/ForceGaugeManager.py` for any `decimation` references
2. Verify git status shows clean working directory
3. Review commit 1017219 to ensure revert was complete

### Errors about missing methods?
1. Check if any files import or call decimation-related methods
2. Search workspace for `set_decimation_factor`, `USE_DECIMATION`, `decimation_buffer`
3. May need to restart VS Code / Python environment

### Timing issues?
1. Verify PositionLogger.py doesn't have forced 8ms rate
2. Check SensorDataWindow.py sampling rate spinbox is enabled
3. Ensure ForceGaugeManager.py uses GUI-configured rate

---

## Success Criteria

✅ **ALL tests pass**: System is ready for production use  
⚠️ **Some tests fail**: Investigate and fix before using for real prints  
❌ **Multiple tests fail**: Revert may be incomplete, review git changes

---

## Next Steps After Testing

1. **If all tests pass**: 
   - System is ready for production use
   - Monitor first few prints closely for any issues
   - Document any noise issues (if decimation removal affects data quality)

2. **If noise is an issue**:
   - Consider post-processing filtering (Gaussian, moving average)
   - Adjust smoothing parameters in adhesion_metrics_calculator.py
   - Do NOT re-implement decimation without solving timing issue

3. **For future improvements**:
   - Explore hardware-side filtering (if available on Phidget)
   - Consider data buffering strategies that match PositionLogger rate
   - Document actual PositionLogger rate for future reference

---

**Date Completed**: ____________  
**Tested By**: ____________  
**Result**: ☐ All Pass  ☐ Some Issues  ☐ Major Problems
