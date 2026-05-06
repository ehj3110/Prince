"""
VideoPattern Print Logging Service
==================================

Handles persistence for VideoPattern prints:
- Per-print CSV files in Print N folders
- Daily rolling CSV keyed by image/model folder name
- Copy of MASTER_WORKFLOW_GUIDE.md in each Print N folder

Author: Cheng Sun Lab Team
Date: April 12, 2026
"""

import csv
import os
from pathlib import Path
from datetime import datetime
import shutil


class VideoPatternPrintLogging:
    """
    Manages logging for VideoPattern prints including daily records and per-print data.
    """
    
    def __init__(self, update_status_callback=None):
        """
        Initialize the logging service.
        
        Args:
            update_status_callback: Function to call with status messages
        """
        self.update_status = update_status_callback or self._default_status_update
        self.current_print_dir = None
        self.current_model_name = None
        self.current_date_dir = None
        
    def _default_status_update(self, message, error=False):
        """Default status update if no callback provided."""
        print(f"PrintLogging: {message}")
    
    def start_new_print(self, print_directory, conditions_dict):
        """
        Prepare for a new print with given conditions.
        
        Args:
            print_directory: Full path to Print N folder (e.g., /path/Printing_Logs/2026-04-12/Print 1)
            conditions_dict: Dict with keys: user, membrane, resin, preprint_notes
        """
        try:
            self.current_print_dir = Path(print_directory)
            self.current_print_dir.mkdir(parents=True, exist_ok=True)
            
            # Extract date from path
            # Path structure: .../Printing_Logs/YYYY-MM-DD/Print N
            path_parts = self.current_print_dir.parts
            if "Printing_Logs" in path_parts:
                idx = list(path_parts).index("Printing_Logs")
                if idx + 1 < len(path_parts):
                    self.current_date_dir = self.current_print_dir.parent  # YYYY-MM-DD folder
            
            # Write pre-print CSV with initial conditions
            self._write_preprint_conditions(conditions_dict)
            
            # Copy MASTER_WORKFLOW_GUIDE.md to print folder
            self._copy_workflow_guide()
            
            self.update_status(f"VideoPattern logging initialized for {self.current_print_dir.name}")
            
        except Exception as e:
            self.update_status(f"Error starting print logging: {e}", error=True)
            print(f"Error in start_new_print: {e}")
            import traceback
            traceback.print_exc()
    
    def _write_preprint_conditions(self, conditions_dict):
        """
        Write pre-print conditions to per-print CSV.
        
        Args:
            conditions_dict: Dict with user, membrane, resin, preprint_notes
        """
        if not self.current_print_dir:
            return
        
        csv_file = self.current_print_dir / "print_conditions.csv"
        
        data = {
            'Print_Date_Time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'User': conditions_dict.get('user', 'N/A'),
            'Membrane_Type': conditions_dict.get('membrane', 'N/A'),
            'Resin': conditions_dict.get('resin', 'N/A'),
            'Pre_print_Notes': conditions_dict.get('preprint_notes', 'N/A'),
            'Print_Status': 'In Progress'
        }
        
        # Write initial record
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=data.keys())
            writer.writeheader()
            writer.writerow(data)
        
        print(f"Pre-print conditions written to {csv_file.name}")
    
    def _copy_workflow_guide(self):
        """Copy MASTER_WORKFLOW_GUIDE.md to the print folder."""
        try:
            source_guide = Path(__file__).parent.parent / "documentation" / "MASTER_WORKFLOW_GUIDE.md"
            
            if not source_guide.exists():
                print(f"Warning: MASTER_WORKFLOW_GUIDE.md not found at {source_guide}")
                return
            
            dest_guide = self.current_print_dir / "MASTER_WORKFLOW_GUIDE.md"
            shutil.copy2(source_guide, dest_guide)
            print(f"Workflow guide copied to {self.current_print_dir}")
            
        except Exception as e:
            print(f"Error copying workflow guide: {e}")
    
    def end_print(self, logging_result):
        """
        End print session and write final records to CSV files.
        
        Args:
            logging_result: Dict from LoggingCheckWindow with keys:
                - status: 'Finished' or 'Failed'
                - notes: User notes
                - wait_for_qc: Boolean
                - timestamp: Timestamp string
        """
        try:
            if not self.current_print_dir:
                return
            
            # Update per-print CSV with final status
            self._update_print_status_csv(logging_result)
            
            # Append to daily records CSV
            self._append_to_daily_records(logging_result)
            
            self.update_status(f"Print {self.current_print_dir.name} logging completed")
            
        except Exception as e:
            self.update_status(f"Error ending print logging: {e}", error=True)
            print(f"Error in end_print: {e}")
            import traceback
            traceback.print_exc()
    
    def _update_print_status_csv(self, logging_result):
        """
        Update the per-print CSV with completion status and notes.
        
        Args:
            logging_result: Result dict from LoggingCheckWindow
        """
        csv_file = self.current_print_dir / "print_conditions.csv"
        
        if not csv_file.exists():
            return
        
        # Read existing data
        rows = []
        fieldnames = None
        with open(csv_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            rows = list(reader)
        
        # Update last row with final status
        if rows:
            rows[-1]['Print_Status'] = logging_result['status']
            rows[-1]['Completion_Notes'] = logging_result['notes']
            rows[-1]['Completion_Timestamp'] = logging_result['timestamp']
            rows[-1]['Wait_for_QC'] = str(logging_result['wait_for_qc'])
        
        # Write back
        fieldnames_extended = list(fieldnames) + ['Completion_Notes', 'Completion_Timestamp', 'Wait_for_QC']
        fieldnames_extended = list(dict.fromkeys(fieldnames_extended))  # Remove duplicates while preserving order
        
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames_extended, restval='')
            writer.writeheader()
            writer.writerows(rows)
        
        print(f"Print status updated in {csv_file.name}")
    
    def _append_to_daily_records(self, logging_result):
        """
        Append entry to daily_records_<model>.csv in the date directory.
        
        Args:
            logging_result: Result dict from LoggingCheckWindow
        """
        if not self.current_date_dir or not self.current_print_dir:
            return
        
        try:
            # Extract model name from path structure
            # Path is typically: .../ModelFolder/Printing_Logs/YYYY-MM-DD/Print N
            # We need to extract "ModelFolder"
            print_path_parts = self.current_print_dir.parts
            printing_logs_idx = None
            for i, part in enumerate(print_path_parts):
                if part == "Printing_Logs":
                    printing_logs_idx = i
                    break
            
            if printing_logs_idx and printing_logs_idx > 0:
                model_name = print_path_parts[printing_logs_idx - 1]
            else:
                # Fallback: use a generic name
                model_name = "unknown_model"
            
            # Create daily records CSV filename
            daily_csv_file = self.current_date_dir / f"daily_records_{model_name}.csv"
            
            # Prepare row data
            print_number = self.current_print_dir.name  # e.g., "Print 1"
            row_data = {
                'Timestamp': logging_result['timestamp'],
                'Print_Number': print_number,
                'Status': logging_result['status'],
                'Wait_for_QC': str(logging_result['wait_for_qc']),
                'Notes': logging_result['notes'],
                'Model': model_name
            }
            
            # Check if file exists
            file_exists = daily_csv_file.exists()
            
            # Append to CSV
            with open(daily_csv_file, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=row_data.keys())
                
                if not file_exists:
                    writer.writeheader()
                
                writer.writerow(row_data)
            
            print(f"Daily record appended to {daily_csv_file.name}")
            
        except Exception as e:
            print(f"Error appending to daily records: {e}")
            import traceback
            traceback.print_exc()
    
    def set_model_name(self, model_name):
        """
        Set the model/image folder name for daily records.
        
        Args:
            model_name: Name of the model folder
        """
        self.current_model_name = model_name


if __name__ == "__main__":
    # Test the logging service
    def test_callback(msg, error=False):
        print(f"{'ERROR: ' if error else ''}{msg}")
    
    logger = VideoPatternPrintLogging(test_callback)
    
    # Test starting a print
    import tempfile
    test_dir = Path(tempfile.gettempdir()) / "VideoPattern_test" / "Printing_Logs" / "2026-04-12" / "Print 1"
    
    conditions = {
        'user': 'Test User',
        'membrane': 'PTFE',
        'resin': 'SU8',
        'preprint_notes': 'Test print conditions'
    }
    
    logger.start_new_print(str(test_dir), conditions)
    
    # Test ending a print
    result = {
        'status': 'Finished',
        'notes': 'Test completed successfully',
        'wait_for_qc': False,
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    logger.end_print(result)
    
    print(f"\nTest files created in: {test_dir}")
    print("Check the print folder for print_conditions.csv and daily_records_*.csv")
