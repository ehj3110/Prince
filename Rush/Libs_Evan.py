import logging
import socket
from pathlib import Path
import math
import re


class Ensemble:
    def __init__(self, ip, port):
        self._ip = ip
        self._port = port
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        logging.info('Ensemble instantiated.')

    def connect(self):
        try:
            self._socket.connect((self._ip, self._port))
            logging.info('Connected')
        except ConnectionRefusedError:
            logging.error("Unble to connect.")

    def write_read(self, command):
        EOS_CHAR = '\n'
        ACK_CHAR = '%'
        NAK_CHAR = '!'
        FAULT_CHAR = '#'
        TIMEOUT_CHAR = '$'

        if EOS_CHAR not in command:
            command = ''.join((command, EOS_CHAR))

        self._socket.send(command.encode())
        read = self._socket.recv(4096).decode().strip()
        code, response = read[0], read[1:]
        if code != ACK_CHAR:
            logging.error(code, response)
            logging.error("Error from write_read().")
        return response

    def home(self):
        return None

    def move(self, x_pos, y_pos, z_pos):
        return None

    def get_positions(self):
        return None

    def close(self):
        self._socket.close()
        logging.info("Disonnected")

class Application():
    def __init__(self):
        self.init = None

    def set_image_directory(self, path=''):
        '''
        Layer	File	Thickness	Pause	Material	time	Intensity
        '''
        txt_name = path.split('\\')[-1] + '.txt'
        txt_path = Path(path).glob(txt_name)
        image_list = []
        exposure_time_list = []
        thickness_list = []
        with open(next(txt_path)) as f:
            lines = f.readlines()
            lines_full = [line for line in lines if line.strip() != ""]
            for line in lines_full[1:]:
                elements = line.split()
                count, image_path, exposure_time, thickness = elements[0], ' '.join(elements[1:-5]), elements[-2], \
                                                              elements[-5]
                exposure_time_list.append(float(exposure_time))
                thickness_list.append(float(thickness))
                image_list.append(path + '\\' + image_path)
        #             self.images = iter(map(ImageTk.PhotoImage, map(Image.open, iter(image_list))))
        #             self.duration_ms_list = iter(iter(exposure_time_list))
        return image_list, exposure_time_list, thickness_list

    def generate_debug_txt(self, path='', thickness='5', pause='0', material='1', time='1', intensity='0', base = '60'):
        txt_name = path.split('\\')[-1] + '.txt'
        txt_path = path + '\\' + txt_name
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
                #f.write('Layer	File	Thickness	Pause	Material	Time	Intensity\n')
                layer = 1
                while image_paths:
                    image_name = str(image_paths.pop(0)).split('\\')[-1]
                    if layer > 1:
                        line = image_name + '\n'
                    else:
                        line = image_name + '\n'
                    f.write(line)
                    layer += 1
        except FileNotFoundError:
            print("The directory does not exist for creating the text file.")
