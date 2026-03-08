import time

# --- TECHNICAL PARAMETERS FROM DLPU018J ---
# USB Command IDs [cite: 2114, 2123]
CMD_MODE_SEL      = 0x1A1B  # Display Mode Selection
CMD_LUT_DEF       = 0x1A34  # Pattern LUT Definition
CMD_LUT_CONF      = 0x1A31  # Pattern LUT Configuration
CMD_BMP_INIT      = 0x1A2A  # Initialize Pattern BMP Load
CMD_BMP_LOAD      = 0x1A2B  # Pattern BMP Load
CMD_PATT_START    = 0x1A24  # Pattern Display Start/Stop

class DLPC900_Research_Driver:
    def __init__(self):
        self.is_running = False

    def setup_3d_print_mode(self):
        """
        Transitions the DLPC900 into the optimal state for 3D printing.
        Workflow: Stop -> Change Mode -> Define LUT -> Load Images -> Start.
        """
        # 1. STOP CURRENT DISPLAY [cite: 1528, 1716]
        # It is mandatory to stop the sequencer before changing LUTs or Modes.
        # Data 0x00 = Stop [cite: 1706]
        self.send_usb(CMD_PATT_START, [0x00])
        
        # 2. SET PATTERN ON-THE-FLY MODE [cite: 1387, 1821]
        # Mode 0x03 is for images loaded dynamically through USB/I2C.
        self.send_usb(CMD_MODE_SEL, [0x03])
        
        # 3. DEFINE THE LOOK-UP TABLE (LUT) [cite: 1796, 1797]
        # For 1-bit printing, we map one slice of a 24-bit image to an exposure.
        # This example defines two 1-bit patterns.
        self.define_1bit_pattern(index=0, exposure_us=200, img_index=0, bit_pos=0)
        self.define_1bit_pattern(index=1, exposure_us=200, img_index=0, bit_pos=1)
        
        # 4. CONFIGURE THE SEQUENCER [cite: 1732, 1733, 1749]
        # Tell the controller how many LUT entries to cycle through.
        # [Num_LUT_Entries(2), Repeat_Indefinitely(4)]
        # 0x02 0x00 (2 entries) | 0x00 0x00 0x00 0x00 (Indefinite)
        self.send_usb(CMD_LUT_CONF, [0x02, 0x00, 0x00, 0x00, 0x00, 0x00])

    def define_1bit_pattern(self, index, exposure_us, img_index, bit_pos):
        """
        Configures a single entry in the pattern sequence.
        
        Capabilities:
        - Trigger: Can wait for external TRIG_IN_1 before displaying[cite: 1530].
        - LED Control: Select Red, Green, Blue, or multiple for the exposure.
        - 1-Bit Optimization: Only 1-bit patterns support the 'Clear' function.
        """
        # Payload construction (LSB First)[cite: 114, 1815]:
        payload = [
            index & 0xFF, (index >> 8) & 0xFF,           # Pattern Index (0-399)
            exposure_us & 0xFF, (exposure_us >> 8) & 0xFF, (exposure_us >> 16) & 0xFF, # Exposure
            0x01, # BitDepth: 1-bit (bits 1-3 = 0) | Clear after exposure (bit 0 = 1)
            0x07, # LED Select: 0x07 = White (All LEDs on) 
            0x00, 0x00, 0x00,                            # Dark Time (0us)
            img_index,                                   # Which image container (0-17)
            bit_pos                                      # Which bit in that container (0-23)
        ]
        self.send_usb(CMD_LUT_DEF, payload)

    def upload_image(self, img_index, rle_data_with_48byte_header):
        """
        Handles the streaming of compressed bitmap data[cite: 1838, 1839].
        
        Limits:
        - Must load in REVERSE order if loading multiple images[cite: 1832].
        - Max packet size for 'Download Data' is 512 bytes[cite: 616].
        """
        data_size = len(rle_data_with_48byte_header)
        
        # Initialize the buffer for this index [cite: 1836]
        # Data: Index(2), Total_Size(4)
        init_payload = [img_index & 0xFF, 0x00] + list(data_size.to_bytes(4, 'little'))
        self.send_usb(CMD_BMP_INIT, init_payload)
        
        # Stream data in 512-byte chunks [cite: 1840, 1842]
        # The first packet MUST contain the 48-byte Image Header[cite: 1462, 1842].
        for i in range(0, data_size, 512):
            chunk = rle_data_with_48byte_header[i:i+512]
            # Pattern BMP Load (CMD_BMP_LOAD)
            self.send_usb(CMD_BMP_LOAD, chunk)

    def start_print(self):
        """Starts the execution of the pattern sequence[cite: 1702]."""
        # Data 0x02 = Start [cite: 1706]
        self.send_usb(CMD_PATT_START, [0x02])

    def send_usb(self, cmd, data):
        """Standard TI USB HID Wrapper[cite: 207, 238]."""
        # Report ID (0) + Flag + Seq + Len(2) + Cmd(2) + Data
        pass

    