# Codebase Documentation Round 2 (Master)

## Objective

Start a comprehensive, systematic documentation refresh for the entire repository.

This document is the master tracker for coverage, sequencing, and quality criteria.

## Baseline Snapshot

Repository file count at kickoff:
- 8713 files (includes environments and generated artifacts).

Top-level distribution snapshot (first-pass, by count):
1. .conda
2. ImageModificationGUI_export
3. Rush_Segmented_VideoPattern
4. support_modules
5. SessionLogs
6. documentation
7. tests
8. calibration_modules
9. post-processing
10. Rush

## Scope Definition

Round-2 scope includes:
1. Runtime Python modules used by active workflows.
2. Test harnesses and test utilities.
3. Core user-facing operational scripts and docs.

Round-2 excludes from deep line-by-line narrative docs (but may receive summary docs):
1. .conda
2. __pycache__
3. Session log outputs
4. Binary assets/images unless behavior-relevant

## Documentation Standards (Round 2)

For each module covered:
1. Purpose and ownership.
2. Inputs/outputs and key data structures.
3. Control flow and major entry points.
4. Failure modes and recovery behavior.
5. Test coverage and known gaps.
6. Change risk notes.

## Phased Coverage Plan

Phase A (in progress):
1. Z-compensation module family and image-modification integration.
2. Add calibration and stress-testing docs.

Phase B:
1. support_modules core utilities and adapters.
2. tests directory structure and execution map.

Phase C:
1. Rush_Segmented_VideoPattern runtime architecture.
2. calibration_modules and batch_processors.

Phase D:
1. post-processing scripts and data flows.
2. legacy/archived areas (summary-level only unless active).

## Coverage Tracker

Status keys:
- TODO
- IN_PROGRESS
- DONE

1. support_modules/z_compensation.py - DONE
2. support_modules/image_modification/processor.py - IN_PROGRESS
3. support_modules/ImageModificationWindow.py - IN_PROGRESS
4. tests/test_z_compensation_torture.py - DONE
5. tests/README.md (round-2 refresh) - TODO
6. support_modules (remaining active modules) - TODO
7. Rush_Segmented_VideoPattern (main runtime files) - TODO
8. calibration_modules - TODO
9. batch_processors - TODO
10. post-processing - TODO

## Deliverables for Round 2

1. Master architecture map by subsystem.
2. Per-subsystem deep docs with cross-links.
3. Updated testing and validation documentation.
4. Risk register for undocumented or fragile areas.

Current deliverables added:
1. Z compensation calibration protocol draft.
2. Z compensation torture-test guide.
3. Subsystem map kickoff document.
4. support_modules deep index.
5. post-processing folder index.
6. calibration folder index.
7. debug folder index.

## Stress-Test Evidence (Z Compensation)

Latest heavy run summary:
1. Command: tests/test_z_compensation_torture.py --z 192 --height 1024 --width 1024 --random-cases 35
2. Estimated exposure stack: 768.00 MB
3. Estimated mask stack: 192.00 MB
4. Heavy solve time: 1.88 s
5. Result: PASS

## Next Immediate Actions

1. Complete round-2 docs for image-modification pipeline and Z-comp subsystem.
2. Add stress-test execution results to docs.
3. Sweep the remaining documentation folder pages and verify cross-links.

## In Progress

1. support_modules root index drafted in [documentation/SUPPORT_MODULES_ROUND2_INDEX.md](documentation/SUPPORT_MODULES_ROUND2_INDEX.md).
2. Follow-on docs should split hardware, logging, motion, and image-modification subdomains.
3. Folder-level docs now added for post-processing, calibration, and debug.
