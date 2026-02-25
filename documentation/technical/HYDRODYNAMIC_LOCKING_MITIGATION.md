# Hydrodynamic Locking Mitigation
**Date:** January 11, 2026  
**Feature:** Time-based Peak Detection Skip

## Problem Statement
At higher retraction speeds (e.g., 400 μm/s), larger cross-sectional areas can experience hydrodynamic locking effects that create false force spikes in the first ~150ms of layer separation. These spikes are NOT adhesion-related but rather fluid dynamics artifacts.

## Solution
Added a configurable time skip parameter to the peak detection algorithm. The calculator can now ignore the first N milliseconds of data when searching for the peak force.

### Implementation

#### 1. Updated `AdhesionMetricsCalculator`
**New Parameter:** `skip_initial_time_ms` (default: 0)

```python
# Example: Skip first 150ms
calculator = AdhesionMetricsCalculator(skip_initial_time_ms=150)
```

**Modified Method:** `_find_peak_force(smoothed_force, times)`
- Now accepts optional `times` array
- If `skip_initial_time_ms > 0`, finds first index after skip time
- Searches for peak only in valid region (after skip time)

```python
def _find_peak_force(self, smoothed_force: np.ndarray, times: Optional[np.ndarray] = None):
    """Find peak force, optionally skipping initial time period"""
    start_idx = 0
    if self.skip_initial_time_ms > 0 and times is not None:
        skip_time_s = self.skip_initial_time_ms / 1000.0
        relative_times = times - times[0]
        skip_mask = relative_times >= skip_time_s
        if np.any(skip_mask):
            start_idx = np.argmax(skip_mask)
    
    peak_idx_relative = np.argmax(smoothed_force[start_idx:])
    peak_idx = start_idx + peak_idx_relative
    return peak_idx, smoothed_force[peak_idx]
```

#### 2. Updated `batch_process_v9.py`
**Automatic Configuration:** Detects 400 μm/s conditions and applies 150ms skip

```python
# Configure calculator for this condition
skip_time_ms = 150 if params['speed_um_s'] == 400 else 0
if skip_time_ms > 0:
    print(f"  ⚠️  Applying {skip_time_ms}ms peak detection skip")
    self.calculator = AdhesionMetricsCalculator(skip_initial_time_ms=skip_time_ms)
    self.processor = RawDataProcessor(self.calculator)
```

### Usage

#### Automatic (V9 Batch Processing)
Simply run the batch processor - it will automatically apply the skip for 400 μm/s conditions:

```powershell
python batch_process_v9.py
```

Output will show:
```
Processing folder: PDMS_500um_V23Ext_Water_400
  Speed: 400 um/s
  ⚠️  Applying 150ms peak detection skip (hydrodynamic locking mitigation)
```

#### Manual (Custom Scripts)
For other processing scenarios:

```python
from adhesion_metrics_calculator import AdhesionMetricsCalculator

# For data with hydrodynamic issues
calc = AdhesionMetricsCalculator(skip_initial_time_ms=150)

# Process as normal
results = calc.calculate_from_arrays(time, position, force)
```

### Configuration Guidelines

**When to use skip:**
- High retraction speeds (≥400 μm/s)
- Large cross-sectional areas (>50 mm²)
- Visible force spikes in first 100-200ms
- Non-physical peak forces (much higher than expected)

**Recommended skip times:**
- **400 μm/s:** 150ms (automatically applied)
- **600 μm/s:** 100ms (configure manually if needed)
- **1000 μm/s:** 50ms or 0ms (usually not needed)

**How to verify it's working:**
1. Check console output for skip warning
2. Compare peak forces before/after (should be lower and more realistic)
3. Check peak timing (should be >150ms from start)

### Technical Details

**Time Calculation:**
```python
skip_time_s = skip_initial_time_ms / 1000.0  # Convert ms to seconds
relative_times = times - times[0]  # Normalize to start at 0
valid_indices = relative_times >= skip_time_s
```

**Peak Search:**
- Original: `peak_idx = argmax(force)`
- With skip: `peak_idx = start_idx + argmax(force[start_idx:])`

**Impact on Metrics:**
- ✅ Peak force: Found after skip period (correct)
- ✅ Peak time: Relative to lifting start (unchanged)
- ✅ Work of adhesion: Integrated from pre-initiation (unchanged)
- ✅ Baseline: Calculated from 80% lift point (unchanged)
- ✅ All other metrics: Derived from corrected peak (improved)

### Backward Compatibility
- Default `skip_initial_time_ms=0` preserves existing behavior
- All existing code continues to work without modification
- Optional parameter - only affects folders explicitly configured

### Example Output Comparison

**Before (False Spike):**
```
Layer 350 (Area: 100 mm²)
  Peak Force: 8.5 N (at t=0.08s)  ← Hydrodynamic spike!
  Work of Adhesion: 3.2 mJ
```

**After (True Peak):**
```
Layer 350 (Area: 100 mm²)
  Peak Force: 4.2 N (at t=0.21s)  ← Real adhesion peak
  Work of Adhesion: 1.8 mJ
```

### Testing
To test on specific data:

```python
# Test with skip
calc_skip = AdhesionMetricsCalculator(skip_initial_time_ms=150)
results_skip = calc_skip.calculate_from_csv('autolog_L350.csv')

# Test without skip
calc_normal = AdhesionMetricsCalculator()
results_normal = calc_normal.calculate_from_csv('autolog_L350.csv')

# Compare
print(f"Without skip: {results_normal['peak_force']:.2f} N at {results_normal['peak_force_time']:.3f}s")
print(f"With skip: {results_skip['peak_force']:.2f} N at {results_skip['peak_force_time']:.3f}s")
```

### Future Enhancements
Potential improvements:
1. **Adaptive skip:** Calculate skip time based on area and speed
2. **Spike detection:** Automatically identify hydrodynamic spikes
3. **Configuration file:** Store skip settings per condition in CSV
4. **Validation plot:** Show skipped region in diagnostic plots

### Related Files
- `support_modules/adhesion_metrics_calculator.py` - Core implementation
- `batch_processors/batch_process_v9.py` - Automatic configuration
- `post-processing/RawData_Processor.py` - Passes times to calculator

### Notes
- Skip time is applied to **each layer independently**
- Does not affect raw data or CSV files
- Only affects peak detection algorithm
- Can be disabled by setting to 0
