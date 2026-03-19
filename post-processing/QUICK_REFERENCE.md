# Quick Reference Guide - Modular Analysis Tools

## One-Line Commands

### Complete Pipeline (Everything at Once)
```powershell
# Batch process + all analyses
python run_complete_analysis.py --folder V3

# Use existing MASTER CSV (skip batch)
python run_complete_analysis.py --folder V3 --skip-batch
```

---

## Individual Modules

### 1. Batch Processing Only
```powershell
python batch_process_steppedcone_generalized.py --folder V3
```

**Output**: MASTER CSV + 4 master plots + individual layer plots

---

### 2. Quality Control
```powershell
python data_validator.py
```

**What it does**:
- Checks for negative values
- Identifies outliers (>3σ)
- Validates physical limits
- Flags missing data

**Output**: `QC_Report.txt`

---

### 3. Advanced Metrics & Scaling Laws
```powershell
python advanced_metrics.py
```

**What it does**:
- Adds 5 normalized metrics (force/area, work/area, etc.)
- Fits power law: Force = k × Area^n
- Tests JKR theory (expects n ≈ 1.0)

**Output**:
- `MASTER_steppedcone_metrics_ENHANCED.csv`
- `scaling_analysis_results.csv`
- `scaling_analysis_*.png` (2 plots)

---

### 4. Statistical Analysis
```powershell
python statistical_analysis.py
```

**What it does**:
- ANOVA: Tests if any conditions differ
- Pairwise t-tests: Identifies which pairs differ
- Bonferroni correction
- Cohen's d effect sizes

**Output**:
- `Statistical_Analysis_Report.txt`
- `ANOVA_results.csv`
- `pairwise_*.csv` (one per metric)

---

### 5. Generate Reports
```powershell
python generate_analysis_report.py
```

**What it does**:
- Combines all analysis results
- Creates multi-page PDF
- Quick text summary

**Output**:
- `Quick_Summary.txt`
- `Analysis_Report_*.pdf`

---

## Common Workflows

### First Time Analysis
```powershell
# Step 1: Process raw data
python batch_process_steppedcone_generalized.py --folder V3

# Step 2: Check data quality
python data_validator.py

# Step 3: Add advanced metrics
python advanced_metrics.py

# Step 4: Statistical tests
python statistical_analysis.py

# Step 5: Generate report
python generate_analysis_report.py
```

---

### Re-run Analysis (Data Already Processed)
```powershell
# Just run the pipeline, skip batch processing
python run_complete_analysis.py --folder V3 --skip-batch
```

---

### Quick Summary Only
```powershell
python -c "from generate_analysis_report import ReportGenerator; from pathlib import Path; g = ReportGenerator(); print(g.generate_quick_summary(Path('V3/MASTER_steppedcone_metrics.csv')))"
```

---

## File Locations

### Input Files
- Raw CSV files: `SteppedConeTests/V3/SteppedCone_*/autolog_*.csv`
- Area mapping: `SteppedConeTests/V3/LayerToArea.txt`

### Output Files (in `V3/` directory)
- `MASTER_steppedcone_metrics.csv` - All metrics
- `MASTER_steppedcone_metrics_ENHANCED.csv` - With normalized metrics
- `MASTER_*.png` - Master plots (4 files)
- `QC_Report.txt` - Quality control
- `Statistical_Analysis_Report.txt` - Stats
- `scaling_analysis_*.png` - Scaling plots
- `Analysis_Report_*.pdf` - Complete PDF

---

## Customization

### Batch Processing Options
```powershell
# Skip individual plots
python batch_process_steppedcone_generalized.py --folder V3 --skip-plots

# CSV only (no plots)
python batch_process_steppedcone_generalized.py --folder V3 --csv-only

# Custom output directory
python batch_process_steppedcone_generalized.py --folder V3 --output-dir "C:/custom/path"
```

### Statistical Analysis Options
```python
# In Python script or interactive session
from statistical_analysis import StatisticalAnalyzer

# Change significance level
analyzer = StatisticalAnalyzer(alpha=0.01)  # More stringent

# Skip Bonferroni correction
pairwise = analyzer.pairwise_comparisons(df, 'peak_force_N', correction='none')
```

### Report Generation Options
```python
from generate_analysis_report import ReportGenerator

generator = ReportGenerator()

# Minimal report (no PDF)
summary = generator.generate_quick_summary(master_csv)

# Custom PDF sections
pdf = generator.generate_full_report(
    master_csv,
    output_dir='.',
    include_qc=True,
    include_stats=False,  # Skip stats
    include_scaling=True,
    include_plots=True
)
```

---

## Troubleshooting

### Problem: "MASTER CSV not found"
**Solution**: Run batch processing first
```powershell
python batch_process_steppedcone_generalized.py --folder V3
```

---

### Problem: Import errors
**Solution**: Ensure you're in the `post-processing` directory
```powershell
cd post-processing
python run_complete_analysis.py --folder V3
```

---

### Problem: "No module named 'pandas'"
**Solution**: The packages are installed, but your IDE doesn't see them. The code will work when you run it. To verify:
```powershell
python -c "import pandas; print('OK')"
```

---

### Problem: PDF generation fails
**Solution**: Use the text report instead
```powershell
# QC report is text-based
python data_validator.py

# Statistical report is text-based
python statistical_analysis.py

# Quick summary is text-based
python -c "from generate_analysis_report import ReportGenerator; from pathlib import Path; g = ReportGenerator(); g.generate_quick_summary(Path('V3/MASTER_steppedcone_metrics.csv'), Path('V3/Quick_Summary.txt'))"
```

---

## Scientific Questions → Commands

### "Which condition has the highest adhesion?"
```powershell
python statistical_analysis.py
# Check Statistical_Analysis_Report.txt → GROUP STATISTICS
```

### "Does force scale with area?"
```powershell
python advanced_metrics.py
# Check scaling_analysis_results.csv → exponent column
# n ≈ 1.0 = linear scaling (JKR theory)
```

### "Are there any bad data points?"
```powershell
python data_validator.py
# Check QC_Report.txt → HIGH Severity issues
```

### "What's the mean force for each condition?"
```powershell
python -c "import pandas as pd; df = pd.read_csv('V3/MASTER_steppedcone_metrics.csv'); print(df.groupby('condition_label')['peak_force_N'].agg(['mean', 'std']))"
```

---

## Integration with Existing Workflow

### Before (Old Workflow)
```powershell
# Manually edit batch_process_v3.py
python batch_process_v3.py
# Open Excel, manually analyze
```

### After (New Modular Workflow)
```powershell
# One command
python run_complete_analysis.py --folder V3

# Or step-by-step with individual modules
python batch_process_steppedcone_generalized.py --folder V3
python data_validator.py
python advanced_metrics.py
python statistical_analysis.py
```

**Benefits**:
- ✅ Reusable across V2, V3, V4, etc.
- ✅ No manual editing required
- ✅ Automated statistical tests
- ✅ PDF reports
- ✅ Reproducible workflow

---

## Next Steps

### To analyze V4 data (when available):
```powershell
python run_complete_analysis.py --folder V4
```

### To compare V3 vs V4:
```powershell
# Combine MASTER CSVs
python -c "import pandas as pd; v3 = pd.read_csv('V3/MASTER_steppedcone_metrics.csv'); v4 = pd.read_csv('V4/MASTER_steppedcone_metrics.csv'); combined = pd.concat([v3, v4]); combined.to_csv('MASTER_V3_V4_combined.csv', index=False)"

# Run analysis on combined data
# (Requires minor modification to scripts to accept custom CSV path)
```

---

## Full Documentation
See `MODULAR_ANALYSIS_README.md` for detailed module documentation.
