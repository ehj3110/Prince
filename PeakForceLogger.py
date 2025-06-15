import csv
import os
import time
from datetime import datetime
import threading
import numpy as np # For numerical operations, especially for work calculation

class PeakForceLogger:
    def __init__(self, output_csv_filepath, is_manual_log=False):
        self.output_csv_filepath = output_csv_filepath
        self.is_manual_log = is_manual_log # Flag to indicate if this instance is for manual logging
        self.current_layer_number = 0
        self._monitoring = False
        self._lock = threading.Lock()
        self._data_buffer = []  # Stores (timestamp, position, force) tuples for the current layer
        self.log_file_exists = os.path.exists(self.output_csv_filepath)
        self._ensure_header()

        # For plotting integration
        self.plot_time_data = []       # Stores ABSOLUTE timestamps for shading
        self.plot_force_data = []      # Stores corresponding forces for shading
        # self.plot_position_data = [] # Not strictly needed for current shading, but could be stored
        
        self.z_peel_peak_mm = None 
        self.z_return_pos_mm = None 

    def _ensure_header(self):
        if not self.log_file_exists:
            with open(self.output_csv_filepath, 'w', newline='') as f:
                writer = csv.writer(f)
                if self.is_manual_log:
                    # Manual log keeps Timestamp, Layer, Peak_Force_N, Work_of_Adhesion_mJ
                    writer.writerow(['Timestamp', 'Layer', 'Peak_Force_N', 'Work_of_Adhesion_mJ'])
                else:
                    # Print run log: Layer, Peak_Force_N, Work_of_Adhesion_mJ
                    writer.writerow(['Layer', 'Peak_Force_N', 'Work_of_Adhesion_mJ'])
            self.log_file_exists = True

    def start_monitoring_for_layer(self, layer_number, z_peel_peak=None, z_return_pos=None):
        with self._lock:
            self.current_layer_number = layer_number
            # For manual logs, z_peel_peak and z_return_pos might not be relevant or provided
            # They are primarily for automated print-run logging.
            self.z_peel_peak_mm = z_peel_peak 
            self.z_return_pos_mm = z_return_pos 
            self._monitoring = True
            self._data_buffer = []
            self.plot_time_data = []  # Reset for new layer/segment
            self.plot_force_data = [] # Reset for new layer/segment
            # self.plot_position_data = []
            print(f"PFL: Started monitoring for layer {self.current_layer_number} with peel {z_peel_peak}mm to {z_return_pos}mm")

    def add_data_point(self, timestamp, position_mm, force_N):
        if self._monitoring:
            with self._lock:
                self._data_buffer.append((timestamp, position_mm, force_N))
                
                if position_mm is not None and self.z_peel_peak_mm is not None and self.z_return_pos_mm is not None:
                    in_peel_range_up = (self.z_peel_peak_mm <= self.z_return_pos_mm and 
                                        self.z_peel_peak_mm <= position_mm <= self.z_return_pos_mm)
                    in_peel_range_down = (self.z_peel_peak_mm > self.z_return_pos_mm and 
                                          self.z_return_pos_mm <= position_mm <= self.z_peel_peak_mm)

                    if in_peel_range_up or in_peel_range_down:
                        self.plot_time_data.append(timestamp) # Store absolute timestamp
                        self.plot_force_data.append(force_N)
                        # self.plot_position_data.append(position_mm)

    def stop_monitoring_and_log_peak(self):
        peak_force = 0
        work_of_adhesion_mJ = 0
        log_entry_made = False

        with self._lock:
            if not self._monitoring and not self._data_buffer: 
                 print(f"PFL: Monitoring was already stopped or no data for layer {self.current_layer_number}. Buffer size {len(self._data_buffer)}")
                 return False

            if self._monitoring and not self._data_buffer:
                print(f"PFL: No data collected during monitoring for layer {self.current_layer_number}.")
            
            self._monitoring = False

            forces = [force for _, _, force in self._data_buffer if force is not None]
            if forces:
                peak_force = max(forces)
            else:
                peak_force = 0

            relevant_data_for_work = []
            if not self.is_manual_log and self.z_peel_peak_mm is not None and self.z_return_pos_mm is not None:
                # Automated log with defined peel range
                for ts, pos, force in self._data_buffer:
                    if pos is not None and force is not None:
                        in_peel_range_up = (self.z_peel_peak_mm <= self.z_return_pos_mm and \
                                            self.z_peel_peak_mm <= pos <= self.z_return_pos_mm)
                        in_peel_range_down = (self.z_peel_peak_mm > self.z_return_pos_mm and \
                                              self.z_return_pos_mm <= pos <= self.z_peel_peak_mm)
                        if in_peel_range_up or in_peel_range_down:
                            relevant_data_for_work.append((pos / 1000.0, force)) # Convert position to meters
            elif self.is_manual_log:
                # Manual log: use all data points in the buffer that have position and force
                for ts, pos, force in self._data_buffer:
                    if pos is not None and force is not None:
                        relevant_data_for_work.append((pos / 1000.0, force)) # Convert position to meters
            
            # Sort by position for correct dx calculation
            relevant_data_for_work.sort(key=lambda x: x[0])

            if len(relevant_data_for_work) >= 2:
                work_J = 0.0
                for i in range(len(relevant_data_for_work) - 1):
                    pos1_m, force1_N = relevant_data_for_work[i]
                    pos2_m, force2_N = relevant_data_for_work[i+1]
                    
                    f1_calc = force1_N if force1_N > 0 else 0
                    f2_calc = force2_N if force2_N > 0 else 0
                    
                    dx_m = abs(pos2_m - pos1_m) 
                    
                    segment_work_J = ((f1_calc + f2_calc) / 2.0) * dx_m
                    work_J += segment_work_J
                work_of_adhesion_mJ = work_J * 1000 # Convert Joules to milliJoules
            elif self._data_buffer: 
                print(f"PFL: Not enough data points ({len(relevant_data_for_work)}) with valid position for work calculation for layer {self.current_layer_number}.")

            timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            try:
                with open(self.output_csv_filepath, 'a', newline='') as f:
                    writer = csv.writer(f)
                    if self.is_manual_log:
                        writer.writerow([
                            timestamp_str, 
                            self.current_layer_number, 
                            f"{peak_force:.4f}", 
                            f"{work_of_adhesion_mJ:.4f}"
                        ])
                    else:
                        # For print run logs, only log Layer, Peak Force, and Work
                        writer.writerow([
                            self.current_layer_number, 
                            f"{peak_force:.4f}", 
                            f"{work_of_adhesion_mJ:.4f}"
                        ])
                log_entry_made = True
                print(f"PFL: Logged data for layer {self.current_layer_number}. Peak Force: {peak_force:.4f} N, Work: {work_of_adhesion_mJ:.4f} mJ")
            except Exception as e:
                print(f"PFL: Error writing to CSV for layer {self.current_layer_number}: {e}")
            
            self._data_buffer = [] 
        return log_entry_made

    def is_monitoring(self):
        return self._monitoring

    def get_current_peel_data_for_plot_shading(self):
        """
        Returns the time and force data points that fall within the current peel segment
        and are currently stored in self.plot_time_data and self.plot_force_data.
        This data is used by SensorDataWindow to shade the peel area on the plot.
        It returns copies of the lists to prevent modification.
        """
        with self._lock:
            # These lists (plot_time_data, plot_force_data) are already filtered 
            # in add_data_point to only include data within the peel range.
            # They store absolute timestamps.
            return list(self.plot_time_data), list(self.plot_force_data)

    def get_data_for_plot(self):
        with self._lock:
            return list(self.plot_time_data), list(self.plot_force_data)

    def close_log_file(self):
        print(f"PFL: Log file operations complete for {self.output_csv_filepath}")

# Example Usage (for testing purposes, not part of the class itself):
if __name__ == '__main__':
    # Create a dummy logger instance
    logger = PeakForceLogger("peak_force_log_test.csv")

    # Simulate for layer 1
    print("\nSimulating Layer 1...")
    logger.start_monitoring_for_layer(1, z_peel_peak=10.0, z_return_pos=12.0) # Peel from 10mm to 12mm
    current_time = time.time()
    logger.add_data_point(current_time + 0.0, 9.8, 0.01)  # Outside peel start
    logger.add_data_point(current_time + 0.1, 10.0, 0.05) # Peel start
    logger.add_data_point(current_time + 0.2, 10.5, 0.20) # In peel
    logger.add_data_point(current_time + 0.3, 11.0, 0.25) # In peel (peak force for this segment)
    logger.add_data_point(current_time + 0.4, 11.5, 0.15) # In peel
    logger.add_data_point(current_time + 0.5, 12.0, 0.08) # Peel end
    logger.add_data_point(current_time + 0.6, 12.2, 0.02) # Outside peel end
    # Check plot data before stopping (it should contain points from 10.0mm to 12.0mm)
    plot_t, plot_f = logger.get_data_for_plot()
    print(f"Layer 1 - Plot time data points: {len(plot_t)}") # Expect 5 points
    print(f"Layer 1 - Plot force data points: {len(plot_f)}")
    logger.stop_monitoring_and_log_peak()


    # Simulate for layer 2 (peeling downwards)
    print("\nSimulating Layer 2...")
    logger.start_monitoring_for_layer(2, z_peel_peak=15.0, z_return_pos=13.0) # Peel from 15mm to 13mm
    current_time = time.time()
    logger.add_data_point(current_time + 0.0, 15.2, 0.01) # Outside
    logger.add_data_point(current_time + 0.1, 15.0, 0.06) # Peel start
    logger.add_data_point(current_time + 0.2, 14.5, 0.22) # In peel
    logger.add_data_point(current_time + 0.3, 14.0, 0.28) # In peel
    logger.add_data_point(current_time + 0.4, 13.5, 0.18) # In peel
    logger.add_data_point(current_time + 0.5, 13.0, 0.07) # Peel end
    logger.add_data_point(current_time + 0.6, 12.8, 0.01) # Outside
    plot_t, plot_f = logger.get_data_for_plot()
    print(f"Layer 2 - Plot time data points: {len(plot_t)}") # Expect 5 points
    logger.stop_monitoring_and_log_peak()

    # Simulate for layer 3 (no valid force data in peel range)
    print("\nSimulating Layer 3...")
    logger.start_monitoring_for_layer(3, z_peel_peak=5.0, z_return_pos=6.0)
    current_time = time.time()
    logger.add_data_point(current_time + 0.0, 4.0, 0.1)
    logger.add_data_point(current_time + 0.1, 7.0, 0.2)
    plot_t, plot_f = logger.get_data_for_plot()
    print(f"Layer 3 - Plot time data points: {len(plot_t)}") # Expect 0 points
    logger.stop_monitoring_and_log_peak()


    # Simulate for layer 4 (not enough data points for work calc)
    print("\nSimulating Layer 4...")
    logger.start_monitoring_for_layer(4, z_peel_peak=8.0, z_return_pos=9.0)
    current_time = time.time()
    logger.add_data_point(current_time + 0.0, 8.5, 0.15) # In peel, but only 1 point
    plot_t, plot_f = logger.get_data_for_plot()
    print(f"Layer 4 - Plot time data points: {len(plot_t)}") # Expect 1 point
    logger.stop_monitoring_and_log_peak()
    
    print(f"\nCheck '{logger.output_csv_filepath}' for results.")
