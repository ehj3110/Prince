# VIDEO PATTERN MODE HANDOFF
**Date**: April 4, 2026  
**Scope**: Video pattern mode, silent startup, and debug-mode cleanup  
**Status**: ✅ Working, documented, and ready for follow-up cleanup

---

## Summary

Over the last few days we iterated on `Prince_Segmented_VideoPattern.py` until video-pattern projection worked reliably again in stepped printing. The core problem was not the sliced image data itself, but the interaction between DLP startup sequencing, frame presentation, and the temporary debugging changes we introduced while chasing the failure.

The end result is a working video-pattern path with a silent wake sequence, a much quieter default terminal, and a dedicated debug toggle path for verbose diagnostics when needed.

---

## What We Tried

### 1. Video-pattern startup integration

We started by taking the validated silent startup logic from `tkinter_video_mode_test.py` and transferring the same projector arm sequence into `Prince_Segmented_VideoPattern.py`.

That test script established the successful baseline:
- start in dark idle
- enter HDMI handshake while dark
- wait for the display link to settle
- switch into pattern mode
- configure a single pattern definition
- start the sequence
- only then enable light output

The important lesson was that the projector could work in video-pattern mode, but only when the startup order and settle timing matched the known-good test flow closely enough.

### 2. Silent wake sequence

Once the video path was stable, we added a silent wake helper so the projector would remain dark during arming and only come up after the HDMI lock and pattern setup were complete.

This preserved the no-flash behavior we wanted while still using video-pattern mode.

### 3. Debug-heavy troubleshooting

We temporarily added a large amount of diagnostic output to isolate the failure mode. That helped reveal several distinct issues:
- startup ordering differences mattered
- `power(0)` / `changemode()` sequencing mattered
- the perceived lack of image was not just a rendering issue
- stepped-mode blackout logic had been disabled during debugging and needed to be restored

### 4. Terminal cleanup and debug-mode separation

After the working path was restored, we reduced the terminal noise and introduced a central debug helper so verbose output can be turned on intentionally instead of being hardcoded across modules.

---

## What Worked

### Silent video-pattern startup

The successful configuration uses a silent wake path that mirrors the tested sequence closely:
- `stopsequence()`
- `power(0)`
- `changemode(0x00)`
- `hdmi()`
- settle while dark
- `changemode(0x02)`
- `configurelut(1, 0xFFFFFFFF)`
- `definepattern(...)`
- `startsequence()`
- short settle delay
- low wake power before the print loop takes over

This is the first configuration that consistently got video-pattern projection working again without losing the startup silence.

### Stepped motion with blackout restored

The stepped print path now correctly turns the projector dark during peel/return motion again. That behavior had been disabled during troubleshooting, which is why we saw the pattern remain visible between layers.

### Shared debug gate

We added `support_modules/DebugSupport.py` as a central debug switch. Normal runs now stay quieter, while verbose terminal chatter can still be enabled deliberately when diagnosing issues.

The main support modules that now respect the shared debug path are:
- `support_modules/libs.py`
- `support_modules/AutoHomeRoutine.py`
- `support_modules/USBCoordinator.py`
- `support_modules/motion_controller.py`
- `Prince_Segmented_VideoPattern.py`

---

## What Did Not Work

### Direct video-pattern startup without matching the tested order

Earlier attempts started pattern mode too early, or skipped the exact mode-0 HDMI handshake sequence that the test script relied on. Those versions projected inconsistently or not at all.

### Leaving the debug pacing enabled

During troubleshooting, a test-style pacing mode was temporarily left active. That caused the projector to stay lit between layers, which was useful diagnostically but not acceptable for the actual stepped print workflow.

We corrected that and restored blackout-by-default in stepped mode.

### Overly noisy console output

The repository had a mix of hardcoded `print()` calls, ad hoc debug messages, and status updates routed through the GUI logger. That made it hard to tell which messages were real operational state versus temporary diagnostics.

The noise reduction work improved this, but some print-heavy modules still remain for future cleanup.

---

## Debug Mode Design

We did not remove all helper code immediately. Instead, we separated two concerns:

1. Normal production behavior
2. Verbose debug behavior when explicitly enabled

The new shared debug module provides a central switch that can be enabled through `PRINCE_DEBUG_MODE`.

That lets us keep the main workflow quiet while still preserving the ability to turn diagnostics back on when hardware timing questions come up again.

This is preferable to scattering `print()` calls across the codebase because it keeps the normal operator experience clean and makes the debug path discoverable and intentional.

---

## Why We Did Not Move Forward With the Ring Buffer Idea

We considered a ring buffer for debug history, but it was not the right next step for this problem.

### Reason 1: The problem was not loss of history

We were not losing debug information because of insufficient storage. The problem was that too much of it was being emitted all the time.

The immediate need was to reduce runtime noise while preserving a way to re-enable detailed traces, not to create a more complex history structure.

### Reason 2: The root issue was sequencing, not retrospective analysis

The projector failure was caused by startup order, settle timing, and stepped-mode blackout behavior. A ring buffer would have helped retain more events, but it would not have fixed the underlying hardware sequencing problems.

### Reason 3: A buffer would add complexity without operational benefit

Introducing a ring buffer at this stage would have added another subsystem to maintain, configure, and inspect. That would have made sense only if we needed bounded event history for later analysis.

We did not need that. We needed a clean on/off debug path and a reliable startup sequence.

### Reason 4: The session logs already provide durable history

The existing session log files already capture the operational record well enough for post-run review. The main gap was terminal discipline, not archival storage.

For that reason, the debug-mode helper was the right abstraction, not a ring buffer.

---

## Limitations Remaining

### 1. Some modules still contain hardcoded print statements

We removed the biggest sources of chatter, but not every module in `support_modules/` has been converted to the shared debug helper yet.

Candidates for future cleanup include:
- `support_modules/PeakForceLogger.py`
- `support_modules/SandwichRoutines.py`
- `support_modules/ExperimentalConditionsWindow.py`
- `support_modules/PatternBatchController.py`
- `support_modules/adhesion_metrics_calculator.py`

### 2. Debug mode is still module-driven, not yet fully unified across the app

The shared helper exists now, but we have not yet refactored every status source to use it. That is acceptable for the current state because the critical print path is stable.

### 3. Silent wake is still a workflow assumption

The current silent wake path is correct for our known-good projector setup, but it still depends on the same hardware and monitor arrangement that we validated during debugging.

If the projector topology changes, the startup assumptions should be revalidated.

---

## Current State

### Working behavior

- Video-pattern projection works again in stepped printing.
- Stepped motion goes dark between layers.
- The projector can be armed silently without the earlier flashing behavior.
- Default terminal output is much quieter.

### Files introduced or updated during this work

- `Prince_Segmented_VideoPattern.py`
- `tkinter_video_mode_test.py` was used as the reference baseline
- `support_modules/DebugSupport.py`
- `support_modules/libs.py`
- `support_modules/AutoHomeRoutine.py`
- `support_modules/USBCoordinator.py`
- `support_modules/motion_controller.py`

---

## Recommended Next Step

The best next cleanup step is to migrate the remaining noisy helper modules to the shared debug gate, one at a time, while leaving the stable video-pattern path alone.

That would preserve the working behavior we now have and reduce terminal clutter further without reopening the hardware sequencing problem.
