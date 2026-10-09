# System Monitoring Dashboard Guide

**Date:** 2026-10-02  
**Launch:** Prince **Monitoring Suite** button, or:

```powershell
.\.conda\python.exe -m calibration_modules.monitoring_dashboard
```

Optional: `--image-dir PATH` for slice geometry, `--triple-force` / `--single-force` to override force mode.

---

## What It Is

A separate **PySide6** process that shows live printer sensors while the main **Tkinter** Print GUI (`Prince_Segmented.py`) stays free for printing. Prince starts it with `close_fds=True` so the DLP HID handle is not inherited.

| Card | Sensor | Notes |
|------|--------|--------|
| Optical | Allied Vision Alvium 1800 U-511m | Continuous Vimba X stream |
| Thermal | Seek InspectionCAM | Radiometric °C; no AGC LINEAR |
| Force | Phidget 4x Bridge | Sum of load cells 0+1+2 when `MODE=TRIPLE` |
| Power | Thorlabs PM100A (NI-VISA) | Measured mW + expected dashed line |
| Geometry | Slice folder from `--image-dir` / Prince path | Layer follows `data/monitor_print_state.json` |

Missing hardware is covered with a gray “unavailable” banner. Do **not** invent simulated camera or force feeds for demos.

---

## Process Isolation Rules

1. Use the project interpreter: `.conda\python.exe` (Python 3.14 + PySide6 + pyvisa + Phidget22 + seekcamera + vmbpy).
2. Keep **Sensor Panel** closed while the dashboard owns the Phidget (one process per bridge).
3. Do **not** call DLP `standby()` from this stack; release the light engine with HDMI mode and `close()` when calibration scripts finish.
4. Close the TI **DLPC900REF-GUI** before any script that opens the projector.

---

## Force Gauge (Triple Load Cells)

### Hardware

Three smaller load cells in parallel, wired to Phidget bridge ports **0, 1, and 2**. Real platform force is the **sum** of the three calibrated channels.

### Auto mode

On start, the newest `data/force_gauge_calibration_*.txt` (or repo-root match) is loaded. If it has `MODE=TRIPLE` and `GAIN_0..2` / `OFFSET_0..2`, the dashboard opens all three channels and plots the sum. Status chip: `live · triple sum`.

### Sampling

Default **40 Hz (25 ms)**. Phidget `dataInterval` is 25 ms. Plot history is 50 s of **total** force only.

### Display

- Total force to **three decimals**.
- Monospace readout with a leading space when non-negative so digits do not jump when the minus sign appears.
- Per-channel labels are **not** shown in the UI (they caused layout shake).

### Tare

**Tare** zeros the session readout (0.5 s average of total Newtons). It does **not** rewrite file offsets. An automatic tare also runs shortly after connect.

### Calibrate (same dialog flow as Sensor Data Window)

1. Ensure all three cells are unloaded → OK.  
2. Average voltage ratios ~0.5 s → `OFFSET_i`.  
3. Enter **total** known force in N (e.g. 9.81 for 1 kg).  
4. Apply that load **centered** so cells share → OK.  
5. Average ratios → proportional gains (docs method):

\[
\Delta V_i = V_i - \mathrm{OFFSET}_i,\quad
F_i = F_{\mathrm{total}}\frac{\Delta V_i}{\sum_j \Delta V_j},\quad
\mathrm{GAIN}_i = \frac{F_i}{\Delta V_i}
\]

6. Show share %; warn if a cell is outside ~25–40%.  
7. Hot-apply into the live thread, session-tare, optionally save:

```
data/force_gauge_calibration_YYYYMMDD_HHMMSS.txt
MODE=TRIPLE
GAIN_0=...
OFFSET_0=...
GAIN_1=...
OFFSET_1=...
GAIN_2=...
OFFSET_2=...
```

Production `ForceGaugeManager` / Sensor Panel remain **single-channel**. Triple calibrate/tare for the tour lives in this dashboard only. Background: [TRIPLE_FORCE_GAUGE_GUIDE.md](TRIPLE_FORCE_GAUGE_GUIDE.md), [QUICK_CALIBRATION_GUIDE.md](QUICK_CALIBRATION_GUIDE.md).

---

## Optical Power (Thorlabs PM100A)

### Driver

[`calibration_modules/thorlabs_pm100a.py`](../calibration_modules/thorlabs_pm100a.py) — NI-VISA / USBTMC, vendor `0x1313`, SCPI. Default wavelength **385 nm**. Hardware auto-range is **off**; software steps the watt range up when a reading exceeds **75%** of full scale (never steps down).

### Density model

Two-point line from LED command **10** and **100** on the white calibration square (`Power_255.png`, 504×504 white pixels, pitch 4.005 µm → 4.0744 mm²). Saved in [`data/uv_power_calibration.json`](../data/uv_power_calibration.json):

- `measured_mW_at_10`, `measured_mW_at_200` (historical key: milliwatts at the **high** command, which is 100), `area_mm2`, `command_low`, `command_high`.

\[
\rho(p) = \rho_{10} + (\rho_{100}-\rho_{10})\frac{p-10}{90},\quad
P_{\mathrm{expected}} = \rho(p)\cdot A_{\mathrm{cm}^2}
\]

Expected power uses the current layer white-pixel area from the print job / monitor state.

### Recalibrate projector + meter

```powershell
.\.conda\python.exe -u -m calibration_modules.power_density_calibration
```

Projects the square at 10 then 100, waits **4 s** for the beam to settle, then iterates meter ranges and keeps a reading between ~2% and 40% of full scale. Stress check against stent layers:

```powershell
.\.conda\python.exe -u -m calibration_modules.power_expected_stress_test
```

Results: `data/stent_power_comparison.csv`.

### Dashboard power card

Wavelength combo 365 / **385** / 405. Record 10 / Record 100 can update the JSON from a live projection. Solid = measured mW; dashed = expected mW.

---

## Print Progress Link

While printing, Prince writes [`data/monitor_print_state.json`](../data/monitor_print_state.json) (layer, power, running). The dashboard polls every 250 ms and advances the geometry card. Cleared when the print finishes.

---

## Module Map

| Path | Role |
|------|------|
| `calibration_modules/monitoring_dashboard/window.py` | PySide6 UI |
| `calibration_modules/monitoring_dashboard/workers.py` | Optical/thermal/force/power threads; triple force cal math |
| `calibration_modules/monitoring_dashboard/theme.py` | Dark QSS |
| `calibration_modules/thorlabs_pm100a.py` | PM100A SCPI |
| `calibration_modules/power_density_calibration.py` | Projector + density script |
| `calibration_modules/power_expected_stress_test.py` | Expected vs measured check |
| `calibration_modules/power_range_sweep.py` | Meter range validation |
| `calibration_modules/print_monitor_state.py` | Layer state file I/O |
| `calibration_modules/monitoring_requirements.txt` | pyvisa / pyvisa-py |

Prince entry: `MyWindow.open_camera_view_window` → `subprocess.Popen([.conda\python.exe, -m, calibration_modules.monitoring_dashboard], close_fds=True)`.

Shared light-engine helpers (used by print and cal scripts, no Zaber home): `MyWindow.open_projection_window`, `enter_pattern_mode`, `show_projection`, `set_projection_power`, `release_light_engine`.

---

## Tour / Demo Checklist

1. Sensor Panel closed; TI light-engine GUI closed.  
2. Open Print GUI, then **Monitoring Suite** (or standalone command above).  
3. Confirm force `live · triple sum`, 40 Hz, cameras/power live.  
4. Optional: **Calibrate** with a known total weight; save; **Tare**.  
5. Start a print; force plot keeps summing ch0–2; expected UV line tracks layer area and LED power.  

---

## Related Images

- Preview: [monitoring_dashboard_preview.png](monitoring_dashboard_preview.png)  
- Suite cards: `monitoring_suite_optical.png`, `monitoring_suite_thermal.png`, `monitoring_suite_sensors.png`
