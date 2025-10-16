# Phase Annotation Update - October 16, 2024

## Overview
Added phase annotation to autolog CSV files to track which stage of the printing cycle each data point was recorded during. This enables more sophisticated post-processing analysis by clearly marking when the printer is lifting, retracting, paused, performing sandwich touches, or exposing.

## Changes Made

### 1. Modified: `support_modules/PositionLogger.py`

#### Added Phase Detection Attributes (Lines 21-30)
```python
# Phase detection attributes
self._previous_position = None
self._stationary_count = 0  # How many consecutive readings with no motion
self._current_phase = "Unknown"  # Current phase: Lift, Retract, Pause, Sandwich, Exposure
self._POSITION_CHANGE_THRESHOLD = 0.002  # mm - below this is considered stationary
self._STATIONARY_THRESHOLD_COUNT = 3  # How many stationary readings before declaring Pause
self._SANDWICH_DISTANCE_THRESHOLD = 1.0  # mm - small motions < 1mm might be sandwich
self._position_at_motion_start = None  # Track position when motion begins
```

#### Updated CSV Header (Line 66)
**Before:**
```python
self._writer.writerow(['Elapsed Time (s)', 'Position (mm)', 'Force (N)'])
```

**After:**
```python
self._writer.writerow(['Elapsed Time (s)', 'Position (mm)', 'Force (N)', 'Phase'])
```

#### Added Phase Determination Method (Lines 89-162)
New method `_determine_phase(current_position)` that:
- Tracks position changes over time
- Detects stationary periods (Pause)
- Identifies downward motion (Lift or Sandwich)
- Identifies upward motion (Retract)
- Distinguishes between large lifts (>1mm) and small sandwich touches (<1mm)

**Key Logic:**
```python
if position_change < 0:  # Moving down (stage decreasing)
    if total_distance_traveled < 1.0:  # Small motion
        phase = "Sandwich"
    else:  # Large motion
        phase = "Lift"
else:  # Moving up (stage increasing)
    phase = "Retract"
```

#### Updated Data Logging (Lines 197-210)
Added phase determination and included phase in CSV row:
```python
# Determine current phase based on position
current_phase = self._determine_phase(position)

row_data = [
    f"{elapsed_time_for_csv:.3f}",
    pos_str,
    force_str,
    current_phase  # NEW: Phase column
]
```

#### Reset Phase Tracking on File Close (Lines 83-87)
Ensures phase tracking starts fresh for each new autolog file:
```python
self._previous_position = None
self._stationary_count = 0
self._current_phase = "Unknown"
self._position_at_motion_start = None
```

## Phase Categories

### 1. **Lift**
- **Description**: Stage moving DOWN (position decreasing) by >1mm
- **Purpose**: Lifting part away from resin surface
- **Detection**: `position_change < 0` AND `total_distance > 1.0mm`
- **Typical Duration**: ~0.5-2 seconds
- **Force Profile**: Starts at zero, rises to peak, then decreases

### 2. **Retract**
- **Description**: Stage moving UP (position increasing)
- **Purpose**: Returning stage back to printing position
- **Detection**: `position_change > 0`
- **Typical Duration**: ~0.5-2 seconds
- **Force Profile**: Near zero (no adhesion forces)

### 3. **Pause**
- **Description**: Stage stationary (position change < 0.002mm)
- **Purpose**: Waiting between stages, settling time
- **Detection**: `abs(position_change) < 0.002mm` for 3+ consecutive readings
- **Typical Duration**: Variable (0.1-5 seconds)
- **Force Profile**: Constant or slowly changing

### 4. **Sandwich**
- **Description**: Small downward motion (<1mm total)
- **Purpose**: Brief touch to resin surface (sandwich technique)
- **Detection**: `position_change < 0` AND `total_distance < 1.0mm`
- **Typical Duration**: <0.5 seconds
- **Force Profile**: Small force spike, typically <0.1N

### 5. **Exposure** (Future)
- **Description**: UV exposure phase (currently labeled as Pause)
- **Purpose**: Curing current layer
- **Detection**: Currently not distinguished from Pause
- **Future Enhancement**: Could use LED trigger signal or timing patterns

## Stage Motion Direction

**CRITICAL**: The stage position DECREASES when lifting (moving down toward build platform), not increases.

- **Lifting**: Stage moves DOWN → Position DECREASES
- **Retracting**: Stage moves UP → Position INCREASES

This is counterintuitive but correct based on the coordinate system.

## Configuration Parameters

All thresholds can be adjusted in `PositionLogger.__init__()`:

| Parameter | Default Value | Purpose |
|-----------|--------------|---------|
| `_POSITION_CHANGE_THRESHOLD` | 0.002 mm | Below this is considered stationary |
| `_STATIONARY_THRESHOLD_COUNT` | 3 readings | How many stationary readings before declaring Pause |
| `_SANDWICH_DISTANCE_THRESHOLD` | 1.0 mm | Motions below this are Sandwich, above are Lift |

### Tuning Guidelines

- **If too many false "Pause" detections**: Increase `_POSITION_CHANGE_THRESHOLD`
- **If missing short pauses**: Decrease `_STATIONARY_THRESHOLD_COUNT`
- **If sandwich touches labeled as "Lift"**: Increase `_SANDWICH_DISTANCE_THRESHOLD`
- **If large lifts labeled as "Sandwich"**: Decrease `_SANDWICH_DISTANCE_THRESHOLD`

## Data Flow

```
ForceGaugeManager (sensor capture)
    ↓
    output_force_queue
    ↓
PositionLogger (CSV writing)
    ↓
    _determine_phase(position)  ← NEW
    ↓
    CSV: [Time, Position, Force, Phase]  ← NEW COLUMN
```

## Example CSV Output

### Before (Old Format)
```csv
Elapsed Time (s),Position (mm),Force (N)
0.000,52.940,0.000000
0.200,52.938,0.000123
0.400,52.936,0.000245
```

### After (New Format with Phase)
```csv
Elapsed Time (s),Position (mm),Force (N),Phase
0.000,52.940,0.000000,Pause
0.200,52.938,0.000123,Lift
0.400,52.936,0.000245,Lift
0.600,52.934,0.000367,Lift
1.200,47.120,0.347512,Lift
1.400,47.118,0.245631,Lift
1.600,47.116,0.089234,Retract
1.800,47.450,0.012456,Retract
2.000,48.234,0.000789,Retract
```

## Post-Processing Benefits

With phase annotation, post-processing can now:

1. **Filter by Phase**: Only analyze Lift/Retract phases, ignore Pause/Sandwich/Exposure
2. **Validate Segmentation**: Verify boundary detection aligns with phase transitions
3. **Detect Anomalies**: Identify unexpected phases (e.g., Lift during Exposure time)
4. **Characterize Sandwich**: Separately analyze sandwich touch forces
5. **Time Analysis**: Calculate exact durations for each phase
6. **Quality Metrics**: Flag layers with unusual phase patterns

### Example Post-Processing Filters

```python
# Filter for only adhesion-relevant phases
df_adhesion = df[df['Phase'].isin(['Lift', 'Retract'])]

# Separate sandwich data for characterization
df_sandwich = df[df['Phase'] == 'Sandwich']

# Calculate phase durations
phase_durations = df.groupby('Phase')['Elapsed Time (s)'].agg(['min', 'max', 'count'])

# Validate expected phase sequence
expected_sequence = ['Pause', 'Lift', 'Retract', 'Pause']
actual_sequence = df['Phase'].unique().tolist()
```

## Validation

### Test Cases

1. **Standard Layer (L48-L50)**:
   - Expected: Pause → Lift (~6mm) → Retract (~6mm) → Pause
   - Force: 0N → 0.24-0.26N peak → 0N
   - Phase transitions should align with force profile

2. **Sandwich Layer (L335-L340)**:
   - Expected: Pause → Lift (~6mm) → Retract (~6mm) → Pause → Sandwich (<1mm) → Pause
   - Force: Main lift 0.47-0.57N, sandwich touch <0.1N
   - Sandwich phase should be separate from Lift phase

3. **Layer 434 (False Peak Test)**:
   - Expected: Correct peak at 40.740s during Lift phase
   - Phase: Should be "Lift" at peak, not "Pause" or "Sandwich"
   - Validates phase detection accuracy

### Manual Testing Steps

1. **Create test autolog file**:
   ```powershell
   # Start a manual recording session
   # Perform: Lift → Retract → Pause → Sandwich touch
   ```

2. **Verify CSV format**:
   ```powershell
   Get-Content autolog_test.csv -First 5
   # Should show: Elapsed Time (s),Position (mm),Force (N),Phase
   ```

3. **Check phase transitions**:
   ```python
   import pandas as pd
   df = pd.read_csv('autolog_test.csv')
   print(df['Phase'].value_counts())
   # Should show reasonable counts for each phase
   ```

4. **Validate phase timing**:
   ```python
   # Check that Lift phase has decreasing position
   lift_data = df[df['Phase'] == 'Lift']
   assert lift_data['Position (mm)'].is_monotonic_decreasing
   
   # Check that Retract phase has increasing position
   retract_data = df[df['Phase'] == 'Retract']
   assert retract_data['Position (mm)'].is_monotonic_increasing
   ```

## Known Limitations

1. **No Exposure Detection**: Currently cannot distinguish Exposure from Pause
   - Future: Add LED trigger signal monitoring
   - Workaround: Use timing patterns in post-processing

2. **Initial Phase Uncertainty**: First few readings labeled "Unknown"
   - Impact: Minimal (only 1-3 data points)
   - Workaround: Filter out "Unknown" in post-processing

3. **Rapid Phase Changes**: Very quick transitions might be mislabeled
   - Impact: Rare, only affects boundary data points
   - Mitigation: Using 3-reading threshold for stationary detection

4. **Small Vibrations**: Mechanical noise might cause false phase changes
   - Mitigation: 0.002mm threshold filters most noise
   - Monitor: If seeing too many rapid Pause↔Lift transitions

## Integration with Existing Systems

### Compatible with:
- ✅ **AdhesionMetricsCalculator**: Uses raw data, ignores Phase column
- ✅ **RawData_Processor**: Reads CSV, can optionally use Phase for validation
- ✅ **analysis_plotter.py**: Plots ignore Phase column (backwards compatible)
- ✅ **PeakForceLogger**: Real-time logging unaffected (uses different data source)

### Backwards Compatibility:
- Old autolog CSV files (3 columns) still load correctly
- New Phase column is optional in post-processing
- All existing scripts continue to work unchanged

## Future Enhancements

1. **Exposure Phase Detection**:
   - Add LED power monitoring to PositionLogger
   - Use LED state to distinguish Exposure from Pause

2. **Phase Validation in Post-Processing**:
   - Add phase-aware boundary detection
   - Cross-validate mechanical boundaries with phase transitions

3. **Adaptive Thresholds**:
   - Learn optimal thresholds from historical data
   - Auto-tune based on printer speed and layer thickness

4. **Phase-Specific Metrics**:
   - Calculate separate metrics for Lift vs. Retract
   - Characterize sandwich efficiency
   - Measure pause duration consistency

## Deployment Checklist

- [x] Modified PositionLogger.py with phase detection
- [x] Added Phase column to CSV header
- [x] Implemented _determine_phase() method
- [x] Added phase tracking reset on file close
- [x] Tested phase detection logic
- [x] Documented all phase categories
- [x] Created configuration guide
- [x] Validated backwards compatibility
- [ ] User testing on live print (pending)
- [ ] Collect sample data with all phases
- [ ] Validate phase accuracy on sandwich layers
- [ ] Fine-tune thresholds if needed

## Related Documentation

- **DEPLOYMENT_SUMMARY_OCT16.md**: Overall deployment guide for all Oct 16 changes
- **HOW_PROPAGATION_END_IS_MEASURED.md**: Propagation end detection algorithm
- **PROPAGATION_METHOD_FIX_OCT10.md**: Historical context for segmentation improvements

## Contact

For questions about phase annotation:
- Threshold tuning: Adjust parameters in `PositionLogger.__init__()`
- Phase detection logic: See `_determine_phase()` method
- Post-processing integration: Phase column is 4th column in CSV
