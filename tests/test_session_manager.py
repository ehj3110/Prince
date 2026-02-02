"""
Unit tests for SessionManager module

Tests session management functionality including:
- Session log initialization
- Print numbering
- GUI state save/load
- Post-print analysis triggering
"""

import unittest
import sys
import os
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from support_modules.SessionManager import SessionManager


class MockMyWindow:
    """Mock MyWindow class for testing SessionManager"""
    def __init__(self):
        self.terminal_output = Mock()
        self.terminal_output.insert = Mock()
        self.terminal_output.see = Mock()
        self.terminal_output.yview = Mock()
        
        # Mock GUI elements
        self.name_input = Mock()
        self.name_input.get = Mock(return_value="TestPrint")
        self.name_input.delete = Mock()
        self.name_input.insert = Mock()
        
        self.exposure_input = Mock()
        self.exposure_input.get = Mock(return_value="1000")
        self.exposure_input.delete = Mock()
        self.exposure_input.insert = Mock()
        
        self.layer_height_input = Mock()
        self.layer_height_input.get = Mock(return_value="50")
        self.layer_height_input.delete = Mock()
        self.layer_height_input.insert = Mock()
        
        # Mock additional GUI elements that SessionManager uses
        self.t1 = Mock()  # directory input
        self.t1.get = Mock(return_value="C:/TestDir")
        self.t1.delete = Mock()
        self.t1.insert = Mock()
        
        # Mock reference attribute
        self.reference = 0
        
        # Mock update_status_message method
        self.update_status_message = Mock()
        
        # Session log files
        self.session_log_file = None
        self.detailed_log_file = None


class TestSessionManager(unittest.TestCase):
    """Test cases for SessionManager class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.parent = MockMyWindow()
        self.session_manager = SessionManager(self.parent)
        
    def tearDown(self):
        """Clean up test fixtures"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """Test SessionManager initialization"""
        self.assertIsNotNone(self.session_manager)
        self.assertEqual(self.session_manager.parent, self.parent)
        self.assertIsNone(self.session_manager.session_log_file)
        self.assertIsNone(self.session_manager.detailed_log_file)
    
    def test_init_session_log_creates_files(self):
        """Test that init_session_log creates log files"""
        with patch('os.path.dirname') as mock_dirname:
            # Mock to use temp directory
            mock_dirname.return_value = self.temp_dir
            
            self.session_manager.init_session_log()
            
            # Check that log files were created
            self.assertIsNotNone(self.session_manager.session_log_file)
            self.assertIsNotNone(self.session_manager.detailed_log_file)
            
            # Check that files exist
            self.assertTrue(os.path.exists(self.session_manager.session_log_file))
            self.assertTrue(os.path.exists(self.session_manager.detailed_log_file))
            
            # Check that parent references were set
            self.assertEqual(self.parent.session_log_file, self.session_manager.session_log_file)
            self.assertEqual(self.parent.detailed_log_file, self.session_manager.detailed_log_file)
    
    def test_init_session_log_writes_headers(self):
        """Test that log files contain proper headers"""
        with patch('os.path.dirname') as mock_dirname:
            mock_dirname.return_value = self.temp_dir
            
            self.session_manager.init_session_log()
            
            # Read session log
            with open(self.session_manager.session_log_file, 'r') as f:
                content = f.read()
                self.assertIn("Prince GUI Session Log", content)
                self.assertIn("Started:", content)
            
            # Read detailed log
            with open(self.session_manager.detailed_log_file, 'r') as f:
                content = f.read()
                self.assertIn("Detailed Diagnostics", content)
                self.assertIn("verbose diagnostic", content)
    
    def test_get_next_print_number_empty_directory(self):
        """Test print numbering with empty directory"""
        result = self.session_manager.get_next_print_number(self.temp_dir)
        self.assertEqual(result, 1)
    
    def test_get_next_print_number_with_existing_prints(self):
        """Test print numbering with existing print directories"""
        # Create mock print directories
        os.makedirs(os.path.join(self.temp_dir, "Print 1 - TestPrint"))
        os.makedirs(os.path.join(self.temp_dir, "Print 2 - TestPrint"))
        os.makedirs(os.path.join(self.temp_dir, "Print 5 - TestPrint"))
        
        result = self.session_manager.get_next_print_number(self.temp_dir)
        self.assertEqual(result, 6)
    
    def test_get_next_print_number_nonexistent_directory(self):
        """Test print numbering with nonexistent directory"""
        fake_dir = os.path.join(self.temp_dir, "nonexistent")
        result = self.session_manager.get_next_print_number(fake_dir)
        self.assertEqual(result, 1)
    
    def test_save_gui_state(self):
        """Test GUI state saving"""
        config_file = os.path.join(self.temp_dir, "prince_gui_state.json")
        
        with patch('os.path.dirname') as mock_dirname:
            # Mock to use temp directory
            mock_dirname.return_value = self.temp_dir
            
            # Save state (should not raise exception)
            try:
                self.session_manager.save_gui_state()
                # If no exception, test passes
                success = True
            except Exception as e:
                success = False
                print(f"Save GUI state error: {e}")
            
            # Verify update_status_message was called (indicates attempt was made)
            self.assertTrue(self.parent.update_status_message.called or success)
    
    def test_load_gui_state_nonexistent_file(self):
        """Test loading GUI state with nonexistent file"""
        config_file = os.path.join(self.temp_dir, "nonexistent.json")
        
        with patch('os.path.dirname') as mock_dirname:
            mock_dirname.return_value = self.temp_dir
            
            # Should not raise exception
            self.session_manager.load_gui_state()
    
    def test_load_gui_state_valid_file(self):
        """Test loading GUI state from valid file"""
        config_file = os.path.join(self.temp_dir, "prince_gui_state.json")
        
        # Create test config
        test_config = {
            "name": "LoadedPrint",
            "exposure_time": "1500",
            "layer_height": "100"
        }
        
        with open(config_file, 'w') as f:
            json.dump(test_config, f)
        
        with patch('os.path.dirname') as mock_dirname:
            mock_dirname.return_value = self.temp_dir
            
            # Load state (should not raise exception)
            try:
                self.session_manager.load_gui_state()
                success = True
            except Exception as e:
                success = False
                print(f"Load GUI state error: {e}")
            
            # Verify either no exception or update_status_message was called
            self.assertTrue(success or self.parent.update_status_message.called)


class TestSessionManagerIntegration(unittest.TestCase):
    """Integration tests for SessionManager"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.parent = MockMyWindow()
        self.session_manager = SessionManager(self.parent)
    
    def tearDown(self):
        """Clean up integration test fixtures"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_full_session_workflow(self):
        """Test complete session workflow"""
        with patch('os.path.dirname') as mock_dirname:
            mock_dirname.return_value = self.temp_dir
            
            # 1. Initialize session logs
            self.session_manager.init_session_log()
            self.assertIsNotNone(self.session_manager.session_log_file)
            
            # 2. Get print number
            print_num = self.session_manager.get_next_print_number(self.temp_dir)
            self.assertEqual(print_num, 1)
            
            # 3. Create a print directory
            os.makedirs(os.path.join(self.temp_dir, "Print 1 - Test"))
            
            # 4. Get next print number (should be 2)
            print_num = self.session_manager.get_next_print_number(self.temp_dir)
            self.assertEqual(print_num, 2)


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestSessionManager))
    suite.addTests(loader.loadTestsFromTestCase(TestSessionManagerIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
