/*! \mainpage Information about KPDLP660 API
 *
 * \section intro_sec Introduction
 *
 *   This API library file is used to communicate with dual DDP4422 ASICs on a
 * Visitech LC4kA/WQm Controller board in conjunction with a DLP660 DMD.
 *   The KPDLP660 library is required to access these functions and
 * includes both the DLP660 and MSP430 API.
 *
 * \section how_to_sec How to use:
 *
 * &emsp;   Before being able to use any of the functionality of the library, the USB cable
 * must be connected to both the Controller board and the computer.  Make sure 
 * that the hidapi DLL and the KPDLP660 DLL are in the same folder (Windows). <BR>
 * &emsp;   To establish communications with the board use the KPDLP660::USB_Open() command.
 * Once communications with the board is established the LCR functions will
 * become available. <BR>
 * &emsp;   At the point in which communications with the ASIC are to be terminated, use
 * the KPDLP660::USB_Close() command. <BR>
 * <blockquote>
 *     Basic Example code: <BR>
 * &emsp;      KPDLP660::USB_Open(); <BR>
 * &emsp;      KPDLP660::LCR_GetVersion(&pApp_ver, &pAPI_ver, &pSWConfig_ver,
 *								&pSeqConfig_ver, &pSeqRevision, &dllVersion); <BR>
 * &emsp;      KPDLP660::USB_Close();
 * </blockquote>
 *
 * \section version_history Version History:
 *
 * v1.0: <BR>
 * &emsp;   - Initial Release
 * 
 * v1.2: <BR>
 * &emsp;   - Deprecated commands USB_Init(), USB_Exit()
 *
 * v1.3: <BR>
 * &emsp;   - Added advanced control commands and reorganized the main page
 *
 * v1.4: <BR>
 * &emsp;   - Added additional error checking on the commands within the LCR_LEDWithTimer()
 *          routine to address the ambiguous response (>0 value).  Also added a delay to avoid
 *          command inversion which caused the function to sometimes lose an illuminator
 *          on/off request without warning.  This command is still recommended for controlled
 *          exposure times since it synchronizes the on/off time with the full frame but the
 *          LCR_SetLEDMode() command can be used if the exact exposure time is not critical
 *          such as when the exposure time is in the range of multiple seconds.
 *
 * v1.5: <BR>
 * &emsp;   - Added new commands for accessing the FPGA video input mux IC which can assist in
 *          debugging noisy or unstable video sources from the HDMI or DP inputs.  Requires
 *          FPGA firmware v5.0.43 or greater (contact Visitech for upgrade information if you 
 *          do not already have a compatible version).
 *
 * <blockquote>
 *          LCR_GetFPGAvideoInputStatus() -   Provides error flags to allow identification of
 *                                            problems from user software.<BR>
 *          LCR_ResetFPGAvideoInputStatus() - Resets sticky flags in Status word
 * </blockquote>
 *
 * v1.6: <BR>
 * &emsp;   - Added new commands to Set/Get the DMD Mirror Park state which will promote mirror
 *          stability when remaining idle for extended periods with the illuminators disabled.
 *
 * <blockquote>
 *          LCR_GetDMDpark() <BR>
 *          LCR_SetDMDpark()
 * </blockquote>
 *
 * &emsp;   - Added new Projector Mode to the existing LCR_ChangeProjectorMode() call which allows
 *          selecting a 50/50 Mirror conditioning mode for improving the DMD lifetime.  After 
 *          displaying an image for some period of time, this mode should be used during idle 
 *          periods.  If more than 2 minutes of idle time is expected, it is recommended to place 
 *          the DMD in the Parked state (see LCR_SetDMDpark() command) after 2 minutes of using 
 *          this mode. <BR>
 *          NOTE: This Mirror Conditioning improvment requires Sequence Revision 20230522 or newer
 *          (included in DDP4422_KN_4kSirius_Api7_App9.0.7_2023-05-22.img firmware update file).
 *
 *          See specific API command documentation for additional details.
 *
 * v1.6.1: <BR>
 * &emsp;   - Fixed a bug with the LCR_LEDWithTimer() command to address an issue that would
 *          occasionally cause the projected image to get stuck in a "flickering" state when
 *          turning the LED on/off in rapid succession.  This also caused the phase lock/unlock
 *          status to alternate while in this state.
 *
 * v1.6.2: <BR>
 * &emsp;   - Added new USB_Open() command that includes an index to be used when multiple units
 *          are connected to the same PC.  Similar to the equivalent MSP430 command, instead of
 *          connecting to the first instance of the matching PID/VID USB device, the device index
 *          will be used.  If no valid indexed device exists, an error is returned indicating
 *          there are not that many devices currently connected.
 *
 * v1.6.3: <BR>
 * &emsp;   - Added 5-10 sec delay in LCR_ChangeProjectorMode() method as well as some cleanup
 *          of LCR_LEDWithTimer() to address sensitivity seen in some applications to display
 *          mode changes.
 *
 * v1.6.5: <BR>
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

#ifndef KPDLP660_H
#define KPDLP660_H

#include "../common.h"



#if LINUX_MAC_BUILD==1
//For Linux/Mac use this line
#define KPDLP660_API
#else      //_WIN32

// Based on KPDLP660_DLL_EXPORTS Pre-processor directives, this properly creates DLL or allows access
// (define in .pro file for Qt DLL)
#if KPDLP660_DLL_EXPORTS==1		//defined in MSVC preprocessor settings for DLL
    #define KPDLP660_API __declspec(dllexport)
#else
    #define KPDLP660_API __declspec(dllimport)
#endif      // KPDLP660_DLL_EXPORTS
#endif // LINUX_MAC_BUILD


extern "C" class KPDLP660_API KPDLP660
{

public:
    KPDLP660();

    /*! \enum display_t kpdlp660.h
     * Useful enumeration of the Display modes that
     * can be selected.
    */
    typedef enum
    {
        DISP_DP,                   	/**< 0x00 = Display-Port input */
        DISP_TPG,                    /**< 0x01 = ASIC internal Test Pattern Generator */
        DISP_SOLID,                  /**< 0x02 = Solid Field */
        DISP_SPLASH,                 /**< 0x03 = Splash image */
        DISP_HDMI,                   /**< 0x04 = HDMI Input */
        DISP_FPGA,                   /**< 0x05 = FPGA test patterns */
        DISP_5050,                   /**< 0x06 = Mirror Conditioning (50/50 mode) */
    }display_t;

    /*! \enum testPatterns_t kpdlp660.h
     * Useful enumeration of Test Patterns that
     * can be selected.
    */
    typedef enum
    {
        RED,                 	/**< 0x00 = Red Flat Field */
        H_RAMP,                 /**< 0x01 = Horizontal Ramp */
        V_RAMP,                 /**< 0x02 = Vertical Ramp */
        H_LINES,                /**< 0x03 = Horizontal Lines */
        D_LINES,                /**< 0x04 = Diagonal Lines */
        V_LINES,                /**< 0x05 = Vertical Lines */
        GRID,                   /**< 0x06 = Grid Pattern */
        CHECKER,                /**< 0x07 = Checker-board Pattern */
        C_BAR,                  /**< 0x08 = Color Bars */
        RGB_RAMP,               /**< 0x09 = RGB Ramp */
    }testPatterns_t;

    typedef enum
    {
        BOTH_OFF        = 0x00,
        STROB_REPEAT    = 0x01,
        EARLY_TRIGGER   = 0x80,
        BOTH_ON         = 0x81,
    }strobeRepeat_t;

    /** @defgroup group1 The image control commands
     *  This is the list of commands relevant to changing the image on the projector
     *  @{
     */

    int  LCR_SetTPGSelect(testPatterns_t pattern);
    int  LCR_GetTPGSelect(testPatterns_t *pattern);

    int  LCR_SetImageFreeze(bool freeze);
    int  LCR_GetImageFreeze(bool *freeze);

    int  LCR_SetDMDpark(bool parked);
    BOOL LCR_GetDMDpark();

    int  LCR_SetLongAxisImageFlip(bool  flip);
    BOOL LCR_GetLongAxisImageFlip(void);

    int  LCR_SetShortAxisImageFlip(bool  flip);
    BOOL LCR_GetShortAxisImageFlip(void);

    int  LCR_SetDLPFunctions(bool CI, bool CTI, bool GC, bool CCA, bool BC, bool STM, bool BS);         // Only STM does anything. The rest are not confiugured
    int  LCR_GetDLPFunctions(bool *CI, bool *CTI, bool *GC, bool *CCA, bool *BC, bool *STM, bool *BS);  // Only STM does anything. The rest are not confiugured
    int  LCR_SetSolidFieldColor(int red, int green, int blue);
    int  LCR_GetSolidFieldColor(int *red, int *green, int *blue);
    int  LCR_GetGammaTableSelection(int *selection);
    int  LCR_SetGammaTableSelection(int selection);
    int  LCR_GetLedCurrents(unsigned int *pRed, unsigned int *pGreen, unsigned int *pBlue);
    int  LCR_SetLedCurrents(unsigned int RedCurrent, unsigned int GreenCurrent, unsigned int BlueCurrent);
    int  LCR_SetLEDMode(bool mode);
    int  LCR_GetLEDMode(bool *mode);
    int  LCR_LEDWithTimer(bool enable, float time);
    int  LCR_ChangeProjectorMode(display_t mode);
    int  LCR_GetProjectorOutputMode(display_t *type);
    int  LCR_GetFRCParameters(float *input, float *output, unsigned long *mode);
    int  LCR_GetSTM_Bypass(unsigned char *state);
    int  LCR_SetSTM_Bypass(unsigned char state);
    int  LCR_SetFrameRepeat(unsigned char frameEnable, unsigned char triggEnable, unsigned int frames);


    /** @} */ // end of group1

    /** @defgroup group2 The general status commands
     *  This is the list of commands relevant to obtaining or updating the status of the projector
     *  @{
     */

    int LCR_GetSystemStatusWord(unsigned char *byte0, unsigned char *byte1, unsigned char *byte2, unsigned char *byte3);
    int LCR_GetErrorStatusWord(unsigned char *byte0, unsigned char *byte1, unsigned char *byte2, unsigned char *byte3);
    int LCR_SetStrobeOverride(unsigned char redEnable, unsigned char greenEnable, unsigned char blueEnable);
    int LCR_GetStrobeOverride(unsigned char *redEnable, unsigned char *greenEnable, unsigned char *blueEnable);
    int LCR_SetSystemMode(short mode);
    int LCR_GetSystemMode(short *mode);
    int LCR_GetPowerMode(unsigned char *powerMode);
    int LCR_FPGAVersion(unsigned int *version);
    int LCR_GetFPGAvideoInputStatus(int *status);
    int LCR_ResetFPGAvideoInputStatus();
    int LCR_GetFPGAdebugReg(int size, unsigned int *FPGA_DebugVal);
    int LCR_GetVersion(unsigned int *pApp_ver, unsigned int *pAPI_ver, unsigned int *pSWConfig_ver, unsigned int *pSeqConfig_ver, unsigned int *pSeqRevision, unsigned int *dllVersion);

    /** @} */ // end of group2

    /** @defgroup group3 The motor control commands
     *  This is the list of commands relevant to changing the settings of the motors
     *  @{
     */

    int LCR_SetXPRmode(unsigned int xprMode);
    int LCR_GetXPRmode(unsigned int *xprMode);
    int LCR_SetXPR_DAC(unsigned int xprLevel);
    int LCR_GetXPR_DAC(unsigned int *xprLevel);
    int LCR_SetFanPWM(int fan, int duty);
    int LCR_GetFanPWM(int fan, int *duty);

    /** @} */ // end of group3

    /** @defgroup group4 The USB communication commands
     *  This is the list of commands relevant to instantiating, maintaining, and closing USB communications
     *  @{
     */

    int USB_Open(void);
    int USB_Open(uint8 device);
    int USB_Open(char *path);
    // future option; int USB_Open(uint8 Port, uint8 *PortLUT, char *Path, uint8 numPorts);
    // future option; int USBOpen(uint8 ProjectorNum, uint8 *portLUT);

    bool USB_IsConnected();
    int  USB_Close();

    /** @} */ // end of group4

}; //class


#endif // KPDLP660_H

