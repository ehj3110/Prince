"""
Generate Complete TEMPO Picker Style Master Plots for V2 Data
==============================================================

This script applies the full TEMPO Picker plotting system to V2 SteppedCone data:
- Mean plots with SEM error bands
- Median plots with MAD error bands
- Log-log plots with power law fits

All plots use the exact TEMPO Picker styling (Times New Roman, tab10 colors, etc.)

Author: Cheng Sun Lab Team
Date: January 20, 2026
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Import the TEMPO Picker plotting styles module
import tempo_picker_plot_styles as tempo_styles

def prepare_v2_data(csv_path):
    """
    Load and prepare V2 data for plotting
    
    Args:
        csv_path: Path to MASTER_v2_selected_metrics.csv
    
    Returns:
        DataFrame ready for plotting
    """
    print("\n" + "="*80)
    print("LOADING V2 DATA")
    print("="*80)
    
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} layers from {csv_path}")
    
    # Load area mapping from LayerToArea.txt
    v2_dir = Path(csv_path).parent
    area_file = v2_dir / "LayerToArea.txt"
    
    if area_file.exists():
        print(f"\nLoading area mapping from {area_file.name}...")
        area_map = pd.read_csv(area_file, sep='\t')
        print(f"  Found {len(area_map)} layer-area mappings")
        print(f"  Area range: {area_map['Area'].min():.2f} to {area_map['Area'].max():.2f} mm²")
        print(f"  Unique areas: {area_map['Area'].nunique()}")
        
        # Merge area data
        df = df.merge(area_map, left_on='layer_number', right_on='Layer_Number', how='left')
        df.rename(columns={'Area': 'cross_sectional_area_mm2'}, inplace=True)
        
        # Create autolog file identifier based on layer number groups
        # Layer numbers like 100-105, 140-145, etc. indicate different autolog files
        print(f"\nIdentifying autolog files from layer numbers...")
        
        def get_autolog_group(layer_num):
            """Determine which autolog file a layer belongs to based on layer number patterns"""
            # Autolog files contain 6 consecutive layers
            # Common patterns: L60-65, L100-105, L140-145, L180-185, L210-215, 
            #                  L250-255, L300-305, L335-340, L365-370, L430-435
            # Strategy: Find the starting layer (nearest multiple of pattern)
            
            if layer_num <= 65:
                return "L60"  # L60-65
            elif layer_num <= 105:
                return "L100"  # L100-105
            elif layer_num <= 145:
                return "L140"  # L140-145
            elif layer_num <= 185:
                return "L180"  # L180-185
            elif layer_num <= 215:
                return "L210"  # L210-215
            elif layer_num <= 255:
                return "L250"  # L250-255
            elif layer_num <= 305:
                return "L300"  # L300-305
            elif layer_num <= 340:
                return "L335"  # L335-340
            elif layer_num <= 370:
                return "L365"  # L365-370
            elif layer_num <= 435:
                return "L430"  # L430-435
            else:
                # Fallback for unknown ranges
                return f"L{(layer_num // 10) * 10}"
        
        df['autolog_group'] = df['layer_number'].apply(get_autolog_group)
        df['autolog_id'] = df['folder'] + '_' + df['autolog_group']
        
        # Calculate AVERAGE area per autolog file and assign to all layers from that file
        print(f"Calculating average area per autolog file...")
        avg_area_per_autolog = df.groupby('autolog_id')['cross_sectional_area_mm2'].mean()
        print(f"  Found {len(avg_area_per_autolog)} unique autolog files")
        print(f"  Sample average areas:")
        for autolog_id in sorted(avg_area_per_autolog.index)[:5]:
            avg_area = avg_area_per_autolog[autolog_id]
            count = (df['autolog_id'] == autolog_id).sum()
            print(f"    {autolog_id}: {avg_area:.2f} mm² ({count} layers)")
        
        # Replace all areas with the average for their autolog file
        df['cross_sectional_area_mm2'] = df['autolog_id'].map(avg_area_per_autolog)
        
        # Calculate radius from average area
        df['radius_mm'] = np.sqrt(df['cross_sectional_area_mm2'] / np.pi)
        print(f"  Calculated radius range: {df['radius_mm'].min():.3f} to {df['radius_mm'].max():.3f} mm")
        
        x_col = 'radius_mm'
        xlabel = 'Contact Radius (mm)'
    else:
        print(f"\n⚠ Warning: {area_file.name} not found, using layer_number as x-axis")
        x_col = 'layer_number'
        xlabel = 'Layer Number'
    
    # Create a simplified condition label
    df['condition_label'] = df['folder'].apply(lambda x: '2.5% PEO' if '2p5PEO' in x else 'Water')
    
    # Ensure we have layer_number column
    if 'layer_number' not in df.columns:
        # Create layer numbers grouped by condition
        df['layer_number'] = df.groupby('condition_label').cumcount() + 1
    
    # Take absolute values of distance metrics if they're negative
    distance_cols = ['pre_initiation_distance', 'propagation_distance']
    for col in distance_cols:
        if col in df.columns and df[col].min() < 0:
            print(f"  Taking absolute value of {col} (was negative)")
            df[col] = df[col].abs()
    
    # Filter out the last Water data point (Layer 430-435)
    # This is the autolog_L430 group - to match 9 data points for both conditions
    print("\nFiltering data...")
    before_count = len(df)
    df = df[~((df['condition_label'] == 'Water') & (df['autolog_group'] == 'L430'))]
    after_count = len(df)
    print(f"  Removed {before_count - after_count} Water layers (L430-435 group) - both datasets now have 9 autolog groups")
    
    # Print summary
    print("\nConditions found:")
    for condition in sorted(df['condition_label'].unique()):
        count = len(df[df['condition_label'] == condition])
        print(f"  - {condition}: {count} layers")
    
    print("\nColumns available:")
    available_metrics = [
        'peak_force',
        'work_of_adhesion_corrected_mJ',
        'total_peel_distance',
        'peak_retraction_force_N'
    ]
    for col in available_metrics:
        if col in df.columns:
            print(f"  ✓ {col}")
        else:
            print(f"  ✗ {col} (NOT FOUND)")
    
    return df, x_col, xlabel


def main():
    """Main execution function"""
    
    # Define paths
    v2_data_dir = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V2")
    csv_path = v2_data_dir / "MASTER_v2_selected_metrics.csv"
    output_dir = v2_data_dir / "V2_MASTER_plots"
    
    # Check if input file exists
    if not csv_path.exists():
        print(f"\n❌ ERROR: Input file not found: {csv_path}")
        print("Please run batch_process_v2_selected.py first to generate the data.")
        return
    
    # Load and prepare data
    df, x_col, xlabel = prepare_v2_data(csv_path)
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nOutput directory: {output_dir}")
    
    # Generate all master plots using TEMPO Picker styles
    print("\n" + "="*80)
    print("APPLYING TEMPO PICKER PLOTTING STYLES")
    print("="*80)
    print("\nGenerating:")
    print("  1. Mean plots (with SEM error bands)")
    print("  2. Median plots (with MAD error bands)")
    print("  3. Log-Log plots (with power law fits)")
    print(f"\nUsing {x_col} as x-axis")
    
    tempo_styles.generate_complete_master_plots(
        df=df,
        output_dir=output_dir,
        x_col=x_col,
        condition_col='condition_label'
    )
    
    print("\n" + "="*80)
    print("✓ COMPLETE!")
    print("="*80)
    print(f"\nAll plots saved to: {output_dir}")
    print("\nPlot organization:")
    print(f"  📊 Mean plots:    {output_dir / 'Mean_plots'}")
    print(f"  📊 Median plots:  {output_dir / 'Median_plots'}")
    print(f"  📊 Log-Log plots: {output_dir / 'Log-Log_plots'}")
    
    # Print summary statistics
    print("\n" + "="*80)
    print("SUMMARY STATISTICS")
    print("="*80)
    
    for condition in sorted(df['condition_label'].unique()):
        condition_data = df[df['condition_label'] == condition]
        print(f"\n{condition} (n={len(condition_data)}):")
        print(f"  Peak Force: {condition_data['peak_force'].mean():.4f} ± {condition_data['peak_force'].std():.4f} N")
        print(f"  Work of Adhesion: {condition_data['work_of_adhesion_corrected_mJ'].mean():.4f} ± {condition_data['work_of_adhesion_corrected_mJ'].std():.4f} mJ")
        if 'pre_initiation_distance' in condition_data.columns:
            print(f"  Pre-Initiation Distance: {condition_data['pre_initiation_distance'].mean():.4f} ± {condition_data['pre_initiation_distance'].std():.4f} mm")
        if 'propagation_distance' in condition_data.columns:
            print(f"  Propagation Distance: {condition_data['propagation_distance'].mean():.4f} ± {condition_data['propagation_distance'].std():.4f} mm")
    
    print("\n" + "="*80)


if __name__ == "__main__":
    main()
