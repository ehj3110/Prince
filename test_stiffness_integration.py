"""
Quick Stiffness Test - Single Folder
=====================================

Tests stiffness calculation on a single ACF folder to verify integration.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Add paths
sys.path.insert(0, str(Path(__file__).parent / 'support_modules'))
sys.path.insert(0, str(Path(__file__).parent / 'post-processing'))

from adhesion_metrics_calculator import AdhesionMetricsCalculator
from RawData_Processor import RawDataProcessor
from material_stiffness_analyzer import MaterialStiffnessAnalyzer

# Test on one file
TEST_FILE = Path(r'C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V6\ACF_5mm_V19_Cone_BPAGDA_200\autolog_L100-L105.csv')

def main():
    print("="*70)
    print("QUICK STIFFNESS INTEGRATION TEST")
    print("="*70)
    
    if not TEST_FILE.exists():
        print(f"\nERROR: Test file not found: {TEST_FILE}")
        return
    
    print(f"\nTest file: {TEST_FILE.name}")
    
    # Initialize
    calculator = AdhesionMetricsCalculator()
    processor = RawDataProcessor(calculator)
    stiffness_analyzer = MaterialStiffnessAnalyzer()
    
    # Load data
    print("\nLoading data...")
    df = pd.read_csv(TEST_FILE)
    time_data = df['Elapsed Time (s)'].to_numpy()
    force_data = df['Force (N)'].to_numpy()
    position_data = df['Position (mm)'].to_numpy()
    
    print(f"  Data points: {len(df)}")
    print(f"  Time range: {time_data[0]:.2f} - {time_data[-1]:.2f} s")
    print(f"  Force range: {force_data.min():.4f} - {force_data.max():.4f} N")
    print(f"  Position range: {position_data.min():.2f} - {position_data.max():.2f} mm")
    
    # Process layers
    print("\nProcessing layers...")
    layers = processor.process_csv(str(TEST_FILE))
    
    if not layers:
        print("ERROR: No layers detected")
        return
    
    print(f"  Detected {len(layers)} layers")
    
    # Test stiffness on first layer
    layer = layers[0]
    layer_num = layer['number']
    
    print(f"\nTesting stiffness on Layer {layer_num}...")
    
    # Extract indices
    lifting_start = layer['start_idx']
    lifting_end = layer['end_idx']
    pre_init_idx = layer.get('pre_init_idx', lifting_start)
    peak_idx = layer.get('peak_idx', lifting_start)
    
    print(f"  Lifting: {lifting_start} - {lifting_end}")
    print(f"  Pre-init: {pre_init_idx}")
    print(f"  Peak: {peak_idx}")
    
    # Extract data
    lifting_disp = position_data[lifting_start:lifting_end+1]
    lifting_force = force_data[lifting_start:lifting_end+1]
    
    print(f"  Data points in segment: {len(lifting_disp)}")
    
    # Calculate stiffness
    print("\nCalculating stiffness...")
    stiffness_result = stiffness_analyzer.analyze_stiffness(
        displacement=lifting_disp,
        force=lifting_force,
        baseline_idx=pre_init_idx - lifting_start,
        peak_idx=peak_idx - lifting_start,
        auto_crop=True
    )
    
    # Display results
    print("\n" + "="*70)
    print("STIFFNESS RESULTS")
    print("="*70)
    
    print(f"\nData Cropping:")
    print(f"  Cropped: {stiffness_result['cropped']}")
    print(f"  Info: {stiffness_result['crop_info']}")
    print(f"  Points used: {stiffness_result['n_points_used']}")
    
    print(f"\nBest Fit:")
    print(f"  Model: {stiffness_result['best_model']}")
    print(f"  Stiffness: {stiffness_result['best_stiffness_N_per_mm']:.4f} N/mm")
    print(f"  R²: {stiffness_result['best_r_squared']:.4f}")
    
    print(f"\nAll Models:")
    for model in ['linear', 'exponential', 'logarithmic', 'power_law']:
        result = stiffness_result[model]
        if result['success']:
            print(f"  {model.capitalize()}: k = {result['stiffness_N_per_mm']:.4f} N/mm (R² = {result['r_squared']:.4f})")
        else:
            print(f"  {model.capitalize()}: FAILED - {result.get('error', 'Unknown error')}")
    
    print("\n" + "="*70)
    print("TEST COMPLETE - Integration Working!")
    print("="*70)

if __name__ == "__main__":
    main()
