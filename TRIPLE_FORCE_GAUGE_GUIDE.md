# Triple Force Gauge Test System - Quick Start Guide

**Date**: October 31, 2025

## Overview

The new test script (`test_triple_force_gauge.py`) mimics the **SensorDataWindow** and **ForceGaugeManager** workflow from the main printing system, but adapted for three parallel load cells.

## Features

### 🎯 Main Window
- **Large total force readout** - Sum of all three channels
- **Individual channel forces** - Color-coded (Blue, Red, Green)
- **Calibration parameters** - Gain and offset for each channel
- **Two main buttons**:
  - `Calibrate Force Gauges` - Runs the standard two-point calibration
  - `Open Live Plot` - Opens real-time plotting window (enabled after calibration)

### 📊 Live Plot Window
- **Top subplot**: Individual forces from all three channels (overlaid)
- **Bottom subplot**: Total summed force
- **Auto-scaling axes** with 500-point rolling buffer
- **20 Hz update rate** for smooth visualization
- **Color-coded traces**: Ch0=Blue, Ch1=Red, Ch2=Green

## How to Use

### 1. Start the System

```powershell
cd "c:\Users\cheng sun\BoyuanSun\Prince_CurrentWorkingVersion"
python test_triple_force_gauge.py
```

### 2. Wait for Initialization

The system automatically initializes all three channels in the background:
- Status will show "Initializing..." → "All 3 channels attached ✅"
- If any channel fails, status shows "⚠️ Only X/3 channels attached"

### 3. Run Calibration

Click **"Calibrate Force Gauges"** button:

1. **Dialog 1**: "Remove all force from ALL THREE load cells" → Click OK
   - All channels tared to zero

2. **Dialog 2**: "Enter the TOTAL known force in Newtons"
   - This is the TOTAL force across all three cells
   - Example: 9.81 N for 1kg weight (each cell would see ~3.27 N)
   - Example: 4.905 N for 500g weight (each cell would see ~1.64 N)

3. **Dialog 3**: "Apply X.XX N TOTAL force to the system" → Click OK
   - Place weight/force on top so all three cells share the load
   - System automatically calculates each cell's share based on voltage response
   - **Uneven distribution will be reported** (indicates mechanical misalignment)

4. **Final Dialog**: "All three channels calibrated successfully!"
   - Shows force distribution across the three cells
   - Example: "Ch0: 33.2% (3.26N), Ch1: 33.5% (3.29N), Ch2: 33.3% (3.27N)"
   - Ideally all three should be close to 33.3% each

### 4. Monitor Forces

After calibration:
- Main window shows real-time forces (updates at 10 Hz)
- **Total Force** updates as sum of all three
- **Individual channels** show force on each cell

### 5. Open Live Plot

Click **"Open Live Plot"** button (enabled after calibration):
- New window opens with dual subplots
- Apply force to cells and watch the traces
- **Use this to verify load alignment**:
  - If all three cells show similar forces → Good alignment
  - If one cell is much higher/lower → Mechanical misalignment

## What to Look For

### ✅ Good Alignment (Even Force Distribution)
```
Calibration Result:
Ch0: 33.2% (~3.26 N)  →  All three channels
Ch1: 33.5% (~3.29 N)  →  within a few percent
Ch2: 33.3% (~3.27 N)  →  of 33.3% each
```

### ⚠️ Misalignment (Uneven Force Distribution)
```
Calibration Result:
Ch0: 45.2% (~4.43 N)  →  Channel 0 bearing
Ch1: 28.1% (~2.76 N)  →  more load than others
Ch2: 26.7% (~2.62 N)  →  (mechanical tilt)
```

**During live monitoring:**
- All three traces should move together proportionally
- If one channel consistently reads higher → that cell is taking more load
- Check mechanical alignment if distribution is >40% / 30% / 30%

## Calibration Tips

### Recommended Calibration Weights:
- **1 kg** = 9.81 N total (each cell sees ~3.27 N)
- **500 g** = 4.905 N total (each cell sees ~1.64 N)
- **100 g** = 0.981 N total (each cell sees ~0.33 N)

### Best Practices:
1. **Apply force evenly** - Place weight centered so all three cells share equally
2. **Wait for stabilization** - Let readings settle before clicking OK (0.5s built-in delay)
3. **Check distribution** - Calibration result shows if load is evenly distributed
4. **Use enough weight** - Need significant voltage change for accurate calibration
5. **Re-calibrate if needed** - If distribution is very uneven, adjust mechanics and re-calibrate

## Troubleshooting

### "Not all force sensors attached"
- Check USB connection to Phidget Bridge
- Verify bridge is powered
- Check that load cells are connected to ports 0, 1, 2

### "Voltage did not change"
- Weight not heavy enough or not applied
- Check load cell wiring
- Verify cell is properly mounted

### Forces don't sum correctly
- Re-run calibration
- Make sure you used the same weight for all three channels
- Check for mechanical binding in the cell mounts

### One channel always reads zero
- Check wiring on that specific port
- Swap cables to verify if it's the cell or the bridge port
- Re-run calibration

## Integration Next Steps

Once you've verified all three channels work correctly and are aligned:

1. **Create TripleForceGaugeManager class** - Based on this test script
2. **Update SensorDataWindow** - Add option for triple vs single mode
3. **Modify data logging** - Store all three individual forces + sum
4. **Add diagnostics** - Warn if force distribution is uneven
5. **Update GUI** - Show individual channel status

## Notes

- The test system runs independently - doesn't interfere with main printing system
- Can run this anytime to verify sensor health
- Calibration values are only stored in memory (not saved to file)
- Close the window cleanly to properly shut down Phidget connections

---

**Questions?** Check console output for detailed initialization and calibration messages.
