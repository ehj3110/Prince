# Debug Folder Index

## Purpose

The debug-related areas in this repository serve two different roles.

1. The top-level `debug/` folder contains integration and pipeline validation utilities.
2. The shared `support_modules/DebugSupport.py` module provides centralized debug logging control.
3. The Rush legacy folder also contains small debug text-generation scripts.

This document covers the debug surface as a documentation target, not as a production subsystem.

## What This Area Owns

1. Integration checks for end-to-end pipeline behavior.
2. Centralized debug-message gating.
3. One-off scripts for generating debug text outputs.
4. Temporary validation helpers used during development and troubleshooting.

## Major Files

### `debug/verify_pipeline_integration.py`

Standalone validator for the post-processing pipeline.
It validates folder-level CSV discovery, segmentation, metric calculation, sign checks, and production plot generation for a known dataset.

### `support_modules/DebugSupport.py`

Central debug helper used to keep normal runs quiet while allowing verbose output when needed.
It exposes shared enable/disable state and a gated print helper.

### `Rush/debug_gen_txt.py`

Legacy debug text generator that writes Rush layer instructions from a folder of image files.

### `Rush/debug_gen_txt_Evan.py`

Variant of the Rush debug text generator with a slightly different header/output format.

## Debug Patterns

1. Use a gated shared debug helper when the behavior is runtime-wide.
2. Use one-off scripts when the task is file generation or manual validation.
3. Keep validation tools separate from production paths so they do not affect print timing.

## Dependencies

1. `support_modules.RawData_Processor`
2. `support_modules.adhesion_metrics_calculator`
3. `post-processing/analysis_plotter.py`
4. `numpy`, `pandas`, and plotting dependencies for pipeline verification

## Failure Modes

1. Debug helpers left enabled during normal operator runs.
2. One-off scripts drifting out of sync with the production file format.
3. Validation utilities assuming a specific dataset layout or manuscript folder name.

## Documentation Notes

Debug code should stay narrow and clearly labeled.
The main risk in this area is confusion between reusable debug infrastructure and throwaway troubleshooting scripts.
