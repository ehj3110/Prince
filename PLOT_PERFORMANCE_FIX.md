# Force Gauge Plot Performance Fix
**Date**: October 17, 2025  
**Issue**: GUI slowdown after force gauge plot has been running for extended periods

---

## 🐛 Problem Identified

After the force gauge plot runs for a while (especially during long prints), the GUI becomes sluggish. This is caused by:

1. **Data accumulation** - Even though we trim to `MAX_PLOT_POINTS`, matplotlib's internal structures can accumulate memory
2. **Rendering overhead** - Constantly redrawing thousands of points puts strain on the rendering pipeline
3. **No periodic deep cleanup** - The original trimming only happens when threshold is exceeded

---

## ✅ Solution Implemented

### 1. Reduced MAX_PLOT_POINTS
**Before**: `MAX_PLOT_POINTS = 5000` (100 seconds at 50Hz)  
**After**: `MAX_PLOT_POINTS = 2000` (40 seconds at 50Hz)

**Rationale**: 40 seconds of data is still plenty for visual monitoring, and significantly reduces rendering overhead.

### 2. Added Aggressive Periodic Cleanup
**New Feature**: Every 5 minutes, automatically trim to 50% of `MAX_PLOT_POINTS`

```python
# Every 5 minutes (300 seconds)
if current_time - self.last_aggressive_clear_time > 300:
    aggressive_limit = self.MAX_PLOT_POINTS // 2  # 1000 points
    self.plot_data_x = self.plot_data_x[-aggressive_limit:]
    self.plot_data_y_position = self.plot_data_y_position[-aggressive_limit:]
    self.plot_data_y_force = self.plot_data_y_force[-aggressive_limit:]
```

**Rationale**: This prevents gradual memory buildup in matplotlib's internal structures by periodically doing a deeper cut.

### 3. Added Tracking Variables
- `self.last_aggressive_clear_time` - Timestamp of last aggressive cleanup
- Logs cleanup events: `"Aggressive plot cleanup: trimmed to X points"`

---

## 📊 Expected Performance Improvements

| Metric | Before | After |
|--------|--------|-------|
| Max plot points | 5000 | 2000 (60% reduction) |
| Display window | 100 seconds | 40 seconds |
| Memory per data point | ~48 bytes | ~48 bytes |
| Total plot memory | ~240 KB | ~96 KB |
| Periodic cleanup | None | Every 5 minutes → 1000 points |
| Long-term memory growth | Linear | Bounded |

---

## 🔧 Files Modified

### `support_modules/SensorDataWindow.py`

**Line 33**: Reduced `MAX_PLOT_POINTS`
```python
MAX_PLOT_POINTS = 2000  # Reduced from 5000
```

**Lines 244-245**: Added tracking variables
```python
self.plot_update_counter = 0
self.last_aggressive_clear_time = time.time()
```

**Lines 944-954**: Added periodic aggressive cleanup
```python
# Every 5 minutes, trim to 50% of MAX_PLOT_POINTS
if current_time - self.last_aggressive_clear_time > 300:
    aggressive_limit = self.MAX_PLOT_POINTS // 2
    # ... trim logic ...
```

---

## 🧪 Testing Recommendations

### Test 1: Short-Term Performance
1. **Start live readout** with force gauge enabled
2. **Let run for 5 minutes** (one aggressive cleanup cycle)
3. **Check console** for: `"Aggressive plot cleanup: trimmed to 1000 points"`
4. **Verify GUI responsiveness** remains good

### Test 2: Long Print Performance
1. **Start a long print** (30+ minutes)
2. **Monitor GUI responsiveness** throughout
3. **Check console** for periodic cleanup messages (every 5 minutes)
4. **Verify no slowdown** after extended operation

### Test 3: Plot Data Visibility
1. **Verify 40 seconds of data** is sufficient for monitoring
2. **Check that plot updates** remain smooth
3. **Confirm no visual artifacts** from aggressive cleanup

---

## 🔍 Monitoring & Debugging

### Console Messages
Look for these messages to confirm cleanup is working:
```
[SensorDataWindow] Aggressive plot cleanup: trimmed to 1000 points
```

Should appear every 5 minutes during live readout.

### Memory Monitoring
If you want to track memory usage:
```python
import psutil
import os

process = psutil.Process(os.getpid())
print(f"Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB")
```

### Performance Metrics
- **GUI response time**: Should stay < 100ms for button clicks
- **Plot update rate**: Should maintain ~20-30 FPS
- **Memory growth**: Should plateau after 5-10 minutes, not grow linearly

---

## ⚙️ Tuning Options

If performance is still not satisfactory, adjust these parameters:

### Reduce Display Window Further
```python
MAX_PLOT_POINTS = 1000  # 20 seconds at 50Hz
```

### Increase Cleanup Frequency
```python
if current_time - self.last_aggressive_clear_time > 180:  # 3 minutes instead of 5
```

### More Aggressive Cleanup
```python
aggressive_limit = self.MAX_PLOT_POINTS // 4  # Keep only 25% instead of 50%
```

---

## 🔄 Rollback Plan

If the reduced plot window causes issues:

**Restore original MAX_PLOT_POINTS**:
```python
MAX_PLOT_POINTS = 5000  # Back to original
```

**Keep the aggressive cleanup** (it's still beneficial):
```python
# Cleanup code stays, just with larger limits
aggressive_limit = 2500  # 50% of 5000
```

---

## 📝 Additional Performance Tips

### For Very Long Prints (> 1 hour):
1. **Manually clear plot** periodically using "Clear Plot" button
2. **Restart live readout** if GUI becomes sluggish
3. **Monitor console** for cleanup messages

### Alternative: Use collections.deque
If issues persist, consider replacing lists with `deque` for automatic size limiting:

```python
from collections import deque

self.plot_data_x = deque(maxlen=MAX_PLOT_POINTS)
self.plot_data_y_position = deque(maxlen=MAX_PLOT_POINTS)
self.plot_data_y_force = deque(maxlen=MAX_PLOT_POINTS)
```

This automatically discards old data when max length is reached, eliminating manual trimming.

---

## 📚 Related Issues

- **Original data clearing implementation**: Previously added `MAX_PLOT_POINTS` trimming
- **PeakForceLogger buffering**: Already handles data chunking with `DATA_CHUNK_SIZE = 5000`
- **Matplotlib draw optimization**: Already using `draw_idle()` instead of `draw()`

---

## 🎯 Success Criteria

✅ **GUI remains responsive** after 30+ minute prints  
✅ **Plot updates smoothly** throughout entire print  
✅ **Memory usage plateaus** instead of growing linearly  
✅ **40 seconds of data visible** is sufficient for monitoring  
✅ **Periodic cleanup messages** appear in console every 5 minutes  

---

**Status**: ✅ Implemented and ready for testing  
**Impact**: Should significantly improve GUI performance during long prints  
**Risk**: Low - only affects plot display, not data logging
