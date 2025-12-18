"""
Plot comparison of PDMS p2 vs TEMPO p3
"""
from master_plotter import MasterPlotter
import pandas as pd
from pathlib import Path

# Load data
v5_dir = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V5")
df = pd.read_csv(v5_dir / 'MASTER_V5_all_metrics.csv')

# Filter to only PDMS p2 and TEMPO p3
df_filtered = df[df['detailed_condition'].isin(['PDMS, 100um + TankV22p2', 'TEMPO + TankV22p3'])]
print(f'\nFiltered to {len(df_filtered)} rows')
print(f'Conditions: {list(df_filtered["detailed_condition"].unique())}')

# Create plotter
plotter = MasterPlotter(v5_dir)

# Generate plots
print("\nGenerating comparison plots...")

# 1. Area analysis
plotter.generate_area_analysis_plot(
    df_filtered, 
    [
        ('peak_force_N', 'Peak Force (N)'), 
        ('work_of_adhesion_mJ', 'Work of Adhesion (mJ)'), 
        ('pre_initiation_distance_mm', 'Pre-Initiation Distance (mm)'), 
        ('total_peel_time_s', 'Total Peel Time (s)')
    ], 
    'MASTER_area_analysis_PDMSp2_TEMPOp3.png', 
    'Master Area Analysis (PDMS p2 vs TEMPO p3)', 
    apply_abs=['pre_initiation_distance_mm']
)

# 2. Area ratio analysis
plotter.generate_area_ratio_analysis_plot(
    df_filtered, 
    'MASTER_area_ratio_analysis_PDMSp2_TEMPOp3.png'
)

# 3. Distance analysis
plotter.generate_distance_analysis_plot(
    df_filtered, 
    'MASTER_distance_analysis_PDMSp2_TEMPOp3.png'
)

print("\nComparison plots complete!")
