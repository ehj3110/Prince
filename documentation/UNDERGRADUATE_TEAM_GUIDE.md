# Adhesion Measurement System: Guide for Undergraduate Researchers

**Author:** Evan Jones (Lead Researcher)  
**Last Updated:** November 17, 2025  
**Target Audience:** Undergraduate students with limited 3D printing and Python experience

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [System Overview](#2-system-overview)
3. [The Printing Process](#3-the-printing-process)
4. [Understanding the Force Curve](#4-understanding-the-force-curve)
5. [Adhesion Metrics We Measure](#5-adhesion-metrics-we-measure)
6. [Post-Processing Workflow](#6-post-processing-workflow)
7. [Your Mission: Improving Metric Detection](#7-your-mission-improving-metric-detection)
8. [Getting Started with Python](#8-getting-started-with-python)
9. [Glossary](#9-glossary)

---

## 1. Introduction

### What is This Project About?

We're studying **adhesion forces** in resin 3D printing. When a 3D printer creates a layer of cured resin, that layer sticks (adheres) to a transparent film at the bottom of the resin tank. Understanding and measuring these adhesion forces helps us:

- **Optimize printing parameters** for better print quality
- **Prevent print failures** caused by excessive adhesion
- **Study material science** of photopolymers (light-cured plastics)
- **Develop new printing techniques** for advanced applications

### The Challenge

Currently, we collect force data automatically during printing, but analyzing that data requires manual parameter tuning. Your job is to help develop **better algorithms** so our analysis can run automatically without adjustments.

---

## 2. System Overview

### 2.1 Hardware Components

Our custom 3D printer consists of:

1. **DLP Projector (Digital Light Processing)**
   - Projects images onto liquid resin
   - Cures (hardens) resin wherever light hits
   - Like a slide projector, but for 3D printing

2. **Zaber Linear Stage (Z-axis)**
   - Precision motor that moves the build plate up and down
   - Accuracy: ~1 micrometer (0.001 mm)
   - Controlled via USB from our software

3. **Phidgets Force Gauge**
   - Measures forces between 0-10 Newtons (N)
   - Samples data at ~50-65 Hz (50-65 readings per second)
   - Mounted between the build plate and the stage
   - Records every push and pull during printing

4. **Resin Vat**
   - Contains liquid photopolymer resin
   - Bottom is transparent FEP film (like Teflon)
   - Light passes through to cure resin

### 2.2 Software Architecture

Our system has three main software components:

**A. Real-Time Control (`Prince_Segmented.py`)**
- Main graphical interface for operating the printer
- Controls stage movements and light exposure
- Collects force and position data during printing

**B. Live Analysis (`PeakForceLogger.py` + `adhesion_metrics_calculator.py`)**
- Runs in background during printing
- Analyzes force data immediately after each layer
- Saves results to CSV files

**C. Post-Processing (`batch_process_*.py` + modules)**
- Analyzes completed print data
- Creates detailed plots and visualizations
- Aggregates data across multiple tests

---

## 3. The Printing Process

### 3.1 Basic DLP Printing Steps (Standard Print)

For a typical resin print, each layer follows this sequence:

```
1. EXPOSE → 2. LIFT → 3. RETRACT → 4. PAUSE → 5. SANDWICH → [repeat]
```

Let's break down each step:

#### Step 1: EXPOSE (Light Projection)
- **What happens:** Projector displays layer image onto resin
- **Duration:** User-defined (e.g., 3 seconds)
- **Stage motion:** None - build plate is stationary, touching the film
- **Result:** Liquid resin cures (hardens) and bonds to previous layer

#### Step 2: LIFT (Peel Away)
- **What happens:** Stage moves DOWN (build plate moves away from film)
- **Distance:** ~6 mm typically (user-defined)
- **Speed:** Variable (100-6000 µm/s)
- **Force behavior:** This is where we measure adhesion!
  - Force increases as layer stretches
  - Peak occurs when layer begins to peel
  - Force decreases as peeling propagates
  - Returns to baseline when fully separated

#### Step 3: RETRACT (Return to Build Position)
- **What happens:** Stage moves UP (build plate returns toward film)
- **Distance:** Same as lift distance (~6 mm)
- **Speed:** Usually same as lift speed
- **Purpose:** Positions plate for next layer

#### Step 4: PAUSE (Settling Time)
- **What happens:** Stage stops, no motion
- **Duration:** User-defined (e.g., 0-2 seconds)
- **Purpose:** 
  - Allows resin to flow back under print
  - Lets vibrations settle
  - Gives time for film to relax

#### Step 5: SANDWICH (Touch Down)
- **What happens:** Stage touches print back to film gently
- **Distance:** Very small (~0.1-0.5 mm)
- **Purpose:** 
  - Ensures good contact for next layer
  - Squeezes out excess resin
  - Creates thin, controlled layer thickness

### 3.2 Stepped Mode (Research Variant)

For adhesion testing, we use a modified "stepped" sequence:

```
DISPLAY IMAGE → EXPOSE → BLACKOUT → LIFT → RETRACT → PAUSE → SANDWICH → [repeat]
```

**Key Differences:**
- **DISPLAY IMAGE:** Show image 1 second before exposure
- **BLACKOUT:** Turn off projector after exposure
- **Result:** Better synchronized force measurements

### 3.3 Position Convention (Important!)

**Our system has an inverted position convention:**
- **Lifting** = Position DECREASES (moving away from vat = going "down")
- **Retracting** = Position INCREASES (moving toward vat = going "up")

This can be confusing! Always check which direction is which.

**Example:**
```
Initial position:    66.0 mm (build plate near film)
After LIFT:         60.0 mm (build plate moved away)
After RETRACT:      66.0 mm (back at starting position)
```

---

## 4. Understanding the Force Curve

### 4.1 What Does a Complete Test Cycle Look Like?

Here's what force vs. time looks like for one layer:

```
Force (N)
   |
0.2|                    * Peak Force
   |                   /|\
   |                  / | \
0.1|    Pre-Init    /  |  \  Propagation
   |     Phase     /   |   \___
   |    _________ /    |       \____
0.0|___/Baseline       |            \_________ Baseline
   |               
   +-----------------------------------------------------> Time (s)
       LIFT begins  Peak  Prop End    RETRACT complete
```

### 4.2 Phase-by-Phase Breakdown

#### **BASELINE (Before Lifting)**
- **What:** Initial force reading when plate is stable
- **Typical value:** ~0.01-0.02 N (sensor noise)
- **What it represents:** "Zero" reference point
- **Duration:** Until lifting motion begins

#### **PRE-INITIATION PHASE (Force Loading)**
- **What:** Force increases as cured layer stretches
- **Mechanism:** Elastic deformation of the layer
- **Force behavior:** Roughly linear increase
- **Duration:** ~0.1-0.5 seconds
- **Key characteristic:** No peeling yet - layer is stretching like a rubber band
- **Analogy:** Pulling on a piece of tape before it starts to peel

#### **PEAK FORCE (Critical Moment)**
- **What:** Maximum force occurs
- **Physical meaning:** The moment when layer begins to peel away from film
- **Typical value:** 0.05-0.3 N (depends on many factors)
- **Key point:** This is where crack initiation happens
- **Importance:** Peak force determines if print will succeed or fail

#### **PROPAGATION PHASE (Peeling)**
- **What:** Force decreases as peeling spreads across layer
- **Mechanism:** Crack propagates from initiation point across contact area
- **Force behavior:** Exponential decay
- **Duration:** ~0.2-0.8 seconds
- **Key characteristic:** Layer is actively separating from film
- **Analogy:** Peeling a sticker off a surface - once it starts, it gets easier

#### **PROPAGATION END (Separation Complete)**
- **What:** Layer fully separated from film
- **Detection:** Where force decay rate becomes negligible
- **Typical value:** Close to baseline (~0.02-0.04 N)
- **Challenge:** Hard to detect precisely (this is what you'll improve!)

#### **POST-SEPARATION (Retraction)**
- **What:** Stage pulls plate back toward starting position
- **Force behavior:** Minimal force, mostly baseline
- **Peak retraction force:** Small force spike at end of motion (~0.02-0.04 N)

### 4.3 Visual Example with Real Data

```
Time (s):     0.0    0.2    0.4    0.6    0.8    1.0    1.2
              |      |      |      |      |      |      |
Position:   66.0   65.5   64.0   62.0   60.5   60.0   60.5
              |      |      |      |      |      |      |
Force (N):  0.01   0.03   0.10   0.18   0.12   0.03   0.02
              |      |      |      |      |      |      |
Phase:    Baseline PreInit  "    Peak   Prop   PropEnd Retract
                  [---Lifting---]  [-----Separation-----]
```

### 4.4 What Affects the Force Curve?

Many factors influence the shape and magnitude of forces:

**Material Properties:**
- Resin chemistry
- Film type (FEP, PTFE)
- Degree of cure
- Temperature

**Process Parameters:**
- Peel speed (faster = higher peak)
- Exposure time (longer = stronger adhesion)
- Layer thickness
- Contact area

**Environmental Factors:**
- Fluid between film and layer (water, air, PEO solution)
- Gap size (distance between film and print)
- Temperature
- Humidity

---

## 5. Adhesion Metrics We Measure

### 5.1 Overview

We extract **17 different metrics** from each force curve. Here are the most important ones:

### 5.2 Primary Force Metrics

#### **Peak Force (N)**
- **Definition:** Maximum force during peeling
- **Physical meaning:** Force needed to initiate crack propagation
- **Why it matters:** Determines print success/failure threshold
- **Typical range:** 0.05-0.30 N
- **Calculation:** `max(smoothed_force[pre_init_idx:prop_end_idx])`

#### **Baseline Force (N)**
- **Definition:** Force level at propagation end
- **Physical meaning:** Reference "zero" after all adhesion is overcome
- **Why it matters:** Used to correct other measurements
- **Typical range:** 0.010-0.030 N
- **Calculation:** `smoothed_force[prop_end_idx]`

#### **Peak Force Corrected (N)**
- **Definition:** Peak force minus baseline
- **Physical meaning:** True adhesion force
- **Why it matters:** Removes sensor offset/drift effects
- **Calculation:** `peak_force - baseline_force`

#### **Peak Retraction Force (N)**
- **Definition:** Maximum force during retraction phase
- **Physical meaning:** Resistance during return motion
- **Why it matters:** Quality check for unexpected adhesion
- **Typical range:** 0.02-0.05 N

### 5.3 Temporal (Time) Metrics

#### **Pre-Initiation Duration (s)**
- **Definition:** Time from force rises above baseline until peak force
- **Physical meaning:** How long layer stretches before peeling starts
- **Why it matters:** Indicates elastic deformation time
- **Typical range:** 0.1-0.5 seconds
- **Depends on:** Peel speed, material stiffness

#### **Propagation Duration (s)**
- **Definition:** Time from peak force until propagation end
- **Physical meaning:** How long peeling takes to complete
- **Why it matters:** Characterizes crack propagation dynamics
- **Typical range:** 0.2-0.8 seconds
- **Depends on:** Contact area, peel speed, material properties

#### **Total Peel Duration (s)**
- **Definition:** Pre-initiation duration + propagation duration
- **Physical meaning:** Complete peeling event time
- **Calculation:** `propagation_end_time - pre_initiation_time`

### 5.4 Spatial (Distance) Metrics

#### **Pre-Initiation Distance (mm)**
- **Definition:** How far stage moves from baseline crossing to peak force
- **Physical meaning:** Layer stretch distance
- **Typical range:** 0.1-0.5 mm
- **Calculation:** `position[peak_idx] - position[pre_init_idx]`

#### **Propagation Distance (mm)**
- **Definition:** How far stage moves from peak to propagation end
- **Physical meaning:** Distance over which peeling occurs
- **Typical range:** 0.3-1.5 mm
- **Calculation:** `position[prop_end_idx] - position[peak_idx]`

#### **Total Peel Distance (mm)**
- **Definition:** Complete peeling travel distance
- **Calculation:** `position[prop_end_idx] - position[pre_init_idx]`

### 5.5 Energy Metrics

#### **Work of Adhesion (mJ)**
- **Definition:** Energy required to separate layer from film
- **Physical meaning:** Total adhesion energy
- **Why it matters:** Most comprehensive adhesion measure
- **Typical range:** 0.5-5.0 mJ
- **Calculation:** Integral of force over distance (trapezoidal integration)
  ```
  Work = ∫ Force(x) dx  (from peak to propagation end)
  ```

#### **Work of Adhesion Corrected (mJ)**
- **Definition:** Work calculated using baseline-corrected force
- **Physical meaning:** True adhesion work
- **Why it matters:** More accurate than raw work
- **Calculation:** 
  ```
  Work_corrected = ∫ (Force(x) - Baseline) dx
  ```

#### **Energy Density (mJ/mm)**
- **Definition:** Work of adhesion per unit distance
- **Physical meaning:** Energy per mm of separation
- **Why it matters:** Normalizes for different peel distances
- **Calculation:** `work_of_adhesion_corrected / total_peel_distance`

### 5.6 Dynamic Metrics

#### **Max Loading Rate (N/s)**
- **Definition:** Maximum rate of force increase during pre-initiation
- **Physical meaning:** How fast force builds up
- **Why it matters:** Indicates strain rate sensitivity
- **Calculation:** `max(gradient(force)[pre_init:peak])`

#### **Max Unloading Rate (N/s)**
- **Definition:** Maximum rate of force decrease during propagation
- **Physical meaning:** How fast peeling progresses
- **Why it matters:** Characterizes propagation dynamics
- **Calculation:** `max(abs(gradient(force)[peak:prop_end]))`

### 5.7 Quality Metrics

#### **Signal-to-Noise Ratio (SNR)**
- **Definition:** Peak force amplitude divided by noise level
- **Physical meaning:** Data quality indicator
- **Why it matters:** Low SNR = unreliable measurements
- **Typical range:** 10-100
- **Calculation:** `(peak_force - baseline) / std(raw_force - smoothed_force)`

#### **Force Noise STD (N)**
- **Definition:** Standard deviation of noise in force signal
- **Physical meaning:** Sensor noise level
- **Typical range:** 0.002-0.008 N
- **Calculation:** `std(raw_force - smoothed_force)`

---

## 6. Post-Processing Workflow

### 6.1 Data Flow Overview

```
PRINTING → RAW DATA → PROCESSING → ANALYSIS → VISUALIZATION
   ↓          ↓            ↓           ↓            ↓
Sensor   CSV Files   Layer      Metrics     Plots &
Readings (autolog)   Boundary   Calculator  Graphs
                     Detection
```

### 6.2 Files Generated During Printing

When you run a print with adhesion testing enabled, these files are created:

#### **autolog_L##-L##.csv**
- **Contains:** Raw time, position, force data
- **Sampling rate:** ~50-65 Hz
- **Columns:**
  - `Elapsed Time (s)` - Time since layer start
  - `Position (mm)` - Stage position
  - `Force (N)` - Raw force sensor reading
- **Naming:** Layer range included (e.g., `autolog_L48-L50.csv` = Layers 48-50)

#### **automated_work_of_adhesion.csv**
- **Contains:** Real-time calculated metrics
- **Created by:** `PeakForceLogger.py` during printing
- **Columns:** All 17 metrics for each layer
- **Purpose:** Quick results without post-processing

### 6.3 Post-Processing Scripts

After printing, we can re-analyze data with different parameters:

#### **analyze_single_folder.py**
- **Purpose:** Process one test folder
- **Input:** Path to folder with autolog files
- **Output:**
  - Individual layer plots (force vs. time)
  - Metrics CSV file
- **When to use:** Quick check of a single experiment

#### **batch_process_steppedcone.py**
- **Purpose:** Process multiple test conditions
- **Input:** Folder containing subfolders for different tests
- **Output:**
  - Individual plots for each test
  - Master CSV combining all data
  - Comparison plots across conditions
- **When to use:** Analyzing full experimental campaigns

### 6.4 Key Processing Modules

These Python modules do the actual work:

#### **RawData_Processor.py**
- **Responsibility:** Find layer boundaries in raw data
- **Key function:** `_find_layer_boundaries()`
- **How it works:**
  1. Auto-detect lift distance from position data
  2. Find all motions matching that distance (±15%)
  3. Pair consecutive motions as lift/retract cycles
  4. Identify pause and sandwich phases
- **Challenge:** Must work for different lift distances (2mm, 3mm, 6mm)

#### **adhesion_metrics_calculator.py**
- **Responsibility:** Calculate all 17 metrics from force data
- **Key functions:**
  - `calculate_from_arrays()` - Main entry point
  - `_find_peak_force()` - Locate maximum force
  - `_find_propagation_end_reverse_search()` - Detect separation point
  - `_calculate_work_metrics()` - Integrate force-distance curve
- **Critical algorithm:** Propagation end detection (see Section 7)

#### **analysis_plotter.py**
- **Responsibility:** Generate publication-quality plots
- **Key features:**
  - Overview plot showing all layers
  - Individual layer detail plots
  - Color-coded phases (pre-init, propagation)
  - Event markers (peak, propagation end)
- **Output:** PNG files with multiple subplots

### 6.5 Data Smoothing Pipeline

Raw force data is noisy. We use a **two-step filtering approach**:

#### **Step 1: Median Filter**
- **Purpose:** Remove sharp outlier spikes
- **Kernel size:** 5 data points
- **How it works:** Replace each point with median of surrounding 5 points
- **Effect:** Eliminates impulse noise without blurring peaks

#### **Step 2: Savitzky-Golay Filter**
- **Purpose:** Smooth data while preserving peak shape
- **Window:** 9 data points
- **Polynomial order:** 2 (quadratic fit)
- **How it works:** Fits polynomial to local window, replaces point with fit value
- **Effect:** Reduces noise by ~90% while maintaining curve shape

**Combined Result:**
- Original noise: ~0.005 N standard deviation
- After filtering: ~0.0005 N standard deviation
- Peak preservation: >99% (peaks are not artificially lowered)

---

## 7. Your Mission: Improving Metric Detection

### 7.1 The Problem

Currently, our system works well for "typical" data but struggles with edge cases:

- **Variable peel speeds:** Slow speeds (100 µm/s) vs. fast speeds (6000 µm/s) look very different
- **Different contact areas:** Small areas vs. large areas have different force magnitudes
- **Material variations:** Water vs. PEO vs. air changes curve shapes
- **Noise levels:** Some sensors/conditions are noisier than others

The current algorithms require manual parameter tuning to work correctly across all conditions. We want **one algorithm that works everywhere**.

### 7.2 Current Propagation End Detection Method

This is the **most critical** metric to detect accurately. Here's how it currently works:

#### **Algorithm: Second Derivative 10% Threshold Method**

**Step 1:** Define search region
- Start: Peak force index
- End: 80% of lifting distance
- Why 80%?: Excludes tail region where force has stabilized

**Step 2:** Calculate second derivative
```python
# Second derivative shows rate of force decay
second_derivative = gradient(gradient(smoothed_force))
```

**Step 3:** Find highest positive peak in 2nd derivative
- Physical meaning: Where force is decaying FASTEST
- This is the "active peeling" point

**Step 4:** Calculate 10% threshold
```python
threshold = max_second_derivative * 0.10
```

**Step 5:** Find last point BEFORE derivative drops below threshold
- This marks the end of significant peeling activity
- Physical meaning: Decay rate has become negligible

#### **Why This Works (Usually)**

The second derivative amplifies changes in slope:
- During active peeling: High 2nd derivative (force changing rapidly)
- After peeling complete: Low 2nd derivative (force stable)
- The 10% threshold captures where change becomes negligible

#### **Where It Fails**

1. **Very fast peels (>5000 µm/s):**
   - 2nd derivative peak is very sharp
   - 10% threshold crossed too early
   - Result: Propagation end detected before actual separation

2. **Very slow peels (<500 µm/s):**
   - 2nd derivative peak is broad and flat
   - Hard to find distinct threshold crossing
   - Result: Propagation end detected too late

3. **Noisy data:**
   - Multiple false peaks in 2nd derivative
   - Algorithm may pick wrong peak
   - Result: Erratic propagation end detection

4. **Unusual force curves:**
   - Multiple peaks (re-adhesion events)
   - Non-monotonic decay
   - Result: Algorithm confused

### 7.3 Other Detection Challenges

#### **Pre-Initiation Start**
- **Current method:** Forward search from lift start for baseline crossing
- **Challenge:** What is "baseline"? Varies with sensor drift
- **Failure mode:** May start too early (noise) or too late (miss initial rise)

#### **Peak Force**
- **Current method:** Simple maximum of smoothed force
- **Challenge:** Multiple peaks or plateaus
- **Failure mode:** May pick wrong peak (noise spike or secondary peak)

#### **Baseline Calculation**
- **Current method:** Use force value at propagation end
- **Challenge:** If propagation end is wrong, baseline is wrong
- **Failure mode:** Cascading errors in all corrected metrics

### 7.4 What We Need From You

Your goal is to develop **improved detection algorithms** that:

1. **Work across all peel speeds** (100-6000 µm/s)
2. **Handle different curve shapes** (water, PEO, air, etc.)
3. **Are robust to noise** (work with SNR as low as 10)
4. **Require minimal parameters** (ideally zero user tuning)
5. **Are computationally efficient** (run in <0.1s per layer)
6. **Are physically meaningful** (match what you see visually)

### 7.5 Approach Suggestions

Here are some ideas to explore (not required, just suggestions):

#### **Machine Learning Approaches**
- Train classifier to identify propagation end from curve shape
- Use supervised learning with manually labeled "ground truth"
- Features: Curve derivatives, curvature, integral values

#### **Signal Processing Approaches**
- Wavelet analysis to separate noise from signal
- Fourier analysis to identify frequency components
- Autocorrelation to find characteristic decay time

#### **Adaptive Threshold Methods**
- Calculate threshold based on local curve properties
- Use multiple criteria (2nd deriv + force level + distance)
- Weight thresholds by confidence metrics

#### **Template Matching**
- Create "ideal" curve templates for different conditions
- Match real data to templates using correlation
- Interpolate between templates for intermediate cases

#### **Multi-Scale Analysis**
- Analyze curve at different resolutions (zoom levels)
- Coarse scale: Overall decay trend
- Fine scale: Local features and transitions
- Combine insights from multiple scales

### 7.6 Evaluation Criteria

How will we judge if a new algorithm is better?

#### **Quantitative Metrics:**
1. **Accuracy:** Compare to manually labeled ground truth
2. **Precision:** Standard deviation across repeated tests
3. **Speed:** Computation time per layer
4. **Robustness:** Performance on worst-case data
5. **Generalizability:** Works on untrained conditions

#### **Qualitative Metrics:**
1. **Visual inspection:** Does it look right on plots?
2. **Physical intuition:** Does it match peeling physics?
3. **Consistency:** Similar results for similar curves?
4. **Failure mode analysis:** How does it fail? Gracefully or catastrophically?

### 7.7 Development Workflow

Here's how you'll actually work on this:

**Week 1-2: Understanding**
1. Run existing code on sample data
2. Generate plots, inspect results
3. Identify failure cases visually
4. Understand current algorithm thoroughly

**Week 3-4: Experimentation**
1. Modify one thing at a time
2. Test on small dataset
3. Compare before/after results
4. Document what works and what doesn't

**Week 5-6: Refinement**
1. Combine best approaches
2. Test on full dataset
3. Tune parameters (if needed)
4. Create comprehensive validation report

**Week 7-8: Integration**
1. Clean up code
2. Add comments and documentation
3. Create pull request with changes
4. Present results to team

---

## 8. Getting Started with Python

### 8.1 No Python Experience? No Problem!

This section will get you started. The code is well-commented and modular.

### 8.2 Essential Python Concepts

#### **Arrays (NumPy)**
```python
import numpy as np

# Create array of time points
time = np.array([0.0, 0.1, 0.2, 0.3, 0.4])

# Access elements
first_time = time[0]        # 0.0
last_time = time[-1]        # 0.4

# Slicing (get range)
middle_times = time[1:4]    # [0.1, 0.2, 0.3]

# Math operations
doubled = time * 2          # [0.0, 0.2, 0.4, 0.6, 0.8]
```

#### **Loading Data (Pandas)**
```python
import pandas as pd

# Read CSV file
df = pd.read_csv('autolog_L48-L50.csv')

# Access columns
time_data = df['Elapsed Time (s)'].values
force_data = df['Force (N)'].values

# Data is now in NumPy arrays, ready for processing
```

#### **Plotting (Matplotlib)**
```python
import matplotlib.pyplot as plt

# Create simple plot
plt.figure(figsize=(10, 6))
plt.plot(time_data, force_data, 'b-', label='Force')
plt.xlabel('Time (s)')
plt.ylabel('Force (N)')
plt.title('Force vs. Time')
plt.legend()
plt.grid(True)
plt.savefig('my_plot.png')
plt.close()
```

#### **Finding Peaks**
```python
# Find maximum value
peak_force = np.max(force_data)

# Find index of maximum
peak_idx = np.argmax(force_data)

# Get time at peak
peak_time = time_data[peak_idx]

print(f"Peak force: {peak_force:.4f} N at time {peak_time:.3f} s")
```

#### **Calculating Derivatives**
```python
# First derivative (rate of change)
first_deriv = np.gradient(force_data, time_data)

# Second derivative (rate of rate of change)
second_deriv = np.gradient(first_deriv, time_data)

# Interpret derivatives:
# - Positive 1st derivative: Force increasing
# - Negative 1st derivative: Force decreasing
# - Positive 2nd derivative: Force decay slowing down
# - Negative 2nd derivative: Force decay speeding up
```

### 8.3 Key Files to Study

Start by reading these files in order:

1. **`adhesion_metrics_calculator.py`**
   - Lines 1-50: Class setup and initialization
   - Lines 200-250: Main calculation function
   - Lines 310-410: Propagation end detection (THE KEY ALGORITHM)
   - Lines 450-550: Work of adhesion calculation

2. **`RawData_Processor.py`**
   - Lines 1-50: Class setup
   - Lines 200-350: Layer boundary detection
   - Lines 400-500: Data preparation

3. **`analysis_plotter.py`**
   - Lines 50-150: Overview plot creation
   - Lines 200-300: Individual layer plots
   - Study the plots to understand what you're looking for

### 8.4 Running Your First Analysis

**Step 1:** Open PowerShell in the project folder
```powershell
cd "C:\Users\ehunt\OneDrive\Documents\Prince\Prince_Segmented_20250926"
```

**Step 2:** Find a test file
```powershell
cd post-processing
ls *.csv
```

**Step 3:** Run analysis on single file
```python
python -c "
from RawData_Processor import RawDataProcessor
from adhesion_metrics_calculator import AdhesionMetricsCalculator
from analysis_plotter import AnalysisPlotter

# Initialize
calc = AdhesionMetricsCalculator()
processor = RawDataProcessor(calc)
plotter = AnalysisPlotter()

# Process file
layers = processor.process_csv('autolog_L48-L50.csv')

# Create plot
import pandas as pd
df = pd.read_csv('autolog_L48-L50.csv')
time = df['Elapsed Time (s)'].values
force = df['Force (N)'].values
smoothed = calc._apply_smoothing(force)

plotter.create_plot(time, force, smoothed, layers, 
                   'Test Analysis', 'test_plot.png')

print(f'Processed {len(layers)} layers')
"
```

**Step 4:** Open `test_plot.png` to see results

### 8.5 Modifying the Algorithm

To test a new propagation end detection method:

1. **Copy the existing function:**
```python
# In adhesion_metrics_calculator.py
def _find_propagation_end_NEW_METHOD(self, smoothed_force, peak_idx, 
                                     positions, motion_end_idx):
    """
    Your new algorithm here.
    
    Args:
        smoothed_force: Array of smoothed force values
        peak_idx: Index where peak force occurs
        positions: Array of stage positions
        motion_end_idx: Index where motion ends
        
    Returns:
        prop_end_idx: Index where propagation ends
    """
    # YOUR CODE HERE
    # ...
    
    return prop_end_idx
```

2. **Replace the call in _calculate_metrics():**
```python
# OLD:
prop_end_idx = self._find_propagation_end_reverse_search(...)

# NEW:
prop_end_idx = self._find_propagation_end_NEW_METHOD(...)
```

3. **Test on sample data:**
```python
python test_new_algorithm.py
```

4. **Compare results:**
```python
# Generate before/after plots
# Check if results make physical sense
# Measure accuracy vs. ground truth
```

### 8.6 Debugging Tips

**Problem:** Code crashes with "IndexError"
- **Cause:** Trying to access array element that doesn't exist
- **Fix:** Check array lengths, use `len(array)` to see size

**Problem:** "ModuleNotFoundError"
- **Cause:** Python can't find imported module
- **Fix:** Ensure you're in correct directory, check `sys.path`

**Problem:** Weird results
- **Cause:** Usually a logic error or wrong assumption
- **Fix:** Add print statements to see intermediate values:
```python
print(f"Peak index: {peak_idx}")
print(f"Search range: {search_start} to {search_end}")
print(f"2nd derivative max: {max_second_deriv}")
```

**Problem:** Plot looks wrong
- **Cause:** Incorrect index mapping or time offset
- **Fix:** Double-check time/index conversions, plot intermediate steps

---

## 9. Glossary

### Technical Terms

**Adhesion:** The tendency of dissimilar materials to cling to each other. In our case, cured resin sticking to FEP film.

**Contact Area:** The surface area where the cured layer touches the film. Larger area = more force needed to separate.

**Crack Propagation:** The process of a separation (crack) spreading across the contact interface. Starts at a point (initiation) and spreads outward.

**DLP (Digital Light Processing):** 3D printing method using projected light to cure resin. Similar to a movie projector for making solid objects.

**FEP Film:** Fluorinated Ethylene Propylene - a Teflon-like transparent film used at the bottom of resin vats. Non-stick but not perfect.

**Gaussian Filter:** A smoothing technique that averages nearby points with weights following a bell curve. Reduces noise but can blur sharp features.

**Median Filter:** A smoothing technique that replaces each point with the middle value of surrounding points. Good for removing outlier spikes.

**Photopolymer:** A liquid resin that hardens when exposed to light (usually UV or blue). The "ink" for our 3D printer.

**Propagation End:** The moment when layer separation is complete. Most difficult metric to detect accurately.

**Savitzky-Golay Filter:** An advanced smoothing technique that fits polynomials to local regions. Preserves peak shapes better than simple averaging.

**Signal-to-Noise Ratio (SNR):** Ratio of meaningful signal to background noise. SNR > 10 is usually acceptable for our purposes.

**Trapezoidal Integration:** A numerical method for calculating area under a curve. We use this to compute work from force-distance data.

### Abbreviations

- **CSV:** Comma-Separated Values (spreadsheet file format)
- **GUI:** Graphical User Interface
- **Hz:** Hertz (cycles per second) - our sampling rate
- **IQR:** Interquartile Range (statistical measure of spread)
- **MAD:** Median Absolute Deviation (robust statistical measure)
- **mJ:** millijoules (energy unit, 1/1000 of a joule)
- **mm:** millimeters (distance unit, 1/1000 of a meter)
- **N:** Newtons (force unit)
- **PNG:** Portable Network Graphics (image file format)
- **SNR:** Signal-to-Noise Ratio
- **STD:** Standard Deviation
- **USB:** Universal Serial Bus (how devices connect to computer)
- **µm:** micrometers (1/1000 of a millimeter)
- **µm/s:** micrometers per second (peel speed unit)

### Units Cheat Sheet

| Quantity | Unit | Symbol | Typical Range |
|----------|------|--------|---------------|
| Force | Newtons | N | 0.01-0.30 |
| Distance | Millimeters | mm | 0.1-10 |
| Time | Seconds | s | 0.1-5 |
| Speed | Micrometers/sec | µm/s | 100-6000 |
| Energy | Millijoules | mJ | 0.5-5.0 |
| Frequency | Hertz | Hz | 50-65 |

---

## Quick Reference: Common Tasks

### Task: Generate plots for a single test
```powershell
cd post-processing
python analyze_single_folder.py "C:\path\to\test\folder"
```

### Task: Process all tests in a batch
```powershell
cd post-processing
python batch_process_steppedcone.py
```

### Task: View a single autolog file
```python
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('autolog_L48-L50.csv')
plt.plot(df['Elapsed Time (s)'], df['Force (N)'])
plt.xlabel('Time (s)')
plt.ylabel('Force (N)')
plt.grid(True)
plt.show()
```

### Task: Test propagation end detection on one layer
```python
from adhesion_metrics_calculator import AdhesionMetricsCalculator
import pandas as pd
import numpy as np

# Load data
df = pd.read_csv('autolog_L48-L50.csv')
time = df['Elapsed Time (s)'].values
force = df['Force (N)'].values
pos = df['Position (mm)'].values

# Calculate
calc = AdhesionMetricsCalculator()
results = calc.calculate_from_arrays(time, pos, force, layer_number=48)

# Check propagation end
print(f"Propagation end time: {results['propagation_end_time']:.3f} s")
print(f"Propagation end position: {results['propagation_end_position']:.3f} mm")
```

---

## Getting Help

### Resources

1. **Existing Documentation:**
   - `HOW_PROPAGATION_END_IS_MEASURED.md` - Detailed algorithm explanation
   - `BATCH_PROCESSING_GUIDE.md` - Post-processing workflow
   - `README.md` - System overview

2. **Code Comments:**
   - All major functions have detailed docstrings
   - Look for `"""triple-quoted strings"""` at function start

3. **Ask Questions:**
   - Evan Hunt (Lead Researcher) - Check-ins every Monday/Friday
   - Lab Slack channel #adhesion-analysis
   - Team meetings Wednesdays 2pm

### Before Asking for Help

1. **Read the error message carefully** - It usually tells you what's wrong
2. **Check if your file paths are correct** - Windows uses backslashes `\`
3. **Make sure you're in the right directory** - Use `pwd` to check
4. **Try a simpler test case** - Does it work with example data?
5. **Google the error** - Someone has probably seen it before

### When Asking for Help

Provide:
1. What you were trying to do
2. What you expected to happen
3. What actually happened
4. The full error message (if any)
5. The code you ran (copy-paste or screenshot)

---

## Conclusion

You're now ready to start improving our adhesion measurement system! Remember:

- **Start simple** - Understand existing code before modifying
- **Test frequently** - Run code on small datasets as you develop
- **Document everything** - Comment your code, write notes
- **Ask questions** - No question is too basic
- **Have fun** - This is real research with real impact!

Your work will directly improve our 3D printing capabilities and contribute to materials science research. We're excited to see what you discover!

**Good luck, and welcome to the team! 🔬🖨️**

---

*Last updated: November 17, 2025 by Evan Hunt*  
*For questions or suggestions, email: ehunt@northwestern.edu*
