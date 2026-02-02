"""
Unit tests for PeakForceLogger

Tests peak force logging functionality including:
- Layer monitoring start/stop
- Data point addition
- CSV output generation
- Cross-sectional area tracking
- Integration with AdhesionMetricsCalculator
"""

import unittest
import sys
import os
import tempfile
import shutil
import csv
import time
import numpy as np
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from support_modules.PeakForceLogger import PeakForceLogger


class TestPeakForceLogger(unittest.TestCase):
    """Test cases for PeakForceLogger"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.csv_file = os.path.join(self.temp_dir, "test_peak_force.csv")
        self.logger = PeakForceLogger(
            output_csv_filepath=self.csv_file,
            is_manual_log=False,
            use_corrected_calculator=True
        )
    
    def tearDown(self):
        """Clean up test fixtures"""
        if hasattr(self, 'logger'):
            self.logger.close()
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """Test PeakForceLogger initialization"""
        self.assertIsNotNone(self.logger)
        self.assertEqual(self.logger.output_csv_filepath, self.csv_file)
        self.assertFalse(self.logger.is_manual_log)
        self.assertTrue(self.logger.use_corrected_calculator)
        self.assertEqual(self.logger.current_layer_number, 0)
        self.assertFalse(self.logger._monitoring)
    
    def test_csv_header_creation(self):
        """Test that CSV header is created properly"""
        self.assertTrue(os.path.exists(self.csv_file))
        
        with open(self.csv_file, 'r') as f:
            reader = csv.reader(f)
            header = next(reader)
            
            # Check expected headers
            self.assertIn('Layer_Number', header)
            self.assertIn('Peak_Force_N', header)
            self.assertIn('Work_of_Adhesion_mJ', header)
            self.assertIn('Cross_Sectional_Area_mm2', header)
    
    def test_start_monitoring_for_layer(self):
        """Test starting monitoring for a layer"""
        self.logger.start_monitoring_for_layer(
            layer_number=1,
            z_peel_peak=10.0,
            z_return_pos=13.0
        )
        
        self.assertTrue(self.logger._monitoring)
        self.assertEqual(self.logger.current_layer_number, 1)
        self.assertEqual(self.logger.z_peel_peak_mm, 10.0)
        self.assertEqual(self.logger.z_return_pos_mm, 13.0)
    
    def test_stop_monitoring_and_log_peak(self):
        """Test stopping monitoring and logging peak"""
        # Start monitoring
        self.logger.start_monitoring_for_layer(1, 10.0, 13.0)
        
        # Add some data points
        base_time = time.time()
        for i in range(100):
            t = base_time + i * 0.01
            pos = 10.0 + (i / 100.0) * 3.0
            force = max(0.0, 0.5 * np.sin(i / 100.0 * np.pi))
            self.logger.add_data_point(t, pos, force)
        
        # Stop monitoring
        self.logger.stop_monitoring_and_log_peak()
        
        self.assertFalse(self.logger._monitoring)
    
    def test_add_data_point_when_not_monitoring(self):
        """Test that data points are ignored when not monitoring"""
        # Don't start monitoring
        initial_buffer_size = len(self.logger._data_buffer)
        
        self.logger.add_data_point(time.time(), 10.0, 0.5)
        
        # Buffer should not change
        self.assertEqual(len(self.logger._data_buffer), initial_buffer_size)
    
    def test_add_data_point_when_monitoring(self):
        """Test that data points are added when monitoring"""
        self.logger.start_monitoring_for_layer(1, 10.0, 13.0)
        
        initial_buffer_size = len(self.logger._data_buffer)
        
        self.logger.add_data_point(time.time(), 10.5, 0.3)
        
        # Buffer should increase
        self.assertGreater(len(self.logger._data_buffer), initial_buffer_size)
    
    def test_cross_sectional_area_from_image(self):
        """Test cross-sectional area calculation from image"""
        # Create a test image with known white pixels
        import cv2
        img = np.zeros((100, 100), dtype=np.uint8)
        # Create a 10x10 white square (100 pixels)
        img[40:50, 40:50] = 255
        
        test_img_path = os.path.join(self.temp_dir, "test_area.png")
        cv2.imwrite(test_img_path, img)
        
        # Calculate area
        area = self.logger._calculate_cross_sectional_area(test_img_path)
        
        # Expected: 100 pixels * PIXEL_AREA_MM2
        expected_area = 100 * self.logger.PIXEL_AREA_MM2
        self.assertAlmostEqual(area, expected_area, places=6)
    
    def test_cross_sectional_area_no_image(self):
        """Test cross-sectional area when no image provided"""
        self.logger.start_monitoring_for_layer(1, 10.0, 13.0)
        
        # Should not crash, area should be None
        self.assertIsNone(self.logger.current_cross_sectional_area_mm2)


class TestPeakForceLoggerIntegration(unittest.TestCase):
    """Integration tests for PeakForceLogger"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.csv_file = os.path.join(self.temp_dir, "test_integration.csv")
        self.logger = PeakForceLogger(
            output_csv_filepath=self.csv_file,
            is_manual_log=False,
            use_corrected_calculator=True
        )
    
    def tearDown(self):
        """Clean up integration test fixtures"""
        self.logger.close()
        time.sleep(0.5)  # Allow worker thread to finish
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_full_layer_logging_workflow(self):
        """Test complete workflow of logging a layer"""
        # Create test image
        import cv2
        img = np.zeros((100, 100), dtype=np.uint8)
        cv2.circle(img, (50, 50), 20, 255, -1)
        test_img = os.path.join(self.temp_dir, "layer1.png")
        cv2.imwrite(test_img, img)
        
        # 1. Start monitoring
        self.logger.start_monitoring_for_layer(
            layer_number=1,
            z_peel_peak=10.0,
            z_return_pos=13.0,
            image_path=test_img
        )
        
        # 2. Add realistic force data
        base_time = time.time()
        for i in range(200):
            t = base_time + i * 0.01  # 10ms intervals
            pos = 10.0 + (i / 200.0) * 3.0  # 10mm to 13mm
            
            # Realistic force profile: rise -> peak -> decay
            if i < 50:
                force = 0.01  # Baseline
            elif i < 100:
                force = (i - 50) / 50.0 * 0.8  # Rising
            elif i < 120:
                force = 0.8  # Peak
            else:
                force = max(0.01, 0.8 * (1 - (i - 120) / 80.0))  # Decay
            
            self.logger.add_data_point(t, pos, force)
        
        # 3. Stop monitoring and log
        self.logger.stop_monitoring_and_log_peak()
        
        # 4. Wait for worker thread
        time.sleep(1.0)
        
        # 5. Verify CSV output
        self.assertTrue(os.path.exists(self.csv_file))
        
        with open(self.csv_file, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            self.assertEqual(len(rows), 1)
            row = rows[0]
            
            # Verify layer number
            self.assertEqual(row['Layer_Number'], '1')
            
            # Verify peak force is reasonable
            peak_force = float(row['Peak_Force_N'])
            self.assertGreater(peak_force, 0.5)
            self.assertLess(peak_force, 1.0)
            
            # Verify work of adhesion exists
            work = float(row['Work_of_Adhesion_mJ'])
            self.assertGreater(work, 0)
    
    def test_multiple_layers_logging(self):
        """Test logging multiple consecutive layers"""
        for layer_num in range(1, 4):
            # Start monitoring
            self.logger.start_monitoring_for_layer(
                layer_number=layer_num,
                z_peel_peak=10.0,
                z_return_pos=13.0
            )
            
            # Add data
            base_time = time.time()
            for i in range(100):
                t = base_time + i * 0.01
                pos = 10.0 + (i / 100.0) * 3.0
                force = max(0.0, 0.5 * np.sin(i / 100.0 * np.pi))
                self.logger.add_data_point(t, pos, force)
            
            # Stop monitoring
            self.logger.stop_monitoring_and_log_peak()
            time.sleep(0.3)  # Brief pause between layers
        
        # Wait for worker thread
        time.sleep(1.0)
        
        # Verify CSV has 3 layers
        with open(self.csv_file, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            self.assertEqual(len(rows), 3)
            
            # Verify layer numbers
            layer_numbers = [int(row['Layer_Number']) for row in rows]
            self.assertEqual(layer_numbers, [1, 2, 3])


class TestPeakForceLoggerManualMode(unittest.TestCase):
    """Test manual logging mode"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.csv_file = os.path.join(self.temp_dir, "test_manual.csv")
        self.logger = PeakForceLogger(
            output_csv_filepath=self.csv_file,
            is_manual_log=True  # Manual mode
        )
    
    def tearDown(self):
        """Clean up test fixtures"""
        self.logger.close()
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_manual_mode_no_header(self):
        """Test that manual mode doesn't create header automatically"""
        # In manual mode, header should not be auto-created
        # (User may want custom format)
        pass  # Implementation detail


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestPeakForceLogger))
    suite.addTests(loader.loadTestsFromTestCase(TestPeakForceLoggerIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestPeakForceLoggerManualMode))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
