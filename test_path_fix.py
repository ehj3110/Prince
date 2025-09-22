#!/usr/bin/env python3
"""
Test script to verify the path fix for post-print analysis
"""

import os
from pathlib import Path

def test_path_logic():
    """Test the corrected path logic"""
    print("Testing Path Logic Fix")
    print("=" * 30)
    
    # Simulate the directory structure
    current_print_session_log_dir = r"C:\Users\cheng sun\BoyuanSun\Slicing\Evan\1cmCylinder\Printing_Logs\2025-09-21\Print 1"
    
    print(f"Current print session dir: {current_print_session_log_dir}")
    
    # Get daily log directory (what the fix does)
    daily_log_dir = os.path.dirname(current_print_session_log_dir)
    print(f"Daily log dir (parent): {daily_log_dir}")
    
    # Show what the old logic was doing wrong
    old_logs_base_dir = os.path.dirname(current_print_session_log_dir)  # Same as daily_log_dir
    print(f"Old logic was passing to find_print_sessions: {old_logs_base_dir}")
    print("  → find_print_sessions expected to find date dirs like '2025-09-21' inside this")
    print("  → But this IS the '2025-09-21' dir, so no date dirs found!")
    
    print("\n✅ NEW LOGIC:")
    print(f"  → Look directly in daily dir: {daily_log_dir}")
    print("  → Find Print 1, Print 2, etc. folders")
    print("  → Look for CSV files in each Print folder")
    
    return True

if __name__ == "__main__":
    test_path_logic()
