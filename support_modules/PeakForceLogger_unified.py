import csv
import os
import time
from datetime import datetime
import threading
import numpy as np
import sys
sys.path.append('..')
from adhesion_metrics_calculator import AdhesionMetricsCalculator

class PeakForceLogger:
    """
    Unified PeakForceLogger that uses the corrected AdhesionMetricsCalculator
    for consistent analysis across all system components.
    """
    def __init__(self, output_csv_filepath, is_manual_log=False, use_corrected_calculator=True):
        self.output_csv_filepath = output_csv_filepath
        self.is_manual_log = is_manual_log
        self.use_corrected_calculator = use_corrected_calculator
        self.current_layer_number = 0
        self._monitoring = False
        self._lock = threading.Lock()
        self._data_buffer = []  # Stores (timestamp, position, force) tuples for the current layer
        self.log_file_exists = os.path.exists(self.output_csv_filepath)
        
        # Initialize the corrected adhesion calculator with light smoothing
        if self.use_corrected_calculator:
            self.calculator = AdhesionMetricsCalculator(
                smoothing_window=3,      # Light smoothing
                smoothing_polyorder=1,   # Linear polynomial  
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

        # Only create header for automated logging, not manual logging
        if not self.is_manual_log:
            self._ensure_header()

    def _ensure_header(self):
        """Create CSV header based on calculation method."""
        if not self.log_file_exists:
            with open(self.output_csv_filepath, 'w', newline='') as f:
                writer = csv.writer(f)
                
                if self.use_corrected_calculator:
                    # Unified header using corrected calculator results
                    header = [
                        'Layer_Number', 'Peak_Force_N', 'Work_of_Adhesion_mJ',
                        'Initiation_Time_s', 'Propagation_End_Time_s', 'Total_Peel_Duration_s',
                        'Distance_to_Peak_mm', 'Peel_Distance_mm',
                        'Peak_Retraction_Force_N', 'Peak_Position_mm',
                        'Propagation_Start_Time_s', 'Propagation_Duration_s'
                    ]
                else:
                    # Legacy original header for backward compatibility
                    header = [
                        'Layer', 'Peak_Peel_Force_N', 'Work_of_Adhesion_mJ',
                        'Time_to_Peel_Start_s', 'Peel_Time_s', 'Total_Peel_Time_s',
                        'Distance_to_Peel_Start_mm', 'Peak_Retraction_Force_N'
                    ]
                
                if self.is_manual_log:
                    writer.writerow(['Timestamp'] + header)
                else:
                    writer.writerow(header)
            self.log_file_exists = True

    def start_monitoring_for_layer(self, layer_number, z_peel_peak=None, z_return_pos=None):
        """Start monitoring for a new layer."""
        with self._lock:
            self.current_layer_number = layer_number
            self.z_peel_peak_mm = z_peel_peak
            self.z_return_pos_mm = z_return_pos
            self._monitoring = True
            self._data_buffer.clear()
            self.plot_time_data.clear()
            self.plot_force_data.clear()
        print(f"PFL: Started monitoring layer {layer_number} (peel: {z_peel_peak}mm, return: {z_return_pos}mm)")

    def add_data_point(self, timestamp, position, force):
        """Add a data point during monitoring."""
        if not self._monitoring:
            return

        with self._lock:
            # Store all data for analysis
            self._data_buffer.append((timestamp, position, force))
            
            # For plot shading - only store data within peel range
            if position is not None and force is not None:
                if self.z_peel_peak_mm is not None and self.z_return_pos_mm is not None:
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

    def stop_monitoring_and_log_peak(self):
        """Stop monitoring and analyze the collected data."""
        if not self._monitoring:
            print(f"PFL: Warning - stop_monitoring called but not currently monitoring (layer {self.current_layer_number})")
            return False

        with self._lock:
            self._monitoring = False
            
            if not self._data_buffer:
                print(f"PFL: No data collected for layer {self.current_layer_number}")
                return False

            # Extract data arrays
            timestamps = np.array([dp[0] for dp in self._data_buffer])
            positions = np.array([dp[1] for dp in self._data_buffer if dp[1] is not None])
            forces = np.array([dp[2] for dp in self._data_buffer if dp[2] is not None])
            
            if len(forces) == 0:
                print(f"PFL: No valid force data for layer {self.current_layer_number}")
                return False

            success = False
            if self.use_corrected_calculator and self.calculator:
                success = self._analyze_with_corrected_calculator(timestamps, positions, forces)
            else:
                success = self._analyze_with_original_method(timestamps, positions, forces)
                
            print(f"PFL: {'Successfully' if success else 'Failed to'} log layer {self.current_layer_number}")
            return success

    def _analyze_with_corrected_calculator(self, timestamps, positions, forces):
        """Analyze data using the corrected AdhesionMetricsCalculator."""
        try:
            # Use the corrected calculator
            results = self.calculator.calculate_from_arrays(
                timestamps, positions, forces, layer_number=self.current_layer_number
            )
            
            # Extract key metrics with fallbacks
            peak_force = results.get('peak_force', 0.0)
            work_of_adhesion = results.get('work_of_adhesion_mJ', 0.0)
            pre_initiation_time = results.get('pre_initiation_time', np.nan)
            propagation_end_time = results.get('propagation_end_time', np.nan)
            peak_force_time = results.get('peak_force_time', np.nan)
            
            # Calculate durations
            total_duration = results.get('total_peel_duration', np.nan)
            propagation_duration = results.get('propagation_duration', np.nan)
            
            # Position metrics
            peak_position = results.get('peak_force_position', np.nan)
            pre_initiation_distance = results.get('pre_initiation_distance', np.nan)
            total_peel_distance = results.get('total_peel_distance', np.nan)
            
            # Retraction force
            peak_retraction_force = np.min(forces) if len(forces) > 0 else 0.0
            
            # Write to CSV
            return self._write_corrected_csv_entry({
                'peak_force': peak_force,
                'work_of_adhesion_mJ': work_of_adhesion,
                'initiation_time_s': pre_initiation_time,
                'propagation_end_time_s': propagation_end_time,
                'total_duration_s': total_duration,
                'distance_to_peak_mm': pre_initiation_distance,
                'peel_distance_mm': total_peel_distance,
                'peak_retraction_force': peak_retraction_force,
                'peak_position_mm': peak_position,
                'propagation_start_time_s': peak_force_time,
                'propagation_duration_s': propagation_duration
            })
            
        except Exception as e:
            print(f"PFL: Error in corrected calculator analysis for layer {self.current_layer_number}: {e}")
            return False

    def _analyze_with_original_method(self, timestamps, positions, forces):
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
            
            return self._write_original_csv_entry({
                'peak_force': peak_force,
                'work_of_adhesion_mJ': work_of_adhesion_mJ,
                'time_to_peak_s': time_to_peak,
                'peel_time_s': np.nan,  # Not calculated in simple method
                'total_time_s': total_time,
                'distance_to_peak_mm': distance_to_peak,
                'peak_retraction_force': peak_retraction_force
            })
            
        except Exception as e:
            print(f"PFL: Error in original method analysis for layer {self.current_layer_number}: {e}")
            return False

    def _write_corrected_csv_entry(self, results):
        """Write CSV entry using corrected calculator format."""
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        try:
            self._ensure_header()
            with open(self.output_csv_filepath, 'a', newline='') as f:
                writer = csv.writer(f)
                row_data = [
                    self.current_layer_number,
                    f"{results['peak_force']:.4f}",
                    f"{results['work_of_adhesion_mJ']:.4f}",
                    f"{results['initiation_time_s']:.4f}" if not np.isnan(results['initiation_time_s']) else "NaN",
                    f"{results['propagation_end_time_s']:.4f}" if not np.isnan(results['propagation_end_time_s']) else "NaN",
                    f"{results['total_duration_s']:.4f}" if not np.isnan(results['total_duration_s']) else "NaN",
                    f"{results['distance_to_peak_mm']:.4f}" if not np.isnan(results['distance_to_peak_mm']) else "NaN",
                    f"{results['peel_distance_mm']:.4f}" if not np.isnan(results['peel_distance_mm']) else "NaN",
                    f"{results['peak_retraction_force']:.4f}",
                    f"{results['peak_position_mm']:.4f}" if not np.isnan(results['peak_position_mm']) else "NaN",
                    f"{results['propagation_start_time_s']:.4f}" if not np.isnan(results['propagation_start_time_s']) else "NaN",
                    f"{results['propagation_duration_s']:.4f}" if not np.isnan(results['propagation_duration_s']) else "NaN"
                ]
                if self.is_manual_log:
                    writer.writerow([timestamp_str] + row_data)
                else:
                    writer.writerow(row_data)
            return True
        except Exception as e:
            print(f"PFL: Error writing corrected CSV for layer {self.current_layer_number}: {e}")
            return False

    def _write_original_csv_entry(self, results):
        """Write CSV entry using original format."""
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        try:
            self._ensure_header()
            with open(self.output_csv_filepath, 'a', newline='') as f:
                writer = csv.writer(f)
                row_data = [
                    self.current_layer_number,
                    f"{results['peak_force']:.4f}",
                    f"{results['work_of_adhesion_mJ']:.4f}",
                    f"{results['time_to_peak_s']:.4f}" if not np.isnan(results['time_to_peak_s']) else "NaN",
                    f"{results['peel_time_s']:.4f}" if not np.isnan(results['peel_time_s']) else "NaN",
                    f"{results['total_time_s']:.4f}" if not np.isnan(results['total_time_s']) else "NaN",
                    f"{results['distance_to_peak_mm']:.4f}" if not np.isnan(results['distance_to_peak_mm']) else "NaN",
                    f"{results['peak_retraction_force']:.4f}"
                ]
                if self.is_manual_log:
                    writer.writerow([timestamp_str] + row_data)
                else:
                    writer.writerow(row_data)
            return True
        except Exception as e:
            print(f"PFL: Error writing original CSV for layer {self.current_layer_number}: {e}")
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

    def close_log_file(self):
        """Close log file operations."""
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
    
    print("\nUnified PeakForceLogger test complete!")
