# Analysis Investigations Archive

**Archive Date:** February 25, 2026  
**Reason:** Research investigations completed, findings documented

---

## Contents

This directory contains scripts used to investigate specific research questions and data anomalies. Each investigation led to insights that were documented and in some cases influenced the analysis pipeline.

### Investigations

#### 1. **investigate_fep_scaling.py**
- **Research Question:** Why does FEP scaling analysis show super-linear behavior (n=1.29) when visual trendline appears sub-linear?
- **Date:** January 10, 2026
- **File Size:** 208 lines

**Investigation Approach:**
1. Loaded V9 MASTER_all_metrics.csv data
2. Filtered FEP condition only
3. Performed two separate analyses:
   - **Statistical fit:** log(y) = n×log(x) on ALL individual data points
   - **Visual trendline:** Polynomial fit on GROUPED MEANS by radius

**Key Finding:**
The discrepancy arises from different aggregation methods:
- **Statistical scaling:** Uses all 67 individual measurements → captures full data variance → n=1.29 (super-linear)
- **Visual trendline:** Uses ~13 grouped means → smooths out variance → appears sub-linear

**Conclusion:**
- Both analyses are correct for their respective purposes
- Super-linear scaling (n=1.29) is the more accurate physical representation
- Visual plot uses grouped means for cleaner presentation
- Documented in: MEDIAN_PLOTS_AND_FEP_SCALING_SUMMARY.md

**Impact:**
- Clarified interpretation of scaling exponents
- Standard practice: Report statistical fit value (n=1.29) but show grouped plot for clarity
- Added documentation explaining this distinction

---

#### 2. **analyze_v6_scaling.py**
- **Research Question:** What is the scaling behavior of V6 SteppedCone data?
- **Date:** ~November-December 2025
- **Purpose:** Analyze force vs. radius scaling for V6 experimental conditions

**Analysis Performed:**
- Power law fitting: F ∝ R^n
- Comparison across conditions
- Identification of scaling regimes

**Status:** Investigation complete, findings integrated into V6 processing

---

## Methodology Template

These scripts demonstrate the standard investigation workflow:

1. **Load Data:** Read from MASTER CSV files
2. **Filter Condition:** Isolate specific experimental condition
3. **Multiple Analysis Methods:** Compare different approaches
4. **Identify Discrepancy:** Understand why results differ
5. **Document Findings:** Create summary document
6. **Update Pipeline:** Incorporate insights if needed

---

## Research Insights Documented

### FEP Scaling Investigation

**Physical Interpretation:**
- Super-linear scaling (n > 1) suggests increasing adhesion efficiency with larger contact areas
- Could indicate:
  - Edge effects becoming relatively less important at larger scales
  - Better fluid trapping in larger cavities
  - Material deformation effects

**Methodological Insight:**
- Always distinguish between:
  - **Statistical analysis:** Uses all data points (more accurate for physical scaling)
  - **Visual presentation:** Uses grouped means (cleaner for communication)
- Report both methods and explain differences

**Best Practices Established:**
- State aggregation method clearly in figure captions
- Include scatter plots showing individual data points when needed
- Use grouped plots for clean presentation in papers/presentations

---

## Related Analysis Summaries

- [MEDIAN_PLOTS_AND_FEP_SCALING_SUMMARY.md](../../documentation/analysis_summaries/MEDIAN_PLOTS_AND_FEP_SCALING_SUMMARY.md)
- V6 Analysis Summary (in legacy_docs if needed)

---

## If You Need to Investigate New Data

**Use these scripts as templates for:**

1. **Comparing analysis methods:**
   - Statistical fits vs grouped visualization
   - Different aggregation approaches (mean vs median)
   - Various scaling models (linear, power law, exponential)

2. **Identifying anomalies:**
   - Unexpected trends
   - Discrepancies between visualizations and statistics
   - Outlier detection

3. **Scaling analysis:**
   - Power law fitting in log-log space
   - Regime identification (sub-linear, linear, super-linear)
   - Physical interpretation of exponents

**Recommended workflow:**
```python
# 1. Load data
df = pd.read_csv('MASTER_all_metrics.csv')

# 2. Filter condition
condition_data = df[df['condition_label'] == 'YourCondition']

# 3. Statistical analysis (all points)
log_x = np.log(condition_data['radius_mm'])
log_y = np.log(condition_data['peak_force_N'])
slope, intercept, r_value, _, _ = stats.linregress(log_x, log_y)
print(f"Scaling exponent: {slope:.2f}")

# 4. Visual analysis (grouped)
grouped = condition_data.groupby('radius_mm')['peak_force_N'].mean()
# Fit polynomial to grouped data
# Compare with statistical result

# 5. Document findings
# Create summary markdown with plots and interpretation
```

---

**Archived by:** Workspace cleanup Phase 3  
**Scripts remain functional** for reference or template use
