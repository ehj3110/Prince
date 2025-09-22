"""
Test the fixed calculator results without plotting
"""
from hybrid_adhesion_plotter import HybridAdhesionPlotter

# Create plotter instance
plotter = HybridAdhesionPlotter()

print("TESTING FIXED CALCULATOR RESULTS")
print("="*50)
print("Processing autolog_L198-L200.csv...")

# Load and process data (without creating plots)
import pandas as pd
import numpy as np
from scipy.signal import savgol_filter

# Load data
df = pd.read_csv("autolog_L198-L200.csv")
if 'Elapsed Time (s)' in df.columns:
    df = df.rename(columns={'Elapsed Time (s)': 'Time', 'Position (mm)': 'Position', 'Force (N)': 'Force'})

time_data = df['Time'].values
position_data = df['Position'].values
force_data = df['Force'].values
layer_numbers = [198, 199, 200]

print(f"Data loaded: {len(time_data)} points")
print(f"Time range: {time_data.min():.3f} to {time_data.max():.3f} seconds")

# Apply smoothing and detect peaks
smoothed_force = savgol_filter(force_data, window_length=3, polyorder=1)
peaks = plotter._detect_peaks(force_data, smoothed_force)
layer_boundaries = plotter._find_layer_boundaries(peaks, position_data, time_data, layer_numbers)

print(f"Detected peaks at indices: {peaks}")

# Process each layer
for i, peak_idx in enumerate(peaks):
    if i >= len(layer_numbers):
        break
        
    layer_num = layer_numbers[i]
    start_idx, end_idx = layer_boundaries[i]
    
    print(f"\n--- Processing Layer {layer_num} ---")
    print(f"Boundaries: indices {start_idx}-{end_idx}")
    
    # Extract layer segment data using RESET TIME (like hybrid plotter actually does)
    segment_time = time_data[start_idx:end_idx+1] - time_data[start_idx]  # Reset to start at 0
    segment_position = position_data[start_idx:end_idx+1]
    segment_force = force_data[start_idx:end_idx+1]
    
    print(f"Segment time range: {segment_time[0]:.3f} to {segment_time[-1]:.3f} seconds")
    
    # Calculate metrics using the reset time approach
    metrics = plotter.calculator.calculate_from_arrays(
        segment_time, segment_position, segment_force, layer_number=layer_num
    )
    
    print(f"Results (from calculator with reset time):")
    print(f"  Peak Force: {metrics['peak_force']:.6f} N")
    print(f"  Peak Time (relative): {metrics['peak_force_time']:.3f} s")
    print(f"  Propagation End Time (relative): {metrics['propagation_end_time']:.3f} s")
    print(f"  Baseline Force: {metrics['baseline_force']:.6f} N")
    print(f"  Work of Adhesion: {metrics['work_of_adhesion_corrected_mJ']:.3f} mJ")
    
    # Now show the conversion to global time (like hybrid plotter does)
    prop_end_global_time = time_data[start_idx] + metrics['propagation_end_time']
    prop_end_idx = np.argmin(np.abs(time_data - prop_end_global_time))
    final_plot_time = time_data[prop_end_idx]
    
    print(f"Conversion to global time:")
    print(f"  Global time calculation: {time_data[start_idx]:.3f} + {metrics['propagation_end_time']:.3f} = {prop_end_global_time:.3f} s")
    print(f"  Final plot time: {final_plot_time:.3f} s")
    print(f"  Plot index: {prop_end_idx}")

print(f"\nFixed calculator is now using absolute time like the test calculator!")
print(f"Layer 198 propagation end should now be close to your expected ~11.8s")
