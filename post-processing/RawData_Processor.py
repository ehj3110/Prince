import numpy as np
from scipy.signal import find_peaks
from pathlib import Path
import pandas as pd
from typing import List, Tuple

class RawDataProcessor:
    def __init__(self, calculator, plotter):
        self.calculator = calculator
        self.plotter = plotter

    def process_csv(self, csv_filepath: str, title: str = None, save_path: str = None):
        """
        Process a CSV file containing raw force/position data
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
        smoothed_force = self.calculator.apply_smoothing(force_data)
        peak_indices = self._detect_peaks(smoothed_force)

        # Get layer numbers from filename
        layer_numbers = self._extract_layer_numbers_from_filename(csv_filepath)
        if len(layer_numbers) > len(peak_indices):
            layer_numbers = layer_numbers[:len(peak_indices)]

        layer_boundaries = self._find_layer_boundaries(peak_indices, position_data, time_data, layer_numbers)

        # Debug plot to visualize boundaries
        self._create_debug_plot(time_data, force_data, position_data, layer_boundaries, peak_indices,
                              title="Layer Boundary Debug Plot",
                              save_path=Path(save_path).parent / "layer_boundaries_debug.png" if save_path else None)

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

        # 4. Generate Plot
        if layers:
            self.plotter.create_plot(time_data, force_data, smoothed_force, layers, title, save_path)

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


    def _create_debug_plot(self, time_data: np.ndarray, force_data: np.ndarray, 
                         position_data: np.ndarray, layer_boundaries: List[Tuple[int, int]],
                         peak_indices: np.ndarray, title: str = None, save_path: Path = None):
        """Creates a debug plot showing force, position, and layer boundaries."""
        import matplotlib.pyplot as plt
        
        # Create figure with two y-axes
        fig, ax1 = plt.subplots(figsize=(12, 6))
        ax2 = ax1.twinx()
        
        # Plot force data on first axis
        line1 = ax1.plot(time_data, force_data, 'b-', label='Force', alpha=0.6)
        ax1.set_xlabel('Time (s)')
        ax1.set_ylabel('Force (N)', color='b')
        ax1.tick_params(axis='y', labelcolor='b')
        
        # Plot position data on second axis
        line2 = ax2.plot(time_data, position_data, 'r-', label='Position', alpha=0.6)
        ax2.set_ylabel('Position (mm)', color='r')
        ax2.tick_params(axis='y', labelcolor='r')
        
        # Plot peaks and layer boundaries
        for peak_idx in peak_indices:
            ax1.axvline(x=time_data[peak_idx], color='g', linestyle=':', alpha=0.5)
            
        for start, end in layer_boundaries:
            ax1.axvline(x=time_data[start], color='k', linestyle='--', alpha=0.3)
            ax1.axvline(x=time_data[end], color='r', linestyle='--', alpha=0.3)
        
        # Set title if provided
        if title:
            plt.title(title)
            
        # Combine legends
        lines = line1 + line2
        labels = [l.get_label() for l in lines]
        ax1.legend(lines, labels, loc='upper right', fontsize=8)
        
        # Save or show plot
        if save_path:
            plt.savefig(save_path)
            print(f"Plotter: Plot saved to {save_path}")
            plt.close()
        else:
            plt.show()

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
    import sys
    from pathlib import Path
    
    if len(sys.argv) < 2:
        print("Usage: python RawData_Processor.py <csv_file>")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    processor = RawDataProcessor(None, None)  # No calculator/plotter needed for testing
    
    # Load data directly for testing
    df = pd.read_csv(csv_file)
    time_data = df['Elapsed Time (s)'].to_numpy()
    force_data = df['Force (N)'].to_numpy()
    position_data = df['Position (mm)'].to_numpy()
    
    # Just test layer boundary detection
    peak_indices = processor._detect_peaks(processor._smooth_data(force_data))
    boundaries = processor._find_layer_boundaries(peak_indices, position_data, time_data, [1,2,3])
    
    # Helper functions for motion detection
    window_size = 5  # Points to average for stability check
    pos_threshold = 0.03  # mm threshold for movement detection
    sampling_rate = 50  # Hz
    min_stable_points = int(0.2 * sampling_rate)  # 10 points minimum for stable period
    
    def detect_movement(curr_pos, last_pos):
        diff = curr_pos - last_pos
        if abs(diff) < pos_threshold/2:
            return 0  # stable
        return 1 if diff > 0 else -1  # 1 for increasing, -1 for decreasing
    
    # Create debug plot
    import matplotlib.pyplot as plt
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    
    # Plot force data with peaks
    ax1.plot(time_data, force_data, label='Force')
    ax1.scatter(time_data[peak_indices], force_data[peak_indices], color='red', marker='x', s=100, label='Force Peaks')
    layer_starts = boundaries  # Get layer start indices
    ax1.scatter(time_data[layer_starts], force_data[layer_starts], 
                color='green', marker='o', s=100, label='Layer Starts')
    ax1.set_ylabel('Force (N)')
    ax1.legend()
    ax1.grid(True)
    
    # Plot position data
    ax2.plot(time_data, position_data, label='Position')
    
    # Add shaded regions for each layer with increased alpha for visibility
    print(f"Adding shaded regions for layers starting at indices: {layer_starts}")
    colors = ['lightblue', 'lightgreen', 'lightpink']
    
    # Find the last significant motion in the data to set plot range
    last_motion_idx = None
    for i in range(len(position_data)-window_size-1, window_size, -1):
        window = position_data[i-window_size:i+window_size]
        if np.std(window) > pos_threshold/2:
            last_motion_idx = i
            break
    
    if last_motion_idx is None:
        last_motion_idx = len(position_data) - 1
    
    # Add shaded regions with higher alpha for better visibility
    for i in range(len(layer_starts) - 1):
        start_idx = layer_starts[i]
        end_idx = layer_starts[i + 1]
        # Add shading with higher alpha (0.3) for better visibility
        ax2.axvspan(time_data[start_idx], time_data[end_idx], 
                   alpha=0.3, color=colors[i % len(colors)],
                   label=f'Layer {i+1}')
        
        # Also shade the same region in the force plot
        ax1.axvspan(time_data[start_idx], time_data[end_idx],
                   alpha=0.3, color=colors[i % len(colors)])
    
    # Set x-axis limits to show only relevant data
    x_margin = 0.5  # 0.5 second margin
    start_time = time_data[layer_starts[0]] - x_margin
    end_time = min(time_data[last_motion_idx] + x_margin, time_data[layer_starts[-1]] + x_margin)
    ax1.set_xlim(start_time, end_time)
    ax2.set_xlim(start_time, end_time)
    
    ax2.legend()
    ax2.set_xlabel('Time (s)')
    ax2.set_ylabel('Position (mm)')
    ax2.legend()
    ax2.grid(True)
    
    # Add title and additional information
    ax1.set_title('Force Data with Layer Boundaries')
    ax2.set_title('Stage Position with Layer Regions')
    
    # Customize the position plot appearance
    ax2.set_ylabel('Position (mm)')
    ax2.grid(True)
    
    plt.tight_layout()
    plt.savefig('layer_boundaries_debug.png', dpi=300, bbox_inches='tight')
    plt.close()