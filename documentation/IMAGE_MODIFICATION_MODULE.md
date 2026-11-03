# Image Modification Module

**Authors:** Professor Cheng Sun, Evan Jones
**Location:** `support_modules/ImageModificationWindow.py` and `support_modules/image_modification/`

---

## Overview

The Image Modification module is a GUI tool integrated into the main Prince printer application. It pre-processes SLA/DLP projection images before printing to compensate for known optical and resin-flow artifacts. It can also be run as a standalone window for quick testing without launching the full printer GUI.

### Problem Being Solved

DLP/SLA resin printers cure each layer by projecting a grayscale bitmap. Several physical effects distort the actual dose received at each point:

1. **Optical blur** — UV light scatters slightly, causing features to receive dose from neighboring illuminated regions. Edge pixels are most affected; inner pixels less so. This is corrected by **Edge Enhancement**.

2. **Radial intensity fall-off** — The projector's light path is not perfectly uniform; the center is typically dimmer than the edges. For symmetrical parts this is corrected by **Global Enhancement (Symmetric)**; for asymmetric parts, **Global Enhancement (Asymmetric)** adapts the gradient by angular sector so irregular, non-circular shapes can be corrected more locally.

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

### Utility Helpers

The Image Modification window now includes two utility helpers in addition to EE/GE/FDC/SC:

1. **Cone Generator**
2. **Instruction Ramping**

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

**Enable checkbox + Globe ratio / Sigma + Asymmetric checkbox + Slice (°) / Smooth (sectors) / Blend (°)**

Applies a radial vignette map that dims the center relative to the edges, compensating for projector light fall-off.

#### Symmetric Mode

A single circular Gaussian vignette is computed from the image dimensions. The minimum value (at center) is `Globe ratio` and the maximum (at edges) is `1.0`. Sigma controls how gradually the gradient falls off.

**Parameters:**

| Parameter | Default | Meaning |
|---|---|---|
| Globe ratio | 0.8 | Center intensity as a fraction of edge intensity. 0.8 = center is 80% of edge. |
| Sigma | 6.0 | Sigma divisor: `sigma_actual = max(rows,cols) / Sigma`. Larger value = tighter gradient. |

#### Asymmetric Mode

*Check "Asymmetric (angular sectors, per-ray furthest white)"*

Designed for parts that are not centered or not circular. Instead of one fixed radius, the vignette gradient is computed per angular sector, where each sector's radius is scaled to the distance of the **furthest white pixel** from the center in that sector. This means:
- All sectors share the same `Globe ratio` minimum at the center.
- Each sector reaches `1.0` at its own furthest feature, not at a fixed radius.
- `Slice (°)` controls the angular width of each sector. Smaller values give finer shape adaptation.
- `Smooth (sectors)` circularly smooths the per-sector radius profile before applying the map, which helps stabilize noisy or sparse geometries.
- At sector boundaries, values are crossfaded over the `Blend (°)` angular window so transitions are continuous.

**Parameters:**

| Parameter | Default | Meaning |
|---|---|---|
| Globe ratio | 0.8 | Center intensity (shared across all sectors). |
| Slice (°) | 90 | Angular width of each sector. 90° matches the legacy 4-quadrant behavior; 10° is a good starting point for irregular parts. |
| Smooth (sectors) | 0 | Circular moving-average radius, measured in sector counts. 0 means no extra smoothing. |
| Blend (°) | 20 | Angular width of the crossfade zone at each sector boundary. |

> **Note:** In asymmetric mode, the vignette map is rebuilt per image (since the furthest white pixel may vary layer to layer). In symmetric mode, one map is built for the whole folder.

---

### 3. Padding Normalization

**Checkbox: "Insert black padding after each image ({x}_1.png)"**

Inserts a fully black image after each source image in the output sequence. The padding image is generated programmatically (same resolution as the source) — no `New.png` file is required.

**Output naming:** If source image is `5.png`, the padding image is `5_1.png`. This convention makes it easy to copy only the padding images or only the source images from the output folder by filename pattern.

Padding normalization (intensity rescaling) only applies when both EE and GE are disabled.

---

### 4. Robust Feature Depth Correction

**Enable checkbox + Mode (Distance / Pressure) + Strength / Decay / Smooth / Conductivity / Sink**

Compensates for macro-scale overcuring of features deep inside dense lattices, porous networks, and microfluidic channels caused by resin pre-curing and resin flow starvation.

#### Physical Motivation
In dense lattice networks, resin must migrate inward from the external resin pool through narrow channels. As UV light cures adjacent white features, laterally scattered photons partially polymerize the resin in the channels. When this pre-cured resin reaches interior features, it requires less dose to solidify, leading to severe overcuring and channel clogging.

#### Modes of Operation

##### Mode A: Distance / Channel Flow (Geometric Diffusion)
1. **Black Pixel Classification:** Connected components separate open exterior channels from enclosed, trapped pores.
2. **Perimeter Outer Pool Identification:** Dilation of the solid silhouette identifies the true outer resin pool at the boundary (`channel_depth = 0`).
3. **Channel Depth Propagation:** Computes Euclidean distance through connected channels. Sealed pores compute distance through solid walls plus nearest channel depth.
4. **Normalized Convolution:** Spreads channel depth into solid struts using normalized convolution (`GaussianBlur(depth * mask) / GaussianBlur(mask)`), computing the exact local weighted average of feeding channels without boundary dilution.
5. **Effective Depth:** `effective_depth = dist_to_black + channel_spread`.
6. **Saturating Physical Scale Normalization:** Normalizes depth using a saturating exponential $1 - \exp(-\text{depth} / D_{\text{char}})$ with characteristic scale $D_{\text{char}} = 2 \times \sigma_{\text{decay}}$. This avoids artificially over-dimming isolated or small parts.

##### Mode B: Pressure / Porous Media (Poisson Flow Solver)
1. **Resin Starvation Physics:** Formulates resin replenishment as steady-state Darcy flow through a porous medium: $\nabla \cdot (K \nabla P) = S$, where $K$ is the channel conductivity ratio and $S$ is the consumption rate at curing pixels.
2. **Coarse-Grid Acceleration:** Solves the 2D Poisson equation with Successive Over-Relaxation (SOR) on an automatically downsampled $2\times$ or $4\times$ grid for sub-second convergence on $1600\times 2560$ images, followed by smooth bilinear interpolation.
3. **Dirichlet Boundaries:** Anchors pressure to zero at the outer pool and image borders.
4. **Physical Pressure Normalization:** Normalizes using saturating scale $1 - \exp(-P / P_{\text{char}})$.

**Parameters:**

| Parameter | Default | Mode | Meaning |
|---|---|---|---|
| Mode | Distance | Both | Choice of geometric distance propagation vs. physical pressure Poisson solver. |
| Strength | 0.4 | Both | Maximum dimming factor applied to the deepest features ($1 - \text{strength} \times \text{depth}$). |
| Decay (px) | 50.0 | Distance | Characteristic spatial reach of fresh resin replenishment into channels. |
| Smooth (px) | 10.0 | Distance | Gaussian smoothing sigma removing medial-axis ridge artifacts. |
| Conductivity | 100.0 | Pressure | Permeability ratio $K$ of open channels relative to solid struts. |
| Sink | 0.1 | Pressure | Resin consumption rate / sink magnitude at each solid pixel. |

---

### 5. 3D Axial Z Compensation (3D Voxel Energy Model)

**Enable checkbox + Layer Thickness ($h$) / Penetration Depth ($D_p$) / Critical Energy ($E_c$) / Exposure Ratio ($E_0/E_c$)**

Corrects axial print-through and downward overhang overcuring across the Z stack:
- **Lookahead Backward Pass:** Models light penetration using Beer-Lambert attenuation $a = \exp(-h / D_p)$.
- **Single 2D Carry Array:** Streams backward from the top layer to the bottom layer, accumulating penetrating irradiance and computing ideal exposure times $E_k = \text{clip}(E_{\text{target}} - \text{carry}, 0, E_{\text{nominal}})$.
- **Downward Overhang Detection:** Automatically identifies downward-facing overhang teeth and adjusts local exposure to prevent axial overcure.

---

### 6. Pipeline Execution Order (Interactive Stage Reordering)

The Image Modification window provides an interactive listbox allowing operators to customize the order of pipeline stages:
- **Default Order:** `3D Axial` $\rightarrow$ `Edge Enhancement` $\rightarrow$ `Global Enhancement` $\rightarrow$ `Feature Depth` $\rightarrow$ `Scattering Compensation`.
- Configurable via **Move Up**, **Move Down**, and **Reset to Default** buttons.
- Preserves 3D consistency by running 3D axial lookahead before or after 2D slice modifications as desired.
- Encoded directly in output folder tags (`_Ord-...`).

---

### 5. Cone Generator

Creates a brand-new image stack (does not process existing layers) for an expanding cone profile.

**Inputs:**
- Initial radius (µm)
- Ending radius (µm)
- Height (µm)
- Layer height (µm)
- Output base folder

**Behavior:**
- Number of layers is `ceil(height / layer_height)`.
- Radius is linearly interpolated from initial to ending radius over the generated layers.
- Output files are sequentially numbered: `1.png`, `2.png`, ..., `N.png`.
- Output folder is auto-named with the cone parameters and created under the selected base folder.
- Current implementation uses a direct micron-to-pixel mapping (`1 µm == 1 px`).

---

### 6. Instruction Ramping

Builds a new instruction folder from an existing instruction file and image set by ramping exposure time between user-defined control layers.

**Inputs:**
- Source instruction file (`.txt`, standard 10-column tab-delimited format)
- Ramp mode: **Linear** or **Exponential**
- Power at the first control layer
- Control layers entered as one per line: `layer_number, exposure_seconds`

**Behavior:**
- Control layers must be strictly increasing and within the instruction layer count.
- Exposure schedule rules:
   - Layers before the first control layer use the first control-layer exposure.
   - Layers between adjacent control layers are interpolated (linear or exponential).
   - Layers after the last control layer are clamped to the last control-layer exposure.
- Power is recomputed per layer to maintain constant dosage anchored at the first control layer:
   - `dose_anchor = first_control_power × first_control_exposure`
   - `power[layer] = dose_anchor / exposure[layer]` (clipped to `[0, 255]`)
- A new output folder is created (`<source_folder>_ramped_<mode>`), source images are copied into it, and a new instruction file is written as `<output_folder_name>.txt`.

---

## Output Folder Naming

All processed images are saved to a subfolder inside the source folder. The folder name encodes the active settings:

```
EE_{blur}_{Padded|NoPad}_GE_{globe}[_Asym...][_FD_{strength}[_Pres]][_SC][_ZA_LT{h}_DP{dp}_ER{er}][_Ord-{stages}]
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

- **Asymmetric GE — sector tuning:** The angular-sector implementation is now configurable. Smaller `Slice (°)` values give finer local adaptation, while `Smooth (sectors)` can suppress noisy radius estimates on sparse or jagged shapes.

- **Feature Depth Correction — channel width:** The current model does not weight by channel cross-section. A narrow 2-px channel penetrating 100 px into the part gets the same `channel_depth` as a wide 50-px channel of the same length, even though the wide channel can supply far more resin. A potential improvement is to weight `channel_depth` by local channel width (e.g., via the distance transform of the connected-black region itself).
