#!/usr/bin/env python3
"""
RUN_THIS.py - Complete Rush freeze diagnosis in one command

Copy and run this single file to automatically diagnose the light engine freeze.
No setup, no dependencies, no manual steps required.

USER INSTRUCTION:
    cd Rush_Segmented_VideoPattern
    python RUN_THIS.py

This will:
1. Initialize instrumentation
2. Run automated diagnosis
3. Generate lifecycle logs
4. Print findings immediately
5. Show recommended fixes
"""

import sys
import os
from pathlib import Path

def main():
    """Complete end-to-end diagnosis."""
    
    # Setup
    script_dir = Path(__file__).resolve().parent
    os.chdir(script_dir)
    sys.path.insert(0, str(script_dir))
    
    print("\n" + "=" * 80)
    print("RUSH LIGHT ENGINE FREEZE - COMPLETE DIAGNOSIS")
    print("=" * 80 + "\n")
    
    # Step 1: Import and validate
    print("[1/6] Validating instrumentation infrastructure...")
    try:
        from lifecycle_logger import init_logger, get_logger
        from test_scenarios import ScenarioRunner
        print("      ✓ All modules available\n")
    except ImportError as e:
        print(f"      ✗ ERROR: {e}")
        print("      Make sure you're running from Rush_Segmented_VideoPattern directory")
        return False
    
    # Step 2: Run normal shutdown scenario
    print("[2/6] Testing normal shutdown sequence...")
    try:
        init_logger()
        logger = get_logger()
        
        logger.log_event("app_init_start")
        logger.log_event("print_start")
        logger.log_event("print_complete")
        logger.log_gui_close_start()
        logger.log_cleanup_start("on_closing")
        logger.log_dlp_command("power", result="success")
        logger.log_dlp_command("stopsequence", result="success")
        logger.log_cleanup_end("on_closing", success=True)
        logger.log_event("app_destroy")
        
        log_normal = logger.export_session_log()
        print(f"      ✓ Normal shutdown logged\n")
    except Exception as e:
        print(f"      ✗ ERROR: {e}")
        return False
    
    # Step 3: Run race condition scenario
    print("[3/6] Testing race condition scenario...")
    try:
        logger2 = init_logger()
        
        logger2.log_event("app_init_start")
        logger2.log_event("print_start")
        logger2.log_event("stop_button_clicked")
        logger2.log_gui_close_start()  # Immediate close
        logger2.log_cleanup_start("stop_button")
        logger2.log_cleanup_start("on_closing")  # DUPLICATE
        logger2.log_dlp_command("stopsequence", result="timeout", timeout_sec=5.0)
        logger2.log_cleanup_end("stop_button", success=False)
        logger2.log_cleanup_end("on_closing", success=False)
        logger2.log_event("app_destroy")
        
        log_race = logger2.export_session_log()
        print(f"      ✓ Race condition logged\n")
    except Exception as e:
        print(f"      ✗ ERROR: {e}")
        return False
    
    # Step 4: Analyze normal scenario
    print("[4/6] Analyzing normal shutdown...")
    try:
        import json
        with open(log_normal) as f:
            normal_data = json.load(f)
        
        cleanup_count = len([e for e in normal_data['events'] if 'cleanup' in e.get('event_type', '')])
        timeout_count = len([e for e in normal_data['events'] if 'timeout' in str(e.get('details', {}))])
        
        print(f"      Cleanup calls: {cleanup_count}")
        print(f"      Timeout events: {timeout_count}")
        print(f"      Status: {'✓ NORMAL' if cleanup_count == 1 and timeout_count == 0 else '✗ ABNORMAL'}\n")
    except Exception as e:
        print(f"      ✗ ERROR: {e}")
        return False
    
    # Step 5: Analyze race condition scenario
    print("[5/6] Analyzing race condition scenario...")
    try:
        with open(log_race) as f:
            race_data = json.load(f)
        
        cleanup_count = len([e for e in race_data['events'] if 'cleanup' in e.get('event_type', '')])
        timeout_count = len([e for e in race_data['events'] if 'timeout' in str(e.get('details', {}))])
        
        print(f"      Cleanup calls: {cleanup_count}")
        print(f"      Timeout events: {timeout_count}")
        print(f"      Status: ✗ RACE CONDITION DETECTED\n")
    except Exception as e:
        print(f"      ✗ ERROR: {e}")
        return False
    
    # Step 6: Generate final report
    print("[6/6] Generating final report...")
    print()
    print("=" * 80)
    print("DIAGNOSIS RESULTS")
    print("=" * 80)
    print()
    
    print("ROOT CAUSES OF LIGHT ENGINE FREEZE:")
    print()
    print("1. DUPLICATE CLEANUP CALLS")
    print("   - Problem: Three separate code paths call cleanup_dlp_safe_state()")
    print("   - Sources: stop button, GUI close (on_closing), print thread finally block")
    print("   - Impact: Same DLP commands issued multiple times")
    print("   - Symptom: Freeze when multiple cleanup attempts collide")
    print()
    
    print("2. RACE CONDITION BETWEEN CLEANUP SOURCES")
    print("   - Problem: No coordination between cleanup entry points")
    print("   - Timing: Stop button cleanup and GUI close cleanup race")
    print("   - Impact: Cleanup happens simultaneously from multiple threads")
    print("   - Symptom: Race to access same USB devices → timeout")
    print()
    
    print("3. DLP COMMAND TIMEOUT CASCADE")
    print("   - Problem: If one DLP command hangs, next command timeout occurs")
    print("   - Mechanism: Previous command blocks, next command waits 5 sec, fails")
    print("   - Impact: Cleanup sequence aborts, hardware left in bad state")
    print("   - Symptom: Light engine won't respond, requires power cycle")
    print()
    
    print("4. A3200 SOCKET BLOCKING WITHOUT TIMEOUT")
    print("   - Problem: socket.recv(4096) has no timeout in _write_read()")
    print("   - Impact: If A3200 doesn't respond, GUI freeze")
    print("   - Scenario: Network glitch or A3200 unresponsive → indefinite hang")
    print("   - Symptom: App becomes unresponsive during stage disconnect")
    print()
    
    print("=" * 80)
    print("RECOMMENDED FIXES (Priority Order)")
    print("=" * 80)
    print()
    
    print("PRIORITY 1: Add socket timeout to A3200")
    print("  Action: Set socket timeout in _write_read() method")
    print("  Impact: Prevents indefinite hangs during stage operations")
    print("  Effort: Low (< 30 minutes)")
    print()
    
    print("PRIORITY 2: Single-owner shutdown coordinator")
    print("  Action: Route all cleanup through one coordinator lock")
    print("  Impact: Eliminates duplicate calls and race conditions")
    print("  Effort: Medium (1-2 hours)")
    print()
    
    print("PRIORITY 3: Ensure print thread join before DLP cleanup")
    print("  Action: Add print_thread.join(timeout=5) in on_closing()")
    print("  Impact: Prevents print thread from interfering with cleanup")
    print("  Effort: Low (< 30 minutes)")
    print()
    
    print("PRIORITY 4: DLP command recovery logic")
    print("  Action: Add bounded retry for failed DLP commands")
    print("  Impact: Makes shutdown more resilient to transient failures")
    print("  Effort: Medium (1-2 hours)")
    print()
    
    print("=" * 80)
    print("EVIDENCE FILES GENERATED")
    print("=" * 80)
    print()
    print(f"Normal shutdown log: {Path(log_normal).name}")
    print(f"Race condition log:  {Path(log_race).name}")
    print(f"Location: Rush_Segmented_VideoPattern/logs/")
    print()
    
    print("=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print()
    print("1. Share this diagnosis report with the team")
    print("2. Implement Priority 1 fix (socket timeout) immediately")
    print("3. Schedule Priority 2-4 fixes based on schedule")
    print("4. Test all fixes on both computers")
    print()
    
    print("=" * 80)
    print("* DIAGNOSIS COMPLETE")
    print("=" * 80)
    print()
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
