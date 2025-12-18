# How Propagation End is Measured

## Overview
<<<<<<< Updated upstream
The propagation end detection uses a **second-derivative 10% threshold method** implemented in `support_modules/adhesion_metrics_calculator.py`.

**Last Updated:** October 16, 2025 - Switched from zero-crossing to 10% threshold method after extensive validation testing.
=======
The propagation end detection uses a **reverse-search, second-derivative method** implemented in `support_modules/adhesion_metrics_calculator.py`.
>>>>>>> Stashed changes

## Algorithm Step-by-Step

### Step 1: Define Search Region
<<<<<<< Updated upstream
The algorithm searches from the peak force to the 80% lifting point (not the full motion end).
```python
search_start = peak_idx          # Start from peak force
search_end = lifting_80pct_idx   # End at 80% of lifting distance
```

### Step 2: Calculate 80% Lifting Point (Position-Based)
The 80% point is determined by **position**, not force or time:
```python
# Find the minimum position (maximum travel distance)
min_pos = min(positions[peak_idx:motion_end_idx])
max_pos = positions[peak_idx]

# Calculate 80% of the lifting distance
target_position = max_pos - 0.8 * (max_pos - min_pos)

# Find where position first reaches this target
lifting_80pct_idx = first index where positions[i] <= target_position
```

This constrains the search region to the active adhesion zone, excluding the tail where force has already returned to baseline.

### Step 3: Calculate Second Derivative
The second derivative is calculated on the **smoothed force data** (already processed with median + Savitzky-Golay filters):
```python
region_of_interest = smoothed_force[peak_idx:lifting_80pct_idx+1]
second_derivative = np.gradient(np.gradient(region_of_interest))
```

### Step 4: Find the Highest Positive Peak
The highest positive peak in the 2nd derivative indicates where the force is decaying **fastest**:
```python
positive_mask = second_derivative > 0
max_second_deriv_idx = argmax(second_derivative[positive_mask])
max_second_deriv_value = second_derivative[max_second_deriv_idx]
```

### Step 5: Calculate 10% Threshold
```python
threshold = max_second_deriv_value * 0.10
```
This threshold represents when the decay rate has diminished to just 10% of its maximum.

### Step 6: Find LAST Point BEFORE Crossing Threshold
This is the critical step - we find the **last point before** the derivative drops below the threshold:
```python
for i in range(max_second_deriv_idx + 1, len(second_derivative)):
    if second_derivative[i] < threshold:
        # Return the PREVIOUS index (last point before crossing)
        threshold_idx = i - 1
        break

propagation_end_idx = peak_idx + threshold_idx
```

**Why the last point BEFORE?** This ensures we capture the full extent of the propagation zone, marking the boundary just before the decay rate becomes negligible.
=======
```python
search_start = peak_idx          # Start from peak force
search_end = motion_end_idx      # End at motion completion
```

### Step 2: Find "Lifting Point" 
The lifting point is where the stage has traveled the maximum distance (minimum position value).
```python
travel_positions = positions[peak_idx:motion_end_idx]
lifting_point_idx = peak_idx + argmin(travel_positions)
```

### Step 3: Define Reverse Search Start Point
Start searching backwards from **90% of the way** to the lifting point.
```python
reverse_search_start_idx = peak_idx + 0.9 * (lifting_point_idx - peak_idx)
```
This helps avoid finding false plateaus at the very end of the motion.

### Step 4: Calculate Second Derivative
The second derivative identifies inflection points (where the curve changes concavity).
```python
region_of_interest = smoothed_force[peak_idx:lifting_point_idx+1]
second_derivative = gradient(gradient(region_of_interest))
```

### Step 5: Find Peaks in Second Derivative
A peak in the 2nd derivative = an inflection point = the "knee" of the force curve.
```python
peaks_indices = []
for i in range(1, len(second_derivative) - 1):
    if second_derivative[i] > neighbors:
        peaks_indices.append(i)
```

### Step 6: Filter Peaks
Only keep peaks that occur before the 90% search point.
```python
valid_peaks = [p for p in peaks_indices if p <= reverse_search_start_relative]
```

### Step 7: Select Peak ⚠️ **CRITICAL CHOICE**
```python
# CURRENT METHOD:
last_peak_relative_idx = valid_peaks[-1]  # Takes LAST peak (closest to 90% point)
propagation_end_idx = peak_idx + last_peak_relative_idx
```

**This is the key decision point!**
>>>>>>> Stashed changes

## Visual Representation

```
<<<<<<< Updated upstream
Force                    2nd Derivative
  |                           |
  |     Peak                  |        Peak (fastest decay)
  |      *                    |         *
  |     /|\                   |        /|\
  |    / | \                  |       / | \
  |   /  |  \___              |      /  |  \_____ 10% threshold
  |  /   |      \____         |     /   |  |    \____
  | /    |           \____    |    /    |  |         \____
  |/     |                \_  |   /     |  |              \_
  +------+-----+----------->  +---+-----+--+--------------->
         |     |                   |     |  |
       Peak  Prop End            Peak  Last Before
             (10% thresh)              Threshold Crossing
                                       ↑
                                   PROPAGATION END
```

## Physical Meaning

1. **Peak Force** - Maximum adhesion occurs
2. **2nd Derivative Peak** - Force decaying fastest (active crack propagation)
3. **10% Threshold** - Decay rate drops to 10% of maximum
4. **Last Point Before Crossing** - Final moment of significant propagation
5. **After Threshold** - Propagation essentially complete, force stabilizing

## Why 10% Threshold Instead of Zero-Crossing?

**Previous Method (Zero-Crossing):**
- Found where 2nd derivative crossed zero after the peak
- Physical meaning: Where decay rate stabilizes to near-zero
- Issue: Gave slightly **late** detection, especially at high speeds (6000 µm/s)

**Current Method (10% Threshold):**
- Finds where 2nd derivative drops below 10% of peak value
- Physical meaning: Where decay rate becomes negligible (< 10% of maximum)
- Advantage: Detects propagation end 0.015-0.033 seconds **earlier**
- Validated across multiple speeds (1000, 3000, 6000 µm/s) and layer ranges

**Validation Results:**
- Tested on Layers 60-65, 365-370, 430-435 from Water_6000 data
- 10% threshold consistently more accurate than zero-crossing
- Captures propagation end without including the tail decay region

## Testing the Algorithm

Use the troubleshooting script to visualize the detection:
```bash
python troubleshoot_propagation_end.py
```

This generates diagnostic plots showing:
1. **Row 1:** Smoothed force data with all markers
2. **Row 2:** First derivative with zero-crossing and 10% threshold comparison
3. **Row 3:** Second derivative with peak, zero-crossing, and 10% threshold markers

Each plot includes:
- Red dashed line: Peak force location
- Cyan dotted line: 80% lifting point (end of search region)
- Green dash-dot line: 2nd derivative peak (fastest decay)
- Purple dashed line: Zero-crossing (old method)
- Magenta dashed line: 10% threshold (current method) ← **PROPAGATION END**
- Magenta dotted line: Horizontal 10% threshold reference
=======
Force
  |
  |     Peak
  |      *
  |     /|\
  |    / | \
  |   /  |  \_____ Propagation ends here (force levels off)
  |  /   |      \____
  | /    |           \____
  |/     |                \____
  +------+-----+-----+----------> Time
         |     |     |
       Peak  First  Last     Lifting
             Inflec Inflec   Point
              (Alt)  (Curr)
```

## Potential Issue: LAST vs FIRST Peak

### Current Behavior (LAST peak)
- Takes the inflection point **furthest** from the peak force
- Closer to the **end** of propagation
- May be detecting where force has **already leveled off**

### Alternative Behavior (FIRST peak)
- Takes the inflection point **closest** to the peak force  
- Closer to the **start** of the force decay
- May better capture where propagation **begins to end**

## Example Comparison

**Scenario:** Force drops from 0.5N at peak to 0.1N baseline, with 3 inflection points

```
Method      | Selected Point | Force at Point | Time from Peak
------------|----------------|----------------|---------------
LAST peak   | 3rd inflection | 0.15N          | 1.2s
FIRST peak  | 1st inflection | 0.42N          | 0.3s
```

**Result:** LAST peak gives longer propagation time and lower baseline force.
>>>>>>> Stashed changes

## Code Location

**File:** `support_modules/adhesion_metrics_calculator.py`  
<<<<<<< Updated upstream
**Method:** `_find_propagation_end_reverse_search()` (Lines 312-407)  
**Critical Lines:** 
- Line 381-390: 10% threshold calculation and search
- Line 384: `threshold = max_second_deriv_value * 0.10`
- Line 389: `threshold_idx = max(0, i - 1)` ← Returns last point BEFORE crossing

## Constrained Search Region

The algorithm uses a **position-based constraint** rather than time-based:

**Why 80% of lifting distance?**
- Captures the active adhesion zone
- Excludes the tail region where force has returned to baseline
- Prevents false detections from noise or stage settling
- Typical region size: 35-40 data points (0.55-0.65 seconds)

**Example (Layer 431 from Water_6000):**
```
Peak force at:        13.607s (index 853)
80% lifting point:    14.196s (index 890)
Constrained region:   37 points (0.589s duration)
2nd deriv peak:       13.847s (0.240s after peak)
10% threshold:        13.911s (0.304s after peak) ← PROPAGATION END
Zero-crossing (old):  13.960s (0.353s after peak) ← 0.049s later
```

## Validation and History

**Development Timeline:**
- **October 1, 2025:** Initial zero-crossing method implemented
- **October 10, 2025:** Fixed boundary detection (was ending 0.54s too early)
- **October 16, 2025:** Switched to 10% threshold method after validation

**Validation Testing:**
- Files tested: autolog_L60-L65, L365-L370, L430-L435 (Water_6000)
- Speeds tested: 1000, 3000, 6000 µm/s
- Result: 10% threshold consistently 0.015-0.033s earlier than zero-crossing
- Visual inspection: Better alignment with end of active propagation zone

**Key Insight:**
The zero-crossing method was detecting where decay had **completely stabilized**, while the 10% threshold detects where decay has **become negligible** - the latter is more physically meaningful for propagation end.

## Future Considerations

The 10% threshold percentage could be adjusted if needed:
- **Lower threshold (e.g., 5%):** Later detection, closer to zero-crossing
- **Higher threshold (e.g., 15%):** Earlier detection, closer to peak

Current 10% value validated across all test speeds and conditions.
=======
**Method:** `_find_propagation_end_reverse_search()`  
**Critical Line:** Line 332

```python
# Line 332 - THE KEY DECISION
last_peak_relative_idx = valid_peaks[-1]  # Current: LAST peak
```

**To try FIRST peak instead:**
```python
# Change line 332 to:
first_peak_relative_idx = valid_peaks[0]  # Alternative: FIRST peak
propagation_end_idx = peak_idx + first_peak_relative_idx
```

## Testing the Algorithm

Use the diagnostic script:
```bash
python diagnose_propagation_end.py post-processing/autolog_L48-L50.csv
```

This will:
1. Show force vs time with current propagation end marked
2. Plot 2nd derivative with all detected peaks
3. Compare CURRENT (last peak) vs ALTERNATIVE (first peak)
4. Print detailed metrics for both methods

## Questions to Answer

1. **Where SHOULD propagation end be?**
   - At the first "knee" after peak? → Use FIRST peak
   - Where force returns to baseline? → Use LAST peak
   - Somewhere in between?

2. **What is physically happening?**
   - Propagation END = crack stops growing
   - This should be where force stabilizes
   - Early knee = crack growth slowing down
   - Late knee = crack fully stopped

3. **What matches your experimental observations?**
   - Does LAST peak match visual inspection of force curves?
   - Or does FIRST peak better align with physical behavior?

## Recommendation

**Action:** Run the diagnostic script on several representative files and visually inspect:
1. Where each method places the propagation end
2. Which makes more physical sense
3. Which gives consistent, repeatable results

Then decide whether to keep current method (LAST peak) or change to FIRST peak.

## History

- **Created:** October 1, 2025 (commit `edc9890`)
- **Last Modified:** October 1, 2025 (NO changes since)
- **File did not exist before October 1, 2025**

If results were correct before Oct 1, the system was using a different calculator or method.
>>>>>>> Stashed changes
