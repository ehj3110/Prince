"""
Test DLP Pattern Mode for ChArUco Calibration
==============================================

Test displaying ChArUco pattern using DLP pattern-on-the-fly mode
for stable, non-choppy display.

Usage:
    python test_dlp_pattern_display.py
"""

import cv2
import numpy as np
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from support_modules import pycrafter9000
    print("✓ pycrafter9000 imported successfully")
except ImportError as e:
    print(f"✗ Error importing pycrafter9000: {e}")
    sys.exit(1)

try:
    from calibration_modules.ChArucoCalibrator import ChArucoCalibrator
    print("✓ ChArucoCalibrator imported successfully")
except ImportError as e:
    print(f"✗ Error importing ChArucoCalibrator: {e}")
    sys.exit(1)


def test_pattern_display():
    """Test displaying ChArUco pattern on DLP"""
    print("\n" + "="*60)
    print("DLP Pattern Mode Display Test")
    print("="*60)
    
    # Check if pattern file exists
    pattern_file = "charuco_pattern_1920x1080.png"
    
    if not os.path.exists(pattern_file):
        print(f"\n⚠️  Pattern file not found: {pattern_file}")
        print("Generating pattern...")
        
        calibrator = ChArucoCalibrator()
        pattern = calibrator.generate_pattern(1920, 1080, pattern_file)
        print(f"✓ Pattern generated: {pattern_file}")
    else:
        print(f"\n✓ Pattern file found: {pattern_file}")
    
    # Load pattern
    print("\nLoading pattern...")
    pattern = cv2.imread(pattern_file, cv2.IMREAD_GRAYSCALE)
    print(f"✓ Pattern loaded: shape={pattern.shape}, dtype={pattern.dtype}")
    
    # Resize to DLP native resolution (2560×1600 for DLP9000)
    if pattern.shape != (1600, 2560):
        print(f"Resizing pattern from {pattern.shape} to (1600, 2560)...")
        pattern = cv2.resize(pattern, (2560, 1600))
        print("✓ Pattern resized")
    
    # Connect to DLP
    print("\n" + "-"*60)
    print("Connecting to DLP...")
    try:
        dmd = pycrafter9000.dmd()
        print("✓ DLP connected")
    except Exception as e:
        print(f"✗ Failed to connect to DLP: {e}")
        print("\nMake sure:")
        print("  - DLP is powered on")
        print("  - USB cable is connected")
        print("  - No other program is using the DLP")
        return False
    
    # Display pattern
    print("\n" + "-"*60)
    print("PATTERN MODE DISPLAY")
    print("-"*60)
    print("\nDisplaying ChArUco pattern using pattern-on-the-fly mode...")
    print("This provides stable, non-choppy display for calibration.")
    print("")
    
    try:
        # Set to pattern mode (mode 4)
        print("Setting DLP to pattern mode...")
        dmd.changemode(4)
        
        # Display the pattern with 100ms exposure
        dmd.display_static_pattern(
            pattern, 
            exposure_us=100000,  # 100ms exposure
            repeat_count=0       # Infinite loop
        )
        
        print("\n✓ Pattern is now displayed on DLP!")
        print("")
        print("="*60)
        print("CALIBRATION INSTRUCTIONS")
        print("="*60)
        print("")
        print("The ChArUco pattern should now be visible on the DLP.")
        print("Use your camera to view the pattern and perform calibration.")
        print("")
        print("Press Enter when done to clear pattern and return to video mode...")
        input()
        
        # Stop pattern and return to video mode
        print("\nStopping pattern sequence...")
        dmd.stopsequence()
        
        print("Returning to video mode...")
        dmd.changemode(3)  # Video/HDMI mode
        
        print("✓ Pattern cleared, DLP back to video mode")
        return True
        
    except Exception as e:
        print(f"\n✗ Error displaying pattern: {e}")
        import traceback
        traceback.print_exc()
        
        # Try to clean up
        try:
            print("\nAttempting to restore DLP to video mode...")
            dmd.stopsequence()
            dmd.changemode(3)
            print("✓ DLP restored")
        except:
            print("⚠️  Could not restore DLP - may need manual reset")
        
        return False


def main():
    """Run DLP pattern display test"""
    print("\n" + "#"*60)
    print("# DLP Pattern Mode Display Test")
    print("# For ChArUco Calibration")
    print("#"*60)
    
    success = test_pattern_display()
    
    print("\n" + "#"*60)
    if success:
        print("# TEST COMPLETE ✓")
    else:
        print("# TEST FAILED ✗")
    print("#"*60)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
