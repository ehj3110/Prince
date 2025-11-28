# Camera Integration Guide

How to integrate the Allied Vision camera window into the Prince_Segmented.py main application.

## Overview

The camera viewing window is designed to be easily integrated into the main GUI as a separate window (similar to how SensorDataWindow works).

## Integration Steps

### 1. Import Camera Module

Add to imports section in `Prince_Segmented.py`:

```python
from calibration_modules import CameraViewWindow
```

### 2. Add Camera Window Reference

In the main application class `__init__` method:

```python
class YourMainApplication:
    def __init__(self, root):
        self.root = root
        
        # ... existing initialization ...
        
        # Camera window reference
        self.camera_window = None
```

### 3. Add Menu Item or Button

**Option A: Add to Menu Bar**

```python
def create_menus(self):
    """Create application menu bar"""
    menubar = tk.Menu(self.root)
    
    # ... existing menus ...
    
    # Camera menu
    camera_menu = tk.Menu(menubar, tearoff=0)
    camera_menu.add_command(
        label="Open Camera View",
        command=self.open_camera_window
    )
    menubar.add_cascade(label="Camera", menu=camera_menu)
    
    self.root.config(menu=menubar)
```

**Option B: Add Button to Toolbar**

```python
def create_toolbar(self):
    """Create toolbar with buttons"""
    toolbar = ttk.Frame(self.root)
    toolbar.pack(side=tk.TOP, fill=tk.X)
    
    # ... existing buttons ...
    
    # Camera button
    camera_btn = ttk.Button(
        toolbar,
        text="Camera",
        command=self.open_camera_window
    )
    camera_btn.pack(side=tk.LEFT, padx=2)
```

### 4. Implement Window Opening Method

```python
def open_camera_window(self):
    """Open camera viewing window"""
    try:
        # Check if window already exists
        if self.camera_window is not None:
            # Check if window is still open
            if self.camera_window.window.winfo_exists():
                # Bring existing window to front
                self.camera_window.window.lift()
                self.camera_window.window.focus_force()
                return
        
        # Create new camera window
        self.camera_window = CameraViewWindow(parent=self.root)
        
    except Exception as e:
        messagebox.showerror(
            "Camera Error",
            f"Failed to open camera window:\n{e}"
        )
```

### 5. Optional: Add Status Indicator

Show camera connection status in main window:

```python
def create_status_bar(self):
    """Create status bar"""
    status_frame = ttk.Frame(self.root)
    status_frame.pack(side=tk.BOTTOM, fill=tk.X)
    
    # ... existing status items ...
    
    # Camera status
    self.camera_status_label = ttk.Label(
        status_frame,
        text="Camera: Not connected",
        relief=tk.SUNKEN
    )
    self.camera_status_label.pack(side=tk.RIGHT, padx=2)

def update_camera_status(self):
    """Update camera connection status"""
    if self.camera_window and self.camera_window.camera_manager.camera:
        self.camera_status_label.config(text="Camera: Connected")
    else:
        self.camera_status_label.config(text="Camera: Not connected")
```

## Complete Integration Example

```python
# In Prince_Segmented.py

import tkinter as tk
from tkinter import ttk, messagebox

# ... other imports ...
from calibration_modules import CameraViewWindow


class PrinceApplication:
    """Main application class"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Prince - Adhesion Testing System")
        
        # Camera window reference
        self.camera_window = None
        
        # Create GUI
        self.create_menus()
        self.create_main_interface()
        
    def create_menus(self):
        """Create menu bar"""
        menubar = tk.Menu(self.root)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(
            label="Camera View",
            command=self.open_camera_window
        )
        tools_menu.add_command(
            label="Sensor Data",
            command=self.open_sensor_window  # existing
        )
        menubar.add_cascade(label="Tools", menu=tools_menu)
        
        self.root.config(menu=menubar)
    
    def create_main_interface(self):
        """Create main interface"""
        # Your existing main interface code
        pass
    
    def open_camera_window(self):
        """Open camera viewing window"""
        try:
            # Check if window already exists and is open
            if self.camera_window is not None:
                if self.camera_window.window.winfo_exists():
                    self.camera_window.window.lift()
                    self.camera_window.window.focus_force()
                    return
            
            # Create new camera window
            self.camera_window = CameraViewWindow(parent=self.root)
            
        except ImportError:
            messagebox.showerror(
                "Import Error",
                "Camera modules not available.\n\n"
                "Make sure calibration_modules package is installed."
            )
        except Exception as e:
            messagebox.showerror(
                "Camera Error",
                f"Failed to open camera window:\n{e}"
            )


if __name__ == "__main__":
    root = tk.Tk()
    app = PrinceApplication(root)
    root.mainloop()
```

## Testing Integration

1. **Start Application:**
   ```powershell
   python Prince_Segmented.py
   ```

2. **Open Camera Window:**
   - Click "Tools" → "Camera View" (or click Camera button)

3. **Test Camera:**
   - Window should open automatically
   - Try connecting to camera
   - Test streaming if camera is available

## Keyboard Shortcuts (Optional)

Add keyboard shortcuts for quick access:

```python
def setup_keybindings(self):
    """Setup keyboard shortcuts"""
    # ... existing keybindings ...
    
    # Camera window: Ctrl+K
    self.root.bind('<Control-k>', lambda e: self.open_camera_window())
```

## Error Handling

Handle common issues gracefully:

```python
def open_camera_window(self):
    """Open camera window with error handling"""
    try:
        # Check if Vimba is available
        try:
            from vimba import Vimba
            vimba_available = True
        except ImportError:
            vimba_available = False
        
        if not vimba_available:
            response = messagebox.askyesno(
                "Vimba SDK Not Found",
                "Allied Vision Vimba SDK is not installed.\n\n"
                "The camera window will open but camera functionality "
                "will be limited.\n\n"
                "Would you like to continue?"
            )
            if not response:
                return
        
        # Open window
        if self.camera_window is not None and self.camera_window.window.winfo_exists():
            self.camera_window.window.lift()
        else:
            self.camera_window = CameraViewWindow(parent=self.root)
            
    except Exception as e:
        messagebox.showerror("Error", f"Failed to open camera window:\n{e}")
```

## Cleanup on Exit

Ensure camera is properly disconnected when main application closes:

```python
def on_closing(self):
    """Handle application exit"""
    try:
        # Close camera window if open
        if self.camera_window is not None:
            if self.camera_window.window.winfo_exists():
                self.camera_window.on_closing()
        
        # ... other cleanup ...
        
        self.root.destroy()
        
    except Exception as e:
        print(f"Error during cleanup: {e}")
        self.root.destroy()

# In __init__:
self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
```

## Multiple Instances

Prevent multiple camera windows:

```python
def open_camera_window(self):
    """Open camera window (single instance)"""
    # Check if window exists and is open
    if self.camera_window is not None:
        try:
            if self.camera_window.window.winfo_exists():
                # Window already open, bring to front
                self.camera_window.window.lift()
                self.camera_window.window.focus_force()
                messagebox.showinfo(
                    "Camera Window",
                    "Camera window is already open"
                )
                return
        except:
            # Window reference exists but window is closed
            self.camera_window = None
    
    # Create new window
    self.camera_window = CameraViewWindow(parent=self.root)
```

## Advanced: Camera Status Updates

Periodically check camera status in main GUI:

```python
def __init__(self, root):
    # ... existing init ...
    
    # Start status update loop
    self.update_status()

def update_status(self):
    """Update status indicators"""
    # Update camera status if window exists
    if self.camera_window and self.camera_window.window.winfo_exists():
        if self.camera_window.camera_manager.camera:
            self.camera_status_label.config(
                text="Camera: Connected",
                foreground="green"
            )
        else:
            self.camera_status_label.config(
                text="Camera: Disconnected",
                foreground="red"
            )
    else:
        self.camera_status_label.config(
            text="Camera: Not active",
            foreground="gray"
        )
    
    # Schedule next update
    self.root.after(1000, self.update_status)  # Update every 1 second
```

## Summary

The camera window integration is straightforward:

1. Import `CameraViewWindow` from `calibration_modules`
2. Add menu item or button to open window
3. Create window instance when user requests it
4. Handle cleanup on application exit

The window operates independently and manages its own camera connection, making integration clean and simple.

---

**Last Updated:** November 28, 2025  
**Author:** Cheng Sun Lab Team
