"""
Manual Post-Processing Script
==============================
Run this script ANYTIME to generate plots from completed prints.
Works even if automatic post-processing failed during the print.

Usage:
    python manual_post_processing.py

The script will:
1. Show you all available print sessions
2. Let you select which one to process
3. Generate all plots and analysis

Author: GitHub Copilot
Date: November 30, 2025
"""

import sys
import os
from pathlib import Path
import argparse
from datetime import datetime

# Add project directories to path
workspace_dir = Path(__file__).parent
sys.path.insert(0, str(workspace_dir))
sys.path.insert(0, str(workspace_dir / "post-processing"))

from post_print_analyzer import PostPrintAnalyzer


def find_all_print_sessions(base_dir=None):
    """Find all print sessions in the logging directory."""
    if base_dir is None:
        # Try common base directories
        possible_bases = [
            Path(r"C:\Users\cheng sun\BoyuanSun\Slicing\Evan"),
            Path(r"PrintingLogs_Backup"),
            Path.cwd() / "PrintingLogs_Backup",
        ]
        
        for base in possible_bases:
            if base.exists():
                base_dir = base
                break
        
        if base_dir is None:
            print("Could not find PrintingLogs directory.")
            print("Please specify the path manually.")
            return []
    else:
        base_dir = Path(base_dir)
    
    if not base_dir.exists():
        print(f"Directory does not exist: {base_dir}")
        return []
    
    print(f"\nSearching for print sessions in: {base_dir}")
    print("=" * 80)
    
    # Find all print session directories
    sessions = []
    
    # Search pattern: base_dir/**/YYYY-MM-DD/Print N*
    for project_dir in base_dir.iterdir():
        if not project_dir.is_dir():
            continue
        
        # Look for Printing_Logs subdirectory
        logs_dir = project_dir / "Printing_Logs"
        if not logs_dir.exists():
            continue
        
        # Look for date directories
        for date_dir in logs_dir.iterdir():
            if not date_dir.is_dir():
                continue
            
            # Look for Print directories
            for print_dir in date_dir.iterdir():
                if not print_dir.is_dir():
                    continue
                
                if print_dir.name.startswith("Print"):
                    # Check if it has the required CSV files
                    has_autolog = any(print_dir.glob("autolog_*.csv"))
                    has_woa = (print_dir / "automated_work_of_adhesion.csv").exists()
                    
                    if has_autolog or has_woa:
                        sessions.append({
                            'path': print_dir,
                            'project': project_dir.name,
                            'date': date_dir.name,
                            'name': print_dir.name,
                            'has_autolog': has_autolog,
                            'has_woa': has_woa,
                            'modified': datetime.fromtimestamp(print_dir.stat().st_mtime)
                        })
    
    # Sort by modification time (most recent first)
    sessions.sort(key=lambda x: x['modified'], reverse=True)
    
    return sessions


def select_session(sessions):
    """Let user select which session to process."""
    if not sessions:
        print("\nNo print sessions found!")
        print("\nMake sure your prints have:")
        print("  - autolog_*.csv files (from AutomatedLayerLogger)")
        print("  - automated_work_of_adhesion.csv (from PeakForceLogger)")
        return None
    
    print(f"\nFound {len(sessions)} print session(s):\n")
    
    # Show sessions
    for i, session in enumerate(sessions, 1):
        status = []
        if session['has_autolog']:
            status.append("autolog")
        if session['has_woa']:
            status.append("WoA")
        
        print(f"{i:3}. {session['project']}")
        print(f"     {session['date']} / {session['name']}")
        print(f"     Data: {', '.join(status)}")
        print(f"     Modified: {session['modified'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"     Path: {session['path']}")
        print()
    
    # Get user selection
    while True:
        try:
            choice = input(f"Select session to process (1-{len(sessions)}, or 'q' to quit): ").strip()
            
            if choice.lower() == 'q':
                return None
            
            choice_num = int(choice)
            if 1 <= choice_num <= len(sessions):
                return sessions[choice_num - 1]
            else:
                print(f"Please enter a number between 1 and {len(sessions)}")
        except ValueError:
            print("Please enter a valid number or 'q' to quit")
        except KeyboardInterrupt:
            print("\nCancelled.")
            return None


def process_session(session):
    """Process the selected session."""
    print("\n" + "=" * 80)
    print(f"PROCESSING: {session['project']} / {session['date']} / {session['name']}")
    print("=" * 80 + "\n")
    
    try:
        analyzer = PostPrintAnalyzer()
        
        # Get the daily log directory (parent of print session)
        session_path = session['path']
        daily_dir = session_path.parent
        
        print(f"Session directory: {session_path}")
        print(f"Daily directory: {daily_dir}\n")
        
        # Build the session dictionary that analyze_print_session expects
        analyzer_session = {
            'path': session_path,
            'date': session['date'],
            'print_number': session['name'].replace('Print ', '').replace(' - Complete', '').strip(),
            'csv_files': list(session_path.glob("autolog_*.csv"))
        }
        
        # Process the specific session
        results = analyzer.analyze_print_session(analyzer_session)
        
        if results:
            print("\n" + "=" * 80)
            print("SUCCESS!")
            print("=" * 80)
            print(f"\nGenerated files:")
            
            # Look for generated files
            plot_files = list(session_path.glob("*analysis.png"))
            summary_files = list(session_path.glob("*SUMMARY.md"))
            
            for f in plot_files:
                print(f"  ✓ {f.name}")
            for f in summary_files:
                print(f"  ✓ {f.name}")
            
            if not plot_files and not summary_files:
                print("  (Files generated but not found in search)")
            
            print(f"\nAll files saved to: {session_path}")
            
            return True
        else:
            print("\n" + "=" * 80)
            print("FAILED")
            print("=" * 80)
            print("\nPost-processing did not return results.")
            print("Check console output above for error messages.")
            return False
            
    except Exception as e:
        print("\n" + "=" * 80)
        print("ERROR")
        print("=" * 80)
        print(f"\nException during processing: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Manual post-processing for print sessions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (recommended)
  python manual_post_processing.py
  
  # Process specific directory
  python manual_post_processing.py --path "C:\\Path\\To\\Print 1 - Complete"
  
  # Search in custom base directory
  python manual_post_processing.py --base "D:\\MyPrints"
  
  # Process most recent session automatically
  python manual_post_processing.py --latest
"""
    )
    
    parser.add_argument('--path', type=str,
                        help='Direct path to a specific print session directory')
    parser.add_argument('--base', type=str,
                        help='Base directory to search for print sessions')
    parser.add_argument('--latest', action='store_true',
                        help='Automatically process the most recent session')
    
    args = parser.parse_args()
    
    print("\n" + "=" * 80)
    print("MANUAL POST-PROCESSING SCRIPT")
    print("=" * 80)
    
    # Direct path provided
    if args.path:
        session_path = Path(args.path)
        if not session_path.exists():
            print(f"\nError: Path does not exist: {session_path}")
            return 1
        
        session = {
            'path': session_path,
            'project': session_path.parent.parent.name,
            'date': session_path.parent.name,
            'name': session_path.name,
            'has_autolog': any(session_path.glob("autolog_*.csv")),
            'has_woa': (session_path / "automated_work_of_adhesion.csv").exists(),
            'modified': datetime.fromtimestamp(session_path.stat().st_mtime)
        }
        
        success = process_session(session)
        return 0 if success else 1
    
    # Find sessions
    base_dir = args.base if args.base else None
    sessions = find_all_print_sessions(base_dir)
    
    if not sessions:
        print("\nNo sessions found. Try specifying --base directory or --path to specific session.")
        return 1
    
    # Auto-select latest
    if args.latest:
        session = sessions[0]  # Already sorted by most recent first
        print(f"\nAuto-selected most recent session:")
        print(f"  {session['project']} / {session['date']} / {session['name']}")
        success = process_session(session)
        return 0 if success else 1
    
    # Interactive selection
    session = select_session(sessions)
    
    if session is None:
        print("\nNo session selected. Exiting.")
        return 0
    
    success = process_session(session)
    return 0 if success else 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        sys.exit(1)
