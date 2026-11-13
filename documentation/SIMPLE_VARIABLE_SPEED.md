# Simple Variable Speed

**Date:** 2026-11-13  
**Status:** Prince Modern + Prince Segmented (continuous / Run Cont.)  
**Entry (operator):**  
- **Prince Modern:** System Actions → **Simple Variable Speed**  
- **Prince Segmented:** button under **Monitoring Suite** (launches the same Qt dialog via `.conda\python.exe`)  
**Core module:** [`support_modules/simple_variable_speed.py`](../support_modules/simple_variable_speed.py)  
**Dialog:** [`prince_modern/simple_variable_speed_dialog.py`](../prince_modern/simple_variable_speed_dialog.py)  
**Tests:** [`tests/test_simple_variable_speed.py`](../tests/test_simple_variable_speed.py)  
**UI preview:** [`analysis_summaries/simple_variable_speed_dialog_preview.png`](analysis_summaries/simple_variable_speed_dialog_preview.png)

## Purpose

For continuous (Run Cont.) prints, layer exposure time and LED intensity should track local geometry so peel / Stefan adhesion load stays closer to a chosen control condition. Simple Variable Speed:

1. Measures per-layer max external distance \(d_{\max}\) on **raw** slice PNGs (Euclidean distance transform).
2. Scales Z speed with a fixed \(\beta = 4\) Stefan-style law and a tunable correction factor \(C\).
3. Couples LED PWM so unitless dose \(\text{Time} \times \text{LED Current}\) stays matched to the control dose (except where parameter limits clamp values).
4. Rewrites **only** the Time and Intensity columns of the existing Prince instruction `.txt`, then reloads the folder.

It does **not** insert dark-time padding, change Thickness / filenames / other columns, or apply Z-smoothing.

## Where it lives in Prince

| Piece | Role |
|-------|------|
| `Prince_Modern.py` | Modern operator shell |
| `prince_modern/main_window.py` | System Actions button after Monitoring Suite |
| `prince_modern/controller.py` | Opens dialog; on Apply calls `input_directory()` reload |
| `Prince_Segmented.py` | Legacy Tk main window: **Simple Variable Speed** under Monitoring Suite; subprocess launch + reload |
| `prince_modern/simple_variable_speed_dialog.py` | Qt UI: controls + YZ / speed plots (`python -m prince_modern.simple_variable_speed_dialog <folder>`) |
| `support_modules/simple_variable_speed.py` | EDT, hole fill, schedule math, `.txt` rewrite |

Launch either operator UI:

```powershell
.\.conda\python.exe Prince_Modern.py
# or
.\.conda\python.exe Prince_Segmented.py
```

Load a print folder first, then open **Simple Variable Speed**.

## Operator workflow

1. Load the print folder that contains `<foldername>.txt` and the slice PNGs listed in that file.
2. Open **System Actions → Simple Variable Speed**.
3. **Control layer**
   - Set the control layer index (1-based).
   - Click **Use control layer** to measure \(d_{\max}\) on that layer and write **Size d_max** (in Fill holes).
4. **Parameter limits** (optional, blank = no clamp)
   - **LED Current** Min / Max (0–255 PWM).
   - **Speed (µm/s)** Min / Max.
5. **Manual control**
   - **Control speed (µm/s)** — \(v_0\), the reference continuous speed.
   - **Dose (layer time * LED Current)** — unitless control dose.
   - **Correction Factor** — \(C\) (see below).
6. **Fill holes**
   - **Size d_max** — control feature size (mm); required for Update/Apply.
   - **Minimum hole size (µm)** + **Enable** — selectively fill enclosed black holes whose ECD is at or below this threshold before EDT (UI in µm; converted to mm internally).
7. **Update** — recompute schedule and refresh plots (geometry cache reused when only speed/dose/\(C\)/size/limits change).
8. **Apply to instruction file** — overwrite Time & Intensity; auto-reload into Prince.
9. **Browse…** — pick a different print folder (clears geometry cache).

Default dialog size: **900 × 720**.

## Speed law

With control size \(R_0\) (**Size d_max**) and layer size \(R = d_{\max}\):

\[
\tilde{R} = \frac{R}{R_0},\quad
v = \frac{v_0}{1 + C \cdot \max(0,\ \tilde{R}^{4} - 1)}
\]

- \(\beta = 4\) is fixed (Simple / Stefan adhesion scaling).
- \(C\) is the **Correction Factor**:

| \(C\) | Meaning |
|------:|---------|
| 0.0 | No geometry slowdown |
| 1.0 | Default Stefan-Adhesion |
| 1.5 | 50% extra correction |

Empty layers (no white pixels) keep control speed and PWM 0; time is still thickness / \(v_0\).

## Dose coupling

Unitless dose at the control condition:

\[
\text{dose} = t_{\text{ctrl}} \times \text{PWM}_{\text{ctrl}}
\]

For a layer with thickness \(h\) (µm from the `.txt` Thickness column) and scheduled speed \(v\):

\[
t = \frac{h}{v},\quad
\text{PWM} \propto \text{dose}\cdot\frac{v}{v_0}
\]

so \(t \times \text{PWM}\) tracks the control dose when limits do not clamp.

**Soft warning:** if any live layer would use PWM below 5, the dialog warns but still allows Apply. Prefer a smaller \(C\) or LED/speed limits rather than dark padding.

## Geometry notes

- Pixel pitch: **4.005 µm** (`PX_PITCH_MM = 0.004005`).
- \(d_{\max}\): max EDT distance on solid (white) pixels to the exterior background, after optional selective hole fill.
- Hole fill: enclosed black components with equivalent circular diameter ≤ threshold are painted white before EDT; larger voids stay open.
- EDT uses OpenCV `distanceTransform` when available (with bbox crop + thread pool); SciPy is the fallback.
- Preview plots: isotropic **YZ** midplane strip (left) and **speed vs Z** (right), Z-aligned.

## Instruction file contract

- Path: `<print_folder>/<print_folder.name>.txt` (tab-separated, ≥10 columns).
- **Rewritten:** Time, Intensity (PWM).
- **Preserved:** all other columns (including Thickness and image filenames).
- Apply triggers `host.input_directory()` so Run Cont. sees the new schedule.

## Parameter limits behavior

When Min/Max are filled:

1. Speed is computed from the law, then clamped to Speed Min/Max (live layers only).
2. PWM is computed from the dose law at that speed, then clamped to LED Current Min/Max.
3. Clamping can break exact dose tracking at the wall; that is intentional hardware/process limiting.

Blank cells leave that bound unconstrained.

## Tests & diagnostics

```powershell
.\.conda\python.exe tests/run_all_tests.py simple_variable_speed
.\.conda\python.exe -m unittest tests.test_simple_variable_speed -v
```

Diagnostic scripts (optional figures under `documentation/analysis_summaries/`):

| Script | Output |
|--------|--------|
| `debug/capture_simple_variable_speed_dialog.py` | Dialog screenshot |
| `debug/plot_simple_variable_speed_samples.py` | Representative speed profiles |
| `debug/plot_simple_variable_speed_normalized.py` | Uncapped normalized profiles |
| `debug/plot_simple_variable_speed_xz_paired.py` | XZ/YZ + speed paired figures |

## Out of scope (this MVP)

- Dark-time / Regime-B padding
- Stepped (Run Step) schedule rewriting
- Z motion smoothing
- Non-raw / pre-processed PNG inputs (always uses instruction-listed files as-is)
- Native Tk rewrite of the dialog (Segmented launches the existing PySide6 dialog in a subprocess)
