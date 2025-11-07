# Post-Print Plot Generation Fix

**Date**: October 9, 2025  
**Summary**: Fixed plot generation errors and updated post-print analysis to use RawDataProcessor workflow (same as batch processing).

---

## Issue: Plot Generation Failed with AttributeError

### Error Message
```
Warning: Plot generation failed: 'AdhesionMetricsCalculator' object has no attribute 'apply_smoothing'
```

### Root Cause
Two files were calling `apply_smoothing()` as a public method, but it's actually defined as `_apply_smoothing()` (private method with underscore prefix) in `AdhesionMetricsCalculator`.

**Files with incorrect calls:**
1. `hybrid_adhesion_plotter.py` - Line 146
2. `post-processing/RawData_Processor.py` - Line 28

### Fix Applied
Changed both files to call the correct private method:
```python
# BEFORE (incorrect)
smoothed_force = self.calculator.apply_smoothing(force_data)

# AFTER (correct)
smoothed_force = self.calculator._apply_smoothing(force_data)
```

---

## Enhancement: Updated Post-Print Analysis Workflow

### User Request
> "Can you please have the script that generates plots after printing do so in a similar manner to how our batch processing used to work? I do not see the batch processing script anymore, but I know that it was using the RawData_Processor."

### Changes Made

#### 1. Updated `post_print_analyzer.py`
Changed from using `HybridAdhesionPlotter` directly to using the **RawDataProcessor workflow** (same as `batch_process_printing_data.py` and `run_post_analysis.py`):

**Before:**
```python
from hybrid_adhesion_plotter import HybridAdhesionPlotter

class PostPrintAnalyzer:
    def __init__(self):
        self.calculator = AdhesionMetricsCalculator(...)
        self.plotter = HybridAdhesionPlotter()
    
    def _analyze_csv_file(self, csv_file, output_dir):
        # Direct plotting with hybrid plotter
        fig = self.plotter.plot_from_csv(...)
```

**After:**
```python
from RawData_Processor import RawDataProcessor
from analysis_plotter import AnalysisPlotter

class PostPrintAnalyzer:
    def __init__(self):
        self.calculator = AdhesionMetricsCalculator(...)
        self.plotter = AnalysisPlotter()
        self.processor = RawDataProcessor(self.calculator, self.plotter)
    
    def _analyze_csv_file(self, csv_file, output_dir):
        # Use RawDataProcessor to handle everything
        layers = self.processor.process_csv(...)
```

#### 2. Benefits of RawDataProcessor Workflow

The RawDataProcessor approach provides:
- ✅ **Automatic layer detection** - No manual peak finding needed
- ✅ **Layer boundary segmentation** - Intelligent pause/retraction detection
- ✅ **Consistent with batch processing** - Same code path as manual analysis
- ✅ **Comprehensive plots** - Multi-panel visualizations with all layers
- ✅ **Metric calculations** - Per-layer adhesion metrics automatically computed

#### 3. Workflow Comparison

**Old Workflow (HybridAdhesionPlotter):**
```
CSV File → Load Data → HybridAdhesionPlotter → Single Plot
```

**New Workflow (RawDataProcessor - same as batch processing):**
```
CSV File → RawDataProcessor → Layer Detection → Boundary Finding → 
   → Calculator (per layer) → AnalysisPlotter → Comprehensive Multi-Layer Plot
```

---

## Files Modified

### Core Fixes
1. **`hybrid_adhesion_plotter.py`** (Line 146)
   - Changed `self.calculator.apply_smoothing()` → `self.calculator._apply_smoothing()`

2. **`post-processing/RawData_Processor.py`** (Line 28)
   - Changed `self.calculator.apply_smoothing()` → `self.calculator._apply_smoothing()`

### Workflow Update
3. **`post_print_analyzer.py`** (Lines 1-310)
   - Updated imports to use RawDataProcessor and AnalysisPlotter
   - Modified `__init__()` to create RawDataProcessor instance
   - Simplified `_analyze_csv_file()` to delegate to RawDataProcessor
   - Removed redundant `_extract_layer_analysis()` method (handled by RawDataProcessor)
   - Updated session summary generation

---

## Batch Processing Scripts Available

For reference, these batch processing scripts use the same RawDataProcessor workflow:

1. **`batch_process_printing_data.py`** - General batch processing for printing logs
2. **`batch_process_steppedcone.py`** - Specialized for stepped cone prints
3. **`post-processing/run_post_analysis.py`** - Automated post-processing controller

All use the pattern:
```python
from RawData_Processor import RawDataProcessor
processor = RawDataProcessor(calculator, plotter)
layers = processor.process_csv(csv_filepath, title, save_path)
```

---

## Testing

The post-print analysis will now:
1. ✅ No longer throw `AttributeError` for `apply_smoothing`
2. ✅ Generate plots using the same method as batch processing
3. ✅ Automatically detect and segment layers
4. ✅ Create comprehensive multi-panel visualizations
5. ✅ Save plots with consistent naming: `autolog_LX-LY_analysis.png`

### Expected Output
When running a print, the post-processing will now show:
```
Processing: autolog_L60-L65.csv
    Processing: autolog_L60-L65.csv
Detected layers from filename: [60, 61, 62, 63, 64, 65]
Detected 5 peaks at indices: [...]
Found 5 layer starts at indices: [...]
    📊 Plot saved: autolog_L60-L65_analysis.png
    ✅ Analysis complete - 5 layers processed
```

---

## Notes

- **Import warnings** in linter are expected (files are in dynamic paths)
- **RawDataProcessor** handles all layer detection, boundary finding, and metric calculation
- **AnalysisPlotter** creates the multi-panel plots with all layers visualized
- **Consistent methodology** across live printing, post-processing, and batch analysis

No configuration changes needed - the system will automatically use the new workflow! 🎉
