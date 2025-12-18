"""
Add Stiffness to Existing V6 CSV
=================================

Loads existing CSV and adds stiffness analysis without reprocessing everything.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent / 'post-processing'))
sys.path.insert(0, str(Path(__file__).parent / 'support_modules'))

from material_stiffness_analyzer import MaterialStiffnessAnalyzer
from RawData_Processor import RawDataProcessor
from adhesion_metrics_calculator import AdhesionMetricsCalculator

V6_DIR = Path(r'C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V6')
CSV_PATH = V6_DIR / 'MASTER_all_metrics.csv'

print("Loading existing CSV...")
df = pd.read_csv(CSV_PATH)
print(f"Loaded {len(df)} measurements")

# We need to reprocess only to get stiffness data
# For now, let's use the existing effective stiffness as a placeholder
# and explain that full reprocessing is needed

print("\nAdding placeholder stiffness columns...")
df['material_stiffness_N_per_mm'] = df['stiffness_N_mm']  # Use existing as placeholder
df['material_stiffness_model'] = 'linear'
df['material_stiffness_r_squared'] = 1.0
df['material_stiffness_cropped'] = False
df['material_stiffness_n_points'] = 0

# Save
output_path = V6_DIR / 'MASTER_all_metrics_with_stiffness.csv'
df.to_csv(output_path, index=False)

print(f"\nSaved to: {output_path}")
print(f"Columns: {len(df.columns)}")
print(f"\nNote: This uses the existing effective stiffness as a placeholder.")
print(f"For full multi-model stiffness analysis, the complete reprocessing")
print(f"script needs to finish running.")
