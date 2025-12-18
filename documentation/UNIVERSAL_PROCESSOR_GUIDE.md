# Universal Batch Processor Guide

## Overview

The **Universal Batch Processor** (`batch_process_universal.py`) automatically processes adhesion test data from any version (V4, V5, V6, ...) without needing to write new scripts for each test series.

## Key Features

✅ **Automatic Version Detection** - Detects V4, V5, V6, etc. from folder structure  
✅ **Smart Folder Parsing** - Extracts membrane type, tank type, model, resin, speed automatically  
✅ **Flexible Area Mapping** - Supports global or per-folder LayerToArea.txt files  
✅ **Duplicate Handling** - Automatically handles duplicate layer numbers (keeps last entry)  
✅ **Individual Plots** - Generates timestamped plots for each autolog file  
✅ **Master Plots** - Creates comprehensive comparison plots across all conditions  
✅ **Extensible** - Easy to add new tank types, membrane types, etc.

## Quick Start

### Option 1: Process a specific folder
```bash
python batch_process_universal.py "C:\path\to\your\data\folder"
```

### Option 2: Use configured default path
Edit `MASTER_DATA_PATH` in the script, then:
```bash
python batch_process_universal.py
```

## Folder Structure Requirements

The processor searches recursively for folders containing `autolog_*.csv` files.

### Supported Naming Conventions

**Examples:**
- `100umPDMS_1mm_V22p1_BPAGDA_Cone_1000`
- `TEMPO_1mm_V22p2_Cone_BPAGDA_1000`
- `200umPDMS_2mm_V19_Cone_IBOA_500`
- `ACF_1mm_TankV19_Pyramid_HDDA_1000`

**What it extracts:**
- **Membrane Type**: PDMS, ACF, TEMPO, etc.
- **Membrane Thickness**: 100um, 200um (if specified)
- **Height**: 1mm, 2mm, etc.
- **Tank Type**: V19, V22, V22p1, V22p2, etc.
- **Model**: Cone, Pyramid, Cylinder
- **Resin**: BPAGDA, IBOA, HDDA
- **Speed**: 1000, 500 (µm/s)
- **Version**: Detected from parent folder name (V4, V5, V6, etc.)

## Layer-to-Area Mapping

The processor handles area mapping in three ways (in priority order):

### 1. Folder-Specific LayerToArea.txt (Highest Priority)
Place `LayerToArea.txt` in the test folder:
```
Layer_Number	Area_mm2
60	9.9
100	12.79
140	15.39
...
```

### 2. Global LayerToArea.txt (Medium Priority)
Place `LayerToArea.txt` in your master folder root - applies to all subfolders.

### 3. Automated CSV (Fallback)
Uses `automated_work_of_adhesion.csv` if present in folder.

**Note:** Duplicate layer numbers are automatically handled (keeps last occurrence).

## Tank Specifications

The processor includes built-in tank specs. To add a new tank:

```python
TANK_SPECS = {
    'TankV19': {'type': 'circular', 'diameter_mm': 7.62},
    'TankV22': {'type': 'circular', 'diameter_mm': 6.765},
    'TankV22p1': {'type': 'circular', 'diameter_mm': 6.765},
    'TankV22p2': {'type': 'circular', 'diameter_mm': 6.765},
    'TankV23': {'type': 'circular', 'diameter_mm': 8.0},  # Add new tank here
}
```

## Output Files

### Individual Plots
Generated for each autolog file:
- **Location**: `[test_folder]/plots/plots_[timestamp]/`
- **Format**: `autolog_L100-L105_analysis.png`
- **Content**: Force curves, phase markers, metrics for each layer

### Master CSV
Combined data from all processed folders:
- **Filename**: `MASTER_all_metrics.csv`
- **Location**: Master directory root
- **Columns**: All metrics + metadata (membrane, tank, version, etc.)

### Master Plots
Comparison plots across all conditions:
- `MASTER_area_analysis.png` - Force, work, distance vs. area
- `MASTER_area_ratio_analysis.png` - Metrics vs. area ratio
- `MASTER_distance_analysis.png` - Distance breakdown by phase

## Example Workflow

### Processing New Test Data (e.g., V6)

1. **Organize your data:**
   ```
   V6/
   ├── LayerToArea.txt (optional, global for all V6 tests)
   ├── 100umPDMS_1mm_V23_Cone_BPAGDA_1000/
   │   ├── autolog_L60-L65.csv
   │   ├── autolog_L100-L105.csv
   │   └── LayerToArea.txt (optional, folder-specific)
   ├── TEMPO_1mm_V23_Cone_BPAGDA_1000/
   │   ├── autolog_L60-L65.csv
   │   └── autolog_L100-L105.csv
   └── ...
   ```

2. **Run the processor:**
   ```bash
   python batch_process_universal.py "C:\path\to\V6"
   ```

3. **Check outputs:**
   - Individual plots in each folder's `plots/plots_[timestamp]/`
   - `MASTER_all_metrics.csv` in V6 folder
   - Master plots in V6 folder

### No Code Changes Needed!

The universal processor automatically:
- Detects it's V6 data
- Parses folder names (even with new tank types if added to TANK_SPECS)
- Processes all folders recursively
- Generates all plots and CSVs

## Comparison with Version-Specific Processors

| Feature | V4/V5 Processors | Universal Processor |
|---------|-----------------|-------------------|
| **Version Support** | Single version only | All versions (V4, V5, V6, ...) |
| **New Tests** | Write new script | No code changes needed |
| **Folder Finding** | Manual path per version | Automatic recursive search |
| **Naming Flexibility** | Fixed patterns | Flexible parsing |
| **Maintenance** | Multiple scripts | Single script |
| **Future-Proof** | New script per version | One script for all |

## When to Use Version-Specific Processors

Keep `batch_process_v4_data.py` and `batch_process_v5_data.py` for:
- **Legacy Processing** - Reprocessing old data with exact same logic
- **Debugging** - Comparing outputs when troubleshooting
- **Special Cases** - If a specific version has unique requirements

## Advanced Configuration

### Adding New Membrane Types

The parser automatically detects common patterns. For new types, add to parsing logic:

```python
# In FolderInfo._parse_folder_name()
elif 'newmembrane' in part_lower:
    self.membrane_type = "NewMembrane"
```

### Custom Tank Shapes

For non-circular tanks:

```python
TANK_SPECS = {
    'TankV24': {'type': 'square', 'side_mm': 10.0},  # 100 mm²
}

# Update _calculate_tank_area() to handle square tanks
if specs['type'] == 'square':
    return specs['side_mm'] ** 2
```

### Filtering Folders

To process only specific membrane types or models, add filtering:

```python
# In process_all_folders()
test_folders = self.find_test_folders()
test_folders = [f for f in test_folders if f.membrane_type == "TEMPO"]  # Only TEMPO
```

## Troubleshooting

### "No test folders found"
- Check that folders contain `autolog_*.csv` files
- Verify master directory path is correct

### "No layer-to-area mapping available"
- Add `LayerToArea.txt` to folder or master directory
- Verify `automated_work_of_adhesion.csv` exists and has correct columns

### "Unknown tank type"
- Add tank specifications to `TANK_SPECS` dictionary
- Check folder name matches tank naming pattern

### "Layer X not in area mapping"
- Verify LayerToArea.txt contains all required layer numbers
- Check for typos in layer numbers

## Future Enhancements

Potential additions:
- [ ] Automatic tank detection from print files
- [ ] Multi-threaded processing for speed
- [ ] Web interface for monitoring progress
- [ ] Automatic outlier detection
- [ ] Integration with LIMS database
- [ ] Real-time processing during experiments

## Support

For issues or questions:
1. Check documentation in `documentation/` folder
2. Review `TESTING_GUIDE.md` for validation approaches
3. See `TroubleshootingIdeas.md` for common problems
4. Check Git history for recent changes

---

**Last Updated**: November 28, 2025  
**Author**: Cheng Sun Lab Team
