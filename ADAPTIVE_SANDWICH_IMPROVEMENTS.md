# Adaptive Sandwich Improvements - Nov 10, 2025

## Problem Identified
During testing, the adaptive sandwich routine got stuck in an infinite loop where:
- Force reached ~-0.60N (75% threshold) and triggered adaptive stop
- Force only relaxed to ~-0.59N (~3% change)
- System kept reducing speed by 50% each iteration
- Eventually reached 0 µm/s and never completed sandwich

**Root Cause**: When the stage is already very close to or touching the glass, the force doesn't relax significantly because there's nowhere for it to go. The old logic didn't distinguish between "force not relaxed yet" vs "already at glass."

## Solutions Implemented

### 1. Force Stability Check (Primary Solution)
**Logic**: Check how much the force relaxed after stopping
- If force changes by **>20%**: Material is still relaxing, safe to reduce speed and continue
- If force changes by **<20%**: Already at glass, stop adapting and proceed to ascent

**Example from test**:
- Stop force: -0.626N
- After 3s: -0.506N  
- Change: ~19% → SHOULD continue (but was borderline)
- Stop force: -0.601N
- After 3s: -0.598N
- Change: ~0.5% → AT GLASS, stop adapting!

### 2. Failsafe: Iteration Limit
- Maximum **3 adaptive iterations** per layer
- After 3 adaptations, assume glass contact and proceed to ascent
- Prevents infinite loops even if force stability check fails

### 3. Failsafe: Speed Floor
- Minimum speed: **50 µm/s**
- Won't reduce below this threshold
- If speed would go below 50 µm/s, assume glass contact and proceed

**Note**: Both failsafes are implemented but the force stability check should prevent them from ever triggering.

### 4. Split Pause Feature
**Old behavior**: Single pause at 50% during ascent

**New behavior**:
- **Pause 1/2**: At 50% point during ascent (halfway up from glass)
- **Pause 2/2**: At final layer height (100% position)

**Rationale**: Allows forces to settle both during separation from glass AND after reaching final position before exposure.

## Code Changes

### Initialization (Line ~1067)
```python
adaptive_iteration_count = 0  # Track adaptations
max_adaptive_iterations = 3   # Failsafe limit
min_speed_floor = 50.0         # Failsafe floor (µm/s)
```

### Force Stability Check (Line ~1152)
```python
# Record force at stop
force_at_stop = current_force

# Wait for relaxation...
final_force = ...

# Calculate change percentage
force_change = final_force - force_at_stop
force_change_percent = (force_change / abs(force_at_stop)) * 100.0

# Check if <20% change → already at glass
if abs(force_change_percent) < 20.0:
    reached_glass = True
    break
```

### Failsafe Checks (Line ~1165)
```python
adaptive_iteration_count += 1

if adaptive_iteration_count >= max_adaptive_iterations:
    reached_glass = True
    break

new_speed = current_seg_speed * 0.5
if new_speed < min_speed_floor:
    reached_glass = True
    break
```

### Split Pause (Line ~1257)
```python
# Pause 1/2 at 50%
pause_half = actual_pause / 2.0
time.sleep(pause_half)

# Move to 100%...

# Pause 2/2 at layer height
pause_half = actual_pause / 2.0
time.sleep(pause_half)
```

## Testing Recommendations

1. **Monitor force stability messages**: Look for the "Force stability check" log showing percent change
2. **Watch for "GLASS REACHED" message**: Should appear when <20% force change detected
3. **Verify failsafes don't trigger**: Should never see "3 adaptations reached" or "speed floor reached" messages
4. **Check pause behavior**: Should see two separate pause messages during ascent

## Expected Behavior

**Good adaptive scenario** (force relaxes >20%):
```
ADAPTIVE STOP at -0.65N
Force relaxes to -0.48N (26% change)
Speed reduced, continue approach
```

**Glass contact scenario** (force stable <20%):
```
ADAPTIVE STOP at -0.60N  
Force relaxes to -0.59N (1.7% change)
GLASS REACHED - proceed to ascent
```

## Parameters to Tune (if needed)

- **Force stability threshold**: Currently 20%, can adjust if too sensitive/insensitive
- **Max iterations**: Currently 3, increase if prints legitimately need more adaptations
- **Speed floor**: Currently 50 µm/s, can lower if needed (but risk of timeout issues)
