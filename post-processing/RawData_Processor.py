import numpy as np
from scipy.signal import find_peaks
from pathlib import Path
import pandas as pd
from typing import List, Tuple

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

        # 2. Find Layer Boundaries with phase segregation
        # Use calculator's smoothing for consistency with live analysis
        smoothed_force = self.calculator._apply_smoothing(force_data)
        
        # Get layer numbers from filename
        layer_numbers = self._extract_layer_numbers_from_filename(csv_filepath)

        # Find layer boundaries with phase segregation (lifting, retraction, sandwich)
        layer_boundaries = self._find_layer_boundaries([], position_data, time_data, layer_numbers)
        
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
            pause_start, pause_end = boundary_dict.get('pause_expose', (retraction_end, retraction_end))
            sandwich_start, sandwich_end = boundary_dict['sandwich']
            
            print(f"\n--- Analyzing Layer {layer_num} ---")
            print(f"    Lifting phase: {lifting_start}-{lifting_end}")
            print(f"    Retraction phase: {retraction_start}-{retraction_end}")
            if pause_end > pause_start:
                print(f"    Pause/Expose phase: {pause_start}-{pause_end}")
            if sandwich_end > sandwich_start:
                print(f"    Sandwich phase: {sandwich_start}-{sandwich_end}")

            # Extract LIFTING PHASE data only for adhesion metrics
            lifting_time = time_data[lifting_start:lifting_end+1]
            lifting_pos = position_data[lifting_start:lifting_end+1]
            lifting_force = force_data[lifting_start:lifting_end+1]

            # Extract peak retraction force (at end of retraction phase)
            retraction_force = force_data[retraction_start:retraction_end+1]
            peak_retraction_force = np.max(np.abs(retraction_force))
            peak_retraction_idx = retraction_start + np.argmax(np.abs(retraction_force))

            # The calculator expects time to start from 0 for the segment
            lifting_time_relative = lifting_time - lifting_time[0]

            try:
                # Calculate adhesion metrics using ONLY lifting phase data
                metrics = self.calculator.calculate_from_arrays(
                    lifting_time_relative, lifting_pos, lifting_force, layer_number=layer_num
                )
                
                # Add retraction metrics
                metrics['peak_retraction_force_N'] = peak_retraction_force
                metrics['peak_retraction_idx'] = peak_retraction_idx
                
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
                    boundary_dict, retraction_force
                )
                layers.append(layer_obj)
                print(f"  -> Metrics calculated successfully for Layer {layer_num}.")
                print(f"     Peak adhesion force: {metrics['peak_force']:.4f} N (in lifting phase)")
                print(f"     Peak retraction force: {peak_retraction_force:.4f} N (at end of retraction)")

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

    def _find_motion_end(self, start_idx: int, position_data: np.ndarray, 
                        min_stable_points: int = 3) -> int:
        """
        Find where motion actually STOPS (position stabilizes).
        
        After detecting large motion, continue searching until position stabilizes.
        This ensures we capture the complete motion even when it slows down.
        
        Args:
            start_idx: Where to start searching from (after large motion detected)
            position_data: Position array
            min_stable_points: How many consecutive stable points needed
            
        Returns:
            Index where motion ends (position stabilizes)
        """
        stability_threshold = 0.02  # Position must vary less than 0.02mm to be stable
        max_search = 600  # Don't search more than 600 indices ahead
        
        for i in range(start_idx, min(start_idx + max_search, len(position_data) - min_stable_points)):
            # Check if next N points are stable
            window = position_data[i:i+min_stable_points]
            pos_range = np.max(window) - np.min(window)
            
            if pos_range < stability_threshold:
                # Found stable region - motion has stopped
                return i
        
        # If no stable region found, return search limit
        return min(start_idx + max_search, len(position_data) - 1)

    def _find_layer_boundaries(self, peaks: np.ndarray, position_data: np.ndarray,
                             time_data: np.ndarray, layer_numbers: List[int]) -> List[dict]:
        """
        Finds layer boundaries based on lift/retract motions with AUTOMATIC distance detection.
        
        ROBUST STRATEGY (updated for variable lift distances):
        - Auto-detect the typical lift distance from the data (handles 2mm, 3mm, 6mm, etc.)
        - Find all motions matching the detected distance (within tolerance)
        - Pair them sequentially: first motion = lift, second motion = retract
        - Ignore everything else (sandwich touches <1mm, pauses, adjustments)
        
        This approach works for ACF (3mm), standard (6mm), and future test variations.
        """
        print("\n=== Detecting Adhesion Test Cycles ===")
        
        # STEP 1: Auto-detect the typical lift distance from position data
        # Find the MAXIMUM position span - this gives us the total test range
        pos_min = np.min(position_data)
        pos_max = np.max(position_data)
        total_span = pos_max - pos_min
        
        print(f"Total position span: {total_span:.2f} mm")
        
        # The lift distance should be close to the total span
        # (assuming data starts/ends near extremes)
        # Round to nearest integer for common values (2mm, 3mm, 6mm, etc.)
        if total_span >= 5.5:
            detected_distance = 6.0
        elif total_span >= 2.5:
            detected_distance = 3.0
        elif total_span >= 1.5:
            detected_distance = 2.0
        else:
            detected_distance = round(total_span)
        
        print(f"Auto-detected lift distance: {detected_distance:.1f} mm")
        
        # Set tolerance based on detected distance (±15% or minimum 0.4mm)
        DISTANCE_TOLERANCE = max(0.4, detected_distance * 0.15)
        MIN_DISTANCE = detected_distance - DISTANCE_TOLERANCE
        MAX_DISTANCE = detected_distance + DISTANCE_TOLERANCE
        
        print(f"Searching for motions: {MIN_DISTANCE:.2f} - {MAX_DISTANCE:.2f} mm")
        
        window_size = 20  # Window to smooth position measurements
        
        # Find all motions matching the detected distance
        adhesion_motions = []  # List of (start_idx, end_idx, distance_mm)
        
        i = 10  # Skip initial noise
        while i < len(position_data) - 100:
            start_pos = np.mean(position_data[i:i+window_size])
            
            # Look ahead to find ~6mm motion
            for j in range(i + 50, min(i + 1000, len(position_data) - window_size), 10):
                end_pos = np.mean(position_data[j:j+window_size])
                distance = abs(end_pos - start_pos)
                
                # Check if this matches our detected adhesion test motion distance
                if MIN_DISTANCE <= distance <= MAX_DISTANCE:
                    # EXTEND the endpoint to where motion actually stops
                    actual_end = self._find_motion_end(j, position_data, min_stable_points=3)
                    actual_distance = abs(position_data[actual_end] - position_data[i])
                    
                    # Verify the extended motion is still within range
                    if MIN_DISTANCE <= actual_distance <= MAX_DISTANCE:
                        adhesion_motions.append((i, actual_end, actual_distance))
                        print(f"{actual_distance:.2f}mm motion: idx {i}-{actual_end}")
                        i = actual_end + 10  # Skip past this motion
                        break
            else:
                # No matching motion found, advance
                i += 50
        
        print(f"\nFound {len(adhesion_motions)} motions matching {detected_distance:.1f}mm (adhesion test cycles)")
        
        # NEW SIMPLIFIED PAIRING: Just pair motions sequentially
        # Motion 1 = lift, Motion 2 = retract, Motion 3 = lift, Motion 4 = retract, etc.
        # Don't care about direction - just that they're ~6mm movements
        # Everything else (sandwich, pauses, adjustments) is automatically ignored
        
        boundaries = []
        
        # Pair consecutive motions: [0,1], [2,3], [4,5], etc.
        for i in range(0, len(adhesion_motions) - 1, 2):
            lift_motion = adhesion_motions[i]
            retract_motion = adhesion_motions[i + 1]
            
            lift_start = lift_motion[0]
            lift_end = lift_motion[1]
            retract_start = retract_motion[0]
            retract_end = retract_motion[1]
            
            # Detect sandwich and pause/expose phases
            # Between retraction_end and next lift_start (if available)
            pause_start = retract_end
            pause_end = retract_end  # Default: no pause
            sandwich_start = lift_start  # Default: no sandwich
            sandwich_end = lift_start
            
            # Check if there's a next layer to determine pause phase
            if i + 2 < len(adhesion_motions):
                next_lift_start = adhesion_motions[i + 2][0]
                
                # Everything between retraction_end and next_lift_start is pause/expose
                pause_start = retract_end
                pause_end = next_lift_start
                
                # Check for sandwich phase (small <1mm motion between pause and next lift)
                # Look for small position changes in the pause region
                pause_region_pos = position_data[pause_start:pause_end]
                if len(pause_region_pos) > 20:
                    # Check if there's a small downward motion (sandwich touch)
                    pos_changes = np.diff(pause_region_pos)
                    
                    # Look for a small downward excursion (negative change followed by positive)
                    # that's less than 1mm total
                    for j in range(len(pos_changes) - 10):
                        window = pause_region_pos[j:j+10]
                        excursion = np.max(window) - np.min(window)
                        
                        if 0.1 < excursion < 1.0:  # Small motion, likely sandwich
                            sandwich_start = pause_start + j
                            sandwich_end = pause_start + j + 10
                            pause_end = sandwich_start  # Pause ends when sandwich starts
                            break
            
            boundary_dict = {
                'lifting': (lift_start, lift_end),
                'retraction': (retract_start, retract_end),
                'pause_expose': (pause_start, pause_end),
                'sandwich': (sandwich_start, sandwich_end),
                'full': (lift_start, retract_end)
            }
            boundaries.append(boundary_dict)
            print(f"\nLayer {len(boundaries)}:")
            print(f"  Lifting: {lift_start}-{lift_end} ({lift_motion[2]:.2f} mm)")
            print(f"  Retraction: {retract_start}-{retract_end} ({retract_motion[2]:.2f} mm)")
            if pause_end > pause_start:
                pause_duration = time_data[pause_end] - time_data[pause_start]
                print(f"  Pause/Expose: {pause_start}-{pause_end} ({pause_duration:.1f} s)")
            if sandwich_end > sandwich_start:
                print(f"  Sandwich: {sandwich_start}-{sandwich_end}")
        
        # Handle odd number of motions (unpaired final motion)
        if len(adhesion_motions) % 2 == 1:
            print(f"\nWARNING: Found unpaired final motion at idx {adhesion_motions[-1][0]}")
            print("  This may be an incomplete layer at the end of the file")
        
        print(f"\n=== Total layers detected: {len(boundaries)} ===")
        return boundaries

    # NOTE: Plotting methods removed - use AnalysisPlotter module for visualization
    # RawData_Processor is a pure data processing module

    def _create_layer_object(self, metrics, peak_idx, start_idx, time_data, force_data, 
                            layer_idx, end_idx, boundary_dict=None, retraction_force=None):
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
            retraction_force: Force array for retraction phase
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
            'baseline': metrics.get('baseline_force', 0),
            'work_of_adhesion_mJ': metrics.get('work_of_adhesion_corrected_mJ', 0),
            'pre_init_time': time_data[pre_init_idx],
            'pre_init_duration': metrics.get('pre_initiation_duration', 0),
            'peak_time': time_data[peak_idx],
            'prop_end_time': time_data[prop_end_idx],
            'prop_duration': metrics.get('propagation_duration', 0),
            'force_range': metrics.get('peak_force', 0) - metrics.get('baseline_force', 0),
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
