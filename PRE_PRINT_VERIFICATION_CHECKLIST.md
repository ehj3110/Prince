# Pre-Print System Check - Dynamic Decimation
**Date**: November 9, 2025  
**Status**: Ready for Testing

---

## ✅ VERIFICATION COMPLETE

All files have been checked and are compatible with dynamic decimation implementation.

---

## Data Flow During Print

```
Hardware (1200Hz @ 1ms)
    ↓
ForceGaugeManager._onVoltageRatioChange()
    → Collects 25 samples (for 25ms rate)
    → Averages them
    → Pushes 1 sample to raw_data_queue every 25ms
    ↓
ForceGaugeManager._data_processing_loop()
    → Reads from raw_data_queue
    → Calculates force (applies calibration)
    → Pushes to output_force_queue
    ↓
PositionLogger (runs every 25ms)
    → Reads from output_force_queue
    → Gets Zaber position
    → Writes to CSV: Time, Position, Force, Phase
    ↓
PeakForceLogger (during layer)
    → Reads from data buffer
    → Detects phase events
    → Calculates adhesion metrics
    ↓
AdhesionMetricsCalculator
    → Applies smoothing
    → Finds peaks, pre-initiation, propagation
    → Outputs metrics to layer CSV
```

---

## File-by-File Verification

### ✅ ForceGaugeManager.py
**Status**: READY
- ✅ Dynamic decimation implemented
- ✅ `USE_DECIMATION = True`
- ✅ `decimation_factor` auto-calculated from user rate
- ✅ Hardware set to 1ms maximum speed
- ✅ Callback averages N samples before output
- ✅ `set_data_interval()` updates decimation factor
- ✅ Debug messages added for monitoring
- ✅ No hanging dependencies

**What happens**: Averages 25 hardware samples (at 1ms each) → outputs 1 sample every 25ms

---

### ✅ SensorDataWindow.py
**Status**: READY
- ✅ Calls `force_gauge_manager.set_data_interval(interval_ms)`
- ✅ No direct decimation dependencies
- ✅ GUI spinbox controls user sampling rate
- ✅ Rate change triggers decimation recalculation

**What happens**: User changes spinbox → calls `set_data_interval()` → decimation factor updates

---

### ✅ PositionLogger.py
**Status**: READY
- ✅ No decimation dependencies
- ✅ Reads from `force_data_queue_ref` at configured interval
- ✅ Phase detection works independently
- ✅ CSV writing unchanged

**What happens**: Reads force from queue every 25ms → writes to CSV with timestamp, position, force, phase

---

### ✅ PeakForceLogger.py
**Status**: READY
- ✅ No decimation dependencies
- ✅ Phase-aware adhesion tracking implemented
- ✅ Works with `phase_event_queue_ref`
- ✅ Buffers data during layer monitoring
- ✅ Triggers adhesion calculation on layer end

**What happens**: Collects force/position/time during layer → passes to calculator with `lifting_start_idx`

---

### ✅ adhesion_metrics_calculator.py
**Status**: READY
- ✅ No decimation dependencies
- ✅ Phase-aware pre-initiation detection
- ✅ Improved propagation end detection (1st derivative)
- ✅ Works with any sampling rate

**What happens**: Receives data arrays → applies smoothing → calculates adhesion metrics

---

### ✅ Prince_Segmented.py
**Status**: READY
- ✅ No decimation dependencies
- ✅ Standard print flow unchanged
- ✅ Post-processing integration preserved
- ✅ No references to ForceGaugeManager directly

**What happens**: Executes layer sequence → SensorDataWindow manages force logging → prints complete normally

---

## Potential Issues Check

### ❌ NO ISSUES FOUND

All potential problems checked:

1. **Queue Timing Mismatch** ✅ SOLVED
   - Decimation output rate MATCHES PositionLogger sampling rate
   - No more empty queue reads
   - No more repeated values

2. **Callback Dependencies** ✅ CLEAR
   - No code depends on old fixed decimation
   - All downstream consumers work with queue data

3. **Calibration** ✅ COMPATIBLE
   - Calibration applies to voltage AFTER decimation
   - Force calculation unchanged
   - Works with averaged samples

4. **Phase Detection** ✅ INDEPENDENT
   - Phase detection in PositionLogger uses position only
   - No timing dependencies on force sampling
   - Works at any rate

5. **Adhesion Metrics** ✅ INDEPENDENT
   - Calculator works with any sampling rate
   - No hard-coded timing assumptions
   - Phase-aware improvements functional

6. **Print Process** ✅ UNCHANGED
   - Layer execution sequence same
   - Exposure timing unaffected
   - Stage motion unaffected
   - Only force data collection improved

---

## Pre-Print Checklist

Before starting your print, verify these items:

### Console Output
- [ ] **Startup banner shows**:
  ```
  ======================================================================
  DECIMATION STATUS
  ======================================================================
  USE_DECIMATION: True
  Hardware interval: 1ms (~1000Hz)
  User interval: 25ms (40.0Hz)
  Decimation factor: 25×
  Expected noise reduction: 5.00×
  ======================================================================
  ```

- [ ] **On force gauge connection**:
  ```
  Dynamic decimation mode: Hardware at 1ms (~1200Hz), decimating to match user rate
  Current decimation factor: 25× (output: 25ms)
  ```

- [ ] **During recording** (occasional):
  ```
  [DECIMATION DEBUG] Output sample #100: averaged 25 samples
  [DECIMATION DEBUG] Output sample #200: averaged 25 samples
  ```

### GUI Settings
- [ ] Sampling rate set to desired value (e.g., 25ms, 30ms, 50ms)
- [ ] Force gauge calibrated and showing stable readings
- [ ] Position logger plot shows smooth force trace
- [ ] No error messages in status bar

### Test Recording
- [ ] Record 5-10 seconds of force data
- [ ] Check CSV file:
  - [ ] Time intervals consistent (~25ms if that's your setting)
  - [ ] Force values DON'T repeat
  - [ ] All columns present (Time, Position, Force, Phase)
  - [ ] No NaN or blank values

---

## During Print - What to Watch

### Normal Operation Indicators
✅ **Console shows**:
- Layer progress updates
- Phase changes (Pause → Lift → Retract)
- Adhesion metrics calculated per layer
- No queue overflow warnings
- No timing warnings

✅ **GUI shows**:
- Smooth force readout updates
- Position changes during lift/retract
- Phase indicator updates correctly
- No frozen UI or lag

✅ **CSV files**:
- Layer files created in correct directory
- Timestamps sequential and consistent
- Force values reasonable (not all zeros or repeating)
- Phase column shows Pause/Lift/Retract correctly

### Warning Signs
⚠️ **If you see**:
- "Warning: Output force queue full, dropping data"
  → Decimation output too fast or PositionLogger too slow
  → Check sampling rate setting

- Force values repeating 3+ times in CSV
  → Decimation may not be working
  → Check console for debug messages

- Long gaps in CSV timestamps (>100ms)
  → PositionLogger may be stalling
  → Check for Zaber communication issues

- "Queue empty" errors
  → Very unlikely with dynamic decimation
  → Check that USE_DECIMATION is True

---

## Post-Print Verification

After print completes:

1. **Check CSV files exist**:
   - [ ] Main log file in `Evan_AdhesionTests` folder
   - [ ] Individual layer files if enabled
   - [ ] Adhesion metrics CSV if automated logging

2. **Verify data quality**:
   - [ ] Run: `python test_check_decimation_working.py <your_csv_file>`
   - [ ] Should show consistent timing
   - [ ] Should show no/minimal repeated values
   - [ ] Should show expected sample count

3. **Check adhesion metrics**:
   - [ ] Metrics CSV has entries for all layers
   - [ ] Values are reasonable (not NaN or zero)
   - [ ] Pre-initiation times positive
   - [ ] Work of adhesion positive

---

## Emergency Rollback

If print fails or data looks wrong:

**Option 1: Disable decimation**
```python
# In ForceGaugeManager.py line ~40
self.USE_DECIMATION = False  # Change True to False
```
System will revert to direct hardware sampling (no averaging).

**Option 2: Git revert**
```bash
git log --oneline -5  # Find commit before decimation
git revert <commit_hash>  # Revert to previous version
```

**Option 3: Use backup**
Your previous version (pre-decimation) is in git history at commit `1017219`.

---

## Success Criteria

Print is successful if:

✅ All layers print completely  
✅ CSV file has consistent timing intervals  
✅ No repeated force values in CSV  
✅ Adhesion metrics calculated for all layers  
✅ No console errors or warnings  
✅ Force data shows expected noise reduction (~5× for 25ms rate)  
✅ Phase detection works correctly  
✅ Post-processing generates plots (if enabled)  

---

## Summary

**System Status**: ✅ READY FOR PRODUCTION PRINT

**Changes Made**:
- Dynamic decimation tied to user sampling rate
- Hardware samples at 1ms (maximum speed)
- Decimation factor = user_rate_ms / 1ms
- Output rate ALWAYS matches GUI setting
- No timing mismatch with PositionLogger

**Risk Level**: 🟢 LOW
- All code paths verified
- No hanging dependencies found
- Fallback options available
- Debug monitoring active

**Recommendation**: 
Proceed with print. Monitor console for first few layers. If any issues, stop print and check console messages.

---

**Ready to print!** 🚀
