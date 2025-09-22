"""
Test Script for Adhesion Metrics Calculator and Plotter
=======================================================

This script tests the new adhesion metrics calculator and plotter
with the autolog_L48-L50.csv file to verify the results.

Author: Cheng Sun Lab Team
Date: September 19, 2025
"""

import pandas as pd
import numpy as np
from scipy.signal import savgol_filter
import matplotlib.pyplot as plt

# Import our new modules
from adhesion_metrics_calculator import AdhesionMetricsCalculator
from adhesion_metrics_plotter import AdhesionMetricsPlotter

def test_calculator_and_plotter():
    """
    Test the calculator and plotter with real data.
    """
    print("="*80)
    print("TESTING ADHESION METRICS CALCULATOR AND PLOTTER")
    print("="*80)
    
    # Load the CSV file
    csv_file = "autolog_L48-L50.csv"
    print(f"Loading data from: {csv_file}")
    
    try:
        df = pd.read_csv(csv_file)
        print(f"Data loaded successfully: {len(df)} data points")
        print(f"Columns: {list(df.columns)}")
        
        # Check column names and standardize if needed
        if 'Elapsed Time (s)' in df.columns:
            df = df.rename(columns={'Elapsed Time (s)': 'Time'})
        if 'Position (mm)' in df.columns:
            df = df.rename(columns={'Position (mm)': 'Position'})
        if 'Force (N)' in df.columns:
            df = df.rename(columns={'Force (N)': 'Force'})
            
        print(f"Standardized columns: {list(df.columns)}")
        
        # Extract data arrays
        time_data = df['Time'].values
        position_data = df['Position'].values  
        force_data = df['Force'].values
        
        print(f"Data ranges:")
        print(f"  Time: {time_data.min():.3f} to {time_data.max():.3f} seconds")
        print(f"  Position: {position_data.min():.3f} to {position_data.max():.3f} mm")
        print(f"  Force: {force_data.min():.6f} to {force_data.max():.6f} N")
        
    except Exception as e:
        print(f"Error loading CSV file: {e}")
        return
    
    # Initialize the calculator
    print(f"\nInitializing AdhesionMetricsCalculator...")
    calculator = AdhesionMetricsCalculator(
        smoothing_window=11,
        smoothing_polyorder=2,
        baseline_threshold_factor=0.002,
        min_peak_height=0.01,
        min_peak_distance=50
    )
    
    # Apply smoothing for plotting (same as calculator uses internally)
    smoothed_force = savgol_filter(force_data, window_length=11, polyorder=2)
    
    # Method 1: Calculate metrics from the full dataset (let calculator find layers)
    print(f"\n" + "="*60)
    print("METHOD 1: FULL DATASET ANALYSIS")
    print("="*60)
    
    try:
        full_metrics = calculator.calculate_from_arrays(time_data, position_data, force_data)
        print("Full dataset metrics calculated successfully!")
        
        print(f"\nFull Dataset Results:")
        for key, value in full_metrics.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.6f}")
            else:
                print(f"  {key}: {value}")
                
    except Exception as e:
        print(f"Error calculating full dataset metrics: {e}")
        full_metrics = None
    
    # Method 2: Calculate metrics for individual layers manually
    print(f"\n" + "="*60)
    print("METHOD 2: INDIVIDUAL LAYER ANALYSIS")
    print("="*60)
    
    # We'll need to segment the data manually for now
    # Let's divide the data into roughly 3 equal time segments as a test
    total_time = time_data.max() - time_data.min()
    segment_duration = total_time / 3
    
    layer_metrics = []
    layer_numbers = [48, 49, 50]
    
    for i, layer_num in enumerate(layer_numbers):
        print(f"\nAnalyzing Layer {layer_num}...")
        
        # Define time segment for this layer
        start_time = time_data.min() + i * segment_duration
        end_time = time_data.min() + (i + 1) * segment_duration
        
        # Extract segment data
        segment_mask = (time_data >= start_time) & (time_data <= end_time)
        segment_time = time_data[segment_mask] - time_data[segment_mask][0]  # Reset to start at 0
        segment_position = position_data[segment_mask]
        segment_force = force_data[segment_mask]
        
        print(f"  Time segment: {start_time:.2f} to {end_time:.2f} seconds")
        print(f"  Data points: {len(segment_time)}")
        
        if len(segment_time) < 20:
            print(f"  WARNING: Not enough data points for layer {layer_num}")
            continue
            
        try:
            # Calculate metrics for this segment
            metrics = calculator.calculate_from_arrays(
                segment_time, segment_position, segment_force, layer_number=layer_num
            )
            
            layer_metrics.append(metrics)
            
            print(f"  Layer {layer_num} Results:")
            print(f"    Peak Force: {metrics['peak_force']:.6f} N")
            print(f"    Baseline Force: {metrics['baseline_force']:.6f} N")
            print(f"    Peak Force (Corrected): {metrics['peak_force_corrected']:.6f} N")
            print(f"    Work of Adhesion: {metrics['work_of_adhesion_mJ']:.3f} mJ")
            print(f"    Work (Corrected): {metrics['work_of_adhesion_corrected_mJ']:.3f} mJ")
            print(f"    Pre-initiation Duration: {metrics['pre_initiation_duration']:.3f} s")
            print(f"    Propagation Duration: {metrics['propagation_duration']:.3f} s")
            print(f"    SNR: {metrics['signal_to_noise_ratio']:.2f}")
            
        except Exception as e:
            print(f"  Error calculating metrics for layer {layer_num}: {e}")
            import traceback
            traceback.print_exc()
    
    # Test the plotter if we have metrics
    if layer_metrics:
        print(f"\n" + "="*60)
        print("TESTING PLOTTER")
        print("="*60)
        
        try:
            # Initialize plotter
            plotter = AdhesionMetricsPlotter()
            
            # Print metrics summary
            plotter.print_metrics_summary(layer_metrics)
            
            # Create comprehensive plot
            print(f"\nCreating comprehensive analysis plot...")
            fig = plotter.plot_comprehensive_analysis(
                time_data, force_data, smoothed_force, layer_metrics,
                title="L48-L50 Test Analysis",
                save_path="test_L48_L50_analysis.png"
            )
            
            # Create overview plot
            print(f"Creating overview plot...")
            fig_overview = plotter.plot_overview_only(
                time_data, force_data, smoothed_force, layer_metrics,
                title="L48-L50 Force Overview",
                save_path="test_L48_L50_overview.png"
            )
            
            # Create single layer plot for first layer
            if layer_metrics:
                print(f"Creating single layer plot for Layer {layer_metrics[0]['layer_number']}...")
                fig_single = plotter.plot_single_layer(
                    time_data, force_data, smoothed_force, layer_metrics[0],
                    title=f"Layer {layer_metrics[0]['layer_number']} Detailed Analysis",
                    save_path=f"test_L{layer_metrics[0]['layer_number']}_single.png"
                )
            
            print(f"\nPlots created successfully!")
            
        except Exception as e:
            print(f"Error creating plots: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"\nNo layer metrics available for plotting.")
    
    # Method 3: Test with DataFrame method
    print(f"\n" + "="*60)
    print("METHOD 3: DATAFRAME METHOD TEST")
    print("="*60)
    
    try:
        df_metrics = calculator.calculate_from_dataframe(df, layer_number=999)
        print("DataFrame method successful!")
        
        print(f"\nDataFrame Method Results:")
        for key, value in df_metrics.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.6f}")
            else:
                print(f"  {key}: {value}")
                
    except Exception as e:
        print(f"Error with DataFrame method: {e}")
    
    # Method 4: Test CSV method directly
    print(f"\n" + "="*60)
    print("METHOD 4: CSV METHOD TEST")
    print("="*60)
    
    try:
        csv_metrics = calculator.calculate_from_csv(csv_file, layer_number=888)
        print("CSV method successful!")
        
        print(f"\nCSV Method Results:")
        for key, value in csv_metrics.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.6f}")
            else:
                print(f"  {key}: {value}")
                
    except Exception as e:
        print(f"Error with CSV method: {e}")
    
    print(f"\n" + "="*80)
    print("TESTING COMPLETE")
    print("="*80)
    
    return layer_metrics

if __name__ == "__main__":
    layer_metrics = test_calculator_and_plotter()
    
    if layer_metrics:
        print(f"\nSUCCESS: Calculated metrics for {len(layer_metrics)} layers")
        print("Check the generated PNG files for visualization results.")
    else:
        print(f"\nWARNING: No layer metrics were successfully calculated.")
        print("Check the error messages above for debugging information.")
