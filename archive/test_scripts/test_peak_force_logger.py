import sys
import os

# Add the `support_modules` directory to the Python path
support_modules_dir = os.path.join(os.path.dirname(__file__), 'support_modules')
if support_modules_dir not in sys.path:
    sys.path.insert(0, support_modules_dir)

import unittest
import csv
from support_modules.PeakForceLogger import PeakForceLogger

class TestPeakForceLogger(unittest.TestCase):

    def setUp(self):
        # Temporary output file for testing
        self.test_output_csv = "test_peak_force_logger_output.csv"
        
        # Initialize PeakForceLogger
        self.logger = PeakForceLogger(
            output_csv_filepath=self.test_output_csv,
            is_manual_log=False,
            use_corrected_calculator=True
        )

    def tearDown(self):
        # Clean up the test output file
        if os.path.exists(self.test_output_csv):
            os.remove(self.test_output_csv)

    def test_logger_with_csv_data(self):
        # Path to the provided CSV file
        input_csv = "c:\\Users\\cheng sun\\BoyuanSun\\Prince_Segmented_20250926\\archive\\autolog_L48-L50.csv"

        # Read data from the input CSV file
        timestamps, positions, forces = [], [], []
        with open(input_csv, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                timestamps.append(float(row['Elapsed Time (s)']))
                positions.append(float(row['Position (mm)']))
                forces.append(float(row['Force (N)']))

        # Debugging: Print the processed data
        print("DEBUG: Timestamps:", timestamps)
        print("DEBUG: Positions:", positions)
        print("DEBUG: Forces:", forces)

        # Start monitoring for layer 1
        self.logger.start_monitoring_for_layer(1, z_peel_peak=10.0, z_return_pos=12.0)

        # Simulate adding data points to the logger
        for t, p, f in zip(timestamps, positions, forces):
            self.logger.add_data_point(t, p, f)

        # Stop monitoring and log the results
        success = self.logger.stop_monitoring_and_log_peak()

        # Verify that the logging was successful
        self.assertTrue(success, "PeakForceLogger failed to log data.")

        # Verify that the output CSV file was created
        self.assertTrue(os.path.exists(self.test_output_csv), "Output CSV file was not created.")

        # Verify the contents of the output CSV file
        with open(self.test_output_csv, 'r') as f:
            lines = f.readlines()
            self.assertGreater(len(lines), 1, "Output CSV file is empty.")

if __name__ == "__main__":
    unittest.main()