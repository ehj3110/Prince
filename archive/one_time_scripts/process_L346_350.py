"""Process L346-350 autolog file and append to FEP automated_work_of_adhesion.csv"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent / 'support_modules'))
sys.path.insert(0, str(Path(__file__).parent / 'post-processing'))
from adhesion_metrics_calculator import AdhesionMetricsCalculator
from RawData_Processor import RawDataProcessor

# Path to autolog file
autolog_file = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\Presentation data\Final\FEP\autolog_L346-L350.csv")
output_csv = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\Presentation data\Final\FEP\automated_work_of_adhesion.csv")

# Initialize calculator
calculator = AdhesionMetricsCalculator(skip_initial_distance_um=200)
processor = RawDataProcessor(calculator)

print(f"Processing: {autolog_file.name}")

# Process the file
all_results = []
layer_numbers = []

try:
    # Load autolog CSV
    df_raw = pd.read_csv(autolog_file)
    
    # Process data
    results = processor.process_csv(str(autolog_file))
    
    for layer_num, metrics in results.items():
        layer_numbers.append(layer_num)
        all_results.append(metrics)
        print(f"  Layer {layer_num}: Peak force = {metrics.get('Peak_Force_N', 0):.4f} N")
    
    # Create DataFrame
    new_df = pd.DataFrame(all_results)
    new_df['Layer_Number'] = layer_numbers
    new_df['source_file'] = autolog_file.name
    
    # Add cross-sectional area for r=5.64mm (area = 100 mm²)
    new_df['Cross_Sectional_Area_mm2'] = 100.0
    
    print(f"\nProcessed {len(new_df)} layers")
    print(f"Cross-sectional area: {new_df['Cross_Sectional_Area_mm2'].iloc[0]:.2f} mm²")
    
    # Load existing data
    existing_df = pd.read_csv(output_csv)
    print(f"Existing data: {len(existing_df)} layers")
    
    # Append new data
    combined_df = pd.concat([existing_df, new_df], ignore_index=True)
    print(f"Combined data: {len(combined_df)} layers")
    
    # Save
    combined_df.to_csv(output_csv, index=False)
    print(f"\n[OK] Saved to: {output_csv}")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
