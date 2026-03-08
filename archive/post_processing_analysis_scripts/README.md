# Post-Processing Analysis Scripts Archive

**Archive Date:** February 26, 2026  
**Reason:** Reduce context window size by archiving one-time, experimental, and dataset-specific analysis scripts

---

## Overview

This directory contains post-processing scripts that were created for specific analyses, experiments, or datasets. These scripts served important purposes during development and data analysis but are not part of the core pipeline workflow.

**Status:** These scripts are functional but not actively maintained. They remain available for reference or reuse if similar analyses are needed in the future.

---

## Archived Scripts

### Peak Layer Extraction Tools (5 scripts)

#### `extract_peak_layer_comparison.py`
- **Date Created:** February 6, 2026
- **Purpose:** Extract the layer with the most prominent force peak from autolog_L45-L49.csv files across multiple material folders
- **Output:** Single CSV with columns for each folder (FolderName_Time, FolderName_Position, FolderName_Force)
- **Use Case:** Comparative analysis of peak force behavior across different materials
- **Why Archived:** One-time analysis for specific layer range (L45-L49); not part of standard workflow

#### `extract_peak_layer_continuous.py`
- **Purpose:** Extract peak layer data from continuous motion data files
- **Features:** Layer boundary detection, peak force identification, multi-folder comparison
- **Use Case:** Analysis of continuous motion prints
- **Why Archived:** Superseded by `continuous_motion_analyzer.py` in core pipeline

#### `extract_peak_layer_continuous_heavy_smooth.py`
- **Purpose:** Same as above but with heavy smoothing (3x standard parameters)
- **Smoothing:** Median kernel=93, Savitzky-Golay window=153
- **Use Case:** Analyzing noisy continuous motion data
- **Why Archived:** Experimental smoothing parameters; standard pipeline has configurable smoothing

#### `extract_peak_layer_from_phase.py`
- **Date Created:** February 2026
- **Purpose:** Extract peak layer using Phase column for boundary detection
- **Features:** Phase-aware layer detection, supports both old and new phase naming
- **Use Case:** Analysis requiring precise phase-based segmentation
- **Why Archived:** Functionality integrated into `RawData_Processor.py`

#### `extract_specific_layers_from_phase.py`
- **Purpose:** Extract user-specified layer ranges using phase data
- **Features:** Custom layer selection (e.g., L45-L49), phase boundary detection
- **Use Case:** Targeted analysis of specific layer ranges
- **Why Archived:** Ad-hoc analysis tool; not needed for standard pipeline

---

### Plotting and Visualization (3 scripts)

#### `plot_peak_cycles.py`
- **Purpose:** Plot Time vs Force for non-continuous files with logarithmic Y-axis
- **Features:** PFPE (solid lines) vs PDMS (dashed lines), heavy smoothing option
- **Options:** Baseline normalization, log/linear scale, configurable smoothing
- **Use Case:** Visualizing peak cycle comparisons across materials
- **Why Archived:** Specialized plotting for specific material comparison study

#### `plot_peak_cycles_synced.py`
- **Purpose:** Time-synchronized plotting of peak cycles across materials
- **Features:** Aligns time=0 to lift start, overlays multiple materials
- **Use Case:** Temporal comparison of force evolution
- **Why Archived:** One-time visualization for presentation; not part of standard reporting

#### `plot_full_autolog.py`
- **Purpose:** Plot entire autolog CSV file (all layers, full print)
- **Features:** Simple Time/Position vs Force plotting
- **Use Case:** Quick visualization of complete print data
- **Why Archived:** `master_plotter.py` provides more comprehensive full-print visualizations

---

### Analysis and Processing (4 scripts)

#### `analyze_all_layers.py`
- **Date Created:** February 10, 2026
- **Purpose:** Create table of peak force and propagation time for each layer in each dataset
- **Metrics:** 
  - Peak force (absolute and smoothed)
  - Propagation time (peak to baseline return)
- **Use Case:** Layer-by-layer comparison across multiple datasets
- **Why Archived:** One-time analysis; results incorporated into reports

#### `analyze_single_folder_detailed.py`
- **Purpose:** Detailed analysis of a single experimental folder
- **Features:** Extended metrics, comprehensive plots, detailed reports
- **Use Case:** Deep-dive analysis of individual experiments
- **Why Archived:** Not part of standard batch pipeline; use `post_print_analyzer.py` instead

#### `export_processed_data.py`
- **Purpose:** Export processed data in various formats (CSV, Excel, JSON)
- **Features:** Format conversion, data aggregation, custom export schemas
- **Use Case:** Sharing data with collaborators or exporting for external analysis tools
- **Why Archived:** Functionality available through standard pipeline output formats

#### `process_single_v4_folder.py`
- **Date Created:** November 18, 2025
- **Purpose:** Process a single V4 test folder (dataset-specific)
- **Features:** V4-specific folder structure, V4 naming conventions
- **Example:** `V4/100umPDMS_500um_TankV19_BPAGDA_Pyramid_1000`
- **Why Archived:** Dataset-specific (V4 only); superseded by `batch_process_universal.py`

---

## When to Use These Scripts

These archived scripts remain functional and can be used when:

1. **Reproducing specific analyses** from early 2026
2. **Investigating historical data** processed with these tools
3. **Comparing methodologies** between old and new approaches
4. **Extracting specialized subsets** of data for presentations

## How to Use

All scripts are standalone and include `if __name__ == "__main__"` blocks with usage examples.

**General usage pattern:**
```bash
python <script_name>.py <input_path> [options]
```

For detailed usage of any script:
```bash
python <script_name>.py --help
```

---

## Relationship to Core Pipeline

The core post-processing pipeline (in `../post-processing/`) provides:
- **RawData_Processor.py** - Layer boundary detection (replaces extract_* scripts)
- **post_print_analyzer.py** - Comprehensive analysis (replaces analyze_* scripts)
- **master_plotter.py** - Publication-quality plots (replaces plot_* scripts)
- **batch_process_universal.py** - Universal batch processing (replaces dataset-specific scripts)

**Recommendation:** Use core pipeline tools for new analyses. Refer to archived scripts only when replicating historical work or understanding analysis evolution.

---

## Archive History

| Date | Action | Scripts Archived | Reason |
|------|--------|------------------|---------|
| Feb 26, 2026 | Initial archival | 12 scripts | Reduce context window size; consolidate around core pipeline |

---

## Notes

- All scripts tested and functional as of February 2026
- Dependencies: pandas, numpy, scipy, matplotlib
- Most scripts expect standard autolog_*.csv format with Time, Position, Force, Phase columns
- Some scripts have dataset-specific assumptions (folder structures, naming conventions)

**Context Window Reduction:** This archival reduced the post-processing directory from 29 to 17 Python files, focusing on the actively maintained core pipeline.
