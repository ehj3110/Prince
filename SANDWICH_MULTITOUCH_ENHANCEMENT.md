# Sandwich Multi-Touch Enhancement

**Date**: October 10, 2025  
**Summary**: Added three new sandwich parameters (acceleration, pause, and number of touches) with multi-touch capability and 500µm retraction between touches.

---

## New Features

### 1. Three New Sandwich Parameters

**GUI Fields Added:**
- **Sandwich Accel (µm/s²)** - Acceleration during sandwich movements (default: 5000 µm/s²)
- **Sandwich Pause (s)** - Pause duration after detecting glass contact (default: 0.5s)
- **Sandwich Touches (#)** - Number of times to touch the glass window (default: 1)

**Field Locations:**
- `t25`: Sandwich Acceleration (column 2, below Est. Glass Gap)
- `t26`: Sandwich Pause (column 3, below Sandwich Speed)
- `t27`: Sandwich Touches (new column 4, top)

### 2. Multi-Touch Sandwich Capability

When **Sandwich Touches** is set to more than 1, the system will:
1. **Touch glass** - Descend until force threshold is reached
2. **Pause** - Hold position for specified pause duration
3. **Retract 500µm** - Move up exactly 500µm from contact position
4. **Repeat** - Perform next touch cycle
5. **Final return** - After last touch, return to target layer position

**Key Behaviors:**
- ✅ Same speed for **descent AND ascent** (uses Sandwich Speed for both directions)
- ✅ Fixed **500µm retraction** between touches
- ✅ Configurable **pause** after each contact
- ✅ Independent **acceleration** control for sandwich movements
- ✅ 100ms pause between touch cycles for system stability

---

## Implementation Details

### Instruction File Format (Updated)

**Previous format:** 12 columns  
**New format:** 15 columns

```
Layer	File	Thickness	Time	Intensity	Step Speed	Overstep Distance	Step Type	Pause	Estimated Gap	Sandwich Force	Sandwich Speed	Sandwich Accel	Sandwich Pause	Sandwich Touches
1	layer1.png	0.05	60	0	1000	500	5	0	0.5	0.05	500	5000	0.5	3
```

**Column Breakdown:**
- **Columns 1-9**: Original print parameters (unchanged)
- **Column 10**: Estimated Gap (mm) - 0 = skip sandwich
- **Column 11**: Sandwich Force (N) - absolute value threshold
- **Column 12**: Sandwich Speed (µm/s) - approach/retraction speed
- **Column 13**: Sandwich Accel (µm/s²) - **NEW** acceleration for sandwich
- **Column 14**: Sandwich Pause (s) - **NEW** pause after contact
- **Column 15**: Sandwich Touches (#) - **NEW** number of touch cycles

### Backward Compatibility

Old 12-column instruction files are automatically supported with these defaults:
- Sandwich Accel: 5000 µm/s²
- Sandwich Pause: 0.5 s
- Sandwich Touches: 1 (single touch, original behavior)

---

## Multi-Touch Logic Flow

```
For each touch (1 to N):
    ├─ Descend at Sandwich Speed with Sandwich Accel
    ├─ Monitor force every 20ms
    ├─ STOP when |force| >= Sandwich Force
    ├─ Log contact position and gap
    ├─ Pause for Sandwich Pause duration
    ├─ If NOT last touch:
    │   ├─ Retract 500µm from contact position
    │   └─ Pause 100ms before next touch
    └─ If LAST touch:
        └─ Return to target layer position
```

### Example: 3-Touch Cycle

**Parameters:**
- Gap: 0.5mm
- Force: 0.05N
- Speed: 500µm/s
- Accel: 5000µm/s²
- Pause: 0.5s
- **Touches: 3**

**Sequence:**
1. **Touch 1:**
   - Descend from 10.0mm → contact at ~10.5mm
   - Pause 0.5s
   - Retract to 10.0mm (500µm up)
   - Pause 100ms

2. **Touch 2:**
   - Descend from 10.0mm → contact at ~10.5mm
   - Pause 0.5s
   - Retract to 10.0mm (500µm up)
   - Pause 100ms

3. **Touch 3 (final):**
   - Descend from 10.0mm → contact at ~10.5mm
   - Pause 0.5s
   - Return to target layer position (e.g., 9.5mm)
   - **Complete!**

---

## Files Modified

### 1. Prince_Segmented.py
**GUI Changes (lines 136-195):**
- Added 3 new label definitions (`lbl25`, `lbl26`, `lbl27`)
- Added 3 new entry fields (`t25`, `t26`, `t27`)
- Adjusted Auto-Home frame position to y=770 (was 730)
- Added new column 4 at x=850 for Sandwich Touches

**simple_txt() Function (lines 1317-1352):**
- Added extraction of `sandwich_accel`, `sandwich_pause`, `sandwich_touches`
- Passes new parameters to `generate_instructions()`

**input_directory() Function (lines 1242-1315):**
- Added `sandwich_accel_list`, `sandwich_pause_list`, `sandwich_touches_list` to unpacking
- Added initialization of new lists in exception handlers

**print_t() Sandwich Routine (lines 910-1065):**
- Added parameter extraction from new lists
- Implemented multi-touch loop with configurable touches
- Added 500µm retraction between touches
- Uses same speed for descent and ascent
- Added pause after contact detection
- Separate acceleration control for sandwich movements

### 2. support_modules/libs.py

**generate_instructions() Signature (line 197):**
```python
def generate_instructions(self, path='', thickness='5', base='60', time='1', intensity='0',
                          step_speed='100', overstep_distance='0.1', step_type='0', pause='0',
                          estimated_gap='0', sandwich_force='0.05', sandwich_speed='500',
                          sandwich_accel='5000', sandwich_pause='0.5', sandwich_touches='1'):
```

**File Header (line 274):**
- Updated to 15 columns

**File Data Line (line 281):**
- Includes all 15 parameters per layer

**set_image_directory() Lists (lines 104-117):**
- Added `sandwich_accel_list`, `sandwich_pause_list`, `sandwich_touches_list`

**Parsing Logic (lines 130-135):**
- Reads columns 12-14 with backward-compatible defaults
- Converts `sandwich_touches` to integer (others remain float)

**Return Statement (lines 158-162):**
- Returns 14-element tuple (was 11-element)

---

## Usage Examples

### Example 1: Single Touch (Default)
```
Est. Glass Gap: 0.5
Sandwich Force: 0.05
Sandwich Speed: 500
Sandwich Accel: 5000
Sandwich Pause: 0.5
Sandwich Touches: 1
```
**Result:** Original behavior - touch once and return

### Example 2: Triple Touch for Better Wetting
```
Est. Glass Gap: 0.5
Sandwich Force: 0.05
Sandwich Speed: 300   (slower for gentler contact)
Sandwich Accel: 3000  (lower acceleration)
Sandwich Pause: 1.0   (longer pause at contact)
Sandwich Touches: 3   (touch 3 times)
```
**Result:** Three gentle touches with 1s pause at each contact, 500µm retraction between touches

### Example 3: Fast Multi-Touch Sampling
```
Est. Glass Gap: 0.3
Sandwich Force: 0.08  (higher threshold)
Sandwich Speed: 800   (faster approach)
Sandwich Accel: 8000  (aggressive acceleration)
Sandwich Pause: 0.2   (brief pause)
Sandwich Touches: 5   (many quick touches)
```
**Result:** Five rapid sampling touches to characterize surface

---

## Status Messages

During multi-touch operation, you'll see:

```
L5: Waiting 1s for forces to settle before sandwich...
L5: Starting sandwich routine (Gap:0.5mm, Force:0.05N, Speed:500um/s, Touches:3)
L5: Touch 1/3 - Searching for glass down to 10.500mm
L5: Touch 1 - Glass contact at 10.512mm (Gap:0.512mm, Force:0.0534N)
L5: Pausing 0.5s after contact...
L5: Retracting 500um for next touch
L5: Touch 2/3 - Searching for glass down to 10.500mm
L5: Touch 2 - Glass contact at 10.509mm (Gap:0.509mm, Force:0.0528N)
L5: Pausing 0.5s after contact...
L5: Retracting 500um for next touch
L5: Touch 3/3 - Searching for glass down to 10.500mm
L5: Touch 3 - Glass contact at 10.511mm (Gap:0.511mm, Force:0.0531N)
L5: Pausing 0.5s after contact...
L5: Returning to layer position 10.000mm
L5: Sandwich complete (3 touches), position 10.000mm
```

---

## Technical Notes

### Speed Consistency
Both descent and ascent use the **same speed** (`actual_sandwich_speed_mm_s`). This ensures:
- Symmetrical motion profiles
- Predictable contact forces
- Consistent timing between touches

### Acceleration Control
Separate `sandwich_accel` parameter allows:
- Independent tuning from main print acceleration
- Gentler approaches for sensitive samples
- Faster sampling for robust materials

### Fixed Retraction Distance
The 500µm retraction is **hard-coded** because:
- Provides consistent spacing between touches
- Prevents accidental re-contact during repositioning
- Small enough to maintain alignment with glass features
- Large enough to ensure clean force reset

### Pause Timing
Two types of pauses:
1. **Sandwich Pause** (configurable): After force threshold reached, allows:
   - Fluid redistribution
   - Stress relaxation
   - Data collection at contact
   
2. **Inter-Touch Pause** (fixed 100ms): Between touch cycles, allows:
   - System state reset
   - Force gauge stabilization
   - Motion controller readiness

---

## Benefits

1. **Research Flexibility**: Test different contact protocols (single vs. multiple touches)
2. **Better Wetting**: Multiple contacts can improve fluid distribution
3. **Surface Characterization**: Repeated touches reveal material consistency
4. **Process Control**: Independent acceleration/pause tuning per layer
5. **Backward Compatible**: Old instruction files work with default values

---

## Next Steps

**To use multi-touch:**
1. Set **Sandwich Touches** to desired number (2-5 typical)
2. Adjust **Sandwich Pause** for your application (longer = more wetting time)
3. Tune **Sandwich Accel** if needed (lower = gentler)
4. Generate instruction file (creates 15-column format)
5. Run print - watch status messages for each touch

**For single touch (original behavior):**
- Leave **Sandwich Touches** at 1 (default)
- All other parameters work as before

All changes are automatic and backward compatible! 🎉
