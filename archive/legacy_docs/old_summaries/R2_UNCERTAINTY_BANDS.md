# Stiffness vs Radius Plot with R²-Based Uncertainty Bands

## Overview
This document describes the new stiffness visualization that uses R² values from individual stiffness fits to represent measurement uncertainty.

## Implementation Date
December 6, 2025

## Key Features

### 1. R²-Based Uncertainty Representation
- **Shaded bands** around mean stiffness values represent fit quality
- **Band width** is inversely proportional to R² values:
  - High R² (e.g., 0.95) → **narrow bands** (reliable fits)
  - Low R² (e.g., 0.50) → **wide bands** (uncertain fits)
- Formula: `band_width = (1 - R²) × max(std, mean × 0.1)`

### 2. Visual Encoding
- **Shaded regions**: Semi-transparent bands (alpha=0.2) showing R²-weighted uncertainty
- **Mean lines**: Solid lines connecting mean stiffness at each radius
- **Individual points**: Scatter points with opacity scaled by R² (darker = better fit)
- **Color coding**: Each condition has its own color (from Set2 colormap)

### 3. Comparison with SEM Bands
| Feature | SEM Bands (Standard) | R² Bands (New) |
|---------|---------------------|----------------|
| **Represents** | Measurement variability (repeatability) | Fit quality (confidence) |
| **Width** | Based on standard error of mean | Based on (1 - R²) × std |
| **Interpretation** | Tight = consistent measurements | Tight = reliable force-displacement fits |
| **Use case** | Show experimental repeatability | Show model confidence |

## Mathematical Details

### Band Width Calculation
For each radius bin:
1. Group all measurements at that radius
2. Calculate mean stiffness: `k_mean = mean(k_i)`
3. Calculate mean R²: `R²_mean = mean(R²_i)`
4. Calculate std deviation: `σ = std(k_i)`
5. Uncertainty factor: `f = (1 - R²_mean)`
6. Band width: `Δk = f × max(σ, 0.1 × k_mean)`
7. Upper bound: `k_mean + Δk`
8. Lower bound: `k_mean - Δk`

### Physical Interpretation
- **R² = 1.0**: Perfect fit → zero uncertainty → band width = 0
- **R² = 0.8**: Good fit → 20% uncertainty → band width = 0.2 × σ
- **R² = 0.5**: Poor fit → 50% uncertainty → band width = 0.5 × σ
- **R² = 0.0**: No fit → 100% uncertainty → band width = 1.0 × σ

## Results from V6 Dataset

### Processing Summary
- **Total measurements**: 180 (60 per condition)
- **Conditions**: ACF 5mm, Flat PDMS 1mm, TEMPO 1mm
- **R² threshold**: 0.5 (measurements below this excluded from scaling analysis)

### Scaling Results

**ACF, 5mm:**
- k = 0.4566 × r^0.577 (R² = 0.567)
- Moderate size dependence
- Stiffness increases with radius (composite effects)

**Flat PDMS, 1mm:**
- k = 0.0611 × r^1.732 (R² = 0.978)
- Strong size dependence
- Nearly quadratic relationship with radius

**TEMPO, 1mm:**
- k = 0.0507 × r^1.470 (R² = 0.968)
- Strong size dependence
- Between linear and quadratic

## File Locations

### Generated Plot
- **Path**: `V6/stiffness_vs_radius_r2_bands.png`
- **Size**: 505 KB
- **Resolution**: 300 DPI
- **Created**: December 6, 2025 5:38 PM

### Source Code
- **Method**: `plot_stiffness_vs_radius_with_r2_bands()` in `stiffness_scaling_analyzer.py`
- **Script**: `plot_stiffness_r2_bands.py` (generates plot from V6 data)
- **Lines**: ~180-280 in stiffness_scaling_analyzer.py

### Data Source
- **CSV**: `V6/MASTER_all_metrics.csv` (45 columns, 180 rows)
- **Key columns**: 
  - `material_stiffness_N_per_mm`: Stiffness value (best fit model)
  - `material_stiffness_r_squared`: Fit quality (R² value)
  - `radius_mm`: Contact radius

## Usage

### Running the Plot Generation
```powershell
cd post-processing
python plot_stiffness_r2_bands.py
```

### Integration into Analysis Pipeline
```python
from stiffness_scaling_analyzer import StiffnessScalingAnalyzer

# Load data
df = pd.read_csv('V6/MASTER_all_metrics.csv')

# Perform scaling analysis
analyzer = StiffnessScalingAnalyzer(output_dir='V6')
results = analyzer.analyze_stiffness_scaling(df, min_r_squared=0.5)

# Generate R² bands plot
analyzer.plot_stiffness_vs_radius_with_r2_bands(results)
```

## Interpretation Guide

### Reading the Plot

**Narrow bands + high point opacity:**
- Reliable stiffness measurements (high R²)
- Force-displacement curves fit models well
- Confident in stiffness estimate
- Example: Well-behaved elastic response

**Wide bands + low point opacity:**
- Uncertain stiffness measurements (low R²)
- Force-displacement curves deviate from models
- Less confident in stiffness estimate
- Example: Non-ideal behavior (slipping, wrinkling, non-linear response)

### When to Use This Plot vs SEM Plot

**Use R² bands when:**
- Evaluating model quality/fit confidence
- Identifying problematic measurements
- Understanding reliability of stiffness extraction
- Comparing different materials (some may fit models better)

**Use SEM bands when:**
- Showing experimental repeatability
- Demonstrating statistical significance
- Presenting measurement precision
- Standard scientific visualization

## Technical Notes

### Design Choices

1. **Minimum band width = 10% of mean**
   - Ensures visibility even for perfect fits
   - Prevents infinitesimally small bands
   - Shows actual value uncertainty

2. **Point opacity = R² × 0.8 + 0.2**
   - Range: 0.2 to 1.0
   - Ensures all points visible
   - Darker = more reliable

3. **Grouping by unique radius**
   - Bins measurements at identical radii
   - Calculates mean and R²-weighted uncertainty
   - Smooth shading with fill_between()

4. **Legend organization**
   - Shaded regions labeled as "uncertainty band"
   - Mean lines labeled separately
   - Clear distinction between elements

### Limitations

1. **Assumes R² reflects uncertainty**
   - R² measures fit quality, not absolute accuracy
   - Low R² could indicate model mismatch (not just noise)
   - Should interpret alongside physical understanding

2. **Radius binning required**
   - Only exact radius matches are grouped
   - Stepped cone design ensures discrete radii
   - Wouldn't work well for continuous radius variation

3. **Minimum 2 points per radius**
   - Need std calculation for uncertainty
   - Single measurements show max(σ, 0.1×mean) = 0.1×mean

## Future Enhancements

### Potential Improvements
1. **Colormap by R²**: Encode R² in color gradient (not just opacity)
2. **Individual R² overlay**: Small text labels showing R² for each point
3. **Threshold visualization**: Highlight regions below R² cutoff
4. **Log-log version**: Add log-log subplot (like other scaling plots)
5. **Statistical testing**: Add significance markers for R² differences

### Alternative Uncertainty Metrics
- **Option A**: Use AIC weights instead of R²
- **Option B**: Propagate parameter uncertainties from curve_fit covariance
- **Option C**: Bootstrap confidence intervals from individual curves
- **Option D**: Bayesian credible intervals

## References

### Related Documentation
- `MATERIAL_STIFFNESS_IMPLEMENTATION.md`: Complete stiffness analysis system
- `material_stiffness_analyzer.py`: Individual curve fitting (4 models)
- `stiffness_scaling_analyzer.py`: Power law scaling analysis
- `batch_process_universal.py`: Integration into processing pipeline

### Similar Visualizations
- `MASTER_force_per_radius.png`: Force/radius vs radius (SEM bands)
- `MASTER_distance_analysis.png`: Metrics vs area (SEM bands)
- `stiffness_vs_area.png`: Stiffness vs area (scatter only, no bands)
- `stiffness_vs_radius.png`: Stiffness vs radius (scatter only, no bands)

## Changelog

### Version 1.0 (December 6, 2025)
- Initial implementation of R²-based uncertainty bands
- Applied to stiffness vs radius visualization
- Generated plot for V6 dataset (180 measurements)
- Documentation created

---

**Author**: GitHub Copilot  
**Date**: December 6, 2025  
**Status**: ✅ Complete and validated
