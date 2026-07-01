from pathlib import Path
from PIL import Image, ImageTk
from itertools import cycle
import math
import re
import cv2
import glob
import numpy as np
import time

def make2(path="", extension='png', power = 100):
    image_paths = glob.glob(path+"/*." + extension)
    new = np.zeros((1600, 2560))
    for idx in range(len(image_paths)):
        img = cv2.imread(image_paths[idx], cv2.IMREAD_GRAYSCALE)
        # new[:, 170:930] = img[:, 580:1340]
        # new[:, 990:1750] = img[:, 580:1340]
        new[:, 0:1280] = img[:, 640:1920]
        new[:, 1280:2560] = img[:, 640:1920]
        cv2.imwrite(image_paths[idx], new)
    return True