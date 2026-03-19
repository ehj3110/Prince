# Modular Analysis Tools - Documentation

**Last Updated**: October 29, 2025  
**Author**: Cheng Sun Lab Team

---

## Overview

This directory contains a modular suite of analysis tools for post-processing adhesion test data. These tools operate on the MASTER CSV output from batch processing and can be run independently or together via the master pipeline.

## Key Design Principles

1. **Modular**: Each tool is independent and can be run separately
2. **Non-Invasive**: Does not modify the core batch processing workflow
3. **Reusable**: Works with any MASTER CSV from V2, V3, V4, etc.
4. **Configurable**: Uses YAML configuration files for easy customization

---

## Module List

### Core Batch Processing
- **`batch_process_steppedcone_generalized.py`** - Universal batch processor
- **`master_plotter.py`** - Configurable master plot generator
- **`RawData_Processor.py`** - CSV loader with layer boundary detection

### Analysis Modules (NEW)
- **`data_validator.py`** - Quality control checks
- **`advanced_metrics.py`** - Normalized metrics & scaling laws
- **`statistical_analysis.py`** - ANOVA & pairwise t-tests
- **`feature_extraction.py`** - Time-series feature extraction
- **`initiation_work.py`** - Crack initiation vs propagation work
- **`generate_analysis_report.py`** - Automated PDF reports

### Pipeline Orchestration
- **`run_complete_analysis.py`** - Master pipeline runner
- **`analysis_config.yaml`** - Configuration file template

---

## Quick Start

### Option 1: Run Complete Pipeline
```powershell
# Run everything (batch processing + all analyses)
python run_complete_analysis.py --folder V3

# Use existing MASTER CSV (skip batch processing)
python run_complete_analysis.py --folder V3 --skip-batch
```

### Option 2: Run Individual Modules

#### 1. Batch Processing
```powershell
python batch_process_steppedcone_generalized.py --folder V3
```

#### 2. Quality Control
```powershell
python data_validator.py
```

#### 3. Advanced Metrics & Scaling Analysis
```powershell
python advanced_metrics.py
```

#### 4. Statistical Analysis
```powershell
python statistical_analysis.py
```

#### 5. Generate Report
```powershell
python generate_analysis_report.py
```

---

## Module Details

### 1. Data Validator (`data_validator.py`)

**Purpose**: Flag data quality issues before analysis

**Features**:
- Detect negative values in metrics that should be positive
- Identify statistical outliers (>3σ from mean)
- Check for missing critical data
- Validate physical limits (e.g., force < 5N)

**Usage**:
```python
from data_validator import DataValidator

validator = DataValidator()
qc_results = validator.validate(master_df)
validator.generate_qc_report(qc_results, output_path='QC_Report.txt')
```

**Output**:
- `QC_Report.txt` - Human-readable QC summary
- Console output with issue counts

**Example Output**:
```
Total Issues Found: 12

NEGATIVE VALUES: 2 issues
  Layer 45 (Water_1mm_1000um_s): peak_force_N = -0.0023
  
OUTLIERS: 8 issues
  HIGH Severity (2 issues):
    Layer 78 (ACF_5mm_200um_s): work_of_adhesion_mJ = 8.234 (z=4.56)
    
LIMIT VIOLATIONS: 2 issues
  Layer 103 (ACF_5mm_200um_s): peak_force_N = 5.234 (exceeds 5.0 N)
```

---

### 2. Advanced Metrics Calculator (`advanced_metrics.py`)

**Purpose**: Calculate area-normalized metrics and test scaling laws

**Features**:
- **Normalized Metrics** (intensity properties):
  - `adhesion_strength_kPa` = Force / Area
  - `work_per_area_mJ_per_mm2` = Work / Area
  - `stiffness_per_area_MPa` = Stiffness / Area
  - `retraction_strength_kPa` = Retraction Force / Area

- **Scaling Law Analysis**:
  - Fit power law: Force = k × Area^n
  - Test theoretical predictions (JKR: n ≈ 1.0)
  - Identify size effects (edge effects: n < 1, cooperative: n > 1)

**Usage**:
```python
from advanced_metrics import AdvancedMetricsCalculator

calc = AdvancedMetricsCalculator()

# Add normalized metrics
df_enhanced = calc.calculate_normalized_metrics(df)

# Perform scaling analysis
calc.generate_scaling_report(df_enhanced, output_dir='.')
```

**Output**:
- `MASTER_steppedcone_metrics_ENHANCED.csv` - Original + 5 new columns
- `scaling_analysis_results.csv` - Power law parameters by condition
- `scaling_analysis_peak_force_N.png` - Linear + log-log plots
- `scaling_analysis_work_of_adhesion_mJ.png`

**Example Results**:
```
Condition            | n_points | exponent | r² | interpretation
Water_1mm_1000um_s  | 60       | 0.98     | 0.95 | Linear scaling
ACF_5mm_200um_s     | 60       | 1.12     | 0.92 | Super-linear
```

**Scientific Interpretation**:
- **n ≈ 1.0**: Linear scaling (matches JKR theory)
- **n < 0.9**: Sub-linear (edge effects, crack nucleation barriers)
- **n > 1.1**: Super-linear (cooperative failure, bulk fracture)

---

### 3. Statistical Analyzer (`statistical_analysis.py`)

**Purpose**: Test for significant differences between conditions

**Features**:
- **One-way ANOVA**: Tests if any conditions differ
- **Pairwise t-tests**: Identifies which specific pairs differ
- **Bonferroni correction**: Controls family-wise error rate
- **Effect size**: Cohen's d (small/medium/large)

**Usage**:
```python
from statistical_analysis import StatisticalAnalyzer

analyzer = StatisticalAnalyzer(alpha=0.05)
results = analyzer.analyze_all_metrics(df)
analyzer.generate_report(results, output_path='Statistical_Analysis_Report.txt')
analyzer.save_results_csv(results, output_dir='.')
```

**Output**:
- `Statistical_Analysis_Report.txt` - Complete text report
- `ANOVA_results.csv` - F-statistics and p-values
- `pairwise_peak_force_N.csv` - All pairwise comparisons for each metric

**Example Results**:
```
METRIC: peak_force_N

ONE-WAY ANOVA
  F-statistic: 45.23
  p-value: 0.000001
  Significant: YES

PAIRWISE COMPARISONS (Bonferroni corrected)
  Water_1mm vs ACF_5mm:
    Mean difference: 0.234 N
    p-value (adj): 0.00012
    Cohen's d: 1.23 (large effect)
```

---

### 4. Feature Extractor (`feature_extraction.py`)

**Purpose**: Extract time-series features from force curves

**Features**:
- Rise time (baseline → 90% peak)
- Fall time (peak → 10% baseline)
- Asymmetry ratio (rise/fall)
- Peak sharpness (max 2nd derivative)
- Oscillation detection (FFT)
- Plateau detection

**Usage**:
```python
from feature_extraction import TimeSeriesFeatureExtractor

extractor = TimeSeriesFeatureExtractor(sampling_rate=66.67)
features = extractor.extract_features(time, force, baseline_idx, peak_idx)
```

**Output** (Dictionary):
```python
{
    'rise_time_s': 0.234,
    'fall_time_s': 1.456,
    'asymmetry_ratio': 0.161,
    'peak_sharpness': 12.34,
    'has_oscillation': True,
    'dominant_frequency': 2.5,  # Hz
    'oscillation_amplitude': 0.05
}
```

**Note**: Requires raw force curves (not just summary metrics). Integrate with `RawData_Processor` or load CSV files directly.

---

### 5. Initiation Work Calculator (`initiation_work.py`)

**Purpose**: Separate crack initiation energy from propagation energy

**Scientific Question**: How much energy is needed to START crack formation vs. CONTINUE crack propagation?

**Features**:
- **Initiation work**: Baseline → Peak (crack nucleation)
- **Propagation work**: Peak → Detachment (crack growth)
- Calculates fraction of total work in each phase

**Usage**:
```python
from initiation_work import InitiationWorkCalculator

calc = InitiationWorkCalculator()
results = calc.calculate_all(force, displacement, baseline_idx, peak_idx, end_idx)
```

**Output** (Dictionary):
```python
{
    'initiation_work_mJ': 0.123,
    'propagation_work_mJ': 0.456,
    'total_work_mJ': 0.579,
    'initiation_fraction': 0.21,  # 21% initiation, 79% propagation
    'propagation_fraction': 0.79
}
```

**Interpretation**:
- **High initiation fraction (>50%)**: Strong interfacial adhesion, significant energy barrier to crack nucleation
- **Low initiation fraction (<30%)**: Easy crack nucleation, most energy in propagation (viscous dissipation)

---

### 6. Report Generator (`generate_analysis_report.py`)

**Purpose**: Create comprehensive PDF reports

**Features**:
- Multi-page PDF with all analysis results
- Combines QC, statistics, scaling, and plots
- Configurable sections
- Quick text summaries

**Usage**:
```python
from generate_analysis_report import ReportGenerator

generator = ReportGenerator()

# Quick summary (text)
summary = generator.generate_quick_summary(master_csv, output_path='Quick_Summary.txt')

# Full PDF report
pdf_path = generator.generate_full_report(
    master_csv,
    output_dir='.',
    include_qc=True,
    include_stats=True,
    include_scaling=True,
    include_plots=True
)
```

**Output**:
- `Quick_Summary.txt` - Brief text summary
- `Analysis_Report_YYYYMMDD_HHMMSS.pdf` - Comprehensive PDF

**Report Sections**:
1. Title page with metadata
2. Table of contents
3. Data summary
4. Quality control report
5. Statistical analysis
6. Scaling analysis results + plots
7. Master plots (area, distance, stiffness, time)
8. Appendix with parameters

---

## Pipeline Workflow

### Complete Workflow Diagram
```
Raw CSV Files
    ↓
[Batch Processing] → MASTER CSV
    ↓
[Quality Control] → QC Report
    ↓
[Advanced Metrics] → Enhanced CSV + Scaling Plots
    ↓
[Statistical Tests] → ANOVA + Pairwise Results
    ↓
[Report Generation] → PDF Report
```

### Using Master Pipeline
```powershell
# Run everything
python run_complete_analysis.py --folder V3

# What it does:
# 1. Batch process all SteppedCone folders → MASTER CSV
# 2. Validate data quality → QC_Report.txt
# 3. Calculate normalized metrics → MASTER_ENHANCED.csv
# 4. Fit scaling laws → scaling_analysis_*.png
# 5. Run ANOVA & t-tests → Statistical_Analysis_Report.txt
# 6. Generate PDF → Analysis_Report_*.pdf
```

### Modular Workflow (Run Steps Separately)
```powershell
# Step 1: Batch process
python batch_process_steppedcone_generalized.py --folder V3

# Step 2: QC
python data_validator.py

# Step 3: Advanced metrics
python advanced_metrics.py

# Step 4: Statistics
python statistical_analysis.py

# Step 5: Report
python generate_analysis_report.py
```

---

## Configuration

### Using `analysis_config.yaml`

Create a configuration file to customize analysis:

```yaml
data:
  folder: V3
  base_directory: "C:/path/to/SteppedConeTests"

processing:
  skip_individual_plots: false
  csv_only: false

quality_control:
  enabled: true
  outlier_detection: true
  physical_limits:
    max_force_N: 5.0
    max_work_mJ: 10.0

plots:
  master_plots:
    - name: "MASTER_area_analysis.png"
      metrics:
        - [peak_force_N, "Peak Force (N)"]
        - [work_of_adhesion_mJ, "Work of Adhesion (mJ)"]

advanced_analysis:
  normalized_metrics:
    enabled: true
  scaling_analysis:
    enabled: true
    fit_power_law: true
  statistical_tests:
    enabled: true
    alpha: 0.05
```

---

## Output Files Reference

### From Batch Processing
- `MASTER_steppedcone_metrics.csv` - All layer metrics
- `MASTER_area_analysis.png` - Force & work vs area
- `MASTER_distance_analysis.png` - Distance metrics
- `MASTER_stiffness_analysis.png` - Stiffness & retraction
- `MASTER_time_analysis.png` - Time metrics
- Individual layer plots: `SteppedCone_*_Layer_*.png`

### From Quality Control
- `QC_Report.txt` - Data quality summary

### From Advanced Metrics
- `MASTER_steppedcone_metrics_ENHANCED.csv` - Original + normalized metrics
- `scaling_analysis_results.csv` - Power law parameters
- `scaling_analysis_peak_force_N.png` - Force scaling plots
- `scaling_analysis_work_of_adhesion_mJ.png` - Work scaling plots

### From Statistical Analysis
- `Statistical_Analysis_Report.txt` - Complete text report
- `ANOVA_results.csv` - F-statistics
- `pairwise_peak_force_N.csv` - t-test results for peak force
- `pairwise_work_of_adhesion_mJ.csv` - t-test results for work
- (one CSV per metric)

### From Report Generation
- `Quick_Summary.txt` - Brief summary
- `Analysis_Report_YYYYMMDD_HHMMSS.pdf` - Full PDF

---

## Troubleshooting

### Import Errors
If you get `ModuleNotFoundError`, ensure you're in the `post-processing` directory:
```powershell
cd post-processing
python run_complete_analysis.py --folder V3
```

### Missing MASTER CSV
If `MASTER CSV not found`:
```powershell
# Run batch processing first
python batch_process_steppedcone_generalized.py --folder V3
```

### Pandas/Matplotlib Not Found (IDE Warnings)
The import warnings in VS Code are just IDE linting issues. The code will work when you run it because the packages are installed in your Python environment. If you want to verify:
```powershell
python -c "import pandas; import matplotlib; print('All packages installed')"
```

### PDF Generation Fails
If PDF generation fails, you may need to install additional dependencies:
```powershell
pip install reportlab  # Alternative PDF library
```

The quick summary (`.txt` file) will still be generated.

---

## Scientific Use Cases

### 1. Compare Material Systems
**Question**: Does PDMS membrane have higher adhesion than ACF membrane?

**Workflow**:
```powershell
# Run analysis
python run_complete_analysis.py --folder V3 --skip-batch

# Check statistical report
# Look for "Water_1mm vs ACF_5mm" comparison
# Check Cohen's d for effect size
```

### 2. Test Scaling Laws
**Question**: Does force scale linearly with area (as JKR predicts)?

**Workflow**:
```powershell
python advanced_metrics.py

# Check scaling_analysis_results.csv
# Look for exponent column
# n ≈ 1.0 confirms linear scaling
# n < 1.0 suggests edge effects
# n > 1.0 suggests cooperative failure
```

### 3. Identify Outliers
**Question**: Are there any anomalous layers?

**Workflow**:
```powershell
python data_validator.py

# Check QC_Report.txt
# Look for HIGH severity issues
# Cross-reference with plots
```

### 4. Crack Initiation Energy
**Question**: How much energy goes into starting vs. propagating the crack?

**Workflow**:
```python
from initiation_work import InitiationWorkCalculator

calc = InitiationWorkCalculator()
# Requires raw force-displacement data
results = calc.calculate_all(force, disp, baseline_idx, peak_idx, end_idx)
print(f"Initiation fraction: {results['initiation_fraction']:.1%}")
```

---

## Development Notes

### Adding New Modules

To add a new analysis module:

1. Create `your_module.py` in `post-processing/`
2. Follow the template:
```python
"""
Your Module - Description
=========================

Features:
- Feature 1
- Feature 2

Usage:
    from your_module import YourClass
    
    analyzer = YourClass()
    results = analyzer.analyze(df)

Author: Your Name
Date: YYYY-MM-DD
"""

import pandas as pd
from pathlib import Path

class YourClass:
    def __init__(self):
        pass
    
    def analyze(self, df: pd.DataFrame):
        # Your analysis code
        pass

if __name__ == "__main__":
    # Example usage
    master_csv = Path("MASTER_steppedcone_metrics.csv")
    df = pd.read_csv(master_csv)
    
    analyzer = YourClass()
    results = analyzer.analyze(df)
```

3. Add to `run_complete_analysis.py` pipeline
4. Update this README

---

## Version History

### v1.0 - October 29, 2025
- Initial modular analysis toolkit release
- Created 6 analysis modules
- Master pipeline orchestration
- Configuration file support

### Previous Versions
- Integrated batch processor (October 28, 2025)
- Generalized batch processor (October 28, 2025)
- Peel distance fix (October 27, 2025)

---

## Contact

**Cheng Sun Lab**  
Northwestern University  

For questions or issues with the analysis pipeline, please document them in the workspace README or contact the lab.
