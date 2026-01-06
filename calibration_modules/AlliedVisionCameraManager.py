"""
Allied Vision Camera Manager
=============================

Manages Allied Vision USB camera for resin tank alignment and calibration.

Features:
- Camera initialization and connection
- Live video stream display
- Image capture for analysis
- Focus detection (placeholder for future implementation)
- Tilt/tip detection (placeholder for future implementation)

Compatible with Allied Vision Vimba SDK.

Author: Cheng Sun Lab Team
Date: November 28, 2025
"""

import threading
import time
from typing import Optional, Callable
import numpy as np

try:
    from vimba import Vimba, Camera, Frame
    VIMBA_AVAILABLE = True
except ImportError:
    VIMBA_AVAILABLE = False
    print("WARNING: Vimba SDK not installed. Camera functionality will be limited.")
    print("Install with: pip install vimba")

try:
    from .ChArucoCalibrator import ChArucoCalibrator
    CHARUCO_AVAILABLE = True
except ImportError:
    try:
        from ChArucoCalibrator import ChArucoCalibrator
        CHARUCO_AVAILABLE = True
    except ImportError:
        CHARUCO_AVAILABLE = False
        print("WARNING: ChArUco calibrator not available. Focus/tilt detection will be limited.")


class AlliedVisionCameraManager:
    """
    Manages Allied Vision USB camera for resin tank calibration and alignment.
    """
    
    def __init__(self):
        """Initialize camera manager"""
        self.camera: Optional[Camera] = None
        self.vimba: Optional[Vimba] = None
        self.is_streaming = False
        self.frame_callback: Optional[Callable] = None
        self.streaming_thread: Optional[threading.Thread] = None
        self.stop_streaming_event = threading.Event()
        
        # Camera settings
        self.exposure_time = 10000  # microseconds (10ms default)
        self.gain = 0  # dB
        
        # ChArUco calibrator for focus and tilt detection
        self.charuco_calibrator = ChArucoCalibrator() if CHARUCO_AVAILABLE else None
        
        # Calibration data
        self.focus_score = None
        self.tilt_angle_x = None
        self.tilt_angle_y = None
        self.normal_vector = None
        self.markers_detected = 0
        
    def connect(self) -> bool:
        """
        Connect to the Allied Vision camera.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        if not VIMBA_AVAILABLE:
            print("ERROR: Vimba SDK not available")
            return False
        
        try:
            # Initialize Vimba
            self.vimba = Vimba.get_instance()
            self.vimba.__enter__()
            
            # Get available cameras
            cameras = self.vimba.get_all_cameras()
            
            if not cameras:
                print("ERROR: No Allied Vision cameras found")
                return False
            
            # Connect to first available camera
            self.camera = cameras[0]
            self.camera.__enter__()
            
            print(f"Connected to camera: {self.camera.get_id()}")
            print(f"Camera model: {self.camera.get_model()}")
            
            # Configure camera
            self._configure_camera()
            
            return True
            
        except Exception as e:
            print(f"ERROR connecting to camera: {e}")
            return False
    
    def _configure_camera(self):
        """Configure camera settings"""
        try:
            # Set pixel format (adjust based on your camera model)
            self.camera.set_pixel_format(self.camera.get_pixel_formats()[0])
            
            # Set exposure time
            self.camera.ExposureTime.set(self.exposure_time)
            
            # Set gain
            self.camera.Gain.set(self.gain)
            
            print("Camera configured successfully")
            
        except Exception as e:
            print(f"WARNING: Could not configure all camera settings: {e}")
    
    def disconnect(self):
        """Disconnect from camera and cleanup"""
        self.stop_streaming()
        
        if self.camera:
            try:
                self.camera.__exit__(None, None, None)
                self.camera = None
            except Exception as e:
                print(f"WARNING: Error disconnecting camera: {e}")
        
        if self.vimba:
            try:
                self.vimba.__exit__(None, None, None)
                self.vimba = None
            except Exception as e:
                print(f"WARNING: Error cleaning up Vimba: {e}")
    
    def start_streaming(self, frame_callback: Callable):
        """
        Start continuous frame acquisition.
        
        Args:
            frame_callback: Function to call with each frame (receives numpy array)
        """
        if not self.camera:
            print("ERROR: Camera not connected")
            return
        
        if self.is_streaming:
            print("WARNING: Already streaming")
            return
        
        self.frame_callback = frame_callback
        self.stop_streaming_event.clear()
        self.is_streaming = True
        
        # Start streaming in separate thread
        self.streaming_thread = threading.Thread(target=self._streaming_loop, daemon=True)
        self.streaming_thread.start()
        
        print("Camera streaming started")
    
    def _streaming_loop(self):
        """Internal streaming loop (runs in separate thread)"""
        self._frame_count = 0
        try:
            # Start frame acquisition
            self.camera.start_streaming(handler=self._frame_handler)
            
            # Keep streaming until stop event
            while not self.stop_streaming_event.is_set():
                time.sleep(0.01)
            
            # Stop acquisition
            self.camera.stop_streaming()
            
        except Exception as e:
            print(f"ERROR in streaming loop: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.is_streaming = False
    
    def _frame_handler(self, cam: Camera, frame: Frame):
        """
        Handle incoming frames from camera.
        
        Args:
            cam: Camera object
            frame: Frame object from Vimba
        """
        try:
            self._frame_count += 1
            
            # Convert frame to numpy array
            if frame.get_status() == 0:  # Frame is valid
                # CRITICAL: Make a copy of the frame data before it's requeued
                image = frame.as_numpy_ndarray().copy()
                
                # Call user callback with image
                if self.frame_callback:
                    self.frame_callback(image)
            
            # CRITICAL: Requeue the frame back to the camera for continuous streaming
            cam.queue_frame(frame)
                    
        except Exception as e:
            print(f"ERROR processing frame {self._frame_count}: {e}")
            import traceback
            traceback.print_exc()
    
    def stop_streaming(self):
        """Stop continuous frame acquisition"""
        if not self.is_streaming:
            return
        
        print("Stopping camera streaming...")
        self.stop_streaming_event.set()
        
        # Wait for thread to finish
        if self.streaming_thread and self.streaming_thread.is_alive():
            self.streaming_thread.join(timeout=2.0)
        
        self.is_streaming = False
        print("Camera streaming stopped")
    
    def capture_single_frame(self) -> Optional[np.ndarray]:
        """
        Capture a single frame.
        
        Returns:
            numpy array of image, or None if capture failed
        """
        if not self.camera:
            print("ERROR: Camera not connected")
            return None
        
        try:
            # Get a single frame
            frame = self.camera.get_frame()
            
            if frame.get_status() == 0:
                return frame.as_numpy_ndarray()
            else:
                print("ERROR: Frame capture failed")
                return None
                
        except Exception as e:
            print(f"ERROR capturing frame: {e}")
            return None
    
    def set_exposure(self, exposure_us: float):
        """
        Set camera exposure time.
        
        Args:
            exposure_us: Exposure time in microseconds
        """
        if not self.camera:
            print("ERROR: Camera not connected")
            return
        
        try:
            self.camera.ExposureTime.set(exposure_us)
            self.exposure_time = exposure_us
            print(f"Exposure set to {exposure_us} µs")
        except Exception as e:
            print(f"ERROR setting exposure: {e}")
    
    def set_gain(self, gain_db: float):
        """
        Set camera gain.
        
        Args:
            gain_db: Gain in dB
        """
        if not self.camera:
            print("ERROR: Camera not connected")
            return
        
        try:
            self.camera.Gain.set(gain_db)
            self.gain = gain_db
            print(f"Gain set to {gain_db} dB")
        except Exception as e:
            print(f"ERROR setting gain: {e}")
    
    def get_camera_info(self) -> dict:
        """
        Get camera information.
        
        Returns:
            Dictionary with camera information
        """
        if not self.camera:
            return {"status": "Not connected"}
        
        try:
            return {
                "id": self.camera.get_id(),
                "model": self.camera.get_model(),
                "exposure": self.exposure_time,
                "gain": self.gain,
                "streaming": self.is_streaming
            }
        except Exception as e:
            return {"error": str(e)}
    
    # ========================================================================
    # CALIBRATION METHODS (ChArUco-based implementation)
    # ========================================================================
    
    def set_camera_intrinsics(self, camera_matrix: np.ndarray, dist_coeffs: np.ndarray):
        """
        Set camera intrinsic parameters for absolute tilt measurement.
        
        Args:
            camera_matrix: 3x3 camera intrinsic matrix
            dist_coeffs: Distortion coefficients
        """
        if self.charuco_calibrator:
            self.charuco_calibrator.set_camera_intrinsics(camera_matrix, dist_coeffs)
    
    def generate_charuco_pattern(self, width: int, height: int, output_path: str) -> bool:
        """
        Generate ChArUco calibration pattern for projection.
        
        Args:
            width: Pattern width in pixels (projector resolution)
            height: Pattern height in pixels
            output_path: Where to save pattern
            
        Returns:
            True if successful, False otherwise
        """
        if not self.charuco_calibrator:
            print("ERROR: ChArUco calibrator not available")
            return False
        
        try:
            self.charuco_calibrator.generate_pattern(width, height, output_path)
            return True
        except Exception as e:
            print(f"ERROR generating pattern: {e}")
            return False
    
    def calculate_focus_score(self, image: np.ndarray) -> float:
        """
        Calculate focus score using ChArUco pattern (Laplacian variance / MTF proxy).
        
        Uses only center ROI (inner 50%) to avoid vignetting effects.
        Higher score = better focus.
        
        Args:
            image: Camera frame as numpy array
            
        Returns:
            Focus score (higher = sharper)
        """
        if not self.charuco_calibrator:
            print("ERROR: ChArUco calibrator not available")
            self.focus_score = 0.0
            return 0.0
        
        try:
            self.focus_score = self.charuco_calibrator.calculate_focus_score(image)
            return self.focus_score
        except Exception as e:
            print(f"ERROR calculating focus: {e}")
            self.focus_score = 0.0
            return 0.0
    
    def calculate_tilt(self, image: np.ndarray) -> tuple:
        """
        Calculate tilt/tip of surface using ChArUco marker pose estimation.
        
        Works with limited FOV (inner 50%) due to unique marker identification.
        
        Args:
            image: Camera frame as numpy array
            
        Returns:
            Tuple of (tilt_x, tilt_y) angles in degrees
            Returns (0.0, 0.0) if detection fails
        """
        if not self.charuco_calibrator:
            print("ERROR: ChArUco calibrator not available")
            self.tilt_angle_x = 0.0
            self.tilt_angle_y = 0.0
            return (0.0, 0.0)
        
        try:
            success, normal_vector, tilt_x, tilt_y = self.charuco_calibrator.detect_tilt(image)
            
            if success:
                self.tilt_angle_x = tilt_x
                self.tilt_angle_y = tilt_y
                self.normal_vector = normal_vector
                return (tilt_x, tilt_y)
            else:
                self.tilt_angle_x = 0.0
                self.tilt_angle_y = 0.0
                self.normal_vector = None
                return (0.0, 0.0)
                
        except Exception as e:
            print(f"ERROR calculating tilt: {e}")
            self.tilt_angle_x = 0.0
            self.tilt_angle_y = 0.0
            self.normal_vector = None
            return (0.0, 0.0)
    
    def analyze_calibration_frame(self, image: np.ndarray) -> dict:
        """
        Analyze frame for both focus and tilt simultaneously (double duty).
        
        Args:
            image: Camera frame as numpy array
            
        Returns:
            Dictionary with:
            {
                'focus_score': float,
                'tilt_x_deg': float,
                'tilt_y_deg': float,
                'normal_vector': np.ndarray or None,
                'tilt_detected': bool,
                'markers_detected': int
            }
        """
        if not self.charuco_calibrator:
            print("ERROR: ChArUco calibrator not available")
            return {
                'focus_score': 0.0,
                'tilt_x_deg': 0.0,
                'tilt_y_deg': 0.0,
                'normal_vector': None,
                'tilt_detected': False,
                'markers_detected': 0
            }
        
        try:
            results = self.charuco_calibrator.analyze_frame(image)
            
            # Update internal state
            self.focus_score = results['focus_score']
            self.tilt_angle_x = results['tilt_x_deg']
            self.tilt_angle_y = results['tilt_y_deg']
            self.normal_vector = results['normal_vector']
            self.markers_detected = results['markers_detected']
            
            return results
            
        except Exception as e:
            print(f"ERROR analyzing frame: {e}")
            return {
                'focus_score': 0.0,
                'tilt_x_deg': 0.0,
                'tilt_y_deg': 0.0,
                'normal_vector': None,
                'tilt_detected': False,
                'markers_detected': 0
            }
    
    def auto_focus(self) -> bool:
        """
        Automatically adjust focus (if camera supports motorized focus).
        
        Returns:
            True if focus successful, False otherwise
            
        TODO: Implement auto-focus routine if hardware supports it
        """
        print("WARNING: Auto-focus not yet implemented")
        return False
    
    def save_calibration_image(self, filename: str) -> bool:
        """
        Save current frame for calibration purposes.
        
        Args:
            filename: Path to save image
            
        Returns:
            True if save successful, False otherwise
        """
        try:
            import cv2
            
            image = self.capture_single_frame()
            if image is not None:
                cv2.imwrite(filename, image)
                print(f"Calibration image saved: {filename}")
                return True
            else:
                print("ERROR: Could not capture image")
                return False
                
        except Exception as e:
            print(f"ERROR saving image: {e}")
            return False


# ============================================================================
# Utility Functions
# ============================================================================

def list_available_cameras() -> list:
    """
    List all available Allied Vision cameras.
    
    Returns:
        List of camera IDs
    """
    if not VIMBA_AVAILABLE:
        print("ERROR: Vimba SDK not available")
        return []
    
    try:
        with Vimba.get_instance() as vimba:
            cameras = vimba.get_all_cameras()
            return [cam.get_id() for cam in cameras]
    except Exception as e:
        print(f"ERROR listing cameras: {e}")
        return []


if __name__ == "__main__":
    # Test camera connection
    print("Allied Vision Camera Manager Test")
    print("=" * 50)
    
    print("\nSearching for cameras...")
    cameras = list_available_cameras()
    
    if cameras:
        print(f"Found {len(cameras)} camera(s):")
        for cam_id in cameras:
            print(f"  - {cam_id}")
    else:
        print("No cameras found")
