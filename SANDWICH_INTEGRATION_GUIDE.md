# Sandwich Routine Integration Guide

**Last Updated:** October 10, 2025 - Added multi-touch capability and new parameters

## Overview

The sandwich routine has been fully integrated into the stepped printing process! The stage continues moving down until it contacts the glass window (detected by force), then retracts back to the proper layer height. **NEW:** Multi-touch capability with configurable acceleration, pause, and number of touches.

## What Changed

### 1. **New Instruction File Format**

The instruction file now has **15 columns** (updated from 12):

**Current Format (15 columns):**
```
Layer	File	Thickness	Time	Intensity	Step Speed	Overstep Distance	Step Type	Pause	Estimated Gap	Sandwich Force	Sandwich Speed	Sandwich Accel	Sandwich Pause	Sandwich Touches
```

### 2. **Six Sandwich Parameters**

| Parameter | Description | Units | Default | Notes |
|-----------|-------------|-------|---------|-------|
| **Estimated Gap** | Distance from membrane to glass window | mm | 0 | Set to **0 to skip sandwich** |
| **Sandwich Force** | Force threshold for glass contact detection | N | 0.05 | **Absolute value** (no sign needed) |
| **Sandwich Speed** | Speed during sandwich approach/retraction | µm/s | 500 | Same for up and down |
| **Sandwich Accel** 🆕 | Acceleration during sandwich movements | µm/s² | 5000 | Independent from main accel |
| **Sandwich Pause** 🆕 | Pause after detecting contact | s | 0.5 | Allows wetting/relaxation |
| **Sandwich Touches** 🆕 | Number of touch cycles | # | 1 | 2+ for multi-touch |

### 3. **GUI Fields**

Six entry fields in the Print Parameters section:

- **Est. Glass Gap (mm)** - Column 2
- **Sandwich Force (N)** - Column 3  
- **Sandwich Speed (µm/s)** - Column 3
- **Sandwich Accel (µm/s²)** - Column 2 (new)
- **Sandwich Pause (s)** - Column 3 (new)
- **Sandwich Touches (#)** - Column 4 (new)

## How to Use

### Creating a New Instruction File

1. **Set your directory** and basic parameters as usual
2. **Set the sandwich parameters:**
   - **Est. Glass Gap**: Enter your estimate (e.g., `0.5` for 0.5mm). Enter `0` to disable sandwich.
   - **Sandwich Force**: Enter threshold as **absolute value** (e.g., `0.05` for 0.05N force)
   - **Sandwich Speed**: Enter approach speed (e.g., `500` for 500 µm/s)
   - **Sandwich Accel**: Enter acceleration (e.g., `5000` for 5000 µm/s²)
   - **Sandwich Pause**: Enter pause duration (e.g., `0.5` for 0.5 seconds)
   - **Sandwich Touches**: Enter number of touches (e.g., `3` for three touches)
3. **Click "Simple input txt generator"**
4. The instruction file will include all 15 columns

### Using Existing Old Files

**Old 9-column and 12-column files are still compatible!** The system automatically detects old format files and uses default values:
- Estimated Gap = `0` (sandwich disabled)
- Sandwich Force = `0.05` N (absolute value)
- Sandwich Speed = `500` µm/s
- Sandwich Accel = `5000` µm/s² (new default)
- Sandwich Pause = `0.5` s (new default)
- Sandwich Touches = `1` (new default - original single-touch behavior)

## Print Behavior

### When Estimated Gap = 0 (Sandwich Disabled)
The stage behaves **exactly as before**:
1. Exposure
2. Peel up (overstep + thickness)
3. Return to layer position
4. Pause (if defined)
5. Next layer

### When Estimated Gap > 0, Sandwich Touches = 1 (Single Touch - Original Behavior)
Standard behavior for each layer:
1. **Exposure** at current layer position
2. **Peel up** (overstep + thickness)
3. **Return to layer position**
4. **Wait 1 second** for forces to settle
5. **SANDWICH STEP:**
   - Descend at sandwich_speed with sandwich_accel
   - Monitor force every 20ms
   - Stop when |force| >= sandwich_force
   - Pause for sandwich_pause duration
   - Retract to layer position at sandwich_speed
6. **Pause** (if defined) - happens AFTER sandwich completes
7. **DLP power restored** for next layer
8. Next layer

### When Estimated Gap > 0, Sandwich Touches > 1 (Multi-Touch - NEW!)
Enhanced behavior with multiple touch cycles:
1. **Exposure** at current layer position
2. **Peel up** (overstep + thickness)
3. **Return to layer position**
4. **Wait 1 second** for forces to settle
5. **MULTI-TOUCH SANDWICH:**
   - **For each touch (1 to N):**
     - Descend at sandwich_speed with sandwich_accel
     - Monitor force every 20ms
     - Stop when |force| >= sandwich_force
     - Pause for sandwich_pause duration
     - **If NOT last touch:**
       - Retract **500µm** from contact position
       - Wait 100ms before next touch
     - **If LAST touch:**
       - Return to target layer position
6. **Pause** (if defined) - happens AFTER all touches complete
7. **DLP power restored** for next layer
8. Next layer

**Multi-Touch Example (3 touches):**
```
Layer Position: 10.0mm
Touch 1: Descend → Contact at 10.51mm → Pause 0.5s → Up to 10.01mm
Touch 2: Descend → Contact at 10.50mm → Pause 0.5s → Up to 10.00mm
Touch 3: Descend → Contact at 10.51mm → Pause 0.5s → Return to 10.0mm
Complete!
```

## Technical Details

### Sandwich Process Flow

```
Current Layer Position (z_return_pos)
        ↓
    (start sandwich descent at sandwich_speed)
        ↓
    [Monitor force every 20ms]
        ↓
    Force <= sandwich_force? → YES → STOP IMMEDIATELY
        ↓                             ↓
       NO                    Record contact position
        ↓                             ↓
    Continue down           Calculate actual gap
        ↓                             ↓
    Reached search limit?   Retract to z_return_pos
        ↓                    (at 1.0 mm/s)
    YES - No contact found            ↓
        ↓                    Sandwich complete!
    Retract to z_return_pos
```

### Key Implementation Details

1. **Uses existing acceleration**: The sandwich movement uses the same acceleration you defined for that layer's print parameters
2. **Force monitoring**: Checks force every 20ms during descent
3. **Safety limit**: Won't search beyond `estimated_gap + 0.5mm` from the target position
4. **Requires calibrated force gauge**: If force gauge isn't calibrated, sandwich is skipped for that layer
5. **Non-blocking on error**: If sandwich fails, it logs the error but continues the print
6. **Pause timing**: The pause happens AFTER the sandwich completes, not before

### Parameters Per Layer

All three sandwich parameters are **per-layer**, meaning you can:
- Enable/disable sandwich on specific layers by editing the instruction file
- Use different force thresholds for different layers
- Adjust approach speed per layer

## Parameter Guidelines

### Estimated Gap
- **Start conservative**: Begin with a small value (e.g., `0.3` mm)
- **Observe actual gap**: Check the status messages during printing
- **Refine**: Adjust based on measured values
- **Purpose**: This is a safety limit - if no contact is detected within this range, the stage stops searching

### Sandwich Force
- **Enter as absolute value** - no need to worry about sign!
- **Too sensitive** (smaller value, e.g., `0.02`): May trigger false positives, detect contact too early
- **Too insensitive** (larger value, e.g., `0.2`): May compress the part/glass too much
- **Recommended starting value**: `0.05` N (0.05N force magnitude)
- **How it works**: System checks if `|force| >= threshold`, so it works for both compression and tension
- **Adjust based on**:
  - Part size (larger parts = more force needed)
  - Resin viscosity (thicker resin = different force profile)
  - Glass flexibility

### Sandwich Speed
- **Slower** (e.g., `0.2` mm/s): More precise contact detection, less impact force
- **Faster** (e.g., `1.0` mm/s): Faster printing, but risk of overshooting
- **Recommended**: `0.5` mm/s for most applications
- **Consider**: Slower speeds for delicate parts or initial layers

## Troubleshooting

### Sandwich not running
**Symptoms**: Status messages don't mention sandwich
**Causes**:
- Estimated Gap = 0 in instruction file
- Force gauge not calibrated
**Solution**: Check instruction file values, ensure force gauge is calibrated

### "No glass contact" warnings
**Symptoms**: Message says "No glass contact (reached X.XXXmm)"
**Causes**:
- Estimated gap too small (glass is further than expected)
- Force threshold too sensitive (requires more compression)
**Solution**: Increase estimated gap or make force threshold more negative

### Glass contact detected too early
**Symptoms**: Contact detected immediately or at unexpected position
**Causes**:
- Force threshold too sensitive
- Pre-existing force on the system
**Solution**: Increase force threshold (e.g., from `0.02` to `0.05`)

### Print continues despite sandwich errors
**Behavior**: This is intentional!
**Reason**: Sandwich is an enhancement, not critical to basic printing
**Note**: Monitor status messages - if sandwich consistently fails, you should investigate

## Example Instruction File

```tsv
Layer	File	Thickness	Time	Intensity	Step Speed	Overstep Distance	Step Type	Pause	Estimated Gap	Sandwich Force	Sandwich Speed
1	layer_0001.png	50	10	255	1000	500	5	0	0.5	0.05	0.5
2	layer_0002.png	50	3	255	1000	500	5	0	0.5	0.05	0.5
3	layer_0003.png	50	3	255	1000	500	5	2	0.5	0.05	0.5
4	layer_0004.png	50	3	255	1000	500	5	0	0	0.05	0.5
```

**Layer 1-3**: Sandwich enabled (gap=0.5mm, force=0.05N)
**Layer 4**: Sandwich disabled (gap=0)

## Backward Compatibility

✅ **Old 9-column files work perfectly**
- System detects column count
- Defaults to Estimated Gap = 0 (sandwich disabled)
- No changes needed to existing workflows

✅ **New files work with old code**
- If you revert to old code, extra columns are simply ignored
- Print will work normally without sandwich

## Benefits

1. **Consistent glass contact**: Every layer makes proper contact with the glass window
2. **Prevents punching through**: Force-based detection stops movement before damage
3. **Adaptive**: Measures actual gap and reports it
4. **Flexible**: Can be enabled/disabled per layer
5. **Safe**: Non-critical errors don't abort the print

## Advanced Usage

### Variable Sandwich Per Layer

Edit the instruction file to use different parameters:

```tsv
Layer 1-5: Gap=0.5, Force=0.05, Speed=0.3  (slow and gentle for base layers)
Layer 6-100: Gap=0.4, Force=0.08, Speed=0.5  (normal printing)
Layer 101-105: Gap=0, Force=0.05, Speed=0.5  (disable for top layers)
```

### Measuring Your Setup

1. Set Estimated Gap = `1.0` (generous)
2. Run a few layers with sandwich enabled
3. Check status messages for "Actual glass gap: X.XXX mm"
4. Use the average measured value as your Estimated Gap for future prints
5. This optimizes search time and safety

## Status Messages

Watch for these messages during printing:

```
L5: Starting sandwich routine (Gap:0.5mm, Force:0.05N, Speed:0.5mm/s)
L5: Searching for glass down to 5.500mm
L5: Glass contact at 5.523mm (Gap:0.523mm, Force:0.051N)
L5: Returning to layer position 5.000mm
L5: Sandwich complete, position 5.000mm
```

## Questions?

- Check that force gauge is calibrated before each print
- Monitor status messages during the first few layers
- Adjust parameters based on observed behavior
- Start conservative and optimize over time
