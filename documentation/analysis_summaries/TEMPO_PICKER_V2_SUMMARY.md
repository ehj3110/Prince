# TEMPO Picker V2 Master Plot Generation Summary
**Date:** January 20, 2026  
**Task:** Generate master plots for TEMPO Picker V2 dataset

## Dataset Overview

**Location:** `C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\TEMPO Picker\V2`

### Experimental Conditions (6 total):
1. **10umTEMPO_400umGap** - 180 measurements
2. **5umTEMPO_200um** - 180 measurements  
3. **5umTEMPO_200umGap** - 180 measurements
4. **5umTEMPO_400umGap_Good** - 180 measurements
5. **FlatTEMPO_400umGap** - 180 measurements
6. **TEMPO_400umGap** - 180 measurements

**Total measurements:** 1,080 layers (6 conditions × 180 measurements each)

## Data Processing

### Input Files
Each subdirectory contained:
- `automated_work_of_adhesion.csv` - Pre-calculated metrics and area data
- `autolog_L*.csv` - Raw data files (not reprocessed)
- Individual analysis plots (already existed)

### Processing Steps
1. **Data Collection:** Read `automated_work_of_adhesion.csv` from each subfolder
2. **Column Standardization:** Renamed columns from Capital Case to lowercase with underscores
   - `Peak_Force_N` → `peak_force`
   - `Work_of_Adhesion_mJ` → `work_of_adhesion_corrected_mJ`
   - `Total_Peel_Distance_mm` → `total_peel_distance`
   - `Peak_Retraction_Force_N` → `peak_retraction_force_N`
   - `Cross_Sectional_Area_mm2` → `cross_sectional_area_mm2`
   - etc.
3. **Radius Calculation:** `radius_mm = sqrt(cross_sectional_area_mm2 / π)`
4. **Data Combination:** Merged all 6 conditions into single DataFrame
5. **Master Plot Generation:** Created 3 plot types (mean, median, log-log)

## Generated Files

### Data Files
- **MASTER_tempopicker_v2_combined.csv** (120 KB)
  - Combined data from all 6 conditions
  - 1,080 rows (180 per condition)
  - Includes: layer number, forces, adhesion metrics, areas, radii, condition labels

### Master Plots
All plots use **TEMPO Picker presentation style**:
- **Font sizes:** 27pt axis labels, 21pt titles, 15pt legends (bold), 15pt tick labels
- **Layout:** 2×2 subplots (4 metrics per plot)
- **Style:** Scatter markers, shaded error bands, power law trendlines
- **Colors:** tab10 colormap (distinct colors for 6 conditions)
- **Font:** Times New Roman

#### 1. MASTER_tempopicker_v2_mean_analysis.png (1.8 MB)
- **Aggregation:** Mean values at each radius
- **Error bands:** SEM (Standard Error of Mean)
- **Trendlines:** Power law fits (dotted lines)

**Metrics plotted:**
- Top-left: **Relative Peak Force** (normalized to max aggregated value)
- Top-right: **Work of Adhesion (mJ)**
- Bottom-left: **Total Peel Distance (mm)**
- Bottom-right: **Peak Retraction Force (N)**

#### 2. MASTER_tempopicker_v2_median_analysis.png (2.1 MB)
- **Aggregation:** Median values at each radius
- **Error bands:** MAD (Median Absolute Deviation)
- **Trendlines:** Power law fits (dotted lines)

**Same 4 metrics as mean plot**

#### 3. MASTER_tempopicker_v2_loglog_analysis.png (2.0 MB)
- **Aggregation:** Mean values at each radius
- **Axes:** Log-log scale (both x and y)
- **Error bands:** SEM on log scale
- **Trendlines:** Power law fits (dashed lines)

**Same 4 metrics as mean plot**

## Key Features

### Legend Entries
Each of the 6 conditions is labeled using the folder name:
- 10umTEMPO_400umGap
- 5umTEMPO_200um
- 5umTEMPO_200umGap
- 5umTEMPO_400umGap_Good
- FlatTEMPO_400umGap
- TEMPO_400umGap

### Plot Titles
Since there are more than 2 conditions (not a simple A vs B comparison), titles show only the metric name:
- "Relative Peak Force"
- "Work of Adhesion (mJ)"
- "Total Peel Distance (mm)"
- "Peak Retraction Force (N)"

*(For 2-condition plots like V2 SteppedCone, titles use "Water Vs. 2.5% PEO: {metric}" format)*

### Peak Force Normalization
**Relative Peak Force** is calculated as:
1. Aggregate peak force by radius for each condition (mean/median)
2. Find maximum of all aggregated values across all 6 conditions
3. Divide all peak force values by this maximum
4. Result: Highest data point ≈ 1.0, showing relative adhesion strength

### Data Coverage
Each condition has:
- **61 unique radius values** (from automated_work_of_adhesion.csv)
- Variable sample counts per radius point (typically 1-40 measurements)
- Radius range determined by contact area variations

## Script Information

**Generator script:** `generate_tempopicker_v2_master_plots.py`

**Plotting module:** `tempo_picker_plot_styles.py`
- `create_4subplot_mean_plot()` - Mean aggregation
- `create_4subplot_median_plot()` - Median aggregation
- `create_4subplot_loglog_plot()` - Log-log scale

**Usage:**
```python
python generate_tempopicker_v2_master_plots.py
```

The script automatically:
- Finds all subdirectories in TEMPO Picker V2 folder
- Loads data from each `automated_work_of_adhesion.csv`
- Standardizes column names
- Calculates radii
- Generates all 3 master plots
- Saves combined CSV

## Notes

### Warnings During Generation
- RuntimeWarnings for `log` of zero/negative values (expected for some data points)
- These occur when fitting power law trendlines but don't affect plot quality
- Warnings are suppressed in final runs with `2>$null`

### Comparison to V2 SteppedCone
**Similarities:**
- Same plotting style and formatting
- Same 4 metrics displayed
- Same normalization approach for peak force
- Same font sizes and presentation-ready appearance

**Differences:**
- 6 conditions instead of 2
- Generic titles (no "A Vs. B" format)
- Folder names as legend entries
- Different x-axis data range and distribution

## Verification

✅ All 6 subdirectories processed successfully  
✅ 1,080 total measurements combined  
✅ 3 master plots generated (mean, median, log-log)  
✅ Combined CSV saved  
✅ All plots use correct formatting (27pt labels, 21pt titles, bold legends)  
✅ Peak force normalization working correctly  
✅ Power law trendlines fitted for all metrics  
✅ Folder names used as condition labels in legends

## Output Location
All files saved to:
```
C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\TEMPO Picker\V2\
```

---

**Status:** ✅ **COMPLETE**  
All TEMPO Picker V2 master plots successfully generated with same styling as V2 SteppedCone plots.
