import logging
import sys
import socket
import logging
import threading
import math
import re
import glob
import time
import time
import traceback 
import os
import cv2
import screeninfo
import numpy as np
from PIL import Image, ImageTk
from zaber_motion import Units
from zaber_motion.ascii import Connection
import sys
import usb.core
import usb.util 
from pprint import pprint

from pathlib import Path
from itertools import cycle
from datetime import datetime

if sys.version_info[0] == 2:
    import Tkinter
    tkinter = Tkinter
    from Tkinter import *
    from Tkinter.ttk import *
    from Tkinter import filedialog 
else:
    import tkinter
    from tkinter import *
    from tkinter.ttk import *
    from tkinter import filedialog 

height = 100
width = 100

blank_image = np.zeros((height,width,3), np.uint8)

blank_image[:,0:width//2] = (255,0,0)      # (B, G, R)
blank_image[:,width//2:width] = (0,255,0)


def run():
    cv2.namedWindow("preview", cv2.WINDOW_NORMAL)
    cv2.imshow('preview', blank_image)
    cv2.waitKey(0)

if __name__ == "__main__":
    thread = threading.Thread(target=run)
    thread.start()
    while True:
        time.sleep(1)
        print("Hello")
    print("Bye :)")