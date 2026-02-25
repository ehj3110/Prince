# Batch Processor Tests & Debug Scripts Archive

**Archive Date:** February 25, 2026  
**Reason:** One-time test/validation scripts no longer actively used

---

## Contents

This directory contains test and debug scripts used during development and validation of batch processing features. These scripts served specific purposes during development but are no longer actively used in production.

### Test Scripts

#### 1. **test_fep_plots.py**
- **Purpose:** Test script to regenerate plots for FEP folder only
- **Date:** ~January 2026
- **Description:** Quick test to verify plot generation for single FEP condition
- **Status:** Debug/verification complete
- **Usage:** 
  ```python
  from batch_process_v9 import V9BatchProcessor
  processor = V9BatchProcessor(skip_individual_plots=False)
  processor.process_single_folder(fep_folder)
  ```

#### 2. **test_hydrodynamic_skip.py**
- **Purpose:** Test skip_initial_time_ms parameter with synthetic data
- **Date:** January 11, 2026
- **Description:** Creates synthetic force curves with hydrodynamic spikes to verify skip feature works correctly
- **Status:** Feature validated, now deployed in AdhesionMetricsCalculator
- **Key Test:** Verified 150ms skip removes initial spike while preserving real peak

#### 3. **reprocess_tempo.py**
- **Purpose:** Reprocess only TEMPO folders with updated hydrodynamic mitigation
- **Date:** ~January 2026
- **Description:** Targeted reprocessing of TEMPO_200um folders with extended skip time
- **Status:** One-time reprocessing complete
- **Folders Processed:**
  - TEMPO_200um_V23Ext_UPW_1000
  - TEMPO_200um_V23Ext_Water_1000

### Validation Scripts

#### 4. **check_results.py**
- **Purpose:** Quick validation of V9 MASTER_all_metrics.csv
- **Date:** ~January 2026
- **Description:** Prints summary statistics and condition counts
- **Output:** Total layers, columns, condition summary with mean/std
- **Status:** One-time validation

#### 5. **check_tempo_results.py**
- **Purpose:** Verify TEMPO data after 200ms skip applied
- **Date:** ~January 2026
- **Description:** Detailed check of TEMPO conditions showing peak forces for largest areas
- **Output:** Layer counts, peak force statistics, largest area analysis
- **Status:** Validation complete, hydrodynamic mitigation confirmed working

### Plot Generation Scripts

#### 6. **generate_v9_median_plots.py**
- **Purpose:** Generate median-aggregated master plots for V9 data
- **Date:** January 10, 2026
- **Description:** Uses MAD (Median Absolute Deviation) instead of SEM for error bars
- **Generated Files:**
  - MASTER_radius_analysis_MEDIAN.png
  - MASTER_radius_analysis_modified_MEDIAN.png
- **Status:** One-time plot generation, median support now in MasterPlotter class
- **Superseded By:** `MasterPlotter.generate_radius_analysis_plot_median()`

#### 7. **organize_and_generate_v9_loglog.py**
- **Purpose:** Reorganize V9 plots into folders and generate log-log versions
- **Date:** January 11, 2026
- **Description:** 
  - Created folder structure (data/, Mean plots/, Median plots/, Log-Log plots/)
  - Moved existing files into appropriate folders
  - Generated new log-log master plots
- **Status:** One-time organization task complete

---

## Why These Were Archived

### Development Lifecycle

1. **Feature Development:** New features need isolated testing (test_hydrodynamic_skip.py)
2. **Validation:** Results need verification against expected behavior (check_*.py)
3. **Deployment:** Feature integrated into production code (AdhesionMetricsCalculator)
4. **Archive:** Test scripts no longer needed for routine operations

### Current Workflow

**For new datasets:**
- Use `batch_process_universal.py` (handles all cases)
- Hydrodynamic skip is automated based on speed parameter
- Median plots available via MasterPlotter class methods
- Validation done through standard output inspection

**For debugging:**
- Check generated CSV files directly
- Review autolog plots in timestamped folders
- Use MasterPlotter for custom visualizations

---

## Historical Context

These scripts document the iterative development of robust batch processing:

- **Early January 2026:** Discovered hydrodynamic locking in high-speed tests
- **Mid January 2026:** Developed and tested time-based skip feature
- **Late January 2026:** Added median aggregation support
- **February 2026:** Consolidated all features into universal processor

---

## If You Need to Reference These Scripts

**For test methodology:**
- `test_hydrodynamic_skip.py` shows how to create synthetic test data
- Demonstrates proper validation approach for signal processing features

**For validation approach:**
- `check_*.py` scripts show useful summary statistics to review
- Template for quick data quality checks

**For plot generation:**
- `generate_v9_median_plots.py` shows median aggregation implementation
- `organize_and_generate_v9_loglog.py` shows file organization automation

---

## Related Documentation

- [HYDRODYNAMIC_LOCKING_MITIGATION.md](../../documentation/technical/HYDRODYNAMIC_LOCKING_MITIGATION.md) - Feature documentation
- [COMPREHENSIVE_PLOT_FORMAT_GUIDE.md](../../COMPREHENSIVE_PLOT_FORMAT_GUIDE.md) - Plot formatting standards
- [batch_processors/README.md](../../batch_processors/README.md) - Current batch processor overview

---

**Archived by:** Workspace cleanup Phase 3  
**Scripts remain functional** but are no longer actively maintained
