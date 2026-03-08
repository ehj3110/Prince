import usb.core
import usb.util
import numpy
import sys

##function that converts a number into a bit string of given length

def convlen(a,l):
    b=bin(a)[2:]
    padding=l-len(b)
    b='0'*padding+b

    return b

##function that converts a bit string into a given number of bytes

def bitstobytes(a):
    bytelist=[]
    if len(a)%8!=0:
        padding=8-len(a)%8
        a='0'*padding+a
    for i in range(len(a)//8):
        bytelist.append(int(a[8*i:8*(i+1)],2))

    bytelist.reverse()

    return bytelist

##function that encodes a 8 bit numpy array matrix as a enhanced run lenght encoded string of bits

def mergeimages(images):
    mergedimage=numpy.zeros((1600,2560,3),dtype='uint8')

    for i in range(len(images)):
        if i<8:
            mergedimage[:,:,2]=mergedimage[:,:,2]+images[i]*(2**i)
        if i>7 and i<16:
            mergedimage[:,:,1]=mergedimage[:,:,1]+images[i]*(2**(i-8))
        if i>15 and i<24:
            mergedimage[:,:,0]=mergedimage[:,:,0]+images[i]*(2**(i-16))

    return mergedimage

def encode(image): 
    """Encode full 2560x1600 image for DLP9000"""
    return encode_custom(image, 2560, 1600)

def encode_custom(image, width, height):
    """
    Encode image with custom dimensions for dual-controller DLP9000.
    Uses Standard RLE (Type 1) for robust, safe encoding.
    
    Args:
        image: numpy array (height, width, 3)
        width: image width (2560 for full, 1280 for half)
        height: image height (typically 1600)
    
    Returns:
        (bitstring, bytecount): encoded data and size
    """
    
    ## Header creation (48 bytes)
    bytecount = 48    
    bitstring = []

    # Signature: "Spld"
    bitstring.append(0x53)
    bitstring.append(0x70)
    bitstring.append(0x6c)
    bitstring.append(0x64)
    
    # Width (uint16 little endian)
    width_bytes = convlen(width, 16)
    width_bytes = bitstobytes(width_bytes)
    for i in range(len(width_bytes)):
        bitstring.append(width_bytes[i])

    # Height (uint16 little endian)
    height_bytes = convlen(height, 16)
    height_bytes = bitstobytes(height_bytes)
    for i in range(len(height_bytes)):
        bitstring.append(height_bytes[i])

    # Total size (placeholder, filled later)
    total = convlen(0, 32)
    total = bitstobytes(total)
    for i in range(len(total)):
        bitstring.append(total[i])        

    # Padding (0xFF * 8)
    for i in range(8):
        bitstring.append(0xff)

    # Black curtain (0x00 * 4)
    for i in range(4):
        bitstring.append(0x00)

    bitstring.append(0x00)  # Reserved

    bitstring.append(0x01)  ## STANDARD RLE (Type 1) - Safer than Enhanced RLE

    bitstring.append(0x01)  # Encoding type

    # Padding (0x00 * 21)
    for i in range(21):
        bitstring.append(0x00)

    ## Standard RLE (Type 1) Encoding Logic
    # Pack RGB into uint32 for atomic pixel comparison
    # This prevents the numpy.all() bug and is faster
    packed_pixels = (image[:,:,0].astype(numpy.uint32) << 16) | \
                    (image[:,:,1].astype(numpy.uint32) << 8) | \
                    (image[:,:,2].astype(numpy.uint32))
    
    for row in range(height):
        col = 0
        while col < width:
            pixel_val = packed_pixels[row, col]
            run_len = 1
            
            # Calculate run length (max 127 for safety)
            while (col + run_len < width) and \
                  (packed_pixels[row, col + run_len] == pixel_val) and \
                  (run_len < 127):
                run_len += 1
            
            # Extract RGB channels (maintain R-G-B order to match existing bit-packer)
            r = (pixel_val >> 16) & 0xFF
            g = (pixel_val >> 8) & 0xFF
            b = pixel_val & 0xFF
            
            # Write packet: [Length, R, G, B]
            bitstring.append(run_len)
            bitstring.append(r)
            bitstring.append(g)
            bitstring.append(b)
            bytecount += 4
            
            col += run_len
        
        # End of line marker
        bitstring.append(0x00)
        bitstring.append(0x00)
        bytecount += 2
    
    # End of image marker
    bitstring.append(0x00)
    bitstring.append(0x01)
    bytecount += 2

    # Pad to 4-byte boundary
    while (bytecount) % 4 != 0:
        bitstring.append(0x00)
        bytecount += 1        

    size = bytecount

    # Update total size in header (bytes 8-11)
    total = convlen(size, 32)
    total = bitstobytes(total)
    for i in range(len(total)):
        bitstring[i+8] = total[i]    

    return bitstring, bytecount



##a dmd controller class

class dmd():
    def __init__(self):
        self.dev=usb.core.find(idVendor=0x0451 ,idProduct=0xc900 )

        self.dev.set_configuration()

        self.ans=[]

## standard usb command function

    def command(self,mode,sequencebyte,com1,com2,data=None):
        buffer = []

        flagstring=''
        if mode=='r':
            flagstring+='1'
        else:
            flagstring+='0'        
        flagstring+='1000000'
        buffer.append(bitstobytes(flagstring)[0])
        buffer.append(sequencebyte)
        temp=bitstobytes(convlen(len(data)+2,16))
        buffer.append(temp[0])
        buffer.append(temp[1])
        buffer.append(com2)
        buffer.append(com1)

        if len(buffer)+len(data)<65:
        
            for i in range(len(data)):
                buffer.append(data[i])

            for i in range(64-len(buffer)):
                buffer.append(0x00)


            self.dev.write(1, buffer)

        else:
            for i in range(64-len(buffer)):
                buffer.append(data[i])

            self.dev.write(1, buffer)

            buffer = []

            j=0
            while j<len(data)-58:
                buffer.append(data[j+58])
                j=j+1
                if j%64==0:
                    self.dev.write(1, buffer)

                    buffer = []

            if j%64!=0:

                while j%64!=0:
                    buffer.append(0x00)
                    j=j+1


                self.dev.write(1, buffer)                
                





        self.ans=self.dev.read(0x81,64)

## functions for checking error reports in the dlp answer

    def checkforerrors(self):
        self.command('r',0x22,0x01,0x00,[])
        if self.ans[6]!=0:
            print (self.ans[6])    

## function printing all of the dlp answer

    def readreply(self):
        for i in self.ans:
            print (hex(i))

## functions for idle mode activation

    def idle_on(self):
        self.command('w',0x00,0x02,0x01,[int('00000001',2)])
        self.checkforerrors()

    def idle_off(self):
        self.command('w',0x00,0x02,0x01,[int('00000000',2)])
        self.checkforerrors()

## functions for power management

    def standby(self):
        self.command('w',0x00,0x02,0x00,[int('00000001',2)])
        self.checkforerrors()

    def wakeup(self):
        self.command('w',0x00,0x02,0x00,[int('00000000',2)])
        self.checkforerrors()

    def reset(self):
        self.command('w',0x00,0x02,0x00,[int('00000010',2)])
        self.checkforerrors()

## test write and read operations, as reported in the dlpc900 programmer's guide

    def testread(self):
        self.command('r',0xff,0x11,0x00,[])
        self.readreply()

    def testwrite(self):
        self.command('w',0x22,0x11,0x00,[0xff,0x01,0xff,0x01,0xff,0x01])
        self.checkforerrors()

## some self explaining functions

    def changemode(self,mode):
        self.command('w',0x00,0x1a,0x1b,[mode])
        self.checkforerrors()

    def startsequence(self):
        self.command('w',0x00,0x1a,0x24,[2])
        self.checkforerrors()

    def pausesequence(self):
        self.command('w',0x00,0x1a,0x24,[1])
        self.checkforerrors()

    def stopsequence(self):
        self.command('w',0x00,0x1a,0x24,[0])
        self.checkforerrors()

    def power(self, current=0):
        self.command('w', 0x00, 0x0b, 0x01, [0, 0, current])
        self.checkforerrors()

    def hdmi(self):
        self.command('w', 0x00, 0x1a, 0x01, [1])
        self.checkforerrors()

    def configurelut(self,imgnum,repeatnum):
        img=convlen(imgnum,11)
        repeat=convlen(repeatnum,32)

        string=repeat+'00000'+img

        bytes=bitstobytes(string)

        self.command('w',0x00,0x1a,0x31,bytes)
        self.checkforerrors()
        

    def definepattern(self,index,exposure,bitdepth,color,triggerin,darktime,triggerout,patind,bitpos):
        payload=[]
        index=convlen(index,16)
        index=bitstobytes(index)
        for i in range(len(index)):
            payload.append(index[i])

        exposure=convlen(exposure,24)
        exposure=bitstobytes(exposure)
        for i in range(len(exposure)):
            payload.append(exposure[i])
        optionsbyte=''
        optionsbyte+='1'
        bitdepth=convlen(bitdepth-1,3)
        optionsbyte=bitdepth+optionsbyte
        optionsbyte=color+optionsbyte
        if triggerin:
            optionsbyte='1'+optionsbyte
        else:
            optionsbyte='0'+optionsbyte

        payload.append(bitstobytes(optionsbyte)[0])

        darktime=convlen(darktime,24)
        darktime=bitstobytes(darktime)
        for i in range(len(darktime)):
            payload.append(darktime[i])

        triggerout=convlen(triggerout,8)
        triggerout=bitstobytes(triggerout)
        payload.append(triggerout[0])

        patind=convlen(patind,11)
        bitpos=convlen(bitpos,5)
        lastbits=bitpos+patind
        lastbits=bitstobytes(lastbits)
        for i in range(len(lastbits)):
            payload.append(lastbits[i])



        self.command('w',0x00,0x1a,0x34,payload)
        self.checkforerrors()
        


    def setbmp(self,index,size):
        """Initialize Pattern BMP Load for PRIMARY controller (left half of DLP9000)"""
        payload=[]

        index=convlen(index,5)
        index='0'*11+index
        index=bitstobytes(index)
        for i in range(len(index)):
            payload.append(index[i]) 


        total=convlen(size,32)
        total=bitstobytes(total)
        for i in range(len(total)):
            payload.append(total[i])         
        
        self.command('w',0x00,0x1a,0x2a,payload)
        self.checkforerrors()

    def setbmp_secondary(self,index,size):
        """Initialize Pattern BMP Load for SECONDARY controller (right half of DLP9000)"""
        payload=[]

        index=convlen(index,5)
        index='0'*11+index
        index=bitstobytes(index)
        for i in range(len(index)):
            payload.append(index[i]) 


        total=convlen(size,32)
        total=bitstobytes(total)
        for i in range(len(total)):
            payload.append(total[i])         
        
        # 0x2C is the Secondary controller command (vs 0x2A for Primary)
        self.command('w',0x00,0x1a,0x2c,payload)
        self.checkforerrors()

## bmp loading function, divided in 56 bytes packages
## max  hid package size=64, flag bytes=4, usb command bytes=2
## size of package description bytes=2. 64-4-2-2=56

    def bmpload(self,image,size):
        """Upload pattern data to PRIMARY controller (left half of DLP9000)"""
        packnum=size//504+1

        counter=0

        for i in range(packnum):
            if i %100==0:
                print (i,packnum)
            payload=[]
            if i<packnum-1:
                leng=convlen(504,16)
                bits=504
            else:
                leng=convlen(size%504,16)
                bits=size%504
            leng=bitstobytes(leng)
            for j in range(2):
                payload.append(leng[j])
            for j in range(bits):
                payload.append(image[counter])
                counter+=1
            self.command('w',0x11,0x1a,0x2b,payload)


            self.checkforerrors()

    def bmpload_secondary(self,image,size):
        """Upload pattern data to SECONDARY controller (right half of DLP9000)"""
        packnum=size//504+1

        counter=0

        for i in range(packnum):
            if i %100==0:
                print (i,packnum)
            payload=[]
            if i<packnum-1:
                leng=convlen(504,16)
                bits=504
            else:
                leng=convlen(size%504,16)
                bits=size%504
            leng=bitstobytes(leng)
            for j in range(2):
                payload.append(leng[j])
            for j in range(bits):
                payload.append(image[counter])
                counter+=1
            # 0x2D is the Secondary controller command (vs 0x2B for Primary)
            self.command('w',0x11,0x1a,0x2d,payload)


            self.checkforerrors()


    def defsequence(self,images,exp,ti,dt,to,rep):

        self.stopsequence()

        arr=[]

        for i in images:
            arr.append(i)

##        arr.append(numpy.ones((1080,1920),dtype='uint8'))

        num=len(arr)

        encodedimages=[]
        sizes=[]

        for i in range((num-1)//24+1):
            print ('merging...')
            if i<((num-1)//24):
                imagedata=mergeimages(arr[i*24:(i+1)*24])
            else:
                imagedata=mergeimages(arr[i*24:])
            print ('encoding...')
            imagedata,size=encode(imagedata)

            encodedimages.append(imagedata)
            sizes.append(size)

            if i<((num-1)//24):
                for j in range(i*24,(i+1)*24):
                    self.definepattern(j,exp[j],1,'111',ti[j],dt[j],to[j],i,j-i*24)
            else:
                for j in range(i*24,num):
                    self.definepattern(j,exp[j],1,'111',ti[j],dt[j],to[j],i,j-i*24)

        self.configurelut(num,rep)

        for i in range((num-1)//24+1):
        
            self.setbmp((num-1)//24-i,sizes[(num-1)//24-i])

            print ('uploading...')
            self.bmpload(encodedimages[(num-1)//24-i],sizes[(num-1)//24-i])

    def display_static_pattern(self, image_array, exposure_us=100000, repeat_count=0):
        """
        Display a single static 1-bit pattern (fast upload, ~3 seconds).
        This provides stable, non-choppy display suitable for calibration patterns.
        
        Args:
            image_array: 2D numpy array (1600×2560) of pattern (0-255 uint8)
            exposure_us: Exposure time in microseconds (default 100ms = 100000us)
            repeat_count: Number of times to repeat (0 = infinite loop)
        
        Example:
            import cv2
            pattern = cv2.imread('charuco_pattern.png', cv2.IMREAD_GRAYSCALE)
            pattern_resized = cv2.resize(pattern, (2560, 1600))
            dmd.display_static_pattern(pattern_resized, exposure_us=100000)
        """
        print(f"Uploading 1-bit pattern (exposure: {exposure_us}us)...")
        
        # Ensure correct dtype and size
        if image_array.dtype != numpy.uint8:
            image_array = image_array.astype(numpy.uint8)
        if image_array.shape != (1600, 2560):
            raise ValueError(f"Image must be (1600, 2560), got {image_array.shape}")
        
        # Convert to binary (threshold at 128)
        binary_pattern = (image_array > 128).astype(numpy.uint8)
        
        # Pack into bits (8 pixels per byte)
        # 2560 × 1600 = 4,096,000 pixels → 512,000 bytes at 1-bit
        flat = binary_pattern.flatten()
        packed = numpy.packbits(flat)
        image_bytes = packed.tolist()
        size = len(image_bytes)
        
        # Configure pattern LUT (1 pattern, repeat count)
        self.configurelut(1, repeat_count)
        
        # Set up and upload BMP
        self.setbmp(0, size)
        self.bmpload(image_bytes, size)
        
        # Define pattern (1-bit depth, white color)
        self.definepattern(
            index=0, exposure=exposure_us, bitdepth=1, color='111',
            triggerin=0, darktime=0, triggerout=0, patind=0, bitpos=0
        )
        
        # Start display
        self.startsequence()
        print("✓ Pattern displayed")






