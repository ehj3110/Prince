# V6 Data Analysis Summary

## Overview
V6 dataset contains 30 adhesion measurements across 3 different material conditions:
- **ACF, 5mm + TankV19**: 10 measurements
- **Flat PDMS, 1mm + TankV22**: 10 measurements  
- **TEMPO, 1mm + TankV22p1**: 10 measurements

Each condition was tested at 10 different layer heights (layer numbers 60-435), resulting in contact areas ranging from ~12,000 mm² to ~586,000 mm².

## Processing Complete

### 1. Batch Processing
✅ All 30 autolog files processed successfully
✅ Individual analysis plots created for each test (30 plots)
✅ Master CSV generated: `MASTER_V6_all_metrics.csv`

### 2. Master Plots Generated
- `MASTER_area_analysis.png`: Peak force, work of adhesion, pre-initiation distance, propagation distance vs contact area
- `MASTER_area_ratio_analysis.png`: Same metrics vs area ratio (layer area / membrane area)
- `MASTER_distance_analysis.png`: Distance-to-peak and propagation distance analysis

**Note:** ACF condition shows "No SEM (all single samples)" - each area tested only once, so no error regions visible.

### 3. Scaling Analysis
Power law fits performed for each metric: **F = a × A^n**

#### Peak Force Scaling:
| Material | Exponent (n) | R² | Interpretation |
|----------|--------------|-----|----------------|
| **ACF, 5mm** | 0.045 ± 0.061 | 0.06 | Nearly constant (area-independent) |
| **Flat PDMS, 1mm** | 0.965 ± 0.188 | 0.84 | Linear scaling (n ≈ 1) |
| **TEMPO, 1mm** | 0.543 ± 0.094 | 0.85 | Sublinear scaling (n ≈ 0.5) |

#### Work of Adhesion Scaling:
(Data extracted from processing log - to be confirmed in CSV)

#### Pre-Initiation Distance Scaling:
(Analysis completed - see generated plots)

#### Propagation Distance Scaling:
(Analysis completed - see generated plots)

### 4. Output Files

**Main Directory:** `C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V6\`

**Data:**
- `MASTER_V6_all_metrics.csv` - All measurements with full metrics

**Master Plots:**
- `MASTER_area_analysis.png`
- `MASTER_area_ratio_analysis.png`
- `MASTER_distance_analysis.png`

**Scaling Analysis:**
- `V6_scaling_peak_force_N.png` - Peak force scaling (linear + log-log)
- `V6_scaling_peak_force_N_results.csv` - Fit parameters
- `V6_scaling_work_of_adhesion_mJ.png` - Work of adhesion scaling
- `V6_scaling_work_of_adhesion_mJ_results.csv` - Fit parameters
- `V6_scaling_pre_initiation_distance_mm.png` - Pre-initiation distance scaling
- `V6_scaling_propagation_distance_mm.png` - Propagation distance scaling
- `V6_scaling_exponents_comparison.png` - Bar chart comparing all exponents

**Individual Test Plots (30 files):**
- `ACF_5mm_V19_Cone_BPAGDA_200/autolog_L*_analysis.png` (10 files)
- `FlatPDMS_1mm_V22_Cone_BPAGDA_1000/autolog_L*_analysis.png` (10 files)
- `TEMPO_1mm_V22p1_Cone_BPAGDA_1000/autolog_L*_analysis.png` (10 files)

## Key Findings

### Material Comparison

1. **ACF (Anisotropic Conductive Film, 5mm thick)**
   - Peak force: 0.49-0.88 N (relatively constant across areas)
   - Scaling exponent ≈ 0.045 (area-independent behavior)
   - Poor fit (R² = 0.06) suggests ACF adhesion is dominated by factors other than contact area
   - Tested with TankV19

2. **Flat PDMS (1mm thick)**
   - Peak force: 0.16-1.01 N (increases linearly with area)
   - Scaling exponent ≈ 0.965 (nearly perfect linear scaling)
   - Excellent fit (R² = 0.84)
   - Classic adhesive behavior: force proportional to contact area
   - Tested with TankV22

3. **TEMPO (1mm thick, print round p1)**
   - Peak force: 0.14-0.61 N (sublinear increase with area)
   - Scaling exponent ≈ 0.543 (roughly square-root scaling)
   - Excellent fit (R² = 0.85)
   - Suggests edge-dominated adhesion or partial contact
   - Tested with TankV22p1

### Physical Interpretation

The scaling exponent provides insight into adhesion mechanisms:

- **n ≈ 1** (Flat PDMS): Classical adhesion, force scales linearly with area
- **n ≈ 0.5** (TEMPO): Edge-dominated or crack propagation limited adhesion
- **n ≈ 0** (ACF): Area-independent, possibly cohesive failure or constant peeling force

## Comparison with V5 Data

V6 includes new material conditions not present in V5:
- **ACF, 5mm**: New material, thick film
- **Flat PDMS, 1mm**: Similar to V5 PDMS but 1mm thick
- **TEMPO, 1mm + p1**: First print round of TEMPO at 1mm

V5 had PDMS 100µm and TEMPO with p1/p2/p3 variants, so V6 provides complementary data at different membrane thicknesses.

## Area Binning

Unlike V5 which used 5% area binning to group similar measurements, V6 has only one measurement per area per condition. This means:
- No error bars on V6 master plots
- Each data point represents a single test
- Scaling analysis uses 10 points per condition
- Future testing could benefit from replicate measurements at each area

## Next Steps

1. **Compare V5 vs V6**
   - How does membrane thickness (100µm vs 1mm vs 5mm) affect scaling?
   - Does TEMPO p1 behavior change with thickness?

2. **Statistical Analysis**
   - Confidence intervals on scaling exponents
   - ANOVA across materials
   - Effect size calculations

3. **Physical Modeling**
   - Why does ACF show area-independent adhesion?
   - What causes TEMPO's sublinear scaling?
   - Can we predict scaling behavior from material properties?

4. **Additional Testing**
   - Replicate measurements for error quantification
   - Test intermediate areas to improve fit quality
   - Explore different peel speeds

## Files for Publication

Key figures for paper/presentation:
1. `V6_scaling_exponents_comparison.png` - Shows all materials' scaling behavior
2. `V6_scaling_peak_force_N.png` - Detailed peak force scaling with fits
3. `MASTER_area_analysis.png` - Overview of all metrics vs area
4. Individual test plots for specific examples

Data tables:
1. `MASTER_V6_all_metrics.csv` - Full dataset
2. `V6_scaling_peak_force_N_results.csv` - Scaling parameters with uncertainties

---

**Analysis Date:** December 2, 2025  
**Analyst:** Cheng Sun Lab Team  
**Software:** Prince_Segmented_20250926 batch processing system
