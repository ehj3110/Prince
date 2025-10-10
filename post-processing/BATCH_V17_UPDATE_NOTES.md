# Batch V17 Analysis - Update Summary

## Date: October 2, 2025

## Changes Made to `batch_v17_analysis.py`

### 1. **Modernized Import Structure**
- **OLD:** Used deprecated `HybridAdhesionPlotter`
- **NEW:** Uses modern trio:
  - `AdhesionMetricsCalculator` (from support_modules)
  - `AnalysisPlotter` (from post-processing)
  - `RawDataProcessor` (from post-processing)

### 2. **Updated Initialization**
```python
# OLD (deprecated):
self.plotter = HybridAdhesionPlotter(
    figure_size=(20, 14),
    dpi=150,
    smoothing_window=3,      # Wrong parameter
    smoothing_polyorder=1    # Wrong parameter
)

# NEW (modern):
self.calculator = AdhesionMetricsCalculator(smoothing_sigma=0.5)
self.plotter = AnalysisPlotter(figure_size=(16, 12), dpi=150)
self.processor = RawDataProcessor(self.calculator, self.plotter)
```

### 3. **Updated Processing Logic**
- **OLD:** Called `plotter.plot_from_csv()` directly - no metrics extraction
- **NEW:** Uses `processor.process_csv()` which:
  - Detects layer boundaries automatically
  - Calculates adhesion metrics for each layer
  - Generates comprehensive plots
  - Returns layer objects with all metrics

### 4. **Added Metrics Collection**
Now collects for each layer:
- Peak force
- Baseline force
- Work of adhesion (corrected, in mJ)
- Pre-initiation duration
- Propagation duration
- Max derivative
- Failure rate
- Step speed (from instruction file)
- Test metadata (fluid type, gap, test type, resin)

### 5. **Added CSV Export Feature**
New `export_results_to_csv()` method that:
- Exports all collected metrics to timestamped CSV file
- Saves in master folder: `V17_batch_results_YYYYMMDD_HHMMSS.csv`
- Prints summary statistics (mean ± std for WoA and peak force)
- Shows count of unique test conditions and total layers

## Benefits of Updates

### ✅ Consistency
- Same processing pipeline as `run_full_analysis.py`
- Uses proven layer boundary detection
- Consistent smoothing (sigma=0.5)

### ✅ Better Metrics
- Automatic layer boundary detection using stage motion
- Robust propagation end detection via second derivative
- Baseline calculation from post-propagation region

### ✅ Data Export
- All metrics automatically saved to CSV
- Easy to import into Excel, Python, R for further analysis
- Includes test metadata for correlation analysis

### ✅ Better Error Handling
- More detailed progress reporting
- Layer-by-layer metric summaries printed
- Continues processing if one file fails

## Usage

### Run Full Batch Processing:
```bash
cd post-processing
python batch_v17_analysis.py
```

### Test on Single Folder First:
```bash
python test_batch_v17.py
```
Edit the test script to specify a single folder for testing before running the full batch.

## Output Files

### For Each Autolog File:
- **Plot:** `FluidType_Gap_TestType_LX-LY.png`
  - Comprehensive multi-panel analysis plot
  - Overview + individual layer details
  - Shaded peeling stages
  - Metric annotations

### At End of Batch:
- **CSV:** `V17_batch_results_YYYYMMDD_HHMMSS.csv`
  - All metrics from all layers
  - Test metadata for grouping/filtering
  - Ready for statistical analysis

## Example Output Row in CSV:
```
folder,fluid_type,gap,test_type,resin,layer_number,step_speed,peak_force,baseline_force,work_of_adhesion_mJ,pre_initiation_duration,propagation_duration,max_derivative,failure_rate
Water_1mm_Ramped_BPAGDA,Water,1mm,Ramped,BPAGDA,48,3000,0.2374,0.0402,0.172,0.960,0.186,0.0,0.0
```

## Testing Checklist

Before running full batch:
- [ ] Verify master folder path is correct
- [ ] Test imports work (run test_batch_v17.py)
- [ ] Test single folder processing
- [ ] Check that plots are generated correctly
- [ ] Verify CSV export contains expected columns
- [ ] Review a few plots to ensure metrics look reasonable

## Notes

- The batch processor will skip folders that don't match naming convention
- Instruction files are optional - will still process without them
- All errors are caught and printed but processing continues
- Results are accumulated and exported even if some files fail
