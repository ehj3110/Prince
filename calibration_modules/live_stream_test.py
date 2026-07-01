#!/usr/bin/env python3
"""Minimal PyQt6 + vmbpy live stream test with ChArUco calibration."""

import sys
from collections import deque

import cv2
import numpy as np
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget
from vmbpy import VmbSystem

from ChArucoCalibrator import ChArucoCalibrator


class CameraWorker(QThread):
    frame_ready = pyqtSignal(np.ndarray)

    def __init__(self) -> None:
        super().__init__()
        self._running = True

    def stop(self) -> None:
        self._running = False

    def run(self) -> None:
        try:
            with VmbSystem.get_instance() as vmb:
                cameras = vmb.get_all_cameras()
                physical_camera = None

                for cam in cameras:
                    model = cam.get_model()
                    cam_id = cam.get_id()
                    if "simulator" not in model.lower() and "simulator" not in cam_id.lower():
                        physical_camera = cam
                        break

                if physical_camera is None:
                    print("ERROR: No physical cameras detected. Skipping simulator devices.")
                    return

                with physical_camera:
                    for frame in physical_camera.get_frame_generator(limit=None, timeout_ms=2000):
                        if not self._running:
                            break
                        image = frame.as_opencv_image()
                        self.frame_ready.emit(image)
        except Exception as exc:
            print(f"ERROR: CameraWorker failed: {exc}")


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Allied Vision Live Stream Test + ChArUco Calibration")

        # Initialize ChArUco calibrator
        self.calibrator = ChArucoCalibrator()
        
        # Rolling average for focus score (last 10 frames)
        self.focus_scores = deque(maxlen=10)

        central = QWidget()
        layout = QVBoxLayout(central)

        self.focus_label = QLabel("Focus Score: --")
        self.focus_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.focus_label.setStyleSheet("font-size: 24px; font-weight: 600;")

        self.tilt_label = QLabel("Tip: -- | Tilt: -- | Markers: 0")
        self.tilt_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tilt_label.setStyleSheet("font-size: 24px; font-weight: 600; color: #0066cc;")

        self.label = QLabel("Waiting for camera frames...")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.focus_label)
        layout.addWidget(self.tilt_label)
        layout.addWidget(self.label, 1)
        self.setCentralWidget(central)

        self.worker = CameraWorker()
        self.worker.frame_ready.connect(self.update_frame)
        self.worker.start()

        self.resize(1200, 900)

    def update_frame(self, image: np.ndarray) -> None:
        if image is None or image.size == 0:
            return

        if image.ndim == 3 and image.shape[2] == 1:
            image = image[:, :, 0]
        elif image.ndim != 2:
            return

        image = np.ascontiguousarray(image)
        height, width = image.shape

        # Calculate rolling average focus score from center ROI
        roi_w = width // 2
        roi_h = height // 2
        roi_x0 = (width - roi_w) // 2
        roi_y0 = (height - roi_h) // 2
        roi_x1 = roi_x0 + roi_w
        roi_y1 = roi_y0 + roi_h

        roi = image[roi_y0:roi_y1, roi_x0:roi_x1]
        focus_score = cv2.Laplacian(roi, cv2.CV_64F).var()
        self.focus_scores.append(focus_score)
        
        avg_focus = np.mean(list(self.focus_scores))
        self.focus_label.setText(f"Focus Score: {avg_focus:.2f}")

        # Analyze frame with ChArUco calibrator for tilt/markers
        display_image = image.copy()
        
        try:
            # Convert to BGR for the calibrator (it expects BGR)
            image_bgr = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
            
            # Get analysis results
            analysis = self.calibrator.analyze_frame(image_bgr)
            
            # Extract results
            markers_detected = analysis.get('markers_detected', 0)
            tilt_detected = analysis.get('tilt_detected', False)
            tilt_x = analysis.get('tilt_x_deg', None)
            tilt_y = analysis.get('tilt_y_deg', None)
            
            # Update tilt label
            if tilt_detected and tilt_x is not None and tilt_y is not None:
                self.tilt_label.setText(f"Tip: {tilt_x:+.2f}° | Tilt: {tilt_y:+.2f}° | Markers: {markers_detected}")
            else:
                self.tilt_label.setText(f"Tip: -- | Tilt: -- | Markers: {markers_detected}")
            
            # Draw overlay if markers detected
            if markers_detected > 0:
                overlay_image = self.calibrator.draw_detection_overlay(image_bgr)
                # Convert back to grayscale for display
                display_image = cv2.cvtColor(overlay_image, cv2.COLOR_BGR2GRAY)
            else:
                # Still draw the ROI box for focus reference
                cv2.rectangle(display_image, (roi_x0, roi_y0), (roi_x1, roi_y1), 200, 2)
                
        except Exception as e:
            # Gracefully handle any calibrator errors
            print(f"WARNING: Calibrator analysis failed: {e}")
            # Draw ROI box as fallback
            cv2.rectangle(display_image, (roi_x0, roi_y0), (roi_x1, roi_y1), 200, 2)
            self.tilt_label.setText("Tip: -- | Tilt: -- | Markers: ERROR")

        # Convert to QImage and display
        bytes_per_line = width
        qimg = QImage(
            display_image.data,
            width,
            height,
            bytes_per_line,
            QImage.Format.Format_Grayscale8,
        )

        scaled = qimg.scaled(
            self.label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.label.setPixmap(QPixmap.fromImage(scaled))

    def closeEvent(self, event) -> None:
        self.worker.stop()
        self.worker.wait(3000)
        super().closeEvent(event)


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
