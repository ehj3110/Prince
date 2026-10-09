# Prince Modern GUI

**Date:** 2026-10-09  
**Entry:** [`Prince_Modern.py`](../Prince_Modern.py)  
**Launch:**

```powershell
.\.conda\python.exe Prince_Modern.py
```

Or double-click [`Launch_Prince_Modern.bat`](../Launch_Prince_Modern.bat).  
`Prince_Modern.py` also restarts itself under `.conda\python.exe` if the current interpreter is missing PySide6.

## Purpose

PySide6 rebuild of the Prince printer control GUI. Visuals follow the original Modern mockup: charcoal panels (`#19202A` / `#1F2130`), dusty-lavender card headers and progress (`#8870A3`), and the bundled **Inter** font (`prince_modern/fonts/`). **Print and hardware behavior** come from a withdrawn copy of Unified ([`prince_modern_unified_source.py`](../prince_modern_unified_source.py)) so Continuous/Stepped/`print_t` stay at Unified parity while the shell is new.

[`Prince_Segmented_Unified.py`](../Prince_Segmented_Unified.py) is **unchanged** (stable Tk baseline).

## Architecture

| Piece | Role |
|-------|------|
| `Prince_Modern.py` | `QApplication` entry |
| `prince_modern/main_window.py` | Mockup layout (cards, log, viz, footer) |
| `prince_modern/theme.py` | QSS (mockup lavender `#8870A3`, charcoal cards, Inter) |
| `prince_modern/controller.py` | Qt ↔ hidden Unified `MyWindow` bridge; Monitoring Suite launcher |
| `prince_modern_unified_source.py` | Full Unified backend (not shown) |

Tk is created withdrawn and pumped with a 50 ms `QTimer` so satellite Tk windows (Sensor Panel, Image Modification, etc.) still work.

## Feature gap checklist (review)

### Included in Modern (parity or better)

| Feature | Notes |
|---------|--------|
| Run Cont / Run Step / Stop | Via Unified backend |
| Image dir, LED, print params, stage | Qt fields synced to Unified entries |
| Projection Video Pattern toggle | Checkbox → `projection_mode_var` |
| Sensor Logging / Monitoring | Existing Tk panels; mutual exclusion mirrored |
| Image Mod / Exp Conditions / Ramped Cylinder | Unified launchers |
| Disconnect / Reconnect DLP | Unified |
| SessionManager autoload | Backend `__init__` still runs it |
| System Log panel | **New** (Unified had no visible log) |
| Header PRINTING + Z chips | **New** |
| Footer progress strip | **New** |
| **Monitoring Suite** | **New vs Unified** (subprocess, `close_fds=True`) |
| Slice preview + stack | **Generate visualization** loads PNGs on demand (no auto-refresh) |
| Power-mode warning | Shown when not in Video Pattern mode |

### Deferred (still in Unified code paths / other apps)

| Feature | Decision |
|---------|----------|
| Sandwich / Auto-Home UI | Logic may still exist in backend; panels stay hidden |
| Smooth retraction/lifting checkboxes | Vars exist; no Modern UI |
| Viscosity Monitor | Not in Unified; later |
| Full 3D lattice viz | Placeholder until requested |
| Rewriting Sensor/IM windows to PySide6 | Later |
| `goto_position` button | Backend has method; no button yet |

### Cosmetic / TBD

- Mockup had duplicate “Simple txt generator” — Modern has one (Print Configuration).
- Units use Unified conventions (µm, s, µm/s, mm/s²).

## Risks

- Qt + Tk on one thread: keep pumping Tk; avoid long blocking in slots where possible (print work stays in Unified’s print thread).
- Do not open Sensor Panel and Monitoring Suite force gauge together.
- Do not call DLP `standby()`.
