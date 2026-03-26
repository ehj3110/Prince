# Gemini Handoff Report: Prince Segmented Architecture and Workflow

## 1) Document Purpose

This report gives Gemini a high-signal, low-noise understanding of the current project architecture, dependencies, workflow, and known failure patterns.

Primary goals:
- Improve suggestion quality for improvements, segmentation, and workflow changes.
- Reduce context overload by separating stable facts from task-specific details.
- Preserve consistency with the unified adhesion-analysis design.

---

## 2) Project Metadata

- Project: Prince Segmented 3D Printer Control Software
- Workspace root: Prince_Segmented_20250926
- Date: 2026-03-18
- Platform: Windows
- Main application entry point: Prince_Segmented.py
- Core analysis engine: support_modules/adhesion_metrics_calculator.py
- Batch manuscript analyzer: post-processing/manuscript_autolog_batch_analyzer.py
- Single-file propagation diagnostic harness: post-processing/test_single_autolog_prop_end_labels.py

---

## 3) Architecture Overview

### 3.1 Runtime Application Layer

Responsibilities:
- GUI-driven print control and operator interaction.
- Workflow orchestration for stage movement, exposure, and logging.
- Integration with hardware and support modules.

Primary file:
- Prince_Segmented.py

### 3.2 Hardware and Service Module Layer

Responsibilities:
- DLP projector control.
- Force gauge acquisition and calibration.
- Z-axis homing and movement coordination.
- USB conflict prevention between hardware components.
- Real-time sensor monitoring and logging.

Primary modules:
- support_modules/pycrafter9000.py
- support_modules/ForceGaugeManager.py
- support_modules/AutoHomeRoutine.py
- support_modules/USBCoordinator.py
- support_modules/dlp_phidget_coordinator.py
- support_modules/SensorDataWindow.py
- support_modules/PositionLogger.py
- support_modules/AutomatedLayerLogger.py
- support_modules/PeakForceLogger.py

### 3.3 Unified Scientific Analysis Layer

Responsibilities:
- Calculate adhesion-related metrics from Time/Position/Force data.
- Detect key physical events (initiation, peak force, propagation end, lift interval metrics).
- Provide a single source of truth for metric definitions used by runtime and post-processing paths.

Primary module:
- support_modules/adhesion_metrics_calculator.py

Important note:
- The architecture intent is that this calculator remains authoritative, with downstream scripts consuming it rather than re-implementing metric logic.

### 3.4 Post-Processing and Manuscript Analysis Layer

Responsibilities:
- Discover and batch-process autolog CSV files.
- Standardize columns and detect layers/windows.
- Compute per-layer metrics and export CSV summaries.
- Produce analysis plots and derivative diagnostics.

Primary files:
- post-processing/manuscript_autolog_batch_analyzer.py
- post-processing/analysis_plotter.py
- post-processing/debug_derivative_plotter.py
- post-processing/test_single_autolog_prop_end_labels.py

### 3.5 Documentation Layer

Responsibilities:
- Track scientific methodology, implementation details, and project status.

Primary index files:
- README.md
- documentation/README.md

---

## 4) Data Flow and Operational Workflow

### 4.1 Runtime Workflow (Printing Session)

1. Operator configures print and movement parameters in GUI.
2. Stage and projector actions are coordinated through control modules.
3. Force and position are sampled and buffered through dedicated acquisition/logging threads.
4. Layer-window logging captures targeted intervals.
5. Adhesion metrics are computed via unified calculator where enabled.

### 4.2 Post-Print Workflow (Batch Manuscript Analysis)

1. Recursively discover autolog CSV datasets.
2. Parse or infer metadata (window type, contact area).
3. Standardize data columns to Time, Position, Force.
4. Segment or infer layer regions and key indices.
5. Compute layer metrics using AdhesionMetricsCalculator.
6. Generate visual outputs (autolog analysis and derivative diagnostics).
7. Write per-file layer CSV outputs.
8. Aggregate combined manuscript summary CSV.

### 4.3 Validation Workflow

1. Use single-file diagnostic script for event marker verification.
2. Check marker alignment between derivative labels and autolog annotation.
3. Apply validated settings to full batch only after single-file confirmation.

---

## 5) Dependency Inventory (Thorough, Categorized)

This section distinguishes likely core requirements from optional and archival usage.

### 5.1 Python Standard Library (Commonly Used Across Active Scripts)

- argparse
- collections
- csv
- dataclasses
- datetime
- functools
- itertools
- math
- os
- pathlib
- queue
- re
- shutil
- signal
- subprocess
- sys
- threading
- time
- traceback
- typing
- warnings

### 5.2 Core Scientific and Analysis Dependencies

- numpy
- pandas
- scipy
- matplotlib

Commonly used components:
- scipy.signal.find_peaks
- scipy.ndimage.gaussian_filter1d

### 5.3 GUI and Visualization Runtime Dependencies

- tkinter
- matplotlib backend configuration (including headless Agg for batch plotting)

### 5.4 Hardware and Device Integration Dependencies

- cv2 (OpenCV)
- zaber_motion
- Phidget22
- usb.core
- screeninfo
- winsound (Windows-specific)

### 5.5 Internal Project Module Dependencies (Key Active Modules)

- support_modules.adhesion_metrics_calculator
- support_modules.PeakForceLogger
- support_modules.PositionLogger
- support_modules.SensorDataWindow
- support_modules.AutoHomeRoutine
- support_modules.AutomatedLayerLogger
- support_modules.USBCoordinator
- support_modules.dlp_phidget_coordinator
- support_modules.pycrafter9000
- support_modules.libs
- support_modules.Libs_Evan

### 5.6 Optional / Legacy / Experimental Dependencies Found in Repository Scan

Some archived or experimental files reference additional packages that are not necessarily baseline requirements for the active workflow, including examples such as:
- bokeh, dask, numba, cupy, torch, sympy, pyarrow, hypothesis, sphinx, reportlab, wx

Guidance:
- Treat these as optional unless the task explicitly targets those archived or specialized scripts.

---

## 6) Current Analysis Strategy Notes

The current analysis workflow emphasizes:
- Unified metric computation through support_modules/adhesion_metrics_calculator.py.
- Propagation-end strategies that include derivative-based detection modes.
- Batch processing via post-processing/manuscript_autolog_batch_analyzer.py.
- Visual diagnostics to validate event timing and marker alignment.

Recent tuning patterns in this project have included:
- Switching propagation-end detection modes for consistency.
- Adjusting derivative smoothing strength.
- Ensuring diagnostic scripts and production analyzers share equivalent configuration assumptions.

---

## 7) Coding Conventions and Style Signals

No dedicated style-guide markdown file was detected by style/guide filename patterns in this workspace.

Observed conventions from README and implementation structure:
- Keep scientific metric logic centralized in the unified calculator.
- Separate concerns by module category (hardware control, logging, analysis, post-processing).
- Maintain documentation that links methodology to implementation and validation.
- Prefer explicit validation runs on known datasets before broad batch reprocessing.

Recommended operational convention for AI-assisted edits:
- Avoid duplicating metric definitions in plotting or orchestration scripts.
- When changing event-detection parameters, update both diagnostic and batch contexts together.

---

## 8) Top 3 Recurring Error or Logic-Miss Categories

1. Mode or parameter mismatch between diagnostic and production paths.
- Symptom: event markers disagree between debug figures and batch/autolog plots.

2. Over-restrictive filtering of candidate signal events.
- Symptom: valid early post-peak candidates are excluded by distance or offset constraints.

3. Definition drift in key event boundaries.
- Symptom: core events (for example, lift start) shift from intended scientific definition to an alternate heuristic during iteration.

---

## 9) Context Segmentation Plan for Gemini

Use this to prevent context overload and keep recommendations focused.

### Segment A: Stable Baseline Context (Send Once Per Session)

- Architecture overview (Sections 3 and 4).
- Dependency inventory core blocks (Sections 5.1 to 5.5).
- Conventions and error categories (Sections 7 and 8).

### Segment B: Task-Specific Change Context (Send Per Task)

- Exact target files.
- Current algorithm mode and parameter values.
- One concrete failing behavior and one expected behavior.

### Segment C: Validation Context (Send with Fix Requests)

- One known-good dataset and expected outputs.
- One known-problem dataset and observed mismatch.
- Required acceptance checks (plots, CSV fields, marker alignment).

### Segment D: Risk and Scope Constraints (Send for Refactors)

- Must keep unified calculator as source of truth.
- Must avoid output schema breakage unless explicitly requested.
- Must include migration notes for changed definitions.

---

## 10) Gemini Prompt Blueprint

Use the following pattern for future asks:

Project context:
- Prince segmented printer control and adhesion analysis pipeline.
- Unified calculator is authoritative for metric definitions.

Task scope:
- [Describe one bounded objective]
- [List exact file targets]

Constraints:
- Do not create a second source of truth for adhesion metrics.
- Keep debug and batch analysis settings synchronized when validating event timing.
- Preserve output CSV and plot conventions unless schema change is requested.

Dependencies available:
- numpy, pandas, scipy, matplotlib, tkinter, cv2, zaber_motion, Phidget22, usb.core.

Validation requirements:
- Provide before/after behavior on one single-file diagnostic case.
- Provide impact check on one representative batch run.
- Report risks and rollback path.

Expected response format:
1) Proposed change set
2) Risk assessment
3) Validation plan
4) Minimal implementation order

---

## 11) Canonical Files for AI Grounding

- README.md
- documentation/README.md
- Prince_Segmented.py
- support_modules/adhesion_metrics_calculator.py
- support_modules/ForceGaugeManager.py
- support_modules/PeakForceLogger.py
- post-processing/manuscript_autolog_batch_analyzer.py
- post-processing/test_single_autolog_prop_end_labels.py

---

## 12) Maintenance Notes

Update this handoff report whenever one of the following changes:
- Core metric definitions in adhesion_metrics_calculator.
- Event boundary definitions (initiation, peak, propagation end, lift start/end).
- Output schema for per-layer or summary CSV files.
- Core dependency additions or removals.
- Runtime architecture changes across GUI, hardware coordination, or logging pipelines.
