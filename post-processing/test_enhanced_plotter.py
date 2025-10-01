"""
Test script for the enhanced plotting system
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
from RawData_Processor import RawDataProcessor
from enhanced_layer_plotter import EnhancedLayerPlotter
from adhesion_metrics_calculator import AdhesionMetricsCalculator

# Create the components
calculator = AdhesionMetricsCalculator(
    smoothing_sigma=0.5,
    baseline_threshold_factor=0.002,
    min_peak_height=0.01,
    min_peak_distance=50
)
plotter = EnhancedLayerPlotter()
processor = RawDataProcessor(calculator, plotter)

# Process test file
test_file = "autolog_L48-L50.csv"
output_file = "enhanced_analysis_L48_L50.png"

print(f"Processing file: {test_file}")
processor.process_csv(test_file, title="Enhanced Analysis L48-L50", save_path=output_file)