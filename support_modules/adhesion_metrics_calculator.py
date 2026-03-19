"""
Adhesion Metrics Calculator
===========================

Unified calculator for adhesion metrics during DLP resin 3D printing.
Implements the exact methodology defined in WORK_OF_ADHESION_METRICS_DEFINITIONS.md

This calculator can work with:
- Live data arrays during printing
- Saved CSV files for post-processing
- Pandas DataFrames for batch analysis

Author: Cheng Sun Lab Team
Date: September 19, 2025
"""

import numpy as np
import pandas as pd
from scipy import integrate
from scipy.signal import savgol_filter, medfilt
import warnings
from typing import Dict, Tuple, Optional, Union
from pathlib import Path


class AdhesionMetricsCalculator:
    """
    Unified calculator for adhesion metrics using a reverse-search, second-derivative
    propagation end detection method and two-step filtering (Median + Savitzky-Golay).
    """
    
    def __init__(self, 
                 median_kernel=31,
                 savgol_window=51,
                 savgol_order=3,
                 baseline_threshold_factor=0.002,
                 baseline_mode='prop_end_point',
                 baseline_window_points=25,
                 prop_end_mode='second_derivative_zero_crossing',
                 prop_end_local_window_seconds=1.0,
                 min_peak_height=0.01,
                 min_peak_distance=50):
        """
        Initialize the adhesion metrics calculator. 
        
        Args:
            median_kernel (int): Kernel size for median filter (must be odd, for outlier rejection).
            savgol_window (int): Window length for Savitzky-Golay filter (must be odd).
            savgol_order (int): Polynomial order for Savitzky-Golay filter.
            baseline_threshold_factor (float): Threshold above baseline for initiation detection (N).
            baseline_mode (str): Baseline strategy.
                - 'prop_end_point': force at propagation end index.
                - 'two_step': mean force in forward stabilization window.
            baseline_window_points (int): Forward averaging window size for two_step baseline.
            prop_end_mode (str): Propagation-end mode.
                Supported: 'second_derivative_zero_crossing',
                'two_step_max_second_derivative'.
            prop_end_local_window_seconds (float): Local post-peak window duration
                used by two_step_max_second_derivative mode.
            min_peak_height (float): Minimum peak height for detection (N).
            min_peak_distance (int): Minimum distance between peaks (data points).
        """
        self.median_kernel = median_kernel if median_kernel % 2 == 1 else median_kernel + 1
        self.savgol_window = savgol_window if savgol_window % 2 == 1 else savgol_window + 1
        self.savgol_order = savgol_order
        self.baseline_threshold_factor = baseline_threshold_factor
        self.baseline_mode = baseline_mode
        self.baseline_window_points = baseline_window_points
        self.prop_end_mode = prop_end_mode
        self.prop_end_local_window_seconds = prop_end_local_window_seconds
        self.min_peak_height = min_peak_height
        self.min_peak_distance = min_peak_distance
        
    def calculate_from_arrays(self, 
                            time_data: np.ndarray, 
                            position_data: np.ndarray, 
                            force_data: np.ndarray,
                            layer_number: Optional[int] = None,
                            motion_end_idx: Optional[int] = None,
                            lifting_start_idx: Optional[int] = None,
                            retraction_force_data: Optional[np.ndarray] = None,
                            retraction_start_idx: Optional[int] = None,
                            contact_area: float = 1.0) -> Dict:
        """
        Calculate adhesion metrics from numpy arrays (live data or pre-loaded).
        
        Args:
            time_data: Time values (seconds).
            position_data: Position values (mm).
            force_data: Force values (N).
            layer_number: Layer identifier (optional).
            motion_end_idx: Index where stage motion ends (optional, uses full data if None).
            lifting_start_idx: Index where lifting phase started at prescribed speed (optional). 
                             For smooth lifting (2-stage), this should be the start of Stage 2 (prescribed speed),
                             not Stage 1 (gentle break). Prevents pre-initiation search from going
                             before this point, which is critical when earlier phases create pre-existing forces.
            retraction_force_data: Optional force array from the retraction phase.
            retraction_start_idx: Global index of the first retraction sample.
            contact_area: Contact area in m^2 used for energy release rate G.
            
        Returns:
            Dictionary containing all calculated metrics.
        """
        # Convert to numpy arrays and validate
        times = np.asarray(time_data)
        positions = np.asarray(position_data)
        forces = np.asarray(force_data)
        
        if len(times) != len(positions) or len(times) != len(forces):
            raise ValueError("Time, position, and force arrays must have the same length")
            
        if len(times) < 10:
            return self._empty_results(layer_number, contact_area)
            
        # Remove any NaN or infinite values
        valid_mask = np.isfinite(times) & np.isfinite(positions) & np.isfinite(forces)
        times = times[valid_mask]
        positions = positions[valid_mask]
        forces = forces[valid_mask]
        
        if len(times) < 10:
            return self._empty_results(layer_number, contact_area)
            
        # Apply smoothing using Gaussian filter
        smoothed_force = self._apply_smoothing(forces)
        
        # Calculate metrics using the new methodology with phase awareness
        return self._calculate_metrics(times, positions, forces, smoothed_force, 
                                     layer_number, motion_end_idx, lifting_start_idx,
                                     retraction_force_data, retraction_start_idx,
                                     contact_area)
    
    def calculate_from_csv(self, 
                          csv_filepath: Union[str, Path],
                          time_col: str = 'Time',
                          position_col: str = 'Position', 
                          force_col: str = 'Force',
                          layer_number: Optional[int] = None) -> Dict:
        """
        Calculate adhesion metrics from a CSV file.
        
        Args:
            csv_filepath: Path to CSV file.
            time_col: Name of time column.
            position_col: Name of position column.
            force_col: Name of force column.
            layer_number: Layer identifier (optional).
            
        Returns:
            Dictionary containing all calculated metrics.
        """
        try:
            df = pd.read_csv(csv_filepath)
            return self.calculate_from_dataframe(df, time_col, position_col, force_col, layer_number)
        except Exception as e:
            print(f"Error reading CSV file {csv_filepath}: {e}")
            return self._empty_results(layer_number)
    
    def calculate_from_dataframe(self, 
                               df: pd.DataFrame,
                               time_col: str = 'Time',
                               position_col: str = 'Position',
                               force_col: str = 'Force',
                               layer_number: Optional[int] = None) -> Dict:
        """
        Calculate adhesion metrics from a pandas DataFrame.
        
        Args:
            df: DataFrame with time, position, force data.
            time_col: Name of time column.
            position_col: Name of position column.  
            force_col: Name of force column.
            layer_number: Layer identifier (optional).
            
        Returns:
            Dictionary containing all calculated metrics.
        """
        try:
            # Extract data arrays
            time_data = df[time_col].values
            position_data = df[position_col].values
            force_data = df[force_col].values
            
            return self.calculate_from_arrays(time_data, position_data, force_data, layer_number)
        except KeyError as e:
            print(f"Column not found in DataFrame: {e}")
            return self._empty_results(layer_number)
        except Exception as e:
            print(f"Error processing DataFrame: {e}")
            return self._empty_results(layer_number)
    
    def _apply_smoothing(self, force_data: np.ndarray) -> np.ndarray:
        """
        Apply two-step filtering: Median filter for outlier rejection, then Savitzky-Golay for smoothing.
        
        This is the optimal filtering approach determined through comprehensive testing.
        - Step 1: Median filter (kernel=5) removes sharp outlier peaks
        - Step 2: Savitzky-Golay filter (window=9, order=2) smooths while preserving peak shape
        
        Args:
            force_data: Raw force data.
            
        Returns:
            Smoothed force data.
        """
        if len(force_data) < max(self.median_kernel, self.savgol_window):
            return force_data.copy()
            
        try:
            # Step 1: Median filter for outlier rejection (removes sharp spikes)
            median_filtered = medfilt(force_data, kernel_size=self.median_kernel)
            
            # Step 2: Savitzky-Golay filter for smoothing (preserves peak shape)
            smoothed = savgol_filter(median_filtered, 
                                    window_length=self.savgol_window,
                                    polyorder=self.savgol_order)
            return smoothed
        except Exception as e:
            warnings.warn(f"Two-step filtering failed: {e}. Using raw data.")
            return force_data.copy()
    
    def _calculate_metrics(self, 
                         times: np.ndarray, 
                         positions: np.ndarray, 
                         forces: np.ndarray, 
                         smoothed_force: np.ndarray,
                         layer_number: Optional[int],
                         motion_end_idx: Optional[int],
                         lifting_start_idx: Optional[int] = None,
                         retraction_force_data: Optional[np.ndarray] = None,
                         retraction_start_idx: Optional[int] = None,
                         contact_area: float = 1.0) -> Dict:
        """
        Calculate all adhesion metrics using the new methodology.
        
        Args:
            times: Time array
            positions: Position array  
            forces: Force array
            smoothed_force: Smoothed force data
            layer_number: Layer identifier
            motion_end_idx: Index where motion ends
            lifting_start_idx: Index where lifting at prescribed speed started (phase awareness).
                             For smooth lifting (2-stage), this is Stage 2 start, not Stage 1.
        """
        area_m2 = float(contact_area)
        results = {
            'layer_number': layer_number,
            'contact_area_m2': area_m2,
        }
        
        # Step 1: Find peak force
        peak_idx, peak_force_absolute = self._find_peak_force(smoothed_force)
        results['peak_force_absolute'] = peak_force_absolute
        results['peak_force_position'] = positions[peak_idx]
        results['peak_force_time'] = times[peak_idx] - times[0]  # Relative time
        
        # Step 2: Find propagation end using configured mode.
        mode = str(getattr(self, 'prop_end_mode', 'second_derivative_zero_crossing')).lower()

        if mode == 'second_derivative_zero_crossing':
            prop_end_idx = self._find_propagation_end_second_derivative_zero_crossing(
                smoothed_force, peak_idx, motion_end_idx
            )
        elif mode == 'two_step_max_second_derivative':
            prop_end_idx = self._find_propagation_end_two_step_max_second_derivative(
                times, smoothed_force, peak_idx, motion_end_idx
            )
        else:
            raise ValueError(
                f"Unsupported prop_end_mode '{self.prop_end_mode}'. "
                "Supported modes: second_derivative_zero_crossing, two_step_max_second_derivative"
            )

        # Step 3: Calculate baseline at propagation end and corrected peak force.
        baseline = self._calculate_baseline(smoothed_force, prop_end_idx)
        results['baseline_force'] = baseline
        peak_force_corrected = peak_force_absolute - baseline
        results['peak_force'] = peak_force_corrected
        results['peak_force_corrected'] = peak_force_corrected
        results['force_range'] = peak_force_absolute - baseline

        results['propagation_end_position'] = positions[prop_end_idx]
        results['propagation_end_time'] = times[prop_end_idx] - times[0]
        
        # COMMENTED OUT: Old derivative-based propagation end detection
        # This method searched for where the first derivative rises above 10% of its
        # most prominent negative peak. However, for very slow force relaxation,
        # this method was cutting off propagation too early (~40% of lift instead of expected 80%).
        # The force decay rate remained too slow for too long, never crossing the threshold.
        #
        # prop_end_idx = self._find_propagation_end_reverse_search(
        #     smoothed_force, peak_idx, positions, motion_end_idx)
        # baseline = self._calculate_baseline(smoothed_force, prop_end_idx)
        
        # Step 4: Find pre-initiation start (with phase awareness)
        pre_init_idx = self._find_pre_initiation(smoothed_force, peak_idx, baseline, lifting_start_idx)
        results['pre_initiation_position'] = positions[pre_init_idx]
        results['pre_initiation_time'] = times[pre_init_idx] - times[0]
        results['pre_initiation_force'] = smoothed_force[pre_init_idx]
        
        # Step 5: Calculate temporal metrics
        results['pre_initiation_duration'] = times[peak_idx] - times[pre_init_idx]
        results['propagation_duration'] = times[prop_end_idx] - times[peak_idx]
        results['total_peel_duration'] = times[prop_end_idx] - times[pre_init_idx]
        
        # Step 6: Calculate spatial metrics
        results['pre_initiation_distance'] = positions[peak_idx] - positions[pre_init_idx]
        results['propagation_distance'] = positions[prop_end_idx] - positions[peak_idx]
        results['total_peel_distance'] = positions[prop_end_idx] - positions[pre_init_idx]
        
        # Step 7: Calculate work and energy metrics
        work_metrics = self._calculate_work_metrics(
            positions, forces, smoothed_force, baseline, pre_init_idx, peak_idx, prop_end_idx)
        results.update(work_metrics)
        
         # Step 8: Calculate effective stiffness from pre-initiation stage
        stiffness_metrics = self._calculate_stiffness(
            positions, forces, smoothed_force, baseline, pre_init_idx, peak_idx)
        results.update(stiffness_metrics)
        
        # Step 9: Calculate dynamic metrics
        dynamic_metrics = self._calculate_dynamic_metrics(
            times, forces, smoothed_force, pre_init_idx, peak_idx, prop_end_idx)
        results.update(dynamic_metrics)
        
        # Step 10: Calculate data quality metrics
        quality_metrics = self._calculate_quality_metrics(forces, smoothed_force, baseline, peak_force_corrected)
        results.update(quality_metrics)

        # Step 11: Partitioned baseline-corrected energies from lift-start(0) to peak/prop-end.
        partitioned_energy_metrics = self._calculate_partitioned_energy_metrics(
            positions, forces, baseline, peak_idx, prop_end_idx, area_m2
        )
        results.update(partitioned_energy_metrics)

        # Step 12: Optional retraction metrics from paired retraction phase data.
        retraction_metrics = self._calculate_retraction_metrics(
            retraction_force_data, retraction_start_idx
        )
        results.update(retraction_metrics)
        
        return results

    def _calculate_partitioned_energy_metrics(
        self,
        positions: np.ndarray,
        forces: np.ndarray,
        baseline: float,
        peak_idx: int,
        prop_end_idx: int,
        contact_area_m2: float,
    ) -> Dict:
        """
        Calculate partitioned baseline-corrected energies in Joules.

        Partitions:
        - Total work: lift start (index 0) to propagation end
        - Propagation energy: peak index to propagation end
        - Initiation (dissipated) energy: lift start (index 0) to peak index
        """
        results = {
            'work_of_adhesion_total_J': 0.0,
            'energy_release_rate_G_J_per_m2': 0.0,
            'dissipated_energy_initiation_J': 0.0,
        }

        if len(positions) < 2 or len(forces) < 2:
            return results

        end_idx = int(np.clip(prop_end_idx, 0, len(positions) - 1))
        peak_idx = int(np.clip(peak_idx, 0, end_idx))

        pos_total_m = positions[0:end_idx + 1] / 1000.0
        force_total_corr = forces[0:end_idx + 1] - baseline

        pos_prop_m = positions[peak_idx:end_idx + 1] / 1000.0
        force_prop_corr = forces[peak_idx:end_idx + 1] - baseline

        pos_init_m = positions[0:peak_idx + 1] / 1000.0
        force_init_corr = forces[0:peak_idx + 1] - baseline

        try:
            if len(pos_total_m) >= 2:
                results['work_of_adhesion_total_J'] = float(np.trapezoid(force_total_corr, pos_total_m))

            propagation_energy_J = 0.0
            if len(pos_prop_m) >= 2:
                propagation_energy_J = float(np.trapezoid(force_prop_corr, pos_prop_m))

            if len(pos_init_m) >= 2:
                results['dissipated_energy_initiation_J'] = float(np.trapezoid(force_init_corr, pos_init_m))

            if contact_area_m2 > 0:
                results['energy_release_rate_G_J_per_m2'] = propagation_energy_J / contact_area_m2
            else:
                warnings.warn("contact_area must be > 0 for energy release rate. Returning G=0.")
        except Exception as e:
            warnings.warn(f"Partitioned energy metric calculation failed: {e}")

        return results

    def _calculate_retraction_metrics(
        self,
        retraction_force_data: Optional[np.ndarray],
        retraction_start_idx: Optional[int],
    ) -> Dict:
        """
        Calculate peak retraction force and global index from retraction phase data.
        """
        results = {
            'peak_retraction_force_N': 0.0,
            'peak_retraction_idx': -1,
        }

        if retraction_force_data is None:
            return results

        retraction_force = np.asarray(retraction_force_data)
        if len(retraction_force) == 0:
            return results

        try:
            peak_rel_idx = int(np.argmax(np.abs(retraction_force)))
            results['peak_retraction_force_N'] = float(np.abs(retraction_force[peak_rel_idx]))
            if retraction_start_idx is not None:
                results['peak_retraction_idx'] = int(retraction_start_idx) + peak_rel_idx
            else:
                results['peak_retraction_idx'] = peak_rel_idx
        except Exception as e:
            warnings.warn(f"Retraction metric calculation failed: {e}")

        return results
    
    def _calculate_baseline(self, smoothed_force: np.ndarray, prop_end_idx: Optional[int] = None) -> float:
        """
        Calculate baseline using configured strategy.
        """
        if prop_end_idx is None:
            prop_end_idx = len(smoothed_force) - 1

        prop_end_idx = int(np.clip(prop_end_idx, 0, len(smoothed_force) - 1))
        mode = str(getattr(self, 'baseline_mode', 'prop_end_point')).lower()

        if mode == 'two_step':
            n_points = max(1, int(getattr(self, 'baseline_window_points', 25)))
            end_idx = min(prop_end_idx + n_points, len(smoothed_force))
            return float(np.mean(smoothed_force[prop_end_idx:end_idx]))

        return float(smoothed_force[prop_end_idx])
    
    def _find_peak_force(self, smoothed_force: np.ndarray) -> Tuple[int, float]:
        """
        Find peak force index and value.
        """
        peak_idx = np.argmax(smoothed_force)
        peak_force = smoothed_force[peak_idx]
        return peak_idx, peak_force
    
    def _find_pre_initiation(self, smoothed_force: np.ndarray, peak_idx: int, baseline: float, 
                            lifting_start_idx: Optional[int] = None) -> int:
        """
        Find pre-initiation start - the point where force crosses baseline.
        
        Searches backwards from peak to find where force equals baseline (within tolerance).
        This represents the moment when adhesion forces begin to develop.
        
        Special case for sandwich data: If the force starts HIGHER than baseline
        (indicating pre-existing adhesion), use the beginning of the data as the
        pre-initiation point.
        
        NEW: Phase awareness - if lifting_start_idx is provided, the search will not
        go before this point. This prevents searching past Exposure/Pause/Sandwich phases
        when those phases create pre-existing force above baseline.
        
        For smooth lifting (2-stage), lifting_start_idx should point to Stage 2 start (prescribed speed),
        not Stage 1. This ensures pre-initiation detection starts where the actual peel
        at normal speed begins, excluding the gentle break phase.
        
        Args:
            smoothed_force: Smoothed force data
            peak_idx: Index of peak force
            baseline: Baseline force level
            lifting_start_idx: Optional index where prescribed-speed lifting phase started (phase boundary).
                             For smooth lifting: Stage 2 start. For standard: motion start.
            
        Returns:
            Index where force crosses baseline before peak
        """
        # Small tolerance for numerical comparison (0.1% of baseline or minimum 0.001 N)
        tolerance = max(abs(baseline) * 0.001, 0.001)
        
        # Search backwards from peak to find baseline crossing.
        # Priority 1: if a phase boundary is provided, search the full lift phase.
        # Priority 2: fallback to a wide look-back window for compliant materials.
        if lifting_start_idx is not None:
            search_start = int(np.clip(lifting_start_idx, 0, peak_idx))
            print(f"Pre-initiation search uses full lift phase indices {search_start}-{peak_idx} (lifting started at {lifting_start_idx})")
        else:
            search_start = max(0, peak_idx - 1000)
        
        # Special case: Check if the force at the beginning is already above baseline
        # This happens with sandwich data where adhesion exists before lifting starts
        if smoothed_force[search_start] > (baseline + tolerance):
            # Force starts above baseline - use the beginning as pre-initiation
            return search_start
        
        for i in range(peak_idx - 1, search_start, -1):
            # Check if force is at or below baseline (within tolerance)
            if smoothed_force[i] <= (baseline + tolerance):
                return i  # Return the baseline crossing point
                
        # If no crossing found, return search start
        return search_start

    def _find_propagation_end_reverse_search(self, 
                                           smoothed_force: np.ndarray, 
                                           peak_idx: int,
                                           positions: np.ndarray,
                                           motion_end_idx: Optional[int]) -> int:
        """
        Find propagation end using first derivative prominent peak method.
        
        Method:
        1. Find the MOST PROMINENT NEGATIVE PEAK in the first derivative 
           (steepest downward slope) between peak force and 80% of lifting phase
        2. Calculate 10% threshold of that peak's magnitude
        3. Search forward from the peak to find where derivative rises back to threshold
        4. This is where propagation ends (force decay has slowed to 10% of maximum rate)
        
        Physical meaning: The most prominent negative peak in dF/dt is where the force
        is dropping fastest during propagation. When the rate rises back to 10% of that
        maximum, propagation is essentially complete.
        """
        # 1. Define the full search region from the peak to the end of motion
        search_start_abs = peak_idx
        search_end_abs = motion_end_idx if motion_end_idx is not None else len(smoothed_force) - 1
        
        if (search_end_abs - search_start_abs) < 10:
            return search_end_abs  # Not enough data, return end of motion

        # 2. Determine the "80% point in lifting stage" for position constraint
        try:
            travel_positions = positions[search_start_abs:search_end_abs]
            if len(travel_positions) > 0:
                # Find the minimum position (maximum travel point)
                min_pos = np.min(travel_positions)
                max_pos = positions[peak_idx]
                
                # 80% of the lifting distance
                target_position = max_pos - 0.8 * (max_pos - min_pos)
                
                # Find index where position first reaches or passes the 80% point
                lifting_80pct_idx = search_start_abs
                for i in range(search_start_abs, search_end_abs):
                    if positions[i] <= target_position:
                        lifting_80pct_idx = i
                        break
                else:
                    # If never reached 80%, use the minimum position index
                    min_pos_relative_idx = np.argmin(travel_positions)
                    lifting_80pct_idx = search_start_abs + min_pos_relative_idx
            else:
                lifting_80pct_idx = search_end_abs
        except Exception:
            lifting_80pct_idx = search_end_abs

        # 3. Calculate first derivative for the FULL region from peak to end of motion
        try:
            # Use full region from peak to end of motion (not just 80%)
            full_region = smoothed_force[peak_idx:search_end_abs+1]
            if len(full_region) < 5:
                return search_end_abs

            # Calculate first derivative using np.gradient
            first_derivative = np.gradient(full_region)
            
            # 4. Find the MOST PROMINENT NEGATIVE PEAK in the first derivative
            # Search only up to 80% lifting point for the peak itself
            # (physical reasoning: steepest propagation should happen in first 80%)
            search_80pct_relative = lifting_80pct_idx - peak_idx
            deriv_search_region = first_derivative[:search_80pct_relative+1] if search_80pct_relative < len(first_derivative) else first_derivative
            
            from scipy.signal import find_peaks
            
            # Invert to find negative peaks
            inverted_deriv = -deriv_search_region
            
            # Find peaks with prominence to get the most significant one
            peaks, properties = find_peaks(inverted_deriv, prominence=0.001)
            
            if len(peaks) > 0:
                # Get the most prominent peak (highest prominence)
                most_prominent_idx = peaks[np.argmax(properties['prominences'])]
                most_prominent_value = deriv_search_region[most_prominent_idx]  # This will be negative
            else:
                # No prominent peaks found, use the minimum (most negative) value
                most_prominent_idx = np.argmin(deriv_search_region)
                most_prominent_value = deriv_search_region[most_prominent_idx]
            
            # 5. Calculate 10% threshold (10% of the magnitude)
            # Since the value is negative, threshold is closer to zero
            threshold = most_prominent_value * 0.10  # e.g., if peak is -0.5, threshold is -0.05
            
            # 6. Search forward from the prominent peak through the FULL derivative array
            # This allows finding threshold crossing beyond 80% if needed
            threshold_idx = None
            for i in range(most_prominent_idx + 1, len(first_derivative)):
                if first_derivative[i] > threshold:
                    # Found where derivative rises above threshold (decay rate has slowed)
                    threshold_idx = i
                    break
            
            # If no threshold crossing found, use a conservative estimate
            if threshold_idx is None:
                # Use a point that's 50% from peak to end
                threshold_idx = most_prominent_idx + int(0.5 * (len(first_derivative) - most_prominent_idx))
            
            # Convert back to absolute index in the original array
            propagation_end_idx = peak_idx + threshold_idx
            
            # Cap at end of motion, but NOT at 80% lifting point
            propagation_end_idx = min(propagation_end_idx, search_end_abs)
            
            return propagation_end_idx

        except Exception as e:
            warnings.warn(f"Second derivative 10% threshold search failed: {e}. Using 95% lifting point as fallback.")
            return search_end_abs

    def _find_propagation_end_second_derivative_zero_crossing(
        self,
        smoothed_force: np.ndarray,
        peak_idx: int,
        motion_end_idx: Optional[int],
    ) -> int:
        """
        Modern mode: highest second-derivative peak after force peak,
        then first zero-crossing after that peak.
        """
        search_end_abs = motion_end_idx if motion_end_idx is not None else len(smoothed_force) - 1
        if search_end_abs <= peak_idx + 2:
            return search_end_abs

        region = smoothed_force[peak_idx:search_end_abs + 1]
        if len(region) < 5:
            return search_end_abs

        second_derivative = np.gradient(np.gradient(region))

        peak_candidates = [
            i for i in range(1, len(second_derivative) - 1)
            if second_derivative[i] > second_derivative[i - 1]
            and second_derivative[i] >= second_derivative[i + 1]
        ]
        if not peak_candidates:
            return search_end_abs

        best_peak_rel = max(peak_candidates, key=lambda i: second_derivative[i])
        for j in range(best_peak_rel + 1, len(second_derivative)):
            if float(second_derivative[j - 1]) > 0 and float(second_derivative[j]) <= 0:
                return peak_idx + j

        return search_end_abs

    def _find_propagation_end_two_step_max_second_derivative(
        self,
        times: np.ndarray,
        smoothed_force: np.ndarray,
        peak_idx: int,
        motion_end_idx: Optional[int],
    ) -> int:
        """
        Legacy two-step Step 1: locate maximum second derivative in a local
        post-peak window and map its timestamp to global index.
        """
        search_end_abs = motion_end_idx if motion_end_idx is not None else len(smoothed_force) - 1
        if search_end_abs <= peak_idx + 3:
            return search_end_abs

        sample_rate_hz = 50.0
        if len(times) > 1:
            dt = np.diff(times)
            dt = dt[np.isfinite(dt) & (dt > 0)]
            if len(dt) > 0:
                sample_rate_hz = 1.0 / float(np.median(dt))

        window_seconds = float(getattr(self, 'prop_end_local_window_seconds', 1.0))
        window_points = max(10, int(round(window_seconds * sample_rate_hz)))
        local_end = min(search_end_abs, peak_idx + window_points)

        window_force = smoothed_force[peak_idx:local_end + 1]
        window_time = times[peak_idx:local_end + 1]
        if len(window_force) < 5:
            return local_end

        first_derivative = np.diff(window_force)
        if len(first_derivative) < 3:
            return local_end

        first_deriv_time = (window_time[:-1] + window_time[1:]) / 2.0
        second_derivative = np.diff(first_derivative)
        if len(second_derivative) == 0:
            return local_end

        second_deriv_time = (first_deriv_time[:-1] + first_deriv_time[1:]) / 2.0
        max_second_deriv_idx = int(np.argmax(second_derivative))
        target_time = float(second_deriv_time[max_second_deriv_idx])
        global_idx = int(np.argmin(np.abs(times - target_time)))

        return int(np.clip(global_idx, peak_idx, search_end_abs))
    
    def _calculate_work_metrics(self, 
                              positions: np.ndarray, 
                              forces: np.ndarray, 
                              smoothed_force: np.ndarray,
                              baseline: float,
                              pre_init_idx: int,
                              peak_idx: int,
                              prop_end_idx: int) -> Dict:
        """
        Calculate work and energy metrics.
        
        Work of adhesion is integrated from PRE-INITIATION START to PROPAGATION END
        (entire loading phase: pre-initiation + propagation).
        """
        results = {}
        
        # Extract peel region data - FROM PRE-INITIATION START TO PROPAGATION END
        peel_positions = positions[pre_init_idx:prop_end_idx+1]
        peel_forces = forces[pre_init_idx:prop_end_idx+1]
        peel_forces_corrected = peel_forces - baseline
        
        if len(peel_positions) < 2:
            results.update({
                'work_of_adhesion_mJ': 0.0,
                'work_of_adhesion_corrected_mJ': 0.0,
                'energy_dissipation_mJ': 0.0,
                'total_energy_mJ': 0.0,
                'energy_density_mJ_per_mm': 0.0
            })
            return results
        
        # Convert positions to meters for work calculation
        peel_positions_m = peel_positions / 1000.0
        
        # Ensure positions are in increasing order for integration
        if np.any(np.diff(peel_positions_m) <= 0):
            warnings.warn("Peel positions are not in increasing order. Sorting may be required.")
            sorted_indices = np.argsort(peel_positions_m)
            peel_positions_m = peel_positions_m[sorted_indices]
            peel_forces = peel_forces[sorted_indices]
            peel_forces_corrected = peel_forces_corrected[sorted_indices]
        
        try:
            # Work of adhesion (trapezoidal integration)
            work_J = np.trapezoid(peel_forces, peel_positions_m)
            results['work_of_adhesion_mJ'] = work_J * 1000
            
            # Baseline-corrected work
            work_corrected_J = np.trapezoid(peel_forces_corrected, peel_positions_m)
            results['work_of_adhesion_corrected_mJ'] = work_corrected_J * 1000
            
            # Energy dissipation (negative work regions)
            negative_forces = np.minimum(peel_forces_corrected, 0)
            dissipation_J = np.trapezoid(np.abs(negative_forces), peel_positions_m)
            results['energy_dissipation_mJ'] = dissipation_J * 1000
            
            # Total energy
            total_energy_J = np.trapezoid(np.abs(peel_forces_corrected), peel_positions_m)
            results['total_energy_mJ'] = total_energy_J * 1000
            
            # Energy density
            total_distance = np.max(peel_positions) - np.min(peel_positions)
            if total_distance > 0:
                results['energy_density_mJ_per_mm'] = (work_corrected_J * 1000) / total_distance
            else:
                results['energy_density_mJ_per_mm'] = 0.0
                
        except Exception as e:
            warnings.warn(f"Work calculation failed: {e}")
            results.update({
                'work_of_adhesion_mJ': 0.0,
                'work_of_adhesion_corrected_mJ': 0.0,
                'energy_dissipation_mJ': 0.0,
                'total_energy_mJ': 0.0,
                'energy_density_mJ_per_mm': 0.0
            })
        
        return results
    
    def _calculate_stiffness(self,
                           positions: np.ndarray,
                           forces: np.ndarray,
                           smoothed_force: np.ndarray,
                           baseline: float,
                           pre_init_idx: int,
                           peak_idx: int) -> Dict:
        """
        Calculate effective stiffness from the pre-initiation stage.
        
        Uses the first 50% of the pre-initiation data (most linear region)
        to calculate stiffness as the slope of the force-position curve.
        
        Returns:
            Dict with stiffness metrics in N/mm
        """
        results = {}
        
        try:
            # Extract pre-initiation region
            pre_init_positions = positions[pre_init_idx:peak_idx+1]
            pre_init_forces = smoothed_force[pre_init_idx:peak_idx+1]
            
            # Baseline-correct the forces
            pre_init_forces_corrected = pre_init_forces - baseline
            
            # Use only the first 50% of the pre-initiation data (most linear)
            half_length = len(pre_init_positions) // 2
            if half_length < 3:
                # Not enough data points for reliable linear fit
                results['effective_stiffness_N_per_mm'] = 0.0
                results['stiffness_r_squared'] = 0.0
                return results
            
            linear_positions = pre_init_positions[:half_length]
            linear_forces = pre_init_forces_corrected[:half_length]
            
            # Perform linear regression: F = k * x + b
            # where k is the stiffness (slope)
            from scipy import stats
            slope, intercept, r_value, p_value, std_err = stats.linregress(linear_positions, linear_forces)
            
            # Stiffness is the absolute value of the slope (N/mm)
            # Note: slope will be negative (force decreases as position increases during retraction)
            results['effective_stiffness_N_per_mm'] = abs(slope)
            results['stiffness_r_squared'] = r_value ** 2  # Coefficient of determination
            
        except Exception as e:
            warnings.warn(f"Stiffness calculation failed: {e}")
            results.update({
                'effective_stiffness_N_per_mm': 0.0,
                'stiffness_r_squared': 0.0
            })
        
        return results
    
    def _calculate_dynamic_metrics(self, 
                                 times: np.ndarray, 
                                 forces: np.ndarray, 
                                 smoothed_force: np.ndarray,
                                 pre_init_idx: int, 
                                 peak_idx: int, 
                                 prop_end_idx: int) -> Dict:
        """
        Calculate dynamic analysis metrics.
        """
        results = {}
        
        try:
            # Calculate force gradients
            force_gradient = np.gradient(smoothed_force, times)
            
            # Loading phase (pre-initiation to peak)
            loading_gradients = force_gradient[pre_init_idx:peak_idx+1]
            if len(loading_gradients) > 0:
                results['max_loading_rate_N_per_s'] = np.max(loading_gradients)
            else:
                results['max_loading_rate_N_per_s'] = 0.0
            
            # Unloading phase (peak to propagation end)
            unloading_gradients = force_gradient[peak_idx:prop_end_idx+1]
            if len(unloading_gradients) > 0:
                results['max_unloading_rate_N_per_s'] = np.abs(np.min(unloading_gradients))
            else:
                results['max_unloading_rate_N_per_s'] = 0.0
                
        except Exception as e:
            warnings.warn(f"Dynamic metrics calculation failed: {e}")
            results.update({
                'max_loading_rate_N_per_s': 0.0,
                'max_unloading_rate_N_per_s': 0.0
            })
        
        return results
    
    def _calculate_quality_metrics(self, 
                                 forces: np.ndarray, 
                                 smoothed_force: np.ndarray,
                                 baseline: float, 
                                 peak_force: float) -> Dict:
        """
        Calculate data quality metrics.
        """
        results = {}
        
        try:
            # Force noise analysis
            force_noise = forces - smoothed_force
            noise_std = np.std(force_noise)
            
            # Signal-to-noise ratio
            signal_amplitude = peak_force - baseline
            if noise_std > 0:
                snr = signal_amplitude / noise_std
            else:
                snr = float('inf')
            
            results['force_noise_std'] = noise_std
            results['signal_to_noise_ratio'] = snr
            
        except Exception as e:
            warnings.warn(f"Quality metrics calculation failed: {e}")
            results.update({
                'force_noise_std': 0.0,
                'signal_to_noise_ratio': 0.0
            })
        
        return results
    
    def _empty_results(self, layer_number: Optional[int] = None, contact_area: float = 1.0) -> Dict:
        """
        Return empty results structure for invalid data.
        """
        return {
            'layer_number': layer_number,
            'contact_area_m2': float(contact_area),
            'baseline_force': 0.0,
            'peak_force': 0.0,
            'peak_force_corrected': 0.0,
            'peak_force_absolute': 0.0,
            'force_range': 0.0,
            'work_of_adhesion_total_J': 0.0,
            'energy_release_rate_G_J_per_m2': 0.0,
            'dissipated_energy_initiation_J': 0.0,
            'peak_force_position': 0.0,
            'peak_force_time': 0.0,
            'pre_initiation_position': 0.0,
            'pre_initiation_time': 0.0,
            'pre_initiation_force': 0.0,
            'propagation_end_position': 0.0,
            'propagation_end_time': 0.0,
            'pre_initiation_duration': 0.0,
            'propagation_duration': 0.0,
            'total_peel_duration': 0.0,
            'pre_initiation_distance': 0.0,
            'propagation_distance': 0.0,
            'total_peel_distance': 0.0,
            'work_of_adhesion_mJ': 0.0,
            'work_of_adhesion_corrected_mJ': 0.0,
            'energy_dissipation_mJ': 0.0,
            'total_energy_mJ': 0.0,
            'energy_density_mJ_per_mm': 0.0,
            'max_loading_rate_N_per_s': 0.0,
            'max_unloading_rate_N_per_s': 0.0,
            'force_noise_std': 0.0,
            'signal_to_noise_ratio': 0.0,
            'peak_retraction_force_N': 0.0,
            'peak_retraction_idx': -1,
        }
    
    def format_results_for_csv(self, results: Dict, precision: int = 4) -> Dict:
        """
        Format results for CSV output with specified precision.
        
        Args:
            results: Dictionary of calculated metrics
            precision: Number of decimal places
            
        Returns:
            Dictionary with formatted values
        """
        formatted = {}
        
        for key, value in results.items():
            if key == 'layer_number' and value is not None:
                formatted[key] = int(value)
            elif isinstance(value, (int, float)):
                if np.isnan(value) or np.isinf(value):
                    formatted[key] = "NaN"
                else:
                    formatted[key] = round(float(value), precision)
            else:
                formatted[key] = value
                
        return formatted


# Example usage and testing functions
if __name__ == "__main__":
    # Test the calculator with simulated data
    print("Testing Adhesion Metrics Calculator...")
    
    # Create test data
    t = np.linspace(0, 2.0, 200)  # 2 seconds, 100 Hz sampling
    pos = 10 + t * 2  # Moving from 10mm to 14mm
    
    # Simulate realistic peeling force curve
    force = np.zeros_like(t)
    for i, time in enumerate(t):
        if time < 0.3:
            force[i] = 0.01  # Baseline
        elif time < 1.0:
            force[i] = 0.01 + 0.3 * (time - 0.3)  # Gradual increase
        elif time < 1.2:
            force[i] = 0.22 - 0.15 * (time - 1.0)  # Peak and drop
        else:
            force[i] = 0.07 - 0.075 * (time - 1.2)  # Return to baseline
    
    # Add some noise
    force += np.random.normal(0, 0.005, len(t))
    force = np.maximum(force, 0)  # Ensure non-negative
    
    # Test the calculator
    calculator = AdhesionMetricsCalculator()
    results = calculator.calculate_from_arrays(t, pos, force, layer_number=1)
    
    # Display results
    print("\nCalculated Metrics:")
    print("=" * 40)
    formatted_results = calculator.format_results_for_csv(results)
    for key, value in formatted_results.items():
        print(f"{key}: {value}")
    
    print(f"\nTest completed successfully!")
