# Universal Batch Processing System

## The Problem We Solved

**STOP creating new batch processors for each folder version!**

Previously, we had separate scripts for V4, V5, V6, etc., requiring manual reformatting of plots each time. This was tedious and error-prone.

## The Solution: One Script for Everything

`process_folder.py` - A single universal processor that handles **ANY** version of test data.

## Usage

### Process Any Folder Version

```bash
# Process V6 data
python process_folder.py V6

# Process V5 data
python process_folder.py V5

# Process any custom folder
python process_folder.py "C:\path\to\any\folder"
```

That's it! No more custom scripts. No more reformatting plots.

## What It Does Automatically

1. **Auto-detects folder structure**
   - Recognizes membrane types (PDMS, ACF, TEMPO, Flat PDMS, etc.)
   - Identifies tank types (V19, V22, V22p1, V22p2, V22p3, etc.)
   - Detects model types (Cone, Pyramid, Cylinder)
   - Extracts metadata (thickness, speed, resin, etc.)

2. **Processes all autolog files**
   - Detects layers automatically
   - Calculates all metrics
   - Generates individual analysis plots

3. **Creates master outputs**
   - **MASTER_all_metrics.csv** - All measurements combined
   - **MASTER_area_analysis.png** - Peak force, work of adhesion, distances vs area
   - **MASTER_area_ratio_analysis.png** - Same metrics vs area ratio
   - **MASTER_distance_analysis.png** - Distance analysis

4. **Handles area mapping intelligently**
   - Uses LayerToArea.txt if available (global or per-folder)
   - Falls back to automated_work_of_adhesion.csv
   - Calculates from cone geometry as last resort

## Master Plot Formatting

All master plots use the **same consistent formatting** (from V5 work):
- **Area binning** (±5% tolerance) to group similar measurements
- **Error regions** (filled bands) showing SEM at each point
- **Dotted trendlines** (polynomial fits)
- **Small markers** (size=4) without connecting lines
- **Bold fonts** (12pt labels, 10pt legends)
- **Y-axis starts at 0** for positive-only data

## Folder Naming Conventions

The processor understands various naming patterns:

### Examples It Handles:
- `100umPDMS_1mm_V22p1_BPAGDA_Cone_1000`
- `TEMPO_1mm_V22p2_Cone_BPAGDA_1000`
- `ACF_5mm_V19_Cone_BPAGDA_200`
- `FlatPDMS_1mm_V22_Cone_BPAGDA_1000`

### Extracted Information:
- **Membrane**: PDMS, ACF, TEMPO, Flat PDMS, etc.
- **Thickness**: 100um, 5mm, 1mm, etc.
- **Tank**: V19, V22, V22p1, V22p2, V22p3
- **Model**: Cone, Pyramid, Cylinder
- **Resin**: BPAGDA, IBOA, HDDA
- **Speed**: 1000, 500, 200 µm/s

## Adding New Tanks

If you add a new tank type, update `TANK_SPECS` in `batch_process_universal.py`:

```python
TANK_SPECS = {
    'V19': {'type': 'circular', 'diameter_mm': 2 * 6.765},
    'V22': {'type': 'circular', 'diameter_mm': 2 * 6.765},
    'V23': {'type': 'circular', 'diameter_mm': 2 * 8.0},  # New tank
}
```

## Output Structure

After processing, your folder will contain:

```
V6/
├── MASTER_all_metrics.csv              # Combined data
├── MASTER_area_analysis.png            # Area-based plots
├── MASTER_area_ratio_analysis.png      # Ratio-based plots
├── MASTER_distance_analysis.png        # Distance plots
├── ACF_5mm_V19_Cone_BPAGDA_200/
│   ├── autolog_L100-L105.csv
│   ├── plots/
│   │   └── plots_20251202_HHMMSS/
│   │       ├── autolog_L100-L105_analysis.png
│   │       ├── autolog_L140-L145_analysis.png
│   │       └── ...
├── FlatPDMS_1mm_V22_Cone_BPAGDA_1000/
│   └── plots/...
└── TEMPO_1mm_V22p1_Cone_BPAGDA_1000/
    └── plots/...
```

## Comparison with Old System

### Before (Manual):
1. Copy `batch_process_v5_data.py` → `batch_process_v6_data.py`
2. Edit folder parsing logic
3. Update tank specifications
4. Fix plot formatting
5. Debug import paths
6. Test and iterate
7. **Repeat for every new version**

### Now (Automatic):
1. `python process_folder.py V6`
2. Done!

## Technical Details

### Architecture
- **UniversalBatchProcessor** - Main processing engine
- **FolderInfo** - Smart folder name parser
- **RawDataProcessor** - Layer detection and metrics calculation
- **AnalysisPlotter** - Individual test plots
- **MasterPlotter** - Combined comparison plots

### Dependencies
- pandas, numpy, matplotlib, scipy
- adhesion_metrics_calculator
- RawData_Processor
- analysis_plotter
- master_plotter

### Imports Are Fixed
The universal processor correctly handles import paths from any location in the project hierarchy.

## Future-Proof

This system works with:
- ✅ V4, V5, V6 (tested)
- ✅ V7, V8, V9, ... (automatic)
- ✅ Any new membrane materials
- ✅ Any new tank types (just add to TANK_SPECS)
- ✅ Any new model geometries

## No More Manual Reformatting!

The days of reformatting plots for each new folder are over. One script, consistent formatting, automatic processing.

---

**Author:** Cheng Sun Lab Team  
**Date:** December 2, 2025  
**Last Update:** Fixed for universal processing across all versions
