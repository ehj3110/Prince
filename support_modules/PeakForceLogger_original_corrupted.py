import csv
import os
import time
from datetime import datetime
import threading
import numpy as np # For numerical operations, especially for work calculation
from enhanced_adhesion_metrics import EnhancedAdhesionAnalyzer, create_analyzer

class PeakForceLogger:
    def __init__(self, output_csv_filepath, is_manual_log=False, enhanced_analysis=True, analyzer_type="unified"):
        self.output_csv_filepath = output_csv_filepath
        self.is_manual_log = is_manual_log # Flag to indicate if this instance is for manual logging
        self.enhanced_analysis = enhanced_analysis  # Enable enhanced adhesion analysis
        self.analyzer_type = analyzer_type  # Type of analyzer to use
        self.current_layer_number = 0
        self._monitoring = False
        self._lock = threading.Lock()
        self._data_buffer = []  # Stores (timestamp, position, force) tuples for the current layer
        self.log_file_exists = os.path.exists(self.output_csv_filepath)
        
        # Initialize the adhesion analyzer based on type
        if self.enhanced_analysis:
            self.adhesion_analyzer = create_analyzer(analyzer_type)
from datetime import datetime
import threading
import numpy as np # For numerical operations, especially for work calculation
from adhesion_metrics_calculator import AdhesionMetricsCalculator

class PeakForceLogger:
    def __init__(self, output_csv_filepath, is_manual_log=False, enhanced_analysis=True, analyzer_type="two_step_baseline"):
        self.output_csv_filepath = output_csv_filepath
        self.is_manual_log = is_manual_log # Flag to indicate if this instance is for manual logging
        self.enhanced_analysis = enhanced_analysis  # Enable enhanced adhesion analysis
        self.analyzer_type = analyzer_type  # Type of analyzer to use
        self.current_layer_number = 0
        self._monitoring = False
        self._lock = threading.Lock()
        self._data_buffer = []  # Stores (timestamp, position, force) tuples for the current layer
        self.log_file_exists = os.path.exists(self.output_csv_filepath)
        
        # Initialize analyzer using factory function
        if self.enhanced_analysis:
            self.adhesion_analyzer = create_analyzer(analyzer_type)
        else:
            self.adhesion_analyzer = None
            
        # Only create header for automated logging, not manual logging
        if not self.is_manual_log:
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
                
                if self.enhanced_analysis and self.analyzer_type == "two_step_baseline":
                    # New Two-Step Baseline Analysis header (user's exact specification)
                    header = [
                        'Layer_Number', 'Peak_Force_N', 'Work_of_Adhesion_mJ',
                        'Pre_Initiation_Time_s', 'Propagation_Time_s', 'Total_Peeling_Time_s',
                        'Distance_to_Peel_Start_mm', 'Distance_to_Full_Peel_mm',
                        'Peak_Retraction_Force_N', 'Pre_Peel_Force_N',
                        'Raw_Peak_Force_Reading_N', 'Baseline_Reading_N'
                    ]
                elif self.enhanced_analysis:
                    # Legacy enhanced header for backward compatibility
                    header = [
                        'Layer', 'Peak_Peel_Force_N', 'Work_of_Adhesion_mJ',
                        'Peel_Initiation_Time_s', 'Time_to_Peak_s', 'Peak_to_Completion_s', 'Total_Peel_Duration_s',
                        'Peel_Initiation_Position_mm', 'Peak_Force_Position_mm', 'Peel_Completion_Position_mm',
                        'Max_Loading_Rate_N_s', 'Max_Unloading_Rate_N_s', 'Adhesion_Stiffness_N_per_mm',
                        'Energy_Dissipation_mJ', 'Total_Energy_mJ', 'Work_Baseline_Corrected_mJ',
                        'Energy_Density_mJ_per_mm', 'Force_Signal_to_Noise', 'Peak_Retraction_Force_N'
                    ]
                else:
                    # Original header for backward compatibility
                    header = [
                        'Layer', 'Peak_Peel_Force_N', 'Work_of_Adhesion_mJ',
                        'Time_to_Peel_Start_s', 'Peel_Time_s', 'Total_Peel_Time_s',
                        'Distance_to_Peel_Start_mm', 'Peak_Retraction_Force_N'
                    ]
                
                if self.is_manual_log:
                    # Manual log has a timestamp column at the beginning
                    writer.writerow(['Timestamp'] + header)
                else:
                    writer.writerow(header)
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
        with self._lock:
            if not self._monitoring and not self._data_buffer:
                print(f"PFL: Monitoring was already stopped or no data for layer {self.current_layer_number}. Buffer size {len(self._data_buffer)}")
                return False

            if self._monitoring and not self._data_buffer:
                print(f"PFL: No data collected during monitoring for layer {self.current_layer_number}.")
            
            self._monitoring = False

            if len(self._data_buffer) > 1:
                # Convert buffer to numpy array for processing
                data = np.array(self._data_buffer)
                timestamps = data[:, 0]
                positions = data[:, 1]
                forces = data[:, 2]

                if self.enhanced_analysis and self.adhesion_analyzer:
                    # Use enhanced analysis
                    enhanced_results = self.adhesion_analyzer.analyze_peel_data(timestamps, positions, forces)
                    
                    if self.analyzer_type == "two_step_baseline":
                        # TwoStepBaselineAnalyzer returns direct values, no formatting needed
                        formatted_results = {}  # Not used for our analyzer
                        
                        # Extract key values for logging using our result structure
                        peak_peel_force = enhanced_results.get('peak_force_N', 0)
                        work_of_adhesion_mJ = enhanced_results.get('work_of_adhesion_mJ', 0)
                        peak_retraction_force = enhanced_results.get('peak_retraction_force_N', 0)
                    else:
                        # Legacy enhanced analyzer needs formatting
                        formatted_results = self.adhesion_analyzer.format_results_for_csv(enhanced_results)
                        
                        # Extract key values for logging using legacy structure
                        peak_peel_force = enhanced_results.get('peak_force_magnitude', 0)
                        work_of_adhesion_mJ = enhanced_results.get('work_of_adhesion_mJ', 0)
                        peak_retraction_force = enhanced_results.get('peak_retraction_force_N', 0)
                    
                    # Log enhanced results
                    log_entry_made = self._write_enhanced_csv_entry(enhanced_results, formatted_results)
                    
                    print(f"PFL Enhanced: Layer {self.current_layer_number} - Peak: {peak_peel_force:.4f}N, Work: {work_of_adhesion_mJ:.4f}mJ, Analysis Points: {len(self._data_buffer)}")
                    
                else:
                    # Use original analysis for backward compatibility
                    original_results = self._calculate_original_metrics(timestamps, positions, forces)
                    log_entry_made = self._write_original_csv_entry(original_results)
                    
                    peak_peel_force = original_results.get('peak_peel_force', 0)
                    work_of_adhesion_mJ = original_results.get('work_of_adhesion_mJ', 0)
                    peak_retraction_force = original_results.get('peak_retraction_force', 0)
                    
                    print(f"PFL Original: Layer {self.current_layer_number} - Peak: {peak_peel_force:.4f}N, Work: {work_of_adhesion_mJ:.4f}mJ")

            else:
                print(f"PFL: Not enough data points ({len(self._data_buffer)}) for analysis for layer {self.current_layer_number}.")
                log_entry_made = False
            
            self._data_buffer = []
        return log_entry_made

    def _calculate_original_metrics(self, timestamps, positions, forces):
        """Calculate metrics using the original algorithm for backward compatibility."""
        # Initialize all metrics to default values
        peak_peel_force = 0
        work_of_adhesion_mJ = 0
        time_to_peel_start_s = float('nan')
        peel_time_s = float('nan')
        total_peel_time_s = float('nan')
        distance_to_peel_start_mm = float('nan')
        peak_retraction_force = 0

        # --- Original Metric Calculations ---
        # 1. Find start of peel (assuming it's the first data point)
        peel_start_time = timestamps[0]
        peel_start_position = positions[0]

        # 2. Find peak peel force (max positive force) and its details
        if np.any(forces > 0):
            peak_peel_force_index = np.argmax(forces)
            peak_peel_force = forces[peak_peel_force_index]
            peak_peel_time = timestamps[peak_peel_force_index]
            peak_peel_position = positions[peak_peel_force_index]

            # 3. Calculate Time and Distance to Peel Start
            time_to_peel_start_s = peak_peel_time - peel_start_time
            distance_to_peel_start_mm = abs(peak_peel_position - peel_start_position)

            # 4. Find end of peel (when force drops below a threshold after the peak)
            peel_finish_threshold = 0.01  # Threshold in Newtons
            post_peak_forces = forces[peak_peel_force_index:]
            post_peak_timestamps = timestamps[peak_peel_force_index:]
            
            peel_end_indices = np.where(post_peak_forces < peel_finish_threshold)[0]
            if peel_end_indices.size > 0:
                peel_end_time = post_peak_timestamps[peel_end_indices[0]]
                peel_time_s = peel_end_time - peak_peel_time
                total_peel_time_s = time_to_peel_start_s + peel_time_s

        # 5. Find peak retraction force (most negative force)
        if np.any(forces < 0):
            peak_retraction_force = np.min(forces)

        # --- Work of Adhesion Calculation (Original logic) ---
        relevant_data_for_work = []
        if not self.is_manual_log and self.z_peel_peak_mm is not None and self.z_return_pos_mm is not None:
            for ts, pos, force in self._data_buffer:
                if pos is not None and force is not None:
                    in_peel_range_up = (self.z_peel_peak_mm <= self.z_return_pos_mm and \
                                        self.z_peel_peak_mm <= pos <= self.z_return_pos_mm)
                    in_peel_range_down = (self.z_peel_peak_mm > self.z_return_pos_mm and \
                                          self.z_return_pos_mm <= pos <= self.z_peel_peak_mm)
                    if in_peel_range_up or in_peel_range_down:
                        relevant_data_for_work.append((pos / 1000.0, force))
        elif self.is_manual_log:
            for ts, pos, force in self._data_buffer:
                if pos is not None and force is not None:
                    relevant_data_for_work.append((pos / 1000.0, force))
        
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
            work_of_adhesion_mJ = work_J * 1000
        elif self._data_buffer:
            print(f"PFL: Not enough data points ({len(relevant_data_for_work)}) with valid position for work calculation for layer {self.current_layer_number}.")

        return {
            'peak_peel_force': peak_peel_force,
            'work_of_adhesion_mJ': work_of_adhesion_mJ,
            'time_to_peel_start_s': time_to_peel_start_s,
            'peel_time_s': peel_time_s,
            'total_peel_time_s': total_peel_time_s,
            'distance_to_peel_start_mm': distance_to_peel_start_mm,
            'peak_retraction_force': peak_retraction_force
        }

    def _write_original_csv_entry(self, results):
        """Write CSV entry using original format."""
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        try:
            self._ensure_header()  # Ensure header exists before writing
            with open(self.output_csv_filepath, 'a', newline='') as f:
                writer = csv.writer(f)
                row_data = [
                    self.current_layer_number,
                    f"{results['peak_peel_force']:.4f}",
                    f"{results['work_of_adhesion_mJ']:.4f}",
                    f"{results['time_to_peel_start_s']:.4f}" if not np.isnan(results['time_to_peel_start_s']) else "NaN",
                    f"{results['peel_time_s']:.4f}" if not np.isnan(results['peel_time_s']) else "NaN",
                    f"{results['total_peel_time_s']:.4f}" if not np.isnan(results['total_peel_time_s']) else "NaN",
                    f"{results['distance_to_peel_start_mm']:.4f}" if not np.isnan(results['distance_to_peel_start_mm']) else "NaN",
                    f"{results['peak_retraction_force']:.4f}"
                ]
                if self.is_manual_log:
                    writer.writerow([timestamp_str] + row_data)
                else:
                    writer.writerow(row_data)
            return True
        except Exception as e:
            print(f"PFL: Error writing to CSV for layer {self.current_layer_number}: {e}")
            return False

    def _write_enhanced_csv_entry(self, enhanced_results, formatted_results):
        """Write CSV entry using enhanced format."""
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        try:
            self._ensure_header()  # Ensure header exists before writing
            with open(self.output_csv_filepath, 'a', newline='') as f:
                writer = csv.writer(f)
                
                if self.analyzer_type == "two_step_baseline":
                    # New Two-Step Baseline Analysis format (user's exact specification)
                    row_data = [
                        self.current_layer_number,
                        f"{enhanced_results.get('peak_force_N', 0.0):.4f}",
                        f"{enhanced_results.get('work_of_adhesion_mJ', 0.0):.4f}",
                        f"{enhanced_results.get('pre_initiation_time_s', 0.0):.4f}",
                        f"{enhanced_results.get('propagation_time_s', 0.0):.4f}",
                        f"{enhanced_results.get('total_peeling_time_s', 0.0):.4f}",
                        f"{enhanced_results.get('distance_to_peel_start_mm', 0.0):.4f}",
                        f"{enhanced_results.get('distance_to_full_peel_mm', 0.0):.4f}",
                        f"{enhanced_results.get('peak_retraction_force_N', 0.0):.4f}",
                        f"{enhanced_results.get('pre_peel_force_N', 0.0):.4f}",
                        f"{enhanced_results.get('raw_peak_force_reading_N', 0.0):.4f}",
                        f"{enhanced_results.get('baseline_reading_N', 0.0):.4f}"
                    ]
                else:
                    # Legacy enhanced format for backward compatibility
                    row_data = [
                        self.current_layer_number,
                        formatted_results.get('peak_force_magnitude', '0.0000'),
                        formatted_results.get('work_of_adhesion_mJ', '0.0000'),
                        formatted_results.get('peel_initiation_time', 'NaN'),
                        formatted_results.get('time_to_peak_from_initiation', 'NaN'),
                        formatted_results.get('peak_to_completion_time', 'NaN'),
                        formatted_results.get('total_peel_duration', 'NaN'),
                        formatted_results.get('peel_initiation_position', 'NaN'),
                        formatted_results.get('peak_force_position', 'NaN'),
                        formatted_results.get('peel_completion_position', 'NaN'),
                        formatted_results.get('max_loading_rate', '0.000'),
                        formatted_results.get('max_unloading_rate', '0.000'),
                        formatted_results.get('adhesion_stiffness_N_per_mm', 'NaN'),
                        formatted_results.get('energy_dissipation_mJ', '0.0000'),
                        formatted_results.get('total_energy_mJ', '0.0000'),
                        formatted_results.get('work_baseline_corrected_mJ', '0.0000'),
                        formatted_results.get('energy_density_mJ_per_mm', '0.0000'),
                        formatted_results.get('force_signal_to_noise', 'NaN'),
                        formatted_results.get('peak_retraction_force_N', '0.0000') if 'peak_retraction_force_N' in formatted_results 
                            else f"{np.min(enhanced_results.get('forces', [0])):.4f}" if len(enhanced_results.get('forces', [])) > 0 else '0.0000'
                    ]
                
                if self.is_manual_log:
                    writer.writerow([timestamp_str] + row_data)
                else:
                    writer.writerow(row_data)
            return True
        except Exception as e:
            print(f"PFL: Error writing enhanced CSV for layer {self.current_layer_number}: {e}")
            return False

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
