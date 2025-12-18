# Quick Reference: What Changed and How to Test

## 🎯 What Was Fixed

### 1. **Stage Stalls / GUI Freezing** ✅ FIXED
- **Problem**: Background analysis thread never stopped, queues accumulated data
- **Solution**: Threads shut down and queues cleared when print ends
- **How to verify**: 
  - Print → Wait 10 minutes → Click "Clear Plot" → Should be instant (no freeze)
  - Print → Wait 10 minutes → Start new print → Should work without hesitation

### 2. **DLP Stuck After Errors** ✅ FIXED  
- **Problem**: DLP left in pattern mode when print stopped/errored
- **Solution**: All error paths now call `cleanup_dlp_safe_state()`
- **How to verify**:
  - Start print → Click Stop → DLP should show HDMI (not black screen)
  - Cause stage fault → DLP should reset automatically
  - Should NEVER need to power cycle DLP between prints

### 3. **Background Light in Stepped Mode** ✅ FIXED
- **Problem**: DLP emits light even with black image in video mode
- **Solution**: Power set to 0 after exposure, restored before next layer
- **How to verify**:
  - Run stepped print in dark room
  - After exposure, look for ANY light from DLP → Should be ZERO
  - Check status messages: "DLP power=0" and "DLP power restored to X"

## 📋 Status Messages to Watch For

### Normal Operation (Stepped Mode):
```
L48: DLP power=0 (background light off)
Stepped L48: Peeling up to 60.5999 mm
SUCCESS L48: Return movement completed
L48: DLP power restored to 255
```

### Print Completion:
```
Print thread finished.
PeakForceLogger shut down.
Plot queue cleared.
DLP reset to safe state (video mode, power=0)
```

### Stop Button:
```
DLP reset to safe state (video mode, power=0)
```

### After Fault:
```
RECOVERY FAILED L48: <error message>
DLP reset to safe state (video mode, power=0)
```

## 🧪 Quick Test Checklist

### Test 1: Normal Print (5 min)
- [ ] Start 3-layer stepped print
- [ ] Verify "DLP power=0" appears after each exposure
- [ ] Verify "DLP power restored" appears after stage returns
- [ ] Let print complete
- [ ] Verify "PeakForceLogger shut down" message
- [ ] Wait 2 minutes
- [ ] Click "Clear Plot" → Should be instant
- [ ] Start another print → Should work immediately

### Test 2: Stop Button (2 min)
- [ ] Start stepped print
- [ ] Click Stop after layer 2
- [ ] Verify "DLP reset to safe state" message
- [ ] Check DLP showing HDMI (not black)
- [ ] Start new print immediately → Should work

### Test 3: Background Light Check (2 min)
- [ ] Turn off room lights
- [ ] Start stepped print
- [ ] During exposure: Light should project
- [ ] After exposure: Look at DLP → Should be COMPLETELY DARK
- [ ] After stage return: Light should be ready for next layer

### Test 4: Long Idle (15 min)
- [ ] Run a print
- [ ] Let it complete
- [ ] Wait 15 minutes (do other work)
- [ ] Click "Clear Plot" → Should be instant (not frozen)
- [ ] Start new print → Should work without lag

## ⚠️ What to Report

### If Issues Occur:
1. **Copy the full error message** from status window
2. **Note which test** you were running
3. **Check if any status messages are missing** (compare to list above)
4. **Note if DLP requires power cycle** to recover

### Success Indicators:
- ✅ No GUI freezing when clearing plots
- ✅ No DLP power cycles needed between prints
- ✅ No visible light from DLP between exposures (stepped mode)
- ✅ Clean status messages for all operations
- ✅ No stage stalls after long idle periods

## 🔍 Troubleshooting

### If GUI still freezes on "Clear Plot":
- Check if `_cleanup_print_resources()` is being called (status message should appear)
- Check if PeakForceLogger shutdown message appears at print end

### If DLP still gets stuck:
- Check if "DLP reset to safe state" message appears when stopping
- Verify cleanup is called in fault recovery (check status messages)

### If background light still visible:
- Check status messages for "DLP power=0" after each exposure
- Verify you're in stepped mode (not segmented mode)
- Check if power is being restored (should see "restored to X")

## 📞 Quick Summary for Reporting

**All working? Report this:**
```
✅ All fixes verified working:
- No GUI freezing after 15min idle + Clear Plot
- No DLP power cycle needed after errors
- No background light in stepped mode
- All status messages appearing correctly
```

**Issues? Report this:**
```
⚠️ Issue found in Test X:
- Symptom: <what happened>
- Status messages: <copy last 5-10 lines>
- DLP state: <showing HDMI / black screen / other>
- Workaround needed: <yes/no, what>
```

---

**Remember**: These fixes address the ROOT CAUSES of your issues:
1. Background threads running when they shouldn't
2. DLP not being reset properly
3. Light leaking during stage movement

If the tests pass, these problems should be **completely solved**! 🎉
