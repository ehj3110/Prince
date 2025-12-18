// LRS-4KA-ConsoleDemo.cpp : Defines the entry point for the console application.
//  Last modified; 2021-10-19


// MSVS includes
#include "stdafx.h"
#include <Windows.h>

#include <iostream>
#include "kpdlp660.h"
#include "kpmsp430.h"

using namespace std;

// millisecond Delay macro used to a create delay between commands
//MSVS version;  
#define MSLEEP(x)        Sleep(x);

int _tmain(int argc, _TCHAR* argv[])
{
    // Create objects of both Microcontroller and DLP controller API
    KPMSP430 uCDev;
    KPDLP660 DLPDev;

    int i;

    cout << "Hello World!" << endl;

    // Open the USB Connections

    cout << " - Connecting to micro-controller" << endl;
    i = 0;
    do
    {
          uCDev.USB_Open();
    }
    while (!uCDev.USB_IsConnected() && i++ < 10);

    if (!uCDev.USB_IsConnected()) {
        cout << "Can't connect to micro-controller" << endl;

        return -1;
    }

    cout << " - Connecting to DLP controller" << endl;
    i = 0;
    do
    {
          DLPDev.USB_Open();
    }
    while (!DLPDev.USB_IsConnected() && i++ < 10);

    if (!DLPDev.USB_IsConnected()) {
        cout << "Can't connect to DLP controller" << endl;

        return -1;
    }

    // Check power state of projector before sending any other commands
    unsigned char powerMode = 99;
    if (DLPDev.LCR_GetPowerMode(&powerMode) == 0)
    {
        switch (powerMode)
        {
        case 0:
			cout << "Projector is still in RESET...exiting for now" << endl;
			return -1;

        case 1:
    	    cout << "Projector is still in STANDBY...exiting for now" << endl;
			return -1;

        case 2:
    	    cout << "Projector is in READY..." << endl;
            break;

        case 3:
    	    cout << "Projector is still in COOLING...exiting for now" << endl;
			return -1;

        case 4:
    	    cout << "Projector is still in BOOTUP...exiting for now" << endl;
			return -1;

        case 5:
    	    cout << "Projector is still in POWERUP...exiting for now" << endl;
			return -1;

        default:
    	    cout << "Projector is in an Unknown State...exiting." << endl;
			return -1;
        }
    } else {
    	cout << "Projector connection problem ... exiting." << endl;
		return -1;
    }

    cout << "Initialize actuator and move to starting position" << endl;
    DLPDev.LCR_SetXPRmode(1);		// Make sure we are in manual actuator mode (only one supported)
    DLPDev.LCR_SetXPR_DAC(0);		// Set nominal starting actuator position

	unsigned int major, minor, build;
	unsigned char fanSel = 1;
	unsigned char fanPWM = 50;
	unsigned char fanMode = 1;

	unsigned int minTemp16, lowTemp16, maxTemp16;

	uCDev.MSP_GetVersion(&major, &minor, &build); // Checking the MSP firmware version to determine if the MSP is capable of fan control. 

	//DISCLAIMER: Firmware/hardware mismatch can cause this function not to work. 
	// Rev C or later Jackboard and firmware v2.0.0 are required for the fan controls to work.
	if(major >= 2)
	{
		cout << "Reading current fan Temperature limits." << endl;
		if(uCDev.MSP_GetFanTempLimits(&minTemp16, &lowTemp16, &maxTemp16) < 0)
		{
			cout << "Unable to set fan duty cycle." << endl;
		}
		cout << "  -- Low Temp Bin = " << (float)minTemp16/10 << "C, Med Temp Bin = " << (float)lowTemp16/10  << "C, Hi Temp Bin = " << (float)maxTemp16/10 << "C." << 

		cout << "Setting fan #" << (int)fanSel << " to " << (int)fanPWM << "% PWM and mode " << (int)fanMode << "." << endl;
		if(uCDev.MSP_SetFanPWM(fanSel, fanMode, fanPWM) < 0)
		{
			cout << "Unable to set fan duty cycle." << endl;
		}

		cout << "  -- Reading back the fan settings to confirm." << endl;
		if(uCDev.MSP_GetFanPWM(fanSel, &fanMode, &fanPWM) < 0)
		{
			cout << "Unable to get fan duty cycle." << endl;
		} else {
			cout << "  -- Fan #" << (int)fanSel << " is currently in mode " << (int)fanMode << ", set to a PWM of " << (int)fanPWM << "%." << endl;
		}
	} else {									  // If correct Jackboard firmware/hardware version is not present, use DLP controller for fan control
		cout << "Setting fan PWM to 50% duty cycle." << endl;
		if(DLPDev.LCR_SetFanPWM(1, 50) < 0)
		{
			cout << "Unable to set fan duty cycle." << endl;
		}
	}

    ////////////////////////////////////////////////////////////////////
    // Example 1: Display Splash image
    ////////////////////////////////////////////////////////////////////
    float Amplitude;
    unsigned int AmpReg;

    AmpReg = 0;
    cout << "Reading the current LED amplitude setting from projector" << endl;
    if(uCDev.MSP_GetLEDAmplitude(&AmpReg) < 0)
    {
        cout << "Unable to get LED Driver Amplitude" << endl;
        return -1;
    }
    cout << "Current LED amplitude = " << AmpReg << endl;

    // Set LED drive to desired level [W]
    Amplitude = 0.25;
    AmpReg = (unsigned int) (Amplitude * 0x1f4);

    cout << "Setting LED amplitude to " << AmpReg << endl;
    if(uCDev.MSP_SetLEDAmplitude(AmpReg) < 0)
    {
        cout << "Unable to set LED Driver Amplitude" << endl;
        return -1;
    }

    cout << "Switching projector display mode to Splash Screen" << endl;
    DLPDev.LCR_ChangeProjectorMode(DLPDev.DISP_SPLASH);
    MSLEEP(5000); // longer delay required after mode changes

    // Enable the LED (constant on)
    if(DLPDev.LCR_LEDWithTimer(true, 0) < 0)
    {
        cout << "Unable to enable the LED" << endl;
        return -1;
    }

    cout << "Manually displaying splash image for ~10 seconds" << endl;
    MSLEEP(10000); // using software delay this time

    // Turn off the LED
    if(DLPDev.LCR_LEDWithTimer(false, 0) < 0)
    {
        cout << "Unable to disable the LED" << endl;
        return -1;
    }

    cout << "-\n---- Splash image Test Completed \n-" << endl;

    ////////////////////////////////////////////////////////////////////
    // Example 2: Controlled Exposure from HDMI/Display-Port input
    ////////////////////////////////////////////////////////////////////
    unsigned int origLEDOnTime, newLEDOnTime;
    float desiredExposure = 2.0;
	unsigned int actualExposure;
    unsigned char s0, s1, s2, s3;	// Status bytes
	
	
#if (0)		// Only select display port if something is connected
    cout << "Selecting DisplayPort input" << endl;
    DLPDev.LCR_ChangeProjectorMode(DLPDev.DISP_DP);  // switch projector to Display Port mode
    //MSLEEP(5000); // longer delay required after mode changes - or better to poll status ...
#endif
#if (1)		// Only select HDMI port if something is connected
    cout << "Selecting HDMI input" << endl;
    DLPDev.LCR_ChangeProjectorMode(DLPDev.DISP_HDMI);  // switch projector to HDMI mode
    //MSLEEP(5000); // longer delay required after mode changes - or better to poll status ...
#endif

    cout << "Polling Status after mode change until phase/freq lock is complete ..." << endl;
   if (DLPDev.LCR_GetErrorStatusWord(&s0, &s1, &s2, &s3) < 0)
    {
        cout << "Unable to get Error Status from DLP controller" << endl;
        return -1;
    } else {
		cout << " Error Status words: " << (unsigned int)s0 << " : " << (unsigned int)s1 << " : " << (unsigned int)s2 << " : " << (unsigned int)s3 << endl;
    }

    if ((s0 & 0x01) != 0)                                     // Sequence Error
		cout << " *** Sequencer Error detected ***" << endl;

    if ((s0 & 0x02) != 0)                                     // Pixel Clock Out of Range
		cout << " *** Pixel Clock out of range ***" << endl;

    if ((s0 & 0x04) != 0)                                     // VSync Lost or Out of Range
		cout << " *** Vsync lost or out of range ***" << endl;


	int pollNum = 50;		// Max Repeat polling status to see when we are locked
	do {	
	// After mode change to another source, check status to be sure
	// the input is valid before continuing.
    if (DLPDev.LCR_GetSystemStatusWord(&s0, &s1, &s2, &s3) < 0)
    {
        cout << "Unable to get System Status from DLP controller" << endl;
        return -1;
    } else {
		cout << " System Status words: " << (unsigned int)s0 << " : " << (unsigned int)s1 << " : " << (unsigned int)s2 << " : " << (unsigned int)s3 << endl;
	}

    if ((s1 & 0x04) != 0x04)                                  // Frame Rate Conversion (incorrect Vsync)
		cout << "  *** Sequencer Frane Rate is NOT Locked ***" << endl;

    if ((s1 & 0x08) != 0x08)                                  // Sequencer Phase Lock
		cout << "  *** Sequencer NOT Phase Locked ***" << endl;

	if ((s1 & 0x10) != 0x10)                                  // Sequencer Frequency Lock
		cout << "  *** Sequencer NOT Frequency Locked ***" << endl;
	
    MSLEEP(500);		// 0.5 sec delay between status polls
	} while (--pollNum && (s1 != 0x1C));

	if(pollNum < 1)
	    cout << "  *** Unable to get valid status within alloted time.  *** \n  Ignoring for now to continue testing" << endl;
	else
	    cout << "System Status indicates Phase and Frequency successfully locked on input\n" << endl;

    cout << "Shifting actuator to maximum position, turning on LED" << endl;
    DLPDev.LCR_SetXPR_DAC(252);

    // Check LED driver for current total On-Time for reference later
    if(uCDev.MSP_GetLEDOnTime(&origLEDOnTime) < 0)
    {
        cout << "Unable to get LED Driver On Time" << endl;
        return -1;
    }

    // Turn on the LED for 2 seconds
    if(DLPDev.LCR_LEDWithTimer(true, desiredExposure) < 0)
    {
        cout << "Unable to enable the LED with internal timer" << endl;
        return -1;
    }

    cout << "Waiting for Exposure to complete (at least 2 seconds)" << endl;
    MSLEEP(2500); // software delay until after expose time (> 2 seconds)

    // Check LED Driver timer to determine actual exposure duration
    if(uCDev.MSP_GetLEDOnTime(&newLEDOnTime) < 0)
    {
        cout << "Unable to get LED Driver On Time" << endl;
        return -1;
    }

    actualExposure = newLEDOnTime - origLEDOnTime;
    cout << "Actual Exposure according to LED driver was " << actualExposure << endl;

    cout << "-\n---- External Mode Change Test Completed \n-" << endl;

    ////////////////////////////////////////////////////////////////////
    // Example 3: Internal Test Pattern Generator control
    ////////////////////////////////////////////////////////////////////

    cout << "Reset actuator to starting position" << endl;
    DLPDev.LCR_SetXPR_DAC(0);

    // Set LED drive to desired level [W]
    Amplitude = 0.5;
    AmpReg = (unsigned int) (Amplitude * 0x1f4);

    if(uCDev.MSP_SetLEDAmplitude(AmpReg) < 0)
    {
        cout << "Unable to set LED Driver Amplitude" << endl;
        return -1;
    }

    cout << "Switch to Test Pattern mode" << endl;
    DLPDev.LCR_ChangeProjectorMode(DLPDev.DISP_TPG);  // switch projector to test pattern mode
    MSLEEP(5000); // longer delay required after mode changes

    // Enable the LED (constant on)
    if(DLPDev.LCR_LEDWithTimer(true, 0) < 0)
    {
        cout << "Unable to enable the LED" << endl;
        return -1;
    }

    cout << "Selecting various Test Patterns" << endl;
    DLPDev.LCR_SetTPGSelect(DLPDev.H_RAMP); // set test pattern- horizontal ramp
    cout << " - Displaying Horizontal ramps ..." << endl;
    MSLEEP(3000); // short pause

    DLPDev.LCR_SetTPGSelect(DLPDev.V_RAMP); // set test pattern- vertical ramp
    cout << " - Displaying Vertical ramps ..." << endl;
    MSLEEP(3000); // short pause

    DLPDev.LCR_SetTPGSelect(DLPDev.CHECKER); // set test pattern- checkerboard
    cout << " - Displaying Checkerboard ..." << endl;
    MSLEEP(3000); // short pause

    // Turn off the LED
    if(DLPDev.LCR_LEDWithTimer(false, 0) < 0)
    {
        cout << "Unable to disable the LED" << endl;
        return -1;
    }

    cout << "Turn off actuator (move to neutral position)." << endl;

    // turn off actuator
    if (DLPDev.LCR_SetXPR_DAC(128) < 0)
    {
        cout << "Unable to set XPR DAC in manual mode" << endl;
    }

    cout << "-\n---- Internal TPG Control Test Completed \n-" << endl;

    // Close USB connections
    cout << "Disconnect from projector and exit." << endl;

    DLPDev.USB_Close();
    uCDev.USB_Close();

    return 0;
}

