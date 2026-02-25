"""
Test script to visualize smooth lifting detection
Shows position, velocity, and force with detected transition point
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'support_modules'))
sys.path.insert(0, str(Path(__file__).parent / 'post-processing'))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from adhesion_metrics_calculator import AdhesionMetricsCalculator

def test_smooth_lifting_visualization(csv_path, speed_um_s, layer_idx=0):
    """
    Visualize smooth lifting detection for a single layer
    
    Args:
        csv_path: Path to autolog CSV file
        speed_um_s: Target peel speed (400 or 4000)
        layer_idx: Which layer to visualize (0-based)
    """
    # Load data
    df = pd.read_csv(csv_path)
    time_data = df['Elapsed Time (s)'].to_numpy()
    position_data = df['Position (mm)'].to_numpy()
    force_data = df['Force (N)'].to_numpy()
    
    # Find lifting phase for the selected layer
    if 'Phase' in df.columns:
        phase_data = df['Phase'].to_numpy()
        # Find lifting phases
        lifting_starts = []
        in_lifting = False
        for i in range(len(phase_data)):
            if phase_data[i] == 2 and not in_lifting:  # Start of lifting
                lifting_starts.append(i)
                in_lifting = True
            elif phase_data[i] != 2:
                in_lifting = False
        
        if layer_idx >= len(lifting_starts):
            print(f"Layer {layer_idx} not found, only {len(lifting_starts)} layers available")
            return
        
        # Find end of lifting phase
        start_idx = lifting_starts[layer_idx]
        end_idx = start_idx + 1
        while end_idx < len(phase_data) and phase_data[end_idx] == 2:
            end_idx += 1
        
        print(f"Layer {layer_idx}: Lifting phase from index {start_idx} to {end_idx}")
    else:
        print("No Phase column found")
        return
    
    # Extract lifting phase
    times = time_data[start_idx:end_idx] - time_data[start_idx]
    positions = position_data[start_idx:end_idx]
    forces = force_data[start_idx:end_idx]
    
    # Calculate velocity
    dt = np.diff(times)
    dpos = np.diff(positions)
    velocities = (dpos / dt) * 1000  # um/s
    velocity_times = times[:-1] + dt/2  # Midpoints
    
    # Smooth velocities
    from scipy.signal import savgol_filter
    window = min(9, len(velocities))
    if window >= 3 and window % 2 == 1:
        velocities_smooth = savgol_filter(np.abs(velocities), window, 2)
    else:
        velocities_smooth = np.abs(velocities)
    
    # Create calculator and detect transition
    calc = AdhesionMetricsCalculator(skip_initial_time_ms=150, target_speed_um_s=speed_um_s)
    detected_idx = calc._detect_smooth_lifting_transition(times, positions)
    
    # Create visualization
    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
    
    # Plot 1: Position
    axes[0].plot(times * 1000, positions, 'b-', linewidth=2, label='Position')
    if detected_idx is not None:
        axes[0].axvline(times[detected_idx] * 1000, color='red', linestyle='--', 
                       linewidth=2, label=f'Detected transition (idx={detected_idx})')
    axes[0].set_ylabel('Position (mm)', fontsize=12)
    axes[0].set_title(f'Smooth Lifting Detection - {speed_um_s} um/s (Layer {layer_idx})', fontsize=14, fontweight='bold')
    axes[0].legend(fontsize=10)
    axes[0].grid(True, alpha=0.3)
    
    # Plot 2: Velocity
    axes[1].plot(velocity_times * 1000, velocities, 'gray', alpha=0.3, label='Raw velocity')
    axes[1].plot(velocity_times * 1000, velocities_smooth, 'g-', linewidth=2, label='Smoothed velocity')
    axes[1].axhline(speed_um_s * 0.85, color='orange', linestyle=':', linewidth=2, 
                   label=f'Target threshold (85% = {speed_um_s*0.85:.0f} um/s)')
    if detected_idx is not None and detected_idx < len(velocity_times):
        axes[1].axvline(velocity_times[detected_idx] * 1000, color='red', linestyle='--', linewidth=2)
    axes[1].set_ylabel('Velocity (um/s)', fontsize=12)
    axes[1].legend(fontsize=10)
    axes[1].grid(True, alpha=0.3)
    
    # Plot 3: Force
    axes[2].plot(times * 1000, forces, 'purple', linewidth=2, label='Force')
    if detected_idx is not None:
        axes[2].axvline(times[detected_idx] * 1000, color='red', linestyle='--', 
                       linewidth=2, label=f'Transition point')
        # Shade the "ignored" region before transition
        axes[2].axvspan(0, times[detected_idx] * 1000, alpha=0.2, color='yellow', 
                       label='Slow startup region (ignored)')
    axes[2].set_xlabel('Time (ms)', fontsize=12)
    axes[2].set_ylabel('Force (N)', fontsize=12)
    axes[2].legend(fontsize=10)
    axes[2].grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save figure
    output_name = f'smooth_lifting_test_{speed_um_s}ums_layer{layer_idx}.png'
    plt.savefig(output_name, dpi=150, bbox_inches='tight')
    print(f"\nVisualization saved: {output_name}")
    
    # Print statistics
    print(f"\n=== Statistics ===")
    print(f"Total lifting phase duration: {times[-1]*1000:.1f} ms")
    print(f"Transition detected at: {times[detected_idx]*1000:.1f} ms (index {detected_idx})")
    print(f"Position at transition: {positions[detected_idx]:.3f} mm")
    print(f"Distance traveled before transition: {abs(positions[detected_idx] - positions[0]):.3f} mm ({abs(positions[detected_idx] - positions[0])*1000:.0f} um)")
    print(f"Average velocity after transition: {np.mean(velocities_smooth[detected_idx:]):.0f} um/s")
    print(f"Target speed: {speed_um_s} um/s")
    
    plt.close()


if __name__ == "__main__":
    print("=== Testing 400 um/s Smooth Lifting Detection ===")
    test_folder_400 = Path(r'C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V9\PDMS_500um_V23Ext_Water_400')
    csv_files_400 = sorted(test_folder_400.glob('autolog*.csv'))
    if csv_files_400:
        test_smooth_lifting_visualization(csv_files_400[0], 400, layer_idx=0)
    
    print("\n" + "="*60)
    print("=== Testing 4000 um/s Smooth Lifting Detection ===")
    test_folder_4000 = Path(r'C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V9\PDMS_500um_V23Ext_Water_4000')
    csv_files_4000 = sorted(test_folder_4000.glob('autolog*.csv'))
    if csv_files_4000:
        test_smooth_lifting_visualization(csv_files_4000[0], 4000, layer_idx=0)
    
    print("\n✅ Visualization complete!")
