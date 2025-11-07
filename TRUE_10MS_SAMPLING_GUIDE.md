# Achieving True 10ms Sampling with Oversampling

## 🎯 Your Requirement
- **Effective output rate:** 10ms (100 Hz)
- **Measuring:** Fast events near 10ms timescale
- **Goal:** Maximum noise reduction without missing events

## ⚡ The Solution: High-Speed Oversampling

### Hardware Capability
Your Phidget Bridge can sample at **up to 1200 Hz** (0.83ms per sample)!

**How to unlock it:**
```python
setVoltageRatioChangeTrigger(0.0)  # Stream at maximum hardware rate
```

This bypasses the 8ms (125 Hz) software limit and gives you full hardware speed.

## 📊 The Perfect Configuration

### For 10ms Output Rate:

**Input:** 1200 Hz hardware sampling (0.83ms per sample)  
**Processing:** Collect 12 samples per 10ms window  
**Output:** 100 Hz (every 10ms)  
**Noise Reduction:** √12 = **3.46× better SNR**

### Implementation:

```python
class FastOversamplingForceGauge:
    def __init__(self):
        # Buffer for 10ms window
        self.sample_window = deque(maxlen=12)  # 12 samples @ 1200Hz ≈ 10ms
        self.last_output_time = 0
        self.output_interval = 0.010  # 10ms
        
    def configure_phidget(self):
        """Set up for maximum speed sampling."""
        # Maximum speed configuration
        self.voltage_ratio_input.setVoltageRatioChangeTrigger(0.0)  # Max speed!
        self.voltage_ratio_input.setDataInterval(1)  # Advisory minimum
        self.voltage_ratio_input.setBridgeGain(BridgeGain.BRIDGE_GAIN_1)
        
    def on_voltage_change(self, phidget, voltage_ratio):
        """Called at ~1200 Hz - collect samples."""
        current_time = time.time()
        
        # Add to window
        self.sample_window.append(voltage_ratio)
        
        # Output every 10ms
        if current_time - self.last_output_time >= self.output_interval:
            if len(self.sample_window) > 0:
                # Average all samples in the 10ms window
                averaged_voltage = sum(self.sample_window) / len(self.sample_window)
                
                # Calculate force
                if self.GAIN and self.OFFSET:
                    force = self.GAIN * (averaged_voltage - self.OFFSET)
                    
                    # Output this force value
                    self.latest_calibrated_force = force
                    self.update_gui(force)
                    
                self.last_output_time = current_time
```

## 🔬 Expected Performance

### Sampling Characteristics:

| Metric | Value |
|--------|-------|
| Hardware sampling rate | ~1200 Hz |
| Samples per 10ms window | ~12 samples |
| Output rate | 100 Hz (10ms) |
| Nyquist frequency | 50 Hz (can measure up to 50 Hz phenomena) |
| Noise reduction | 3.46× (√12) |
| Latency | 10ms (one window) |

### What You Can Measure:

✅ **Events as fast as 20ms duration** (Nyquist = 50 Hz)  
✅ **Step changes with <1ms resolution** (captured at 1200 Hz)  
✅ **Smooth force curves** with 3.5× less noise  
✅ **No aliasing** of fast transients  

## 💡 Advanced: Adaptive Windowing

For even better performance, use **adaptive window size**:

```python
class AdaptiveOversamplingForceGauge:
    def __init__(self):
        self.min_samples = 12   # Minimum for noise reduction
        self.max_samples = 60   # Maximum for heavy filtering
        self.current_window_size = 12
        
    def on_voltage_change(self, phidget, voltage_ratio):
        """Adaptive oversampling."""
        current_time = time.time()
        self.sample_window.append(voltage_ratio)
        
        # Calculate rate of change
        if len(self.sample_window) >= 2:
            recent_std = np.std(list(self.sample_window)[-10:])
            
            # Adapt window size
            if recent_std > threshold_high:
                # Fast changes - use smaller window (less lag)
                self.current_window_size = self.min_samples
            else:
                # Slow changes - use larger window (more filtering)
                self.current_window_size = self.max_samples
        
        # Output when window is full
        if len(self.sample_window) >= self.current_window_size:
            averaged_voltage = sum(self.sample_window) / len(self.sample_window)
            # ... process ...
            self.sample_window.clear()
```

## 🚀 Practical Recommendations

### For Your 3D Printing Application:

**During Active Printing (Fast Response Needed):**
```python
window_size = 12 samples  # 10ms output, 3.5× noise reduction
```

**During Monitoring (Noise Reduction Priority):**
```python
window_size = 60 samples  # 50ms output, 7.7× noise reduction
```

**During Pre-Calibration (Maximum Quality):**
```python
window_size = 120 samples  # 100ms output, 11× noise reduction
```

## 🔧 Testing the Configuration

Run the updated test file:
```powershell
python test_oversampling_methods.py
```

**What to look for:**
1. **"Actual: ~1000-1200 Hz"** - confirms max hardware speed
2. **Decimation with factor=12** - simulates 10ms output
3. **Std Dev improvement** - should see 3-4× reduction

## ⚠️ Important Notes

### CPU Usage:
- Processing 1200 samples/second is manageable
- Python can handle this easily with proper buffering
- Use deque (fixed-size buffer) for efficiency

### Timing Accuracy:
- Hardware timing is very precise (±microseconds)
- Software 10ms output may jitter slightly (±1-2ms)
- Use `time.perf_counter()` for best accuracy

### Thread Safety:
- High-speed callbacks need careful threading
- Your current architecture (queue-based) handles this well
- Don't do heavy processing in the callback!

## 📈 Verification

**Test that you're getting full speed:**

```python
# Add to your code:
import time

sample_times = []

def on_voltage_change(self, phidget, voltage_ratio):
    sample_times.append(time.perf_counter())
    
    # Every second, calculate actual rate
    if len(sample_times) >= 1000:
        intervals = np.diff(sample_times[-1000:])
        avg_interval = np.mean(intervals)
        actual_rate = 1.0 / avg_interval
        print(f"Actual sampling rate: {actual_rate:.0f} Hz")
        sample_times.clear()
```

Expected output: **~1000-1200 Hz**

## ✅ Bottom Line

**You CAN achieve:**
- ✅ True 10ms effective output rate (100 Hz)
- ✅ Capture events as fast as 1ms (hardware limit)
- ✅ 3.5× noise reduction from oversampling
- ✅ No aliasing of fast transients

**The key:** Use `setVoltageRatioChangeTrigger(0.0)` to unlock full hardware speed!

Run the updated test file to see it in action!
