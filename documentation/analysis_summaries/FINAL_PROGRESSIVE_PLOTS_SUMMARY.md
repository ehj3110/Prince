# Final Folder - Progressive Reveal Master Plots
**Date:** January 20, 2026
**Analysis Type:** Progressive reveal presentation plots

---

## 📊 Overview

Successfully generated **8 master plots** (4 mean + 4 log-log) with progressive data reveal for presentation purposes. All plots use **consistent axis ranges** to ensure smooth transitions when revealing additional data.

### Key Improvements Implemented

1. **✅ Fixed Negative Peel Distance**
   - Modified `adhesion_metrics_calculator.py` to use `abs()` for all distance calculations
   - Peel distances are now correctly **positive** (stage moves up = positive distance)
   - Calculation uses **real position data**, not time-based estimates

2. **✅ Custom Plot Titles**
   - All plots titled: "Adhesion Metrics Comparison (Mean)"
   - Consistent professional formatting

3. **✅ Consistent Axis Scaling**
   - Calculated global axis ranges from ALL data (Version 4)
   - Applied same ranges to Versions 1-3 for smooth transitions
   - No "jumping" or rescaling between slides

---

## 📈 Progressive Reveal Sequence

### Version 1: FEP Only
- **Data:** 67 measurements (FEP membrane only)
- **Files:** `Master_Mean_Plot_1.png`, `Master_LogLog_Plot_1.png`
- **Purpose:** Establish baseline with stiffest material

### Version 2: FEP + PDMS Unsealed
- **Data:** 138 measurements (FEP + PDMS Unsealed)
- **Files:** `Master_Mean_Plot_2.png`, `Master_LogLog_Plot_2.png`
- **Purpose:** Compare FEP to unsealed PDMS

### Version 3: FEP + Both PDMS
- **Data:** 209 measurements (FEP + PDMS Unsealed + PDMS Sealed)
- **Files:** `Master_Mean_Plot_3.png`, `Master_LogLog_Plot_3.png`
- **Purpose:** Show effect of sealing on PDMS

### Version 4: All 5 Conditions
- **Data:** 343 measurements (all folders)
- **Conditions:**
  - FEP
  - PDMS - Unsealed
  - PDMS - Sealed
  - Hybrid
  - Hybrid - Compliant
- **Files:** `Master_Mean_Plot_4.png`, `Master_LogLog_Plot_4.png`
- **Purpose:** Complete dataset with hybrid membranes

---

## 📊 Plot Details

### Metrics Displayed (4 subplots per plot)

1. **Peak Force (N)** - Maximum adhesive force
2. **Work of Adhesion (mJ)** - Energy required to separate
3. **Total Peel Distance (mm)** - Distance peeled (NOW POSITIVE!)
4. **Peak Retraction Force (N)** - Maximum force during retraction

### Plot Types

**Mean Plots:**
- Mean values with SEM error bands
- Power law trendlines (dotted)
- No individual data points

**Log-Log Plots:**
- Log-log axes for power law visualization
- Power law fits with exponents
- Identifies scaling relationships

---

## 📂 File Locations

**Master Plots Directory:**
```
C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\Presentation data\Final\progressive_plots\
```

**Generated Files (8 total):**
```
Master_Mean_Plot_1.png    (743 KB)
Master_Mean_Plot_2.png    (1.0 MB)
Master_Mean_Plot_3.png    (1.1 MB)
Master_Mean_Plot_4.png    (1.4 MB)

Master_LogLog_Plot_1.png  (896 KB)
Master_LogLog_Plot_2.png  (1.1 MB)
Master_LogLog_Plot_3.png  (1.4 MB)
Master_LogLog_Plot_4.png  (1.8 MB)
```

**Combined Data:**
```
MASTER_final_combined.csv  (343 measurements from 5 folders)
```

---

## 🔧 Technical Details

### Axis Range Calculation
- Global ranges calculated from Version 4 (all data)
- Each metric has fixed (x_min, x_max, y_min, y_max)
- Applied consistently across all 4 versions
- Prevents axis rescaling during presentation reveal

### Data Processing
- Loaded from existing `automated_work_of_adhesion.csv` in each folder
- Applied `abs()` to Total_Peel_Distance_mm to fix negative values
- Calculated radius from Cross_Sectional_Area_mm2
- Standardized column names for plotting compatibility

### Plotting Configuration
- Font sizes: 27pt axis labels, 21pt subplot titles, 15pt legends
- Mean plots: SEM error bands + polynomial trendlines
- Log-log plots: Power law fits with scaling exponents
- All plots: 300 DPI, 16x12" figsize

---

## 🎯 Presentation Usage Guide

### Slide-by-Slide Reveal

**Slide 1: Introduce FEP**
- Show `Master_Mean_Plot_1.png` or `Master_LogLog_Plot_1.png`
- Discuss FEP membrane characteristics
- Note: This is the stiffest material in your dataset

**Slide 2: Add PDMS Unsealed**
- Replace with `Master_Mean_Plot_2.png` or `Master_LogLog_Plot_2.png`
- Compare FEP vs PDMS Unsealed
- Discuss material property differences

**Slide 3: Add PDMS Sealed**
- Replace with `Master_Mean_Plot_3.png` or `Master_LogLog_Plot_3.png`
- Show effect of sealing on PDMS behavior
- Compare sealed vs unsealed

**Slide 4: Complete Dataset**
- Replace with `Master_Mean_Plot_4.png` or `Master_LogLog_Plot_4.png`
- Introduce hybrid membranes
- Show full material comparison

### Key Advantages
- ✅ **No axis jumping** - consistent scales throughout
- ✅ **Smooth transitions** - data appears in same position
- ✅ **Professional appearance** - uniform formatting
- ✅ **Clear story** - progressive complexity buildup

---

## 📋 Data Quality Notes

### Peel Distance Fix
The earlier negative Total_Peel_Distance values were due to stage encoder decreasing as physical height increased. The fix applies `abs()` to ensure all distances are positive while preserving the magnitude.

**Before fix:** -0.627 mm, -0.683 mm, -0.665 mm
**After fix:** 0.627 mm, 0.683 mm, 0.665 mm

### Position Data Source
- Peel distances calculated from **real position encoder data**
- NOT time-based estimates
- Formula: `abs(positions[prop_end_idx] - positions[pre_init_idx])`

---

## ✅ Summary

Successfully created 4 progressive reveal versions of master plots with:
- ✅ Positive peel distances (fixed sign issue)
- ✅ Custom title: "Adhesion Metrics Comparison (Mean)"
- ✅ Consistent axis scaling across all versions
- ✅ Professional formatting for presentation
- ✅ 8 total plots (4 mean + 4 log-log)

**Ready for presentation!** 🎉
