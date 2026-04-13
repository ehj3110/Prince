"""Seam module for projection frame preparation and display calls."""

import cv2
import numpy as np


class ProjectionFrameManager:
    def __init__(self, window_name: str, black_image: np.ndarray):
        self.window_name = window_name
        self.black_image = black_image

    def show_frame(self, frame: np.ndarray) -> None:
        cv2.imshow(self.window_name, frame)
        cv2.waitKey(1)

    def show_black(self) -> None:
        cv2.imshow(self.window_name, self.black_image)
        cv2.waitKey(1)

    def show_from_path(self, image_path: str) -> bool:
        frame = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
        if frame is None:
            self.show_black()
            return False
        self.show_frame(frame)
        return True
