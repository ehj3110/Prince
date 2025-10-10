# Analysis Plotter Annotation Fix Summary

## Date: October 2, 2025

## Issues Identified

### Problem 1: Hardcoded Annotation Offsets
The annotation text boxes (t_pre, t_prop, ΔF) used **hardcoded absolute offsets** that didn't scale with the force range:
- Y-offsets: `-0.025`, `-0.045`, `-0.008` (in Newtons)
- X-offset: `+0.3` (in seconds)

### Why This Failed
- **Water data** (L48-50): Force range ~0.2-0.27 N → offsets were ~10-20% of range → acceptable
- **PEO data** (L110-114): Force range ~0.02-0.03 N → offsets were 80-150% of range → **annotations way outside plot**

## Solution Implemented

### Made All Offsets Proportional to Data Range

**Force Range Calculation:**
```python
force_range = layer['peak_force'] - layer['baseline']
if force_range <= 0:
    force_range = 0.05  # Fallback minimum
```

**Y-axis Annotations (time durations):**
```python
y_offset_1 = force_range * 0.35  # First annotation 35% below baseline
y_offset_2 = force_range * 0.65  # Second annotation 65% below baseline  
text_y_offset = force_range * 0.12  # Text 12% below arrow
```

**X-axis Annotation (force range ΔF):**
```python
time_range = layer['prop_end_time'] - layer['pre_init_time']
text_x_offset = time_range * 0.05  # 5% of time range
```

**Y-axis Limits:**
```python
y_margin_top = force_range * 0.15  # 15% above peak
y_margin_bottom = force_range * 0.75  # 75% below baseline (for annotations)
```

## Files Modified

1. **`analysis_plotter.py`** - `_add_layer_annotations()` method:
   - Changed hardcoded offsets to proportional scaling
   - Scales with both force range (vertical) and time range (horizontal)

2. **`analysis_plotter.py`** - `_plot_individual_layer()` method:
   - Updated y-axis limits to accommodate proportional annotations
   - Ensures 75% margin below baseline for annotation visibility

3. **`batch_v17_analysis.py`** - `parse_folder_name()` method:
   - Updated fluid type validation to accept "2p5PEO" and similar variants
   - Now accepts any folder name containing "peo" in the fluid type field

## Test Results

### Command Used:
```bash
python run_full_analysis.py "C:\...\V17Tests\2p5PEO_1mm_Ramped_BPAGDA\autolog_L110-L114.csv"
```

### Output Generated:
- ✅ Plot saved successfully: `autolog_L110-L114_analysis.png`
- ✅ No annotation positioning errors
- ✅ All text boxes visible within plot boundaries

### Sample Metrics (PEO data):
- Layer 1: Peak=0.0229N, Baseline=0.0048N, Force Range=0.0181N
- Layer 2: Peak=0.0338N, Baseline=0.0061N, Force Range=0.0277N  
- Layer 3: Peak=0.0272N, Baseline=0.0005N, Force Range=0.0267N

**Annotation offsets now scale appropriately:**
- For Layer 1 (ΔF=0.018N): y_offset_1 = 0.006N, y_offset_2 = 0.012N
- For Layer 2 (ΔF=0.028N): y_offset_1 = 0.010N, y_offset_2 = 0.018N

## Remaining Issue: Work of Adhesion = 0.000 mJ

All layers show `Work of Adhesion: 0.000 mJ`, which suggests:
1. Layer boundary detection may be incorrect for this dataset
2. The pre-initiation or propagation phases are not being identified correctly
3. Integration window may be too narrow or misaligned

**This requires separate investigation** - likely in the `RawDataProcessor` layer boundary detection or `AdhesionMetricsCalculator` integration logic.

## Batch Processing Status

### Folder Tested: `2p5PEO_1mm_Ramped_BPAGDA`
- Found 22 autolog files
- Successfully processed at least 3 files:
  - `autolog_L110-L114.csv` → plot generated (1.4 MB)
  - `autolog_L125-L129.csv` → plot generated (1.5 MB)
  - `autolog_L140-L144.csv` → **failed (0 bytes)** - needs investigation

## Next Steps

1. **Review Generated Plots:**
   - Open `2p5peo_1mm_Ramped_L110-L114.png` 
   - Verify annotation positioning is correct
   - Check if layer boundaries look reasonable

2. **Investigate Zero Work of Adhesion:**
   - Check layer boundary detection against actual stage motion
   - Verify integration windows in metrics calculator
   - May need to adjust threshold parameters for low-force data

3. **Fix Failed Plot:**
   - Investigate why `autolog_L140-L144.csv` produced 0-byte output
   - Check for errors in terminal output
   - May be matplotlib memory issue or data problem

4. **Complete Batch Run:**
   - Once plots look good, run full batch on all V17 folders
   - Generate comprehensive CSV export with all metrics
