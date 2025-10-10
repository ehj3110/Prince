# How Propagation End is Measured

## Overview
The propagation end detection uses a **reverse-search, second-derivative method** implemented in `support_modules/adhesion_metrics_calculator.py`.

## Algorithm Step-by-Step

### Step 1: Define Search Region
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

## Visual Representation

```
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

## Code Location

**File:** `support_modules/adhesion_metrics_calculator.py`  
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
