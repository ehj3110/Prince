"""
Logging Check Window - VideoPattern
===================================

A post-print popup dialog for recording print completion status and notes.
Blocks next print until quality check is complete and data is saved.

Author: Cheng Sun Lab Team
Date: April 12, 2026
"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime


class LoggingCheckWindow_VideoPattern:
    """
    Post-print popup for logging check and completion status.
    Displays print number, allows status selection (Finished/Failed),
    captures notes, handles quality-check gating.
    """
    
    def __init__(self, parent_window, print_number, on_close_callback=None):
        """
        Initialize the Logging Check window.
        
        Args:
            parent_window: Parent tkinter window
            print_number: Print number (e.g., "1", "2") for display
            on_close_callback: Function to call when closing with (status, notes, wait_for_qc)
                               status: 'Finished' or 'Failed'
                               notes: text from notes field
                               wait_for_qc: True if waiting for quality check
        """
        self.parent = parent_window
        self.print_number = print_number
        self.on_close_callback = on_close_callback
        
        # State
        self.status_var = tk.StringVar(value="")  # "Finished" or "Failed"
        self.wait_for_qc_var = tk.BooleanVar(value=False)
        self.result = None  # Will be set when dialog closes
        
        # Create top-level window
        self.window = tk.Toplevel(parent_window)
        self.window.title(f"Print - {print_number}")
        self.window.geometry("500x400")
        self.window.protocol("WM_DELETE_WINDOW", self._on_close_request)
        
        # Make modal - grab focus
        self.window.grab_set()
        
        # Build UI
        self._build_ui()
        
        # Center on parent
        self.window.update_idletasks()
        x = parent_window.winfo_x() + (parent_window.winfo_width() // 2) - (self.window.winfo_width() // 2)
        y = parent_window.winfo_y() + (parent_window.winfo_height() // 2) - (self.window.winfo_height() // 2)
        self.window.geometry(f"+{x}+{y}")
        
        print(f"LoggingCheckWindow_VideoPattern initialized for Print {print_number}")
    
    def _build_ui(self):
        """Build the user interface."""
        # Main container
        main_frame = ttk.Frame(self.window, padding="15")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights for resizing
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        # Heading
        heading_label = ttk.Label(main_frame, text="Logging Check", 
                                 font=('Helvetica', 14, 'bold'))
        heading_label.grid(row=0, column=0, columnspan=2, pady=(0, 10), sticky=tk.W)
        
        # Print info
        info_text = f"Print #{self.print_number} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        info_label = ttk.Label(main_frame, text=info_text, 
                              font=('Helvetica', 10))
        info_label.grid(row=1, column=0, columnspan=2, pady=(0, 15), sticky=tk.W)
        
        # Status selection (Finished/Failed)
        status_frame = ttk.LabelFrame(main_frame, text="Print Status", padding="10")
        status_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        finished_radio = ttk.Radiobutton(status_frame, text="Finished", 
                                        variable=self.status_var, value="Finished")
        finished_radio.grid(row=0, column=0, sticky=tk.W, padx=(0, 20))
        
        failed_radio = ttk.Radiobutton(status_frame, text="Failed", 
                                      variable=self.status_var, value="Failed")
        failed_radio.grid(row=0, column=1, sticky=tk.W)
        
        # Notes section
        notes_label = ttk.Label(main_frame, text="Notes (optional):", font=('Helvetica', 10))
        notes_label.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(10, 5))
        
        # Notes textbox
        notes_frame = ttk.Frame(main_frame)
        notes_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        notes_frame.columnconfigure(0, weight=1)
        notes_frame.rowconfigure(0, weight=1)
        
        self.notes_text = tk.Text(notes_frame, height=8, width=50, wrap=tk.WORD)
        self.notes_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbar for notes
        scrollbar = ttk.Scrollbar(notes_frame, orient=tk.VERTICAL, command=self.notes_text.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.notes_text.config(yscrollcommand=scrollbar.set)
        
        # Wait for quality check checkbox
        qc_frame = ttk.LabelFrame(main_frame, text="Quality Check", padding="10")
        qc_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        qc_check = ttk.Checkbutton(qc_frame, text="Wait for Quality Check (blocks next print)",
                                   variable=self.wait_for_qc_var)
        qc_check.grid(row=0, column=0, sticky=tk.W)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
        save_button = ttk.Button(button_frame, text="Close and Save", 
                                command=self._on_save)
        save_button.pack(side=tk.LEFT, padx=5)
        
        # Bind Enter key to close
        self.window.bind('<Return>', lambda e: self._on_save())
    
    def _on_save(self):
        """Handle save button click."""
        # Validate status selection
        if not self.status_var.get():
            import tkinter.messagebox as messagebox
            messagebox.showwarning("Missing Status", "Please select Finished or Failed")
            return
        
        # Capture result
        self.result = {
            'status': self.status_var.get(),
            'notes': self.notes_text.get("1.0", tk.END).strip(),
            'wait_for_qc': self.wait_for_qc_var.get(),
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        print(f"Logging check result: {self.result}")
        
        # Call callback if provided
        if self.on_close_callback:
            try:
                self.on_close_callback(self.result)
            except Exception as e:
                print(f"Error in on_close_callback: {e}")
        
        # Close window
        self.window.destroy()
    
    def _on_close_request(self):
        """Handle window close request."""
        # Don't allow closing without saving
        import tkinter.messagebox as messagebox
        if messagebox.askyesno("Close Without Saving?", 
                              "Close without saving logging data?"):
            self.window.destroy()
    
    def wait_for_result(self):
        """
        Wait for user to complete the dialog and return result.
        
        Returns:
            dict: Result with keys: status, notes, wait_for_qc, timestamp
        """
        self.window.wait_window()
        return self.result


if __name__ == "__main__":
    # Test the window
    root = tk.Tk()
    root.title("Test Parent Window")
    root.geometry("400x200")
    
    def test_callback(result):
        print(f"Dialog result: {result}")
    
    def open_dialog():
        dialog = LoggingCheckWindow_VideoPattern(root, "1", test_callback)
        root.after(100, lambda: print(f"Dialog result: {dialog.wait_for_result()}"))
    
    btn = tk.Button(root, text="Open Logging Check", command=open_dialog)
    btn.pack(pady=20)
    
    root.mainloop()
