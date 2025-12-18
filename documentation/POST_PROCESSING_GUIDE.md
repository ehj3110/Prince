# Post-Processing Analysis Guide

**Complete guide for analyzing printing data after completion**

Last Updated: December 18, 2025

---

## Table of Contents

1. [Post-Processing Overview](#post-processing-overview)
2. [Immediate Post-Print Analysis](#immediate-post-print-analysis)
3. [Batch Processing System](#batch-processing-system)
4. [RawData Processor](#rawdata-processor)
5. [Analysis Tools](#analysis-tools)
6. [Advanced Metrics](#advanced-metrics)
7. [Statistical Analysis](#statistical-analysis)
8. [Visualization Tools](#visualization-tools)
9. [Common Workflows](#common-workflows)
10. [Troubleshooting](#troubleshooting)

---

## Post-Processing Overview

### What is Post-Processing?

Post-processing analyzes the CSV data files generated during printing to:
- Extract adhesion metrics per layer
- Detect layer boundaries automatically
- Generate comprehensive plots
- Compare multiple test conditions
- Perform statistical analysis
- Create reports and summaries

### Data Flow

```
PRINTING GENERATES:
├── sensor_log.csv          (Full print, all layers)
├── autolog_LXX-LYY.csv     (Layer ranges of interest)
└── peak_force_output.csv   (Real-time metrics)

          ↓ POST-PROCESSING ↓

ANALYSIS PRODUCES:
├── Individual layer plots   (Force-distance curves with annotations)
├── MASTER CSV files        (Combined metrics across tests)
├── Master plots            (Comparison across conditions)
├── Statistical reports     (ANOVA, t-tests, effect sizes)
└── Analysis reports        (PDF summaries)
```

### Two Analysis Modes

**1. Immediate Post-Print (Single File)**
- Analyzes one CSV file immediately after print
- Quick quality check
- Individual layer plots
- Used during printing for validation

**2. Batch Processing (Multiple Tests)**
- Processes entire experimental campaign
- Compares across conditions
- Statistical analysis
- Master plots and reports
- Used for publication/reporting

---

## Immediate Post-Print Analysis

### Purpose

Quick analysis right after print completes to:
- Verify data quality
- Check for anomalies
- View detailed force curves
- Confirm expected behavior

### Tool: post_print_analyzer.py

**Location:** `post-processing/post_print_analyzer.py`

**Usage:**

```powershell
# Analyze most recent print automatically
python post_print_analyzer.py

# Analyze specific daily directory
python post_print_analyzer.py --daily-dir "PrintingLogs/2025-12-18"

# Analyze specific CSV file
python post_print_analyzer.py --csv-file "PrintingLogs/2025-12-18/Print 1/autolog_L48-L50.csv"
```

### What It Does

```
1. Finds most recent autolog CSV file(s)
   ↓
2. Loads time, position, force, phase data
   ↓
3. Detects layer boundaries
   ↓
4. For each layer:
   - Extracts lifting phase data
   - Calculates adhesion metrics
   - Identifies peak force
   ↓
5. Generates plot with all layers
   ↓
6. Saves to plots/ subdirectory
```

### Output Example

**Console:**
```
Scanning for current session in: PrintingLogs
Current session: 2025-12-18/Print 1 (3 CSV files)

Processing: autolog_L48-L50.csv
Using phase-aware boundary detection (Phase column found)

--- Analyzing Layer 48 ---
    Lifting phase: 2345-2890
    Retraction phase: 2891-3234
    Sandwich phase: 3235-3456
  -> Metrics calculated successfully for Layer 48.
     Peak adhesion force: 0.2340 N (in lifting phase)
     Peak retraction force: 0.0120 N (at end of retraction)

[Similar for layers 49, 50...]

Plot saved: PrintingLogs/2025-12-18/Print 1/plots/plots_20251218_143022/autolog_L48-L50_analysis.png
```

**Plot Features:**
- Time-series: Force and position vs time
- Phase shading: Color-coded phases (Lift, Retract, Sandwich, Pause)
- Annotations: Peak force, work of adhesion, distances
- Baseline detection shown
- Smoothed force curve overlaid

---

## Batch Processing System

### Purpose

Process multiple test conditions simultaneously to:
- Compare different materials
- Test parameter effects
- Generate master comparison plots
- Perform statistical analysis

### Universal Batch Processor

**The Problem:** Previously needed separate scripts for each data version (V4, V5, V6...)

**The Solution:** One universal processor handles ANY folder structure

**Tool:** `batch_process_steppedcone_generalized.py` or universal processor

### Quick Start - Universal Processor

```powershell
cd post-processing

# Process any folder version
python process_folder.py V6
python process_folder.py V5
python process_folder.py "C:\custom\path\to\data"
```

**That's it!** No configuration needed.

### What Gets Detected Automatically

**From Folder Names:**
```
100umPDMS_1mm_V22p1_BPAGDA_Cone_1000
    ↓
Membrane: 100um PDMS
Gap: 1mm
Tank: V22p1
Resin: BPAGDA
Model: Cone
Speed: 1000 µm/s
```

**Recognized Patterns:**
- **Membranes:** PDMS, ACF, TEMPO, Flat PDMS, USW (Unsealed Water)
- **Thicknesses:** 100um, 1mm, 2.5mm, 5mm
- **Tanks:** V19, V22, V22p1, V22p2, V22p3
- **Models:** Cone, Pyramid, Cylinder
- **Resins:** BPAGDA, IBOA, HDDA
- **Speeds:** Any numeric value (µm/s)

### Batch Processing Workflow

```
1. SCAN FOLDERS
   └── Find all subfolders with autolog CSV files
   
2. PROCESS EACH FOLDER
   ├── Parse folder name → extract metadata
   ├── Load all autolog_*.csv files
   ├── Detect layer boundaries (phase-aware or adaptive)
   ├── Calculate metrics per layer
   ├── Generate individual plots
   └── Collect results
   
3. COMBINE RESULTS
   ├── Create MASTER_all_metrics.csv
   ├── Group by conditions
   └── Calculate statistics (mean, SEM, median, IQR)
   
4. GENERATE MASTER PLOTS
   ├── MASTER_area_analysis.png
   ├── MASTER_area_ratio_analysis.png
   ├── MASTER_distance_analysis.png
   └── Speed/area comparisons with error bars
```

### Master Plot Features

**Consistent Formatting (No More Manual Reformatting!):**
- ✅ Area binning (±5% tolerance) - groups similar measurements
- ✅ Error regions (filled bands) - shows SEM or IQR
- ✅ Dotted trendlines - polynomial fits
- ✅ Small markers (size=4) - no connecting lines
- ✅ Bold fonts - 12pt labels, 10pt legends
- ✅ Y-axis starts at 0 - for positive-only metrics

### Output Structure

```
YourDataFolder/
├── MASTER_all_metrics.csv              # All data combined
├── MASTER_area_analysis.png            # 4-subplot comparison
├── MASTER_area_ratio_analysis.png      # Ratio-based analysis
├── MASTER_distance_analysis.png        # Distance metrics
│
├── Condition1_Folder/
│   ├── autolog_L100-L105.csv
│   ├── autolog_L140-L145.csv
│   └── plots/
│       └── plots_20251218_HHMMSS/
│           ├── autolog_L100-L105_analysis.png
│           └── autolog_L140-L145_analysis.png
│
├── Condition2_Folder/
│   └── [similar structure]
│
└── Condition3_Folder/
    └── [similar structure]
```

---

## RawData Processor

### Purpose

Core module for loading CSV files and extracting layer-by-layer metrics.

**File:** `post-processing/RawData_Processor.py`

**Used By:**
- Post-print analyzer
- Batch processor
- Custom analysis scripts

### Key Features

#### 1. Layer Boundary Detection

**Two Methods:**

**Method A: Phase-Aware (Preferred)**
- Uses "Phase" column from PositionLogger
- Directly identifies Lift, Retract, Sandwich phases
- Most accurate and reliable

```python
# Detects boundaries from phase transitions
Exposure → Lift → Retract → Sandwich → Pause
    ↓         ↓        ↓         ↓
  Layer    Lifting  Retraction  Sandwich
  Start     Phase     Phase       Phase
```

**Method B: Adaptive (Fallback)**
- Analyzes position changes when no phase column
- Detects motion patterns automatically
- Robust to different printing parameters

```python
# Detects from position derivatives
Position change → Direction → Magnitude → Phase classification
```

**Detection Logic:**
```python
def _detect_boundaries_from_phases(time, position, force, phase):
    """
    Extract boundaries directly from phase labels.
    
    Returns for each layer:
    {
        'lifting': (start_idx, end_idx),
        'retraction': (start_idx, end_idx),
        'sandwich': (start_idx, end_idx)
    }
    """
```

#### 2. Metric Calculation

**Pipeline:**
```
1. Load CSV → time, position, force, phase arrays

2. Find layer boundaries → lifting/retraction/sandwich indices

3. For each layer:
   a. Extract lifting phase data ONLY
   b. Pass to AdhesionMetricsCalculator
   c. Calculate:
      - Peak force
      - Work of adhesion
      - Pre-initiation distance
      - Propagation distance
      - Time metrics
   d. Extract retraction force (from retraction phase)

4. Return structured results
```

**Critical: Phase-Aware Analysis**

```python
# CORRECT: Only analyze lifting phase
lifting_time = time_data[lifting_start:lifting_end+1]
lifting_pos = position_data[lifting_start:lifting_end+1]
lifting_force = force_data[lifting_start:lifting_end+1]

metrics = calculator.calculate_from_arrays(
    lifting_time, lifting_pos, lifting_force
)

# This EXCLUDES:
# - Pre-lift forces (exposure, previous sandwich)
# - Post-lift forces (retraction, next sandwich)
# Result: Accurate adhesion metrics
```

#### 3. Data Validation

**Automatic Checks:**
- Minimum data points per layer (>50 points)
- Force range reasonable (-5 to +5 N typical)
- Position monotonic during lift
- No excessive gaps in time series

### Usage Examples

#### Basic Usage

```python
from RawData_Processor import RawDataProcessor
from support_modules.adhesion_metrics_calculator import AdhesionMetricsCalculator

# Initialize
calculator = AdhesionMetricsCalculator(
    median_kernel=5,
    savgol_window=9,
    savgol_order=2
)
processor = RawDataProcessor(calculator)

# Process CSV file
layers = processor.process_csv('autolog_L48-L50.csv')

# Access results
for layer in layers:
    print(f"Layer {layer['layer_number']}:")
    print(f"  Peak force: {layer['peak_force']:.4f} N")
    print(f"  Work: {layer['work_of_adhesion']:.4f} mJ")
```

#### Custom Analysis

```python
# Get detailed layer data for custom plots
layer = layers[0]  # First layer

# Indices for plotting
lifting_start = layer['lifting_start_idx']
lifting_end = layer['lifting_end_idx']
peak_idx = layer['peak_idx']

# Time/force/position for this layer's lifting phase
layer_time = time_data[lifting_start:lifting_end+1]
layer_force = force_data[lifting_start:lifting_end+1]
layer_position = position_data[lifting_start:lifting_end+1]

# Create custom visualization
plt.plot(layer_time, layer_force)
plt.axvline(time_data[peak_idx], color='red', label='Peak')
```

---

## Analysis Tools

### 1. Analysis Plotter

**Purpose:** Generate comprehensive annotated plots for individual CSV files

**File:** `post-processing/analysis_plotter.py`

**Features:**
- Time-series plot (force + position)
- Phase-coded color shading
- Peak force annotation
- Work of adhesion calculation
- Distance markers
- Baseline detection shown
- Smoothed vs raw force comparison

**Usage:**

```python
from analysis_plotter import AnalysisPlotter

plotter = AnalysisPlotter()
plotter.plot_layers(
    layers=processor_output,
    time_data=time,
    force_data=force,
    position_data=position,
    csv_name='autolog_L48-L50',
    save_path='plots/analysis.png'
)
```

**Plot Elements:**

```
┌─────────────────────────────────────────────────────┐
│  Force (N) vs Time (s)                              │
│                                                      │
│  0.3 │     LIFT ╱╲   RETRACT  ─┐  SANDWICH  ╱╲    │
│      │        ╱    ╲          ╱ ╲          ╱  ╲    │
│  0.2 │       ╱      ╲        ╱   ╲        ╱    ╲   │
│      │  EXPOSURE     ╲      ╱     ╲  PAUSE      ╲  │
│  0.1 │     │          ╲────╱       ╲───────────  ╲ │
│      │     │                                       │
│  0.0 │─────┴─────────────────────────────────────  │
│      0s    5s   10s   15s   20s   25s   30s   35s  │
│                                                      │
│  Peak: 0.234 N   Work: 1.234 mJ   Distance: 2.34mm │
│                                                      │
│  ┌─ Position (mm) overlaid on secondary axis ──┐  │
│  └────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

---

### 2. Master Plotter

**Purpose:** Create comparison plots across multiple conditions

**File:** `post-processing/master_plotter.py`

**Standard Plots:**

#### Plot 1: Area Analysis (4 subplots)
```
┌─────────────────────┬─────────────────────┐
│  Peak Force vs Area │  Work vs Area       │
│  • Points grouped   │  • Error bands (SEM)│
│  • Trendline        │  • Polynomial fit   │
└─────────────────────┴─────────────────────┘
┌─────────────────────┬─────────────────────┐
│  Pre-init Distance  │  Peak Retract Force │
│    vs Area          │    vs Area          │
└─────────────────────┴─────────────────────┘
```

#### Plot 2: Speed Analysis
```
Same 4-subplot layout, but X-axis = Speed (µm/s)
Compare different peel speeds at constant geometry
```

#### Plot 3: Distance Analysis (2 subplots)
```
┌─────────────────────┬─────────────────────┐
│  Distance to Peak   │  Propagation Dist   │
│    vs Speed         │    vs Speed         │
│  (Pre-initiation)   │  (Crack growth)     │
└─────────────────────┴─────────────────────┘
```

**Configuration:**

```python
from master_plotter import MasterPlotter

plotter = MasterPlotter(
    use_area_binning=True,     # Group similar areas
    bin_tolerance=0.05,         # ±5% tolerance
    error_type='SEM',           # or 'IQR'
    marker_size=4,              # Small markers
    show_individual_points=False # Only show binned means
)

plotter.create_master_plots(
    master_df=combined_data,
    output_dir='.',
    plot_prefix='MASTER'
)
```

---

### 3. Hybrid Adhesion Plotter

**Purpose:** Quick analysis combining real-time + post-processing data

**File:** `post-processing/hybrid_adhesion_plotter.py`

**When to Use:**
- Compare real-time metrics (PeakForceLogger) vs post-processed
- Validate real-time system accuracy
- Debug discrepancies

**Features:**
- Loads both peak_force_output.csv and autolog CSVs
- Calculates metrics from both sources
- Generates comparison table
- Identifies differences

**Usage:**

```powershell
python hybrid_adhesion_plotter.py --folder "PrintingLogs/2025-12-18/Print 1"
```

**Output:**
```
Layer | Real-Time Peak | Post-Proc Peak | Difference
------|----------------|----------------|------------
48    | 0.234 N        | 0.236 N        | +0.002 N (0.9%)
49    | 0.245 N        | 0.243 N        | -0.002 N (0.8%)
50    | 0.256 N        | 0.258 N        | +0.002 N (0.8%)

Average difference: 0.8%
Max difference: 0.9%
Status: ✅ Excellent agreement
```

---

## Advanced Metrics

### Purpose

Calculate normalized metrics and test scaling laws for materials science analysis.

**Tool:** `post-processing/advanced_metrics.py`

### Normalized Metrics (Intensity Properties)

**Why Normalize?**
- Different layer sizes have different contact areas
- Raw force/work scales with area
- Normalized values are material properties (intensive)

**Calculated Metrics:**

```python
# Area-normalized metrics
adhesion_strength_kPa = peak_force_N / cross_sectional_area_mm2 * 1000

work_per_area_mJ_per_mm2 = work_of_adhesion_mJ / cross_sectional_area_mm2

stiffness_per_area_MPa = (peak_force_N / distance_to_peak_mm) / cross_sectional_area_mm2

retraction_strength_kPa = peak_retraction_force_N / cross_sectional_area_mm2 * 1000

# Additional derived metrics
energy_density_J_per_m3 = work_of_adhesion_mJ / (cross_sectional_area_mm2 * layer_thickness_mm)
```

**Physical Interpretation:**
- **Adhesion Strength (kPa):** Stress at failure, material-independent
- **Work per Area (mJ/mm²):** Energy to create new surface (fracture energy)
- **Stiffness per Area (MPa):** Material stiffness (Young's modulus proxy)
- **Energy Density (J/m³):** Volumetric energy dissipation

### Scaling Law Analysis

**Theory:** JKR (Johnson-Kendall-Roberts) predicts F ∝ A^1.0

**Method:** Fit power law F = k × A^n

```python
# For each condition
log(F) = log(k) + n × log(A)

# Linear regression in log-log space
n = slope
k = exp(intercept)
r² = coefficient of determination
```

**Interpretation:**
- **n ≈ 1.0:** Linear scaling (matches JKR theory)
  - Indicates homogeneous adhesion
  - Uniform stress distribution
  
- **n < 0.9:** Sub-linear scaling
  - Edge effects dominate
  - Crack nucleation barriers
  - Small features behave differently
  
- **n > 1.1:** Super-linear scaling
  - Cooperative failure mechanisms
  - Bulk fracture instead of peeling
  - Size-dependent toughening

**Usage:**

```powershell
python advanced_metrics.py
```

**Output:**
```
SCALING ANALYSIS RESULTS
========================

Condition: Water_1mm_1000um_s
  Points analyzed: 60
  Power law: F = 0.0234 × A^0.98
  R²: 0.95
  Interpretation: Linear scaling (matches JKR theory)

Condition: ACF_5mm_200um_s
  Points analyzed: 60
  Power law: F = 0.0456 × A^1.12
  R²: 0.92
  Interpretation: Super-linear (cooperative failure)
  
[Generates scaling_analysis_*.png plots]
[Saves scaling_analysis_results.csv]
```

---

## Statistical Analysis

### Purpose

Test for significant differences between experimental conditions.

**Tool:** `post-processing/statistical_analysis.py`

### Methods

#### 1. One-Way ANOVA

**Purpose:** Determine if ANY conditions differ significantly

**Null Hypothesis:** All condition means are equal

**Test:** F-statistic comparing between-group vs within-group variance

**Output:**
```
METRIC: peak_force_N

ONE-WAY ANOVA
  F-statistic: 45.23
  p-value: 0.000001
  Result: SIGNIFICANT (p < 0.05)
  
Conclusion: At least one condition differs from others
```

#### 2. Pairwise t-tests

**Purpose:** Identify WHICH specific pairs differ

**Method:** Student's t-test for each pair

**Multiple Comparison Correction:** Bonferroni method
```
Adjusted α = α / number_of_comparisons
```

**Output:**
```
PAIRWISE COMPARISONS (Bonferroni corrected)

Water_1mm vs ACF_5mm:
  Mean difference: 0.234 N
  95% CI: [0.189, 0.279]
  p-value (raw): 0.000004
  p-value (adj): 0.00012
  Cohen's d: 1.23 (large effect)
  Significant: YES

Water_1mm vs TEMPO_1mm:
  Mean difference: 0.045 N
  95% CI: [-0.012, 0.102]
  p-value (raw): 0.089
  p-value (adj): 0.267
  Cohen's d: 0.34 (small effect)
  Significant: NO
```

#### 3. Effect Size (Cohen's d)

**Formula:**
```
d = (mean1 - mean2) / pooled_std

pooled_std = sqrt((std1² + std2²) / 2)
```

**Interpretation:**
- **|d| < 0.2:** Negligible
- **0.2 ≤ |d| < 0.5:** Small
- **0.5 ≤ |d| < 0.8:** Medium
- **|d| ≥ 0.8:** Large

**Why It Matters:**
- Statistical significance (p-value) can be misleading with large samples
- Effect size shows practical/scientific importance
- Large effect + significant p-value = strong evidence

### Usage

```powershell
python statistical_analysis.py
```

**Output Files:**
- `Statistical_Analysis_Report.txt` - Complete text summary
- `ANOVA_results.csv` - F-stats and p-values for all metrics
- `pairwise_peak_force_N.csv` - All pairs for peak force
- `pairwise_work_of_adhesion_mJ.csv` - All pairs for work
- [One CSV per metric...]

---

## Visualization Tools

### Plot Types Reference

#### 1. Individual Layer Plot

**Generated By:** AnalysisPlotter, post_print_analyzer.py

**Shows:**
- Time-series force and position
- Color-coded phases
- Annotations (peak, work, distances)
- Raw + smoothed force

**When to Use:**
- Quality check individual layers
- Debug anomalies
- Detailed force curve analysis
- Publication-quality single-layer figures

---

#### 2. Master Comparison Plots

**Generated By:** MasterPlotter, batch processor

**Shows:**
- Multiple conditions on same axes
- Error bands (SEM or IQR)
- Trendlines
- Grouped/binned data

**When to Use:**
- Compare experimental conditions
- Show trends across parameter space
- Publication multi-panel figures
- Executive summaries

---

#### 3. Scaling Analysis Plots

**Generated By:** advanced_metrics.py

**Shows:**
- Linear plot: F vs A
- Log-log plot: log(F) vs log(A)
- Power law fits
- R² values

**When to Use:**
- Test theoretical predictions
- Identify size effects
- Materials science analysis
- Mechanism investigation

---

#### 4. Statistical Comparison Plots

**Generated By:** statistical_analysis.py (future enhancement)

**Shows:**
- Bar charts with error bars
- Significance brackets (* p<0.05, ** p<0.01)
- Effect size indicators

**When to Use:**
- Present statistical differences
- Publication-ready stats figures
- Grant proposals
- Scientific talks

---

## Common Workflows

### Workflow 1: Quick Post-Print Check

**Purpose:** Verify print quality immediately after completion

```powershell
# Step 1: Run automatic analysis
cd post-processing
python post_print_analyzer.py

# Step 2: Review plot
# Open: PrintingLogs/YYYY-MM-DD/Print X/plots/latest/*.png

# Step 3: Check console for anomalies
# Look for: negative work, zero forces, missing layers
```

**Time:** 30 seconds

**Decision:** Continue testing or investigate issues

---

### Workflow 2: Single Condition Analysis

**Purpose:** Analyze one test condition in detail

```powershell
# Step 1: Process folder
python process_folder.py "path/to/test/folder"

# Step 2: Review outputs
# - Individual plots in plots/ subdirectory
# - Check metrics consistency
# - Verify expected trends

# Step 3: Calculate advanced metrics (optional)
cd path/to/test/folder
python ../../advanced_metrics.py
```

**Time:** 2-5 minutes

**Output:** Plots + enhanced metrics CSV

---

### Workflow 3: Multi-Condition Comparison

**Purpose:** Compare several test conditions

```powershell
# Step 1: Organize data
# Ensure all test folders in one parent directory

# Step 2: Run batch processor
cd post-processing
python process_folder.py "path/to/parent/directory"

# This processes ALL subfolders automatically

# Step 3: Review master plots
# MASTER_area_analysis.png - Key comparison
# MASTER_distance_analysis.png - Detailed metrics

# Step 4: Statistical analysis
python statistical_analysis.py

# Step 5: Generate report
python generate_analysis_report.py
```

**Time:** 5-15 minutes (depending on data volume)

**Output:** Master plots + statistics + PDF report

---

### Workflow 4: Publication-Ready Analysis

**Purpose:** Complete analysis for journal submission

```powershell
# Step 1: Complete pipeline
python run_complete_analysis.py --folder V6

# Step 2: Quality control
# Review QC_Report.txt
# Address any flagged issues

# Step 3: Advanced analysis
# Already included in pipeline:
# - Normalized metrics
# - Scaling laws
# - Statistical tests

# Step 4: Custom plotting
# Use matplotlib scripts to create
# publication-specific figures

# Step 5: Export data
# MASTER_steppedcone_metrics_ENHANCED.csv
# Ready for import to Origin/Igor/Matlab
```

**Time:** 15-30 minutes

**Output:** Publication-ready figures + data tables

---

### Workflow 5: Re-analysis with Different Settings

**Purpose:** Re-process with updated smoothing or thresholds

```python
# Create custom analysis script

from RawData_Processor import RawDataProcessor
from support_modules.adhesion_metrics_calculator import AdhesionMetricsCalculator

# Adjust calculator settings
calculator = AdhesionMetricsCalculator(
    median_kernel=7,              # Changed from 5
    savgol_window=11,             # Changed from 9
    baseline_threshold_factor=0.005  # Changed from 0.002
)

# Process with new settings
processor = RawDataProcessor(calculator)
layers = processor.process_csv('autolog_L48-L50.csv')

# Generate plots with new results
# [your plotting code here]
```

**When to Use:**
- Data very noisy → increase smoothing
- Data very clean → decrease smoothing
- Baseline detection issues → adjust threshold

---

## Troubleshooting

### Issue: "No layers detected"

**Symptoms:**
- Processor returns empty list
- "No layer boundaries found" message

**Possible Causes:**

1. **Phase column missing or incorrect**
   - Solution: Check CSV has "Phase" column
   - Verify: Phase values are "Lift", "Retract", etc. (not empty/NaN)

2. **Adaptive detection failing**
   - Solution: Check position data reasonable
   - Verify: Position changes >1 mm during peel
   - Increase: Detection sensitivity in code

3. **Insufficient data points**
   - Solution: Check CSV not truncated
   - Verify: Minimum ~500 points per layer
   - Fix: Re-run print with longer logging

---

### Issue: Negative work of adhesion

**Symptoms:**
- work_of_adhesion_mJ < 0 in results
- Physically impossible

**Possible Causes:**

1. **Phase detection wrong**
   - Solution: Verify lift phase boundaries
   - Check: Lifting phase starts at ~zero force
   - Fix: Use phase-aware detection (add Phase column)

2. **Baseline detection incorrect**
   - Solution: Plot raw force to visualize baseline
   - Adjust: baseline_threshold_factor (increase for noisy data)

3. **Force gauge not calibrated**
   - Solution: Check force readings during stationary periods
   - Verify: Should be near 0 N when no load
   - Fix: Recalibrate force gauge, re-run print

---

### Issue: Excessive noise in force data

**Symptoms:**
- Jagged force curves
- Erratic peak detection
- High standard deviations

**Solutions:**

1. **Increase smoothing**
   ```python
   calculator = AdhesionMetricsCalculator(
       median_kernel=7,    # Increase from 5
       savgol_window=15    # Increase from 9
   )
   ```

2. **Check decimation settings**
   - Verify: ForceGaugeManager using decimation
   - Increase: Sampling interval (25ms → 50ms)

3. **Electrical interference**
   - Check: USB connections
   - Isolate: Force gauge from DLP/motors
   - Ground: All metal components

---

### Issue: "Module not found" errors

**Symptoms:**
```
ImportError: No module named 'support_modules'
ModuleNotFoundError: No module named 'RawData_Processor'
```

**Solutions:**

1. **Working directory wrong**
   ```powershell
   # Must be in post-processing directory
   cd post-processing
   python analysis_script.py
   ```

2. **Python path not set**
   ```python
   import sys
   from pathlib import Path
   
   # Add support_modules to path
   project_root = Path(__file__).parent.parent
   sys.path.insert(0, str(project_root / 'support_modules'))
   ```

3. **Files moved/renamed**
   - Verify: support_modules/ directory exists
   - Check: Files not accidentally deleted
   - Restore: From git if necessary

---

### Issue: Out of memory during batch processing

**Symptoms:**
- Script crashes with MemoryError
- System becomes unresponsive
- Very slow performance

**Solutions:**

1. **Process in smaller batches**
   ```powershell
   # Instead of processing entire V6:
   python process_folder.py "V6/subset1"
   python process_folder.py "V6/subset2"
   # Then manually combine MASTER CSV files
   ```

2. **Reduce plot resolution**
   ```python
   # In plotting code:
   plt.figure(dpi=100)  # Instead of dpi=300
   ```

3. **Close plots after saving**
   ```python
   plt.savefig('plot.png')
   plt.close()  # Free memory
   ```

4. **Disable individual plots**
   ```python
   # In batch processor config:
   GENERATE_INDIVIDUAL_PLOTS = False  # Only master plots
   ```

---

### Issue: Master plots show unexpected trends

**Symptoms:**
- Linear fit where expecting nonlinear
- Scatter with no clear pattern
- Outliers dominating plot

**Solutions:**

1. **Enable outlier filtering**
   ```python
   ENABLE_OUTLIER_FILTER = True
   OUTLIER_METHOD = 'iqr'
   OUTLIER_THRESHOLD = 1.5
   ```

2. **Check area binning**
   ```python
   # Tighter binning for cleaner plots
   bin_tolerance = 0.03  # ±3% instead of ±5%
   ```

3. **Review QC report**
   ```powershell
   python data_validator.py
   # Examine QC_Report.txt for issues
   ```

4. **Verify metadata extraction**
   - Check: Folder names parsed correctly
   - Verify: Conditions not mixed up
   - Fix: Rename folders if needed

---

## Quick Reference - Command Summary

### Single File Analysis
```powershell
python post_print_analyzer.py
python post_print_analyzer.py --csv-file "path/to/file.csv"
```

### Batch Processing
```powershell
python process_folder.py V6
python process_folder.py "C:\custom\path"
```

### Advanced Metrics
```powershell
python advanced_metrics.py
```

### Statistical Analysis
```powershell
python statistical_analysis.py
```

### Complete Pipeline
```powershell
python run_complete_analysis.py --folder V6
python run_complete_analysis.py --folder V6 --skip-batch
```

### Report Generation
```powershell
python generate_analysis_report.py
```

---

## File Organization Best Practices

### Folder Structure Recommendation

```
YourProject/
├── PrintingLogs/                    # Raw data from prints
│   ├── 2025-12-01/
│   │   ├── Print 1/
│   │   │   ├── sensor_log.csv
│   │   │   ├── autolog_L48-L50.csv
│   │   │   ├── peak_force_output.csv
│   │   │   └── plots/              # Auto-generated
│   │   └── Print 2/
│   └── 2025-12-02/
│
├── AnalyzedData/                    # Post-processed results
│   ├── V6_SteppedCones/
│   │   ├── MASTER_all_metrics.csv
│   │   ├── MASTER_*.png
│   │   ├── QC_Report.txt
│   │   └── Condition_Subfolders/
│   └── V7_Pyramids/
│
└── PublicationFigures/              # Final publication-ready plots
    ├── Figure1_Overview.png
    ├── Figure2_Scaling.png
    └── FigureS1_RawData.png
```

### Naming Conventions

**Folder Names (for auto-parsing):**
```
{Material}_{Thickness}_{Tank}_{Model}_{Resin}_{Speed}
100umPDMS_1mm_V22p1_Cone_BPAGDA_1000
```

**CSV Files:**
```
autolog_L{start}-L{end}.csv
autolog_L48-L50.csv
```

**Plot Files:**
```
{csv_name}_analysis.png
autolog_L48-L50_analysis.png
```

**Master Files:**
```
MASTER_{metric_type}.{ext}
MASTER_all_metrics.csv
MASTER_area_analysis.png
```

---

## Summary

**Post-Processing Capabilities:**

✅ **Immediate Analysis** - Quick checks after each print  
✅ **Batch Processing** - Compare multiple conditions automatically  
✅ **Universal Processor** - One script handles all data versions  
✅ **Layer Detection** - Automatic boundary finding (phase-aware or adaptive)  
✅ **Metrics Calculation** - Peak force, work, distances, timing  
✅ **Advanced Analysis** - Normalized metrics, scaling laws  
✅ **Statistics** - ANOVA, t-tests, effect sizes  
✅ **Visualization** - Individual plots, master comparisons, publication figures  
✅ **Reports** - Automated PDF summaries  

**Key Modules:**

- **post_print_analyzer.py** - Immediate single-file analysis
- **RawData_Processor.py** - Core CSV processing and layer detection
- **batch processor** - Multi-condition comparison
- **advanced_metrics.py** - Normalized metrics and scaling
- **statistical_analysis.py** - Hypothesis testing
- **analysis_plotter.py** - Individual layer plots
- **master_plotter.py** - Multi-condition comparison plots

**For More Information:**
- Pre-print setup: [PRE_PRINT_SETUP_GUIDE.md](PRE_PRINT_SETUP_GUIDE.md)
- During-print: [PRINTING_PROCESS_GUIDE.md](PRINTING_PROCESS_GUIDE.md)
- Technical details: documentation/technical/

---

**Last Updated:** December 18, 2025  
**Guide Version:** 1.0  
**Software:** Prince Segmented 3D Printer Control Software
