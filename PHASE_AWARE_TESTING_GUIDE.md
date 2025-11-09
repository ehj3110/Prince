# Phase-Aware Adhesion Metrics - Quick Testing Guide

**Date**: November 7, 2025  
**Status**: Ready for hardware testing

---

## What Changed?

### Real-Time Phase Awareness
- PositionLogger now emits phase events (Lift, Retract, Pause, Sandwich, Exposure)
- PeakForceLogger receives these events and tracks when lifting starts
- Adhesion calculator uses lifting start marker to limit pre-initiation search
- **Result**: Pre-initiation detection won't search past exposure/pause into sandwich

### Adaptive Boundary Detection
- RawData_Processor now checks for Phase column in CSV
- If Phase column exists: Uses phase-based detection (most accurate)
- If no Phase column: Uses adaptive detection (50% of max motion)
- **Result**: No longer relies on hardcoded 6mm distance

---

## Expected Console Output

### During Printing

**Phase Transitions** (from PositionLogger):
```
PositionLogger: Phase transition → Sandwich at 10.234mm
PositionLogger: Phase transition → Pause at 9.876mm
PositionLogger: Phase transition → Lift at 9.876mm
PositionLogger: Phase transition → Retract at 15.890mm
PositionLogger: Phase transition → Pause at 15.890mm
```

**Phase Tracking** (from PeakForceLogger):
```
PFL: Lifting started at buffer idx 45, time 2.345s
```

**Pre-Initiation Search** (from AdhesionCalculator):
```
Pre-initiation search limited to indices 45-234 (lifting started at 45)
```

### Post-Processing

**With Phase Column**:
```
Using phase-aware boundary detection (Phase column found)
Layer 1: Lift[123-456, 6.02mm], Retract[789-890, 6.01mm]
Layer 2: Lift[1234-1567, 5.98mm], Retract[1890-2001, 6.00mm]
...
=== Total layers detected: 50 ===
```

**Without Phase Column**:
```
Phase column not found - using adaptive detection
Found 100 significant motions (>3.12mm)
  Motion 1: idx 123-456, distance 6.02mm
  Motion 2: idx 789-890, distance 6.01mm
  ...
Layer 1: Lift[123-456, 6.02mm], Retract[789-890, 6.01mm]
...
=== Total layers detected: 50 ===
```

---

## Quick Tests

### Test 1: Phase Events Working?
**What to do**: Run any print  
**What to look for**: Console messages "Phase transition →"  
**Expected**: 4-5 phase transitions per layer  
**✅ Pass**: Phase transitions appear in console  
**❌ Fail**: No phase transition messages

### Test 2: Lifting Start Tracked?
**What to do**: Run automated print with work of adhesion logging  
**What to look for**: "PFL: Lifting started at buffer idx"  
**Expected**: One message per layer  
**✅ Pass**: Lifting start messages appear  
**❌ Fail**: No lifting start messages

### Test 3: Pre-Initiation Limited?
**What to do**: Run print with sandwich step, check adhesion CSV  
**What to look for**: Pre-initiation times should be SHORT (0.2-0.5s typical)  
**Before**: Pre-initiation times might be 2-5s (searching into sandwich)  
**After**: Pre-initiation times should be 0.2-0.5s (limited to Lift phase)  
**✅ Pass**: Pre-initiation times are reasonable  
**❌ Fail**: Pre-initiation times still very long

### Test 4: Adaptive Detection?
**What to do**: Run post_print_analyzer.py on CSV with various overstep distances  
**What to look for**: All layers detected correctly  
**Expected**: Works with 0mm, 3mm, 6mm, 10mm overstep  
**✅ Pass**: All layers found regardless of overstep  
**❌ Fail**: Only finds layers with specific distance

### Test 5: Phase-Based Detection?
**What to do**: Run post_print_analyzer.py on CSV with Phase column  
**What to look for**: "Using phase-aware boundary detection"  
**Expected**: Uses phase transitions to find layers  
**✅ Pass**: Phase-based detection message appears  
**❌ Fail**: Falls back to adaptive even with Phase column

---

## Troubleshooting

### Problem: No phase transition messages
**Cause**: Position logger not running or phase detection disabled  
**Solution**: Check that position logger thread is started

### Problem: No lifting start messages
**Cause**: Phase queue not connected to PeakForceLogger  
**Solution**: Verify SensorDataWindow passes `phase_event_queue_ref`

### Problem: Pre-initiation still very long
**Cause**: Phase events not reaching adhesion calculator  
**Solution**: Check that lifting_start_idx is being passed through analysis chain

### Problem: Boundary detection still hardcoded
**Cause**: Old RawData_Processor code still running  
**Solution**: Verify latest code deployed, check for Phase column in CSV

### Problem: Phase queue full warning
**Cause**: PeakForceLogger not consuming events fast enough  
**Solution**: This is rare but harmless - queue will skip events if full

---

## Validation Checklist

Before Production Use:
- [ ] Phase transitions appear in console during printing
- [ ] Lifting start index tracked by PeakForceLogger
- [ ] Pre-initiation times are reasonable (0.2-0.5s typical)
- [ ] Boundary detection works with different overstep distances
- [ ] Phase-based detection used when Phase column available
- [ ] No performance degradation during printing
- [ ] Adhesion metrics CSV shows reasonable values

Advanced Validation:
- [ ] Compare adhesion metrics before/after phase awareness
- [ ] Verify pre-initiation times reduced by 1-3s for sandwich prints
- [ ] Test with 0mm overstep (minimal lift)
- [ ] Test with 10mm overstep (large lift)
- [ ] Process old CSV files without Phase column (adaptive fallback)

---

## Metrics to Watch

### Pre-Initiation Time
**Before**: 1-5s (searching into sandwich/pause)  
**After**: 0.2-0.5s (limited to Lift phase)  
**Improvement**: 2-4.5s reduction

### Total Peel Duration
**Before**: May include sandwich/pause time  
**After**: Only Lift phase  
**Improvement**: More accurate representation

### Work of Adhesion
**Before**: May include sandwich pre-force  
**After**: Only adhesion during lifting  
**Improvement**: More physically meaningful

---

## Files to Monitor

### During Printing
- Console output (phase transitions, lifting start)
- Automated work of adhesion CSV (reasonable metrics)

### Post-Processing
- Console output (detection method used)
- Processed metrics CSV (all layers found)
- Analysis plots (boundaries match actual data)

---

## Expected Improvements

### Real-Time Analysis
✅ Phase awareness during printing  
✅ No need to save all raw data  
✅ Accurate metrics calculated on-the-fly

### Pre-Initiation Detection
✅ Respects phase boundaries  
✅ Doesn't search into sandwich/pause  
✅ More accurate initiation times

### Boundary Detection
✅ Works with any overstep distance  
✅ No hardcoded 6mm requirement  
✅ Adaptive to print parameters

### Backward Compatibility
✅ Works without phase info (fallback)  
✅ Old CSV files still processable  
✅ No breaking changes

---

## Quick Commands

### Run Test Print
```powershell
# Start Prince_Segmented.py
# Load instruction file
# Start print
# Watch console for phase transitions
```

### Post-Process with Phase Column
```powershell
cd "c:\Users\cheng sun\BoyuanSun\Prince_CurrentWorkingVersion\post-processing"
python run_post_analysis.py
# Select CSV file with Phase column
# Verify "Using phase-aware boundary detection" appears
```

### Post-Process without Phase Column (Test Adaptive)
```powershell
# Process old CSV file (before Nov 7, 2025)
# Verify "Phase column not found - using adaptive detection" appears
# Verify all layers still detected correctly
```

---

**Ready to Test!** Run a print and observe the console output for phase transitions and lifting start tracking.
