"""Quick test to see actual CSV output."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
import cv2
import time
from support_modules.PeakForceLogger import PeakForceLogger

# Create test images
img = np.zeros((2560, 1600), dtype=np.uint8)
cv2.circle(img, (800, 1280), 70, 255, -1)
cv2.imwrite("test_layer1.png", img)

img2 = np.zeros((2560, 1600), dtype=np.uint8)
cv2.circle(img2, (800, 1280), 90, 255, -1)
cv2.imwrite("test_layer2.png", img2)

# Create logger
logger = PeakForceLogger("test_quick_output.csv", is_manual_log=False)

# Process 2 layers
for layer_num in [1, 2]:
    img_path = f"test_layer{layer_num}.png"
    logger.start_monitoring_for_layer(layer_num, z_peel_peak=10.0, z_return_pos=13.0, image_path=img_path)
    
    # Add force data
    base_time = time.time()
    for j in range(100):
        t = base_time + j * 0.01
        pos = 10.0 + (j / 100.0) * 3.0
        force = max(0.0, 1.0 * np.sin(j / 100.0 * 3.14159))
        logger.add_data_point(t, pos, force)
    
    logger.stop_monitoring_and_log_peak()
    print(f"Layer {layer_num} processed")

logger.close()
time.sleep(1.0)  # Wait for worker

# Show CSV
print("\n=== CSV Contents ===")
with open("test_quick_output.csv", 'r') as f:
    print(f.read())
