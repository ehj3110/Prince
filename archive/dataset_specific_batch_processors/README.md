# Dataset-Specific Batch Processors Archive

**Archive Date:** February 25, 2026  
**Reason:** These scripts were created for specific experimental datasets and are superseded by `batch_process_universal.py`

---

## Contents

This directory contains batch processing scripts that were created for specific experimental datasets and processing iterations. Each script was designed to handle a particular dataset with specific requirements at the time.

### Scripts in This Archive

#### 1. **batch_process_final_presentation.py**
- **Dataset:** "Final" folder (renamed presentation data)
- **Purpose:** Reprocess with corrected peel distance calculations (positive values)
- **Special Features:** 
  - Hydrodynamic locking mitigation (200um skip)
  - Fixed peel distance sign issue
- **Date Created:** ~January 2026
- **Superseded By:** `batch_process_universal.py` with distance correction enabled

#### 2. **batch_process_final_with_areas.py**
- **Dataset:** Final presentation data
- **Purpose:** Extract layer numbers from filenames and assign cross-sectional areas
- **Special Features:**
  - Hardcoded FEP reference layer-to-area mapping (layers 50-325)
  - Layer number extraction from autolog filenames
  - Cross-sectional area assignment based on layer height
- **Date Created:** ~January 2026
- **Note:** Area mapping now handled by LayerToArea.txt files

#### 3. **batch_process_presentation_data.py**
- **Dataset:** Presentation data (multiple folders)
- **Purpose:** Comprehensive analysis with stiffness detection
- **Special Features:**
  - Hydrodynamic locking mitigation (200um)
  - Individual layer plots (AnalysisPlotter)
  - Dual-regime stiffness analysis
  - Master plots across conditions
  - Scaling analysis (radius vs metrics)
- **Date Created:** ~December 2025
- **Superseded By:** `batch_process_universal.py` + separate stiffness analyzer

#### 4. **batch_process_tempopicker_v2.py**
- **Dataset:** TEMPO Picker V2 folders
- **Purpose:** Process all subdirectories and generate master plots
- **Special Features:**
  - Uses `analyze_single_folder.py` processor
  - Area from `automated_work_of_adhesion.csv`
  - Master plot generation with TEMPO Picker style
- **Date Created:** ~January 20, 2026
- **Superseded By:** `batch_process_universal.py`

#### 5. **batch_process_tempopicker_v2_with_skip.py**
- **Dataset:** TEMPO Picker V2 folders (reprocessed)
- **Purpose:** Reprocess with hydrodynamic locking mitigation
- **Special Features:**
  - Distance-based peak filtering (200um skip)
  - Individual autolog plots with AnalysisPlotter
  - Timestamped plot folders
  - Combined results CSV
- **Date Created:** ~January 2026
- **Note:** Same as #4 but with skip distance feature

#### 6. **batch_process_v2_selected.py**
- **Dataset:** Selected V2 data (2p5PEO and Water_1000)
- **Purpose:** Generate master plots similar to TEMPO Picker format
- **Special Features:**
  - Filters out metrics files from autolog search
  - 4-metric master plots (peak force, work, distance, retraction)
  - Uses tempo_picker_plot_styles.py functions
- **Date Created:** ~January 20, 2026
- **Superseded By:** `batch_process_universal.py`

---

## Why These Were Archived

### Evolution of Batch Processing System

**Original Approach (2025):** Create custom scripts for each dataset
- Pros: Tailored to specific needs
- Cons: Code duplication, hard to maintain

**Current Approach (2026):** Universal batch processor
- `batch_process_universal.py` - Handles any dataset automatically
- Detects folder naming conventions
- Identifies data types (cone, pyramid, cylinder)
- Extracts metadata automatically
- Supports LayerToArea.txt (global or per-folder)
- Generates both individual and master plots

### Functionality Now Available In

| Feature | Old Script(s) | New Location |
|---------|--------------|--------------|
| Universal processing | All | `batch_processors/batch_process_universal.py` |
| Hydrodynamic mitigation | #1, #3, #5 | AdhesionMetricsCalculator parameter |
| Individual plots | #3, #5 | AnalysisPlotter (auto in universal) |
| Master plots | #2-6 | MasterPlotter (auto in universal) |
| Stiffness analysis | #3 | `post-processing/material_stiffness_analyzer.py` |
| Area mapping | #2 | LayerToArea.txt support |
| TEMPO Picker style | #4-6 | `tempo_picker_plot_styles.py` functions |

---

## Current Recommended Workflow

For any new dataset:

1. **Organize data structure:**
   ```
   MasterFolder/
   ├── Condition1/
   │   ├── autolog_L101-L110.csv
   │   └── ...
   ├── Condition2/
   │   └── ...
   └── LayerToArea.txt (optional)
   ```

2. **Run universal processor:**
   ```bash
   python batch_processors/batch_process_universal.py "path/to/MasterFolder"
   ```
   
   Or configure MASTER_DATA_PATH in the script and run:
   ```bash
   python batch_processors/batch_process_universal.py
   ```

3. **Additional analyses (optional):**
   - Stiffness: `python post-processing/material_stiffness_analyzer.py`
   - Custom master plots: Use `MasterPlotter` class directly
   - TEMPO Picker style: Import from `tempo_picker_plot_styles.py`

---

## Historical Context

These scripts document the iterative development of the adhesion test analysis system:

- **Early 2025:** Basic processing with manual area assignment
- **Mid 2025:** Added hydrodynamic locking mitigation
- **Late 2025:** Developed comprehensive plotting (AnalysisPlotter)
- **Dec 2025 - Jan 2026:** Multiple iterations on presentation data
- **Jan 2026:** Standardized TEMPO Picker plotting style
- **Jan 2026:** Consolidated into universal processor

Each script represents a learning step in developing the final, robust analysis pipeline.

---

## If You Need to Reference These Scripts

**For algorithm details:**
- Hydrodynamic mitigation: See `skip_initial_distance_um` implementation
- Area assignment logic: See hardcoded mappings in #2
- Stiffness detection: See dual-regime analysis in #3

**For dataset-specific parameters:**
- Check hardcoded paths and folder names
- Review skip distances used
- See metric calculations and normalization

**Note:** The core algorithms have been extracted and integrated into the support modules. These scripts are preserved for reference only.

---

## Migration Notes

If you need to reprocess these specific datasets:

1. **Use universal processor** with same parameters
2. **Check for dataset-specific quirks** documented in script headers
3. **Verify area mapping** - may need LayerToArea.txt file
4. **Enable hydrodynamic skip** if data is affected (200um typical)

---

**Related Documentation:**
- [WORKSPACE_ORGANIZATION_RECOMMENDATIONS.md](../../WORKSPACE_ORGANIZATION_RECOMMENDATIONS.md) - Phase 2
- [batch_processors/README.md](../../batch_processors/README.md) - Current batch processor overview
- [COMPREHENSIVE_PLOT_FORMAT_GUIDE.md](../../COMPREHENSIVE_PLOT_FORMAT_GUIDE.md) - Plot formatting standards

---

**Archived by:** Workspace cleanup Phase 2  
**Scripts remain functional** but are no longer actively maintained
