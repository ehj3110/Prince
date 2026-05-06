"""
Phase 1 Test Scenario Runner for Rush Lifecycle Instrumentation

This script guides operators through the three test scenarios that expose the
freeze/power-cycle issue. Run each scenario 3 times and collect the lifecycle logs.

Scenarios:
1. NORMAL_COMPLETE: Let a print finish naturally, then close GUI
2. STOP_WITH_DELAY: Click Stop button, wait 5 seconds, then close GUI
3. STOP_IMMEDIATE: Click Stop button, immediately close GUI

Each scenario generates a lifecycle_*.json log in Rush_Segmented_VideoPattern/logs/
"""

import sys
import json
from pathlib import Path
from datetime import datetime


class ScenarioRunner:
    """Guides user through test scenarios and interprets results."""
    
    def __init__(self):
        self.logs_dir = Path(__file__).parent / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.report_file = self.logs_dir / f"phase1_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    
    def print_scenario_1_normal_complete(self):
        """Guide for normal print completion scenario."""
        print("\n" + "="*70)
        print("SCENARIO 1: NORMAL COMPLETE (Print finishes, then close GUI)")
        print("="*70)
        print("""
Steps:
  1. Launch Rush GUI: python no_hardware_preview.py
  2. Load a small test print (or use demo data)
  3. Click "Start Print" and let it run to completion
  4. Wait for the print to finish and all dialogs to appear
  5. Close any dialogs (click OK/Close on logging/status popups)
  6. Close the main Rush window
  7. Check console output for lifecycle log export message
  8. Open the generated logs/lifecycle_*.json file and review event order
        
Expected behavior:
  - No GUI freeze
  - Lifecycle log shows: app_init → print_start → ... → cleanup_dlp_end 
                        → stage_stop → stage_disconnect → gui_close → destroy
  - All cleanup calls complete successfully
  - No timeout warnings in log

Possible failure indicators:
  - GUI becomes unresponsive during close
  - Timeout warnings in lifecycle log
  - Duplicate cleanup_dlp_start entries with no _end
  - Stage operations timeout/exception
        """)
        input("Press ENTER when ready to start Scenario 1...")
    
    def print_scenario_2_stop_with_delay(self):
        """Guide for stop button with 5-second delay then close."""
        print("\n" + "="*70)
        print("SCENARIO 2: STOP WITH 5-SECOND DELAY (Stop → wait 5s → close)")
        print("="*70)
        print("""
Steps:
  1. Launch Rush GUI: python no_hardware_preview.py
  2. Load a small test print
  3. Click "Start Print"
  4. Let print run for a few seconds (don't wait for completion)
  5. Click the "Stop" button
  6. WAIT 5 SECONDS (let signal propagate and cleanup run)
  7. Close the main Rush window
  8. Check console output for lifecycle log export message
  9. Review the logs/lifecycle_*.json file
        
Expected behavior:
  - Stop button triggers cleanup_dlp smoothly
  - After 5-second wait, close completes without freeze
  - Lifecycle log shows: ... → cleanup_dlp_start (from stop_button) 
                        → cleanup_dlp_end → ... → gui_close
  - No exception for duplicate cleanup (second cleanup from print_finally)

Possible failure indicators:
  - GUI freeze during 5-second wait or after
  - duplicate_cleanup_detected warning in log
  - Cleanup exception for A3200 socket timeout
  - print_thread_join_result shows success=False
        """)
        input("Press ENTER when ready to start Scenario 2...")
    
    def print_scenario_3_stop_immediate(self):
        """Guide for stop button with immediate close."""
        print("\n" + "="*70)
        print("SCENARIO 3: STOP IMMEDIATE (Stop → immediately close)")
        print("="*70)
        print("""
Steps:
  1. Launch Rush GUI: python no_hardware_preview.py
  2. Load a small test print
  3. Click "Start Print"
  4. Let print run for a few seconds
  5. Click the "Stop" button
  6. DO NOT WAIT - immediately click the close (X) button on the window
  7. Observe if GUI freezes or closes cleanly
  8. Review the logs/lifecycle_*.json file
        
Expected behavior:
  - Close proceeds immediately without freeze
  - Lifecycle log shows: ... → cleanup_dlp_start (from stop_button)
                        → cleanup_dlp_end 
                        → print_thread_join_attempt/result → gui_close
  - All operations complete within expected time

Possible failure indicators:
  - GUI freeze after close button clicked
  - print_thread_join_result shows success=False AND timeout message
  - Multiple cleanup_dlp_start entries without corresponding _end
  - Callback_skipped warnings in log (suggests thread was still active)
        """)
        input("Press ENTER when ready to start Scenario 3...")
    
    def analyze_log_file(self, log_path):
        """Analyze a single lifecycle log and report findings."""
        try:
            with open(log_path, 'r') as f:
                data = json.load(f)
            
            events = data.get('events', [])
            session_id = data.get('session_id', 'unknown')
            
            report = {
                'session_id': session_id,
                'log_file': str(log_path),
                'total_events': len(events),
                'cleanup_calls': [],
                'thread_join_results': [],
                'exceptions': [],
                'warnings': [],
                'stage_operations': [],
                'dlp_operations': [],
            }
            
            for event in events:
                event_type = event.get('event_type', '')
                level = event.get('level', '')
                details = event.get('details', {})
                
                # Track cleanup calls
                if 'cleanup' in event_type:
                    report['cleanup_calls'].append({
                        'type': event_type,
                        'caller': details.get('caller', 'unknown'),
                        'call_number': details.get('call_number', 'unknown'),
                        'success': details.get('success', 'unknown'),
                    })
                
                # Track thread joins
                if 'thread_join' in event_type:
                    report['thread_join_results'].append({
                        'type': event_type,
                        'success': details.get('success', 'unknown'),
                        'timeout_sec': details.get('timeout_sec', 'unknown'),
                    })
                
                # Track exceptions
                if level == 'ERROR':
                    report['exceptions'].append({
                        'event': event_type,
                        'exception': details.get('exception_type', 'unknown'),
                        'message': details.get('exception_msg', 'unknown'),
                    })
                
                # Track warnings
                if level == 'WARNING':
                    report['warnings'].append({
                        'event': event_type,
                        'message': details.get('message', 'unknown'),
                    })
                
                # Track stage operations
                if 'stage_' in event_type:
                    report['stage_operations'].append({
                        'type': event_type,
                        'command': details.get('command', 'unknown'),
                        'result': details.get('result', 'unknown'),
                    })
                
                # Track DLP operations
                if 'dlp_' in event_type:
                    report['dlp_operations'].append({
                        'type': event_type,
                        'command': details.get('command', 'unknown'),
                        'result': details.get('result', 'unknown'),
                    })
            
            return report
        except Exception as e:
            print(f"Error analyzing log {log_path}: {e}")
            return None
    
    def print_analysis_report(self, scenario_name, analysis_reports):
        """Print and save analysis report for a scenario."""
        print("\n" + "="*70)
        print(f"ANALYSIS REPORT: {scenario_name}")
        print("="*70)
        
        for i, report in enumerate(analysis_reports, 1):
            print(f"\nRun {i}: {report['log_file']}")
            print(f"  Total events: {report['total_events']}")
            print(f"  Cleanup calls: {len(report['cleanup_calls'])}")
            for cleanup in report['cleanup_calls']:
                print(f"    - {cleanup['type']}: caller={cleanup['caller']}, "
                      f"success={cleanup['success']}")
            
            print(f"  Thread join results: {len(report['thread_join_results'])}")
            for join in report['thread_join_results']:
                print(f"    - {join['type']}: success={join['success']}, "
                      f"timeout={join['timeout_sec']}s")
            
            print(f"  DLP operations: {len(report['dlp_operations'])}")
            for dlp in report['dlp_operations']:
                if dlp['result'] != 'success':
                    print(f"    - {dlp['command']}: {dlp['result']} !!!")
                else:
                    print(f"    - {dlp['command']}: {dlp['result']}")
            
            print(f"  Stage operations: {len(report['stage_operations'])}")
            for stage in report['stage_operations']:
                if stage['result'] != 'success':
                    print(f"    - {stage['command']}: {stage['result']} !!!")
                else:
                    print(f"    - {stage['command']}: {stage['result']}")
            
            if report['exceptions']:
                print(f"  ❌ EXCEPTIONS ({len(report['exceptions'])}):")
                for exc in report['exceptions']:
                    print(f"    - {exc['event']}: {exc['exception']} - {exc['message']}")
            
            if report['warnings']:
                print(f"  ⚠️ WARNINGS ({len(report['warnings'])}):")
                for warn in report['warnings']:
                    print(f"    - {warn['event']}: {warn['message']}")
    
    def run_interactive_guide(self):
        """Run the interactive test scenario guide."""
        print("\n" + "="*70)
        print("RUSH LIFECYCLE INSTRUMENTATION - PHASE 1: REPRODUCTION")
        print("="*70)
        print("""
This guide will help you capture evidence of the light engine freeze issue
by instrumenting the app to log all shutdown operations with timestamps.

You will run 3 test scenarios, each designed to stress different shutdown paths:
  1. Normal print completion
  2. Stop button with 5-second delay before close
  3. Stop button with immediate close

For each scenario, you can run it 1-3 times independently to build confidence.
The logs will be saved to: Rush_Segmented_VideoPattern/logs/lifecycle_*.json

After each run, a summary will be printed showing cleanup sequence, exceptions,
and warnings. Look for:
  - Timeouts or exceptions in stage disconnect or DLP cleanup
  - Duplicate cleanup calls
  - Print thread failing to join within timeout
  - Any "callback_skipped" events (suggests GUI was closed while thread active)
        """)
        
        response = input("\nProceed with interactive scenario guide? (y/n): ").strip().lower()
        if response != 'y':
            print("Exiting. To run scenarios manually, see instructions above.")
            return
        
        scenarios = [
            ("NORMAL_COMPLETE", self.print_scenario_1_normal_complete),
            ("STOP_WITH_DELAY", self.print_scenario_2_stop_with_delay),
            ("STOP_IMMEDIATE", self.print_scenario_3_stop_immediate),
        ]
        
        for scenario_name, scenario_func in scenarios:
            scenario_func()
            
            # Collect logs generated since this scenario started
            recent_logs = sorted(self.logs_dir.glob("lifecycle_*.json"))
            
            print(f"\nWaiting for user to complete Scenario: {scenario_name}")
            input("Press ENTER after you have completed the scenario and the app has closed...")
            
            # Find newly generated logs
            new_logs = [log for log in sorted(self.logs_dir.glob("lifecycle_*.json"))
                       if log not in recent_logs]
            
            if new_logs:
                print(f"\nAnalyzing {len(new_logs)} log(s) from this scenario...")
                reports = [self.analyze_log_file(log) for log in new_logs]
                self.print_analysis_report(scenario_name, reports)
            else:
                print("\n⚠️ No new logs found. Make sure the app properly exported the log.")
        
        print("\n" + "="*70)
        print("PHASE 1 COMPLETE")
        print("="*70)
        print(f"""
All scenarios have been executed. Review the analysis above to identify:
  1. Which scenario triggers freezes or longest shutdown times
  2. Which operations timeout or raise exceptions
  3. Whether cleanup is called once or multiple times

The next phase will be to fix issues in order of severity:
  Priority 1: Fix any A3200 socket timeout that blocks close
  Priority 2: Ensure print thread is properly joined before final cleanup
  Priority 3: Prevent duplicate cleanup calls
  Priority 4: Add DLP recovery flow for next startup

All logs are saved in: {self.logs_dir}
        """)


if __name__ == '__main__':
    runner = ScenarioRunner()
    runner.run_interactive_guide()
