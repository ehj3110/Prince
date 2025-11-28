"""
Automated Calibration Workflow
================================

Integrated calibration system with DLP projection control, automatic camera
optimization, and real-time guidance for tank alignment.

Workflow:
1. User clicks "Start Calibration" button
2. System projects ChArUco pattern (DLP power = 10)
3. Auto-optimizes camera exposure/gain for marker detection
4. Continuously measures focus and tilt in real-time
5. Provides live guidance: "Move tank lower", "Tilt left", etc.
6. User adjusts hardware while seeing live feedback
7. When optimal, user clicks "Accept Calibration"
8. System saves calibration data and returns DLP to normal

Author: Cheng Sun Lab Team
Date: November 28, 2025
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import numpy as np
from datetime import datetime
from typing import Optional, Tuple, Dict
import os


class CalibrationWorkflow:
    """
    Automated calibration workflow with DLP control and real-time guidance.
    """
    
    def __init__(self, camera_manager, dlp_controller=None):
        """
        Initialize calibration workflow.
        
        Args:
            camera_manager: AlliedVisionCameraManager instance
            dlp_controller: DLP projector controller (if available)
        """
        self.camera_manager = camera_manager
        self.dlp_controller = dlp_controller
        
        # Calibration state
        self.is_calibrating = False
        self.calibration_thread = None
        self.stop_calibration_event = threading.Event()
        
        # Current measurements
        self.current_focus = 0.0
        self.current_tilt_x = 0.0
        self.current_tilt_y = 0.0
        self.current_markers = 0
        
        # Target thresholds
        self.target_focus_min = 500  # Minimum acceptable focus
        self.target_tilt_max = 2.0   # Maximum acceptable tilt (degrees)
        
        # Measurement history for stability detection
        self.focus_history = []
        self.tilt_x_history = []
        self.tilt_y_history = []
        self.history_length = 10  # Number of samples to average
        
        # Auto-optimization parameters
        self.exposure_min = 5000    # 5ms
        self.exposure_max = 50000   # 50ms
        self.exposure_step = 2000   # 2ms steps
        self.gain_min = 0
        self.gain_max = 20
        self.gain_step = 2
        
        # Pattern path (will be generated)
        self.pattern_path = None
        
        # Callbacks for UI updates
        self.update_callback = None  # Called with measurement dict
        self.guidance_callback = None  # Called with guidance string
        self.status_callback = None  # Called with status string
    
    def set_callbacks(self, update_callback, guidance_callback, status_callback):
        """
        Set callbacks for UI updates.
        
        Args:
            update_callback: Function(dict) - receives measurement data
            guidance_callback: Function(str) - receives guidance text
            status_callback: Function(str) - receives status text
        """
        self.update_callback = update_callback
        self.guidance_callback = guidance_callback
        self.status_callback = status_callback
    
    def start_calibration(self) -> bool:
        """
        Start automated calibration workflow.
        
        Returns:
            True if started successfully, False otherwise
        """
        if self.is_calibrating:
            print("Calibration already in progress")
            return False
        
        if not self.camera_manager.camera:
            print("ERROR: Camera not connected")
            return False
        
        # Generate ChArUco pattern if needed
        if not self._prepare_pattern():
            return False
        
        # Project pattern
        if not self._project_pattern():
            return False
        
        # Start calibration thread
        self.stop_calibration_event.clear()
        self.is_calibrating = True
        self.calibration_thread = threading.Thread(target=self._calibration_loop, daemon=True)
        self.calibration_thread.start()
        
        return True
    
    def stop_calibration(self):
        """Stop calibration workflow and restore DLP."""
        if not self.is_calibrating:
            return
        
        print("Stopping calibration...")
        self.stop_calibration_event.set()
        
        if self.calibration_thread and self.calibration_thread.is_alive():
            self.calibration_thread.join(timeout=3.0)
        
        self._restore_dlp()
        self.is_calibrating = False
        
        if self.status_callback:
            self.status_callback("Calibration stopped")
    
    def accept_calibration(self) -> Dict:
        """
        Accept current calibration and save data.
        
        Returns:
            Dictionary with calibration results
        """
        if not self.is_calibrating:
            return None
        
        # Calculate stable averages
        focus_avg = np.mean(self.focus_history) if self.focus_history else self.current_focus
        tilt_x_avg = np.mean(self.tilt_x_history) if self.tilt_x_history else self.current_tilt_x
        tilt_y_avg = np.mean(self.tilt_y_history) if self.tilt_y_history else self.current_tilt_y
        
        calibration_data = {
            'timestamp': datetime.now().isoformat(),
            'focus_score': focus_avg,
            'tilt_x_deg': tilt_x_avg,
            'tilt_y_deg': tilt_y_avg,
            'exposure_us': self.camera_manager.exposure_time,
            'gain_db': self.camera_manager.gain,
            'markers_detected': self.current_markers,
            'within_tolerance': self._is_within_tolerance()
        }
        
        # Save to file
        self._save_calibration_data(calibration_data)
        
        # Stop calibration
        self.stop_calibration()
        
        return calibration_data
    
    def _prepare_pattern(self) -> bool:
        """Generate ChArUco pattern if not already available."""
        # Check if pattern already exists
        pattern_dir = "calibration_patterns"
        os.makedirs(pattern_dir, exist_ok=True)
        
        self.pattern_path = os.path.join(pattern_dir, "charuco_calibration.png")
        
        if os.path.exists(self.pattern_path):
            print(f"Using existing pattern: {self.pattern_path}")
            return True
        
        # Generate new pattern (assume 1920x1080 DLP projector)
        print("Generating ChArUco pattern...")
        try:
            success = self.camera_manager.generate_charuco_pattern(
                1920, 1080, self.pattern_path
            )
            if success:
                print(f"Pattern generated: {self.pattern_path}")
                return True
            else:
                print("ERROR: Failed to generate pattern")
                return False
        except Exception as e:
            print(f"ERROR generating pattern: {e}")
            return False
    
    def _project_pattern(self) -> bool:
        """Project ChArUco pattern with DLP at power=10."""
        if self.dlp_controller is None:
            print("WARNING: No DLP controller available")
            print(f"Please manually project: {self.pattern_path}")
            print("Set DLP power to 10")
            return True  # Continue anyway
        
        try:
            # Set DLP power to 10 for calibration
            self.dlp_controller.set_power(10)
            
            # Project pattern
            self.dlp_controller.project_image(self.pattern_path)
            
            print("ChArUco pattern projected (DLP power = 10)")
            return True
            
        except Exception as e:
            print(f"ERROR projecting pattern: {e}")
            return False
    
    def _restore_dlp(self):
        """Restore DLP to normal operating state."""
        if self.dlp_controller is None:
            print("Please manually restore DLP to normal power")
            return
        
        try:
            # Clear projection
            self.dlp_controller.clear()
            
            # Restore normal power (you may want to set specific value)
            # self.dlp_controller.set_power(100)  # or whatever is normal
            
            print("DLP restored to normal state")
            
        except Exception as e:
            print(f"ERROR restoring DLP: {e}")
    
    def _auto_optimize_camera(self) -> bool:
        """
        Automatically optimize camera exposure and gain for ChArUco detection.
        
        Strategy:
        1. Start with mid-range exposure, low gain
        2. Capture frame and count detected markers
        3. Adjust exposure/gain to maximize marker detection
        4. Ensure pattern is not over/under exposed
        
        Returns:
            True if optimization successful, False otherwise
        """
        if self.status_callback:
            self.status_callback("Optimizing camera settings...")
        
        print("Auto-optimizing camera for ChArUco detection...")
        
        best_markers = 0
        best_exposure = 10000
        best_gain = 0
        
        # Quick scan: try a few exposure values with low gain
        test_exposures = [5000, 10000, 15000, 20000, 30000]
        
        for exposure in test_exposures:
            if self.stop_calibration_event.is_set():
                return False
            
            self.camera_manager.set_exposure(exposure)
            time.sleep(0.2)  # Let camera adjust
            
            # Capture frame
            frame = self.camera_manager.capture_single_frame()
            if frame is None:
                continue
            
            # Count markers
            results = self.camera_manager.analyze_calibration_frame(frame)
            markers = results['markers_detected']
            
            print(f"  Exposure {exposure}µs: {markers} markers")
            
            if markers > best_markers:
                best_markers = markers
                best_exposure = exposure
                best_gain = 0
        
        # If not enough markers, try increasing gain
        if best_markers < 4:
            print("  Low marker count, trying higher gain...")
            for gain in [5, 10, 15]:
                if self.stop_calibration_event.is_set():
                    return False
                
                self.camera_manager.set_exposure(best_exposure)
                self.camera_manager.set_gain(gain)
                time.sleep(0.2)
                
                frame = self.camera_manager.capture_single_frame()
                if frame is None:
                    continue
                
                results = self.camera_manager.analyze_calibration_frame(frame)
                markers = results['markers_detected']
                
                print(f"  Gain {gain}dB: {markers} markers")
                
                if markers > best_markers:
                    best_markers = markers
                    best_gain = gain
        
        # Apply best settings
        self.camera_manager.set_exposure(best_exposure)
        self.camera_manager.set_gain(best_gain)
        
        print(f"Optimized: Exposure={best_exposure}µs, Gain={best_gain}dB, Markers={best_markers}")
        
        if self.status_callback:
            self.status_callback(f"Camera optimized: {best_markers} markers detected")
        
        return best_markers >= 4  # Need at least 4 markers for pose estimation
    
    def _calibration_loop(self):
        """
        Main calibration loop - runs in separate thread.
        
        Continuously:
        1. Captures frames
        2. Analyzes focus and tilt
        3. Generates guidance
        4. Updates UI
        """
        # Auto-optimize camera first
        if not self._auto_optimize_camera():
            if self.status_callback:
                self.status_callback("ERROR: Could not detect ChArUco markers")
            if self.guidance_callback:
                self.guidance_callback("Cannot detect calibration pattern.\nCheck projection and camera focus.")
            self.is_calibrating = False
            return
        
        # Start streaming
        if not self.camera_manager.is_streaming:
            self.camera_manager.start_streaming(self._frame_callback)
        
        if self.status_callback:
            self.status_callback("Calibration active - Adjust tank as guided")
        
        # Continuous measurement loop
        while not self.stop_calibration_event.is_set():
            try:
                # Capture and analyze frame
                frame = self.camera_manager.capture_single_frame()
                if frame is not None:
                    self._process_calibration_frame(frame)
                
                time.sleep(0.1)  # 10 Hz update rate
                
            except Exception as e:
                print(f"ERROR in calibration loop: {e}")
                time.sleep(0.5)
        
        print("Calibration loop ended")
    
    def _frame_callback(self, frame):
        """Callback for streaming frames (optional, for live display)."""
        pass  # Live display handled by camera window
    
    def _process_calibration_frame(self, frame):
        """
        Process single calibration frame and update guidance.
        
        Args:
            frame: Camera frame (numpy array)
        """
        # Analyze frame
        results = self.camera_manager.analyze_calibration_frame(frame)
        
        # Update current measurements
        self.current_focus = results['focus_score']
        self.current_tilt_x = results['tilt_x_deg'] if results['tilt_detected'] else 0.0
        self.current_tilt_y = results['tilt_y_deg'] if results['tilt_detected'] else 0.0
        self.current_markers = results['markers_detected']
        
        # Update history for stability
        self.focus_history.append(self.current_focus)
        self.tilt_x_history.append(self.current_tilt_x)
        self.tilt_y_history.append(self.current_tilt_y)
        
        # Keep history to fixed length
        if len(self.focus_history) > self.history_length:
            self.focus_history.pop(0)
            self.tilt_x_history.pop(0)
            self.tilt_y_history.pop(0)
        
        # Generate guidance
        guidance = self._generate_guidance()
        
        # Update UI via callbacks
        if self.update_callback:
            self.update_callback(results)
        
        if self.guidance_callback:
            self.guidance_callback(guidance)
    
    def _generate_guidance(self) -> str:
        """
        Generate human-readable guidance based on current measurements.
        
        Returns:
            Guidance string with adjustment recommendations
        """
        guidance_lines = []
        
        # Check markers
        if self.current_markers == 0:
            return "⚠️ NO MARKERS DETECTED\n\nCheck:\n- Pattern is projected\n- Camera can see pattern\n- Adjust exposure/gain"
        elif self.current_markers < 4:
            guidance_lines.append(f"⚠️ Only {self.current_markers} markers detected")
            guidance_lines.append("Need at least 4 for accurate tilt")
        
        # Check focus
        # Note: Moving stage UP = surface further from camera = worse focus
        # Note: Moving stage DOWN = surface closer to camera = better focus
        if self.current_focus < 100:
            guidance_lines.append("❌ FOCUS: Very poor - Adjust camera focus or tank position")
        elif self.current_focus < 300:
            guidance_lines.append("⚠️ FOCUS: Poor - Move stage DOWN (bring surface closer)")
        elif self.current_focus < self.target_focus_min:
            guidance_lines.append("⚙️ FOCUS: Fair - Move stage down slightly")
        elif self.current_focus < 1000:
            guidance_lines.append("✓ FOCUS: Good")
        else:
            guidance_lines.append("✓✓ FOCUS: Excellent")
        
        # Check tilt (only if enough markers)
        if self.current_markers >= 4:
            tilt_x = self.current_tilt_x
            tilt_y = self.current_tilt_y
            
            # X-axis tilt (pitch) - positive = front down
            if abs(tilt_x) > 5:
                direction = "FORWARD" if tilt_x > 0 else "BACKWARD"
                guidance_lines.append(f"❌ TILT X: Tip tank {direction} ({tilt_x:+.1f}°)")
            elif abs(tilt_x) > self.target_tilt_max:
                direction = "forward" if tilt_x > 0 else "backward"
                guidance_lines.append(f"⚙️ TILT X: Tip tank {direction} slightly ({tilt_x:+.1f}°)")
            elif abs(tilt_x) > 1:
                guidance_lines.append(f"✓ TILT X: Good ({tilt_x:+.1f}°)")
            else:
                guidance_lines.append(f"✓✓ TILT X: Excellent ({tilt_x:+.1f}°)")
            
            # Y-axis tilt (roll) - positive = right side down
            if abs(tilt_y) > 5:
                direction = "LEFT" if tilt_y > 0 else "RIGHT"
                guidance_lines.append(f"❌ TILT Y: Tilt tank {direction} ({tilt_y:+.1f}°)")
            elif abs(tilt_y) > self.target_tilt_max:
                direction = "left" if tilt_y > 0 else "right"
                guidance_lines.append(f"⚙️ TILT Y: Tilt tank {direction} slightly ({tilt_y:+.1f}°)")
            elif abs(tilt_y) > 1:
                guidance_lines.append(f"✓ TILT Y: Good ({tilt_y:+.1f}°)")
            else:
                guidance_lines.append(f"✓✓ TILT Y: Excellent ({tilt_y:+.1f}°)")
        
        # Overall status
        if self._is_within_tolerance():
            guidance_lines.append("\n🎯 CALIBRATION OPTIMAL")
            guidance_lines.append("Click 'Accept Calibration' to save")
        elif self._is_improving():
            guidance_lines.append("\n📈 Getting better...")
        
        return "\n".join(guidance_lines)
    
    def _is_within_tolerance(self) -> bool:
        """Check if current measurements are within acceptable tolerance."""
        focus_ok = self.current_focus >= self.target_focus_min
        tilt_x_ok = abs(self.current_tilt_x) <= self.target_tilt_max
        tilt_y_ok = abs(self.current_tilt_y) <= self.target_tilt_max
        markers_ok = self.current_markers >= 4
        
        return focus_ok and tilt_x_ok and tilt_y_ok and markers_ok
    
    def _is_improving(self) -> bool:
        """Check if measurements are trending towards better values."""
        if len(self.focus_history) < 3:
            return False
        
        # Check if focus is increasing (recent > older)
        recent_focus = np.mean(self.focus_history[-3:])
        older_focus = np.mean(self.focus_history[:3])
        focus_improving = recent_focus > older_focus
        
        # Check if tilt is decreasing
        recent_tilt = np.mean([abs(self.tilt_x_history[-1]), abs(self.tilt_y_history[-1])])
        older_tilt = np.mean([abs(self.tilt_x_history[0]), abs(self.tilt_y_history[0])])
        tilt_improving = recent_tilt < older_tilt
        
        return focus_improving or tilt_improving
    
    def _save_calibration_data(self, data: Dict):
        """Save calibration data to log file."""
        log_dir = "calibration_logs"
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, "calibration_history.txt")
        
        try:
            with open(log_file, 'a') as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"Calibration: {data['timestamp']}\n")
                f.write(f"{'='*60}\n")
                f.write(f"Focus Score: {data['focus_score']:.2f}\n")
                f.write(f"Tilt X: {data['tilt_x_deg']:+.2f}°\n")
                f.write(f"Tilt Y: {data['tilt_y_deg']:+.2f}°\n")
                f.write(f"Exposure: {data['exposure_us']} µs\n")
                f.write(f"Gain: {data['gain_db']} dB\n")
                f.write(f"Markers: {data['markers_detected']}\n")
                f.write(f"Within Tolerance: {data['within_tolerance']}\n")
            
            print(f"Calibration data saved to: {log_file}")
            
        except Exception as e:
            print(f"ERROR saving calibration data: {e}")
    
    def get_current_state(self) -> Dict:
        """Get current calibration state for display."""
        return {
            'is_calibrating': self.is_calibrating,
            'focus_score': self.current_focus,
            'tilt_x_deg': self.current_tilt_x,
            'tilt_y_deg': self.current_tilt_y,
            'markers_detected': self.current_markers,
            'within_tolerance': self._is_within_tolerance(),
            'exposure_us': self.camera_manager.exposure_time if self.camera_manager else 0,
            'gain_db': self.camera_manager.gain if self.camera_manager else 0
        }


if __name__ == "__main__":
    print("Calibration Workflow Module")
    print("=" * 60)
    print("This module provides automated calibration workflow.")
    print("Use with CameraViewWindow for integrated calibration.")
