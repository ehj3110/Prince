# Sandwich Speed Floor Modifications - November 29, 2025

## Problem Statement
High Stefan adhesion forces during initial lift from glass window were causing issues with the sandwich step, particularly when the part is pressed against the window and then needs to peel away at the start of the ascent.

## Changes Made

### 1. General Speed Floor Reduced
**Before:** 50 µm/s  
**After:** 30 µm/s

**Location:** `Prince_Segmented.py` line ~1206  
**Variable:** `min_speed_floor = 30.0`

This provides more control during the descent phase when approaching the glass, allowing slower, more controlled movements.

### 2. Extra-Low Speed Floor for Initial Lift
**New:** 15 µm/s  
**Purpose:** Specifically for the initial lifting segment (0-33% of ascent) where Stefan adhesion is strongest

**Location:** `Prince_Segmented.py` line ~1207  
**Variable:** `min_speed_floor_lifting = 15.0`

This ultra-slow speed applies ONLY to the first segment of the ascent (when peeling away from glass), where adhesion forces are highest.

### 3. Applied Speed Floors to Ascent Segments
**Location:** `Prince_Segmented.py` line ~1377  
**Code Added:**
```python
# Apply extra-low floor to initial lifting segment (Stefan adhesion zone)
ascent_tier3 = max(min_speed_floor_lifting, ascent_tier3)  # 15 µm/s min for 0-33%
ascent_tier2 = max(min_speed_floor, ascent_tier2)          # 30 µm/s min for 33-50%
ascent_tier1 = max(min_speed_floor, ascent_tier1)          # 30 µm/s min for 50-100%
```

### 4. Updated Safety Clamp
**Before:** Clamped adaptive speed to 50-2000 µm/s  
**After:** Clamped adaptive speed to 30-2000 µm/s

**Location:** `Prince_Segmented.py` line ~1168  
Ensures adaptive speed adjustments respect the new lower floor.

---

## Technical Details

### Speed Profile During Sandwich

#### Descent (toward glass):
1. **0-33% of gap:** Base speed → min 30 µm/s
2. **33-67% of gap:** Base / 3 → min 30 µm/s
3. **67-100% of gap:** Base / 9 → min 30 µm/s

#### Ascent (away from glass):
1. **0-33% of ascent (CRITICAL):** Base / 9 → **min 15 µm/s** ← NEW ULTRA-LOW FLOOR
2. **33-50% of ascent:** Base / 3 → min 30 µm/s
3. **50-100% of ascent:** Base speed → min 30 µm/s

### Why Different Floors?

**Stefan Adhesion** is strongest in the first moments of separation from the glass. By allowing the system to move as slowly as **15 µm/s** during this initial lift:
- Reduces peak peel forces
- Allows thin fluid films to break more gradually
- Prevents sudden rupture that could damage delicate parts
- Still maintains reasonable speed (only affects first ~33% of a typically 0.5mm gap = 0.166mm at 15µm/s = 11 seconds)

**General floor at 30 µm/s** provides:
- Better control during approach to glass
- More responsive adaptive behavior
- Still fast enough to avoid excessive cycle times

---

## Example Speed Calculation

**Starting Condition:**
- User-set sandwich speed: 500 µm/s
- Adaptive sandwich enabled
- Gap distance: 0.5mm

**Descent Speeds:**
- Tier 1 (0-33%): 500 µm/s
- Tier 2 (33-67%): 166 µm/s
- Tier 3 (67-100%): 55 µm/s → stays above 30 µm/s floor ✓

**If speed adapts down to 270 µm/s:**
- New Tier 3: 270 / 9 = 30 µm/s → **exactly at floor**

**Ascent Speeds (with adaptation):**
- Segment 1 (0-33%): 30 µm/s → **clamped to 15 µm/s floor** ← CRITICAL ZONE
- Segment 2 (33-50%): 90 µm/s → stays above 30 µm/s floor ✓
- Segment 3 (50-100%): 270 µm/s → stays above 30 µm/s floor ✓

---

## Timing Impact

**For a 0.5mm gap with base speed 500 µm/s:**

### Without Lower Floors (old: 50 µm/s minimum):
- Ascent segment 1: 0.166mm @ 55 µm/s = **3.0 seconds**

### With New Lower Floors (30/15 µm/s):
- Ascent segment 1: 0.166mm @ 15 µm/s = **11.1 seconds** (+8.1 sec)
- Other segments: Unchanged

**Total sandwich time increase:** ~8 seconds per layer (only if speed adapts down to floor)

**Trade-off:** Extra 8 seconds vs. potential part damage from high peel forces

---

## Recommended Parameter Adjustments

### If Still Having Stefan Adhesion Issues:

1. **Further lower lifting floor:**
   ```python
   min_speed_floor_lifting = 10.0  # Even slower initial lift
   ```

2. **Extend slow zone:**
   Modify ascent waypoints to use tier3 speed for longer:
   ```python
   waypoint_50pct_up_um  # Change to 40% or 33%
   ```

3. **Reduce base sandwich speed:**
   In GUI or instruction file, use 300 µm/s instead of 500 µm/s

### If Sandwich Takes Too Long:

1. **Raise lifting floor:**
   ```python
   min_speed_floor_lifting = 20.0  # Faster initial lift
   ```

2. **Raise general floor:**
   ```python
   min_speed_floor = 40.0  # Faster descent
   ```

3. **Increase base sandwich speed:**
   Use 800-1000 µm/s in instruction file (if part can handle it)

---

## Files Modified

### `Prince_Segmented.py`
**Line ~1168:** Updated adaptive speed clamp (50 → 30 µm/s)  
**Line ~1206:** Lowered general speed floor (50 → 30 µm/s)  
**Line ~1207:** Added lifting-specific speed floor (15 µm/s) **[NEW]**  
**Line ~1377:** Applied speed floors to ascent tiers **[NEW]**

---

## Testing Recommendations

1. **Test with current parts:** Monitor status messages for actual speeds used
2. **Check force gauge data:** Look at peak forces during initial lift
3. **Adjust floors if needed:** Balance between speed and force control
4. **Document results:** Note which floor values work best for your materials

---

## Rollback Instructions

If you need to revert to the old behavior:

1. Change `min_speed_floor = 30.0` back to `50.0`
2. Remove or comment out `min_speed_floor_lifting = 15.0`
3. Remove the three lines applying speed floors to ascent tiers:
   ```python
   # ascent_tier3 = max(min_speed_floor_lifting, ascent_tier3)
   # ascent_tier2 = max(min_speed_floor, ascent_tier2)
   # ascent_tier1 = max(min_speed_floor, ascent_tier1)
   ```
4. Change adaptive clamp back to `max(50.0, min(2000.0, ...))`

---

**Status:** ✅ Implemented and ready for testing  
**Impact:** Slower initial lift from glass, lower overall speed floor  
**Trade-off:** +8 sec/layer vs. reduced Stefan adhesion forces
