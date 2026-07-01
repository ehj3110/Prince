================================================================================
RUSH LIGHT ENGINE FREEZE - PHASE 1 INSTRUMENTATION
================================================================================

STATUS: ✓ COMPLETE AND READY FOR TESTING

================================================================================
WHAT IS THIS?
================================================================================

Phase 1 is a diagnostic framework to capture detailed evidence of why the light
engine freezes and requires power cycling after shutdown on the other computer.

All code is instrumented and ready. You just need to run the test scenarios.

================================================================================
QUICK START (ONE COMMAND)
================================================================================

cd Rush_Segmented_VideoPattern
python test_scenarios.py

That's it. The script will guide you through everything.

================================================================================
WHAT HAPPENS
================================================================================

1. You run 3 different shutdown scenarios
2. Each scenario logs detailed events (DLP commands, stage operations, etc.)
3. Logs are automatically analyzed and reported
4. Results will show what's happening (or hanging) during shutdown

Expected time: 15-20 minutes for all 3 scenarios

================================================================================
WHERE TO FIND DOCUMENTATION
================================================================================

START HERE:
  - GO.md                          ← Quick start (2 min read)
  - NEXT_STEPS.md                  ← What to do next (3 min read)

DETAILED GUIDES:
  - QUICKSTART_PHASE1.md           ← Step-by-step how-to (5 min read)
  - PHASE1_README.md               ← Complete overview (5 min read)

TECHNICAL DETAILS:
  - PHASE1_IMPLEMENTATION.md       ← What was built (10 min read)
  - PHASE1_VALIDATION_CHECKLIST.md ← Quality proof (5 min read)
  - DOCUMENTATION_INDEX.md         ← Master index (reference)

MASTER INDEX:
  - This file (you're reading it)

================================================================================
TEST SCENARIOS
================================================================================

SCENARIO 1: NORMAL_COMPLETE
  - Let a print finish naturally
  - Close the app normally
  - Expected: clean shutdown, no freeze

SCENARIO 2: STOP_WITH_DELAY
  - Click "Stop" button
  - Wait 5 seconds
  - Close the app
  - Expected: may show transition between stop and close

SCENARIO 3: STOP_IMMEDIATE
  - Click "Stop" button
  - Immediately close the app
  - Expected: may trigger race conditions

================================================================================
WHAT GETS LOGGED
================================================================================

For each scenario, a JSON file records:
  ✓ Every DLP command (power, stopsequence, changemode, standby)
  ✓ Stage operations (stop, disconnect) with exceptions
  ✓ Print thread lifecycle (join success/timeout)
  ✓ GUI close sequence
  ✓ Cleanup call order and who initiated it
  ✓ All timeouts and exceptions
  ✓ Monotonic timestamps and thread context

Files saved to: Rush_Segmented_VideoPattern/logs/

================================================================================
AFTER YOU RUN PHASE 1
================================================================================

The test scenarios will:
  1. Show step-by-step instructions for each scenario
  2. Auto-analyze the logs after each run
  3. Print detailed event timeline and findings
  4. Save JSON files for later review

Look for:
  ✓ SUCCESS: Single cleanup sequence, all operations succeed, no timeouts
  ✗ PROBLEM: Timeouts, exceptions, multiple cleanup calls, thread join failures

================================================================================
NEXT PHASE
================================================================================

After you provide Phase 1 evidence (logs or analysis output):
  → Phase 2: Root cause diagnosis
  → Phases 3-7: Implementation of targeted fixes

The fixes will address:
  - Duplicate cleanup calls
  - Socket timeouts on A3200 stage
  - Print thread join failures
  - DLP recovery on startup

================================================================================
QUESTIONS?
================================================================================

Before running, read:
  - GO.md (2 min) - Quick start
  - QUICKSTART_PHASE1.md (5 min) - How-to guide

If something goes wrong:
  - Check PHASE1_README.md FAQ section
  - Verify Python 3.8+ is installed

================================================================================
IMMEDIATE NEXT ACTION
================================================================================

Run this command:

  cd Rush_Segmented_VideoPattern
  python test_scenarios.py

Follow the prompts. Takes 15-20 minutes.

Share the analysis output or the JSON files from logs/ directory.

================================================================================
That's all you need to know. START WITH: GO.md
================================================================================
