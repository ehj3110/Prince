# Force Gauge Migration Guide

**Date**: October 31, 2025  
**Migration**: Single Load Cell → Triple Load Cell System

---

## Overview

This document explains how the force gauge system was migrated from a **single load cell** to a **triple load cell parallel configuration** while maintaining backward compatibility.

---

## Hardware Change

### Original Setup (Single Cell)
- **Hardware**: 1 load cell on Phidget Bridge Port 0
- **Range**: Higher force ceiling, lower resolution
- **Calibration**: Two-point (tare + known force) for one channel

### New Setup (Triple Cell)
- **Hardware**: 3 load cells on Phidget Bridge Ports 0, 1, 2
- **Range**: Same total force ceiling (distributed), higher resolution per cell
- **Calibration**: Two-point simultaneous (tare all 3 + apply force to all 3)
- **Output**: Sum of all three cells

---

## Software Architecture: "Drop-in Replacement"

### Design Philosophy
The triple cell system was integrated as a **transparent upgrade**:
- ✅ **Zero changes** to any code outside `ForceGaugeManager.py`
- ✅ **Same interface** - all methods return same data types
- ✅ **Backward compatible** - existing code works unchanged
- ✅ **Internal detail** - rest of system doesn't know about 3 channels

### Key Principle
```
External View (Rest of System):
    ForceGaugeManager.get_latest_calibrated_force() → Returns ONE force value
    
Internal Reality (Inside ForceGaugeManager):
    3 channels → 3 voltages → 3 forces → Sum → Return total
```

---

## File Changes Summary

### Files Modified
1. **`ForceGaugeManager.py`** - Modified to handle 3 channels internally
   - Backup: `ForceGaugeManager_SingleCell_Backup.py`

### Files Unchanged
- ✅ `SensorDataWindow.py` - GUI unchanged
- ✅ `Prince_Segmented.py` - Main printing logic unchanged
- ✅ `AutomatedLayerLogger.py` - Logging unchanged
- ✅ `PeakForceLogger.py` - Peak force logging unchanged
- ✅ All pre-calibration routines - Unchanged

---

## Reverting to Single Cell

### Option A: Quick Revert (Use Backup)
If you need to go back to single cell operation:

1. **Restore the backup**:
   ```powershell
   cd "c:\Users\cheng sun\BoyuanSun\Prince_CurrentWorkingVersion\support_modules"
   cp ForceGaugeManager_SingleCell_Backup.py ForceGaugeManager.py
   ```

2. **Reconnect single load cell** to Port 0

3. **Done** - System works as before

### Option B: Configuration Flag (Future Enhancement)
Could add a mode selection:
```python
class ForceGaugeManager:
    def __init__(self, ..., mode="triple"):  # or "single"
        if mode == "single":
            # Initialize 1 channel
        else:
            # Initialize 3 channels
```

---

## Single Cell Implementation (Original)

### Key Components (Backed up in `ForceGaugeManager_SingleCell_Backup.py`)

#### 1. Initialization
```python
class ForceGaugeManager:
    def __init__(self, gain_label, offset_label, ...):
        self.GAIN = None  # Single gain value
        self.OFFSET = None  # Single offset value
        self.voltage_ratio_input = None  # Single Phidget channel
        self.latest_calibrated_force = 0.0
```

#### 2. Channel Setup
```python
def initialize_phidget_background(self):
    ch = VoltageRatioInput()
    ch.setChannel(0)  # Port 0 only
    ch.setBridgeGain(BridgeGain.BRIDGE_GAIN_128)
    ch.setDataInterval(8)
    ch.setOnVoltageRatioChangeHandler(self.on_voltage_ratio_change)
    self.voltage_ratio_input = ch
```

#### 3. Calibration (Single Cell)
```python
def calibrate_force_gauge(self):
    # Step 1: Tare (zero force)
    zero_voltage = self.voltage_ratio_input.getVoltageRatio()
    self.OFFSET = zero_voltage
    
    # Step 2: Apply known force
    known_force = float(input("Enter force (N): "))
    loaded_voltage = self.voltage_ratio_input.getVoltageRatio()
    
    # Step 3: Calculate gain
    self.GAIN = known_force / (loaded_voltage - self.OFFSET)
```

#### 4. Force Calculation (Single Cell)
```python
def on_voltage_ratio_change(self, sender, voltage_ratio):
    if self.GAIN and self.OFFSET:
        # Force = Gain × (Voltage - Offset)
        force = self.GAIN * (voltage_ratio - self.OFFSET)
        self.latest_calibrated_force = force
```

#### 5. Public Interface
```python
def get_latest_calibrated_force(self):
    """Returns single force reading."""
    return self.latest_calibrated_force
```

---

## Triple Cell Implementation (Current)

### Key Components (Current `ForceGaugeManager.py`)

#### 1. Initialization (Multi-Channel)
```python
class ForceGaugeManager:
    def __init__(self, gain_label, offset_label, ...):
        # Internal: 3 channels
        self.GAINS = [None, None, None]
        self.OFFSETS = [None, None, None]
        self.voltage_ratio_inputs = [None, None, None]
        self.latest_voltages = [0.0, 0.0, 0.0]
        self.latest_forces = [0.0, 0.0, 0.0]
        self.channel_ports = [0, 1, 2]
        
        # Public: Single values (for GUI compatibility)
        self.GAIN = None  # Average gain for display
        self.OFFSET = None  # Average offset for display
        self.latest_calibrated_force = 0.0  # Sum of all 3
```

#### 2. Channel Setup (3 Channels)
```python
def initialize_phidget_background(self):
    for i, port in enumerate([0, 1, 2]):
        ch = VoltageRatioInput()
        ch.setChannel(port)
        ch.setBridgeGain(BridgeGain.BRIDGE_GAIN_128)
        ch.setDataInterval(8)
        ch.setOnVoltageRatioChangeHandler(
            lambda sender, v, i=i: self.on_voltage_ratio_change(sender, v, i))
        self.voltage_ratio_inputs[i] = ch
```

#### 3. Calibration (Simultaneous 3-Cell)
```python
def calibrate_force_gauge(self):
    # Step 1: Tare all 3 channels
    for i in range(3):
        zero_v = self.voltage_ratio_inputs[i].getVoltageRatio()
        self.OFFSETS[i] = zero_v
    
    # Step 2: Apply total force to all 3
    total_force = float(input("Enter TOTAL force (N): "))
    
    loaded_voltages = []
    voltage_changes = []
    for i in range(3):
        loaded_v = self.voltage_ratio_inputs[i].getVoltageRatio()
        loaded_voltages.append(loaded_v)
        voltage_changes.append(loaded_v - self.OFFSETS[i])
    
    # Step 3: Calculate each cell's share
    total_v_change = sum(abs(v) for v in voltage_changes)
    
    for i in range(3):
        force_fraction = abs(voltage_changes[i]) / total_v_change
        cell_force = total_force * force_fraction
        self.GAINS[i] = cell_force / abs(voltage_changes[i])
        if voltage_changes[i] < 0:
            self.GAINS[i] = -self.GAINS[i]  # Negative for compression
    
    # Step 4: Set public values for GUI
    self.GAIN = sum(abs(g) for g in self.GAINS) / 3  # Average magnitude
    self.OFFSET = sum(self.OFFSETS) / 3  # Average offset
```

#### 4. Force Calculation (Sum of 3)
```python
def on_voltage_ratio_change(self, sender, voltage_ratio, channel_index):
    self.latest_voltages[channel_index] = voltage_ratio
    
    if self.GAINS[channel_index] and self.OFFSETS[channel_index]:
        # Force = Gain × (Voltage - Offset) for each cell
        force = self.GAINS[channel_index] * (
            voltage_ratio - self.OFFSETS[channel_index])
        self.latest_forces[channel_index] = force
    
    # Update total (public interface)
    if all(g is not None for g in self.GAINS):
        self.latest_calibrated_force = sum(self.latest_forces)
```

#### 5. Public Interface (Unchanged)
```python
def get_latest_calibrated_force(self):
    """Returns total force (sum of 3 cells)."""
    return self.latest_calibrated_force
```

---

## Differences Summary

| Aspect | Single Cell | Triple Cell |
|--------|-------------|-------------|
| **Channels** | 1 (Port 0) | 3 (Ports 0, 1, 2) |
| **GAIN** | Single float | List of 3 floats (internal) |
| **OFFSET** | Single float | List of 3 floats (internal) |
| **Calibration** | Apply force once | Apply force once (to all 3) |
| **Force Calc** | `Gain × (V - Offset)` | Sum of 3: `Σ(Gain[i] × (V[i] - Offset[i]))` |
| **Public Output** | Direct force | Sum of 3 forces |
| **GUI Display** | Actual gain/offset | Average gain/offset |
| **External Code** | No changes needed | No changes needed |

---

## Calibration File Format

### Single Cell Format
```
# force_gauge_calibration_YYYY-MM-DD_HHMMSS.txt
GAIN: 10118.0739
OFFSET: -0.00000914
```

### Triple Cell Format (New)
```
# force_gauge_calibration_YYYY-MM-DD_HHMMSS.txt
MODE: TRIPLE
GAIN_CH0: -9847.2341
OFFSET_CH0: -0.00012345
GAIN_CH1: -10234.5678
OFFSET_CH1: 0.00034567
GAIN_CH2: -10012.8901
OFFSET_CH2: -0.00008901
# For GUI compatibility:
GAIN_AVG: 10031.5640
OFFSET_AVG: 0.00004574
```

---

## Testing & Validation

### Single Cell Test Checklist
- [ ] Initialize sensor on Port 0
- [ ] Run calibration with tare + known force
- [ ] Verify force reading matches applied force
- [ ] Check GUI shows gain and offset
- [ ] Test force monitoring during print
- [ ] Verify data logging works

### Triple Cell Test Checklist
- [ ] Initialize all 3 sensors on Ports 0, 1, 2
- [ ] Run simultaneous calibration
- [ ] Verify total force = applied force
- [ ] Check force distribution ~33% each
- [ ] Test force monitoring during print
- [ ] Verify data logging works (sums correctly)

---

## Troubleshooting

### Reverting to Single Cell

**Symptoms indicating need to revert:**
- Only have 1 load cell available
- Triple cell setup not working properly
- Need simpler system for debugging

**Steps:**
1. Stop the Prince system
2. Restore backup: `cp ForceGaugeManager_SingleCell_Backup.py ForceGaugeManager.py`
3. Connect single load cell to Port 0
4. Restart Prince
5. Calibrate as normal

### Common Issues

**Triple cell shows wrong total:**
- Check all 3 cells are connected (Ports 0, 1, 2)
- Verify calibration was done with all 3 loaded
- Check individual voltages in test script

**Single cell not working after revert:**
- Ensure backup file was restored correctly
- Check load cell connected to Port 0
- Re-run calibration

---

## Future Enhancements

### Possible Improvements
1. **Mode selection** - Add single/triple flag in config
2. **Save individual channels** - Store all 3 calibrations for diagnostics
3. **Alignment check** - Warn if force distribution is very uneven (>40/30/30)
4. **Hot swap** - Switch between single/triple without restarting

### Backwards Compatibility Commitment
Any future changes will maintain the **drop-in replacement** philosophy:
- External interface unchanged
- `get_latest_calibrated_force()` always returns ONE value
- No changes to calling code required

---

## References

- **Test Script**: `test_triple_force_gauge.py` - For testing triple cell system
- **Backup File**: `support_modules/ForceGaugeManager_SingleCell_Backup.py`
- **Current File**: `support_modules/ForceGaugeManager.py` (triple cell)
- **Documentation**: `TRIPLE_FORCE_GAUGE_GUIDE.md` - User guide for triple cell

---

**Last Updated**: October 31, 2025  
**Author**: Cheng Sun Lab Team
