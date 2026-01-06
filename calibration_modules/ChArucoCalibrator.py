"""
ChArUco Calibration Module
===========================

Implements focus and tilt detection using ChArUco (Checkerboard + ArUco) patterns.

This module provides:
1. ChArUco pattern generation for projection
2. Focus detection via Laplacian variance (MTF proxy)
3. Tilt/tip detection via marker pose estimation
4. Works with limited FOV (inner 50% due to vignetting)

Author: Cheng Sun Lab Team
Date: November 28, 2025
"""

import numpy as np
import cv2
from typing import Optional, Tuple
import os


class ChArucoCalibrator:
    """
    ChArUco-based focus and tilt calibration for projection systems.
    
    Handles vignetting by using only the center region (inner 50% of image).
    Single pattern performs "double duty" for both focus and tilt measurement.
    """
    
    def __init__(self, 
                 squares_x: int = 8,
                 squares_y: int = 6,
                 square_length: float = 100,  # pixels
                 marker_length: float = 50,   # pixels (smaller = better focus sensitivity)
                 dictionary=cv2.aruco.DICT_4X4_50):
        """
        Initialize ChArUco calibrator.
        
        Args:
            squares_x: Number of squares in X direction
            squares_y: Number of squares in Y direction
            square_length: Length of checkerboard square in pixels
            marker_length: Length of ArUco marker in pixels
            dictionary: ArUco dictionary to use
        """
        self.squares_x = squares_x
        self.squares_y = squares_y
        self.square_length = square_length
        self.marker_length = marker_length
        
        # Create ArUco dictionary and board
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(dictionary)
        self.board = cv2.aruco.CharucoBoard(
            (squares_x, squares_y),
            square_length,
            marker_length,
            self.aruco_dict
        )
        
        # Detector parameters
        self.detector_params = cv2.aruco.DetectorParameters()
        
        # Camera intrinsic matrix (None = use relative measurements)
        self.camera_matrix = None
        self.dist_coeffs = None
        
        # ROI settings (inner 50% due to vignetting)
        self.roi_fraction = 0.5  # Use center 50% of image
        
    def generate_pattern(self, width: int, height: int, output_path: Optional[str] = None) -> np.ndarray:
        """
        Generate ChArUco pattern for projection.
        
        Args:
            width: Pattern width in pixels (projector resolution)
            height: Pattern height in pixels (projector resolution)
            output_path: Optional path to save pattern as PNG
            
        Returns:
            ChArUco pattern as numpy array
        """
        # Calculate board size in pixels
        board_width = self.squares_x * self.square_length
        board_height = self.squares_y * self.square_length
        
        # Create pattern
        pattern = self.board.generateImage((int(board_width), int(board_height)))
        
        # Scale to fit projector resolution (with margins)
        margin = 50  # pixels
        target_width = width - 2 * margin
        target_height = height - 2 * margin
        
        # Calculate scale factor (maintain aspect ratio)
        scale_x = target_width / board_width
        scale_y = target_height / board_height
        scale = min(scale_x, scale_y)
        
        new_width = int(board_width * scale)
        new_height = int(board_height * scale)
        
        pattern_scaled = cv2.resize(pattern, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
        
        # Create final image with white border
        final_pattern = np.ones((height, width), dtype=np.uint8) * 255
        
        # Center the pattern
        offset_x = (width - new_width) // 2
        offset_y = (height - new_height) // 2
        final_pattern[offset_y:offset_y+new_height, offset_x:offset_x+new_width] = pattern_scaled
        
        # Save if requested
        if output_path:
            cv2.imwrite(output_path, final_pattern)
            print(f"ChArUco pattern saved to: {output_path}")
        
        return final_pattern
    
    def set_camera_intrinsics(self, camera_matrix: np.ndarray, dist_coeffs: np.ndarray):
        """
        Set camera intrinsic parameters for absolute tilt measurement.
        
        Args:
            camera_matrix: 3x3 camera intrinsic matrix
            dist_coeffs: Distortion coefficients
        """
        self.camera_matrix = camera_matrix
        self.dist_coeffs = dist_coeffs
    
    def _get_roi_mask(self, image_shape: Tuple[int, int]) -> np.ndarray:
        """
        Create mask for center ROI (inner 50% due to vignetting).
        
        Args:
            image_shape: (height, width) of image
            
        Returns:
            Binary mask with ROI set to 255
        """
        height, width = image_shape[:2]
        
        # Calculate ROI boundaries
        roi_width = int(width * self.roi_fraction)
        roi_height = int(height * self.roi_fraction)
        
        x_start = (width - roi_width) // 2
        y_start = (height - roi_height) // 2
        
        # Create mask
        mask = np.zeros((height, width), dtype=np.uint8)
        mask[y_start:y_start+roi_height, x_start:x_start+roi_width] = 255
        
        return mask
    
    def calculate_focus_score(self, image: np.ndarray, method: str = 'edge') -> float:
        """
        Calculate focus quality using edge-based measurement.
        
        Uses edge sharpness of ArUco markers for superior focus detection.
        Smaller markers provide better sensitivity to defocus.
        
        Args:
            image: Camera frame (grayscale or BGR)
            method: 'edge' (default, best), 'tenengrad', or 'laplacian'
            
        Returns:
            Focus score (higher = sharper)
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Get ROI mask
        mask = self._get_roi_mask(gray.shape)
        
        # Apply mask
        roi = cv2.bitwise_and(gray, gray, mask=mask)
        
        if method == 'edge':
            # Edge-based focus using gradient magnitude on marker edges
            # This is most sensitive to defocus on small features
            focus_score = self._edge_focus_score(roi)
        elif method == 'tenengrad':
            # Tenengrad gradient method (better than Laplacian)
            gx = cv2.Sobel(roi, cv2.CV_64F, 1, 0, ksize=3)
            gy = cv2.Sobel(roi, cv2.CV_64F, 0, 1, ksize=3)
            focus_score = np.mean(gx**2 + gy**2)
        else:
            # Laplacian variance (original method)
            laplacian = cv2.Laplacian(roi, cv2.CV_64F)
            focus_score = laplacian.var()
        
        return focus_score
    
    def _edge_focus_score(self, image: np.ndarray) -> float:
        """
        Calculate focus score based on edge sharpness.
        
        Detects ArUco marker edges and measures gradient strength.
        Sharp edges have high gradients; blurry edges have low gradients.
        
        Args:
            image: Grayscale image
            
        Returns:
            Focus score based on edge sharpness
        """
        # Detect ArUco markers to find edges
        corners, ids, rejected = cv2.aruco.detectMarkers(
            image,
            self.aruco_dict,
            parameters=self.detector_params
        )
        
        if ids is None or len(ids) == 0:
            # No markers found - fall back to gradient-based method
            gx = cv2.Sobel(image, cv2.CV_64F, 1, 0, ksize=3)
            gy = cv2.Sobel(image, cv2.CV_64F, 0, 1, ksize=3)
            gradient_magnitude = np.sqrt(gx**2 + gy**2)
            return np.mean(gradient_magnitude)
        
        # Calculate gradients
        gx = cv2.Sobel(image, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(image, cv2.CV_64F, 0, 1, ksize=3)
        gradient_magnitude = np.sqrt(gx**2 + gy**2)
        
        # Create mask for marker edges (dilate marker regions)
        edge_mask = np.zeros(image.shape, dtype=np.uint8)
        
        for corner in corners:
            # Get marker corners
            pts = corner[0].astype(np.int32)
            
            # Draw marker boundary with thickness for edge detection
            cv2.polylines(edge_mask, [pts], True, 255, thickness=10)
        
        # Measure gradient strength only at marker edges
        edge_gradients = gradient_magnitude[edge_mask > 0]
        
        if len(edge_gradients) == 0:
            # No edges found - use full image
            return np.mean(gradient_magnitude)
        
        # Return mean gradient at edges (higher = sharper)
        focus_score = np.mean(edge_gradients)
        
        return focus_score
    
    def detect_tilt(self, image: np.ndarray) -> Tuple[bool, Optional[np.ndarray], Optional[float], Optional[float]]:
        """
        Detect surface tilt using ChArUco marker pose estimation.
        
        Args:
            image: Camera frame (grayscale or BGR)
            
        Returns:
            Tuple of (success, normal_vector, tilt_x_deg, tilt_y_deg)
            - success: True if tilt detected successfully
            - normal_vector: Surface normal vector [x, y, z] (None if failed)
            - tilt_x_deg: Tilt angle around X-axis in degrees (None if failed)
            - tilt_y_deg: Tilt angle around Y-axis in degrees (None if failed)
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Detect ArUco markers
        corners, ids, rejected = cv2.aruco.detectMarkers(
            gray,
            self.aruco_dict,
            parameters=self.detector_params
        )
        
        if ids is None or len(ids) == 0:
            return False, None, None, None
        
        # Refine marker corners to sub-pixel accuracy
        # Interpolate ChArUco corners
        retval, charuco_corners, charuco_ids = cv2.aruco.interpolateCornersCharuco(
            corners,
            ids,
            gray,
            self.board
        )
        
        if charuco_corners is None or len(charuco_corners) < 4:
            # Need at least 4 corners for pose estimation
            return False, None, None, None
        
        # Estimate pose
        if self.camera_matrix is not None and self.dist_coeffs is not None:
            # Absolute pose estimation with camera intrinsics
            retval, rvec, tvec = cv2.aruco.estimatePoseCharucoBoard(
                charuco_corners,
                charuco_ids,
                self.board,
                self.camera_matrix,
                self.dist_coeffs,
                None,
                None
            )
            
            if not retval:
                return False, None, None, None
            
            # Convert rotation vector to rotation matrix
            rotation_matrix, _ = cv2.Rodrigues(rvec)
            
            # Extract surface normal (Z-axis of the board in camera coordinates)
            normal_vector = rotation_matrix[:, 2]
            
            # Calculate tilt angles
            # Tilt X: rotation around X-axis (pitch)
            # Tilt Y: rotation around Y-axis (roll)
            tilt_x = np.arctan2(normal_vector[1], normal_vector[2])
            tilt_y = np.arctan2(-normal_vector[0], normal_vector[2])
            
            tilt_x_deg = np.degrees(tilt_x)
            tilt_y_deg = np.degrees(tilt_y)
            
            return True, normal_vector, tilt_x_deg, tilt_y_deg
            
        else:
            # Relative measurement without camera intrinsics
            # Use homography estimation as fallback
            # This gives relative tilt but not absolute degrees
            
            # Get board corners in 3D
            obj_points = self.board.getChessboardCorners()
            
            # Filter to only detected corners
            obj_points_detected = []
            img_points_detected = []
            
            for i, charuco_id in enumerate(charuco_ids):
                obj_points_detected.append(obj_points[charuco_id[0]])
                img_points_detected.append(charuco_corners[i][0])
            
            obj_points_detected = np.array(obj_points_detected, dtype=np.float32)
            img_points_detected = np.array(img_points_detected, dtype=np.float32)
            
            # Estimate homography
            if len(obj_points_detected) >= 4:
                H, mask = cv2.findHomography(obj_points_detected[:, :2], img_points_detected)
                
                if H is not None:
                    # Extract approximate normal from homography
                    # This is a simplified approach without camera calibration
                    # Provides relative tilt indication
                    
                    # Normalize homography
                    H = H / H[2, 2]
                    
                    # Approximate tilt from homography scaling
                    scale_x = np.linalg.norm(H[:2, 0])
                    scale_y = np.linalg.norm(H[:2, 1])
                    
                    # Relative tilt indicator (not absolute degrees)
                    tilt_x_rel = (scale_x - 1.0) * 100  # percentage deviation
                    tilt_y_rel = (scale_y - 1.0) * 100
                    
                    # Note: Without camera matrix, we can't compute true normal vector
                    normal_approx = np.array([tilt_x_rel, tilt_y_rel, 100.0])
                    normal_approx = normal_approx / np.linalg.norm(normal_approx)
                    
                    return True, normal_approx, tilt_x_rel, tilt_y_rel
            
            return False, None, None, None
    
    def analyze_frame(self, image: np.ndarray) -> dict:
        """
        Analyze frame for both focus and tilt (double duty).
        
        Args:
            image: Camera frame
            
        Returns:
            Dictionary with results:
            {
                'focus_score': float,
                'tilt_detected': bool,
                'normal_vector': np.ndarray or None,
                'tilt_x_deg': float or None,
                'tilt_y_deg': float or None,
                'markers_detected': int
            }
        """
        # Calculate focus score
        focus_score = self.calculate_focus_score(image)
        
        # Detect tilt
        tilt_success, normal_vector, tilt_x, tilt_y = self.detect_tilt(image)
        
        # Count detected markers
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        corners, ids, _ = cv2.aruco.detectMarkers(gray, self.aruco_dict, parameters=self.detector_params)
        num_markers = len(ids) if ids is not None else 0
        
        return {
            'focus_score': focus_score,
            'tilt_detected': tilt_success,
            'normal_vector': normal_vector,
            'tilt_x_deg': tilt_x,
            'tilt_y_deg': tilt_y,
            'markers_detected': num_markers
        }
    
    def draw_detection_overlay(self, image: np.ndarray) -> np.ndarray:
        """
        Draw detection overlay on image for visualization.
        
        Shows:
        - Detected ArUco markers
        - ChArUco corners
        - ROI boundary
        - Coordinate axes (if pose estimated)
        
        Args:
            image: Input image
            
        Returns:
            Image with overlay drawn
        """
        overlay = image.copy()
        
        # Convert to BGR if grayscale
        if len(overlay.shape) == 2:
            overlay = cv2.cvtColor(overlay, cv2.COLOR_GRAY2BGR)
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        # Detect markers
        corners, ids, rejected = cv2.aruco.detectMarkers(
            gray,
            self.aruco_dict,
            parameters=self.detector_params
        )
        
        # Draw detected markers
        if ids is not None:
            cv2.aruco.drawDetectedMarkers(overlay, corners, ids)
            
            # Interpolate ChArUco corners
            retval, charuco_corners, charuco_ids = cv2.aruco.interpolateCornersCharuco(
                corners,
                ids,
                gray,
                self.board
            )
            
            # Draw ChArUco corners
            if charuco_corners is not None:
                cv2.aruco.drawDetectedCornersCharuco(overlay, charuco_corners, charuco_ids)
                
                # Draw coordinate axes if camera calibrated
                if self.camera_matrix is not None and len(charuco_corners) >= 4:
                    retval, rvec, tvec = cv2.aruco.estimatePoseCharucoBoard(
                        charuco_corners,
                        charuco_ids,
                        self.board,
                        self.camera_matrix,
                        self.dist_coeffs,
                        None,
                        None
                    )
                    
                    if retval:
                        # Draw 3D axes
                        axis_length = self.square_length * 2
                        cv2.drawFrameAxes(overlay, self.camera_matrix, self.dist_coeffs, 
                                        rvec, tvec, axis_length, 3)
        
        # Draw ROI boundary
        mask = self._get_roi_mask(overlay.shape[:2])
        roi_contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(overlay, roi_contours, -1, (0, 255, 0), 2)
        
        return overlay


def generate_calibration_pattern(width: int = 1920, 
                                 height: int = 1080,
                                 output_path: str = "charuco_pattern.png"):
    """
    Convenience function to generate ChArUco calibration pattern.
    
    Args:
        width: Pattern width in pixels
        height: Pattern height in pixels
        output_path: Where to save pattern
        
    Returns:
        Pattern as numpy array
    """
    calibrator = ChArucoCalibrator()
    pattern = calibrator.generate_pattern(width, height, output_path)
    return pattern


if __name__ == "__main__":
    # Test pattern generation
    print("ChArUco Calibration Module Test")
    print("=" * 60)
    
    # Create calibrator
    calibrator = ChArucoCalibrator()
    
    # Generate pattern for 1920x1080 projector
    print("\nGenerating ChArUco pattern...")
    pattern = calibrator.generate_pattern(1920, 1080, "charuco_calibration_pattern.png")
    print(f"Pattern size: {pattern.shape}")
    print(f"Pattern saved: charuco_calibration_pattern.png")
    
    print("\nPattern parameters:")
    print(f"  Squares (X × Y): {calibrator.squares_x} × {calibrator.squares_y}")
    print(f"  Square length: {calibrator.square_length} pixels")
    print(f"  Marker length: {calibrator.marker_length} pixels")
    print(f"  ROI fraction: {calibrator.roi_fraction * 100}%")
    
    print("\nReady to use!")
    print("Next steps:")
    print("  1. Project charuco_calibration_pattern.png")
    print("  2. Capture image with camera")
    print("  3. Use analyze_frame() to get focus and tilt")
