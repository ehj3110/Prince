# Start here — handoff for a coding assistant

**Repo:** Prince resin DLP printer control (`https://github.com/ehj3110/Prince.git`, branch `main`)  
**Updated:** 2026-10-09  
**Audience:** A new coding AI opening this workspace. Read this before editing.

This is lab hardware, not a web app. Changes can move a Zaber stage, fire a DLP projector, or claim a USB device that another process already owns. Prefer reading the file you are about to change over guessing from older docs. Several guides under `documentation/` describe earlier generations of the GUI.

## What to run

Use the project interpreter. System Python and a generic Anaconda `dev` env often lack PySide6, vmbpy, Phidget22, and pyvisa.

```powershell
.\.conda\python.exe Prince_Modern.py
.\.conda\python.exe -m calibration_modules.monitoring_dashboard
```

`Prince_Modern.py` and `Launch_Prince_Modern.bat` re-exec under `.conda\python.exe` when the current interpreter has no PySide6. `.conda/` is gitignored and must be recreated on a new PC. Machine setup is in `documentation/DEPLOYMENT_GUIDE.md` (section “Moving the printer onto a new desktop”).

Check syntax with:

```powershell
.\.conda\python.exe -m py_compile <file.py>
```

## Which program is current

| Entry | Role | Touch it when |
|-------|------|----------------|
| `Prince_Modern.py` + `prince_modern/` | Current operator UI (PySide6) | Layout, theme, buttons, viz, launching tools |
| `prince_modern_unified_source.py` | Withdrawn copy of Unified. Hidden Tk window. Real print, stage, and DLP behavior | Print logic, field names, hardware calls used by Modern |
| `Prince_Segmented_Unified.py` | Stable Tk baseline. **Leave it unchanged** unless the user explicitly asks | Reference only for Modern work |
| `Prince_Segmented.py` | Older Tk app. Still has Camera View and Monitoring Suite hooks | Only if the task names this file |
| `Prince_Segmented_VideoPattern.py` | Older video-pattern Tk app | Only if the task names this file |
| `calibration_modules/monitoring_dashboard/` | Live sensor dashboard, separate process | Cameras, force, power, slice geometry on the monitor |

Modern does not reimplement printing. `prince_modern/controller.py` loads `prince_modern_unified_source.py` as a withdrawn Tk `MyWindow` and pumps Tk with a 50 ms `QTimer`. Qt fields sync into that window. Satellite tools (Sensor Panel, Image Modification, Experimental Conditions, Ramped Cylinder) are still Tk.

If you change print behavior for Modern, edit `prince_modern_unified_source.py`, not `Prince_Segmented_Unified.py`. Those two files can drift. Say so in the summary when you change only one of them.

## Map of the tree

| Path | What lives there |
|------|------------------|
| `prince_modern/main_window.py` | Cards, log, stage, **Generate visualization** |
| `prince_modern/theme.py` | QSS. Mockup palette: window `#19202A`, cards `#1F2130`, headers and progress `#8870A3` |
| `prince_modern/fonts/` | Bundled Inter (SIL OFL). `theme.load_fonts()` registers them |
| `prince_modern/controller.py` | Qt ↔ Tk bridge, Monitoring Suite subprocess |
| `support_modules/` | DLP (`pycrafter9000.py`), Zaber, Phidget force, session, adhesion math |
| `calibration_modules/` | Alvium (`vmbpy`), Seek thermal, Thorlabs PM100A, power-calibration scripts |
| `data/` | UV calibration JSON, triple-cell cal files, `monitor_print_state.json` |
| `documentation/` | Operator guides. Start with the two below, then `CHANGELOG.md` |
| `post-processing/`, `batch_processors/` | After a print. Not on the live control path |

Deeper guides:

- `documentation/PRINCE_MODERN_GUI.md` — shell, feature gaps, risks
- `documentation/MONITORING_DASHBOARD_GUIDE.md` — sensors, force cal/tare, UV expected power
- `documentation/CALIBRATION_FOLDER_INDEX.md` — calibration module map
- `documentation/PRINCE_UNIFIED_GUI.md` — Tk Unified behavior the Modern backend copies

`DOCUMENTATION_INDEX.md` still leads with an old Phase 1 shutdown-instrumentation project. Do not treat `NEXT_STEPS.md` as the current task list.

## Hardware rules

These are easy to violate and expensive to discover at the printer.

1. **Do not call DLP `standby()`.** Release the light engine with HDMI mode and `close()`. `standby()` has left the LightCrafter needing a power cycle.
2. **One owner for the Phidget bridge.** Sensor Panel (`ForceGaugeManager`, single channel) and the monitoring dashboard (channels 0+1+2 when the newest `force_gauge_calibration_*.txt` has `MODE=TRIPLE`) must not run together.
3. **Launch the monitor as its own process** with `close_fds=True` so it does not inherit the DLP HID handle. That is already how Modern starts it.
4. **Close TI DLPC900REF-GUI** before any script that opens the projector. The HID is exclusive.
5. **Do not fake live camera or force data** in the dashboard when hardware is missing. Gray “unavailable” covers are intentional.
6. **Alvium exposure** is manual. Cap is 0.5 s (`500000` µs). Do not turn ExposureAuto back on.
7. **PM100A** is NI-VISA, wavelength 385 nm, USBTMC via Thorlabs Driver Switcher. Expected UV power is density(LED command) × white slice area, from `data/uv_power_calibration.json`.
8. **Print position crosses processes only through** `data/monitor_print_state.json` (`calibration_modules/print_monitor_state.py`). The dashboard does not share memory with Prince.
9. **Triple force** is the sum of cells on ports 0, 1, and 2. Default sample period is 25 ms (40 Hz). Calibrate/Tare on the dashboard match the Sensor Data Window dialogs and use proportional total-force math. Tare does not rewrite file offsets.

## UI rules for Prince Modern

- Card headers are the dusty lavender bars from the mockup photo, not the flat gray titles used by the Sensor Monitor.
- Corners stay moderately rounded. The UI font is Inter, loaded from `prince_modern/fonts/`. The system log stays monospace.
- The build-visualization panel stays empty until the user clicks **Generate visualization**. Do not put a timer back on the slice preview. An earlier timer plus a pixmap-driven label made the slice grow forever. Feed labels use `QSizePolicy.Ignored` for that reason.

## Known gaps (do not “finish” these unless asked)

Tracked in `documentation/PRINCE_MODERN_GUI.md`:

- Sandwich and Auto-Home panels stay hidden.
- No viscosity monitor in Modern.
- 3D preview is a tinted stack stand-in, not a full lattice viewer.
- Sensor Panel, Image Modification, and Experimental Conditions are still Tk.
- No `goto_position` button yet.

## How to work in this repo

- Match existing names and patterns in the file you edit. Modern, Unified, and the dashboard do not share one style.
- Keep edits scoped to the task. This tree has several full printer GUIs; a drive-by cleanup across all of them will fight the user.
- Update `documentation/CHANGELOG.md` when a change is something an operator or the next assistant needs to know. Update the matching guide (`PRINCE_MODERN_GUI.md` or `MONITORING_DASHBOARD_GUIDE.md`) when behavior changes.
- Do not commit `.conda/`, `__pycache__/`, or `Printing_Logs/`.
- Commit and push only when the user asks. Remote is `origin` → `https://github.com/ehj3110/Prince.git`.
- On this Windows checkout, `git` is 2.30 and rejects `git commit --trailer`. If a wrapper injects that flag, commit with `git commit -F <message file>` through `subprocess` calling `C:\Program Files\Git\cmd\git.exe`.

## First files to open for a typical task

| Task | Open |
|------|------|
| Modern layout or theme | `prince_modern/main_window.py`, `prince_modern/theme.py` |
| A button does the wrong hardware thing | `prince_modern/controller.py`, then the matching method in `prince_modern_unified_source.py` |
| Monitor plot, force, exposure, power | `calibration_modules/monitoring_dashboard/window.py`, `workers.py` |
| UV calibration numbers | `calibration_modules/power_density_calibration.py`, `data/uv_power_calibration.json` |
| “Why did the new PC fail to launch?” | `documentation/DEPLOYMENT_GUIDE.md`, `Prince_Modern.py` bootstrap |
