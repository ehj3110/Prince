# START HERE: Phase 1 Testing Instructions

## One Command to Run Everything

```bash
cd C:\Users\cheng sun\BoyuanSun\Prince_CurrentWorkingVersion\Rush_Segmented_VideoPattern
python test_scenarios.py
```

## What Happens Next

The script will:
1. Prompt you to run **Scenario 1: NORMAL_COMPLETE**
   - You launch Rush GUI, run a print, close normally
   - Takes ~5 minutes
   - Script auto-analyzes logs and shows results
   
2. Prompt you to run **Scenario 2: STOP_WITH_DELAY**
   - You launch Rush GUI, click Stop, wait 5 seconds, close
   - Takes ~5 minutes
   - Script auto-analyzes logs and shows results

3. Prompt you to run **Scenario 3: STOP_IMMEDIATE**  
   - You launch Rush GUI, click Stop, immediately close
   - Takes ~5 minutes
   - Script auto-analyzes logs and shows results

## Expected Output

For each scenario, you'll see:
- Clear step-by-step instructions
- What to expect vs. what problems to watch for
- Automatic log analysis with:
  - Event timeline (in chronological order)
  - Any exceptions or timeouts
  - Thread join results
  - DLP/stage operation status
  - Summary of findings

## What Gets Saved

Three JSON files in `logs/` directory:
```
Rush_Segmented_VideoPattern/logs/
├── lifecycle_20260415_120000_SESSION1.json
├── lifecycle_20260415_120100_SESSION2.json
└── lifecycle_20260415_120200_SESSION3.json
```

Each JSON contains complete event history with:
- Timestamp (ISO and elapsed time)
- Thread ID and name
- Event type (gui_close, dlp_power, stage_disconnect, etc.)
- Details (success/failure, exceptions, operation outcomes)

## Troubleshooting

**Q: Script won't run?**
- Make sure you're in `Rush_Segmented_VideoPattern` directory
- Python version: `python --version` (need 3.8+)

**Q: GUI freezes during test?**
- That's the bug we're looking for! Close the window and continue.
- The freeze itself is captured in the log.

**Q: "No images loaded" warning?**
- Fine - test_scenarios.py will guide you through what to do
- Use demo data or small test image

**Q: Can't find logs?**
- Check: `dir logs\`
- Files start with `lifecycle_` and end with `.json`

## Next Steps After Running

1. All 3 scenarios complete → You have 3 JSON files
2. Copy those files or share the console output
3. I analyze the logs to find root cause
4. Phase 2 implementation of targeted fixes begins

## Time Estimate

- **Total for all 3 scenarios:** 15-20 minutes
- **Per scenario:** ~5-6 minutes (mostly waiting for GUI operations)

## Questions?

Before running, check these docs:
- **Quick overview:** `PHASE1_README.md`
- **Detailed how-to:** `QUICKSTART_PHASE1.md`
- **Technical details:** `PHASE1_IMPLEMENTATION.md`
- **Quality assurance:** `PHASE1_VALIDATION_CHECKLIST.md`
- **File index:** `DOCUMENTATION_INDEX.md`

---

**Ready?** Run this:

```bash
cd Rush_Segmented_VideoPattern && python test_scenarios.py
```
