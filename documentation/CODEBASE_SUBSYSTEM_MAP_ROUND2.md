# Codebase Subsystem Map (Round 2 Kickoff)

## Purpose

This document starts the thorough documentation sweep by mapping active subsystems,
their scope, and documentation priority.

## Priority Legend

1. P0 - Core runtime and safety-critical workflows.
2. P1 - Frequently used processing and calibration workflows.
3. P2 - Supporting tools and legacy utilities.

## First-Pass Scope Matrix

| Subsystem | Python Files | Priority | Rationale | Status |
|-----------|--------------|----------|-----------|--------|
| Rush_Segmented_VideoPattern | 52 | P0 | Active production runtime path | IN_PROGRESS |
| support_modules | 49 | P0 | Shared logic used across runtimes | IN_PROGRESS |
| tests | 21 | P0 | Verification and regression safety | IN_PROGRESS |
| post-processing | 18 | P1 | Analysis workflows used after print runs | TODO |
| Rush (legacy) | 14 | P2 | Legacy scripts, still useful reference | TODO |
| calibration_modules | 11 | P1 | Calibration and camera workflows | TODO |
| batch_processors | 9 | P1 | High-volume data processing scripts | TODO |

## Excluded from Deep Module Narrative

These areas are tracked but excluded from full line-level docs unless needed:
1. .conda
2. __pycache__
3. SessionLogs
4. Binary image/media artifacts

## Round 2 Coverage Strategy

For each subsystem, produce:
1. Architecture overview.
2. Module-by-module index with entry points.
3. Data flow and interfaces.
4. Failure modes and operational constraints.
5. Test references and known gaps.

## Current Round 2 Progress (This Session)

Completed:
1. Z compensation calibration protocol draft.
2. Z compensation torture-test guide.
3. Dedicated torture test script and heavy execution.
4. Master documentation tracker and subsystem map kickoff.
5. support_modules deep index draft.
6. post-processing folder index.
7. calibration folder index.
8. debug folder index.

Next in queue:
1. support_modules follow-on docs for hardware, logging, motion, and image modification.
2. Rush_Segmented_VideoPattern runtime architecture map.
3. tests coverage map and execution matrix.
