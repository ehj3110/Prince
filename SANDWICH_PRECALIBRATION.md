# Sandwich Pre-Calibration System
## Adaptive Speed Control with Force Derivative Detection

**Date:** October 17, 2025  
**Status:** ✅ Implemented and Ready for Testing

---

## 🎯 Problem Solved

### Old System Issues:
- **Area-Dependent Creep**: Large area parts reached force threshold faster than small area parts
- **Fixed Force Detection**: Single force value couldn't account for varying part sizes
- **No Gap Verification**: Relied on manual gap estimates without validation
- **Constant Speed**: Fixed descent speed regardless of proximity to glass

### New System Benefits:
- **Dynamic Calibration**: Measures actual gap and force derivative threshold at print start
- **Area-Agnostic Detection**: Uses force derivative (dF/dt) which spikes consistently regardless of area
- **Adaptive Speed Control**: Slows down automatically as stage approaches glass (500→250→100 µm/s)
- **Safety Override**: Max force threshold prevents excessive pressure even if derivative detection fails

---

## 📋 System Overview

### Pre-Calibration Routine (Run Once at Print Start)

**Purpose**: Automatically measure the actual gap distance and force derivative threshold for this specific print.

**Process**:
1. **3-Stage Adaptive Descent** (500→250→100 µm/s)
   - First 50% of gap: 500 µm/s
   - 50-75% of gap: 250 µm/s
   - Last 25% of gap: 100 µm/s
   - Acceleration: 1 mm/s² (very gentle)

2. **Force Derivative Detection**
   - Monitors dF/dt continuously during descent
   - Initial threshold: 0.075 N/s
   - Stops when derivative spike indicates glass contact

3. **5-Cycle Oscillation for Averaging**
   - Touch glass, move up 100µm
   - Pause 1 second
   - Move down 100µm to glass (50 µm/s)
   - Record contact position and peak derivative
   - Repeat 5 times

4. **Calculate Averages**
   - Average gap distance from 5-6 contact measurements
   - Average peak derivative from 5 cycles
   - These values used for ALL sandwich steps during print

5. **Return to Start**
   - Move back to starting position (500 µm/s)
   - Pause 5 seconds before beginning print

### Sandwich Routine During Print (Each Layer)

**When Enabled**:
- Runs after each layer's peel/retract cycle
- Uses calibrated gap and derivative values from pre-cal

**Process**:
1. **1-Second Force Settling**
   - Waits for residual retraction forces to dissipate

2. **Adaptive Descent to Glass**
   - Uses 3-stage speed reduction (X → X/2 → X/4)
   - Base speed X from instruction file (default 500 µm/s)
   - Monitors both force derivative AND max force
   - Stops on either:
     - Force derivative exceeds calibrated threshold → Normal contact
     - Absolute force exceeds max_sandwich_force → FORCE OVERRIDE (safety)

3. **Force Override Handling**
   - If max force exceeded:
     - Logs "FORCE OVERRIDE" warning with layer number
     - Immediately moves back up to layer position
     - Skips remaining sandwich touches
   - Prevents excessive pressure on delicate parts

4. **Adaptive Ascent from Glass**
   - Returns using reversed speed profile (slow → medium → fast)
   - For multi-touch: retracts 500µm for next touch
   - For final touch: returns to exact layer position

5. **Multi-Touch Support**
   - Configurable number of touches per layer (default 1)
   - 100ms pause between touches

---

## 🖥️ GUI Controls

### Sandwich Routine Panel

**Location**: Main window, below Auto-Home Control panel

**Checkbox**: ☑ **Enable Pre-Calibration**
- **Checked** (default): Pre-calibration runs at print start, sandwich enabled during print
- **Unchecked**: Both pre-calibration AND sandwich steps are skipped entirely

**Legacy Controls** (for manual sandwich testing only):
- Target Height (mm)
- Est. Glass Gap (mm)
- Contact Force (N)
- Run Sandwich button

**Note**: During printing, these manual controls are **ignored**. All values come from instruction file + pre-calibration.

---

## 📄 Instruction File Format Changes

### Old Format (15 columns):
```
Layer  File  Thickness  Exposure  Intensity  Speed  Overstep  Accel  Pause  Gap  Force  SandSpeed  SandAccel  SandPause  SandTouches
1      img1  50         2.0       255        1000   200       5000   0.5    0.5  0.05   500        5000       0.5        1
```

### New Format (14 columns):
```
Layer  File  Thickness  Exposure  Intensity  Speed  Overstep  Accel  Pause  Gap  MaxForce  SandSpeed  SandTouches  DerivThreshold
1      img1  50         2.0       255        1000   200       5000   0.5    0.5  0.2       500        1            0.075
```

### Column Definitions:

| Column | Name | Unit | Purpose | Default |
|--------|------|------|---------|---------|
| 0 | Layer | # | Layer number | - |
| 1 | File | - | Image filename | - |
| 2 | Thickness | µm | Layer thickness | - |
| 3 | Exposure | s | Exposure time | - |
| 4 | Intensity | 0-255 | DLP power | - |
| 5 | Speed | µm/s | Step/peel speed | - |
| 6 | Overstep | µm | Overstep distance | - |
| 7 | Accel | mm/s² | Movement acceleration | - |
| 8 | Pause | s | Layer pause | - |
| 9 | **Gap** | mm | **Gap estimate for pre-cal** | 0.5 |
| 10 | **MaxForce** | N | **Max safety force limit** | 0.2 |
| 11 | **SandSpeed** | µm/s | **Base sandwich speed** | 500 |
| 12 | **SandTouches** | # | **Number of touches** | 1 |
| 13 | **DerivThreshold** | N/s | **Fallback derivative (unused if pre-cal enabled)** | 0.075 |

### Removed Columns (Commented Out for Rollback):
- ~~Column 10: Force~~ (contact force - replaced by derivative detection)
- ~~Column 12: SandAccel~~ (sandwich acceleration - now fixed at 1 mm/s²)
- ~~Column 13: SandPause~~ (pause after contact - removed)

---

## 🔬 Technical Details

### Force Derivative Calculation

**Method**: Sliding window differentiation
```python
def calculate_force_derivative(force_history, dt=0.02):
    """
    Calculate dF/dt using 5-sample window
    
    Args:
        force_history: List of recent force measurements
        dt: Time between samples (20ms)
    
    Returns:
        Derivative in N/s
    """
    window_size = min(5, len(force_history))
    recent_forces = force_history[-window_size:]
    df = recent_forces[-1] - recent_forces[0]
    time_span = dt * (window_size - 1)
    return df / time_span
```

**Why Derivative?**
- **Area-Independent**: dF/dt spike is consistent across part sizes
- **Contact Sensitivity**: Sharp rise at first touch, even with low absolute force
- **Noise Rejection**: Smoothing over 5 samples (100ms window) filters high-frequency noise

**Typical Values**:
- No contact: 0 to ±0.01 N/s (noise)
- Light touch: 0.05 to 0.15 N/s (derivative spike)
- Full contact: 0.15 to 0.50 N/s (rapid force increase)

### Adaptive Speed Control

**3-Stage Profile**:
```
Position:    Start    50%      75%      100% (Glass)
Speed:       500      500      250      100    µm/s
             └────────┘└───────┘└────────┘
             Fast      Medium   Slow
```

**Implementation**: Multiple `move_absolute()` calls with decreasing velocity
- Zaber stages cannot change velocity mid-movement
- Each segment is a separate move command
- Force monitoring continues across all segments

**Speed Ratios**: Always X → X/2 → X/4
- If base speed = 500 µm/s: 500 → 250 → 100
- If base speed = 1000 µm/s: 1000 → 500 → 250
- Configurable via instruction file column 11

### Acceleration Settings

**Pre-Calibration**: 1.0 mm/s² (very gentle)
- Slow enough to detect contact before momentum carries stage forward
- Tested minimum for Zaber X-LDA series

**Sandwich During Print**: 1.0 mm/s² (same as pre-cal)
- Consistency between calibration and execution
- Safety margin for delicate parts

**Return/Retract**: 5.0 mm/s² (normal)
- Faster acceleration acceptable when moving away from glass

---

## 🧪 Testing Checklist

### Pre-Calibration Validation

- [ ] **Checkbox Control**
  - Verify checkbox appears in Sandwich panel
  - Check that unchecking disables both pre-cal and sandwich

- [ ] **Pre-Cal Execution**
  - Run with checkbox enabled
  - Verify 3-stage speed reduction (watch stage slow down)
  - Check status messages show all 5 oscillations
  - Confirm 5-second pause before print starts

- [ ] **Gap Measurement**
  - Compare measured gap to manual measurement
  - Should be within ±0.05mm
  - Check that value is logged in status window

- [ ] **Derivative Threshold**
  - Verify average derivative is calculated
  - Typical range: 0.05 - 0.20 N/s
  - Check consistency across 5 cycles (std dev < 0.05 N/s)

### Sandwich Routine Validation

- [ ] **Small Area Part** (e.g., 5mm diameter cylinder)
  - Verify sandwich contacts glass each layer
  - Check derivative detection works
  - Confirm no force overrides triggered

- [ ] **Large Area Part** (e.g., 100mm² stepped cone)
  - Verify sandwich still works despite higher forces
  - Check that derivative detection prevents creep
  - Monitor for force overrides (should be rare)

- [ ] **Adaptive Speed**
  - Visually confirm stage slows as it approaches glass
  - Listen for motor speed changes (3 distinct stages)
  - Verify smooth transitions between speeds

- [ ] **Multi-Touch**
  - Set SandTouches = 3 in instruction file
  - Verify 3 touches per layer
  - Check 100ms pause between touches
  - Confirm final position matches layer height

- [ ] **Force Override**
  - Intentionally set MaxForce very low (e.g., 0.05 N)
  - Verify "FORCE OVERRIDE" message appears
  - Check that stage immediately retracts
  - Confirm remaining touches are skipped

### Integration Testing

- [ ] **Full Print Test**
  - Run complete print with pre-cal enabled
  - Monitor status messages for errors
  - Check autolog files for phase annotation
  - Verify print completes without crashes

- [ ] **Without Pre-Cal**
  - Uncheck pre-cal checkbox
  - Verify print proceeds normally
  - Confirm no sandwich steps occur
  - Check that status shows "Sandwich skipped"

- [ ] **Instruction File Compatibility**
  - Test with old 15-column format (should use defaults)
  - Test with new 14-column format
  - Verify backward compatibility

---

## 📊 Expected Behavior

### Successful Pre-Calibration Output:
```
=== STARTING PRE-CALIBRATION ROUTINE ===
Pre-cal: Starting at 10.000mm, searching to 10.500mm
Pre-cal: Using derivative threshold 0.0750 N/s
Pre-cal: Phase 1 - Initial descent with adaptive speed...
Pre-cal: First contact at 10.487mm (gap: 0.487mm)
Pre-cal: Phase 2 - Performing 5 oscillations for averaging...
Pre-cal: Oscillation 1/5 - Moving up to 10.387mm
Pre-cal: Pausing 1s before descent 1/5...
Pre-cal: Oscillation 1/5 - Moving down to find contact...
Pre-cal: Oscillation 1/5 - Contact at 10.488mm, peak dF/dt=0.0823 N/s
[... 4 more oscillations ...]
Pre-cal: RESULTS - Avg gap: 0.489mm, Avg peak dF/dt: 0.0817 N/s
Pre-cal: Contact measurements: 6 samples
Pre-cal: Returning to start position 10.000mm...
Pre-cal: Pausing 5 seconds before starting print...
=== PRE-CALIBRATION COMPLETE ===
```

### Successful Sandwich Output (Layer 25):
```
L25: Waiting 1s for forces to settle before sandwich...
L25: Starting ADAPTIVE sandwich (Gap:0.489mm, dF/dt:0.0817N/s, MaxF:0.2N, Speed:500µm/s, Touches:1)
L25: Touch 1/1 - Adaptive descent to glass
L25: Touch 1/1 - Contact at 9.011mm (Gap:0.491mm, derivative trigger)
L25: Adaptive ascent to layer position 8.520mm
L25: Sandwich complete, position 8.520mm
```

### Force Override Output:
```
L42: Touch 1/3 - Adaptive descent to glass
L42: Touch 1/3 - FORCE OVERRIDE at 6.234mm (Gap:0.494mm) - ABORTING TOUCH
L42: Sandwich complete, position 5.740mm
```

---

## 🔄 Rollback Plan

If the new system causes issues, you can revert to the old system:

### Code Rollback:
1. **libs.py**: Uncomment old parameter lists, comment out new ones
2. **Prince_Segmented.py**: 
   - Restore old sandwich code (search for "COMMENTED OUT OLD PARAMETERS")
   - Remove pre-calibration call in `print_t()`
   - Remove helper methods: `calculate_force_derivative()`, `adaptive_speed_move()`, `perform_precalibration()`

### Instruction File Rollback:
- Revert to 15-column format
- Restore columns: Force (10), SandAccel (12), SandPause (13)

### Quick Test of Old System:
- Uncheck "Enable Pre-Calibration" checkbox
- Old sandwich code is preserved but not executed
- System will skip all sandwich steps

---

## 🛠️ Troubleshooting

### Pre-Calibration Fails to Detect Contact

**Symptoms**: "No contact detected" message

**Possible Causes**:
- Force gauge not calibrated → **Solution**: Calibrate from Sensor Panel
- Gap estimate too small → **Solution**: Increase column 9 (Gap) in instruction file
- Derivative threshold too high → **Solution**: Lower to 0.050 N/s

### Sandwich Triggers Force Override Every Layer

**Symptoms**: "FORCE OVERRIDE" messages frequently

**Possible Causes**:
- MaxForce set too low → **Solution**: Increase column 10 to 0.3 or 0.4 N
- Part area too large → **Solution**: Use pre-cal to get accurate derivative threshold
- Base speed too fast → **Solution**: Reduce column 11 (SandSpeed) to 300 µm/s

### Stage Moves Too Slowly During Sandwich

**Symptoms**: Sandwich takes > 30 seconds per layer

**Possible Causes**:
- Base speed too low → **Solution**: Increase column 11 to 800-1000 µm/s
- Gap too large → **Solution**: Verify actual gap with calipers, update column 9
- Multiple touches configured → **Solution**: Reduce column 12 to 1 touch

### Pre-Calibration Measurements Inconsistent

**Symptoms**: Contact positions vary by > 0.1mm

**Possible Causes**:
- Force settling time insufficient → **Solution**: Add `time.sleep(2.0)` after each oscillation
- Derivative threshold too sensitive → **Solution**: Increase to 0.100 N/s
- Mechanical play in stage → **Solution**: Check coupling tightness, re-home stage

---

## 📝 Notes for Future Development

### Potential Enhancements:
1. **Periodic Re-Calibration**: Run pre-cal every N layers to account for thermal drift
2. **Adaptive Threshold**: Adjust derivative threshold based on recent sandwich measurements
3. **Speed Optimization**: Use position encoder feedback for smoother speed transitions
4. **Multi-Point Calibration**: Average gap measurements from multiple XY positions
5. **Force History Logging**: Save force curves from each sandwich for post-analysis

### Known Limitations:
- Pre-calibration adds ~60 seconds to print start time
- Assumes glass position is constant across entire print area
- Force derivative requires stable force gauge readings (calibration critical)
- Maximum base speed limited by Zaber acceleration constraints

---

## 📚 Related Documentation

- `SANDWICH_IMPLEMENTATION_SUMMARY.md` - Original sandwich implementation details
- `SANDWICH_INTEGRATION_GUIDE.md` - Integration with main printing loop
- `SANDWICH_MULTITOUCH_ENHANCEMENT.md` - Multi-touch feature specification

---

**Last Updated**: October 17, 2025  
**Implementation Status**: ✅ Code Complete, Ready for Testing  
**Testing Status**: ⏳ Awaiting User Testing
