# Smooth Lifting Phase Detection Enhancement

**Date**: January 10, 2026  
**Status**: Implemented, Ready for Testing

## Overview

Updated the phase detection system to distinguish between smooth lifting stages, allowing adhesion analysis to correctly identify where prescribed-speed lifting begins vs gentle break phases.

## Motivation

When using smooth lifting (multi-stage velocity ramping), the first two stages are designed to gently break the hydrodynamic lock at very slow speeds (50-100 µm/s). These stages should **not** be included in the adhesion analysis as the "lifting phase" because:

1. They move at intentionally slow speeds to ease water flow
2. They create force profiles that are part of the controlled break, not the actual peel
3. Adhesion metrics should measure the peel at **prescribed speed** (Stage 3), not the gentle break

## New Phase Labels

### For Smooth Lifting (3-stage velocity ramping):
- **`Lift-Stage1`**: First 50µm at 50 µm/s (very gentle initial break)
- **`Lift-Stage2`**: Next 100µm at 100 µm/s (slow transition)
- **`Lift-Stage3`**: Remaining distance at prescribed speed (normal peel)

### For Standard Lifting (single-stage):
- **`Lift`**: Entire movement at prescribed speed

## Implementation Details

### 1. MotionController (`motion_controller.py`)
- Added `phase_callback` parameter to `execute_lift()`
- Reports phase changes during smooth lifting:
  - Stage 1 → calls `phase_callback("Lift-Stage1")`
  - Stage 2 → calls `phase_callback("Lift-Stage2")`
  - Stage 3 → calls `phase_callback("Lift-Stage3")`
- For standard lift → calls `phase_callback("Lift")`

### 2. PositionLogger (`PositionLogger.py`)
- Updated `set_phase()` docstring to document new phases
- Updated `_determine_phase()` docstring to explain smooth lifting stages
- Accepts and logs all new phase labels

### 3. PeakForceLogger (`PeakForceLogger.py`)
- Updated `_update_phase_info()` to recognize both `"Lift"` and `"Lift-Stage3"` as lifting start
- When smooth lifting is enabled, `lifting_start_idx` points to Stage 3 start
- This ensures adhesion analysis excludes gentle break phases from pre-initiation search

### 4. AdhesionMetricsCalculator (`adhesion_metrics_calculator.py`)
- Updated documentation for `lifting_start_idx` parameter
- Clarified that for smooth lifting, this should be Stage 3 start
- Pre-initiation detection starts at prescribed-speed lifting, not gentle break

### 5. Prince_Segmented (`Prince_Segmented.py`)
- Passes `phase_callback=self._set_phase_robust` to `motion_controller.execute_lift()`
- Phase changes are automatically logged during smooth lifting

## Data Flow

```
Prince_Segmented.py
  └─> motion_controller.execute_lift(phase_callback=self._set_phase_robust)
       └─> Stage 1: calls phase_callback("Lift-Stage1")
       └─> Stage 2: calls phase_callback("Lift-Stage2")
       └─> Stage 3: calls phase_callback("Lift-Stage3")
            └─> self._set_phase_robust("Lift-Stage3")
                 └─> PositionLogger.set_phase("Lift-Stage3")
                      └─> Logs to autolog CSV with phase="Lift-Stage3"
                           └─> PeakForceLogger tracks this as lifting_start_idx
                                └─> AdhesionMetricsCalculator uses this for pre-initiation search boundary
```

## Benefits

### For Adhesion Analysis:
1. **Accurate Pre-Initiation Detection**: Pre-initiation search starts where prescribed-speed peel begins, not during gentle break
2. **Clean Baseline**: Excludes forces from intentional slow-speed break phases
3. **Correct Phase Boundaries**: Metrics measure actual peel performance, not controlled break

### For Data Visualization:
1. **Clear Phase Labels**: Autolog CSV shows exactly which stage the data belongs to
2. **Easy Filtering**: Can filter data by phase (e.g., only show "Lift-Stage3" for adhesion analysis)
3. **Debugging Support**: Can see if hydrodynamic locking occurs in Stage 1, 2, or 3

### For Post-Processing:
1. **Flexible Analysis**: Can analyze gentle break separately from normal peel
2. **Stage-Specific Metrics**: Can calculate metrics for each stage independently
3. **Validation**: Can verify smooth lifting is working by checking phase transitions in data

## Autolog CSV Example

**With Smooth Lifting Enabled:**
```csv
Elapsed Time (s),Position (mm),Force (N),Phase
4.100,55.9000,-0.050,Pause
4.150,55.8950,-0.055,Lift-Stage1    # 0-50µm at 50µm/s
4.200,55.8900,-0.060,Lift-Stage1
...
5.100,55.8500,-0.100,Lift-Stage2    # 50-150µm at 100µm/s
5.200,55.8400,-0.120,Lift-Stage2
...
6.100,55.7900,0.050,Lift-Stage3     # 150µm+ at prescribed speed
6.200,55.7500,0.150,Lift-Stage3     # <- ADHESION ANALYSIS STARTS HERE
6.300,55.7100,0.180,Lift-Stage3
```

**With Standard Lifting:**
```csv
Elapsed Time (s),Position (mm),Force (N),Phase
4.100,55.9000,-0.050,Pause
4.150,55.8900,0.020,Lift            # Entire movement at prescribed speed
4.200,55.8700,0.100,Lift            # <- ADHESION ANALYSIS STARTS HERE
4.250,55.8500,0.180,Lift
```

## Configuration

### Current Smooth Lifting Profile (motion_controller.py):
```python
smooth_lift_config = {
    'stage1_distance_um': 50,       # Stage 1: 50µm
    'stage1_velocity_um_s': 50,     # At 50µm/s
    'stage2_distance_um': 100,      # Stage 2: 100µm
    'stage2_velocity_um_s': 100,    # At 100µm/s
    # Stage 3: Remaining at base_velocity (from instruction file)
}
```

### Enabling Smooth Lifting:
1. Check the "Smooth Lifting" checkbox in Prince_Segmented GUI
2. Phase labels will automatically be reported
3. Adhesion analysis will automatically use Stage 3 start as lifting_start_idx

## Testing

### Validation Steps:
1. ✓ Check autolog CSV shows "Lift-Stage1", "Lift-Stage2", "Lift-Stage3" phases
2. ✓ Verify Stage 1 is ~50µm (1 second at 50µm/s)
3. ✓ Verify Stage 2 is ~100µm (1 second at 100µm/s)
4. ✓ Verify Stage 3 starts at ~150µm from peel start
5. ✓ Check adhesion analysis excludes Stage 1 & 2 from pre-initiation search
6. ✓ Verify force profile shows smooth transition without hydrodynamic locking

### Expected Results:
- **Terminal Output**: "Smooth 3-stage" in status message, "3 segments" in completion
- **Autolog Data**: Three distinct phase regions with clear labels
- **Force Profile**: Gradual rise in Stage 1 & 2, normal peel in Stage 3
- **Peak Force Log**: Pre-initiation starts at Stage 3 boundary

## Rollback

If issues occur, revert to standard lifting:
1. Uncheck "Smooth Lifting" checkbox
2. Phase will be labeled as "Lift" for entire movement
3. Adhesion analysis will use motion start as lifting_start_idx

No code changes needed - behavior is controlled by checkbox.

## Future Enhancements

1. **Smart Peel Integration**: Use phase-aware force monitoring to detect when Stage 3 completes early
2. **Stage-Specific Metrics**: Calculate adhesion metrics separately for each stage
3. **Adaptive Stage Tuning**: Adjust Stage 1 & 2 velocities based on detected hydrodynamic forces
4. **Phase-Based Plots**: Color-code force curves by phase in post-processing plots

## Related Files

- `support_modules/motion_controller.py` - Phase callback implementation
- `support_modules/PositionLogger.py` - Phase label definitions
- `support_modules/PeakForceLogger.py` - Phase-aware lifting_start_idx tracking
- `support_modules/adhesion_metrics_calculator.py` - Pre-initiation boundary handling
- `Prince_Segmented.py` - Phase callback connection

## References

- `MOTION_CONTROLLER_INTEGRATION.md` - Original motion controller documentation
- `STAGE_STALL_PREVENTION.md` - Smooth retraction implementation
- Autolog CSV files in PrintingLogs folders
