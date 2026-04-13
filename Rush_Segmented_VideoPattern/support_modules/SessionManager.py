"""
SessionManager.py

Handles session logging, print numbering, state persistence, and post-print analysis
for the Rush printing system. Extracted from Prince_Segmented.py to improve
code organization and maintainability.

Author: Refactored from Prince_Segmented.py
Date: January 2026
"""

import os
import datetime
import json
import traceback
from tkinter import END


class SessionManager:
    """
    Manages session logging, GUI state persistence, print numbering,
    and post-print analysis triggering.
    """
    
    def __init__(self, parent):
        """
        Initialize SessionManager with reference to parent GUI.
        
        Args:
            parent: MyWindow instance (provides access to GUI elements and callbacks)
        """
        self.parent = parent
        self.session_log_file = None
        self.detailed_log_file = None
    
    def init_session_log(self):
        """Initialize session log files for this GUI session."""
        try:
            # Create logs directory if it doesn't exist
            log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'SessionLogs')
            os.makedirs(log_dir, exist_ok=True)
            
            # Create timestamped log files
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Standard session log (terminal mirror)
            log_filename = f"rush_session_{timestamp}.log"
            self.session_log_file = os.path.join(log_dir, log_filename)
            
            # Detailed diagnostics log (verbose)
            detailed_log_filename = f"rush_detailed_{timestamp}.log"
            self.detailed_log_file = os.path.join(log_dir, detailed_log_filename)
            
            # Write headers to both log files
            with open(self.session_log_file, 'w') as f:
                f.write(f"Rush GUI Session Log (Terminal Mirror)\n")
                f.write(f"Started: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"="*80 + "\n\n")
            
            with open(self.detailed_log_file, 'w') as f:
                f.write(f"Rush GUI Detailed Diagnostics Log\n")
                f.write(f"Started: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"This log contains verbose diagnostic information.\n")
                f.write(f"="*80 + "\n\n")
            
            print(f"Session logs initialized:")
            print(f"  Standard: {self.session_log_file}")
            print(f"  Detailed: {self.detailed_log_file}")
            
            # Store log file references in parent for logging system to use
            self.parent.session_log_file = self.session_log_file
            self.parent.detailed_log_file = self.detailed_log_file
            
        except Exception as e:
            print(f"Warning: Could not initialize session logs: {e}")
            self.session_log_file = None
            self.detailed_log_file = None
            self.parent.session_log_file = None
            self.parent.detailed_log_file = None
    
    def get_next_print_number(self, date_specific_log_dir):
        """
        Determines the next print number for a given date directory.
        
        Args:
            date_specific_log_dir: Path to the date-specific logging directory
            
        Returns:
            int: Next print number (1-indexed)
        """
        next_print_num = 1
        if os.path.exists(date_specific_log_dir):
            try:
                entries = os.listdir(date_specific_log_dir)
                print_nums = []
                for entry in entries:
                    if os.path.isdir(os.path.join(date_specific_log_dir, entry)) and entry.startswith("Print "):
                        parts = entry.split(" - ")
                        if len(parts) > 0:  # Check if split produced at least one part
                            num_part = parts[0].replace("Print ", "").strip()
                            if num_part.isdigit():
                                print_nums.append(int(num_part))
                if print_nums:
                    next_print_num = max(print_nums) + 1
            except Exception as e:
                self.parent.update_status_message(f"Error determining next print number: {e}", error=True)
                # Fallback to 1 on error
        return next_print_num
    
    def save_gui_state(self):
        """Save current GUI state to JSON file."""
        try:
            state = {
                # File paths
                'directory': self.parent.t1.get(),
                'reference': self.parent.reference,
                
                # GUI entry fields
                'move_distance': self.parent.t9.get(),
                'layer_thickness': self.parent.t10.get(),
                'layer_pause': self.parent.t11.get(),
                'overstep': self.parent.t11_2.get(),
                'offset': self.parent.t14.get(),
                
                # Feature set is intentionally minimal for Rush build.
                'sensor_settings': {}
            }
            
            # Sensor panel state is intentionally not persisted in Rush.
            
            # Save to file in the same directory as Rush_Segmented_VideoPattern.py
            state_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'rush_gui_state.json')
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
            
            self.parent.update_status_message(f"GUI state saved to {os.path.basename(state_file)}")
            
        except Exception as e:
            self.parent.update_status_message(f"Error saving GUI state: {e}", error=True)
            traceback.print_exc()
    
    def load_gui_state(self):
        """Load GUI state from JSON file."""
        try:
            state_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'rush_gui_state.json')
            
            if not os.path.exists(state_file):
                self.parent.update_status_message("No saved state found. Use 'Save State' to create one.")
                return
            
            with open(state_file, 'r') as f:
                state = json.load(f)
            
            # Restore file paths
            if 'directory' in state and state['directory']:
                self.parent.t1.delete(0, END)
                self.parent.t1.insert(0, state['directory'])
                # Try to load the directory
                try:
                    self.parent.input_directory()
                except:
                    pass
            
            if 'reference' in state:
                self.parent.reference = state['reference']
            
            # Restore GUI entry fields
            if 'move_distance' in state:
                self.parent.t9.delete(0, END)
                self.parent.t9.insert(0, state['move_distance'])
            
            if 'layer_thickness' in state:
                self.parent.t10.delete(0, END)
                self.parent.t10.insert(0, state['layer_thickness'])
            
            if 'layer_pause' in state:
                self.parent.t11.delete(0, END)
                self.parent.t11.insert(0, state['layer_pause'])
            
            if 'overstep' in state:
                self.parent.t11_2.delete(0, END)
                self.parent.t11_2.insert(0, state['overstep'])
            
            if 'offset' in state:
                self.parent.t14.delete(0, END)
                self.parent.t14.insert(0, state['offset'])
            
            self.parent.update_status_message(f"GUI state loaded from {os.path.basename(state_file)}")
            
        except Exception as e:
            self.parent.update_status_message(f"Error loading GUI state: {e}", error=True)
            traceback.print_exc()
    
    def trigger_post_print_analysis(self):
        """
        Trigger automated post-print analysis and plot generation.
        This runs whether the print completed successfully or was stopped early.
        """
        try:
            self.parent.update_status_message("Starting post-print analysis...")
            
            # Rush stores the active print folder directly on the main window.
            analysis_dir = self.parent.current_print_session_log_dir
            
            # Check if we have a valid log directory
            if not analysis_dir:
                self.parent.update_status_message("No log directory available for post-print analysis.")
                return
            
            if not os.path.exists(analysis_dir):
                self.parent.update_status_message(f"Log directory does not exist for post-print analysis: {analysis_dir}")
                return
            
            # Update the stored path for use below
            self.parent.current_print_session_log_dir = analysis_dir
            
            # Import and run post-print analyzer
            import sys
            from pathlib import Path
            
            # Add post-processing directory to path if not already there
            post_processing_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'post-processing')
            if post_processing_dir not in sys.path:
                sys.path.insert(0, post_processing_dir)
            
            from post_print_analyzer import PostPrintAnalyzer
            
            analyzer = PostPrintAnalyzer()
            
            # Get the daily log directory (parent of current print session)
            daily_log_dir = os.path.dirname(self.parent.current_print_session_log_dir)
            
            # Find only the current session (most recent) instead of all sessions
            # Use the PostPrintAnalyzer method to find current session in daily directory
            current_session = analyzer.find_current_session_in_daily_dir(daily_log_dir)
            
            if not current_session:
                self.parent.update_status_message("Post-print analysis: No current session found.")
                return
            
            # Analyze the current session and track results
            total_plots = 0
            processed_sessions = 0
            
            try:
                session_results = analyzer.analyze_print_session(current_session)
                if session_results:
                    processed_sessions += 1
                    
                    # Count plots generated
                    plots_count = len([r for r in session_results if r.get('plot_path')])
                    total_plots += plots_count
                    
                    # Count total layers processed across all CSV files in this session
                    total_layers = sum(len(r.get('layers', [])) for r in session_results)
                    
                    if plots_count > 0:
                        session_name = f"{current_session['date']}/{current_session['print_number']}"
                        self.parent.update_status_message(f"  📊 {session_name}: {total_layers} layers → {plots_count} plots")
                        
            except Exception as e:
                print(f"Error analyzing current session {current_session.get('print_number', 'Unknown')}: {e}")
        
            if processed_sessions > 0:
                self.parent.update_status_message(f"Post-print analysis complete: {processed_sessions} session, {total_plots} plots generated.")
            else:
                self.parent.update_status_message("Post-print analysis: No suitable data found for plotting.")
                
        except Exception as e:
            self.parent.update_status_message(f"Error in post-print analysis: {e}")
            import traceback
            traceback.print_exc()
