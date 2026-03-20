import numpy as np
from scipy.signal import find_peaks
from pathlib import Path
import pandas as pd
from typing import Any, Dict, List, Tuple


DEFAULT_LAYER_LEGIT_FORCE_THRESHOLD_N = 0.1


def detect_bad_layers(
    layers: List[Dict[str, Any]],
    legitimacy_threshold_n: float = DEFAULT_LAYER_LEGIT_FORCE_THRESHOLD_N,
) -> Tuple[List[Dict[str, Any]], List[int]]:
    """
    Flag layers with incomplete peeling behavior using force legitimacy checks.

    A layer is considered valid only if both absolute baseline force and absolute
    pre-initiation force are below the threshold.

    Args:
        layers: Layer dictionaries output by RawDataProcessor.
        legitimacy_threshold_n: Absolute-force threshold in Newtons.

    Returns:
        Tuple of (updated layers list, list of bad layer numbers).
    """
    flagged_layers: List[int] = []

    for layer in layers:
        baseline_force = float(layer.get("baseline", 0.0))
        pre_init_force = float(layer.get("pre_initiation_force", 0.0))

        is_legit_layer = (
            abs(baseline_force) < legitimacy_threshold_n
            and abs(pre_init_force) < legitimacy_threshold_n
        )
        is_incomplete_peeling = not is_legit_layer

        layer["analysis_included"] = bool(is_legit_layer)
        layer["incomplete_peeling"] = bool(is_incomplete_peeling)
        layer["peeling_status"] = "complete" if is_legit_layer else "incomplete_peeling"

        if is_incomplete_peeling:
            layer["color"] = "dimgray"
            layer_num = int(layer.get("number", -1))
            flagged_layers.append(layer_num)
            layer["bad_layer_reason"] = (
                f"|baseline|={abs(baseline_force):.4f} N, "
                f"|pre-init force|={abs(pre_init_force):.4f} N, "
                f"threshold={legitimacy_threshold_n:.3f} N"
            )
        else:
            layer["bad_layer_reason"] = ""

    return layers, flagged_layers

class RawDataProcessor:
    """
    Pure data processing module for adhesion test data.
    Responsibilities:
    1. Load CSV data
    2. Find layer boundaries
    3. Calculate metrics for each layer
    4. Return structured results
    
    Does NOT handle plotting - that should be done separately.
    """
    
    def __init__(self, calculator):
        """
        Initialize processor with metrics calculator.
        
        Args:
            calculator: AdhesionMetricsCalculator instance
        """
        self.calculator = calculator

    def process_csv(self, csv_filepath: str, title: str = None, save_path: str = None):
        """
        Process a CSV file containing raw force/position data.
        
        Note: title and save_path parameters are kept for backward compatibility
        but are not used by this processor. Plotting should be handled externally.
        
        Args:
            csv_filepath: Path to CSV file
            title: Not used (kept for compatibility)
            save_path: Not used (kept for compatibility)
            
        Returns:
            List of layer dictionaries with metrics and indices
        """
        # 1. Load and prepare data
        df = self._load_and_prepare_data(csv_filepath)
        if df is None:
            return

        # Extract data arrays
        time_data = df['Elapsed Time (s)'].to_numpy()
        force_data = df['Force (N)'].to_numpy()
        position_data = df['Position (mm)'].to_numpy()

        # 2. Find Layer Boundaries - use phase-aware detection if available
        # Use calculator's smoothing for consistency with live analysis
        smoothed_force = self.calculator._apply_smoothing(force_data)
        
        # Get layer numbers from filename
        layer_numbers = self._extract_layer_numbers_from_filename(csv_filepath)

        # Check if Phase column exists - use phase-aware detection if available
        if 'Phase' in df.columns:
            print("Using phase-aware boundary detection (Phase column found)")
            phase_data = df['Phase'].to_numpy()
            layer_boundaries = self._detect_boundaries_from_phases(
                time_data, position_data, force_data, phase_data
            )
            
            # Fallback to adaptive detection if phase-aware found no layers
            if len(layer_boundaries) == 0:
                print("Phase-aware detection found 0 layers - falling back to adaptive detection")
                layer_boundaries = self._detect_boundaries_adaptive(
                    time_data, position_data, force_data
                )
        else:
            print("Phase column not found - using adaptive detection")
            layer_boundaries = self._detect_boundaries_adaptive(
                time_data, position_data, force_data
            )
        
        # Limit to expected number of layers
        if len(layer_numbers) > len(layer_boundaries):
            layer_numbers = layer_numbers[:len(layer_boundaries)]

        # 3. Calculate Metrics for Each Layer (using ONLY lifting phase)
        layers = []
        for i, boundary_dict in enumerate(layer_boundaries):
            if i >= len(layer_numbers): break

            layer_num = layer_numbers[i]
            lifting_start, lifting_end = boundary_dict['lifting']
            retraction_start, retraction_end = boundary_dict['retraction']
            sandwich_start, sandwich_end = boundary_dict['sandwich']
            
            print(f"\n--- Analyzing Layer {layer_num} ---")
            print(f"    Lifting phase: {lifting_start}-{lifting_end}")
            print(f"    Retraction phase: {retraction_start}-{retraction_end}")
            print(f"    Sandwich phase: {sandwich_start}-{sandwich_end}")

            # Extract LIFTING PHASE data only for adhesion metrics
            lifting_time = time_data[lifting_start:lifting_end+1]
            lifting_pos = position_data[lifting_start:lifting_end+1]
            lifting_force = force_data[lifting_start:lifting_end+1]

            retraction_force = force_data[retraction_start:retraction_end+1]

            # The calculator expects time to start from 0 for the segment
            lifting_time_relative = lifting_time - lifting_time[0]

            try:
                # Calculate adhesion metrics using ONLY lifting phase data
                metrics = self.calculator.calculate_from_arrays(
                    lifting_time_relative,
                    lifting_pos,
                    lifting_force,
                    layer_number=layer_num,
                    retraction_force_data=retraction_force,
                    retraction_start_idx=retraction_start,
                )
                
                # CRITICAL: Find peak index from SEGMENTED smoothed data
                # The calculator returns peak_force_time which is relative to lifting phase start
                # We need to find this index WITHIN the lifting phase, then map to global
                peak_time_relative = metrics['peak_force_time']
                
                # Find index within lifting_time array
                peak_idx_in_segment = np.argmin(np.abs(lifting_time_relative - peak_time_relative))
                
                # Map to global index by adding lifting_start offset
                peak_idx = lifting_start + peak_idx_in_segment
                
                layer_obj = self._create_layer_object(
                    metrics, peak_idx, lifting_start, time_data, force_data, i, lifting_end,
                    boundary_dict
                )
                layers.append(layer_obj)
                print(f"  -> Metrics calculated successfully for Layer {layer_num}.")
                print(f"     Peak adhesion force: {metrics['peak_force']:.4f} N (in lifting phase)")
                print(f"     Peak retraction force: {metrics.get('peak_retraction_force_N', 0.0):.4f} N (in retraction phase)")

            except Exception as e:
                print(f"  -> ERROR calculating metrics for Layer {layer_num}: {e}")
                import traceback
                traceback.print_exc()
                continue

        # Return layers only - NO PLOTTING in this module
        return layers

    def _smooth_data(self, data: np.ndarray, window_size: int = 5) -> np.ndarray:
        """Simple moving average smoothing."""
        return np.convolve(data, np.ones(window_size)/window_size, mode='same')

    def _extract_layer_numbers_from_filename(self, filepath: str) -> List[int]:
        """Extract layer numbers from filename pattern L{start}-L{end}"""
        import re
        filename = Path(filepath).stem
        
        # Look for pattern like L100-L105 or L100-105
        match = re.search(r'L(\d+)-L?(\d+)', filename)
        if match:
            start = int(match.group(1))
            end = int(match.group(2))
            return list(range(start, end + 1))
        
        # Look for single layer L100
        match = re.search(r'L(\d+)', filename)
        if match:
            layer = int(match.group(1))
            return [layer]
        
        return [1, 2, 3, 4, 5, 6]  # Fallback - assume 6 layers

    def _find_test_start(self, position_data: np.ndarray) -> int:
        """
        Find where actual adhesion testing starts (after sandwich section).
        
        The sandwich section is the initial contact phase where the stage
        touches down. We want to ignore any force peaks during this phase.
        
        Strategy: Find the first significant downward motion (lifting phase start)
        which indicates the beginning of the first actual adhesion test.
        
        Returns:
            Index where testing begins (after sandwich section)
        """
        window_size = 5
        pos_threshold = 0.03  # 0.03mm threshold for movement detection
        
        def detect_movement(curr_pos, last_pos):
            diff = curr_pos - last_pos
            if abs(diff) < pos_threshold/2:
                return 0  # stable
            return 1 if diff > 0 else -1  # 1 for increasing, -1 for decreasing
        
        # Start looking after initial stabilization
        i = 10
        last_pos = position_data[i]
        
        while i < len(position_data) - window_size:
            window = position_data[i:i+window_size]
            current_pos = np.mean(window)
            direction = detect_movement(current_pos, last_pos)
            
            # Look for first downward motion (lifting phase of first test)
            if direction == -1:  # Moving down (LIFTING)
                # Return a point slightly before this to capture the baseline
                return max(5, i - 50)
            
            last_pos = current_pos
            i += 1
        
        # If no lifting motion found, start from beginning
        return 5

    def _detect_peaks(self, smoothed_force: np.ndarray, start_idx: int = 0) -> np.ndarray:
        """
        Detects force peaks corresponding to layer peeling events.
        
        Args:
            smoothed_force: Smoothed force array
            start_idx: Index to start peak detection from (ignores data before this)
        """
        # Only detect peaks after the start index (ignoring sandwich section)
        peaks, _ = find_peaks(smoothed_force[start_idx:], height=0.01, distance=150, prominence=0.005)
        
        # Adjust peak indices to account for the offset
        peaks = peaks + start_idx
        
        print(f"Detected {len(peaks)} peaks at indices: {peaks}")
        return peaks

    def _detect_boundaries_from_phases(self, time_data: np.ndarray, position_data: np.ndarray, 
                                      force_data: np.ndarray, phase_data: np.ndarray) -> List[dict]:
        """
        Detect layer boundaries using explicit phase markers from CSV.
        
        This is the PREFERRED method when Phase column is available in the CSV.
        Uses explicit phase transitions (Lift→Retract) to identify layers.
        
        Args:
            time_data: Time array
            position_data: Position array  
            force_data: Force array
            phase_data: Array of phase strings ('Lift', 'Retract', 'Pause', 'Sandwich', 'Exposure')
        
        Returns:
            List of boundary dictionaries with lifting/retraction/sandwich/full ranges
        """
        print("\n=== Detecting Boundaries from Phase Markers ===")
        
        # Convert to string and handle NaN values
        import pandas as pd
        phase_data_clean = pd.Series(phase_data).fillna('').astype(str).values
        
        # Debug: Show unique phases and their counts
        unique_phases = pd.Series(phase_data_clean).value_counts()
        print(f"Unique phases found: {dict(unique_phases)}")
        
        boundaries = []
        i = 0
        
        while i < len(phase_data_clean):
            # Look for start of Lift phase (including 2-stage smooth lifting)
            # Accept: 'Lift', 'Lift-Stage1', 'Lift-Stage2'
            if phase_data_clean[i].startswith('Lift'):
                lift_start = i
                
                # Check if this is an isolated old 'Lift' label (just 1-5 points)
                # If so, skip it - we want the staged sequences
                is_isolated_old_lift = True
                check_range = min(i + 10, len(phase_data_clean))
                for check_idx in range(i, check_range):
                    if 'Stage' in phase_data_clean[check_idx]:
                        is_isolated_old_lift = False
                        break
                    if check_idx > i and not phase_data_clean[check_idx].startswith('Lift'):
                        break
                
                # If it's an isolated old label, skip it
                if is_isolated_old_lift and (i + 1 < len(phase_data_clean)) and not phase_data_clean[i + 1].startswith('Lift'):
                    i += 1
                    continue
                
                # Search backwards to find the ACTUAL start of lifting (before mislabeled Sandwich)
                # Stop when we hit a Pause phase or reach the beginning
                actual_lift_start = lift_start
                search_idx = lift_start - 1
                while search_idx >= 0 and phase_data_clean[search_idx] != 'Pause':
                    # Check if this earlier phase should be part of lifting
                    # (Sandwich and Exposure phases before Lift are often mislabeled)
                    if phase_data_clean[search_idx] in ['Sandwich', 'Exposure']:
                        actual_lift_start = search_idx
                        search_idx -= 1
                    else:
                        break
                
                # If we found earlier phases, report the correction
                if actual_lift_start < lift_start:
                    corrected_count = lift_start - actual_lift_start
                    print(f"  Corrected lift start: moved back {corrected_count} samples from {lift_start} to {actual_lift_start}")
                    lift_start = actual_lift_start
                
                # Find end of Lift phase (including all lift stages)
                lift_end = lift_start
                while lift_end < len(phase_data_clean) and (phase_data_clean[lift_end].startswith('Lift') or phase_data_clean[lift_end] in ['Sandwich', 'Exposure']):
                    lift_end += 1
                lift_end -= 1  # Back to last Lift index
                
                # Look for subsequent Retract phase (including 2-stage smooth retraction)
                retract_start = lift_end + 1
                while retract_start < len(phase_data_clean) and not phase_data_clean[retract_start].startswith('Retract') and not phase_data_clean[retract_start].startswith('Lift'):
                    retract_start += 1
                
                if retract_start < len(phase_data_clean) and phase_data_clean[retract_start].startswith('Retract'):
                    # Find end of Retract phase (including all retract stages)
                    retract_end = retract_start
                    while retract_end < len(phase_data_clean) and phase_data_clean[retract_end].startswith('Retract'):
                        retract_end += 1
                    retract_end -= 1  # Back to last Retract index
                    
                    # Found complete layer
                    boundary_dict = {
                        'lifting': (lift_start, lift_end),
                        'retraction': (retract_start, retract_end),
                        'sandwich': (lift_start, lift_start),  # No separate sandwich in phase-based detection
                        'full': (lift_start, retract_end)
                    }
                    boundaries.append(boundary_dict)
                    
                    lift_distance = abs(position_data[lift_end] - position_data[lift_start])
                    retract_distance = abs(position_data[retract_end] - position_data[retract_start])
                    print(f"Layer {len(boundaries)}: Lift[{lift_start}-{lift_end}, {lift_distance:.2f}mm], "
                          f"Retract[{retract_start}-{retract_end}, {retract_distance:.2f}mm]")
                    i = retract_end + 1
                else:
                    # Incomplete layer (Lift without Retract) - skip it
                    lift_duration = lift_end - lift_start + 1
                    print(f"WARNING: Lift phase at {lift_start} ({lift_duration} points) has no matching Retract - skipping")
                    i = lift_end + 1
            else:
                i += 1
        
        print(f"\n=== Total layers detected: {len(boundaries)} ===")
        return boundaries
    
    def _detect_boundaries_adaptive(self, time_data: np.ndarray, position_data: np.ndarray, 
                                   force_data: np.ndarray) -> List[dict]:
        """
        Detect layer boundaries adaptively based on significant position changes.
        Does not rely on hardcoded distance values.
        
        This is the FALLBACK method when Phase column is not available in CSV.
        Finds significant motions (>50% of maximum motion) and pairs them as lift-retract cycles.
        
        Args:
            time_data: Time array
            position_data: Position array
            force_data: Force array
        
        Returns:
            List of boundary dictionaries
        """
        print("\n=== Adaptive Boundary Detection ===")
        
        # Calculate all position changes
        pos_changes = np.abs(np.diff(position_data))
        max_pos_change = np.max(pos_changes)
        
        # Adaptive motion threshold: use 10% of maximum motion per sample
        # This handles both fast (1000 um/s) and slow (200 um/s) tests
        motion_threshold = max(0.001, max_pos_change * 0.1)  # At least 0.001mm
        print(f"Adaptive motion threshold: {motion_threshold:.4f} mm/sample (based on max change: {max_pos_change:.4f} mm)")
        
        # Find motion segments (continuous motion periods)
        motion_starts = []
        motion_ends = []
        in_motion = False
        motion_start_idx = 0
        
        for i in range(1, len(position_data)):
            pos_change = abs(position_data[i] - position_data[i-1])
            
            if pos_change > motion_threshold and not in_motion:
                # Motion starts
                motion_start_idx = i
                in_motion = True
            elif pos_change <= motion_threshold and in_motion:
                # Check if motion has really stopped (3 consecutive stable points)
                if i + 2 < len(position_data):
                    next_changes = [abs(position_data[i+j] - position_data[i+j-1]) for j in range(1, 3)]
                    if all(c <= motion_threshold for c in next_changes):
                        # Motion truly stopped
                        motion_starts.append(motion_start_idx)
                        motion_ends.append(i)
                        in_motion = False
        
        # Calculate distance for each motion segment
        motion_segments = []
        for start, end in zip(motion_starts, motion_ends):
            distance = abs(position_data[end] - position_data[start])
            motion_segments.append((start, end, distance))
        
        if not motion_segments:
            print("ERROR: No motion segments detected")
            return []
        
        # Find significant motions (>50% of maximum motion)
        max_distance = max([dist for _, _, dist in motion_segments])
        significant_threshold = 0.5 * max_distance  # Adaptive threshold
        
        significant_motions = [
            seg for seg in motion_segments 
            if seg[2] >= significant_threshold
        ]
        
        print(f"Found {len(significant_motions)} significant motions (>{significant_threshold:.2f}mm)")
        for i, (start, end, dist) in enumerate(significant_motions):
            print(f"  Motion {i+1}: idx {start}-{end}, distance {dist:.2f}mm")
        
        # Pair consecutive motions as lift-retract cycles
        boundaries = []
        for i in range(0, len(significant_motions) - 1, 2):
            lift_motion = significant_motions[i]
            retract_motion = significant_motions[i + 1]
            
            boundary_dict = {
                'lifting': (lift_motion[0], lift_motion[1]),
                'retraction': (retract_motion[0], retract_motion[1]),
                'sandwich': (lift_motion[0], lift_motion[0]),
                'full': (lift_motion[0], retract_motion[1])
            }
            boundaries.append(boundary_dict)
            print(f"Layer {len(boundaries)}: Lift[{lift_motion[0]}-{lift_motion[1]}, {lift_motion[2]:.2f}mm], "
                  f"Retract[{retract_motion[0]}-{retract_motion[1]}, {retract_motion[2]:.2f}mm]")
        
        print(f"\n=== Total layers detected: {len(boundaries)} ===")
        return boundaries

    # NOTE: Plotting methods removed - use AnalysisPlotter module for visualization
    # RawData_Processor is a pure data processing module

    def _create_layer_object(self, metrics, peak_idx, start_idx, time_data, force_data, 
                            layer_idx, end_idx, boundary_dict=None):
        """
        Creates a layer object with calculated metrics and indices.
        
        Args:
            metrics: Calculated metrics from adhesion calculator
            peak_idx: Index of peak force in full data array
            start_idx: Start index of lifting phase
            time_data: Full time array
            force_data: Full force array
            layer_idx: Layer index (0-based)
            end_idx: End index of lifting phase
            boundary_dict: Dictionary with phase boundaries (lifting, retraction, sandwich)
        """
        colors = ['red', 'blue', 'green', 'orange', 'purple', 'brown']
        
        # Convert relative metric times to global indices
        pre_init_time = time_data[start_idx] + metrics.get('pre_initiation_time', 0)
        prop_end_time = time_data[start_idx] + metrics.get('propagation_end_time', 0)
        
        # Find closest indices in full time array
        pre_init_idx = np.argmin(np.abs(time_data - pre_init_time))
        prop_end_idx = np.argmin(np.abs(time_data - prop_end_time))
        
        layer_object = {
            'metrics': metrics,
            'peak_idx': peak_idx,
            'pre_init_idx': pre_init_idx,
            'prop_end_idx': prop_end_idx,
            'start_idx': start_idx,
            'end_idx': end_idx,
            'color': colors[layer_idx % len(colors)],
            'number': metrics.get('layer_number', layer_idx + 1),
            'peak_force': metrics.get('peak_force', 0),
            'peak_force_corrected': metrics.get('peak_force_corrected', 0),
            'baseline': metrics.get('baseline_force', 0),
            'pre_initiation_force': metrics.get('pre_initiation_force', 0),
            'work_of_adhesion_mJ': metrics.get('work_of_adhesion_corrected_mJ', 0),
            'pre_init_time': time_data[pre_init_idx],
            'pre_init_duration': metrics.get('pre_initiation_duration', 0),
            'peak_time': time_data[peak_idx],
            'prop_end_time': time_data[prop_end_idx],
            'prop_duration': metrics.get('propagation_duration', 0),
            'force_range': metrics.get('force_range', 0),
            'peak_retraction_force': metrics.get('peak_retraction_force_N', 0),
            'peak_retraction_idx': metrics.get('peak_retraction_idx', 0)
        }
        
        # Add phase boundary information if provided
        if boundary_dict:
            layer_object['phases'] = boundary_dict
        
        return layer_object

    def _load_and_prepare_data(self, csv_filepath):
        """Loads and prepares data from CSV file."""
        try:
            df = pd.read_csv(csv_filepath)
            return df
        except Exception as e:
            print(f"Error loading CSV file: {e}")
            return None

if __name__ == "__main__":
    """
    Standalone test mode - validates layer boundary detection only.
    For plotting, use AnalysisPlotter module separately.
    """
    import sys
    from pathlib import Path
    from adhesion_metrics_calculator import AdhesionMetricsCalculator
    
    if len(sys.argv) < 2:
        print("Usage: python RawData_Processor.py <csv_file>")
        print("Note: This only processes data. Use AnalysisPlotter for visualization.")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    
    # Initialize with calculator
    calculator = AdhesionMetricsCalculator()
    processor = RawDataProcessor(calculator)
    
    # Process the file
    print(f"\nProcessing: {csv_file}")
    layers = processor.process_csv(csv_file)
    
    print(f"\n{'='*60}")
    print(f"Processing Complete:")
    print(f"  Found {len(layers)} layers")
    print(f"{'='*60}")
    
    for layer in layers:
        print(f"\nLayer {layer['number']}:")
        print(f"  Peak Force: {layer['peak_force']:.4f} N")
        print(f"  Work of Adhesion: {layer['work_of_adhesion_mJ']:.4f} mJ")
        print(f"  Indices: {layer['start_idx']}-{layer['end_idx']}")
    
    print("\nTo generate plots, use AnalysisPlotter module.")
