"""
Generate individual force-distance plots for Hybrid - Compliant folder
"""

import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import sys

sys.path.insert(0, str(Path(__file__).parent / 'support_modules'))
sys.path.insert(0, str(Path(__file__).parent / 'post-processing'))
from adhesion_metrics_calculator import AdhesionMetricsCalculator
from RawData_Processor import RawDataProcessor

# Set Times New Roman font
plt.rcParams['font.family'] = 'Times New Roman'
plt.rcParams['font.size'] = 12

folder_path = Path(r'C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\Presentation data\Final\Hybrid - Compliant')
output_dir = folder_path / 'plots'
output_dir.mkdir(exist_ok=True)

print("="*80)
print("GENERATING INDIVIDUAL PLOTS FOR HYBRID - COMPLIANT")
print("="*80)
print(f"Output directory: {output_dir}")

# Initialize with 500um skip
calculator = AdhesionMetricsCalculator(skip_initial_distance_um=500)
processor = RawDataProcessor(calculator)

autolog_files = sorted(folder_path.glob('autolog_*.csv'))
print(f'Found {len(autolog_files)} autolog files')

for autolog_file in autolog_files:
    print(f"\nProcessing: {autolog_file.name}")
    
    # Read raw data
    raw_df = pd.read_csv(autolog_file)
    
    # Determine displacement column name
    if 'Displacement (mm)' in raw_df.columns:
        disp_col = 'Displacement (mm)'
    elif 'Position (mm)' in raw_df.columns:
        disp_col = 'Position (mm)'
    else:
        print(f"  [X] Missing displacement/position column")
        continue
    
    if 'Force (N)' not in raw_df.columns:
        print(f"  [X] Missing Force (N) column")
        continue
    
    # Create plot
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Plot force vs displacement
    ax.plot(raw_df[disp_col], raw_df['Force (N)'], 'b-', linewidth=0.5, alpha=0.8)
    
    ax.set_xlabel('Position (mm)', fontsize=14)
    ax.set_ylabel('Force (N)', fontsize=14)
    ax.set_title(f'Force-Position: {autolog_file.name}', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    # Add vertical line at 500um (0.5mm) to show skip region
    if raw_df[disp_col].min() < 0.5:
        ax.axvline(x=0.5, color='r', linestyle='--', linewidth=1, label='500µm skip boundary')
        ax.legend(loc='best')
    
    plt.tight_layout()
    
    # Save plot
    plot_path = output_dir / f'{autolog_file.stem}_plot.png'
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"  [OK] Saved: {plot_path.name}")

print("\n" + "="*80)
print(f"Generated {len(autolog_files)} individual plots in {output_dir}")
