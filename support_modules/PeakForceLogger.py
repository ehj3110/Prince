import csv
import os
import time
from datetime import datetime
import threading
import numpy as np
import sys
from pathlib import Path
import queue
import warnings
import cv2

# Import the adhesion_metrics_calculator from the support_modules directory
from support_modules.adhesion_metrics_calculator import AdhesionMetricsCalculator

class PeakForceLogger:
    """
    Unified PeakForceLogger that uses the corrected AdhesionMetricsCalculator
    for consistent analysis across all system components.
    """
    DATA_CHUNK_SIZE = 5000  # Number of data points to hold in memory before flushing
    
    # Hardware-specific pixel size for cross-sectional area calculation
    PIXEL_SIZE_MM = 0.007607  # Each pixel is 0.007607mm x 0.007607mm (square)
    PIXEL_AREA_MM2 = PIXEL_SIZE_MM ** 2  # Area of one pixel in mm²
    
    def __init__(self, output_csv_filepath, is_manual_log=False, use_corrected_calculator=True, phase_event_queue_ref=None, main_window_ref=None):
        self.output_csv_filepath = output_csv_filepath
        self.is_manual_log = is_manual_log
        self.use_corrected_calculator = use_corrected_calculator
        self.current_layer_number = 0
        self._monitoring = False
        self._lock = threading.Lock()
        self._data_buffer = []  # Stores (timestamp, position, force) tuples for the current layer
        self.log_file_exists = os.path.exists(self.output_csv_filepath)
        
        # Reference to main window for experimental conditions tracking
        self.main_window_ref = main_window_ref
        
        # Phase event tracking
        self.phase_event_queue_ref = phase_event_queue_ref
        self._current_lifting_start_idx = None  # Data buffer index where lifting started
        self._current_lifting_start_time = None  # Timestamp when lifting started

        # --- Analysis Worker Thread Setup ---
        self._analysis_queue = queue.Queue()
        self._analysis_thread = threading.Thread(target=self._analysis_worker, daemon=True)
        self._analysis_thread.start()
        
        # Initialize the corrected adhesion calculator with two-step filtering
        if self.use_corrected_calculator:
            self.calculator = AdhesionMetricsCalculator(
                median_kernel=5,         # Median filter for outlier rejection
                savgol_window=9,         # Savitzky-Golay window
                savgol_order=2,          # Polynomial order
                baseline_threshold_factor=0.002,  # Standard threshold
                min_peak_height=0.01,    # Minimum peak detection
                min_peak_distance=50     # Standard distance
            )
        else:
            self.calculator = None
            
        # For plotting integration
        self.plot_time_data = []       # Stores ABSOLUTE timestamps for shading
        self.plot_force_data = []      # Stores corresponding forces for shading
        
        self.z_peel_peak_mm = None 
        self.z_return_pos_mm = None
        
        # Cross-sectional area tracking (set per layer)
        self.current_cross_sectional_area_mm2 = None

        # Only create header for automated logging, not manual logging
        if not self.is_manual_log:
            self._ensure_header()

    def _ensure_header(self):
        """Create CSV header based on the updated metrics."""
        if not self.log_file_exists:
            with open(self.output_csv_filepath, 'w', newline='') as f:
                writer = csv.writer(f)
                header = [
                    'Layer_Number', 
                    'Peak_Force_N',  # Baseline-corrected peak force
                    'Work_of_Adhesion_mJ',
                    'Initiation_Time_s', 
                    'Propagation_Duration_s', 
                    'Total_Duration_s',
                    'Distance_to_Peak_mm', 
                    'Distance_to_Propagate_mm',
                    'Total_Peel_Distance_mm', 
                    'Peak_Retraction_Force_N',
                    'Cross_Sectional_Area_mm2'
                ]
                writer.writerow(header)

        # Improved error handling for CSV writing
        try:
            with open(self.output_csv_filepath, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(self._data_buffer)
        except Exception as e:
            print(f"Error writing to CSV: {e}")

        # Example usage for testing
        if __name__ == '__main__':
            print("Testing Unified PeakForceLogger with Corrected Calculator")
            logger = PeakForceLogger("test_output.csv", use_corrected_calculator=True)
            logger.start_monitoring_for_layer(1, z_peel_peak=10.0, z_return_pos=12.0)
            logger.add_data_point(time.time(), 10.5, 0.2)
            logger.stop_monitoring_and_log_peak()

    def pause_monitoring(self):
        """Temporarily pause data collection (for sandwich routines, etc.)"""
        with self._lock:
            if self._monitoring:
                self._monitoring = False
                print(f"PFL: Monitoring paused for layer {self.current_layer_number}")
    
    def resume_monitoring(self):
        """Resume data collection after pause"""
        with self._lock:
            if not self._monitoring:
                self._monitoring = True
                print(f"PFL: Monitoring resumed for layer {self.current_layer_number}")
    
    def start_monitoring_for_layer(self, layer_number, z_peel_peak=None, z_return_pos=None, image_path=None):
        """
        Start monitoring for a new layer.
        
        Args:
            layer_number: Current layer number
            z_peel_peak: Peak z position (mm)
            z_return_pos: Return z position (mm)
            image_path: Path to the PNG image for this layer (optional, for area calculation)
        """
        with self._lock:
            # Prevent duplicate recording if already monitoring this layer
            if self._monitoring and self.current_layer_number == layer_number:
                print(f"PFL: Already monitoring layer {layer_number}, ignoring duplicate start request")
                return
            
            self.current_layer_number = layer_number
            self.z_peel_peak_mm = z_peel_peak
            self.z_return_pos_mm = z_return_pos
            self._monitoring = True
            self._data_buffer.clear()
            self.plot_time_data.clear()
            self.plot_force_data.clear()
            # Reset phase tracking for new layer
            self._current_lifting_start_idx = None
            self._current_lifting_start_time = None
            
            # Calculate cross-sectional area from image if provided
            if image_path is not None:
                self.current_cross_sectional_area_mm2 = self._calculate_cross_sectional_area(image_path)
            else:
                self.current_cross_sectional_area_mm2 = None
        
        # Format area message (conditional must be outside format specifier)
        area_msg = f"{self.current_cross_sectional_area_mm2:.4f}mm²" if self.current_cross_sectional_area_mm2 is not None else "N/A"
        
        # Detect continuous motion mode (overstep=0)
        if z_peel_peak is not None and z_return_pos is not None:
            if abs(z_peel_peak - z_return_pos) < 0.001:  # Within 1 micron
                print(f"PFL: Continuous motion mode detected (overstep=0) - no position filtering for layer {layer_number}")
        
        print(f"PFL: Started monitoring layer {layer_number} (peel: {z_peel_peak}mm, return: {z_return_pos}mm, area: {area_msg})")
    
    def _calculate_cross_sectional_area(self, image_path):
        """
        Calculate cross-sectional area from PNG image by counting white pixels.
        
        Args:
            image_path: Path to the PNG image file (can be string or Path object)
            
        Returns:
            Cross-sectional area in mm² or None if calculation fails
        """
        try:
            from pathlib import Path
            
            # Convert to Path object (handles both string and Path inputs)
            img_path = Path(image_path)
            
            if not img_path.exists():
                print(f"PFL: ERROR - Image does not exist: {img_path}")
                return None
            
            # Read image as grayscale
            img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
            
            if img is None:
                print(f"PFL: ERROR - Failed to read image: {img_path}")
                return None
            
            # Count white pixels (≥250 threshold for robustness)
            white_pixel_count = np.sum(img >= 250)
            
            if white_pixel_count == 0:
                print(f"PFL: ERROR - No white pixels in image (min={np.min(img)}, max={np.max(img)})")
                return None
            
            # Calculate area
            area_mm2 = white_pixel_count * self.PIXEL_AREA_MM2
            
            print(f"PFL: Area calculated: {area_mm2:.4f}mm² ({white_pixel_count} white pixels)")
            return area_mm2
            
        except Exception as e:
            print(f"PFL: ERROR calculating area: {e}")
            return None
    
    def _update_phase_info(self):
        """Check for phase events and update lifting start marker.
        
        For smooth lifting (2-stage), we track 'Lift-Stage2' as the real lifting start at prescribed speed.
        Stage 1 is the gentle break phase and should not be used as the adhesion analysis start.
        """
        if self.phase_event_queue_ref is None:
            return
        
        # Process all pending phase events
        while not self.phase_event_queue_ref.empty():
            try:
                event = self.phase_event_queue_ref.get_nowait()
                
                # For smooth lifting: Track 'Lift-Stage2' as the true lifting start (prescribed speed)
                # For standard lifting: Track 'Lift' as the lifting start
                # This allows adhesion analysis to exclude the gentle break phase (Stage 1)
                is_lifting_phase = event['phase'] in ['Lift', 'Lift-Stage2']
                
                if is_lifting_phase:
                    # Mark the time when prescribed-speed lifting phase was declared
                    self._current_lifting_start_time = event['timestamp']
                    
                    # Find the first data point at or after the phase event
                    # Then look backwards to find where motion actually started
                    with self._lock:
                        # First, find index at or after phase event
                        phase_event_idx = None
                        for idx, (ts, pos, force) in enumerate(self._data_buffer):
                            if ts >= event['timestamp']:
                                phase_event_idx = idx
                                break
                        
                        if phase_event_idx is not None:
                            # Now search backwards from this point to find where position started changing
                            # Look for the last stationary point before motion began
                            motion_start_idx = phase_event_idx
                            if phase_event_idx > 5:  # Need some history to detect motion start
                                prev_pos = self._data_buffer[phase_event_idx][1]
                                for idx in range(phase_event_idx - 1, max(0, phase_event_idx - 20), -1):
                                    curr_pos = self._data_buffer[idx][1]
                                    if curr_pos is not None and prev_pos is not None:
                                        pos_change = abs(curr_pos - prev_pos)
                                        if pos_change < 0.01:  # Found stationary point (< 0.01mm change)
                                            motion_start_idx = idx + 1  # Motion starts after this stationary point
                                            break
                                        prev_pos = curr_pos
                            
                            self._current_lifting_start_idx = motion_start_idx
                            ts = self._data_buffer[motion_start_idx][0]
                            print(f"PFL: Lifting motion detected starting at buffer idx {motion_start_idx}, time {ts:.3f}s")
                                
            except queue.Empty:
                break

    def add_data_point(self, timestamp, position, force):
        """Add a data point during monitoring and flush buffer if chunk size is reached."""
        if not self._monitoring:
            return
        
        # Update phase information from queue
        self._update_phase_info()

        with self._lock:
            # Store all data for analysis
            self._data_buffer.append((timestamp, position, force))

            # For plot shading - only store data within peel range
            # Skip position filtering if z_peel_peak == z_return_pos (continuous motion mode with overstep=0)
            if position is not None and force is not None:
                # Check if this is continuous motion mode (peel peak == return pos)
                is_continuous_mode = (self.z_peel_peak_mm is not None and 
                                     self.z_return_pos_mm is not None and 
                                     abs(self.z_peel_peak_mm - self.z_return_pos_mm) < 0.001)  # Within 1 micron
                
                if is_continuous_mode:
                    # Continuous motion mode: Include ALL data (no position filtering)
                    self.plot_time_data.append(timestamp)
                    self.plot_force_data.append(force)
                elif self.z_peel_peak_mm is not None and self.z_return_pos_mm is not None:
                    # Standard mode: Filter by position range
                    # Check if position is within peel range
                    in_peel_range_up = (self.z_peel_peak_mm <= self.z_return_pos_mm and 
                                       self.z_peel_peak_mm <= position <= self.z_return_pos_mm)
                    in_peel_range_down = (self.z_peel_peak_mm > self.z_return_pos_mm and 
                                         self.z_return_pos_mm <= position <= self.z_peel_peak_mm)
                    
                    if in_peel_range_up or in_peel_range_down:
                        self.plot_time_data.append(timestamp)
                        self.plot_force_data.append(force)
                elif self.is_manual_log:
                    # For manual logging, include all data
                    self.plot_time_data.append(timestamp)
                    self.plot_force_data.append(force)
            
            # If buffer reaches chunk size, flush it to the analysis thread
            if len(self._data_buffer) >= self.DATA_CHUNK_SIZE:
                self._flush_buffer_to_analysis_thread()

    def _flush_buffer_to_analysis_thread(self):
        """Internal method to queue the current buffer for analysis without stopping monitoring."""
        # This method assumes the lock is already held from add_data_point or stop_monitoring_and_log_peak
        if not self._data_buffer:
            return # Nothing to flush

        # Create a copy of the data to avoid race conditions
        data_to_process = {
            "layer_number": self.current_layer_number,
            "data_buffer": list(self._data_buffer),
            "is_manual": self.is_manual_log,
            "output_csv": self.output_csv_filepath
        }
        self._analysis_queue.put(data_to_process)
        
        # Clear the buffer for the next chunk
        self._data_buffer.clear()
        print(f"PFL: Flushed {len(data_to_process['data_buffer'])} data points for layer {self.current_layer_number} to analysis queue.")

    def stop_monitoring_and_log_peak(self):
        """Stop monitoring and queue any remaining data for analysis."""
        if not self._monitoring:
            print(f"PFL: Warning - stop_monitoring called but not currently monitoring (layer {self.current_layer_number})")
            return False

        with self._lock:
            self._monitoring = False
            lifting_start_idx = self._current_lifting_start_idx  # Capture phase info
            
            # Flush any remaining data in the buffer before stopping
            if self._data_buffer:
                print(f"PFL: Flushing remaining {len(self._data_buffer)} data points before stopping.")
                # Include lifting_start_idx in the flush
                if not self._data_buffer:
                    return False
                
                # Create a copy of the data to avoid race conditions
                data_to_process = {
                    "layer_number": self.current_layer_number,
                    "data_buffer": list(self._data_buffer),
                    "is_manual": self.is_manual_log,
                    "output_csv": self.output_csv_filepath,
                    "lifting_start_idx": lifting_start_idx,  # Pass phase info
                    "cross_sectional_area_mm2": self.current_cross_sectional_area_mm2  # Pass area
                }
                self._analysis_queue.put(data_to_process)
                self._data_buffer.clear()
                print(f"PFL: Flushed {len(data_to_process['data_buffer'])} data points for layer {self.current_layer_number} to analysis queue.")
            else:
                print(f"PFL: No remaining data to flush for layer {self.current_layer_number}")

        print(f"PFL: Stopped monitoring layer {self.current_layer_number}.")
        return True

    def _analysis_worker(self):
        """Worker thread to process queued adhesion data analysis."""
        while True:
            try:
                job = self._analysis_queue.get()
                if job is None: # Sentinel for shutting down the thread
                    print("PFL: Analysis worker shutting down.")
                    break

                layer_num = job["layer_number"]
                data_buffer = job["data_buffer"]
                lifting_start_idx = job.get("lifting_start_idx")  # Get phase info
                cross_sectional_area_mm2 = job.get("cross_sectional_area_mm2")  # Get area
                
                # Extract data arrays
                timestamps = np.array([dp[0] for dp in data_buffer])
                positions = np.array([dp[1] for dp in data_buffer if dp[1] is not None])
                forces = np.array([dp[2] for dp in data_buffer if dp[2] is not None])

                if len(forces) == 0:
                    print(f"PFL Worker: No valid force data for layer {layer_num}")
                    continue

                success = False
                if self.use_corrected_calculator and self.calculator:
                    success = self._analyze_with_corrected_calculator(
                        timestamps, positions, forces, layer_num, 
                        job["output_csv"], job["is_manual"], lifting_start_idx, cross_sectional_area_mm2
                    )
                else:
                    success = self._analyze_with_original_method(timestamps, positions, forces, layer_num, job["output_csv"], job["is_manual"], cross_sectional_area_mm2)
                
                print(f"PFL Worker: {'Successfully' if success else 'Failed to'} analyze and log layer {layer_num}")

            except Exception as e:
                print(f"PFL Worker: Error during analysis: {e}")

    def _analyze_with_corrected_calculator(self, timestamps, positions, forces, layer_number, output_csv, is_manual, lifting_start_idx=None, cross_sectional_area_mm2=None):
        """Analyze data using the corrected AdhesionMetricsCalculator."""
        try:
            # Skip layer 0 - it's used for initialization/calibration only
            if layer_number == 0:
                return False
            
            # Use the corrected calculator with phase awareness
            results = self.calculator.calculate_from_arrays(
                timestamps, positions, forces, layer_number=layer_number,
                lifting_start_idx=lifting_start_idx  # NEW: Pass phase info
            )
            
            # Extract key metrics with fallbacks
            peak_force = results.get('peak_force', 0.0)
            work_of_adhesion = results.get('work_of_adhesion_mJ', 0.0)
            pre_initiation_time = results.get('pre_initiation_time', np.nan)
            
            # Update experimental conditions failure detector if main window exists
            if (self.main_window_ref and 
                hasattr(self.main_window_ref, 'exp_conditions_window') and 
                self.main_window_ref.exp_conditions_window):
                try:
                    self.main_window_ref.exp_conditions_window.update_layer_force(layer_number, peak_force)
                except Exception as e:
                    print(f"PFL: Error updating experimental conditions: {e}")
            propagation_end_time = results.get('propagation_end_time', np.nan)
            peak_force_time = results.get('peak_force_time', np.nan)
            
            # Calculate durations - convert to absolute values
            total_duration = abs(results.get('total_peel_duration', np.nan)) if not np.isnan(results.get('total_peel_duration', np.nan)) else np.nan
            propagation_duration = abs(results.get('propagation_duration', np.nan)) if not np.isnan(results.get('propagation_duration', np.nan)) else np.nan
            
            # Position metrics - convert distances to absolute values
            peak_position = results.get('peak_force_position', np.nan)
            pre_initiation_distance = abs(results.get('pre_initiation_distance', np.nan)) if not np.isnan(results.get('pre_initiation_distance', np.nan)) else np.nan
            total_peel_distance = abs(results.get('total_peel_distance', np.nan)) if not np.isnan(results.get('total_peel_distance', np.nan)) else np.nan
            
            # Retraction force - keep as-is (negative value expected)
            peak_retraction_force = np.min(forces) if len(forces) > 0 else 0.0
            
            # Get propagation distance - convert to absolute value
            propagation_distance = abs(results.get('propagation_distance', np.nan)) if not np.isnan(results.get('propagation_distance', np.nan)) else np.nan
            
            # Validate metrics - warn about unexpected values
            if peak_force < 0:
                warnings.warn(f"Layer {layer_number}: Negative peak force detected ({peak_force:.4f} N)")
            if work_of_adhesion < 0:
                warnings.warn(f"Layer {layer_number}: Negative work of adhesion detected ({work_of_adhesion:.4f} mJ)")
            
            # Write to CSV with validated values (no abs() masking)
            # Note: All distances and durations should already be positive from calculator
            # Only peak_retraction_force is expected to be negative
            return self._write_corrected_csv_entry({
                'peak_force': peak_force,  # Keep sign - validate instead of mask
                'work_of_adhesion_mJ': work_of_adhesion,  # Keep sign - validate instead of mask
                'initiation_time_s': pre_initiation_time if not np.isnan(pre_initiation_time) else np.nan,
                'propagation_end_time_s': propagation_end_time if not np.isnan(propagation_end_time) else np.nan,
                'total_duration_s': total_duration,
                'distance_to_peak_mm': pre_initiation_distance,
                'distance_to_propagate_mm': propagation_distance,
                'total_peel_distance_mm': total_peel_distance,
                'peak_retraction_force': peak_retraction_force,  # Keep sign (expected negative)
                'peak_position_mm': peak_position,
                'propagation_start_time_s': peak_force_time if not np.isnan(peak_force_time) else np.nan,
                'propagation_duration_s': propagation_duration,
                'cross_sectional_area_mm2': cross_sectional_area_mm2  # Add cross-sectional area
            }, layer_number, output_csv, is_manual)
            
        except Exception as e:
            print(f"PFL: Error in corrected calculator analysis for layer {layer_number}: {e}")
            return False

    def _analyze_with_original_method(self, timestamps, positions, forces, layer_number, output_csv, is_manual, cross_sectional_area_mm2=None):
        """Fallback analysis using original simple method."""
        try:
            # Original simple calculations
            peak_force = np.max(forces) if len(forces) > 0 else 0.0
            peak_retraction_force = np.min(forces) if len(forces) > 0 else 0.0
            
            # Simple work calculation
            work_of_adhesion_mJ = 0.0
            if len(positions) >= 2 and len(forces) >= 2:
                # Trapezoidal integration for positive forces only
                positive_mask = forces > 0
                if np.any(positive_mask):
                    pos_forces = forces[positive_mask]
                    pos_positions = positions[positive_mask] / 1000.0  # Convert to meters
                    if len(pos_positions) >= 2:
                        work_J = np.trapz(pos_forces, pos_positions)
                        work_of_adhesion_mJ = work_J * 1000
            
            # Simple timing
            if len(timestamps) >= 2:
                time_to_peak = timestamps[np.argmax(forces)] - timestamps[0]
                total_time = timestamps[-1] - timestamps[0]
            else:
                time_to_peak = np.nan
                total_time = np.nan
            
            # Simple distance
            if len(positions) >= 2:
                distance_to_peak = abs(positions[np.argmax(forces)] - positions[0])
            else:
                distance_to_peak = np.nan

            # Ensure layer 0 is not processed
            if layer_number == 0:
                return False
            
            return self._write_original_csv_entry({
                'peak_force': peak_force,
                'work_of_adhesion_mJ': work_of_adhesion_mJ,
                'time_to_peak_s': time_to_peak,
                'peel_time_s': np.nan,  # Not calculated in simple method
                'total_time_s': total_time,
                'distance_to_peak_mm': distance_to_peak,
                'peak_retraction_force': peak_retraction_force,
                'cross_sectional_area_mm2': cross_sectional_area_mm2  # Add cross-sectional area
            }, layer_number, output_csv, is_manual)
            
        except Exception as e:
            print(f"PFL: Error in original method analysis for layer {layer_number}: {e}")
            return False

    def _write_corrected_csv_entry(self, results, layer_number, output_csv, is_manual):
        """Write CSV entry using corrected calculator format."""
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        try:
            # This check is now less critical as the worker ensures the header exists,
            # but it provides an extra layer of safety.
            if not os.path.exists(output_csv):
                self._ensure_header() # This will use self.output_csv_filepath, needs adjustment if paths differ

            with open(output_csv, 'a', newline='') as f:
                writer = csv.writer(f)
                row_data = [
                    layer_number,
                    f"{results['peak_force']:.4f}",
                    f"{results['work_of_adhesion_mJ']:.4f}",
                    f"{results['initiation_time_s']:.4f}" if not np.isnan(results['initiation_time_s']) else "NaN",
                    f"{results['propagation_duration_s']:.4f}" if not np.isnan(results['propagation_duration_s']) else "NaN",
                    f"{results['total_duration_s']:.4f}" if not np.isnan(results['total_duration_s']) else "NaN",
                    f"{results['distance_to_peak_mm']:.4f}" if not np.isnan(results['distance_to_peak_mm']) else "NaN",
                    f"{results['distance_to_propagate_mm']:.4f}" if not np.isnan(results['distance_to_propagate_mm']) else "NaN",
                    f"{results['total_peel_distance_mm']:.4f}" if not np.isnan(results['total_peel_distance_mm']) else "NaN",
                    f"{results['peak_retraction_force']:.4f}",
                    f"{results['cross_sectional_area_mm2']:.4f}" if results['cross_sectional_area_mm2'] is not None else "NaN"
                ]
                if is_manual:
                    writer.writerow([timestamp_str] + row_data)
                else:
                    writer.writerow(row_data)
            return True
        except Exception as e:
            print(f"PFL: Error writing corrected CSV for layer {layer_number}: {e}")
            return False

    def _write_original_csv_entry(self, results, layer_number, output_csv, is_manual):
        """Write CSV entry using original format."""
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        try:
            if not os.path.exists(output_csv):
                self._ensure_header()

            with open(output_csv, 'a', newline='') as f:
                writer = csv.writer(f)
                # Match the 11-column header format
                row_data = [
                    layer_number,
                    f"{results['peak_force']:.4f}",
                    f"{results['work_of_adhesion_mJ']:.4f}",
                    f"{results['time_to_peak_s']:.4f}" if not np.isnan(results['time_to_peak_s']) else "NaN",
                    f"{results['peel_time_s']:.4f}" if not np.isnan(results['peel_time_s']) else "NaN",
                    f"{results['total_time_s']:.4f}" if not np.isnan(results['total_time_s']) else "NaN",
                    f"{results['distance_to_peak_mm']:.4f}" if not np.isnan(results['distance_to_peak_mm']) else "NaN",
                    "NaN",  # Distance_to_Propagate_mm (not calculated in simple method)
                    f"{results['distance_to_peak_mm']:.4f}" if not np.isnan(results['distance_to_peak_mm']) else "NaN",  # Total_Peel_Distance_mm (use distance_to_peak as approximation)
                    f"{results['peak_retraction_force']:.4f}",
                    f"{results['cross_sectional_area_mm2']:.4f}" if results['cross_sectional_area_mm2'] is not None else "NaN"
                ]
                if is_manual:
                    writer.writerow([timestamp_str] + row_data)
                else:
                    writer.writerow(row_data)
            return True
        except Exception as e:
            print(f"PFL: Error writing original CSV for layer {layer_number}: {e}")
            return False

    def is_monitoring(self):
        """Check if currently monitoring."""
        return self._monitoring

    def get_current_peel_data_for_plot_shading(self):
        """
        Returns the time and force data points for plot shading.
        Returns copies to prevent modification.
        """
        with self._lock:
            return list(self.plot_time_data), list(self.plot_force_data)

    def get_data_for_plot(self):
        """Get plot data (alias for compatibility)."""
        with self._lock:
            return list(self.plot_time_data), list(self.plot_force_data)

    def close(self):
        """Gracefully shuts down the analysis worker thread."""
        print("PFL: Sending shutdown signal to analysis worker.")
        self._analysis_queue.put(None) # Send sentinel to stop the worker
        try:
            self._analysis_thread.join(timeout=2.0) # Wait for thread to finish
        except Exception as e:
            print(f"PFL: Error joining analysis thread: {e}")
        if self._analysis_thread.is_alive():
            print("PFL: Warning - analysis thread did not shut down cleanly.")

    def close_log_file(self):
        """Close log file operations."""
        self.close() # Ensure the worker thread is also stopped
        print(f"PFL: Log file operations complete for {self.output_csv_filepath}")

# Example Usage
if __name__ == '__main__':
    print("Testing Unified PeakForceLogger with Corrected Calculator")
    print("=" * 60)
    
    # Test with corrected calculator
    logger = PeakForceLogger("unified_peak_force_test.csv", use_corrected_calculator=True)
    
    print("\nSimulating Layer 1 with corrected calculator...")
    logger.start_monitoring_for_layer(1, z_peel_peak=10.0, z_return_pos=12.0)
    
    # Simulate realistic peel data
    current_time = time.time()
    timestamps = np.linspace(current_time, current_time + 2.0, 100)
    positions = np.linspace(9.5, 12.5, 100)
    
    # Create realistic force profile with peel event
    forces = []
    for i, pos in enumerate(positions):
        if pos < 10.0:  # Before peel
            force = 0.005 + 0.002 * np.random.random()
        elif pos < 10.5:  # Rising to peak (pre-initiation)
            force = 0.005 + (pos - 10.0) * 0.1 + 0.005 * np.random.random()
        elif pos < 11.0:  # Peak force region
            force = 0.055 + (pos - 10.5) * 0.4 + 0.01 * np.random.random()
        elif pos < 11.5:  # Propagation (declining)
            force = 0.255 - (pos - 11.0) * 0.3 + 0.005 * np.random.random()
        else:  # After peel
            force = 0.105 - (pos - 11.5) * 0.1 + 0.002 * np.random.random()
        forces.append(max(force, 0.0))
    
    # Add data points
    for t, pos, force in zip(timestamps, positions, forces):
        logger.add_data_point(t, pos, force)
    
    # Stop and analyze
    success = logger.stop_monitoring_and_log_peak()
    print(f"Layer 1 analysis: {'Success' if success else 'Failed'}")
    
    # Check results
    if os.path.exists("unified_peak_force_test.csv"):
        print("\nGenerated CSV contents:")
        with open("unified_peak_force_test.csv", 'r') as f:
            print(f.read())
    
    logger.close() # Test the shutdown
    print("\nUnified PeakForceLogger test complete!")