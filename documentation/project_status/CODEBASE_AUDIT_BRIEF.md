# Codebase Audit Brief (Gemini-Ready)
## Prince Segmented 3D Printer Control + Analysis

Date: 2026-03-18  
Purpose: Compact architecture + risk + action brief for AI planning.

---

## 1) Current Authoritative Architecture

### Core Runtime
- Main app: [Prince_Segmented.py](Prince_Segmented.py)
- Hardware/logging modules: [support_modules](support_modules)

### Unified Analysis Source of Truth
- Authoritative metrics engine: [support_modules/adhesion_metrics_calculator.py](support_modules/adhesion_metrics_calculator.py)
- Active mode support includes:
  - `prop_end_mode`
  - `baseline_mode`
  - `prop_end_local_window_seconds`
  - `two_step_max_second_derivative`

### Production Batch Path
- Primary post-processing analyzer: [post-processing/manuscript_autolog_batch_analyzer.py](post-processing/manuscript_autolog_batch_analyzer.py)

---

## 2) Validation Snapshot (Current)

Validated on [autolog_L48-L50.csv](autolog_L48-L50.csv):

1. Modern mode
- Command: `python test_adhesion_calculator.py --mode modern --csv autolog_L48-L50.csv`
- Status: PASS

2. Legacy mode
- Command: `python test_adhesion_calculator.py --mode legacy --csv autolog_L48-L50.csv`
- Status: PASS

Implication:
- Both modern and backward-compatibility paths are currently functional in this workspace snapshot.

---

## 3) Import Standardization State

Active imports use `libs` only:
- [Prince_Segmented.py](Prince_Segmented.py#L16)
- [support_modules/prints_layergenerator.py](support_modules/prints_layergenerator.py#L10)

No active `Libs_Evan` imports were detected.

---

## 4) Highest-Risk Redundancies Remaining

1. Duplicate/legacy logger variants in [support_modules](support_modules):
- [support_modules/PeakForceLogger_original_corrupted.py](support_modules/PeakForceLogger_original_corrupted.py)
- [support_modules/PeakForceLogger_unified.py](support_modules/PeakForceLogger_unified.py)

2. Potential analysis drift file:
- [batch_process_printing_data.py](batch_process_printing_data.py)
- Risk: likely contains inline metrics logic outside unified calculator.

3. Root script sprawl:
- Many one-off debug/utility scripts in root increase indexing noise and maintenance overhead.

---

## 5) Immediate Action Plan (Short)

### A. Safe Cleanup
1. Archive/delete [support_modules/PeakForceLogger_original_corrupted.py](support_modules/PeakForceLogger_original_corrupted.py)
2. Merge-or-remove [support_modules/PeakForceLogger_unified.py](support_modules/PeakForceLogger_unified.py) after confirming parity with [support_modules/PeakForceLogger.py](support_modules/PeakForceLogger.py)

### B. Logic Consolidation
1. Refactor [batch_process_printing_data.py](batch_process_printing_data.py) to call [support_modules/adhesion_metrics_calculator.py](support_modules/adhesion_metrics_calculator.py)

### C. Workspace Hygiene
1. Move root one-off scripts into `tools/`, `debug/`, `experiments/`
2. Move ad-hoc CSV artifacts into `tests/data/`

---

## 6) Constraints for Gemini Suggestions

Any proposed refactor should preserve:
1. Modern path: `second_derivative_zero_crossing` + point baseline
2. Legacy path: `two_step_max_second_derivative` + two-step baseline averaging
3. Single source of truth in [support_modules/adhesion_metrics_calculator.py](support_modules/adhesion_metrics_calculator.py)

---

End of brief.
