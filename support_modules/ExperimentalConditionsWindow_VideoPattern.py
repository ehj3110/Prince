"""
Experimental Conditions Window - VideoPattern Version
=====================================================

A simplified window for recording experimental conditions specific to VideoPattern prints.
Only 4 fields: User, Membrane, Resin, Pre-print notes.
Data is saved and handed off to VideoPatternPrintLogging for persistence.

Author: Cheng Sun Lab Team
Date: April 12, 2026
"""

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import csv
from pathlib import Path
from datetime import datetime
import threading


class ExperimentalConditionsWindow_VideoPattern:
    """
    Simplified window for inputting experimental conditions for VideoPattern prints.
    Reduced to 4 essential fields only.
    """
    
    def __init__(self, parent_window, update_status_callback=None):
        """
        Initialize the VideoPattern experimental conditions window.
        
        Args:
            parent_window: Parent tkinter window
            update_status_callback: Function to call with status messages
        """
        self.parent = parent_window
        self.update_status = update_status_callback or self._default_status_update
        
        # Create window
        self.window = tk.Toplevel(parent_window)
        self.window.title("Experimental Conditions - VideoPattern")
        self.window.geometry("600x300")
        self.window.protocol("WM_DELETE_WINDOW", self.hide_window)
        
        # State variables
        self.logging_enabled = tk.BooleanVar(value=True)
        self.current_conditions = {}  # Store current conditions for passing to logging service
        
        # Build UI
        self._build_ui()
        
        # Hide initially
        self.window.withdraw()
        
        print("ExperimentalConditionsWindow_VideoPattern initialized")
    
    def _default_status_update(self, message, error=False):
        """Default status update if no callback provided."""
        print(f"ExpConditions_VP: {message}")
    
    def _build_ui(self):
        """Build the user interface."""
        # Main container with padding
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(main_frame, text="VideoPattern Print Conditions", 
                               font=('Helvetica', 12, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 10))
        
        # Enable/Disable checkbox
        self.enable_check = ttk.Checkbutton(main_frame, text="Enable Conditions Logging",
                                            variable=self.logging_enabled,
                                            command=self._on_enable_toggle)
        self.enable_check.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(0, 15))
        
        # Input fields frame with 4 fields only
        fields_frame = ttk.LabelFrame(main_frame, text="Print Information", padding="10")
        fields_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Create entry fields - only 4 fields
        row = 0
        self.entries = {}
        
        fields = [
            ("User:", "user", 30),
            ("Membrane Type:", "membrane", 30),
            ("Resin:", "resin", 40),
            ("Pre-print Notes:", "preprint_notes", 60),
        ]
        
        for label_text, field_name, width in fields:
            label = ttk.Label(fields_frame, text=label_text)
            label.grid(row=row, column=0, sticky=tk.W, pady=5)
            
            entry = ttk.Entry(fields_frame, width=width)
            entry.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=5)
            self.entries[field_name] = entry
            row += 1
        
        # Configure column weights for resizing
        fields_frame.columnconfigure(1, weight=1)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=(10, 0))
        
        self.clear_button = ttk.Button(button_frame, text="Clear All Fields", 
                                       command=self._clear_fields)
        self.clear_button.grid(row=0, column=1, padx=5)
        
        self.save_button = ttk.Button(button_frame, text="Save & Reserve Session", 
                                      command=self._save_and_reserve)
        self.save_button.grid(row=0, column=0, padx=5)
        
        close_button = ttk.Button(button_frame, text="Close", command=self.hide_window)
        close_button.grid(row=0, column=2, padx=5)
    
    def show_window(self):
        """Show the window."""
        self.window.deiconify()
        self.window.lift()
        self.window.focus_force()
    
    def hide_window(self):
        """Hide the window."""
        self.window.withdraw()
    
    def _on_enable_toggle(self):
        """Handle enable/disable toggle."""
        if self.logging_enabled.get():
            self.update_status("Experimental conditions logging enabled")
        else:
            self.update_status("Experimental conditions logging disabled")
    
    def _clear_fields(self):
        """Clear all input fields."""
        for entry in self.entries.values():
            entry.delete(0, tk.END)
        self.update_status("All fields cleared")
        def _save_and_reserve(self):
            """Save current conditions and reserve a print session for today.
        
            If no print is currently active, attempts to reserve a Print N session for today.
            """
            if not self.logging_enabled.get():
                messagebox.showwarning("Logging Disabled", 
                                      "Experimental conditions logging is disabled. Enable it first.")
                return
        
            # Try to reserve a session if main app reference exists
            if hasattr(self, 'prince_main_app_ref') and self.prince_main_app_ref:
                try:
                    reserved_dir = self.prince_main_app_ref.reserve_print_session_for_conditions()
                
                    # Capture conditions to current_conditions
                    self.current_conditions = self.get_conditions()
                
                    messagebox.showinfo("Session Reserved", 
                        f"VideoPattern conditions reserved for today.\nSession: {Path(reserved_dir).name}\n"
                        f"User: {self.current_conditions.get('user', 'N/A')}")
                    self.update_status("VideoPattern conditions reserved for print session")
                except Exception as e:
                    messagebox.showerror("Reservation Error", 
                        f"Could not reserve print session:\n{e}")
                    self.update_status(f"Error reserving print session: {e}", error=True)
            else:
                messagebox.showwarning("No Main App Reference", 
                                      "Cannot reserve session. Please set image directory and try again.")
                self.update_status("Error: No main app reference for session reservation", error=True)
    
    
    def start_new_print(self, print_directory):
        """
        Prepare for a new print session - capture current field values.
        This doesn't write to disk; VideoPatternPrintLogging handles persistence.
        
        Args:
            print_directory: Path to the print's log directory (for reference)
        """
        if not self.logging_enabled.get():
            print("VideoPattern conditions logging is disabled - skipping")
            return
        
        try:
            # Capture current conditions
            self.current_conditions = {
                'user': self.entries['user'].get() or 'N/A',
                'membrane': self.entries['membrane'].get() or 'N/A',
                'resin': self.entries['resin'].get() or 'N/A',
                'preprint_notes': self.entries['preprint_notes'].get() or 'N/A',
            }
            
            self.update_status(f"VideoPattern print conditions captured for: {self.current_conditions.get('user', 'Unknown')}")
            print(f"VideoPattern conditions: {self.current_conditions}")
            
        except Exception as e:
            self.update_status(f"Error capturing conditions: {e}", error=True)
            print(f"Error in start_new_print: {e}")
            import traceback
            traceback.print_exc()
    
    def get_conditions(self):
        """
        Get the current conditions as a dictionary.
        
        Returns:
            dict: Current condition values
        """
        return {
            'user': self.entries['user'].get() or 'N/A',
            'membrane': self.entries['membrane'].get() or 'N/A',
            'resin': self.entries['resin'].get() or 'N/A',
            'preprint_notes': self.entries['preprint_notes'].get() or 'N/A',
        }
    
    def end_print(self, success=True):
        """
        End current print session.
        For VideoPattern, this is mostly a placeholder as logging is handled by VideoPatternPrintLogging.
        
        Args:
            success: True if print completed successfully
        """
        # Conditions data is already captured; VideoPatternPrintLogging handles final write
        self.update_status("Print ended" + (" successfully" if success else " with failure"))
    
    def is_logging_enabled(self):
        """Check if logging is enabled."""
        return self.logging_enabled.get()


if __name__ == "__main__":
    # Test the window
    root = tk.Tk()
    root.title("Test Parent Window")
    root.geometry("400x200")
    
    def test_callback(msg, error=False):
        print(f"{'ERROR: ' if error else ''}{msg}")
    
    exp_window = ExperimentalConditionsWindow_VideoPattern(root, test_callback)
    
    # Add test button
    def open_window():
        exp_window.show_window()
    
    btn = tk.Button(root, text="Open VideoPattern Conditions", command=open_window)
    btn.pack(pady=20)
    
    root.mainloop()
