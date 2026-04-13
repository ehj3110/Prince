# Support Modules Documentation

This directory contains the core support libraries and utilities that power the Prince 3D printing system. Each module handles a specific aspect of hardware control, data acquisition, analysis, or system management.

## Table of Contents

- [Hardware Control Modules](#hardware-control-modules)
- [Data Logging & Analysis Modules](#data-logging--analysis-modules)
- [Motion Control](#motion-control)
- [Specialized Routines](#specialized-routines)
- [Utilities](#utilities)
- [Module Dependencies](#module-dependencies)

---

## Hardware Control Modules

### `pycrafter9000.py`
**Purpose:** Low-level control interface for Texas Instruments DLP LightCrafter 9000 projector

**Key Functions:**
- `changemode(mode)` - Switch between video (3) and pattern (4) modes
- `power(current=0-255)` - Set LED illumination power
- `patternmode(fps, bitdepth, num_pats)` - Configure pattern projection
- `startsequence()` / `stopsequence()` - Control pattern sequence playback
- `loadsequence(image_array)` - Upload image patterns via USB

**Usage:**
```python
from support_modules import pycrafter9000
controller = pycrafter9000.dmd()
controller.changemode(4)  # Pattern mode
controller.power(current=128)  # 50% power
controller.patternmode(fps=60, bitdepth=1, num_pats=24)
```

**Critical Notes:**
- Always set power to 0 BEFORE changing modes to prevent LED flash
- Use `stopsequence()` before mode changes
- Pattern mode (4) is for printing, video mode (3) is for idle/HDMI

---

### `ForceGaugeManager.py`
**Purpose:** Manages Phidgets force gauge with high-frequency data acquisition and smart decimation

**Key Features:**
- Threaded data acquisition (up to 1200 Hz)
- Automatic USB device detection and reconnection
- Dynamic decimation for manageable data rates
- Real-time force statistics (mean, std, min, max)
- Thread-safe data access via queue

**Main Class:** `ForceGaugeManager`

**Key Methods:**
- `connect()` - Initialize connection to force gauge
- `disconnect()` - Clean shutdown
- `calibrate()` - Zero the force reading (tare)
- `get_latest_force()` - Get most recent force value
- `get_statistics()` - Get running statistics
- `set_decimation_factor(factor)` - Adjust data decimation

**Usage:**
```python
force_manager = ForceGaugeManager(data_queue=my_queue)
force_manager.connect()
force_manager.calibrate()  # Zero with no load
current_force = force_manager.get_latest_force()
```

**Decimation System:**
- Reduces high-frequency data to manageable rate
- Default: 10x decimation (1200 Hz → 120 Hz)
- Preserves peak force detection
- Reduces file sizes and processing time

---

### `motion_controller.py`
**Purpose:** Unified motion control for Zaber stage with 2-stage symmetric smooth motion profiles

**Architecture:**

```
MotionController
├── Basic Motion
│   ├── move_absolute(position)
│   ├── move_relative(distance)
│   └── get_position()
│
├── Smooth Lifting (2-stage)
│   ├── Stage 1: 50μm at 100μm/s (gentle break)
│   └── Stage 2: Remaining at base velocity
│
└── Smooth Retraction (2-stage)
    ├── Stage 1: Most distance at base velocity
    └── Stage 2: Last 200μm at 100μm/s (gentle landing)
```

**Configuration:**
```python
smooth_lift_config = {
    'stage1_distance_um': 50,
    'stage1_velocity_um_s': 100,
}

smooth_retraction_config = {
    'stage1_distance_um': 200,
    'stage1_velocity_um_s': 100,
}
```

**Phase Callbacks:**
Reports motion phases for data logging:
- `Lift-Stage1`, `Lift-Stage2`
- `Retract-Stage1`, `Retract-Stage2`

**Key Methods:**
- `execute_lift(start_pos_um, end_pos_um, base_velocity_um_s, phase_callback)`
- `execute_retraction(start_pos_um, end_pos_um, base_velocity_um_s, phase_callback)`

**Usage:**
```python
def my_phase_callback(phase_name):
    print(f"Motion phase: {phase_name}")

motion_ctrl.execute_lift(
    start_pos_um=10000,
    end_pos_um=11000,
    base_velocity_um_s=500,
    phase_callback=my_phase_callback
)
```

**Critical Notes:**
- Inverted stage: Higher position values = downward in real space
- Always use micrometers (μm) for distances
- Phase callbacks enable synchronized data logging

---

## Data Logging & Analysis Modules

### `PositionLogger.py`
**Purpose:** Threaded CSV logger for position, force, time, and phase data

**Data Format:**
```csv
Time (s),Position (mm),Force (N),Phase
Opened from main Rush GUI via sensor panel buttons.
0.001,10.000,0.016,Exposure
Rush_Segmented_VideoPattern.py
```
5. **Add import to `Rush_Segmented_VideoPattern.py`** if needed
**Key Features:**
- High-frequency logging (configurable rate)
- Thread-safe queue-based architecture
- Automatic file creation and management
- Phase label integration
- Graceful shutdown with flush

**Main Class:** `PositionLogger`

**Key Methods:**
- `start(csv_filename)` - Begin logging to file
- `update_phase(phase_name)` - Set current phase label
- `stop()` - Stop logging and close file

**Usage:**
```python
logger = PositionLogger(
    axis=stage_axis,
    force_gauge_manager=force_manager,
    sampling_rate_hz=100
)
logger.start("autolog_Print1.csv")
logger.update_phase("Lift-Stage1")
# ... printing happens ...
logger.stop()
```

**Phase Labels:**
- `Exposure`, `Pause`, `Sandwich`
- `Lift-Stage1`, `Lift-Stage2`
- `Retract-Stage1`, `Retract-Stage2`

---

### `AutomatedLayerLogger.py`
**Purpose:** Extracts and saves layer-specific data from continuous logging

**Functionality:**
- Monitors main autolog CSV file
- Detects layer boundaries from phase transitions
- Extracts data for individual layers
- Saves to separate layer-specific CSV files
- Generates file naming: `autolog_L##-L##.csv`

**Key Methods:**
- `start_logging(layer_number)` - Begin tracking a layer
- `stop_and_save_layer(layer_number)` - Extract and save layer data
- `finalize_logging()` - Complete extraction process

**Output Files:**
```
autolog_L1-L1.csv    # Layer 1
autolog_L2-L2.csv    # Layer 2
autolog_L48-L50.csv  # Layers 48-50 (batch)
```

---

### `PeakForceLogger.py`
**Purpose:** Real-time peak force detection and adhesion metrics calculation during printing

**Key Features:**
- Monitors force data stream in real-time
- Detects peak forces per layer
- Calculates work of adhesion
- Measures peeling distances
- Saves to adhesion metrics CSV

**Main Class:** `PeakForceLogger`

**Key Methods:**
- `start_new_layer(layer_num)` - Initialize layer tracking
- `update_phase(phase_name)` - Track motion phases
- `add_data_point(time, position, force)` - Process data point
- `finalize_layer()` - Complete layer analysis
- `save_metrics()` - Write CSV file

**Output Format:**
```csv
Layer_Number,Peak_Force_N,Work_of_Adhesion_mJ,Peeling_Initiation_Distance_mm,...
1,0.125,0.0234,0.150,0.085,0.235
```

**Phase-Aware Analysis:**
- Monitors `Lift-Stage2` as prescribed-speed start
- Excludes gentle break (Stage 1) from pre-initiation search
- Ensures accurate peeling initiation detection

---

### `adhesion_metrics_calculator.py`
**Purpose:** Comprehensive adhesion analysis engine (can run real-time or post-processing)

**Core Algorithm:**

```
1. Load position/force/time data
2. Detect force baseline (two-step algorithm)
3. Find peeling initiation (force exceeds baseline)
4. Locate peak force
5. Detect peeling completion (return to baseline)
6. Calculate work of adhesion (integrate force curve)
7. Compute distances and normalized metrics
```

**Key Functions:**
- `calculate_adhesion_metrics_from_data()` - Main analysis function
- `detect_baseline_two_step()` - Robust baseline detection
- `find_adhesion_boundaries()` - Identify start/peak/end points
- `integrate_work_of_adhesion()` - Trapezoidal integration

**Input:**
- Time series: time, position, force
- Optional: prescribed speed start position/time
- Optional: contact area for normalization

**Output Dictionary:**
```python
{
    'peak_force_N': 0.125,
    'work_of_adhesion_mJ': 0.0234,
    'peeling_initiation_distance_mm': 0.150,
    'post_peak_distance_mm': 0.085,
    'total_adhesion_distance_mm': 0.235,
    'peak_force_per_area_N_mm2': 0.0031,  # if area provided
    'work_per_area_mJ_mm2': 0.000585,     # if area provided
    # ... plus boundary indices, times, positions
}
```

**Usage:**
```python
from post_processing.adhesion_metrics_calculator import calculate_adhesion_metrics_from_data

metrics = calculate_adhesion_metrics_from_data(
    time_s=time_array,
    position_mm=position_array,
    force_N=force_array,
    prescribed_speed_start_pos_mm=10.5,
    contact_area_mm2=40.0
)

print(f"Peak Force: {metrics['peak_force_N']:.3f} N")
print(f"Work of Adhesion: {metrics['work_of_adhesion_mJ']:.3f} mJ")
```

---

### `SensorDataWindow.py`
**Purpose:** Real-time sensor data visualization and logging control GUI

**Window Components:**

```
┌─────────────────────────────────────────────────┐
│  Sensor Data & Logging Window                   │
├─────────────────────────────────────────────────┤
│  Connection Controls                            │
│    [Connect] [Disconnect] [Calibrate]           │
│                                                  │
│  Force Gauge Status                             │
│    Current: 0.015 N                             │
│    Mean: 0.014 N    Std: 0.002 N                │
│                                                  │
│  Real-Time Plot                                 │
│    ┌──────────────────────────────────┐         │
│    │  Force (N)                       │         │
│    │     ╱╲                           │         │
│    │    ╱  ╲                          │         │
│    │───┘    ╲─────────                │         │
│    └──────────────────────────────────┘         │
│                                                  │
│  Logging Controls                               │
│    ☑ Enable Automated Logging                   │
│    ☑ Record Peak Force                          │
│    [ ] Log Raw Data (High Frequency)            │
│                                                  │
└─────────────────────────────────────────────────┘
```

**Key Features:**
- Real-time force and position plotting
- Connection management for force gauge
- Calibration (zeroing) functionality
- Automated logging configuration
- Peak force recording toggle
- Raw data logging toggle

**Integration:**
- Communicates with `ForceGaugeManager`
- Controls `PositionLogger` and `AutomatedLayerLogger`
- Triggers `PeakForceLogger` when enabled
- Receives updates from main application

**Usage:**
Opened from main Prince GUI via "Open Sensor Panel" button.

---

### `two_step_baseline_analyzer.py`
**Purpose:** Robust baseline detection for force data with two-stage algorithm

**Algorithm:**

```
Step 1: Coarse Baseline Detection
- Use median + MAD (Median Absolute Deviation)
- Identify initial baseline candidates
- Filter out adhesion peaks

Step 2: Fine-Tuning
- Focus on pre-adhesion data
- Statistical outlier removal
- Refine baseline estimate
```

**Why Two-Step?**
- Handles noisy data
- Robust to force spikes
- Works with varying baseline drift
- Better than simple mean/median

**Key Function:**
- `detect_baseline_two_step(force_data, ...)` - Returns baseline value and statistics

**Usage:**
```python
from post_processing.two_step_baseline_analyzer import detect_baseline_two_step

baseline_N, stats = detect_baseline_two_step(
    force_N=force_array,
    time_s=time_array,
    position_mm=position_array
)
```

---

## Specialized Routines

### `SandwichRoutines.py`
**Purpose:** Controlled glass contact routines for platform adhesion

**Sandwich Modes:**

1. **Standard Sandwich**
   - Lower stage until glass contact detected
   - Hold for specified duration
   - Lift to build position

2. **Force-Controlled Sandwich**
   - Approach until target force reached
   - Maintain force for duration
   - Controlled release

3. **Adaptive Sandwich**
   - Adjust based on previous layers
   - Dynamic force targets
   - Learning algorithm

**Key Class:** `SandwichRoutineManager`

**Methods:**
- `execute_sandwich(mode, target_force, duration_s)`
- `detect_contact()` - Force threshold detection
- `hold_contact(duration_s)` - Maintain contact

**Usage in Print:**
```python
sandwich_mgr.execute_sandwich(
    mode='standard',
    target_force=0.5,  # N
    duration_s=2.0
)
```

---

### `SessionManager.py`
**Purpose:** Session state persistence and logging directory management

**Key Features:**
- Save/load GUI state (last used parameters)
- Manage logging directory structure
- Track print session numbers
- Organize data by date and print number

**Directory Structure:**
```
Printing_Logs/
├── 2026-02-02/
│   ├── Print_1/
│   │   ├── autolog_Print1.csv
│   │   ├── autolog_L1-L1.csv
│   │   ├── adhesion_metrics_Print1.csv
│   │   └── instruction_file_copy.txt
│   └── Print_2/
│       └── ...
└── 2026-02-03/
    └── ...
```

**Key Methods:**
- `save_gui_state()` - Save to JSON
- `load_gui_state()` - Restore from JSON
- `init_session_log()` - Create new session directory
- `get_next_print_number(date_dir)` - Determine print number

---

## Utilities

### `USBCoordinator.py`
**Purpose:** Prevent USB resource conflicts between DLP and Phidgets

**Problem:**
- Both devices communicate via USB
- Simultaneous operations can cause conflicts
- Need coordination for reliable operation

**Solution:**
- Mutex-based resource locking
- Queued operations
- Automatic retry logic

---

### `image_edge_enhancer.py`
**Purpose:** Batch image edge enhancement for improved print quality

**Algorithm (matches MATLAB ImageModification_V3.m):**
```python
# 1. Apply Gaussian blur
blurred = GaussianBlur(image, kernel=101×101, sigma=25)

# 2. Subtract from original
edges = image - blurred

# 3. Normalize to [min_intensity, 255]
normalized = (edges - min) / (max - min) * (255 - min_intensity) + min_intensity

# 4. Preserve background
result[original == 0] = 0
```

**Command-Line Usage:**
```powershell
python support_modules/image_edge_enhancer.py "C:\path\to\images" --blur 50 --min 125 --max 255
```

**Parameters:**
- `--blur` - Gaussian blur sigma (default: 25)
- `--min` - Minimum intensity for normalized edges (default: 100)
- `--max` - Maximum intensity (default: 255)
- `--output` - Custom output folder name

**Output:**
Creates subfolder named `EdgeEnhanced_##Blur_###Min` with processed images.

**Why Use Edge Enhancement?**
- Improves feature definition during UV exposure
- Sharper edges in printed parts
- Better resolution of fine details

---

### `libs.py`
**Purpose:** Print instruction file parsing and image list generation

**Key Functions:**
- `parse_instruction_file(filepath)` - Read .txt print file
- `generate_image_list()` - Build array of image paths
- `validate_parameters()` - Check parameter consistency

**Instruction File Format:**
```
Directory: C:\path\to\images
Exposure_Time: 1.0,1.0,1.0,...
Thickness: 50,50,50,...
Step_Speed: 500,500,500,...
Overstep: 300,300,300,...
Pause: 0.5,0.5,0.5,...
Intensity: 128,128,128,...
```

---

## Module Dependencies

### Import Hierarchy

```
Prince_Segmented.py
├── motion_controller.py
│   └── zaber_motion
│
├── SensorDataWindow.py
│   ├── ForceGaugeManager.py
│   │   └── Phidget22
│   ├── PositionLogger.py
│   ├── AutomatedLayerLogger.py
│   └── PeakForceLogger.py
│       └── adhesion_metrics_calculator.py
│           └── two_step_baseline_analyzer.py
│
├── pycrafter9000.py
│   └── usb.core
│
├── SandwichRoutines.py
├── SessionManager.py
└── libs.py
```

### External Dependencies

**Python Packages:**
- `tkinter` - GUI framework
- `numpy` - Numerical operations
- `opencv-python` - Image processing and display
- `zaber-motion` - Stage control
- `Phidget22` - Force gauge communication
- `usb.core` (PyUSB) - DLP USB communication
- `screeninfo` - Multi-monitor support
- `queue`, `threading` - Concurrency

**Hardware Drivers:**
- Zaber Motion Library
- Phidgets22 drivers
- libusb (for DLP communication)

---

## Development Guidelines

### Adding a New Module

1. **Create module file in `support_modules/`**
2. **Follow naming convention:** `lowercase_with_underscores.py`
3. **Include docstrings:**
   ```python
   """
   Module description.
   
   Key Features:
   - Feature 1
   - Feature 2
   
   Usage:
   example code
   """
   ```
4. **Update this README** with module documentation
5. **Add import to `Prince_Segmented.py`** if needed
6. **Test thoroughly** on hardware

### Modifying Existing Modules

**Critical Considerations:**

1. **Phase Detection Changes:**
   - Update `motion_controller.py` phase callbacks
   - Update `PositionLogger.py` phase label handling
   - Update `PeakForceLogger.py` phase tracking
   - Update `RawData_Processor.py` boundary detection

2. **Data Format Changes:**
   - Maintain backwards compatibility
   - Update all analysis scripts
   - Document format changes
   - Test with existing data files

3. **Hardware Interface Changes:**
   - Test with actual hardware
   - Verify no USB conflicts
   - Check thread safety
   - Update calibration procedures

### Testing Checklist

- [ ] Imports work correctly
- [ ] No circular dependencies
- [ ] Thread-safe if multi-threaded
- [ ] Graceful error handling
- [ ] Status messages to user
- [ ] Compatible with existing data
- [ ] Hardware tested (if applicable)
- [ ] Documentation updated

---

## Common Issues & Solutions

### Force Gauge Connection Lost
**Problem:** Force gauge disconnects during print  
**Solution:** Check USB cable, try different port, restart ForceGaugeManager

### Stage Not Responding
**Problem:** Stage ignores movement commands  
**Solution:** Check COM port, restart connection, verify axis is homed

### DLP Pattern Not Displaying
**Problem:** Images don't project  
**Solution:** 
1. Check mode (should be 4 for pattern mode)
2. Verify power > 0
3. Ensure sequence is loaded
4. Call startsequence()

### High Force Noise
**Problem:** Force readings very noisy  
**Solution:** 
1. Check decimation factor
2. Calibrate force gauge
3. Reduce vibration sources
4. Check electrical interference

### Phase Labels Not Recording
**Problem:** Phase column empty or incorrect  
**Solution:** 
1. Verify phase_callback is connected
2. Check PositionLogger.update_phase() calls
3. Ensure motion_controller callbacks are firing

---

## Performance Optimization

### Data Acquisition Rate

**Force Gauge:**
- Native: 1200 Hz
- Decimated: 120 Hz (10x factor)
- Adjust based on print speed and data needs

**Position Logger:**
- Default: 100 Hz
- Increase for fast motions
- Decrease for long prints (file size)

### File Sizes

**Typical Print (100 layers, 2 hours):**
- Raw autolog: ~50-200 MB (depending on decimation)
- Layer-specific files: ~500 KB - 2 MB per layer
- Adhesion metrics: ~10 KB

**Optimization:**
- Use appropriate decimation
- Enable layer-specific logging only when needed
- Archive old prints regularly

---

## Module Version History

**Major Updates:**

**January 2026:**
- `motion_controller.py` - Converted to 2-stage symmetric smooth motion
- `adhesion_metrics_calculator.py` - Enhanced boundary detection
- `PeakForceLogger.py` - Updated for new phase labels
- `image_edge_enhancer.py` - Created (replicates MATLAB algorithm)

**December 2025:**
- `SensorDataWindow.py` - Added peak force recording toggle
- `ForceGaugeManager.py` - Improved decimation logging
- `two_step_baseline_analyzer.py` - Refined algorithm

---

## Quick Reference

### Most Commonly Modified Modules

1. **`motion_controller.py`** - Motion profile tuning
2. **`adhesion_metrics_calculator.py`** - Analysis algorithm refinement
3. **`SensorDataWindow.py`** - GUI and logging features
4. **`PeakForceLogger.py`** - Real-time analysis logic

### Most Stable Modules (Rarely Changed)

1. **`pycrafter9000.py`** - Hardware interface
2. **`ForceGaugeManager.py`** - Hardware interface
3. **`SessionManager.py`** - Session/log orchestration
4. **`libs.py`** - File parsing

---

## Contact

For questions about support modules:

**General Questions:** Evan Jones (evanjones2026@u.northwestern.edu)  
**Hardware Interface:** Boyuan Sun (boyuansun2026@u.northwestern.edu)  
**Analysis Algorithms:** Evan Jones (evanjones2026@u.northwestern.edu)

---

**Last Updated:** February 2, 2026  
**Module Count:** 17 active modules  
**Python Version:** 3.8+
