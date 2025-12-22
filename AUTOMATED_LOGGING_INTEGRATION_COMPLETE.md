# Automated Logging Integration - COMPLETED

**Date:** December 22, 2024  
**Status:** ? **INTEGRATION COMPLETE**  
**File Modified:** `printer_helper_force_sensing.py`

---

## Changes Applied

### **1. Print Start Hook (Line ~860 in `run()` method)**

**Added automated logging configuration before print starts:**

```python
# Configure automated logging if enabled
if self.sensor_data_window_instance and hasattr(self.sensor_data_window_instance, 'auto_log_enabled_var'):
    if self.sensor_data_window_instance.auto_log_enabled_var.get():
        # Get the image directory
        image_dir = os.path.dirname(self.entPath.get())
        date_str = datetime.now().strftime('%Y-%m-%d')
        log_dir = os.path.join(image_dir, "Printing_Logs", date_str, "Print_001")
        
        # Configure logging for this print run
        try:
            os.makedirs(log_dir, exist_ok=True)
            self.sensor_data_window_instance.configure_automated_layer_logging(
                main_image_dir=image_dir,
                print_number=1,
                date_str_for_dir=date_str,
                log_directory=log_dir
            )
            print("? Automated layer logging configured for this print")
            self.update_system_message("Automated logging: ACTIVE")
        except Exception as e:
            print(f"?? Could not configure automated logging: {e}")
            traceback.print_exc()
```

**What this does:**
- Checks if Sensor Panel is open and automated logging is enabled
- Extracts the image directory from the txt file path
- Creates the logging directory structure
- Configures the AutomatedLayerLogger with print session details
- Shows status message: "Automated logging: ACTIVE"

---

### **2. Print End Hook (Line ~895 in `run()` method)**

**Added logging save/stop after print completes:**

```python
# Stop and save automated logging after print
if self.sensor_data_window_instance and hasattr(self.sensor_data_window_instance, 'stop_and_save_automated_logs'):
    try:
        self.sensor_data_window_instance.stop_and_save_automated_logs()
        print("? Automated logging stopped and saved")
        self.update_system_message("Automated logging: SAVED")
    except Exception as e:
        print(f"?? Could not stop automated logging: {e}")
        traceback.print_exc()
```

**What this does:**
- Stops all active logging sessions
- Saves collected data to CSV files
- Saves final peak force data and work of adhesion
- Shows status message: "Automated logging: SAVED"

---

### **3. Layer Update Hook (Line ~980 in `_()` method)**

**Added layer-by-layer logging update:**

```python
# Update automated logger with current layer
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
```

**What this does:**
- After each layer completes, gets current Z position
- Calls AutomatedLayerLogger with layer number, Z position, and image path
- Triggers peak force detection and work of adhesion calculation
- Prints confirmation: "? Layer X logged at Z=XX.XXXXmm"

---

## How to Test

### **Test 1: Path Setup**
1. Launch `printer_helper_force_sensing.py`
2. Click "Open Sensor Panel"
3. Enable "Enable Automated Logging" checkbox
4. Verify path shows: `E:\MC\...\Printing_Logs\2024-12-22\logging_windows.csv`

### **Test 2: Add Windows**
1. Enter Start L: `1`, End L: `5`
2. Click "Add Window"
3. Add another: Start L: `10`, End L: `12`
4. Navigate to the Printing_Logs folder and verify CSV contains:
   ```csv
   StartLayer,EndLayer
   1,5
   10,12
   ```

### **Test 3: Print with Logging**
1. Load a test print (12+ layers recommended)
2. Verify Sensor Panel is open with automated logging enabled
3. Click "Run" to start print
4. Watch terminal for:
   ```
   ? Automated layer logging configured for this print
   ? Layer 1 logged at Z=19.9950mm
   ? Layer 2 logged at Z=19.9900mm
   ...
   ? Layer 12 logged at Z=19.9350mm
   done printing
   ? Automated logging stopped and saved
   ```

### **Test 4: Verify Output Files**
Navigate to: `E:\MC\...\Printing_Logs\2024-12-22\Print_001\`

Expected files:
- `layer_data_L1-5.csv` - Position/force data for layers 1-5
- `layer_data_L10-12.csv` - Position/force data for layers 10-12
- `automated_work_of_adhesion.csv` - Peak force per layer
- `peak_force_per_layer.csv` - Work calculations

---

## Expected Terminal Output

### **Print Start:**
```
The window has opened
? Automated layer logging configured for this print
Automated logging: ACTIVE
```

### **During Print:**
```
run_: Image path C:\\Users\\...\\1.png
exposure time 1.0, index 0
Thickness: -0.005
run_: Show
show_image: Started showing image
...
? Layer 1 logged at Z=19.9950mm

run_: Image path C:\\Users\\...\\2.png
exposure time 1.0, index 1
...
? Layer 2 logged at Z=19.9900mm
```

### **Print End:**
```
done printing
Setting LED amplitude to 0
? Automated logging stopped and saved
Automated logging: SAVED
Print Done
```

---

## What Gets Logged

### **Layer Data CSV (layer_data_L1-5.csv):**
```csv
Timestamp,Layer,Z_Position_mm,Force_N
1234567890.123,1,19.9950,0.00012
1234567890.223,1,19.9949,0.00015
...
```

### **Work of Adhesion CSV (automated_work_of_adhesion.csv):**
```csv
Layer,Peak_Force_N,Z_at_Peak_mm,Work_of_Adhesion_mJ,Cross_Section_Area_mm2
1,0.0045,20.1234,0.234,12.5
2,0.0048,20.1245,0.245,12.5
...
```

---

## Troubleshooting

### **Issue: No CSV files created**

**Check:**
1. Sensor Panel was open during print
2. "Enable Automated Logging" checkbox was checked
3. At least one window was defined in logging_windows.csv
4. Live readout was active (auto-starts if needed)

**Solution:** Re-run print with Sensor Panel open and logging enabled

---

### **Issue: Missing layers in log**

**Check:**
1. Verify layer number is within defined windows
2. Check terminal for error messages
3. Verify force gauge was calibrated

**Solution:** Layers outside defined windows won't be logged (by design)

---

### **Issue: "configure_automated_layer_logging not found"**

**Check:**
1. Sensor Panel was opened at least once
2. SensorDataWindow.py has the configure method
3. Check Python errors in terminal

**Solution:** Update SensorDataWindow.py from latest version

---

## Integration Summary

| Hook Point | Method | Line | Status |
|------------|--------|------|--------|
| Print Start | `run()` | ~860 | ? ADDED |
| Layer Complete | `_()` | ~980 | ? ADDED |
| Print End | `run()` | ~895 | ? ADDED |

---

## Next Steps

1. ? **Integration Complete** - All hooks added
2. ? **Test with 5-layer print** - Verify CSV generation
3. ? **Verify data quality** - Check force/position values
4. ? **Scale to production** - Use on real prints

---

## Rollback Instructions

If needed, revert to backup:
```bash
cd C:\printer_code\dinglab_printer_notebook
copy backup_working_YYYYMMDD\printer_helper_force_sensing.py printer_helper_force_sensing.py
```

---

**Status:** ? Integration successful - Ready for testing  
**Modified:** `printer_helper_force_sensing.py` (3 integration points added)  
**Next:** Test print with automated logging enabled

---

*Integration Completed: December 22, 2024*  
*Modified by: GitHub Copilot*  
*Tested: Pending first print run*
