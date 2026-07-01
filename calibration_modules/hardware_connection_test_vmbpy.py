#!/usr/bin/env python3
"""Minimal Allied Vision hardware connection test using vmbpy - physical hardware only."""

import sys

import cv2
from vmbpy import VmbSystem


with VmbSystem.get_instance() as vmb:
    cameras = vmb.get_all_cameras()
    if not cameras:
        print("ERROR: No cameras found.")
        sys.exit(1)

    # Filter out simulator cameras; keep only physical hardware
    physical_cameras = [c for c in cameras if 'Simulator' not in c.get_model()]
    
    if not physical_cameras:
        print("**ERROR: No physical cameras detected. Check power, cables, and Vimba Viewer.**")
        sys.exit(1)

    cam = physical_cameras[0]
    with cam:
        model = cam.get_model()
        frame = cam.get_frame()
        image = frame.as_opencv_image()

if not cv2.imwrite("physical_hardware_test.png", image):
    print("ERROR: Failed to save physical_hardware_test.png")
    sys.exit(1)

print(f"SUCCESS: camera={model}, image_shape={image.shape}")
