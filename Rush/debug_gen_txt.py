import glob
import re
from pathlib import Path
import math
import itertools

def generate_debug_txt(path='', thickness='5', pause='0', material='1', time='10', intensity='0'):
    txt_name = path.split('\\')[-1] + '.txt'
    txt_path = path + '\\'+ txt_name
    print(txt_path)
    image_paths = Path(path).glob("*[!.txt]")
    file_pattern = re.compile(r'.*?(\d+).*?')
    def get_order(file):
        match = file_pattern.match(Path(file).name)
        if not match:
            return math.inf
        return int(match.groups()[-1])
    image_paths = sorted(image_paths, key=get_order)
    try:
        with open(txt_path, 'w') as f:
            f.write('Layer	File	Thickness	Pause	Material	Speed	Intensity\n')
            layer = 1
            while image_paths:
                image_name = str(image_paths.pop(0)).split('\\')[-1]
                line = str(layer) + '   ' + image_name + '  ' + thickness \
                       + '  ' + pause + '  ' + material + '  ' + time + '  ' + intensity + '\n'
                print(line)
                f.write(line)
                layer += 1
    except FileNotFoundError:
        print("The directory does not exist for creating the text file.")
