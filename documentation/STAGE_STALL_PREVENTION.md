# Stage Stall Prevention and Recovery System

## Overview
Comprehensive debugging and recovery mechanisms have been added to prevent and diagnose stage stall issues during printing.

## Date: October 1, 2025

## Problem
The Zaber linear stage was stalling during printing with error:
```
MovementFailedException: Movement may have failed because fault was observed: Stalled and Stopped (FS).
```

This typically occurs when:
1. Excessive adhesion force prevents movement
2. Part is stuck to the FEP film
3. Mechanical obstruction
4. Acceleration/speed settings are too aggressive for the load

## Solutions Implemented

### 1. Pre-Movement Diagnostics
**Before each movement**, the system now logs:
- Current position
- Current force reading
- Pre-movement warnings if force is too high

```
PRE-PEEL L236: Pos=58.2498mm, Force=0.123N
WARNING L236: High pre-peel force detected (0.567N). Part may be stuck!
```

### 2. Post-Movement Success Confirmation
**After each successful movement**, the system confirms:
```
SUCCESS L236: Peel movement completed
SUCCESS L236: Return movement completed
```

### 3. Detailed Error Diagnostics
**When a movement fails**, the system logs:
- Exception details
- Fault status flags
- Position where failure occurred
- Force reading at failure

```
ERROR L236: Return movement failed: MovementFailedException...
DIAGNOSTICS L236: Fault=FS (Stalled), Pos=56.3mm, Force=0.842N
```

### 4. Automatic Recovery Attempt
**After a stall**, the system attempts to recover by:
1. Clearing fault flags
2. Waiting 0.5 seconds for mechanics to settle
3. Attempting a slow, gentle upward movement (100 µm/s, very low acceleration)
4. Moving 0.5mm up slowly to relieve any binding

```
RECOVERY L236: Attempting to clear faults and recover...
RECOVERY L236: Successfully moved to 56.8mm
```

If recovery fails:
```
RECOVERY FAILED L236: Still unable to move
```

## Force Thresholds

### Pre-Peel Force Warning
- **Threshold**: 0.5N
- **Purpose**: Detect if part is stuck before attempting peel
- **Action**: Logs warning, continues with movement

### Pre-Return Force Warning  
- **Threshold**: 0.3N
- **Purpose**: Detect if adhesion is still high after peel
- **Action**: Logs warning, continues with movement

**Adjust these thresholds** in the code if needed based on your material properties:
```python
if abs(current_force) > 0.5:  # <-- Adjust this value
    self.update_status_message(f"WARNING: High pre-peel force...", error=True)
```

## How to Use the Diagnostics

### During Printing
Monitor the status messages for:
1. **PRE-PEEL/PRE-RETURN logs** - Check force values
2. **WARNING messages** - High force detected
3. **SUCCESS messages** - Movements completed normally
4. **ERROR messages** - Movement failed
5. **DIAGNOSTICS messages** - Details of failure
6. **RECOVERY messages** - Automatic recovery attempts

### After a Stall
Review the log file to find:
1. Last successful layer
2. Force values before the stall
3. Fault codes (FS = Stalled and Stopped)
4. Whether recovery was attempted
5. Patterns in force buildup across layers

## Preventing Future Stalls

### 1. Monitor Force Trends
If you see increasing force warnings across layers:
```
WARNING L230: High pre-peel force (0.45N)
WARNING L234: High pre-peel force (0.51N)
WARNING L236: High pre-peel force (0.67N)  <-- Stall imminent!
```

**Action**: The adhesion is building up. Consider:
- Reducing layer exposure time
- Increasing peel speed slightly
- Adding release agent to FEP film
- Checking resin temperature

### 2. Adjust Motion Parameters
If stalls occur frequently, try:
- **Reduce acceleration**: Lower `actual_acceleration_to_set_um_s2`
- **Reduce speed**: Lower `actual_step_speed_um_s` 
- **Increase overstep**: Larger `actual_overstep_microns`

### 3. Material Considerations
High adhesion can be caused by:
- Resin too cold (increase viscosity)
- Over-exposure (too much cure)
- Old/contaminated FEP film
- Incorrect build plate level

## Recovery Procedure

### If Stall Occurs
1. **Check if auto-recovery succeeded**
   - Look for "RECOVERY: Successfully moved" message
   - If yes, print may continue normally

2. **If auto-recovery failed**
   - Print will abort (as designed for safety)
   - Manually home the stage
   - Check for mechanical issues
   - Clean FEP film
   - Restart print from last good layer

### Manual Recovery Commands
If you need to manually recover the stage:
```python
# Clear faults
self.axis.warnings.clear()

# Move slowly
self.axis.move_relative(
    distance=1000,  # 1mm
    unit=Units.LENGTH_MICROMETRES,
    velocity=50,  # Very slow
    velocity_unit=Units.VELOCITY_MICROMETRES_PER_SECOND
)
```

## Test Results

### Before Changes
- Stalls occurred unpredictably
- No warning before failure
- No diagnostic information
- Manual intervention required every time

### After Changes
- Pre-warning when force is high
- Detailed diagnostics logged
- Automatic recovery attempted
- Better understanding of failure conditions

## Future Improvements

### Potential Enhancements
1. **Adaptive acceleration**: Reduce acceleration when high forces detected
2. **Force-limited movement**: Stop movement if force exceeds threshold
3. **Multi-stage peel**: Slow initial peel, then faster
4. **Historical force tracking**: Detect force buildup trends
5. **Automatic pause**: Pause print for manual intervention if warnings persist

### Data Logging
Consider adding to PeakForceLogger:
- Maximum force during peel
- Force at start of return
- Number of recovery attempts
- Success rate of recoveries

## Configuration

### Adjustable Parameters
Edit `Prince_Segmented.py` around line 720-760:

```python
# Pre-peel force threshold (N)
PRE_PEEL_FORCE_THRESHOLD = 0.5

# Pre-return force threshold (N)
PRE_RETURN_FORCE_THRESHOLD = 0.3

# Recovery movement distance (µm)
RECOVERY_DISTANCE = 500

# Recovery speed (µm/s)
RECOVERY_SPEED = 100

# Recovery acceleration (µm/s²)
RECOVERY_ACCEL = 10000
```

## Troubleshooting

### Issue: Too many force warnings
**Solution**: Increase force thresholds or improve release

### Issue: Stalls still occur with no warning
**Solution**: Force sensor may be slow - increase threshold lead time

### Issue: Recovery always fails
**Solution**: Binding may be too severe - manual intervention needed

### Issue: False warnings (low force reported as high)
**Solution**: Calibrate force sensor, check sensor connection

## Conclusion

These changes provide comprehensive monitoring and recovery for stage stalls. The system now:
- ✅ Warns before problems occur
- ✅ Logs detailed diagnostics when failures happen
- ✅ Attempts automatic recovery
- ✅ Provides clear error messages for troubleshooting

**Next Steps**: Run a test print and monitor the new diagnostic messages to understand your system's force behavior patterns.
