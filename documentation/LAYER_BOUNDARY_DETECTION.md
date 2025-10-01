# Layer Boundary Detection Logic

## Overview
This document describes the algorithm used for detecting layer boundaries in the printing process data. The detection is based on stage motion patterns and uses position data to identify distinct phases of each layer cycle.

## Layer Definition
A layer is defined as a complete cycle of printing operations, starting from a stable position and ending when the stage returns to stability after retraction. The key characteristic of our layer boundary detection is that **each layer starts when the stage has stabilized after the previous layer's retraction**.

## Stage Motion Pattern
Each layer follows this distinct motion pattern:

1. **Layer Start**
   - Stage is stable at high position (~66mm)
   - This is the ready position for starting a new layer

2. **Lifting Phase (DOWN)**
   - Stage moves downward from ~66mm to ~60mm
   - Detected by continuous downward motion
   - Ends when stage stops moving down

3. **Retraction Phase (UP)**
   - Stage moves upward from ~60mm back to ~66mm
   - Detected by continuous upward motion
   - Ends when stage reaches stable position

4. **Layer End/Next Layer Start**
   - Stage stabilizes at high position (~66mm)
   - This stability point marks both the end of current layer and start of next layer

## Detection Parameters
The algorithm uses the following parameters for reliable motion detection:

```python
sampling_rate = 50  # Hz (50 samples per second)
window_size = 5     # Points to average for stability check
pos_threshold = 0.03  # mm threshold for movement detection
min_stable_points = int(0.2 * sampling_rate)  # Minimum points for stability confirmation
```

## Movement Detection Logic
Movement is detected using a threshold-based approach:
```python
def detect_movement(curr_pos, last_pos):
    diff = curr_pos - last_pos
    if abs(diff) < pos_threshold/2:
        return 0  # stable
    return 1 if diff > 0 else -1  # 1 for increasing, -1 for decreasing
```

## Layer Boundary Algorithm
1. **First Layer Start**
   - Set at beginning of file (after initial averaging window)
   - Wait for first lift motion

2. **Subsequent Layer Detection**
   - Track downward motion (lifting phase)
   - Follow through until motion stops
   - Wait for upward motion (retraction phase)
   - Wait for stability period (min_stable_points)
   - Mark stable point as next layer start

## Important Notes
1. Stage direction is inverted in our data:
   - Lifting motion = Stage position DECREASES
   - Retraction motion = Stage position INCREASES

2. Layer boundaries are marked at stability points:
   - Each boundary point represents both the end of one layer and start of next
   - Stage should be at high position (~66mm) at boundaries

3. Stability Requirements:
   - Position change less than pos_threshold/2
   - Must maintain stability for min_stable_points consecutive readings

## Example Position Values
Typical position values at key points:
- Layer Start/End: ~66.1-66.2mm
- After Lifting: ~60.1-60.2mm
- After Retraction: ~66.0-66.1mm

## Implementation Success Criteria
The algorithm successfully identifies layer boundaries when:
1. It correctly identifies the start of first layer
2. It captures all layer transitions
3. Each layer boundary corresponds to a stable stage position at the upper position
4. Layer timings align with force peaks and stage motion patterns