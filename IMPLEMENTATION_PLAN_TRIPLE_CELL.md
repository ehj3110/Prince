# Triple Force Gauge Implementation Plan

**Target File**: `support_modules/ForceGaugeManager.py`  
**Strategy**: Drop-in replacement - maintain external interface

---

## Changes Required

### 1. `__init__()` - Add Multi-Channel Support

**Add after line 35 (after `self.calibrated_once = False`):**
```python
# === TRIPLE LOAD CELL CONFIGURATION ===
# Internal: 3 channels for parallel load cells
self.USE_TRIPLE_CELL = True  # Set to False to revert to single cell
self.channel_ports = [0, 1, 2] if self.USE_TRIPLE_CELL else [0]
self.num_channels = len(self.channel_ports)

# Multi-channel arrays (indexed by channel)
self.voltage_ratio_inputs_multi = [None] * self.num_channels
self.GAINS_multi = [None] * self.num_channels
self.OFFSETS_multi = [None] * self.num_channels
self.latest_voltages_multi = [0.0] * self.num_channels
self.latest_forces_multi = [0.0] * self.num_channels
self.calibrated_multi = [False] * self.num_channels

# Keep single-channel variable for backward compatibility (points to channel 0 or aggregate)
# self.voltage_ratio_input, self.GAIN, self.OFFSET remain for GUI compatibility
```

### 2. `initialize_phidget_background()` - Initialize Multiple Channels

**Replace single channel init with loop:**
```python
for i, port in enumerate(self.channel_ports):
    try:
        ch = VoltageRatioInput()
        ch.setChannel(port)
        ch.setOnAttachHandler(lambda sender, i=i: self._onAttach_multi(sender, i))
        ch.setOnDetachHandler(lambda sender, i=i: self._onDetach_multi(sender, i))
        ch.setOnErrorHandler(lambda sender, code, desc, i=i: self._onError_multi(sender, code, desc, i))
        ch.setOnVoltageRatioChangeHandler(lambda sender, v, i=i: self._onVoltageRatioChange_multi(sender, v, i))
        
        # ... rest of setup ...
        
        self.voltage_ratio_inputs_multi[i] = ch
        
    except Exception as e:
        print(f"Channel {i} initialization failed: {e}")

# Set channel 0 as the primary for backward compatibility
if self.voltage_ratio_inputs_multi[0]:
    self.voltage_ratio_input = self.voltage_ratio_inputs_multi[0]
```

### 3. New Event Handlers - Multi-Channel Versions

**Add new methods:**
```python
def _onAttach_multi(self, phidget, channel_index):
    \"\"\"Handle attachment for multi-channel setup.\"\"\"
    # ... existing _onAttach logic but for specific channel ...
    print(f"Channel {channel_index} attached")

def _onVoltageRatioChange_multi(self, phidget, voltageRatio, channel_index):
    \"\"\"Handle voltage change for specific channel.\"\"\"
    self.latest_voltages_multi[channel_index] = voltageRatio
    
    # Calculate force if calibrated
    if self.calibrated_multi[channel_index]:
        force = self.GAINS_multi[channel_index] * (voltageRatio - self.OFFSETS_multi[channel_index])
        self.latest_forces_multi[channel_index] = force
    
    # Update total force (sum of all channels)
    if all(self.calibrated_multi):
        self.latest_calibrated_force = sum(self.latest_forces_multi)
    
    # Push to queue (existing logic)
    self.raw_data_queue.put(('voltage', voltageRatio, time.time()))
```

### 4. `calibrate_force_gauge()` - Simultaneous Calibration

**Replace entire method with triple-cell calibration:**
```python
def calibrate_force_gauge(self):
    if self.USE_TRIPLE_CELL:
        return self._calibrate_triple_cell()
    else:
        return self._calibrate_single_cell()  # Original method

def _calibrate_triple_cell(self):
    # Step 1: Tare all channels
    for i in range(self.num_channels):
        zero_v = self.voltage_ratio_inputs_multi[i].getVoltageRatio()
        self.OFFSETS_multi[i] = zero_v
    
    # Step 2: Apply known force
    known_force = # ... from dialog ...
    
    # Step 3: Calculate gains (from test script logic)
    # ... distribute force based on voltage changes ...
    
    # Step 4: Set public values for GUI compatibility
    self.GAIN = sum(abs(g) for g in self.GAINS_multi if g) / self.num_channels
    self.OFFSET = sum(self.OFFSETS_multi) / self.num_channels
    self.calibrated_once = all(self.calibrated_multi)
```

### 5. `get_latest_calibrated_force()` - No Change Needed!

**Already returns the correct value** (sum is calculated in `_onVoltageRatioChange_multi`)

### 6. `close()` / `close_phidget()` - Close All Channels

**Update to close all channels:**
```python
for ch in self.voltage_ratio_inputs_multi:
    if ch:
        try:
            ch.close()
        except:
            pass
```

---

## Methods That DON'T Need Changes

- ✅ `get_latest_calibrated_force()` - Returns `self.latest_calibrated_force` (already sum)
- ✅ `get_force_N()` - Just calls `get_latest_calibrated_force()`
- ✅ `set_high_frequency_logging()` - Works with existing queue
- ✅ `get_buffered_force_data()` - Works with existing buffer
- ✅ All GUI update methods - Use `self.latest_calibrated_force`
- ✅ All threading methods - Work with existing architecture

---

## Testing Checklist

After implementation:
- [ ] System initializes all 3 channels
- [ ] Calibration dialog works
- [ ] Force reading shows sum of 3 cells
- [ ] GUI labels update correctly
- [ ] Logging captures total force
- [ ] Pre-calibration works with total force
- [ ] Sandwich routine force monitoring works
- [ ] No errors in console

---

## Rollback Plan

If anything breaks:
```powershell
cd "c:\Users\cheng sun\BoyuanSun\Prince_CurrentWorkingVersion\support_modules"
cp ForceGaugeManager_SingleCell_Backup.py ForceGaugeManager.py
```

Set in code:
```python
self.USE_TRIPLE_CELL = False
```

Or restore full backup.
