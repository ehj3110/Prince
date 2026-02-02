"""
Unit tests for AdhesionMetricsCalculator

Tests adhesion metrics calculation including:
- Force smoothing
- Peak detection
- Work of adhesion calculation
- Baseline detection
- Edge case handling
"""

import unittest
import sys
import numpy as np
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from support_modules.adhesion_metrics_calculator import AdhesionMetricsCalculator


class TestAdhesionMetricsCalculator(unittest.TestCase):
    """Test cases for AdhesionMetricsCalculator"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.calculator = AdhesionMetricsCalculator(
            median_kernel=5,
            savgol_window=9,
            savgol_order=2,
            baseline_threshold_factor=0.002,
            min_peak_height=0.01,
            min_peak_distance=50
        )
    
    def test_initialization(self):
        """Test calculator initialization"""
        self.assertIsNotNone(self.calculator)
        self.assertEqual(self.calculator.median_kernel, 5)
        self.assertEqual(self.calculator.savgol_window, 9)
        self.assertEqual(self.calculator.savgol_order, 2)
    
    def test_initialization_ensures_odd_kernel(self):
        """Test that kernel sizes are forced to be odd"""
        calc = AdhesionMetricsCalculator(median_kernel=4, savgol_window=8)
        self.assertEqual(calc.median_kernel, 5)  # Should be rounded up
        self.assertEqual(calc.savgol_window, 9)  # Should be rounded up
    
    def test_calculate_from_arrays_simple_peak(self):
        """Test calculation with simple synthetic peak data"""
        # Create synthetic data with a clear peak
        n_points = 200
        time_data = np.linspace(0, 2, n_points)  # 2 seconds
        position_data = np.linspace(10, 13, n_points)  # 10mm to 13mm
        
        # Create force profile: baseline -> rise -> peak -> fall
        force_data = np.zeros(n_points)
        force_data[50:150] = np.sin(np.linspace(0, np.pi, 100)) * 0.5  # Peak at 0.5N
        
        # Add small noise
        force_data += np.random.normal(0, 0.001, n_points)
        
        result = self.calculator.calculate_from_arrays(
            time_data, position_data, force_data, layer_number=1
        )
        
        # Check that results were calculated
        self.assertIsNotNone(result)
        self.assertIn('layer_number', result)
        self.assertEqual(result['layer_number'], 1)
        self.assertIn('peak_force', result)
        self.assertIn('work_of_adhesion_mJ', result)
    
    def test_calculate_from_arrays_no_peak(self):
        """Test calculation with no significant peak"""
        # Create flat data with just noise
        n_points = 100
        time_data = np.linspace(0, 1, n_points)
        position_data = np.linspace(10, 11, n_points)
        force_data = np.random.normal(0, 0.001, n_points)  # Just noise
        
        result = self.calculator.calculate_from_arrays(
            time_data, position_data, force_data, layer_number=1
        )
        
        # Should return results but with low/zero values
        self.assertIsNotNone(result)
        self.assertIn('peak_force', result)
    
    def test_calculate_from_arrays_with_nan_values(self):
        """Test calculation handles NaN values gracefully"""
        n_points = 100
        time_data = np.linspace(0, 1, n_points)
        position_data = np.linspace(10, 11, n_points)
        force_data = np.random.normal(0.1, 0.01, n_points)
        
        # Insert some NaN values
        force_data[20:25] = np.nan
        
        result = self.calculator.calculate_from_arrays(
            time_data, position_data, force_data, layer_number=1
        )
        
        # Should still return results (NaN values filtered out)
        self.assertIsNotNone(result)
        self.assertIn('peak_force', result)
    
    def test_calculate_from_arrays_insufficient_data(self):
        """Test calculation with insufficient data points"""
        # Only 5 data points (below minimum)
        time_data = np.array([0, 1, 2, 3, 4])
        position_data = np.array([10, 10.5, 11, 11.5, 12])
        force_data = np.array([0, 0.1, 0.2, 0.1, 0])
        
        result = self.calculator.calculate_from_arrays(
            time_data, position_data, force_data, layer_number=1
        )
        
        # Should return empty/default results
        self.assertIsNotNone(result)
    
    def test_calculate_from_arrays_mismatched_lengths(self):
        """Test calculation with mismatched array lengths"""
        time_data = np.linspace(0, 1, 100)
        position_data = np.linspace(10, 11, 100)
        force_data = np.linspace(0, 0.5, 50)  # Different length!
        
        with self.assertRaises(ValueError):
            self.calculator.calculate_from_arrays(
                time_data, position_data, force_data, layer_number=1
            )
    
    def test_realistic_adhesion_profile(self):
        """Test with realistic adhesion force profile"""
        # Simulate realistic printing scenario
        n_points = 500
        time_data = np.linspace(0, 5, n_points)  # 5 seconds
        position_data = np.linspace(10, 15, n_points)  # 10mm to 15mm lift
        
        # Realistic force profile:
        # 1. Baseline (0-100): ~0N
        # 2. Initiation (100-150): Rising
        # 3. Peak (150-200): Max force
        # 4. Propagation (200-400): Declining
        # 5. End (400-500): Return to baseline
        
        force_data = np.zeros(n_points)
        force_data[0:100] = 0.01 + np.random.normal(0, 0.002, 100)  # Baseline
        force_data[100:150] = np.linspace(0.01, 0.8, 50)  # Rising
        force_data[150:200] = 0.8 + np.random.normal(0, 0.02, 50)  # Peak
        force_data[200:400] = np.linspace(0.8, 0.05, 200)  # Declining
        force_data[400:500] = 0.01 + np.random.normal(0, 0.002, 100)  # End
        
        result = self.calculator.calculate_from_arrays(
            time_data, position_data, force_data, layer_number=1
        )
        
        # Verify realistic results
        self.assertGreater(result['peak_force'], 0.5)
        self.assertGreater(result['work_of_adhesion_mJ'], 0)
        self.assertIn('pre_initiation_time', result)
        self.assertIn('propagation_duration', result)


class TestAdhesionMetricsCalculatorCSV(unittest.TestCase):
    """Test CSV loading functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.calculator = AdhesionMetricsCalculator()
    
    def test_calculate_from_csv_nonexistent_file(self):
        """Test CSV loading with nonexistent file"""
        result = self.calculator.calculate_from_csv(
            "nonexistent_file.csv",
            layer_number=1
        )
        
        # Should handle gracefully
        self.assertIsNotNone(result)


class TestAdhesionMetricsCalculatorEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.calculator = AdhesionMetricsCalculator()
    
    def test_all_zero_force(self):
        """Test with all zero force values"""
        n_points = 100
        time_data = np.linspace(0, 1, n_points)
        position_data = np.linspace(10, 11, n_points)
        force_data = np.zeros(n_points)
        
        result = self.calculator.calculate_from_arrays(
            time_data, position_data, force_data, layer_number=1
        )
        
        self.assertIsNotNone(result)
        # Peak force should be very low or zero
        self.assertLess(result.get('peak_force', 0), 0.01)
    
    def test_negative_force_values(self):
        """Test with negative force values (should be handled)"""
        n_points = 100
        time_data = np.linspace(0, 1, n_points)
        position_data = np.linspace(10, 11, n_points)
        force_data = np.random.normal(-0.5, 0.1, n_points)  # Negative forces
        
        result = self.calculator.calculate_from_arrays(
            time_data, position_data, force_data, layer_number=1
        )
        
        # Should still calculate (may give warning)
        self.assertIsNotNone(result)
    
    def test_very_high_noise(self):
        """Test with very noisy data"""
        n_points = 200
        time_data = np.linspace(0, 2, n_points)
        position_data = np.linspace(10, 12, n_points)
        
        # Create signal with 50% noise
        signal = np.sin(np.linspace(0, 2*np.pi, n_points)) * 0.5
        noise = np.random.normal(0, 0.25, n_points)
        force_data = signal + noise
        
        result = self.calculator.calculate_from_arrays(
            time_data, position_data, force_data, layer_number=1
        )
        
        # Should still process (filtering should help)
        self.assertIsNotNone(result)


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestAdhesionMetricsCalculator))
    suite.addTests(loader.loadTestsFromTestCase(TestAdhesionMetricsCalculatorCSV))
    suite.addTests(loader.loadTestsFromTestCase(TestAdhesionMetricsCalculatorEdgeCases))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
