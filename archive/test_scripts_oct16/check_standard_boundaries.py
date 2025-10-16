"""
Test boundary detection on standard (non-sandwich) data
"""
import sys
import os
import pandas as pd
import numpy as np

# Add support_modules to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'post-processing'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'support_modules'))

from RawData_Processor import RawDataProcessor
from adhesion_metrics_calculator import AdhesionMetricsCalculator

# Test on standard data (no sandwich)
csv_file = 'post-processing/autolog_L48-L50.csv'

print(f"Testing standard data: {csv_file}\n")

# Initialize processor
calc = AdhesionMetricsCalculator()
processor = RawDataProcessor(calc)

# Process the file
processor.process_csv(csv_file)

# Check layers
print(f"\n{'='*60}")
print(f"Processing Results:")
print(f"{'='*60}")

for i, layer in enumerate(processor.layers):
    metrics = layer['metrics']
    print(f"\n--- Layer {metrics.get('layer_number', i+1)} ---")
    print(f"  Peak adhesion force: {metrics.get('peak_force', 0):.4f} N")
    print(f"  Pre-initiation time: {metrics.get('pre_initiation_time', 0):.4f} s")
    print(f"  Propagation time: {metrics.get('propagation_time', 0):.4f} s")
