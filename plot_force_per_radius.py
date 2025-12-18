"""
Generate Force/Radius vs Radius Master Plot
============================================

Creates a plot showing Force/Radius (N/mm) vs Contact Radius (mm)
to analyze edge effects and scaling behavior.
"""

import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent / 'post-processing'))
from master_plotter import MasterPlotter

V6_DIR = Path(r'C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V6')

print("Loading data...")
df = pd.read_csv(V6_DIR / 'MASTER_all_metrics.csv')
print(f"Loaded {len(df)} measurements")

print("\nGenerating Force/Radius plot...")
plotter = MasterPlotter(output_directory=str(V6_DIR), dpi=300)
output_path = plotter.generate_force_per_radius_plot(df)

print(f"\nDone! Plot saved to:\n{output_path}")
print("\nThis plot shows how Force/Radius changes with part size:")
print("  • If F/r is constant → Force scales with perimeter (edge effect)")
print("  • If F/r increases → Bulk adhesion dominates at larger sizes")
print("  • If F/r decreases → Edge effects more important at small sizes")
