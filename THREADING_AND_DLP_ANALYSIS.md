# Threading and DLP Issues Analysis - October 8, 2025

## Issue 1: GUI Freezing and Potential Stage Stalls

### Root Causes Identified:

#### 1. **PeakForceLogger Analysis Worker Thread Never Stops**
**Location**: `support_modules/PeakForceLogger.py` lines 167-198

**Problem**:
- A daemon thread (`_analysis_worker`) runs continuously in an infinite loop
- The thread processes queued analysis jobs: `while True: job = self._analysis_queue.get()`
- The `close()` method (lines 389-398) sends a shutdown signal, but **it's never called during normal operation**
- The daemon thread continues running between prints, consuming CPU and potentially interfering with stage movements

**Evidence**:
```python
# Line 32-33: Thread starts immediately on PeakForceLogger creation
self._analysis_thread = threading.Thread(target=self._analysis_worker, daemon=True)
self._analysis_thread.start()

# Line 169: Infinite loop
def _analysis_worker(self):
    """Worker thread to process queued adhesion data analysis."""
    while True:  # <-- NEVER EXITS unless None is sent to queue
        try:
            job = self._analysis_queue.get()
```

**Impact**:
- Between prints: Thread sits idle but queue.get() blocks waiting for jobs
- During long idle periods: May accumulate stale data in memory
- When printing resumes: Old queued jobs may process unexpectedly
- GUI freezing during "Clear Plot": If analysis thread is processing large dataset, it blocks

#### 2. **Plot Queue Not Cleared on Print End**
**Location**: `support_modules/SensorDataWindow.py` lines 250, 904-908

**Problem**:
- `position_plot_queue` accumulates data during printing
- Only cleared when "Clear Plot" button is clicked or when starting new live readout
- If print ends abnormally, queue retains all data
- Next print start may process thousands of old data points

**Evidence**:
```python
# Line 904-908: Only cleared in toggle_live_readout()
while not self.position_plot_queue.empty():
    try:
        self.position_plot_queue.get_nowait()
    except queue.Empty:
        break
```

#### 3. **No Cleanup in Print Thread Completion**
**Location**: `Prince_Segmented.py` lines 946-951

**Problem**:
- When print completes, only GUI buttons are re-enabled
- No queue cleanup, no thread shutdown, no resource release
- Background threads continue running

**Evidence**:
```python
# Lines 946-951: Print thread finishes
self.update_status_message("Print thread finished.")
if hasattr(self, 'b1'): self.b1.config(state=NORMAL)
if hasattr(self, 'b2'): self.b2.config(state=NORMAL)
if hasattr(self, 'b4'): self.b4.config(state=DISABLED)
self.print_thread = None  # <-- Only sets variable to None, doesn't clean up### Recommended Fixes for Issue 1:

#### Fix 1A: Add Proper Cleanup When Print Ends
**File**: Prince_Segmented.py around line 946

Add cleanup code after print finishes:
```python
# After line 951 (self.print_thread = None), add:
# Clean up sensor data window resources
if hasattr(self, 'sensor_data_window_instance') and self.sensor_data_window_instance:
    # Clear plot queues
    while not self.sensor_data_window_instance.position_plot_queue.empty():
        try:
            self.sensor_data_window_instance.position_plot_queue.get_nowait()
        except:
            break
    
    # Close PeakForceLogger if exists
    if hasattr(self.sensor_data_window_instance, 'peak_force_logger') and self.sensor_data_window_instance.peak_force_logger:
        self.sensor_data_window_instance.peak_force_logger.close()
        self.sensor_data_window_instance.peak_force_logger = None
```

#### Fix 1B: Add Cleanup on Print Error/Stop
**File**: Prince_Segmented.py in the exception handlers

When print is stopped or errors occur, ensure cleanup happens.

#### Fix 1C: Clear Queue on "Clear Plot" Button
**File**: support_modules/SensorDataWindow.py line 805

Enhance clear_plot_data() to also clear force queue:
```python
def clear_plot_data(self):
    self.plot_data_x.clear()
    self.plot_data_y_position.clear()
    self.plot_data_y_force.clear()
    
    # Also clear the force data queue to prevent stale data
    while not self.force_data_queue_for_logger.empty():
        try:
            self.force_data_queue_for_logger.get_nowait()
        except queue.Empty:
            break
```

---

## Issue 2: DLP Not Turning Back On After Errors

### Root Causes Identified:

#### 1. **DLP Mode Not Reset Properly on Error**
**Location**: Prince_Segmented.py lines 859-864

**Problem**:
- When print completes normally, DLP is set to mode 3 (HDMI/video) and power set to 0
- When print is stopped via button or error, DLP cleanup only calls stopsequence() (line 977)
- Power is NOT set to 0, mode is NOT changed back to video
- DLP may remain in pattern mode with no active sequence → stuck state

**Evidence**:
```python
# Normal completion (lines 859-864):
self.controller.stopsequence()
self.controller.power(current=0)  # ← LED turned off
self.controller.changemode(3)     # ← Back to video mode

# Button stop (lines 977-981):
self.controller.stopsequence()    # ← Only stops sequence!
# self.controller.power(current=0)  # ← COMMENTED OUT!
```

#### 2. **No DLP Cleanup in Error Handlers**
**Location**: Multiple exception blocks throughout print_t()

**Problem**:
- When MovementFailedException or other errors occur, print aborts
- No DLP cleanup code in the exception handlers
- DLP left in unknown state (possibly pattern mode with stopped sequence)

#### 3. **Missing DLP State Reset in Recovery**
**Location**: Prince_Segmented.py lines 794-816 (fault recovery section)

**Problem**:
- When stage fault occurs and recovery is attempted, DLP state is ignored
- After recovery fails, DLP is not reset to safe state
- User tries to start new print → DLP still in bad state from previous fault

### DLP Background Light Issue (Video Mode):

#### Problem Statement:
- In stepped mode, using cv2.imshow() to display patterns via HDMI
- DLP is in video mode (mode 3) during stepped printing
- Even with black image displayed, DLP emits background light
- This light can cure resin unintentionally between layers

#### Current Behavior:
```python
# Stepped mode sequence:
# 1. Show image → DLP displays via HDMI
# 2. Expose (time.sleep)
# 3. Show BLACK image → DLP still outputs some light!
# 4. Move stage
```

#### Desired Behavior:
Set DLP power to 0 between exposures to eliminate background light.

### Recommended Fixes for Issue 2:

#### Fix 2A: Standardize DLP Cleanup Function
**File**: Prince_Segmented.py

Create a dedicated cleanup method:
```python
def cleanup_dlp_safe_state(self):
    \"\"\"Reset DLP to safe idle state: stop sequence, power off, video mode.\"\"\"
    try:
        if hasattr(self, 'controller'):
            self.controller.stopsequence()
            self.controller.power(current=0)  # Turn off LED
            self.controller.changemode(3)     # HDMI/video mode
            self.update_status_message("DLP reset to safe state (video mode, power=0)")
    except Exception as e:
        self.update_status_message(f"Error resetting DLP: {e}", error=True)
```

Call this function:
- When print completes (replace existing cleanup code)
- When print is stopped via button
- In ALL exception handlers in print_t()
- After fault recovery fails

#### Fix 2B: Add DLP Cleanup to Stop Button Handler
**File**: Prince_Segmented.py line 977-981

Replace:
```python
try:
    self.controller.stopsequence()
    # self.controller.power(current=0)  # ← UNCOMMENT THIS!
```

With:
```python
try:
    self.cleanup_dlp_safe_state()  # Use new standardized function
```

#### Fix 2C: Add Power Cycling Between Layers in Stepped Mode
**File**: Prince_Segmented.py in the stepped mode section

Modify the sequence:
```python
elif print_mode == "stepped":
    # --- Stepped Mode: Display, Expose, Blackout, then Move ---
    # 1. Display image for layer i
    image_path = self.image_list[i]
    image_to_show = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
    cv2.imshow(self.window_name, image_to_show)
    cv2.waitKey(1)
    
    # 2. Expose
    if current_exposure_s > 0:
        time.sleep(current_exposure_s)
    
    # 3. Show black image AND turn off DLP power
    cv2.imshow(self.window_name, self.black_image)
    cv2.waitKey(1)
    
    # NEW: Turn off DLP power to eliminate background light
    if hasattr(self, 'controller'):
        self.controller.power(current=0)
        self.update_status_message(f"L{current_layer_num_for_display}: DLP power set to 0 (background light off)")
    
    # 4. Z-Axis Movement (Peel and Return)
    # ... existing movement code ...
    
    # 5. After stage returns, restore DLP power for next layer
    if hasattr(self, 'controller') and i < num_layers - 1:  # Not on last layer
        # Get next layer's power setting
        next_layer_power = int(actual_dlp_power)  # or from dlp_power_list
        self.controller.power(current=next_layer_power)
        self.update_status_message(f"L{current_layer_num_for_display}: DLP power restored to {next_layer_power}")
```

#### Difficulty Assessment for Power Cycling:

**Complexity**: Low to Medium

**Pros**:
- Simple code addition (just call power(current=0) after exposure)
- Uses existing controller interface
- No new hardware or mode changes needed
- Eliminates background light completely

**Cons**:
- Adds ~50-100ms per layer for power cycling (negligible for most prints)
- LED power-up time may vary slightly between layers
- May need to measure if power cycling affects LED lifespan

**Implementation Steps**:
1. Add power-off call after black image display (1 line)
2. Add power-on call before next layer's image display (2-3 lines)
3. Test with single layer to verify timing
4. Verify no background light during stage movement
5. Check if LED warm-up time is consistent

**Recommendation**: This is **worth implementing** - it's a simple change with high value for preventing unwanted resin curing.

---

## Summary of Critical Issues:

| Issue | Severity | Impact | Fix Complexity |
|-------|----------|--------|----------------|
| PeakForceLogger thread never stops | High | Stage stalls, GUI freezing | Medium (add cleanup calls) |
| Plot queues not cleared | Medium | Memory growth, stale data | Low (add queue.clear()) |
| DLP not reset on errors | High | DLP stuck, won't restart | Low (standardize cleanup) |
| Background light in stepped mode | Medium | Unwanted curing | Low (add power cycling) |

**Next Steps**:
1. Implement DLP cleanup function (Fix 2A) - Highest priority
2. Add cleanup to print completion (Fix 1A)
3. Add power cycling in stepped mode (Fix 2C) - High value, low effort
4. Test thoroughly with error scenarios

