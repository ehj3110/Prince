# Stage and Light Engine Modularization Proposal

## Goal

Split printer hardware control so stage and light engine can be swapped independently, without rewriting main print orchestration.

## Current Coupling Snapshot

`Prince_Segmented_VideoPattern.py` currently contains direct hardware calls mixed into print logic:

- Stage calls via `self.axis.*` are spread through homing, movement, recovery, diagnostics, and manual jog paths.
- Light engine calls via `self.controller.*` are spread through startup, mode switching, exposure power, blackout, and shutdown paths.

This creates a single-file integration surface where changing one hardware subsystem tends to force edits in the same large file.

## Target Architecture

### 1) Adapter interfaces

Create two hardware interfaces (protocol/ABC):

- `IStageAdapter`
- `ILightEngineAdapter`

These should hide vendor-specific APIs (Zaber / pycrafter9000) behind a stable contract.

#### Suggested stage interface

- `connect()`
- `disconnect()`
- `home(wait_until_idle: bool = True)`
- `move_absolute_um(position_um, velocity_um_s=None, accel_um_s2=None, wait_until_idle=True)`
- `move_relative_um(delta_um, velocity_um_s=None, accel_um_s2=None, wait_until_idle=True)`
- `get_position_um()`
- `wait_until_idle()`
- `stop()`
- `get_fault_flags()`

#### Suggested light engine interface

- `connect()`
- `disconnect()`
- `enter_dark_idle()`
- `arm_video_pattern_mode(silent_wake_power, settle_s, color_mask)`
- `set_exposure_power(current_0_255)`
- `blackout_power_off()`
- `restore_next_layer_power(current_0_255)`
- `standby()`

### 2) Concrete adapters

Add vendor implementations in support modules:

- `support_modules/hardware/stage/zaber_stage_adapter.py`
- `support_modules/hardware/light_engine/dlp9000_light_engine_adapter.py`

For a new printer with different stage but same projector, only add:

- `support_modules/hardware/stage/<new_stage_adapter>.py`

No change to light engine adapter needed.

### 3) Hardware context / dependency injection

Add a small composition layer:

- `support_modules/hardware/hardware_context.py`

This creates adapter instances from config and hands them to main print logic.

### 4) Separate print orchestrator from UI

Extract print execution flow into:

- `support_modules/print_engine/print_orchestrator.py`

UI remains in `Prince_Segmented_VideoPattern.py`, but print loop delegates to orchestrator that only speaks adapter interfaces.

### 5) Capability flags

Adapters expose capability info, for example:

- `supports_accel_control`
- `supports_nonblocking_move`
- `supports_pattern_on_the_fly`

Orchestrator selects safe behavior per device instead of assuming vendor-specific features.

## Migration Plan

### Phase 1 (low risk)

- Add interfaces and concrete adapters.
- Keep existing flow in place.
- Replace direct `self.controller.*` calls with `self.light_engine.*` wrappers only.

### Phase 2 (medium risk)

- Replace direct `self.axis.*` calls with `self.stage.*` wrappers.
- Keep method names/units explicit (`_um`, `_mm`) to avoid conversion mistakes.

### Phase 3 (higher value)

- Extract print loop into `print_orchestrator.py`.
- Leave Tkinter/UI and status reporting in current main file.

### Phase 4 (new hardware onboarding)

- Implement new stage adapter.
- Run adapter conformance test suite and short dry print.

## Estimated Rewrite Impact

### Files likely touched (core)

- `Prince_Segmented_VideoPattern.py` (high-touch)
- `support_modules/motion_controller.py` (medium-touch for stage abstraction)
- `support_modules/AutoHomeRoutine.py` (medium-touch if directly using `axis`)
- `support_modules/SensorDataWindow.py` and `support_modules/PositionLogger.py` (light-touch if they consume stage handle directly)

### New files (recommended)

- `support_modules/hardware/interfaces.py`
- `support_modules/hardware/hardware_context.py`
- `support_modules/hardware/stage/zaber_stage_adapter.py`
- `support_modules/hardware/light_engine/dlp9000_light_engine_adapter.py`
- Optional tests under `tests/hardware/`

### Effort estimate

- Minimal adapter wrap only: 1-2 focused dev days
- Adapter + orchestrator extraction + validation: 4-8 dev days
- New stage bring-up after architecture exists: typically 0.5-2 days (depends on SDK quality)

## Runtime Performance Impact

Expected runtime impact is negligible.

- Adapter indirection adds function-call overhead in Python, usually microseconds per call.
- Stage and projector operations are millisecond-to-second scale, so overhead is effectively hidden.
- Practical throughput impact expected: <1% overall print cycle time in normal operation.

## Risks and Unforeseen Consequences

### 1) Unit mismatch bugs

Risk: mixing mm, um, and vendor native units.
Mitigation: enforce unit-specific method names and central conversion helpers.

### 2) Behavior drift during migration

Risk: startup/order timing changes in DLP path (historically sensitive).
Mitigation: keep existing known-good sequence unchanged inside light engine adapter first.

### 3) Thread ownership and shutdown semantics

Risk: disconnect/stop called from multiple places (UI close, stop button, exception handler).
Mitigation: define adapter lifecycle ownership in one place (hardware context) and make `disconnect()` idempotent.

### 4) Hidden direct hardware access in helper modules

Risk: some support modules may still call `axis`/`controller` directly.
Mitigation: add short audit and gradually route through adapters.

### 5) Testing gap for hardware abstraction

Risk: integration breaks are discovered only on machine.
Mitigation: add a fake stage and fake light engine adapter for dry-run test coverage.

## Future-Proofing Recommendations

- Keep a `printer_hardware.json` config that maps printer name to adapter classes and comm settings.
- Add a very small adapter conformance test script for each new hardware module.
- Keep DLP startup/shutdown sequencing encapsulated entirely in light engine adapter.
- Keep phase logging and safety checks in orchestrator, not in device adapters.

## Bottom Line

This modular split is very feasible and high leverage.

- You can make stage hardware swappable while preserving light engine behavior.
- You can reduce future printer bring-up from "rewrite large print script" to "implement one adapter".
- Performance penalty is effectively negligible relative to mechanical and exposure times.
