# Phase-Aware Adhesion Metrics Design

**Date**: November 7, 2025  
**Issue**: Pre-initiation searches past phase boundaries, boundary detection hardcoded to 6mm  
**Goal**: Enable real-time adhesion metrics with phase awareness, no raw data saving required

---

## Problems Identified

### 1. Pre-Initiation Searches Too Far Back
**Current Behavior**:
- `_find_pre_initiation()` searches backward from peak to baseline
- No awareness of phase boundaries
- Searches past Exposure → Pause → Sandwich phases
- When sandwich creates pre-existing force above baseline, pre-initiation time becomes very long

**Physical Context**:
```
Time →
[Sandwich: Press down, create force] → [Pause] → [Exposure] → [Lift: Peel starts]
                    ↑                                              ↑
            Pre-existing force                               Actual peel begins
```

**Problem**: Backward search finds baseline crossing in Sandwich phase, not true pre-initiation

### 2. Boundary Detection Hardcoded to 6mm
**Current Code** (RawData_Processor.py line 265):
```python
EXPECTED_LIFT_DISTANCE = 6.0  # mm (from instruction file)
DISTANCE_TOLERANCE = 0.5      # Allow 5.5-6.5mm
```

**Problem**: Overstep distance is variable (user changes between prints)
- Current setting: 6mm
- Future prints: Could be 0mm, 3mm, 8mm, etc.
- Hardcoded detection will fail for non-6mm prints

### 3. Phase Information Not Accessible in Real-Time
**Current State**:
- PositionLogger tracks phases: Lift, Retract, Pause, Sandwich, Exposure
- Phase info written to CSV only
- PeakForceLogger cannot access phases during printing
- User wants real-time metrics without saving all raw data

**Need**: Interface to pass phase events from PositionLogger → PeakForceLogger → AdhesionCalculator

---

## Solution Design

### Phase Detection System (Already Exists)

**PositionLogger._determine_phase()** (lines 102-165):

**Phase Definitions**:
- **Lift**: Downward motion >1mm total (position decreasing)
- **Retract**: Upward motion (position increasing) 
- **Pause**: Stationary (position change <0.002mm for multiple readings)
- **Sandwich**: Small downward motion <1mm total
- **Exposure**: Currently labeled as Pause (future enhancement)

**Detection Logic**:
1. Track position changes between readings
2. Calculate total distance from motion start
3. Classify based on direction and magnitude:
   - Down + >1mm = Lift (adhesion test)
   - Down + <1mm = Sandwich
   - Up = Retract
   - Stationary = Pause

---

## Implementation Plan

### Part 1: Phase Event Queue (PositionLogger → PeakForceLogger)

**Modify PositionLogger.__init__()** to add phase event queue:
```python
def __init__(self, axis, force_data_queue_ref, ...):
    # ... existing code ...
    
    # Phase event queue for real-time notification
    self.phase_event_queue = queue.Queue(maxsize=100)
    self._last_emitted_phase = None  # Track to avoid duplicate events
```

**Modify PositionLogger._determine_phase()** to emit phase transitions:
```python
def _determine_phase(self, current_position):
    # ... existing phase detection logic ...
    
    # Emit phase change event if phase has changed
    if self._current_phase != self._last_emitted_phase:
        try:
            event = {
                'phase': self._current_phase,
                'timestamp': time.time(),  # Absolute timestamp
                'position': current_position,
                'data_index': len(self._data_buffer)  # Index in position logger's buffer
            }
            self.phase_event_queue.put_nowait(event)
            self._last_emitted_phase = self._current_phase
            print(f"PositionLogger: Phase transition → {self._current_phase} at {current_position:.3f}mm")
        except queue.Full:
            print("PositionLogger: Phase event queue full - skipping event")
    
    return self._current_phase
```

**Benefits**:
- Minimal overhead (only emits on phase changes, not every reading)
- Non-blocking (put_nowait)
- Small queue (100 events = ~50 layers worst case)
- Already has timestamp and position for correlation

---

### Part 2: PeakForceLogger Receives Phase Events

**Modify PeakForceLogger.__init__()** to accept phase queue:
```python
def __init__(self, output_csv_filepath, phase_event_queue_ref=None, ...):
    # ... existing code ...
    
    # Phase event tracking
    self.phase_event_queue_ref = phase_event_queue_ref
    self._current_lifting_start_idx = None  # Data buffer index where lifting started
    self._current_lifting_start_time = None  # Timestamp when lifting started
```

**Add method to consume phase events**:
```python
def _update_phase_info(self):
    """Check for phase events and update lifting start marker."""
    if self.phase_event_queue_ref is None:
        return
    
    # Process all pending phase events
    while not self.phase_event_queue_ref.empty():
        try:
            event = self.phase_event_queue_ref.get_nowait()
            
            # If we just started lifting, mark the data buffer index
            if event['phase'] == 'Lift':
                # Calculate corresponding index in our data buffer
                # (Rough estimate based on timestamps)
                self._current_lifting_start_time = event['timestamp']
                
                # Find closest data point in our buffer
                with self._lock:
                    for idx, (ts, pos, force) in enumerate(self._data_buffer):
                        if abs(ts - event['timestamp']) < 0.05:  # Within 50ms
                            self._current_lifting_start_idx = idx
                            print(f"PFL: Lifting started at buffer idx {idx}, time {ts:.3f}s")
                            break
                            
        except queue.Empty:
            break
```

**Call in add_data_point()**:
```python
def add_data_point(self, timestamp, position, force):
    if not self._monitoring:
        return
    
    # Update phase information from queue
    self._update_phase_info()
    
    with self._lock:
        self._data_buffer.append((timestamp, position, force))
        # ... rest of method ...
```

---

### Part 3: Phase-Aware Pre-Initiation Detection

**Modify AdhesionMetricsCalculator._find_pre_initiation()**:
```python
def _find_pre_initiation(self, smoothed_force, peak_idx, baseline, 
                        lifting_start_idx=None):
    """
    Find pre-initiation point where force first rises above baseline before peak.
    
    Args:
        smoothed_force: Smoothed force data
        peak_idx: Index of peak force
        baseline: Baseline force value
        lifting_start_idx: Optional index where lifting phase started
                          (prevents searching before this point)
    
    Returns:
        int: Index of pre-initiation point (or None if not found)
    """
    # Search backward from peak
    search_start = max(0, peak_idx - 300)  # Don't search more than 300 points back
    
    # If lifting start is provided, don't search before it
    if lifting_start_idx is not None:
        search_start = max(search_start, lifting_start_idx)
        print(f"Pre-initiation search limited to indices {search_start}-{peak_idx} (lifting started at {lifting_start_idx})")
    
    # Look backward from peak to find where force first exceeded baseline
    baseline_threshold = baseline + 0.01  # Small margin above baseline
    
    for i in range(peak_idx, search_start, -1):
        if smoothed_force[i] < baseline_threshold:
            # Found where force drops below baseline
            # Pre-initiation is the point just after this
            if i + 1 <= peak_idx:
                return i + 1
    
    # If no crossing found, use search_start as fallback
    print(f"WARNING: No baseline crossing found in search range, using start of search")
    return search_start
```

**Update PeakForceLogger to pass lifting_start_idx**:
```python
def stop_monitoring_and_log_peak(self):
    """Stop monitoring and analyze the collected data."""
    with self._lock:
        if not self._monitoring:
            return
        self._monitoring = False
        
        # Copy data for analysis
        data_copy = list(self._data_buffer)
        lifting_start_idx = self._current_lifting_start_idx
    
    # Submit to analysis thread with phase info
    if len(data_copy) >= 100:
        self._analysis_queue.put({
            'layer': self.current_layer_number,
            'data': data_copy,
            'z_peel': self.z_peel_peak_mm,
            'z_return': self.z_return_pos_mm,
            'lifting_start_idx': lifting_start_idx  # NEW
        })
```

**Update analysis worker to use lifting_start_idx**:
```python
def _analysis_worker(self):
    """Background thread that processes layer data."""
    while True:
        task = self._analysis_queue.get()
        
        # ... existing segmentation code ...
        
        # Calculate metrics with phase awareness
        metrics = self.calculator.calculate_metrics(
            time_data, 
            position_data, 
            force_data,
            lifting_start_idx=task.get('lifting_start_idx')  # Pass to calculator
        )
```

**Update AdhesionMetricsCalculator.calculate_metrics()**:
```python
def calculate_metrics(self, time_data, position_data, force_data, 
                     lifting_start_idx=None):
    """
    Calculate adhesion metrics with optional phase awareness.
    
    Args:
        time_data: Time array
        position_data: Position array
        force_data: Force array
        lifting_start_idx: Optional index where lifting phase started
    """
    # ... existing filtering and peak detection ...
    
    # Find pre-initiation with phase boundary awareness
    pre_init_idx = self._find_pre_initiation(
        smoothed_force, 
        peak_idx, 
        baseline,
        lifting_start_idx=lifting_start_idx  # NEW
    )
```

---

### Part 4: Adaptive Boundary Detection (Post-Processing)

**Two approaches for RawData_Processor:**

#### Approach A: Use Phase Column (Preferred)
**Advantages**: Most accurate, uses explicit phase markers  
**Requirements**: CSV must have 'Phase' column

```python
def detect_layer_boundaries_from_phases(self, time_data, position_data, force_data, phase_data):
    """
    Detect layer boundaries using explicit phase markers from CSV.
    
    Args:
        time_data, position_data, force_data: Sensor data arrays
        phase_data: Array of phase strings ('Lift', 'Retract', 'Pause', etc.)
    
    Returns:
        List of boundary dictionaries
    """
    print("\n=== Detecting Boundaries from Phase Markers ===")
    
    boundaries = []
    i = 0
    
    while i < len(phase_data):
        # Look for start of Lift phase
        if phase_data[i] == 'Lift':
            lift_start = i
            
            # Find end of Lift phase
            lift_end = lift_start
            while lift_end < len(phase_data) and phase_data[lift_end] == 'Lift':
                lift_end += 1
            
            # Look for subsequent Retract phase
            retract_start = lift_end
            while retract_start < len(phase_data) and phase_data[retract_start] != 'Retract':
                retract_start += 1
            
            if retract_start < len(phase_data):
                # Find end of Retract phase
                retract_end = retract_start
                while retract_end < len(phase_data) and phase_data[retract_end] == 'Retract':
                    retract_end += 1
                
                # Found complete layer
                boundary_dict = {
                    'lifting': (lift_start, lift_end),
                    'retraction': (retract_start, retract_end),
                    'sandwich': (lift_start, lift_start),  # No separate sandwich in this method
                    'full': (lift_start, retract_end)
                }
                boundaries.append(boundary_dict)
                
                print(f"Layer {len(boundaries)}: Lift[{lift_start}-{lift_end}], Retract[{retract_start}-{retract_end}]")
                i = retract_end
            else:
                # Incomplete layer
                print(f"WARNING: Lift phase at {lift_start} has no matching Retract")
                break
        else:
            i += 1
    
    print(f"\n=== Total layers detected: {len(boundaries)} ===")
    return boundaries
```

#### Approach B: Adaptive Motion Detection (Fallback)
**Use when**: Phase column not available in CSV  
**Method**: Detect significant position changes (adaptive threshold)

```python
def detect_layer_boundaries_adaptive(self, time_data, position_data, force_data):
    """
    Detect layer boundaries adaptively based on significant position changes.
    Does not rely on hardcoded distance values.
    
    Args:
        time_data, position_data, force_data: Sensor data arrays
    
    Returns:
        List of boundary dictionaries
    """
    print("\n=== Adaptive Boundary Detection ===")
    
    # Calculate all position changes
    position_diff = np.diff(position_data)
    cumulative_motion = np.cumsum(np.abs(position_diff))
    
    # Find segments of continuous motion
    motion_threshold = 0.01  # mm/sample (adjust based on sampling rate)
    is_moving = np.abs(position_diff) > motion_threshold
    
    # Find motion segments (start and end of continuous motion)
    motion_starts = []
    motion_ends = []
    in_motion = False
    
    for i in range(len(is_moving)):
        if is_moving[i] and not in_motion:
            # Motion starts
            motion_starts.append(i)
            in_motion = True
        elif not is_moving[i] and in_motion:
            # Motion ends
            motion_ends.append(i)
            in_motion = False
    
    # Calculate distance for each motion segment
    motion_segments = []
    for start, end in zip(motion_starts, motion_ends):
        if end < len(position_data):
            distance = abs(position_data[end] - position_data[start])
            motion_segments.append((start, end, distance))
    
    # Find significant motions (>50% of maximum motion)
    if motion_segments:
        max_distance = max([dist for _, _, dist in motion_segments])
        significant_threshold = 0.5 * max_distance  # Adaptive threshold
        
        significant_motions = [
            seg for seg in motion_segments 
            if seg[2] >= significant_threshold
        ]
        
        print(f"Found {len(significant_motions)} significant motions (>{significant_threshold:.2f}mm)")
        
        # Pair consecutive motions as lift-retract cycles
        boundaries = []
        for i in range(0, len(significant_motions) - 1, 2):
            lift_motion = significant_motions[i]
            retract_motion = significant_motions[i + 1]
            
            boundary_dict = {
                'lifting': (lift_motion[0], lift_motion[1]),
                'retraction': (retract_motion[0], retract_motion[1]),
                'sandwich': (lift_motion[0], lift_motion[0]),
                'full': (lift_motion[0], retract_motion[1])
            }
            boundaries.append(boundary_dict)
        
        print(f"\n=== Total layers detected: {len(boundaries)} ===")
        return boundaries
    else:
        print("ERROR: No motion segments detected")
        return []
```

**Update process_layer_data() to use phase-aware detection**:
```python
def process_layer_data(self, csv_filepath):
    """Main processing function with automatic phase detection."""
    # Load CSV
    df = pd.read_csv(csv_filepath)
    
    time_data = df['Elapsed Time (s)'].values
    position_data = df['Position (mm)'].values
    force_data = df['Force (N)'].values
    
    # Check if Phase column exists
    if 'Phase' in df.columns:
        print("Using phase-aware boundary detection")
        phase_data = df['Phase'].values
        boundaries = self.detect_layer_boundaries_from_phases(
            time_data, position_data, force_data, phase_data
        )
    else:
        print("Phase column not found - using adaptive detection")
        boundaries = self.detect_layer_boundaries_adaptive(
            time_data, position_data, force_data
        )
    
    # ... rest of processing ...
```

---

## Integration Steps

### Step 1: Modify PositionLogger
- [ ] Add `phase_event_queue` attribute in `__init__()`
- [ ] Add `_last_emitted_phase` tracker
- [ ] Modify `_determine_phase()` to emit events on transitions
- [ ] Add `data_index` to event (track buffer position)

### Step 2: Modify PeakForceLogger
- [ ] Add `phase_event_queue_ref` parameter to `__init__()`
- [ ] Add `_current_lifting_start_idx` and `_current_lifting_start_time` attributes
- [ ] Create `_update_phase_info()` method to consume phase events
- [ ] Call `_update_phase_info()` in `add_data_point()`
- [ ] Pass `lifting_start_idx` to analysis queue
- [ ] Update `_analysis_worker()` to use `lifting_start_idx`

### Step 3: Modify AdhesionMetricsCalculator
- [ ] Add `lifting_start_idx` parameter to `calculate_metrics()`
- [ ] Update `_find_pre_initiation()` to accept and use `lifting_start_idx`
- [ ] Add bounds checking to prevent search before lifting started
- [ ] Add debug logging for phase-limited searches

### Step 4: Modify RawData_Processor
- [ ] Create `detect_layer_boundaries_from_phases()` method
- [ ] Create `detect_layer_boundaries_adaptive()` method as fallback
- [ ] Update `process_layer_data()` to check for Phase column
- [ ] Remove hardcoded `EXPECTED_LIFT_DISTANCE = 6.0`
- [ ] Use phase-aware or adaptive detection automatically

### Step 5: Update Prince_Segmented.py (Main Script)
- [ ] Pass `position_logger.phase_event_queue` to `PeakForceLogger.__init__()`
- [ ] Verify all connections are established

---

## Testing Plan

### Test 1: Phase Event Generation
**Goal**: Verify PositionLogger correctly emits phase events

```python
# In PositionLogger test:
logger = PositionLogger(...)
# Simulate motion sequence
logger._determine_phase(10.0)  # Start position
logger._determine_phase(9.0)   # Downward 1mm → should emit "Sandwich"
logger._determine_phase(8.0)   # Downward 2mm total → should emit "Lift"
logger._determine_phase(8.0)   # Stationary → should emit "Pause"
logger._determine_phase(9.0)   # Upward → should emit "Retract"

# Check queue
while not logger.phase_event_queue.empty():
    event = logger.phase_event_queue.get()
    print(f"Event: {event['phase']} at {event['position']:.2f}mm")
```

**Expected Output**:
```
Event: Sandwich at 9.00mm
Event: Lift at 8.00mm
Event: Pause at 8.00mm
Event: Retract at 9.00mm
```

### Test 2: Phase-Aware Pre-Initiation
**Goal**: Verify pre-initiation doesn't search before lifting_start_idx

```python
# Create synthetic data with sandwich pre-force
force = np.concatenate([
    np.ones(100) * 0.5,    # Sandwich phase (pre-existing force)
    np.ones(50) * 0.0,     # Pause/Exposure (baseline)
    np.linspace(0, 2, 200) # Lift phase (rising to peak)
])

# Test WITHOUT phase awareness (old behavior)
pre_init_old = calculator._find_pre_initiation(force, peak_idx=349, baseline=0.0)
print(f"Old method: Pre-initiation at idx {pre_init_old}")  # Should be ~150 (wrong!)

# Test WITH phase awareness (new behavior)
lifting_start_idx = 150  # Lifting actually starts at idx 150
pre_init_new = calculator._find_pre_initiation(force, peak_idx=349, baseline=0.0, 
                                               lifting_start_idx=lifting_start_idx)
print(f"New method: Pre-initiation at idx {pre_init_new}")  # Should be ~150 (correct!)
```

### Test 3: Adaptive Boundary Detection
**Goal**: Verify detection works for various overstep distances

```python
# Test with 6mm overstep (current)
processor.EXPECTED_LIFT_DISTANCE = None  # Disable hardcoded value
boundaries = processor.detect_layer_boundaries_adaptive(time, position, force)

# Test with 0mm overstep
# (Modify test data to have 0mm motions)

# Test with 10mm overstep
# (Modify test data to have 10mm motions)
```

### Test 4: Phase-Based Boundary Detection
**Goal**: Verify phase column correctly identifies layers

```python
# Create test CSV with Phase column
df = pd.DataFrame({
    'Elapsed Time (s)': time_data,
    'Position (mm)': position_data,
    'Force (N)': force_data,
    'Phase': ['Pause', 'Pause', 'Lift', 'Lift', ..., 'Retract', 'Retract', 'Pause']
})

boundaries = processor.detect_layer_boundaries_from_phases(
    df['Elapsed Time (s)'].values,
    df['Position (mm)'].values,
    df['Force (N)'].values,
    df['Phase'].values
)

# Verify boundaries match phase transitions
```

---

## Benefits

### Real-Time Metrics Without Raw Data
- Phase events are lightweight (4 values per transition)
- Only need to store phase event queue (100 events = ~3KB)
- PeakForceLogger calculates metrics during printing
- No need to save all raw position/force data

### Accurate Pre-Initiation Detection
- Searches only within Lift phase
- Ignores Sandwich/Pause/Exposure pre-existing forces
- More physically meaningful results

### Adaptive to Print Parameters
- No hardcoded distances
- Works with any overstep value (0mm to any value)
- Automatically adjusts to different print configurations

### Backward Compatible
- If no phase queue provided, falls back to current behavior
- Old CSV files without Phase column use adaptive detection
- No breaking changes to existing code

---

## Performance Considerations

### Queue Size
- 100 events max
- ~4-5 phase transitions per layer
- Supports ~20 layers buffered
- Non-blocking put_nowait prevents deadlock

### Processing Overhead
- Phase detection: Already running (no new cost)
- Queue operations: O(1) amortized
- Phase update in PeakForceLogger: O(n) where n = pending events (~4-5)
- Total overhead: <1ms per data point

### Memory Usage
- Phase event: ~200 bytes (dict with 4 keys)
- Queue: 100 events × 200 bytes = 20KB
- Negligible compared to data buffers

---

## Future Enhancements

### Exposure Phase Detection
Currently Exposure is labeled as Pause. Future improvement:
```python
# Track time since last motion
if self._current_phase == "Pause":
    pause_duration = time.time() - self._motion_stopped_time
    if pause_duration > EXPOSURE_DURATION_THRESHOLD:
        self._current_phase = "Exposure"
```

### Phase Statistics
Add to PeakForceLogger output:
- Actual lift distance from Phase markers
- Actual retract distance
- Pause duration before lifting
- Sandwich duration and magnitude

### Instruction File Integration
Read overstep distance from instruction file:
```python
def load_expected_distances(self, instruction_file):
    """Parse instruction file for lift/retract distances."""
    # Read overstep_distance_mm from instruction
    # Use for validation, not hardcoded detection
```

---

## Files to Modify

1. **support_modules/PositionLogger.py**
   - Add phase event queue
   - Emit events on phase transitions

2. **support_modules/PeakForceLogger.py**
   - Accept phase queue reference
   - Consume phase events
   - Track lifting_start_idx
   - Pass to adhesion calculator

3. **support_modules/adhesion_metrics_calculator.py**
   - Add lifting_start_idx parameter
   - Limit pre-initiation search to phase boundary

4. **post-processing/RawData_Processor.py**
   - Add phase-aware boundary detection
   - Add adaptive boundary detection
   - Remove hardcoded EXPECTED_LIFT_DISTANCE

5. **Prince_Segmented.py** (main script)
   - Connect phase queue: `position_logger.phase_event_queue` → PeakForceLogger
   - No other changes needed

---

## Summary

This design provides:
✅ **Phase-aware pre-initiation** - respects Lift phase boundaries  
✅ **Adaptive boundary detection** - works with any overstep distance  
✅ **Real-time metrics** - no raw data saving required  
✅ **Backward compatible** - falls back to current behavior if no phase info  
✅ **Minimal overhead** - lightweight queue, non-blocking operations  
✅ **Tested approach** - phase detection already working, just needs connection  

Next step: Implement modifications in order (PositionLogger → PeakForceLogger → Calculator → Processor)
