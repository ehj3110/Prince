# Baseline Detection Test Results - Layer 111

**Date**: October 2, 2025  
**Test File**: autolog_L110-L114.csv  
**Layer**: 111

## New Detection Method Results

### Method Description
- **Constrained Search**: Limited to first 50% of data between peak force and end of lifting motion
- **Detection Criterion**: First zero-crossing of second derivative after peak force

### Results

**Peak Force Detection**:
- Time: 29.564 s (relative to layer start)
- Force: 0.2078 N
- Index: 737

**Motion End Detection**:
- Index: 869
- Motion duration: 132 indices from peak

**Search Window**:
- Start: Index 737 (peak)
- End: Index 803 (50% of peak-to-motion-end = 66 indices)
- **Constrained region**: 66 data points instead of 132

**Propagation End (New Method)**:
- Time: 29.692 s
- Force: 0.1218 N
- Index: 745
- **Time from peak**: 0.128 s (8 indices after peak)

## Comparison with Issue

### Problem Identified
The original method was finding a false baseline at ~14 seconds due to a random sharp negative force spike, which caused incorrect second derivative behavior.

### New Method Advantages

1. **Avoids False Spikes**: By constraining search to 50% of peak-to-motion-end, we stay close to the peak and avoid random spikes later in the data.

2. **Faster Detection**: Found propagation end only 0.128 seconds after peak force, suggesting crack propagation completed quickly.

3. **Baseline Force**: 0.1218 N is much higher than if we used the spike region (~14s), which would give near-zero or negative baseline.

## Visualization Features

The updated plot (`baseline_test_L111.png`) shows:

1. **Time Window**: Cropped to ±1 second from peak (28.564s - 30.564s)
   - Makes it easier to see the critical region
   - Removes distraction from distant spikes

2. **Markers on All Panels**:
   - **Orange dashed line + circle**: Peak force location
   - **Red dashed line + square**: Propagation end (new method)
   - Both markers appear on all three panels for easy alignment

3. **Three Analysis Panels**:
   - **Top**: Raw and smoothed force
   - **Middle**: First derivative (dF/dt)
   - **Bottom**: Second derivative (d²F/dt²) with zero-crossing visible

## Next Steps

1. **Review Plot**: Check if the red marker (propagation end) appears at a reasonable location
   - Should be where force has stabilized
   - Should be after crack propagation is complete
   - Should avoid random spikes

2. **Test Other Layers**: Try different layers to see if method is consistent
   - Edit `target_layer` in script (e.g., try 110, 112, 113)
   - Check if 50% constraint works across different speeds

3. **Implement in Calculator**: If satisfied with results, update `AdhesionMetricsCalculator._find_propagation_end_reverse_search()` to use this method

4. **Compare Metrics**: Re-run batch processing with new method and compare:
   - Work of adhesion values
   - Baseline force values
   - Propagation duration/distance

## Implementation Code

The new detection logic:

```python
# Find end of lifting motion
motion_end_idx = peak_idx
for i in range(peak_idx + 10, len(position) - 10):
    window = position[i:i+10]
    if np.std(window) < 0.01:  # Stable position
        motion_end_idx = i
        break

# Constrain search to first 50% between peak and motion end
search_end_idx = peak_idx + int((motion_end_idx - peak_idx) * 0.5)

# Find first zero-crossing of second derivative in search window
second_deriv = np.gradient(first_deriv, time)
for i in range(peak_idx + 5, search_end_idx):
    if (second_deriv[i-1] < 0 and second_deriv[i] >= 0) or \
       (second_deriv[i-1] > 0 and second_deriv[i] <= 0):
        prop_end_idx = i
        break
```
