# Automated Logging System - Verification Report

**Date:** December 22, 2024  
**Status:** ? **READY FOR TESTING**  
**System:** RED Lab Printer with Force Sensing

---

## Executive Summary

The automated logging system has been **thoroughly reviewed and fixed**. One critical path handling issue was identified and resolved.

### **Key Finding:**
- **ISSUE:** SensorDataWindow expected a directory path, but RED Lab provides a txt file path
- **FIX:** Added path extraction logic to get directory from txt file path
- **STATUS:** ? FIXED

---

## What Was Checked

### ? **1. Path Compatibility (printer_helper_force_sensing.py)**

**Line 642:**
```python
self.t1 = self.entPath  # Direct reference for SensorDataWindow logging
```

**Status:** ? WORKING  
**Provides:** `E:\MC\_Animal_Study_Stent_ADJ3_Henry_50um\sent_50um 200.txt`

---

### ? **2. Path Extraction (SensorDataWindow.py) - FIXED**

**Original Code (Line 498):**
```python
main_app_image_dir_val = self.prince_main_app_ref.t1.get()
if not main_app_image_dir_val or not os.path.isdir(main_app_image_dir_val):
    # ? FAILS: txt file is not a directory!
```

**Fixed Code (Line 498-507):**
```python
main_app_txt_file_path = self.prince_main_app_ref.t1.get()

# Extract directory from txt file path (RED Lab uses txt file path)
if main_app_txt_file_path and os.path.isfile(main_app_txt_file_path):
    main_app_image_dir_val = os.path.dirname(main_app_txt_file_path)  # ? EXTRACTS DIRECTORY
elif main_app_txt_file_path and os.path.isdir(main_app_txt_file_path):
    main_app_image_dir_val = main_app_txt_file_path  # Fallback for Prince style
else:
    main_app_image_dir_val = main_app_txt_file_path

if not main_app_image_dir_val or not os.path.isdir(main_app_image_dir_val):
    # Now correctly validates the extracted directory
```

**Status:** ? FIXED  
**Result:** Correctly extracts `E:\MC\_Animal_Study_Stent_ADJ3_Henry_50um\`

---

### ? **3. Directory Structure Creation (SensorDataWindow.py)**

**Lines 512-520:**
```python
# Create [main_image_dir]/Printing_Logs/
printing_logs_base_dir = os.path.join(main_app_image_dir_val, "Printing_Logs")
os.makedirs(printing_logs_base_dir, exist_ok=True)

# Create [main_image_dir]/Printing_Logs/[YYYY-MM-DD]/
date_str = datetime.datetime.now().strftime('%Y-%m-%d')
self.date_specific_log_dir_for_windows_file = os.path.join(printing_logs_base_dir, date_str)
os.makedirs(self.date_specific_log_dir_for_windows_file, exist_ok=True)
```

**Expected Output:**
```
E:\MC\_Animal_Study_Stent_ADJ3_Henry_50um\
??? Printing_Logs\
?   ??? 2024-12-22\
?       ??? logging_windows.csv  ? Created automatically
```

**Status:** ? CORRECT

---

### ? **4. CSV File Creation (SensorDataWindow.py)**

**Lines 522-542:**
```python
logging_windows_csv_path = os.path.join(
    self.date_specific_log_dir_for_windows_file, 
    "logging_windows.csv"
)

if not os.path.exists(logging_windows_csv_path):
    with open(logging_windows_csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["StartLayer", "EndLayer"])  # Header
```

**Status:** ? CORRECT  
**Creates:** `logging_windows.csv` with proper CSV header

---

### ? **5. GUI Integration (SensorDataWindow.py)**

**on_auto_log_enable_change() - Line 709:**
```python
if is_enabled_by_checkbox:
    paths_setup_successfully = self._setup_default_logging_paths()
    if paths_setup_successfully and self.current_logging_windows_file:
        # Enable "Add Window" button
        self.btn_add_window_to_file.config(state=tk.NORMAL)
```

**Status:** ? CORRECT  
**UI Updates:**
- Checkbox: "Enable Automated Logging"
- Label: Shows full path to `logging_windows.csv`
- Button: "Add Window" (enabled when path is valid)

---

### ? **6. Add Window Function (SensorDataWindow.py)**

**add_window_to_active_file() - Line 726:**
```python
start_layer = int(start_layer_str)
end_layer = int(end_layer_str)

with open(self.current_logging_windows_file, mode, newline='') as f:
    writer = csv.writer(f)
    if mode == 'w' or not file_exists_and_not_empty:
        writer.writerow(["StartLayer", "EndLayer"])
    writer.writerow([start_layer, end_layer])  # Add layer range
```

**Status:** ? CORRECT  
**Validates:**
- Layer numbers are positive integers
- Start layer ? End layer
- File exists and is writable

---

## Expected Behavior

### **1. Enable Automated Logging:**
1. User clicks checkbox: "Enable Automated Logging"
2. System calls `_setup_default_logging_paths()`
3. Extracts directory from `E:\MC\...\sent_50um 200.txt`
4. Creates folder structure:
   ```
   E:\MC\_Animal_Study_Stent_ADJ3_Henry_50um\
   ??? Printing_Logs\
       ??? 2024-12-22\
           ??? logging_windows.csv
   ```
5. Label updates with full path
6. "Add Window" button becomes enabled

### **2. Add Layer Window:**
1. User enters: Start L: `1`, End L: `5`
2. Clicks "Add Window"
3. System validates input
4. Appends to CSV:
   ```csv
   StartLayer,EndLayer
   1,5
   ```
5. Clears input fields
6. Shows status: "Window [1-5] added to logging_windows.csv"

### **3. During Print Run:**
1. `AutomatedLayerLogger` reads `logging_windows.csv`
2. When layer 1-5 print, system logs:
   - Position data
   - Force data
   - Peak force per layer
   - Work of adhesion
3. Creates session-specific CSV files in print subdirectory

---

## Testing Procedure

### **Phase 1: Path Setup Test**
```
1. Launch printer_helper_force_sensing.py
2. Click "Open Sensor Panel"
3. Check "Enable Automated Logging"
4. Verify label shows:
   E:\MC\_Animal_Study_Stent_ADJ3_Henry_50um\Printing_Logs\2024-12-22\logging_windows.csv
5. Verify "Add Window" button is enabled
```

### **Phase 2: Add Window Test**
```
1. Enter Start L: 1
2. Enter End L: 3
3. Click "Add Window"
4. Verify message: "Window [1-3] added to logging_windows.csv"
5. Verify fields cleared
6. Navigate to folder and open logging_windows.csv
7. Verify contents:
   StartLayer,EndLayer
   1,3
```

### **Phase 3: Multiple Windows Test**
```
1. Add window: 5-7
2. Add window: 10-12
3. Open CSV and verify:
   StartLayer,EndLayer
   1,3
   5,7
   10,12
```

### **Phase 4: Print Integration Test** (When ready)
```
1. Set up automated logging with windows
2. Load a small test print (12 layers)
3. Run print
4. After completion, check for:
   - Position CSV logs
   - Force CSV logs
   - Peak force logs
   - Work of adhesion logs
```

---

## File Changes Made

### **1. printer_helper_force_sensing.py**
- **Line 642:** Added `self.t1 = self.entPath` for compatibility
- **Status:** ? COMPLETE

### **2. SensorDataWindow.py**
- **Lines 498-507:** Fixed path extraction from txt file
- **Status:** ? COMPLETE

---

## Potential Issues & Solutions

### **Issue 1: Path doesn't update when user selects new file**

**Symptom:** Old path still shown after clicking "Select File"

**Solution:** Click "Enable Automated Logging" checkbox OFF then ON again to refresh paths

---

### **Issue 2: "Add Window" button disabled**

**Possible Causes:**
1. Checkbox not enabled
2. Directory doesn't exist
3. No txt file selected

**Solution:** 
1. Select a valid txt file first
2. Enable checkbox
3. Check system message for specific error

---

### **Issue 3: CSV file not created**

**Possible Causes:**
1. Directory permissions
2. Drive not accessible
3. Path too long

**Solution:**
1. Check folder permissions for `E:\MC\...`
2. Verify drive `E:` is mounted
3. Use shorter folder names if needed

---

## Success Criteria

- ? **Path Extraction:** Directory correctly extracted from txt file path
- ? **Folder Creation:** `Printing_Logs/YYYY-MM-DD/` created automatically
- ? **CSV Creation:** `logging_windows.csv` created with proper header
- ? **GUI Updates:** Label shows correct path, button enables
- ? **Window Addition:** Layer ranges added to CSV correctly
- ? **Print Integration:** Needs testing with actual print run

---

## Compatibility Summary

| Feature | Prince Lab | RED Lab | Status |
|---------|------------|---------|--------|
| Path Source | `t1` (directory entry) | `t1` (txt file path) | ? FIXED |
| Path Type | Directory | File ? Extract directory | ? WORKING |
| Folder Structure | Same | Same | ? COMPATIBLE |
| CSV Format | Same | Same | ? COMPATIBLE |
| GUI Layout | Same | Same | ? COMPATIBLE |

---

## Next Steps

1. **Test Path Setup** ? Ready
2. **Test Add Window** ? Ready
3. **Test Multiple Windows** ? Ready
4. **Test Print Integration** ? Requires DLP fix
5. **Verify Log Files** ? After print test

---

## Conclusion

The automated logging system is **READY FOR TESTING**. The critical path handling issue has been fixed, and all components are properly integrated.

**Confidence Level:** HIGH  
**Recommendation:** Proceed with testing once DLP is operational

---

*Report Generated: December 22, 2024*  
*System: RED Lab Force Sensing Printer*  
*Status: ? All Pre-Flight Checks Complete*
