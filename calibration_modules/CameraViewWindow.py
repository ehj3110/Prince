"""
Camera View Window
==================

Real-time camera viewing window for resin tank alignment and calibration.

Features:
- Live video display from Allied Vision camera
- Exposure and gain controls
- Snapshot capture
- Focus score display (placeholder)
- Tilt angle display (placeholder)

Author: Cheng Sun Lab Team
Date: November 28, 2025
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import numpy as np
from datetime import datetime
import os

try:
    from .AlliedVisionCameraManager import AlliedVisionCameraManager
    from .CalibrationWorkflow import CalibrationWorkflow
except ImportError:
    from AlliedVisionCameraManager import AlliedVisionCameraManager
    from CalibrationWorkflow import CalibrationWorkflow


class CameraViewWindow:
    """
    Real-time camera viewing window for alignment and calibration.
    """
    
    def __init__(self, parent=None, dlp_controller=None):
        """
        Initialize camera view window.
        
        Args:
            parent: Parent Tkinter window (optional)
            dlp_controller: DLP projector controller (optional)
        """
        self.parent = parent
        self.dlp_controller = dlp_controller
        self.camera_manager = AlliedVisionCameraManager()
        
        # Calibration workflow
        self.calibration_workflow = CalibrationWorkflow(
            self.camera_manager,
            dlp_controller
        )
        self.calibration_workflow.set_callbacks(
            self.on_calibration_update,
            self.on_guidance_update,
            self.on_status_update
        )
        
        # Create window
        self.window = tk.Toplevel(parent) if parent else tk.Tk()
        self.window.title("Camera View - Resin Tank Alignment")
        self.window.geometry("1200x800")
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Current image data
        self.current_image = None
        self.display_image = None
        
        # Build UI
        self._build_ui()
        
        # Try to connect to camera
        self.connect_camera()
    
    def _build_ui(self):
        """Build user interface"""
        # Main container
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)
        
        # Title
        title_label = ttk.Label(
            main_frame, 
            text="Allied Vision Camera - Resin Tank Alignment", 
            font=('Arial', 14, 'bold')
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 10))
        
        # Left panel - Camera view
        left_frame = ttk.LabelFrame(main_frame, text="Camera View", padding="5")
        left_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        
        # Camera canvas
        self.canvas = tk.Canvas(left_frame, width=800, height=600, bg='black')
        self.canvas.pack(padx=5, pady=5)
        
        # Right panel - Controls
        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Automated calibration panel
        self._build_calibration_panel(right_frame)
        
        # Camera controls
        self._build_camera_controls(right_frame)
        
        # Calibration info
        self._build_calibration_info(right_frame)
        
        # Action buttons
        self._build_action_buttons(right_frame)
        
        # Status bar
        self.status_var = tk.StringVar(value="Camera not connected")
        status_label = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_label.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # Configure grid weights
        main_frame.columnconfigure(0, weight=3)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
    
    def _build_calibration_panel(self, parent):
        """Build automated calibration panel"""
        cal_panel = ttk.LabelFrame(parent, text="🎯 Automated Calibration", padding="5")
        cal_panel.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Info label
        info_label = ttk.Label(
            cal_panel,
            text="Start calibration to automatically:\n"
                 "• Project ChArUco pattern (DLP=10)\n"
                 "• Optimize camera settings\n"
                 "• Get real-time adjustment guidance",
            font=('Arial', 8),
            foreground='gray'
        )
        info_label.grid(row=0, column=0, columnspan=2, pady=(0, 10))
        
        # Start/Stop button
        self.calibration_button = ttk.Button(
            cal_panel,
            text="🚀 Start Calibration",
            command=self.toggle_calibration,
            style='Accent.TButton'
        )
        self.calibration_button.grid(row=1, column=0, columnspan=2, pady=5, sticky=(tk.W, tk.E))
        
        # Accept button (initially disabled)
        self.accept_button = ttk.Button(
            cal_panel,
            text="✓ Accept Calibration",
            command=self.accept_calibration,
            state=tk.DISABLED
        )
        self.accept_button.grid(row=2, column=0, columnspan=2, pady=5, sticky=(tk.W, tk.E))
        
        # Real-time guidance display
        guidance_label = ttk.Label(cal_panel, text="Guidance:", font=('Arial', 9, 'bold'))
        guidance_label.grid(row=3, column=0, columnspan=2, pady=(10, 0), sticky=tk.W)
        
        # Guidance text area
        guidance_frame = ttk.Frame(cal_panel)
        guidance_frame.grid(row=4, column=0, columnspan=2, pady=5, sticky=(tk.W, tk.E))
        
        self.guidance_text = tk.Text(
            guidance_frame,
            height=8,
            width=35,
            wrap=tk.WORD,
            font=('Courier', 9),
            bg='#f0f0f0',
            relief=tk.SUNKEN
        )
        self.guidance_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        guidance_scroll = ttk.Scrollbar(guidance_frame, command=self.guidance_text.yview)
        guidance_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.guidance_text.config(yscrollcommand=guidance_scroll.set)
        
        # Initial guidance message
        self.guidance_text.insert('1.0', "Click 'Start Calibration' to begin.\n\n"
                                         "The system will:\n"
                                         "1. Project ChArUco pattern\n"
                                         "2. Auto-tune camera\n"
                                         "3. Guide your adjustments\n"
                                         "4. Monitor in real-time")
        self.guidance_text.config(state=tk.DISABLED)
    
    def _build_camera_controls(self, parent):
        """Build camera control widgets"""
        control_frame = ttk.LabelFrame(parent, text="Camera Controls", padding="5")
        control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Connection button
        self.connect_button = ttk.Button(
            control_frame, 
            text="Connect Camera", 
            command=self.toggle_connection
        )
        self.connect_button.grid(row=0, column=0, columnspan=2, pady=5, sticky=(tk.W, tk.E))
        
        # Streaming button
        self.stream_button = ttk.Button(
            control_frame, 
            text="Start Streaming", 
            command=self.toggle_streaming,
            state=tk.DISABLED
        )
        self.stream_button.grid(row=1, column=0, columnspan=2, pady=5, sticky=(tk.W, tk.E))
        
        # Exposure control
        ttk.Label(control_frame, text="Exposure (µs):").grid(row=2, column=0, sticky=tk.W, pady=(10, 0))
        self.exposure_var = tk.StringVar(value="10000")
        exposure_entry = ttk.Entry(control_frame, textvariable=self.exposure_var, width=10)
        exposure_entry.grid(row=2, column=1, pady=(10, 0))
        
        ttk.Button(
            control_frame, 
            text="Set Exposure", 
            command=self.set_exposure
        ).grid(row=3, column=0, columnspan=2, pady=5, sticky=(tk.W, tk.E))
        
        # Gain control
        ttk.Label(control_frame, text="Gain (dB):").grid(row=4, column=0, sticky=tk.W, pady=(10, 0))
        self.gain_var = tk.StringVar(value="0")
        gain_entry = ttk.Entry(control_frame, textvariable=self.gain_var, width=10)
        gain_entry.grid(row=4, column=1, pady=(10, 0))
        
        ttk.Button(
            control_frame, 
            text="Set Gain", 
            command=self.set_gain
        ).grid(row=5, column=0, columnspan=2, pady=5, sticky=(tk.W, tk.E))
    
    def _build_calibration_info(self, parent):
        """Build calibration information display"""
        cal_frame = ttk.LabelFrame(parent, text="Calibration Info", padding="5")
        cal_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Focus score
        ttk.Label(cal_frame, text="Focus Score:").grid(row=0, column=0, sticky=tk.W)
        self.focus_var = tk.StringVar(value="--")
        ttk.Label(cal_frame, textvariable=self.focus_var, font=('Arial', 10, 'bold')).grid(
            row=0, column=1, sticky=tk.E
        )
        
        # Tilt X
        ttk.Label(cal_frame, text="Tilt X:").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        self.tilt_x_var = tk.StringVar(value="--")
        ttk.Label(cal_frame, textvariable=self.tilt_x_var, font=('Arial', 10)).grid(
            row=1, column=1, sticky=tk.E, pady=(5, 0)
        )
        
        # Tilt Y
        ttk.Label(cal_frame, text="Tilt Y:").grid(row=2, column=0, sticky=tk.W, pady=(5, 0))
        self.tilt_y_var = tk.StringVar(value="--")
        ttk.Label(cal_frame, textvariable=self.tilt_y_var, font=('Arial', 10)).grid(
            row=2, column=1, sticky=tk.E, pady=(5, 0)
        )
        
        # Note about placeholders
        note_label = ttk.Label(
            cal_frame, 
            text="Note: Calibration algorithms\nare placeholders for now", 
            font=('Arial', 8, 'italic'),
            foreground='gray'
        )
        note_label.grid(row=3, column=0, columnspan=2, pady=(10, 0))
    
    def _build_action_buttons(self, parent):
        """Build action buttons"""
        action_frame = ttk.LabelFrame(parent, text="Actions", padding="5")
        action_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Generate ChArUco pattern
        ttk.Button(
            action_frame, 
            text="Generate ChArUco Pattern", 
            command=self.generate_pattern
        ).grid(row=0, column=0, pady=5, sticky=(tk.W, tk.E))
        
        # Capture snapshot
        ttk.Button(
            action_frame, 
            text="Capture Snapshot", 
            command=self.capture_snapshot
        ).grid(row=1, column=0, pady=5, sticky=(tk.W, tk.E))
        
        # Calculate focus
        ttk.Button(
            action_frame, 
            text="Calculate Focus", 
            command=self.calculate_focus
        ).grid(row=2, column=0, pady=5, sticky=(tk.W, tk.E))
        
        # Calculate tilt
        ttk.Button(
            action_frame, 
            text="Calculate Tilt", 
            command=self.calculate_tilt
        ).grid(row=3, column=0, pady=5, sticky=(tk.W, tk.E))
        
        # Analyze frame (both focus and tilt)
        ttk.Button(
            action_frame, 
            text="Analyze Frame (Both)", 
            command=self.analyze_frame
        ).grid(row=4, column=0, pady=5, sticky=(tk.W, tk.E))
    
    def connect_camera(self):
        """Connect to camera"""
        try:
            success = self.camera_manager.connect()
            
            if success:
                self.status_var.set("Camera connected")
                self.connect_button.config(text="Disconnect Camera")
                self.stream_button.config(state=tk.NORMAL)
                
                # Update exposure and gain from camera
                info = self.camera_manager.get_camera_info()
                self.exposure_var.set(str(info.get('exposure', 10000)))
                self.gain_var.set(str(info.get('gain', 0)))
            else:
                self.status_var.set("Failed to connect to camera")
                messagebox.showerror("Connection Error", "Could not connect to camera")
                
        except Exception as e:
            self.status_var.set(f"Error: {e}")
            messagebox.showerror("Connection Error", str(e))
    
    def disconnect_camera(self):
        """Disconnect from camera"""
        try:
            if self.camera_manager.is_streaming:
                self.camera_manager.stop_streaming()
            
            self.camera_manager.disconnect()
            
            self.status_var.set("Camera disconnected")
            self.connect_button.config(text="Connect Camera")
            self.stream_button.config(text="Start Streaming", state=tk.DISABLED)
            
            # Clear canvas
            self.canvas.delete("all")
            
        except Exception as e:
            self.status_var.set(f"Error: {e}")
            messagebox.showerror("Disconnection Error", str(e))
    
    def toggle_connection(self):
        """Toggle camera connection"""
        if self.camera_manager.camera is None:
            self.connect_camera()
        else:
            self.disconnect_camera()
    
    def toggle_streaming(self):
        """Toggle video streaming"""
        if self.camera_manager.is_streaming:
            self.camera_manager.stop_streaming()
            self.stream_button.config(text="Start Streaming")
            self.status_var.set("Streaming stopped")
        else:
            self.camera_manager.start_streaming(self.update_frame)
            self.stream_button.config(text="Stop Streaming")
            self.status_var.set("Streaming active")
    
    def update_frame(self, image: np.ndarray):
        """
        Update display with new camera frame.
        Called from camera thread, must use after() to update GUI in main thread.
        
        Args:
            image: Numpy array from camera
        """
        # Schedule GUI update in main thread
        if hasattr(self, 'window') and self.window.winfo_exists():
            self.window.after(0, self._update_frame_gui, image)
    
    def _update_frame_gui(self, image: np.ndarray):
        """
        Internal method to update frame in main GUI thread.
        
        Args:
            image: Numpy array from camera
        """
        try:
            self.current_image = image
            
            # Handle different image formats
            if len(image.shape) == 2:
                # Grayscale image
                pil_image = Image.fromarray(image, mode='L')
            elif len(image.shape) == 3 and image.shape[2] == 1:
                # Grayscale with extra dimension
                pil_image = Image.fromarray(image[:, :, 0], mode='L')
            elif len(image.shape) == 3 and image.shape[2] == 3:
                # RGB image
                pil_image = Image.fromarray(image, mode='RGB')
            else:
                # Unknown format, try to squeeze and convert
                image_2d = np.squeeze(image)
                pil_image = Image.fromarray(image_2d, mode='L')
            
            # Resize to fit canvas
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            if canvas_width > 1 and canvas_height > 1:
                # Use Image.LANCZOS for older Pillow versions (< 9.0)
                try:
                    pil_image.thumbnail((canvas_width, canvas_height), Image.Resampling.LANCZOS)
                except AttributeError:
                    pil_image.thumbnail((canvas_width, canvas_height), Image.LANCZOS)
            
            # Convert to PhotoImage
            self.display_image = ImageTk.PhotoImage(pil_image)
            
            # Update canvas
            self.canvas.delete("all")
            self.canvas.create_image(
                canvas_width // 2, 
                canvas_height // 2, 
                image=self.display_image
            )
            
        except Exception as e:
            print(f"ERROR updating frame: {e}")
    
    def set_exposure(self):
        """Set camera exposure"""
        try:
            exposure = float(self.exposure_var.get())
            self.camera_manager.set_exposure(exposure)
            self.status_var.set(f"Exposure set to {exposure} µs")
        except ValueError:
            messagebox.showerror("Invalid Input", "Exposure must be a number")
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def set_gain(self):
        """Set camera gain"""
        try:
            gain = float(self.gain_var.get())
            self.camera_manager.set_gain(gain)
            self.status_var.set(f"Gain set to {gain} dB")
        except ValueError:
            messagebox.showerror("Invalid Input", "Gain must be a number")
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def generate_pattern(self):
        """Generate ChArUco calibration pattern"""
        # Ask for projector resolution
        dialog = tk.Toplevel(self.window)
        dialog.title("Generate ChArUco Pattern")
        dialog.geometry("350x200")
        dialog.transient(self.window)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Projector Resolution:", font=('Arial', 10, 'bold')).pack(pady=(10, 5))
        
        # Width
        width_frame = ttk.Frame(dialog)
        width_frame.pack(pady=5)
        ttk.Label(width_frame, text="Width:").pack(side=tk.LEFT, padx=5)
        width_var = tk.StringVar(value="1920")
        width_entry = ttk.Entry(width_frame, textvariable=width_var, width=10)
        width_entry.pack(side=tk.LEFT)
        
        # Height
        height_frame = ttk.Frame(dialog)
        height_frame.pack(pady=5)
        ttk.Label(height_frame, text="Height:").pack(side=tk.LEFT, padx=5)
        height_var = tk.StringVar(value="1080")
        height_entry = ttk.Entry(height_frame, textvariable=height_var, width=10)
        height_entry.pack(side=tk.LEFT)
        
        def generate():
            try:
                width = int(width_var.get())
                height = int(height_var.get())
                
                # Ask for save location
                filepath = filedialog.asksaveasfilename(
                    defaultextension=".png",
                    initialfile="charuco_calibration_pattern.png",
                    filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
                )
                
                if filepath:
                    success = self.camera_manager.generate_charuco_pattern(width, height, filepath)
                    if success:
                        messagebox.showinfo(
                            "Success",
                            f"ChArUco pattern generated:\n{filepath}\n\n"
                            "Project this pattern and use camera to analyze focus/tilt."
                        )
                        dialog.destroy()
                    else:
                        messagebox.showerror("Error", "Failed to generate pattern")
            except ValueError:
                messagebox.showerror("Invalid Input", "Width and height must be integers")
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=20)
        ttk.Button(button_frame, text="Generate", command=generate).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def capture_snapshot(self):
        """Capture and save current frame"""
        if self.current_image is None:
            messagebox.showwarning("No Image", "No image available to capture")
            return
        
        # Ask user for save location
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"camera_snapshot_{timestamp}.png"
        
        filepath = filedialog.asksaveasfilename(
            defaultextension=".png",
            initialfile=default_filename,
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
        )
        
        if filepath:
            success = self.camera_manager.save_calibration_image(filepath)
            if success:
                self.status_var.set(f"Snapshot saved: {os.path.basename(filepath)}")
                messagebox.showinfo("Success", f"Snapshot saved to:\n{filepath}")
            else:
                messagebox.showerror("Error", "Failed to save snapshot")
    
    def calculate_focus(self):
        """Calculate focus score from current frame using ChArUco pattern"""
        if self.current_image is None:
            messagebox.showwarning("No Image", "No image available for focus calculation")
            return
        
        try:
            focus_score = self.camera_manager.calculate_focus_score(self.current_image)
            self.focus_var.set(f"{focus_score:.2f}")
            self.status_var.set(f"Focus score: {focus_score:.2f}")
            
            # Provide guidance on score interpretation
            if focus_score > 1000:
                quality = "Excellent"
            elif focus_score > 500:
                quality = "Good"
            elif focus_score > 100:
                quality = "Fair"
            else:
                quality = "Poor - Adjust focus"
            
            messagebox.showinfo(
                "Focus Calculation", 
                f"Focus Score: {focus_score:.2f}\n"
                f"Quality: {quality}\n\n"
                "Method: Laplacian variance on ChArUco pattern\n"
                "Higher score = sharper image\n\n"
                "Uses inner 50% of image to avoid vignetting."
            )
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def calculate_tilt(self):
        """Calculate tilt angles from current frame using ChArUco markers"""
        if self.current_image is None:
            messagebox.showwarning("No Image", "No image available for tilt calculation")
            return
        
        try:
            tilt_x, tilt_y = self.camera_manager.calculate_tilt(self.current_image)
            
            if tilt_x == 0.0 and tilt_y == 0.0 and self.camera_manager.markers_detected == 0:
                messagebox.showwarning(
                    "No Markers Detected",
                    "No ChArUco markers detected in image.\n\n"
                    "Make sure:\n"
                    "1. ChArUco pattern is projected/displayed\n"
                    "2. Pattern is visible in camera view\n"
                    "3. Markers are in the center 50% of image\n"
                    "4. Image is in focus enough to detect markers"
                )
                return
            
            self.tilt_x_var.set(f"{tilt_x:.2f}°")
            self.tilt_y_var.set(f"{tilt_y:.2f}°")
            
            # Determine if camera intrinsics are set
            has_intrinsics = self.camera_manager.charuco_calibrator.camera_matrix is not None
            
            # Provide guidance on tilt magnitude
            max_tilt = max(abs(tilt_x), abs(tilt_y))
            if max_tilt < 1.0:
                alignment = "Excellent"
            elif max_tilt < 3.0:
                alignment = "Good"
            elif max_tilt < 5.0:
                alignment = "Fair"
            else:
                alignment = "Poor - Adjust alignment"
            
            markers_msg = f"Detected {self.camera_manager.markers_detected} ChArUco markers"
            intrinsics_msg = "Absolute angles" if has_intrinsics else "Relative measurements (no camera calibration)"
            
            self.status_var.set(f"Tilt: X={tilt_x:.2f}°, Y={tilt_y:.2f}° ({markers_msg})")
            
            messagebox.showinfo(
                "Tilt Calculation", 
                f"Tilt X: {tilt_x:.2f}°\n"
                f"Tilt Y: {tilt_y:.2f}°\n"
                f"Alignment: {alignment}\n\n"
                f"Method: ChArUco marker pose estimation\n"
                f"{intrinsics_msg}\n"
                f"{markers_msg}\n\n"
                "Uses inner 50% of image (vignetting safe zone)."
            )
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def analyze_frame(self):
        """Analyze current frame for both focus and tilt simultaneously"""
        if self.current_image is None:
            messagebox.showwarning("No Image", "No image available for analysis")
            return
        
        try:
            results = self.camera_manager.analyze_calibration_frame(self.current_image)
            
            # Update display
            self.focus_var.set(f"{results['focus_score']:.2f}")
            
            if results['tilt_detected']:
                self.tilt_x_var.set(f"{results['tilt_x_deg']:.2f}°")
                self.tilt_y_var.set(f"{results['tilt_y_deg']:.2f}°")
            else:
                self.tilt_x_var.set("--")
                self.tilt_y_var.set("--")
            
            # Status message
            if results['markers_detected'] == 0:
                status_msg = f"Focus: {results['focus_score']:.2f} | No markers detected"
            else:
                status_msg = f"Focus: {results['focus_score']:.2f} | Tilt: X={results['tilt_x_deg']:.2f}°, Y={results['tilt_y_deg']:.2f}° | {results['markers_detected']} markers"
            
            self.status_var.set(status_msg)
            
            # Interpret results
            focus_quality = "Excellent" if results['focus_score'] > 1000 else "Good" if results['focus_score'] > 500 else "Fair" if results['focus_score'] > 100 else "Poor"
            
            tilt_msg = ""
            if results['tilt_detected']:
                max_tilt = max(abs(results['tilt_x_deg']), abs(results['tilt_y_deg']))
                tilt_quality = "Excellent" if max_tilt < 1.0 else "Good" if max_tilt < 3.0 else "Fair" if max_tilt < 5.0 else "Poor"
                tilt_msg = f"\nTilt X: {results['tilt_x_deg']:.2f}° | Tilt Y: {results['tilt_y_deg']:.2f}°\nAlignment: {tilt_quality}"
            else:
                tilt_msg = "\nTilt: Not detected (no markers visible)"
            
            messagebox.showinfo(
                "Frame Analysis",
                f"Focus Score: {results['focus_score']:.2f}\nFocus Quality: {focus_quality}"
                f"{tilt_msg}\n\n"
                f"Markers Detected: {results['markers_detected']}\n\n"
                "Method: ChArUco double-duty analysis\n"
                "Both metrics from single image capture."
            )
            
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def toggle_calibration(self):
        """Start or stop automated calibration workflow"""
        if self.calibration_workflow.is_calibrating:
            # Stop calibration
            self.calibration_workflow.stop_calibration()
            self.calibration_button.config(text="🚀 Start Calibration")
            self.accept_button.config(state=tk.DISABLED)
        else:
            # Start calibration
            if not self.camera_manager.camera:
                messagebox.showerror("Error", "Camera not connected.\n\nConnect camera before starting calibration.")
                return
            
            success = self.calibration_workflow.start_calibration()
            if success:
                self.calibration_button.config(text="⏹️ Stop Calibration")
                self.accept_button.config(state=tk.NORMAL)
            else:
                messagebox.showerror("Error", "Failed to start calibration.\n\nCheck camera connection and DLP projector.")
    
    def accept_calibration(self):
        """Accept and save current calibration"""
        if not self.calibration_workflow.is_calibrating:
            return
        
        # Check if within tolerance
        state = self.calibration_workflow.get_current_state()
        
        if not state['within_tolerance']:
            response = messagebox.askyesno(
                "Calibration Not Optimal",
                f"Current calibration is not within optimal tolerance:\n\n"
                f"Focus: {state['focus_score']:.1f} (target: >500)\n"
                f"Tilt X: {state['tilt_x_deg']:+.2f}° (target: <2°)\n"
                f"Tilt Y: {state['tilt_y_deg']:+.2f}° (target: <2°)\n\n"
                f"Accept anyway?"
            )
            if not response:
                return
        
        # Accept calibration
        cal_data = self.calibration_workflow.accept_calibration()
        
        if cal_data:
            messagebox.showinfo(
                "Calibration Accepted",
                f"Calibration saved successfully!\n\n"
                f"Focus Score: {cal_data['focus_score']:.2f}\n"
                f"Tilt X: {cal_data['tilt_x_deg']:+.2f}°\n"
                f"Tilt Y: {cal_data['tilt_y_deg']:+.2f}°\n"
                f"Exposure: {cal_data['exposure_us']} µs\n"
                f"Gain: {cal_data['gain_db']} dB\n\n"
                f"DLP restored to normal operation."
            )
            
            self.calibration_button.config(text="🚀 Start Calibration")
            self.accept_button.config(state=tk.DISABLED)
    
    def on_calibration_update(self, results):
        """Callback for calibration measurement updates"""
        # Update calibration info display
        self.focus_var.set(f"{results['focus_score']:.2f}")
        
        if results['tilt_detected']:
            self.tilt_x_var.set(f"{results['tilt_x_deg']:.2f}°")
            self.tilt_y_var.set(f"{results['tilt_y_deg']:.2f}°")
        else:
            self.tilt_x_var.set("--")
            self.tilt_y_var.set("--")
    
    def on_guidance_update(self, guidance):
        """Callback for guidance text updates"""
        self.guidance_text.config(state=tk.NORMAL)
        self.guidance_text.delete('1.0', tk.END)
        self.guidance_text.insert('1.0', guidance)
        self.guidance_text.config(state=tk.DISABLED)
    
    def on_status_update(self, status):
        """Callback for status text updates"""
        self.status_var.set(status)
    
    def on_closing(self):
        """Handle window close event"""
        try:
            # Stop calibration if running
            if self.calibration_workflow.is_calibrating:
                self.calibration_workflow.stop_calibration()
            
            # Stop streaming and disconnect
            if self.camera_manager.is_streaming:
                self.camera_manager.stop_streaming()
            
            if self.camera_manager.camera:
                self.camera_manager.disconnect()
            
            self.window.destroy()
            
        except Exception as e:
            print(f"ERROR during cleanup: {e}")
            self.window.destroy()
    
    def run(self):
        """Run the window (if standalone)"""
        if not self.parent:
            self.window.mainloop()


if __name__ == "__main__":
    # Run standalone for testing
    app = CameraViewWindow()
    app.run()
