# Phase 1 Quick Start: Running the Lifecycle Tests

## What to do now

You have complete instrumentation ready. To collect evidence of the light engine freeze, run the interactive test scenario guide:

```bash
cd Rush_Segmented_VideoPattern
python test_scenarios.py
```

## What happens

The script will:
1. Prompt you to run **3 scenarios** (each takes 2-3 minutes)
2. Guide you through each scenario step-by-step
3. Automatically analyze logs after each run
4. Show you which operations succeed/fail/timeout

## Expected scenarios

### Scenario 1: NORMAL_COMPLETE
- Let a print run to completion
- Close the GUI normally
- **Expected:** Clean shutdown, no exceptions

### Scenario 2: STOP_WITH_DELAY  
- Start a print, click "Stop", wait 5 seconds
- Then close the GUI
- **Expected:** Should show how stop-sequence transitions to close

### Scenario 3: STOP_IMMEDIATE
- Start a print, click "Stop", immediately close GUI
- **Expected:** May reveal race conditions or timeouts

## What gets logged

For each scenario, a lifecycle log is saved to:
```
Rush_Segmented_VideoPattern/logs/lifecycle_YYYYMMDD_HHMMSS_SESSIONID.json
```

The logs capture:
- ✓ Every DLP command (power, stopsequence, changemode, standby)
- ✓ Stage operations (stop, disconnect) with exceptions
- ✓ Print thread lifecycle (join success/failure)
- ✓ GUI close sequence timing
- ✓ Cleanup call order and who initiated each one
- ✓ All exceptions with stack context

## How to interpret results

After running all 3 scenarios, look for:

### Problem indicators:
1. **Timeout errors** → A3200 socket or DLP command hanging
2. **duplicate_cleanup_detected** → Same cleanup called multiple times
3. **print_thread_join_result: success=false** → Thread didn't stop gracefully
4. **callback_skipped** → GUI callback tried to fire after window closed
5. **Exception in dlp_* or stage_*  operations** → Hardware command failed

### Success indicators:
- No timeout errors
- Single cleanup_dlp_start → single cleanup_dlp_end
- print_thread_join_result: success=true
- All DLP operations result="success"
- All stage operations result="success"

## After you run Phase 1

1. Save all the lifecycle JSON files
2. Note which scenario is problematic (or report if all pass)
3. Share the analysis output or the JSON files
4. Implementation of Phase 2 will fix the root causes shown in logs

## Example: What a problematic log might show

```
Event timeline:
1. gui_close_start (user clicked close button)
2. print_thread_join_attempt (timeout_sec=5.0)
3. stage_disconnect_start
4. stage_disconnect → EXCEPTION: TimeoutError (A3200 socket recv timed out)
5. cleanup_dlp_start (called from on_closing)
6. dlp_power → exception: device communication lost
7. print_thread_join_result (success=false) ← PROBLEM: thread still running!
8. callback_skipped (reason: gui_closed) ← Thread tried GUI callback after close

CONCLUSION: A3200 socket hangs, preventing print thread from joining,
which blocks DLP cleanup, which leaves hardware in bad state.
```

## Troubleshooting

**"No logs generated?"**
- Make sure the app closes completely (check no Python processes running)
- Check that `logs/` directory exists: `ls Rush_Segmented_VideoPattern/logs/`

**"Test scenarios script won't run?"**
- Ensure you're in the right directory: `cd Rush_Segmented_VideoPattern`
- Python version check: `python --version` (need 3.8+)

**"Can't load any images for print?"**
- Use test_scenarios.py in interactive mode, it provides guidance
- Or manually create test pattern directory

## Next steps after Phase 1

Once you run scenarios and identify the hang:
1. Share the lifecycle logs or the analysis output
2. Phase 2 implementation will add:
   - Shutdown coordinator to prevent duplicate calls
   - Socket timeout on A3200
   - DLP recovery startup sequence
   - Forced print thread join before final cleanup

---

**Ready?** Run: `python test_scenarios.py`

This is the instrumentation-first approach: **understand the problem before fixing it**.
