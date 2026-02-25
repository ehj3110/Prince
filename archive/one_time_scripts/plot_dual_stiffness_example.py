"""
Plot the best example of dual-stiffness behavior for presentation.
Shows force vs displacement with dotted lines for the two stiffness regimes.
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import sys

# Add support modules to path
sys.path.insert(0, str(Path(__file__).parent / 'support_modules'))

from adhesion_metrics_calculator import AdhesionMetricsCalculator

def plot_dual_stiffness_layer(folder_num, layer_num, autolog_file):
    """
    Create a presentation-quality plot showing dual stiffness behavior.
    
    Args:
        folder_num: Folder number
        layer_num: Layer number
        autolog_file: Name of the autolog file
    """
    # Paths
    base_dir = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\TEMPO Picker")
    folder_path = base_dir / str(folder_num)
    autolog_path = folder_path / autolog_file
    output_path = base_dir / f"Dual_Stiffness_Example_F{folder_num}_L{layer_num}.png"
    
    print(f"Processing Folder {folder_num}, Layer {layer_num}")
    print(f"Reading: {autolog_path}")
    
    # Read the CSV to get the metrics that were already calculated
    master_csv = base_dir / 'MASTER_all_metrics.csv'
    metrics_df = pd.read_csv(master_csv)
    
    # Find this specific layer (folder and layer_number are both integers in CSV)
    layer_metrics = metrics_df[(metrics_df['folder'] == folder_num) & 
                               (metrics_df['layer_number'] == layer_num)].iloc[0]
    
    # Read the autolog file
    df = pd.read_csv(autolog_path)
    
    # Process with calculator to get metrics and phase information
    calculator = AdhesionMetricsCalculator(
        skip_initial_distance_um=200
    )
    
    # Extract layer data
    # The file has multiple layers, need to find the right one
    # Use phase markers to identify layer boundaries
    phase_col = 'Phase' if 'Phase' in df.columns else None
    
    if phase_col:
        # Find layer boundaries using phase transitions to Lift-Stage1
        # (each layer starts with a new Lift-Stage1 phase)
        phase_changes = df[phase_col] != df[phase_col].shift()
        lift_starts = df[phase_changes & (df[phase_col] == 'Lift-Stage1')].index.tolist()
        
        # Find which lift corresponds to our layer
        # Layers are numbered sequentially in the file
        from_layer = int(autolog_file.split('L')[1].split('-')[0])
        layer_offset = layer_num - from_layer
        
        print(f"  Found {len(lift_starts)} layers in file (layers {from_layer}-{from_layer + len(lift_starts) - 1})")
        print(f"  Looking for layer {layer_num} (offset {layer_offset})")
        
        if layer_offset < len(lift_starts):
            start_idx = lift_starts[layer_offset]
            
            # Find end of this layer (start of next layer or end of file)
            if layer_offset + 1 < len(lift_starts):
                end_idx = lift_starts[layer_offset + 1]
            else:
                end_idx = len(df)
            
            # Extract layer data
            layer_df = df.iloc[start_idx:end_idx].copy()
            
            # Get baseline from the pre-calculated metrics
            baseline = float(layer_metrics['baseline_force'])
            
            # DEBUG: Print phase information
            if 'Phase' in layer_df.columns:
                unique_phases = layer_df['Phase'].unique()
                print(f"  Unique phases in layer: {unique_phases}")
                print(f"  Total rows before filtering: {len(layer_df)}")
            
            # Filter to LIFTING stage only (exclude retraction)
            if 'Phase' in layer_df.columns:
                lifting_mask = layer_df['Phase'].str.contains('Lift', na=False) & ~layer_df['Phase'].str.contains('Retract', na=False)
                layer_df = layer_df[lifting_mask].copy()
                print(f"  Rows after lifting-only filter: {len(layer_df)}")
            
            # Get force and position data
            force = layer_df['Force (N)'].values
            position = layer_df['Position (mm)'].values
            
            # DEBUG: Print data ranges
            print(f"  Baseline: {baseline:.4f} N")
            print(f"  Force range: {force.min():.4f} to {force.max():.4f} N")
            print(f"  Delta-force range: {(force.min()-baseline):.4f} to {(force.max()-baseline):.4f} N")
            print(f"  Position range: {position.min():.4f} to {position.max():.4f} mm")
            
            # Calculate metrics to get indices for plotting - NOW ON LIFTING DATA ONLY
            time = layer_df['Time (s)'].values if 'Time (s)' in layer_df.columns else np.arange(len(force)) / 10
            results = calculator.calculate_from_arrays(
                time, position, force,
                layer_number=layer_num
            )
            
            # Get stiffness values from the RECALCULATED metrics (lifting-only)
            regime1_stiffness = results.get('regime1_stiffness_N_per_mm', 0)
            regime2_stiffness = results.get('regime2_stiffness_N_per_mm', 0)
            transition_distance = results.get('transition_position_um', 0)
            two_regime_detected = results.get('two_regime_detected', False)
            
            if not two_regime_detected:
                print(f"  WARNING: No two-regime behavior detected in lifting-only data!")
                print(f"  Using CSV values (which may include retraction): R1={layer_metrics['regime1_stiffness_N_per_mm']:.4f}, R2={layer_metrics['regime2_stiffness_N_per_mm']:.4f}")
                regime1_stiffness = float(layer_metrics['regime1_stiffness_N_per_mm'])
                regime2_stiffness = float(layer_metrics['regime2_stiffness_N_per_mm'])
                transition_distance = float(layer_metrics['transition_position_um'])
            else:
                print(f"  Two-regime detected in LIFTING data: R1={regime1_stiffness:.4f} N/mm, R2={regime2_stiffness:.4f} N/mm")
                print(f"  Transition position: {transition_distance:.1f} um (expected ~500-1500 um)")
                
                # For Layer 158, show additional debug info
                if folder_num == 2 and layer_num == 158:
                    print(f"\n  LAYER 158 TRANSITION DETAILS:")
                    print(f"  Pre-init index: {results.get('pre_initiation_idx', 'N/A')}")
                    print(f"  Peak index: {results.get('peak_idx', 'N/A')} (where propagation starts)")
                    print(f"  Transition from CSV (full data): {layer_metrics['transition_position_um']:.1f} um")
                    print(f"  Transition from lifting-only: {transition_distance:.1f} um")
            
            # Get the key indices from results
            pre_init_idx = results.get('pre_initiation_idx', 0)
            
            # Adjust pre_init_idx if needed (it's already relative to filtered data)
            if pre_init_idx >= len(position):
                pre_init_idx = 0
            
            # Convert to delta-position (relative to start of lifting)
            # Use absolute value since position decreases during lifting (printer moves up)
            if len(position) > 0:
                position_start = position[0]
                delta_position = np.abs(position - position_start) * 1000  # Convert to micrometers (absolute value)
            else:
                print("  Warning: No data in lifting stage")
                return
            
            # Convert to delta-force (baseline-corrected)
            delta_force = force - baseline
            
            # Use delta_force directly (no additional smoothing)
            delta_force_smooth = delta_force
            
            # DEBUG: Verify we're only plotting lifting data
            print(f"\n  DATA VERIFICATION:")
            print(f"  Position direction: {position[0]:.4f} -> {position[-1]:.4f} mm ({'DECREASING (lifting)' if position[-1] < position[0] else 'INCREASING (retraction?)'})")
            print(f"  Delta-position range: 0 -> {delta_position[-1]:.1f} um")
            print(f"  Number of points: {len(delta_position)}")
            print(f"  Pre-init index: {pre_init_idx} (delta-pos = {delta_position[pre_init_idx]:.1f} um)")
            if 'Phase' in layer_df.columns:
                print(f"  Phases in data: {layer_df['Phase'].unique()}")
            
            # Create the plot
            fig, ax = plt.subplots(figsize=(12, 8))
            
            # Plot the actual data (delta-position in μm vs delta-force)
            # Use different label and thickness for Layer 158
            if folder_num == 2 and layer_num == 158:
                data_label = 'Measured Force'
                linewidth = 3
            else:
                data_label = 'Measured Force (baseline-corrected)'
                linewidth = 2
            
            ax.plot(delta_position, delta_force_smooth, 'k-', linewidth=linewidth, label=data_label, zorder=1)
            
            # Plot zero line (was baseline, now zero since we're using delta-force)
            ax.axhline(y=0, color='gray', linestyle='--', linewidth=1.5, 
                      label='Zero (baseline removed)', alpha=0.7)
            
            # Calculate the two stiffness regime lines using delta-position
            # Regime 1: From start to transition (now in micrometers)
            if transition_distance > 0:
                # Get pre-initiation position in delta-coordinates
                pre_init_delta_pos = delta_position[pre_init_idx] if pre_init_idx < len(delta_position) else 0
                
                # Regime 1 region: from pre-init to transition
                regime1_mask = (delta_position >= pre_init_delta_pos) & (delta_position <= pre_init_delta_pos + transition_distance)
                if np.any(regime1_mask):
                    regime1_positions = delta_position[regime1_mask]
                    # Stiffness is in N/mm, positions are in μm, so convert: N/mm * (μm/1000) = N
                    regime1_start_force = 0  # Starting from baseline (zero in delta-force)
                    regime1_forces = regime1_start_force + regime1_stiffness * (regime1_positions - pre_init_delta_pos) / 1000
                    
                    # Update labels to include full info for Layer 158
                    if folder_num == 2 and layer_num == 158:
                        regime1_label = f'Regime 1: {regime1_stiffness:.4f} N/mm'
                    else:
                        regime1_label = f'Regime 1: {regime1_stiffness:.4f} N/mm'
                    
                    ax.plot(regime1_positions, regime1_forces, 'b--', linewidth=3, 
                           label=regime1_label, zorder=3, alpha=0.8)
                
                # Regime 2 region: from transition onward
                regime2_start_pos = pre_init_delta_pos + transition_distance
                regime2_mask = delta_position >= regime2_start_pos
                if np.any(regime2_mask):
                    regime2_positions = delta_position[regime2_mask]
                    # Start from where regime 1 ended
                    regime2_start_force = regime1_stiffness * transition_distance / 1000
                    regime2_forces = regime2_start_force + regime2_stiffness * (regime2_positions - regime2_start_pos) / 1000
                    
                    # Update labels to include full info for Layer 158
                    if folder_num == 2 and layer_num == 158:
                        regime2_label = f'Regime 2: {regime2_stiffness:.4f} N/mm'
                    else:
                        regime2_label = f'Regime 2: {regime2_stiffness:.4f} N/mm'
                    
                    ax.plot(regime2_positions, regime2_forces, 'r--', linewidth=3, 
                           label=regime2_label, zorder=3, alpha=0.8)
                
                # Mark transition point
                if folder_num == 2 and layer_num == 158:
                    transition_label = f'Transition at {transition_distance:.0f} μm'
                else:
                    transition_label = f'Transition ({transition_distance:.0f} μm)'
                
                ax.axvline(x=regime2_start_pos, color='orange', linestyle=':', linewidth=2, 
                          label=transition_label, alpha=0.7)
            
            # Formatting
            # Use larger font sizes for Layer 158
            if folder_num == 2 and layer_num == 158:
                xlabel_size = 20
                ylabel_size = 20
                tick_size = 16
            else:
                xlabel_size = 16
                ylabel_size = 16
                tick_size = 12
            
            ax.set_xlabel('Δ Position (μm)', fontsize=xlabel_size, fontweight='bold')
            ax.set_ylabel('Δ Force (N)', fontsize=ylabel_size, fontweight='bold')
            
            # Update title format for Layer 158
            if folder_num == 2 and layer_num == 158:
                ax.set_title(f'Dual-Stiffness Behaviour\nStiffness Ratio: {regime2_stiffness/regime1_stiffness:.2f}×', 
                            fontsize=18, fontweight='bold')
            else:
                ax.set_title(f'Dual Stiffness Behavior - Folder {folder_num}, Layer {layer_num}\n' + 
                            f'Stiffness Ratio: {regime2_stiffness/regime1_stiffness:.2f}×', 
                            fontsize=18, fontweight='bold')
            ax.legend(fontsize=12, loc='best', framealpha=0.9)
            ax.grid(True, alpha=0.3)
            ax.tick_params(labelsize=tick_size)
            
            # Crop axes to data range with 10% padding on each side
            # For Layer 158, clip X to 100-4000 μm
            if folder_num == 2 and layer_num == 158:
                x_min = 100
                x_max = 4000
                x_range = x_max - x_min
                ax.set_xlim(x_min - 0.1 * x_range, x_max + 0.1 * x_range)
                
                # Crop Y to match the data within the X range
                x_mask = (delta_position >= x_min) & (delta_position <= x_max)
                if np.any(x_mask):
                    y_min, y_max = delta_force_smooth[x_mask].min(), delta_force_smooth[x_mask].max()
                    y_range = y_max - y_min
                    ax.set_ylim(y_min - 0.1 * y_range, y_max + 0.1 * y_range)
            else:
                x_min, x_max = delta_position.min(), delta_position.max()
                x_range = x_max - x_min
                ax.set_xlim(x_min - 0.1 * x_range, x_max + 0.1 * x_range)
                
                y_min, y_max = delta_force_smooth.min(), delta_force_smooth.max()
                y_range = y_max - y_min
                ax.set_ylim(y_min - 0.1 * y_range, y_max + 0.1 * y_range)
            
            # Add text box with key metrics (only for non-Layer 158)
            if not (folder_num == 2 and layer_num == 158):
                textstr = '\n'.join([
                    f'Regime 1: {regime1_stiffness:.4f} N/mm',
                    f'Regime 2: {regime2_stiffness:.4f} N/mm',
                    f'Ratio: {regime2_stiffness/regime1_stiffness:.2f}×',
                    f'Transition: {transition_distance:.0f} μm'
                ])
                props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
                ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=12,
                       verticalalignment='top', bbox=props)
            
            plt.tight_layout()
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            print(f"\nPlot saved to: {output_path}")
            plt.close()
            
            # Print summary
            print(f"\nDual Stiffness Summary:")
            print(f"  Regime 1 Stiffness: {regime1_stiffness:.4f} N/mm")
            print(f"  Regime 2 Stiffness: {regime2_stiffness:.4f} N/mm")
            print(f"  Stiffness Ratio: {regime2_stiffness/regime1_stiffness:.2f}x")
            print(f"  Transition Distance: {transition_distance:.0f} um")
    else:
        print("Error: No Phase column found in data")

if __name__ == "__main__":
    # Plot the best example: Folder 2, Layer 145
    # Ratio=3.14×, Regime1=0.0231, Regime2=0.0726, Diff=0.0495 N/mm
    # Good balance of high ratio and good absolute difference (visually clear)
    plot_dual_stiffness_layer(
        folder_num=2,
        layer_num=145,
        autolog_file='autolog_L142-L146.csv'
    )
    
    print("\n" + "="*70)
    print("Also generating backup examples...")
    print("="*70)
    
    # Also generate a few backup options
    backup_examples = [
        (2, 158, 'autolog_L154-L158.csv'),  # Ratio 2.76, high absolute difference
        (2, 145, 'autolog_L142-L146.csv'),  # Ratio 3.14
        (1, 110, 'autolog_L107-L111.csv'),  # Ratio 2.87, from Folder 1
    ]
    
    for folder, layer, file in backup_examples:
        try:
            plot_dual_stiffness_layer(folder, layer, file)
        except Exception as e:
            print(f"Error processing Folder {folder}, Layer {layer}: {e}")
