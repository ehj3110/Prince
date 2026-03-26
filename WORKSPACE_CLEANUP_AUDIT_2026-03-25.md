# Workspace Cleanup Audit And Reorganization Plan

Date: 2026-03-25
Workspace: Prince_Segmented_20250926
Audience: Project maintainers, reviewers, and Gemini handoff collaborator

## 1. Executive Summary

The workspace is functional but overgrown at the root level. Core production scripts, one-time debug scripts, test files, generated figures, and historical backups are mixed together. This increases review risk, slows onboarding, and makes accidental execution of stale scripts more likely.

Main findings:

1. Root contains many scripts that are either duplicates of files in other folders or one-time debug/test utilities.
2. There are exact duplicate test files in both root and tests.
3. Debug and manuscript artifacts are large and should be handled as generated outputs, not primary source files.
4. Multiple backup directories and archives are retained in the main repo and should be moved to a dedicated archive strategy.
5. Canonical module ownership is unclear in a few key areas (especially metrics and post-processing entry points).

High-confidence cleanup can be done safely in phases, starting with exact duplicates and generated files.

---

## 2. Audit Scope And Method

This review included:

1. Root file inventory and naming-pattern analysis.
2. First-level directory size and file count analysis (excluding .venv and .git).
3. Duplicate filename and hash comparison for root Python files against subdirectories.
4. Review of current cleanup scripts, root README, archive documentation, and post-processing docs.
5. Git working tree snapshot for untracked/new content context.

This review did not execute destructive file operations.

---

## 3. Current State Snapshot

### 3.1 Largest non-venv directories

1. PrintingLogs_Backup: ~255.04 MB, 669 files
2. post-processing: ~192.75 MB, 279 files
3. archived_files: ~9.28 MB, 38 files
4. backup_complete_system_20250921: ~4.45 MB, 14 files
5. debug: ~3.25 MB, 48 files

### 3.2 Project file distribution (excluding .venv and .git)

1. CSV: 536
2. PNG: 257
3. PY: 145
4. TXT: 134
5. MD: 51
6. LOG: 31

Interpretation: generated data and visualization artifacts dominate repository volume and context noise.

### 3.3 Root-level clutter indicators

Root currently contains:

1. 28 Python scripts
2. 9 Markdown documents
3. 12 CSV/PNG test artifacts

This is high for a root directory and suggests weak separation between:

1. production entry points
2. tests
3. debug tooling
4. outputs/artifacts
5. handoff and historical docs

---

## 4. Key Risks If Left Unchanged

1. Execution risk: stale scripts in root can be launched accidentally.
2. Merge risk: unrelated generated artifacts and debug files make PRs noisy.
3. Review risk: duplicate files with same names in multiple folders can diverge silently.
4. Reproducibility risk: unclear canonical script locations reduce pipeline determinism.
5. Maintenance drag: future cleanup becomes harder as temporary files accumulate.

---

## 5. Verified Duplicate And Redundant Patterns

### 5.1 Exact duplicates between root and tests

The following root files are byte-identical to their counterparts in tests:

1. test_adhesion_calculator_with_derivatives.py
2. test_data_length.py
3. test_extra_point.py
4. test_fixed_calculator.py
5. test_motion_end_idx.py
6. test_parameter_fix.py
7. test_path_fix.py
8. test_post_print_integration.py
9. test_print_workflow.py

Recommendation: keep only tests copies and delete root copies.

### 5.2 Exact duplicates between root and debug/tools

Exact duplicates found:

1. analyze_cleanup.py and tools/analyze_cleanup.py
2. cleanup_comparison_files.py and tools/cleanup_comparison_files.py
3. cleanup_debug_files.py and tools/cleanup_debug_files.py
4. compare_time_data.py and tools/compare_time_data.py
5. final_calculator_comparison.py and debug/final_calculator_comparison.py
6. final_layer_visualization.py and debug/final_layer_visualization.py
7. quick_workflow_test.py and debug/quick_workflow_test.py
8. replicate_hybrid_plotter.py and debug/replicate_hybrid_plotter.py
9. run_corrected_plotter.py and debug/run_corrected_plotter.py
10. run_fixed_plotter.py and debug/run_fixed_plotter.py
11. upgrade_peak_force_logger.py and debug/upgrade_peak_force_logger.py

Recommendation: keep subfolder copies, remove root duplicates.

### 5.3 Same filename, not same content

These indicate version drift and require canonical ownership decisions:

1. adhesion_metrics_calculator.py in root vs support_modules and backups
2. post_print_analyzer.py in root vs post-processing
3. Prince_Segmented.py in root vs backup copies
4. hybrid_adhesion_plotter.py in root vs backup copies

Recommendation: decide one authoritative location per module and convert non-authoritative copies into archive/history only.

---

## 6. Root Directory Cleanup Matrix

### 6.1 Keep in root (core operational entry points)

Suggested root keep set (lean):

1. Prince_Segmented.py
2. batch_process_printing_data.py
3. README.md (expanded, not minimal)
4. .gitignore

Optional keep in root only if frequently run directly:

1. post_print_analyzer.py (if this is truly canonical, otherwise move)
2. hybrid_adhesion_plotter.py (if still used as direct main entry)

### 6.2 Move or remove from root

1. All test_*.py files: remove root copies, retain tests copies.
2. debug_*.py files: move under debug or remove if duplicates already exist.
3. cleanup scripts: keep under tools only.
4. one-time runner scripts (run_fixed_plotter.py, run_corrected_plotter.py): keep only in debug or remove after final validation.
5. temporary comparison scripts: move to debug/legacy_tests or archive if no longer needed.

### 6.3 Root-generated artifacts to relocate

Current root artifacts include:

1. autolog_L48-L50.csv
2. autolog_L148-L150.csv
3. autolog_L198-L200.csv
4. test.csv
5. test_auto.csv
6. test_default.csv
7. test_two_step_integration.csv
8. dynamic_layout_test.png
9. example_plot_current_format.png
10. improved_plot_format.png
11. position_test_output.png
12. thread_safe_test.png

Recommendation:

1. Move deterministic test inputs to tests/data/fixtures.
2. Move visual outputs used for validation to debug/plots or documentation/assets.
3. Delete throwaway output files that can be regenerated.

---

## 7. Documentation Cleanup Recommendations

Root currently has many project-state and handoff markdown files. This is useful historically but noisy operationally.

Recommendation:

1. Keep only README.md plus one current STATUS.md in root.
2. Move all handoff and milestone docs into documentation/handoffs and documentation/history.
3. Keep one index file in documentation that links active docs and archives stale ones.

Candidates to move from root into documentation/handoffs or documentation/history:

1. ANALYSIS_RESULTS_COMPARISON.md
2. HYBRID_SYSTEM_BACKUP_MANIFEST.md
3. HYBRID_SYSTEM_SUCCESS_REPORT.md
4. MERGE_HANDOFF_FOR_GEMINI.md
5. POST_PRINT_ANALYSIS_INTEGRATION.md
6. PROJECT_UPDATE_HYBRID_SYSTEM.md
7. UNIFIED_CALCULATOR_IMPLEMENTATION.md
8. WORK_OF_ADHESION_METRICS_DEFINITIONS.md

---

## 8. Archive Strategy (GitHub Archive + Local Trim)

### 8.1 High-value archive candidates

1. backup_complete_system_20250921
2. backup_corrected_system_20250921
3. archived_files (if already superseded by newer archive policies)
4. archive_experimental_compressed.zip
5. large historic output bundles under PrintingLogs_Backup if not actively needed in this repo

### 8.2 Recommended archive approach

1. Create a dedicated archive repository (or release artifacts) for historical backups.
2. Preserve one tagged snapshot before removal from active repo.
3. Document archive retrieval steps in documentation/archive_index.md.
4. Remove archive payload from active working repo after verification.

### 8.3 Retention policy proposal

1. Keep only last 1-2 validated backups in active repo.
2. Move anything older than 30-60 days to archive repository.
3. Keep generated plots/logs only if tied to publication/regression evidence.

---

## 9. Consolidation Opportunities (Script Rationalization)

### 9.1 Adhesion metrics calculators

Observation: there are multiple calculators with overlapping intent. Repository memory indicates support_modules/adhesion_metrics_calculator.py is canonical.

Recommendation:

1. Set support_modules/adhesion_metrics_calculator.py as canonical implementation.
2. Convert root adhesion_metrics_calculator.py into one of:
   - thin wrapper import, or
   - deprecated alias with warning, or
   - remove if all imports updated.
3. Keep backup calculators only in archive.

### 9.2 Post-print analyzer ownership

Observation: post_print_analyzer.py exists both in root and post-processing with non-identical content.

Recommendation:

1. Choose one canonical location (prefer post-processing for analysis pipeline cohesion).
2. Keep root entry point as a tiny delegating launcher only if operationally convenient.
3. Add tests that verify delegation path and expected outputs.

### 9.3 Plotting entry points

Observation: multiple plotter runners and debug plot scripts exist.

Recommendation:

1. Keep one production plotter API and one production CLI entry point.
2. Move all experimental and one-time plotting scripts to debug/legacy_tests or archive.
3. Add naming convention with prefixes:
   - prod_ for production entry points
   - exp_ for experimental scripts
   - deprecated_ for sunset scripts

---

## 10. Proposed Target Workspace Structure

Suggested top-level layout:

1. src/
2. support_modules/
3. post-processing/
4. tests/
5. tools/
6. debug/
7. documentation/
8. data/
9. archive/ (lightweight pointers only)

And a cleaner root containing only:

1. README.md
2. STATUS.md
3. Prince_Segmented.py (or src entry point)
4. batch_process_printing_data.py (or src CLI entry)
5. pyproject.toml or requirements.txt
6. .gitignore

If full src migration is too disruptive now, first step should still be root minimization and strict folder ownership.

---

## 11. Immediate Safe Actions (Low Risk, High Value)

Execute in this order:

1. Delete exact duplicate root test files already present in tests.
2. Delete exact duplicate root debug/tool scripts already present in debug or tools.
3. Move root PNG/CSV artifacts into tests/data/fixtures or debug/plots, then delete redundant copies.
4. Move handoff/status markdown files from root into documentation/handoffs and documentation/history.
5. Expand root README.md into a true entry map.

These actions should produce a major clarity improvement with minimal functional risk.

---

## 12. Medium-Term Actions (Requires Validation)

1. Unify calculator module ownership and import paths.
2. Unify post_print_analyzer ownership and entry point strategy.
3. Create a single accepted end-to-end batch workflow and deprecate alternatives.
4. Remove legacy backup folders from active repo after archive transfer.
5. Add folder-level READMEs for tests, debug, tools, and data.

---

## 13. Git And Ignore Policy Improvements

Current .gitignore covers logs and Python artifacts but should better isolate generated analysis output.

Suggested additions (after confirming desired tracking behavior):

1. debug/plots/
2. debug/*.log
3. post-processing/manuscript_plot_runs/
4. post-processing/archive/
5. temporary result CSV/XLSX patterns if regenerated routinely

Note: do not ignore all CSV globally unless all CSV are regenerated artifacts.

---

## 14. Validation Checklist After Cleanup

1. Run main print workflow smoke test.
2. Run post-processing batch on representative data.
3. Run tests suite in tests.
4. Confirm no imports still reference removed root duplicate files.
5. Confirm all docs links remain valid after moves.
6. Confirm generated plots and result tables are still reproducible.

---

## 15. Suggested Gemini Handoff Tasks

Use Gemini to accelerate mechanical refactors while preserving behavior.

Recommended task sequence:

1. Build a machine-generated move/delete plan from this audit.
2. Create import-path update patch for canonical module ownership.
3. Produce a docs reindex patch (documentation/index.md with active vs archived docs).
4. Propose .gitignore update with explicit rationale per pattern.
5. Generate a cleanup PR checklist and scripted validation commands.

Suggested prompt for Gemini:

"Using WORKSPACE_CLEANUP_AUDIT_2026-03-25.md as the source of truth, generate a conservative cleanup patch that only applies low-risk changes first: remove exact duplicate root files already present in tests/debug/tools, move root markdown handoff files into documentation/handoffs, move root artifact PNG/CSV files into debug/plots or tests/data/fixtures, and produce an explicit report of every change. Do not alter core production code logic in this first pass."

---

## 16. Final Recommendation

Proceed with a two-PR strategy:

1. PR 1: Non-functional cleanup only (duplicates, file moves, docs relocation, artifact reorganization).
2. PR 2: Functional consolidation (canonical module ownership and import updates).

This minimizes integration risk, preserves traceability, and gives a clear handoff path for both human reviewers and Gemini-assisted follow-up.
