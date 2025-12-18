"""
Generate stiffness vs radius plot with R²-based uncertainty bands.
"""

import pandas as pd
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

sys.path.insert(0, str(Path(__file__).parent))
from stiffness_scaling_analyzer import StiffnessScalingAnalyzer

# V6 data path (OneDrive location)
v6_dir = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V6")
csv_path = v6_dir / 'MASTER_all_metrics.csv'

if not csv_path.exists():
    raise FileNotFoundError(f"MASTER CSV not found at: {csv_path}\n"
                          "Please run the V6 processor first (analyze_v6_stiffness.py)")

print(f"Loading MASTER CSV from: {csv_path}")
output_dir = v6_dir
df = pd.read_csv(csv_path)

# Rename condition_label to Condition for compatibility
if 'condition_label' in df.columns:
    df['Condition'] = df['condition_label']

print(f"Loaded {len(df)} measurements")
print(f"Conditions: {df['Condition'].unique()}")
print(f"Stiffness columns: {[col for col in df.columns if 'stiffness' in col.lower()][:5]}...")

# Create analyzer
analyzer = StiffnessScalingAnalyzer(output_dir=output_dir)

# Perform scaling analysis
print("\nAnalyzing stiffness scaling...")
results = analyzer.analyze_stiffness_scaling(df, min_r_squared=0.5)

# Generate new plot with R² bands
print("\nGenerating stiffness vs radius plot with R² uncertainty bands...")
analyzer.plot_stiffness_vs_radius_with_r2_bands(results)

print("\n✓ Complete!")
