import logging
import socket
import re
import math  # Ensure math is imported
from pathlib import Path  # Ensure Path is imported
import traceback  # For more detailed error printing
import os  # Ensure os is imported
from support_modules.DebugSupport import debug_print


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
    POWER_SCALE_FACTOR = 2.72

    def __init__(self):
        self.image_list = []
        self.position_list = []
        self.time_list = []
        self.thickness_list = []
        self.step_speed_list = []
        self.step_type_list = []
        self.pause_list = []
        self.intensity_list = []
        debug_print("Application instance created.")

    @staticmethod
    def _power_from_speed(speed_um_s):
        """Compute calibrated layer power from speed using updated polynomial scaling."""
        x = float(speed_um_s)
        y = (-1.939507e-6 * x * x) + (4.869025e-3 * x) + 7.617950e-3
        return y * Application.POWER_SCALE_FACTOR

    @staticmethod
    def _safe_exposure_from_speed(thickness_um, speed_um_s):
        """Convert speed input to exposure time while guarding against zero/negative speeds."""
        t_um = float(thickness_um)
        v_um_s = float(speed_um_s)
        if v_um_s <= 1e-9:
            return 0.0
        return t_um / v_um_s

    def set_image_directory(self, path=''):
        """
        Reads the instruction text file and extracts image file paths and printing parameters.
        
        Segmented Mode format: 9 columns (Layer, File, Thickness, Time, Intensity, Step Speed, Acceleration, Pause, Sandwich Speed)

        Returns:
            image_list (list): List of image file paths.
            exposure_time_list (list): List of exposure times per layer.
            thickness_list (list): List of thickness values per layer.
            step_speed_list (list): List of step speeds per layer.
            step_type_list (list): List of acceleration values per layer.
            pause_list (list): List of pause times per layer.
            intensity_list (list): List of intensity values per layer.
            sandwich_speed_list (list): List of sandwich speeds per layer.
        """

        debug_print(f"Application.set_image_directory called with path: '{path}'")

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
        step_type_list = []
        pause_list = []
        intensity_list = []
        sandwich_speed_list = []

        # Process each line (excluding header)
        for line in lines_full[1:]:
            elements = line.split("\t")  # Use tab as the separator

            if len(elements) < 9:
                raise ValueError(f"Incorrect format in line: {line}. Expected at least 9 columns, got {len(elements)}.")

            # Extract parameters from columns
            count = elements[0]  # Layer number
            image_path = elements[1]  # Image filename
            thickness = elements[2]  # Layer thickness
            exposure_time = elements[3]  # Exposure time
            intensity = elements[4]  # Intensity level
            step_speed = elements[5]  # Step speed

            # New format is 9 columns without overstep.
            # Backward compatibility: accept legacy 10-column files and ignore overstep column.
            if len(elements) >= 10:
                step_type = elements[7]  # Acceleration
                pause = elements[8]  # Pause time
                sandwich_speed = elements[9]  # Sandwich speed
            else:
                step_type = elements[6]  # Acceleration
                pause = elements[7]  # Pause time
                sandwich_speed = elements[8]  # Sandwich speed

            # Append extracted values to respective lists
            image_list.append(Path(path) / image_path)
            exposure_time_list.append(float(exposure_time))
            thickness_list.append(float(thickness))
            step_speed_list.append(float(step_speed))
            step_type_list.append(float(step_type))
            pause_list.append(float(pause))
            intensity_list.append(float(intensity))
            sandwich_speed_list.append(float(sandwich_speed))

        # Right before the final return statement in set_image_directory:
        debug_print(f"Application.set_image_directory FINISHING. Image list length: {len(image_list)}")
        # Segmented Mode return: 9 values (includes step_type and sandwich_speed)
        return (
            image_list, exposure_time_list, thickness_list,
            step_speed_list, step_type_list,
            pause_list, intensity_list,
            sandwich_speed_list
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
                              step_speed='100', step_type='500', 
                              pause='0', sandwich_speed='100'):
        """
        Generates a simplified instruction text file for Segmented Mode.
        Format: 9 columns (Layer, File, Thickness, Time, Intensity, Step Speed, Acceleration, Pause, Sandwich Speed)
        step_type parameter represents acceleration (µm/s²).

        'time' is interpreted as exposure speed (µm/s) for non-base layers.
        Exposure time is derived as thickness/speed while preserving the base-layer exposure override.
        Intensity is computed from the calibrated speed->power polynomial.
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
                    f.write('Layer\tFile\tThickness\tTime\tIntensity\tStep Speed\tAcceleration\tPause\tSandwich Speed\n')
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
                    f.write('Layer\tFile\tThickness\tTime\tIntensity\tStep Speed\tAcceleration\tPause\tSandwich Speed\n')
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
            non_base_speed_um_s = float(time)
            layer_thickness_um = float(thickness)
            calibrated_power = self._power_from_speed(non_base_speed_um_s)
            calibrated_intensity = int(round(max(0.0, min(255.0, calibrated_power))))

            with open(txt_path, 'w') as f:
                f.write('Layer\tFile\tThickness\tTime\tIntensity\tStep Speed\tAcceleration\tPause\tSandwich Speed\n')
                layer = 1

                for img_path_obj in image_paths_sorted:  # Iterate through sorted Path objects
                    image_name = img_path_obj.name  # Get filename from Path object

                    if layer == 1:
                        current_exposure_time = float(base)
                    else:
                        current_exposure_time = self._safe_exposure_from_speed(layer_thickness_um, non_base_speed_um_s)

                    line = f"{str(layer)}\t{str(image_name)}\t{str(thickness)}\t{str(current_exposure_time)}\t{str(calibrated_intensity)}\t{str(step_speed)}\t{str(step_type)}\t{str(pause)}\t{str(sandwich_speed)}\n"
                    f.write(line)
                    layer += 1

            dosage_mj_per_um = 0.0 if non_base_speed_um_s <= 1e-9 else calibrated_power / non_base_speed_um_s
            print(
                f"Instruction file generated: {txt_path} with {layer - 1} layers. "
                f"Calibrated power={calibrated_power:.4f}, intensity={calibrated_intensity}, dosage={dosage_mj_per_um:.6f} mJ/um"
            )
        except Exception as e:
            print(f"An unexpected error occurred during instruction file generation for {txt_path}: {e}")
            traceback.print_exc()  # Print full traceback for debugging

    def get_total_layers(self):
        """
        Returns the total number of layers based on the loaded image list.
        """
        debug_print(f"Application.get_total_layers called. Image list length: {len(self.image_list)}")
        return len(self.image_list)