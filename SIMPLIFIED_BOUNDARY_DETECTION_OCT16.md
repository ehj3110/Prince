# Simplified Boundary Detection - Using Known Lift Distance

**Date:** October 16, 2025  
**Status:** ✅ IMPLEMENTED & TESTED

## Problem Summary

The previous boundary detection algorithm tried to classify motions by direction (DOWN=lift, UP=retract), which:
- Failed on sandwich data (direction labels were backwards)
- Required complex special cases for different data types
- Included pause/exposure data incorrectly
- Produced incorrect peak forces (0.01N instead of 0.3-0.5N)

## New Simplified Approach

**Key Insight from User:**
> "For these files, our lift should be 6mm, and the MAX sandwich step is 1mm. What I recommend that you do is to instead start by finding the stage data that corresponds to a lift and retraction of the distance outlined in the instructions, and segment that data into it's respective parts, and then go no further trying to segment the data for the remaining part."

### Implementation

The adhesion test uses a **known 6mm lift distance** from the instruction file. Instead of trying to classify motion directions:

1. **Find all ~6mm motions** (5.5-6.5mm tolerance)
2. **Pair them sequentially**: motion 1+2, motion 3+4, motion 5+6, etc.
3. **Ignore everything else** (sandwich touches <1mm, pauses, adjustments)

This works for **both standard and sandwich data** without special cases.

### Code Changes

**File:** `post-processing/RawData_Processor.py`

**Before:** 
- Detected motion direction (UP/DOWN)
- Special sandwich mode detection
- Complex pairing logic with direction checks
- ~60 lines of if/else branching

**After:**
- Find all ~6mm movements (direction-agnostic)
- Simple sequential pairing: `for i in range(0, len(motions)-1, 2)`
- ~30 lines total

```python
# Parameters from instruction file
EXPECTED_LIFT_DISTANCE = 6.0  # mm
DISTANCE_TOLERANCE = 0.5      # Allow 5.5-6.5mm
MIN_DISTANCE = EXPECTED_LIFT_DISTANCE - DISTANCE_TOLERANCE
MAX_DISTANCE = EXPECTED_LIFT_DISTANCE + DISTANCE_TOLERANCE

# Find all ~6mm motions
adhesion_motions = []
i = 10  # Skip initial noise
while i < len(position_data) - 100:
    start_pos = np.mean(position_data[i:i+window_size])
    
    for j in range(i + 50, min(i + 1000, len(position_data) - window_size), 10):
        end_pos = np.mean(position_data[j:j+window_size])
        distance = abs(end_pos - start_pos)
        
        # Check if this is a ~6mm adhesion test motion
        if MIN_DISTANCE <= distance <= MAX_DISTANCE:
            actual_end = self._find_motion_end(j, position_data)
            actual_distance = abs(position_data[actual_end] - position_data[i])
            
            if MIN_DISTANCE <= actual_distance <= MAX_DISTANCE:
                adhesion_motions.append((i, actual_end, actual_distance))
                i = actual_end + 10
                break
    else:
        i += 50

# Pair motions sequentially
boundaries = []
for i in range(0, len(adhesion_motions) - 1, 2):
    lift_motion = adhesion_motions[i]
    retract_motion = adhesion_motions[i + 1]
    
    boundaries.append({
        'lifting': (lift_motion[0], lift_motion[1]),
        'retraction': (retract_motion[0], retract_motion[1]),
        'sandwich': (lift_motion[0], lift_motion[0]),  # No separate sandwich
        'full': (lift_motion[0], retract_motion[1])
    })
```

## Test Results

### Sandwich Data (L335-L340.csv)

**Before:**
```
Found 12 large motions
Detected 5 layers (should be 6)
Peak forces: 0.0111N (completely wrong)
Problem: Including pause/exposure data
```

**After:**
```
Found 12 ~6mm motions
Detected 6 layers ✓
Peak forces: 0.45-0.57N ✓
All motions within 5.5-6.5mm range ✓
```

### Standard Data (L48-L50.csv)

**Before:**
```
Detected 3 layers ✓
Peak forces: ~0.24N ✓
Already working for standard data
```

**After:**
```
Detected 3 layers ✓
Peak forces: 0.24-0.26N ✓
Still works correctly ✓
All motions 5.98-6.05mm ✓
```

## Benefits

1. **Simpler Code:** 50% reduction in algorithm complexity
2. **No Special Cases:** Same logic for all data types
3. **More Robust:** Based on physical measurement (6mm lift), not direction heuristics
4. **Self-Documenting:** Distance threshold from instruction file
5. **Automatic Filtering:** Anything <5.5mm or >6.5mm is ignored (sandwich touches, pauses, etc.)

## Configuration

The algorithm can be adjusted via instruction file parameters:
- `Step Speed`: Affects how fast stage moves (doesn't affect 6mm detection)
- `Overstep Distance`: Total lift distance (currently 6mm)
- Sandwich step: <1mm (automatically filtered out by 5.5mm minimum)

## Next Steps

- ✅ Test on sandwich data - COMPLETE
- ✅ Test on standard data - COMPLETE
- ⏳ Re-run batch processing with new algorithm
- ⏳ Verify all Water_Sandwich datasets process correctly
- ⏳ Update documentation for batch processing

## Files Modified

- `post-processing/RawData_Processor.py` - Main algorithm update
- Created test scripts:
  - `check_sandwich_boundaries.py` - Test on sandwich data
  - `check_standard_boundaries.py` - Test on standard data

## Related Issues

This fix resolves:
1. **Sandwich data including pause/exposure:** Now excluded (not ~6mm)
2. **Incorrect layer detection:** Now finds all layers correctly
3. **Wrong peak forces in sandwich data:** Now realistic (0.45-0.57N)
4. **Complex special case logic:** Eliminated entirely
