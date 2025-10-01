import sys
import os

# Add the workspace directory to the Python path
workspace_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, workspace_dir)

import unittest
from unittest.mock import MagicMock, patch
from support_modules.SensorDataWindow import SensorDataWindow
from support_modules.adhesion_metrics_calculator import AdhesionMetricsCalculator
import numpy as np
import pandas as pd

class TestSensorDataWindow(unittest.TestCase):

    def setUp(self):
        # Mock dependencies
        self.mock_update_main_status = MagicMock()
        self.mock_on_print_start = MagicMock()
        self.mock_master_window = MagicMock()
        self.mock_zaber_axis_ref = MagicMock()
        self.mock_main_app_status_callback = MagicMock()
        self.mock_prince_main_app_ref = MagicMock()

        # Initialize SensorDataWindow with mocked methods
        self.sensor_data_window = SensorDataWindow(
            master_window=self.mock_master_window,
            zaber_axis_ref=self.mock_zaber_axis_ref,
            main_app_status_callback=self.mock_main_app_status_callback,
            prince_main_app_ref=self.mock_prince_main_app_ref
        )
        self.sensor_data_window.update_main_status = self.mock_update_main_status
        self.sensor_data_window.on_print_start = self.mock_on_print_start

        # Mock attributes
        self.sensor_data_window.image_list = []
        self.sensor_data_window.automated_peak_force_logger = MagicMock()

        # Initialize AdhesionMetricsCalculator
        self.calculator = AdhesionMetricsCalculator()

    def test_monitoring_not_started_without_layers(self):
        """Test that monitoring does not start if no layers are defined."""
        self.sensor_data_window.on_print_start()
        self.mock_update_main_status.assert_called_with(
            "Error: No layers defined. Cannot start monitoring.", error=True
        )
        self.sensor_data_window.automated_peak_force_logger.start_monitoring_for_layer.assert_not_called()

    def test_monitoring_starts_with_layers(self):
        """Test that monitoring starts correctly when layers are defined."""
        self.sensor_data_window.image_list = ["Layer1", "Layer2"]

        self.sensor_data_window.on_print_start()

        self.sensor_data_window.automated_peak_force_logger.start_monitoring_for_layer.assert_called_once_with(
            1, z_peel_peak=1.0, z_return_pos=3.0
        )
        self.mock_update_main_status.assert_called_with(
            "Automated peak force monitoring started for initial layer."
        )

    def test_find_pre_initiation(self):
        """Test the _find_pre_initiation method with mock data."""
        smoothed_force = np.array([0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.1])
        peak_idx = 9
        baseline = 0.02

        # Call the method
        pre_init_idx = self.calculator._find_pre_initiation(smoothed_force, peak_idx, baseline)

        # Validate the result
        self.assertIsInstance(pre_init_idx, int)
        self.assertGreaterEqual(pre_init_idx, 0)
        self.assertLess(pre_init_idx, peak_idx)

    def test_calculate_metrics(self):
        """Test the _calculate_metrics method with mock data."""
        times = np.linspace(0, 1, 10)
        positions = np.linspace(0, 5, 10)
        forces = np.linspace(0, 0.1, 10)
        smoothed_force = np.linspace(0, 0.1, 10)
        layer_number = 1
        motion_end_idx = 9

        # Call the method
        metrics = self.calculator._calculate_metrics(times, positions, forces, smoothed_force, layer_number, motion_end_idx)

        # Validate the result
        self.assertIsInstance(metrics, dict)
        self.assertIn('pre_initiation_distance', metrics)
        self.assertIn('pre_initiation_duration', metrics)

    def test_find_pre_initiation_with_csv(self):
        """Test the _find_pre_initiation method using data from a CSV file."""
        # Load the dataset
        data = pd.read_csv("c:\\Users\\cheng sun\\BoyuanSun\\Prince_Segmented_20250926\\archive\\autolog_L48.csv")
        smoothed_force = data['Force (N)'].values
        peak_idx = len(smoothed_force) - 1  # Assume the last point is the peak for simplicity
        baseline = smoothed_force.min()  # Use the minimum force as the baseline

        # Call the method
        pre_init_idx = self.calculator._find_pre_initiation(smoothed_force, peak_idx, baseline)

        # Log the results
        print(f"Pre-initiation index: {pre_init_idx}")
        print(f"Pre-initiation force: {smoothed_force[pre_init_idx]}")

        # Validate the result
        self.assertIsInstance(pre_init_idx, int)
        self.assertGreaterEqual(pre_init_idx, 0)
        self.assertLess(pre_init_idx, peak_idx)

    def test_calculate_metrics_with_csv(self):
        """Test the _calculate_metrics method using data from a CSV file."""
        # Load the dataset
        data = pd.read_csv("c:\\Users\\cheng sun\\BoyuanSun\\Prince_Segmented_20250926\\archive\\autolog_L48.csv")
        times = data['Elapsed Time (s)'].values
        positions = data['Position (mm)'].values
        forces = data['Force (N)'].values
        smoothed_force = forces  # Assume forces are already smoothed
        layer_number = 1
        motion_end_idx = len(times) - 1

        # Call the method
        metrics = self.calculator._calculate_metrics(times, positions, forces, smoothed_force, layer_number, motion_end_idx)

        # Log the results
        print("Metrics:")
        for key, value in metrics.items():
            print(f"{key}: {value}")

        # Validate the result
        self.assertIsInstance(metrics, dict)
        self.assertIn('pre_initiation_distance', metrics)
        self.assertIn('pre_initiation_duration', metrics)

if __name__ == "__main__":
    unittest.main()