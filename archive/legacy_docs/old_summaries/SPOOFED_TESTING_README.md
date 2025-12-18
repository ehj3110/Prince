# Spoofed Print Testing Guide

**Purpose**: Test phase-aware adhesion metrics without running actual prints

---

## Quick Answer: What You Need

### Your existing autolog files are ENOUGH! ✅

The autolog files you have (e.g., `autolog_L48-L50.csv`) contain:
- ✅ Elapsed Time (s)
- ✅ Position (mm)  
- ✅ Force (N)

This is **sufficient** to test everything! The test scripts will:
1. Simulate phase detection from position data
2. Generate phase events
3. Test the entire data flow

---

## Test Scripts Created

### 1. **test_post_processing_spoofed.py** (Simple - Start Here!)

**What it tests**:
- ✅ RawData_Processor adaptive boundary detection
- ✅ RawData_Processor phase-based boundary detection
- ✅ Adhesion metrics calculation
- ✅ Backward compatibility

**How to run**:
```powershell
python test_post_processing_spoofed.py
```

**What it does**:
1. Loads your existing autolog CSV file
2. Tests adaptive detection (works without Phase column)
3. Adds Phase column to data (simulates what PositionLogger would output)
4. Tests phase-based detection
5. Compares both methods

**Output**:
- Console: Shows both detection methods working
- File: `test_output_with_phase.csv` (autolog with Phase column added)

**Expected results**:
```
TEST 1: Adaptive Boundary Detection (No Phase Column)
Processing with adaptive detection...
Layers detected: 3

TEST 2: Phase-Based Boundary Detection (With Phase Column)  
Processing with phase-based detection...
Layers detected: 3

✅ Adaptive Detection: PASS
✅ Phase-Based Detection: PASS
```

---

### 2. **test_print_simulation_spoofed.py** (Comprehensive - Full Simulation!)

**What it tests**:
- ✅ Phase event generation
- ✅ Phase event queue mechanism
- ✅ PeakForceLogger data collection
- ✅ Real-time adhesion metrics with phase awareness
- ✅ Phase-aware pre-initiation detection

**How to run**:
```powershell
python test_print_simulation_spoofed.py
```

**What it does**:
1. Creates `SimulatedPositionLogger` that reads CSV and emits phase events
2. Creates real `PeakForceLogger` connected to simulated phase queue
3. Feeds data point-by-point (like real print)
4. Tests phase-aware pre-initiation directly
5. Compares results with/without phase awareness

**Output**:
- Console: Complete simulation log with phase transitions
- File: `test_simulated_peak_force_output.csv` (metrics for each layer)

**Expected console output**:
```
SIMULATING PRINT DATA STREAM
  Phase transition → Pause at 66.200mm (index 0)
  Phase transition → Lift at 60.123mm (index 234)
  Phase transition → Retract at 66.456mm (index 567)

PROCESSING LAYER 1
PFL: Lifting started at buffer idx 0, time 1.234s
Pre-initiation search limited to indices 0-123 (lifting started at 0)

RESULTS
Layer 1:
  Peak Force: 1.2345 N
  Work of Adhesion: 3.4567 mJ
  Initiation Time: 0.3456 s  
  ✅ Initiation time looks good (phase-aware)

✅ Real-time logging: PASS (3 layers processed)
✅ Phase-aware pre-initiation: PASS
```

---

## What Files You Need

### Minimum Required:
Just **ONE autolog CSV file** from any previous print!

Example files that work:
- `archive/autolog_L48-L50.csv`
- `archive/autolog_L148-L150.csv`  
- `archive/autolog_L198-L200.csv`
- Any CSV with columns: `Elapsed Time (s)`, `Position (mm)`, `Force (N)`

### The scripts automatically:
1. Find available autolog files
2. Use the first one found
3. Generate Phase column from position data
4. Simulate complete print session

**You don't need to save any additional data!** The existing autolog files are perfect.

---

## Expected Test Results

### Test 1: Post-Processing (Simple)

**Adaptive Detection** (old CSV without Phase):
- Should detect layers based on significant motions (>50% max)
- Works with ANY overstep distance (not hardcoded to 6mm)

**Phase-Based Detection** (after adding Phase):
- Should detect layers based on Lift→Retract transitions
- More accurate boundary identification
- Uses explicit phase markers

**Both should find the same number of layers!**

### Test 2: Full Simulation (Comprehensive)

**Phase Events**:
- Should see phase transitions in console
- Typical sequence: Pause → Sandwich → Lift → Pause → Retract → Pause

**Phase-Aware Pre-Initiation**:
- Pre-initiation time should be SHORT (0.2-0.5s typical)
- Message: "Pre-initiation search limited to indices X-Y (lifting started at X)"
- If sandwich present, should NOT search into sandwich phase

**Metrics Output**:
- Should generate CSV with all adhesion metrics
- Values should match post-processing results
- Phase awareness should reduce pre-initiation times

---

## Interpreting Results

### Good Signs ✅

**Phase Detection**:
```
Phase transition → Sandwich at 10.234mm
Phase transition → Lift at 9.876mm  
Phase transition → Retract at 15.890mm
```
→ Phase detection is working!

**Phase Tracking**:
```
PFL: Lifting started at buffer idx 45, time 2.345s
```
→ PeakForceLogger receiving phase events!

**Phase-Aware Pre-Initiation**:
```
Pre-initiation search limited to indices 45-234 (lifting started at 45)
Initiation Time: 0.3456 s
✅ Initiation time looks good (phase-aware)
```
→ Pre-initiation correctly limited to Lift phase!

### Warning Signs ⚠️

**No phase transitions**:
```
(No "Phase transition →" messages)
```
→ Phase detection not running - check SimulatedPositionLogger

**Long initiation times**:
```
Initiation Time: 3.5678 s
⚠️ WARNING: Long initiation time
```
→ Phase awareness may not be working - check lifting_start_idx

**No layers detected**:
```
Layers detected: 0
```
→ Boundary detection failed - check CSV format or motion in data

---

## Troubleshooting

### Problem: "No autolog files found"
**Solution**: Place an autolog CSV in one of these locations:
- `archive/autolog_L48-L50.csv`
- `post-processing/autolog_L48-L50.csv`

Or edit the script to point to your file:
```python
csv_file = Path("path/to/your/autolog.csv")
```

### Problem: "Import errors" 
**Solution**: Run from project root directory:
```powershell
cd "c:\Users\cheng sun\BoyuanSun\Prince_CurrentWorkingVersion"
python test_post_processing_spoofed.py
```

### Problem: "No layers detected"
**Solution**: Your CSV might not have motion data. Try a different autolog file with actual print data (position changes >6mm).

### Problem: CSV format error
**Solution**: Verify your CSV has these columns:
- `Elapsed Time (s)`
- `Position (mm)`
- `Force (N)`

---

## Quick Start

**Simplest test** (5 seconds):
```powershell
python test_post_processing_spoofed.py
```

**Comprehensive test** (30 seconds):
```powershell
python test_print_simulation_spoofed.py
```

**Both tests** (1 minute):
```powershell
python test_post_processing_spoofed.py
python test_print_simulation_spoofed.py
```

---

## What Gets Tested

### ✅ RawData_Processor
- Adaptive boundary detection (no hardcoded 6mm)
- Phase-based boundary detection (Lift→Retract)
- Backward compatibility

### ✅ PeakForceLogger  
- Phase event consumption
- Lifting start index tracking
- Real-time data collection

### ✅ AdhesionMetricsCalculator
- Phase-aware pre-initiation
- Work of adhesion calculation
- All temporal/spatial metrics

### ✅ Phase System
- Phase detection from position
- Phase event queue
- Event emission and consumption

---

## Success Criteria

Run both test scripts. You should see:

✅ **Both scripts complete without errors**  
✅ **Layers detected in both adaptive and phase-based modes**  
✅ **Phase transitions appear in console**  
✅ **Pre-initiation times are reasonable (0.2-0.5s)**  
✅ **Metrics CSV files created**  
✅ **"All tests PASSED" message**

If all above are true, your phase-aware system is working correctly! 🎉

---

## Files Created by Tests

### test_post_processing_spoofed.py:
- `test_output_with_phase.csv` - Autolog with Phase column added

### test_print_simulation_spoofed.py:
- `test_simulated_peak_force_output.csv` - Adhesion metrics for each layer

**You can inspect these files to verify results!**

---

## Next Steps After Testing

Once tests pass:

1. **Run actual print** - Verify phase transitions appear in real-time
2. **Compare results** - Test metrics vs real print metrics
3. **Try different prints** - Test with various overstep distances
4. **Process old data** - Verify backward compatibility with old autologs

---

## Summary

**Q: Do I need to save more data for testing?**  
**A: NO! Your existing autolog files are perfect.**

**Q: What gets tested?**  
**A: Everything - phase detection, boundary detection, adhesion metrics, real-time simulation.**

**Q: How long does testing take?**  
**A: Simple test: 5 seconds, Comprehensive test: 30 seconds.**

**Q: What if tests fail?**  
**A: Check console output for specific errors, verify CSV format, try different autolog file.**

**Q: Can I test with my own data?**  
**A: Yes! Just point the script to your autolog CSV file.**

---

**Ready to test!** Run the simple test first, then the comprehensive test:

```powershell
python test_post_processing_spoofed.py
python test_print_simulation_spoofed.py
```
