# Quick Calibration Guide - Triple Load Cell System

## 🚀 Quick Start (First Time)

1. **Start Program** → Three channels initialize automatically
2. **Click "Calibrate Force Gauge"**
3. **Follow 3-step wizard:**
   - Step 1: Remove all force → OK
   - Step 2: Enter total force (e.g., 1.5)
   - Step 3: Apply force to all cells → OK
4. **Save when prompted** → Choose location
5. **Done!** Check console for individual channel values

## 🔄 Quick Start (Subsequent Uses)

1. **Start Program**
2. **Click "Quick Calibrate"**
3. **Done!** Most recent calibration loaded

## 📋 Calibration Procedure Details

### Step 1: Tare (Zero Force)
```
❌ Remove all weights from load cells
❌ Ensure nothing is touching the platform
✅ Click OK when ready
```

**What happens:**
- System reads voltage from all 3 channels
- Stores as baseline (OFFSET values)
- Console shows: `Channel X OFFSET: -0.0000XXXXX`

### Step 2: Enter Known Force
```
Enter the TOTAL force: [____] N
```

**Examples:**
- Using 100g weight: Enter `0.981` (100g × 9.81 m/s²)
- Using 150g weight: Enter `1.472`
- Using 1.5N spring scale: Enter `1.5`

### Step 3: Apply Force
```
✅ Place known weight on platform (all three cells)
✅ Wait for system to stabilize (~0.5s)
✅ Click OK when ready
```

**What happens:**
- System reads loaded voltages from all 3 channels
- Calculates voltage changes per channel
- Distributes total force proportionally
- Calculates individual gains
- Handles compression automatically

## 📊 Console Output Explained

### During Initialization
```
=== TRIPLE LOAD CELL MODE ===

--- Initializing Channel 0 ---
Channel 0 connected successfully!

--- Initializing Channel 1 ---
Channel 1 connected successfully!

--- Initializing Channel 2 ---
Channel 2 connected successfully!

=== ALL THREE CHANNELS CONNECTED ===
```

### During Calibration
```
Channel 0 OFFSET (tare): -0.00001234
Channel 1 OFFSET (tare): -0.00000987
Channel 2 OFFSET (tare): -0.00001111

Channel 0 loaded voltage: -0.00001534, change: -0.00000300
Channel 1 loaded voltage: -0.00001287, change: -0.00000300
Channel 2 loaded voltage: -0.00001411, change: -0.00000300

Channel 0 calibration: Force=0.5000N (33.3%), GAIN=3456.7890
Channel 1 calibration: Force=0.5000N (33.3%), GAIN=3501.2345
Channel 2 calibration: Force=0.5000N (33.4%), GAIN=3478.5678
```

**What to look for:**
- ✅ **Balanced distribution:** ~33% each channel (good alignment)
- ⚠️ **Unbalanced:** One >50% (check platform alignment)
- ❌ **One near 0%:** Check that cell's connection

### After Calibration
```
=== CALIBRATION COMPLETE ===
Individual Channel Gains:
  Channel 0: GAIN = 3456.7890, OFFSET = -0.00001234
  Channel 1: GAIN = 3501.2345, OFFSET = -0.00000987
  Channel 2: GAIN = 3478.5678, OFFSET = -0.00001111

Total force readout enabled. Smart update trigger: 0.001 N
```

## 💾 Save/Load Operations

### Saving Calibration

**When:**
- After successful calibration
- When prompted: "Save these values to a file?"

**File Created:**
```
force_gauge_calibration_20251031_143522.txt
```

**Contents:**
```
# Force Gauge Calibration File
# Created: 2025-10-31 14:35:22
# Mode: TRIPLE CELL
MODE=TRIPLE
GAIN_0=3456.78901234
OFFSET_0=-0.00001234
GAIN_1=3501.23456789
OFFSET_1=-0.00000987
GAIN_2=3478.56789012
OFFSET_2=-0.00001111
```

### Loading Calibration

**Quick Calibrate:**
- Automatically finds most recent `.txt` file
- No file selection needed
- Shows which file was loaded

**Load Calibration:**
- Manual file selection
- Choose specific calibration
- Useful for switching between setups

### Managing Calibration Files

**Recommended Organization:**
```
📁 Prince_CurrentWorkingVersion/
  📁 calibrations/
    📄 calibration_aligned_1.5N.txt
    📄 calibration_production_setup.txt
    📄 calibration_test_weights.txt
  📄 force_gauge_calibration_YYYYMMDD_HHMMSS.txt (latest)
```

**Best Practices:**
1. Save calibration after each successful setup
2. Name files descriptively for easy identification
3. Keep multiple calibrations for different scenarios
4. Backup known-good calibrations

## ⚠️ Troubleshooting

### "Channel X not attached"
**Problem:** Hardware not detected  
**Solution:**
1. Check USB cable connection
2. Open Phidget Control Panel → verify channels 0,1,2 visible
3. Restart application
4. Check Device Manager (Windows)

### Force Distribution Unbalanced
**Problem:** One channel reads >50% of force  
**Symptoms:**
```
Channel 0 calibration: Force=0.8N (53.3%)  ⚠️
Channel 1 calibration: Force=0.4N (26.7%)
Channel 2 calibration: Force=0.3N (20.0%)
```

**Solutions:**
1. Check platform is level
2. Verify weight placement is centered
3. Check for mechanical binding
4. Inspect load cell mounting

### Negative Force Readings
**Problem:** Force shows negative when loaded  
**Note:** This is handled automatically if detected during calibration  
**If still occurring:**
1. Re-calibrate (system will auto-detect compression)
2. Check console for negative GAIN values (normal for compression)
3. Verify weight is being applied (not removed)

### "No saved calibration files found"
**Problem:** Quick Calibrate can't find files  
**Solution:**
1. Perform full calibration first
2. Save when prompted
3. Or use "Load Calibration" to browse to file

### "Mode mismatch"
**Problem:** Trying to load wrong mode's calibration  
**Example:** Loading SINGLE file in TRIPLE mode  
**Solution:**
- Check file header: `MODE=TRIPLE` or `MODE=SINGLE`
- Create new calibration for current mode
- Or change `USE_TRIPLE_CELL` flag in code (advanced)

## 🔍 Verification Procedure

### After Calibration - Quick Check

1. **Apply known weight** (e.g., 150g = 1.472N)
2. **Check GUI readout:** Should show ~1.47N
3. **Check console:** Individual forces should sum to ~1.47N
4. **Remove weight:** Should return to ~0.00N

### Health Check - Force Distribution

**Apply weight and check console:**
```
Channel 0: 0.49N (33.1%) ✅ Good
Channel 1: 0.50N (33.8%) ✅ Good
Channel 2: 0.49N (33.1%) ✅ Good
Total: 1.48N
```

**Warning signs:**
```
Channel 0: 0.10N (6.8%) ⚠️ Check connection
Channel 1: 0.80N (54.1%) ⚠️ Alignment issue
Channel 2: 0.58N (39.1%) ⚠️ Platform tilted
Total: 1.48N
```

## 📞 Quick Reference

| Action | Method | When |
|--------|--------|------|
| First calibration | "Calibrate Force Gauge" button | Initial setup |
| Daily startup | "Quick Calibrate" button | Each session |
| Specific setup | "Load Calibration" + file browse | Switch configurations |
| Save current | Automatic prompt after calibration | After successful cal |
| Check values | Look at console output | Anytime |
| Verify accuracy | Apply known weight | After calibration |

## 💡 Tips & Best Practices

### For Accurate Calibration

1. **Use known weights, not estimates**
   - Certified calibration weights preferred
   - Or verify on accurate scale first

2. **Allow settling time**
   - Wait 0.5-1 second after placing weight
   - System automatically waits, but be patient

3. **Calibrate in operating environment**
   - Same temperature as printing
   - Same platform configuration
   - Same mechanical setup

4. **Regular re-calibration**
   - Weekly for production use
   - After any mechanical changes
   - If readings seem off

### For Best Results

1. **Center the weight**
   - Place directly over center of platform
   - Use all three cells equally

2. **Keep it clean**
   - Remove debris from load cells
   - Keep surfaces clean and dry

3. **Document your calibrations**
   - Note weight used
   - Note date and conditions
   - Save with descriptive filename

4. **Validate periodically**
   - Keep test weight handy
   - Quick check before important prints
   - Compare to known good calibration

---

## 🎯 One-Page Cheat Sheet

```
┌─────────────────────────────────────────────────────────────┐
│         TRIPLE LOAD CELL - QUICK REFERENCE                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  FIRST TIME CALIBRATION:                                    │
│  1. Click "Calibrate Force Gauge"                           │
│  2. Remove force → OK                                       │
│  3. Enter total force → OK                                  │
│  4. Apply force → OK                                        │
│  5. Save when prompted                                      │
│                                                             │
│  DAILY USE:                                                 │
│  1. Click "Quick Calibrate"                                 │
│  2. Done!                                                   │
│                                                             │
│  CONSOLE OUTPUT:                                            │
│  ✅ Good: Each channel ~33% of total                        │
│  ⚠️ Check: One channel >50% or <10%                         │
│                                                             │
│  FILES:                                                     │
│  📄 force_gauge_calibration_YYYYMMDD_HHMMSS.txt             │
│  📁 Save to: calibrations/ folder                           │
│                                                             │
│  TROUBLESHOOTING:                                           │
│  ❌ Channel not attached → Check USB                        │
│  ❌ Unbalanced forces → Check alignment                     │
│  ❌ Negative readings → Re-calibrate (auto-fixed)           │
│  ❌ No saved files → Do full calibration first              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

**Need Help?** Check console output first - it shows what's happening!
