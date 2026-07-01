# Silent Video Pattern Mode Breakthrough and Integration Roadmap

## Status Summary
The standalone `tkinter_video_mode_test.py` has validated a stable "Silent Wakeup" into Video Pattern Mode (`0x02`) over a 30 Hz HDMI link, using:
- dark HDMI handshake (`power=0` while receiver sync settles)
- pattern-mode pivot after stabilization
- infinite LUT repeat
- 30 Hz exposure (`33333` us)
- delayed LED reveal after `startsequence()`

This removes the cold-boot white-flash behavior and avoids dependence on manual GUI resets.

---

## Part 1: Technical Summary of the Validated Silent Pattern Mode Sequence

## 1) The Handshake (Dark Synchronization)
In `tkinter_video_mode_test.py`, `_arm_hardware_worker` performs:
1. `stopsequence()`
2. `power(current=0)`
3. `changemode(0x00)`
4. `hdmi()`
5. `time.sleep(1.5)`

Why this matters:
- `power(0)` guarantees no optical output while receiver state changes happen.
- `hdmi()` selects the expected external video source path.
- The `1.5 s` wait gives Windows + GPU + receiver timing (including IT6535 path behavior) time to settle while dark.
- This is the key anti-flash move: receiver lock is established before any light is emitted.

## 2) Pattern Logic (Mode + LUT + Timing)
After handshake settles:
1. `changemode(0x02)`
2. `configurelut(1, 0xFFFFFFFF)`
3. `definepattern(... bitdepth=8, color="100", exposure=33333, ...)`

Semantics:
- `0x02`: Video Pattern Mode.
- `configurelut(1, 0xFFFFFFFF)`: one entry, infinite repeat.
- `exposure=33333`: 33.333 ms = 30 Hz frame period.
- `color="100"`: Blue/UV channel mask used by this validated workflow.

Operational effect:
- Pattern engine continuously replays one 8-bit pattern slot at display-period timing.
- Tkinter screen updates are mapped through the video path while pattern engine remains armed.

## 3) The Reveal (Mirror-First, Light-Second)
After LUT/programming:
1. `startsequence()`
2. `time.sleep(0.5)`
3. `power(current=50)`

Why this ordering is stable:
- `startsequence()` lets control logic and mirror timing settle first.
- `0.5 s` delay prevents immediate optical emission during transient state.
- LED power turns on only after the internal state machine is already running.

This is the second anti-flash move: optics are enabled only after control state is stable.

---

## Part 2: 4-Step Integration Roadmap for `Prince_Segmented.py`

## Step 1: Initialization Refactor (Replace Startup and Print-Start Mode Ordering)
Target locations to refactor:
- Constructor startup DLP init around `Prince_Segmented.py` lines near:
  - `self.controller.stopsequence()`
  - `self.controller.power(current=0)`
  - `self.controller.changemode(3)`
  - `self.controller.hdmi()`
- Print start setup inside `print_t(...)` around lines near:
  - `self.controller.power(current=0)`
  - `self.controller.changemode(0)`
  - `time.sleep(2.0)`
  - `self.controller.power(current=dlp_power)`

Refactor goal:
- Replace these split/legacy transitions with a single reusable method implementing the validated silent sequence:
  - safety reset -> dark HDMI handshake -> wait -> `changemode(0x02)` -> infinite LUT @ 30 Hz -> `startsequence()` -> reveal LED.

Recommended implementation:
- Add one method (for example `_enter_silent_pattern_mode(target_power, exposure_us)`), invoked from print-start code path.
- Keep all DLP USB operations inside `USBCoordinator.dlp_operation(...)`.

## Step 2: State Management (Render Black Before USB Arm Hits)
Problem to avoid:
- Mode/receiver commands executed before display surface is black and composited can reintroduce flashes.

Current Prince rendering path uses OpenCV (`cv2.imshow`), not Tkinter in print loop. Practical equivalent of `root.update()` is:
- draw black frame: `cv2.imshow(self.window_name, self.black_image)`
- flush UI/event loop: `cv2.waitKey(1)`

Integration rule:
1. Create/move fullscreen render window.
2. Show black frame.
3. Force one UI pump (`cv2.waitKey(1)`).
4. Only then run silent USB arm sequence.

If/when a Tkinter rendering branch is added in Prince:
- do `widget.configure(...black...)` + `root.update_idletasks()` + `root.update()` before USB arm.

## Step 3: Parameter Synchronization (Map Print Settings into Pattern/LUT Strategy)
Current Prince uses per-layer power changes and exposure values from print instructions.

For Pattern Mode integration, define a policy:
- Base pattern timing:
  - default `exposure_us = 33333` for 30 Hz links (or dynamic from measured refresh).
- LED power:
  - map existing per-layer `dlp_power` list to `power(current=...)` updates.
- Bit depth and color mask:
  - `bitdepth=8`, `color="100"` from validated test baseline.

Two viable integration models:
1. Fixed-pattern-engine timing, variable LED power per layer.
2. Update `definepattern(... exposure=...)` if per-layer exposure timing must vary.

Start with model (1) for stability, then expand if needed.

## Step 4: Safety Teardown (Always Return to Clean Next-Run State)
Target teardown paths in `Prince_Segmented.py`:
- `print_t(...)` `finally` block
- `disconnect_dlp(...)`
- `reconnect_dlp(...)`
- any abort/cancel path that can stop printing early

Required safety sequence on all exits:
1. `stopsequence()`
2. `power(current=0)`
3. set safe mode (`changemode(0x00)` or chosen idle mode policy)
4. force/render black before window destroy (`cv2.imshow(...black...)`, `cv2.waitKey(1)`).

Important note:
- Do not allow one exit path to skip teardown, or next-run startup will inherit stale pattern state and become intermittent.

---

## Recommended Implementation Order
1. Add reusable silent arm method + reusable safe teardown method in Prince.
2. Switch `print_t(...)` startup to call silent arm method after black-frame flush.
3. Switch all exit paths to shared teardown method.
4. Validate with two consecutive fresh runs (no manual DLP GUI intervention), then 10-run soak test.

---

## Validation Checklist for Integration
- Cold boot printer + projector, run print once: no flash.
- Immediate second run: no white lock, no blank output.
- Layer images still update correctly in render window.
- Abort mid-print leaves projector dark and next run starts clean.
- USB coordinator logs show serialized DLP operations without overlap.

---

## Final Note
The breakthrough is not a single command change; it is an order-of-operations guarantee:
- dark handshake first,
- pattern state second,
- light last,
- deterministic teardown always.

Porting should preserve this ordering exactly across all start/stop code paths.
