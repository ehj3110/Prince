# Testing Instructions for RED Lab Engineer

**Date:** December 18, 2025  
**Purpose:** Pre-deployment testing of force sensing hardware  
**Time Required:** ~15 minutes

---

## Overview

You will test the Phidget bridge connection and force sensing system **without requiring the full printer setup**. This test can be done on any computer with the bridge connected via USB.

**What you need:**
- Computer with Python installed
- Phidget bridge (VoltageRatioInput) connected via USB
- **Force gauge does NOT need to be connected yet**

---

## Step 1: Download Files from GitHub

1. **Go to GitHub repository:**
   ```
   https://github.com/ehj3110/Prince
   ```

2. **Download the RED lab upgrade folder:**
   - Navigate to: `RED_PotentialUpgradeScript/`
   - Click the green "Code" button
   - Select "Download ZIP"
   - Extract the ZIP file to your Desktop or Documents folder

   **OR use git clone (if you have git installed):**
   ```bash
   git clone https://github.com/ehj3110/Prince.git
   cd Prince/RED_PotentialUpgradeScript
   ```

3. **Verify you have these files:**
   ```
   RED_PotentialUpgradeScript/
   ├── test_force_sensing_hardware.py  ← TEST SCRIPT (you'll run this)
   ├── RED_Segmented.py                 ← Main printer control
   ├── RED_LAB_UPGRADE_DOCUMENTATION.md ← Full documentation
   ├── TESTING_INSTRUCTIONS_FOR_ENGINEER.md ← This file
   └── support_modules/                 ← Force sensing modules
       ├── ForceGaugeManager.py
       ├── SensorDataWindow.py
       └── ... (8 more files)
   ```

---

## Step 2: Install Phidget22 Library

1. **Open PowerShell or Command Prompt**

2. **Install Phidget22:**
   ```powershell
   pip install Phidget22
   ```

3. **Verify installation:**
   ```powershell
   python -c "import Phidget22; print('Phidget22 installed successfully')"
   ```

   **Expected output:**
   ```
   Phidget22 installed successfully
   ```

   **If you get an error:**
   - Try: `pip3 install Phidget22`
   - Or: `python -m pip install Phidget22`

---

## Step 3: Connect Hardware

1. **Connect Phidget bridge to computer via USB**
   - Use a USB-A or USB-C port (depending on your bridge model)
   - Wait 5-10 seconds for driver installation (first time only)

2. **DO NOT connect the force gauge yet**
   - The bridge can be tested on its own
   - We'll test the bridge → computer connection first

3. **Verify connection (Windows):**
   - Open Device Manager (Win + X → Device Manager)
   - Look for "Phidgets" or "HID-compliant device"
   - Should NOT show yellow warning icons

---

## Step 4: Run Test Script

1. **Navigate to the RED_PotentialUpgradeScript folder:**
   ```powershell
   cd C:\Users\[YourUsername]\Desktop\RED_PotentialUpgradeScript
   ```
   *(Replace [YourUsername] with your actual username, or navigate to wherever you extracted the files)*

2. **Run the test script:**
   ```powershell
   python test_force_sensing_hardware.py
   ```

3. **Watch the output carefully**
   - The script will run 5 test sections
   - Each test will show ✓ PASS or ✗ FAIL
   - Tests take ~20-30 seconds total

---

## Step 5: Interpret Results

### Expected Output (Success):

```
======================================================================
  TEST 1: Phidget22 Library Installation
======================================================================

✓ PASS - Phidget22 Import
      Library is installed and importable

======================================================================
  TEST 2: Phidget Bridge Detection
======================================================================

Attempting to detect Phidget bridge (15 second timeout)...
Please ensure the Phidget bridge is connected via USB.

✓ PASS - Bridge Detection
      Found Phidget device (Serial: 123456, Channel: 0)

✓ PASS - Read Voltage Ratio
      Current reading: 0.000123 V/V

======================================================================
  TEST 3: ForceGaugeManager Initialization
======================================================================

✓ PASS - ForceGaugeManager Import
      Module found and imported

Attempting to initialize ForceGaugeManager...

✓ PASS - ForceGaugeManager Creation
      Instance created successfully

✓ PASS - Bridge Connection via Manager
      ForceGaugeManager successfully connected to bridge

✓ PASS - Calibration Status Check
      Calibrated: False (expected: False for new setup)

======================================================================
  TEST 4: Continuous Data Acquisition
======================================================================

Testing continuous data reading (10 samples over 2 seconds)...

Reading samples:
  Sample 1: 0.000123 V/V
  Sample 2: 0.000124 V/V
  Sample 3: 0.000122 V/V
  ...

✓ PASS - Data Acquisition
      Collected 10 samples (mean: 0.000123, std: 0.000002)

✓ PASS - Data Quality
      Low noise detected (std: 0.000002)

======================================================================
  TEST 5: System Integration Check
======================================================================

✓ PASS - Support Modules Directory
      Path: C:\...\support_modules

✓ PASS - File: ForceGaugeManager.py
      Found

✓ PASS - File: SensorDataWindow.py
      Found

... (more files)

✓ PASS - RED_Segmented.py
      Main control file found

======================================================================
  TEST SUMMARY
======================================================================

Total Tests: 15
Passed: 15
Failed: 0
Success Rate: 100.0%

✓ ALL TESTS PASSED - Force sensing hardware is ready!

======================================================================
  RECOMMENDATIONS
======================================================================

✓ Hardware tests passed successfully!

Next steps:
1. Connect the force gauge to the Phidget bridge
2. Run RED_Segmented.py with MOCK_MODE = False
3. Open Sensor Panel and calibrate the force gauge
4. Test auto-home routine

For detailed instructions, see:
  - TESTING_INSTRUCTIONS_FOR_ENGINEER.md
  - RED_LAB_UPGRADE_DOCUMENTATION.md

======================================================================
Test completed. Save this output and report results.
======================================================================
```

---

## Step 6: Report Results

### If ALL tests passed (✓ PASS for everything):

**Send this message:**

```
✓ Force sensing hardware test PASSED

Test summary:
- Total tests: [number]
- All passed: YES
- Phidget bridge detected: YES
- Serial number: [number from output]
- Data acquisition working: YES

System is ready for next steps. Awaiting further instructions.
```

**Next steps:**
- Wait for instructions to proceed with full system test
- Keep the Phidget bridge connected

---

### If some tests failed (✗ FAIL):

**Copy the ENTIRE terminal output** and send it, along with:

1. **Which tests failed** (look for ✗ FAIL in the output)
2. **Error messages** (copy any red error text)
3. **System info:**
   - Windows version: (Win + R → `winver` → screenshot)
   - Python version: Run `python --version`
   - USB port used: (front/back of computer, USB 2.0/3.0?)

**Common failure scenarios:**

---

### Failure Case 1: "Phidget22 Import FAILED"

**Problem:** Phidget22 library not installed

**Fix:**
```powershell
pip install Phidget22
```

Then re-run the test script.

---

### Failure Case 2: "Bridge Detection FAILED - Timeout"

**Problem:** Bridge not detected by computer

**Troubleshooting:**
1. **Check USB connection:**
   - Try a different USB port (prefer USB 3.0 ports - usually blue)
   - Try a different USB cable if possible
   - Unplug and replug the bridge

2. **Check Device Manager (Windows):**
   - Win + X → Device Manager
   - Look for "Phidgets" section
   - Check for yellow warning icons
   - If warning present → Right-click → Update driver

3. **Restart computer:**
   - Sometimes USB drivers need a restart to load

4. **Re-run test after each fix attempt**

---

### Failure Case 3: "ForceGaugeManager Import FAILED"

**Problem:** Support modules not in correct location

**Fix:**
1. Verify folder structure:
   ```
   RED_PotentialUpgradeScript/
   ├── test_force_sensing_hardware.py
   └── support_modules/
       └── ForceGaugeManager.py  ← Must be here
   ```

2. If `support_modules/` folder is missing or in wrong place:
   - Re-download from GitHub
   - Extract ZIP completely (don't run from inside ZIP)

---

### Failure Case 4: "Data Acquisition FAILED"

**Problem:** Bridge detected but can't read data

**Troubleshooting:**
1. **Check if bridge LED is on** (if applicable to your model)
2. **Try unplugging and replugging** the bridge
3. **Check USB power:**
   - Some USB hubs don't provide enough power
   - Try plugging directly into computer (not through hub)
4. **Restart computer** and try again

---

## Step 7: After Successful Test

Once all tests pass:

1. **Keep the bridge connected**
2. **Wait for instructions** on next steps (likely Monday when Evan returns)
3. **Optional:** You can try opening the GUI:
   ```powershell
   python RED_Segmented.py
   ```
   - The GUI should open with "[MOCK MODE]" in the title
   - You can click around to see the interface
   - **Don't try to run prints or connect to the actual printer yet**

---

## Frequently Asked Questions

### Q: Do I need the force gauge (load cell) connected?
**A:** No! This test only requires the Phidget bridge connected via USB. The bridge can be tested on its own.

### Q: Do I need the full printer connected?
**A:** No! This is a hardware-only test. No printer, no DLP, no Zaber stage required.

### Q: How long should the test take?
**A:** About 20-30 seconds. If it's taking much longer, check the terminal output for timeout messages.

### Q: What if I get "CRITICAL: Install Phidget22" but I already installed it?
**A:** Try these in order:
1. Close and reopen PowerShell/Command Prompt
2. Run: `python -m pip install --upgrade Phidget22`
3. Try with `python3` instead of `python`
4. Check if you have multiple Python installations (run `where python` to see all)

### Q: Can I run this test multiple times?
**A:** Yes! Run it as many times as needed. It won't harm anything.

### Q: What if the bridge was working yesterday but not today?
**A:** 
1. Check USB cable connection
2. Try a different USB port
3. Restart the computer
4. Check Device Manager for driver issues

### Q: Should I install any Phidget Control Panel software?
**A:** Not required for this test, but it can be helpful for troubleshooting:
- Download from: https://www.phidgets.com/docs/Phidget_Control_Panel
- Can use it to verify the bridge is detected by Windows

---

## Emergency Contacts

If you encounter issues you can't resolve:

1. **Take screenshots of:**
   - Full terminal output from test script
   - Device Manager showing Phidgets section
   - Any error messages

2. **Send to:**
   - Evan Jones: evanjones2026@u.northwestern.edu
   - Include: "RED Lab Force Sensing Test - [PASS/FAIL]" in subject line

3. **Include:**
   - Full terminal output (copy-paste)
   - Python version: `python --version`
   - Windows version
   - Description of what failed

---

## Success Criteria

✓ **Test is successful if you see:**
- "ALL TESTS PASSED - Force sensing hardware is ready!"
- At least 10/15 tests passing (some failures may be OK depending on which)
- Bridge serial number detected
- Data samples successfully collected

✗ **Test needs troubleshooting if:**
- "Phidget22 Import" fails → Install library
- "Bridge Detection" fails → Check USB connection
- "Data Acquisition" fails → Check bridge power/drivers

---

## What Happens Next (After Successful Test)

**Monday (or when Evan returns):**
1. Connect the force gauge to the bridge
2. Open RED_Segmented.py with MOCK_MODE = False
3. Calibrate force gauge using Sensor Panel
4. Test auto-home routine
5. Run test print with force logging

**You'll receive detailed instructions for these steps after this initial hardware test is confirmed working.**

---

## File Locations Reference

After downloading from GitHub, you should have:

```
Desktop/RED_PotentialUpgradeScript/    (or wherever you extracted)
│
├── test_force_sensing_hardware.py     ← RUN THIS FIRST
├── RED_Segmented.py                   ← Main printer control (don't run yet)
├── RED_LAB_UPGRADE_DOCUMENTATION.md   ← Full docs (read later)
├── TESTING_INSTRUCTIONS_FOR_ENGINEER.md ← This file
│
├── support_modules/                   ← Force sensing code
│   ├── ForceGaugeManager.py
│   ├── SensorDataWindow.py
│   ├── AutoHomeRoutine.py
│   ├── PositionLogger.py
│   ├── AutomatedLayerLogger.py
│   ├── ExperimentalConditionsWindow.py
│   ├── PeakForceLogger.py
│   ├── adhesion_metrics_calculator.py
│   ├── USBCoordinator.py
│   └── two_step_baseline_analyzer.py
│
└── dinglab_printer/                   ← Existing RED lab DLP control
    └── ... (keep these - don't modify)
```

---

## Quick Command Reference

```powershell
# Install Phidget22
pip install Phidget22

# Navigate to test folder
cd C:\Users\[YourUsername]\Desktop\RED_PotentialUpgradeScript

# Run test
python test_force_sensing_hardware.py

# Check Python version
python --version

# Verify Phidget22 installed
python -c "import Phidget22; print('OK')"

# List all Python installations (if issues)
where python
```

---

**Good luck with the testing! The test script will guide you through everything step-by-step.**

**Remember: COPY THE ENTIRE TERMINAL OUTPUT and send it regardless of pass/fail - Evan needs to see the full results.**

---

*Document version: 1.0*  
*Last updated: December 18, 2025*  
*For questions: evanjones2026@u.northwestern.edu*
