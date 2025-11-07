# Git Merge Strategy - November 6, 2025

## Situation Summary

**Local Branch (Today's Work):**
- Decimation implementation (1200Hz→100Hz with 3.46× noise reduction)
- Bridge gain optimization (BRIDGE_GAIN_1 → BRIDGE_GAIN_16)
- GUI bridge gain selector
- Quick calibrate restoration
- Logging rate fix (all 1200 samples/sec queued)
- 38 new test/documentation files

**Remote Branch (Other Computer):**
- Adhesion metrics improvements (propagation end, pre-initiation detection)
- Code cleanup (removed redundant files, consolidated archives)
- Documentation updates
- Bug fixes in PeakForceLogger.py and adhesion_metrics_calculator.py

**Files with Conflicts:**
1. `support_modules/ForceGaugeManager.py` - **HIGH PRIORITY**
2. `support_modules/SensorDataWindow.py` - **MEDIUM PRIORITY**
3. `support_modules/PeakForceLogger.py` - **LOW (remote only)**
4. `support_modules/adhesion_metrics_calculator.py` - **LOW (remote only)**
5. `Prince_Segmented.py` - **MEDIUM**
6. `support_modules/libs.py` - **MEDIUM**

---

## Conflict Analysis

### ForceGaugeManager.py

**Local Changes (Lines Modified):**
- Lines 25-53: Added USE_DECIMATION, decimation_factor, decimation_buffer, decimation_counter
- Line 53: `self.latest_averaged_voltage = None`
- Lines 517-534: Changed from USE_TRIPLE_CELL to single cell mode
- Line 530: Changed to `setBridgeGain(BridgeGain.BRIDGE_GAIN_16)` (was BRIDGE_GAIN_1)
- Line 574: Same bridge gain change for alternate path
- Lines 627-665: Modified `_onVoltageRatioChange` to queue ALL raw samples + maintain averaged voltage
- Line 1114: Restored `def quick_calibrate_force_gauge(self):`
- Lines 1318-1373: Added `set_bridge_gain()` method

**Remote Changes (From diff):**
- Line 26: Added `import math`
- Lines 29-50: Added triple cell support (USE_TRIPLE_CELL flag, arrays for GAINS/OFFSETS/etc.)
- Lines 53-55: Added decimation variables (SAME as local!)
- Lines 131-180: Modified `_data_processing_loop` for triple cell support
- Possibly other threading/queue improvements

**Good News:** Both local and remote added decimation! The variables are identical.

**Conflict Resolution:**
- **Keep local:** BRIDGE_GAIN_16 changes (lines 530, 574)
- **Keep local:** USE_TRIPLE_CELL = False (we're using single cell)
- **Keep local:** Decimation variables (already compatible)
- **Keep local:** set_bridge_gain() method (lines 1318-1373)
- **Keep local:** quick_calibrate_force_gauge() restoration (line 1114)
- **Keep local:** _onVoltageRatioChange decimation logic (lines 627-665)
- **Take remote:** import math (line 26) - harmless addition
- **Take remote:** Any other threading improvements that don't conflict

---

### SensorDataWindow.py

**Local Changes:**
- Lines 178-187: Bridge gain dropdown and Apply button
- Lines 1229-1274: `on_bridge_gain_change()` and `apply_bridge_gain()` callbacks

**Remote Changes:**
- Unknown (need to check diff)

**Conflict Resolution:**
- **Keep local:** All GUI bridge gain additions

---

### adhesion_metrics_calculator.py

**Local Changes:** NONE

**Remote Changes:**
- Removed `lifting_start_idx` parameter from methods
- Modified `_find_pre_initiation()` to search backwards from peak
- Fixed propagation end detection to use zero-crossing method

**Conflict Resolution:**
- **Take remote:** All adhesion metrics improvements (no local conflict)

---

### PeakForceLogger.py

**Local Changes:** NONE

**Remote Changes:**
- Unknown adhesion-related improvements

**Conflict Resolution:**
- **Take remote:** All changes (no local conflict)

---

## Merge Execution Plan

### Step 1: Stash Local Work
```powershell
git add -A
git stash save "Nov 6 2025: Decimation + Bridge Gain + Logging Fix"
```

### Step 2: Pull Remote Changes
```powershell
git pull origin main
```
Expected result: Fast-forward merge OR merge conflicts

### Step 3: Review Conflicts (if any)
```powershell
git status
git diff  # See conflict markers
```

### Step 4: Manual Conflict Resolution

If conflicts occur in ForceGaugeManager.py:

**Sections to preserve from LOCAL (stash):**
1. USE_DECIMATION = True + decimation configuration (lines 48-55)
2. BRIDGE_GAIN_16 in both locations (lines 530, 574)
3. Decimation logic in _onVoltageRatioChange (lines 627-665)
4. quick_calibrate_force_gauge() method (line 1114)
5. set_bridge_gain() method (lines 1318-1373)

**Sections to preserve from REMOTE:**
1. import math (if present)
2. Any other threading/queue improvements
3. Triple cell support code (but keep USE_TRIPLE_CELL = False)

### Step 5: Re-apply Stash (if needed)
```powershell
git stash pop
```
Then manually resolve conflicts using the strategy above.

### Step 6: Verify Integration
```powershell
# Test decimation
python test_decimation_integration.py

# Test adhesion metrics (if test file exists)
python test_adhesion_calculator.py
```

### Step 7: Commit Merged Changes
```powershell
git add -A
git commit -m "Integrate decimation/gain improvements with adhesion metrics fixes

Local changes (Nov 6):
- Decimation: 1200Hz input -> 100Hz output (3.46x noise reduction)
- Bridge gain: BRIDGE_GAIN_1 -> BRIDGE_GAIN_16 (16x resolution)
- GUI: Bridge gain selector dropdown
- Fixed: Logging rate (all 1200 samples/sec queued)
- Fixed: Restored quick_calibrate_force_gauge() method
- Added: set_bridge_gain() method
- Added: 38 test/documentation files

Remote changes (other computer):
- Adhesion: Fixed pre-initiation detection (removed lifting_start_idx)
- Adhesion: Fixed propagation end (zero-crossing method)
- Cleanup: Removed redundant files, consolidated archives
- Documentation: Multiple new guides and summaries

All changes tested and verified."
```

### Step 8: Push to Remote
```powershell
git push origin main
```

---

## Potential Issues & Solutions

### Issue 1: Merge Conflict in ForceGaugeManager.py
**Solution:** Manually edit the file:
1. Keep all decimation variables from EITHER local or remote (they're identical)
2. Keep BRIDGE_GAIN_16 from local
3. Keep USE_TRIPLE_CELL = False
4. Keep set_bridge_gain() method from local
5. Keep quick_calibrate_force_gauge() from local
6. Take any remote threading improvements that don't conflict

### Issue 2: New Files Not Tracked
**Solution:**
```powershell
git add *.md          # Add all new documentation
git add test_*.py     # Add all new test files
git add DECIMATION_*.md TRUE_10MS_*.md OVERSAMPLING_*.md
```

### Issue 3: Remote Has Deleted Files We Still Have
**Solution:**
```powershell
git status  # See what's deleted on remote
# If we agree with deletions:
git rm <file>
# If we want to keep:
git add <file>
```

---

## Testing Checklist

After merge, verify:

- [ ] **Decimation works:** Run `test_decimation_integration.py`
  - Expect: 1200Hz sampling, 100Hz output, 3.46× noise reduction
  
- [ ] **Bridge gain works:** Check SensorDataWindow GUI
  - Expect: Dropdown shows options, Apply button works
  
- [ ] **Force resolution improved:** Check force readout
  - Expect: ~0.075mN steps (was ~1.2mN)
  
- [ ] **Logging rate correct:** Check CSV output
  - Expect: Unique force values every ~0.83ms (1200Hz)
  
- [ ] **Quick calibrate works:** Test button in GUI
  - Expect: Loads most recent calibration file
  
- [ ] **Adhesion metrics work:** Run post-processing
  - Expect: Pre-initiation detection works without lifting_start_idx
  - Expect: Propagation end uses zero-crossing method
  
- [ ] **No errors:** Check console output
  - Expect: No Python errors or warnings

---

## Rollback Plan

If merge causes problems:

```powershell
# Abort merge (if in progress)
git merge --abort

# Reset to before merge
git reset --hard HEAD@{1}

# Restore stash
git stash pop
```

Then try alternative strategy: cherry-pick specific commits instead of full merge.

---

## Summary

**Priority:** Keep local decimation/gain improvements + add remote adhesion fixes

**Strategy:** Stash → Pull → Resolve conflicts → Test → Commit → Push

**Key Principle:** Both sets of improvements are valuable and should be preserved.

**Expected Outcome:** 
- High-speed decimation (today's work) ✅
- Improved resolution (today's work) ✅
- Accurate adhesion metrics (remote work) ✅
- Clean codebase (remote work) ✅

