/*! \mainpage Information about the KPMSP430 API
 *
 * \section intro_sec Introduction
 *
 *   This API library file is used to communicate with a jack board attached
 * to a Visitech LC4kA/WQm Controller board in conjunction with a DLP660 DMD.
 *   The KPDLP660 library is required to access these functions and
 * includes both the DLP660 and MSP430 API.
 *
 * \section how_to_sec How to use:
 *
 * Before being able to use any of the functionality of the DLL the USB 
 * cable must be connected to both the jack board and the computer. 
 * For Windows based applications, make sure that the hidapi DLL and
 * the KPDLP660 DLL are in the same folder as the KPMSP430 DLL.
 * To establish communications with the board use the KPMSP430::USB_Open() command
 * is issued to instantiate the object.
 * Once communications with the jack board is established the MSP functions
 * will become available.
 * At the point in which communications with the ASIC are to be terminated 
 * use the KPMSP430::USD_Close() command.
 * \n   Basic Example code:
 * \n       KPMSP430::USB_Open(); 
 * \n       KPMSP430::MSP_GetVersion(&versionMajor, &versionMinor, &versionBuild); 
 * \n       KPMSP430::USB_Close(); 
 *
 * \section version_history Version History:
 *
 * v1.1   - Deprecated redundant commands USB_Init(), USB_Exit()
 *
 * v1.3   - Added MSP fan control
 *
 * v1.4   - Added MSP flash read command for projector serial numbers.
 *
 * v1.5   - Added temperature controlled mode to the existing Fan PWM command.  
 *          This will require MSP430 Hardware Rev C boards and MSP430 firmware 
 *          v2.2 or greater.  Note that these commands previously contained the 
 *          mode parameter but it was not fully implemented.
 *              MSP_GetFanPWM(), MSP_SetFanPWM()
 *         - Added new command to modify the temperature trip points for the 
 *           new temperature controlled fan speed mode.
 *             MSP_GetFanTempLimits(), MSP_SetFanTempLimits()
 *         See specific commands for details.
 *
 * v1.5.1: <BR>
 * &emsp;   - Fixed bug with Fan PWM readback that caused a stack crash.
 *
 * v1.5.2: <BR>
 * &emsp;   - Added directives to API for "C" type export of DLL
 *
 */

/*************************************************************************
 * Copyright (C) {2023} Visitech - visitech.com
 *
 *  Redistribution and use in source and binary forms, with or without
 *  modification, are permitted provided that the following conditions
 *  are met:
 *
 *    Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 *
 *    Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the
 *    distribution.
 *
 *    Neither the name of Visitech nor the names of its contributors 
 *    may be used to endorse or promote products derived from this 
 *    software without specific prior written permission.
 *
 *  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 *  "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 *  LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
 *  A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
 *  OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 *  SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 *  LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 *  DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 *  THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 *  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 *  OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 *
 *************************************************************************/

#ifndef KPMSP430_H
#define KPMSP430_H

#include "../common.h"

#include <stdlib.h>
#include <stdio.h>
#include <string>

using namespace std;


#if LINUX_MAC_BUILD==1
    // For Linux/Mac use this line
    #define KPMSP430_API
#else		//_WIN32
    // This is defined in MSVC pre-processor configuration (or pro file in Qt)
    #if KPMSP430_DLL_EXPORTS==1
        #define KPMSP430_API __declspec(dllexport)
    #else
        #define KPMSP430_API __declspec(dllimport)
    #endif      // KPMSP430_DLL_EXPORTS
#endif		//_WIN32

#include <iostream>

extern "C" class KPMSP430_API KPMSP430
{
 public:
 
	KPMSP430();

    /*! \enum ledLogEntry
     * Structure describing an entry in the LED Driver log */
    typedef struct
    {
        unsigned int amp;           /**< LED Amplitude (12-bits) */ 
        unsigned int lightFB;       /**< Light Feedback (12-bits) */ 
        unsigned int currentFB;     /**< Current Feedback (12-bits) */ 
        unsigned int ledTemp;       /**< LED Temperature (12-bits) */ 
        unsigned int first;         // First 32-bit word from initial log address (prior to parsing)
        unsigned int second;        // Second 32-bit word from initial log address (prior to parsing)
    } ledLogEntry;

     /*! \enum t_FanMode
      * Structure describing Fan control Modes */
     typedef enum
     {
         FB_OFF,                 /**< Fan speed is user controlled (direct PWM setting) */
         TEMP_FB,                /**< Fan speed is controlled by the temperature */
         POWER_FB,               /**< Fan speed is controlled by the drive power */
     } t_FanMode;

    bool USB_IsConnected();

    int USB_Open(void);
    int USB_Open(uint8 device);
    int USB_Open(char *path);
    int USB_Open(const wchar_t *serNum);
    // future option; int USB_Open(uint8 Port, uint8 *PortLUT, char *Path, uint8 numPorts);
    // future option; int USBOpen(uint8 ProjectorNum, uint8 *portLUT);

    int USBgetSerialNumber(uint8 device, wchar_t **serNum);
    int USB_Close();

    int  MSP_GetLEDAmplitude(unsigned int *amp16);
    int  MSP_SetLEDAmplitude(unsigned int  amp16);
    int  MSP_GetLEDDriveTemp(unsigned int *temp16);
    int  MSP_GetLEDBoardTemp(unsigned int *temp16);
    int  MSP_GetLEDStatus   (unsigned int *status16);    
    int  MSP_GetLEDLightFeedback(unsigned int *FeedbackVal);
    int  MSP_GetLEDCurrentFeedback(unsigned int *FeedbackVal);    
    int  MSP_GetLEDOnTime(unsigned int *FeedbackVal);
    int  MSP_GetLEDlogEntry(unsigned int logAddr, ledLogEntry *LogEntry);
    int  MSP_GetVersion(unsigned int *versionMajor, unsigned int *versionMinor, unsigned int *versionBuild);
    int  MSP_SetBSLMode();
    void MSP_GetDLLVersion(unsigned int *version);

    int  MSP_GetFanPWM(unsigned char fan8, unsigned char *mode8, unsigned char *duty8);
    int  MSP_SetFanPWM(unsigned char fan8, unsigned char mode8, unsigned char duty8);

    int MSP_GetFanTempLimits(unsigned int *minTemp16, unsigned int *lowTemp16, unsigned int *maxTemp16);
    int MSP_SetFanTempLimits(unsigned int minTemp16, unsigned int lowTemp16, unsigned int maxTemp16);

    int  MSP_ReadFromFlash(uint8 bank, uint8 *serial);
    bool MSP_Busy();

    int  MSP_GetLEDRegMode(unsigned int *regmode16);
    int  MSP_SetLEDRegMode(unsigned int  regmode16);

}; //class


#endif // KPMSP430_H
