# Post-Processing Folder Index

## Purpose

The post-processing folder contains the analysis pipeline used after a print run completes.
Its job is to convert raw force/position CSV data into segmented layer data, adhesion metrics, plots, summary tables, and comparison reports.

## What This Folder Owns

1. Raw CSV discovery and validation.
2. Layer segmentation from continuous print logs.
3. Adhesion metric computation.
4. Plot generation and summary reporting.
5. Batch and specialized analysis workflows.

## Core Pipeline

The common flow is:

1. Read `autolog_*.csv` or related print-session CSVs.
2. Segment layers with `RawData_Processor.py`.
3. Compute metrics with `post_print_analyzer.py` and `support_modules/adhesion_metrics_calculator.py`.
4. Generate plots with `analysis_plotter.py` and `master_plotter.py`.
5. Produce summary tables and reports.

## Major Modules

### `RawData_Processor.py`

The layer-boundary detector and segmentation engine.
It loads raw print data, finds layer transitions, and returns per-layer structures for downstream analysis.

### `post_print_analyzer.py`

The main print-session analyzer.
It iterates through segmented layers, computes adhesion metrics, and writes per-print summaries.

### `analysis_plotter.py`

The primary plotting helper for force/position and multi-layer visualization.

### `master_plotter.py`

The top-level plot orchestration entry point for large result sets.

### `statistical_analysis.py`

Computes aggregate statistics across runs or parameter sweeps.

### `generate_analysis_report.py`

Builds human-readable report outputs from completed analysis runs.

### `generate_summary_table.py`

Produces summary CSV or table outputs for quick comparison.

### `summary_plot_generator.py`

Creates condensed visual summaries for reports or presentations.

### `critical_dimension_analysis.py`

Specialized dimensional analysis for key feature classes.

### `continuous_motion_analyzer.py`

Analyzes runs that use continuous motion rather than discrete step cycles.

### `batch_continuous_motion_processor.py`

Batch wrapper for continuous-motion analysis sets.

### `material_stiffness_analyzer.py` and `stiffness_scaling_analyzer.py`

Specialized stiffness and scaling studies used for comparative material analysis.

### `advanced_metrics.py`

Higher-level metrics and derived quantities used by summary workflows.

### `data_validator.py`

Checks input consistency before downstream processing.

### `run_complete_analysis.py` and `run_scaling_analysis.py`

Convenience entry points for end-to-end analysis runs.

### `manual_post_processing.py`

Operator-oriented or ad hoc analysis helper for cases that do not fit the automated pipeline.

## Key Inputs

1. Raw layer log CSVs.
2. Layer-segmented CSVs.
3. Contact-area parameters when available.
4. Experimental metadata from print-session folders.

## Key Outputs

1. Adhesion metrics CSVs.
2. Layer boundary exports.
3. Summary plots.
4. Analysis reports and tables.

## Dependencies

1. `support_modules.RawData_Processor`
2. `support_modules.adhesion_metrics_calculator`
3. `support_modules.SessionManager`
4. `support_modules.PositionLogger` and related print-session log producers
5. `matplotlib`, `numpy`, `pandas`, and `scipy`

## Failure Modes

1. Missing or malformed CSV input.
2. Phase labeling mismatch between old and new print logs.
3. Plotting backend issues in headless runs.
4. Inconsistent contact-area assumptions across runs.

## Documentation Notes

The existing `post-processing/README.md` remains the primary directory overview.
This index is the round-2 folder-level map and should be treated as the current architecture summary.
