"""
Experimental Conditions Window
================================

A dedicated window for recording experimental conditions and metadata for each print.
Saves data to CSV files in the print's autolog folder and tracks print status including
automatic failure detection based on force trends.

Author: Cheng Sun Lab Team
Date: November 25, 2025
"""

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import csv
from pathlib import Path
from datetime import datetime
import threading


class PrintFailureDetector:
    """
    Monitors peak force trends across layers to detect potential print failures.
    
    Triggers "Possibly Failed" status if 10 consecutive layers show >=5% force decrease.
    """
    
    def __init__(self, callback=None):
        """
        Initialize the failure detector.
        
        Args:
            callback: Optional function to call when failure is detected
        """
        self.consecutive_decreases = 0
        self.last_peak_force = None
        self.failure_detected = False
        self.callback = callback
        self.layer_history = []  # Track (layer_num, peak_force) for debugging
        self.lock = threading.Lock()
    
    def reset(self):
        """Reset detector state for a new print."""
        with self.lock:
            self.consecutive_decreases = 0
            self.last_peak_force = None
            self.failure_detected = False
            self.layer_history = []
            print("PrintFailureDetector: Reset for new print")
    
    def check_layer(self, layer_number, peak_force):
        """
        Check if current layer indicates potential failure.
        
        Args:
            layer_number: Current layer number
            peak_force: Peak adhesion force for this layer (N)
        
        Returns:
            bool: True if failure detected on this check
        """
        with self.lock:
            # Skip if already detected failure
            if self.failure_detected:
                return False
            
            # Record in history
            self.layer_history.append((layer_number, peak_force))
            
            # First layer - just record
            if self.last_peak_force is None:
                self.last_peak_force = peak_force
                print(f"Failure Detector L{layer_number}: Baseline force = {peak_force:.4f}N")
                return False
            
            # Calculate decrease percentage
            decrease_percent = ((self.last_peak_force - peak_force) / self.last_peak_force) * 100
            
            # Check if decreased by at least 5%
            if decrease_percent >= 5.0:
                self.consecutive_decreases += 1
                print(f"Failure Detector L{layer_number}: Force decreased {decrease_percent:.1f}% "
                      f"({self.last_peak_force:.4f}N → {peak_force:.4f}N) - "
                      f"Count: {self.consecutive_decreases}/10")
                
                # Check threshold
                if self.consecutive_decreases >= 10:
                    self.failure_detected = True
                    print(f"⚠️ FAILURE DETECTED at Layer {layer_number}: "
                          f"10 consecutive layers with >=5% force decrease")
                    
                    # Call callback if provided
                    if self.callback:
                        try:
                            self.callback(layer_number)
                        except Exception as e:
                            print(f"Error in failure detector callback: {e}")
                    
                    return True
            else:
                # Reset counter if no significant decrease
                if self.consecutive_decreases > 0:
                    print(f"Failure Detector L{layer_number}: Force increased or stable - "
                          f"reset counter (was {self.consecutive_decreases})")
                self.consecutive_decreases = 0
            
            # Update baseline for next comparison
            self.last_peak_force = peak_force
            return False
    
    def get_status_string(self):
        """Get current status as a string."""
        if self.failure_detected:
            return "Possible Failure"
        return "In Progress"


class ExperimentalConditionsWindow:
    """
    Window for inputting and tracking experimental conditions for prints.
    """
    
    def __init__(self, parent_window, update_status_callback=None):
        """
        Initialize the experimental conditions window.
        
        Args:
            parent_window: Parent tkinter window
            update_status_callback: Function to call with status messages
        """
        self.parent = parent_window
        self.update_status = update_status_callback or self._default_status_update
        
        # Create window
        self.window = tk.Toplevel(parent_window)
        self.window.title("Experimental Conditions")
        self.window.geometry("700x650")
        self.window.protocol("WM_DELETE_WINDOW", self.hide_window)
        
        # Initialize failure detector
        self.failure_detector = PrintFailureDetector(callback=self._on_failure_detected)
        
        # State variables
        self.logging_enabled = tk.BooleanVar(value=True)
        self.current_print_dir = None
        self.current_csv_file = None
        self.print_status = "Not Started"
        
        # Build UI
        self._build_ui()
        
        # Hide initially
        self.window.withdraw()
        
        print("ExperimentalConditionsWindow initialized")
    
    def _default_status_update(self, message, error=False):
        """Default status update if no callback provided."""
        print(f"ExpConditions: {message}")
    
    def _build_ui(self):
        """Build the user interface."""
        # Main container with padding
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(main_frame, text="Experimental Conditions", 
                               font=('Helvetica', 14, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 10))
        
        # Enable/Disable checkbox
        self.enable_check = ttk.Checkbutton(main_frame, text="Enable Experimental Conditions Logging",
                                            variable=self.logging_enabled,
                                            command=self._on_enable_toggle)
        self.enable_check.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(0, 15))
        
        # Input fields frame
        fields_frame = ttk.LabelFrame(main_frame, text="Conditions", padding="10")
        fields_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Create entry fields
        row = 0
        self.entries = {}
        
        fields = [
            ("User:", "user", 30),
            ("Membrane Type:", "membrane_type", 30),
            ("TEMPO Pattern:", "tempo_pattern", 50),
            ("Oil:", "oil", 30),
            ("Fluid Type:", "fluid_type", 30),
            ("Fluid Gap (mm):", "fluid_gap", 15),
            ("Tank:", "tank", 30),
            ("Resin:", "resin", 50),
            ("Build Platform:", "build_platform", 30),
        ]
        
        for label_text, field_name, width in fields:
            label = ttk.Label(fields_frame, text=label_text)
            label.grid(row=row, column=0, sticky=tk.W, pady=2)
            
            entry = ttk.Entry(fields_frame, width=width)
            entry.grid(row=row, column=1, sticky=tk.W, padx=(5, 0), pady=2)
            self.entries[field_name] = entry
            row += 1
        
        # Status display (read-only)
        status_frame = ttk.LabelFrame(main_frame, text="Print Status", padding="10")
        status_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 10))
        
        self.status_var = tk.StringVar(value="Not Started")
        status_display = ttk.Label(status_frame, textvariable=self.status_var, 
                                   font=('Helvetica', 10, 'bold'))
        status_display.grid(row=0, column=0, sticky=tk.W)
        
        # Current file display
        file_frame = ttk.LabelFrame(main_frame, text="Current Log File", padding="10")
        file_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.file_var = tk.StringVar(value="No active print")
        file_display = ttk.Label(file_frame, textvariable=self.file_var, 
                                 font=('Helvetica', 8), wraplength=650)
        file_display.grid(row=0, column=0, sticky=tk.W)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=(10, 0))
        
        self.save_button = ttk.Button(button_frame, text="Save Current Conditions", 
                                      command=self._save_conditions)
        self.save_button.grid(row=0, column=0, padx=5)
        
        self.clear_button = ttk.Button(button_frame, text="Clear All Fields", 
                                       command=self._clear_fields)
        self.clear_button.grid(row=0, column=1, padx=5)
        
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
    
    def _save_conditions(self):
        """Manually save current conditions to CSV."""
        if not self.logging_enabled.get():
            messagebox.showwarning("Logging Disabled", 
                                  "Experimental conditions logging is disabled. Enable it first.")
            return
        
        if not self.current_csv_file:
            messagebox.showwarning("No Active Print", 
                                  "No active print session. Start a print first.")
            return
        
        try:
            self._write_conditions_to_csv()
            messagebox.showinfo("Saved", "Conditions saved successfully!")
            self.update_status("Experimental conditions saved manually")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save conditions: {e}")
            self.update_status(f"Error saving conditions: {e}", error=True)
    
    def start_new_print(self, print_directory):
        """
        Start a new print session - creates CSV file and resets failure detector.
        
        Args:
            print_directory: Path to the print's log directory
        """
        if not self.logging_enabled.get():
            print("Experimental conditions logging is disabled - skipping")
            return
        
        try:
            self.current_print_dir = Path(print_directory)
            self.current_print_dir.mkdir(parents=True, exist_ok=True)
            
            # Create CSV file
            self.current_csv_file = self.current_print_dir / "experimental_conditions.csv"
            
            # Reset failure detector
            self.failure_detector.reset()
            self.print_status = "In Progress"
            self.status_var.set("In Progress")
            
            # Write initial conditions
            self._write_conditions_to_csv()
            
            self.file_var.set(str(self.current_csv_file))
            self.update_status(f"Experimental conditions logging started: {self.current_csv_file.name}")
            
        except Exception as e:
            self.update_status(f"Error starting experimental conditions logging: {e}", error=True)
            print(f"Error in start_new_print: {e}")
            import traceback
            traceback.print_exc()
    
    def _write_conditions_to_csv(self):
        """Write current conditions to CSV file."""
        if not self.current_csv_file:
            return
        
        # Collect data
        data = {
            'Print_Date_Time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'User': self.entries['user'].get() or 'N/A',
            'Printer': 'Prince',
            'Membrane_Type': self.entries['membrane_type'].get() or 'N/A',
            'TEMPO_Pattern': self.entries['tempo_pattern'].get() or 'N/A',
            'Oil': self.entries['oil'].get() or 'N/A',
            'Fluid_Type': self.entries['fluid_type'].get() or 'N/A',
            'Fluid_Gap_mm': self.entries['fluid_gap'].get() or 'N/A',
            'Tank': self.entries['tank'].get() or 'N/A',
            'Resin': self.entries['resin'].get() or 'N/A',
            'Build_Platform': self.entries['build_platform'].get() or 'N/A',
            'Print_Status': self.print_status
        }
        
        # Check if file exists to determine if we need headers
        file_exists = self.current_csv_file.exists()
        
        # Write to CSV
        with open(self.current_csv_file, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=data.keys())
            
            if not file_exists:
                writer.writeheader()
            
            writer.writerow(data)
        
        print(f"Experimental conditions written to {self.current_csv_file.name}")
    
    def update_layer_force(self, layer_number, peak_force):
        """
        Update failure detector with new layer data.
        
        Args:
            layer_number: Layer number
            peak_force: Peak adhesion force (N)
        """
        if not self.logging_enabled.get():
            return
        
        if self.print_status not in ["In Progress", "Possible Failure"]:
            return
        
        # Check for failure
        self.failure_detector.check_layer(layer_number, peak_force)
    
    def _on_failure_detected(self, layer_number):
        """Callback when failure is detected."""
        self.print_status = "Possible Failure"
        self.status_var.set("Possible Failure ⚠️")
        
        # Update CSV with new status
        try:
            self._write_conditions_to_csv()
        except Exception as e:
            print(f"Error updating CSV on failure detection: {e}")
        
        self.update_status(f"⚠️ Possible print failure detected at layer {layer_number}", error=True)
        print(f"\n{'='*60}")
        print(f"⚠️ POSSIBLE PRINT FAILURE DETECTED")
        print(f"Layer: {layer_number}")
        print(f"Reason: 10 consecutive layers with >=5% force decrease")
        print(f"{'='*60}\n")
    
    def end_print(self, success=True):
        """
        End current print session and update status.
        
        Args:
            success: True if print completed successfully
        """
        if not self.logging_enabled.get() or not self.current_csv_file:
            return
        
        # Determine final status
        if self.print_status == "Possible Failure":
            final_status = "Possible Failure"
            folder_suffix = " - Possible Failure"
        elif success:
            final_status = "Complete"
            folder_suffix = " - Complete"
        else:
            final_status = "Stopped/Failed"
            folder_suffix = " - Stopped"
        
        self.print_status = final_status
        self.status_var.set(final_status)
        
        # Write final status to CSV
        try:
            self._write_conditions_to_csv()
        except Exception as e:
            print(f"Error writing final status: {e}")
        
        # Rename folder with status suffix
        try:
            if self.current_print_dir and self.current_print_dir.exists():
                new_name = self.current_print_dir.name + folder_suffix
                new_path = self.current_print_dir.parent / new_name
                
                # Only rename if not already suffixed
                if not self.current_print_dir.name.endswith(folder_suffix):
                    self.current_print_dir.rename(new_path)
                    self.current_print_dir = new_path
                    self.current_csv_file = new_path / "experimental_conditions.csv"
                    self.file_var.set(str(self.current_csv_file))
                    self.update_status(f"Print folder renamed: {new_name}")
        except Exception as e:
            print(f"Error renaming print folder: {e}")
        
        self.update_status(f"Print ended with status: {final_status}")
    
    def is_logging_enabled(self):
        """Check if logging is enabled."""
        return self.logging_enabled.get()
    
    def get_failure_detector(self):
        """Get the failure detector instance."""
        return self.failure_detector


if __name__ == "__main__":
    # Test the window
    root = tk.Tk()
    root.title("Test Parent Window")
    root.geometry("400x200")
    
    def test_callback(msg, error=False):
        print(f"{'ERROR: ' if error else ''}{msg}")
    
    exp_window = ExperimentalConditionsWindow(root, test_callback)
    
    # Add test button
    def open_window():
        exp_window.show_window()
    
    def start_test_print():
        import tempfile
        test_dir = Path(tempfile.gettempdir()) / "test_print"
        exp_window.start_new_print(test_dir)
        print(f"Test print started in: {test_dir}")
    
    btn = tk.Button(root, text="Open Experimental Conditions", command=open_window)
    btn.pack(pady=20)
    
    btn2 = tk.Button(root, text="Start Test Print", command=start_test_print)
    btn2.pack(pady=10)
    
    root.mainloop()
