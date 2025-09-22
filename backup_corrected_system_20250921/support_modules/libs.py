import logging
import socket
import re
import math  # Ensure math is imported
from pathlib import Path  # Ensure Path is imported
import traceback  # For more detailed error printing
import os  # Ensure os is imported


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
        self.image_list = []
        self.position_list = []
        self.time_list = []
        self.thickness_list = []
        self.step_speed_list = []
        self.overstep_distance_list = []
        self.step_type_list = []
        self.pause_list = []
        self.intensity_list = []
        print("DEBUG: Application instance created.")  # Add this

    def set_image_directory(self, path=''):
        """
        Reads the instruction text file and extracts image file paths and printing parameters.

        Returns:
            image_list (list): List of image file paths.
            exposure_time_list (list): List of exposure times per layer.
            thickness_list (list): List of thickness values per layer.
            step_speed_list (list): List of step speeds per layer.
            overstep_distance_list (list): List of overstep distances per layer.
            step_type_list (list): List of step types per layer.
            pause_list (list): List of pause times per layer.
            intensity_list (list): List of intensity values per layer.
        """

        print(f"DEBUG: Application.set_image_directory called with path: '{path}'")  # Add this

        # Generate the expected text file name based on the directory
        txt_name = path.split('\\')[-1] + '.txt'
        txt_path = list(Path(path).glob(txt_name))  # Convert iterator to list

        # Check if the file exists
        if not txt_path:
            raise FileNotFoundError(f"Instruction file '{txt_name}' not found in {path}")

        # Open the first matching file
        with open(txt_path[0], 'r') as f:
            lines = f.readlines()

        # Remove empty lines and extract only non-empty ones
        lines_full = [line.strip() for line in lines if line.strip() != ""]

        # Initialize storage lists
        image_list = []
        exposure_time_list = []
        thickness_list = []
        step_speed_list = []
        overstep_distance_list = []
        step_type_list = []
        pause_list = []
        intensity_list = []

        # Process each line (excluding header)
        for line in lines_full[1:]:
            elements = line.split("\t")  # Use tab as the separator

            if len(elements) < 9:
                raise ValueError(f"Incorrect format in line: {line}")

            # Extract parameters from the appropriate columns
            count = elements[0]  # Layer number
            image_path = elements[1]  # Image filename
            thickness = elements[2]  # Layer thickness
            exposure_time = elements[3]  # Exposure time
            intensity = elements[4]  # Intensity level
            step_speed = elements[5]  # Step speed
            overstep_distance = elements[6]  # Overstep distance
            step_type = elements[7]  # Step type
            pause = elements[8]  # Pause time

            # Append extracted values to respective lists
            image_list.append(Path(path) / image_path)
            exposure_time_list.append(float(exposure_time))
            thickness_list.append(float(thickness))
            step_speed_list.append(float(step_speed))
            overstep_distance_list.append(float(overstep_distance))
            step_type_list.append(int(step_type))
            pause_list.append(float(pause))
            intensity_list.append(float(intensity))

        # Right before the final return statement in set_image_directory:
        print(f"DEBUG: Application.set_image_directory FINISHING. Image list length: {len(image_list)}")  # Add this
        return (
            image_list, exposure_time_list, thickness_list,
            step_speed_list, overstep_distance_list, step_type_list,
            pause_list, intensity_list
        )

    def generate_debug_txt(self, path='', thickness='5', pause='0', material='1', time='1', intensity='0', base='60'):
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
                f.write('Layer	File	Thickness	Pause	Material	Speed	Intensity\n')
                layer = 1
                while image_paths:
                    image_name = str(image_paths.pop(0)).split('\\')[-1]
                    if layer > 1:
                        line = str(layer) + '       ' + image_name + '      ' + thickness \
                               + '              ' + pause + '       ' + material + '        ' + time + '        ' + intensity + '\n'
                    else:
                        line = str(layer) + '       ' + image_name + '      ' + thickness \
                               + '              ' + pause + '       ' + material + '        ' + base + '        ' + intensity + '\n'
                    f.write(line)
                    layer += 1
        except FileNotFoundError:
            print("The directory does not exist for creating the text file.")

    def generate_instructions(self, path='', thickness='5', base='60', time='1', intensity='0',
                              step_speed='100', overstep_distance='0.1', step_type='0', pause='0'):
        """
        Generates an instruction text file for the 3D printer.
        It lists image files found in the 'path' directory, excluding any 'autologs' subdirectory.
        """

        # Generate the text file name based on the folder name
        txt_name = path.split('\\')[-1] + '.txt'
        txt_path = os.path.join(path, txt_name)  # Use os.path.join for robustness

        collected_image_paths = []
        # Define common image extensions (case-insensitive)
        image_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff']

        path_obj = Path(path)
        if not path_obj.is_dir():
            print(f"Error: Provided path is not a directory or does not exist: {path}")
            try:
                with open(txt_path, 'w') as f:
                    f.write('Layer\tFile\tThickness\tTime\tIntensity\tStep Speed\tOverstep Distance\tStep Type\tPause\n')
                    f.write("0\tERROR_INVALID_PATH\t0\t0\t0\t0\t0\t0\t0\n")  # Indicate error
                print(f"Generated empty/error instruction file: {txt_path}")
            except Exception as e_write:
                print(f"Could not write to instruction file {txt_path}: {e_write}")
            return

        for item in path_obj.iterdir():
            if item.is_dir():
                if item.name.lower() == "autologs":  # Case-insensitive check for autologs
                    print(f"Skipping 'autologs' directory: {item}")
                    continue
                # If you wanted to recursively search other subdirectories, you'd add logic here.
                # For now, we only process files directly in 'path'.
            elif item.is_file():
                if item.suffix.lower() in image_extensions:  # Check for image extensions
                    collected_image_paths.append(item)
                # Silently ignore other files like .txt (which is good) or other non-image files.

        if not collected_image_paths:
            print(f"No suitable image files found in '{path}' (after excluding 'autologs' and non-image files).")
            try:
                with open(txt_path, 'w') as f:
                    f.write('Layer\tFile\tThickness\tTime\tIntensity\tStep Speed\tOverstep Distance\tStep Type\tPause\n')
                    f.write("0\tNO_IMAGES_FOUND\t0\t0\t0\t0\t0\t0\t0\n")  # Indicate no images
                print(f"Generated instruction file with no images: {txt_path}")
            except Exception as e_write:
                print(f"Could not write to instruction file {txt_path}: {e_write}")
            return

        # Regular expression pattern to extract numbers from filenames for sorting
        file_pattern = re.compile(r'.*?(\d+).*?')

        def get_order(file_path_obj):  # Expects a Path object
            """
            Extracts the numeric part of the filename to determine the order of layers.
            If no number is found, it returns infinity (places file at the end).
            """
            match = file_pattern.match(file_path_obj.name)  # Use .name for Path object
            if not match:
                return math.inf
            return int(match.groups()[-1])

        # Sort the image paths based on their numeric order
        image_paths_sorted = sorted(collected_image_paths, key=get_order)

        try:
            with open(txt_path, 'w') as f:
                f.write('Layer\tFile\tThickness\tTime\tIntensity\tStep Speed\tOverstep Distance\tStep Type\tPause\n')
                layer = 1

                for img_path_obj in image_paths_sorted:  # Iterate through sorted Path objects
                    image_name = img_path_obj.name  # Get filename from Path object

                    current_exposure_time = base if layer == 1 else time

                    line = f"{str(layer)}\t{str(image_name)}\t{str(thickness)}\t{str(current_exposure_time)}\t{str(intensity)}\t{str(step_speed)}\t{str(overstep_distance)}\t{str(step_type)}\t{str(pause)}\n"
                    f.write(line)
                    layer += 1
            print(f"Instruction file generated: {txt_path} with {layer - 1} layers.")
        except Exception as e:
            print(f"An unexpected error occurred during instruction file generation for {txt_path}: {e}")
            traceback.print_exc()  # Print full traceback for debugging

    def get_total_layers(self):
        """
        Returns the total number of layers based on the loaded image list.
        """
        print(f"DEBUG: Application.get_total_layers called. Image list length: {len(self.image_list)}")  # Add this
        return len(self.image_list)