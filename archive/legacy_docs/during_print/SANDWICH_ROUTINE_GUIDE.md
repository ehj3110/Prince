# Sandwich Routine Usage Guide

## What is the Sandwich Routine?

The **Sandwich Routine** is a specialized procedure for 3D printing that moves the stage down until it gently contacts the glass window, then retracts to the proper layer height. This prevents accidentally punching through the glass while ensuring good contact between the resin and the glass surface.

## When to Use It

- **Before starting a print**: To ensure proper contact with the glass window
- **When you're uncertain about the glass gap**: The routine will measure and report the actual distance
- **To prevent glass damage**: By detecting contact through force rather than hard stops

## How It Works

1. **Moves down slowly** from the target height at a controlled speed (default: 0.5 mm/s)
2. **Monitors force continuously** using the force gauge
3. **Detects glass contact** when force exceeds the threshold (e.g., -0.05 N compression)
4. **Stops immediately** upon contact to prevent damage
5. **Retracts back** to the target layer height (default: 1.0 mm/s)
6. **Reports the actual glass gap** measured during the procedure

## GUI Controls (New!)

The Sandwich Routine now has dedicated GUI controls in the main Prince window:

### Location
- Below the "Auto-Home Control" section
- In a labeled frame: "Sandwich Routine (Glass Contact)"

### Parameters

| Parameter | Description | Default | Units |
|-----------|-------------|---------|-------|
| **Target Height** | The final Z position where the stage should end up | 0.0 | mm |
| **Est. Glass Gap** | Your guess for how far below the glass window is | 0.5 | mm (positive) |
| **Contact Force** | Force threshold to detect glass contact | 0.05 | N (absolute value) |

### How to Use the GUI

1. **Open the Sensor Panel** and **calibrate the force gauge** first
   - Click "Open Sensor Panel"
   - Click "Calibrate Force Gauge"
   - The "Run Sandwich" button will become enabled when calibrated

2. **Set your parameters**:
   - **Target Height**: Enter the Z position where you want the stage to end up (usually your starting print position)
   - **Est. Glass Gap**: Enter your best guess for how far the glass is below the target (e.g., 0.5 mm)
   - **Contact Force**: Enter the force threshold as absolute value (e.g., 0.05 for 0.05 N force magnitude)

3. **Click "Run Sandwich"**
   - The routine will start automatically
   - Status messages will appear in the "System Message" area
   - The stage will move down slowly until glass contact is detected
   - It will then retract back to the target height

4. **Review the results**
   - A dialog box will show the measured glass gap
   - The actual gap is displayed (e.g., "Actual glass gap: 0.523 mm")
   - This information helps you refine your estimates for future runs

## Parameter Guidelines

### Target Height
- This is where you want to START your print
- Usually `0.0` mm if you've already homed
- Or a specific Z coordinate from your print plan

### Estimated Glass Gap
- **Must be positive** (how far DOWN to search)
- Start with `0.5` mm and adjust based on experience
- The routine will search up to `0.5` mm beyond this estimate for safety
- Example: If you think glass is 0.4 mm below target, enter `0.4`

### Contact Force Threshold
- **Enter as absolute value** (no sign needed)
- Recommended starting value: `0.05` N (0.05 N force magnitude)
- More sensitive (smaller value): `0.02` N
- Less sensitive (larger value): `0.1` N
- System checks `|force| >= threshold`, works for both compression and tension
- Adjust based on your glass/resin/setup

## Safety Features

- **Force-based detection**: Stops immediately when threshold is reached
- **Maximum travel limit**: Won't search more than 0.5 mm beyond your estimate
- **Slow approach speed**: Default 0.5 mm/s to prevent damage
- **Thread safety**: Can be cancelled during operation
- **Calibration check**: Won't run without a calibrated force gauge

## Troubleshooting

### "Run Sandwich" button is disabled
- **Solution**: Open Sensor Panel and calibrate the force gauge

### "Sandwich routine timed out"
- **Cause**: Glass wasn't found within the search area
- **Solution**: Increase your "Est. Glass Gap" estimate

### Glass contact not detected
- **Cause**: Contact force threshold might be too sensitive (too small)
- **Solution**: Increase the threshold (e.g., from `0.02` to `0.05`)

### Glass contact detected too early
- **Cause**: Force threshold too large or pre-existing force
- **Solution**: Decrease the threshold (e.g., from `0.1` to `0.05`)
### Stage moved too far
- **Cause**: Estimated gap was much larger than actual
- **Solution**: Use a more conservative (smaller) estimate next time

## Advanced: Programmatic Usage

If you need to call the sandwich routine from code (not the GUI):

```python
from SandwichRoutine import perform_sandwich_step_blocking

success, message, glass_gap = perform_sandwich_step_blocking(
    zaber_axis=self.axis,
    force_gauge_manager=self.force_gauge_manager,
    target_layer_height=0.0,        # mm
    estimated_glass_gap=0.5,        # mm (positive)
    contact_force_threshold=-0.05,  # N (negative)
    status_callback=self.update_status_message,
    timeout=30  # seconds
)

if success:
    print(f"Glass gap measured: {glass_gap:.3f} mm")
else:
    print(f"Failed: {message}")
```

## Technical Details

### Routine Phases

**Phase 1: Approach**
- Starts at current position
- Moves down at `approach_speed` (0.5 mm/s default)
- Monitors force every 0.02 seconds
- Stops when force <= threshold

**Phase 2: Measurement**
- Records exact position of glass contact
- Calculates actual gap = contact_position - target_height

**Phase 3: Retraction**
- Moves back up at `retract_speed` (1.0 mm/s default)
- Returns to target_layer_height
- Print can begin from this position

### Configurable Parameters (in code)
Located in `SandwichRoutine.py`:
- `approach_speed`: 0.5 mm/s
- `retract_speed`: 1.0 mm/s
- `max_travel_beyond_estimate`: 0.5 mm
- `force_check_interval`: 0.02 seconds

## Credits

Module created by the Prince development team for safe glass contact detection in DLP resin printing.
