# Propagation End Detection - Analysis and Troubleshooting

## Current Status
**Date:** October 10, 2025  
**Concern:** Results seem incorrect for propagation end calculation  
**File:** `support_modules/adhesion_metrics_calculator.py`  
**Last Modified:** October 1, 2025 (commit `edc9890`)  
**Status:** ✅ NO CHANGES since October 1 backup

## File History
```
git log support_modules/adhesion_metrics_calculator.py:
- edc9890 (Oct 1, 2025) - Backup: Prince_Segmented_20250926 — local commit
- File did not exist before Oct 1, 2025
```

## Current Implementation

### Method: `_find_propagation_end_reverse_search()`

**Algorithm:**
1. **Search Region:** From peak to end of motion
2. **Lifting Point:** Find point of maximum travel (minimum position)
3. **Reverse Search Start:** 90% of the way to lifting point
4. **Detection Method:** Find peaks in 2nd derivative (inflection points)
5. **Selection:** Take the LAST peak found (first when searching backwards)
6. **Result:** `propagation_end_idx = peak_idx + last_peak_relative_idx`

### Code Flow
```python
# Step 1: Define search region
search_start_abs = peak_idx
search_end_abs = motion_end_idx (or end of array)

# Step 2: Find lifting point (maximum travel)
travel_positions = positions[peak_idx:search_end_abs]
lifting_point_idx = peak_idx + argmin(travel_positions)

# Step 3: Define reverse search start (90% of way to lifting point)
reverse_search_start_idx = peak_idx + 0.9 * (lifting_point_idx - peak_idx)

# Step 4: Calculate 2nd derivative
region_of_interest = smoothed_force[peak_idx:lifting_point_idx+1]
second_derivative = gradient(gradient(region_of_interest))

# Step 5: Find peaks in 2nd derivative
peaks_indices = [i where second_derivative[i] > neighbors]

# Step 6: Filter peaks before 90% point
valid_peaks = [p for p in peaks_indices if p <= reverse_search_start_relative]

# Step 7: Take LAST valid peak (first when searching backwards)
last_peak_relative_idx = valid_peaks[-1]
propagation_end_idx = peak_idx + last_peak_relative_idx
```

## Potential Issues

### Issue 1: Using LAST peak instead of FIRST
**Current Behavior:**
```python
valid_peaks = [p for p in peaks_indices if p <= reverse_search_start_relative]
last_peak_relative_idx = valid_peaks[-1]  # Takes LAST peak in list
```

**Problem:** This takes the peak CLOSEST to the 90% search point, not the one closest to the peak force.

**What you might want:** The FIRST significant inflection point after the peak (i.e., `valid_peaks[0]` instead of `valid_peaks[-1]`)

### Issue 2: 90% Search Point Too Far
**Current:** Starts searching backwards from 90% of the distance to lifting point  
**Problem:** May miss the actual propagation end if it occurs earlier  
**Consider:** Reducing to 70-80% or removing this constraint

### Issue 3: 2nd Derivative Sensitivity
**Current:** Uses simple peak detection (point > neighbors)  
**Problem:** May find noise or minor inflections  
**Consider:** Adding threshold or prominence requirement

### Issue 4: No Minimum Threshold
**Current:** Accepts any peak in 2nd derivative, no matter how small  
**Problem:** May detect insignificant inflection points  
**Consider:** Adding `min_prominence` parameter

## Diagnostic Questions

To help identify the issue, please check:

1. **What is the current behavior?**
   - Where is the propagation end being detected?
   - Is it too early or too late in the peel curve?

2. **What was the correct behavior before?**
   - When did results become incorrect?
   - Do you have example data showing correct vs incorrect detection?

3. **Visual inspection:**
   - Looking at force vs time plots, where SHOULD propagation end?
   - Is it at the first "knee" after peak force?
   - Is it where force returns to baseline?

## Suggested Fixes

### Fix 1: Use FIRST peak instead of LAST
**Change line 332:**
```python
# OLD:
last_peak_relative_idx = valid_peaks[-1]

# NEW:
first_peak_relative_idx = valid_peaks[0]  # First inflection after peak
propagation_end_idx = peak_idx + first_peak_relative_idx
```

### Fix 2: Remove or reduce 90% constraint
**Change line 324:**
```python
# OLD:
valid_peaks = [p for p in peaks_indices if p <= reverse_search_start_relative]

# NEW (search all peaks):
valid_peaks = peaks_indices
# Then take first one
```

### Fix 3: Add threshold for peak significance
```python
# After calculating second_derivative:
peak_threshold = 0.1 * np.max(np.abs(second_derivative))

# Modified peak finding:
peaks_indices = []
for i in range(1, len(second_derivative) - 1):
    if (second_derivative[i] > second_derivative[i-1] and 
        second_derivative[i] > second_derivative[i+1] and
        second_derivative[i] > peak_threshold):  # Add threshold
        peaks_indices.append(i)
```

### Fix 4: Use baseline-based detection instead
**Alternative approach:** Find where force returns close to baseline
```python
def _find_propagation_end_baseline_method(self, smoothed_force, peak_idx, baseline):
    """
    Find propagation end as point where force returns close to baseline.
    """
    # Search region after peak
    search_region = smoothed_force[peak_idx:]
    
    # Find where force is within 2% of baseline
    threshold = baseline + 0.02  # 0.02 N above baseline
    
    # Find first point that stays below threshold
    for i in range(len(search_region)):
        if search_region[i] <= threshold:
            # Check that it stays low (not just a dip)
            if i + 10 < len(search_region):
                if np.mean(search_region[i:i+10]) <= threshold:
                    return peak_idx + i
    
    # Fallback: use lifting point
    return peak_idx + len(search_region) - 1
```

## Testing Recommendations

1. **Create visualization script** to plot:
   - Force vs time
   - 2nd derivative vs time
   - Detected peaks in 2nd derivative
   - Current propagation end location
   - Lifting point location

2. **Test with known-good data** from before Oct 1

3. **Compare results** between:
   - Current method
   - Modified method (first peak vs last peak)
   - Baseline-based method

## Action Items

1. ⬜ Identify when results became incorrect
2. ⬜ Determine desired behavior (early knee vs late return-to-baseline)
3. ⬜ Create visualization to diagnose current detection
4. ⬜ Test suggested fixes
5. ⬜ Update algorithm based on testing

## Git Recovery

If you want to try an older version:
```bash
# The calculator didn't exist before Oct 1, 2025
# Current version IS the original version

# To experiment with changes:
git checkout -b test-propagation-fix
# Make changes
# Test
# If good: git checkout main; git merge test-propagation-fix
# If bad: git checkout main; git branch -D test-propagation-fix
```

## Notes
- The algorithm has NOT changed since creation (Oct 1)
- If results were correct before, it wasn't using this calculator
- May have been using a different method/file previously
- Check if there's an older calculator in PrintingLogs_Backup or archive/
