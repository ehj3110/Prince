"""Simple DLP projection test - uses small target pattern for fast encoding"""
from support_modules import pycrafter9000
import numpy as np
import cv2
import time

print("="*60)
print("SIMPLE DLP PROJECTION TEST")
print("="*60)

# Connect
print("\nConnecting to DLP...")
dmd = pycrafter9000.dmd()
print("✓ Connected")

# Set LED power
print("Setting LED power to 100...")
dmd.power(100)

# Switch to pattern mode
print("Switching to pattern mode...")
dmd.changemode(4)
time.sleep(0.5)

# Create a simple test pattern: circle in center
print("\nCreating test pattern (circle in center)...")
pattern = np.zeros((1600, 2560), dtype=np.uint8)

# Draw a large circle in the center
center_x, center_y = 1280, 800  # Center of 2560×1600
radius = 400
cv2.circle(pattern, (center_x, center_y), radius, 255, -1)  # Filled white circle

# Add some text
cv2.putText(pattern, "DLP TEST", (center_x-200, center_y), 
            cv2.FONT_HERSHEY_SIMPLEX, 2, 255, 4)

print(f"Pattern created: {pattern.shape}, min={pattern.min()}, max={pattern.max()}")

# Display
print("\nDisplaying pattern...")
print("(This may take 10-30 seconds for encoding...)")

try:
    dmd.display_static_pattern(pattern, exposure_us=100000, repeat_count=0)
    
    print("\n" + "="*60)
    print("PATTERN DISPLAYED!")
    print("="*60)
    print("\nYou should see a white circle with 'DLP TEST' text")
    print("in the center of the projection.")
    print("\nIf you don't see anything, check:")
    print("  - DLP power is on")
    print("  - Projection surface is in front of DLP")
    print("  - Room is reasonably dark")
    print("  - Lens cap is removed")
    print("\nPress Enter to stop and return to video mode...")
    input()
    
except KeyboardInterrupt:
    print("\nInterrupted by user")
except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()

# Cleanup
print("\nCleaning up...")
try:
    dmd.stopsequence()
    dmd.changemode(3)  # Back to video mode
    print("✓ DLP back to video mode")
except:
    print("⚠️  Could not restore DLP")

print("\nDone.")
