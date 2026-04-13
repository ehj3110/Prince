# Rush Segmented VideoPattern

This folder is a standalone Rush-focused copy of the modular VideoPattern printer code.

## What is different
- Uses the A3200 stage adapter instead of the Zaber stage.
- Keeps the A3200 / Ensemble session open during printing.
- Does not home the stage automatically at the start of a print session.
- Uses Rush-local GUI state files.

## Main entry point
- `Rush_Segmented_VideoPattern.py`

## Notes
- The light engine and print workflow are intended to stay aligned with the modular codebase.
- If you move this folder to another machine, keep the folder structure intact so `support_modules/` stays beside the main script.
