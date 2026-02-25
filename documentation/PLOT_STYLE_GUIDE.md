# Plot Style Guide
**Version 2.0 - Updated January 15, 2026**

This document defines the standardized styling for all adhesion test analysis plots.

---

## General Settings

### Font Family
- **All text**: Times New Roman
- Set via: `plt.rcParams['font.family'] = 'Times New Roman'`

### Figure Size & DPI
- **Default figure size**: 16" × 12" (width × height)
- **DPI**: 100 (standard), 300 (for publication-quality exports)
- **Dynamic height**: Adjusts based on number of subplot rows

### Color Scheme
- **Layer colors**: Assigned from palette `['red', 'blue', 'green', 'orange', 'purple', 'brown']`
- **Raw force**: Black with 40% transparency (`'k-', alpha=0.4`)
- **Smoothed force**: Uses assigned layer color
- **Pre-initiation phase**: Light blue shading (`alpha=0.3`)
- **Propagation phase**: Light coral shading (`alpha=0.3`)
- **Baseline**: Gray dashed line (`'gray', linestyle='--', alpha=0.6`)
- **Propagation end marker**: Purple dotted line (`'purple', linestyle=':'`)

---

## Title Formatting

### Main Figure Title
- **Font size**: 24 points (base), scales down for multi-row plots
  - 2 rows or less: 24 pt
  - 3 rows: 22 pt
  - 4+ rows: 20 pt
- **Font weight**: Bold
- **Format**: `[Membrane]_[Gap]_[Tank]_[Fluid]_[Speed] - Layers X -> Y\nAverage Area: Z mm²`
  - Example: `FEP_500um_V19_Air_400 - Layers 101 -> 105\nAverage Area: 32.54 mm²`
- **Position**: Top of figure (`y=0.98`)
- **Note**: Layer range is specific to each autolog file, NOT the entire batch

### Complete Force Profile Title
- **Font size**: `font_size + 6` (typically ~20 pt)
- **Font weight**: Bold
- **Text**: "Complete Force Profile"

### Individual Layer Subplot Titles
- **Font size**: `font_size + 2` (typically ~16 pt)
- **Font weight**: Bold
- **Color**: Black
- **Format**: `Layer [number] - Pre-init: [X.XX]s | Prop: [Y.YY]s`
  - Example: `Layer 101 - Pre-init: 4.32s | Prop: 0.58s`

---

## Axes Formatting

### Axis Labels
- **Font size**: `font_size + 4` (typically ~18 pt)
- **Font weight**: Bold
- **X-axis**: "Time (s)"
- **Y-axis**: "Force (N)"

### Axis Tick Labels
- **Font size**: `font_size + 4` (typically ~18 pt)
- **Number of ticks**: Reduced to ~6 bins per axis (`ax.locator_params(axis='both', nbins=6)`)
- **Purpose**: Cleaner appearance, easier to read

### Grid
- **Style**: Enabled on all plots
- **Alpha**: 0.3 (subtle)

---

## Legend Formatting

### Complete Force Profile Legend
- **Font size**: `font_size - 1` (typically ~13 pt)
- **Location**: Lower right (`loc='lower right'`)
- **Frame alpha**: 0.9
- **Entries**:
  - Raw Force
  - Smoothed Force
  - (Layer markers shown with colors)

### Individual Layer Subplot Legends
- **Font size**: `font_size - 2` (typically ~12 pt)
- **Location**: Upper left (`loc='upper left'`)
- **Frame alpha**: 0.9
- **Columns**: 2 (`ncol=2`)
- **Entries**:
  - Raw Force
  - Smoothed Force
  - Pre-Initiation (shaded region)
  - Propagation (shaded region)
  - Peak Force (dashed line)
  - Prop End (dotted line)
  - Baseline (with force value)

---

## Annotations

### Peak Force Annotation (Individual Layers)
- **Font size**: `font_size` (typically ~14 pt)
- **Font weight**: Bold
- **Color**: Matches layer color (red, blue, green, etc.)
- **Position**: 15% to the right of peak time, centered vertically on peak force value
  - `x = peak_time + (prop_end_time - pre_init_time) * 0.15`
  - `y = peak_force`
  - `ha='left', va='center'`
- **Content**: Relative force (peak - baseline) in Newtons
  - Format: `"X.XXXXN"` (4 decimal places)
- **Box style**:
  - Shape: Round with 0.3 padding (`boxstyle='round,pad=0.3'`)
  - Background: White (`facecolor='white'`)
  - Border: Matches layer color (`edgecolor=color`)
  - Alpha: 0.9

### Layer Number Annotations (Complete Force Profile)
- **Font size**: `font_size + 2` (typically ~16 pt)
- **Font weight**: Bold
- **Color**: Matches layer color
- **Position**: Slightly above peak marker (5 points offset)
- **Format**: `"L[number]"` (e.g., "L101")

---

## Markers and Lines

### Peak Force Marker
- **Style**: Circle (`'o'`)
- **Size**: 12 points
- **Color**: Layer color
- **Edge**: Black, 2pt width
- **Z-order**: 5 (on top)

### Peak Force Vertical Line
- **Style**: Dashed (`'--'`)
- **Width**: 3 points
- **Color**: Layer color
- **Alpha**: 0.8
- **Z-order**: 4

### Propagation End Marker
- **Style**: Square (`'s'`)
- **Size**: 9 points
- **Color**: Purple
- **Edge**: Black, 1.5pt width
- **Z-order**: 5

### Propagation End Vertical Line
- **Style**: Dotted (`':'`)
- **Width**: 3 points
- **Color**: Purple
- **Alpha**: 0.8
- **Z-order**: 4

### Baseline Horizontal Line
- **Style**: Dashed (`'--'`)
- **Width**: 2 points
- **Color**: Gray
- **Alpha**: 0.6
- **Z-order**: 2

---

## Plot Windows and Margins

### Complete Force Profile
- **X-axis**: Shows all detected layers with 5% margin on each side
- **Y-axis**: 0 to max peak force × 1.1

### Individual Layer Subplots
- **X-axis**: Pre-initiation start - 1 second buffer to propagation end + 1 second buffer
  - Buffer allows visualization of stage transitions
- **Y-axis**: Baseline - 20% force range to peak + 20% force range
  - Ensures all features are visible with adequate margins

---

## Subplot Layout

### Grid Structure
- **Arrangement**: 2 columns, variable rows
- **Row calculation**: `(total_plots + 1) // 2`
  - Total plots = 1 (Complete Force Profile) + number of layers
- **First subplot**: Complete Force Profile (top-left)
- **Remaining subplots**: Individual layers in reading order

### Spacing
- **Top margin**: 0.90 (leaves room for main title)
- **Bottom margin**: 0.08
- **Horizontal spacing**: 0.3
- **Vertical spacing**: 0.4

---

## File Organization

### Output Structure
```
[Condition_Folder]/
└── plots/
    └── [YYYYMMDD_HHMMSS]/          # Timestamped subfolder for version control
        ├── autolog_L[X]-L[Y]_analysis.png
        ├── autolog_L[X]-L[Y]_analysis.png
        └── ...
```

### Naming Convention
- **Format**: `autolog_L[start]-L[end]_analysis.png`
- **Example**: `autolog_L101-L105_analysis.png`
- **Timestamp folders**: `YYYYMMDD_HHMMSS` (e.g., `20260115_141016`)

---

## Implementation Notes

### Key Code References

#### Font Configuration
```python
plt.rcParams['font.family'] = 'Times New Roman'
plt.rcParams['font.size'] = 12
```

#### Title Sizing Logic
```python
base_title_size, base_label_size = (24, 14)
if rows_needed <= 2: title_size, label_size = base_title_size, base_label_size
elif rows_needed <= 3: title_size, label_size = base_title_size - 2, base_label_size - 1
else: title_size, label_size = base_title_size - 4, base_label_size - 2
```

#### Peak Annotation Positioning
```python
x_range = layer['prop_end_time'] - layer['pre_init_time']
annotation_x = layer['peak_time'] + x_range * 0.15
ax.text(annotation_x, layer['peak_force'], 
        f"{relative_force:.4f}N",
        ha='left', va='center', fontsize=font_size, fontweight='bold', 
        color=color, bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                               edgecolor=color, alpha=0.9))
```

#### Axis Tick Reduction
```python
ax.tick_params(axis='both', which='major', labelsize=font_size + 4)
ax.locator_params(axis='both', nbins=6)  # Reduce to ~6 ticks per axis
```

---

## Version History

### Version 2.0 (January 15, 2026)
- **Major updates**: Complete style overhaul
- Changed all fonts to Times New Roman
- Increased main title size to 24pt
- Reduced subplot title size to font_size + 2
- Increased axis tick labels to font_size + 4
- Reduced legend sizes (font_size - 1 for overview, font_size - 2 for subplots)
- Moved peak annotation to right side (15% offset from peak time)
- Restored color-coded peak annotations matching layer colors
- Reduced number of axis ticks to ~6 per axis for cleaner appearance
- Added timestamped subfolders for version control
- Fixed title format to show per-file layer ranges instead of batch-wide ranges

### Version 1.0 (Previous)
- Initial style guide with basic formatting
- Original peak annotation above peak
- Different font sizes and color schemes

---

## Quick Reference

| Element | Size | Weight | Color | Position |
|---------|------|--------|-------|----------|
| Main Title | 24pt | Bold | Black | Top (y=0.98) |
| Subplot Title | 16pt | Bold | Black | Top of subplot |
| Axis Labels | 18pt | Bold | Black | Standard |
| Axis Ticks | 18pt | Regular | Black | ~6 per axis |
| Legend (Overview) | 13pt | Regular | Black | Lower Right |
| Legend (Subplot) | 12pt | Regular | Black | Upper Left |
| Peak Annotation | 14pt | Bold | Layer Color | Right of peak (15% offset) |
| Layer Label | 16pt | Bold | Layer Color | Above peak marker |

---

**Maintained by**: Cheng Sun Lab Analysis Team  
**Last Updated**: January 15, 2026  
**Applies to**: analysis_plotter.py v2.0+
