# Calibration Modules Handoff
**Date:** April 4, 2026  
**Scope:** `calibration_modules/` status review, technical state, and next-step planning  
**Prepared for:** project handoff and calibration roadmap planning

---

## Executive Summary

The calibration subsystem is in a **partially integrated but technically strong** state.

At the algorithm and module level, ChArUco-based focus and tilt analysis appears **implemented and functional**. The camera manager, ChArUco calibrator, and automated workflow logic are present and substantial. Pattern generation and DLP pattern-mode test tooling also exist.

However, there is **documentation drift and UI text drift**:
- Several docs and in-window labels still describe focus/tilt as placeholders.
- Newer docs and code indicate those features are already implemented.

Current practical interpretation:
- **Core calibration logic:** implemented
- **Operator workflow consistency and deployment confidence:** not fully locked down
- **Production readiness:** close, but requires one coordinated validation pass and doc/UI cleanup

---

## What Exists Right Now

## Module Inventory

- `calibration_modules/AlliedVisionCameraManager.py`
- `calibration_modules/ChArucoCalibrator.py`
- `calibration_modules/CalibrationWorkflow.py`
- `calibration_modules/CameraViewWindow.py`
- `calibration_modules/test_camera.py`
- `calibration_modules/test_pattern_generation.py`
- `calibration_modules/test_dlp_pattern_display.py`
- `calibration_modules/README.md`
- `calibration_modules/IMPLEMENTATION_SUMMARY.md`
- `calibration_modules/INTEGRATION_GUIDE.md`
- `calibration_modules/AUTOMATED_WORKFLOW_GUIDE.md`
- `calibration_modules/SETUP_ON_PRINTER_COMPUTER.md`
- `calibration_modules/CHARUCO_IMPLEMENTATION_SUMMARY.md`
- `calibration_modules/CHARUCO_TECHNICAL_DOCUMENTATION.md`
- `calibration_modules/QUICK_REFERENCE.md`

## Functional Components

### 1) Camera hardware interface

`AlliedVisionCameraManager.py` includes:
- camera discovery/connect/disconnect
- threaded streaming with callback dispatch
- single-frame capture
- exposure/gain control
- ChArUco integration entry points

Notable technical detail:
- Frame data is copied before requeue (`.copy()`), reducing race/corruption risk during streaming callbacks.

### 2) ChArUco calibration engine

`ChArucoCalibrator.py` includes:
- pattern generation at projector resolution
- ROI masking (center fraction; default 50%) for vignetting constraints
- focus scoring (edge-based method default, plus Tenengrad/Laplacian options)
- tilt detection using ArUco/ChArUco pose estimation
- fallback relative tilt estimation when intrinsics are unavailable
- optional overlay rendering for detections

This is a meaningful implementation, not a placeholder.

### 3) Automated calibration workflow

`CalibrationWorkflow.py` includes:
- automatic pattern preparation
- DLP projection setup for calibration mode
- camera auto-optimization loop (exposure/gain sweep based on marker detection)
- real-time guidance callbacks
- accept/save flow with calibration logging
- DLP restoration logic

The structure is suitable for a guided operator workflow at print startup.

### 4) Camera window UX

`CameraViewWindow.py` includes:
- live camera view
- exposure/gain controls
- snapshot capture
- pattern generation button
- focus, tilt, and combined analysis buttons
- calibration workflow panel with start/stop/accept flow

Important mismatch:
- It still contains stale text indicating calibration algorithms are placeholders, while the backend implementation exists.

---

## Documentation Reality Check

The folder contains two generations of documentation.

## Older generation (now partially stale)

Examples:
- `README.md`
- `IMPLEMENTATION_SUMMARY.md`
- `QUICK_REFERENCE.md`

These contain statements like placeholder focus/tilt or "next step" implementation language that no longer fully matches current code.

## Newer generation (closer to code truth)

Examples:
- `CHARUCO_IMPLEMENTATION_SUMMARY.md`
- `CHARUCO_TECHNICAL_DOCUMENTATION.md`
- `AUTOMATED_WORKFLOW_GUIDE.md`

These describe complete ChArUco focus+tilt and automated workflow behavior, and are largely aligned with module capabilities.

## Practical implication

Do not treat every calibration doc equally. Some files are implementation-era snapshots and now out of date. The handoff and planning process should prioritize:
1. actual Python code behavior
2. ChArUco-focused docs
3. updated integration assumptions from current mainline printer code

---

## Where Work Likely Left Off

Based on code and docs together, the project appears to have stopped at the boundary between:
- "algorithm + workflow built"
- and "fully standardized daily operator flow on printer hardware"

In concrete terms, this suggests:
- The team implemented calibration modules deeply.
- They documented multiple onboarding/testing paths.
- They had not yet fully consolidated stale docs/UI text.
- They likely still needed a clean end-to-end runbook on the target printer computer with the exact DLP mode and camera setup used in production.

---

## What Is Working vs Not Confirmed

## Strongly implemented in code

- ChArUco pattern generation
- focus scoring pipeline
- tilt estimation pipeline
- streaming and frame callback architecture
- calibration workflow orchestration
- test scripts for camera, pattern generation, DLP pattern display

## Not fully confirmed from this review alone

- real hardware validation status on your current printer computer image
- exact compatibility with your latest DLP control path used in `Prince_Segmented_VideoPattern.py`
- stability/latency of continuous workflow during concurrent print-system activity
- whether camera intrinsics are calibrated and persisted for absolute tilt

---

## Gaps and Limitations

### 1) Stale labels/messages create operator confusion

At least one UI area still says "placeholder" despite implemented logic.

Impact:
- users may under-trust features that actually work
- inconsistent training/handoff narratives

### 2) Dependency naming and install ambiguity

Docs mention Vimba Python package and SDK steps. Environment logs show unrelated package attempts (for example `vimbaX`) that failed.

Impact:
- setup friction
- risk of "installed wrong thing" on printer computer

### 3) Integration assumptions for DLP mode differ by era

`CalibrationWorkflow.py` uses a specific DLP pattern-mode flow and restoration behavior. Your current print pipeline has been actively tuned recently.

Impact:
- calibration workflow may need alignment with current DLP startup/cleanup conventions to avoid mode/state conflicts.

### 4) Intrinsics path likely optional but not operationalized

Code supports intrinsics for absolute angles, but no evidence in this pass that there is a finalized intrinsics artifact lifecycle (capture, save, load, versioning).

Impact:
- potential inconsistency in tilt interpretation across machines/sessions.

### 5) Test scripts exist, but no single canonical "go/no-go" checklist linked to latest printer stack

Impact:
- high chance of teams repeating bring-up effort or missing one critical dependency step.

---

## Interpretation of Provided Pattern Images

The supplied images are consistent with a ChArUco projection workflow and include both successful pattern projections and at least one dark frame. This aligns with expected behavior during mode transitions, exposure changes, or DLP stop/idle states.

What we can infer:
- Pattern generation and rendering pipeline likely works.
- There may still be transition states where display is intentionally or unintentionally dark.

What we cannot infer from images alone:
- absolute focus quality
- quantitative tilt correctness
- camera intrinsics calibration quality
- exact runtime state machine correctness

---

## Recommended Next Steps (Prioritized)

## Phase 1: Truth Alignment (fast)

1. Update stale wording in `CameraViewWindow.py` and older docs to reflect implemented ChArUco capabilities.
2. Add a single "current state" section in `calibration_modules/README.md` that points to canonical docs.
3. Standardize dependency instructions to the exact printer-computer procedure and tested package names.

Deliverable:
- one source of truth for capabilities and setup.

## Phase 2: Hardware Validation (critical)

1. Run `test_camera.py` discovery, connection, capture, and window tests on the printer computer.
2. Run `test_pattern_generation.py` and `test_dlp_pattern_display.py` with current DLP stack.
3. Execute one full automated workflow session (`CalibrationWorkflow`) and verify:
   - pattern projection
   - marker detection counts
   - focus/tilt responsiveness
   - DLP restore state

Deliverable:
- signed validation log with pass/fail and screenshots.

## Phase 3: Integration Hardening

1. Align calibration DLP mode transitions with the current production DLP state machine used for printing.
2. Ensure calibration start/stop cannot leave DLP in a conflicting mode for print startup.
3. Define behavior if camera unavailable: degrade gracefully and continue print prep.

Deliverable:
- deterministic calibration-to-print handoff behavior.

## Phase 4: Intrinsics Operationalization (optional but valuable)

1. Capture and store camera intrinsics in a known location.
2. Add load-on-start behavior with clear status indicator (absolute vs relative tilt mode).
3. Version and timestamp intrinsics for reproducibility.

Deliverable:
- consistent absolute tilt measurements across sessions.

---

## Proposed Handoff Checklist

### Setup
- Vimba SDK installed and validated in vendor tools
- Python deps installed from `camera_requirements.txt`
- camera detected by `test_camera.py --discovery`

### Functional
- live stream stable in `CameraViewWindow`
- exposure/gain controls verified
- snapshot verified
- ChArUco pattern generated and displayed on projector

### Calibration
- focus score responds monotonically to deliberate focus perturbations
- tilt responds correctly to known physical adjustments in both axes
- combined analysis returns marker count and metrics consistently

### Workflow
- `Start Calibration` performs projection + optimization + guidance
- `Accept Calibration` persists data and exits cleanly
- DLP returns to expected mode for print preparation

### Documentation
- stale placeholder text removed
- canonical docs linked from `README.md`
- operator runbook finalized for daily startup

---

## Risk Register

### Risk: Documentation mismatch causes incorrect operation
Mitigation: Canonicalize docs and remove stale placeholder language.

### Risk: DLP mode conflict between calibration and print startup
Mitigation: Validate transition contract and enforce explicit restore state.

### Risk: Camera setup variance across machines
Mitigation: Standardize SDK + dependency procedure and add machine verification checklist.

### Risk: Relative tilt interpreted as absolute
Mitigation: Explicitly label measurement mode and prioritize intrinsics provisioning.

---

## Bottom Line

The calibration subsystem is not an early prototype. It is a substantial implementation with ChArUco-based focus/tilt and an automated workflow.

Where you left off is best described as:
- **Core calibration engineering complete**
- **Operational hardening and documentation unification pending**

The highest-value immediate action is a short integration validation sprint that aligns calibration mode transitions with your now-stabilized print/DLP pipeline and then updates docs/UI to match reality.
