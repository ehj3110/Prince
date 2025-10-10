# Adhesion Calculator Status and Differences

**Date**: October 10, 2025

## Summary of Changes Made Today

### 1. Added Colors Back to Master Plots ✅
- **Issue**: All plots were showing in black and white, making it impossible to distinguish between conditions
- **Solution**: 
  - Updated color map in `batch_process_steppedcone.py` to include all V2 conditions:
    - `2p5PEO_1mm_1000um_s`: Blue (#0000FF)
    - `Water_1mm_1000um_s`: Red (#FF0000)
    - `Water_1mm_3000um_s`: Green (#00CC00)
    - `Water_1mm_6000um_s`: Magenta (#FF00FF)
  - Added automatic color assignment for any unmapped conditions
  - Each condition now has a distinct color with different line styles (solid for PEO, dashed for Water)

### 2. Confirmed Individual Layer Plots Are Being Generated ✅
- **Status**: Individual layer plots ARE being created for each autolog file
- **Location**: Each condition folder has a `plots/` subdirectory
- **Example**: `C:\...\2p5PEO_1mm_SteppedCone_BPAGDA_1000\plots\`
- **Files**: `autolog_L100-L105_analysis.png`, etc.
- **Code**: Line 165 in `batch_process_steppedcone.py` passes `save_path` to `processor.process_csv()`

## Adhesion Metrics Calculator Files - Key Differences

### Current Active File: `adhesion_metrics_calculator.py`
- **Date**: September 19, 2025 (newer)
- **Status**: CURRENTLY IN USE by all processing scripts
- **Features**:
  - Uses **Gaussian smoothing only** (`smoothing_sigma` parameter)
  - Reverse-search propagation end detection (searches backward from end of motion)
  - Second-derivative based propagation end detection
  - Methods: `calculate_from_arrays()`, `calculate_from_dataframe()`, `calculate_from_csv()`
  - Returns comprehensive metrics dictionary with standardized naming

### Legacy File: `enhanced_adhesion_metrics.py`
- **Date**: September 15, 2025 (older)
- **Status**: WRAPPER/ADAPTER - redirects to `adhesion_metrics_calculator.py`
- **Purpose**: Backward compatibility adapter
- **Function**: The `EnhancedAdhesionAnalyzerAdapter` class simply wraps `AdhesionMetricsCalculator`
- **Recommendation**: This file is for legacy compatibility only; use `adhesion_metrics_calculator.py` directly

## Current Metrics Being Calculated

Based on the V2 processing output, the following metrics are being calculated correctly:

### Force Metrics
- `peak_force_N`: Maximum force during peel (0.13-0.26 N range for V2 data) ✅
- `peak_retraction_force_N`: Baseline-corrected peak force ✅
- `baseline_force`: Force at propagation end ✅

### Work/Energy Metrics
- `work_of_adhesion_mJ`: Total work during peel ✅
- `work_of_adhesion_corrected_mJ`: Baseline-corrected work ✅
  - **Note**: RawData_Processor stores this as `work_of_adhesion_mJ` in layer object
- Range for V2 data: 0.13-0.36 mJ ✅

### Distance Metrics
- `total_peel_distance`: Full peel distance (mm)
- `pre_initiation_distance`: Distance from baseline to peak (mm)
- `propagation_distance`: Distance from peak to propagation end (mm)
- **Note**: All distances are negative because stage moves down (decreasing position)
  - Batch processor takes absolute value for plotting

### Time Metrics
- `pre_initiation_time`: Time at start of peel
- `propagation_end_time`: Time when propagation ends
- `pre_initiation_duration`: Time to reach peak
- `propagation_duration`: Time for crack to propagate

### Quality Metrics
- `signal_to_noise_ratio`: Data quality indicator
- `peak_sharpness`: How distinct the peak is

## Data Flow in Batch Processing

1. **Batch Processor** (`batch_process_steppedcone.py`):
   - Calls `RawData_Processor.process_csv()` for each autolog file
   - Passes `save_path` for individual plots

2. **RawData Processor** (`post-processing/RawData_Processor.py`):
   - Finds layer boundaries using position/time patterns
   - Calls `AdhesionMetricsCalculator.calculate_from_arrays()` for each layer
   - Creates layer object with metrics
   - Calls `AnalysisPlotter.create_plot()` to generate individual plots

3. **Adhesion Calculator** (`support_modules/adhesion_metrics_calculator.py`):
   - Applies Gaussian smoothing
   - Finds peak force
   - Detects propagation end (reverse search method)
   - Calculates all metrics
   - Returns metrics dictionary

4. **Analysis Plotter** (`post-processing/analysis_plotter.py`):
   - Creates detailed 3-panel plots for each autolog file
   - Saves to `plots/` subdirectory in each condition folder

## Known Issues and Considerations

### 1. Negative Distance Values
- **Cause**: Stage moves DOWN during peel (position decreases)
- **Effect**: All distance metrics are negative
- **Solution**: Batch processor takes `abs()` when plotting
- **Status**: This is expected behavior, not a bug

### 2. Metric Naming Consistency
- Layer object stores: `work_of_adhesion_mJ` (from `work_of_adhesion_corrected_mJ`)
- This is intentional - we want the baseline-corrected value
- **Status**: Working as intended

### 3. Speed Effect Observed in V2 Data
- Water @ 1000 μm/s: 0.132 ± 0.029 N, 0.128 ± 0.041 mJ
- Water @ 3000 μm/s: 0.213 ± 0.100 N, 0.234 ± 0.126 mJ
- Water @ 6000 μm/s: 0.241 ± 0.079 N, 0.359 ± 0.152 mJ
- **Observation**: Higher peel speed → higher forces and work
- **Interpretation**: Consistent with viscoelastic behavior ✅

## Recommendations

1. **Use `adhesion_metrics_calculator.py` directly** - it's the current, maintained version
2. **Individual layer plots are working** - check the `plots/` subdirectories in each condition folder
3. **Colors are now active** - master plots should show different colors for each condition
4. **Distance signs are correct** - negative values indicate downward motion (expected)

## Files Modified Today (October 10, 2025)

1. `batch_process_steppedcone.py`:
   - Updated color map to include V2 conditions
   - Added automatic color assignment for unmapped conditions
   - Applied to both area analysis and distance analysis plots
   - Individual plot generation was already working (no changes needed)

---

**Next Steps**: 
- Review the newly colored master plots to confirm different conditions are distinguishable
- Check individual layer plots in `plots/` subdirectories for detailed analysis
- If metrics still look wrong, compare with original SteppedConeTests results from Oct 7
