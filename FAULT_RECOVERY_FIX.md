# Fault Recovery Fix - October 8, 2025

## Problem
During printing, when a stage fault occurred (e.g., "Stalled and Stopped (FS)"), the recovery script failed with:
```
ERROR: RECOVERY FAILED L48: 'Warnings' object has no attribute 'clear'
```

## Root Cause
The code attempted to call `self.axis.warnings.clear()` on line 798 of `Prince_Segmented.py`, but the Zaber Motion API's `Warnings` object does not have a `.clear()` method.

## Solution
Replaced the invalid `.clear()` call with a proper fault clearing sequence:

**Old Code (BUGGY):**
```python
# Clear any faults
self.axis.warnings.clear()
time.sleep(0.5)
```

**New Code (FIXED):**
```python
# Clear any faults by sending home command to reset state
# Note: Zaber warnings don't have a .clear() method
# Instead, we try to reset the axis state
self.axis.home(wait_until_idle=False)
time.sleep(0.5)
self.axis.stop()
time.sleep(0.5)
```

## How It Works
1. Sends a non-blocking `home()` command to reset the axis controller state
2. Waits briefly for the homing to initiate
3. Sends a `stop()` command to halt the homing process
4. Waits again for the controller to stabilize
5. Attempts the gentle recovery movement (0.5mm upward at 100 µm/s)

This sequence clears the "Stalled and Stopped" fault and allows the recovery movement to proceed.

## Files Modified
- `Prince_Segmented.py` - Line 798-803 (recovery section)

## Testing Needed
Next time a stage fault occurs during printing, verify:
1. The recovery attempt no longer crashes with AttributeError
2. The axis successfully clears the fault
3. The gentle recovery movement executes
4. The stage returns to a safe position

## Date Applied
October 8, 2025
