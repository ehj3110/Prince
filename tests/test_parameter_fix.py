#!/usr/bin/env python3
"""
Test script to verify PeakForceLogger parameter fix
"""

import sys
import os
from pathlib import Path

# Add support_modules to path
support_dir = Path(__file__).parent / 'support_modules'
sys.path.insert(0, str(support_dir))

def test_peak_force_logger_parameters():
    """Test that PeakForceLogger can be instantiated with both old and new calling patterns"""
    print("Testing PeakForceLogger parameter compatibility...")
    
    try:
        from PeakForceLogger import PeakForceLogger
        print("✅ PeakForceLogger import successful")
        
        # Test 1: Manual logging (should work)
        logger1 = PeakForceLogger('test_manual.csv', is_manual_log=True)
        print("✅ Manual logger instantiation successful")
        
        # Test 2: Automated logging with corrected calculator (should work)
        logger2 = PeakForceLogger('test_auto.csv', is_manual_log=False, use_corrected_calculator=True)
        print("✅ Automated logger with corrected calculator successful")
        
        # Test 3: Default parameters (should work)
        logger3 = PeakForceLogger('test_default.csv')
        print("✅ Default parameters instantiation successful")
        
        print("\n🎯 All PeakForceLogger parameter tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_sensor_data_window_import():
    """Test that SensorDataWindow can import without errors"""
    print("\nTesting SensorDataWindow import...")
    
    try:
        # Set up proper path for imports
        parent_dir = Path(__file__).parent
        sys.path.insert(0, str(parent_dir))
        
        from support_modules.SensorDataWindow import SensorDataWindow
        print("✅ SensorDataWindow import successful")
        return True
        
    except Exception as e:
        print(f"❌ SensorDataWindow import error: {e}")
        return False

if __name__ == "__main__":
    print("PeakForceLogger Parameter Compatibility Test")
    print("=" * 50)
    
    success1 = test_peak_force_logger_parameters()
    success2 = test_sensor_data_window_import()
    
    if success1 and success2:
        print("\n🚀 All tests passed! System ready for printing.")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")
