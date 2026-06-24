# Image Modification GUI — Export Package

Standalone image-processing tool for pre-processing SLA print layers before sending
them to the printer. Runs independently of the main Prince printing software.

---

## How to use

### Option A — Executable (recommended for printer computer)
Double-click **`ImageModificationGUI.exe`**.  
No Python, no installation required.

### Option B — Python script (development computer)
```
pip install -r requirements_image_gui.txt
python support_modules/ImageModificationWindow.py
```

---

## Features

| Section | What it does |
|---|---|
| **Edge Enhancement** | Brightens pixels near part boundaries to compensate for optical blur. |
| **Global Blur Enhancement** | Applies a spatially-varying intensity map (globe shape) to compensate for projector brightness fall-off. |
| **Image Padding** | Inserts a black padding frame after each real layer (`{x}_1.png`) to improve layer separation. |
| **Scattering Compensation** | Dims pixels near part boundaries to counter resin light scattering. Inverse of Edge Enhancement. |

### Local-only helpers (not in export package)

The integrated Prince Image Modification window includes additional utilities:
- Cone Generator
- Instruction Ramping

These helpers are currently implemented in the main project GUI and are not included in this standalone export package.

### Key parameters

**Blur** — Gaussian sigma (px). Controls how far the effect extends from the boundary.  
**Falloff** — Kernel size (px, odd integer). Controls the Gaussian window size independently of Blur.
- `0` (default) → auto-computes as `4×Blur+1`.
- Reduce for dense lattices to prevent the kernel spanning multiple struts simultaneously.

**Min / Max** — Output intensity range. Min sets the darkest output value at the boundary; Max sets the brightest interior value (normally 255).

---

## Workflow

1. Click **Browse** and select the folder containing your `.png` layer images.
2. Click **Load** to display a sample layer in the preview panel.
3. Adjust parameters and click **Preview** to see the effect on the loaded layer.
4. Click **Build** to process the entire folder. Output is saved to a new subfolder.

---

## File structure

```
ImageModificationGUI_export/
├── ImageModificationGUI.exe          ← Standalone executable (copy to printer computer)
├── launch_image_modification.bat     ← Alternative launcher (requires Python in PATH)
├── requirements_image_gui.txt        ← Python dependencies for Option B
├── README.md                         ← This file
└── support_modules/
    ├── ImageModificationWindow.py    ← Main GUI
    ├── DefinitionsWindow.py          ← In-app parameter reference
    └── image_modification/
        ├── processor.py              ← Orchestrates the processing pipeline
        ├── edge_enhancement.py
        ├── global_enhancement.py
        ├── scattering_compensation.py
        ├── padding.py
        └── clip_pressure_compensator.py
```

---

## Notes

- Images named `*_1.png` (padding outputs) are automatically excluded from the input list.
- Feature Depth Correction is intentionally excluded from this package (experimental, development use only).
- The `.venv_image_gui/` folder is created automatically by `launch_image_modification.bat` on first run and can be ignored.

---

*Last updated: March 2026*
