# Sandwich Pre-Calibration Quick Reference
**Last Updated**: October 17, 2025

---

## 🎯 Quick Start

### Enable the Feature:
1. Check ☑ "Enable Pre-Calibration" in Sandwich Routine panel
2. Update instruction file to 14-column format (see below)
3. Start print - pre-cal runs automatically before layer 1

### Disable the Feature:
1. Uncheck ☐ "Enable Pre-Calibration" in Sandwich Routine panel
2. Sandwich steps will be skipped entirely during print

---

## 📄 Instruction File Format

### Old Format (15 columns) - DEPRECATED:
```
Layer  File  Thickness  Exposure  Intensity  Speed  Overstep  Accel  Pause  Gap  Force  Speed  Accel  Pause  Touches
1      img1  50         2.0       255        1000   200       5000   0.5    0.5  0.05   500    5000   0.5    1
```

### New Format (14 columns) - CURRENT:
```
Layer  File  Thickness  Exposure  Intensity  Speed  Overstep  Accel  Pause  Gap  MaxForce  Speed  Touches  DerivThresh
1      img1  50         2.0       255        1000   200       5000   0.5    0.5  0.2       500    1        0.075
```

### Column Changes:
- **Column 9**: `gap_estimate` (mm) - Initial guess for pre-cal [default: 0.5]
- **Column 10**: `max_sandwich_force` (N) - Safety limit [default: 0.2]
- **Column 11**: `sandwich_speed` (µm/s) - Base speed [default: 500]
- **Column 12**: `sandwich_touches` (#) - Number of touches [default: 1]
- **Column 13**: `precalib_derivative_threshold` (N/s) - Fallback [default: 0.075]

### Removed Columns:
- ~~Column 10: sandwich_force~~ (replaced by derivative detection)
- ~~Column 12: sandwich_accel~~ (now fixed at 1 mm/s²)
- ~~Column 13: sandwich_pause~~ (removed, not needed)

---

## ⚙️ Recommended Settings

### Small Parts (< 20mm²):
```
Gap  MaxForce  Speed  Touches  DerivThresh
0.5  0.15      500    1        0.075
```

### Medium Parts (20-50mm²):
```
Gap  MaxForce  Speed  Touches  DerivThresh
0.5  0.25      500    1        0.075
```

### Large Parts (> 50mm²):
```
Gap  MaxForce  Speed  Touches  DerivThresh
0.5  0.40      500    1        0.075
```

### High Adhesion Materials:
```
Gap  MaxForce  Speed  Touches  DerivThresh
0.5  0.25      500    3        0.075
```

### Delicate Parts:
```
Gap  MaxForce  Speed  Touches  DerivThresh
0.5  0.15      300    1        0.075
```

---

## 🔍 Status Messages to Watch For

### Pre-Calibration Success:
```
=== STARTING PRE-CALIBRATION ROUTINE ===
Pre-cal: Phase 1 - Initial descent with adaptive speed...
Pre-cal: First contact at 10.487mm (gap: 0.487mm)
Pre-cal: Phase 2 - Performing 5 oscillations for averaging...
Pre-cal: RESULTS - Avg gap: 0.489mm, Avg peak dF/dt: 0.0817 N/s
=== PRE-CALIBRATION COMPLETE ===
```

### Sandwich Success (Each Layer):
```
L25: Starting ADAPTIVE sandwich (Gap:0.489mm, dF/dt:0.0817N/s, MaxF:0.2N, Speed:500µm/s, Touches:1)
L25: Touch 1/1 - Contact at 9.011mm (Gap:0.491mm, derivative trigger)
L25: Sandwich complete, position 8.520mm
```

### Force Override (Warning):
```
L42: Touch 1/1 - FORCE OVERRIDE at 6.234mm (Gap:0.494mm) - ABORTING TOUCH
```
→ **Action**: Increase MaxForce in instruction file

### Pre-Cal Failed (Error):
```
Pre-cal: No contact detected (reason: user_stop)
Pre-calibration FAILED: Will skip sandwich during print
```
→ **Action**: Check force gauge calibration, increase gap estimate

---

## 🛠️ Troubleshooting

| Problem | Possible Cause | Solution |
|---------|----------------|----------|
| Pre-cal fails to detect contact | Force gauge not calibrated | Calibrate from Sensor Panel |
| Pre-cal fails to detect contact | Gap estimate too small | Increase Column 9 to 0.8 or 1.0 |
| Pre-cal fails to detect contact | Derivative threshold too high | Lower Column 13 to 0.050 |
| Force override every layer | MaxForce too low | Increase Column 10 to 0.3-0.4 |
| Force override every layer | Speed too high | Reduce Column 11 to 300 |
| Sandwich takes too long | Speed too low | Increase Column 11 to 800 |
| Sandwich takes too long | Too many touches | Reduce Column 12 to 1 |
| Contact inconsistent | Gap changed during print | Re-run pre-cal (restart print) |
| No sandwich steps running | Checkbox unchecked | Check GUI checkbox |
| No sandwich steps running | Pre-cal failed | Check status for error messages |

---

## 📊 Expected Timings

| Stage | Duration |
|-------|----------|
| Pre-calibration (total) | ~60 seconds |
| - Initial descent | ~10 seconds |
| - 5 oscillations | ~40 seconds |
| - Return to start | ~5 seconds |
| - Final pause | 5 seconds |
| **Per-Layer Sandwich** | **4-6 seconds** |
| - Force settling | 1 second |
| - Adaptive descent | 1-2 seconds |
| - Adaptive ascent | 1-2 seconds |
| - Touch pause (if multi) | 0.1 seconds |

---

## 🔄 Rollback Plan

### Quick Disable (No Code Changes):
1. Uncheck ☐ "Enable Pre-Calibration" checkbox
2. Sandwich skipped entirely
3. Print proceeds normally

### Full Rollback (Restore Old System):
**Files to Modify**: `Prince_Segmented.py`, `support_modules/libs.py`  
**See**: `SANDWICH_ADAPTIVE_SPEED_SUMMARY.md` Section "Rollback Instructions"

---

## 📐 Force Derivative Reference Values

| Condition | Typical dF/dt |
|-----------|---------------|
| No contact (noise) | 0.0 - 0.01 N/s |
| Light touch | 0.05 - 0.15 N/s |
| Full contact | 0.15 - 0.50 N/s |
| **Pre-cal default threshold** | **0.075 N/s** |

---

## 🎚️ Adaptive Speed Profile

| Stage | Distance | Speed | Purpose |
|-------|----------|-------|---------|
| 1st 50% | 0% - 50% of gap | X (base) | Fast approach |
| 2nd 25% | 50% - 75% of gap | X/2 | Slow down |
| 3rd 25% | 75% - 100% of gap | X/4 | Gentle contact |

**Example with base_speed = 500 µm/s**:
- 0-50%: 500 µm/s
- 50-75%: 250 µm/s
- 75-100%: 100 µm/s

---

## 🔧 Advanced Tuning

### Increase Contact Sensitivity:
- **Lower derivative threshold**: Column 13 = 0.050 N/s
- **Reduce base speed**: Column 11 = 300 µm/s

### Increase Sandwich Speed:
- **Raise base speed**: Column 11 = 800 µm/s
- **Reduce touches**: Column 12 = 1

### Improve Adhesion:
- **More touches**: Column 12 = 3 or 5
- **Higher max force**: Column 10 = 0.3 N

### Reduce Part Stress:
- **Lower max force**: Column 10 = 0.15 N
- **Slower base speed**: Column 11 = 300 µm/s

---

## 📞 Support Reference

**Documentation**:
- Full Guide: `SANDWICH_PRECALIBRATION.md`
- Implementation Summary: `SANDWICH_ADAPTIVE_SPEED_SUMMARY.md`

**Code Locations**:
- Pre-calibration method: `Prince_Segmented.py` lines 1689-1874
- Adaptive speed method: `Prince_Segmented.py` lines 1535-1687
- Sandwich routine: `Prince_Segmented.py` lines 955-1099
- Instruction parser: `support_modules/libs.py` lines 103-183

---

**Quick Reference Version**: 1.0  
**Implementation Date**: October 17, 2025
