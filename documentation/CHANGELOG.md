# Changelog - Prince 3D Printer Control Software

## [2026-11-03] - Graphite Slicing Support Separator & Image Modification Vectorization

### Graphite Slicing Pipeline: Supported Mesh Separator (graphite/slicing/support_separator.py)
- **Combined STL Separation (split_supported_mesh):** Decouples multi-shell STL files containing printed parts and slicer-generated supports into co-registered meshes while strictly preserving original world coordinates.
  - **Mode A (Reference Guided):** Uses KDTree spatial query against the reference part geometry to accurately identify part shells with sub-millimeter precision.
  - **Mode B (Autonomous / Heuristic):** Autonomous classification analyzing vertical aspect ratio (Z/extent_XY), characteristic cross-sectional thickness, volume ratios, and build-plate rafts.
- **Support Contact Tip Extraction (extract_support_tips):** Identifies vertices and submeshes within tip_distance_threshold (default 0.8 mm) of the part surface. Tags tips with lower grayscale intensity (G_tip = 128 vs G_pillar = 255) to prevent contact overcuring and facilitate clean mechanical release.
- **Pillar Top Disconnection (detect_and_disconnect_support_tops):** Clusters support shells into XY pillar columns and separates top contact modules from bulk scaffolding either via modular shell grouping (component mode) or clean horizontal cross-sectional cuts (planar_cut mode).
- **Object-Oriented & CLI Interface:** Added SupportedMeshSeparator class (separate(), tag_tips(), disconnect_tops(), export()) and a command-line interface supporting batch STL processing.
- **Unit Test Suite:** Added tests/test_support_separator.py (12 tests) verifying synthetic cube + penetrating cylinders, multi-shell parts, base rafts, coordinate invariance, zero triangle loss, and CLI execution.

### Robust Feature Depth Correction & Interactive Pipeline Ordering (Image Modification Suite)
- **Robust Feature Depth Correction (`support_modules/image_modification/feature_depth.py`):**
  - **Physical Scale Normalization:** Replaced global min/max rescaling with a saturating exponential physical scale $1 - \exp(-\text{depth} / D_{\text{char}})$ with $D_{\text{char}} = 2 \times \sigma_{\text{decay}}$. Ensures small or isolated parts are not artificially over-dimmed.
  - **Normalized Convolution:** Spreads channel depth into solid features via $\text{GaussianBlur}(\text{depth} \times \text{mask}) / \text{GaussianBlur}(\text{mask})$, eliminating boundary dilution artifacts and computing the true local weighted average of arriving channel depths.
  - **Dual Operating Modes:**
    - **Mode A (Distance / Channel Flow):** Connected component classification separating exterior channels from enclosed pores; Euclidean propagation from the perimeter outer pool (`outer_pool`, depth = 0).
    - **Mode B (Pressure / Porous Media Poisson Solver):** Solves 2D Darcy flow $\nabla \cdot (K \nabla P) = S$ with Successive Over-Relaxation (SOR) and automatic $2\times / 4\times$ coarse-grid acceleration for sub-second convergence on $1600\times 2560$ SLA masks.
- **Interactive Pipeline Stage Reordering (`support_modules/ImageModificationWindow.py`):**
  - Added interactive listbox allowing operators to dynamically reorder pipeline stages (`3D Axial`, `Edge Enhancement`, `Global Enhancement`, `Feature Depth`, `Scattering Compensation`) using Move Up / Move Down controls.
  - Stages before and after axial compensation are partitioned cleanly during batch multiprocessing.
  - Added folder tag encoding for custom order sequences (`_Ord-EEZAGE`, etc.).
- **3D Axial Z Compensation GUI Integration:**
  - Added controls for critical energy $E_c$, exposure ratio $E_0/E_c$, layer thickness $h$, and penetration depth $D_p$.
  - Integrated single-layer lookahead downward overhang solver into live image preview.
- **Unit Tests (`tests/test_image_modification.py`):**
  - Added unit tests for 3D axial folder processing, custom pipeline execution order, and single-layer lookahead overhang dimming.
  - Added `image_mod` test suite to `tests/run_all_tests.py` (all 71 tests pass).

### High-Efficiency SIMD Image Modification Optimizations
- **Edge Enhancement Vectorization (support_modules/image_modification/edge_enhancement.py):**
  - Converted internal calculations to single-precision float32 SIMD operations for reduced memory overhead and increased throughput during high-layer-count slicing.
  - Replaced Python boolean array indexing (edge_enhanced[mask]) with OpenCV SIMD-accelerated cv2.minMaxLoc(), avoiding large intermediate allocations.
- **Scattering Compensation Vectorization (support_modules/image_modification/scattering_compensation.py):**
  - Optimized Gaussian boundary dimming using float32 vectorization and cv2.minMaxLoc().
  - Streamlined normalization and scaling into a fused linear transformation ((max_val + scale * lo) - signal * scale).

### Control UI Safety & Test Suite Consolidation
- **Viscosity Monitor Button State:** Temporarily set b_viscosity_monitor and chk_preprint_viscosity to DISABLED state across Prince control GUIs (Prince_Segmented.py, Prince_Segmented_Unified.py, Prince_Segmented_VideoPattern.py, prince_modern_unified_source.py) pending physical sensor attachment, while maintaining the underlying mathematical engine and tests.
- **Full Test Suite (57 Tests):** Registered support_separator and exp_conditions in tests/run_all_tests.py. All 57 tests across 7 active test modules pass cleanly.

## [2026-10-19] - Save Print Instruction File on Experimental Conditions Logging

### Experimental Conditions Logging & Print Instruction Persistence
- Updated the print finalization and initialization logic across Prince GUIs (`Prince_Segmented.py`, `Prince_Segmented_Unified.py`, `prince_modern_unified_source.py`, `Prince_Segmented_VideoPattern.py`, and `ExperimentalConditionsWindow.py`) so that whenever **"Enable Experimental Conditions Logging"** is enabled, the active print instruction file (`.txt`) is automatically copied into the print's session log folder.
- **Immediate Save at Print Start:** The instruction file is copied as soon as the print session directory is established, ensuring that aborted prints or unexpected shutdowns still retain their instruction `.txt` in the log directory.
- **Folder Rename Persistence:** When `ExperimentalConditionsWindow.end_print()` renames the session folder to include status suffixes (`- Complete` or `- Stopped`), the copied `.txt` file persists within the renamed folder, and post-print finalization verifies the instruction file exists in the target folder.
- **Robust Fallback Discovery:** If `active_instruction_file_path` is not explicitly set in memory, the system automatically discovers the expected `<foldername>.txt` from the image directory specified in `t1`.
- **Unit Tests:** Added unit tests in `tests/test_experimental_conditions_logging.py` covering copy at start, persistence across folder rename, fallback from directory path, and exclusion when logging is disabled. Added `exp_conditions` test target to `tests/run_all_tests.py`.

## [2026-10-14] - Test Suite Robustness & Documentation Consolidation

### Test Suite Multi-Subsystem Expansion
- Extended master test runner (`tests/run_all_tests.py`) to execute unit and regression suites across all major subsystems: `SessionManager`, `ViscosityAnalyzer`, `RampedCylinder`, `CameraViewWindow` (optical robustness), and `SeekThermalViewerWindow` (radiometric thermography).
- All 42 test cases across 5 active test suites now pass cleanly in ~15 seconds.
- Handled optional post-processing dependencies (`pandas`, `scipy`) gracefully in `run_all_tests.py`, allowing the printing and hardware suites to execute on production environments without requiring the dev analysis stack.
- Added module path resolution to `tests/test_ramped_cylinder.py` so it can be executed standalone or via test runner.
- Resolved Windows console `cp1252` encoding crashes in `run_all_tests.py` by eliminating non-ASCII glyphs.

### Seek Thermal Radiometric Viewer Robustness
- Enhanced `SeekThermalWorker` synthetic simulation fallback: When running in mock mode or headless test environments without physical USB hardware attached, the worker initializes the simulation loop within a fast 0.15 s detection window, enabling automated testing without UI blocking or timeout failures.

### Master Documentation Index & Subsystem Collation
- Rebuilt `DOCUMENTATION_INDEX.md` as the unified master index for the Prince repository, replacing obsolete Rush Phase 1 shutdown testing documentation.
- Synchronized `README.md` with complete architecture, core components, and chronological changelog entries spanning the addition of the live Sensor Suite, In-Situ Resin Viscosity Monitor, and Prince Modern PySide6 GUI.
- Updated `documentation/PROJECT_ORGANIZATION.md` to map new modules across `/support_modules/`, `/calibration_modules/`, `/prince_modern/`, and `/tests/`.

## [2026-10-09] - AI handoff

- New [`START_HERE_FOR_AI.md`](../START_HERE_FOR_AI.md): which entry point is current, launch commands, hardware constraints, and docs that are out of date. Linked from `DOCUMENTATION_INDEX.md`.

## [2026-10-09] - Prince Modern look + printer-PC handoff

- Prince Modern cards use the mockup dusty lavender (`#8870A3`) and bundled Inter (`prince_modern/fonts/`).
- Build visualization loads only after **Generate visualization** (fixed the slice preview growing on a timer).
- Printer-PC move checklist: [`documentation/DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md) (clone from GitHub; do not copy `.conda`).

## [2026-10-03] - Prince Modern (PySide6 shell)

- New entry [`Prince_Modern.py`](../Prince_Modern.py): dark-purple card UI matching the Modern mockup and monitoring-dashboard palette.
- Package [`prince_modern/`](../prince_modern/): `main_window`, `theme`, `controller`.
- Backend: withdrawn copy of Unified as [`prince_modern_unified_source.py`](../prince_modern_unified_source.py) so print/stage/DLP/sensor windows keep Unified behavior.
- Adds System Log, header/footer status chips, slice preview placeholder, and **Monitoring Suite** launcher (missing from Unified).
- Operator notes + feature gap checklist: [`documentation/PRINCE_MODERN_GUI.md`](PRINCE_MODERN_GUI.md).
- [`Prince_Segmented_Unified.py`](../Prince_Segmented_Unified.py) left unchanged.

## [2026-10-02] - Monitoring dashboard: live sensors, UV expected power, triple force

### PySide6 System Monitoring dashboard
- Separate process under `.conda\python.exe`; Prince **Monitoring Suite** launches it with `close_fds=True` so the DLP HID is not inherited.
- Live cards: Alvium optical, Seek thermal (radiometric), Phidget force, Thorlabs PM100A power, slice geometry driven by `data/monitor_print_state.json`.
- Gray unavailable covers when a device is missing (no fake camera/force streams).

### Thorlabs PM100A + expected UV line
- NI-VISA SCPI driver (`thorlabs_pm100a.py`); default wavelength **385 nm**; software up-range at 75% of full scale.
- Two-point density calibration at LED commands **10** and **100** on `Power_255.png`; saved to `data/uv_power_calibration.json`.
- Expected power = density(command) × layer white area; dashed line on the power plot.
- Scripts: `power_density_calibration.py` (4 s settle + range iteration), `power_expected_stress_test.py`, `power_range_sweep.py`.

### Triple load-cell force on the monitor
- When newest `force_gauge_calibration_*.txt` has `MODE=TRIPLE`, opens Phidget channels **0+1+2** and plots the **sum** at default **40 Hz (25 ms)**.
- **Calibrate** / **Tare** on the force card: SensorDataWindow-style dialogs with proportional total-force math from the triple-cell guides; optional save under `data/`.
- Total force readout to 3 decimals with stable sign spacing; per-channel UI labels removed to avoid layout shake.
- Sensor Panel / `ForceGaugeManager` remain single-channel; keep Sensor Panel closed while the dashboard owns the bridge.

### Docs
- New operator guide: `documentation/MONITORING_DASHBOARD_GUIDE.md`.

## [2026-09-30] - PySide6 monitoring dashboard

- Prince **Monitoring Suite** now launches a separate PySide6 dashboard (`calibration_modules/monitoring_dashboard`) so the printer GUI stays on Tkinter.
- Dark 2x2 layout: dual camera feeds, peel-force plot, 3D lattice with a moving slice plane plus the current mask, and a UV dose stand-in.
- Force, dose, and print progress are simulated. Cameras use the Allied Vision and Seek workers when those devices start, and synthetic frames otherwise.

## [2026-09-30] - In-Situ Resin Viscosity & Solvent Evaporation Drift Monitoring

### Mathematical Engine & Stefan Squeeze-Flow Theory (`support_modules/viscosity_analyzer.py`)
- Implemented linearized Stefan squeeze-flow regression for circular plate rheometry ($D = 12.7\text{ mm}$ aluminum build stage): transforms raw hydrodynamic force to $F^{-1/3}\text{ vs } z$.
- Slope $m = (32 / (3\pi D^4 \mu v))^{1/3}$ extracts relative viscosity changes while providing mathematical invariance to zero-gap datum shifts ($z_0$) caused by chassis thermal expansion ($10\text{--}25\ \mu\text{m}$).
- Added lumped elastohydrodynamic compliance solver to decouple FEP membrane deflection from viscous drag.
- Added multi-speed power-law rheology solver for evaluating non-Newtonian shear-thinning indices.
- Pre-fluid dry membrane touch and contact-stiffness detector.

### Relative Drift Tracking & Solvent Evaporation Alerts
- Self-referencing morning baseline model: Tracks $\Delta \mu\% = [(m_0/m_k)^3 - 1] \times 100\%$ across printing sessions without requiring external calibration standards.
- Designed specifically for volatile diluents and reactive solvents that evaporate over long print runs.
- Added automated descent sampling hook in `Prince_Segmented.py` before Layer 1 exposure.
- Automated threshold alerts: Warnings triggered at $+20\%$ thickening; critical stop alerts at $+25\%$ to prevent delamination or suction failure.
- Auto-persists daily baselines to `config/daily_viscosity_baseline.json` with same-day date validation.

### Real-Time Viscosity Monitor Window (`support_modules/ViscosityMonitorWindow.py`)
- Dedicated Tkinter + Matplotlib secondary GUI window.
- Dual-plot real-time visualization: Top plot displays raw squeeze force $F(z)$ vs gap; bottom plot displays linearized Stefan fit $F^{-1/3}(z)$ with live $R^2$ goodness-of-fit and slope readouts.
- Pre-print dry membrane touch checks, reference fluid precalibration dialog, and baseline reset controls.

### Reference Fluids Database (`support_modules/reference_fluids_db.py`)
- Standardized laboratory reference fluid database with Arrhenius temperature models ($\ln \mu = A + B/T$):
  - PEG 400 (Polyethylene Glycol 400, water-soluble, non-toxic, ideal resin viscosity match)
  - Glycerol-Water mixtures (85% w/w and 90% w/w Newtonian standards)
  - Propylene Glycol (USP)

### Testing & Technical Documentation
- Added 9-test unit test suite in `tests/test_viscosity_analyzer.py` verifying geometry prefactors, linearized regression, zero-datum recovery, baseline persistence, reference fluids, and synthetic curve simulation (all passing).
- Detailed technical guides:
  - `documentation/technical/RESIN_VISCOSITY_SQUEEZE_FLOW_PHYSICS.md` (fluid mechanics and EHL theory)
  - `documentation/technical/VISCOSITY_DATA_ANALYSIS_METHODS.md` (data analysis and numerical solvers)
  - `documentation/technical/IN_SITU_VISCOSITY_DRIFT_HANDOVER.md` (developer handover and implementation guide)

## [2026-09-30] - Monitoring Suite (optical, thermal, force, power slot)

- Prince **Monitoring Suite** opens one window with tabs for the Allied Vision camera, Seek Thermal camera, and force/power readouts.
- Force is read from the existing Sensor Panel gauge. The suite does not open a second Phidget.
- Thorlabs power meter is a reserved readout until a driver is added.
- Optical and thermal viewers can still run standalone.

## [2026-09-23] - Allied Vision Camera View (Phase 1, Vimba X / vmbpy)

### Live camera preview in `Prince_Segmented.py`
- Added **Camera View** button (second control row) opening a non-blocking Tk popup for the Alvium 1800 U-511m.
- New stack under `calibration_modules/`: `vmb_camera_worker.py`, `zoom_pan_canvas.py`, rewritten `CameraViewWindow.py`.
- Features: live stream, pan/zoom, exposure/gain (debounced), display contrast/brightness/gamma, center crosshair, raw snapshot.
- CLI bring-up: `stream_smoke_test_vmbpy.py`, `vmb_worker_harness.py`.
- Main-window shutdown joins the camera worker so the device unlocks for Vimba Viewer.

### Cleanup
- Removed non-working legacy `vimba` manager and unvalidated ChArUco / calibration-workflow modules and related docs.
- `camera_requirements.txt` now targets `vmbpy` (Vimba X), not legacy `vimba`.

## [2026-09-06] - Prince Unified GUI (Projection Mode Switcher & Rush-Aligned Clean Interface)

### Unified Dual Projection Mode Architecture (`Prince_Segmented_Unified.py`)
- Created unified Prince control script porting the dual-mode architecture from Rush to Prince.
- Added **Projection Mode** frame (`x=800, y=225`) allowing seamless toggling between:
  - **Video Mode (`video`)**: 60 Hz HDMI video projection with Light UI theme (pastel red accent `#FFB3B3`, Prince purple `#834bd0` header).
  - **Video Pattern Mode (`video_pattern`)**: 30 Hz HDMI Video Pattern LUT projection with Dark UI theme (`#1A1B26` background, `#2E1C1C` dark red panel accent, `#B794F4` soft purple header).
- Preserved existing scripts (`Prince_Segmented.py` and `Prince_Segmented_VideoPattern.py`) intact without modifications.

### Clean Layout & Visual Overhaul (Aligned with Rush Redesign)
- **Header**: Centered unboxed header at `x=620, y=0, anchor='n'`, dynamically themed with Prince purple (`#834bd0` / `#B794F4`) and automatic `Prince_Logo.png` fallback.
- **Checklist Repositioning**: Moved `lbl5` to `x=710, y=330` below the Projection Mode frame, eliminating the previous layout overlap.
- **Clutter Removal**: Hidden Sandwich routine box and Auto-Home box via `place_forget()` (retaining background variables for full session compatibility); removed smooth motion checkboxes and redundant save/load/reload buttons.
- **Compact Window Sizing**: Integrated `_apply_recommended_window_geometry()` to dynamically size the window height to `1200x680` with balanced padding.
- **Dual Sensor Panels**: Added `Sensor Panel (Logging)` and `Sensor Panel (Monitoring)` with mutual exclusion enforcement.

### Hardware Alignment & Stability Fixes
- **Zaber Acceleration Readback**: Adjusted quantization tolerance to `max(100.0, 0.01 * desired)` across `Prince_Segmented_Unified.py`, `Prince_Segmented_VideoPattern.py`, and `Prince_Segmented.py`, eliminating false readback warnings caused by discrete microstep math.
- **Physical Absolute Coordinates**: Enforced strict physical stage coordinates in `t4` (`get_position`, `set_home`, `goto_position`, `moveup`, `movedown`), resolving the relative-offset discrepancy.
- **Thread-Safe Post-Print Survey**: Implemented `_post_print_queue` and main-thread poller (`_poll_post_print_queue`) to safely schedule post-print survey dialogs without cross-thread Tkinter crashes.
- **State Persistence**: Updated `support_modules/SessionManager.py` to persist `projection_mode` and validate directory paths on autoload to prevent modal error popups on startup.

## [2026-06-11] - Image Modification Helpers: Cone Generator + Instruction Ramping

### Cone Generator (Image Modification Window)
- Added a new helper that generates a synthetic cone layer stack directly from geometry inputs.
- Inputs: initial radius (µm), ending radius (µm), height (µm), layer height (µm), output base folder.
- Output: newly created parameter-tagged folder containing sequential files `1.png`..`N.png`.
- Layer count computed as `ceil(height / layer_height)`.

### Instruction Ramping (Image Modification Window)
- Added instruction-file utility that builds a new instruction folder from a selected source `.txt`.
- Supports control points specified as `layer, exposure` and ramp mode selection (`linear` or `exponential`).
- Exposure schedule behavior:
   - Before first control layer: fixed to first control exposure.
   - Between control layers: interpolated by chosen mode.
   - After last control layer: fixed to last control exposure.
- Per-layer power is recomputed to preserve constant dosage anchored at the first control layer:
   - `D = P_first × t_first`
   - `P_i = D / t_i` (clipped to `0..255`).
- Output: `<source_folder>_ramped_linear` or `_ramped_exponential` folder with copied images and a new compatible 10-column tab-delimited instruction file.

## [2026-03-07] - Image Modification GUI Overhaul

### Scattering Compensation — algorithm rewrite
- **Bug fix**: SC now computes `original − blurred` (same direction as EE) with *inverted* normalisation, so boundary pixels dim and interior stays bright. Previous `blurred − original` approach gave the wrong gradient direction.
- **API unification**: Replaced single `strength` param with `min_val` / `max_val` matching the EE interface.

### Falloff parameter — EE and SC
- New `Falloff` GUI field for both Edge Enhancement and Scattering Compensation.
- Controls Gaussian kernel size independently of `Blur` (sigma).
- `Falloff = 0` auto-computes as `4×Blur+1` (unchanged default behaviour).
- Smaller Falloff + large Blur avoids cross-strut blur overlap in dense lattice geometries.
- Updated: `scattering_compensation.py` (×2), `processor.py` (×2), `ImageModificationWindow.py` (×2), `DefinitionsWindow.py`.

### Export packaging (`ImageModificationGUI_export/`)
- Feature Depth Correction removed (experimental, local only).
- "Padding Normalization" → "Image Padding" label rename.
- `DefinitionsWindow.py` copied into export so the Definitions tab is available on the printer computer.
- `ImageModificationGUI.exe` built with PyInstaller — fully self-contained, no Python needed.
- PIL/Pillow import made lazy to fix PyInstaller boot-time initialisation bug (caused false "Install Pillow" message).
- Cleaned: `build_temp/`, `__pycache__/`, orphaned `feature_depth.py` removed from export folder.

---

## [2025-10-05] - Hybrid Signal Filtering Integration

### 🎯 Signal Processing Enhancement

#### **INTEGRATION STATUS: ✅ COMPLETE**
New hybrid Median-Savitzky-Golay filter chain integrated into adhesion analysis.

---

### Filter Optimization (October 2025)

#### **Hybrid Two-Stage Filter Implementation**
**STATUS:** ✅ Production-Ready

**What Changed:**
- Replaced single Gaussian filter (σ=0.5) with hybrid two-stage filter chain
- Stage 1: Median filter (kernel=5) for outlier/spike rejection
- Stage 2: Savitzky-Golay filter (window=9, order=2) for polynomial smoothing

**Why It Matters:**
- **90.1% improvement in smoothness** (validated on test data)
- Better spike/outlier rejection from non-linear median filter
- Preserves sharp edges better than Gaussian-only approach
- More accurate baseline and peak detection

**Quantitative Optimization:**
- 30+ filter combinations tested via parameter grid search
- Combined Score metric: SSR + λ * Roughness
- Median(k=5) → Savitzky-Golay(w=9, o=2) scored 0.02124 (2nd best)
- Lambda value: 1.0 (balanced fidelity-smoothness tradeoff)

**Technical Implementation:**
```python
# Stage 1: Median filter for spike rejection
median_filtered = median_filter(force_data, size=5)

# Stage 2: Savitzky-Golay for polynomial smoothing  
smoothed = savgol_filter(median_filtered, window_length=9, 
                        polyorder=2, mode='nearest')
```

**Files Updated:**
- `support_modules/adhesion_metrics_calculator.py` - New `_apply_smoothing()` method
- `support_modules/PeakForceLogger.py` - Updated calculator initialization
- Added parameters: `median_kernel`, `savgol_window`, `savgol_order`
- Deprecated: `smoothing_sigma` (kept for backward compatibility)

**Validation:**
- Test file: autolog_L48-L50.csv (2,260 data points)
- Metrics calculated correctly (Peak: 0.26N, WoA: 0.28mJ)
- Smoothness improvement: 90.1% vs old filter
- Comparison plot: `filter_integration_test_results.png`

**Research Documentation:**
- Full methodology: `archive/filtering_experimentation/README.md`
- Test results: `archive/filtering_experimentation/full_results_table.txt`
- Analysis summary: `CLEANUP_AND_FILTERING_SUMMARY.md`

---

## [2025-10-03] - Major Adhesion Analysis System Overhaul

### 🔬 Critical Changes - Adhesion Metrics Calculation

#### **INTEGRATION STATUS: ✅ VERIFIED**
All changes have been integrated into the live printing system and post-processing pipeline.

---

### Core Algorithm Improvements

#### 1. **Time-Based Derivative Analysis** (adhesion_metrics_calculator.py)
**STATUS:** ✅ Production-Ready

**What Changed:**
- Replaced position-based derivatives with time-based derivatives for baseline detection
- Added Gaussian smoothing (σ=0.5) to reduce noise sensitivity
- Implemented baseline intersection verification to prevent false positives

**Why It Matters:**
- Eliminates false baseline detection from random force spikes
- More robust to varying peel speeds and stage acceleration profiles
- Correctly identifies end of crack propagation using physics-based criteria

**Technical Details:**
```python
# Old Method (Position-based - REMOVED):
dx = np.diff(position_data)
dy = np.diff(force_data)
first_derivative = dy / dx  # Sensitive to stage speed variations

# New Method (Time-based - ACTIVE):
dt = np.diff(time_data)
dy = np.diff(smoothed_force)
first_derivative = dy / dt  # Consistent regardless of stage speed
second_derivative = np.diff(first_derivative) / dt[:-1]
```

**Validation:**
- Tested on L111 (previously showed false baseline at ~14s spike)
- Tested on L48-L50, L198-L200 datasets
- All layers now correctly identify baseline

---

#### 2. **Layer Boundary Detection** (RawData_Processor.py)
**STATUS:** ✅ Production-Ready

**What Changed:**
- Replaced position-based layer detection with time-gap clustering
- Uses 8-second threshold to separate distinct peel events
- Creates non-overlapping boundaries for each layer

**Why It Matters:**
- Fixes critical bug where only 1 layer was detected instead of 5 in multi-layer files
- Handles variable layer timing and peel durations automatically
- Prevents data loss from incorrect layer segmentation

**Technical Details:**
```python
# Time-gap clustering algorithm
peak_times = time_data[peaks]
time_diffs = np.diff(peak_times)
gap_threshold = 8.0  # seconds between layers
layer_transitions = np.where(time_diffs > gap_threshold)[0]
```

**Validation:**
- L50-L54: Now correctly detects 5 layers (was 1)
- L65-L69: Now correctly detects 5 layers (was 1)
- L47-L49: Now correctly detects 3 layers (was 1)

---

### Integration Points

#### **Real-Time Analysis (During Printing)**

1. **PeakForceLogger.py** → **adhesion_metrics_calculator.py**
   - Status: ✅ Integrated
   - Used when: Printing with peak force logging enabled
   - Data flow:
     ```
     Prince_Segmented.py (print loop)
       → SensorDataWindow.py (sensor monitoring)
         → PeakForceLogger.py (per-layer analysis)
           → adhesion_metrics_calculator.py (metrics calculation)
     ```
   - Output: Real-time CSV with 13 metrics per layer

2. **Automated Layer Logger** → **PeakForceLogger**
   - Status: ✅ Integrated
   - Used when: Auto-logging enabled for specific layer ranges
   - Configuration: `logging_windows.csv` in print session folder
   - Output: `autolog_L##-L##.csv` files

#### **Post-Print Analysis**

1. **Manual Analysis** → **RawData_Processor.py** → **adhesion_metrics_calculator.py**
   - Status: ✅ Integrated
   - Used when: Analyzing existing CSV files
   - Scripts:
     - `post-processing/RawData_Processor.py` (single file analysis)
     - `post-processing/batch_v17_analysis.py` (folder batch processing)
   - Output: `autolog_metrics.csv` with enhanced metrics

2. **Automated Post-Print Analysis** → **post_print_analyzer.py**
   - Status: ✅ Integrated
   - Used when: Automatically triggered after print completion
   - Called by: `Prince_Segmented.py._trigger_post_print_analysis()`
   - Output: Analysis plots in session folder

---

### New Features

#### 1. **Speed-Dependent Analysis Plots**
**Files Created:**
- `plot_speed_analysis.py` (mean values, 4 metrics)
- `plot_speed_analysis_median.py` (median values, 4 metrics)
- `plot_master_speed_analysis.py` (mean, all conditions combined)
- `plot_master_speed_analysis_median.py` (median, all conditions)
- `plot_master_distance_analysis.py` (median, distance-focused 2 plots)

**Metrics Analyzed:**
- Peak Force vs. Speed
- Work of Adhesion vs. Speed
- Total Peel Distance vs. Speed
- Peak Retraction Force vs. Speed
- Distance to Peak vs. Speed
- Propagation Distance vs. Speed

**Statistical Methods:**
- Mean with standard deviation
- Median (robust to outliers)
- 2nd order polynomial trend lines
- Multi-transparency visualization (individual points 5-10%, averaged 25%)

**Usage:**
```bash
# Individual folder analysis (mean)
python plot_speed_analysis.py "path/to/folder/autolog_metrics.csv"

# Master comparison (median, all test conditions)
python plot_master_speed_analysis_median.py "path/to/V17Tests"

# Distance-focused analysis
python plot_master_distance_analysis.py "path/to/V17Tests"
```

#### 2. **Enhanced CSV Output Format**
**New Columns Added:**
- `Propagation_Start_Time_s` - When crack initiation begins
- `Propagation_End_Time_s` - When crack propagation completes
- `Propagation_Duration_s` - Time spent in active propagation
- `Distance_to_Peak_mm` - Pre-initiation distance (substrate travel before crack starts)
- `Propagation_Distance_mm` - Distance during active crack growth
- `Total_Peel_Distance_mm` - Sum of above two distances

**Old Columns (Still Present):**
- `Layer_Number`
- `Peak_Force_N`
- `Work_of_Adhesion_mJ`
- `Peak_Retraction_Force_N`
- `Peak_Position_mm`

---

### Testing & Validation

#### Test Dataset: V17Tests (9 Conditions, 451 Layers)

**Test Conditions:**
1. 2p5PEO_1mm_Ramped_BPAGDA_0928 (32 layers)
2. 2p5PEO_1mm_Ramped_BPAGDA_Old (108 layers)
3. 2p5PEO_5mm_Constant_BPAGDA (21 layers)
4. 2p5PEO_5mm_RampedFaster_BPAGDA (21 layers)
5. 2p5PEO_5mm_Ramped_BPAGDA (21 layers)
6. Water_1mm_Constant_BPAGDA (108 layers)
7. Water_1mm_Ramped_BPAGDA (98 layers)
8. Water_5mm_RampedFaster_BPAGDA (21 layers)
9. Water_5mm_Ramped_BPAGDA (21 layers)

**Validation Results:**
- ✅ All 451 layers processed successfully
- ✅ Layer boundary detection: 100% accuracy
- ✅ Baseline detection: No false positives
- ✅ Metrics consistency: Mean and median values align
- ✅ Speed analysis: 22 unique speeds detected and analyzed

---

### Configuration Parameters

#### adhesion_metrics_calculator.py
```python
# Current Production Settings
smoothing_sigma = 0.5              # Gaussian smoothing for noise reduction
baseline_threshold_factor = 0.002  # Relative threshold for baseline detection
min_peak_height = 0.01             # Minimum peak force (N)
min_peak_distance = 50             # Minimum distance between peaks (samples)
```

#### RawData_Processor.py
```python
# Layer Detection Settings
gap_threshold = 8.0                # Time gap (seconds) between layers
sampling_rate = 50                 # Hz (20ms per sample)
```

---

### File Changes Summary

#### Modified Files
1. ✅ `support_modules/adhesion_metrics_calculator.py`
   - Updated: `_find_propagation_end_reverse_search()` method
   - Added: Time-based derivative calculations
   - Added: Baseline intersection verification

2. ✅ `support_modules/PeakForceLogger.py`
   - Integration: Now uses `AdhesionMetricsCalculator` by default
   - Parameter: `use_corrected_calculator=True` (default)
   - Output: Enhanced CSV format with 13 metrics

3. ✅ `post-processing/RawData_Processor.py`
   - Updated: `_find_layer_boundaries()` method
   - Changed: Position-based → Time-gap clustering

#### Created Files
1. ✅ `post-processing/plot_speed_analysis.py`
2. ✅ `post-processing/plot_speed_analysis_median.py`
3. ✅ `post-processing/plot_master_speed_analysis.py`
4. ✅ `post-processing/plot_master_speed_analysis_median.py`
5. ✅ `post-processing/plot_master_distance_analysis.py`
6. ✅ `post-processing/batch_v17_analysis.py`
7. ✅ `post-processing/analyze_single_folder.py`
8. ✅ `post-processing/test_baseline_detection.py` (debugging tool)

#### Documentation Files
1. ✅ `CHANGELOG.md` (this file)
2. ✅ `documentation/LAYER_BOUNDARY_DETECTION.md`
3. ✅ `post-processing/BATCH_V17_UPDATE_NOTES.md`
4. ✅ `post-processing/PEO_OLD_TEST_RESULTS.md`

---

### Backward Compatibility

#### ✅ Existing Functionality Preserved
- All existing Prince_Segmented.py functions work unchanged
- Old CSV files can still be processed
- Manual logging and automated logging both use new calculator
- No changes required to user workflow

#### ⚠️ CSV Format Changes
- **Impact:** New CSV files have additional columns
- **Compatibility:** Old analysis scripts may ignore new columns (safe)
- **Recommendation:** Update analysis scripts to leverage new metrics

---

### Deployment Checklist

#### Before Deploying to Production Printer:

1. ✅ **Code Integration Verified**
   - PeakForceLogger uses new calculator
   - RawData_Processor uses time-gap clustering
   - Post-print analysis uses updated modules

2. ✅ **Testing Completed**
   - 451 layers analyzed successfully
   - Layer detection validated
   - Baseline detection validated

3. 🔲 **File Cleanup** (See DEPLOYMENT_NOTES.md)
   - Remove test files
   - Archive old versions
   - Clean __pycache__ directories

4. 🔲 **Documentation Updated**
   - README.md updated
   - CHANGELOG.md completed
   - User guide created

5. 🔲 **Backup Current System**
   - Archive current working directory
   - Document current software versions
   - Save example output files

---

### Known Issues & Limitations

#### None Critical
All known issues from previous versions have been resolved:
- ✅ False baseline detection → FIXED
- ✅ Layer boundary detection → FIXED
- ✅ Inconsistent analysis between real-time and post-processing → FIXED

#### Recommendations for Future Work
1. **Adaptive Smoothing:** Consider speed-dependent smoothing sigma
2. **Multi-Material Support:** Test with different resin formulations
3. **Real-Time Feedback:** Add live baseline detection visualization
4. **Machine Learning:** Explore ML-based baseline detection for edge cases

---

### Support & Contact

**For Technical Issues:**
- Evan Jones: evanjones2026@u.northwestern.edu
- Professor Cheng Sun: c-sun@northwestern.edu

**Documentation:**
- `/documentation/` folder contains detailed technical docs
- `README.md` for general overview
- `STAGE_STALL_PREVENTION.md` for mechanical troubleshooting

---

### Version History

**Version 2025.10.03:**
- Time-based derivative baseline detection
- Time-gap layer clustering
- Speed analysis visualization suite
- Enhanced metrics output (13 columns)

**Version 2025.09.XX (Previous):**
- Initial unified calculator implementation
- Hybrid adhesion analysis system
- Position-based analysis (deprecated)

---

**END OF CHANGELOG**
