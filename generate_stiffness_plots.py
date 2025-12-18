"""
Generate Stiffness Scaling Plots from Existing CSV
"""
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent / 'post-processing'))
from stiffness_scaling_analyzer import StiffnessScalingAnalyzer

V6_DIR = Path(r'C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V6')

print("Loading CSV...")
df = pd.read_csv(V6_DIR / 'MASTER_all_metrics.csv')
print(f"Loaded {len(df)} measurements")

print("\nPerforming scaling analysis...")
analyzer = StiffnessScalingAnalyzer(output_dir=str(V6_DIR))
results = analyzer.analyze_stiffness_scaling(df, min_r_squared=0.5)

print("\nGenerating plots...")
analyzer.plot_stiffness_vs_area(results)
analyzer.plot_stiffness_vs_radius(results)
analyzer.generate_summary_report(results)

print("\nDone!")
