# Continuous Motion Mode for Adhesion Metrics (overstep=0)

## Problem Description

When using `overstep_distance = 0` (continuous motion mode), the standard peel-overshoot-return cycle is replaced with a simpler motion profile:

**Standard Mode (overstep > 0):**
```
Exposure → Lift (overshoot) → Retract (return to layer height) → Pause
Peak force: During lift overshoot phase
```

**Continuous Mode (overstep = 0):**
```
Exposure → Lift (directly to final layer height) → Pause (long dwell)
Peak force: At END of lift or DURING pause (force relaxation)
```

### Original Issue

The adhesion metrics system was designed for standard peeling with overshoot. When using overstep=0:

1. **Position filtering excluded pause data:** The system filtered plot data to positions between `z_peel_peak` and `z_return_pos`
2. **With overstep=0:** `z_peel_peak` = `z_return_pos` (same position!)
3. **Result:** All pause phase data was excluded from analysis, causing sharp peaks to be missed

## Solution

### 1. Pass Actual Peel Positions

**Modified Files:**
- `Prince_Segmented.py` (lines ~1625-1635)
- `SensorDataWindow.py` (lines ~1107-1145)

**Changes:**
- `Prince_Segmented.py` now passes `z_peel_peak` and `z_return_pos` (in mm) to `update_auto_logger_current_layer()`
- `SensorDataWindow.py` forwards these values to `PeakForceLogger.start_monitoring_for_layer()`

**Before:**
```python
# SensorDataWindow.py used hardcoded fallback values
peel_start_z = z_position_mm + 1.0  # Generic +1mm
peel_end_z = z_position_mm + 3.0    # Generic +3mm
```

**After:**
```python
# Actual peel positions from Prince_Segmented
peel_peak_mm = z_peel_peak / 1000.0  # Actual calculated position
return_pos_mm = z_return_pos / 1000.0  # Actual calculated position
```

### 2. Continuous Motion Detection

**Modified File:** `PeakForceLogger.py` (lines ~266-295)

**Detection Logic:**
```python
is_continuous_mode = (self.z_peel_peak_mm is not None and 
                     self.z_return_pos_mm is not None and 
                     abs(self.z_peel_peak_mm - self.z_return_pos_mm) < 0.001)  # Within 1 micron
```

**Behavior:**
- **Continuous Mode:** Disables position filtering, includes ALL data (Lift + Pause phases)
- **Standard Mode:** Retains position filtering for traditional peel range
- **Manual Mode:** Always includes all data (unchanged)

### 3. User Feedback

When continuous motion is detected, the console displays:
```
PFL: Continuous motion mode detected (overstep=0) - no position filtering for layer N
PFL: Started monitoring layer N (peel: 50.050mm, return: 50.050mm, area: 12.34mm²)
```

## Analysis Window Behavior

### Data Collection Timing

**Monitoring starts:** At beginning of layer N exposure (via `start_monitoring_for_layer()`)

**Monitoring stops:** At beginning of layer N+1 exposure (via `stop_monitoring_and_log_peak()`)

**Data captured:**
- Exposure phase (layer N)
- Lift phase (peel movement)
- Pause phase (dwell before next layer)
- Up to start of next exposure

This ensures the **entire cycle** including pause is analyzed, capturing peaks that occur:
- At the end of lift (when stage reaches final position)
- During pause (force relaxation)

### Position Filtering Impact

**Standard Mode (overstep > 0):**
- Plot data filtered to peel range: `z_peel_peak` to `z_return_pos`
- Excludes baseline before peel and pause after return
- Peak expected during overshoot, within filtered range

**Continuous Mode (overstep = 0):**
- **No position filtering** (all data included)
- Pause phase data preserved for analysis
- Peak anywhere in Lift + Pause window detected correctly

## Usage

### Automatic Detection

No user configuration required! The system automatically detects continuous motion when:
- `z_peel_peak` ≈ `z_return_pos` (within 1 micron tolerance)
- This occurs when instruction file has `overstep_distance = 0`

### Verification

Check console output during print:
```
PFL: Continuous motion mode detected (overstep=0) - no position filtering for layer 1
PFL: Started monitoring layer 1 (peel: 50.050mm, return: 50.050mm, area: 12.34mm²)
                                       ^^^^^^^^           ^^^^^^^^
                                       Same position = Continuous mode
```

### Expected Results

With continuous motion mode enabled:
- ✅ Sharp peaks at end of lift phase **will be detected**
- ✅ Pause phase data **included in analysis**
- ✅ Pre-initiation, propagation, and work of adhesion calculated correctly
- ✅ Plot shading includes full analysis window

## Technical Details

### Motion Parameters Calculation

From `Prince_Segmented.py` line ~1226:
```python
z_peel_peak = z_exposure_pos_current_layer_i - (actual_overstep_microns + current_thickness_um)
z_return_pos = z_peel_peak + actual_overstep_microns
```

**When overstep = 0:**
```
z_return_pos = z_peel_peak + 0 = z_peel_peak
```

### Phase Tracking

The system uses phase events from `PositionLogger` to track:
- **Exposure:** DLP pattern display
- **Lift:** Stage moving away from resin (constant prescribed speed)
- **Pause:** Stage stationary after reaching final position

**Phase-Aware Analysis:**
- `lifting_start_idx` passed to calculator for accurate pre-initiation detection
- Limits backward search to actual motion start (prevents false baseline)

### Smoothing Filters

**Still Active (unchanged):**
- Median filter (kernel=5) for outlier rejection
- Savitzky-Golay filter (window=9, order=2) for smoothing

**Note:** These filters smooth the data but do NOT reject valid peaks. The median filter removes **noise spikes** (single-point outliers), not genuine force peaks that span multiple data points.

## Comparison Chart

| Feature | Standard Mode | Continuous Mode |
|---------|--------------|-----------------|
| **Overstep** | > 0 (e.g., 10mm) | = 0 |
| **Motion** | Lift → Overshoot → Return → Pause | Lift → Pause |
| **Peak Location** | During overshoot | End of lift / During pause |
| **Position Filter** | Active (z_peel to z_return) | **Disabled** (all data) |
| **z_peel_peak** | z_layer - overstep - thickness | z_layer - thickness |
| **z_return_pos** | z_layer - thickness | z_layer - thickness |
| **Analysis Window** | Filtered to peel range | **Full cycle** |
| **Pause Data** | Excluded by position filter | **Included** |

## Future Enhancements

Potential improvements for continuous motion analysis:

1. **Separate phase metrics:** Calculate adhesion metrics separately for Lift and Pause phases
2. **Relaxation analysis:** Measure force relaxation rate during pause
3. **Creep detection:** Identify slow force buildup during long pauses
4. **Motion end detection:** Explicitly track when stage stops moving (motion_end_idx)

## Related Documentation

- [MASTER_WORKFLOW_GUIDE.md](MASTER_WORKFLOW_GUIDE.md) - Complete printing workflow
- [LAYER_BOUNDARY_DETECTION.md](LAYER_BOUNDARY_DETECTION.md) - Phase detection system
- [adhesion_metrics_calculator.py](../support_modules/adhesion_metrics_calculator.py) - Analysis algorithms

## Changelog

**2024-01-XX:** Initial implementation of continuous motion mode detection
- Added automatic detection when z_peel_peak ≈ z_return_pos
- Disabled position filtering for overstep=0 scenarios
- Passed actual peel positions from Prince_Segmented to PeakForceLogger
- Added console feedback for mode detection
