"""Quick test of the updated plotter without arrows"""
import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, 'post-processing')
sys.path.insert(0, 'support_modules')

from RawData_Processor import RawDataProcessor
from adhesion_metrics_calculator import AdhesionMetricsCalculator
from analysis_plotter import AnalysisPlotter

# File to test
test_file = r'C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V2\2p5PEO_1mm_SteppedCone_BPAGDA_1000\autolog_L100-L105.csv'
output_plot = r'C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V2\2p5PEO_1mm_SteppedCone_BPAGDA_1000\plots\TEST_updated_plot.png'

# Initialize
calc = AdhesionMetricsCalculator()
proc = RawDataProcessor(calc)
plotter = AnalysisPlotter(figure_size=(16, 12), dpi=150)

# Process
layers = proc.process_csv(test_file)
print(f"\n✓ Processed {len(layers)} layers")

# Load raw data for plotting
df = pd.read_csv(test_file)
time_data = df['Elapsed Time (s)'].to_numpy()
force_data = df['Force (N)'].to_numpy()
smoothed_force = calc._apply_smoothing(force_data)

# Generate plot
plotter.create_plot(
    time_data=time_data,
    force_data=force_data,
    smoothed_force=smoothed_force,
    layers=layers,
    title="TEST - Updated Plotter (No Arrows)",
    save_path=output_plot
)

print(f"\n✓ Plot saved to: {output_plot}")
print("\nPlease check the plot to verify:")
print("  1. NO horizontal arrows for durations")
print("  2. Labels contained within plot area")
print("  3. Shaded regions for pre-initiation and propagation")
print("  4. Duration info in subplot titles")
