# Derivative-Based Sandwich Implementation

**Date:** November 30, 2025  
**Status:** ✅ Implemented and ready for testing

## Overview

Added a new sandwich routine that uses **force derivative (dF/dZ)** to detect window contact instead of absolute force thresholds. This method is more robust because it:

1. **Detects the moment of contact** rather than waiting for force buildup
2. **Auto-scales with part size** using Stefan-Reynolds squeeze flow physics
3. **Self-adjusts for water loss** since it detects contact position changes, not force magnitude

## Physics Background

### Stefan-Reynolds Squeeze Flow Equation

$$F = \frac{3\pi \mu R^4}{2h^3} \cdot v$$

Where:
- $F$ = Squeezing force (N)
- $R$ = Radius of part (m) 
- $h$ = Gap height (m)
- $v$ = Velocity (m/s)

**Key insight:** Force scales with $R^4$, which means it scales with $Area^2$

Therefore: $\frac{dF}{dh} \propto Area^2$

## Implementation Details

### New UI Elements

**Location:** Prince_Segmented.py, Sandwich Frame (row 2)

- ✅ Added checkbox: "Use Derivative-Based Sandwich (Contact Detection)"
- ✅ Mutual exclusion with Adaptive Sandwich checkbox
- ✅ New variables:
  - `self.derivative_contact_threshold` - Calibrated dF/dZ threshold (N/mm)
  - `self.derivative_base_area` - Area used for calibration (mm²)
  - `self.derivative_calibration_speed` - Calibration speed (default 2000 µm/s)

### New Module

**File:** `support_modules/derivative_sandwich.py`

**Functions:**

1. **`calibrate_derivative_contact()`**
   - Runs on first sandwich layer only
   - Moves down at constant speed (2000 µm/s default)
   - Records force vs. position data at 100 Hz
   - Applies Savitzky-Golay filter to smooth noise
   - Calculates spatial derivative dF/dZ
   - Finds maximum derivative (contact point)
   - Returns: threshold (N/mm), contact position (µm), contact force (N)

2. **`derivative_sandwich_descent()`**
   - Scales threshold based on current layer area: `scaled_threshold = base_threshold × (Area_current / Area_base)²`
   - Uses 70% of scaled threshold for detection (safety margin)
   - Monitors dF/dZ in real-time during descent
   - Stops when derivative exceeds threshold
   - Returns: contact position (µm), contact force (N), stopped_early flag

### Integration into Prince_Segmented.py

**Location:** Lines 1181-1276 (approximately)

**Logic Flow:**

```
IF derivative_sandwich enabled:
    IF no calibration data:
        Run calibrate_derivative_contact()
        Store threshold and base area
        Return to layer position
    
    Get current layer area
    Run derivative_sandwich_descent() with area scaling
    
    Ascent (3-tier, same as adaptive):
        0-33%: Slow peel (speed/3)
        33-50%: Medium speed
        Pause at 50%
        50-100%: Fast return (speed×2)
        Final pause at layer height
    
ELSE IF adaptive_sandwich enabled:
    [Existing adaptive code]
    
ELSE:
    [Existing classic code]
```

### Safety Features

1. **Hard force limit:** -2.0 N (absolute safety cutoff)
2. **Detection factor:** 70% of calibrated threshold (prevents false positives)
3. **Fallback:** If calibration fails, disables derivative mode and falls back to classic
4. **Sampling rate:** 100 Hz (10ms intervals) for responsive detection

### Area Scaling Formula

```python
area_ratio = current_area_mm2 / base_area_mm2
scaled_derivative = base_derivative * (area_ratio ** 2)
detection_threshold = scaled_derivative * 0.7  # 70% safety margin
```

**Example:**
- Base area: 10 mm² → calibrated threshold: 0.5 N/mm
- Current area: 100 mm² (10× larger)
- Scaled threshold: 0.5 × (10)² = 50 N/mm
- Detection threshold: 50 × 0.7 = 35 N/mm

## Advantages Over Existing Methods

### vs. Classic Sandwich:
- ✅ No fixed force threshold needed
- ✅ Adapts to water loss automatically
- ✅ More precise contact detection
- ✅ Less over-compression risk

### vs. Adaptive Sandwich:
- ✅ Simpler logic (no multi-tier ramping during descent)
- ✅ Physics-based scaling (not empirical)
- ✅ Single-pass descent (faster)
- ✅ No speed adaptation needed between layers

### Shared Benefits:
- ✅ Uses same 3-tier ascent for gentle peeling
- ✅ Maintains pause functionality
- ✅ Integrates with existing force gauge infrastructure
- ✅ Easy to switch back if issues arise

## Testing Plan

### First Print Test:

1. **Enable derivative sandwich** checkbox
2. **Disable** adaptive sandwich checkbox  
3. Start print as normal
4. **Watch calibration** on first sandwich layer:
   - Should see: "Running derivative calibration"
   - Should take ~2-5 seconds depending on gap
   - Should report: "Calibration complete - Threshold: X.XXX N/mm"
5. **Monitor subsequent layers:**
   - Should see: "Scaled derivative: X.XXX N/mm"
   - Should stop at different positions based on area
   - Larger areas should contact sooner (higher detection threshold)

### Expected Behavior:

**First layer (small area, e.g., 10 mm²):**
```
Derivative-based descent:
  Current area: 10.00 mm²
  Base derivative: 0.500 N/mm
  Scaled derivative: 0.500 N/mm
  Detection threshold (70%): 0.350 N/mm
  Contact detected: dF/dZ = 0.380 N/mm
```

**Later layer (large area, e.g., 100 mm²):**
```
Derivative-based descent:
  Current area: 100.00 mm²
  Base derivative: 0.500 N/mm
  Scaled derivative: 50.000 N/mm
  Detection threshold (70%): 35.000 N/mm
  Contact detected: dF/dZ = 38.500 N/mm
```

### Troubleshooting:

**If detection happens too early:**
- Increase `detection_factor` from 0.7 to 0.8 or 0.9
- Check for force gauge noise

**If detection happens too late (over-compression):**
- Decrease `detection_factor` from 0.7 to 0.5 or 0.6
- Verify calibration completed successfully

**If calibration fails:**
- Check force gauge connection
- Ensure sandwich pre-calibration is enabled
- Verify gap measurement is valid

## Files Modified

1. **Prince_Segmented.py**
   - Lines 244-267: Added derivative sandwich checkbox and variables
   - Lines 2147-2153: Added mode selection callback
   - Lines 1181-1276: Integrated derivative sandwich routine

2. **support_modules/derivative_sandwich.py** (NEW)
   - 285 lines
   - Two main functions for calibration and descent
   - Includes scipy filtering for noise reduction

## Next Steps

1. ✅ Code implemented and syntax-checked
2. ⏭️ Run test print with derivative mode enabled
3. ⏭️ Analyze automated_work_of_adhesion.csv to verify consistent contact detection
4. ⏭️ Compare membrane flatness between methods
5. ⏭️ Fine-tune `detection_factor` if needed (currently 0.7)

## Reverting if Needed

To switch back to adaptive or classic:
1. Uncheck "Use Derivative-Based Sandwich" checkbox
2. Check "Use Adaptive Sandwich" OR leave both unchecked for classic
3. No code changes needed - all three methods coexist

## Configuration Options

Can be tuned in Prince_Segmented.py initialization:

```python
self.derivative_calibration_speed = 2000.0  # µm/s - calibration descent speed
```

Can be tuned in derivative_sandwich.py function calls:

```python
detection_factor=0.7  # 70% of scaled threshold (safety margin)
max_force_N=-2.0      # Safety force limit
sampling_rate_hz=100  # Force sampling rate
```

---

**Author:** Implemented by GitHub Copilot  
**Reviewed by:** Cheng Sun Lab Team  
**Ready for testing:** ✅ Yes
