# Baseline Detection Test Tool

**Created**: October 2, 2025  
**Purpose**: Visualize force data and derivatives to evaluate baseline detection methods

## Overview

`test_baseline_detection.py` is a diagnostic tool that extracts data for a specific layer and plots:
1. Raw and smoothed force data
2. First derivative of smoothed force (dF/dt)
3. Second derivative of smoothed force (d²F/dt²)

This helps evaluate when the baseline force is reached after crack propagation.

## Usage

### Basic Usage (Layer 111 in working folder)

```powershell
cd "C:\Users\ehunt\OneDrive\Documents\Prince\Prince_Segmented_20250926\post-processing"
python test_baseline_detection.py
```

### Customization

To test a different layer or folder, edit the configuration in `main()`:

```python
# Configuration
master_folder = r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\V17Tests"
working_folder = "2p5PEO_1mm_Ramped_BPAGDA_Old"  # Change folder here
target_layer = 111  # Change layer number here
```

## Output

### Plot File
`baseline_test_L{layer_number}.png` saved in the `post-processing` directory.

### Plot Contents

**Panel 1 - Force Data**
- Gray line: Raw force data
- Blue line: Smoothed force (Gaussian, σ=0.5)
- Shows the adhesion peak and return to baseline

**Panel 2 - First Derivative (dF/dt)**
- Green line: Rate of force change
- **Positive**: Force increasing (crack initiation)
- **Zero crossing (pos→neg)**: Peak force reached
- **Negative**: Force decreasing (crack propagation)
- **Zero crossing (neg→pos)**: Baseline potentially reached

**Panel 3 - Second Derivative (d²F/dt²)**
- Red line: Acceleration of force change
- **Zero crossings**: Inflection points in force curve
- **Stable near zero**: Indicates force has stabilized (potential baseline)

## Interpreting Results for Baseline Detection

### Current Method
The current baseline is measured at the **propagation end** point, which is found by searching backward from the end of the lift motion for where the second derivative stabilizes.

### Evaluation Points

1. **Too Early**: If baseline is detected while force is still decreasing (first derivative still negative), the baseline will be too high.

2. **Too Late**: If baseline is detected after force has started increasing again (retraction phase), the baseline may be affected by retraction forces.

3. **Ideal**: Baseline should be where:
   - First derivative ≈ 0 (force not changing)
   - Second derivative ≈ 0 (force change rate stable)
   - Force has reached a steady value

### Potential Alternative Methods

After viewing the derivatives, you might consider:

1. **Zero-crossing of first derivative** (from negative to positive after peak)
   - Pro: Clearly marks when force stops decreasing
   - Con: May be sensitive to noise

2. **Second derivative stabilization** (current method)
   - Pro: Identifies when force change rate stabilizes
   - Con: May be too late if retraction has started

3. **Hybrid method**: First derivative crosses zero AND second derivative is stable
   - Pro: Combines both indicators
   - Con: More complex to implement

4. **Fixed time/distance after peak**
   - Pro: Simple and consistent
   - Con: May not adapt to different propagation speeds

## Example Session

```powershell
PS> cd post-processing
PS> python test_baseline_detection.py

================================================================================
BASELINE DETECTION TEST
================================================================================
Target layer: 111
Working folder: 2p5PEO_1mm_Ramped_BPAGDA_Old

Found autolog file: autolog_L110-L114.csv
Detected 5 peaks in file
Found 6 layer boundaries
Layer 111 data: indices 1079 to 2165
Extracted 1087 data points for layer 111

Plot saved to: C:\...\post-processing\baseline_test_L111.png

[OK] Baseline test completed successfully!
```

## Next Steps

1. Run the script and examine the plot
2. Identify where you think the baseline should be detected
3. Compare with current propagation_end detection
4. Propose new baseline detection logic based on derivative patterns
5. Implement and test new method in AdhesionMetricsCalculator

## Related Files

- `support_modules/adhesion_metrics_calculator.py` - Current baseline calculation
- `post-processing/RawData_Processor.py` - Layer boundary detection
- `post-processing/test_baseline_detection.py` - This diagnostic tool
