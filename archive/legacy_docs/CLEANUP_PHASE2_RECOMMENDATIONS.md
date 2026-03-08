# Comprehensive Cleanup Recommendations - Phase 2 Complete
**Date:** February 25, 2026  
**Status:** Phase 2 complete, additional recommendations provided

---

## ✅ Phase 2 Complete: Dataset-Specific Batch Processors

**Actions Taken:**
- Created `archive/dataset_specific_batch_processors/` directory
- Moved 6 dataset-specific scripts from root:
  1. `batch_process_final_presentation.py`
  2. `batch_process_final_with_areas.py`
  3. `batch_process_presentation_data.py`
  4. `batch_process_tempopicker_v2.py`
  5. `batch_process_tempopicker_v2_with_skip.py`
  6. `batch_process_v2_selected.py`
- Created comprehensive README documenting purpose, features, and migration notes

**Impact:** Root directory further cleaned, 6 less files cluttering workspace

---

## 📋 Additional Cleanup Opportunities Identified

### Category 1: batch_processors/ Directory

#### **A. One-Time Test/Debug Scripts (7 scripts) - ARCHIVE**

**Recommendation:** Move to `archive/batch_processor_tests/`

1. **test_fep_plots.py** (24 lines)
   - Purpose: Test script to regenerate plots for FEP folder only
   - Status: One-time debug script
   - Action: Archive

2. **test_hydrodynamic_skip.py** (133 lines)
   - Purpose: Test skip_initial_time_ms parameter with synthetic data
   - Date: January 11, 2026
   - Status: Feature verification test (feature now in production)
   - Action: Archive

3. **reprocess_tempo.py** (43 lines)
   - Purpose: Reprocess only TEMPO folders with updated mitigation
   - Status: One-time reprocessing task
   - Action: Archive

4. **check_results.py** (30 lines)
   - Purpose: Quick check of V9 MASTER_all_metrics.csv
   - Status: Data validation script
   - Action: Archive

5. **check_tempo_results.py** (47 lines)
   - Purpose: Check TEMPO data after 200ms skip applied
   - Status: Data validation script
   - Action: Archive

6. **generate_v9_median_plots.py** (76 lines)
   - Purpose: Generate median master plots for V9 (superseded by MasterPlotter)
   - Date: January 10, 2026
   - Status: One-time plot generation
   - Action: Archive

7. **organize_and_generate_v9_loglog.py** (181 lines)
   - Purpose: Reorganize V9 master plots into folders + generate log-log
   - Date: January 11, 2026
   - Status: One-time organization task
   - Action: Archive

#### **B. Analysis Scripts (2 scripts) - ARCHIVE**

**Recommendation:** Move to `archive/analysis_investigations/`

8. **investigate_fep_scaling.py** (208 lines)
   - Purpose: Investigate FEP scaling discrepancy (sub-linear visual vs super-linear fit)
   - Date: January 10, 2026
   - Status: Research investigation (findings documented)
   - Action: Archive - conclusions documented in MEDIAN_PLOTS_AND_FEP_SCALING_SUMMARY.md

9. **analyze_v6_scaling.py** (in batch_processors/)
   - Purpose: Analyze V6 data scaling behavior
   - Status: One-time analysis
   - Action: Archive

#### **C. V9-Specific Master Plot Generator (1 script) - ARCHIVE**

**Recommendation:** Move to `archive/dataset_specific_batch_processors/`

10. **v9_automated_work_master_plots.py** (522 lines)
   - Purpose: Create master plots using automated_work_of_adhesion.csv files from V9
   - Date: January 10, 2026
   - Status: Dataset-specific (V9 only), superseded by MasterPlotter
   - Action: Archive with dataset-specific processors

#### **D. Core Batch Processors - KEEP**

**These should stay in batch_processors/ - they are actively used:**

1. **batch_process_universal.py** ✓ - Universal processor for any dataset
2. **batch_process_steppedcone_generalized.py** ✓ - Generalized processor
3. **batch_process_tempo_picker.py** ✓ - TEMPO picker specific
4. **batch_process_v4_data.py** ✓ - V4 legacy support
5. **batch_process_v5_data.py** ✓ - V5 legacy support
6. **batch_process_v6_data.py** ✓ - V6 support
7. **batch_process_v9.py** ✓ - V9 support (V9BatchProcessor class)
8. **batch_process_printing_data.py** ✓ - Printing data processor

---

### Category 2: Root Directory Markdown Files

#### **A. Analysis Summaries (5 docs) - MOVE TO documentation/analysis_summaries/**

These document specific analysis results/iterations:

1. **FINAL_PROGRESSIVE_PLOTS_SUMMARY.md** (188 lines)
   - Date: January 20, 2026
   - Content: Progressive reveal presentation plots (8 master plots)
   - Purpose: Documents Final folder analysis with consistent axis scaling
   - Action: Move to `documentation/analysis_summaries/`

2. **MEDIAN_PLOTS_AND_FEP_SCALING_SUMMARY.md** (204 lines)
   - Date: January 10, 2026
   - Content: Median plots implementation + FEP scaling investigation
   - Purpose: Documents median aggregation feature and FEP discrepancy research
   - Action: Move to `documentation/analysis_summaries/`

3. **PRESENTATION_DATA_ANALYSIS_SUMMARY.md** (268 lines)
   - Date: January 20, 2026
   - Content: Comprehensive analysis of 604 measurements from 9 conditions
   - Purpose: Documents Presentation folder processing results
   - Action: Move to `documentation/analysis_summaries/`

4. **TEMPO_PICKER_V2_SUMMARY.md** (178 lines)
   - Date: January 20, 2026
   - Content: Master plot generation for 1,080 TEMPO Picker V2 measurements
   - Purpose: Documents TEMPO Picker V2 dataset processing
   - Action: Move to `documentation/analysis_summaries/`

5. **HYDRODYNAMIC_LOCKING_MITIGATION.md** (176 lines)
   - Date: January 11, 2026
   - Content: Time-based peak detection skip feature
   - Purpose: Documents skip_initial_time_ms implementation
   - Action: Move to `documentation/technical/` (it's a technical feature doc)

#### **B. Style/Format Guides - MOVE TO documentation/**

6. **PLOT_STYLE_GUIDE.md** (296 lines)
   - Version: 2.0, January 15, 2026
   - Content: Autolog plot styling standards
   - Action: Move to `documentation/` (general reference)

7. **COMPREHENSIVE_PLOT_FORMAT_GUIDE.md** (just created)
   - Version: 1.0, February 25, 2026
   - Content: Complete format reference for all plot types
   - Action: Already in root, should move to `documentation/`

#### **C. Workspace Organization - KEEP IN ROOT**

8. **WORKSPACE_ORGANIZATION_RECOMMENDATIONS.md** ✓
   - Purpose: Workspace cleanup plan (this document)
   - Action: Keep in root for visibility

9. **README.md** ✓
   - Purpose: Project overview
   - Action: Keep in root

---

### Category 3: Root Directory Log Files

**Recommendation:** Move to `archive/logs/`

1. **presentation_data_reprocess_log.txt** - Presentation data reprocessing log
2. **tempo_processing_log.txt** - TEMPO processing log
3. **tempopicker_v2_reprocess_log.txt** - TEMPO Picker V2 reprocessing log
4. **tempopicker_v2_batch_log.txt** - TEMPO Picker V2 batch log

**Note:** Keep `force_gauge_calibration_20251106_144013.txt` in root (it's calibration data, not a log)

---

### Category 4: Data Files in Root

**Recommendation:** Create `data/` directory and move

1. **v9_area_mapping.csv** - V9 layer-to-area mapping data
   - Action: Move to `data/` directory

---

## 📦 Proposed Archive Structure

```
archive/
├── batch_processor_tests/          # NEW - Test/debug scripts
│   ├── README.md
│   ├── test_fep_plots.py
│   ├── test_hydrodynamic_skip.py
│   ├── reprocess_tempo.py
│   ├── check_results.py
│   ├── check_tempo_results.py
│   ├── generate_v9_median_plots.py
│   └── organize_and_generate_v9_loglog.py
│
├── analysis_investigations/        # NEW - Research investigations
│   ├── README.md
│   ├── investigate_fep_scaling.py
│   └── analyze_v6_scaling.py
│
├── dataset_specific_batch_processors/  # COMPLETED
│   ├── README.md
│   ├── batch_process_final_presentation.py
│   ├── batch_process_final_with_areas.py
│   ├── batch_process_presentation_data.py
│   ├── batch_process_tempopicker_v2.py
│   ├── batch_process_tempopicker_v2_with_skip.py
│   ├── batch_process_v2_selected.py
│   └── v9_automated_work_master_plots.py  # NEW
│
├── logs/                           # NEW - Processing logs
│   ├── presentation_data_reprocess_log.txt
│   ├── tempo_processing_log.txt
│   ├── tempopicker_v2_reprocess_log.txt
│   └── tempopicker_v2_batch_log.txt
│
├── one_time_scripts/               # FROM PHASE 1
│   └── [28 scripts already archived]
│
├── legacy_docs/                    # EXISTING
│   └── [legacy documentation]
│
└── unused_modules/                 # EXISTING
    └── [deprecated code]
```

---

## 📁 Proposed documentation/ Structure

```
documentation/
├── analysis_summaries/             # NEW - Dataset analysis results
│   ├── FINAL_PROGRESSIVE_PLOTS_SUMMARY.md
│   ├── MEDIAN_PLOTS_AND_FEP_SCALING_SUMMARY.md
│   ├── PRESENTATION_DATA_ANALYSIS_SUMMARY.md
│   └── TEMPO_PICKER_V2_SUMMARY.md
│
├── technical/                      # EXISTING - Technical docs
│   ├── HYDRODYNAMIC_LOCKING_MITIGATION.md  # NEW
│   ├── ANALYSIS_RESULTS_COMPARISON.md
│   ├── POST_PRINT_ANALYSIS_INTEGRATION.md
│   ├── SANDWICH_ROUTINE.md
│   ├── UNIFIED_CALCULATOR_IMPLEMENTATION.md
│   └── WORK_OF_ADHESION_METRICS_DEFINITIONS.md
│
├── PLOT_STYLE_GUIDE.md            # NEW - Moved from root
├── COMPREHENSIVE_PLOT_FORMAT_GUIDE.md  # NEW - Moved from root
├── [other existing docs...]
└── README.md
```

---

## 📊 Summary Statistics

### Phase 2 (Completed):
- **Archived:** 6 dataset-specific batch processors
- **Root files removed:** 6

### Additional Recommendations:
- **batch_processors/ to archive:** 10 scripts (test/debug/analysis)
- **Root .md files to move:** 7 docs (5 to analysis_summaries/, 2 to documentation/)
- **Root .txt files to archive:** 4 log files
- **Root .csv to organize:** 1 data file

### Total Additional Cleanup Potential:
- **22 more files** can be organized for cleaner workspace
- **Root directory:** From 11 Python files → could reduce to ~6-7 with data/log organization

---

## 🎯 Recommended Next Steps (In Order)

### Phase 3: Archive batch_processors Tests & Investigations
1. Create `archive/batch_processor_tests/`
2. Create `archive/analysis_investigations/`
3. Move 10 scripts from batch_processors/
4. Create README files documenting each archive

### Phase 4: Organize Documentation
1. Create `documentation/analysis_summaries/`
2. Move 5 analysis summary .md files from root
3. Move HYDRODYNAMIC_LOCKING_MITIGATION.md to `documentation/technical/`
4. Move 2 style guides to `documentation/`

### Phase 5: Archive Logs & Organize Data
1. Create `archive/logs/`
2. Move 4 .txt log files from root
3. Create `data/` directory
4. Move v9_area_mapping.csv to `data/`

---

## ⚠️ Files to Keep in Root

**Essential root files:**
- `Prince_Segmented.py` - Main application
- `process_folder.py` - Folder processing utility
- `tempo_picker_plot_styles.py` - Plot style functions (actively used)
- `README.md` - Project overview
- `WORKSPACE_ORGANIZATION_RECOMMENDATIONS.md` - This cleanup plan
- `.gitignore` - Git configuration
- `force_gauge_calibration_20251106_144013.txt` - Important calibration data
- `v9_area_mapping.csv` - Until data/ folder created
- `CLEAR_PYTHON_CACHE.bat` - Utility script

---

## 📈 Benefits of Proposed Cleanup

1. **Clearer Purpose:** batch_processors/ contains only production processors
2. **Better Organization:** Analysis summaries grouped together
3. **Easier Navigation:** Related documents in appropriate folders
4. **Preserved History:** All scripts archived with context, not deleted
5. **Reduced Clutter:** Root directory much cleaner
6. **Improved Onboarding:** New team members can find relevant docs easily

---

**Next Action:** Would you like to proceed with:
- Phase 3 (Archive batch processor tests)?
- Phase 4 (Organize documentation)?
- Phase 5 (Archive logs & organize data)?
- All remaining phases?

