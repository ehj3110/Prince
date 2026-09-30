# In-Situ Relative Viscosity Drift Monitoring (Solvent Evaporation Tracking)
**Developer & Future Agent Implementation Guide**

---

**Date:** September 2026  
**Status:** ✅ Implemented and Validated in `Prince_Segmented.py` | ⏳ Queued for `Prince_Segmented_Unified.py`  
**Target Hardware:** $\varnothing 12.7\text{ mm}$ ($\frac{1}{2}\text{ inch}$) Aluminum Stage, Phidget Load Cell, Zaber Linear Stage  
**Primary Authors:** Cheng Sun Lab Team / Antigravity Pair-Programming  

---

## 1. Executive Summary

This document serves as the handover and architecture guide for any future agent or developer continuing work on the **In-Situ Viscosity & Solvent Evaporation Drift Monitoring System**.

### Core Value Proposition
Resin mixtures containing volatile components (reactive diluents, photoinitiators, or solvents like ethanol/acetone in composite/ceramic slurries) suffer from progressive solvent evaporation over printing sessions. This causes the fluid viscosity to rise nonlinearly, leading to delamination, suction failure, and mechanical stalls.

Rather than attempting hard-to-calibrate absolute rheometry in the field, this module implements a **self-referencing relative measurement system**:
1. **Zero External Calibration Required:** Does not require calibration oils, water, or chemical standards.
2. **Immune to Thermal Chassis Drift:** Uses the slope $m = \frac{d(F^{-1/3})}{dz}$ of the linearized Stefan squeeze curve, making it mathematically immune to $10 - 25\ \mu\text{m}$ thermal shifts in the zero-gap position $z_0$.
3. **Automatic Morning Baseline:** The first descent of the day (or when fresh resin is loaded) establishes the baseline slope $m_0$.
4. **Automated Print-Start Tracking:** Every subsequent print naturally samples the squeeze force during stage descent to Layer 1, computing $\Delta \mu\% = \left[\left(\frac{m_0}{m_k}\right)^3 - 1\right] \times 100\%$ and alerting operators if evaporation exceeds safety thresholds ($> 20\%$).

---

## 2. Mathematical Foundation

### 2.1 Classical Squeeze Flow
For a circular disk of diameter $D = 12.7\text{ mm}$ descending at constant velocity $v = -\dot{z}$ towards the vat floor, Stefan's equation governs hydrodynamic force:
$$F(z) = \frac{3\pi D^4 \mu v}{32 (z - z_0)^3}$$
where $C_{\text{geom}} = \frac{3\pi D^4}{32} \approx 7.662 \times 10^{-9}\text{ m}^4$.

### 2.2 Linearized Stefan Form & Datum Decoupling
Transforming $F$ to $Y = F^{-1/3}$:
$$F^{-1/3}(z) = m \cdot (z - z_0)$$
$$\text{Slope } m = \left(\frac{32}{3\pi D^4 \mu v}\right)^{1/3} \propto \mu^{-1/3}$$

Because $m = \frac{d(F^{-1/3})}{dz}$:
* Thermal expansion of stage mounts and mechanical compliance shifts the horizontal position $z_0$, but **does not alter the slope $m$**.
* The slope $m$ changes **solely if the viscosity $\mu$ changes**.

### 2.3 Relative Drift Formula
Comparing current run $k$ against morning baseline $0$:
$$\frac{\mu_k}{\mu_0} = \left(\frac{m_0}{m_k}\right)^3$$
$$\Delta \mu\% = \left[ \left(\frac{m_0}{m_k}\right)^3 - 1 \right] \times 100\%$$

* **$\Delta \mu\% \approx 0\%$:** Normal baseline reference.
* **$+10\% \le \Delta \mu\% < +25\%$:** Warning — noticeable solvent loss / thickening.
* **$\Delta \mu\% \ge +25\%$:** Critical Alert — severe solvent evaporation; operator should replenish diluent/solvent or adjust dwell times.

---

## 3. Subsystem Architecture & File Map

```
Prince_CurrentWorkingVersion/
│
├── support_modules/
│   ├── viscosity_analyzer.py          <-- Core mathematical engine & baseline persistence
│   ├── ViscosityMonitorWindow.py      <-- Dedicated secondary GUI window (Tkinter + Matplotlib)
│   └── reference_fluids_db.py         <-- Optional reference fluid library (PEG 400, Glycerol, etc.)
│
├── config/
│   └── daily_viscosity_baseline.json  <-- Auto-generated daily baseline storage (same-day validity)
│
├── tests/
│   └── test_viscosity_analyzer.py     <-- Comprehensive unit test suite (9 tests, all passing)
│
├── documentation/technical/
│   ├── RESIN_VISCOSITY_SQUEEZE_FLOW_PHYSICS.md   <-- Phase 0: Physics documentation
│   ├── VISCOSITY_DATA_ANALYSIS_METHODS.md        <-- Phase 1: Analysis methods & solvers
│   └── IN_SITU_VISCOSITY_DRIFT_HANDOVER.md       <-- This handover document
│
├── Prince_Segmented.py                <-- Currently ACTIVE implementation
└── Prince_Segmented_Unified.py        <-- QUEUED for future integration (notes added)
```

---

## 4. Current Implementation in `Prince_Segmented.py`

### 4.1 UI Controls & Window Hooks
* **Button added (Line ~126):**
  `self.b_viscosity_monitor = Button(win, text="Viscosity Monitor", command=self.open_viscosity_monitor_window)` placed at `x=1205, y=60`.
* **Checkbox in Auto-Home Control Frame (Line ~258):**
  `self.enable_preprint_viscosity = BooleanVar(value=True)`
  `self.chk_preprint_viscosity = Checkbutton(self.frame_auto_home, text='Scan Viscosity at Start', variable=self.enable_preprint_viscosity)`
* **Window Launcher Method (Line ~2260):**
  `self.open_viscosity_monitor_window()` links `self.axis`, `self.sensor_data_window_instance.force_gauge_manager`, and the main app reference.

### 4.2 Pre-Print Descent Hook in `print_t` (Line ~1060 & ~2284)
* **Trigger:** When starting `Run-Cont.` or `Run-Step`, before moving directly to `self.reference`:
  ```python
  if hasattr(self, 'enable_preprint_viscosity') and self.enable_preprint_viscosity.get():
      self._perform_preprint_viscosity_measurement()
  else:
      self.axis.move_absolute(position=self.reference, unit=Units.LENGTH_MILLIMETRES, wait_until_idle=True)
  ```
* **Motion Profile in `_perform_preprint_viscosity_measurement()`:**
  1. Descend to $z_{\text{ref}} + 0.800\text{ mm}$ at normal speed.
  2. Dwell $0.4\text{ s}$ and tare force gauge to cancel buoyancy.
  3. Descend at constant $v = 1.0\text{ mm/s}$ down to $z_{\text{ref}} + 0.150\text{ mm}$ (safe asymptotic rigid zone, well above membrane contact).
  4. Stop axis and analyze $(z, F)$ via `ViscosityAnalyzer.analyze_stefan_linearized()`.
  5. Check `daily_baseline`:
     - If none: Save as today's baseline ($0.0\%$ drift).
     - If exists: Compute $\Delta \mu\%$ and report to status bar and GUI dashboard.
  6. Complete move down to $z_{\text{ref}}$.

---

## 5. Upcoming Task: Porting to `Prince_Segmented_Unified.py`

Future agents should follow this step-by-step migration checklist:

### Checklist for `Prince_Segmented_Unified.py` Integration:

- [ ] **Step 1: Verify Imports**
  Ensure `support_modules/ViscosityMonitorWindow.py` and `support_modules/viscosity_analyzer.py` are importable from `Prince_Segmented_Unified.py`.
- [ ] **Step 2: Add GUI Button & Instance Variables**
  - In `MyWindow.__init__`:
    - Initialize `self.viscosity_monitor_window = None`
    - Initialize `self.enable_preprint_viscosity = BooleanVar(value=True)`
    - Place `self.b_viscosity_monitor` on the top bar or inside the sensor/tool frame.
    - Place `self.chk_preprint_viscosity` near the stage homing controls.
- [ ] **Step 3: Port Window Launcher**
  Copy `open_viscosity_monitor_window(self)` from `Prince_Segmented.py` to `Prince_Segmented_Unified.py`.
- [ ] **Step 4: Hook into Unified Print Orchestrator / `print_t`**
  In `Prince_Segmented_Unified.py`, identify the stage initialization before Layer 1 (where stage approaches `self.reference`), and wrap with `_perform_preprint_viscosity_measurement(self)`.
- [ ] **Step 5: Verify Hardware Context / Stage Adapter**
  Note that `Prince_Segmented_Unified.py` uses modular hardware adapters (`ZaberStageAdapter`, `HardwareContext`). Ensure that `_perform_preprint_viscosity_measurement` accepts either raw Zaber axis objects or the new adapter interface.
- [ ] **Step 6: Run Unit & Compilation Tests**
  ```powershell
  C:\Python314\python.exe tests/test_viscosity_analyzer.py
  C:\Python314\python.exe -m py_compile Prince_Segmented_Unified.py
  ```

---

## 6. How to Test & Verify

### 1. Automated Regression Test Suite
Run the test suite covering all 9 analytical, rheological, and persistence tests:
```powershell
C:\Python314\python.exe tests/test_viscosity_analyzer.py
```
*Expected Output:* `Ran 9 tests in ~0.17s - OK`.

### 2. Dry-Run / Simulation Mode
Both `Prince_Segmented.py` and `ViscosityMonitorWindow.py` include **built-in hardware simulation**:
* If Zaber stage or Phidget force gauge is disconnected, clicking **"Quick Single Probe"** or **"Multi-Speed Probe"** generates synthetic hydrodynamic curves with realistic noise.
* Testing relative drift in simulation mode automatically simulates $+14\%$ thickening after baseline is set to demonstrate the alert UI.

---

## 7. Reference Contact & Lab Context
* **Lab:** Professor Cheng Sun Lab, Northwestern University.
* **Lead Students / Maintainers:** Boyuan Sun (`boyuansun2026@u.northwestern.edu`), Evan Jones (`evanjones2026@u.northwestern.edu`).
* **Hardware:** Prince Segmented DLP 3D-Printer, Phidget load cell bridge, Zaber linear motion stage.
