"""
Unit tests for Experimental Conditions Logging and instruction file saving.
"""

import unittest
import sys
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, MagicMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from support_modules.ExperimentalConditionsWindow import ExperimentalConditionsWindow


class MockPrinceApp:
    """Mock Prince main application for testing instruction file copying."""
    def __init__(self, img_dir, instruction_file_path=None):
        self.t1 = Mock()
        self.t1.get = Mock(return_value=str(img_dir))
        self.active_instruction_file_path = instruction_file_path
        self.status_messages = []

    def update_status_message(self, msg, error=False):
        self.status_messages.append(msg)


class TestExperimentalConditionsInstructionSave(unittest.TestCase):
    def setUp(self):
        self.temp_root = tempfile.mkdtemp()
        self.img_dir = Path(self.temp_root) / "TestPrintFolder"
        self.img_dir.mkdir(parents=True)
        self.instruction_file = self.img_dir / "TestPrintFolder.txt"
        self.instruction_file.write_text("Layer\tTime\tThickness\n1\t2.5\t50\n")

        self.log_dir = Path(self.temp_root) / "Printing_Logs" / "2026-10-19" / "Print 1"

    def tearDown(self):
        if os.path.exists(self.temp_root):
            shutil.rmtree(self.temp_root)

    def test_copy_instruction_file_at_start_and_end(self):
        root = MagicMock()
        window = MagicMock()
        root.tk = MagicMock()

        # Instantiate window with mocks for Tk elements
        with unittest.mock.patch('tkinter.Toplevel') as mock_toplevel, \
             unittest.mock.patch('tkinter.ttk.Frame'), \
             unittest.mock.patch('tkinter.ttk.Label'), \
             unittest.mock.patch('tkinter.ttk.Checkbutton'), \
             unittest.mock.patch('tkinter.ttk.LabelFrame'), \
             unittest.mock.patch('tkinter.ttk.Entry'), \
             unittest.mock.patch('tkinter.ttk.Button'), \
             unittest.mock.patch('tkinter.StringVar'), \
             unittest.mock.patch('tkinter.BooleanVar') as mock_bool:
            
            mock_bool_inst = MagicMock()
            mock_bool_inst.get.return_value = True
            mock_bool.return_value = mock_bool_inst

            exp_win = ExperimentalConditionsWindow(root)
            exp_win.entries = {k: MagicMock(get=Mock(return_value="test")) for k in [
                'user', 'membrane_type', 'tempo_pattern', 'oil', 'fluid_type',
                'fluid_gap', 'tank', 'resin', 'build_platform'
            ]}
            mock_app = MockPrinceApp(self.img_dir, str(self.instruction_file))
            exp_win.prince_main_app_ref = mock_app

            # Start new print session
            exp_win.start_new_print(self.log_dir)

            # Check that instruction file was copied into self.log_dir
            copied_file = self.log_dir / "TestPrintFolder.txt"
            self.assertTrue(copied_file.exists(), "Instruction file should be copied to log dir at print start")
            self.assertEqual(copied_file.read_text(), self.instruction_file.read_text())

            # End print session with success -> directory should be renamed to Print 1 - Complete
            exp_win.end_print(success=True)
            renamed_dir = self.log_dir.parent / "Print 1 - Complete"
            self.assertTrue(renamed_dir.exists(), "Log directory should be renamed to Complete")
            copied_file_after_rename = renamed_dir / "TestPrintFolder.txt"
            self.assertTrue(copied_file_after_rename.exists(), "Instruction file must persist in renamed folder")

    def test_copy_instruction_file_fallback_from_t1(self):
        root = MagicMock()

        with unittest.mock.patch('tkinter.Toplevel'), \
             unittest.mock.patch('tkinter.ttk.Frame'), \
             unittest.mock.patch('tkinter.ttk.Label'), \
             unittest.mock.patch('tkinter.ttk.Checkbutton'), \
             unittest.mock.patch('tkinter.ttk.LabelFrame'), \
             unittest.mock.patch('tkinter.ttk.Entry'), \
             unittest.mock.patch('tkinter.ttk.Button'), \
             unittest.mock.patch('tkinter.StringVar'), \
             unittest.mock.patch('tkinter.BooleanVar') as mock_bool:
            
            mock_bool_inst = MagicMock()
            mock_bool_inst.get.return_value = True
            mock_bool.return_value = mock_bool_inst

            exp_win = ExperimentalConditionsWindow(root)
            exp_win.entries = {k: MagicMock(get=Mock(return_value="test")) for k in [
                'user', 'membrane_type', 'tempo_pattern', 'oil', 'fluid_type',
                'fluid_gap', 'tank', 'resin', 'build_platform'
            ]}
            # active_instruction_file_path is None, but t1 has image dir
            mock_app = MockPrinceApp(self.img_dir, instruction_file_path=None)
            exp_win.prince_main_app_ref = mock_app

            exp_win.start_new_print(self.log_dir)

            copied_file = self.log_dir / "TestPrintFolder.txt"
            self.assertTrue(copied_file.exists(), "Instruction file should be discovered from t1 and copied")
            self.assertEqual(mock_app.active_instruction_file_path, str(self.instruction_file))

    def test_do_not_copy_when_logging_disabled(self):
        root = MagicMock()

        with unittest.mock.patch('tkinter.Toplevel'), \
             unittest.mock.patch('tkinter.ttk.Frame'), \
             unittest.mock.patch('tkinter.ttk.Label'), \
             unittest.mock.patch('tkinter.ttk.Checkbutton'), \
             unittest.mock.patch('tkinter.ttk.LabelFrame'), \
             unittest.mock.patch('tkinter.ttk.Entry'), \
             unittest.mock.patch('tkinter.ttk.Button'), \
             unittest.mock.patch('tkinter.StringVar'), \
             unittest.mock.patch('tkinter.BooleanVar') as mock_bool:
            
            mock_bool_inst = MagicMock()
            mock_bool_inst.get.return_value = False  # Disabled!
            mock_bool.return_value = mock_bool_inst

            exp_win = ExperimentalConditionsWindow(root)
            mock_app = MockPrinceApp(self.img_dir, str(self.instruction_file))
            exp_win.prince_main_app_ref = mock_app

            exp_win.start_new_print(self.log_dir)

            copied_file = self.log_dir / "TestPrintFolder.txt"
            self.assertFalse(copied_file.exists(), "Instruction file should not be copied when logging is disabled")


if __name__ == '__main__':
    unittest.main()
