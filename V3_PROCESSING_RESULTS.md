# V3 Processing Results - October 27, 2025

## Summary

✅ **Successfully Processed:** 174 layers across 3 conditions  
❌ **Failed to Process:** ACF_5mm_SteppedCone_BPAGDA_200 (data quality issue)

## Successfully Generated Files

### Master CSV
- **Location:** `C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V3\MASTER_steppedcone_metrics.csv`
- **Rows:** 174 layers
- **Columns:** folder_name, layer_number, condition_label, fluid_type, gap_mm, speed_um_s, area_mm2, peak_force_N, work_of_adhesion_mJ, peel_distance_mm, peak_retraction_force_N, distance_to_peak_mm, propagation_distance_mm, effective_stiffness_N_per_mm, stiffness_r_squared

### Master Plots (Area-Based Analysis with Colored Bands)
1. **MASTER_area_analysis.png** - 4 subplots:
   - Peak Force vs Area
   - Work of Adhesion vs Area
   - Peel Distance vs Area
   - Peak Retraction Force vs Area

2. **MASTER_area_distance_analysis.png** - 2 subplots:
   - Distance to Peak vs Area
   - Propagation Distance vs Area

3. **MASTER_stiffness_analysis.png** - 1 subplot:
   - Effective Stiffness vs Area

### Individual Layer Plots
Each folder contains a `plots/` subdirectory with individual analysis plots for each layer range.

## Processed Conditions

| Condition | Layers | Area Range (mm²) | Peak Force (N) | Work of Adhesion (mJ) |
|-----------|--------|------------------|----------------|-----------------------|
| 2p5PEO_1mm_1000um_s | 54 | 9.90 - 77.15 | 0.2534 ± 0.1014 | 0.0559 ± 0.0357 |
| TEMPOV2_1mm_1000um_s | 60 | 9.90 - 99.72 | 0.1319 ± 0.0182 | 0.0447 ± 0.0192 |
| Water_1mm_1000um_s | 60 | 9.90 - 99.72 | 0.1241 ± 0.0265 | 0.0414 ± 0.0194 |

## ACF Data Issue 🚨

### Problem Description
The ACF_5mm_SteppedCone_BPAGDA_200 folder contains 10 autolog CSV files, but they **do not contain valid adhesion test data**. Analysis of the files reveals:

- **Position Range:** 78.47 - 81.77 mm (only 3.3mm total, mostly constant)
- **No Adhesion Cycles:** No ~6mm lifting/retracting motions detected
- **Static Position:** Position values remain mostly constant at ~81.6-81.8mm
- **Time Range:** 0 - 212 seconds per file
- **Force Data:** Present but with no corresponding position changes

### Expected vs Actual
**Expected:** Adhesion test data with:
- 6 layers per file
- ~6mm lifting motions (adhesion/peel phase)
- ~6mm retraction motions (return to baseline)
- Clear force peaks during lifting

**Actual:** What appears to be:
- Baseline/calibration data only
- No stage movement (position constant)
- Force measurements at static position
- Possibly incomplete data logging

### Possible Causes
1. **Incomplete Data Logging:** The old code version may have failed to log position data properly
2. **Baseline-Only Files:** These may be calibration/baseline files, not actual test data
3. **Stage Malfunction:** The motion stage may not have moved during these tests
4. **Wrong Files:** The actual test data may be in different files not included in this folder

### Next Steps for ACF Data

1. **Check for Additional Files:** Look for other ACF data files that may contain the actual test data
2. **Review Test Log:** Check if there's a lab notebook or test log from May 20, 2025 (file timestamp) that describes what was run
3. **Inspect Original Data:** Verify if these are the complete/correct files for this experiment
4. **Contact Original Experimenter:** If someone else collected this data, check with them about the test setup

## Plot Format

All master plots follow the same style as V2 processing:
- **Colored bands:** SEM (Standard Error of Mean) shading for each condition
- **Trendlines:** Polynomial fit (degree 2) for each dataset
- **Data points:** Individual area measurements shown as markers
- **Consistent formatting:** Matching V2 plot aesthetics

## Script Used

**File:** `batch_process_v3.py`  
**Based on:** `batch_process_steppedcone.py` (V2 processor)  
**Key Features:**
- Identical processing logic to V2
- Configured for V3 directory path
- Handles variable speeds (200-1000 µm/s)
- Handles variable gaps (1mm, 5mm)
- Uses same area mapping file (`LayerToArea.txt`)

## Files Created

1. `batch_process_v3.py` - V3 processing script
2. `V3_PROCESSING_SUMMARY.md` - Processing documentation
3. `v3_processing_log.txt` - Complete processing log
4. `analyze_acf_motion.py` - ACF data diagnostic script
5. `ACF_data_overview.png` - Diagnostic plot showing ACF position/force over time

## Recommendations

### For Current Analysis
Use the successfully processed data from the 3 conditions (2p5PEO, TEMPOV2, Water). The master plots and CSV are ready for analysis.

### For ACF Data
**Priority 1:** Locate the actual ACF adhesion test data files  
**Priority 2:** Verify the test was properly executed on May 20, 2025  
**Priority 3:** If no other files exist, consider re-running the ACF test with current code version

### For Future V3 Work
- The processing pipeline is ready for additional folders
- Simply add new folders to V3 directory and re-run `batch_process_v3.py`
- All plots will automatically update to include new conditions

## Contact Information

If you find the correct ACF data files or have questions about the processing:
1. Place corrected files in the ACF folder
2. Re-run: `python batch_process_v3.py`
3. The script will automatically reprocess everything including ACF data

---

**Processing Date:** October 27, 2025  
**Total Processing Time:** ~15-20 minutes  
**Script Version:** Based on batch_process_steppedcone.py (V2)
