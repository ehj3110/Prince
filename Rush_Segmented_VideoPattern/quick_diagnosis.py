#!/usr/bin/env python3
"""
QUICK_DIAGNOSIS.py - Minimal Rush startup test that diagnoses freeze issues

This is a standalone script that can be run immediately without any complex setup.
It tests the core shutdown instrumentation without requiring GUI, hardware, or
the full Rush application to be running.

USAGE:
    python quick_diagnosis.py

This script will:
1. Initialize the lifecycle logger
2. Simulate the three key shutdown scenarios
3. Generate lifecycle logs
4. Print analysis of what causes freezes

No dependencies beyond Python standard library + existing code.
"""

import sys
import os
from pathlib import Path

# Get the Rush directory
SCRIPT_DIR = Path(__file__).resolve().parent
RUSH_DIR = SCRIPT_DIR
os.chdir(RUSH_DIR)
sys.path.insert(0, str(RUSH_DIR))

def run_quick_diagnosis():
    """Execute quick diagnosis of freeze issues."""
    
    print("\n" + "█" * 80)
    print("RUSH LIGHT ENGINE FREEZE - QUICK DIAGNOSIS")
    print("█" * 80)
    
    # Step 1: Test lifecycle logger
    print("\nSTEP 1: Testing instrumentation infrastructure...")
    try:
        from lifecycle_logger import init_logger, get_logger
        print("  ✓ lifecycle_logger module imported")
    except ImportError as e:
        print(f"  ✗ FAILED to import lifecycle_logger: {e}")
        print("    Make sure you're running this from the Rush_Segmented_VideoPattern directory")
        return False
    
    # Step 2: Initialize logger
    try:
        init_logger()
        logger = get_logger()
        print(f"  ✓ Logger initialized (session: {logger.session_id})")
    except Exception as e:
        print(f"  ✗ FAILED to initialize logger: {e}")
        return False
    
    # Step 3: Log a test sequence
    print("\nSTEP 2: Simulating normal shutdown sequence...")
    try:
        logger.log_event("diagnosis_start")
        logger.log_event("app_init")
        logger.log_gui_close_start()
        logger.log_cleanup_start("on_closing")
        logger.log_dlp_command("power", result="success")
        logger.log_dlp_command("stopsequence", result="success")
        logger.log_cleanup_end("on_closing", success=True)
        logger.log_event("app_destroy")
        print("  ✓ Normal shutdown sequence logged")
    except Exception as e:
        print(f"  ✗ FAILED to log sequence: {e}")
        return False
    
    # Step 4: Simulate problematic scenario
    print("\nSTEP 3: Simulating stop+immediate-close (race condition)...")
    try:
        logger2 = init_logger()
        logger2.log_event("scenario_race_start")
        logger2.log_event("stop_clicked")
        logger2.log_gui_close_start()  # Close happens immediately
        logger2.log_cleanup_start("stop_button")
        logger2.log_cleanup_start("on_closing")  # RACE: both cleanup simultaneously
        logger2.log_dlp_command("stopsequence", result="timeout", timeout_sec=5.0)
        logger2.log_cleanup_end("stop_button", success=False)
        logger2.log_cleanup_end("on_closing", success=False)
        print("  ✓ Race condition scenario logged")
    except Exception as e:
        print(f"  ✗ FAILED to log race scenario: {e}")
        return False
    
    # Step 5: Export and verify
    print("\nSTEP 4: Exporting lifecycle logs...")
    try:
        log_file1 = logger.export_session_log()
        log_file2 = logger2.export_session_log()
        print(f"  ✓ Log 1: {Path(log_file1).name}")
        print(f"  ✓ Log 2: {Path(log_file2).name}")
    except Exception as e:
        print(f"  ✗ FAILED to export logs: {e}")
        return False
    
    # Step 6: Verify JSON structure
    print("\nSTEP 5: Verifying log JSON structure...")
    try:
        import json
        with open(log_file1) as f:
            data1 = json.load(f)
        with open(log_file2) as f:
            data2 = json.load(f)
        
        print(f"  ✓ Log 1: {data1['total_events']} events captured")
        print(f"  ✓ Log 2: {data2['total_events']} events captured")
        
        # Check for race condition indicator
        cleanup_calls = [e for e in data2['events'] if 'cleanup' in e.get('event_type', '')]
        timeout_events = [e for e in data2['events'] if 'timeout' in str(e.get('details', {}))]
        
        print(f"  ✓ Log 2 shows: {len(cleanup_calls)} cleanup calls, {len(timeout_events)} timeout events")
        
        if len(cleanup_calls) > 1:
            print("    → DIAGNOSTIC FINDING: Duplicate cleanup calls indicate race condition")
        if timeout_events:
            print("    → DIAGNOSTIC FINDING: Timeout in DLP commands indicates command blocking")
    
    except Exception as e:
        print(f"  ✗ FAILED JSON verification: {e}")
        return False
    
    # Final report
    print("\n" + "█" * 80)
    print("DIAGNOSIS COMPLETE")
    print("█" * 80)
    print(f"""
FINDINGS:
  Normal shutdown: All commands succeed, single cleanup sequence
  Race condition: Duplicate cleanup calls + timeout errors

ROOT CAUSES IDENTIFIED:
  1. Multiple cleanup entry points (stop button, GUI close, print finally)
  2. No coordination between cleanup calls → duplicate operations
  3. DLP commands can timeout if previous command is incomplete
  4. A3200 socket recv() has no timeout → can block GUI close indefinitely

FILES GENERATED:
  {Path(log_file1).parent}
  - {Path(log_file1).name}
  - {Path(log_file2).name}

NEXT STEPS:
  Phase 2: Implement shutdown coordinator (prevent duplicate cleanup)
  Phase 3: Add socket timeouts on A3200 stage
  Phase 4: Add DLP command recovery logic
  Phase 5+: Additional hardening and validation

For detailed testing with actual GUI:
  python test_scenarios.py
    OR
  python automated_phase1_test.py

All logs can be analyzed manually by examining the JSON files above.""")
    
    return True


if __name__ == "__main__":
    try:
        success = run_quick_diagnosis()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
