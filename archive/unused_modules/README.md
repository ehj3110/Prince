# Unused Modules Archive

This directory contains post-processing modules that were developed but are not currently used in the active pipeline.

## Modules

### initiation_work.py
**Purpose:** Separate work of adhesion into initiation work (baselinepeak) vs propagation work (peakdetachment)

**Status:** Planned feature, not integrated into pipeline

**Scientific Value:** Could distinguish energy needed to START crack formation vs CONTINUE propagation

**To Use:** Import InitiationWorkCalculator and integrate with RawData_Processor output

---

### hybrid_adhesion_plotter.py
**Purpose:** Hybrid plotting approach combining AdhesionMetricsCalculator with automatic layer detection

**Status:** Replaced by analysis_plotter.py + RawData_Processor.py

**Note:** Older plotting system, superseded by current modular approach

---

### feature_extraction.py
**Purpose:** Extract time-series features from force curves (rise time, fall time, asymmetry, peak sharpness, oscillations, plateaus)

**Status:** Planned feature, not integrated into pipeline

**Scientific Value:** Could provide detailed insights into failure mechanisms

**To Use:** Import TimeSeriesFeatureExtractor and apply to raw force-time curves

---

### batch_process_v2_data.py
**Purpose:** Batch processor specifically for V2 data format (TEMPO, TEMPOV2 tests)

**Status:** Replaced by universal batch processor (process_folder.py)

**Note:** Version-specific processor no longer needed with universal system

---

### process_old_data.py
**Purpose:** Simple script to process very old data formats and generate metrics CSV

**Status:** Replaced by RawData_Processor.py + universal batch processor

**Note:** Legacy processor for old data formats

---

## Restoration

If you need any of these modules:
1. Copy from archive/unused_modules/ back to post-processing/
2. Review integration points with current pipeline
3. Update imports and test thoroughly

## Date Archived
December 18, 2025
