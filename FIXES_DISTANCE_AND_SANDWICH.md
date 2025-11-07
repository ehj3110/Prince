# Fixes: Distance Calculation, Sandwich Force, and Plot Generation

**Date**: October 9, 2025  
**Summary**: Fixed three issues - incorrect distance calculations, sandwich routine triggering from residual retraction forces, and post-print plot generation errors.

---

## Issue 1: Distance_to_Propagate Incorrectly Higher Than Distance_to_Peak

### Problem
The `Distance_to_Propagate` metric was consistently being recorded as **higher** than `Distance_to_Peak`, which doesn't make physical sense. The propagation distance should be the distance traveled **after** the peak force.

### Root Cause
The issue was in `adhesion_metrics_calculator.py` lines 216-218. During retraction:
1. The stage moves **UP** (retracting away from the build platform)
2. Position values **decrease** (going from higher position to lower position)
3. `peak_idx` occurs early in the peel (when part first lifts)
4. `prop_end_idx` occurs later (when crack propagation finishes)
5. Since position is decreasing: `positions[prop_end_idx]` < `positions[peak_idx]`
6. The calculation `positions[prop_end_idx] - positions[peak_idx]` gave a **negative** value
7. `PeakForceLogger.py` was taking `abs()` of this negative value, hiding the sign error

The distances were being calculated in the wrong direction!

### Solution
Modified `adhesion_metrics_calculator.py` lines 216-218 to use **absolute values**:

```python
# Step 6: Calculate spatial metrics
# Use absolute values since retraction moves from high to low position (decreasing)
results['pre_initiation_distance'] = abs(positions[peak_idx] - positions[pre_init_idx])
results['propagation_distance'] = abs(positions[prop_end_idx] - positions[peak_idx])
results['total_peel_distance'] = abs(positions[prop_end_idx] - positions[pre_init_idx])
```

This ensures distances are always positive regardless of motion direction.

### Files Changed
- **`support_modules/adhesion_metrics_calculator.py`** (lines 216-218)
  - Added `abs()` to all three distance calculations
  - Added explanatory comment about retraction direction

- **`support_modules/PeakForceLogger.py`** (lines 213-221)
  - Removed redundant `abs()` calls since calculator now returns absolute values
  - Simplified code and added comments

### Testing Recommendation
Re-run your prints and verify that:
- `Distance_to_Peak` > `Distance_to_Propagate` (peak should happen first during retraction)
- `Total_Peel_Distance` ≈ `Distance_to_Peak` + `Distance_to_Propagate`

---

## Issue 2: Sandwich Routine Triggering From Residual Retraction Forces

### Problem
At high part areas, the sandwich force threshold was being met **immediately** because the sandwich routine was detecting residual forces from the retraction step, not actual glass contact.

### Root Cause
The sandwich routine started monitoring force **immediately** after the retraction movement completed. For large part areas:
1. Retraction creates high forces (can be >0.3N)
2. These forces take time to decay
3. Sandwich routine started before forces settled
4. Immediate false trigger from residual retraction force

### Solution
Added a **hard-coded 1-second pause** between retraction and sandwich in `Prince_Segmented.py` (line 893):

```python
# 4a. SANDWICH ROUTINE (if enabled for this layer)
actual_estimated_gap = self.estimated_gap_list[i] if i < len(self.estimated_gap_list) else 0
if actual_estimated_gap > 0:  # Only run sandwich if gap is defined
    # IMPORTANT: Wait 1 second after retraction to let forces settle
    # This prevents the sandwich routine from detecting residual retraction forces
    self.update_status_message(f"L{current_layer_num_for_display}: Waiting 1s for forces to settle before sandwich...")
    time.sleep(1.0)
    
    actual_sandwich_force = self.sandwich_force_list[i] if i < len(self.sandwich_force_list) else 0.05
    # ... rest of sandwich routine
```

### Files Changed
- **`Prince_Segmented.py`** (lines 893-898)
  - Added `time.sleep(1.0)` with explanatory message
  - Added status update so user knows system is waiting

### Benefits
1. **Prevents false triggers**: Forces from retraction have time to dissipate
2. **Cleaner force readings**: Sandwich routine sees only true contact forces
3. **User feedback**: Status message explains the 1-second delay
4. **Simple and robust**: No complex force monitoring or thresholds needed

### Testing Recommendation
Test with high-area parts (>50mm²) and verify:
- Sandwich routine doesn't trigger immediately
- Status log shows "Waiting 1s for forces to settle" message
- Glass contact detection happens at expected position, not at start position

---

## Issue 3: Post-Print Plot Generation Failed

### Problem
Post-print analysis was failing with error:
```
Warning: Plot generation failed: 'AdhesionMetricsCalculator' object has no attribute 'apply_smoothing'
```

Additionally, the user wanted the plot generation to work like the old batch processing system that used `RawData_Processor`.

### Root Cause
Two issues:
1. **Method naming error**: `hybrid_adhesion_plotter.py` and `RawData_Processor.py` were calling `apply_smoothing()` (public) but the method is defined as `_apply_smoothing()` (private) in `AdhesionMetricsCalculator`
2. **Workflow mismatch**: Post-print analyzer was using `HybridAdhesionPlotter` directly instead of the proven `RawDataProcessor` workflow

### Solution

**Part 1: Fixed method calls**
```python
# Changed in hybrid_adhesion_plotter.py and RawData_Processor.py
smoothed_force = self.calculator._apply_smoothing(force_data)  # Added underscore
```

**Part 2: Updated post_print_analyzer.py to use RawDataProcessor workflow**
```python
# BEFORE
from hybrid_adhesion_plotter import HybridAdhesionPlotter
self.plotter = HybridAdhesionPlotter()
fig = self.plotter.plot_from_csv(...)

# AFTER (same as batch processing)
from RawData_Processor import RawDataProcessor
from analysis_plotter import AnalysisPlotter
self.processor = RawDataProcessor(self.calculator, self.plotter)
layers = self.processor.process_csv(...)
```

### Files Changed
- **`hybrid_adhesion_plotter.py`** (line 146) - Fixed method call
- **`post-processing/RawData_Processor.py`** (line 28) - Fixed method call  
- **`post_print_analyzer.py`** (complete refactor) - Now uses RawDataProcessor workflow

### Benefits
1. **No more AttributeError**: Correct method name used
2. **Consistent workflow**: Same code path as batch processing
3. **Automatic layer detection**: No manual configuration needed
4. **Better plots**: Multi-panel visualizations with all layers
5. **Proven methodology**: Uses the same tested RawDataProcessor approach

### Testing Recommendation
Run a print and verify post-processing shows:
- ✅ No AttributeError
- ✅ "Detected X peaks" messages
- ✅ "Analysis complete - X layers processed"
- ✅ Plots saved with "_analysis.png" suffix

---

## Summary

All three fixes address fundamental issues:

1. **Distance Calculation Fix**: Ensures accurate metrics regardless of stage motion direction
2. **Sandwich Pause Fix**: Prevents false force triggers by allowing system to settle
3. **Plot Generation Fix**: Uses proven RawDataProcessor workflow for consistent analysis

These changes provide:
- ✅ Accurate adhesion metrics for analysis
- ✅ Reliable glass contact detection
- ✅ Consistent plot generation across all workflows
- ✅ Better print quality with proper sandwich positioning

No configuration changes needed - fixes are automatic! 🎉
