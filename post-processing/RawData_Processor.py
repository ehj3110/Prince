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

        # 2. Find Layer Boundaries
        # Use calculator's smoothing for consistency with live analysis
        smoothed_force = self.calculator._apply_smoothing(force_data)
        peak_indices = self._detect_peaks(smoothed_force)

        # Get layer numbers from filename
        layer_numbers = self._extract_layer_numbers_from_filename(csv_filepath)
        if len(layer_numbers) > len(peak_indices):
            layer_numbers = layer_numbers[:len(peak_indices)]

        layer_boundaries = self._find_layer_boundaries(peak_indices, position_data, time_data, layer_numbers)

        # Debug plot to visualize boundaries - DISABLED DUE TO WINDOWS CRASHES
        # self._create_debug_plot(time_data, force_data, position_data, layer_boundaries, peak_indices,
        #                       title="Layer Boundary Debug Plot",
        #                       save_path=Path(save_path).parent / "layer_boundaries_debug.png" if save_path else None)

        # 3. Calculate Metrics for Each Layer
        layers = []
        for i, peak_idx in enumerate(peak_indices):
            if i >= len(layer_numbers): break

            layer_num = layer_numbers[i]
            start_idx, end_idx = layer_boundaries[i]
            print(f"\n--- Analyzing Layer {layer_num} (Indices {start_idx}-{end_idx}) ---")

            # Create data segments for the calculator
            seg_time = time_data[start_idx:end_idx+1]
            seg_pos = position_data[start_idx:end_idx+1]
            seg_force = force_data[start_idx:end_idx+1]

            # The calculator expects time to start from 0 for the segment
            seg_time_relative = seg_time - seg_time[0]

            try:
                metrics = self.calculator.calculate_from_arrays(
                    seg_time_relative, seg_pos, seg_force, layer_number=layer_num
                )
                layer_obj = self._create_layer_object(metrics, peak_idx, start_idx, time_data, force_data, i, end_idx)
                layers.append(layer_obj)
                print(f"  -> Metrics calculated successfully for Layer {layer_num}.")

            except Exception as e:
                print(f"  -> ERROR calculating metrics for Layer {layer_num}: {e}")
                continue

        # Return layers only - NO PLOTTING in this module
        return layers

    def _smooth_data(self, data: np.ndarray, window_size: int = 5) -> np.ndarray:
        """Simple moving average smoothing."""
        return np.convolve(data, np.ones(window_size)/window_size, mode='same')

    def _extract_layer_numbers_from_filename(self, filepath: str) -> List[int]:
        """Extract layer numbers from filename pattern L{start}-L{end}"""
        filename = Path(filepath).stem
        if 'L' in filename and '-' in filename:
            try:
                parts = filename.split('L')[1].split('-')
                start = int(parts[0])
                end = int(parts[1]) if len(parts) > 1 else start
                return list(range(start, end + 1))
            except:
                pass
        return [1, 2, 3]  # Fallback

    def _detect_peaks(self, smoothed_force: np.ndarray) -> np.ndarray:
        """Detects force peaks corresponding to layer peeling events."""
        peaks, _ = find_peaks(smoothed_force, height=0.01, distance=150, prominence=0.005)
        print(f"Detected {len(peaks)} peaks at indices: {peaks}")
        return peaks

    def _find_layer_boundaries(self, peaks: np.ndarray, position_data: np.ndarray,
                             time_data: np.ndarray, layer_numbers: List[int]) -> List[Tuple[int, int]]:
        """
        Finds layer boundaries using stage motion pattern:
        1. First layer:
           - Starts at beginning of file (in pause)
           - Wait for first upward motion
        2. Subsequent layers:
           - Start after previous layer's retraction cycle completes
           - Wait for upward motion
        """
        boundaries = []
        sampling_rate = 50  # Assuming 50Hz sampling rate
        window_size = 5  # Points to average for stability check
        pos_threshold = 0.03  # 0.03mm threshold for movement detection
        min_stable_points = int(0.2 * sampling_rate)  # 10 points minimum for stable period
        
        def detect_movement(curr_pos, last_pos):
            diff = curr_pos - last_pos
            if abs(diff) < pos_threshold/2:
                return 0  # stable
            return 1 if diff > 0 else -1  # 1 for increasing, -1 for decreasing
            
        # Start with the first layer
        layer_starts = [5]  # First layer starts after initial pause
        i = 10  # Start looking after initial stabilization
        last_pos = position_data[i]  # Initialize last position

        while i < len(position_data) - window_size:
            window = position_data[i:i+window_size]
            current_pos = np.mean(window)
            direction = detect_movement(current_pos, last_pos)
            
            # Look for stage starting to move down (lifting phase)
            if direction == -1:  # Moving down (LIFTING)
                print(f"Stage starts lifting down at {i}, pos={current_pos:.3f}")
                
                # Follow through lift until it stops
                lift_end = None
                lift_end_pos = None
                while i < len(position_data) - window_size:
                    i += 1
                    window = position_data[i:i+window_size]
                    current_pos = np.mean(window)
                    if detect_movement(current_pos, last_pos) >= 0:  # No longer moving down
                        lift_end = i
                        lift_end_pos = current_pos
                        print(f"Lift motion ends at {i}, pos={current_pos:.3f}")
                        break
                    last_pos = current_pos
                
                if lift_end is None:
                    break  # End of file during lift
                
                # Now wait for the retraction (upward motion) and return cycle to complete
                # This will mark the start of the next layer
                retraction_found = False
                return_stable_count = 0
                last_pos = lift_end_pos
                
                while i < len(position_data) - window_size:
                    i += 1
                    window = position_data[i:i+window_size]
                    current_pos = np.mean(window)
                    direction = detect_movement(current_pos, last_pos)
                    
                    # First wait for retraction to start (upward motion)
                    if not retraction_found and direction == 1:  # Moving up (RETRACTION)
                        retraction_found = True
                        print(f"Retraction starts at {i}, pos={current_pos:.3f}")
                    
                    # After retraction starts, wait for stable period
                    if retraction_found:
                        if direction == 0:  # Stable
                            return_stable_count += 1
                            if return_stable_count >= min_stable_points:
                                print(f"Stage stable after retraction at {i}, pos={current_pos:.3f}")
                                layer_starts.append(i)  # This is the start of next layer
                                break
                        else:
                            return_stable_count = 0
                    
                    last_pos = current_pos
            
            i += 1
            last_pos = current_pos
        
        # Create layer boundaries as start/end index pairs
        boundaries = []
        for j in range(len(layer_starts)-1):
            boundaries.append((layer_starts[j], layer_starts[j+1]-1))
        
        # For the last layer, use the end of the file
        if layer_starts:
            boundaries.append((layer_starts[-1], len(position_data)-1))
            
        print(f"Found {len(layer_starts)} layer starts at indices: {layer_starts}")
        return boundaries
        
        # Store all the layer start indices we find
        layer_starts = []
        
        # First layer starts at beginning of file
        first_start = window_size  # Skip first few points for averaging
        layer_starts.append(first_start)
        print(f"First layer starts at index {first_start}")
        
        # Initialize position tracking
        i = first_start
        last_pos = np.mean(position_data[0:window_size])
        
        # Track through the entire position data
        while i < len(position_data) - window_size:
            window = position_data[i:i+window_size]
            current_pos = np.mean(window)
            direction = detect_movement(current_pos, last_pos)
            
            # Look for stage starting to move down (lifting phase)
            if direction == -1:  # Moving down (LIFTING)
                print(f"Stage starts lifting down at {i}, pos={current_pos:.3f}")
                
                # Follow through lift until it stops
                lift_end = None
                lift_end_pos = None
                while i < len(position_data) - window_size:
                    i += 1
                    window = position_data[i:i+window_size]
                    current_pos = np.mean(window)
                    if detect_movement(current_pos, last_pos) >= 0:  # No longer moving down
                        lift_end = i
                        lift_end_pos = current_pos
                        print(f"Lift motion ends at {i}, pos={current_pos:.3f}")
                        break
                    last_pos = current_pos
                
                if lift_end is None:
                    break  # End of file during lift
                
                # Now wait for the retraction (upward motion) and return cycle to complete
                # This will mark the start of the next layer
                retraction_found = False
                return_stable_count = 0
                last_pos = lift_end_pos
                
                while i < len(position_data) - window_size:
                    i += 1
                    window = position_data[i:i+window_size]
                    current_pos = np.mean(window)
                    direction = detect_movement(current_pos, last_pos)
                    
                    # First wait for retraction to start (upward motion)
                    if not retraction_found and direction == 1:  # Moving up (RETRACTION)
                        retraction_found = True
                        print(f"Retraction starts at {i}, pos={current_pos:.3f}")
                    
                    # After retraction starts, wait for stable period
                    if retraction_found:
                        if direction == 0:  # Stable
                            return_stable_count += 1
                            if return_stable_count >= min_stable_points:
                                print(f"Stage stable after retraction at {i}, pos={current_pos:.3f}")
                                layer_starts.append(i)  # This is the start of next layer
                                break
                        else:
                            return_stable_count = 0
                    
                    last_pos = current_pos
            
            i += 1
            last_pos = current_pos
            
        print(f"Found {len(layer_starts)} layer starts at indices: {layer_starts}")
        return layer_starts  # Return the actual layer start indices

    # NOTE: Plotting methods removed - use AnalysisPlotter module for visualization
    # RawData_Processor is a pure data processing module

    def _create_layer_object(self, metrics, peak_idx, start_idx, time_data, force_data, layer_idx, end_idx):
        """Creates a layer object with calculated metrics and indices."""
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
            'force_range': metrics.get('peak_force', 0) - metrics.get('baseline_force', 0)
        }
        
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
