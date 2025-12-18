# Batch Processors

This folder contains all batch processing scripts for adhesion test data analysis.

## Scripts Overview

### 🌟 Universal Processor (Recommended)
**`batch_process_universal.py`** - Use this for all new test data
- Works with any version (V4, V5, V6, ...)
- Automatic folder detection and parsing
- No code changes needed for new test series
- See `documentation/UNIVERSAL_PROCESSOR_GUIDE.md` for details

### Legacy/Version-Specific Processors
**`batch_process_v4_data.py`** - V4 data processor
- For reference or reprocessing old V4 data
- Handles PDMS and ACF membranes with TankV19/V22

**`batch_process_v5_data.py`** - V5 data processor
- For reference or reprocessing old V5 data
- Added TEMPO membrane support
- Handles TankV22p1/V22p2 variants

### Specialized Processors
**`batch_process_printing_data.py`** - Process raw printing logs
- Extracts metrics from printer autolog files during experiments

**`batch_process_steppedcone_generalized.py`** - Generalized cone processing
- Earlier version with flexible configuration

## Quick Start

### For New Test Data
```bash
# Navigate to project root
cd C:\Users\ehunt\OneDrive\Documents\Prince\Prince_Segmented_20250926

# Run universal processor
python batch_processors\batch_process_universal.py "path\to\your\data"
```

### For Legacy Data
```bash
# V4 data
python batch_processors\batch_process_v4_data.py

# V5 data
python batch_processors\batch_process_v5_data.py
```

## Output Structure

All processors generate:
- **Individual plots** - One per autolog file in `plots/plots_[timestamp]/`
- **Master CSV** - Combined metrics in `MASTER_all_metrics.csv`
- **Master plots** - Comparison plots in data root directory

## Related Documentation

- `documentation/UNIVERSAL_PROCESSOR_GUIDE.md` - Complete universal processor guide
- `documentation/TESTING_GUIDE.md` - Testing and validation
- `documentation/DEPLOYMENT_GUIDE.md` - Setup and configuration
- `post-processing/BATCH_PROCESSING_GUIDE.md` - Technical details

## Migration Path

**Old workflow (Version-specific):**
```
New V6 data → Write batch_process_v6_data.py → Process
New V7 data → Write batch_process_v7_data.py → Process
```

**New workflow (Universal):**
```
Any new data → python batch_process_universal.py "path" → Process
```

---
Last Updated: November 28, 2025
