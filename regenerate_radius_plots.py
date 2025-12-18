"""
Regenerate radius plots with corrected area binning
"""
import sys
from pathlib import Path

# Add paths
sys.path.insert(0, 'batch_processors')
sys.path.insert(0, 'post-processing')

from master_plotter import MasterPlotter
import pandas as pd

# Load V6 data
v6_dir = Path(r'C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V6')
csv_path = v6_dir / 'MASTER_all_metrics.csv'

print(f"Loading data from: {csv_path}")
df = pd.read_csv(csv_path)

# Create detailed_condition if needed
if 'detailed_condition' not in df.columns:
    df['detailed_condition'] = df['membrane_type'] + ' + ' + df['tank_type']

print(f"Loaded {len(df)} measurements")
print(f"Area range: {df['area_mm2'].min():.2f} to {df['area_mm2'].max():.2f} mm²")

# Create plotter and regenerate radius plots
plotter = MasterPlotter(output_directory=str(v6_dir), dpi=300)
print("\nRegenerating radius plots with corrected area binning...")
plotter.generate_standard_radius_plots(df)

print("\n✓ Radius plots regenerated successfully!")
