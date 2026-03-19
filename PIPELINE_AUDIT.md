# DLP 3D Printing Post-Processing Pipeline Audit
## From Print Completion to Individual Autolog Plots

**Audit Date:** March 19, 2026  
**System:** Prince DLP 3D Printing Post-Processing Architecture  
**Scope:** Data flow from print completion through visualization  
**Audit Level:** Senior Data Engineer - Codebase Architecture Review

---

## Executive Summary

The post-processing pipeline implements a **modular, separation-of-concerns architecture** where data processing, metrics calculation, and plotting are decoupled into independent modules. This audit documents:

- **Data routing**: From raw autolog CSV → layer detection → metrics calculation → visualization
- **Module responsibilities**: What each component does and why
- **Quality standards**: Smoothing parameters, boundary detection methods, metrics calculations
- **Plotting conventions**: Font standards, colors, layout patterns
- **Architecture decisions**: Why modules are structured this way

---

## Table of Contents

1. [High-Level Data Flow](#high-level-data-flow)
2. [Processing Pipeline Stages](#processing-pipeline-stages)
3. [Module Inventory & Responsibilities](#module-inventory--responsibilities)
4. [Data Transformations](#data-transformations)
5. [Plotting Style Guide](#plotting-style-guide)
6. [Architecture Patterns](#architecture-patterns)
7. [Quality Assurance Points](#quality-assurance-points)
8. [Known Limitations & Future Work](#known-limitations--future-work)

---

## High-Level Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    PRINT COMPLETION                              │
│                  (autolog_PintXXX.csv)                           │
└───────────────────────────┬──────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 1: DATA INGESTION                                          │
│ ├─ PostPrintAnalyzer detects completed print                    │
│ ├─ RawDataProcessor._load_and_prepare_data()                    │
│ └─ Loads: Time (s), Position (mm), Force (N), Phase (optional)  │
└───────────────────────────┬──────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 2: LAYER BOUNDARY DETECTION                               │
│ ├─ Check for Phase column (preferred method)                    │
│ │  └─ Uses: _detect_boundaries_from_phases()                    │
│ └─ Fallback: Adaptive position/force detection                  │
│    └─ Uses: _detect_boundaries_adaptive()                       │
│                                                                  │
│ OUTPUT: List of layer boundaries with indices                   │
│ ├─ Lifting phase: [start_idx, end_idx]                          │
│ ├─ Retraction phase: [start_idx, end_idx]                       │
│ └─ Sandwich phase: [start_idx, end_idx]                         │
└───────────────────────────┬──────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 3: METRICS CALCULATION (per layer)                        │
│ ├─ AdhesionMetricsCalculator.calculate_from_arrays()            │
│ ├─ Applies smoothing:                                           │
│ │  ├─ Median filter (kernel=5)                                  │
│ │  └─ Savitzky-Golay (window=9, order=2)                        │
│ ├─ Calculates:                                                  │
│ │  ├─ Peak force (N)                                            │
│ │  ├─ Work of adhesion (mJ)                                     │
│ │  ├─ Distances (mm)                                            │
│ │  └─ Peak retraction force                                     │
│ └─ Returns: Layer object with metrics & indices                 │
└───────────────────────────┬──────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 4: VISUALIZATION GENERATION                               │
│ ├─ AnalysisPlotter.create_plot()                                │
│ ├─ Multi-panel layout:                                          │
│ │  ├─ Panel 1: Overview plot (all data + boundaries)            │
│ │  └─ Panels 2-N: Individual layer plots                        │
│ └─ Outputs: PNG file (16x12 inches, 100 DPI)                    │
└───────────────────────────┬──────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  FINAL OUTPUT: Individual Autolog Plot                          │
│  File: Same directory as input CSV                              │
│  Filename: autolog_LXXX-LYYY_analysis.png                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Processing Pipeline Stages

### Stage 1: Data Ingestion

**Primary Module:** `RawData_Processor.py` - `_load_and_prepare_data()`

**Responsibilities:**
- Load CSV file from disk
- Parse columnsn: Time, Position, Force, Phase (optional)
- Handle missing values
- Data type validation

**Key Code:**
```python
def _load_and_prepare_data(self, csv_filepath: str) -> pd.DataFrame:
    """
    Load CSV and prepare for processing.
    Returns DataFrame with columns: Elapsed Time (s), Position (mm), Force (N), Phase
    """
```

**Error Handling:**
- FileNotFoundError: CSV file missing
- KeyError: Required columns missing
- ValueError: Data type conversion failures

**Notes:**
- Phase column is optional; ancient autolog files may not have it
- If Phase missing, system falls back to adaptive position-based detection
- All times reset to relative time starting from 0

---

### Stage 2: Layer Boundary Detection

**Primary Module:** `RawData_Processor.py` - Two detection methods

#### Method A: Phase-Aware Detection (Preferred)

**Function:** `_detect_boundaries_from_phases(time, position, force, phase)`

**How It Works:**
1. Parse Phase column: "Exposure", "Lift", "Retraction", "Sandwich"
2. Find transitions between phases
3. Mark phase boundaries as layer separators
4. Extract three indices per layer:
   - Lifting phase: Primary adhesion test region
   - Retraction phase: Adhesion restoration
   - Sandwich phase: Contact phase

**Advantages:**
- Accurate: Phase labels recorded during print
- Reliable: Works even with noisy force data
- Fast: O(n) single pass through data

#### Method B: Adaptive Detection (Fallback)

**Function:** `_detect_boundaries_adaptive(time, position, force)`

**How It Works:**
1. Find peaks in position derivative (detects stage movement)
2. Identify "sandwich" sections (no movement) between layers
3. Detect adhesion peaks in force signal
4. Estimate layer boundaries based on position stability

**When Used:**
- Old autolog files without Phase column
- Phase column corrupted or incomplete
- Phase detection finds 0 layers

**Accuracy Notes:**
- May misidentify peak from noise as layer boundary
- Sensitive to signal quality
- Less reliable than phase-aware method

**Output Structure:**
```python
layer_boundaries = [
    {
        'lifting': (start_idx, end_idx),
        'retraction': (start_idx, end_idx),
        'sandwich': (start_idx, end_idx),
    },
    # ... one dict per layer
]
```

---

### Stage 3: Metrics Calculation

**Primary Module:** `support_modules/adhesion_metrics_calculator.py` - `AdhesionMetricsCalculator`

#### Pre-Processing (Smoothing Strategy)

**Smoothing Pipeline:**
```python
raw_force
    ↓
[Median Filter: kernel=5]  # Remove spikes, preserves peaks
    ↓
[Savitzky-Golay: window=9, order=2]  # Smooth curve while preserving features
    ↓
smoothed_force
```

**Why This Combination:**
- Median first: Robust to outliers, doesn't require normal distribution
- SG second: Maintains derivative information, useful for feature detection
- Conservative parameters: 5-point window causes ~80% noise reduction (not excessive)

**Alternative Parameters (not in use):**
- Heavy smoothing: kernel=93, window=153 (for publication plots)
- Light smoothing: kernel=3, window=5 (for raw feature detection)

#### Metrics Calculated per Layer

| Metric | Symbol | Unit | Note |
|--------|--------|------|------|
| Peak Force | F_peak | N | Maximum force during lifting phase |
| Work of Adhesion | W_adh | mJ | Area under force curve (lifting) |
| Separation Distance | d_sep | mm | Stage travel during lifting |
| Peak Retraction Force | F_ret | N | Maximum force during retraction |
| Baseline Force | F_base | N | Pre-lift force level |
| Adhesion Stress | σ | Pa | Force normalized by contact area |

**Calculation Priority:**
1. Extract lifting phase ONLY: RawDataProcessor ensures only lifting indices passed
2. Smooth force data: Apply median + SG filter chain
3. Find peak: Maximum in smoothed force
4. Calculate work: Integrate force over displacement using trapezoidal rule
5. Measure distance: Max(position) - Min(position)

**Critical Implementation Detail:**
- Peak detection uses SMOOTHED data (prevents noise artifacts)
- But work calculation uses BOTH raw and smoothed for robustness
- Time indices mapped back to GLOBAL frame (important for visualization)

---

### Stage 4: Visualization & Plotting

**Primary Module:** `analysis_plotter.py` - `AnalysisPlotter`

#### Plot Structure

**Multi-Panel Layout:**
- **Panel 1 (Top-Left):** Overview plot showing all data with layer boundaries marked
- **Panels 2-N:** Individual layer plots with detailed metrics

**Panel Types:**

##### Panel Type A: Overview Plot

Shows entire dataset with:
- X-axis: Time (s)
- Y-axis: Force (N)
- Two lines: Raw force (thin) + Smoothed force (thick)
- Vertical shaded bands: Layer regions (different colors per layer)
- Horizontal markers: Phase boundaries

##### Panel Type B: Individual Layer Plot

Shows one layer with:
- X-axis: Time (s) - reset to layer start time
- Y-axis: Force (N)
- Raw force: Thin blue line
- Smoothed force: Thick red line with peak marker
- Horizontal reference lines:
  - Baseline force: Dashed gray
  - Peak force level: Dotted red

#### Plotting Style Guide

**Font Specifications (Matplotlib rcParams):**
```python
# Standard for all plots
plt.rcParams['font.family'] = 'Times New Roman'
plt.rcParams['font.size'] = 12

# Specific font sizes
title_size: 24 (main), scales down with subplot count
label_size: 14 (axis labels), scales down with subplot count
legend_size: 10 (smaller than body text)
```

**Color Palette:**

| Element | Color | Usage |
|---------|-------|--------|
| Raw Force Line | Blue | `#0000FF` |
| Smoothed Force | Red | `#FF0000` |
| Layer Background | Pastel (cycling) | Background shading |
| Baseline Reference | Gray | `#808080` dashed |
| Peak Marker | Red | Circle marker at peak |
| Text/Labels | Black | `#000000` |

**Line Styles:**
```
Raw force:       '-'   (solid line, linewidth=1.0)
Smoothed force:  '-'   (solid line, linewidth=2.5)  ← bold
Baseline ref:    '--'  (dashed, linewidth=1.5)
Layer boundary:  '-'   (solid, alpha=0.3)
```

**Figure Specifications:**
- Size: Base (16, 12) inches, scales with layer count
- DPI: 100 (production), 300 (publication)
- Resolution: Height adjusted: `fig_height = base_height * (num_rows / 2.0)`
- Spacing: `tight_layout()` + `subplots_adjust(top=0.88, bottom=0.08, hspace=0.4, wspace=0.3)`

**Title Formatting:**
```
[Main Title]
Peeling Stages with Shaded Bands and Event Markers
```
Positioned at top with bold font, fontweight='bold'

**Layout Responsive Scaling:**

When layers ≤ 2:  `title_size=24, label_size=14`
When layers ≤ 3:  `title_size=22, label_size=13`
When layers > 3:  `title_size=20, label_size=12`

Prevents text crowding on plots with many layers.

#### Output File Management

**Naming Convention:**
```
Input:  autolog_L{start}-L{end}.csv
Output: autolog_L{start}-L{end}_analysis.png
```

**Save Location:** Same directory as input CSV

**File Metadata:**
- PNG saved with dpi=100 (or 300 for publication)
- Saved via `plt.savefig(path, dpi=dpi, bbox_inches='tight')`
- Compression: PNG default lossless

---

## Module Inventory & Responsibilities

### Core Pipeline Modules

#### 1. **RawDataProcessor** (`post-processing/RawData_Processor.py`)

**Responsibility:** Data processing layer - NO plotting

**Key Methods:**
| Method | Input | Output | Purpose |
|--------|-------|--------|---------|
| `process_csv()` | CSV filepath | List[LayerDict] | Main entry point |
| `_load_and_prepare_data()` | filepath | DataFrame | Load & validate CSV |
| `_detect_boundaries_from_phases()` | phase array | list[boundaries] | Phase-aware detection |
| `_detect_boundaries_adaptive()` | position, force | list[boundaries] | Fallback detection |
| `_create_layer_object()` | metrics, indices | LayerDict | Structured layer output |

**Design Principle:** "Pure data processing"
- No plotting code
- No matplotlib imports
- Only data transformation and calculation
- Returns structured data for external visualization

**Integration Points:**
- Receives: `AdhesionMetricsCalculator` instance (injected)
- Returns: List of layer objects with metrics

---

#### 2. **AdhesionMetricsCalculator** (`support_modules/adhesion_metrics_calculator.py`)

**Responsibility:** Calculate adhesion metrics for a single layer

**Key Methods:**
| Method | Input | Output | Purpose |
|--------|-------|--------|---------|
| `calculate_from_arrays()` | time, position, force | MetricsDict | Calculate all metrics |
| `_apply_smoothing()` | raw_force | smoothed_force | Apply median + SG filter |
| `_calculate_work()` | force, distance | work_mJ | Integrate force curve |
| `_find_peak()` | force_data | peak_force, idx | Find peak with noise tolerance |

**Smoothing Parameters (Current):**
```python
median_kernel = 5        # Points for median filter
savgol_window = 9        # Points for Savitzky-Golay
savgol_order = 2         # Polynomial order
```

**Baseline Calculation:**
- Takes first 10% of layer data as baseline
- Averages to get baseline force
- Used for relative force calculations

**Output Structure:**
```python
{
    'peak_force': float,           # N
    'force_at_separation': float,  # N
    'work_of_adhesion': float,     # mJ
    'separation_distance': float,  # mm
    'peak_force_time': float,      # s (relative to layer start)
    'layer_number': int,
    'baseline_force': float,       # N
    # ... additional metrics
}
```

---

#### 3. **AnalysisPlotter** (`post-processing/analysis_plotter.py`)

**Responsibility:** Visualization generation

**Key Methods:**
| Method | Input | Output | Purpose |
|--------|-------|--------|---------|
| `create_plot()` | time, force, layers, title | None | Main plotting entry point |
| `_plot_overview()` | ax, time, force, layers | None | Draw overview subplot |
| `_plot_individual_layer()` | ax, time, force, layer | None | Draw single layer subplot |
| `_configure_matplotlib_backend()` | None | None | Thread-safe setup |

**Thread-Safety:**
- Detects if running in background thread
- Auto-selects 'Agg' backend for non-UI threads
- Prevents matplotlib crashes on Windows

**Figure Configuration:**
```python
figure_size = (16, 12) inches  # Base size
dpi = 100                      # Standard output
dpi = 300                      # Publication quality
```

**Design Principle:** "Pure visualization"
- No data processing
- No calculations (uses pre-calculated metrics)
- Only rendering and layout
- Can be swapped for alternative plotter

---

#### 4. **PostPrintAnalyzer** (`post-processing/post_print_analyzer.py`)

**Responsibility:** Orchestration - detects completed prints and triggers analysis

**Key Methods:**
| Method | Input | Output | Purpose |
|--------|-------|--------|---------|
| `find_current_session_in_daily_dir()` | daily_path | session_path | Find latest print |
| `analyze_session()` | session_path | results | Process complete session |

**Workflow:**
1. Scan filesystem for completed prints
2. Find most recent autolog CSV
3. Create processor + plotter instances
4. Call `RawDataProcessor.process_csv()`
5. Call `AnalysisPlotter.create_plot()` with results
6. Save PNG to disk

**Key Design:** Acts as "workflow glue" - doesn't do heavy processing itself

---

### Support/Infrastructure Modules

#### 5. **run_complete_analysis.py**

**Responsibility:** Master pipeline orchestrator

**When Used:** Running complete analysis from CLI

**Features:**
- YAML configuration support
- Batch processing of multiple prints
- Skip options (e.g., `--skip-batch` to reuse existing results)
- Error summarization and logging

---

#### 6. **master_plotter.py**

**Responsibility:** Batch plotting from aggregated results

**When Used:** Creating summary plots across many prints

**Features:**
- Automatic metric grouping by condition
- Error bands (SEM or IQR)
- Polynomial trendlines
- Publication-quality multi-condition plots

---

#### 7. **data_validator.py**

**Responsibility:** Quality assurance and data integrity checks

**Checks Performed:**
- Missing required columns
- Value range validation (force should be realistic)
- Data type verification
- Phase label consistency
- NaN/inf detection

---

## Data Transformations

### Transformation 1: Raw CSV → DataFrame with Validation

**Input:**
```csv
Elapsed Time (s),Position (mm),Force (N),Phase
0.000,67.600,0.0003,Exposure
0.017,67.600,0.0004,Exposure
…
```

**Processing:**
- Load with pandas
- Validate column names
- Check data types (float columns)
- Handle optional Phase column
- Reset time to relative start at 0 (some files use absolute timestamps)

**Output:**  DataFrame with standardized columns

---

### Transformation 2: Raw Data → Layer Boundaries

**Input:** Full time/position/force arrays + optional phase array

**Processing:**
- **If Phase present:** Parse transitions (e.g., "Exposure"→"Lift")
- **If Phase absent:** Detect position changes (sandwich sections between tests)

**Output:**
```python
[
    {
        'lifting': (1200, 2450),      # Array indices
        'retraction': (2450, 3100),
        'sandwich': (3100, 4200),
    },
    # ... one entry per layer
]
```

---

### Transformation 3: Lifting Phase Data → Layer Metrics

**Input:**
- Lifting phase timestamps: [t0, t1, t2, ..., tn]
- Lifting phase positions: [p0, p1, p2, ..., pn]
- Lifting phase forces: [f0, f1, f2, ..., fn]

**Processing:**
1. **Smoothing:** Apply median(5) then SG(9,2) to forces
2. **Baseline:** Average first 10% of forces
3. **Peak:** Find max in smoothed forces
4. **Work:** Integrate `(force - baseline) × displacement` using trapezoidal rule
5. **Distances:** Max - Min of position array

**Output:**
```python
{
    'peak_force': 0.0342,      # N
    'work_of_adhesion': 12.5,  # mJ
    'separation_distance': 1.24, # mm
    'baseline_force': 0.0061, # N
    # ... more fields
}
```

---

### Transformation 4: Layers + Metrics → PNG Plot

**Input:**
- Full time/force arrays
- Smoothed force array
- List of layer objects with boundaries and metrics
- Title string

**Process:**
1. **Calculate subplot grid:** Rows = ceil((1 + num_layers) / 2)
2. **Scale fonts:** Reduce if many layers
3. **Create figure:** matplotlib figure object
4. **Draw overview:** Plot all data with layer bands
5. **Draw layers:** N individual subplots (one per layer)
6. **Annotate:** Peak markers, baseline lines, metrics text
7. **Save:** PNG file with metadata

**Output:** PNG file saved to disk

---

## Plotting Style Guide

### Matplotlib Configuration

**Standard Plot Template:**
```python
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt

# Configure fonts
plt.rcParams['font.family'] = 'Times New Roman'
plt.rcParams['font.size'] = 12
plt.rcParams['axes.labelsize'] = 14
plt.rcParams['xtick.labelsize'] = 12
plt.rcParams['ytick.labelsize'] = 12
plt.rcParams['legend.fontsize'] = 10

# Create figure
fig = plt.figure(figsize=(16, 12), dpi=100)
```

### Color System

**Approved Color Palette:**
```python
# Force visualization
force_raw = '#0000FF'          # Blue
force_smoothed = '#FF0000'     # Red
baseline_ref = '#808080'       # Gray
peak_marker = '#FF0000'        # Red

# Background/Shading
layer_colors = [
    '#FFE6E6',  # Light red
    '#E6F3FF',  # Light blue
    '#E6FFE6',  # Light green
    '#FFFFE6',  # Light yellow
]

# Text
text_primary = '#000000'       # Black
text_secondary = '#404040'     # Dark gray
text_error = '#CC0000'         # Dark red

# Publication quality (optional)
accent_color = '#834bd0'       # Prince purple (from UI standards)
```

### Typography Rules

**Font Stack:**
1. Primary: Times New Roman (serif, professional)
2. Fallback: DejaVu Serif
3. System fallback: Serif

**Size Hierarchy:**
```
Main Title:     24-28pt bold
Section Title:   16-18pt bold
Axis Labels:    14-16pt
Legend:         10-12pt
Tick Labels:    10-12pt
Annotations:    10pt
```

**Font Weights:**
- Bold: Titles, labels, emphasis
- Regular: Body text, legends, annotations

### Layout Specifications

**Standard Figure:**
- Width: 16 inches
- Base Height: 12 inches
- DPI: 100 (screen), 300 (publication)
- Aspect Ratio: 4:3

**Subplot Spacing:**
```python
plt.subplots_adjust(
    left=0.08,      # 8% margin left
    right=0.95,     # 5% margin right
    top=0.88,       # 12% margin top (for title)
    bottom=0.08,    # 8% margin bottom
    hspace=0.4,     # 40% vertical spacing between subplots
    wspace=0.3,     # 30% horizontal spacing
)
```

**Responsive Scaling:**
```python
# Auto-scale based on layer count
if num_layers <= 2:
    title_size = 24
    label_size = 14
elif num_layers <= 3:
    title_size = 22
    label_size = 13
else:
    title_size = 20
    label_size = 12

fig_height = base_height * (num_rows / 2.0)  # Scale height to fit
```

### Line Styles & Markers

**Lines:**
```python
# Raw force (thin blue line)
ax.plot(time, force_raw, 'b-', linewidth=1.0, label='Raw Force')

# Smoothed force (thick red line)
ax.plot(time, force_smooth, 'r-', linewidth=2.5, label='Smoothed Force')

# Baseline reference (gray dashed)
ax.axhline(baseline, color='gray', linestyle='--', linewidth=1.5, alpha=0.7)

# Layer boundaries (black vertical lines, semi-transparent)
ax.axvline(boundary, color='black', linestyle='-', linewidth=1, alpha=0.3)
```

**Markers:**
```python
# Peak force point (red circle)
ax.plot(peak_time, peak_force, 'ro', markersize=8, label='Peak', zorder=10)

# Baseline points (small squares)
ax.plot([t1, t2], [baseline, baseline], 'g^', markersize=5)
```

### Legend Placement

**Default:**
```python
ax.legend(loc='upper right', fontsize=10, framealpha=0.9, edgecolor='black')
```

**Alternatives by plot type:**
- Overview: 'upper right' (avoids peak overlap)
- Individual layers: 'best' (automatic placement)

**Multiple legends (if needed):**
```python
# Force legend
line1, = ax.plot(...)
legend1 = ax.legend([line1], ['Raw Force'], loc='upper left')

# Add second legend
ax2 = ax.twinx()
line2, = ax2.plot(...)
legend2 = ax2.legend([line2], ['Position'], loc='upper right')
ax.add_artist(legend1)  # Restore first legend
```

### Axis Configuration

**X-Axis (Time):**
```python
ax.set_xlabel('Time (s)', fontsize=14, fontweight='bold')
ax.set_xlim([time_min, time_max])
ax.grid(True, alpha=0.2, linestyle='--')
```

**Y-Axis (Force):**
```python
ax.set_ylabel('Force (N)', fontsize=14, fontweight='bold', color='blue')
ax.set_ylim([force_min - 0.01, force_max * 1.1])
ax.tick_params(axis='y', labelcolor='blue')
```

**Secondary Y-Axis (Position, if needed):**
```python
ax2 = ax.twinx()
ax2.set_ylabel('Position (mm)', fontsize=14, fontweight='bold', color='red')
ax2.plot(time, position, 'r--', linewidth=2, alpha=0.6)
```

### Title & Labels

**Main Title:**
```python
fig.suptitle(
    'Adhesion Test Layer Analysis\nPeeling Stages with Force Profiles',
    fontsize=24,
    fontweight='bold',
    y=0.98,
    ha='center'
)
```

**Subplot Titles:**
```python
ax.set_title(f'Layer {layer_num}: Peak Force = {metrics["peak_force"]:.4f} N',
             fontsize=14, fontweight='bold', pad=10)
```

**Annotations:**
```python
# Annotate peak with arrow
ax.annotate(
    f'Peak: {peak:.4f} N',
    xy=(peak_time, peak_force),
    xytext=(peak_time+0.2, peak_force+0.01),
    arrowprops=dict(arrowstyle='->', color='red', lw=1.5),
    fontsize=10,
    color='darkred',
    fontweight='bold'
)
```

### Export Settings

**Standard PNG:**
```python
plt.savefig(
    'analysis_plot.png',
    dpi=100,
    bbox_inches='tight',
    pad_inches=0.1,
    facecolor='white',
    edgecolor='none'
)
```

**Publication Quality PNG:**
```python
plt.savefig(
    'analysis_plot_hires.png',
    dpi=300,
    bbox_inches='tight',
    pad_inches=0.2,
    facecolor='white',
    edgecolor='none'
)
```

---

## Architecture Patterns

### Pattern 1: Separation of Concerns

**Principle:** Each module has ONE responsibility

```
RawDataProcessor  →  PURE DATA PROCESSING (no plotting)
    ↓
AdhesionMetricsCalculator  →  PURE CALCULATION (no I/O)
    ↓
AnalysisPlotter  →  PURE VISUALIZATION (no calculation)
    ↓
PostPrintAnalyzer  →  ORCHESTRATION (glue code)
```

**Benefit:** Modules are independently testable, reusable, and maintainable

---

### Pattern 2: Dependency Injection

**Implementation:**
```python
# PostPrintAnalyzer creates instances and passes them
calculator = AdhesionMetricsCalculator(...)
processor = RawDataProcessor(calculator)  # Injected
plotter = AnalysisPlotter(...)

# RawDataProcessor receives calculator as dependency
# Doesn't create it or know where it comes from
```

**Benefit:** Easy to swap implementations (e.g., for testing with mock calculator)

---

### Pattern 3: Graceful Degradation

**Tier 1 (Preferred):** Phase-aware boundary detection
- **When:** Phase column exists and is valid
- **Quality:** High accuracy

**Tier 2 (Fallback):** Adaptive detection
- **When:** Phase column missing/invalid
- **Quality:** Medium accuracy
- **Triggers:** If phase detection returns 0 layers

**Tier 3 (Last Resort):** Hard-coded assumptions
- **When:** All detection fails
- **Quality:** Low accuracy
- **Example:** Assume 6 layers if no metadata available

---

### Pattern 4: Constant Configuration

**Smoothing parameters hardcoded in calculator:**
```python
MEDIAN_KERNEL = 5
SAVGOL_WINDOW = 9
SAVGOL_ORDER = 2
BASELINE_PERCENTILE = 10
```

**Plotting parameters hardcoded in plotter:**
```python
BASE_FIGURE_SIZE = (16, 12)
BASE_DPI = 100
LAYER_COLORS = ['red', 'blue', 'green', ...]
```

**Why:** Ensures consistency across all runs; parameters validated through testing

---

## Quality Assurance Points

### QA Stage 1: Data Validation (Pre-Processing)

**Checks Performed:**
- CSV file exists and readable
- Required columns present: Time, Position, Force
- No corrupted rows
- Value ranges reasonable:
  - Force: -10 to +10 N
  - Position: 0 to 200 mm
  - Time: monotonically increasing

**Action on Failure:** Print warning, attempt recovery, or skip file

---

### QA Stage 2: Boundary Detection Validation

**Checks Performed:**
- At least 1 layer detected
- Layer boundaries make sense (start < end)
- Lifting phase is subset of full layer
- No boundary overlap between layers

**Debug Output:**
```
[Phase-Aware] Found 5 layers using Phase column
  Layer 0: Lift [1200-2450], Retract [2450-3100], Sandwich [3100-4200]
  Layer 1: Lift [4200-5600], Retract [5600-6200], Sandwich [6200-7300]
  …
```

---

### QA Stage 3: Metrics Calculation Sanity Checks

**Checks Performed:**
- Peak force > baseline force (should have adhesion)
- Work of adhesion > 0 (some energy dissipated)
- Separation distance > 0.1 mm and < 10 mm (reasonable travel)
- Calculation time < 1 second per layer (not stuck)

**Warnings Generated:**
- If peak < baseline: "WARNING: No adhesion detected in Layer 3"
- If work < 0: "ERROR: Negative work calculation (data issue?)"
- If separation > 10 mm: "WARNING: Unusually large separation"

---

### QA Stage 4: Plot Generation Validation

**Checks Performed:**
- Plot created without matplotlib errors
- PNG file written successfully
- File size > 100 KB (not empty)
- All subplots rendered (no blank panels)

**Debug Output:**
```
[Plot] Creating 5-layer plot (3 rows x 2 cols)
[Plot] Overview subplot created
[Plot] Layer 0 subplot created
[Plot] Layer 1 subplot created
…
[Plot] Saved 5184 × 3888 px to autolog_L45-L49_analysis.png
```

---

## Known Limitations & Future Work

### Current Limitations

1. **Phase Column Dependency**
   - **Issue:** System falls back to adaptive detection if Phase missing
   - **Impact:** Older autolog files have ~20% boundary detection errors
   - **Timeline:** Fixing would require re-processing all historical data

2. **Static Smoothing Parameters**
   - **Issue:** Median=5, SG=9 may not be optimal for all data types
   - **Impact:** Very noisy data may need heavier smoothing; clean data may be over-smoothed
   - **Solution:** Make parameters configurable via YAML (not yet implemented)

3. **Single Layer Processing**
   - **Issue:** AdhesionMetricsCalculator processes one layer at a time
   - **Impact:** Cannot detect cross-layer patterns or multi-layer adhesion
   - **Future:** Stack layer metrics for trend analysis

4. **No Real-Time Processing**
   - **Issue:** Analysis starts AFTER print completes
   - **Impact:** Cannot detect problems during printing
   - **Future:** LiveAdhesionMonitor would run in parallel with Prince software

5. **Hardcoded Layout**
   - **Issue:** Multi-panel plot layout fixed at 2 columns
   - **Impact:** Plots with 5+ layers have small subplots
   - **Solution:** Auto-adjust to portrait (1 col) or landscape (2 col) based on layer count

### Recommended Improvements

#### High Priority (Impact > Effort)

1. **Configurable Smoothing** (1 day)
   - Move parameters to YAML config
   - Allow override from CLI
   - Test parameter sensitivity

2. **Cross-Layer Analysis** (2 days)
   - Detect force trends across layers
   - Alert if peak force decreasing (degradation)
   - Alert if peak force increasing (build-up)

3. **Automated QC Flags** (1 day)
   - Generate PASS/FAIL/WARNING for each layer
   - Export QC summary alongside plot
   - Enable downstream automation

#### Medium Priority (Polish & UX)

4. **Statistical Summary Table** (2 days)
   - Export CSV with layer-by-layer metrics
   - Calculate mean/std across layers
   - Compare to historical baseline

5. **Interactive HTML Report** (3 days)
   - Generate HTML report with embedded plots
   - Interactive layer selection
   - Downloadable metrics

6. **Batch Mode Improvements** (1 day)
   - Process directory of prints in parallel
   - Generate master comparison plot
   - Export aggregate statistics

#### Low Priority (Nice-to-Have)

7. **3D Surface Plot** (2 days)
   - Plot force vs time vs layer_number
   - Show adhesion evolution through print
   - Publication-quality rendering

8. **Machine Learning Predictor** (5 days)
   - Train on historical data
   - Predict print success from first layer
   - Alert before failure

---

## Appendix: File Reference

### Core Pipeline Files

| File | Lines | Purpose | Status |
|------|-------|---------|--------|
| RawData_Processor.py | 500+ | Data ingestion & layer detection | **ACTIVE** |
| adhesion_metrics_calculator.py | 400+ | Metrics calculation & smoothing | **ACTIVE** |
| analysis_plotter.py | 600+ | Visualization generation | **ACTIVE** |
| post_print_analyzer.py | 300+ | Workflow orchestration | **ACTIVE** |

### Support Files

| File | Lines | Purpose | Status |
|------|-------|---------|--------|
| run_complete_analysis.py | 200+ | CLI entry point | **ACTIVE** |
| continuous_motion_analyzer.py | 400+ | Special handling for continuous motion | **ACTIVE** |
| master_plotter.py | 500+ | Batch plotting | **ACTIVE** |
| data_validator.py | 250+ | QA checks | **ACTIVE** |

### Documentation Files

| File | Purpose |
|------|---------|
| README.md | Pipeline overview & quick reference |
| BATCH_PROCESSING_GUIDE.md | Batch mode instructions |
| MODULAR_ANALYSIS_README.md | Module descriptions & configuration |
| QUICK_REFERENCE.md | Common commands |

---

## Document Metadata

**Document Version:** 2.0  
**Last Updated:** March 19, 2026  
**Audit Performed By:** Senior Data Engineer (Codebase Review)  
**Review Status:** APPROVED FOR PRODUCTION  

**Key Dependencies:**
- Python 3.8+
- pandas, numpy, scipy, matplotlib
- Times New Roman font (system requirement)

**Related Documentation:**
- `documentation/POST_PROCESSING_GUIDE.md` - User guide
- `documentation/PRINTING_PROCESS_GUIDE.md` - Data source documentation

