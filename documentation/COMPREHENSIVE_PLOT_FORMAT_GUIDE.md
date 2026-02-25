# Comprehensive Plot Format & Style Guide
**Version 1.0 - Created February 25, 2026**

This document provides a complete reference for all plot types, structures, elements, and styling standards used in the Prince adhesion test analysis system.

---

## Table of Contents
1. [Overview](#overview)
2. [Autolog Plots (Individual Layer Analysis)](#autolog-plots-individual-layer-analysis)
3. [Master Plots (Dataset Comparison)](#master-plots-dataset-comparison)
4. [Batch Processing Workflow](#batch-processing-workflow)
5. [Universal Style Standards](#universal-style-standards)
6. [File Organization](#file-organization)

---

## Overview

The Prince system generates three main categories of plots:

### 1. **Autolog Plots** (Individual Layer Analysis)
- **Purpose**: Detailed analysis of individual adhesion test layers
- **Engine**: `analysis_plotter.py` (AnalysisPlotter class)
- **Usage**: Generated per autolog file during batch processing
- **Output**: Multi-panel figures showing force profiles with peeling stages

### 2. **Master Plots** (Dataset Comparison)
- **Purpose**: Compare metrics across multiple experimental conditions
- **Engines**: 
  - `tempo_picker_plot_styles.py` (4-subplot TEMPO Picker style)
  - `master_plotter.py` (MasterPlotter class, flexible layouts)
- **Usage**: Generated after processing complete dataset
- **Output**: 2×2 or 3×3 subplot figures with aggregated statistics

### 3. **Summary Plots** (Coming from `summary_plot_generator.py`)
- **Purpose**: High-level overview of test results
- **Usage**: Optional supplementary visualizations

---

## Autolog Plots (Individual Layer Analysis)

### Plot Structure

**Total Figure Layout**: Dynamic multi-panel layout
- **Total Panels**: 1 overview + N individual layer panels (where N = number of layers per autolog)
- **Grid**: 2 columns × variable rows
  - Row count = `(1 + N) / 2` rounded up
- **Panel Arrangement**:
  ```
  ┌─────────────────┬─────────────────┐
  │  Overview       │  Layer 1        │
  │  (Complete)     │  (Detail)       │
  ├─────────────────┼─────────────────┤
  │  Layer 2        │  Layer 3        │
  │  (Detail)       │  (Detail)       │
  ├─────────────────┼─────────────────┤
  │  Layer 4        │  Layer 5        │
  │  (Detail)       │  (Detail)       │
  └─────────────────┴─────────────────┘
  ```

### Overview Panel (Top-Left)

**Purpose**: Show all detected layers in context

**Elements**:
1. **Raw Force Trace**
   - Line: Black solid (`'k-'`)
   - Width: 1pt
   - Alpha: 0.4 (40% transparent)
   - Label: "Raw Force"

2. **Smoothed Force Trace**
   - Line: Navy solid (`'navy'`)
   - Width: 2.5pt
   - Alpha: 0.9
   - Label: "Smoothed Force"

3. **Layer Shaded Regions**
   - Fill: Layer color (from palette)
   - Alpha: 0.08 (8% transparent)
   - Span: From `start_idx` to `end_idx` of layer

4. **Peak Force Markers**
   - Symbol: Circle (`'o'`)
   - Size: 12pt
   - Color: Layer color
   - Edge: Black, 2pt width
   - Z-order: 5 (on top)

5. **Peak Vertical Lines**
   - Style: Dashed (`'--'`)
   - Width: 3pt
   - Color: Layer color
   - Alpha: 0.8

6. **Layer Number Labels**
   - Position: 5pt above each peak marker
   - Format: `"L[number]"` (e.g., "L101")
   - Font size: 16pt (font_size + 2)
   - Font weight: Bold
   - Color: Layer color

7. **Baseline Lines**
   - Style: Solid horizontal lines
   - Width: 3pt
   - Color: Layer color
   - Alpha: 0.9
   - Span: From pre-init time to propagation end time

8. **Propagation End Markers**
   - Style: Dotted vertical line (`':'`)
   - Width: 2pt
   - Color: Purple
   - Alpha: 0.8

**Axes**:
- **X-axis**: "Time (s)", 18pt bold
- **Y-axis**: "Force (N)", 18pt bold
- **Range X**: All layers with 5% margin on each side
- **Range Y**: 0 to (max peak force × 1.1)
- **Grid**: Enabled, alpha 0.3

**Title**: "Complete Force Profile", 20pt bold (font_size + 6)

**Legend**:
- Location: Lower right
- Font size: 13pt (font_size - 1)
- Frame alpha: 0.9
- Entries: Raw Force, Smoothed Force, (layer colors implied)

---

### Individual Layer Panels

**Purpose**: Detailed view of single layer peeling stages

**Elements**:
1. **Raw Force Trace**
   - Same styling as overview
   - Zoomed to layer time window

2. **Smoothed Force Trace**
   - Line: Layer color solid
   - Width: 2.5pt
   - Alpha: 0.9

3. **Pre-Initiation Shaded Region**
   - Fill: Light blue (`color='blue'`)
   - Alpha: 0.3
   - Label: "Pre-Initiation"
   - Span: Pre-init start to pre-init end

4. **Propagation Shaded Region**
   - Fill: Light coral (`color='red'`)
   - Alpha: 0.3
   - Label: "Propagation"
   - Span: Propagation start to propagation end

5. **Peak Force Vertical Line**
   - Style: Dashed (`'--'`)
   - Width: 2pt
   - Color: Layer color
   - Label: "Peak Force"

6. **Propagation End Vertical Line**
   - Style: Dotted (`':'`)
   - Width: 2pt
   - Color: Purple
   - Label: "Prop End"

7. **Baseline Horizontal Line**
   - Style: Dashed (`'--'`)
   - Width: 2pt
   - Color: Gray
   - Alpha: 0.6
   - Label: "Baseline ([value]N)"

8. **Peak Force Annotation Box**
   - **Position**: 15% to the right of peak time, centered on peak force
     - `x = peak_time + (prop_end_time - pre_init_time) × 0.15`
     - `y = peak_force`
   - **Content**: Relative force (peak - baseline) in Newtons
   - **Format**: `"X.XXXXN"` (4 decimal places)
   - **Font size**: 14pt (font_size)
   - **Font weight**: Bold
   - **Color**: Layer color
   - **Box style**: 
     - Shape: Rounded rectangle (`boxstyle='round,pad=0.3'`)
     - Background: White
     - Border: Layer color
     - Alpha: 0.9
   - **Alignment**: Left-aligned, vertically centered

**Axes**:
- **X-axis**: "Time (s)", 18pt bold
- **Y-axis**: "Force (N)", 18pt bold
- **Range X**: (pre_init_start - 1s) to (prop_end + 1s)
- **Range Y**: (baseline - 20% × force_range) to (peak + 20% × force_range)
- **Ticks**: Reduced to ~6 bins per axis
- **Grid**: Enabled, alpha 0.3

**Title**: `"Layer [number] - Pre-init: [X.XX]s | Prop: [Y.YY]s"`, 16pt bold (font_size + 2)

**Legend**:
- Location: Upper left
- Font size: 12pt (font_size - 2)
- Frame alpha: 0.9
- Columns: 2 (`ncol=2`)
- Entries: Raw Force, Smoothed Force, Pre-Initiation, Propagation, Peak Force, Prop End, Baseline

---

### Figure-Level Settings

**Size & Resolution**:
- Base width: 16 inches
- Height: 12 inches × (rows_needed / 2.0)
  - Adjusts dynamically based on number of layers
- DPI: 100 (display), 300 (export)

**Main Title**:
- Format: `"[Membrane]_[Gap]_[Tank]_[Fluid]_[Speed] - Layers X -> Y\nAverage Area: Z mm²"`
- Example: `"FEP_500um_V19_Air_400 - Layers 101 -> 105\nAverage Area: 32.54 mm²"`
- Font size: 24pt (base), scales down for multi-row plots:
  - ≤2 rows: 24pt
  - 3 rows: 22pt
  - ≥4 rows: 20pt
- Font weight: Bold
- Position: y=0.98
- **Note**: Layer range is specific to each autolog file

**Spacing**:
- `top=0.90` (leaves room for title)
- `bottom=0.08`
- `hspace=0.4` (vertical spacing)
- `wspace=0.3` (horizontal spacing)

**Color Palette** (assigned sequentially):
- Layer 1: Red
- Layer 2: Blue
- Layer 3: Green
- Layer 4: Orange
- Layer 5: Purple
- Layer 6: Brown

---

## Master Plots (Dataset Comparison)

Master plots aggregate data across multiple tests to compare conditions. Two main systems are used:

### System 1: TEMPO Picker Style (4-Subplot Layout)

**Engine**: `tempo_picker_plot_styles.py`

**Three Plot Types Generated**:

#### 1. Mean Plot (`MASTER_mean_analysis.png`)
#### 2. Median Plot (`MASTER_median_analysis.png`)
#### 3. Log-Log Plot (`MASTER_loglog_analysis.png`)

---

### Structure (All Three Types)

**Layout**: Fixed 2×2 grid (4 subplots)
```
┌────────────────┬────────────────┐
│  Peak Force    │  Work of Adh.  │
│  (normalized)  │  (mJ)          │
├────────────────┼────────────────┤
│  Peel Distance │  Peak Retract  │
│  (mm)          │  Force (N)     │
└────────────────┴────────────────┘
```

**Standard Metrics** (in order):
1. **Peak Force** (normalized to max median/mean)
   - Y-axis: "Relative Peak Force"
2. **Work of Adhesion** (mJ)
   - Y-axis: "Work of Adhesion (mJ)"
3. **Total Peel Distance** (mm)
   - Y-axis: "Total Peel Distance (mm)"
4. **Peak Retraction Force** (N)
   - Y-axis: "Peak Retraction Force (N)"

**X-Axis** (configurable):
- Default: "Layer Number"
- Alternative: "Contact Radius (mm)" or other metric

---

### Mean Plot Specifics

**Data Aggregation**:
- Group data by x-axis value (e.g., layer number)
- Calculate **mean** for each group
- Calculate **Standard Error of Mean (SEM)** for error bars
  - SEM = std / √(count)

**Visual Elements per Condition**:

1. **Shaded Error Region**
   - Fill: Mean ± SEM
   - Color: Condition color
   - Alpha: 0.2 (20% transparent)
   - Z-order: 1 (background)

2. **Data Points**
   - Symbol: Scatter points (`s=16`)
   - Color: Condition color
   - Alpha: 0.8
   - Edge: None
   - Z-order: 3 (middle)
   - **No connecting lines** between points

3. **Power Law Trendline**
   - Style: Dotted (`':'`)
   - Width: 1pt
   - Color: Condition color
   - Alpha: 0.7
   - Z-order: 2
   - Fit: `y = A × x^n` in log-log space

**Subplot Title**: Metric name (e.g., "Relative Peak Force"), 21pt bold

---

### Median Plot Specifics

**Data Aggregation**:
- Group data by x-axis value
- Calculate **median** for each group
- Calculate **Median Absolute Deviation (MAD)** for error bars
  - MAD = median(|x - median(x)|)
  - Error bars = 1.4826 × MAD / √(count)

**Visual Elements**: Same as Mean Plot, but with median values and MAD error regions

---

### Log-Log Plot Specifics

**Axes**: Both x and y on logarithmic scale

**Data Aggregation**: Same as Mean Plot (mean + SEM)

**Power Law Trendline**:
- Style: **Dashed** (`'--'`) instead of dotted
- Width: 1.5pt (thicker)
- Fit displayed more prominently

**Special Handling**:
- Filters out non-positive values before plotting
- Error bars adjusted to prevent negative values: `max(mean - sem, 1e-10)`

**Grid**: Enabled for both major and minor ticks (`which='both'`)

---

### Subplot Formatting (All Master Plots)

**Axes Labels**:
- Font size: 27pt
- Font weight: Bold
- X-axis: Variable (e.g., "Layer Number", "Contact Radius (mm)")
- Y-axis: Metric-specific

**Subplot Titles**:
- Font size: 21pt
- Font weight: Bold
- Text: Y-axis label (metric name)
- Padding: 10pt above subplot

**Legend**:
- Location: Best (auto-positioned)
- Font size: 15pt
- Font weight: Bold (for all entries)

**Grid**:
- Style: Enabled
- Alpha: 0.3
- Log-log plots: Both major and minor gridlines

**Y-Axis Range**:
- Default: Start at 0 if all values positive
- Can be overridden with `axis_ranges` parameter for consistency

---

### Figure-Level Settings (Master Plots)

**Size & Resolution**:
- Figure size: 16" × 12" (default, configurable)
- DPI: 300 (high quality)

**Main Title**:
- Mean plot: "Master Analysis (MEAN)"
- Median plot: "Master Analysis (MEDIAN)"
- Log-log plot: "Master Analysis (LOG-LOG)"
- Font size: 16pt
- Font weight: Bold
- Position: y=0.995

**Layout**:
- `tight_layout()` with `bbox_inches='tight'`

---

### Condition Color Mapping

**Fixed Color Dictionary** (`CONDITION_COLORS` in `tempo_picker_plot_styles.py`):

Ensures consistent colors across all progressive plots. Common conditions:
```python
CONDITION_COLORS = {
    'FEP_500um_V19_Air_200': '#1f77b4',      # Blue
    'FEP_500um_V19_Air_400': '#ff7f0e',      # Orange
    'FEP_500um_V19_HDODA_200': '#2ca02c',    # Green
    'FEP_500um_V19_HDODA_400': '#d62728',    # Red
    'ACF_4p8mm_V22_Air_200': '#9467bd',      # Purple
    'ACF_4p8mm_V22_Air_400': '#8c564b',      # Brown
    # ... additional conditions ...
    '[unknown condition]': '#333333'          # Dark gray fallback
}
```

**Usage**: Conditions not in dictionary use fallback gray (#333333)

---

### Data Preprocessing

**Area Binning** (before aggregation):
- Tolerance: ±10% (0.10)
- Method: `bin_areas()` function
- Purpose: Group similar contact areas to reduce noise
- Applies to: `cross_sectional_area_mm2` or `area_mm2` columns

**Peak Force Normalization** (after aggregation):
- Find maximum of all aggregated means/medians for the metric
- Divide all values by this maximum
- Result: Relative Peak Force (0 to 1.0 scale)
- **Only applies to peak force metric**, all others are absolute

**Distance Metrics**:
- Take absolute value if any negative values found
- Ensures proper visualization on log scales

---

### System 2: MasterPlotter Class (Flexible Layout)

**Engine**: `post-processing/master_plotter.py`

**Structure**: Dynamic grid based on number of metrics
- 1-3 metrics: 1×3 grid
- 4-6 metrics: 2×3 grid
- 7-9 metrics: 3×3 grid
- 10+ metrics: 3×N columns

**Features**:
- Configurable metrics list
- SEM error bars (shaded regions + error bars)
- Power law fitting
- Absolute or normalized values
- Area binning (±5% default)
- Multiple plot types:
  - `generate_area_analysis_plot()`: Peak force vs. area
  - `generate_radius_analysis_plot()`: Metrics vs. contact radius
  - `generate_absolute_force_plot()`: Non-normalized forces
  - Many more specialized plots

**Styling**: Similar to TEMPO Picker style but with more flexibility

---

## Batch Processing Workflow

### Complete Processing Pipeline

**Engine**: `batch_processors/batch_process_universal.py`

**Workflow**:
```
1. Scan master directory for test folders
   └─> Detect folders with autolog_*.csv files

2. For each test folder:
   ├─> Parse folder metadata (FolderInfo)
   │   └─> Extract: membrane, gap, tank, model, speed, fluid
   │
   ├─> Load LayerToArea.txt (global or local)
   │
   ├─> Process each autolog_*.csv file:
   │   ├─> Read raw force/time data
   │   ├─> Smooth data (Savitzky-Golay filter)
   │   ├─> Detect layers (RawDataProcessor)
   │   ├─> Calculate metrics (AdhesionMetricsCalculator)
   │   │   └─> Peak force, work of adhesion, peel distance, etc.
   │   ├─> Generate autolog plot (AnalysisPlotter)
   │   │   └─> Save to: plots/YYYYMMDD_HHMMSS/autolog_L[X]-L[Y]_analysis.png
   │   └─> Append to results DataFrame
   │
   ├─> Save combined results CSV:
   │   └─> detailed_results_[timestamp].csv
   │
   └─> Generate master plots (MasterPlotter):
       ├─> MASTER_mean_analysis.png (4 subplots)
       ├─> MASTER_median_analysis.png (4 subplots)
       └─> MASTER_loglog_analysis.png (4 subplots)

3. Save batch-level MASTER CSV:
   └─> MASTER_all_metrics.csv (all folders combined)
```

---

### Output File Organization

**Per Test Folder** (`[Condition_Folder]/`):
```
[Condition_Folder]/
├── autolog_L101-L110.csv          # Raw test data
├── autolog_L111-L120.csv
├── autolog_L121-L130.csv
├── plots/                         # Plot outputs
│   └── 20260115_141016/           # Timestamped subfolder
│       ├── autolog_L101-L110_analysis.png
│       ├── autolog_L111-L120_analysis.png
│       └── autolog_L121-L130_analysis.png
├── detailed_results_20260115_141016.csv  # All metrics for this folder
└── [Other processing files...]
```

**Master Directory** (contains all test folders):
```
SteppedConeTests/
├── V6/                            # Version grouping
│   ├── FEP_500um_V19_Air_200/    # Test folder 1
│   ├── FEP_500um_V19_Air_400/    # Test folder 2
│   ├── FEP_500um_V19_HDODA_200/  # Test folder 3
│   └── ...
├── MASTER_all_metrics.csv         # Combined results from all folders
├── LayerToArea.txt                # Global area mapping (optional)
└── master_plots/                  # Master comparison plots
    ├── MASTER_mean_analysis.png
    ├── MASTER_median_analysis.png
    └── MASTER_loglog_analysis.png
```

---

### Timestamped Subfolders

**Purpose**: Version control for iterative reprocessing

**Format**: `YYYYMMDD_HHMMSS`
- Example: `20260115_141016` = January 15, 2026, 2:10:16 PM

**Benefit**: Previous plots are preserved when reprocessing data with updated algorithms

---

## Universal Style Standards

These standards apply to **all** plot types (autolog, master, summary):

### Typography

**Font Family**: Times New Roman (all text)
```python
plt.rcParams['font.family'] = 'Times New Roman'
```

**Font Sizes** (defaults, may scale):
| Element | Size | Weight |
|---------|------|--------|
| Main title | 24pt | Bold |
| Subplot title | 16-21pt | Bold |
| Axis labels | 18-27pt | Bold |
| Axis tick labels | 18pt | Regular |
| Legend (overview) | 13-15pt | Regular |
| Legend (subplot) | 12pt | Regular |
| Annotations | 14pt | Bold |

### Resolution & Export

**DPI Settings**:
- Display/preview: 100 DPI
- Export/publication: 300 DPI

**File Format**: PNG (`.png`)

**Bounding box**: `bbox_inches='tight'` (removes excess whitespace)

### Grid & Background

**Grid**:
- Always enabled (`ax.grid(True)`)
- Alpha: 0.3 (subtle, not distracting)
- Color: Default gray

**Background**:
- Figure: White (`facecolor='white'`)
- Axes: Default (white/transparent)

### Line Widths

**Reference**:
- Raw data: 1pt
- Smoothed data: 2.5pt
- Markers/dividers: 2-3pt
- Trendlines: 1-1.5pt

### Transparency (Alpha) Values

**Reference**:
- Shaded regions (error bands): 0.2-0.3
- Shaded phases (pre-init, prop): 0.3
- Layer regions (overview): 0.08
- Lines/markers: 0.7-0.9
- Legends: 0.9

---

## File Organization

### Code Structure

**Main Application**:
- `Prince_Segmented.py` - Main GUI application

**Batch Processors**:
- `batch_processors/batch_process_universal.py` - Universal batch processor
- `batch_processors/batch_process_tempo_picker.py` - TEMPO picker datasets
- Other specialized batch processors for specific datasets

**Plotting Engines**:
- `post-processing/analysis_plotter.py` - Autolog plots (AnalysisPlotter class)
- `post-processing/master_plotter.py` - Master plots (MasterPlotter class)
- `tempo_picker_plot_styles.py` - TEMPO Picker master plots (functions)
- `post-processing/summary_plot_generator.py` - Summary plots

**Support Modules**:
- `support_modules/adhesion_metrics_calculator.py` - Calculate metrics
- `support_modules/RawData_Processor.py` - Detect layers in raw data

**Documentation**:
- `PLOT_STYLE_GUIDE.md` - Original autolog plot style guide (v2.0)
- `COMPREHENSIVE_PLOT_FORMAT_GUIDE.md` - This file
- `tempo_picker_plot_styles.py` - Contains style constants inline

---

### Style Guide Hierarchy

**This file** (`COMPREHENSIVE_PLOT_FORMAT_GUIDE.md`):
- **Scope**: Master reference for all plot types
- **Content**: Structure, elements, layout, styling
- **Use case**: Understanding system architecture, planning new plots

**PLOT_STYLE_GUIDE.md**:
- **Scope**: Autolog plots only (AnalysisPlotter)
- **Content**: Detailed styling specifications, code snippets
- **Use case**: Implementing autolog plot styling

**tempo_picker_plot_styles.py**:
- **Scope**: TEMPO Picker master plots
- **Content**: Color dictionaries, plotting functions
- **Use case**: Generating 4-subplot master plots

**master_plotter.py** (inline documentation):
- **Scope**: Flexible master plots
- **Content**: MasterPlotter class methods, parameters
- **Use case**: Custom master plot configurations

---

## Quick Reference Tables

### Plot Type Selection Guide

| Goal | Plot Type | File |
|------|-----------|------|
| Analyze individual test layers in detail | Autolog plot | `autolog_L[X]-L[Y]_analysis.png` |
| Compare peak forces across conditions | Master mean plot | `MASTER_mean_analysis.png` |
| Compare medians (robust to outliers) | Master median plot | `MASTER_median_analysis.png` |
| Identify scaling laws | Master log-log plot | `MASTER_loglog_analysis.png` |
| Custom metric comparison | MasterPlotter methods | Various outputs |

---

### Metrics Calculated & Plotted

**Standard Autolog Metrics** (per layer):
- Peak force (N) - absolute and relative to baseline
- Work of adhesion (mJ) - area under force curve
- Total peel distance (mm) - retraction distance during peel
- Pre-initiation duration (s)
- Propagation duration (s)
- Baseline force (N)
- Contact area (mm²) - from LayerToArea.txt or geometry
- Peak retraction force (N)

**Standard Master Plot Metrics** (aggregated):
- Relative peak force (normalized)
- Work of adhesion (mJ)
- Total peel distance (mm)
- Peak retraction force (N)
- [Additional metrics configurable]

---

### Color Reference

**Layer Colors** (autolog plots):
1. Red - `'red'`
2. Blue - `'blue'`
3. Green - `'green'`
4. Orange - `'orange'`
5. Purple - `'purple'`
6. Brown - `'brown'`

**Phase Colors** (autolog plots):
- Pre-initiation: Light blue (`'blue'`, alpha 0.3)
- Propagation: Light coral (`'red'`, alpha 0.3)
- Baseline: Gray dashed

**Special Markers**:
- Propagation end: Purple dotted
- Raw force: Black with low alpha
- Smoothed force: Navy (overview) or layer color (detail)

---

## Implementation Notes

### Matplotlib Backend

**Non-interactive backend** (`Agg`) is used for batch processing to prevent:
- GUI crashes on Windows during multi-threaded processing
- Memory leaks from unclosed figures
- Display window pop-ups during automation

```python
import matplotlib
matplotlib.use('Agg')
```

### Figure Management

**Always close figures** after saving to prevent memory accumulation:
```python
plt.savefig(output_path, dpi=300, bbox_inches='tight')
plt.close(fig)  # Critical!
```

### Error Handling

**Graceful degradation**:
- Missing columns → Display "Column not found" message in subplot
- Insufficient data → Skip trendline fitting
- Zero/negative values in log plots → Filter before plotting

---

## Version History

### Version 1.0 (February 25, 2026)
- Initial comprehensive format guide
- Consolidates information from:
  - `PLOT_STYLE_GUIDE.md` (v2.0)
  - `tempo_picker_plot_styles.py`
  - `analysis_plotter.py`
  - `master_plotter.py`
  - `batch_process_universal.py`
- Covers all three plot systems (autolog, TEMPO picker master, MasterPlotter)
- Includes structural layout, elements, and styling
- Documents batch processing workflow
- Provides file organization standards

---

## Related Documentation

- **PLOT_STYLE_GUIDE.md** - Detailed autolog plot styling (v2.0, Jan 2026)
- **TEMPO_PICKER_V2_SUMMARY.md** - TEMPO picker processing workflow
- **WORKSPACE_ORGANIZATION_RECOMMENDATIONS.md** - File organization plan
- **README.md** - Overall project documentation

---

**Maintained by**: Cheng Sun Lab  
**Contact**: For questions about plot formatting or modifications  
**Last Updated**: February 25, 2026

---

## Appendix: Common Questions

**Q: How many plots are generated per test?**  
A: N autolog plots (where N = number of autolog files) + 3 master plots (mean, median, log-log)

**Q: Why are there different master plot systems?**  
A: `tempo_picker_plot_styles.py` is optimized for 4-metric comparisons with fixed layout. `master_plotter.py` offers flexibility for custom metric sets and layouts.

**Q: Can I change the color scheme?**  
A: Yes, modify `CONDITION_COLORS` dict in `tempo_picker_plot_styles.py` or `self.layer_colors` in `analysis_plotter.py`

**Q: What if I have more than 6 layers in one autolog?**  
A: Colors will cycle back to red (index % 6). Consider adding more colors to the palette.

**Q: Why Times New Roman?**  
A: Professional appearance and scientific publication standards. Widely available on all systems.

**Q: How do I regenerate plots after changes?**  
A: Run the appropriate batch processor. New plots will go in a fresh timestamped subfolder, preserving old versions.

**Q: Where are plot titles generated?**  
A: Autolog titles: Constructed in batch processor from folder metadata. Master plot titles: Hardcoded in plotting functions.

**Q: What's the difference between "peak force" and "relative peak force"?**  
A: Peak force is the raw maximum force value. Relative peak force subtracts the baseline and may be normalized to the maximum value in the dataset.
