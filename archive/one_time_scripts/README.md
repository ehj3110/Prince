# One-Time Scripts Archive

**Archived:** February 25, 2026  
**Purpose:** Preserve scripts that were created for specific one-time tasks

---

## Overview

This directory contains 28 scripts that were created for specific datasets, analyses, or presentations and are no longer part of the regular workflow. They are preserved for reference and documentation purposes.

## Categories

### One-Time Plotting Scripts (9 files)
Scripts that generated specific plots for presentations or papers:
- `generate_final_progressive_plots.py`
- `generate_final_progressive_plots_no_fep.py`
- `generate_individual_plots_hybrid_compliant.py`
- `generate_presentation_master_plots.py`
- `generate_tempopicker_v2_master_plots.py`
- `generate_v2_complete_master_plots.py`
- `generate_v2_master_plots.py`
- `plot_dual_stiffness_example.py`
- `no_fep_plots_verification.py`

### One-Time Reprocessing Scripts (4 files)
Scripts used to reprocess specific datasets with updated algorithms:
- `reprocess_hybrid_compliant.py`
- `reprocess_tempopicker_v2_complete.py`
- `reprocess_tempopicker_v2_folders.py`
- `reprocess_tempopicker_v2_simple.py`

### One-Time Analysis Scripts (3 files)
Scripts that performed specific analyses on particular datasets:
- `analyze_presentation_scaling.py`
- `analyze_presentation_stiffness.py`
- `analyze_presentation_stiffness_v2.py`

### One-Time Data Manipulation Scripts (6 files)
Scripts that performed one-time data transformations or corrections:
- `add_areas_to_conditions.py`
- `add_L346_349_manually.py`
- `extract_v9_areas.py`
- `merge_new_hybrid_data.py`
- `process_L346_350.py`
- `verify_radius_data.py`

### Debug/Check Scripts (9 files)
Scripts used to validate data or check specific conditions:
- `check_baseline_columns.py`
- `check_groups.py`
- `check_hybrid_compliant.py`
- `check_max_areas.py`
- `check_original_areas.py`
- `check_peak_force.py`
- `check_peel_distance.py`
- `check_v9_conditions.py`
- `debug_plot_data.py`

---

## Usage Notes

These scripts are archived and may require updates to work with the current codebase:
- Import paths may need adjustment
- They may reference deprecated functions or parameters
- They were designed for specific datasets that may no longer be available in the same location

## For New Datasets

Instead of using these archived scripts, refer to:
- **Batch Processing:** `batch_processors/batch_process_universal.py` (recommended)
- **Plotting:** `post-processing/master_plotter.py` and `post-processing/analysis_plotter.py`
- **Analysis:** Tools in `post-processing/` directory

## Historical Context

Refer to the Git commit history for context on when and why these scripts were created. The commit messages and documentation summaries provide valuable context about the specific experiments and analyses these scripts supported.

---

## Archive Date

All scripts in this directory were archived on **February 25, 2026** as part of workspace organization Phase 1.
