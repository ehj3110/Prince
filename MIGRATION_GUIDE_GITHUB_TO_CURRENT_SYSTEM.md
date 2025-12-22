# Migration Guide: GitHub Engineer Code ? Current Working System

**Created:** December 22, 2024  
**Updated:** December 22, 2024 - Added AutomatedLayerLogger compatibility
**Purpose:** Document EXACT changes needed to deploy fresh GitHub code to current RED lab system

---

## Executive Summary

Based on our extensive debugging session, we learned these critical facts about your system:

### **Hardware Configuration Discovered:**
1. **Force Gauge Channel:** Connected to **Channel 2** (NOT Channel 0 like original code assumes)
2. **Phidget Device:** 4x Bridge Phidget (VID_06C2&PID_003B)
3. **Connection Type:** Direct USB (HubPort = -1)
4. **Stage:** Zaber on COM3
5. **Working Sampling Rate:** 10ms (was 25ms in original)

### **What Currently Works:**
- ? Force gauge connects successfully on Channel 2
- ? SensorDataWindow reuses existing ForceGaugeManager (no duplicate connection)
- ? Force data flows through queue to plotting system
- ? Calibration (Quick Calibrate) loads saved values
- ? Blue position line and red force line both plot correctly AFTER calibration
- ? DLP initialized successfully
- ? Full system operational

---

## **NEW: AutomatedLayerLogger Compatibility Analysis**

### **RED Lab File Path Structure (Verified Working):**

**RED Lab uses:**
```python
# Line 618: Default path in GUI
self.entPath.insert(END, r"E:\MC\_Animal_Study_Stent_ADJ3_Henry_50um\sent_50um 200.txt")

# Line 646-653: File parsing in Application.set_image_directory()
path = os.path.dirname(txt_path)  # E:\MC\_Animal_Study_Stent_ADJ3_Henry_50um\
image_list.append(path + '\\' + image_path)  # E:\MC\...\image001.png
```

**Structure:**
```
E:\MC\_Animal_Study_Stent_ADJ3_Henry_50um\
??? sent_50um 200.txt          ? Print job file
??? image001.png               ? Layer images
??? image002.png
??? ...
```

### **AutomatedLayerLogger Expected Paths:**

The `AutomatedLayerLogger` expects to create this structure:
```
[Main Image Directory]\
??? Printing_Logs\
?   ??? YYYY-MM-DD\
?       ??? logging_windows.csv
?       ??? Print_001\
?       ?   ??? layer_data.csv
?       ?   ??? automated_work_of_adhesion.csv
?       ??? Print_002\
?           ??? ...
```

### **Compatibility Status: ? COMPATIBLE**

**Why it works:**
1. `SensorDataWindow._setup_default_logging_paths()` uses `self.prince_main_app_ref.t1.get()`
2. But RED Lab uses `self.entPath` instead of `t1`
3. **SOLUTION**: Need to add a property or method to RED Lab's `MyWindow` class

### **PRIORITY 4: Add Image Directory Property (NEW)**

#### File: `printer_helper_force_sensing.py`

**Lines to Add:** After line 638 (in `MyWindow.__init__` after file selection setup)

**REQUIRED ADDITION:**
```python
# After the file selection setup (line 638)
self.entPath.place(x=180, y=150)
self.btnFind.place(x=180+730+10, y=150)      
self.loaded_image_info.place(x=180+740+70+10, y=150)     
self.entPath.insert(END, r"E:\MC\_Animal_Study_Stent_ADJ3_Henry_50um\sent_50um 200.txt")

# ? ADD THIS: Create compatibility property for SensorDataWindow
@property
def t1(self):
    """Compatibility property for SensorDataWindow logging paths.
    Returns the Entry widget containing the image directory txt file path.
    """
    return self.entPath
```

**WHY:** `SensorDataWindow._setup_default_logging_paths()` looks for `prince_main_app_ref.t1.get()` to determine the base image directory. RED Lab uses `entPath` instead of `t1`, so we add a property to provide compatibility without changing SensorDataWindow.

**Alternative (if property doesn't work):** Update `SensorDataWindow._setup_default_logging_paths()` line 492:
```python
# OLD:
main_app_image_dir_val = self.prince_main_app_ref.t1.get()

# NEW:
if hasattr(self.prince_main_app_ref, 't1'):
    main_app_image_dir_val = self.prince_main_app_ref.t1.get()
elif hasattr(self.prince_main_app_ref, 'entPath'):
    main_app_image_dir_val = self.prince_main_app_ref.entPath.get()
else:
    main_app_image_dir_val = None
```

---

## Critical Changes Required (Priority Order)

### **PRIORITY 1: Force Gauge Channel Configuration**

#### File: `support_modules/ForceGaugeManager.py`

**Lines to Change:** ~Line 415 in `initialize_phidget()` method

**CURRENT GITHUB CODE:**
```python
def initialize_phidget(self):
    try:
        print("Initializing VoltageRatioInput (ForceGaugeManager)...")
        
        self.voltage_ratio_input = VoltageRatioInput()
        
        # GitHub code uses Channel 0
        self.voltage_ratio_input.setHubPort(-1)  # Direct USB connection
        self.voltage_ratio_input.setChannel(0)   # ? WRONG FOR RED LAB
        
        # ... rest of connection code
```

**REQUIRED CHANGE:**
```python
def initialize_phidget(self):
    try:
        print("Initializing Force Gauge on Channel 2...")  # Updated message
        
        self.voltage_ratio_input = VoltageRatioInput()
        
        # RED lab requires Channel 2
        self.voltage_ratio_input.setHubPort(-1)  # Direct USB connection  
        self.voltage_ratio_input.setChannel(2)   # ? CORRECT FOR RED LAB
        
        print("Attempting connection with 10s timeout...")
        self.voltage_ratio_input.openWaitForAttachment(10000)
        print("Force gauge connected successfully on Channel 2")
```

**WHY:** The force gauge in RED lab is physically connected to Port/Channel 2 of the Phidget bridge. Using Channel 0 will result in timeout errors.

---

### **PRIORITY 2: Sampling Rate Default**

#### File: `support_modules/SensorDataWindow.py`

**Line to Change:** ~Line 147 where sampling rate entry is created

**CURRENT GITHUB CODE:**
```python
self.sampling_rate_entry = Entry(buttons_and_sampling_frame, width=6, font=control_box_font)
self.sampling_rate_entry.insert(0, "25")  # ? 25ms default
```

**REQUIRED CHANGE:**
```python
self.sampling_rate_entry = Entry(buttons_and_sampling_frame, width=6, font=control_box_font)
self.sampling_rate_entry.insert(0, "10")  # ? 10ms works better with decimation
```

**WHY:** During testing, we found 10ms sampling rate provides better data quality with the dynamic decimation system (1200Hz ? 100Hz is cleaner than 1200Hz ? 40Hz).

---

### **PRIORITY 3: Queue Reference When Reusing Manager**

#### File: `support_modules/SensorDataWindow.py`

**Lines to Change:** ~Line 183-198 in `__init__` method

**CURRENT GITHUB CODE:**
```python
if existing_force_gauge_manager:
    print("SensorDataWindow: Using existing ForceGaugeManager from main app")
    self.force_gauge_manager = existing_force_gauge_manager
    # Update the manager's sensor_window_ref to point to this window
    self.force_gauge_manager.sensor_window_ref = self
    # Update label references to use this window's labels
    self.force_gauge_manager.gain_label = self.lbl_gain
    self.force_gauge_manager.offset_label = self.lbl_offset
    self.force_gauge_manager.force_status_label = self.lbl_force_gauge_status
    self.force_gauge_manager.large_force_readout_label = self.lbl_current_force
    # ? MISSING: Queue update!
```

**REQUIRED CHANGE:**
```python
if existing_force_gauge_manager:
    print("SensorDataWindow: Using existing ForceGaugeManager from main app")
    self.force_gauge_manager = existing_force_gauge_manager
    # Update the manager's sensor_window_ref to point to this window
    self.force_gauge_manager.sensor_window_ref = self
    # Update label references to use this window's labels
    self.force_gauge_manager.gain_label = self.lbl_gain
    self.force_gauge_manager.offset_label = self.lbl_offset
    self.force_gauge_manager.force_status_label = self.lbl_force_gauge_status
    self.force_gauge_manager.large_force_readout_label = self.lbl_current_force
    # ? CRITICAL: Update the output queue to use this window's queue
    self.force_gauge_manager.output_force_queue = self.force_data_queue_for_logger
    print(f"SensorDataWindow: Updated ForceGaugeManager output queue to Sensor Panel's queue")
```

**WHY:** Without this, force data goes to the main app's dummy queue instead of the SensorDataWindow's queue that feeds the plot. This is why you saw blue line (position) but no red line (force) before calibration.

---

### **PRIORITY 4: Image Directory Compatibility**

#### File: `printer_helper_force_sensing.py`

**Lines to Add:** After line 638 (after file path entry setup)

**REQUIRED ADDITION:**
```python
# Add property for SensorDataWindow compatibility
@property
def t1(self):
    """Compatibility property: Returns entPath for SensorDataWindow logging."""
    return self.entPath
```

**WHY:** SensorDataWindow expects `prince_main_app_ref.t1.get()` to get the image directory. RED Lab uses `entPath` instead, so this property provides compatibility.

---

### **PRIORITY 5: Update System Message Signature (ALREADY FIXED ?)**

#### File: `printer_helper_force_sensing.py`

**Line:** 837 (in `update_system_message` method)

**CURRENT (ALREADY CORRECT):**
```python
def update_system_message(self, message, error=False, warning=False):
    """Update the system message display"""
    self.t8.delete(0, 'end')
    self.t8.insert(END, str(message))
    if error:
        self.t8.config(foreground='red')
    elif warning:
        self.t8.config(foreground='orange')
    else:
        self.t8.config(foreground='black')
    self.win.update()
```

**STATUS:** ? Already fixed - no action needed

---

## Terminal Output Review

### **? What's Working:**
1. DLP Controller connected
2. Zaber Stage found (1 device on COM3)
3. Force Gauge connected on Channel 2
4. Decimation system active (1200Hz ? 100Hz at 10ms)
5. Sensor Panel opened successfully
6. Full calibration completed (GAIN: 8205.87)
7. Tare operation successful
8. Calibration saved to file
9. Live readout started at 10ms
10. Data decimation working (10× averaging)

### **?? Minor Issues (Non-Critical):**
1. **DLP Status Polling:** "Unable to get Error Status from DLP controller"
   - **Impact:** Minor - DLP still functions
   - **Fix:** Check if DLP Control Panel is open, close it

2. **TypeError on Auto-Log Enable (FIXED):** 
   - **Was:** `warning=True` parameter not recognized
   - **Fixed:** Added `warning` parameter to `update_system_message()`

3. **File Generation Error:**
   - **Message:** "The directory does not exist for creating the text file."
   - **Impact:** None - occurs when default path doesn't exist
   - **Fix:** Not needed - user will select actual path

###**Status Summary (Updated Dec 22, 2024 16:36):**

| Component | Status | Notes |
|-----------|--------|-------|
| Force Gauge Connection | ? Working | Channel 2, 1200Hz decimation |
| Data Logging | ? Working | 10ms sampling, queue flowing |
| Live Plotting | ? Working | Blue + Red lines both active |
| Calibration | ? Working | Full + Quick + Tare + Save |
| DLP Controller | ?? Partial | Connected, status polling issue |
| Zaber Stage | ? Working | COM3, position tracking |
| Automated Logging | ?? Needs Testing | Path compatibility added |

---

## Optional Improvements (Not Critical)

### **OPTIONAL 1: Fallback Channel Detection**

The GitHub `ForceGaugeManager.py` has fallback logic to try other channels if Channel 2 fails. Your current working version does NOT have this fallback.

**Trade-off:**
- **GitHub version:** More robust, tries channels [0,1,3] if 2 fails
- **Your version:** Faster, fails immediately with clear error message

**Recommendation:** Keep your version (no fallback) since you KNOW it's Channel 2. Fallback logic adds complexity and delay.

---

### **OPTIONAL 2: Comprehensive Mock System**

The GitHub `RED_Segmented.py` has extensive mock classes for testing without hardware.

**If you want this feature:**
1. Copy the mock class definitions from `RED_Segmented.py` lines 43-169
2. Wrap them in `if SPOOF_PHIDGET:` block in your `printer_helper_force_sensing.py`
3. Inject mock modules into `sys.modules` before importing support modules

**Benefit:** Can test GUI without any hardware connected.

**Your current SPOOF system:** Creates mock Phidget classes in ForceGaugeManager itself.

---

### **OPTIONAL 3: Enhanced Debug Output**

GitHub version has cleaner, more structured debug messages.

**Example improvements:**
```python
# Instead of:
print(f"Force gauge: {self.actual_sample_rate:.1f} Hz")

# GitHub uses:
if int(current_time) % 10 == 0:  # Every 10 seconds
    print(f"Force gauge: {self.actual_sample_rate:.1f} Hz actual rate, "
          f"Queue: {self.raw_data_queue.qsize()}/{self.raw_data_queue.maxsize}")
```

**Recommendation:** Not critical, your current debug output is functional.

---

## Files That DON'T Need Changes

### ? Files That Can Be Used As-Is From GitHub:

1. **`PositionLogger.py`** - No hardware-specific code
2. **`PeakForceLogger.py`** - No hardware-specific code  
3. **`AutomatedLayerLogger.py`** - No hardware-specific code (path compatibility added to main app)
4. **`ExperimentalConditionsWindow.py`** - Pure GUI
5. **`AutoHomeRoutine.py`** - Uses abstract force gauge interface
6. **`adhesion_metrics_calculator.py`** - Pure computation
7. **`USBCoordinator.py`** - Generic USB management
8. **`two_step_baseline_analyzer.py`** - Pure data analysis

**WHY:** These modules don't directly interact with the Phidget hardware. They work through the ForceGaugeManager abstraction layer.

---

## Step-by-Step Migration Plan

### **Phase 1: Backup Everything**
```bash
cd C:\printer_code\dinglab_printer_notebook
mkdir backup_working_$(date +%Y%m%d)
copy support_modules\ForceGaugeManager.py backup_working_*\
copy support_modules\SensorDataWindow.py backup_working_*\
copy printer_helper_force_sensing.py backup_working_*\
```

### **Phase 2: Update Critical Files**

1. **Update ForceGaugeManager.py:**
   - Find `initialize_phidget()` method (~line 415)
   - Change `setChannel(0)` to `setChannel(2)`
   - Update print messages to mention Channel 2

2. **Update SensorDataWindow.py:**
   - Find the `if existing_force_gauge_manager:` block (~line 183)
   - Add the queue update line: `self.force_gauge_manager.output_force_queue = self.force_data_queue_for_logger`
   - Find sampling rate entry creation (~line 147)
   - Change default from `"25"` to `"10"`

3. **Update printer_helper_force_sensing.py:**
   - Add `@property` for `t1` after line 638 for AutomatedLayerLogger compatibility

4. **Test Immediately:**
   ```bash
   python printer_helper_force_sensing.py
   ```
   - Should connect to Channel 2 ?
   - Open Sensor Panel ?
   - Click "Quick Calibrate" ?
   - Verify both blue AND red lines appear ?
   - Enable auto-logging checkbox ?
   - Verify logging windows file path appears ?

### **Phase 3: Copy Non-Critical Support Modules (Optional)**

If you want the latest versions of other modules:
```bash
copy engineer_review\support_modules\PeakForceLogger.py support_modules\
copy engineer_review\support_modules\PositionLogger.py support_modules\
# etc...
```

**Test after each copy:**
```bash
python printer_helper_force_sensing.py
```

### **Phase 4: Enable DLP (ALREADY DONE ?)**

In `printer_helper_force_sensing.py`:
```python
ENABLE_DLP = True  # Line 47
```

**Test sequence:**
1. System starts ?
2. Force gauge connects ?
3. DLP initializes ?
4. Open Sensor Panel ?
5. Quick Calibrate ?
6. Plot shows both lines ?

---

## Testing Checklist

After making changes, verify:

- [x] **Connection Test:**
  - [x] Script starts without errors
  - [x] Terminal shows "Force gauge connected successfully on Channel 2"
  - [x] No timeout errors

- [x] **Sensor Panel Test:**
  - [x] "Open Sensor Panel" button works
  - [x] Sensor Panel window opens
  - [x] No duplicate connection messages
  - [x] Force gauge status shows voltage ratio

- [x] **Calibration Test:**
  - [x] "Quick Calibrate" button works
  - [x] Gain and Offset labels update
  - [x] Force status changes from voltage to "Force: X.XXXXXX N"
  - [x] Tare function works
  - [x] Save Calibration creates timestamped file

- [x] **Plotting Test:**
  - [x] "Start Live Readout" works
  - [x] Blue line (position) appears and updates
  - [x] **Red line (force) appears and updates** ? Critical test
  - [x] Both lines scroll together
  - [x] No data lag or freezing

- [ ] **Automated Logging Test (PENDING):**
  - [ ] Enable "Enable Automated Logging" checkbox
  - [ ] Verify logging_windows.csv path appears
  - [ ] Add window (start layer, end layer)
  - [ ] Verify window added to CSV
  - [ ] Run test print with logging enabled
  - [ ] Verify layer data logged correctly

- [ ] **Data Flow Test:**
  - [ ] Stage moves ? blue line responds
  - [ ] Touch force gauge ? red line responds
  - [ ] "Start Recording" creates CSV file
  - [ ] CSV contains both position and force columns

---

## Summary of Changes

### **Absolutely Required (System Won't Work Without These):**

1. ? **ForceGaugeManager.py:** Change Channel 0 ? Channel 2
2. ? **SensorDataWindow.py:** Add queue update when reusing manager
3. ? **printer_helper_force_sensing.py:** Add `warning` parameter to `update_system_message()`
4. ?? **printer_helper_force_sensing.py:** Add `t1` property for AutomatedLayerLogger compatibility

### **Strongly Recommended:**

5. ? **SensorDataWindow.py:** Change default sampling rate 25ms ? 10ms

### **Optional (Nice to Have):**

6. ? Add fallback channel detection
7. ? Implement comprehensive mock system  
8. ? Enhance debug output
9. ? Update other support modules

---

## Contact for Issues

If issues persist after making these changes:

1. Check the backup files in `backup_working_YYYYMMDD\`
2. Compare your edits against this guide
3. Verify force gauge is actually on Channel 2 using Phidget Control Panel
4. Check terminal output for specific error messages

---

**Status:** ? Documentation Complete (Updated with AutomatedLayerLogger compatibility)
**Next Step:** Add `t1` property to printer_helper_force_sensing.py, then test automated logging
**Confidence:** High - based on extensive debugging session and terminal output analysis

---

*Created: December 22, 2024*  
*Updated: December 22, 2024 - Added AutomatedLayerLogger compatibility analysis*  
*Based on: Real debugging session with working hardware*  
*System Tested: RED lab force sensing with Phidget 4x Bridge on Channel 2*
