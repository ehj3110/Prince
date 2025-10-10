# Speed Analysis Plot - Documentation

## Overview
The speed analysis plot automatically generates a 4-subplot figure showing how adhesion metrics vary with peel speed.

## Features

### Data Processing
- **Automatic averaging**: For each unique speed value, all layer measurements are averaged together
  - Example: If 5 layers were tested at 1000 µm/s, the plot shows the mean of those 5 layers
  - Standard deviation is also calculated (can be used for error bars in future versions)

### Visualization Design
- **Consistent color scheme across all plots**:
  - Peak Force: Blue (#2E86AB)
  - Work of Adhesion: Purple (#A23B72)
  - Peel Distance: Orange (#F18F01)
  - Peak Retraction Force: Red (#C73E1D)

- **Three-layer visualization**:
  1. **Individual points** (90% transparent): Shows all raw layer measurements
  2. **Mean values** (60% transparent): Shows averaged values for each speed with black outline
  3. **Smooth trend line**: Cubic spline interpolation through mean values

### Smooth Line Generation
- Uses `scipy.interpolate.make_interp_spline` for smooth curves
- Automatically handles edge cases:
  - Less than 3 points: Falls back to linear interpolation
  - Single speed (constant tests): Shows single point with no trend line
  - Multiple speeds (ramped tests): Beautiful smooth curve through averaged data

## Generated Plots

### 1. Peak Force vs. Speed
Shows how maximum adhesive force changes with peel speed.

### 2. Work of Adhesion vs. Speed
Displays energy required for complete debonding as a function of speed.

### 3. Total Peel Distance vs. Speed
Shows the total distance traveled during the peel event (initiation + propagation).

### 4. Peak Retraction Force vs. Speed
Displays maximum retraction force (absolute value) during stage return.

## Usage

### Generate plot for single folder:
```powershell
cd post-processing
python plot_speed_analysis.py "C:\Path\to\autolog_metrics.csv"
```

### Automatic generation during batch processing:
```powershell
python analyze_single_folder.py "C:\Path\to\TestFolder"
```

The plot is automatically saved as `speed_analysis.png` in the same folder as `autolog_metrics.csv`.

## Output Files

Each analyzed folder will contain:
- `autolog_metrics.csv` - Combined metrics for all layers
- `speed_analysis.png` - 4-subplot speed analysis figure
- Individual layer plots (e.g., `Water_1mm_Ramped_L50-L54.png`)

## Example Results

### Constant Speed Test (Water_1mm_Constant_BPAGDA)
- 1 unique speed value
- Shows mean ± variation across all layers at that speed
- Individual points visible as cloud around mean

### Ramped Speed Test (2p5PEO_1mm_Ramped_BPAGDA_Old)
- 22 unique speed values
- Smooth curves showing trends across speed range
- Individual layer scatter shows measurement variability
- Can clearly identify speed-dependent behavior

## Technical Details

### Speed Conversion
- Input CSV uses `Speed_um_s` (µm/s from instruction file)
- Automatically converted to mm/min for plotting: `speed_mm_min = Speed_um_s / 1000 * 60`

### Averaging Logic
```python
# For each unique speed, calculate:
mean_value = average(all_layers_at_this_speed)
std_value = std_dev(all_layers_at_this_speed)
```

### Spline Interpolation
- Creates 300 interpolated points for smooth curves
- Cubic spline (k=3) for datasets with ≥4 unique speeds
- Linear interpolation fallback for smaller datasets

## Future Enhancements (Optional)

Potential additions:
- Error bars showing ± 1 standard deviation
- R² values for correlation strength
- Logarithmic scale option for speed axis
- Export statistics to separate CSV
- Overlay multiple test conditions on same plot

## Version History

### v1.0 (Oct 2, 2025)
- Initial implementation with mean averaging
- Consistent color scheme across plots
- Smooth cubic spline interpolation
- 90% transparent individual points
- Automatic integration with batch processing
