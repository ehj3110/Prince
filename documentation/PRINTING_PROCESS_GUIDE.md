# Printing Process Guide

**Complete guide for understanding and monitoring the printing loop, data logging, and real-time analysis**

Last Updated: December 18, 2025

---

## Table of Contents

1. [Print Flow Overview](#print-flow-overview)
2. [Print Modes](#print-modes)
3. [Layer Execution Sequence](#layer-execution-sequence)
4. [Data Logging Systems](#data-logging-systems)
5. [Phase Detection](#phase-detection)
6. [Sandwich Routine](#sandwich-routine)
7. [Real-Time Adhesion Metrics](#real-time-adhesion-metrics)
8. [Monitoring During Printing](#monitoring-during-printing)
9. [Troubleshooting Print Issues](#troubleshooting-print-issues)

---

## Print Flow Overview

### High-Level Print Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PRINT INITIALIZATION                      │
│  - Load image files                                          │
│  - Initialize DLP (pattern mode, set power)                  │
│  - Move stage to reference position                          │
│  - Optional: Pre-calibration (sandwich gap measurement)      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                      LAYER LOOP                              │
│  FOR each layer i in range(num_layers):                      │
│    1. Fetch per-layer parameters                            │
│    2. Calculate target Z position                            │
│    3. EXPOSURE: Display image, UV cure                       │
│    4. LIFT: Peel layer from FEP film                         │
│    5. RETRACT: Move to next layer position                   │
│    6. SANDWICH (optional): Contact & retract from glass      │
│    7. PAUSE: Wait before next layer                          │
│    8. Data logging & adhesion metrics calculation            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    PRINT CLEANUP                             │
│  - Stop all logging threads                                  │
│  - Calculate & save adhesion metrics                         │
│  - Reset DLP to safe state (video mode, power=0)            │
│  - Close data files                                          │
│  - Clear queues and threads                                  │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow During Printing

```
HARDWARE LAYER:
┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│  Force Gauge     │   │   Zaber Stage    │   │   DLP Projector  │
│  (1200 Hz)       │   │   (Position)     │   │   (UV Cure)      │
└────────┬─────────┘   └────────┬─────────┘   └────────┬─────────┘
         │                      │                       │
         └──────────────────────┼───────────────────────┘
                                │
SOFTWARE LAYER:                 ↓
┌─────────────────────────────────────────────────────────────┐
│                  ForceGaugeManager                           │
│  - High-freq sampling (1 ms)                                 │
│  - Dynamic decimation (averages to 25 ms)                    │
│  - Calibration: Force = GAIN × voltage + OFFSET              │
│  - Outputs to: force_data_queue                              │
└─────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────┐
│                    PositionLogger                            │
│  - Reads: force_data_queue, stage position                   │
│  - Phase detection (Exposure, Lift, Retract, Pause, Sandwich)│
│  - Writes: CSV (Time, Position, Force, Phase)                │
│  - Outputs to: position_plot_queue, phase_event_queue        │
└─────────────────────────────────────────────────────────────┘
                                ↓
                    ┌───────────┴───────────┐
                    │                       │
                    ↓                       ↓
         ┌──────────────────┐   ┌──────────────────────┐
         │ SensorDataWindow │   │   PeakForceLogger    │
         │ - Real-time plot │   │ - Buffers layer data │
         │ - GUI updates    │   │ - Calculates metrics │
         │ - User controls  │   │ - Saves per-layer CSV│
         └──────────────────┘   └──────────────────────┘
```

---

## Print Modes

### Continuous Mode (Legacy)

**Description:** Smooth continuous motion during peel, no discrete steps.

**Characteristics:**
- Stage moves continuously from exposure position to peel position
- Single smooth velocity profile
- Simpler control logic
- Less DLP power management needed

**Use Cases:**
- Simple prints with minimal adhesion
- Testing and development
- When discrete step control not required

**Status:** Legacy mode, less commonly used

### Stepped Mode (Recommended)

**Description:** Layer-by-layer discrete movements with DLP power management.

**Characteristics:**
- Discrete exposure → lift → retract sequence per layer
- DLP power set to 0 during peel (prevents background light)
- DLP power restored before next exposure
- Precise control over each phase
- Optimal for adhesion force measurement

**Status Messages During Stepped Mode:**
```
L48: DLP power=0 (background light off)
Stepped L48: Peeling up to 60.5999 mm
SUCCESS L48: Return movement completed
L48: DLP power restored to 255
```

**Use Cases:**
- Production printing (most common)
- Adhesion force research
- High-precision applications
- When background light elimination is critical

### Segmented Mode (Advanced)

**Description:** Multiple sub-exposures per layer with intermediate movements.

**Characteristics:**
- Layer divided into multiple exposure segments
- Partial cure → move → partial cure sequence
- Allows gradient curing strategies
- Complex control logic

**Use Cases:**
- Advanced material research
- Gradient property materials
- Special curing strategies

**Status:** Specialized mode, requires careful parameter tuning

---

## Layer Execution Sequence

### Complete Layer Cycle (Stepped Mode)

#### Phase 0: Pre-Layer Setup

```python
# Fetch per-layer parameters from instruction file
current_exposure_s = self.exposure_time[i]      # Exposure duration
current_thickness_um = self.thickness[i]        # Layer thickness
actual_dlp_power = self.intensity_list[i]       # DLP LED power (0-255)
actual_step_speed_um_s = self.step_speed_list[i] # Peel speed
actual_overstep_microns = self.overstep_distance_list[i] # Peel overshoot
actual_acceleration_um_s2 = self.step_type_list[i] # Stage acceleration
actual_layer_pause_s = self.pause_list[i]       # Pause between layers
actual_sandwich_speed_um_s = self.sandwich_speed_list[i] # Sandwich speed

# Calculate target Z position for this layer
current_target_z_um = reference_position_um - sum(all_previous_layer_thicknesses)

# Calculate peel peak position (overshoot beyond target)
z_peel_peak_um = current_target_z_um - actual_overstep_microns
z_return_pos_um = current_target_z_um  # Final position after retract
```

**What happens:**
- System reads all parameters for current layer from instruction file
- Calculates exact Z positions for all movements
- Prepares DLP and stage for layer execution

---

#### Phase 1: EXPOSURE

```python
# Set DLP power for this layer
self.controller.power(current=actual_dlp_power)

# Set phase for data logging
self._set_current_phase("Exposure")

# Display image on DLP
cv2.imshow(self.window_name, current_layer_image)
cv2.waitKey(1)

# Hold for exposure duration
time.sleep(current_exposure_s)

# Turn off DLP background light before peel
self.controller.power(current=0)  # Prevents light during movement
```

**Purpose:** UV cure the liquid resin to solidify the current layer

**Duration:** Typically 1-10 seconds per layer

**Status Messages:**
```
Layer 48: DLP power set to 255
L48: Phase set to Exposure
L48: DLP power=0 (background light off)
```

**Force/Position Behavior:**
- Force: Near zero (part adhered to both FEP and previous layer)
- Position: Stationary at previous layer's Z position
- Phase Detection: "Exposure" or "Pause" (stationary)

---

#### Phase 2: LIFT (Peeling)

```python
# Set phase for data logging
self._set_current_phase("Lift")

# Start monitoring for adhesion metrics (if PeakForceLogger enabled)
if peak_force_logger:
    peak_force_logger.start_monitoring_for_layer(
        layer_number=i+1,
        z_peel_peak=z_peel_peak_mm,
        z_return_pos=z_return_pos_mm,
        image_path=current_layer_image_path  # For area calculation
    )

# CRITICAL PEEL MOVEMENT
self.axis.move_absolute(
    position=z_peel_peak_um,           # Overshoot position (down/away)
    velocity=actual_step_speed_um_s / 1000.0,  # Peel speed
    acceleration=actual_acceleration_um_s2,
    wait_until_idle=True  # Block until complete
)
```

**Purpose:** Peel the newly cured layer from the FEP film

**Duration:** Typically 2-10 seconds depending on peel speed and distance

**Status Messages:**
```
L48: Phase set to Lift
Stepped L48: Peeling up to 60.5999 mm
PFL: Started monitoring layer 48 (peel: 60.600mm, return: 61.000mm, area: 12.3456mm²)
```

**Force/Position Behavior:**
- **Force Peak:** Maximum tensile force as layer separates from FEP
- **Pre-Initiation:** Force builds before separation begins
- **Propagation:** Force decreases as crack propagates across layer
- **Position:** Moving downward (away from build platform, increasing distance from vat)
- **Phase Detection:** "Lift" (significant downward motion >1mm)

**Critical Measurements (PeakForceLogger):**
- Peak force (N)
- Work of adhesion (mJ) - area under force-distance curve
- Distance to peak (mm) - pre-initiation distance
- Distance to propagate (mm) - propagation distance
- Total peel distance (mm)

---

#### Phase 3: RETRACT (Return to Layer Position)

```python
# Set phase for data logging
self._set_current_phase("Retract")

# Return to target layer position
self.axis.move_absolute(
    position=z_return_pos_um,          # Target layer height
    velocity=actual_step_speed_um_s / 1000.0,
    acceleration=actual_acceleration_um_s2,
    wait_until_idle=True
)

# Restore DLP power for next layer
self.controller.power(current=next_layer_dlp_power)
```

**Purpose:** Return stage to correct position for next layer

**Duration:** Typically 1-5 seconds

**Status Messages:**
```
L48: Phase set to Retract
SUCCESS L48: Return movement completed
L48: DLP power restored to 255
```

**Force/Position Behavior:**
- **Force:** Returns toward zero (no contact)
- **Retraction Force:** Small negative force possible from viscous drag
- **Position:** Moving upward (back toward build platform)
- **Phase Detection:** "Retract" (significant upward motion >1mm)

---

#### Phase 4: SANDWICH (Optional Contact Routine)

**Only executed if:**
- Pre-calibration completed successfully (`measured_gap_mm` is not None)
- Sandwich routine enabled in GUI
- Force gauge calibrated

```python
# Set phase for data logging
self._set_current_phase("Sandwich")

# Calculate force threshold based on layer area and target pressure
target_pressure_pa = 15790  # From pre-calibration (Pa = N/m²)
layer_area_mm2 = 12.34      # From image analysis
contact_force_threshold = -(target_pressure_pa / 1e6) * layer_area_mm2  # Negative for compression

# Choose sandwich type: Adaptive (force-responsive) or Simple (force threshold only)
if adaptive_sandwich_enabled:
    # ADAPTIVE SANDWICH: 3-tier ramped descent with force monitoring
    # See detailed section below
    perform_adaptive_sandwich_routine(...)
else:
    # SIMPLE SANDWICH: Single-speed descent until force threshold
    perform_simple_sandwich_routine(
        target_position=z_return_pos_um,
        gap_estimate=measured_gap_mm,
        contact_force_threshold=contact_force_threshold,
        sandwich_speed=actual_sandwich_speed_um_s
    )
```

**Purpose:** 
- Re-establish contact between part and build platform
- Ensure good adhesion for next layer
- Measure glass gap consistency

**Duration:** Typically 2-5 seconds per sandwich cycle

**Status Messages:**
```
L48: Starting sandwich (Gap:0.523mm)
L48: Pressure mode: 0.015790MPa × 12.34mm² = 0.195N
L48: Speed: 500µm/s
L48: [DESCENT SEG 1/3] Moving 0-33% of gap
L48: [DESCENT SEG 2/3] Moving 33-67% of gap  
L48: [DESCENT SEG 3/3] Moving 67-100% of gap
L48: Glass contact at 60.477mm, Force=-0.198N
L48: [ASCENT] Fast retract to 61.000mm @ 2000µm/s
```

**Force/Position Behavior:**
- **Descent:** Force becomes increasingly compressive (negative)
- **Contact:** Sharp force increase when touching glass
- **Ascent:** Force returns toward zero
- **Position:** Small downward then upward motion (~0.5mm total)
- **Phase Detection:** "Sandwich" (small downward motion <1mm followed by retract)

**See [Sandwich Routine](#sandwich-routine) section for detailed breakdown**

---

#### Phase 5: PAUSE

```python
# Set phase for data logging
self._set_current_phase("Pause")

# Stop monitoring adhesion metrics for this layer
if peak_force_logger:
    peak_force_logger.stop_monitoring_and_log_peak()

# Wait before next layer
time.sleep(actual_layer_pause_s)
```

**Purpose:**
- Allow resin to flow and settle
- Give system time to stabilize
- Ensure adhesion metrics calculation completes

**Duration:** User-configurable, typically 1-5 seconds

**Status Messages:**
```
L48: Phase set to Pause
Layer 48 adhesion metrics:
  Peak Force: 0.234 N
  Work of Adhesion: 1.234 mJ
  Pre-initiation: 0.523 mm
  Propagation: 2.345 mm
```

**Force/Position Behavior:**
- **Force:** Near zero (stationary)
- **Position:** Stationary at target layer height
- **Phase Detection:** "Pause" (stationary for 3+ readings)

---

### Timing Diagram (Single Layer)

```
Time (s) │ Phase      │ Stage Position │ Force (N)   │ DLP Power
─────────┼────────────┼────────────────┼─────────────┼───────────
0.0      │ Exposure   │ 10.000 mm      │  0.00       │ 255
  ↓      │ (3s)       │ (stationary)   │  0.00       │ 255
3.0      │            │                │             │
─────────┼────────────┼────────────────┼─────────────┼───────────
3.0      │ Lift       │ 10.000 mm      │  0.00       │ 0
  ↓      │ (5s)       │    ↓           │  0.05 ↗     │ 0
4.0      │            │  9.500 mm      │  0.15 ↗     │ 0
5.0      │            │  9.000 mm      │  0.25 ← PEAK│ 0
6.0      │            │  8.500 mm      │  0.12 ↘     │ 0
7.0      │            │  8.200 mm      │  0.03 ↘     │ 0
8.0      │            │  8.000 mm      │  0.00       │ 0
─────────┼────────────┼────────────────┼─────────────┼───────────
8.0      │ Retract    │  8.000 mm      │  0.00       │ 0
  ↓      │ (3s)       │    ↑           │ -0.02       │ 0
11.0     │            │  9.000 mm      │  0.00       │ 255
─────────┼────────────┼────────────────┼─────────────┼───────────
11.0     │ Sandwich   │  9.000 mm      │  0.00       │ 255
  ↓      │ (3s)       │    ↓ (0.5mm)   │ -0.10 ↘     │ 255
12.0     │            │  8.500 mm ← GLASS CONTACT    │ 255
  ↓      │            │    ↑ (fast)    │  0.00 ↗     │ 255
14.0     │            │  9.000 mm      │  0.00       │ 255
─────────┼────────────┼────────────────┼─────────────┼───────────
14.0     │ Pause      │  9.000 mm      │  0.00       │ 255
  ↓      │ (2s)       │ (stationary)   │  0.00       │ 255
16.0     │            │                │             │
─────────┴────────────┴────────────────┴─────────────┴───────────
         Next Layer Begins at 16.0s
```

---

## Data Logging Systems

### Three-Tier Logging Architecture

#### 1. Raw CSV Logging (PositionLogger)

**Purpose:** High-fidelity position and force data for entire print

**File:** `PrintingLogs/YYYY-MM-DD/Run_X_sensor_log.csv`

**Columns:**
```
Elapsed Time (s), Position (mm), Force (N), Phase
0.000, 10.000, 0.000, Exposure
0.025, 10.000, 0.001, Exposure
0.050, 10.000, 0.000, Exposure
...
3.000, 10.000, 0.000, Lift
3.025, 9.995, 0.002, Lift
3.050, 9.990, 0.005, Lift
...
```

**Sampling Rate:** 25-100 ms (user configurable, default 25 ms)

**Data Source:**
- Position: Read directly from Zaber stage (`axis.get_position()`)
- Force: Read from `force_data_queue` (ForceGaugeManager output after decimation)
- Phase: Calculated by PositionLogger based on position changes
- Time: Elapsed time since logging started

**When Active:** Entire print duration (all layers)

**Controls:**
- Start/Stop: Manual via Sensor Data Window
- Automatic: Can be triggered by print start

---

#### 2. Layer-Specific Logging (AutomatedLayerLogger)

**Purpose:** Capture detailed data for specific layer ranges of interest

**Configuration File:** `logging_windows.csv`
```
StartLayer,EndLayer
48,50
100,105
200,210
```

**Output Files:** `autolog_LXX-LYY.csv` (same format as raw CSV)

**Example:** `autolog_L48-L50.csv` contains only data from layers 48, 49, 50

**How It Works:**
```python
# At start of each layer
layer_logger.update_current_layer(current_layer=48, current_z=9.0)

# Layer 48 starts → Check logging windows
# (48,50) window active → Start new CSV file
# Layer 48-50 data logged to autolog_L48-L50.csv
# Layer 51 starts → Window ends → Stop logging, close file
```

**Use Cases:**
- Focus analysis on problematic layers
- Reduce data volume (only log interesting regions)
- Compare behavior at different print heights
- Capture transient phenomena at specific layers

---

#### 3. Adhesion Metrics Logging (PeakForceLogger)

**Purpose:** Per-layer adhesion metrics and peak force analysis

**File:** `PrintingLogs/YYYY-MM-DD/Run_X_peak_force_output.csv`

**Columns:**
```
Layer_Number, Peak_Force_N, Work_of_Adhesion_mJ, Initiation_Time_s, Propagation_Duration_s, Total_Duration_s, Distance_to_Peak_mm, Distance_to_Propagate_mm, Total_Peel_Distance_mm, Peak_Retraction_Force_N, Cross_Sectional_Area_mm2
1, 0.234, 1.234, 0.523, 1.234, 2.345, 0.523, 2.345, 3.456, -0.012, 12.3456
2, 0.245, 1.345, 0.534, 1.345, 2.456, 0.534, 2.456, 3.567, -0.013, 12.4567
...
```

**Metrics Explained:**
- **Peak_Force_N:** Maximum tensile force during peel
- **Work_of_Adhesion_mJ:** Energy to separate layer (area under force-distance curve)
- **Initiation_Time_s:** Time from lift start to force peak
- **Propagation_Duration_s:** Time from peak to propagation end
- **Total_Duration_s:** Total time for peel (initiation + propagation)
- **Distance_to_Peak_mm:** Distance traveled before reaching peak force (pre-initiation)
- **Distance_to_Propagate_mm:** Distance for crack propagation
- **Total_Peel_Distance_mm:** Total distance moved during lift phase
- **Peak_Retraction_Force_N:** Maximum compressive force during retract (usually small)
- **Cross_Sectional_Area_mm2:** Layer's solid area from image analysis

**Data Source:**
- Buffered from PositionLogger data during lift phase
- Phase-aware: Only analyzes data during "Lift" phase
- Processed by AdhesionMetricsCalculator (smoothing, peak detection, integration)

**When Calculated:** After each layer's lift+retract completes, during pause phase

**See [Real-Time Adhesion Metrics](#real-time-adhesion-metrics) section for calculation details**

---

### Data Flow Diagram

```
┌───────────────────────────────────────────────────────────────┐
│                    ForceGaugeManager                           │
│  Hardware: 1200 Hz → Decimation (25:1) → Output: 40 Hz       │
└──────────────────────┬────────────────────────────────────────┘
                       │ force_data_queue (40 Hz)
                       ↓
┌───────────────────────────────────────────────────────────────┐
│                    PositionLogger (25 ms loop)                 │
│  - Read force from queue                                       │
│  - Read position from stage                                    │
│  - Detect phase from position                                  │
│  - Output to 3 destinations:                                   │
└──────┬───────────────────┬─────────────────────┬──────────────┘
       │                   │                     │
       │ CSV write         │ position_plot_queue │ phase_event_queue
       │ (if enabled)      │ (for GUI)           │ (for metrics)
       ↓                   ↓                     ↓
┌──────────────┐  ┌─────────────────┐  ┌─────────────────────┐
│ sensor_log   │  │ SensorDataWindow│  │  PeakForceLogger    │
│   .csv       │  │ - Real-time plot│  │  - Buffer layer data│
│              │  │ - Updates 10 Hz │  │  - Calculate metrics│
│ Entire print │  └─────────────────┘  │  - Write peak CSV   │
└──────────────┘                       └──────┬──────────────┘
       ↑                                       │
       │ Also controlled by:                   ↓
       │                               ┌──────────────────────┐
┌──────────────────────┐               │ peak_force_output.csv│
│ AutomatedLayerLogger │               │  Per-layer metrics   │
│ - Layer-specific CSV │               └──────────────────────┘
│ - autolog_LXX-LYY    │
└──────────────────────┘
```

---

## Phase Detection

### What is Phase Detection?

Phase detection automatically identifies what the printer is doing based on **stage position changes**:

- **Exposure:** Stationary (curing)
- **Lift:** Moving down/away (peeling)
- **Retract:** Moving up/back (returning)
- **Pause:** Stationary (waiting)
- **Sandwich:** Small down+up motion (<1mm)

### Why Phase Detection Matters

1. **Accurate Adhesion Analysis:** Only analyze force data during "Lift" phase
2. **Data Organization:** Label CSV data with current operation
3. **Real-Time Monitoring:** Know what's happening without manual observation
4. **Automated Layer Boundaries:** Detect start/end of each layer automatically

### Detection Algorithm (PositionLogger)

```python
def _determine_phase(self, current_position):
    """
    Determines phase based on position changes.
    
    Thresholds:
    - Position change < 0.002 mm → Stationary
    - 3+ stationary readings → Pause
    - Down motion > 1mm total → Lift
    - Up motion > 1mm total → Retract
    - Down motion < 1mm → Sandwich
    """
    
    # Calculate change from previous reading
    position_change = current_position - self._previous_position
    abs_change = abs(position_change)
    
    # Check if stationary
    if abs_change < 0.002:  # mm threshold
        self._stationary_count += 1
        
        if self._stationary_count >= 3:
            return "Pause"
    
    else:  # Motion detected
        self._stationary_count = 0
        
        # Calculate total distance since motion started
        total_distance = abs(current_position - self._position_at_motion_start)
        
        # Classify based on direction and magnitude
        if position_change < 0:  # Moving down
            if total_distance > 1.0:  # mm
                return "Lift"
            else:
                return "Sandwich"
        
        else:  # Moving up
            if total_distance > 1.0:  # mm
                return "Retract"
            else:
                return "Pause"  # Small upward adjustment
```

### Phase Transition Example

```
Position (mm)  │  Change (mm)  │  Total (mm)  │  Phase
───────────────┼───────────────┼──────────────┼──────────────
10.000         │   0.000       │    0.00      │  Pause (stationary)
10.000         │   0.000       │    0.00      │  Pause
10.000         │   0.000       │    0.00      │  Pause
9.995          │  -0.005       │    0.01      │  Sandwich (small down)
9.990          │  -0.005       │    0.01      │  Sandwich
9.950          │  -0.040       │    0.05      │  Sandwich
9.850          │  -0.100       │    0.15      │  Sandwich
9.500          │  -0.350       │    0.50      │  Sandwich
9.000          │  -0.500       │    1.00      │  Lift (crossed 1mm threshold)
8.500          │  -0.500       │    1.50      │  Lift
8.000          │  -0.500       │    2.00      │  Lift
8.000          │   0.000       │    0.00      │  Pause (stationary)
8.000          │   0.000       │    0.00      │  Pause
8.005          │  +0.005       │    0.01      │  Sandwich (small up)
8.050          │  +0.045       │    0.05      │  Sandwich
8.500          │  +0.450       │    0.50      │  Sandwich
9.000          │  +0.500       │    1.00      │  Retract (crossed 1mm threshold)
9.500          │  +0.500       │    1.50      │  Retract
10.000         │  +0.500       │    2.00      │  Retract
10.000         │   0.000       │    0.00      │  Pause (stationary)
```

### Phase-Aware Data Analysis

**AdhesionMetricsCalculator receives:**
- `lifting_start_idx`: Buffer index where "Lift" phase began
- Only analyzes data from lift start to peel peak

**Benefits:**
- Excludes pre-lift forces (exposure, sandwich compression)
- Accurate baseline detection (starts from zero force at lift beginning)
- Correct work of adhesion (only integrates peel region)
- No contamination from retract phase

**Before Phase Awareness:**
```
Problem: Analysis included sandwich compression forces
Result: Negative work of adhesion, incorrect peak detection
```

**After Phase Awareness:**
```
Solution: Analysis starts exactly when lift begins
Result: Accurate metrics, repeatable measurements
```

---

## Sandwich Routine

### Overview

The sandwich routine is a **controlled contact sequence** that:
1. Moves stage downward until glass contact detected (force threshold)
2. Immediately retracts to layer position
3. Ensures good adhesion between part and build platform

### When Sandwich Runs

**Requirements (ALL must be met):**
- ✅ Pre-calibration completed (glass gap measured)
- ✅ Force gauge calibrated
- ✅ Sandwich enabled in GUI settings
- ✅ After retract phase, before pause

**Skip Conditions:**
- Pre-calibration failed or disabled
- Force gauge not calibrated
- Sandwich disabled by user
- First layer (no previous layer to adhere to)

### Two Sandwich Modes

#### Simple Sandwich (Force Threshold)

**Method:** Single-speed descent until force threshold reached

**Algorithm:**
```python
1. Start at z_return_pos (layer position)
2. Move down at sandwich_speed (e.g., 500 µm/s)
3. Monitor force continuously (20 ms intervals)
4. When force <= threshold: STOP immediately
5. Record glass position
6. Move up (fast, 4× speed) to z_return_pos
```

**Parameters:**
- `sandwich_speed`: User-defined (typically 200-500 µm/s)
- `contact_force_threshold`: Calculated from pressure × area
- `measured_gap`: From pre-calibration (e.g., 0.523 mm)

**Status Messages:**
```
L48: Starting sandwich (Gap:0.523mm)
L48: Pressure mode: 0.015790MPa × 12.34mm² = 0.195N
L48: Speed: 500µm/s
L48: Glass contact at 60.477mm, Force=-0.198N
L48: [ASCENT] Fast retract to 61.000mm @ 2000µm/s
```

---

#### Adaptive Sandwich (Force-Responsive)

**Method:** 3-tier ramped descent with adaptive force response

**Algorithm:**
```python
1. Calculate 3-tier speeds:
   - Tier 1: Base speed (0-33% of gap)
   - Tier 2: Base/3 (33-67% of gap)
   - Tier 3: Base/9 (67-100% of gap - slowest)

2. Define force thresholds:
   - Adaptive stop: 75% of contact threshold
   - Relaxation target: 50% of contact threshold
   - Hard failsafe: 5.0 N absolute (200%)

3. Descent with monitoring:
   FOR each tier (33%, 67%, 100% of gap):
     - Move toward tier target at tier speed
     - Monitor force every 20 ms
     
     IF force >= Hard failsafe (5.0 N):
       → EMERGENCY STOP, raise exception
     
     IF force >= Adaptive stop (75%):
       → Stop movement
       → Wait up to 3 seconds for relaxation
       
       IF force relaxes to <50% OR 3s timeout:
         → Calculate new base speed (slower)
         → Continue to next tier at reduced speed
       
       ELSE:
         → Assume at glass, exit descent
     
     IF reached tier target:
       → Continue to next tier

4. Fast ascent (4× base speed) back to layer position
```

**Benefits:**
- **Gentler contact:** Gradual speed reduction as approaching glass
- **Adaptive response:** Slows down if force builds too quickly
- **Safety:** Multiple force thresholds prevent damage
- **Learning:** Adjusts speed for subsequent layers

**Status Messages:**
```
L48: Using ADAPTIVE sandwich routine
L48: ADAPTIVE SANDWICH - 3-Tier Ramping
L48: Speeds: 500/167/56µm/s, Gap:0.523mm
L48: Pressure thresholds: Adaptive=75% (0.146N), Relax=50% (0.098N), HARD FAILSAFE=200% (5.000N)
L48: [DESCENT SEG 1/3] 61.000mm → 60.826mm @ 500µm/s (0-33%)
L48: [DESCENT SEG 1/3 DONE] Reached: 60.826mm
L48: [DESCENT SEG 2/3] 60.826mm → 60.652mm @ 167µm/s (33-67%)
L48: [DESCENT SEG 2/3 DONE] Reached: 60.652mm
L48: [DESCENT SEG 3/3] 60.652mm → 60.477mm @ 56µm/s (67-100%)
L48: *** ADAPTIVE STOP *** Force=-0.151N at 60.490mm
L48: Waiting for force relaxation (target: ≥-0.098N or 3s)...
L48: Force relaxed to -0.085N after 1.23s
L48: Adaptive iteration 1: Speed reduced 56µm/s → 47µm/s
L48: [DESCENT CONTINUE] 60.490mm → 60.477mm @ 47µm/s
L48: Glass contact detected at 60.477mm, Force=-0.198N
L48: [ASCENT] Fast retract to 61.000mm @ 2000µm/s
L48: Adaptive sandwich SUCCEEDED (1 iterations)
```

**Adaptive Speed Evolution:**
```
Layer 1: 500 µm/s (user setting)
  → Force builds early → Reduced to 425 µm/s for next layer

Layer 2: 425 µm/s (adaptive)
  → Good contact → Maintained for next layer

Layer 3: 425 µm/s (adaptive)
  → Force builds → Reduced to 350 µm/s for next layer

...and so on, adapting to material behavior
```

---

### Pressure-Based Contact Threshold

**Why Pressure Instead of Absolute Force?**

Problem: Different layer sizes have different contact areas
- Small layer (10 mm²): 0.16 N threshold appropriate
- Large layer (50 mm²): 0.16 N threshold too gentle (under-pressured)

Solution: **Constant pressure across all layers**

**Calculation:**
```python
# Set during pre-calibration
target_pressure_pa = 15790  # Pascal (N/m²)

# For each layer during printing
layer_area_mm2 = calculate_from_image(layer_image)  # e.g., 12.34 mm²
target_pressure_mpa = target_pressure_pa / 1e6      # Convert to MPa (N/mm²)
contact_force_threshold = -(target_pressure_mpa * layer_area_mm2)  # Negative for compression
```

**Example:**
```
Pre-calibration (Build platform Ø6.35mm):
  Area = π × (6.35/2)² = 31.67 mm²
  Force = 0.5 N
  Pressure = 0.5 N / 31.67 mm² = 0.015790 MPa = 15790 Pa

Layer 10 (Small feature, 10 mm²):
  Threshold = 0.015790 MPa × 10 mm² = 0.158 N

Layer 50 (Large feature, 50 mm²):
  Threshold = 0.015790 MPa × 50 mm² = 0.790 N

Result: Same pressure, appropriate force for each layer size
```

---

### Sandwich Safety Features

**Multi-Level Protection:**

1. **Soft Limit (75%):** Adaptive stop, allows relaxation
2. **Hard Limit (100%):** Contact threshold, target pressure
3. **Failsafe (200%):** 5.0 N absolute, emergency stop

**Travel Limits:**
- Won't search more than 0.5 mm beyond estimated gap
- Prevents runaway if glass gap incorrect

**Force Monitoring:**
- Reads force every 20 ms during descent
- Immediate stop when threshold crossed (<40 ms response)

**Graceful Degradation:**
- If sandwich fails: Print continues (warning logged)
- Won't abort entire print due to sandwich issue
- User can disable sandwich mid-print if needed

---

## Real-Time Adhesion Metrics

### AdhesionMetricsCalculator

**Purpose:** Calculate scientifically meaningful adhesion metrics from force-distance data

**Module:** `support_modules/adhesion_metrics_calculator.py`

**Used By:**
- PeakForceLogger (during printing)
- Post-processing analysis scripts
- Batch processing pipelines

### Calculation Pipeline

```
1. RAW DATA INPUT
   ↓
   Arrays: time[], position[], force[]
   Phase index: lifting_start_idx (where "Lift" began)
   
2. PHASE-AWARE EXTRACTION
   ↓
   Extract only data from lifting_start_idx to end
   Result: Clean peel data without pre-lift forces
   
3. TWO-STEP FILTERING
   ↓
   Step 1: Median filter (kernel=5) → Remove outliers/spikes
   Step 2: Savitzky-Golay (window=9, order=2) → Smooth for derivatives
   
4. BASELINE DETECTION
   ↓
   Find first sustained rise above threshold
   Threshold: 0.002× peak force or 0.01 N minimum
   
5. PEAK FORCE DETECTION
   ↓
   Maximum force in lifting phase
   Location: Index and position of maximum
   
6. PROPAGATION END DETECTION
   ↓
   Method: First derivative crosses zero after peak
   Indicates crack propagation complete
   
7. WORK OF ADHESION
   ↓
   Integrate force × distance from baseline to propagation end
   Trapezoidal rule: W = Σ(F_avg × Δx)
   Units: Joules → millijoules (mJ)
   
8. DISTANCE METRICS
   ↓
   - Pre-initiation: Baseline to peak
   - Propagation: Peak to propagation end
   - Total: Baseline to propagation end
   
9. TIME METRICS
   ↓
   - Initiation: Time from lift start to peak
   - Propagation: Time from peak to propagation end
   - Total: Initiation + propagation
   
10. RETRACTION FORCE
    ↓
    Minimum (most negative) force after peel
    Usually small (~0.01-0.05 N)
```

### Key Metrics Explained

#### 1. Peak Force (N)

**Definition:** Maximum tensile force during peel

**Physical Meaning:** 
- Strength of adhesion between layer and FEP
- Highest stress during separation
- Indicates bond strength

**Typical Values:**
- Small layers (10 mm²): 0.1-0.3 N
- Medium layers (30 mm²): 0.3-0.8 N
- Large layers (100 mm²): 1.0-3.0 N

**Influences:**
- Layer area (larger → higher peak)
- Peel speed (faster → higher peak)
- Material stiffness
- FEP surface energy
- Temperature

---

#### 2. Work of Adhesion (mJ)

**Definition:** Total energy required to separate layer from FEP

**Calculation:** 
```
W = ∫ F(x) dx  from baseline to propagation end
W = Σ [(F_i + F_i+1)/2] × (x_i+1 - x_i)  [Trapezoidal rule]
```

**Physical Meaning:**
- Energy dissipated during crack propagation
- Combines force magnitude and distance
- True measure of adhesive bond energy

**Typical Values:**
- Small layers: 0.5-2.0 mJ
- Medium layers: 2.0-8.0 mJ
- Large layers: 8.0-30.0 mJ

**Scaling:**
- Linear with layer area (W ∝ Area)
- Independent of peel speed (for slow peels)
- Fundamental material property

**Use Cases:**
- Compare different resins
- Optimize FEP surface treatment
- Characterize temperature effects
- Quality control (layer-to-layer consistency)

---

#### 3. Pre-Initiation Distance (mm)

**Definition:** Distance traveled from baseline to peak force

**Physical Meaning:**
- Elastic deformation before crack initiation
- Indicates material compliance
- Shorter = stiffer system

**Typical Values:**
- Stiff resins: 0.2-0.5 mm
- Flexible resins: 0.5-1.5 mm
- High-temperature: 1.0-3.0 mm

**Influences:**
- Resin elastic modulus (E)
- Layer thickness
- Peel speed
- Temperature

---

#### 4. Propagation Distance (mm)

**Definition:** Distance from peak force to propagation end

**Physical Meaning:**
- Length of crack propagation phase
- Distance over which bond breaks
- Related to fracture toughness

**Typical Values:**
- Small layers: 1.0-3.0 mm
- Medium layers: 2.0-5.0 mm
- Large layers: 3.0-10.0 mm

**Influences:**
- Layer area (larger → longer propagation)
- Peel angle
- Material fracture toughness
- FEP compliance

---

#### 5. Cross-Sectional Area (mm²)

**Definition:** Solid area of layer calculated from image

**Calculation:**
```python
# Load layer image (black/white, 0/255)
image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

# Count white pixels
white_pixel_count = np.sum(image == 255)

# Calculate area
PIXEL_SIZE_MM = 0.004005  # mm per pixel (calibrated)
PIXEL_AREA_MM2 = PIXEL_SIZE_MM ** 2
area_mm2 = white_pixel_count * PIXEL_AREA_MM2
```

**Use Cases:**
- Normalize peak force: Stress = Force / Area
- Normalize work: Energy density = Work / Area
- Calculate sandwich pressure threshold
- Compare layers of different sizes

**Typical Values:**
- Small features: 5-20 mm²
- Medium parts: 20-100 mm²
- Large parts: 100-500 mm²
- Build platform: 31.67 mm² (Ø6.35mm circle)

---

### Metric Validation

**Quality Checks:**
```python
# Check 1: Peak force positive
if peak_force <= 0:
    return None, "No tensile force detected"

# Check 2: Work of adhesion positive
if work_of_adhesion <= 0:
    return None, "Work of adhesion cannot be negative"

# Check 3: Distances reasonable
if distance_to_peak > 10.0:  # mm
    warning("Pre-initiation distance unusually large")

# Check 4: Propagation detected
if propagation_end_idx == peak_idx:
    warning("Propagation end not detected, using last data point")
```

**Typical Failure Modes:**
- Force gauge not calibrated → Force = 0
- Phase detection wrong → Analyzing wrong data
- Too few data points → Noisy metrics
- Lift distance too short → Truncated peel

---

## Monitoring During Printing

### Real-Time GUI (SensorDataWindow)

**What You See:**

```
┌─────────────────────────────────────────────────────────────┐
│  Sensor Readout Panel                                        │
├─────────────────────────────────────────────────────────────┤
│  Position: 9.523 mm          Force: 0.234 N                 │
├─────────────────────────────────────────────────────────────┤
│  [Live Plot: Position (blue) and Force (red) vs Time]       │
│                                                              │
│   0.3 N┤     ╱╲                  ╱╲                         │
│        │    ╱  ╲                ╱  ╲                        │
│   0.2 N┤   ╱    ╲              ╱    ╲                       │
│        │  ╱      ╲            ╱      ╲                      │
│   0.1 N┤ ╱        ╲          ╱        ╲                     │
│        │╱          ╲________╱          ╲___                 │
│   0.0 N┼─────────────────────────────────────────────────   │
│        0s        10s       20s        30s        40s        │
│                                                              │
│  Current Phase: Lift                                        │
│  Layer: 48 / 150                                            │
├─────────────────────────────────────────────────────────────┤
│  [Start Recording] [Stop Recording] [Clear Plot]            │
│  Sampling Rate: 25 ms  [Calibrate Force Gauge]             │
└─────────────────────────────────────────────────────────────┘
```

**Update Rate:** 10 Hz (100 ms GUI refresh)

**Plot Features:**
- Scrolling window (shows last 5000 points)
- Dual Y-axes (position on left, force on right)
- Auto-scaling
- Clear/reset button
- Export plot image

---

### Console Status Messages

**Normal Print Sequence:**
```
Print thread started.
Moved to reference: 0.0 mm
OpenCV window initialized.
DLP set to pattern mode, power: 255.
Layer 48: DLP power set to 255.
L48: Phase set to Exposure
L48: DLP power=0 (background light off)
L48: Phase set to Lift
Stepped L48: Peeling up to 60.600 mm
PFL: Started monitoring layer 48 (peel: 60.600mm, return: 61.000mm, area: 12.3456mm²)
L48: Phase set to Retract
SUCCESS L48: Return movement completed
L48: DLP power restored to 255
L48: Phase set to Sandwich
L48: Starting sandwich (Gap:0.523mm)
L48: Glass contact at 60.477mm, Force=-0.198N
L48: Phase set to Pause
Layer 48 adhesion metrics:
  Peak Force: 0.234 N
  Work of Adhesion: 1.234 mJ
  Pre-initiation: 0.523 mm
  Propagation: 2.345 mm
```

**Warning Messages:**
```
Warning: Requested accel 0.100 mm/s² (100 µm/s²) is below practical minimum. Using 800 µm/s².
L48: Sandwich skipped - force gauge not calibrated
Warning: Pre-initiation distance unusually large: 5.234 mm
```

**Error Messages:**
```
Error: No layers loaded. Aborting print.
L48: Could not set DLP power: Device not responding
L48: *** ADAPTIVE STOP *** Force=-0.151N at 60.490mm
L48: *** HARD FORCE FAILSAFE *** Force=-5.234N exceeded 200% limit (5.000N)
```

---

### What to Watch For

#### Healthy Print Indicators

✅ **Force Profile:**
- Smooth peak during each lift
- Peak returns to ~0 N after propagation
- Consistent peak heights layer-to-layer
- No erratic spikes

✅ **Phase Transitions:**
- Clean transitions between phases
- "Lift" phase clearly defined
- Consistent timing per layer

✅ **Adhesion Metrics:**
- Peak force scales with layer area
- Work of adhesion relatively stable
- Pre-initiation distance consistent
- Propagation distance reasonable

✅ **Status Messages:**
- "SUCCESS" messages for movements
- Adhesion metrics calculated each layer
- No error or warning messages
- DLP power commands successful

---

#### Problem Indicators

⚠️ **Force Issues:**
- Peak force = 0 N → Force gauge not calibrated
- Peak force increasing rapidly → FEP degradation
- Erratic spikes → Electrical noise or stage vibration
- Negative work of adhesion → Phase detection wrong

⚠️ **Stage Issues:**
- "Timeout" messages → Stage stall or connection lost
- Jerky motion → Acceleration too high
- Missed target positions → Mechanical binding

⚠️ **DLP Issues:**
- "Could not set DLP power" → USB connection issue
- Black screen during print → DLP stuck in pattern mode
- No UV light → Power = 0 not restored

⚠️ **Sandwich Issues:**
- "Sandwich skipped" → Force gauge not calibrated
- "HARD FORCE FAILSAFE" → Threshold too high or glass gap wrong
- "Adaptive iterations exceeded" → Speed too fast for material

---

## Troubleshooting Print Issues

### Issue: Layers Not Adhering to Build Platform

**Symptoms:**
- Part falls off during print
- First few layers successful, then detachment
- Force measurements show decreasing peak

**Possible Causes:**

1. **Sandwich routine disabled or failing**
   - Solution: Enable sandwich, verify force gauge calibrated
   - Check: Pre-calibration successful, glass gap measured

2. **Insufficient sandwich force**
   - Solution: Increase contact force threshold (higher pressure)
   - Try: 0.5 N → 0.8 N for build platform, scale proportionally

3. **Peel force exceeds adhesion to platform**
   - Solution: Reduce peel speed, use shorter overstep
   - Try: 500 µm/s → 300 µm/s, 500 µm → 200 µm overstep

4. **Build platform not level**
   - Solution: Run camera calibration, check tilt angles
   - Target: <1° tilt on both axes

---

### Issue: Excessive Peel Forces

**Symptoms:**
- Peak force >5 N
- Stage stalls during lift
- FEP film damage
- Print failure mid-layer

**Possible Causes:**

1. **Peel speed too fast**
   - Solution: Reduce step_speed
   - Try: 1000 µm/s → 500 µm/s → 200 µm/s

2. **Large layer area**
   - Expected: Peak scales with area (F ∝ A)
   - Solution: Not a problem if force gauge range adequate
   - Consider: Segmented exposure for very large layers

3. **FEP degradation**
   - Solution: Replace FEP film
   - Check: Cloudy appearance, scratches, permanent deformation

4. **Resin over-cured**
   - Solution: Reduce exposure time or DLP power
   - Check: Part dimensions, surface quality

---

### Issue: Inconsistent Adhesion Metrics

**Symptoms:**
- Peak force varies wildly layer-to-layer
- Work of adhesion fluctuates >50%
- Some layers show zero force

**Possible Causes:**

1. **Force gauge calibration drift**
   - Solution: Re-calibrate force gauge mid-print
   - Check: Zero-force reading when stage stationary

2. **Phase detection incorrect**
   - Solution: Verify phase transitions in CSV file
   - Check: "Lift" phase clearly separated from exposure

3. **Electrical noise**
   - Solution: Increase decimation factor, slower sampling rate
   - Check: Force readings when stage completely idle

4. **Automated layer logging interfering**
   - Solution: Stop/start logging creates transients
   - Check: CSV gaps when logging windows change

---

### Issue: Sandwich Routine Failing

**Symptoms:**
- "Sandwich routine timed out"
- "Glass contact not detected"
- "HARD FORCE FAILSAFE" triggered

**Possible Causes:**

1. **Glass gap changed**
   - Solution: Re-run pre-calibration
   - Check: Compare measured_gap to initial value

2. **Force threshold too high**
   - Solution: Reduce target pressure
   - Try: 15790 Pa → 10000 Pa

3. **Force gauge saturated**
   - Solution: Check force range, may need different load cell
   - Check: Maximum rated force vs applied force

4. **Adaptive sandwich too aggressive**
   - Solution: Switch to simple sandwich
   - Or: Increase relaxation threshold, allow more time

---

### Issue: Print Stops Mid-Layer

**Symptoms:**
- Print halts with error message
- Stage position frozen
- DLP black screen

**Possible Causes:**

1. **Stage timeout**
   - Solution: Check USB connection, reduce acceleration
   - Check: Stage responds to manual jog commands

2. **Force failsafe triggered**
   - Solution: Review force threshold settings
   - Check: Console for "HARD FORCE FAILSAFE" message

3. **DLP communication lost**
   - Solution: Check USB cable, power cycle DLP
   - Check: DLP controller object valid

4. **Memory/resource exhaustion**
   - Solution: Clear plot data more frequently
   - Check: Task Manager for memory usage

---

### Issue: Data Not Being Logged

**Symptoms:**
- CSV file empty or missing
- Peak force output shows no data
- "Layer X adhesion metrics: (none)" messages

**Possible Causes:**

1. **PeakForceLogger not enabled**
   - Solution: Check "Enable Peak Force Logging" checkbox
   - Verify: Sensor Data Window → Peak Force Logger section

2. **Force gauge not calibrated**
   - Solution: Calibrate before starting print
   - Check: Force readings show real values, not zeros

3. **Phase detection not working**
   - Solution: Verify PositionLogger running
   - Check: CSV shows "Phase" column populated

4. **File permissions**
   - Solution: Check write permissions on log directory
   - Try: Run as administrator, choose different directory

---

### Issue: GUI Freezing After Print

**Symptoms:**
- Can't click "Clear Plot" after print
- GUI unresponsive for 30+ seconds
- Must force-close application

**Possible Causes:**

1. **Background threads not shut down**
   - Solution: Update to latest version with `_cleanup_print_resources()`
   - Check: Console shows "PeakForceLogger shut down" message

2. **Queue accumulation**
   - Solution: Queues should be cleared at print end
   - Check: "Plot queue cleared" message appears

3. **Analysis thread blocking**
   - Solution: PeakForceLogger uses worker thread for analysis
   - Check: Analysis completes before print end

**Workaround:** Wait 1-2 minutes for threads to timeout naturally

---

## Advanced Topics

### Custom Layer Sequences

You can define per-layer parameters in the instruction file:

```
# Format: Layer, Exposure(s), Thickness(µm), Intensity(0-255), Speed(µm/s), Overstep(µm), Accel(mm/s²), Pause(s), SandwichSpeed(µm/s)

1, 5.0, 50, 255, 300, 200, 5.0, 2.0, 500
2, 3.0, 50, 255, 400, 300, 5.0, 2.0, 500
3, 3.0, 50, 200, 500, 400, 8.0, 1.5, 600
...
```

### Dynamic Parameter Adjustment

During printing, some parameters can be adjusted:
- ❌ **Cannot change:** Exposure time, thickness (would corrupt layer alignment)
- ✅ **Can change:** DLP power, peel speed, pause time (live updates)

### Experimental Conditions Tracking

Use ExperimentalConditionsWindow to record metadata:
- Resin type and batch number
- Temperature and humidity
- Print date and operator
- Special notes

This metadata is saved with print data for analysis correlation.

---

## Summary

**Key Takeaways:**

1. **Print Flow:** Init → Layer Loop (Exposure → Lift → Retract → Sandwich → Pause) → Cleanup

2. **Data Logging:** Three-tier system (Raw CSV, Layer-specific, Adhesion metrics)

3. **Phase Detection:** Automatic identification of print operations from position

4. **Sandwich Routine:** Controlled glass contact for platform adhesion

5. **Adhesion Metrics:** Real-time calculation of peak force, work of adhesion, distances

6. **Monitoring:** Real-time GUI, console messages, CSV data files

7. **Troubleshooting:** Systematic approach to identifying and fixing print issues

**For More Information:**
- Pre-print setup: See [PRE_PRINT_SETUP_GUIDE.md](PRE_PRINT_SETUP_GUIDE.md)
- Post-processing: See post-processing/README.md
- Technical details: See documentation/technical/

---

**Last Updated:** December 18, 2025  
**Guide Version:** 1.0  
**Software:** Prince Segmented 3D Printer Control Software
