# support_modules Round 2 Index

## Purpose

This document is the first deep documentation pass for the shared support_modules tree.
It is meant to be an inventory and architecture guide, not a line-by-line code review.

## What This Tree Contains

support_modules is the shared runtime library layer for the Prince/Rush codebase.
It covers hardware adapters, GUI windows, logging, motion, print orchestration,
image modification, calibration support, and analysis helpers.

## Major Dependency Clusters

1. Hardware control and abstraction.
2. Print workflow orchestration.
3. Sensor logging and post-print analysis.
4. Image modification and compensation pipelines.
5. Calibration and experimental condition capture.
6. Utility and debug support.

## Module Inventory

### Core Hardware and Control

| Module | Role | Primary Consumers | Notes |
|-------|------|-------------------|------|
| pycrafter9000.py | Low-level DLP LightCrafter control | Prince GUI, Rush GUI, modular light adapters | Hardware-facing, safety-sensitive |
| DLPLightController.py | Thin controller seam for DLP power/state changes | Modular print orchestrator | Caches power state to avoid redundant writes |
| USBCoordinator.py | Serializes USB access across DLP/Phidget devices | Main GUIs, logging code | Helps prevent resource contention |
| dlp_phidget_coordinator.py | Coordination layer for mixed DLP/Phidget timing | Legacy and experimental paths | Similar conflict-avoidance role to USB coordinator |
| hardware/interfaces.py | Protocols for stage and light adapters | Hardware adapters and orchestrators | Defines adapter boundaries |
| hardware/hardware_context.py | Composition wrapper for stage + light engine | Modular hardware path | Provides connect/disconnect grouping |

### Motion and Stage Control

| Module | Role | Primary Consumers | Notes |
|-------|------|-------------------|------|
| motion_controller.py | Unified motion logic with smooth lift/retract | Rush/Prince runtime loops | Centralizes motion profiles and phase callbacks |
| StageSequencer.py | Stage command sequencing for modular runtime path | Print orchestrator | Bridges high-level intent to stage adapter |
| AutoHomeRoutine.py | Force-based automatic homing routine | Main GUI and setup flows | Safety-sensitive startup utility |
| hardware/stage/zaber_stage_adapter.py | Zaber hardware adapter implementation | Modular path | Concrete stage adapter |
| hardware/stage/mock_stage_adapter.py | Mock stage adapter for testing | Test harnesses, dry runs | Used when hardware is unavailable |

### Logging and Analytics

| Module | Role | Primary Consumers | Notes |
|-------|------|-------------------|------|
| PositionLogger.py | Threaded position/force/phase CSV logging | Sensor windows, print workflows | Captures live motion state |
| AutomatedLayerLogger.py | Splits continuous logs into per-layer artifacts | Main GUI and sensor panel | Layer boundary aware |
| PeakForceLogger.py | Real-time adhesion/peak-force metrics | Sensor panel and print flows | Used for per-layer peel analytics |
| VideoPatternPrintLogging.py | Video-pattern print session logging | Rush video-pattern GUI | Print-session metadata and event logs |
| LoggingCheckWindow_VideoPattern.py | UI helper for validating logging status | Video-pattern GUI | Human-facing logging validation |
| SessionManager.py | Session directory/state management | Main GUIs | Owns print numbering and log layout |
| adhesion_metrics_calculator.py | Adhesion metric computation from recorded data | Post-processing and real-time analysis | Core post-print math |
| two_step_baseline_analyzer.py | Robust baseline estimation helper | Adhesion analysis code | Baseline estimator for noisy force traces |

### Sensor and Experimental Windows

| Module | Role | Primary Consumers | Notes |
|-------|------|-------------------|------|
| SensorDataWindow.py | Live sensor dashboard and logging controls | Main GUI | Opens from sensor panel actions |
| SensorDataWindow_ExtendedWindow.py | Monitoring-focused sensor window | Main GUI | Read-only or extended monitoring mode |
| ExperimentalConditionsWindow.py | Capture experiment metadata | Main GUI | Stores run context for traceability |
| ExperimentalConditionsWindow_VideoPattern.py | Video-pattern metadata entry window | Rush video-pattern GUI | Variant tuned for video-pattern workflow |
| DefinitionsWindow.py | In-app documentation and parameter help | Main and Rush GUIs | User-facing reference panels |

### Image Modification and Compensation

| Module | Role | Primary Consumers | Notes |
|-------|------|-------------------|------|
| image_modification/processor.py | Full image-processing pipeline | ImageModificationWindow | Applies edge/global/depth/scatter compensation |
| image_modification/edge_enhancement.py | Edge enhancement routines | Processor | Image preconditioning |
| image_modification/global_enhancement.py | Global blur/asymmetric enhancement routines | Processor | Broad-brush luminance shaping |
| image_modification/padding.py | Padding and output sequencing helpers | Processor | Handles insert-padding outputs |
| image_modification/scattering_compensation.py | Scattering compensation model | Processor | Compensates internal light spread |
| image_modification/feature_depth.py | Feature-depth / Z-like overcuring compensation | Processor, ImageModificationWindow | Existing experimental axial-style compensation basis |
| image_modification/clip_pressure_compensator.py | Pressure-flow compensation model | Experimental docs and utilities | Alternative physics-based compensation path |
| image_modification/__init__.py | Package exports | Importers | Convenience re-exports |
| z_compensation.py | Dedicated axial Z-compensation utilities | ImageModificationWindow, future calibration tools | New dedicated module for future calibration work |
| ImageModificationWindow.py | GUI for image preprocessing and build/export | Standalone and Rush integration | UI front-end for the image-modification pipeline |

### Print Orchestration and Modular Runtime

| Module | Role | Primary Consumers | Notes |
|-------|------|-------------------|------|
| print_engine/print_orchestrator.py | Modular print-path coordinator | Rush modular scaffold | Encapsulates stage/light/frame sequencing |
| ProjectionFrameManager.py | Manages projected frame display | Modular and legacy print flows | Helps separate frame handling from control logic |
| hardware/light_engine/dlp9000_light_engine_adapter.py | Concrete DLP adapter | Modular print path | Wraps projector control for the modular seam |
| hardware/light_engine/mock_light_engine_adapter.py | Mock light-engine adapter | Tests and no-hardware modes | Enables safe dry-run validation |
| hardware_context.py | Bundles stage and light engine together | Modular setup code | Simple dependency container |

### Calibration, Analysis, and Utilities

| Module | Role | Primary Consumers | Notes |
|-------|------|-------------------|------|
| RawData_Processor.py | Raw analysis data handling | Post-processing tools | Bridges collected logs to analysis outputs |
| PatternBatchController.py | Pattern batch control helper | Special workflows | Batch-oriented control path |
| Parse/utility helpers in libs.py | File parsing, instruction generation, shared utilities | GUIs and print workflows | Legacy shared utility layer |
| DebugSupport.py | Debug logging and feature flags | Across support_modules | Controls verbose diagnostics |
| pycrafter9000 coordinator utilities | Direct hardware/protocol helper functions | DLP paths | Low-level control surface |

## Key Runtime Entry Points

1. Prince_Segmented.py uses support_modules for the main legacy print application.
2. Rush_Segmented_VideoPattern.py uses support_modules for the video-pattern workflow.
3. ImageModificationWindow.py uses support_modules/image_modification for preprocessing.
4. tests/ scripts import support_modules for unit and integration validation.

## Documentation Priorities For the Next Pass

1. High priority: motion_controller.py, SessionManager.py, print_orchestrator.py, hardware adapters.
2. Medium priority: sensor windows, logging modules, adhesion analytics.
3. Low priority: utility helpers and thin compatibility wrappers.

## Known Gaps

1. Several modules still rely on legacy implicit state and should receive explicit interface docs.
2. Some functionality is duplicated between legacy and Rush paths and needs a comparison note.
3. The image-modification package needs a separate design note for its compensation pipeline ordering.

## Next Documentation Artifacts To Write

1. support_modules/hardware architecture note.
2. support_modules/logging and analysis architecture note.
3. support_modules/image_modification pipeline note.
4. support_modules motion control note.
