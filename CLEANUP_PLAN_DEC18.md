# Documentation Cleanup Plan - December 18, 2025

## Overview

**Goal:** Consolidate 49+ fragmented markdown files into 3 comprehensive workflow-based guides

**Status:** ✅ Documentation consolidation complete, ready for file archival

---

## New Documentation Structure

### Three Comprehensive Guides (KEEP - Already Created)

1. **documentation/PRE_PRINT_SETUP_GUIDE.md** (33,758 chars)
   - Complete hardware-to-first-print reference
   - Consolidates 8+ pre-print documentation files

2. **documentation/PRINTING_PROCESS_GUIDE.md** (59,455 chars)
   - Complete printing process flow reference
   - Consolidates 10+ during-print documentation files

3. **documentation/POST_PROCESSING_GUIDE.md** (42,000+ chars)
   - Complete post-processing analysis reference
   - Consolidates 6+ post-processing documentation files

---

## Files to Archive

### Category 1: Pre-Print Documentation (8 files → archive/legacy_docs/)

| File | Reason | Content Preserved In |
|------|--------|---------------------|
| `TESTING_GUIDE.md` | Redundant | PRE_PRINT_SETUP_GUIDE.md § Pre-Print Verification |
| `SETUP_ON_PRINTER_COMPUTER.md` | Redundant | PRE_PRINT_SETUP_GUIDE.md § Software Installation |
| `calibration_modules/INTEGRATION_GUIDE.md` | Redundant | PRE_PRINT_SETUP_GUIDE.md § Camera Calibration |
| `calibration_modules/QUICK_REFERENCE.md` | Redundant | PRE_PRINT_SETUP_GUIDE.md § Camera Calibration |
| `calibration_modules/AUTOMATED_WORKFLOW_GUIDE.md` | Redundant | PRE_PRINT_SETUP_GUIDE.md § Camera Calibration |
| `documentation/PRE_PRINT_VERIFICATION_CHECKLIST.md` | Redundant | PRE_PRINT_SETUP_GUIDE.md § Pre-Print Verification |

**Total:** 6 files to archive

---

### Category 2: During-Print Documentation (7 files → archive/legacy_docs/)

| File | Reason | Content Preserved In |
|------|--------|---------------------|
| `THREE_FIXES_SUMMARY.md` | Redundant | PRINTING_PROCESS_GUIDE.md § Layer Execution Sequence |
| `SANDWICH_ROUTINE_GUIDE.md` | Redundant | PRINTING_PROCESS_GUIDE.md § Sandwich Routine |
| `documentation/technical/SANDWICH_ROUTINE.md` | Redundant | PRINTING_PROCESS_GUIDE.md § Sandwich Routine |
| `HOW_PROPAGATION_END_IS_MEASURED.md` | Redundant | PRINTING_PROCESS_GUIDE.md § Real-Time Adhesion Metrics |
| `PROPAGATION_END_ANALYSIS.md` | Redundant | PRINTING_PROCESS_GUIDE.md § Real-Time Adhesion Metrics |
| `PROPAGATION_METHOD_FIX_OCT10.md` | Redundant | PRINTING_PROCESS_GUIDE.md § Real-Time Adhesion Metrics |

**Total:** 6 files to archive

---

### Category 3: Post-Processing Documentation (4 files → archive/legacy_docs/)

| File | Reason | Content Preserved In |
|------|--------|---------------------|
| `post-processing/BATCH_PROCESSING_GUIDE.md` | Redundant | POST_PROCESSING_GUIDE.md § Batch Processing System |
| `post-processing/MODULAR_ANALYSIS_README.md` | Redundant | POST_PROCESSING_GUIDE.md § Analysis Tools |
| `post-processing/QUICK_REFERENCE.md` | Redundant | POST_PROCESSING_GUIDE.md § Common Workflows |
| `UNIVERSAL_PROCESSING_README.md` | Redundant | POST_PROCESSING_GUIDE.md § Batch Processing System |

**Total:** 4 files to archive

---

### Category 4: Old Analysis Summaries (12 files → archive/legacy_docs/)

| File | Reason | Notes |
|------|--------|-------|
| `V6_ANALYSIS_SUMMARY.md` | Historical | V6 data already processed |
| `SPOOF_TEST_RESULTS_NOV7.md` | Historical | Test results from Nov 7 |
| `SESSION_SUMMARY_OCT10.md` | Historical | Old session notes |
| `REFACTORING_SUMMARY_OCT10.md` | Historical | Old refactoring notes |
| `CLEANUP_SUMMARY_OCT10.md` | Historical | Old cleanup notes |
| `COMPLETE_RECOVERY_SUMMARY_OCT10.md` | Historical | Old recovery notes |
| `FILTERING_RESTORATION_OCT10.md` | Historical | Old filtering notes |
| `INTEGRATION_VERIFICATION.md` | Historical | Integration already verified |
| `STAGE_STALL_PREVENTION.md` | Historical | Stage stall already fixed |
| `post-processing/PEO_OLD_TEST_RESULTS.md` | Historical | Old PEO test results |
| `post-processing/ANNOTATION_FIX_SUMMARY.md` | Historical | Annotation fix completed |
| `post-processing/BATCH_V17_UPDATE_NOTES.md` | Historical | V17 batch notes |

**Total:** 12 files to archive

---

### Category 5: Technical Documentation (KEEP - Reference Material)

| File | Status | Reason |
|------|--------|--------|
| `documentation/LAYER_BOUNDARY_DETECTION.md` | ✅ KEEP | Technical algorithm reference |
| `documentation/BASELINE_DETECTION_TEST.md` | ✅ KEEP | Test results for baseline detection |
| `documentation/BASELINE_TEST_RESULTS_L111.md` | ✅ KEEP | Specific test results |
| `documentation/AUTOLOG_METRICS_CSV_EXPORT.md` | ✅ KEEP | CSV format specification |
| `documentation/CSV_EXPORT_UPDATES.md` | ✅ KEEP | Export format updates |
| `documentation/SPEED_ANALYSIS_PLOT.md` | ✅ KEEP | Specific analysis documentation |
| `documentation/technical/*.md` | ✅ KEEP | Detailed technical specs |

**Reason:** These contain specific test results, algorithm details, and format specifications that are referenced by the comprehensive guides but contain deeper technical detail.

---

### Category 6: Project Status (KEEP - Active Project Management)

| File | Status | Reason |
|------|--------|--------|
| `README.md` | ✅ KEEP | Main project entry point |
| `CHANGELOG.md` | ✅ KEEP | Version history |
| `DEPLOYMENT_GUIDE.md` | ✅ KEEP | System deployment reference |
| `GITHUB_SETUP_GUIDE.md` | ✅ KEEP | Git workflow documentation |
| `TroubleshootingIdeas.md` | ✅ KEEP | Active troubleshooting notes |
| `DATA_SMOOTHING_METHODS.md` | ✅ KEEP | Methods comparison reference |
| `FILE_REDUNDANCY_ANALYSIS.md` | ✅ KEEP | Analysis of file redundancy |
| `ADHESION_CALCULATOR_STATUS.md` | ✅ KEEP | Calculator development status |

---

## Summary

### Files Moving to archive/legacy_docs/
- **Pre-print docs:** 6 files
- **During-print docs:** 6 files
- **Post-processing docs:** 4 files
- **Old summaries:** 12 files
- **Total:** 28 files

### Files Staying (Active Documentation)
- **New comprehensive guides:** 3 files
- **Technical references:** 7+ files
- **Project management:** 8 files
- **Total:** 18+ files

### Before/After Comparison

**Before:**
- 49+ markdown files across project
- 7 camera calibration guides
- 5 quick reference guides
- Multiple README files per directory
- Significant redundancy and fragmentation

**After:**
- 3 comprehensive workflow-based guides
- Technical references preserved
- Project management docs active
- Clear organization by workflow stage
- Easy navigation for team members

---

## Execution Plan

### Step 1: Create archive structure
```
archive/legacy_docs/
├── pre_print/
├── during_print/
├── post_processing/
└── old_summaries/
```

### Step 2: Move files systematically
- Move pre-print docs → archive/legacy_docs/pre_print/
- Move during-print docs → archive/legacy_docs/during_print/
- Move post-processing docs → archive/legacy_docs/post_processing/
- Move old summaries → archive/legacy_docs/old_summaries/

### Step 3: Update README.md
- Add links to three new comprehensive guides
- Update "Documentation Structure" section
- Add note about archived documentation

### Step 4: Verify no broken references
- Check that no Python scripts reference archived docs
- Check that no markdown files link to archived docs
- Update any broken links

### Step 5: Git commit
```powershell
git add .
git commit -m "Documentation consolidation: 28 files archived, 3 comprehensive guides created"
git push origin main
```

---

## Risk Assessment

**Risk:** Information loss
- **Mitigation:** All content preserved in new guides or technical references
- **Verification:** Migration map shows where each file's content went

**Risk:** Broken code references
- **Mitigation:** Check Python scripts for documentation imports/references
- **Verification:** Grep search for archived filenames

**Risk:** User confusion
- **Mitigation:** Update README with clear pointers to new guides
- **Verification:** Test documentation navigation path

---

## Approval Required

**Question for User:** 
Ready to proceed with moving 28 files to archive/legacy_docs/?

All content is preserved in:
- PRE_PRINT_SETUP_GUIDE.md
- PRINTING_PROCESS_GUIDE.md  
- POST_PROCESSING_GUIDE.md

Type "proceed" to start cleanup, or "wait" to review plan first.
