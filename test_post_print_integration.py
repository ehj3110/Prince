#!/usr/bin/env python3
"""
Test script to verify post-print analysis integration
"""

import sys
import os
from pathlib import Path

def test_post_print_integration():
    """Test the post-print analysis integration"""
    print("Testing Post-Print Analysis Integration")
    print("=" * 50)
    
    try:
        # Test import
        from post_print_analyzer import PostPrintAnalyzer
        print("✅ PostPrintAnalyzer import successful")
        
        # Test instantiation
        analyzer = PostPrintAnalyzer()
        print("✅ PostPrintAnalyzer instantiation successful")
        
        # Test method existence
        if hasattr(analyzer, 'find_print_sessions'):
            print("✅ find_print_sessions method exists")
        else:
            print("❌ find_print_sessions method missing")
            
        if hasattr(analyzer, 'analyze_print_session'):
            print("✅ analyze_print_session method exists")
        else:
            print("❌ analyze_print_session method missing")
        
        # Test with dummy directory
        test_dir = "test_logs"
        sessions = analyzer.find_print_sessions(test_dir)
        print(f"✅ find_print_sessions works (found {len(sessions)} sessions in non-existent dir)")
        
        print("\n🎯 Post-print analysis integration test complete!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_post_print_integration()
