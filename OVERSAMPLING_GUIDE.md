# Phidget Bridge Oversampling & Noise Reduction Techniques

## 📊 Your Hardware: Phidget Bridge (1.2kHz capable)

**Specifications:**
- Maximum data rate: 1200 Hz (0.83ms interval)
- Minimum data interval: 8ms (125 Hz) - software limit
- Bridge gain options: 1x, 2x, 4x, 8x, 16x, 32x, 64x, 128x
- Resolution: 16-bit (but effective resolution depends on noise)

## 🎯 Noise Reduction Strategies

### Strategy 1: Hardware Gain Adjustment
**What it does:** Amplifies signal before digitization
**Benefit:** Better use of ADC range, can reduce quantization noise
**Tradeoff:** Amplifies sensor noise too, can saturate with large signals

```python
# In your code:
phidget.setBridgeGain(BridgeGain.BRIDGE_GAIN_128)  # Maximum gain
```

**Recommended approach:**
- Test different gain levels (1x, 2x, 4x, 8x)
- Find sweet spot where signal is large but doesn't saturate
- Higher isn't always better if sensor noise dominates

---

### Strategy 2: Oversampling with Software Averaging
**What it does:** Read data very fast, average multiple samples
**Benefit:** Reduces random noise by √N (N = number of samples averaged)
**Tradeoff:** Increased CPU usage, some lag

**Maximum achievable with Phidget Bridge:**
```
Data Interval: 8ms (minimum, gives 125 Hz)
Oversample Factor: 12 samples averaged
Output Rate: ~10 Hz (every 12×8ms = 96ms)
Noise Reduction: √12 ≈ 3.46×
```

**Practical implementation:**
```python
# Collect 12 samples at 8ms intervals
samples = []
for i in range(12):
    samples.append(read_voltage())
    time.sleep(0.008)

# Average them
averaged_value = sum(samples) / 12
# Noise is now 3.46× lower!
```

---

### Strategy 3: Moving Average Filter (Current Implementation)
**What it does:** Continuously average last N samples
**Benefit:** Smooth real-time filtering, √N noise reduction
**Tradeoff:** Introduces lag = N × sampling_interval

**Current in your system:**
```
Sampling: 25ms (40 Hz)
Window: 10 samples
Lag: 250ms
Noise reduction: √10 ≈ 3.16×
```

**Optimized version:**
```
Sampling: 8ms (125 Hz)
Window: 50 samples  
Lag: 400ms
Noise reduction: √50 ≈ 7.07×
```

---

### Strategy 4: Decimation (Oversample + Downsample)
**What it does:** Sample fast, average in batches, output slow
**Benefit:** Best noise reduction for given output rate
**Tradeoff:** No continuous output, batched results

**Example:**
```
Input: 8ms sampling (125 Hz)
Average: 125 samples (1 second worth)
Output: 1 Hz
Noise reduction: √125 ≈ 11.18× 
```

---

### Strategy 5: Median Filter
**What it does:** Use median instead of mean
**Benefit:** Immune to outliers/spikes
**Tradeoff:** Doesn't reduce Gaussian noise as well as averaging

**Use when:** You have occasional spikes/glitches

---

### Strategy 6: Kalman Filter
**What it does:** Optimal statistical filtering using prediction model
**Benefit:** Best possible noise reduction for given lag
**Tradeoff:** Complex to implement, requires tuning

**Use when:** You need maximum performance and can invest time

---

### Strategy 7: Change Trigger (Already in your code!)
**What it does:** Only update when force changes significantly
**Benefit:** Reduces CPU, ignores noise when static
**Tradeoff:** Might miss small changes

**Current setting:**
```python
self.force_change_trigger_N = 0.001  # 1 millinewton
```

---

## 🚀 Recommended Configuration for Your Application

### For 10ms Output Rate with Maximum Noise Reduction:

**Method: Oversampling + Decimation**

```python
# In ForceGaugeManager __init__ or configuration:

# 1. Set minimum data interval
self.voltage_ratio_input.setDataInterval(8)  # 125 Hz

# 2. Buffer for oversampling
self.oversample_buffer = deque(maxlen=16)  # 16 samples
self.oversample_counter = 0
self.oversample_target = 16  # Average every 16 samples

# 3. In _onVoltageRatioChange callback:
def _onVoltageRatioChange(self, phidget, voltageRatio):
    self.oversample_buffer.append(voltageRatio)
    self.oversample_counter += 1
    
    # Every 16 samples (16×8ms = 128ms ≈ 8 Hz output)
    if self.oversample_counter >= self.oversample_target:
        # Calculate average
        averaged_voltage = sum(self.oversample_buffer) / len(self.oversample_buffer)
        
        # Process this averaged value
        # (rest of your force calculation)
        
        self.oversample_counter = 0
        # Noise reduction: √16 = 4× better!
```

**Result:**
- Output rate: ~8 Hz (128ms update)
- Noise reduction: 4× (from √16)
- Lag: 128ms
- CPU usage: Reasonable

---

## 🔬 Advanced: Adaptive Oversampling

**Idea:** Use different oversampling based on conditions

```python
# When force is changing rapidly (printing):
oversample_target = 4  # Light filtering, fast response

# When force is stable (monitoring):
oversample_target = 50  # Heavy filtering, low noise

# Automatically switch based on force rate of change
```

---

## 📊 Comparison Table

| Method | Noise Reduction | Output Rate | Lag | CPU Usage | Complexity |
|--------|----------------|-------------|-----|-----------|------------|
| Hardware Gain 8× | 1-2× | No change | 0ms | None | Easy |
| Moving Avg (10) | 3.16× | Continuous | 250ms | Low | Easy |
| Moving Avg (50) | 7.07× | Continuous | 400ms | Medium | Easy |
| Decimation (16) | 4× | ~8 Hz | 128ms | Low | Medium |
| Decimation (125) | 11.18× | 1 Hz | 1000ms | Low | Medium |
| Kalman Filter | 5-10× | Continuous | 50-200ms | High | Hard |

---

## 💡 My Recommendation for Your System

**Best overall approach:**

1. **Set bridge gain to 4× or 8×**
   - Test to find sweet spot
   - Improves signal without over-amplifying noise

2. **Use 8ms data interval** (125 Hz sampling)

3. **Implement decimation with 12-16 samples**
   - Gives ~10 Hz output rate
   - 3.5-4× noise reduction
   - Acceptable 100-128ms lag for printing

4. **Keep change trigger** for static periods

**Expected improvement:** **3-4× better SNR** compared to current 25ms sampling

---

## 🛠️ Want me to implement this?

I can create:
1. **Modified ForceGaugeManager** with oversampling
2. **Test file** to compare different methods
3. **Configuration GUI** to adjust parameters on-the-fly

Which would you like?
