SMOOTHING PARAMETER CORRECTION - September 21, 2025
=====================================================

## PROBLEM IDENTIFICATION
During debugging of propagation end time calculations, we discovered that the hybrid adhesion system was showing incorrect propagation end times:
- Expected: ~11.7s for Layer 198
- Observed: ~11.8s for Layer 198
- Difference: ~0.1s error in propagation end detection

## ROOT CAUSE ANALYSIS
The issue was traced to incorrect smoothing parameters in the AdhesionMetricsCalculator:

### INCORRECT SETTINGS (causing ~11.8s):
```python
self.calculator = AdhesionMetricsCalculator(
    smoothing_window=11,        # HEAVY smoothing
    smoothing_polyorder=2,      # Quadratic polynomial
    baseline_threshold_factor=0.002,
    min_peak_height=0.01,
    min_peak_distance=50
)
```

### CORRECT SETTINGS (producing accurate ~11.7s):
```python
self.calculator = AdhesionMetricsCalculator(
    smoothing_window=3,         # LIGHT smoothing
    smoothing_polyorder=1,      # Linear polynomial
    baseline_threshold_factor=0.002,
    min_peak_height=0.01,
    min_peak_distance=50
)
```

## TECHNICAL EXPLANATION
The propagation end detection uses second derivative analysis of the force curve. Heavy smoothing (window=11, polyorder=2) was:

1. **Over-smoothing the force data**: Removing important fine-scale features needed for accurate derivative calculation
2. **Shifting derivative peaks**: The large smoothing window displaced the second derivative maximum
3. **Reducing sensitivity**: Making the detection less responsive to actual propagation characteristics

Light smoothing (window=3, polyorder=1) preserves the essential force curve characteristics while removing noise, allowing accurate second derivative peak detection.

## VERIFICATION RESULTS
With corrected settings:
- **Layer 198**: Propagation End = 11.719s (calc) → 11.704s (plot) ≈ **11.7s** ✅
- **Layer 199**: Propagation End = 7.513s (calc) → 25.838s (plot) ✅  
- **Layer 200**: Propagation End = 7.577s (calc) → 40.144s (plot) ✅

## FILES CORRECTED
1. **adhesion_metrics_calculator.py**: Default parameters corrected to light smoothing
2. **hybrid_adhesion_plotter.py**: Calculator initialization corrected to light smoothing  
3. **test_adhesion_calculator_with_derivatives.py**: Test calculator updated to match production settings

## LESSON LEARNED
**Smoothing parameters must be carefully tuned for derivative-based analysis**:
- Too little smoothing: Noise affects derivative calculation
- Too much smoothing: Signal features are lost, derivatives are displaced
- **Optimal**: Minimal smoothing (window=3, polyorder=1) that removes noise while preserving signal fidelity

## BACKUP LOCATION
Corrected files backed up to: `backup_corrected_system_20250921/`

## TESTING VALIDATION
- Test calculator with derivatives shows accurate propagation end detection at ~11.7s
- Hybrid plotter produces correct plot with propagation end at index 395 (11.704s)
- Debug scripts confirm time conversion accuracy
- Visual verification: Propagation end markers align with expected values

Author: Cheng Sun Lab Team
Date: September 21, 2025
Status: RESOLVED ✅
