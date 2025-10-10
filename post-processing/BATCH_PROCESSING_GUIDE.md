# Enhanced Batch Processing with Outlier Filtering

**Date:** October 6, 2025  
**Author:** Cheng Sun Lab Team

## Overview

This enhanced batch processing system includes:

✅ **New hybrid Median-Savitzky-Golay smoothing filter** (90.1% smoother)  
✅ **Statistical outlier detection and filtering** (IQR, Z-score, or MAD methods)  
✅ **USW (Unsealed Water) fluid type support**  
✅ **4 master plots with error bars** (Mean+SEM and Median+IQR)  
✅ **Clean visualization** (no scattered individual points, smaller markers)

---

## Quick Start

### 1. Configure Your Data Path

Edit `batch_process_with_outliers.py` (line 686):

```python
master_folder_path = r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\FilesToProcess"
```

### 2. Configure Outlier Filtering (Optional)

```python
ENABLE_OUTLIER_FILTER = True   # Set to False to disable
OUTLIER_METHOD = 'iqr'         # Options: 'iqr', 'zscore', 'mad'
OUTLIER_THRESHOLD = 1.5        # See details below
```

### 3. Run the Script

```powershell
cd "c:\Users\ehunt\OneDrive\Documents\Prince\Prince_Segmented_20250926\post-processing"
python batch_process_with_outliers.py
```

---

## Outlier Filtering Methods

### **Method 1: IQR (Interquartile Range) - RECOMMENDED** ✅

**How it works:**
- Calculates Q1 (25th percentile) and Q3 (75th percentile)
- IQR = Q3 - Q1
- Removes values outside: `[Q1 - threshold×IQR, Q3 + threshold×IQR]`

**Thresholds:**
- `1.5` = Standard (removes extreme outliers, ~0.7% of normal data)
- `2.0` = Lenient (only very extreme outliers)
- `1.0` = Strict (removes more data)

**Best for:** General use, robust against extreme outliers

---

### **Method 2: Z-Score**

**How it works:**
- Calculates how many standard deviations each point is from the mean
- Removes values with |Z| > threshold

**Thresholds:**
- `3.0` = Standard (~0.3% of normal data removed)
- `2.0` = Strict (~5% of normal data removed)
- `4.0` = Very lenient

**Best for:** Normally distributed data without extreme outliers

**⚠️ Warning:** Less robust - extreme outliers can affect mean/SD calculation

---

### **Method 3: MAD (Median Absolute Deviation)**

**How it works:**
- Uses median instead of mean (more robust)
- Modified Z-score = 0.6745 × (value - median) / MAD
- Removes values with modified Z > threshold

**Thresholds:**
- `3.5` = Standard (similar to Z-score = 3)
- `2.5` = Stricter
- `4.5` = More lenient

**Best for:** Skewed distributions or data with many outliers

---

## Example Configurations

### Conservative (Keep Most Data)
```python
ENABLE_OUTLIER_FILTER = True
OUTLIER_METHOD = 'iqr'
OUTLIER_THRESHOLD = 2.0  # Only removes extreme outliers
```

### Standard (Recommended)
```python
ENABLE_OUTLIER_FILTER = True
OUTLIER_METHOD = 'iqr'
OUTLIER_THRESHOLD = 1.5  # Standard IQR method
```

### Strict (Noisy Data)
```python
ENABLE_OUTLIER_FILTER = True
OUTLIER_METHOD = 'iqr'
OUTLIER_THRESHOLD = 1.0  # Removes more outliers
```

### Very Noisy Data
```python
ENABLE_OUTLIER_FILTER = True
OUTLIER_METHOD = 'zscore'
OUTLIER_THRESHOLD = 2.0  # Removes ~5% of data
```

### No Filtering
```python
ENABLE_OUTLIER_FILTER = False
```

---

## Output Files

### Per-Folder Outputs

Each test folder will contain:

1. **`autolog_metrics_filtered.csv`** - Metrics after outlier filtering
   - Columns: layer, speed, peak_force_N, work_of_adhesion_mJ, etc.
   - Filtered data only

2. **Individual layer plots** (if enabled)
   - One plot per autolog file

### Master Outputs (in main folder)

1. **`MASTER_all_metrics.csv`** - Combined data from all folders

2. **`MASTER_speed_mean_analysis.png`**
   - 4 subplots: Peak Force, Work of Adhesion, Peel Distance, Retraction Force vs Speed
   - Mean values with SEM (Standard Error of Mean) error bars
   - Polynomial trendlines

3. **`MASTER_speed_median_analysis.png`**
   - Same 4 subplots as above
   - Median values with IQR (Interquartile Range) error bars
   - More robust to outliers

4. **`MASTER_distance_mean_analysis.png`**
   - 2 subplots: Distance to Peak, Propagation Distance vs Speed
   - Mean values with SEM error bars

5. **`MASTER_distance_median_analysis.png`**
   - Same 2 subplots as above
   - Median values with IQR error bars

---

## Understanding Error Bars

### SEM (Standard Error of Mean)
- Shows: **Uncertainty in the mean estimate**
- Formula: `SEM = SD / √n`
- Interpretation: "If we repeated this experiment, the mean would likely fall within these error bars"
- Used in: Mean plots

### IQR (Interquartile Range)
- Shows: **Spread of the middle 50% of data**
- Formula: `IQR = Q3 - Q1`
- Interpretation: "Half of our measurements fall between these bounds"
- Used in: Median plots

**When to use which:**
- **Mean + SEM:** Scientific publications, showing precision of your measurement
- **Median + IQR:** Data with outliers, showing data distribution

---

## Supported Fluid Types

The system recognizes these folder naming patterns:

- **Water_1mm_Ramped_BPAGDA**
- **Water_5mm_Constant_BPAGDA**
- **USW_1mm_Ramped_BPAGDA** ← New! (Unsealed Water)
- **USW_5mm_Constant_BPAGDA**
- **PEO_1mm_Ramped_BPAGDA**
- **2p5PEO_5mm_Ramped_BPAGDA** (2.5% PEO)

**Format:** `FluidType_Gap_TestType_Resin[_OptionalSuffix]`

---

## Folder Structure Requirements

```
FilesToProcess/
├── Water_1mm_Ramped_BPAGDA/
│   ├── PrintInstructions.csv       (optional - for speed mapping)
│   ├── autolog_L10-L15.csv         (required)
│   └── autolog_L20-L25.csv
├── USW_5mm_Constant_BPAGDA/
│   ├── PrintInstructions.csv
│   └── autolog_L50-L60.csv
└── PEO_1mm_Ramped_BPAGDA/
    └── autolog_L100-L110.csv
```

---

## Troubleshooting

### "No autolog files found"
- Ensure files are named: `autolog_L##-L##.csv` (case-insensitive)
- Example: `autolog_L48-L50.csv`

### "Could not parse folder name"
- Check folder naming: `FluidType_Gap_Type_Resin`
- Must have at least 4 underscore-separated parts

### "No data points after filtering"
- Outlier filter too strict → Increase threshold or disable filtering
- Check data quality in CSV files

### "Module import errors"
- Ensure you're in the post-processing directory
- Verify `support_modules/` folder exists with required files

### "No master plots generated"
- Ensure `plot_master_with_errorbars.py` exists in post-processing folder
- Check console output for specific error messages

---

## Key Improvements Over Previous System

### 1. **Smoothing Filter** (Oct 5, 2025)
- **Old:** Single Gaussian filter (σ=0.5)
- **New:** Hybrid Median (k=5) → Savitzky-Golay (w=9, o=2)
- **Result:** 90.1% smoother, better spike rejection

### 2. **Outlier Filtering** (Oct 6, 2025)
- **Old:** Manual data cleaning required
- **New:** Automated statistical filtering (IQR/Z-score/MAD)
- **Result:** Handles noisy data automatically

### 3. **Master Plots** (Oct 6, 2025)
- **Old:** Individual scattered points at 90% transparency, large markers
- **New:** Clean mean/median points with error bars, smaller markers
- **Result:** Publication-ready figures

### 4. **USW Support** (Oct 6, 2025)
- **Old:** Only Water and PEO
- **New:** Added USW (Unsealed Water)
- **Result:** Supports new experimental conditions

---

## Technical Notes

### Filter Parameters (Optimized Oct 2025)

**Stage 1: Median Filter**
- Kernel size: 5
- Purpose: Spike/outlier rejection

**Stage 2: Savitzky-Golay Filter**
- Window: 9
- Polynomial order: 2
- Purpose: Smooth polynomial fit

**Combined Score:** 0.02124 (2nd best of 30+ tested combinations)

### Statistical Methods

**Outlier Detection:**
- Applied per-metric (peak force, work of adhesion, etc.)
- Combined mask: All metrics must pass filter
- Preserves layer-speed relationships

**Aggregation:**
- Mean: Arithmetic average per speed
- Median: 50th percentile per speed
- SEM: Standard deviation / √count
- IQR: 75th percentile - 25th percentile

---

## Contact

For questions or issues, contact the Cheng Sun Lab Team.

**Related Documentation:**
- `CHANGELOG.md` - Full change history
- `CLEANUP_AND_FILTERING_SUMMARY.md` - Filter optimization details
- `archive/filtering_experimentation/README.md` - Complete filter analysis
