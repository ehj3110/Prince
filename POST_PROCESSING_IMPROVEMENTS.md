# Post-Processing Improvements Summary

## Changes Made

### 1. **Fixed AttributeError in PeakForceLogger Initialization**
   - **Issue**: Code was trying to access `self.position_logger_thread.phase_event_queue` but the attribute is actually named `self.position_logger`
   - **Location**: `SensorDataWindow.py` lines 354 and 1039
   - **Fix**: Changed both occurrences from `self.position_logger_thread.phase_event_queue` to `self.position_logger.phase_event_queue`
   - **Impact**: Work of adhesion checkbox now works without AttributeError

### 2. **Enhanced Post-Print Analysis with Master Plot Generation**
   - **Location**: `post_print_analyzer.py`
   - **New Feature**: Added `_generate_master_plot()` method that creates a comprehensive master plot when automated work of adhesion data is available
   
   **Master Plot Includes:**
   - **Panel 1**: Peak Adhesion Force vs Layer Number
     * Line plot with markers
     * Mean line showing average peak force
   - **Panel 2**: Work of Adhesion vs Layer Number  
     * Line plot with markers
     * Mean line showing average work of adhesion
   - **Panel 3**: Peeling Phase Durations (if available)
     * Stacked bar chart showing pre-initiation and propagation times
     * Compares timing across all layers
   
   **Output**: Saved as `MASTER_work_of_adhesion_analysis.png` in the print session directory

### 3. **Automatic Post-Processing Workflow**

The system now automatically generates plots after each print:

```
Print Finishes Successfully
    ↓
stop_and_save_automated_logs() called
    ↓
_trigger_post_print_analysis() called
    ↓
PostPrintAnalyzer processes current session
    ↓
Generates individual plots for each autolog CSV file
    ↓
Generates master plot from automated_work_of_adhesion.csv
    ↓
Creates POST_PROCESSING_SUMMARY.md
```

### 4. **AutomatedLayerLogger Stop Behavior Verified**

**Question**: Does the autologger stop recording when the last layer finishes?

**Answer**: ✅ **YES**, it stops correctly through multiple mechanisms:

#### Mechanism 1: Layer-Based Stopping (Primary)
```python
# In AutomatedLayerLogger.update_current_layer()
if not should_be_logging_now and self.is_current_session_active:
    if not (self.current_session_start_layer <= current_layer_num <= self.current_session_end_layer):
        self._stop_current_auto_log_session()
```

**How it works**: 
- If you set a logging window of L430-L435
- When the print advances to Layer 436 (after completing L435)
- `should_be_logging_now` becomes False (layer 436 is outside the window)
- `is_current_session_active` is True (still recording)
- Condition triggers: stops the recording session
- CSV file is closed and saved

#### Mechanism 2: Print Completion Safety Net (Backup)
```python
# In Prince_Segmented.py print_t() at end of print
self.sensor_data_window_instance.stop_and_save_automated_logs()
    ↓
# Which calls AutomatedLayerLogger.stop_all_logging_sessions()
```

**How it works**:
- When the print thread finishes (normally or stopped early)
- Explicitly calls `stop_all_logging_sessions()`
- Ensures any active recording sessions are closed
- Acts as a safety net in case layer-based stopping didn't trigger

**Example Scenario**:
```
Logging window: L430-L435

Layer 430: Recording starts (autolog_L430-L435.csv opened)
Layer 431: Recording continues
Layer 432: Recording continues  
Layer 433: Recording continues
Layer 434: Recording continues
Layer 435: Recording continues (last layer in window)
Layer 436: Recording STOPS (outside window, file closed and saved)
    OR
Print Ends: Recording STOPS (safety net, file closed and saved)
```

### 5. **Post-Processing Output Files**

After a print completes, you'll find in the print session directory:

1. **Individual Layer Analysis Plots**:
   - `autolog_L430-L435_analysis.png`
   - One plot per autolog CSV file
   - Shows force profiles with pre-initiation, propagation phases
   - Includes timing annotations and baseline detection

2. **Master Work of Adhesion Plot**:
   - `MASTER_work_of_adhesion_analysis.png`
   - Combines all layers into summary plots
   - Shows trends across the entire print
   - Includes mean values for reference

3. **Summary Report**:
   - `POST_PROCESSING_SUMMARY.md`
   - Lists all files processed
   - Processing timestamps and method info

## How to Use

### During Print Setup:

1. **Enable Automated Logging**:
   - Check "Enable Automated Logging" in SensorDataWindow
   - Add layer windows (e.g., L430-L435)
   - Logging windows are saved to `logging_windows.csv`

2. **Enable Work of Adhesion Recording** (optional):
   - Check "Record Work of Adhesion" checkbox
   - Data saved to `automated_work_of_adhesion.csv`

### During Print:

- Autologger automatically starts/stops based on layer windows
- Recording stops when layer number exceeds the window
- No manual intervention needed

### After Print:

- Post-processing runs automatically
- Individual plots generated for each CSV file
- Master plot generated if work of adhesion data exists
- Check print session directory for output files

## Comparison to Batch Processor

### Similarities:
- Uses same `RawDataProcessor` workflow
- Same adhesion metrics calculations
- Same plot styling and layout
- Same phase detection (pre-initiation, propagation, baseline)

### Differences:
- **Batch Processor**: Processes multiple test conditions, creates subplots for comparison
- **Post-Print Analyzer**: Processes single print session, individual plots per CSV + master summary
- **Batch Processor**: Manual execution with folder selection
- **Post-Print Analyzer**: Automatic execution after print completes

## Testing Recommendations

1. **Test Autologger Stopping**:
   ```
   - Set logging window: L5-L10
   - Run a print with 15 layers
   - Verify recording stops after Layer 10
   - Check autolog_L5-L10.csv is properly closed
   ```

2. **Test Post-Processing**:
   ```
   - Run a print with work of adhesion enabled
   - Let print complete normally
   - Check for output files:
     ✓ autolog_LX-LY_analysis.png (individual plots)
     ✓ MASTER_work_of_adhesion_analysis.png (master plot)
     ✓ POST_PROCESSING_SUMMARY.md (summary report)
   ```

3. **Test Early Stop Behavior**:
   ```
   - Start a print with logging enabled
   - Stop print manually during logging window
   - Verify recording stops and files are saved
   - Check that post-processing still runs
   ```

## Known Limitations

1. **Master Plot Requirements**:
   - Only generated if `automated_work_of_adhesion.csv` exists
   - Requires "Record Work of Adhesion" checkbox to be enabled
   - If CSV is empty or missing columns, master plot is skipped

2. **Post-Processing Timing**:
   - Runs in the print thread before thread finishes
   - May add ~5-30 seconds to print completion time
   - User sees "Print thread finished" message after post-processing completes

3. **File Naming**:
   - Master plot always named `MASTER_work_of_adhesion_analysis.png`
   - Individual plots use autolog filename as base
   - Existing plots are overwritten without warning

## Future Enhancements (Optional)

1. **Add post-processing progress indicator** to show which file is being processed
2. **Option to skip post-processing** if user wants faster print completion
3. **Email notification** when post-processing completes (for long prints)
4. **Comparison plots** between multiple print sessions in the same daily directory
5. **Export data to Excel** format for easier external analysis

## Troubleshooting

### Problem: AttributeError when enabling work of adhesion
**Solution**: ✅ Fixed - update to latest SensorDataWindow.py

### Problem: Autologger keeps recording after last layer
**Solution**: ✅ Verified working correctly - check logic in AutomatedLayerLogger.py

### Problem: No master plot generated
**Causes**:
- Work of adhesion not enabled during print
- `automated_work_of_adhesion.csv` doesn't exist
- CSV file is empty or has missing columns
**Solution**: Enable "Record Work of Adhesion" checkbox before starting print

### Problem: Post-processing takes too long
**Options**:
- Reduce number of layers in logging windows
- Use larger layer ranges (fewer CSV files)
- Consider implementing skip post-processing option

