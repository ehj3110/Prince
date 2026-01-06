"""Quick test to check DLP visibility"""
from support_modules import pycrafter9000
import numpy as np
import time

print("Connecting to DLP...")
dmd = pycrafter9000.dmd()
print("✓ Connected")

# Check current mode
try:
    mode = dmd.getmode()
    print(f"Current mode: {mode}")
except:
    print("Could not read mode")

# Set high power for visibility (0-255 current, 100 is reasonable)
print("\nSetting LED power to 100...")
dmd.power(100)
time.sleep(0.5)

# Switch to pattern mode
print("Switching to pattern mode (mode 4)...")
dmd.changemode(4)
time.sleep(1)

# Create a simple white pattern (all 255s)
print("\nDisplaying FULL WHITE pattern...")
white_pattern = np.full((1600, 2560), 255, dtype=np.uint8)

dmd.display_static_pattern(
    white_pattern,
    exposure_us=100000,  # 100ms
    repeat_count=0
)

print("\n" + "="*60)
print("FULL WHITE PATTERN DISPLAYED")
print("="*60)
print("\nThe DLP should now be showing a bright white screen.")
print("If you don't see anything:")
print("  1. Check DLP is powered on")
print("  2. Check projection surface/screen")
print("  3. Check if DLP lens cap is removed")
print("  4. Check HDMI/connection cables")
print("\nPress Enter to test a BLACK/WHITE checkerboard pattern...")
input()

# Create checkerboard
print("\nDisplaying CHECKERBOARD pattern...")
checkerboard = np.zeros((1600, 2560), dtype=np.uint8)
# Create 200x200 pixel squares
square_size = 200
for i in range(0, 1600, square_size):
    for j in range(0, 2560, square_size):
        if ((i // square_size) + (j // square_size)) % 2 == 0:
            checkerboard[i:i+square_size, j:j+square_size] = 255

dmd.stopsequence()
time.sleep(0.5)
dmd.display_static_pattern(checkerboard, exposure_us=100000, repeat_count=0)

print("\n" + "="*60)
print("CHECKERBOARD PATTERN DISPLAYED")
print("="*60)
print("\nYou should see alternating white and black squares.")
print("\nPress Enter to clean up and exit...")
input()

print("\nStopping pattern and returning to video mode...")
dmd.stopsequence()
dmd.changemode(3)
print("✓ Done. DLP back to video mode.")
