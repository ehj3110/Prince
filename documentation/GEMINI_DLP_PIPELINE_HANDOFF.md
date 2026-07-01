# Gemini Handoff: DLP Pipeline Architecture and Operating Notes

## Purpose
This document summarizes how the printer software and DLP control pipeline currently work, with emphasis on:
- DLP mode transitions and timing
- how images are shown and at what rate
- what has been validated in hardware
- what is still fragile
- what operational rules must be followed to avoid projector aborts or blank output

This handoff is intentionally verbose so Gemini can reason about the system without rediscovering known constraints.

---

## High-Level System Model
The pipeline has three interacting layers:

1. Render layer (Windows + GPU + monitor link)
- Runs through Pyglet or OpenCV fullscreen windows.
- Responsible for producing a stable 60 Hz display signal over DP/HDMI.
- If this signal drops even briefly at sensitive moments, the DLPC900 can abort or fall back to blank output.

2. DLP control layer (DLPC900 over USB)
- Uses `support_modules/pycrafter9000.py` for command transport.
- Uses `support_modules/USBCoordinator.py` to serialize USB operations and avoid bus conflicts.
- Commands include mode changes, sequence start/stop, LUT/pattern setup, and LED power.

3. Frame production layer (host memory + storage)
- For stress tests: synthetic frames from preallocated pools.
- For real prints: strict streaming from preconverted `.npy` slices (not full preload).
- Uses queue buffering to cap memory and decouple producer/consumer rates.

The key engineering lesson is that these layers are coupled by timing. USB commands are "slow" relative to 60 Hz rendering, and blocking the render loop can destabilize the display signal seen by DLPC900.

---

## Core Code Paths in This Repo

### Production baseline
- `Prince_Segmented.py`

This is the lab baseline for real print workflow. Historically, this script has been treated as the canonical behavior reference when other modules disagreed.

### Pipeline experimentation and validation
- `ring_buffer_graphics_test.py`
- `barebones_dlp_test.py`
- `slice_converter.py`

These scripts were used to isolate and validate:
- rendering throughput
- memory behavior
- mode sequencing behavior
- warmup/cooldown race conditions

### Low-level DLP wrapper and arbitration
- `support_modules/pycrafter9000.py`
- `support_modules/USBCoordinator.py`

---

## DLP Modes and Practical Usage

Important: there have been conflicting interpretations across scripts and older notes. What matters is tested behavior in this repo and hardware session logs.

Observed/used mode values:
- `0x00`: standard video receiver mode (desktop/video path)
- `0x02`: used in recent pattern-mode experiments in test harnesses
- `3` (decimal): used in `Prince_Segmented.py` as safe/idle HDMI-video state in several flows

Implication:
- There is no single universal mapping that has been perfectly stable across every script history.
- The mode sequence must be treated as part of a timed state machine, not a single command.

---

## Image Display Strategy and Target Rate

### Display rate target
- Stable 60 Hz VSYNC-locked render loop for exposure synchronization.
- Earlier benchmarking with VSYNC disabled confirmed host can overproduce frames, but production logic now prioritizes stable synchronization over raw FPS.

### Render content during critical phases
- Warmup: render black to stabilize compositor/GPU/display link.
- Armed exposure phase: currently white in `barebones_dlp_test.py` to force mirror ON state across the panel.
- Cooldown/teardown: render black continuously while DLP transitions back to safe state.

### Why this matters
Any render-loop stall can break the observed display lock quality and trigger DLP instability during mode transitions.

---

## Throughput and Memory Architecture

## What was validated
- Queue-based producer/consumer architecture works reliably.
- `queue.Queue(maxsize=300)` provides a hard memory bound.
- Preallocation removes GC spikes in synthetic mode.

## Strict streaming rule for real slices
Do not preload all print slices into RAM.

For real print data:
- Convert PNG slices to `.npy` ahead of time using `slice_converter.py`.
- Stream one `.npy` slice at a time from SSD.
- Convert each slice to RGB buffer and enqueue.
- Block on queue put when full.

Reason:
- Full preload can exceed RAM for high-layer-count jobs.
- Queue-limited streaming keeps memory bounded and predictable.

---

## Arming/Teardown State Machine Constraints

## Critical rule
Never block `on_draw` with USB calls.

USB operations can take around 1 second and must run in background threads, while `on_draw` keeps rendering every frame.

### Warmup phase
- Wait a fixed frame count before arming (recent tests used 120 frames = about 2 seconds at 60 Hz).
- Keep rendering black during warmup.

### Async arming phase
- Spawn daemon thread.
- Run USB commands inside `usb_coordinator.dlp_operation(...)`.
- Keep rendering from main thread while arming thread runs.

### Hold phase
- After armed flag is set, hold exposure render for fixed frame duration (example: 300 frames, around 5 seconds).

### Teardown phase
- Run teardown commands in async thread.
- Then hold black for a full cooldown interval while window remains alive.
- Exit app only after cooldown completes.

---

## Receiver-Specific Rules (Very Important)

The projector link path (DisplayPort vs HDMI) changes what is safe.

If the projector is on DisplayPort:
- Do not force HDMI receiver switching calls in the test harness.
- A receiver switch at the wrong time can black out projection.

If the workflow depends on HDMI receiver mode:
- You must explicitly command and then allow settle time.
- Changing receiver selection during unstable render timing is high risk.

Bottom line:
- Receiver selection must match physical cable path and firmware boot state.
- Do not blindly copy `hdmi()` usage between scripts without verifying physical link assumptions.

---

## Pattern and LED Channel Notes

Pattern setup in tests uses:
- `configurelut(1, 0)` (single entry, repeat)
- `definepattern(..., bitdepth=8, color=...)`
- `startsequence()`
- `power(current=100)`

Color mask semantics have caused confusion in prior iterations.
Current test harness update sets blue exposure mask as:
- `color="100"`

Interpret this as a hardware-specific convention validated by current testing assumptions. If behavior disagrees on another projector firmware build, re-validate channel mapping with a controlled color-only test.

---

## Why the Pipeline Can Fail Even When Commands Are Correct

Common failure causes are timing/race related, not syntax related:

1. Blocking `on_draw`
- USB arming/teardown done inline in draw callback.
- Result: dropped VSYNC continuity and unstable receiver lock.

2. Premature arming
- DLP mode transitions triggered before window/display path is fully settled.

3. Premature teardown exit
- Window destroyed immediately after USB teardown commands.
- DLP still transitioning and loses clean input lock.

4. Receiver mismatch
- DisplayPort-connected system receives HDMI receiver commands.

5. Misinterpreted channel mask
- Pattern channel mask not aligned with expected LED/optical channel.

---

## Current Test Harness Behavior Snapshot

### `ring_buffer_graphics_test.py`
- Includes warmup, async arming, strict streaming queue model, poison-pill end-of-print signal, and cooldown logic.
- Supports synthetic fallback and real `.npy` streaming mode.
- Designed to preserve render-loop responsiveness while USB commands execute off-thread.

### `barebones_dlp_test.py`
- Minimal state machine for DLP bring-up validation.
- Warmup black, async arm, fixed hold phase, async teardown, cooldown black.
- Useful for isolating DLP timing and mode behavior from the larger print pipeline.

---

## Practical Operating Sequence (Recommended)

1. Confirm environment and dependencies
- Project-local Python interpreter only.
- USB access and wrapper import success.

2. Confirm display routing assumptions
- Physical cable path (DP vs HDMI).
- Avoid receiver-switch commands that conflict with physical link.

3. Start fullscreen render loop with VSYNC
- Secondary display if available.
- Keep draw callback lightweight and non-blocking.

4. Warmup
- Render black for fixed frame budget (for example 120 frames).

5. Async arm
- In background thread with `USBCoordinator` lock.
- Apply mode/pattern/power sequence.

6. Exposure hold
- Render intended exposure content for fixed frame count.

7. Async teardown
- Stop sequence, LED off, mode-safe return.

8. Cooldown while window remains active
- Continue black rendering for full cooldown period.

9. Exit
- Only after cooldown timer expires.

---

## Recommendations for Gemini When Proposing Changes

- Treat render loop continuity as a first-class hardware requirement.
- Never place long USB calls directly in `on_draw`.
- Preserve strict streaming memory bounds for real print data.
- Keep warmup and cooldown explicit and measurable (frame/time based).
- Keep receiver-mode assumptions explicit in code comments and logs.
- When changing mode/channel settings, include a validation plan, not just code edits.

---

## Appendix: Key Files to Inspect First

- `Prince_Segmented.py`
- `ring_buffer_graphics_test.py`
- `barebones_dlp_test.py`
- `slice_converter.py`
- `support_modules/pycrafter9000.py`
- `support_modules/USBCoordinator.py`
