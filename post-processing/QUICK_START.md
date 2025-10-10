# Enhanced Batch Processing - Quick Reference Card

## 🚀 To Run Your New FilesToProcess Data

```powershell
cd "c:\Users\ehunt\OneDrive\Documents\Prince\Prince_Segmented_20250926\post-processing"
python batch_process_with_outliers.py
```

**Note:** The path is already configured to:
`C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\FilesToProcess`

---

## 📊 What You'll Get

### 4 Master Plots (All with Error Bars, No Individual Points)

1. **MASTER_speed_mean_analysis.png**
   - Peak Force, Work of Adhesion, Peel Distance, Retraction vs Speed
   - Mean values ± SEM error bars

2. **MASTER_speed_median_analysis.png**  
   - Same metrics as above
   - Median values ± IQR error bars

3. **MASTER_distance_mean_analysis.png**
   - Distance to Peak, Propagation Distance vs Speed
   - Mean values ± SEM error bars

4. **MASTER_distance_median_analysis.png**
   - Same distance metrics
   - Median values ± IQR error bars

### Per-Folder Files

- `autolog_metrics_filtered.csv` - Filtered metrics data

---

## 🎯 Key Features

✅ **New Smoothing:** Hybrid Median-Savitzky-Golay (90.1% improvement)  
✅ **Outlier Filtering:** IQR method (removes extreme outliers automatically)  
✅ **USW Support:** Recognizes "USW" (Unsealed Water) folders  
✅ **Clean Plots:** Smaller markers, error bars, no scattered points  
✅ **Error Bars:** SEM for means, IQR for medians

---

## ⚙️ Outlier Filter Settings (Current)

```python
ENABLE_OUTLIER_FILTER = True
OUTLIER_METHOD = 'iqr'        # Interquartile Range
OUTLIER_THRESHOLD = 1.5       # Standard setting
```

**What this does:**
- Removes data points < Q1 - 1.5×IQR or > Q3 + 1.5×IQR
- Typically removes ~0.7% of normally distributed data
- Perfect for removing extreme outliers while keeping most data

**To change:** Edit lines 686-690 in `batch_process_with_outliers.py`

---

## 🔧 Common Adjustments

### Make Filter More Lenient (Keep More Data)
```python
OUTLIER_THRESHOLD = 2.0  # Only removes very extreme outliers
```

### Make Filter Stricter (For Very Noisy Data)
```python
OUTLIER_THRESHOLD = 1.0  # Removes more outliers
```

### Disable Outlier Filtering
```python
ENABLE_OUTLIER_FILTER = False
```

### Use Different Method (For Skewed Data)
```python
OUTLIER_METHOD = 'mad'       # Median Absolute Deviation
OUTLIER_THRESHOLD = 3.5
```

---

## 📝 Error Bar Types Explained

### SEM (Standard Error of Mean)
- **Shows:** How precise is our mean estimate?
- **Formula:** Standard Deviation / √(sample size)
- **Smaller bars = More precise measurement**
- **Use when:** Showing statistical precision (scientific papers)

### IQR (Interquartile Range)  
- **Shows:** Where does the middle 50% of data fall?
- **Formula:** 75th percentile - 25th percentile
- **Smaller bars = Less variability in data**
- **Use when:** Showing data spread, robust to outliers

**Both types are generated automatically!**

---

## 📁 Folder Naming Requirements

**Format:** `FluidType_Gap_TestType_Resin[_OptionalSuffix]`

**Supported Fluid Types:**
- `Water` - Regular water
- `USW` - Unsealed water (new!)
- `PEO` - PEO solution
- `2p5PEO` - 2.5% PEO solution

**Examples:**
```
Water_1mm_Ramped_BPAGDA
USW_5mm_Constant_BPAGDA
PEO_1mm_Ramped_BPAGDA_Old
2p5PEO_5mm_Ramped_BPAGDA
```

---

## 🔍 How Outlier Detection Works

### IQR Method (Default)

1. **Calculate quartiles** for each metric (peak force, work of adhesion, etc.)
   - Q1 = 25th percentile
   - Q3 = 75th percentile
   - IQR = Q3 - Q1

2. **Define bounds:**
   - Lower = Q1 - 1.5 × IQR
   - Upper = Q3 + 1.5 × IQR

3. **Remove outliers:** Any value outside bounds

4. **Why it's robust:**
   - Uses percentiles (not affected by extreme values)
   - Standard statistical method (same as box plots)
   - Threshold of 1.5 is industry standard

**Example:**
- Your data: [0.1, 0.12, 0.11, 0.13, 0.10, 0.50] ← 0.50 is outlier
- Q1 = 0.10, Q3 = 0.13, IQR = 0.03
- Bounds: [0.055, 0.175]
- **0.50 removed!** ✅

---

## 📊 Plot Improvements

### Old System
- Individual points at 90% transparency (hard to see trends)
- Large markers for means (visually overwhelming)
- No error bars
- All points shown (including outliers)

### New System ✅
- **NO individual points** (clean visualization)
- **Smaller markers** (6pt instead of 80pt)
- **Error bars** showing uncertainty
- **Outliers filtered** before plotting
- **Polynomial trendlines** (2nd order)
- **Publication-ready** quality

---

## 🧪 Filter Validation

**Tested on:** autolog_L48-L50.csv (2,260 data points)

**Results:**
- Peak Force: 0.26 N ✅
- Work of Adhesion: 0.28 mJ ✅
- Smoothness: **90.1% improvement** over old Gaussian filter ✅

**Research:** 30+ filter combinations tested
**Optimal:** Median (k=5) → Savitzky-Golay (w=9, o=2)
**Score:** 0.02124 (2nd best combination)

---

## 📖 Full Documentation

For detailed information, see:
- `BATCH_PROCESSING_GUIDE.md` - Complete user guide
- `CHANGELOG.md` - All changes and updates
- `CLEANUP_AND_FILTERING_SUMMARY.md` - Filter optimization details

---

## ❓ Quick Troubleshooting

**"No autolog files found"**
→ Files must be named `autolog_L##-L##.csv`

**"Could not parse folder name"**
→ Check format: `FluidType_Gap_Type_Resin`

**"All data filtered out"**
→ Filter too strict, increase threshold to 2.0

**"Module not found"**
→ Run from post-processing directory

**"No master plots"**
→ Ensure `plot_master_with_errorbars.py` exists

---

## 🎓 Scientific Note

**Why both Mean and Median plots?**

- **Mean:** Better when data is normally distributed, shows average behavior
- **Median:** Better when outliers present, shows typical behavior

**Recommendation:** 
- Use **Mean plots** for scientific papers (with SEM)
- Use **Median plots** for preliminary analysis of noisy data

Both are generated automatically, so you can choose the best for your purpose!

---

**Created:** October 6, 2025  
**Version:** 2.0 (Enhanced with outlier filtering and error bars)
