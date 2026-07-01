import cv2
import time
import numpy as np
from screeninfo import get_monitors
from support_modules import pycrafter9000
from support_modules.USBCoordinator import usb_coordinator

def test_startup_flashes():
    print("="*60)
    print("DLP SILENT STARTUP FLASH TEST (Video Pattern Mode)")
    print("="*60)
    
    # 1. Connect to DLP
    print("\nConnecting to DLP...")
    try:
        controller = pycrafter9000.dmd()
        print("✓ Connected to DLP hardware.")
    except Exception as e:
        print(f"Error connecting to DLP: {e}")
        return

    # 2. Setup OpenCV Window on project screen
    print("\nSetting up OpenCV Display...")
    monitors = get_monitors()
    projector_screen = None
    for m in monitors:
        if m.width == 2560 and m.height == 1600:
            projector_screen = m
            break
            
    if not projector_screen:
        print("Could not find a 2560x1600 projector screen. Using default/primary.")
        projector_screen = monitors[0] # fallback

    window_name = "Projection Window"
    black_image = np.zeros((1600, 2560), dtype=np.uint8)
    
    cv2.namedWindow(window_name, cv2.WND_PROP_FULLSCREEN)
    # The + 1439 and -1 logic from GUI
    cv2.moveWindow(window_name, projector_screen.x + 1439, projector_screen.y - 1)
    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    cv2.imshow(window_name, black_image)
    
    print("Pumping OpenCV events to ensure black frame reaches HDMI buffer...")
    for _ in range(10):
        cv2.waitKey(50)
    print("✓ OpenCV window initialized and black frame pumped.")

    # 3. Silent Wake sequence
    print("\nExecuting Silent Wake Sequence...")
    try:
        with usb_coordinator.dlp_operation("test_silent_startup"):
            controller.stopsequence()
            print("  -> stopsequence()")
            controller.power(current=0)
            print("  -> power(0)")
            
            controller.changemode(0x00)
            controller.power(current=0) # Implicit ignition prevention
            print("  -> changemode(0x00) followed by power(0)")
            
            controller.hdmi()
            print("  -> hdmi()")
            
            print("  -> Waiting 1.5s for HDMI lock (pumping cv2)")
            start_time = time.time()
            while (time.time() - start_time) < 1.5:
                cv2.waitKey(50)
                
            controller.changemode(0x02)
            controller.power(current=0) # Implicit ignition prevention
            print("  -> changemode(0x02) followed by power(0)")
            
            controller.configurelut(1, 0xFFFFFFFF)
            print("  -> configurelut(1, White)")

        print("\n✓ Startup sequence complete!")
        print("At this point, if fixes are working, you should NOT have seen:")
        print(" 1. The desktop background (prevented by waitKey HDMI pump)")
        print(" 2. A momentary white flash (prevented by instant power(0) clamping)")
        
        print("\nAre you ready to test actual illumination? Press Enter in the console to project white light...")
        input("Press Enter to continue > ")

        # 4. Do a quick projection to prove we can
        print("\nDisplaying White Image for 2 seconds...")
        white_image = np.ones((1600, 2560), dtype=np.uint8) * 255
        cv2.imshow(window_name, white_image)
        for _ in range(5):
            cv2.waitKey(10)
            
        with usb_coordinator.dlp_operation("test_projection"):
            controller.power(current=70) # turn on light to a safe test level
            controller.startsequence()

        time.sleep(2.0)
        
        with usb_coordinator.dlp_operation("test_teardown"):
            controller.stopsequence()
            controller.power(current=0)
            
        print("\nTest finished. Cleaning up.")

    except Exception as e:
        print(f"\nError during DLP operations: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Proper Teardown
        print("\nClosing Display properly...")
        cv2.imshow(window_name, black_image)
        for _ in range(5):
            cv2.waitKey(10)
        cv2.destroyWindow(window_name)
        for _ in range(5):
            cv2.waitKey(10)

if __name__ == "__main__":
    test_startup_flashes()
