# Rush Hardware Checklist

This checklist is specific to the Rush_Segmented_VideoPattern setup (A3200 stage + DLP + Phidget force gauge).

## Automated Runner

Run from the repository root:

```powershell
Set-Location "c:\Users\User\Documents\Boyuan Sun\CLIP1&2&etc\Rush"
.\Rush_Segmented_VideoPattern\.venv\Scripts\python .\Prince_GitHub_Tests\run_rush_hardware_checklist.py
```

Safe defaults:
- Stage check reads position only (no motion)
- DLP check sends safe-idle sequence (stop, power 0, mode 0x03)
- Phidget check attaches then closes cleanly

Useful options:

```powershell
# Planning/manual checklist only
.\Rush_Segmented_VideoPattern\.venv\Scripts\python .\Prince_GitHub_Tests\run_rush_hardware_checklist.py --plan-only

# Enable tiny non-destructive stage motion probe (+50um then return)
.\Rush_Segmented_VideoPattern\.venv\Scripts\python .\Prince_GitHub_Tests\run_rush_hardware_checklist.py --enable-motion

# Skip a subsystem
.\Rush_Segmented_VideoPattern\.venv\Scripts\python .\Prince_GitHub_Tests\run_rush_hardware_checklist.py --skip-phidget

# Write JSON report
.\Rush_Segmented_VideoPattern\.venv\Scripts\python .\Prince_GitHub_Tests\run_rush_hardware_checklist.py --json-out .\Prince_GitHub_Tests\rush_check_report.json
```

## Manual GUI Checklist

1. Launch Rush app and verify status reaches System Ready.
2. Open Sensor Panel (Logging), verify force readout updates, then close panel.
3. Open Image Modification and load a test folder.
4. Use stage controls for a tiny jog up/down and confirm position updates.
5. Run DLP dark-idle then arm workflow through normal UI flow.
6. Close app and verify safe shutdown (DLP power off, stage disconnected).

## Expected Outcome

- All automated checks return PASS.
- Manual UI checks complete without uncaught exceptions.
- Session logs are created under Rush_Segmented_VideoPattern/SessionLogs.

## Sensor Panel Hardening (April 2026)

The sensor panel was hardened to reduce freeze risk during long runs.

### What Changed

- Moved stage position polling off the Tk main thread into a background polling thread.
- Kept UI position updates on a timed loop, but now the UI reads a cached latest position.
- Added stronger point decimation for older data so recent data remains detailed while redraw cost stays bounded.
- Reduced full autoscale frequency to lower repeated relim/autoscale overhead.
- Added a live performance label in the sensor panel showing queue depth and render-loop metrics.

### Why This Helps

- Prevents hardware I/O calls from blocking the UI event loop.
- Lowers redraw pressure when data volume grows over time.
- Keeps queue growth visible so bottlenecks can be spotted quickly.

### Perf Label Guide

The sensor panel now shows a status line like:

`Perf: q=... proc=... render=... loop=...ms fps=...`

- `q`: current queued points waiting for UI processing.
- `proc`: points consumed this update cycle.
- `render`: points sent to the plotting lines after decimation.
- `loop`: wall time spent in one update loop.
- `fps`: effective update cycles per second.

Healthy behavior over time:

- `q` should not grow without bound.
- `loop` should stay relatively stable.
- `fps` should stay non-zero and not collapse for prolonged periods.

### Recommended Runtime Check

1. Start live readout and leave the sensor panel open for at least 10 minutes.
2. Observe `Perf` values while idle and while moving stage.
3. Confirm no callback exceptions are printed.
4. Confirm UI remains interactive (buttons/responding) while data updates.

If `q` climbs continuously for more than about 30 to 60 seconds, reduce sampling rate or increase decimation aggressiveness.
