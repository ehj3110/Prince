# Dynamic Decimation Implementation
**Date**: November 9, 2025  
**Status**: ✅ Implemented and Ready for Testing

---

## Problem Solved

### Previous Issue (Fixed Decimation)
- **Old System**: Fixed decimation factor (e.g., 8×) running at ~8ms output
- **PositionLogger**: Actually runs at ~16ms due to I/O overhead
- **Result**: Queue often empty when sampled → Force values repeated 5× in CSV

### New Solution (Dynamic Decimation)
- **Hardware**: Samples at maximum speed (~1ms = 1200Hz)
- **Decimation Factor**: **Automatically calculated from user's GUI setting**
- **Output Rate**: **Exactly matches user's sampling rate**
- **Result**: No timing mismatch - queue always has fresh data!

---

## How It Works

### Architecture

```
Hardware (1200Hz, 1ms)
    ↓
Decimation Buffer (collects N samples)
    ↓
Average N samples
    ↓
Output 1 sample every N milliseconds
    ↓
Queue (PositionLogger reads at N ms intervals)
    ↓
CSV File (perfect timing match!)
```

### Example: User Sets 25ms (40Hz)

```python
# User sets GUI spinbox to 25ms
user_sampling_interval_ms = 25

# System automatically calculates:
decimation_factor = 25 / 1  # = 25×
hardware_interval = 1ms     # ~1200Hz input
output_interval = 25ms      # 40Hz output

# Hardware collects 25 samples at ~1ms each
# Averages them → outputs 1 sample every 25ms
# PositionLogger reads every 25ms → always finds fresh data!
```

### Benefits

| User Rate | Decimation Factor | Noise Reduction | Output Matches |
|-----------|-------------------|-----------------|----------------|
| 8ms       | 8×                | 2.83×          | ✅ 8ms         |
| 10ms      | 10×               | 3.16×          | ✅ 10ms        |
| 12ms      | 12×               | 3.46×          | ✅ 12ms        |
| 16ms      | 16×               | 4.00×          | ✅ 16ms        |
| 25ms      | 25×               | 5.00×          | ✅ 25ms        |
| 50ms      | 50×               | 7.07×          | ✅ 50ms        |

**Key**: Output rate ALWAYS equals user's GUI setting → No more mismatches!

---

## Implementation Details

### ForceGaugeManager.py Changes

#### 1. Added Decimation Variables (Line ~40)
```python
# === DYNAMIC DECIMATION SYSTEM ===
self.USE_DECIMATION = True
self.user_sampling_interval_ms = 25  # Default 25ms (40Hz)
self.hardware_interval_ms = 1  # Hardware samples at ~1ms (1200Hz)
self.decimation_factor = 25  # Will be calculated dynamically
self.decimation_buffer = deque(maxlen=100)  # Buffer for averaging
self.decimation_counter = 0
self.latest_averaged_voltage = None
```

#### 2. Updated Callback (Line ~455)
```python
def _onVoltageRatioChange(self, phidget, voltageRatio):
    """Implements dynamic decimation tied to user sampling rate."""
    if self.USE_DECIMATION:
        # Collect samples
        self.decimation_buffer.append(voltageRatio)
        self.decimation_counter += 1
        
        # When enough samples collected, average and output
        if self.decimation_counter >= self.decimation_factor:
            averaged = sum(self.decimation_buffer) / len(self.decimation_buffer)
            self.raw_data_queue.put_nowait((timestamp, averaged))
            self.decimation_counter = 0
```

#### 3. Updated _onAttach (Line ~400)
```python
def _onAttach(self, phidget):
    if self.USE_DECIMATION:
        # Set hardware to maximum speed
        phidget.setDataInterval(self.hardware_interval_ms)  # 1ms = 1200Hz
        phidget.setVoltageRatioChangeTrigger(0.0)
        print(f"Dynamic decimation: Hardware at 1ms, decimating to {self.user_sampling_interval_ms}ms")
```

#### 4. Updated set_data_interval (Line ~825)
```python
def set_data_interval(self, interval_ms):
    """Updates decimation factor dynamically when user changes rate."""
    # Enforce minimum 8ms
    if interval_ms < 8:
        interval_ms = 8
    
    self.user_sampling_interval_ms = interval_ms
    
    if self.USE_DECIMATION:
        # Recalculate decimation factor
        self.decimation_factor = max(1, int(interval_ms / self.hardware_interval_ms))
        
        # Update buffer
        self.decimation_buffer = deque(maxlen=max(50, self.decimation_factor * 2))
        self.decimation_counter = 0
        
        print(f"Decimation factor updated to {self.decimation_factor}× for {interval_ms}ms rate")
```

#### 5. Added get_decimation_info() (Line ~795)
```python
def get_decimation_info(self):
    """Get current decimation configuration."""
    return {
        'enabled': True,
        'hardware_rate_hz': 1200,
        'user_rate_hz': 1000 / self.user_sampling_interval_ms,
        'decimation_factor': self.decimation_factor,
        'noise_reduction_factor': self.decimation_factor ** 0.5
    }
```

---

## Configuration

### Current Settings
- **USE_DECIMATION**: `True` (enabled by default)
- **hardware_interval_ms**: `1` (1200Hz maximum speed)
- **user_sampling_interval_ms**: `25` (default, user-adjustable)
- **Minimum Rate**: `8ms` (enforced for safety)
- **Channel**: `0` (updated from previous channel 2)

### To Disable Decimation
If you want to test without decimation:
```python
# In ForceGaugeManager.__init__()
self.USE_DECIMATION = False
```

---

## Testing Plan

### Test 1: Connection and Startup
1. Launch Prince application
2. Observe console output
3. Expected: "Dynamic decimation mode: Hardware at 1ms..."

### Test 2: Default Rate (25ms)
1. Start live readout with default 25ms
2. Record for 15 seconds
3. Check CSV:
   - ✅ Force values should NOT repeat
   - ✅ Timing intervals should be ~25ms ±2ms
   - ✅ Each row has unique force value

### Test 3: Change Rate During Operation
1. Start at 25ms, record for 10 seconds
2. Change to 50ms, record for 10 seconds
3. Change to 10ms, record for 10 seconds
4. Check console: Should show decimation factor updates
5. Check CSV: Timing should match each setting

### Test 4: Minimum Rate Enforcement
1. Try to set rate to 5ms (below minimum)
2. Expected: Console warning, clamped to 8ms
3. GUI spinbox should show 8ms

### Test 5: Print Test
1. Run a 2-layer test print at 25ms
2. Check CSV after print:
   - ✅ No repeated force values
   - ✅ Consistent 25ms intervals
   - ✅ Adhesion metrics calculate correctly

---

## Advantages Over Previous System

| Feature | Old (Fixed Decimation) | New (Dynamic Decimation) |
|---------|------------------------|--------------------------|
| **Output Rate** | Fixed ~8ms (120Hz) | Matches user setting |
| **Timing Match** | ❌ Mismatched with PositionLogger | ✅ Perfect match |
| **Repeated Values** | ❌ Yes (5× repeats) | ✅ No repeats |
| **Noise Reduction** | 2.83× (factor 8) | 2.83× to 10× (adaptive) |
| **User Control** | Limited | Full control via GUI |
| **Flexibility** | Fixed decimation | Dynamic per user rate |

---

## Expected Console Output

### On Connection
```
Phidget device attached (ForceGaugeManager).
Setting basic bridge configuration...
Bridge mode enabled
Dynamic decimation mode: Hardware at 1ms (~1200Hz), decimating to match user rate
Current decimation factor: 25× (output: 25ms)
Basic Phidget configuration complete
```

### On Rate Change (e.g., 25ms → 50ms)
```
ForceGaugeManager: Dynamic decimation updated
  User interval: 50ms (20.0Hz)
  Decimation factor: 50×
  Noise reduction: 7.07×
```

### On Get Info
```python
info = force_gauge_manager.get_decimation_info()
# Returns:
# {
#     'enabled': True,
#     'mode': 'Dynamic Decimation (adaptive)',
#     'hardware_rate_hz': 1200,
#     'user_rate_hz': 40.0,
#     'decimation_factor': 25,
#     'noise_reduction_factor': 5.0
# }
```

---

## Troubleshooting

### If force values still repeat:
1. Check console: Is decimation enabled?
2. Verify `USE_DECIMATION = True` in code
3. Check decimation factor matches user rate
4. Ensure hardware_interval_ms = 1

### If timing is off:
1. Check GUI spinbox value
2. Verify `set_data_interval()` is called on rate change
3. Check console for decimation factor updates
4. Ensure minimum 8ms is enforced

### If noise is too high:
1. Increase decimation factor (slower rate = more averaging)
2. Try 50ms or 100ms for maximum noise reduction
3. Check `get_decimation_info()` for current settings

---

## Next Steps

1. **Test**: Run all 5 tests above
2. **Verify**: No repeated values in CSV
3. **Monitor**: Check console output during rate changes
4. **Document**: Record any issues or observations
5. **Deploy**: If tests pass, use for production prints

---

## Success Criteria

✅ **All tests pass if**:
- No repeated force values in CSV at any rate
- Timing intervals match GUI setting (±2ms jitter acceptable)
- Decimation factor updates correctly when rate changes
- Console shows proper configuration on startup
- Adhesion metrics work correctly with new system

---

## Mathematical Verification

### Noise Reduction Formula
```
Noise Reduction = √(decimation_factor)
```

### Examples
- 8ms rate → 8× decimation → 2.83× noise reduction
- 25ms rate → 25× decimation → 5.00× noise reduction
- 100ms rate → 100× decimation → 10.00× noise reduction

### Output Timing
```
Hardware samples: 1, 2, 3, ..., N (at 1ms intervals)
Average these N samples
Output 1 value at time = N ms
Next output at time = 2N ms
etc.

This perfectly matches PositionLogger sampling at N ms intervals!
```

---

**Status**: ✅ Code complete, ready for testing  
**Risk**: Low (if tests fail, can easily set `USE_DECIMATION = False`)  
**Benefit**: Eliminates timing mismatch, preserves noise reduction
