#!/usr/bin/env python
"""
Minimal test to verify Phase 1 infrastructure actually works end-to-end.
This is what the operator will run.
"""

import sys
import os

# Add Rush directory to path
sys.path.insert(0, os.path.dirname(__file__))

def test_phase1_infrastructure():
    """Run all critical tests that operator needs."""
    
    print("Testing Phase 1 Infrastructure...")
    print("=" * 60)
    
    # Test 1: Import lifecycle logger
    try:
        from lifecycle_logger import get_logger, init_logger
        print("✓ lifecycle_logger imports successfully")
    except Exception as e:
        print(f"✗ FAILED to import lifecycle_logger: {e}")
        return False
    
    # Test 2: Initialize logger
    try:
        init_logger()
        logger = get_logger()
        print(f"✓ Logger initialized (session: {logger.session_id})")
    except Exception as e:
        print(f"✗ FAILED to initialize logger: {e}")
        return False
    
    # Test 3: Log events
    try:
        logger.log_event("test_gui_close")
        logger.log_cleanup_start("test_source")
        logger.log_dlp_command("power", result="success")
        logger.log_dlp_command("stopsequence", result="success")
        logger.log_cleanup_end("test_source", success=True)
        print("✓ Event logging works")
    except Exception as e:
        print(f"✗ FAILED to log events: {e}")
        return False
    
    # Test 4: Export logs
    try:
        report_path = logger.export_session_log()
        print(f"✓ Logs exported to: {report_path}")
    except Exception as e:
        print(f"✗ FAILED to export logs: {e}")
        return False
    
    # Test 5: Verify JSON structure
    try:
        import json
        with open(report_path, 'r') as f:
            data = json.load(f)
        
        assert "session_id" in data
        assert "events" in data
        assert "total_events" in data
        assert len(data["events"]) > 0
        
        # Verify event structure
        sample_event = data["events"][0]
        assert "timestamp_elapsed_sec" in sample_event
        assert "event_type" in sample_event
        assert "thread_id" in sample_event
        assert "details" in sample_event
        
        print(f"✓ JSON structure valid ({data['total_events']} events)")
    except Exception as e:
        print(f"✗ FAILED JSON validation: {e}")
        return False
    
    # Test 6: Import test scenarios
    try:
        from test_scenarios import ScenarioRunner
        print("✓ test_scenarios imports successfully")
    except Exception as e:
        print(f"✗ FAILED to import test_scenarios: {e}")
        return False
    
    # Test 7: Create scenario runner
    try:
        runner = ScenarioRunner()
        print(f"✓ ScenarioRunner instantiated (logs dir: {runner.logs_dir})")
    except Exception as e:
        print(f"✗ FAILED to instantiate ScenarioRunner: {e}")
        return False
    
    # Test 8: Verify scenario methods exist
    try:
        assert callable(runner.print_scenario_1_normal_complete)
        assert callable(runner.print_scenario_2_stop_with_delay)
        assert callable(runner.print_scenario_3_stop_immediate)
        assert callable(runner.analyze_log_file)
        assert callable(runner.print_analysis_report)
        assert callable(runner.run_interactive_guide)
        print("✓ All scenario methods present and callable")
    except Exception as e:
        print(f"✗ FAILED method check: {e}")
        return False
    
    print()
    print("=" * 60)
    print("✓✓✓ ALL TESTS PASSED ✓✓✓")
    print()
    print("Phase 1 infrastructure is fully operational.")
    print("Operator can now run: python test_scenarios.py")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = test_phase1_infrastructure()
    sys.exit(0 if success else 1)
