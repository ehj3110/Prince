# UI Components Documentation

This directory contains reusable UI (User Interface) components and frames that are integrated into the main Prince application and sensor panel. These modules provide specialized GUI functionality with consistent styling and behavior.

## Table of Contents

- [Overview](#overview)
- [Components](#components)
- [Integration](#integration)
- [Styling Guidelines](#styling-guidelines)

---

## Overview

### Purpose

The `ui_components/` directory separates reusable UI elements from the main application logic, promoting:
- **Code reusability** - Components can be used in multiple windows
- **Maintainability** - UI changes isolated to component files
- **Consistency** - Standardized appearance and behavior
- **Modularity** - Easy to add new UI components

### Architecture

```
Main Application (Prince_Segmented.py)
├── Sensor Panel (SensorDataWindow.py)
│   ├── AutomatedLoggingFrame ← ui_components/
│   ├── Force Display Widgets
│   └── Real-Time Plot
│
├── Experimental Conditions Window
│   └── Custom Input Fields
│
└── Main Control Panel
    ├── Print Controls
    ├── Stage Controls
    └── Parameter Inputs
```

---

## Components

### `automated_logging_frame.py`

**Purpose:** Provides UI controls for automated layer-specific data logging

**Location in GUI:** Sensor Data & Logging Window (opened via "Open Sensor Panel")

**Visual Layout:**

```
┌────────────────────────────────────────────────────────────┐
│ Automated Layer Logging Control                            │
├────────────────────────────────────────────────────────────┤
│ ☑ Enable Automated Logging  Start L: [48] End L: [50]     │
│                             [Add Window]                    │
│                                                             │
│ Active File: C:\...\logging_windows_Print1.txt             │
│                                                             │
│ Configured Windows:                                         │
│   • Layers 48-50                                           │
│   • Layers 75-80                                           │
└────────────────────────────────────────────────────────────┘
```

**Key Features:**

1. **Enable/Disable Toggle**
   - Checkbox: "Enable Automated Logging"
   - Controls whether layer-specific CSVs are generated during print
   - Connected to `AutomatedLayerLogger` in backend

2. **Layer Window Definition**
   - Start Layer input: Specify first layer to log
   - End Layer input: Specify last layer to log
   - Add Window button: Register layer range for logging

3. **Active File Display**
   - Shows current logging windows configuration file path
   - Updates when file loaded or created
   - Visual indicator of logging status

4. **Window List Display**
   - Shows all configured layer ranges
   - Allows review of what will be logged
   - Can be edited via configuration file

**Class: `AutomatedLoggingFrame`**

**Inheritance:** `ttk.LabelFrame` (Tkinter themed frame with label)

**Constructor:**
```python
def __init__(self, master, sensor_data_window_ref, control_box_font):
    """
    Parameters:
    -----------
    master : tk.Widget
        Parent widget (typically SensorDataWindow)
    sensor_data_window_ref : SensorDataWindow
        Reference to main sensor window for communication
    control_box_font : tuple
        Font specification (e.g., ('Helvetica', 9))
    """
```

**Key Methods:**

- **`_ui_on_auto_log_enable_change()`**
  - Called when checkbox toggled
  - Enables/disables input fields
  - Notifies parent window of state change
  
- **`_ui_add_window_to_file()`**
  - Validates layer range inputs
  - Adds range to configuration file
  - Updates display of configured windows
  
- **`get_enabled_state()`**
  - Returns current enabled/disabled state
  - Used by main application to check logging status
  
- **`set_enabled(enable: bool)`**
  - Programmatically enable/disable logging
  - Updates checkbox state
  
- **`update_active_file_display(filepath: str)`**
  - Updates displayed configuration file path
  - Called when new file loaded

**Integration with Backend:**

```python
# In SensorDataWindow.py
from ui_components.automated_logging_frame import AutomatedLoggingFrame

class SensorDataWindow:
    def __init__(self, ...):
        # Create logging control frame
        self.auto_log_frame = AutomatedLoggingFrame(
            master=control_panel,
            sensor_data_window_ref=self,
            control_box_font=('Helvetica', 9)
        )
        self.auto_log_frame.pack(...)
        
        # Access enabled state
        is_enabled = self.auto_log_frame.get_enabled_state()
        
        # Update configuration display
        self.auto_log_frame.update_active_file_display("path/to/config.txt")
```

**Configuration File Format:**

The logging windows are stored in a text file:

```
# logging_windows_Print1.txt
48-50    # Layers 48 through 50
75-80    # Layers 75 through 80
100-100  # Single layer 100
```

**Usage Workflow:**

1. **User opens Sensor Panel** from main GUI
2. **User checks "Enable Automated Logging"**
3. **User enters layer range** (e.g., Start: 48, End: 50)
4. **User clicks "Add Window"** - Range added to config file
5. **During print:**
   - When layer 48 starts, `AutomatedLayerLogger` begins recording
   - When layer 50 completes, logger saves `autolog_L48-L50.csv`
6. **Multiple windows** can be defined for same print

**Benefits:**

- **Selective logging** - Only log interesting layer ranges
- **Reduced file sizes** - Don't log entire print if unnecessary
- **Flexible configuration** - Different windows for different experiments
- **Real-time control** - Can enable/disable during setup

**Critical Notes:**

- Must be enabled BEFORE starting print
- Layer numbers are 1-indexed (first layer = Layer 1)
- End layer must be >= Start layer
- Configuration persists across sessions (saved to file)

---

## Integration

### Adding UI Component to Window

**Step 1: Import Component**
```python
from ui_components.automated_logging_frame import AutomatedLoggingFrame
```

**Step 2: Create Instance**
```python
# Inside window initialization
self.my_frame = AutomatedLoggingFrame(
    master=parent_widget,
    sensor_data_window_ref=self,  # Reference for callbacks
    control_box_font=('Helvetica', 9)
)
```

**Step 3: Pack/Place Component**
```python
# Using pack geometry manager
self.my_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

# Or using grid
self.my_frame.grid(row=2, column=0, sticky='ew', padx=5, pady=5)
```

**Step 4: Connect to Backend**
```python
# Access component state
if self.my_frame.get_enabled_state():
    # Logging is enabled
    self.automated_logger.start_logging()
```

---

### Communication Pattern

**Parent → Component:**
```python
# Update component from parent window
self.auto_log_frame.update_active_file_display(new_path)
self.auto_log_frame.set_enabled(True)
```

**Component → Parent:**
```python
# In component's callback method
def _ui_on_auto_log_enable_change(self):
    # Notify parent via reference
    self.sensor_data_window.on_auto_log_state_changed(
        self.auto_log_enabled_var.get()
    )
```

---

## Styling Guidelines

### Font Specifications

**Standard Fonts:**
```python
# Control boxes and buttons
control_box_font = ('Helvetica', 9)

# Headers and labels
header_font = ('Helvetica', 12, 'bold')

# Status messages
status_font = ('Helvetica', 9)

# Large display values
display_font = ('Helvetica', 14)
```

### Color Scheme

**Prince Standard Colors:**
```python
# Primary brand color
prince_purple = '#834bd0'

# Background colors
canvas_bg = '#FFEFD5'  # Wheat/beige
frame_bg = 'white'

# Status colors
status_normal = 'black'
status_warning = 'orange'
status_error = 'red'
status_success = 'green'
```

### Widget Sizing

**Standard Dimensions:**
```python
# Entry fields
entry_width_small = 5   # Layer numbers
entry_width_medium = 15  # File names
entry_width_large = 50   # Full paths

# Buttons
button_width = 12  # Standard button width

# Frames
frame_padding = (10, 5)  # (horizontal, vertical)
widget_spacing = 5  # Padding between widgets
```

### Layout Conventions

**Row-Based Layout:**
```python
# Create frame for each row
row0 = Frame(parent)
row0.pack(side=TOP, fill=X, pady=2)

# Add widgets to row
label.pack(side=LEFT, padx=(0, 5))
entry.pack(side=LEFT, padx=(0, 10))
button.pack(side=LEFT)
```

**Grid-Based Layout:**
```python
# Use grid for complex layouts
label.grid(row=0, column=0, sticky='w', padx=5, pady=2)
entry.grid(row=0, column=1, sticky='ew', padx=5, pady=2)
button.grid(row=0, column=2, padx=5, pady=2)
```

---

## Creating New UI Components

### Template for New Component

```python
from tkinter import Frame, Label, Entry, Button
from tkinter import ttk, StringVar, BooleanVar, TOP, X, LEFT

class MyCustomFrame(ttk.LabelFrame):
    """
    Description of what this component does.
    
    Attributes:
    -----------
    attribute1 : type
        Description
    attribute2 : type
        Description
    """
    
    def __init__(self, master, parent_window_ref, font):
        """
        Initialize the custom frame.
        
        Parameters:
        -----------
        master : tk.Widget
            Parent widget
        parent_window_ref : object
            Reference to parent window for callbacks
        font : tuple
            Font specification
        """
        super().__init__(master, text="My Custom Frame", padding=(10, 5))
        self.parent_window = parent_window_ref
        self.font = font
        
        # Initialize variables
        self.my_var = StringVar()
        
        # Create widgets
        self._create_widgets()
        
    def _create_widgets(self):
        """Create and layout all widgets."""
        # Row 0
        row0 = Frame(self)
        row0.pack(side=TOP, fill=X, pady=2)
        
        Label(row0, text="Label:", font=self.font).pack(side=LEFT, padx=(0, 5))
        Entry(row0, textvariable=self.my_var, font=self.font).pack(side=LEFT)
        Button(row0, text="Action", command=self._on_action, font=self.font).pack(side=LEFT, padx=(10, 0))
        
    def _on_action(self):
        """Handle button click."""
        value = self.my_var.get()
        # Do something with value
        
        # Notify parent window
        if hasattr(self.parent_window, 'on_my_action'):
            self.parent_window.on_my_action(value)
    
    def get_value(self):
        """Public method to get current value."""
        return self.my_var.get()
    
    def set_value(self, value):
        """Public method to set value."""
        self.my_var.set(value)
```

### Best Practices

1. **Use ttk widgets** for consistent theming
2. **Separate creation from layout** (_create_widgets method)
3. **Prefix internal methods** with underscore (_on_action)
4. **Document public interface** (docstrings for public methods)
5. **Keep parent reference** for callbacks
6. **Use variables for dynamic updates** (StringVar, BooleanVar, etc.)
7. **Test in isolation** before integrating

---

## Testing UI Components

### Unit Testing

```python
import tkinter as tk
from ui_components.automated_logging_frame import AutomatedLoggingFrame

# Create test window
root = tk.Tk()
root.title("Component Test")

# Mock parent window
class MockParent:
    def on_auto_log_state_changed(self, enabled):
        print(f"Logging enabled: {enabled}")

mock_parent = MockParent()

# Create component
frame = AutomatedLoggingFrame(
    master=root,
    sensor_data_window_ref=mock_parent,
    control_box_font=('Helvetica', 9)
)
frame.pack(padx=10, pady=10)

# Test programmatic control
frame.set_enabled(True)
print(f"Enabled state: {frame.get_enabled_state()}")

# Run test window
root.mainloop()
```

### Integration Testing

Test component within actual parent window to verify:
- Proper layout and sizing
- Callback communication
- State synchronization
- Visual appearance

---

## Future Components

**Planned UI Components:**

1. **`parameter_grid_frame.py`**
   - Grid-based input for layer-specific parameters
   - Spreadsheet-like interface
   - Bulk editing capabilities

2. **`real_time_plot_frame.py`**
   - Reusable real-time plotting widget
   - Configurable data sources
   - Multiple plot types

3. **`calibration_wizard_frame.py`**
   - Step-by-step calibration interface
   - Progress indicators
   - Validation feedback

4. **`print_queue_frame.py`**
   - Queue multiple print jobs
   - Batch processing interface
   - Progress tracking

---

## Troubleshooting

### Component Not Appearing

**Check:**
1. Import statement correct
2. Component created (initialized)
3. Component packed/gridded in parent
4. Parent window geometry correct

### Callbacks Not Working

**Check:**
1. Parent reference passed to constructor
2. Parent has expected callback method
3. Method name spelled correctly
4. Callback actually being called (add print statement)

### Styling Inconsistent

**Solutions:**
1. Use standardized fonts from guidelines
2. Use ttk widgets instead of tk widgets
3. Check theme settings
4. Verify padding and spacing values

---

## Development Guidelines

### When to Create UI Component

Create a new component when:
- **Reused in multiple windows** - Same UI pattern needed elsewhere
- **Complex layout** - More than 5-10 widgets
- **Self-contained functionality** - Independent feature
- **Frequent updates** - Easier to maintain separately

### When to Keep in Main File

Keep in main file when:
- **One-time use** - Only used in one window
- **Simple layout** - 1-3 widgets
- **Tightly coupled** - Depends heavily on parent window internals

---

## Contact

For questions about UI components:

**UI Design:** Boyuan Sun (boyuansun2026@u.northwestern.edu)  
**Component Development:** Evan Jones (evanjones2026@u.northwestern.edu)  
**Integration Issues:** Boyuan Sun (boyuansun2026@u.northwestern.edu)

---

**Last Updated:** February 2, 2026  
**Component Count:** 1 active component  
**Framework:** Tkinter + ttk  
**Python Version:** 3.8+
