#!/usr/bin/env python3
"""
Quick test of the new plotting style
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks, savgol_filter
import warnings
warnings.filterwarnings('ignore')

# Test with one file
csv_path = r"C:\Users\cheng sun\BoyuanSun\Slicing\Evan\5mmDiameterCylinder_SpeedTest_V3\Printing_Logs\DataToExport\BPAGDA_5mm_2p5PEO_Constant\autolog_L148-L150.csv"

try:
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} data points")
    
    # Standardize column names
    if 'Elapsed Time (s)' in df.columns:
        df = df.rename(columns={'Elapsed Time (s)': 'Time'})
    if 'Position (mm)' in df.columns:
        df = df.rename(columns={'Position (mm)': 'Position'})
    if 'Force (N)' in df.columns:
        df = df.rename(columns={'Force (N)': 'Force'})
    
    # Simple peak detection
    smoothed_force = savgol_filter(df['Force'].values, window_length=11, polyorder=2)
    peaks, _ = find_peaks(smoothed_force, height=0.01, distance=150, prominence=0.005)
    
    print(f"Found {len(peaks)} peaks")
    
    if len(peaks) >= 3:
        # Test the figure style - just one subplot to verify shaded regions work
        fig, ax = plt.subplots(1, 1, figsize=(12, 8))
        
        # Plot the data
        ax.plot(df['Time'], df['Force'], 'k-', linewidth=1, alpha=0.4, label='Raw Force')
        ax.plot(df['Time'], smoothed_force, 'red', linewidth=3, alpha=0.9, label='Smoothed Force')
        
        # Simple timing analysis for first peak
        peak_idx = peaks[0]
        peak_time = df['Time'].iloc[peak_idx]
        peak_force = df['Force'].iloc[peak_idx]
        
        # Simple pre-initiation and propagation estimates
        pre_init_time = peak_time - 1.0  # 1 second before peak
        prop_end_time = peak_time + 1.0  # 1 second after peak
        
        # Add shaded regions - exact style from final_layer_visualization
        ax.axvspan(pre_init_time, peak_time, color='lightblue', alpha=0.5, label='Pre-Initiation', zorder=1)
        ax.axvspan(peak_time, prop_end_time, color='lightcoral', alpha=0.5, label='Propagation', zorder=1)
        
        # Add peak marker
        ax.plot(peak_time, peak_force, 'o', color='red', markersize=14, zorder=5, 
                markeredgecolor='black', markeredgewidth=2, label=f'Peak: {peak_force:.4f}N')
        
        # Add vertical lines
        ax.axvline(x=peak_time, color='red', linestyle='--', linewidth=4, zorder=4)
        ax.axvline(x=prop_end_time, color='purple', linestyle=':', linewidth=4, zorder=4)
        
        ax.set_xlabel('Time (s)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Force (N)', fontsize=12, fontweight='bold')
        ax.set_title('Test: Layer 148 - Peeling Stages with Shaded Bands', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=12)
        
        # Save test plot
        test_output = 'test_shaded_regions_L148.png'
        plt.savefig(test_output, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        print(f"Test plot saved as: {test_output}")
        print("✅ Shaded regions plotting style verified!")
    else:
        print("Not enough peaks detected for testing")
        
except Exception as e:
    print(f"Error in test: {e}")
    import traceback
    traceback.print_exc()
