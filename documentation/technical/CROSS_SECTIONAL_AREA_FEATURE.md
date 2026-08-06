# Cross-Sectional Area Feature

## Overview
Added automatic cross-sectional area calculation and logging to the work of adhesion metrics. The system now counts white pixels in each layer's PNG image and calculates the actual cross-sectional area based on hardware-specific pixel dimensions.

## Implementation Date
November 11, 2025

## Hardware Specifications
- **Pixel Size**: 0.004005 mm × 0.004005 mm (square pixels)
- **Pixel Area**: 0.00001604 mm² per pixel
- **Location**: Hardcoded in `PeakForceLogger.py` as class constants

## Changes Made

### 1. PeakForceLogger.py
**Additions:**
- `PIXEL_SIZE_MM = 0.004005` - Hardware-specific pixel dimension
- `PIXEL_AREA_MM2 = PIXEL_SIZE_MM ** 2` - Area of one pixel
- `current_cross_sectional_area_mm2` - Instance variable to track area per layer
- `_calculate_cross_sectional_area(image_path)` - Method to count white pixels and calculate area

**Method Updates:**
- `__init__()` - Added cross-sectional area tracking variable
- `_ensure_header()` - Added `Cross_Sectional_Area_mm2` column to CSV header
- `start_monitoring_for_layer()` - Now accepts optional `image_path` parameter
- `stop_monitoring_and_log_peak()` - Passes cross-sectional area to analysis worker
- `_analysis_worker()` - Extracts and passes area to analysis methods
- `_analyze_with_corrected_calculator()` - Updated signature to accept area
- `_analyze_with_original_method()` - Updated signature to accept area
- `_write_corrected_csv_entry()` - Writes area to CSV
- `_write_original_csv_entry()` - Writes area to CSV

### 2. SensorDataWindow.py
**Method Updates:**
- `update_auto_logger_current_layer()` - Now accepts optional `image_path` parameter
- Updated call to `start_monitoring_for_layer()` to pass `image_path`

### 3. Prince_Segmented.py
**Updates:**
- Modified call to `update_auto_logger_current_layer()` to pass `image_path`
- Gets `current_image_path = self.image_list[i]` for each layer

## How It Works

### Data Flow:
1. **Prince_Segmented.py** loops through layers and has access to `self.image_list[i]`
2. Calls `sensor_data_window_instance.update_auto_logger_current_layer(layer, z_pos, image_path)`
3. **SensorDataWindow.py** receives the image path and passes it to `automated_peak_force_logger.start_monitoring_for_layer()`
4. **PeakForceLogger.py** receives image path and calls `_calculate_cross_sectional_area()`
5. Reads PNG using OpenCV, counts pixels with value ≥250 (white pixels)
6. Calculates area: `white_pixel_count × PIXEL_AREA_MM2`
7. Stores area in `self.current_cross_sectional_area_mm2`
8. When analysis completes, area is written to CSV along with other metrics

### White Pixel Detection:
```python
img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
white_pixel_count = np.sum(img >= 250)  # Threshold at 250 for robustness
area_mm2 = white_pixel_count * PIXEL_AREA_MM2
```

## CSV Output Format
The adhesion metrics CSV now includes:
```
Layer_Number, Peak_Force_N, Work_of_Adhesion_mJ, ..., Cross_Sectional_Area_mm2
1, 0.2345, 12.4567, ..., 45.6789
2, 0.2456, 13.5678, ..., 47.8901
```

## Example Calculation
- **Image**: 1000 white pixels
- **Pixel Area**: 0.00005786 mm²
- **Cross-Sectional Area**: 1000 × 0.00005786 = **0.05786 mm²**

For a typical print with 10,000 white pixels:
- **Cross-Sectional Area**: 10,000 × 0.00005786 = **0.5786 mm²**

## Benefits
1. **Automatic**: No manual measurement needed
2. **Accurate**: Based on actual projected pixels, not CAD geometry
3. **Per-Layer**: Handles varying cross-sections (cones, complex shapes)
4. **Integrated**: Saved with all other adhesion metrics
5. **Post-Processing**: Enables stress/adhesion normalization by area

## Usage in Analysis
The cross-sectional area can be used to calculate:
- **Stress**: `Peak_Force_N / Cross_Sectional_Area_mm2` (MPa)
- **Adhesion Energy Density**: `Work_of_Adhesion_mJ / Cross_Sectional_Area_mm2` (J/m²)
- **Normalized Metrics**: Compare different layer sizes fairly

## Future Enhancements (Optional)
- Add area change rate tracking (expansion/contraction between layers)
- Calculate perimeter from image for edge effect analysis
- Add shape metrics (circularity, aspect ratio)
- Support for multi-material prints (different pixel value ranges)

## Notes
- Area calculation only occurs if `image_path` is provided (backwards compatible)
- Missing images result in `NaN` for cross-sectional area
- Pixel size is hardcoded - update `PIXEL_SIZE_MM` in `PeakForceLogger.py` if hardware changes
- White pixel threshold (250) can be adjusted if needed for different image formats

## Testing Recommendation
1. Run a test print with adhesion logging enabled
2. Check CSV output for `Cross_Sectional_Area_mm2` column
3. Verify terminal messages: "Image area calculation - White pixels: X, Area: Y mm²"
4. Compare calculated area to expected values (CAD geometry × pixel_area)
