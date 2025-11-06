# V3 Data Processing Summary

**Date:** October 27, 2025  
**Script:** `batch_process_v3.py`

## Overview

Created a new batch processing script specifically for the V3 folder to analyze SteppedCone adhesion data, including the new ACF (Anisotropic Conductive Film) condition.

## Data Structure - V3 Folder

**Location:** `C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V3`

### Folders Processed:
1. **2p5PEO_1mm_SteppedCone_BPAGDA_1000** (10 autolog files)
2. **ACF_5mm_SteppedCone_BPAGDA_200** (10 autolog files) ⭐ *NEW*
3. **TEMPOV2_1mm_SteppedCone__BPAGDA_1000**
4. **Water_1mm_SteppedCone_BPAGDA_1000**

### ACF Data Characteristics:
- **Speed:** 200 µm/s (much slower than typical 1000-6000 µm/s)
- **Gap:** 5mm (vs typical 1mm)
- **Sampling Rate:** ~15-17 ms per sample (~60-70 Hz) vs typical ~1 ms
- **Missing Information:** 
  - No instructions file saved with data (old code version)
  - Pause duration unknown
  - Overstep distance unknown

## Processing Workflow

The `batch_process_v3.py` script follows the same approach as the V2 processing (`batch_process_steppedcone.py`):

### 1. **Area Mapping**
- Loads `LayerToArea.txt` file (440 layers total)
- Maps layer numbers to contact areas (9.90 - 99.72 mm²)

### 2. **Individual Layer Processing**
- Uses `RawData_Processor` to detect ~6mm adhesion cycles
- Uses `AdhesionMetricsCalculator` to calculate adhesion metrics
- Generates individual analysis plots showing ALL layers

### 3. **Metrics Extracted Per Layer**
- Peak Force (N)
- Work of Adhesion (mJ)
- Peel Distance (mm)
- Peak Retraction Force (N)
- Distance to Peak (mm)
- Propagation Distance (mm)
- Effective Stiffness (N/mm)

### 4. **Master CSV Generation**
- `MASTER_steppedcone_metrics.csv` - Contains all layer metrics with columns:
  - folder_name
  - layer_number
  - condition_label
  - fluid_type
  - gap_mm
  - speed_um_s
  - area_mm2
  - All metrics listed above

### 5. **Master Plot Generation**
Creates three master plots with area-based analysis:

#### a) `MASTER_area_analysis.png` (4 subplots):
- Peak Force vs Area
- Work of Adhesion vs Area
- Peel Distance vs Area
- Peak Retraction Force vs Area

#### b) `MASTER_area_distance_analysis.png` (2 subplots):
- Distance to Peak vs Area
- Propagation Distance vs Area

#### c) `MASTER_stiffness_analysis.png` (1 subplot):
- Effective Stiffness vs Area

**Plot Features:**
- Colored bands (SEM shading) for each condition
- Polynomial trendlines (degree 2)
- Data points shown as markers
- All formatted consistently with V2 plots

## Expected Output Files

### In V3 Directory:
- `MASTER_steppedcone_metrics.csv` - All metrics for all layers
- `MASTER_area_analysis.png` - 4-subplot master plot
- `MASTER_area_distance_analysis.png` - 2-subplot master plot
- `MASTER_stiffness_analysis.png` - 1-subplot master plot

### In Each Folder (e.g., ACF_5mm_SteppedCone_BPAGDA_200/plots/):
- `autolog_L60-L65_analysis.png`
- `autolog_L100-L105_analysis.png`
- `autolog_L140-L145_analysis.png`
- ... etc for all layer ranges

## Script Details

**Script Path:** `c:\Users\ehunt\OneDrive\Documents\Prince\Prince_Segmented_20250926\batch_process_v3.py`

**Key Features:**
1. Identical processing logic to V2 batch processor
2. Configured for V3 directory path
3. Handles variable speeds (200 - 1000 µm/s)
4. Handles variable gaps (1mm, 5mm)
5. Automatically parses folder names to extract:
   - Fluid type (2p5PEO, ACF, TEMPOV2, Water)
   - Gap (1mm or 5mm)
   - Speed (if present in folder name)

**Processing Status:**
Currently running in background. Check `v3_processing_log.txt` for real-time progress.

## Comparison with V2 Processing

| Aspect | V2 | V3 |
|--------|----|----|
| Script | `batch_process_steppedcone.py` | `batch_process_v3.py` |
| Total Folders | 6 | 4 |
| Total Layers | 353 | TBD |
| Speed Range | 1000-6000 µm/s | 200-1000 µm/s |
| Gap | 1mm | 1mm & 5mm |
| New Fluids | TEMPO, TEMPOV2 | ACF |
| Sampling Rate | ~1 ms | ~1-17 ms (varies) |

## Notes

1. **ACF Data:** The slower sampling rate and different speed/gap parameters are handled automatically by the existing processing pipeline.

2. **Missing Instructions:** The lack of an instructions file doesn't affect processing since we detect adhesion cycles based on the ~6mm motion detection algorithm.

3. **Consistency:** All plots and metrics are generated in the exact same style as V2 to maintain consistency across datasets.

4. **Area Mapping:** The same `LayerToArea.txt` file is used for both V2 and V3, ensuring consistent area assignments.

## Next Steps

Once processing completes:
1. Check `v3_processing_log.txt` for any errors
2. Review master plots in V3 directory
3. Examine `MASTER_steppedcone_metrics.csv` for data quality
4. Compare ACF results with other fluids
5. Investigate any unusual patterns in ACF data (200 µm/s vs 1000+ µm/s)

## Troubleshooting

If processing fails or produces unexpected results:
- Check log file: `v3_processing_log.txt`
- Verify LayerToArea.txt is present and properly formatted
- Ensure all autolog CSV files have standard format (Elapsed Time, Position, Force)
- Confirm ~6mm adhesion cycles are detected properly (see log output)

---

**Processing initiated:** October 27, 2025  
**Expected completion:** ~10-20 minutes depending on system performance
