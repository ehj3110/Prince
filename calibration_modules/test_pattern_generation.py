"""
Test ChArUco Pattern Generation
================================

Quick test to verify pattern generation and view the output.

Usage:
    python test_pattern_generation.py
"""

import cv2
import sys
import os

try:
    from ChArucoCalibrator import ChArucoCalibrator
    print("✓ ChArucoCalibrator imported successfully")
except ImportError as e:
    print(f"✗ Error importing ChArucoCalibrator: {e}")
    sys.exit(1)


def test_pattern_generation():
    """Test pattern generation with different resolutions"""
    print("\n" + "="*60)
    print("ChArUco Pattern Generation Test")
    print("="*60)
    
    # Create calibrator
    calibrator = ChArucoCalibrator()
    print("\n✓ ChArUco calibrator created")
    print(f"  Board size: {calibrator.squares_x}×{calibrator.squares_y}")
    print(f"  Square size: {calibrator.square_length} pixels")
    print(f"  Marker size: {calibrator.marker_length} pixels")
    
    # Test different resolutions
    test_resolutions = [
        (1920, 1080, "Full HD"),
        (1280, 720, "HD"),
        (800, 600, "SVGA")
    ]
    
    print("\n" + "-"*60)
    print("Generating patterns...")
    print("-"*60)
    
    for width, height, name in test_resolutions:
        output_file = f"charuco_pattern_{width}x{height}.png"
        
        try:
            pattern = calibrator.generate_pattern(width, height, output_file)
            
            print(f"\n✓ {name} ({width}×{height}):")
            print(f"    Pattern shape: {pattern.shape}")
            print(f"    File saved: {output_file}")
            
            # Verify file exists and has reasonable size
            if os.path.exists(output_file):
                file_size = os.path.getsize(output_file)
                print(f"    File size: {file_size:,} bytes")
            
        except Exception as e:
            print(f"\n✗ Failed to generate {name}: {e}")
            return False
    
    print("\n" + "="*60)
    print("Pattern Generation: SUCCESS")
    print("="*60)
    print("\nGenerated files:")
    print("  - charuco_pattern_1920x1080.png (Full HD)")
    print("  - charuco_pattern_1280x720.png (HD)")
    print("  - charuco_pattern_800x600.png (SVGA)")
    print("\nYou can:")
    print("  1. Open these files in an image viewer")
    print("  2. Project them with your DLP projector")
    print("  3. Use them for camera calibration")
    
    # Offer to display the main pattern
    print("\n" + "-"*60)
    response = input("Display Full HD pattern? (y/n): ").strip().lower()
    
    if response == 'y':
        pattern_file = "charuco_pattern_1920x1080.png"
        if os.path.exists(pattern_file):
            print(f"Opening {pattern_file}...")
            print("Press any key in the image window to close")
            
            img = cv2.imread(pattern_file)
            cv2.imshow('ChArUco Calibration Pattern (1920×1080)', img)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
            
            print("✓ Pattern displayed")
        else:
            print(f"✗ Pattern file not found: {pattern_file}")
    
    return True


def main():
    """Run pattern generation test"""
    print("\n" + "#"*60)
    print("# ChArUco Pattern Generation Test")
    print("#"*60)
    
    success = test_pattern_generation()
    
    print("\n" + "#"*60)
    if success:
        print("# TEST PASSED ✓")
    else:
        print("# TEST FAILED ✗")
    print("#"*60)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
