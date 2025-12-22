# AutomatedLayerLogger - ROOT CAUSE ANALYSIS

**Date:** December 22, 2024  
**Issue:** CSV files not created during print  
**Status:** ?? **ROOT CAUSE IDENTIFIED**

---

## Problem Statement

The AutomatedLayerLogger was enabled in the Sensor Panel, but no CSV files were generated during the 20-layer print run.

---

## Root Cause

The RED Lab printer's print loop (`def _()` method in `printer_helper_force_sensing.py`) **does not call any logging methods** during the print. The AutomatedLayerLogger was instantiated in SensorDataWindow but never told to:

1. Start a logging session
2. Update with current layer information  
3. Stop and save the logs

---

## Missing Integration Points

### **Location:** `printer_helper_force_sensing.py` - `def _()` method (Line 907-978)

**Current Code:**
```python
def _(self, idx):
    """Recursive print layer function"""
    if not self.flag:
        return
    
    image = cv2.imread(self.image_list[idx].replace('\\', '\\\\'), cv2.IMREAD_GRAYSCALE)
    cv2.imshow(self.window_name, image)
    cv2.waitKey(1)
    e_time = float(self.exposure_time[idx])
    if idx == 0:
        e_time = float(self.first_layer_exposure_time.get())

    thickness = (self.thickness[idx] * -1) / 1000
    # ...existing printing code...
    
    # ? MISSING: No calls to automated logger!
    
    idx += 1
    self.progress['value'] = 100 / len(self.exposure_time) * idx
    if idx >= len(self.exposure_time):
        self.flag = False
        print("done printing")
        self.set_home()
        cv2.destroyAllWindows()
        # ? MISSING: No call to save/stop logs!
```

---

## Required Changes

### **CHANGE 1: Before Print Starts** (Line ~900 in `run()` method)

**Add this BEFORE calling `self._(0)`:**

```python
def run(self):
    """Perform a print - REAL hardware"""
    sys.setrecursionlimit(500000)
    self.set_power()
    self.input_directory()
    self.set_position()
    self.flag = True
    
    cv2.startWindowThread()
    cv2.namedWindow(self.window_name, cv2.WND_PROP_FULLSCREEN)
    cv2.imshow(self.window_name, self.black_image)
    cv2.moveWindow(self.window_name, self.screen.x + 1439, self.screen.y - 1)
    cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    cv2.waitKey(1)
        
    while self.axis.is_busy():
        time.sleep(0.2)
    
    print("The window has opened")
    
    # ? ADD THIS: Configure automated logging if enabled
    if self.sensor_data_window_instance and hasattr(self.sensor_data_window_instance, 'auto_log_enabled_var'):
        if self.sensor_data_window_instance.auto_log_enabled_var.get():
            # Get the image directory
            image_dir = os.path.dirname(self.entPath.get())
            # Configure logging for this print run
            try:
                self.sensor_data_window_instance.configure_automated_layer_logging(
                    main_image_dir=image_dir,
                    print_number=1,  # Auto-increment could be added
                    date_str_for_dir=datetime.now().strftime('%Y-%m-%d'),
                    log_directory=os.path.join(image_dir, "Printing_Logs", datetime.now().strftime('%Y-%m-%d'), "Print_001")
                )
                print("? Automated layer logging configured for this print")
            except Exception as e:
                print(f"?? Could not configure automated logging: {e}")
    
    self._(0)  # Start recursive print loop
    self.controller.set_amplitude(0)
    self.axis.move_relative(max(0, self.offset), Units.LENGTH_MILLIMETRES, True)
    
    # ? ADD THIS: Stop and save automated logging after print
    if self.sensor_data_window_instance and hasattr(self.sensor_data_window_instance, 'stop_and_save_automated_logs'):
        try:
            self.sensor_data_window_instance.stop_and_save_automated_logs()
            print("? Automated logging stopped and saved")
        except Exception as e:
            print(f"?? Could not stop automated logging: {e}")
    
    self.t8.delete(0, 'end')
    self.t8.insert(END, str("Print Done"))
```

### **CHANGE 2: During Each Layer** (Line ~968 in `_()` method)

**Add this AFTER the layer completes:**

```python
def _(self, idx):
    """Recursive print layer function"""
    if not self.flag:
        return
    
    image = cv2.imread(self.image_list[idx].replace('\\', '\\\\'), cv2.IMREAD_GRAYSCALE)
    cv2.imshow(self.window_name, image)
    cv2.waitKey(1)
    e_time = float(self.exposure_time[idx])
    if idx == 0:
        e_time = float(self.first_layer_exposure_time.get())

    thickness = (self.thickness[idx] * -1) / 1000
    image_path_display = self.image_list[idx].replace('\\', '\\\\')
    print(f"run_: Image path {image_path_display}")
    print(f"exposure time {e_time}, index {idx}")
    print(f"Thickness: {thickness}")
    
    # ...existing printing code (stepwise/continuous modes)...
    
    # ? ADD THIS: Update automated logger with current layer
    layer_number = idx + 1  # Layer numbers are 1-indexed
    if self.sensor_data_window_instance and hasattr(self.sensor_data_window_instance, 'update_auto_logger_current_layer'):
        try:
            current_z_pos = float(self.axis.get_position(Units.LENGTH_MILLIMETRES))
            self.sensor_data_window_instance.update_auto_logger_current_layer(
                layer_number, 
                current_z_pos,
                image_path=self.image_list[idx]
            )
            print(f"? Layer {layer_number} logged at Z={current_z_pos:.4f}mm")
        except Exception as e:
            print(f"?? Could not log layer {layer_number}: {e}")
    
    idx += 1
    self.progress['value'] = 100 / len(self.exposure_time) * idx
    if idx >= len(self.exposure_time):
        self.flag = False
        print("done printing")
        self.set_home()
        cv2.destroyAllWindows()
        
    if self.flag:
        self.win.update()
        self.win.after(1, self._(idx))
```

---

## Why It Didn't Work

1. **Path Setup** ? Working - `logging_windows.csv` was created correctly
2. **Add Window** ? Working - Layer ranges added to CSV
3. **Print Start** ? **MISSING** - Never configured logging for the print session
4. **Layer Updates** ? **MISSING** - Never told logger about each layer
5. **Print End** ? **MISSING** - Never saved the collected logs

---

## Expected Behavior After Fix

### **Print Start:**
```
? Automated layer logging configured for this print
Print session: Print_001
Logging windows: [[1, 5], [10, 12]]
Output directory: E:\MC\...\Printing_Logs\2024-12-22\Print_001\
```

### **During Print:**
```
? Layer 1 logged at Z=19.9950mm
? Layer 2 logged at Z=19.9900mm
? Layer 3 logged at Z=19.9850mm
...
? Layer 20 logged at Z=19.8950mm
```

### **Print End:**
```
? Automated logging stopped and saved
Created files:
  - layer_data_L1-5.csv
  - layer_data_L10-12.csv
  - automated_work_of_adhesion.csv
  - peak_force_per_layer.csv
```

---

## Files to Modify

### **1. printer_helper_force_sensing.py**
- **Method:** `run()` - Add configuration before and cleanup after print
- **Method:** `_()` - Add layer update call
- **Lines:** ~900 (run), ~968 (_)

---

## Alternative: Simpler Integration

If the above is too complex, you can use the **manual "Start Recording" button** workflow:

1. Open Sensor Panel
2. Click "Start Live Readout"
3. Enter file path manually
4. Click "Start Recording"
5. Run print
6. Click "Stop Recording" when done

**This will create a basic CSV with time, position, and force columns.**

---

## Recommended Testing Sequence

### **Phase 1: Verify Configuration**
1. Add the code changes above
2. Launch script
3. Open Sensor Panel
4. Enable "Enable Automated Logging"
5. Add window: 1-3
6. Verify `logging_windows.csv` exists and contains: `1,3`

### **Phase 2: Test 5-Layer Print**
1. Load a 5-layer test print
2. Click "Run"
3. Watch terminal for:
   - "? Automated layer logging configured"
   - "? Layer X logged" messages
   - "? Automated logging stopped and saved"
4. Navigate to `Printing_Logs/2024-12-22/Print_001/`
5. Verify CSV files exist

### **Phase 3: Full Test**
1. Run larger print (20+ layers)
2. Verify data quality
3. Check peak force detection
4. Verify work of adhesion calculations

---

## Why This is a Common Issue

The automated logging system was designed for **Prince Lab** where the print loop already had callbacks for:
- Print session start (`configure_run()`)
- Layer completion (`update_current_layer()`)
- Print session end (`stop_all_logging_sessions()`)

**RED Lab's print loop** (`def _()`) is a **recursive function** with no external callbacks, so it needs these integration points added manually.

---

## Summary

| Integration Point | Status | Action Required |
|-------------------|--------|-----------------|
| Path Setup | ? Working | None |
| Window Definition | ? Working | None |
| Print Start Hook | ? Missing | Add `configure_automated_layer_logging()` call |
| Layer Update Hook | ? Missing | Add `update_auto_logger_current_layer()` call |
| Print End Hook | ? Missing | Add `stop_and_save_automated_logs()` call |

---

## Next Steps

1. **Add the 3 integration points** to `printer_helper_force_sensing.py`
2. **Test with a 5-layer print** to verify logging works
3. **Check CSV output** to ensure data quality
4. **Scale up to production prints**

---

*Analysis Complete: December 22, 2024*  
*Root Cause: Missing print loop integration hooks*  
*Fix Complexity: MEDIUM (3 code additions required)*  
*Confidence: HIGH - The logging system works, just needs to be called*
