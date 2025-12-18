"""
Simple script to process old data and generate metrics CSV
"""
import sys
sys.path.insert(0, '..')
from pathlib import Path
import pandas as pd

# Import from support_modules in parent directory
from support_modules.adhesion_metrics_calculator import AdhesionMetricsCalculator
# Import from post-processing directory
from analysis_plotter import AnalysisPlotter  
from RawData_Processor import RawDataProcessor

folder_path = sys.argv[1] if len(sys.argv) > 1 else None

if not folder_path:
    print("Usage: python process_old_data.py <folder_path>")
    sys.exit(1)

folder = Path(folder_path)

# Initialize components
calc = AdhesionMetricsCalculator(
    median_kernel=5,
    savgol_window=9,
    savgol_order=2,
    baseline_threshold_factor=0.002,
    min_peak_height=0.01,
    min_peak_distance=50
)
processor = RawDataProcessor(calc)

# Load LayerToArea mapping
layer_to_area_file = folder / 'LayerToArea.txt'
layer_to_area = {}
if layer_to_area_file.exists():
    with open(layer_to_area_file, 'r') as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                parts = line.strip().split()
                if len(parts) >= 2:
                    try:
                        layer = int(parts[0])
                        area = float(parts[1])
                        layer_to_area[layer] = area
                    except:
                        pass
    print(f'Loaded area mappings for {len(layer_to_area)} layers')

# Process all CSV files
all_results = []
csv_files = sorted(folder.glob('autolog_*.csv'))

print(f'\nProcessing {len(csv_files)} files...')

for csv_file in csv_files:
    print(f'  {csv_file.name}')
    try:
        layers = processor.process_csv(str(csv_file))
        if layers:
            # Add area information to each layer
            for layer in layers:
                layer_num = layer.get('layer_number', 0)
                if layer_num in layer_to_area:
                    layer['area_mm2'] = layer_to_area[layer_num]
                else:
                    layer['area_mm2'] = None
            
            all_results.extend(layers)
            print(f'    -> {len(layers)} measurements')
    except Exception as e:
        print(f'    ERROR: {e}')
        import traceback
        traceback.print_exc()

# Save to CSV
if all_results:
    df = pd.DataFrame(all_results)
    output_path = folder / 'automated_work_of_adhesion.csv'
    df.to_csv(output_path, index=False)
    
    print(f'\n✓ Saved {len(df)} measurements to {output_path.name}')
    print(f'  Columns: {list(df.columns)[:10]}...')
    layer_col = 'number' if 'number' in df.columns else 'layer_number'
    if layer_col in df.columns:
        print(f'  Layer range: {df[layer_col].min():.0f} - {df[layer_col].max():.0f}')
    if 'area_mm2' in df.columns:
        valid_areas = df['area_mm2'].dropna()
        if len(valid_areas) > 0:
            print(f'  Area range: {valid_areas.min():.2f} - {valid_areas.max():.2f} mm²')
else:
    print('\nERROR: No results generated!')
