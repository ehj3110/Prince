# Prince Energy Test GUI (Prince_EnergyTest.py)

## Overview
Prince_EnergyTest.py is a specialized, DLP-only version of Prince_Segmented.py built for testing resin curing energy output across a wide range of light engine power settings. 

It completely strips out stage motion (Zaber stage), force gauge integration, auto-home routines, sandwich routines, and session loggers so that energy output calibration can be performed safely and quickly using only the DLP light engine and projection display.

---

## Technical Architecture & Design

### 1. Direct Inheritance from Prince_Segmented.py
To guarantee 100% hardware compatibility with the physical DLP9000 engine, Prince_EnergyTest.py uses the exact same class structure (MyWindow), threading setup, and DLP USB commands as Prince_Segmented.py:

- **DLP Initialization (__init__)**:
  `python
  self.controller = pycrafter9000.dmd()
  self.application = libs.Application()
  self.controller.stopsequence()
  self.controller.power(current=0)
  time.sleep(0.1)
  self.controller.changemode(3)  # HDMI / Video Mode
  self.controller.hdmi()
  `

- **Pattern Mode Sequence Switching (print_t)**:
  Before starting exposures, it executes the mandatory DLP mode change sequence required by LightCrafter firmware:
  `python
  self.controller.power(current=0)
  time.sleep(0.1)
  self.controller.changemode(0)  # Switch to pattern sequence mode
  self.controller.power(current=0)
  time.sleep(2.0)                # Crucial delay for mode change to take effect
  self.controller.power(current=initial_power)
  `

- **Projection Window Positioning**:
  Uses the exact display geometry calculation from Prince_Segmented.py:
  `python
  cv2.namedWindow(self.window_name, cv2.WND_PROP_FULLSCREEN)
  if self.screen:
      cv2.moveWindow(self.window_name, self.screen.x + 1439, self.screen.y - 1)
  cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
  cv2.imshow(self.window_name, self.black_image)
  `

---

## Power Routine Sequence

The script steps through **22 power levels** in descending order:

`python
POWER_SEQUENCE = [
    255, 225, 200, 175, 150, 125, 100, 75, 60, 50,
    45, 40, 35, 30, 25, 20, 15, 10, 7, 5,
    1, 0
]
`

### Exposure Loop Routine (Per Step):
1. **Set DLP LED Power**: self.controller.power(current=current_power)
2. **Project Image**: cv2.imshow(self.window_name, image_to_show) (cv2.waitKey(1))
3. **Expose Duration**: 	ime.sleep(exp_time_s) (User-specified in GUI)
4. **Blackout Window**: cv2.imshow(self.window_name, self.black_image)
5. **LED Off**: self.controller.power(current=0)
6. **Inter-Step Delay**: 	ime.sleep(0.1)

---

## Operating Instructions

### Prerequisites
1. Ensure the DLP9000 light engine is powered on.
2. Ensure the official Texas Instruments LightCrafter GUI is **closed**.
3. Do not open windows on the projection display screen.

### Step-by-Step Execution
1. Launch the script:
   `ash
   python Prince_EnergyTest.py
   `
2. Select your image folder path using **Browse...** or enter it in Directory of Images.
3. Click **Load Folder**.
   - If the folder contains a single image, it will automatically reuse that image across all 22 power steps.
   - If the folder contains an instruction .txt file, it will parse images via libs.Application.
4. Enter the desired **Exposure time (s)** in the text box (default is 5.0 s).
5. Click **START ENERGY TEST**.
6. To halt execution at any point, click **STOP**.

---

## Summary of Stripped Components vs Prince_Segmented.py

| Component | Status in Prince_EnergyTest.py |
|---|---|
| Zaber Linear Stage (self.axis) | **Removed** |
| Force Gauge & Sensor Panel (SensorDataWindow) | **Removed** |
| Auto-Home Routine (AutoHomer) | **Removed** |
| Sandwich Routine Manager (SandwichRoutines) | **Removed** |
| Motion Controller (MotionController) | **Removed** |
| Session Logging & Folder Creators (SessionManager) | **Removed** |
| DLP Controller (pycrafter9000.dmd()) | **Preserved (Identical)** |
| Projection Window (cv2.imshow) | **Preserved (Identical)** |
| Instruction Parsing (libs.Application) | **Preserved (Identical)** |
