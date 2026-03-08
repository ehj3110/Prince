# Image Modification Module

**Authors:** Professor Cheng Sun, Evan Jones
**Location:** `support_modules/ImageModificationWindow.py` and `support_modules/image_modification/`

---

## Overview

The Image Modification module is a GUI tool integrated into the main Prince printer application. It pre-processes SLA/DLP projection images before printing to compensate for known optical and resin-flow artifacts. It can also be run as a standalone window for quick testing without launching the full printer GUI.

### Problem Being Solved

DLP/SLA resin printers cure each layer by projecting a grayscale bitmap. Several physical effects distort the actual dose received at each point:

1. **Optical blur** — UV light scatters slightly, causing features to receive dose from neighboring illuminated regions. Edge pixels are most affected; inner pixels less so. This is corrected by **Edge Enhancement**.

2. **Radial intensity fall-off** — The projector's light path is not perfectly uniform; the center is typically dimmer than the edges. For symmetrical parts this is corrected by **Global Enhancement (Symmetric)**; for asymmetric parts, **Global Enhancement (Asymmetric)** adapts the gradient per-quadrant.

3. **Resin pre-curing / overcuring for dense lattices** — In lattice structures, resin flows from the outer bath through black channels to reach the white (curing) features. As it travels, scattered UV partially cures it. Features deep in the lattice receive pre-cured resin, causing overcuring relative to features at the perimeter. This is corrected by **Feature Depth Correction**.

4. **Layer-to-layer exposure normalization** — When printing materials that require periodic blank exposure breaks, a black frame can be inserted after every image using **Padding Normalization**.

---

## File Structure

```
support_modules/
├── ImageModificationWindow.py        # Tkinter GUI window
└── image_modification/
    ├── __init__.py                   # Package exports
    ├── edge_enhancement.py           # Edge Enhancement sub-routine
    ├── global_enhancement.py         # Global Enhancement (symmetric + asymmetric)
    ├── padding.py                    # Padding image generation + output naming
    ├── feature_depth.py              # Feature Depth Correction sub-routine
    └── processor.py                  # Orchestrator: file I/O, multiprocessing, naming

run_image_modification_standalone.py  # Standalone launcher (no Prince GUI required)
```

---

## Launching the Module

### From the Prince GUI
Click the **Image Modification** button in the main window. The module opens as a separate `Toplevel` window. Only one instance is allowed; reopening lifts the existing window.

### Standalone (testing / development)
```powershell
python run_image_modification_standalone.py
```
Status messages are printed to the console.

---

## GUI Reference

### Folder & Layer Selection

| Control | Description |
|---|---|
| **Folder** field | Full path to the folder containing the source `.png` images. Press `Enter` or click **Browse** to load. |
| **Layer** field | 1-based index of the image to display/preview. Press `Enter` or click **Load** to switch layers. |
| **(1-N)** label | Updates automatically to show how many source images are in the folder. |

Padding output files (`*_1.png`) are automatically excluded from the image list.

### Image Preview

The currently loaded image is displayed at up to **640×400 px**, downscaled proportionally. After clicking **Preview**, the processed version replaces the raw image in the preview area.

---

## Sub-Routines

### 1. Edge Enhancement

**Enable checkbox + Blur / Min / Max fields**

Replicates the MATLAB Gaussian edge enhancement, ported to Python with a float64 pipeline (no premature 0–1 scaling, so the Min/Max intensity clamps behave correctly).

**Algorithm:**
1. Apply Gaussian blur with sigma = `Blur`, kernel size = `2*(2*Blur)+1` (forced odd).
2. Subtract blurred image from original → isolates edges.
3. Normalize result to `[Min, Max]` over non-zero pixels.
4. Restore black background.

**Parameters:**

| Parameter | Default | Meaning |
|---|---|---|
| Blur | 25 | Gaussian sigma. Larger = more smoothing before subtraction, preserving lower spatial frequencies. |
| Min | 100 | Minimum output intensity for any non-zero pixel. Prevents features from disappearing. |
| Max | 255 | Maximum output intensity. |

---

### 2. Global Enhancement

**Enable checkbox + Globe ratio / Sigma + Asymmetric checkbox + Blend (°)**

Applies a radial vignette map that dims the center relative to the edges, compensating for projector light fall-off.

#### Symmetric Mode

A single circular Gaussian vignette is computed from the image dimensions. The minimum value (at center) is `Globe ratio` and the maximum (at edges) is `1.0`. Sigma controls how gradually the gradient falls off.

**Parameters:**

| Parameter | Default | Meaning |
|---|---|---|
| Globe ratio | 0.8 | Center intensity as a fraction of edge intensity. 0.8 = center is 80% of edge. |
| Sigma | 6.0 | Sigma divisor: `sigma_actual = max(rows,cols) / Sigma`. Larger value = tighter gradient. |

#### Asymmetric Mode

*Check "Asymmetric (4 quadrants, per-ray furthest white)"*

Designed for parts that are not centered or not circular. Instead of one fixed radius, the vignette gradient in each quadrant (NE, NW, SE, SW) is scaled to the distance of the **furthest white pixel** from the center in that quadrant. This means:
- All four quadrant gradients share the same `Globe ratio` minimum at the center.
- Each gradient reaches `1.0` at its own quadrant's furthest feature, not at a fixed radius.
- At quadrant boundaries, values are **smoothstep-blended** over the `Blend (°)` angular window so transitions are continuous.

**Parameters:**

| Parameter | Default | Meaning |
|---|---|---|
| Globe ratio | 0.8 | Center intensity (shared across all quadrants). |
| Blend (°) | 20 | Angular width of the blend zone at each 90° boundary. |

> **Note:** In asymmetric mode, the vignette map is rebuilt per image (since the furthest white pixel may vary layer to layer). In symmetric mode, one map is built for the whole folder.

---

### 3. Padding Normalization

**Checkbox: "Insert black padding after each image ({x}_1.png)"**

Inserts a fully black image after each source image in the output sequence. The padding image is generated programmatically (same resolution as the source) — no `New.png` file is required.

**Output naming:** If source image is `5.png`, the padding image is `5_1.png`. This convention makes it easy to copy only the padding images or only the source images from the output folder by filename pattern.

Padding normalization (intensity rescaling) only applies when both EE and GE are disabled.

---

### 4. Feature Depth Correction

**Enable checkbox + Strength / Channel decay (px) / Smooth (px)**

Compensates for overcuring of features deep inside a dense lattice, caused by resin pre-curing as it flows inward through the channels.

#### Physical Model

Resin starts in the outer bath (fresh, uncured). It flows through the black (open) channels of the lattice to reach the white (solid) features. As it travels past illuminated white pixels, scattered UV partially cures it. The further it has to travel, the more pre-cured it arrives — and the more overcured the target feature becomes relative to its nominal dose.

Features at the perimeter of the lattice receive fresh resin; features at the center receive pre-cured resin. The correction dims center features more than perimeter features.

#### Algorithm

1. **Classify black pixels** — Connected-component analysis separates black pixels into:
   - *Connected black*: pixels with a path to the image border (open channels)
   - *Enclosed black*: pixels with no path to the image border (sealed pores)

2. **Identify the outer resin pool** — Treat enclosed pores as white to get the true outer silhouette of the part. Dilate this silhouette by 1 pixel; the newly covered pixels that fall in connected-black are the **outer resin pool** — the first ring of fresh resin immediately outside the part perimeter. These have `channel_depth = 0`.

3. **Channel depth for connected-black pixels** — Euclidean distance from each connected-black pixel to the nearest outer-pool pixel. A channel 100 px deep has `channel_depth ≈ 100`.

4. **Channel depth for enclosed pores** — Since sealed pores have no path to the outer pool, their depth is estimated as: (distance through white to nearest connected-black channel) + (channel depth of that connected-black neighbor). This approximates how much white the resin "seeped" through to reach the sealed pore.

5. **Spread channel depth into white pixels** — Gaussian blur (`sigma = Channel decay / 2`) spreads the channel depth map from black pixels into the adjacent white struts. Each white pixel inherits the depth of its surrounding channels.

6. **Effective depth** — `effective_depth = dist_to_black + channel_spread`  
   Additive: how deep inside the strut + how deep the supplying channel is.  
   This is monotonically larger toward the center of a lattice.

7. **Normalise** — Scale to `[0, 1]` over all white pixels. Outliers are clipped at the 99th percentile so a single pathological enclosed pore doesn't compress the rest of the range.

8. **Apply correction** — Each white pixel is dimmed by `(1 - Strength × depth_norm)`. The deepest pixel (depth=1) is multiplied by `(1 - Strength)`; the shallowest (depth=0) is unchanged. A constant minimum intensity floor (100) prevents any white pixel from dropping below printable threshold.

**Parameters:**

| Parameter | Default | Meaning |
|---|---|---|
| Strength | 0.4 | Correction magnitude. 0 = no correction. 1 = deepest pixels dimmed to zero (use with care). |
| Channel decay (px) | 50 | Controls how far the channel depth influence spreads into adjacent white struts. Also the sigma used when blending depth into enclosed pore estimates. |
| Smooth (px) | 10 | Gaussian sigma for final depth map smoothing. Removes medial-axis ridge artifacts. |

> **Recommended usage:** Feature Depth Correction works best in combination with Edge Enhancement. EE handles fine optical blur at feature boundaries; FDC handles systematic overcuring at the macro scale (part center vs. perimeter).

---

## Output Folder Naming

All processed images are saved to a subfolder inside the source folder. The folder name encodes the active settings:

```
EE_{blur}_{Padded|NoPad}_GE_{globe}[_Asym][_FD_{strength}]
```

**Examples:**

| Settings | Output folder name |
|---|---|
| EE blur=25, no GE, no padding | `EE_25_NoPad_GE_0` |
| EE blur=25, GE globe=0.8, with padding | `EE_25_Padded_GE_0_8` |
| No EE, GE asymmetric globe=0.8 | `EE_0_NoPad_GE_0_8_Asym` |
| EE + FDC strength=0.4 | `EE_25_NoPad_GE_0_FD_0_4` |
| All four enabled, asymmetric | `EE_25_Padded_GE_0_8_Asym_FD_0_4` |

---

## Processing Pipeline Order

Routines are applied in this fixed order:

1. Edge Enhancement
2. Global Enhancement (symmetric or asymmetric)
3. Feature Depth Correction
4. Padding normalization (only when EE and GE are both off)

---

## Build vs. Preview

| Action | What it does |
|---|---|
| **Preview** | Applies all enabled routines to the currently displayed layer and shows the result in the preview window. Does not write any files. |
| **Build** | Processes every image in the folder using multiprocessing, writes output to the named subfolder, and shows a completion dialog. The GUI remains responsive during the build (runs in a background thread). |

---

## Dependencies

| Package | Use |
|---|---|
| `opencv-python` (`cv2`) | Image I/O, Gaussian blur, distance transform, connected components |
| `numpy` | Array operations |
| `Pillow` (`PIL`) | Tkinter image display (PhotoImage). If absent, preview is disabled. |
| `tkinter` | GUI (built into Python standard library) |

Install missing packages:
```powershell
pip install numpy opencv-python Pillow
```

---

## Known Considerations & Future Work

- **Feature Depth Correction — outer pool definition:** Currently uses a 1-pixel dilation of the filled part silhouette to define the fresh-resin boundary. An alternative approach (bounding-box outer pool) was explored and may be revisited: this would define the outer pool as all connected-black pixels outside the axis-aligned bounding box of the part, which naturally penalises small channels that penetrate into the lattice without threshold tuning.

- **Asymmetric GE — quadrant count:** Currently hardcoded to 4 quadrants (NE, NW, SE, SW). A finer ray-based approach (more rays, e.g. 8 or 16) could give better correction for highly irregular part shapes.

- **Feature Depth Correction — channel width:** The current model does not weight by channel cross-section. A narrow 2-px channel penetrating 100 px into the part gets the same `channel_depth` as a wide 50-px channel of the same length, even though the wide channel can supply far more resin. A potential improvement is to weight `channel_depth` by local channel width (e.g., via the distance transform of the connected-black region itself).
