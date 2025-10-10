# Archive Directory Structure

This directory contains archived experimental code, test data, and debugging materials from the Prince 3D Printer development project.

**Last Updated:** October 5, 2025

---

## 📁 Directory Organization

### `/filtering_experimentation`
**Purpose:** Complete analysis of signal filtering methods for force data

**Contents:**
- Signal filter comparison scripts (Gaussian, Median, Butterworth, Savitzky-Golay)
- Hybrid filter development (Median + Secondary filter chains)
- Quantitative scoring methodology (Combined Score = Fidelity + λ * Roughness)
- Full parameter grid search results
- Visualization plots for all filter combinations

**Key Finding:**
- **Optimal Filter Chain:** `Median(kernel=5) → Gaussian(σ=1)`
- **Combined Score:** 0.0207 (lambda=1.0)
- **Performance:** Best balance between noise reduction and edge preservation

**Key Files:**
- `README.md` - Complete methodology documentation
- `full_results_table.txt` - All filter combinations ranked by score
- `apply_default_filter.py` - Implementation of optimal filter
- `fft_filter_demonstration.py` - Frequency domain analysis
- `sawtooth_filter_test.py` - Filter testing on synthetic signals

**Analysis Data:**
- `autolog_L345-L349` and `autolog_L80-L84` test datasets
- Multiple lambda values tested (λ = 10, 15, 30, 50)
- Comparison plots showing filter performance

---

### `/test_scripts`
**Purpose:** Development and validation test scripts

**Contents:**
- Unit tests for adhesion calculator
- Baseline detection validation scripts
- Layer boundary detection tests
- Peak force logger testing
- Sensor data window tests
- Method comparison scripts

**Key Files:**
- `test_adhesion_calculator.py` - Calculator unit tests
- `test_baseline_detection.py` - Baseline algorithm validation
- `compare_baseline_methods.py` - Old vs new method comparison
- `verify_new_method.py` - Time-based derivative validation
- `debug_derivative_plotter.py` - Derivative visualization tool

**Status:** All tests passed; validated 451 layers across 9 test conditions

---

### `/test_data`
**Purpose:** Test datasets and validation CSV files

**Subfolders:**
- `/autolog_analysis` - Analysis results from test layer ranges

**Contents:**
- Historical autolog CSV files (L48-L50, L110-L114, L198-L200, etc.)
- Test output CSVs from development
- Analysis plots for validation layers

**Key Datasets:**
- `autolog_L48-L50.csv` - Initial validation dataset
- `autolog_L198-L200.csv` - Secondary validation
- `autolog_L110-L114.csv` - False baseline detection test case
- Various layer range plots showing analysis results

**Note:** These files were used to validate the time-based derivative method and time-gap layer clustering algorithm.

---

### `/debug_plots`
**Purpose:** Debugging visualization outputs

**Contents:**
- Baseline detection debugging plots
- Layer boundary detection visualizations
- Derivative analysis plots
- Method comparison visualizations

**Key Files:**
- `baseline_test_L111.png` - Shows false positive elimination
- `layer_boundaries_debug.png` - Layer clustering visualization

---

### `/experimental_analysis`
**Purpose:** Experimental and superseded analysis scripts

**Contents:**
- Early batch processing implementations
- Hybrid adhesion analysis system (v1)
- Legacy post-print analyzer
- Experimental plotting tools

**Key Files:**
- `batch_process_printing_data.py` - Early batch analysis (superseded by batch_v17_analysis.py)
- `hybrid_adhesion_plotter.py` - Experimental plotter (superseded by analysis_plotter.py)
- `post_print_analyzer.py` - Early version (now in post-processing/)
- `final_layer_visualization.py` - Experimental visualization

**Status:** These scripts were experimental versions that informed the final production implementations.

---

### `/legacy_docs`
**Purpose:** Old documentation and project notes

**Contents:**
- Historical project documentation
- Early README versions
- Development notes

---

### `/old_scripts`
**Purpose:** Deprecated scripts from previous development phases

**Contents:**
- Superseded analysis implementations
- Old GUI components
- Deprecated utility functions

---

### `/old_plots`
**Purpose:** Historical plot outputs

**Contents:**
- Plots from early development
- Comparison visualizations
- Test outputs

---

### `/analysis_files`
**Purpose:** Historical analysis outputs

**Contents:**
- Old CSV analysis results
- Intermediate processing outputs

---

### `/redundant_scripts`
**Purpose:** Duplicate or redundant code

**Contents:**
- Scripts that were duplicated during development
- Redundant implementations

---

## 🔬 Key Technical Milestones Documented

### 1. Filter Development (October 2025)
**Problem:** Noisy force data obscuring adhesion metrics
**Solution:** Hybrid filter chain with quantitative optimization
**Result:** Median(k=5) → Gaussian(σ=1) identified as optimal

### 2. Baseline Detection Fix (October 2025)
**Problem:** False positives from random force spikes
**Solution:** Time-based derivatives + Gaussian smoothing
**Result:** 100% accuracy on validation dataset

### 3. Layer Boundary Detection (October 2025)
**Problem:** Only 1 layer detected instead of 5 in multi-layer files
**Solution:** Time-gap clustering (8-second threshold)
**Result:** 100% detection accuracy across 451 layers

---

## 📊 Validation Results Summary

### Filter Testing
- **Filters Tested:** 30+ combinations
- **Parameters Evaluated:** 100+ unique configurations
- **Lambda Values:** 1.0, 10.0, 15.0, 30.0, 50.0
- **Winner:** Median(k=5) → Gaussian(σ=1)

### Algorithm Validation
- **Total Layers Tested:** 451
- **Test Conditions:** 9 unique combinations
- **Layer Detection Accuracy:** 100%
- **Baseline Detection False Positives:** 0
- **Speed Range:** 0.5 - 6.0 mm/min

---

## 🗂️ File Retention Policy

**Keep Indefinitely:**
- Filtering experimentation results (valuable research)
- Test scripts (for regression testing)
- Validation datasets (benchmarking)

**Review Periodically:**
- Debug plots (can delete after 6 months)
- Old scripts (verify no unique logic before deletion)

**Safe to Delete:**
- Duplicate files
- Superseded implementations (if logic preserved elsewhere)
- Temporary test outputs

---

## 📝 Integration Status

All validated methods from this archive have been integrated into production:

✅ **Filtering:** Median(k=5) → Gaussian(σ=1) ready for integration  
✅ **Baseline Detection:** Time-based derivatives in `adhesion_metrics_calculator.py`  
✅ **Layer Detection:** Time-gap clustering in `RawData_Processor.py`  
✅ **Peak Force Logging:** Updated `PeakForceLogger.py` uses new calculator  

---

## 👥 Contributors

**Evan Jones** - Signal processing, filtering experimentation, algorithm development  
**AI Assistant (Claude)** - Code review, testing, documentation  
**Professor Cheng Sun** - Research direction, validation  

---

## 📞 Questions?

For questions about archived materials or to retrieve experimental code:
- Evan Jones: evanjones2026@u.northwestern.edu

---

**Archive Structure Version:** 2025.10.05
