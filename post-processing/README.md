# Post-Processing Pipeline Documentation

This directory contains the complete analysis pipeline for processing print data after (or during) printing. The tools here transform raw CSV data into adhesion metrics, visualizations, and statistical summaries.

## Directory Organization

**Current Status (February 26, 2026):** Streamlined to focus on core pipeline modules

**Active Scripts (17):**
- **Core Pipeline** (12): RawData_Processor, post_print_analyzer, analysis_plotter, master_plotter, statistical_analysis, run_complete_analysis, run_scaling_analysis, data_validator, generate_analysis_report, generate_summary_table, summary_plot_generator, advanced_metrics
- **Specialized Tools** (5): material_stiffness_analyzer, stiffness_scaling_analyzer, critical_dimension_analysis, continuous_motion_analyzer, batch_continuous_motion_processor

**Archived Scripts:** One-time analysis and experimental scripts moved to `../archive/post_processing_analysis_scripts/` to reduce context window size. See archive README for details on 12 archived scripts.

## Table of Contents

- [Directory Organization](#directory-organization)
- [Pipeline Overview](#pipeline-overview)
- [Core Modules](#core-modules)
- [Workflow](#workflow)
- [Output Files](#output-files)
- [Batch Processing](#batch-processing)
- [Troubleshooting](#troubleshooting)

---

## Pipeline Overview

### Data Flow

```
Raw Data (autolog_*.csv)
    ↓
[Layer Boundary Detection] ← RawData_Processor.py
    ↓
Layer-Specific CSVs (autolog_L##-L##.csv)
    ↓
[Adhesion Analysis] ← post_print_analyzer.py
    ↓
Adhesion Metrics CSV + Plots
    ↓
[Statistical Analysis] ← statistical_analysis.py
    ↓
Summary Tables + Scaling Plots
```

### Purpose

Transform raw position/force/time data into:
- **Quantitative adhesion metrics** (peak force, work of adhesion, distances)
- **Visual representations** (force curves, scaling plots)
- **Statistical summaries** (means, std dev, trends)
- **Comparative analysis** (material testing, parameter optimization)

---

## Core Modules

### `RawData_Processor.py`

**Purpose:** Detect layer boundaries in continuous data and segment into individual layers

**Key Algorithm:**

```python
# Layer boundary detection
1. Load raw CSV with Time, Position, Force, Phase
2. Scan for lift-retract sequences:
   - Find "Lift-Stage1" or "Lift-Stage2" start
   - Find corresponding "Retract-Stage1/Stage2" end
   - Extract all data between these points
3. Save each layer segment to separate CSV
4. Generate layer-specific files: autolog_L##-L##.csv
```

**Phase Detection Logic:**

```python
# Handles both old and new phase label formats
if phase.startswith('Lift'):
    # Check if isolated old label (1-5 points without "Stage")
    if is_isolated_old_label:
        skip_it  # Prevents false positives
    else:
        # Valid staged sequence: Lift-Stage1 → Stage2
        mark_layer_start
        
if phase.startswith('Retract'):
    # Find matching retract for current lift
    mark_layer_end
    extract_and_save_layer
```

**Key Functions:**
- `load_and_clean_data(csv_path)` - Read CSV, handle missing data
- `detect_layer_boundaries(data)` - Find lift-retract pairs
- `extract_layer_segment(start_idx, end_idx)` - Get layer data
- `save_layer_csv(data, layer_number)` - Write layer file

**Usage:**
```python
from RawData_Processor import RawDataProcessor

processor = RawDataProcessor("autolog_Print1.csv")
processor.detect_and_extract_layers()
# Creates: autolog_L1-L1.csv, autolog_L2-L2.csv, ...
```

**Output:**
```
autolog_L1-L1.csv      # Layer 1 (all phases)
autolog_L2-L2.csv      # Layer 2
autolog_L48-L50.csv    # Layers 48-50 (batch)
```

**Critical Update (January 2026):**
- Fixed to detect 2-stage phase labels (Lift-Stage1/Stage2)
- Added isolated label detection to prevent false positives
- Changed from exact match to `startswith()` for robustness

---

### `post_print_analyzer.py`

**Purpose:** Calculate comprehensive adhesion metrics from layer-specific CSV files

**Analysis Pipeline:**

```python
For each layer CSV:
    1. Load time, position, force data
    2. Identify prescribed-speed start (from phase data)
    3. Call adhesion_metrics_calculator.py
    4. Extract metrics dictionary
    5. Append to results list
    
Save all metrics to CSV
Generate summary statistics
```

**Key Features:**
- Batch processing of multiple layers
- Automatic prescribed-speed boundary detection
- Contact area normalization (if provided)
- Error handling for problematic layers
- Progress reporting

**Key Functions:**
- `analyze_single_layer(csv_path)` - Process one layer
- `analyze_print_folder(folder_path)` - Process entire print
- `calculate_contact_area(image_or_params)` - Determine area
- `generate_summary_statistics(metrics_list)` - Aggregate results

**Usage:**
```python
from post_print_analyzer import analyze_print_folder

metrics_df = analyze_print_folder(
    folder_path="Printing_Logs/2026-02-02/Print_1",
    contact_area_mm2=40.0  # Optional
)

# Output: adhesion_metrics_Print1.csv
```

**Output CSV Format:**
```csv
Layer_Number,Peak_Force_N,Work_of_Adhesion_mJ,Peeling_Initiation_Distance_mm,Post_Peak_Distance_mm,Total_Adhesion_Distance_mm,Peak_Force_per_Area_N_mm2,Work_per_Area_mJ_mm2,...
1,0.125,0.0234,0.150,0.085,0.235,0.00313,0.000585
2,0.132,0.0256,0.148,0.089,0.237,0.00330,0.000640
```

**Metrics Calculated:**
- Peak Force (N)
- Work of Adhesion (mJ)
- Peeling Initiation Distance (mm)
- Post-Peak Distance (mm)
- Total Adhesion Distance (mm)
- Peak Force per Area (N/mm²) - if area provided
- Work per Area (mJ/mm²) - if area provided
- Boundary times and positions

---

### `analysis_plotter.py`

**Purpose:** Generate publication-quality visualizations of adhesion data

**Plot Types:**

1. **Force vs. Position Curve**
   ```
   Force (N)
     ↑
     │     Peak
     │      ╱╲
     │     ╱  ╲
     │────┘    ╲────────
     └────────────────→ Position (mm)
         Initiation  Completion
   ```
   - Shows complete peeling cycle
   - Highlights initiation, peak, completion
   - Displays work of adhesion (shaded area)

2. **Force vs. Time Curve**
   - Temporal evolution of forces
   - Identifies phase transitions
   - Shows motion profile effects

3. **Multi-Layer Overlay**
   - Compare multiple layers
   - Identify consistency/variation
   - Detect anomalies

4. **Phase-Annotated Plot**
   - Color-coded by phase
   - Shows Exposure, Lift-Stage1, Lift-Stage2, Retract, etc.
   - Correlates motion with force response

**Key Functions:**
- `plot_force_curve(data, metrics)` - Single layer plot
- `plot_multi_layer(layer_list)` - Overlay multiple layers
- `plot_with_phases(data, phase_data)` - Phase-colored plot
- `add_metric_annotations(ax, metrics)` - Mark key points

**Usage:**
```python
from analysis_plotter import plot_force_curve

plot_force_curve(
    data=layer_data,
    metrics=adhesion_metrics,
    output_path="layer_5_analysis.png"
)
```

**Output:**
```
analysis_L5.png           # Single layer plot
analysis_L1-L10.png       # Multi-layer overlay
phase_annotated_L5.png    # Phase-colored plot
```

---

### `statistical_analysis.py`

**Purpose:** Perform statistical analysis on adhesion metrics across multiple prints

**Analyses Performed:**

1. **Descriptive Statistics**
   - Mean, median, std dev
   - Min, max, range
   - Coefficient of variation

2. **Trend Analysis**
   - Force vs. layer number
   - Work of adhesion evolution
   - Distance metrics trends

3. **Correlation Analysis**
   - Force vs. area
   - Work vs. area
   - Speed effects

4. **Scaling Behavior**
   - Power law fitting: F ~ A^n
   - Determine scaling exponent
   - Confidence intervals

**Key Functions:**
- `calculate_summary_stats(metrics_df)` - Descriptive statistics
- `analyze_trends(metrics_df)` - Temporal trends
- `analyze_scaling(force_list, area_list)` - Scaling exponent
- `generate_report(analyses_dict)` - Create summary report

**Usage:**
```python
from statistical_analysis import analyze_print_data

results = analyze_print_data(
    metrics_csv="adhesion_metrics_Print1.csv"
)

# Output: statistical_summary_Print1.txt
```

---

### `batch_process_universal.py`

**Purpose:** Process multiple prints in batch mode for comparative studies

**Features:**
- Recursive folder scanning
- Automatic print detection
- Parallel processing (optional)
- Consolidated summary tables
- Comparative visualizations

**Workflow:**
```python
1. Scan folder tree for print directories
2. For each print:
   a. Run RawData_Processor
   b. Run post_print_analyzer
   c. Generate plots
   d. Extract summary metrics
3. Combine all summaries into master table
4. Generate comparative plots
```

**Usage:**
```powershell
python post-processing/batch_process_universal.py "C:\PrintingLogs\2026-02-02"
```

**Output:**
```
batch_summary_2026-02-02.csv         # All prints summary
batch_scaling_plot.png               # Force vs. area across prints
batch_statistics.txt                 # Statistical summary
```

---

### `critical_dimension_analysis.py`

**Purpose:** Analyze adhesion scaling with critical dimensions (radius, area)

**Key Analyses:**

1. **Radius-Based Scaling**
   - For circular features
   - F ~ R^n (expect n ≈ 2 for area-dependent)
   - Identify edge effects

2. **Area-Based Scaling**
   - F ~ A^n
   - Linear fit on log-log plot
   - Determine scaling exponent

3. **Geometry Effects**
   - Compare circular vs. square features
   - Edge length vs. area
   - Shape factor analysis

**Key Functions:**
- `analyze_radius_scaling(data)` - Radius-dependent behavior
- `fit_power_law(x, y)` - Power law fitting
- `plot_scaling_with_confidence(data, fit)` - Visualization

---

### `material_stiffness_analyzer.py`

**Purpose:** Estimate effective material stiffness from force-displacement curves

**Methodology:**

```python
# Effective stiffness from initial slope
1. Extract force-displacement in peeling region
2. Fit linear region (elastic response)
3. Calculate slope: k_eff = dF/dx
4. Compare across materials/conditions
```

**Applications:**
- Material comparison
- Resin characterization
- Temperature effects on stiffness

---

## Workflow

### Basic Analysis Workflow

**Step 1: Generate Layer Files**
```powershell
python post-processing/RawData_Processor.py "autolog_Print1.csv"
```
Output: `autolog_L##-L##.csv` files

**Step 2: Calculate Adhesion Metrics**
```powershell
python post-processing/post_print_analyzer.py "Print_1_folder" --area 40.0
```
Output: `adhesion_metrics_Print1.csv`

**Step 3: Generate Plots**
```powershell
python post-processing/analysis_plotter.py "Print_1_folder"
```
Output: `analysis_L##.png` files

**Step 4: Statistical Analysis**
```powershell
python post-processing/statistical_analysis.py "adhesion_metrics_Print1.csv"
```
Output: `statistical_summary_Print1.txt`

---

### Batch Processing Workflow

**Process Multiple Prints:**
```powershell
python post-processing/batch_process_universal.py "C:\PrintingLogs\2026-02-02"
```

This automatically:
1. Finds all print folders
2. Processes each print
3. Generates individual plots and metrics
4. Creates comparative analysis
5. Produces summary tables

---

### Advanced Analysis Workflow

**Scaling Studies:**
```powershell
# Process prints with different contact areas
python post-processing/critical_dimension_analysis.py "scaling_experiment_folder"
```

**Material Comparison:**
```powershell
# Compare different resin formulations
python post-processing/material_stiffness_analyzer.py "material_comparison_folder"
```

---

## Output Files

### CSV Files

**Layer-Specific Data:**
```
autolog_L1-L1.csv
autolog_L2-L2.csv
...
```
Format: Time (s), Position (mm), Force (N), Phase

**Adhesion Metrics:**
```
adhesion_metrics_Print1.csv
```
Format: Layer_Number, Peak_Force_N, Work_of_Adhesion_mJ, ...

**Batch Summaries:**
```
batch_summary_2026-02-02.csv
```
Format: Print_ID, Mean_Peak_Force, Mean_Work, Std_Dev_Force, ...

### Plot Files

**Individual Layer Plots:**
```
analysis_L5.png                    # Force vs. position for layer 5
analysis_L5_time.png               # Force vs. time for layer 5
phase_annotated_L5.png             # Phase-colored plot
```

**Multi-Layer Plots:**
```
analysis_L1-L10_overlay.png        # 10 layers overlaid
```

**Scaling Plots:**
```
force_vs_area_scaling.png          # Log-log scaling plot
work_vs_area_scaling.png           # Work of adhesion scaling
```

**Statistical Plots:**
```
force_distribution.png             # Histogram of peak forces
force_vs_layer_trend.png           # Force evolution over layers
```

### Text Reports

**Statistical Summary:**
```
statistical_summary_Print1.txt

Summary Statistics:
- Mean Peak Force: 0.125 ± 0.015 N
- Mean Work of Adhesion: 0.0234 ± 0.0025 mJ
- Coefficient of Variation: 12%

Trends:
- Force increases slightly with layer number (slope: 0.0002 N/layer)
- Work of adhesion stable across layers

Scaling:
- Force ~ Area^0.98 (R² = 0.95)
- Near-linear scaling indicates area-dependent adhesion
```

---

## Batch Processing

### Folder Structure Requirements

For batch processing to work, organize data as:

```
Experiment_Folder/
├── 2026-02-01/
│   ├── Print_1/
│   │   └── autolog_Print1.csv
│   ├── Print_2/
│   │   └── autolog_Print2.csv
│   └── ...
├── 2026-02-02/
│   ├── Print_1/
│   │   └── autolog_Print1.csv
│   └── ...
└── summary/
    └── (batch outputs will be created here)
```

### Batch Processing Command

**Process all prints in date folder:**
```powershell
python post-processing/batch_process_universal.py "C:\PrintingLogs\2026-02-02"
```

**Process entire experiment:**
```powershell
python post-processing/batch_process_universal.py "C:\PrintingLogs" --recursive
```

**Options:**
- `--area` - Specify contact area for all prints
- `--output-dir` - Custom output location
- `--parallel` - Use multiprocessing
- `--plots-only` - Skip metrics calculation, just plot

---

## Troubleshooting

### Problem: "No layers detected"

**Possible Causes:**
1. Phase labels don't match expected format
2. Isolated old "Lift" labels causing false detection
3. Data file corrupted or incomplete

**Solutions:**
1. Check CSV phase column - should see "Lift-Stage1", "Lift-Stage2", etc.
2. Update `RawData_Processor.py` to latest version (includes isolated label detection)
3. Verify raw data file opens in Excel/text editor

---

### Problem: "Cannot calculate adhesion metrics"

**Possible Causes:**
1. Baseline detection failed (noisy data)
2. No clear peak force
3. Force never returns to baseline
4. Insufficient data points

**Solutions:**
1. Adjust baseline detection parameters in `adhesion_metrics_calculator.py`
2. Check force gauge calibration
3. Verify print motion profile (may need longer retraction)
4. Increase data sampling rate

---

### Problem: "Plots show incorrect boundaries"

**Possible Causes:**
1. Prescribed-speed start position not detected
2. Phase data missing or incorrect
3. Layer segmentation error

**Solutions:**
1. Verify phase labels in layer CSV
2. Check that `Lift-Stage2` is present (marks prescribed speed start)
3. Re-run `RawData_Processor.py` with latest version

---

### Problem: "Batch processing fails on some prints"

**Possible Causes:**
1. Some prints have different data format
2. Missing files in print folder
3. Corrupted CSV files

**Solutions:**
1. Add error handling: `--skip-errors` flag
2. Check each failed print individually
3. Standardize data format across all prints

---

### Problem: "Scaling analysis shows poor fit"

**Possible Causes:**
1. Insufficient data points (need multiple contact areas)
2. Edge effects dominating small features
3. Non-area-dependent adhesion mechanism

**Solutions:**
1. Include more prints with varied areas
2. Filter out smallest features (edge effects)
3. Try different scaling models (linear, exponential, etc.)

---

## Configuration Files

### `analysis_config.yaml` (optional)

Configure analysis parameters:

```yaml
baseline_detection:
  window_size: 50
  threshold_factor: 3.0
  
adhesion_metrics:
  force_threshold: 0.005  # N
  integration_method: 'trapezoid'
  
plotting:
  figure_size: [10, 6]
  dpi: 300
  font_size: 12
  
batch_processing:
  parallel: true
  num_workers: 4
  skip_errors: true
```

---

## Performance Considerations

### Data Volume

**Typical Print (100 layers):**
- Raw autolog: 50-200 MB
- Layer CSVs: 500 KB - 2 MB per layer
- Metrics CSV: ~10 KB
- Plots: ~500 KB per plot

**Batch Processing:**
- 10 prints: ~5 GB raw data
- Processing time: ~10-20 minutes
- Output: ~100 MB (metrics + plots)

### Optimization Tips

1. **Use decimated data** - 100 Hz sufficient for most analyses
2. **Process layers in parallel** - `--parallel` flag
3. **Skip unnecessary plots** - `--no-plots` for quick metrics
4. **Archive old data** - Move processed prints to backup

---

## Development Guidelines

### Adding New Analysis Module

1. **Create module file** in `post-processing/`
2. **Follow naming convention:** `analysis_type_analyzer.py`
3. **Include standard interface:**
   ```python
   def analyze_data(input_path, output_path=None, **kwargs):
       """
       Description
       
       Parameters:
       -----------
       input_path : str
           Path to input data
       output_path : str, optional
           Path for output files
       **kwargs : dict
           Additional parameters
       
       Returns:
       --------
       results : dict
           Analysis results
       """
   ```
4. **Update this README** with module documentation
5. **Add to batch processor** if applicable

### Testing New Analysis

1. **Test on single layer** - Verify algorithm works
2. **Test on complete print** - Check robustness
3. **Test edge cases** - Empty data, noisy data, missing data
4. **Validate output** - Compare with manual calculations
5. **Document parameters** - Default values, valid ranges

---

## Quick Reference

### Most Common Tasks

**Analyze single print:**
```powershell
python post-processing/post_print_analyzer.py "Print_1" --area 40.0
```

**Generate plots for print:**
```powershell
python post-processing/analysis_plotter.py "Print_1"
```

**Batch process date folder:**
```powershell
python post-processing/batch_process_universal.py "2026-02-02"
```

**Create scaling plot:**
```powershell
python post-processing/critical_dimension_analysis.py "scaling_study"
```

### File Locations

**Input:** `Printing_Logs/YYYY-MM-DD/Print_#/autolog_Print#.csv`  
**Output:** Same directory as input  
**Batch Output:** `summary/` subfolder in experiment directory

---

## Integration with Real-Time Analysis

**During Print (Real-Time):**
- `PeakForceLogger.py` calculates metrics as print progresses
- Saves to `adhesion_metrics_Print#.csv` incrementally

**After Print (Post-Processing):**
- Use these modules to verify real-time results
- Generate additional plots
- Perform detailed statistical analysis

**Comparison:**
- Real-time: Fast, approximate, uses decimated data
- Post-processing: Thorough, accurate, uses full data

---

## Contact

For questions about post-processing:

**Analysis Algorithms:** Evan Jones (evanjones2026@u.northwestern.edu)  
**Data Formats:** Boyuan Sun (boyuansun2026@u.northwestern.edu)  
**Visualization:** Evan Jones (evanjones2026@u.northwestern.edu)

---

**Last Updated:** February 26, 2026  
**Active Modules:** 17 (12 core + 5 specialized)  
**Archived Modules:** 12 (see `../archive/post_processing_analysis_scripts/`)  
**Python Version:** 3.8+
