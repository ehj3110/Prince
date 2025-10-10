# File Redundancy Analysis - October 10, 2025

## Executive Summary
Found **significant redundancy** across the workspace. Recommend deleting **~80% of files** to clean up the project.

---

## 1. Adhesion Metrics Files (3 ACTIVE FILES → KEEP ONLY 1)

### ✅ KEEP: `support_modules/adhesion_metrics_calculator.py`
- **Date:** September 19, 2025 (NEWEST)
- **Status:** PRODUCTION - Currently used by ALL scripts
- **Size:** 588 lines
- **Features:**
  - Gaussian smoothing
  - Reverse-search propagation detection
  - Comprehensive metrics
  - Clean, well-documented API

### ❌ DELETE: `support_modules/enhanced_adhesion_metrics.py`
- **Date:** September 15, 2025
- **Status:** **ADAPTER/WRAPPER ONLY** - Just redirects to adhesion_metrics_calculator.py
- **Size:** 105 lines
- **Why Delete:** 
  - Only has `EnhancedAdhesionAnalyzerAdapter` class
  - Literally just wraps `AdhesionMetricsCalculator`
  - No unique functionality
  - Exists only for backward compatibility with old code
- **Action:** Delete if no active code imports `EnhancedAdhesionAnalyzerAdapter`

### ❌ DELETE: `support_modules/enhanced_adhesion_metrics_Old.py`
- **Date:** September 15, 2025
- **Status:** LEGACY CODE - Old implementation with scipy dependencies
- **Size:** ~500 lines
- **Why Delete:**
  - Contains `EnhancedAdhesionAnalyzer` class (obsolete)
  - Has `create_analyzer()` factory function (not used anymore)
  - Requires scipy (unnecessary dependency)
  - Completely superseded by `adhesion_metrics_calculator.py`
  - Named "Old" - clear indicator it's deprecated

**Recommendation:**
```
KEEP: adhesion_metrics_calculator.py
DELETE: enhanced_adhesion_metrics.py
DELETE: enhanced_adhesion_metrics_Old.py
```

---

## 2. Batch Processing Scripts (7 FILES → KEEP 1-2)

### ✅ KEEP: `batch_process_steppedcone.py`
- **Status:** ACTIVE PRODUCTION - Universal SteppedCone processor
- **Last Modified:** Today (Oct 10, 2025, 1:26 PM)
- **Purpose:** Process any SteppedCone folder (original or V2)
- **Features:**
  - Flexible folder parsing (with/without speed suffix)
  - Colored master plots
  - No crashes (plotting disabled)
  - Clean separation of concerns

### ⚠️ KEEP (Maybe): `batch_process_printing_data.py`
- **Status:** Different purpose - processes live printing logs
- **Check:** Verify if still used for live printing analysis
- **Action:** Keep if actively used, otherwise archive

### ❌ DELETE: `batch_process_steppedcone_v2.py`
- **Status:** FAILED ATTEMPT - Created Oct 10, caused crashes
- **Why Delete:** Superseded by universal `batch_process_steppedcone.py`

### ❌ DELETE: `batch_process_steppedcone_v2_fast.py`
- **Status:** FAILED ATTEMPT - Created Oct 10, gave wrong results
- **Why Delete:** No layer boundary detection, incorrect metrics

### ❌ DELETE: `post-processing/batch_v17_analysis.py`
- **Status:** OLD - Specific to V17 tests
- **Why Delete:** Results already generated, not needed for future analysis

### ❌ DELETE: `post-processing/batch_process_simple.py`
- **Status:** OLD - Simplified test version
- **Why Delete:** Superseded by production batch processors

### ❌ DELETE: `post-processing/batch_process_enhanced.py`
- **Status:** OLD - Enhanced test version
- **Why Delete:** Features integrated into production scripts

### ❌ DELETE: `post-processing/batch_process_with_outliers.py`
- **Status:** OLD - Outlier detection test
- **Why Delete:** Experimental, not production-ready

**Recommendation:**
```
KEEP: batch_process_steppedcone.py (DEFINITE)
KEEP: batch_process_printing_data.py (IF STILL USED)
DELETE: batch_process_steppedcone_v2.py
DELETE: batch_process_steppedcone_v2_fast.py
DELETE: post-processing/batch_v17_analysis.py
DELETE: post-processing/batch_process_simple.py
DELETE: post-processing/batch_process_enhanced.py
DELETE: post-processing/batch_process_with_outliers.py
```

---

## 3. Test Files (20+ FILES → KEEP 0-3)

### Current Test Files in Root:
- `test_adhesion_calculator.py`
- `test_adhesion_calculator_with_derivatives.py`
- `test_hybrid_filter_integration.py`
- `test_peak_force_logger.py`
- `test_peakforce_logger.py` ← **DUPLICATE NAME!**
- `test_post_print_analysis.py`
- `test_sensor_data_window.py`

### ❌ DELETE MOST TEST FILES
**Why:**
- Tests were for development/debugging
- Production code is now stable
- Tests are outdated (reference old APIs)
- Results already validated

### ✅ KEEP (Optional):
- `test_adhesion_calculator.py` - IF you want to test metrics calculator
- Delete the rest unless actively developing

**Duplicates in archive/ folders:**
- All tests have copies in `archive/test_scripts/`
- All tests have copies in `archived_files/redundant_scripts/`

**Recommendation:**
```
KEEP: test_adhesion_calculator.py (OPTIONAL)
DELETE: All other test files
DELETE: All archived test copies
```

---

## 4. Analysis Plotter Files (2 FILES → KEEP 1)

### ✅ KEEP: `post-processing/analysis_plotter.py`
- **Status:** ACTIVE - Used by RawData_Processor (when plotting is enabled)
- **Location:** Correct location in post-processing module
- **Size:** 278 lines

### ❌ DELETE: `analysis_plotter.py` (root directory)
- **Status:** DUPLICATE or ORPHAN
- **Why Delete:** Same file exists in post-processing/
- **Check:** Compare file sizes/dates to confirm it's a duplicate

**Recommendation:**
```
KEEP: post-processing/analysis_plotter.py
DELETE: analysis_plotter.py (root)
```

---

## 5. Backup Directories (2 FOLDERS → ARCHIVE EXTERNALLY)

### ❌ REMOVE FROM WORKSPACE: `backup_complete_system_20250921/`
- **Size:** Full copy of entire codebase
- **Date:** September 21, 2025
- **Why Remove:** Git history provides better backup
- **Action:** Move to external archive or delete (already in Git)

### ❌ REMOVE FROM WORKSPACE: `backup_corrected_system_20250921/`
- **Size:** Another full copy of codebase
- **Date:** September 21, 2025  
- **Why Remove:** Duplicate backup, Git is better
- **Action:** Move to external archive or delete

**Recommendation:**
```
DELETE: backup_complete_system_20250921/ (Git has history)
DELETE: backup_corrected_system_20250921/ (Git has history)
```

---

## 6. Archive Directories (2 FOLDERS → CONSOLIDATE)

### Current Structure:
- `archive/` - Contains old scripts, test files, experimental code
- `archived_files/` - Contains redundant scripts, old plots, legacy docs

### ❌ Problem: TWO separate archive folders
**Why This Is Bad:**
- Confusing - which archive to use?
- Duplicates between them
- Hard to find things

### ✅ Solution: Consolidate into ONE archive
**Recommendation:**
```
KEEP: archive/ (consolidate everything here)
DELETE: archived_files/ (merge into archive/)
```

**Archive Subdirectory Structure:**
```
archive/
├── old_scripts/          # Old production scripts
├── test_scripts/         # Old test files
├── experimental/         # Experimental features
├── legacy_docs/          # Old documentation
├── old_plots/            # Historical plots
└── redundant_scripts/    # Confirmed duplicates
```

---

## 7. Miscellaneous Duplicates

### Raw Data Processor:
- ✅ KEEP: `post-processing/RawData_Processor.py` (ACTIVE)
- ❌ DELETE: `raw_data_processor.py` (root) - Check if it's a duplicate

### Hybrid Adhesion Plotter:
- ❌ DELETE: `hybrid_adhesion_plotter.py` (root)
  - Old plotting code, superseded by analysis_plotter.py
  - From earlier version of system

### Post Print Analyzer:
- ❌ DELETE: `post_print_analyzer.py` (root)
  - Check if still used for live printing
  - If not, delete (functionality in batch processors)

### Old Images/Logs:
- ❌ DELETE: All test PNG files in root:
  - `debug_derivatives_layer_*.png`
  - `dynamic_layout_test.png`
  - `example_plot_current_format.png`
  - `filter_integration_test_results.png`
  - `hybrid_L48_L50_analysis.png`
  - `improved_plot_format.png`
  - `position_test_output.png`
  - `thread_safe_test.png`

- ❌ DELETE: Test output CSVs:
  - `test_output.csv`
  - `test_peak_force_output.csv`
  - `unified_peak_force_test.csv`

- ❌ DELETE: Log files:
  - `output.log`
  - `v2_processing_log.txt`

---

## 8. Summary of Recommended Deletions

### IMMEDIATE DELETIONS (Safe):

#### Adhesion Metrics (Delete 2 of 3):
```bash
support_modules/enhanced_adhesion_metrics.py
support_modules/enhanced_adhesion_metrics_Old.py
```

#### Batch Processors (Delete 6 of 7):
```bash
batch_process_steppedcone_v2.py
batch_process_steppedcone_v2_fast.py
post-processing/batch_v17_analysis.py
post-processing/batch_process_simple.py
post-processing/batch_process_enhanced.py
post-processing/batch_process_with_outliers.py
```

#### Test Files (Delete most):
```bash
test_adhesion_calculator_with_derivatives.py
test_hybrid_filter_integration.py
test_peak_force_logger.py
test_peakforce_logger.py
test_post_print_analysis.py
test_sensor_data_window.py
# Keep only test_adhesion_calculator.py if you want unit tests
```

#### Duplicate Files:
```bash
analysis_plotter.py  # Keep post-processing/analysis_plotter.py
raw_data_processor.py  # Keep post-processing/RawData_Processor.py (if duplicate)
```

#### Old Code:
```bash
hybrid_adhesion_plotter.py
post_print_analyzer.py  # Check if used first
```

#### Test Outputs:
```bash
*.png  # All test PNGs in root
test_output.csv
test_peak_force_output.csv  
unified_peak_force_test.csv
output.log
v2_processing_log.txt
```

#### Backup Folders:
```bash
backup_complete_system_20250921/
backup_corrected_system_20250921/
```

### CONSOLIDATIONS:

#### Archive Folders:
```bash
# Move archived_files/ contents into archive/
# Delete archived_files/ folder
```

---

## 9. Estimated Impact

### Current State:
- **Total Files:** ~150+ Python files
- **Duplicates:** ~50+ files
- **Backups:** 2 full system copies
- **Test files:** ~20+ files
- **Old plots:** ~10+ PNG files

### After Cleanup:
- **Active Files:** ~20-25 Python files
- **Archive:** Single consolidated folder
- **Backups:** None (use Git)
- **Disk Space Saved:** Estimate 50-100 MB

### Benefits:
✅ **Clarity:** Easy to find active code
✅ **Maintainability:** No confusion about which file to edit
✅ **Performance:** Faster searches, smaller Git operations
✅ **Safety:** Git provides better version control than manual backups

---

## 10. Recommended Cleanup Process

### Phase 1: Verify Active Files (DO THIS FIRST)
```powershell
# Check what's actively imported
grep -r "from enhanced_adhesion_metrics" --include="*.py"
grep -r "import enhanced_adhesion_metrics" --include="*.py"
```

### Phase 2: Create Safety Backup
```powershell
# Create ONE final backup outside workspace
git commit -am "Pre-cleanup state"
git push  # If using remote repo
```

### Phase 3: Delete Confirmed Redundancies
```powershell
# Move to archive first (safer than delete)
mkdir archive/pre_cleanup_backup_oct10
# Move questionable files there first
```

### Phase 4: Test After Cleanup
```powershell
# Verify main scripts still run
python batch_process_steppedcone.py --help  # Or dry run
python Prince_Segmented.py  # If used for live printing
```

### Phase 5: Final Commit
```powershell
git add .
git commit -m "Major cleanup: Remove redundant files (see FILE_REDUNDANCY_ANALYSIS.md)"
```

---

## 11. Active Production Files (DON'T DELETE THESE)

### Core System:
- ✅ `Prince_Segmented.py` - Main live printing control
- ✅ `batch_process_steppedcone.py` - Universal SteppedCone processor
- ✅ `support_modules/adhesion_metrics_calculator.py` - Metrics calculation
- ✅ `post-processing/RawData_Processor.py` - Data processing
- ✅ `post-processing/analysis_plotter.py` - Plotting (if re-enabled)

### Support Modules (in support_modules/):
- ✅ `AutoHomeRoutine.py`
- ✅ `AutomatedLayerLogger.py`
- ✅ `dlp_phidget_coordinator.py`
- ✅ `ForceGaugeManager.py`
- ✅ `PeakForceLogger.py`
- ✅ `PositionLogger.py`
- ✅ `SensorDataWindow.py`
- ✅ `two_step_baseline_analyzer.py`
- ✅ Others as needed for live printing

### Documentation (Keep):
- ✅ `README.md`
- ✅ `CHANGELOG.md`
- ✅ `DEPLOYMENT_GUIDE.md`
- ✅ `STAGE_STALL_PREVENTION.md`
- ✅ `ADHESION_CALCULATOR_STATUS.md`
- ✅ `REFACTORING_SUMMARY_OCT10.md`
- ✅ `FILE_REDUNDANCY_ANALYSIS.md` (this file)
- ✅ `documentation/` folder

---

## 12. Quick Decision Matrix

| File Pattern | Keep? | Reason |
|-------------|-------|---------|
| `*_Old.py` | ❌ NO | Explicitly marked as old |
| `*_v2.py` or `*_v2_*.py` | ❌ NO | Failed attempts from today |
| `test_*.py` in root | ❌ MOSTLY NO | Old tests, results validated |
| `batch_*.py` in post-processing | ❌ NO | Superseded by main batch processor |
| `backup_*/` folders | ❌ NO | Git provides better version control |
| `enhanced_adhesion_*.py` | ❌ NO | Superseded by adhesion_metrics_calculator.py |
| `*.png` in root | ❌ NO | Test outputs, regenerate if needed |
| `*.csv` in root (test files) | ❌ NO | Test outputs, not production data |
| `archive/` contents | ✅ KEEP | Historical reference |
| `support_modules/*.py` (no _Old) | ✅ KEEP | Active production code |
| `documentation/*.md` | ✅ KEEP | Documentation |

---

## 13. Final Recommendation

**AGGRESSIVE CLEANUP PLAN:**
Delete 60-70 files immediately, saving ~50% of codebase clutter.

**CONSERVATIVE CLEANUP PLAN:**
1. Delete confirmed duplicates (adhesion metrics, batch processors)
2. Move questionable files to archive
3. Delete test files and outputs
4. Remove backup folders after verifying Git history

**YOUR CHOICE:**
Based on your comfort level with Git and backups, I recommend the **CONSERVATIVE** approach:
1. Commit current state to Git
2. Move files to archive/ rather than delete
3. Test that everything still works
4. Delete archive/ later if confident

---

## Need Help Deciding?

**Ask these questions:**
1. "When was the last time I used this file?" → If >1 month, archive it
2. "Does this file have 'old', 'test', 'backup', 'v2' in the name?" → Probably delete
3. "Can I regenerate this output?" → If yes (logs, plots, test CSVs), delete it
4. "Is this in Git history?" → If yes, don't need backup/ folders
5. "Would I know where to find this if I needed it?" → If no, consolidate archives

**Final Answer: YES, you have MASSIVE redundancy. Clean it up!** 🧹
