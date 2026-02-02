"""
Test plot to check for water loss during sandwich step.
Plots first two layers from autolog file showing force vs time (left Y-axis)
and position vs time (right Y-axis).
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# File to analyze
csv_file = Path(r"C:\Users\cheng sun\BoyuanSun\Slicing\Evan\SteppedCone_V1_10mm2to100mm2_50umLayers_V2\Printing_Logs\2025-11-29\Print 2 - Complete\autolog_L430-L435.csv")

print(f"Loading data from: {csv_file}")
df = pd.read_csv(csv_file)

print(f"Columns available: {df.columns.tolist()}")
print(f"Total rows: {len(df)}")

# Extract data
time = df['Elapsed Time (s)'].values
force = df['Force (N)'].values
position = df['Position (mm)'].values

# Determine layer boundaries based on Phase column if available
if 'Phase' in df.columns:
    phase = df['Phase'].values
    
    # Print unique phase values to debug
    unique_phases = np.unique(phase)
    print(f"\nUnique phase values in data: {unique_phases}")
    
    # Find where phase changes to 'lifting' - that's the start of each layer
    layer_starts = []
    for i in range(1, len(phase)):
        if 'lift' in str(phase[i]).lower() and 'lift' not in str(phase[i-1]).lower():
            layer_starts.append(i)
    
    print(f"\nFound {len(layer_starts)} layer starts")
    if len(layer_starts) > 0:
        print(f"Layer 1 starts at index: {layer_starts[0]}")
    if len(layer_starts) > 1:
        print(f"Layer 2 starts at index: {layer_starts[1]}")
    
    # Extract first two complete layers
    if len(layer_starts) >= 3:
        # Layer 1: from first layer start to second layer start
        layer1_start = layer_starts[0]
        layer1_end = layer_starts[1]
        
        # Layer 2: from second layer start to third layer start
        layer2_start = layer_starts[1]
        layer2_end = layer_starts[2]
    elif len(layer_starts) >= 2:
        # Only have 2 layers
        layer1_start = layer_starts[0]
        layer1_end = layer_starts[1]
        
        layer2_start = layer_starts[1]
        layer2_end = len(time)
    else:
        print("ERROR: Not enough layers found in file")
        exit(1)
else:
    print("WARNING: No Phase column found, estimating layers from position changes")
    # Estimate from position changes (crude method)
    layer1_start = 0
    layer1_end = 2500
    layer2_start = 2500
    layer2_end = 5000

# Extract layer data
print(f"\nLayer 1: indices {layer1_start} to {layer1_end}")
print(f"Layer 2: indices {layer2_start} to {layer2_end}")

# Look back a bit before layer start to see sandwich step
lookback = 100  # samples before layer start
layer1_plot_start = max(0, layer1_start - lookback)
layer2_plot_start = max(0, layer2_start - lookback)

# Create figure with extra width for detail
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(20, 10))

# === LAYER 1 ===
l1_time = time[layer1_plot_start:layer1_end]
l1_force = force[layer1_plot_start:layer1_end]
l1_position = position[layer1_plot_start:layer1_end]
l1_time_offset = l1_time - l1_time[0]  # Start from 0

# Plot force on left Y-axis
color_force = 'tab:blue'
ax1.set_xlabel('Time (s)', fontsize=12)
ax1.set_ylabel('Force (N)', color=color_force, fontsize=12)
ax1.plot(l1_time_offset, l1_force, color=color_force, linewidth=1.5, label='Force')
ax1.tick_params(axis='y', labelcolor=color_force)
ax1.grid(True, alpha=0.3)

# Plot position on right Y-axis
ax1_right = ax1.twinx()
color_position = 'tab:red'
ax1_right.set_ylabel('Position (mm)', color=color_position, fontsize=12)
ax1_right.plot(l1_time_offset, l1_position, color=color_position, linewidth=1.5, alpha=0.7, label='Position')
ax1_right.tick_params(axis='y', labelcolor=color_position)

# Add vertical line at sandwich end (layer start)
sandwich_end_time = time[layer1_start] - l1_time[0]
ax1.axvline(x=sandwich_end_time, color='green', linestyle='--', linewidth=2, label='Sandwich End / Lift Start')

# Add title and legend
ax1.set_title('Layer 430 (First Layer) - Force and Position vs Time\n(Includes Sandwich Step Before Lift)', 
              fontsize=14, fontweight='bold')
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax1_right.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=10)

# Highlight sandwich region
if 'Phase' in df.columns:
    phase_slice = phase[layer1_plot_start:layer1_end]
    sandwich_mask = np.array(['sandwich' in str(p).lower() for p in phase_slice])
    if np.any(sandwich_mask):
        sandwich_time = l1_time_offset[sandwich_mask]
        if len(sandwich_time) > 0:
            ax1.axvspan(sandwich_time[0], sandwich_time[-1], alpha=0.2, color='yellow', label='Sandwich Phase')

# === LAYER 2 ===
l2_time = time[layer2_plot_start:layer2_end]
l2_force = force[layer2_plot_start:layer2_end]
l2_position = position[layer2_plot_start:layer2_end]
l2_time_offset = l2_time - l2_time[0]  # Start from 0

# Plot force on left Y-axis
ax2.set_xlabel('Time (s)', fontsize=12)
ax2.set_ylabel('Force (N)', color=color_force, fontsize=12)
ax2.plot(l2_time_offset, l2_force, color=color_force, linewidth=1.5, label='Force')
ax2.tick_params(axis='y', labelcolor=color_force)
ax2.grid(True, alpha=0.3)

# Plot position on right Y-axis
ax2_right = ax2.twinx()
ax2_right.set_ylabel('Position (mm)', color=color_position, fontsize=12)
ax2_right.plot(l2_time_offset, l2_position, color=color_position, linewidth=1.5, alpha=0.7, label='Position')
ax2_right.tick_params(axis='y', labelcolor=color_position)

# Add vertical line at sandwich end (layer start)
sandwich_end_time = time[layer2_start] - l2_time[0]
ax2.axvline(x=sandwich_end_time, color='green', linestyle='--', linewidth=2, label='Sandwich End / Lift Start')

# Add title and legend
ax2.set_title('Layer 431 (Second Layer) - Force and Position vs Time\n(Includes Sandwich Step Before Lift)', 
              fontsize=14, fontweight='bold')
lines1, labels1 = ax2.get_legend_handles_labels()
lines2, labels2 = ax2_right.get_legend_handles_labels()
ax2.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=10)

# Highlight sandwich region
if 'Phase' in df.columns:
    phase_slice = phase[layer2_plot_start:layer2_end]
    sandwich_mask = np.array(['sandwich' in str(p).lower() for p in phase_slice])
    if np.any(sandwich_mask):
        sandwich_time = l2_time_offset[sandwich_mask]
        if len(sandwich_time) > 0:
            ax2.axvspan(sandwich_time[0], sandwich_time[-1], alpha=0.2, color='yellow', label='Sandwich Phase')

plt.tight_layout()

# Save the plot
output_path = csv_file.parent / "water_loss_check_L430-431.png"
plt.savefig(output_path, dpi=150, bbox_inches='tight')
print(f"\n✅ Plot saved to: {output_path}")

# Print some statistics about the sandwich phase
print("\n" + "="*60)
print("SANDWICH STEP ANALYSIS")
print("="*60)

if 'Phase' in df.columns:
    for layer_num, (layer_name, start, end) in enumerate([
        ("Layer 430", layer1_start, layer1_end),
        ("Layer 431", layer2_start, layer2_end)
    ], start=1):
        # Find sandwich phase (case-insensitive)
        sandwich_indices = []
        for i in range(max(0, start-200), start):  # Look back up to 200 samples
            if 'sandwich' in str(phase[i]).lower():
                sandwich_indices.append(i)
        
        if sandwich_indices:
            sandwich_start_idx = sandwich_indices[0]
            sandwich_end_idx = sandwich_indices[-1]
            
            sandwich_duration = time[sandwich_end_idx] - time[sandwich_start_idx]
            sandwich_force_start = force[sandwich_start_idx]
            sandwich_force_end = force[sandwich_end_idx]
            sandwich_force_max = np.max(force[sandwich_indices])
            sandwich_force_rate = (sandwich_force_end - sandwich_force_start) / sandwich_duration if sandwich_duration > 0 else 0
            
            print(f"\n{layer_name}:")
            print(f"  Sandwich duration: {sandwich_duration:.3f} s")
            print(f"  Force at start: {sandwich_force_start:.4f} N")
            print(f"  Force at end: {sandwich_force_end:.4f} N")
            print(f"  Max force during sandwich: {sandwich_force_max:.4f} N")
            print(f"  Force rate of change: {sandwich_force_rate:.4f} N/s")
            print(f"  Position at sandwich end: {position[sandwich_end_idx]:.4f} mm")
            
            # Check if force rises very quickly (potential sign of water loss)
            if sandwich_force_rate > 0.5:  # Threshold for "very fast" rise
                print(f"  ⚠️  WARNING: Force rises very quickly ({sandwich_force_rate:.2f} N/s)")
                print(f"      This could indicate water loss!")

print("\n" + "="*60)
print("INTERPRETATION:")
print("="*60)
print("If water is being lost, you would expect to see:")
print("  1. Force rising VERY quickly during sandwich (> 0.5 N/s)")
print("  2. High force reached before stage even starts moving")
print("  3. Progressively worse behavior in later layers")
print("="*60)

plt.show()
