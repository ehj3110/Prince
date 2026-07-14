# RUSH GUI Changelog

All notable changes to Rush_Segmented_VideoPattern_Enhanced.py
and associated support modules are documented here.

---

## [Unreleased] July 1-14, 2026

### Summary
This sprint focused on hardware-safe thread architecture improvements,
new GUI features (Ramped Cylinder generator, projection mode toggling),
color scheme improvements, post-print logging/survey workflow, and
continuous print mode fixes.

---

### Added

#### Ramped Cylinder Window
- Added a Ramped Cylinder button to the main GUI.
- Implemented open_ramped_cylinder_window() which opens a standalone
  Toplevel dialog for generating ramped cylinder print folders.
- The window includes a Generate Folder button so users can create
  output folders without overwriting existing instruction files.

#### Projection Mode Switcher
- Added a Projection Mode panel (LabelFrame) to the main GUI.
- Implemented a Checkbutton toggling between:
  - Legacy Video Mode (HDMI) = video (default, light theme)
  - Video Pattern Mode (Newer) = video_pattern (dark theme)
- Added _on_projection_mode_change() which applies a full GUI theme swap
  (backgrounds, labels, entries, canvas) when the mode changes.
- Added _arm_dlp_video_mode() for initializing the DLP into HDMI video
  output mode (mode 0x00) with a safe startup sequence.
- Added b_disconnect_dlp / b_reconnect_dlp buttons for safely power-cycling
  the light engine mid-session.

#### Post-Print Logging Survey
- Added self._post_print_queue (queue.Queue) for thread-safe communication
  between the print thread and the main event loop.
- Added _poll_post_print_queue() recurring poller on the main thread that
  opens the survey dialog safely from the main thread only.
- Added show_post_print_dialog() and on_post_print_dialog_closed() as
  main-thread-only UI methods replacing the previous blocking wait_window()
  call from the background thread.
- Added self.post_print_logging_var (BooleanVar, default False) to toggle
  logging on/off independently from the Sensor Data panel.
- Added Enable Post-Print Logging & Survey toggle checkbox inside the
  Experimental Conditions window at the top of the layout.

#### LoggingCheckWindow_VideoPattern.py Updates
- REMOVED the Wait for Quality Check checkbox - caused blocking issues.
- RENAMED the primary action button from Close and Save to Save Log.
- ADDED a Cancel button that sets result to None and destroys window cleanly.
- Updated _on_close_request() so window X button calls _on_cancel().
- Updated window geometry to 500x390 to ensure buttons are always visible.

#### Continuous Print Mode
- Added continuous as a valid value for print_mode.
- When print_mode == continuous, the PeakForceLogger post-processing step
  is bypassed. Raw data is saved directly.

---

### Changed

#### Thread Safety - Post-Print Dialog (Critical Fix)
ROOT CAUSE: The previous implementation called
LoggingCheckWindow_VideoPattern(...).wait_window() directly inside the
finally block of print_t (the background print thread). On Windows CPython,
calling wait_window() from a non-main thread corrupts the Tkinter C-level
event state.

MANIFESTATION: GUI freezing after print completion, post-print dialog becoming
unresponsive, and most critically - the DLP light engine locking up and
requiring a hard USB reset.

FIX: The finally block now calls self._post_print_queue.put(status_to_write).
The main thread polls this queue every 500ms via _poll_post_print_queue(),
wired into the startup block before mainloop().

#### DLP Command Ordering in _enter_dark_pattern_idle()
- Fixed: power(0) was being sent before stopsequence().
- Sending power-off while a video sequence is active can cause firmware hangs
  on the DLP6500.
- Corrected sequence: stopsequence() first, then power(current=0).

#### Theme Logic Inversion
- Previously: Legacy Video Mode = Dark Theme; Video Pattern Mode = Light Theme.
- Now: Legacy Video Mode = Light Theme (default).
       Video Pattern Mode = Dark Theme (enabled by checkbox).
- This matches intended UX where the lab primary working mode uses the
  familiar light UI and switching to the newer mode is visually obvious.

#### Logging Directory Creation
- Log directories (Printing_Logs/YYYY-MM-DD/Print N/) are now created if:
  1. self.post_print_logging_var.get() == True, OR
  2. The Sensor Data panel automated logging is enabled.
- Previously, directory creation was tied exclusively to the Sensor Data
  panel's auto_log_enabled_var.

---

### Fixed
- Fixed Ramped Cylinder window missing a Generate Folder button.
- Fixed low-contrast text in Entry widgets when returning to light mode.
- Fixed button states not restoring correctly after print abort or error.
- Fixed indentation bug in the finally block instruction-file-saving section.

---

## Known Issues / Next Steps

### Color Scheme (Incomplete)
The dynamic theme system in _on_projection_mode_change() iterates over child
widgets and restyles them. Several widget types are still not updated:
- Graph/Canvas widgets inside the Sensor Data Window (a separate Toplevel
  with its own widget tree) are not covered by the main window theme change.
- ttk themed widgets ignore .configure(bg=...) because their appearance is
  controlled by the ttk style engine, not individual widget options.

NEXT STEP: Use ttk.Style() to configure a named theme (e.g., clam) and
override TFrame, TLabel, TButton, TEntry style maps dynamically on mode switch,
rather than per-widget iteration.

### Sensor Data Panel - Cross-Mode Versatility
The Sensor Data panel and automated layer logging are only meaningfully
integrated with stepped print mode. For continuous mode, layer-by-layer
trigger events are not sent to the Sensor Data panel.

NEXT STEP: Define a generic logging event bus (queue.Queue or callback list)
that the print loop posts layer-start/end events to, regardless of mode.
AutomatedLayerLogger subscribes to this bus to record data in both modes.

### Post-Print Logging - Metadata Completeness
Experimental Conditions are saved to VideoPatternPrintLogging at
start_new_print() time only. Changes made mid-print are not reflected.

NEXT STEP: Pass a snapshot of self.experimental_conditions into the survey
dialog and write it into metadata at survey-close time rather than at
print-start time.

### DLP Mode Change Safety
Switching between projection modes while the DLP is projecting can cause
firmware lockups. The UI disables the checkbox during printing, but this is
only advisory and does not prevent programmatic calls.

NEXT STEP: Add a hard guard inside _on_projection_mode_change() that checks
self.print_thread is not None and self.print_thread.is_alive() and returns
early with a status message if a print is running.

### Quality Check Gating (Removed Feature)
The Wait for Quality Check checkbox was removed from the post-print survey
because it introduced blocking behavior. The quality_check_gate flag still
exists in the codebase and _restore_dlp_button_states() still references it.

NEXT STEP: Either fully remove quality_check_gate from the codebase or
re-implement it as a non-blocking state machine: a flag that disables the
Start Print button and shows a banner until manually cleared by a new
Clear QC Gate button.
