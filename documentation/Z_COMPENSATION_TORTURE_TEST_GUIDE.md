# Z Compensation Torture Test Guide

## Purpose

Define a repeatable stress-test procedure for the Z-compensation module to validate:
1. Numerical correctness under varied parameter regimes.
2. Stability and clipping behavior.
3. Heavy-shape runtime and memory behavior.

## Test Script

Primary script:
- tests/test_z_compensation_torture.py

This script runs three tiers:
1. Fast correctness checks.
2. Medium randomized checks.
3. Heavy memmap-backed stress case.

## Recommended Commands

From repository root:

1. Default torture run:
   - c:/Users/cheng sun/BoyuanSun/Prince_CurrentWorkingVersion/.conda/python.exe tests/test_z_compensation_torture.py

2. Heavier custom run:
   - c:/Users/cheng sun/BoyuanSun/Prince_CurrentWorkingVersion/.conda/python.exe tests/test_z_compensation_torture.py --z 224 --height 1024 --width 1024

3. Extra-randomized run:
   - c:/Users/cheng sun/BoyuanSun/Prince_CurrentWorkingVersion/.conda/python.exe tests/test_z_compensation_torture.py --random-cases 40

## What is Verified

1. Layer-factor bounds and monotonic trend.
2. 1D schedule consistency versus forward-dose reconstruction.
3. Backward volume solver correctness on random masks.
4. Memmap output correctness and finite values.
5. Heavy case non-negativity and expected trend under all-ones mask.

## Heavy-Case Notes

The heavy test intentionally uses a large 3D volume and writes exposure output as memmap.

Reason:
- Reduces peak RAM pressure while preserving realistic stress.
- Mirrors real production constraints for high-resolution, high-layer jobs.

## Pass Criteria

Treat run as PASS when:
1. Script exits with code 0.
2. No assertion failures appear.
3. Heavy-case summary prints finite min/max values.

## Failure Triage

If failures occur:
1. Factor bounds failure:
   - Check strength and min_factor clipping logic.
2. Dose reconstruction mismatch:
   - Check attenuation and backward recurrence equations.
3. Memmap or file I/O issues:
   - Verify temporary path permissions and available disk space.
4. Heavy-case OOM or long runtime:
   - Reduce z/height/width and rerun with documented parameters.

## Future Additions

Planned improvements:
1. CI-friendly reduced-size torture profile.
2. Optional benchmark CSV output.
3. Parameter sweep harness for regression envelopes.
