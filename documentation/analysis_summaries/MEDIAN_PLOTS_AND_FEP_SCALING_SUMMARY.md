# Median Master Plots & FEP Scaling Analysis Summary
**Date:** January 10, 2026  
**Author:** Cheng Sun Lab Team

## Overview
This document summarizes two key analyses:
1. Generation of median-aggregated master plots for V9 data
2. Investigation of the FEP scaling discrepancy between visual appearance and statistical analysis

---

## 1. Median Master Plots

### Implementation
Added median aggregation support to `master_plotter.py`:
- **New method:** `generate_radius_analysis_plot_median()`
- **Error metric:** MAD (Median Absolute Deviation) instead of SEM
- **Error calculation:** `1.4826 * MAD / sqrt(n)` (MAD-based standard error)
- **Visual style:** Same as mean plots (shaded regions, polynomial trendlines)

### Generated Files
Created using `generate_v9_median_plots.py`:

1. **MASTER_radius_analysis_MEDIAN.png**
   - Metrics: Peak Force, Work of Adhesion, Peel Distance, Peak Retraction Force
   - Size: 1.29 MB
   - Aggregation: Median by radius

2. **MASTER_radius_analysis_modified_MEDIAN.png**
   - Metrics: Peak Force, Work of Adhesion, Peel Distance, Total Peel Time
   - Size: 1.29 MB
   - Aggregation: Median by radius

### Data Summary
- **Total layers:** 276 (67-71 per condition)
- **Conditions:** 4 (FEP/Air, PDMS/Water variants)
- **Radius bins:** ~13 per condition
- **MAD range:** 0.006 to 1.419 (varies by metric and condition)

### Usage
To regenerate median plots:
```powershell
python .\generate_v9_median_plots.py
```

---

## 2. FEP Scaling Discrepancy Analysis

### Problem Statement
**User observation:** FEP data appears **sub-linear** in visual plots, but scaling analysis reports **super-linear** (n=1.29).

### Root Cause Identified
The discrepancy arises from **different analysis methods**:

#### Method 1: Scaling Analysis (Log-Log Regression)
- **Approach:** Fit `log(Force) = n*log(Radius)` to ALL 67 individual data points
- **Result:** n = 1.290 ± 0.146 (super-linear)
- **R² = 0.546** (moderate fit quality)
- **What it measures:** Overall power-law trend across entire dataset

#### Method 2: Visual Plots (Polynomial on Grouped Means)
- **Approach:** Fit 2nd-degree polynomial to ~13 radius bins (grouped means)
- **Result:** F = -0.1078*r² + 2.0539*r - 2.1305
- **Curvature:** Negative (concave) → appears sub-linear
- **What it measures:** Local curvature of aggregated data

### Key Findings

#### 1. Variable Scaling Behavior
Effective scaling exponent changes with radius:
- **Small radii (r=2mm):** n_eff = 2.10 (super-linear)
- **Medium radii (r=3mm):** n_eff = 1.38 (super-linear)
- **Large radii (r=4mm):** n_eff = 1.09 (linear)
- **Largest radii (r=5mm):** n_eff = 0.90 (sub-linear)

#### 2. High Variance at Large Radii
Coefficient of variation (CV) increases with radius:
- **Small radii:** CV = 2-5% (very consistent)
- **Medium radii:** CV = 44-54% (moderate scatter)
- **Large radii:** CV = 79-116% (extreme scatter)

This high variance at large radii pulls the power-law fit upward, creating super-linear behavior in aggregate.

#### 3. Both Analyses Are Correct
- **Scaling analysis:** Captures overall trend → n=1.29 (super-linear)
- **Visual polynomial:** Captures local curvature → concave (sub-linear appearance)
- **Not contradictory:** Different questions, different answers

### Diagnostic Plot
Generated `FEP_scaling_investigation.png` showing:
1. **Linear scale:** Power law vs polynomial fits
2. **Log-log scale:** Raw data with power law overlay
3. **Residuals:** Scatter increases with radius
4. **Data distribution:** 5 layers per radius bin

### Interpretation
The FEP system exhibits **radius-dependent scaling**:
- Initial super-linear behavior (cooperative failure at small scales)
- Transition to sub-linear at large scales (possibly edge-dominated)
- High variability suggests complex failure mechanisms or experimental noise

### Recommendations
1. **For publications:** Report both the power-law exponent (n=1.29) and note the curvature
2. **For further analysis:** Consider piecewise power laws or investigate failure mechanisms
3. **For comparisons:** Use median plots to reduce influence of outliers

---

## 3. File Locations

### Scripts
- `batch_processors/generate_v9_median_plots.py` - Generate median master plots
- `batch_processors/investigate_fep_scaling.py` - FEP scaling diagnostic tool
- `post-processing/master_plotter.py` - Updated with median support

### Output Files (V9 Directory)
**Median Plots:**
- `MASTER_radius_analysis_MEDIAN.png`
- `MASTER_radius_analysis_modified_MEDIAN.png`

**Mean Plots (existing):**
- `MASTER_radius_analysis.png`
- `MASTER_radius_analysis_modified.png`

**Diagnostic:**
- `FEP_scaling_investigation.png`

**Data:**
- `MASTER_all_metrics.csv` (276 layers, source data)

---

## 4. Technical Details

### Median Aggregation Implementation
```python
# Group by radius and calculate MEDIAN + MAD
grouped = condition_data.groupby('radius_mm')[metric_col].agg(
    median='median',
    count='count',
    mad=lambda x: np.median(np.abs(x - np.median(x)))
).reset_index()

# Calculate MAD-based error (1.4826 * MAD / sqrt(n))
mad_errors = 1.4826 * mads / np.sqrt(counts)
```

### Power Law Scaling Analysis
```python
# Log-transform data
log_r = np.log(radius)
log_f = np.log(force)

# Linear regression in log space
slope, intercept, r_value, p_value, std_err = stats.linregress(log_r, log_f)

# Convert back: Force = A * radius^n
n = slope  # Exponent
A = np.exp(intercept)  # Coefficient
```

---

## 5. Conclusions

### Median Plots
✅ Successfully generated median-aggregated master plots for V9 data  
✅ MAD-based error bars provide robust uncertainty estimates  
✅ Visual style consistent with existing mean plots  

### FEP Scaling
✅ Identified root cause of visual vs. analytical discrepancy  
✅ Both methods are valid for their respective purposes  
✅ High variance at large radii drives super-linear power law fit  
✅ Effective scaling exponent varies from 2.1 (small) to 0.9 (large)  

### Recommendations
1. Use **median plots** when data has outliers (more robust)
2. Use **mean plots** when data is normally distributed (more sensitive)
3. Report **both power law exponent and polynomial curvature** for complete picture
4. Consider **radius-dependent analysis** for systems with changing behavior

---

## Appendix: Statistical Theory

### Why MAD for Median?
MAD (Median Absolute Deviation) is the robust analog of standard deviation:
- **SD:** Mean of squared deviations (sensitive to outliers)
- **MAD:** Median of absolute deviations (robust to outliers)
- **Conversion:** MAD × 1.4826 ≈ SD (for normal distributions)

### Why Log-Log for Scaling?
Power law: `y = A * x^n`  
Log-transform: `log(y) = log(A) + n*log(x)`  
Result: Linear regression in log space gives power law parameters

### Why Polynomial for Visual?
Polynomial captures local curvature that may differ from global power law:
- Flexible fit to non-uniform data
- Easy to see concave/convex behavior
- Common in publication plots
