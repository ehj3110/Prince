# Workspace Organization Recommendations
**Date:** February 25, 2026  
**Analysis By:** Claude (GitHub Copilot)

---

## Executive Summary

Your workspace has undergone significant cleanup recently (December 2025 - January 2026), with excellent documentation consolidation and archive organization. However, **49 Python scripts remain in the root directory** that could be better organized. This document provides recommendations for further cleanup while preserving all important work.

---

## Current State Analysis

### ✅ What's Working Well

1. **Recent Cleanup Success (Dec 2025 - Jan 2026)**
   - Documentation consolidated into 3 workflow guides
   - 28+ legacy docs archived to `archive/legacy_docs/`
   - Unused post-processing modules archived
   - Test files and debug scripts removed
   - Root reduced significantly

2. **Good Directory Structure**
   - `documentation/` - Well-organized with subdirectories
   - `batch_processors/` - Batch processing scripts
   - `post-processing/` - Analysis and plotting tools
   - `support_modules/` - Core libraries
   - `archive/` - Legacy content preserved

3. **Essential Files in Root**
   - `Prince_Segmented.py` - Main application ✓
   - `process_folder.py` - Core utility ✓
   - `README.md` - Project overview ✓
   - `.gitignore` - Git configuration ✓

### ⚠️ Areas for Improvement

**Root directory contains 49 additional Python scripts** organized by type:

#### 1. Dataset-Specific Batch Processing (6 scripts)
Scripts created for specific experimental datasets:
- `batch_process_final_presentation.py`
- `batch_process_final_with_areas.py`
- `batch_process_presentation_data.py`
- `batch_process_tempopicker_v2.py`
- `batch_process_tempopicker_v2_with_skip.py`
- `batch_process_v2_selected.py`

#### 2. Dataset-Specific Reprocessing (4 scripts)
One-time reprocessing tasks:
- `reprocess_hybrid_compliant.py`
- `reprocess_tempopicker_v2_complete.py`
- `reprocess_tempopicker_v2_folders.py`
- `reprocess_tempopicker_v2_simple.py`

#### 3. One-Time Plotting Scripts (9 scripts)
Generated specific plots for presentations/papers:
- `generate_final_progressive_plots.py`
- `generate_final_progressive_plots_no_fep.py`
- `generate_individual_plots_hybrid_compliant.py`
- `generate_presentation_master_plots.py`
- `generate_tempopicker_v2_master_plots.py`
- `generate_v2_complete_master_plots.py`
- `generate_v2_master_plots.py`
- `plot_dual_stiffness_example.py`
- `no_fep_plots_verification.py`

#### 4. One-Time Analysis Scripts (3 scripts)
Specific dataset analyses:
- `analyze_presentation_scaling.py`
- `analyze_presentation_stiffness.py`
- `analyze_presentation_stiffness_v2.py`

#### 5. Data Manipulation/Extraction (6 scripts)
One-time data processing tasks:
- `add_areas_to_conditions.py`
- `add_L346_349_manually.py`
- `extract_v9_areas.py`
- `merge_new_hybrid_data.py`
- `process_L346_350.py`
- `verify_radius_data.py`

#### 6. Debug/Check Scripts (9 scripts)
Data validation and debugging:
- `check_baseline_columns.py`
- `check_groups.py`
- `check_hybrid_compliant.py`
- `check_max_areas.py`
- `check_original_areas.py`
- `check_peak_force.py`
- `check_peel_distance.py`
- `check_v9_conditions.py`
- `debug_plot_data.py`

#### 7. Test Scripts (3 scripts)
Testing/visualization:
- `test_plot_comparison.py`
- `test_smooth_lifting_visualization.py`
- `tempo_picker_plot_styles.py`

#### 8. Documentation Files in Root (7 files)
Analysis summaries that could be organized:
- `FINAL_PROGRESSIVE_PLOTS_SUMMARY.md`
- `HYDRODYNAMIC_LOCKING_MITIGATION.md`
- `MEDIAN_PLOTS_AND_FEP_SCALING_SUMMARY.md`
- `PLOT_STYLE_GUIDE.md`
- `PRESENTATION_DATA_ANALYSIS_SUMMARY.md`
- `TEMPO_PICKER_V2_SUMMARY.md`
- Various `.txt` log files

#### 9. Data Files in Root (2 files)
- `v9_area_mapping.csv`
- `force_gauge_calibration_20251106_144013.txt` (should stay in root)

---

## Detailed Recommendations

### Phase 1: Archive One-Time Scripts (Immediate - Low Risk)

These scripts were used once for specific tasks and are unlikely to be reused:

**Action:** Move to `archive/one_time_scripts/` (create subdirectory)

**Scripts to Archive (28 total):**

1. **One-Time Plotting (9 scripts)**
   ```
   generate_final_progressive_plots.py
   generate_final_progressive_plots_no_fep.py
   generate_individual_plots_hybrid_compliant.py
   generate_presentation_master_plots.py
   generate_tempopicker_v2_master_plots.py
   generate_v2_complete_master_plots.py
   generate_v2_master_plots.py
   plot_dual_stiffness_example.py
   no_fep_plots_verification.py
   ```

2. **One-Time Reprocessing (4 scripts)**
   ```
   reprocess_hybrid_compliant.py
   reprocess_tempopicker_v2_complete.py
   reprocess_tempopicker_v2_folders.py
   reprocess_tempopicker_v2_simple.py
   ```

3. **One-Time Analysis (3 scripts)**
   ```
   analyze_presentation_scaling.py
   analyze_presentation_stiffness.py
   analyze_presentation_stiffness_v2.py
   ```

4. **One-Time Data Manipulation (6 scripts)**
   ```
   add_areas_to_conditions.py
   add_L346_349_manually.py
   extract_v9_areas.py
   merge_new_hybrid_data.py
   process_L346_350.py
   verify_radius_data.py
   ```

5. **Debug/Check Scripts (9 scripts)**
   ```
   check_baseline_columns.py
   check_groups.py
   check_hybrid_compliant.py
   check_max_areas.py
   check_original_areas.py
   check_peak_force.py
   check_peel_distance.py
   check_v9_conditions.py
   debug_plot_data.py
   ```

**Rationale:** These scripts served a specific purpose and are unlikely to be used again. Archiving preserves them for reference while cleaning the root.

---

### Phase 2: Organize Dataset-Specific Batch Processors (Low Risk)

**Action:** Move to `batch_processors/dataset_specific/` (create subdirectory)

**Scripts to Move (6 total):**
```
batch_process_final_presentation.py
batch_process_final_with_areas.py
batch_process_presentation_data.py
batch_process_tempopicker_v2.py
batch_process_tempopicker_v2_with_skip.py
batch_process_v2_selected.py
```

**Rationale:** These are dataset-specific processors. The universal processor (`batch_process_universal.py`) should be used for new data. Keep these organized but accessible if needed to reprocess old datasets.

---

### Phase 3: Organize Test Scripts (Low Risk)

**Action:** Move to `archive/test_scripts/` (create subdirectory)

**Scripts to Move (3 total):**
```
test_plot_comparison.py
test_smooth_lifting_visualization.py
tempo_picker_plot_styles.py
```

**Keep:** `test_plot_vs_scatter.png` in same location

**Rationale:** Test scripts verified functionality but aren't part of regular workflow.

---

### Phase 4: Consolidate Documentation (Medium Priority)

**Action:** Move analysis summary docs to `documentation/analysis_summaries/` (create subdirectory)

**Files to Move (6 markdown files + logs):**
```
FINAL_PROGRESSIVE_PLOTS_SUMMARY.md
MEDIAN_PLOTS_AND_FEP_SCALING_SUMMARY.md
PRESENTATION_DATA_ANALYSIS_SUMMARY.md
TEMPO_PICKER_V2_SUMMARY.md
PLOT_STYLE_GUIDE.md → documentation/PLOT_STYLE_GUIDE.md
HYDRODYNAMIC_LOCKING_MITIGATION.md → documentation/technical/HYDRODYNAMIC_LOCKING_MITIGATION.md

# Log files to archive/logs/
presentation_data_reprocess_log.txt
tempo_processing_log.txt
tempopicker_v2_batch_log.txt
tempopicker_v2_reprocess_log.txt
```

**Rationale:** These are valuable analysis records but should be organized with other documentation.

---

### Phase 5: Organize Data Files (Low Risk)

**Action:** Create `data/` directory for workspace-level data files

**Files to Move:**
```
v9_area_mapping.csv → data/v9_area_mapping.csv
```

**Keep in Root:**
```
force_gauge_calibration_20251106_144013.txt (hardware calibration - stays in root)
```

**Rationale:** Separate data files from code for clarity.

---

## Proposed Final Root Directory Structure

After all phases:

```
Prince_Segmented_20250926/
├── Prince_Segmented.py                          # Main application
├── process_folder.py                             # Core utility
├── README.md                                     # Project overview
├── .gitignore                                    # Git config
├── force_gauge_calibration_20251106_144013.txt  # Hardware calibration
├── CLEAR_PYTHON_CACHE.bat                       # Utility script
│
├── archive/                                      # Historical/completed work
│   ├── legacy_docs/                             # Old documentation (existing)
│   ├── unused_modules/                          # Archived code (existing)
│   ├── one_time_plots/                          # Historic plots (existing)
│   ├── one_time_scripts/                        # NEW: One-time processing scripts
│   ├── test_scripts/                            # NEW: Test/validation scripts
│   └── logs/                                    # NEW: Old processing logs
│
├── batch_processors/                            # Batch processing
│   ├── batch_process_universal.py               # Universal processor (use this!)
│   ├── batch_process*.py                        # Other processors
│   ├── dataset_specific/                        # NEW: Dataset-specific processors
│   └── README.md
│
├── calibration_modules/                         # Camera calibration
│
├── data/                                        # NEW: Workspace data files
│   └── v9_area_mapping.csv
│
├── documentation/                               # All documentation
│   ├── README.md
│   ├── PROJECT_ORGANIZATION.md
│   ├── PLOT_STYLE_GUIDE.md                     # MOVED FROM ROOT
│   ├── analysis_summaries/                     # NEW: Analysis records
│   │   ├── FINAL_PROGRESSIVE_PLOTS_SUMMARY.md
│   │   ├── MEDIAN_PLOTS_AND_FEP_SCALING_SUMMARY.md
│   │   ├── PRESENTATION_DATA_ANALYSIS_SUMMARY.md
│   │   └── TEMPO_PICKER_V2_SUMMARY.md
│   ├── technical/
│   │   ├── HYDRODYNAMIC_LOCKING_MITIGATION.md  # MOVED FROM ROOT
│   │   └── ...
│   └── ...
│
├── post-processing/                             # Analysis tools
│
├── RED_PotentialUpgradeScript/                  # RED Lab upgrade
│
├── support_modules/                             # Core libraries
│
└── ui_components/                               # GUI components
```

---

## Implementation Plan

### Recommended Order

1. **Phase 1: Archive One-Time Scripts** (28 scripts)
   - Least risk, biggest cleanup impact
   - Creates `archive/one_time_scripts/`

2. **Phase 3: Archive Test Scripts** (3 scripts)
   - Creates `archive/test_scripts/`

3. **Phase 4: Consolidate Documentation** (6 docs + logs)
   - Creates `documentation/analysis_summaries/`
   - Creates `archive/logs/`
   - Moves technical docs

4. **Phase 5: Organize Data Files** (1 file)
   - Creates `data/`

5. **Phase 2: Organize Dataset Processors** (6 scripts)
   - Creates `batch_processors/dataset_specific/`

### Safety Measures

**Before ANY changes:**
1. ✅ **Git commit current state** (you have it)
2. ✅ **Verify GitHub sync** (already checked)
3. Create backup of entire folder (optional but recommended)

**During changes:**
- Move files, don't copy (to avoid duplicates)
- Update any README files that reference moved scripts
- Test that main application still works after each phase

---

## What Can Be DELETED (After Archiving)

**NOTHING should be deleted before archiving.** However, after 6-12 months in the archive, consider deletion candidates:

### Low Value for Deletion (Keep Archived)
- One-time plotting scripts (may want to reference formatting)
- Dataset-specific processors (may need to reprocess old data)
- Analysis summaries (valuable scientific records)

### Potential Deletion Candidates (Review in 6 months)
- Debug/check scripts (if issues are resolved)
- Test scripts (if functionality is validated and integrated)
- Log files (if no longer serving debugging purposes)

**Recommendation:** Keep everything archived for now. Revisit in June 2026.

---

## What Should NOT Be Moved

### Keep in Root
1. **`Prince_Segmented.py`** - Main application
2. **`process_folder.py`** - Frequently used utility
3. **`README.md`** - Project overview
4. **`.gitignore`** - Git configuration
5. **`force_gauge_calibration_20251106_144013.txt`** - Hardware calibration reference
6. **`CLEAR_PYTHON_CACHE.bat`** - Utility script

### Keep in Current Locations
1. **All `support_modules/`** - Core libraries actively used
2. **All `post-processing/`** - Active analysis tools
3. **All `batch_processors/`** currently there - Still useful
4. **All `documentation/`** currently there - Well organized
5. **All `calibration_modules/`** - Active calibration system

---

## Documentation Updates Needed

After reorganization, update these files:

### 1. README.md
Update file paths and descriptions:
- Note archive contains one-time scripts
- Update directory structure diagram
- Add note about dataset-specific processors location

### 2. documentation/PROJECT_ORGANIZATION.md
- Update directory structure
- Add information about archive organization
- Document where to find dataset-specific tools

### 3. batch_processors/README.md
- Add note about `dataset_specific/` subdirectory
- Explain when to use dataset-specific vs. universal processor

### 4. Create: archive/one_time_scripts/README.md
Document what's archived and why:
```markdown
# One-Time Scripts Archive

This directory contains scripts that were created for specific one-time tasks
and are no longer part of the regular workflow. They are preserved for reference.

## Categories

### Data Reprocessing
Scripts used to reprocess specific datasets with updated algorithms.

### Plotting
Scripts that generated specific plots for presentations or papers.

### Analysis
One-time analyses conducted on specific datasets.

### Data Manipulation
Scripts that performed one-time data transformations or corrections.

### Validation
Scripts used to validate data or check specific conditions.

## Usage
These scripts are archived and may require updating to work with current code.
Refer to the commit history for context on when/why they were created.
```

---

## Summary of Changes

### Impact Assessment

**Files to Organize:** 49 scripts + 7 docs + 4 logs = **60 files**

**New Directories:** 4 new subdirectories
- `archive/one_time_scripts/`
- `archive/test_scripts/`
- `archive/logs/`
- `documentation/analysis_summaries/`
- `batch_processors/dataset_specific/`
- `data/`

**Root Directory Cleanup:**
- **Before:** ~70 files in root
- **After:** ~10 files in root (**86% reduction**)

**Benefits:**
1. Much cleaner root directory
2. Easier to find active vs. archived code
3. Better organization by purpose
4. All work preserved and documented
5. Maintains full git history

**Risks:** Minimal
- All files moved, not deleted
- Git tracks moves
- Can revert any change
- No code functionality affected

---

## Next Steps

**For you to decide:**

1. **Review these recommendations** - Do they make sense for your workflow?

2. **Choose phases to implement** - Start with Phase 1 (biggest cleanup, lowest risk)?

3. **Let me know your preferences:**
   - Which phases do you want to implement?
   - Any scripts you want to keep in root?
   - Any additional organization ideas?

4. **I can implement the changes** - Just tell me which phases to proceed with!

---

## Recent Cleanup (Already Done - December 2025)

✅ **Documentation Consolidation**
- Created 3 comprehensive workflow guides
- Archived 28+ legacy documentation files

✅ **Code Cleanup**
- Archived 5 unused post-processing modules
- Deleted 8 test files and test data
- Deleted 8 debug/temp scripts
- Deleted 8 one-time analysis scripts

✅ **Post-Processing Cleanup**
- Consolidated plotting scripts
- Reduced from 30 to 22 active files (27% reduction)

**Great work on the initial cleanup!** This proposal builds on that foundation to complete the organization.

---

## Questions?

Feel free to ask:
- Why is a specific file categorized a certain way?
- Whether a specific script should be kept vs. archived?
- How to implement any of these phases?
- Anything else about the organization!
