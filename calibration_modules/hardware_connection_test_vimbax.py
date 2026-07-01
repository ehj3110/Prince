#!/usr/bin/env python3
"""Minimal Allied Vision hardware connection test using Vimba X (vimbax)."""

import sys

import cv2
from vimbax import VimbaX


with VimbaX.get_instance() as vmb:
    cameras = vmb.get_all_cameras()
    if not cameras:
        print("ERROR: No Allied Vision camera found.")
        sys.exit(1)

    camera = cameras[0]
    with camera:
        model = camera.get_model()
        frame = camera.get_frame()
        image = frame.as_numpy_ndarray()

if not cv2.imwrite("hardware_test.png", image):
    print("ERROR: Failed to save hardware_test.png")
    sys.exit(1)

height, width = image.shape[:2]
print(f"SUCCESS: Captured one frame from {model} at {width}x{height} and saved hardware_test.png")
