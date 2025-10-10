# Data Smoothing Methods - History and Current Implementation

## Current Smoothing Method (Oct 1, 2025 - Present)

### **Gaussian Filter**

**File:** `support_modules/adhesion_metrics_calculator.py`  
**Method:** `_apply_smoothing()`

**Implementation:**
```python
from scipy.ndimage import gaussian_filter1d

def _apply_smoothing(self, force_data: np.ndarray) -> np.ndarray:
    """Apply Gaussian smoothing filter."""
    smoothed = gaussian_filter1d(force_data, sigma=self.smoothing_sigma)
    return smoothed
```

**Default Parameters:**
- **`smoothing_sigma = 0.5`** (standard deviation of Gaussian kernel)

**Characteristics:**
- **Type:** Gaussian convolution filter
- **Effect:** Applies a Gaussian-weighted average to the data
- **Smoothness:** Very smooth, no preservation of peaks/edges
- **Phase:** Zero phase shift (symmetric kernel)
- **Endpoint Handling:** Reflects data at boundaries

### How Gaussian Filter Works

The Gaussian filter applies a weighted average where weights follow a Gaussian (bell curve) distribution:

```
Weight distribution (sigma=0.5):
  |
1 |     *
  |    ***
  |   *****
  |  *******
  | *********
  +------------> Distance from center
     -2σ   +2σ
```

**Formula:**
```
G(x) = (1/√(2πσ²)) * e^(-x²/(2σ²))

smoothed[i] = Σ G(j-i) * force[j]
```

**Example with sigma=0.5:**
- Points within ±1 sample get high weight (~60%)
- Points within ±2 samples get medium weight (~14%)
- Points beyond ±3σ get negligible weight (<1%)

---

## Previous Smoothing Method (Sept 22, 2025)

### **Savitzky-Golay Filter**

**File:** `adhesion_metrics_calculator.py` (root directory, Sept 22 version)  
**Method:** `_apply_smoothing()`

**Implementation:**
```python
from scipy.signal import savgol_filter

def _apply_smoothing(self, force_data: np.ndarray) -> np.ndarray:
    """Apply Savitzky-Golay filter."""
    smoothed = savgol_filter(force_data,
                            window_length=self.smoothing_window,
                            polyorder=self.smoothing_polyorder)
    return smoothed
```

**Default Parameters:**
- **`smoothing_window = 3`** (number of points in averaging window, must be odd)
- **`smoothing_polyorder = 1`** (polynomial order for fit, 1 = linear)

**Characteristics:**
- **Type:** Polynomial least-squares fitting filter
- **Effect:** Fits a polynomial to sliding window of data
- **Smoothness:** Moderate, preserves peak shapes better
- **Phase:** Zero phase shift (symmetric window)
- **Endpoint Handling:** Polynomial extrapolation

### How Savitzky-Golay Filter Works

The Savitzky-Golay filter fits a polynomial (in this case, linear) to each window of data:

```
Window size = 3, polyorder = 1 (linear fit):

Original:  ... | a | b | c | ...
            
Fit line through [a, b, c]
Use fitted value at center point b

Very light smoothing - preserves shape!
```

**Example with window=3, poly=1:**
- Fits a straight line through 3 consecutive points
- Uses the middle point of the fitted line
- Effectively a 3-point moving average with edge preservation

---

## Comparison of Methods

| Feature | **Gaussian (Current)** | **Savitzky-Golay (Sept 22)** |
|---------|----------------------|---------------------------|
| **Smoothness** | Very smooth | Moderate |
| **Peak Preservation** | Poor - rounds peaks | Good - preserves peaks |
| **Noise Reduction** | Excellent | Good |
| **Computational Cost** | Low | Low |
| **Parameter Meaning** | Sigma (spread) | Window size + polynomial order |
| **Default Strength** | sigma=0.5 (light) | window=3, poly=1 (very light) |
| **Best For** | Noisy data, baseline detection | Peak detection, derivative calculation |

## Visual Comparison

```
Raw Data (noisy):
Force
  |  *   *
  | * * * *  *
  |*  *   * * *
  +--------------> Time

Gaussian (sigma=0.5):
Force
  |    ___
  |   /   \
  |  /     \
  +--------------> Time
  (very smooth, peak slightly reduced)

Savitzky-Golay (window=3, poly=1):
Force
  |    _
  |   / \
  |  /   \
  +--------------> Time
  (moderate smooth, peak well preserved)
```

## Why the Change?

The change from Savitzky-Golay to Gaussian happened on **October 1, 2025** when the entire calculator was rewritten.

### Likely Reasons:
1. **Simplicity:** Gaussian filter has only 1 parameter (sigma) vs 2 for Savitzky-Golay
2. **Robustness:** Gaussian filter is more robust to endpoint effects
3. **Consistency:** Gaussian is a standard choice in signal processing
4. **Implementation:** `gaussian_filter1d` is simpler to implement than `savgol_filter`

### Trade-offs:
- ✅ **Gaussian:** Better noise reduction, simpler
- ❌ **Gaussian:** May round peaks slightly, less derivative-friendly
- ✅ **Savitzky-Golay:** Better peak preservation, good for derivatives
- ❌ **Savitzky-Golay:** More parameters to tune, slightly more complex

## Impact on Results

### With Current Gaussian Filter (sigma=0.5):
- Slightly smoother force curves
- Peak forces may be **slightly lower** (peaks rounded)
- Better noise reduction in baseline regions
- Second derivatives will be smoother

### With Previous Savitzky-Golay (window=3, poly=1):
- Better peak shape preservation
- Peak forces more accurate (less rounding)
- Slightly noisier baseline
- Second derivatives may have more local variations

## Which is Better?

**For your application (adhesion testing):**

### Use **Gaussian** if:
- ✅ Data is very noisy
- ✅ Baseline detection is critical
- ✅ Absolute peak height is less important than peak location
- ✅ Need smooth second derivatives

### Use **Savitzky-Golay** if:
- ✅ Peak heights are critical measurements
- ✅ Need accurate derivatives
- ✅ Data has moderate noise
- ✅ Want to preserve original signal shape

## Current Parameters

**In your code right now:**
```python
calculator = AdhesionMetricsCalculator(
    smoothing_sigma=0.5,  # Gaussian standard deviation
    baseline_threshold_factor=0.002,
    min_peak_height=0.01,
    min_peak_distance=50
)
```

**To change back to Savitzky-Golay (if desired):**
You would need to modify `_apply_smoothing()` in `adhesion_metrics_calculator.py`:
```python
# Change imports
from scipy.signal import savgol_filter  # Instead of gaussian_filter1d

# Change __init__ parameters
def __init__(self,
             smoothing_window=3,      # Instead of smoothing_sigma
             smoothing_polyorder=1,
             ...):

# Change _apply_smoothing method
def _apply_smoothing(self, force_data: np.ndarray) -> np.ndarray:
    if len(force_data) < self.smoothing_window:
        return force_data.copy()
    
    smoothed = savgol_filter(force_data,
                            window_length=self.smoothing_window,
                            polyorder=self.smoothing_polyorder)
    return smoothed
```

## Recommendation

**For adhesion testing with second derivative analysis:**

Since you're now using the corrected second derivative zero-crossing method, **Gaussian smoothing is probably fine** because:
1. You need smooth second derivatives for accurate zero-crossing detection
2. Gaussian provides better noise reduction
3. sigma=0.5 is a light smoothing that won't distort the curve significantly

**However**, if you notice:
- Peak forces are significantly lower than expected
- Second derivative has too much noise
- Results are inconsistent

You might want to:
1. Try adjusting `sigma` (0.3 for lighter, 0.7 for heavier)
2. Or switch back to Savitzky-Golay with larger window (5 or 7)

## Testing Smoothing Methods

To visualize the effect of different smoothing:
```python
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter1d
from scipy.signal import savgol_filter

# Load your data
force = # ... your force data

# Try different methods
gaussian_smooth = gaussian_filter1d(force, sigma=0.5)
savgol_smooth = savgol_filter(force, window_length=3, polyorder=1)

# Plot comparison
plt.figure(figsize=(12, 4))
plt.plot(force, 'gray', alpha=0.5, label='Raw')
plt.plot(gaussian_smooth, 'b-', label='Gaussian (sigma=0.5)')
plt.plot(savgol_smooth, 'r-', label='Savitzky-Golay (win=3, poly=1)')
plt.legend()
plt.show()
```

---

## Summary

**Current Method (Oct 1, 2025):**
- **Gaussian filter** with `sigma=0.5`
- Simple, robust, smooth
- Good for noisy data and second derivative analysis

**Previous Method (Sept 22, 2025):**
- **Savitzky-Golay filter** with `window=3`, `polyorder=1`
- Better peak preservation
- Good for accurate peak measurements

**Bottom Line:** Both methods are valid. Current Gaussian method is probably fine for your zero-crossing analysis, but you can switch back to Savitzky-Golay if peak accuracy is critical.
