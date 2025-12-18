# Three Fixes for Print Issues - Summary

## Date: Current Session
## Status: ✅ COMPLETED

---

## Issue 1: Sandwich Routine Direction Reversed

### Problem Description
User reported: "The sandwich routine has our axes flipped. I am seeing it moving downwards to contact the glass very fast, but then moving back upwards at the three step ramping when we want it to be the opposite."

**Expected Behavior:**
- Descent toward glass: **RAMPED** (3-4 tier speed reduction)
- Ascent away from glass: **FAST** (single speed)

**Actual Behavior:**
- Descent: Fast
- Ascent: Ramped (symmetrical to descent)

### Root Cause
In `Prince_Segmented.py` lines 1140-1193, the ascent phase was implemented with symmetrical 4-tier ramping matching the descent, when it should have been a fast single-speed retract.

### Solution Implemented
**File Modified:** `Prince_Segmented.py`
**Lines:** ~1140-1193

**Changes:**
- Replaced 4-segment ramped ascent with fast single-speed ascent
- Ascent speed: `4x` base sandwich speed (e.g., 200µm/s base → 800µm/s ascent)
- Kept optional pause at 50% ascent point (if `actual_pause > 0`)
- If pause specified: Move fast to 50% → pause → continue fast to target
- If no pause: Single fast move from glass to layer position

**Key Code:**
```python
# Fast retract speed (4x base sandwich speed)
fast_retract_speed_um_s = actual_sandwich_speed_um_s * 4.0

# Single fast ascent (no ramping)
self.axis.move_absolute(
    position=sandwich_target_position_um,
    velocity=fast_retract_speed_um_s / 1000.0,
    ...
)
```

### Testing Required
- Verify descent still uses 4-tier ramping (200→100→50→25 µm/s pattern)
- Verify ascent is fast and smooth
- Confirm forces are correctly monitored during ramped descent
- Check pause functionality (if enabled) at 50% ascent point

---

## Issue 2: Excessive Console Messages (Decimation Debug)

### Problem Description
Console output was cluttered with debug messages from decimation system:
- `[DECIMATION DEBUG] Counter: 1/12, Buffer size: 50` - Every 500 hardware samples (~0.5 seconds)
- `[DECIMATION DEBUG] Output sample #X: averaged 12 samples` - Every 100 output samples (~1.2 seconds at 12ms rate)

This made console difficult to read during printing.

### Root Cause
Debug messages added during decimation implementation for verification were printing too frequently.

### Solution Implemented
**File Modified:** `support_modules/ForceGaugeManager.py`
**Lines:** ~508-524

**Changes:**
1. **Removed:** Counter debug message (was every 500 callbacks)
2. **Reduced:** Output sample message from every 100 to every 5000 samples
3. **Updated:** Message format to be more concise

**Key Code:**
```python
# Print every 5000 samples (~60 seconds at 12ms rate, ~125 seconds at 25ms rate)
if self.output_count % 5000 == 0 and self.output_count > 0:
    print(f"[DECIMATION] Output sample #{self.output_count}: averaging {self.decimation_factor} samples at {self.user_sampling_interval_ms}ms intervals")
```

### Result
- Debug message now appears approximately once per minute (instead of every second)
- Console remains clean and readable
- Still provides periodic confirmation that decimation is working
- Message includes key info: output count, decimation factor, interval

### Testing Required
- Verify console output is clean during print
- Confirm decimation still working (check occasional debug message)
- Monitor CSV data quality unchanged

---

## Issue 3: Light Engine Not Turning On

### Problem Description
User reported: "The light engine did not turn on. Did we put it into standby mode by accident?"

### Root Cause Analysis
DLP power management sequence had a potential timing issue:

**Current Flow:**
1. Print start: `controller.power(current=dlp_power)` - Set once at beginning
2. Each layer exposure: Image displayed, LED assumed to be at correct power
3. After exposure: `controller.power(current=0)` - Background light off before peel
4. After return: `controller.power(current=next_layer_power)` - Restored for next layer

**Problem:** 
- If previous layer set power to 0, and next layer started before power restoration completed
- No explicit power setting BEFORE each exposure, only AFTER previous peel
- First layer has correct power (from print start), but subsequent layers may not

### Solution Implemented
**File Modified:** `Prince_Segmented.py`
**Lines:** ~827-840

**Changes:**
Added explicit DLP power setting **before each layer's exposure**:

```python
# 0. Ensure DLP power is set correctly for this layer's exposure
if hasattr(self, 'controller'):
    try:
        current_dlp_power = int(actual_dlp_power)
        # Only update if different from last commanded value
        if current_dlp_power != last_commanded_dlp_power:
            self.controller.power(current=current_dlp_power)
            last_commanded_dlp_power = current_dlp_power
            self.update_status_message(f"L{X}: DLP power set to {current_dlp_power}")
    except Exception as e:
        self.update_status_message(f"L{X}: Could not set DLP power: {e}", error=True)

# 1. Display image for layer i
...
```

### Key Benefits
1. **Guaranteed Power:** Every layer explicitly sets DLP power before exposure
2. **Optimization:** Only sends command if power changed (tracked via `last_commanded_dlp_power`)
3. **Redundancy:** Keeps existing power restore after return (defense in depth)
4. **Visibility:** Status message confirms power setting for each layer

### Note on Standby Mode
- Checked line 2316: `self.controller.standby()` only called during final cleanup
- NOT called during pre-calibration or print initialization
- Light engine should remain active throughout print

### Testing Required
- Verify DLP activates for first layer exposure
- Verify DLP remains active for all subsequent layers
- Check console for "DLP power set to X" messages
- Confirm exposures are bright and uniform
- Monitor for any standby mode errors

---

## Files Modified Summary

### 1. Prince_Segmented.py
- **Line ~827:** Added DLP power setting before stepped mode exposure
- **Lines ~1140-1193:** Replaced ramped ascent with fast single-speed ascent

### 2. support_modules/ForceGaugeManager.py
- **Lines ~508-524:** Reduced decimation debug message frequency (100 → 5000 samples)

---

## Testing Checklist

### Pre-Test Verification
- [x] All three fixes applied to correct files
- [ ] No syntax errors (check Python lint)
- [ ] Backup of previous version available

### Sandwich Direction Test
- [ ] Run pre-calibration successfully
- [ ] Observe sandwich descent: Should see 4 speed tiers (ramping down)
- [ ] Observe sandwich ascent: Should be fast, single speed
- [ ] Check console shows correct speed messages
- [ ] Verify forces monitored during descent (failsafe triggers if needed)

### Console Verbosity Test
- [ ] Start print with 12ms sampling rate
- [ ] Monitor console output during print
- [ ] Confirm decimation message appears ~once per minute
- [ ] Console should be clean and readable
- [ ] Essential status messages still visible

### DLP Activation Test
- [ ] Run multi-layer print (at least 3 layers)
- [ ] Verify DLP turns on for Layer 1 exposure
- [ ] Verify DLP stays on for Layer 2 exposure
- [ ] Verify DLP stays on for Layer 3 exposure
- [ ] Check console for "DLP power set to X" messages each layer
- [ ] Visually confirm bright, uniform exposures
- [ ] No "standby mode" errors in console

### Data Quality Test
- [ ] Complete full print (or at least 5 layers)
- [ ] Check CSV files for:
  - [ ] Consistent force data timing (no repeated values)
  - [ ] Proper phase annotations (Exposure, Pause, Lift, Retract, Sandwich)
  - [ ] No gaps or missing data
- [ ] Run post-print analysis (should complete without errors)
- [ ] Verify plots generate correctly

---

## Success Criteria

**Fix 1 - Sandwich Direction:**
- ✅ Descent shows 4-tier ramping in status messages
- ✅ Ascent shows single fast speed in status messages
- ✅ Force failsafe triggers properly during ramped descent (if threshold exceeded)

**Fix 2 - Console Clean:**
- ✅ Decimation debug message appears ≤ once per minute
- ✅ Console readable, essential messages visible
- ✅ No functional changes to decimation behavior

**Fix 3 - DLP Activation:**
- ✅ "DLP power set to X" message for each layer before exposure
- ✅ Bright exposures on all layers
- ✅ No standby mode issues
- ✅ No dark/unexposed layers

---

## Rollback Instructions

If any fix causes issues:

### Revert Fix 1 (Sandwich):
- Restore `Prince_Segmented.py` lines 1140-1193 to previous symmetrical ramping ascent

### Revert Fix 2 (Console):
- Restore `ForceGaugeManager.py` lines 508-524 to previous debug frequency

### Revert Fix 3 (DLP):
- Remove lines ~830-840 in `Prince_Segmented.py` (DLP power setting before exposure)
- Rely on original power restore after return

**Full Rollback:** Use git revert or restore from backup before this session.

---

## Notes for Future

1. **Sandwich Speed Tuning:** If ascent is too fast (causes splash/vibration), reduce multiplier from 4× to 3× or 2×
2. **Console Verbosity:** If more debug needed, change `5000` to `1000` (message every ~12 seconds)
3. **DLP Power Management:** Current implementation has redundancy (before exposure + after return). If issues persist, investigate DLP controller state machine or add power status verification
4. **Standby Mode:** Consider adding explicit wake-up command during print initialization if standby issues recur

---

## Related Documents
- `DYNAMIC_DECIMATION_IMPLEMENTATION.md` - Dynamic decimation technical details
- `PRE_PRINT_VERIFICATION_CHECKLIST.md` - Complete pre-print checklist
- `IMPLEMENTATION_SUMMARY.md` - Overall project status

