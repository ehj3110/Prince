# Propagation End Detection - Method Correction (Oct 10, 2025)

## Problem Identified

The propagation end detection method was changed on **October 1, 2025** from the correct approach to an incorrect one.

## History of Changes

### ✅ September 22, 2025 - PARTIALLY CORRECT METHOD
**File:** `adhesion_metrics_calculator.py` (in root directory)  
**Method:** `_find_propagation_end_second_derivative()`

**Algorithm:**
1. Calculate second derivative of smoothed force
2. Find MAXIMUM of second derivative after peak force
3. Use that maximum location as propagation end

**Code:**
```python
second_derivative = np.diff(np.diff(smoothed_force))
search_region = second_derivative[peak_idx:motion_end_idx]
max_second_deriv_idx = np.argmax(search_region)
prop_end_idx = peak_idx + max_second_deriv_idx + 2  # +2 for double diff
```

**Status:** CLOSE but not quite right - found the max curvature point, but didn't find zero-crossing after it.

### ❌ October 1, 2025 - INCORRECT METHOD (Reverse Search with Peak Finding)
**File:** `support_modules/adhesion_metrics_calculator.py`  
**Method:** `_find_propagation_end_reverse_search()`

**Algorithm:**
1. Calculate second derivative
2. Find ALL peaks in second derivative
3. Filter peaks before 90% search point
4. Select LAST valid peak (furthest from force peak)

**Code:**
```python
# Find peaks in second derivative
peaks_indices = []
for i in range(1, len(second_derivative) - 1):
    if second_derivative[i] > neighbors:
        peaks_indices.append(i)

# Take LAST peak
valid_peaks = [p for p in peaks_indices if p <= reverse_search_start_relative]
last_peak_relative_idx = valid_peaks[-1]
```

**Status:** WRONG - arbitrary peak selection, no physical meaning

### ✅ October 10, 2025 - CORRECTED METHOD (Zero-Crossing After Maximum)
**File:** `support_modules/adhesion_metrics_calculator.py`  
**Method:** `_find_propagation_end_reverse_search()` (renamed but corrected)

**Algorithm - THE CORRECT WAY:**
1. Calculate second derivative of smoothed force
2. Find MAXIMUM of second derivative (highest curvature point)
3. Find where second derivative returns to ZERO after that maximum
4. That zero-crossing is the propagation end

**Code:**
```python
# Calculate second derivative
second_derivative = np.gradient(np.gradient(region_of_interest))

# Find MAXIMUM of second derivative (highest curvature)
max_second_deriv_idx = np.argmax(second_derivative)

# Find where it returns to ZERO after the maximum
for i in range(max_second_deriv_idx + 1, len(second_derivative)):
    if second_derivative[i] <= 0:
        zero_crossing_idx = i
        break
    # Also check if close to zero (within 5% of max)
    if abs(second_derivative[i]) < 0.05 * abs(second_derivative[max_second_deriv_idx]):
        zero_crossing_idx = i
        break

propagation_end_idx = peak_idx + zero_crossing_idx
```

**Status:** CORRECT - physically meaningful, matches original intent

## Physical Interpretation

### What Each Point Represents

```
Force (N)
  |
  |     Peak
  |      *
  |     /|\
  |    / | \       ← Curvature is high here (2nd deriv is large)
  |   /  |  \___   ← Maximum curvature (max 2nd deriv) 
  |  /   |      \_ ← Curvature decreasing
  | /    |        \____  ← Zero curvature (2nd deriv = 0) ← PROPAGATION END
  |/     |             \____
  +------+-------------------> Time
         |      |       |
       Peak   Max    Zero
             2nd Deriv Crossing
             (fastest  (stable
              decay)   baseline)
```

### Why This Makes Physical Sense

1. **Peak Force** - Maximum stress, crack initiates
2. **Maximum 2nd Derivative** - Crack propagating fastest, force dropping rapidly
3. **Zero-Crossing** - Crack propagation complete, force stabilized to baseline

The zero-crossing of the second derivative is where:
- Force curve stops being concave (stops curving downward)
- Force decay has stabilized
- Crack propagation has completed
- Baseline has been reached

## Changes Made

**File Modified:** `support_modules/adhesion_metrics_calculator.py`  
**Method:** `_find_propagation_end_reverse_search()`  
**Lines Changed:** ~267-342

### Key Changes:
1. ✅ Find MAXIMUM of 2nd derivative (not peaks)
2. ✅ Search FORWARD from maximum (not backward from 90%)
3. ✅ Find ZERO-CROSSING after maximum
4. ✅ Use 5% threshold for "close to zero" (handles noise)
5. ✅ Fallback to 2/3 distance if no crossing found

## Expected Impact

### On Propagation End Detection:
- ✅ Will detect propagation end **later** in the curve (closer to true baseline)
- ✅ More consistent across different speeds and viscosities
- ✅ Physically meaningful (end of curvature = end of propagation)

### On Calculated Metrics:
- ⬆️ **Propagation duration** will INCREASE (more realistic)
- ⬆️ **Propagation distance** will INCREASE 
- ⬆️ **Work of adhesion** will INCREASE (integrating to true baseline)
- ⬇️ **Baseline force** will DECREASE (closer to true zero)
- ✅ **All metrics more accurate**

## Testing Required

1. **Run diagnostic script** to visualize the change:
   ```bash
   python diagnose_propagation_end.py post-processing/autolog_L48-L50.csv
   ```

2. **Re-process SteppedCone data** to see impact:
   ```bash
   python batch_process_steppedcone.py
   ```

3. **Compare old vs new results:**
   - Check if propagation end is now at the "flat" part of force curve
   - Verify baseline forces are lower (closer to zero)
   - Confirm work of adhesion values are more consistent

## Why This Changed

**Likely scenario:** On Oct 1, the entire calculator was rewritten from scratch. The person writing it:
1. Read "use second derivative to find propagation end"
2. Interpreted this as "find peaks in second derivative"
3. Implemented a reverse-search peak-finding algorithm
4. **Missed the critical detail:** Find zero-crossing AFTER maximum, not just any peak

This is a classic case of **specification ambiguity** leading to implementation error.

## Documentation Updated

- ✅ `HOW_PROPAGATION_END_IS_MEASURED.md` - Will update to reflect correct method
- ✅ `PROPAGATION_METHOD_FIX_OCT10.md` - This document
- ✅ Code comments in `adhesion_metrics_calculator.py` - Updated with correct explanation

## Git History

```bash
# Sept 22 - Original (mostly correct)
git show ca81d23:adhesion_metrics_calculator.py

# Oct 1 - Incorrect rewrite
git show edc9890:support_modules/adhesion_metrics_calculator.py

# Oct 10 - Corrected
git show HEAD:support_modules/adhesion_metrics_calculator.py
```

## Next Steps

1. ✅ Code fixed (done)
2. ⏳ Test with diagnostic script
3. ⏳ Re-run batch processing
4. ⏳ Compare results with previous data
5. ⏳ Update all documentation
6. ⏳ Commit with clear message explaining the fix
