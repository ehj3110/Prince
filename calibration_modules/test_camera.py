"""
Camera System Test Script
==========================

Test and demonstrate Allied Vision camera functionality.

Usage:
    python test_camera.py

Author: Cheng Sun Lab Team
Date: November 28, 2025
"""

import sys
import time

# Test imports
try:
    from AlliedVisionCameraManager import AlliedVisionCameraManager, list_available_cameras
    from CameraViewWindow import CameraViewWindow
    print("✓ Camera modules imported successfully")
except ImportError as e:
    print(f"✗ Error importing camera modules: {e}")
    sys.exit(1)

try:
    from vimba import Vimba
    print("✓ Vimba SDK available")
    VIMBA_AVAILABLE = True
except ImportError:
    print("✗ Vimba SDK not installed")
    print("  Install with: pip install vimba")
    print("  Note: Also requires Vimba SDK from Allied Vision website")
    VIMBA_AVAILABLE = False


def test_camera_discovery():
    """Test camera discovery"""
    print("\n" + "="*60)
    print("TEST 1: Camera Discovery")
    print("="*60)
    
    if not VIMBA_AVAILABLE:
        print("SKIP: Vimba SDK not available")
        return False
    
    try:
        cameras = list_available_cameras()
        
        if cameras:
            print(f"✓ Found {len(cameras)} camera(s):")
            for i, cam_id in enumerate(cameras, 1):
                print(f"  {i}. {cam_id}")
            return True
        else:
            print("✗ No cameras found")
            print("  Check:")
            print("  - Camera is plugged into USB port")
            print("  - Vimba SDK is installed correctly")
            print("  - Camera drivers are installed")
            return False
            
    except Exception as e:
        print(f"✗ Error during camera discovery: {e}")
        return False


def test_camera_connection():
    """Test camera connection and basic operations"""
    print("\n" + "="*60)
    print("TEST 2: Camera Connection")
    print("="*60)
    
    if not VIMBA_AVAILABLE:
        print("SKIP: Vimba SDK not available")
        return False
    
    camera = AlliedVisionCameraManager()
    
    try:
        # Connect
        print("Connecting to camera...")
        success = camera.connect()
        
        if not success:
            print("✗ Connection failed")
            return False
        
        print("✓ Camera connected")
        
        # Get camera info
        info = camera.get_camera_info()
        print(f"  Camera ID: {info.get('id', 'Unknown')}")
        print(f"  Model: {info.get('model', 'Unknown')}")
        print(f"  Exposure: {info.get('exposure', 'Unknown')} µs")
        print(f"  Gain: {info.get('gain', 'Unknown')} dB")
        
        # Test exposure control
        print("\nTesting exposure control...")
        camera.set_exposure(15000)
        time.sleep(0.1)
        print("✓ Exposure set to 15000 µs")
        
        # Test gain control
        print("Testing gain control...")
        camera.set_gain(5)
        time.sleep(0.1)
        print("✓ Gain set to 5 dB")
        
        # Disconnect
        print("\nDisconnecting camera...")
        camera.disconnect()
        print("✓ Camera disconnected")
        
        return True
        
    except Exception as e:
        print(f"✗ Error during camera test: {e}")
        camera.disconnect()
        return False


def test_single_frame_capture():
    """Test single frame capture"""
    print("\n" + "="*60)
    print("TEST 3: Single Frame Capture")
    print("="*60)
    
    if not VIMBA_AVAILABLE:
        print("SKIP: Vimba SDK not available")
        return False
    
    camera = AlliedVisionCameraManager()
    
    try:
        # Connect
        print("Connecting to camera...")
        if not camera.connect():
            print("✗ Connection failed")
            return False
        
        # Capture frame
        print("Capturing single frame...")
        frame = camera.capture_single_frame()
        
        if frame is not None:
            print(f"✓ Frame captured: {frame.shape}")
            print(f"  Width: {frame.shape[1]} pixels")
            print(f"  Height: {frame.shape[0]} pixels")
            if len(frame.shape) > 2:
                print(f"  Channels: {frame.shape[2]}")
            else:
                print(f"  Channels: 1 (grayscale)")
            
            # Test save
            print("\nSaving test image...")
            success = camera.save_calibration_image("test_camera_frame.png")
            if success:
                print("✓ Test image saved: test_camera_frame.png")
            else:
                print("✗ Failed to save image")
            
            camera.disconnect()
            return True
        else:
            print("✗ Frame capture failed")
            camera.disconnect()
            return False
            
    except Exception as e:
        print(f"✗ Error during frame capture: {e}")
        camera.disconnect()
        return False


def test_camera_window():
    """Test camera window (interactive)"""
    print("\n" + "="*60)
    print("TEST 4: Camera Window (Interactive)")
    print("="*60)
    
    print("Opening camera window...")
    print("  - Test connection button")
    print("  - Test streaming")
    print("  - Test exposure/gain controls")
    print("  - Close window when done")
    print("\nPress Enter to open window...")
    input()
    
    try:
        window = CameraViewWindow()
        window.run()
        print("✓ Camera window test complete")
        return True
        
    except Exception as e:
        print(f"✗ Error opening camera window: {e}")
        return False


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("ALLIED VISION CAMERA SYSTEM TEST")
    print("="*60)
    
    results = []
    
    # Test 1: Discovery
    results.append(("Camera Discovery", test_camera_discovery()))
    
    # Test 2: Connection
    results.append(("Camera Connection", test_camera_connection()))
    
    # Test 3: Frame capture
    results.append(("Frame Capture", test_single_frame_capture()))
    
    # Test 4: Window (interactive)
    print("\nWould you like to test the camera window? (y/n): ", end="")
    response = input().lower()
    if response == 'y':
        results.append(("Camera Window", test_camera_window()))
    else:
        print("Skipping camera window test")
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name:.<50} {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed!")
    else:
        print(f"\n✗ {total - passed} test(s) failed")


if __name__ == "__main__":
    print("\nAllied Vision Camera System Test")
    print("=" * 60)
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--discovery":
            test_camera_discovery()
        elif sys.argv[1] == "--connection":
            test_camera_connection()
        elif sys.argv[1] == "--capture":
            test_single_frame_capture()
        elif sys.argv[1] == "--window":
            test_camera_window()
        else:
            print(f"Unknown test: {sys.argv[1]}")
            print("Available tests: --discovery, --connection, --capture, --window")
    else:
        run_all_tests()
