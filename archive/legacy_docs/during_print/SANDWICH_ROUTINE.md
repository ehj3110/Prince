# Sandwich Routine - Glass Contact Safety System

## Overview
The Sandwich Routine is a safety mechanism for 3D printing operations that prevents the printing stage from punching through the glass window located below the printing window. It performs a controlled downward movement until glass contact is detected via force sensing, then retracts to the proper layer height.

## Purpose
During layer-by-layer printing, the stage needs to retract one layer height above the previous layer. In some cases, it's desirable to push slightly past this point (toward the glass window) and then retract back up to create a "sandwich" effect. However, the glass window position can vary, making it dangerous to use fixed distances. The Sandwich Routine solves this by using real-time force sensing to detect glass contact.

## Technical Implementation

### Module Location
- **File**: `support_modules/SandwichRoutine.py`
- **Class**: `SandwichRoutine`
- **Helper Function**: `perform_sandwich_step_blocking()`

### Key Features
1. **Force-Based Contact Detection**: Monitors force gauge in real-time while moving downward
2. **Immediate Stop**: Halts motion as soon as contact force threshold is reached
3. **Safety Limits**: Won't travel more than 0.5mm beyond estimated glass gap
4. **Adaptive Learning**: Records actual glass gap for future reference
5. **Configurable Parameters**: Adjustable speeds and thresholds

### Algorithm Overview

```
┌─────────────────────────────────────────────┐
│ 1. Validate Force Gauge                     │
│    - Check calibration status               │
│    - Get baseline force reading             │
└─────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│ 2. Calculate Search Range                   │
│    - Target: target_layer_height            │
│    - Estimate: + estimated_glass_gap        │
│    - Max: + estimated_glass_gap + 0.5mm     │
└─────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│ 3. Phase 1: Approach Glass                  │
│    - Move down at 0.5 mm/s (default)        │
│    - Monitor force every 20ms               │
│    - Stop when: force ≤ threshold           │
│    - Record contact position                │
└─────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│ 4. Phase 2: Retract to Target               │
│    - Move up at 1.0 mm/s (default)          │
│    - Final position: target_layer_height    │
└─────────────────────────────────────────────┘
```

## Usage Examples

### Basic Usage (Blocking)
```python
from SandwichRoutine import perform_sandwich_step_blocking

# Perform sandwich step and wait for completion
success, message, actual_gap = perform_sandwich_step_blocking(
    zaber_axis=stage_axis,
    force_gauge_manager=force_gauge,
    target_layer_height=-5.0,        # Final position (mm)
    estimated_glass_gap=1.0,         # Estimated gap below target (mm)
    contact_force_threshold=-0.05,   # Force to detect contact (N)
    status_callback=print,           # Optional status updates
    timeout=30                       # Max time (seconds)
)

if success:
    print(f"Success! Glass was {actual_gap:.3f} mm below target")
else:
    print(f"Failed: {message}")
```

### Advanced Usage (Non-Blocking)
```python
from SandwichRoutine import SandwichRoutine

def status_update(message):
    print(f"Status: {message}")

def completion_callback(success, message):
    if success:
        print(f"Sandwich complete: {message}")
    else:
        print(f"Sandwich failed: {message}")

# Create sandwich routine
sandwich = SandwichRoutine(
    zaber_axis=stage_axis,
    force_gauge_manager=force_gauge,
    target_layer_height=-5.0,
    estimated_glass_gap=1.0,
    contact_force_threshold=-0.05,
    status_callback=status_update,
    result_callback=completion_callback
)

# Start routine in background thread
sandwich.start()

# Do other work...

# Wait for completion
sandwich.join(timeout=30)

# Access results
if sandwich.glass_contact_position is not None:
    print(f"Glass found at {sandwich.glass_contact_position:.4f} mm")
    print(f"Actual gap: {sandwich.actual_glass_gap:.3f} mm")
```

### Integration with Printing Loop
```python
from SandwichRoutine import perform_sandwich_step_blocking

def print_layer_with_sandwich(layer_number, layer_height_mm):
    """Print a layer with sandwich step after retraction."""
    
    # Calculate target position (one layer height above previous)
    target_position = -(layer_number * layer_height_mm)
    
    # Print the layer...
    expose_layer()
    
    # Normal retraction happens here (built into your system)
    
    # Perform sandwich step
    success, msg, gap = perform_sandwich_step_blocking(
        zaber_axis=stage_axis,
        force_gauge_manager=force_gauge,
        target_layer_height=target_position,
        estimated_glass_gap=1.0,  # Adjust based on your setup
        contact_force_threshold=-0.05,
        status_callback=log_to_terminal
    )
    
    if not success:
        print(f"WARNING: Sandwich step failed: {msg}")
        # Decide whether to continue or abort
    
    return success
```

## Configuration Parameters

### Required Parameters
| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `zaber_axis` | Object | Zaber motor axis instance | - |
| `force_gauge_manager` | Object | ForceGaugeManager instance | - |
| `target_layer_height` | float | Final position in mm (negative is up) | `-5.0` |
| `estimated_glass_gap` | float | Estimated distance to glass in mm | `1.0` |
| `contact_force_threshold` | float | Force threshold for contact (N) | `-0.05` |

### Optional Parameters (Configurable)
| Parameter | Default | Description | Adjust If... |
|-----------|---------|-------------|--------------|
| `approach_speed` | 0.5 mm/s | Speed moving toward glass | Need faster/slower approach |
| `retract_speed` | 1.0 mm/s | Speed retracting upward | Need different retract speed |
| `max_travel_beyond_estimate` | 0.5 mm | Safety limit beyond estimate | Need tighter/looser safety |
| `force_check_interval` | 0.02 s | Time between force readings | Need faster/slower response |

## Safety Considerations

### Built-In Safety Features
1. **Force Validation**: Checks force gauge calibration before starting
2. **Travel Limits**: Won't go more than 0.5mm beyond estimated gap
3. **Immediate Stop**: Stops motion within ~20ms of contact detection
4. **Cancellable**: Can be stopped mid-routine with `.stop()` method
5. **Error Handling**: Comprehensive exception handling and logging

### Best Practices
1. **Calibrate Force Gauge First**: Always ensure force gauge is calibrated
2. **Test Initial Estimate**: Manually measure glass gap before first use
3. **Conservative Threshold**: Use a force threshold that's clearly detectable but won't damage glass
4. **Monitor Initial Runs**: Watch the first few sandwich steps to verify behavior
5. **Update Estimate**: Use `actual_glass_gap` result to refine future estimates

### Warning Signs
⚠️ **Stop and investigate if:**
- Routine consistently fails to find glass
- Actual gap differs significantly from estimate (>0.5mm)
- Force readings are noisy or unstable
- Glass contact feels too forceful

## Comparison with Auto-Home Routine

| Feature | Auto-Home | Sandwich Routine |
|---------|-----------|------------------|
| **Purpose** | Find absolute home position | Contact glass and retract |
| **Direction** | Downward scan | Down then up |
| **Refinement** | Multiple measurements | Single contact |
| **Speed** | Variable (scan + slow) | Fixed speeds |
| **End Position** | At contact | Above contact |
| **Use Case** | Initial setup | During printing |

## Troubleshooting

### Problem: Glass Not Detected
**Symptoms**: Routine reaches safety limit without finding glass

**Possible Causes:**
- Glass is further away than `estimated_glass_gap + 0.5mm`
- Force threshold is too low (force never reaches threshold)
- Force gauge not responding

**Solutions:**
1. Increase `estimated_glass_gap`
2. Adjust `contact_force_threshold` (make it less negative, e.g., -0.03 instead of -0.05)
3. Check force gauge calibration
4. Manually measure actual glass gap

### Problem: Too Much Force at Contact
**Symptoms**: Glass experiences strong impact, force spikes

**Possible Causes:**
- Approach speed too fast
- Force check interval too slow
- Force threshold too aggressive

**Solutions:**
1. Reduce `approach_speed` (e.g., 0.2 mm/s)
2. Decrease `force_check_interval` (e.g., 0.01 s)
3. Adjust threshold to detect contact earlier

### Problem: Inconsistent Results
**Symptoms**: Actual gap varies significantly between runs

**Possible Causes:**
- Stage not settling before measurement
- Force gauge noise
- Thermal expansion/contraction

**Solutions:**
1. Add longer settling time before contact detection
2. Average multiple sandwich steps
3. Ensure stable temperature environment

## Technical Notes

### Coordinate System
- **Negative values**: Upward movement (away from build platform)
- **Positive values**: Downward movement (toward build platform)
- **target_layer_height**: Usually negative (e.g., -5.0 mm)
- **estimated_glass_gap**: Always positive (distance downward)

### Force Sign Convention
- **Negative force**: Compression (pushing against something)
- **Positive force**: Tension (pulling)
- **contact_force_threshold**: Negative value (e.g., -0.05 N)

### Threading Behavior
- Runs in daemon thread (won't block program exit)
- Can be stopped mid-execution with `.stop()`
- Blocking function waits for completion with timeout

## Related Documentation
- **Auto-Home Routine**: See `AutoHomeRoutine.py` for initial position finding
- **Force Gauge Manager**: See `ForceGaugeManager.py` for force measurement
- **Layer Boundary Detection**: See `LAYER_BOUNDARY_DETECTION.md` for print analysis

## Version History
- **v1.0** (October 2025): Initial implementation with force-based glass detection
  - Configurable approach and retract speeds
  - 0.5mm safety limit beyond estimate
  - Real-time force monitoring at 50Hz
  - Blocking and non-blocking operation modes

## Future Enhancements
- [ ] Adaptive force threshold based on baseline noise
- [ ] Multiple contact averaging for improved accuracy
- [ ] Historical gap tracking across print sessions
- [ ] Automatic estimate refinement based on previous contacts
- [ ] Integration with automated layer logging
