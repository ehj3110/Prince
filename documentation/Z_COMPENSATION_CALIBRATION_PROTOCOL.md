# Z Compensation Calibration Protocol (Draft for Future Work)

## Purpose

This protocol defines a practical print-and-measure loop to calibrate axial print-through compensation parameters for resin printing.

Primary goals:
- Estimate penetration depth and stable compensation ranges.
- Reduce depth-dependent overcuring bias.
- Produce reusable resin profiles with clear validity bounds.

## Scope

In scope:
- Axial compensation only.
- Per-layer and per-voxel dose model parameterization.
- Offline fitting from printed artifacts.

Out of scope for this protocol revision:
- Full lateral scattering inversion.
- In-print closed-loop control.
- Firmware-level projector nonlinear response correction.

## Model Summary

Dose accumulation model:

For layer index k and applied exposure at layer j:

D_total(k) = sum over j from k to N of E(j) * exp(-((j-k) * h) / Dp)

Inverse solve target:

E(k) = max(0, D_target - sum over j from k+1 to N of E(j) * exp(-((j-k) * h) / Dp))

Where:
- h is layer thickness.
- Dp is penetration depth.
- D_target is target threshold dose proxy.

## Calibration Artifact Design

Use a single build plate containing:
1. Channel array with widths spanning expected process limits.
2. Thin-wall and pillar sets at multiple depths.
3. Repeated motifs at increasing Z depth to expose print-through trend.

Recommended layout:
- At least 3 repeats per feature size.
- Keep measurement zones separated to reduce local interaction effects.
- Include fiducials for consistent metrology positioning.

## Experimental Matrix (Minimum)

Suggested first-pass matrix:
1. Layer thickness: 2 to 3 levels (example: 25, 50, 75 um).
2. Exposure/speed condition: 2 to 3 levels around normal operating point.
3. Optional grayscale bias level: 1 to 2 levels if projector transfer is uncertain.

Run at least 2 replicate prints for each matrix point.

## Measurements to Record

Per feature:
1. Open/closed state (binary).
2. Width or diameter error (measured minus CAD).
3. Depth trend metric (same nominal feature across Z bins).

Per print:
1. Resin ID and age.
2. Temperature and humidity (if available).
3. Build settings snapshot (layer thickness, speed/exposure, grayscale mode).

## Fitting Strategy

Step-by-step:
1. Fit Dp and D_target proxy on the baseline matrix to minimize depth bias.
2. Fit compensation strength and min factor under safety constraints.
3. Validate monotonicity and clipping rates.
4. Freeze resin profile only if validation print passes independent geometry.

Loss objective recommendation:
- Weighted combination of:
  - Mean absolute dimensional error.
  - Depth-slope penalty (bias vs layer index).
  - Hard penalties for blocked channels / catastrophic failures.

## Output Profile Format (Proposed)

Store one profile per resin and operating band.

Fields:
1. profile_name
2. resin_id
3. calibration_date
4. valid_layer_thickness_um_min
5. valid_layer_thickness_um_max
6. penetration_depth_um
7. target_dose_proxy
8. default_strength
9. default_min_factor
10. notes_and_limitations

## Acceptance Criteria

A profile is accepted when all conditions hold:
1. Independent validation geometry shows reduced depth bias versus baseline.
2. Failure rate does not increase in critical feature classes.
3. Compensation clipping remains below agreed threshold.
4. Runtime remains within preprocessing budget.

## Risks and Guardrails

Known risks:
1. Overfitting to one geometry family.
2. Drift from resin aging and environmental changes.
3. Confounding lateral and axial effects.

Guardrails:
1. Keep min_factor floor enabled.
2. Constrain strength to validated range.
3. Record profile provenance with each print session.

## Implementation Hooks Already Available

Current modules that support this protocol:
1. support_modules/z_compensation.py
2. support_modules/image_modification/processor.py
3. support_modules/ImageModificationWindow.py

## Future Enhancements

Planned future additions:
1. Automated fit utility from measurement CSV.
2. Profile loader and validator module.
3. Optional per-voxel solve mode for selected regions of interest.
