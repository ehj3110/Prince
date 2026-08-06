# -*- coding: utf-8 -*-
"""
Ramped Cylinder Generation Module

Calculates layer-by-layer continuous stage speed or power ramps, draws circle image slices 
(forming a cylinder of a specified diameter), and generates the corresponding printer instruction file.
"""

import os
import math
import shutil
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
import cv2
import numpy as np

# Resolution and calibration parameters matching the system
CONE_OUTPUT_WIDTH = 2560
CONE_OUTPUT_HEIGHT = 1600
CONE_UM_PER_PIXEL = 4.005

# Color Palette (Tokyo Night Theme)
COLOR_BG = "#1A1B26"
COLOR_CARD_BG = "#24283B"
COLOR_TEXT = "#A9B1D6"
COLOR_ACCENT = "#7AA2F7"
COLOR_SUCCESS = "#9ECE6A"
COLOR_ERROR = "#F7768E"
COLOR_ENTRY_BG = "#1F2335"
COLOR_ENTRY_FG = "#C0CAF5"
COLOR_BUTTON_BG = "#3D59A1"
COLOR_BUTTON_HOVER = "#41A1F4"


def generate_ramped_cylinder_workflow(
    output_base_folder,
    diameter_um,
    start_val,
    end_val,
    layer_height,
    points,
    replicates,
    led_current,
    step_speed,
    overstep,
    acceleration,
    pause,
    sandwich_speed,
    ramp_mode="speed",
    exposure_time_val=2.0,
    status_callback=None,
    progress_callback=None,
):
    """
    Executes the backend generation logic for the ramped cylinder.
    Generates a folder with PNG circle images and a tab-separated instruction TXT file.
    Supports both "speed" ramping and "power" ramping modes.
    """
    def log(msg, is_error=False):
        if status_callback:
            status_callback(msg, is_error)
        else:
            print(f"[RampedCylinder] {msg}")

    # 1. Validation
    if not output_base_folder or not os.path.isdir(output_base_folder):
        raise ValueError("An output base folder must be selected and must exist.")
    if diameter_um <= 0:
        raise ValueError("Cylinder diameter must be greater than zero.")
    if start_val <= 0 or end_val <= 0:
        raise ValueError("Start and end values must be greater than zero.")
    if layer_height <= 0:
        raise ValueError("Layer height must be greater than zero.")
    if points < 1:
        raise ValueError("Number of unique data points must be at least 1.")
    if replicates < 1:
        raise ValueError("Replicates must be at least 1.")
        
    if ramp_mode == "power":
        if start_val < 1 or start_val > 255 or end_val < 1 or end_val > 255:
            raise ValueError("Power values must be whole numbers between 1 and 255.")
        if exposure_time_val <= 0:
            raise ValueError("Exposure time must be greater than zero for power ramping.")
    else:  # "speed"
        if led_current < 1 or led_current > 255:
            raise ValueError("LED Current / Intensity must be between 1 and 255.")

    # Validate diameter fits printable area
    max_radius_um = diameter_um / 2.0
    max_fit_radius_px = min((CONE_OUTPUT_WIDTH - 4) / 2.0, (CONE_OUTPUT_HEIGHT - 4) / 2.0)
    max_fit_radius_um = max_fit_radius_px * CONE_UM_PER_PIXEL
    if max_radius_um > max_fit_radius_um:
        raise ValueError(
            f"Cylinder diameter {diameter_um:g} μm exceeds the printable field limit. "
            f"Maximum safe diameter is {2.0 * max_fit_radius_um:.1f} μm."
        )

    total_layers = points * replicates
    log(f"Starting generation: {total_layers} total layers ({points} ramp points x {replicates} replicates)")

    # 2. Folder Setup
    if ramp_mode == "power":
        folder_name = f"PowerRampedCylinder_D{diameter_um:g}_P{start_val:g}_P{end_val:g}_N{points}_R{replicates}"
    else:
        folder_name = f"RampedCylinder_D{diameter_um:g}_S{start_val:g}_S{end_val:g}_N{points}_R{replicates}"
        
    folder_path = os.path.join(output_base_folder, folder_name)
    os.makedirs(folder_path, exist_ok=True)
    log(f"Created output folder: {folder_path}")

    # 3. Create Circle Image and Duplicate
    log("Drawing cylinder slice image...")
    draw_radius = max(0, int(round((diameter_um / 2.0) / CONE_UM_PER_PIXEL)))
    
    # Initialize black canvas
    image = np.zeros((CONE_OUTPUT_HEIGHT, CONE_OUTPUT_WIDTH), dtype=np.uint8)
    cv2.circle(
        image,
        (CONE_OUTPUT_WIDTH // 2, CONE_OUTPUT_HEIGHT // 2),
        draw_radius,
        255,
        thickness=-1,
        lineType=cv2.LINE_8,
    )
    
    first_image_path = os.path.join(folder_path, "1.png")
    cv2.imwrite(first_image_path, image)
    
    # Copy file to save encoding overhead
    for i in range(2, total_layers + 1):
        shutil.copy(first_image_path, os.path.join(folder_path, f"{i}.png"))
        if progress_callback:
            progress_callback(i / 2, total_layers)

    log(f"Generated {total_layers} circle PNG slices.")

    # 4. Math: Ramped Array (Speed or Power)
    if points == 1:
        ramp_array = [start_val]
    else:
        ramp_array = np.linspace(start_val, end_val, points)
    layer_ramp_vals = np.repeat(ramp_array, replicates)

    # 5. Write Instruction TXT File
    txt_path = os.path.join(folder_path, f"{folder_name}.txt")
    log(f"Writing instruction file: {txt_path}")
    
    with open(txt_path, "w") as f:
        # Write column headers
        f.write("Layer\tFile\tThickness\tTime\tIntensity\tStep Speed\tOverstep Distance\tAcceleration\tPause\tSandwich Speed\n")
        
        for idx in range(1, total_layers + 1):
            ramp_val = layer_ramp_vals[idx - 1]
            
            if ramp_mode == "power":
                exposure_time = exposure_time_val
                intensity = int(max(1, min(255, round(ramp_val))))
            else:  # "speed"
                speed = ramp_val
                exposure_time = layer_height / speed
                intensity = int(max(1, min(255, round(led_current))))
                
            # Step Speed is left as the default value (step_speed) instead of ramping
            line = (
                f"{idx}\t{idx}.png\t{layer_height:g}\t{exposure_time:.6f}\t"
                f"{intensity}\t{step_speed:g}\t{overstep:g}\t"
                f"{acceleration:g}\t{pause:g}\t{sandwich_speed:g}\n"
            )
            f.write(line)
            if progress_callback:
                progress_callback(total_layers / 2 + idx / 2, total_layers)

    log(f"Instruction file generated successfully: {txt_path}")
    return folder_path


class RampedCylinderWindow:
    def __init__(self, master_window, update_status_callback=None, prince_main_app_ref=None):
        self.master = master_window
        self.update_status = update_status_callback or (lambda msg, err=False: print(msg))
        self.prince_main_app_ref = prince_main_app_ref

        # Create window
        self.window = tk.Toplevel(master_window)
        self.window.title("Ramped Cylinder Generator")
        self.window.geometry("760x600")
        self.window.configure(bg=COLOR_BG)
        self.window.resizable(False, False)

        # Parse defaults from main GUI reference
        self.defaults = self._gather_defaults()

        # Set up variables
        self.var_diameter = tk.StringVar(value="5000.0")
        self.var_ramp_mode = tk.StringVar(value="speed")
        
        # Blank by default to force user input
        self.var_start_val = tk.StringVar(value="")
        self.var_end_val = tk.StringVar(value="")
        
        self.var_points = tk.StringVar(value="10")
        self.var_replicates = tk.StringVar(value="5")
        
        self.var_layer_height = tk.StringVar(value=self.defaults["layer_height"])
        self.var_led_current = tk.StringVar(value=self.defaults["led_current"])
        self.var_exposure_time = tk.StringVar(value=self.defaults["exposure_time"])
        
        # Hidden variables (used invisibly to populate instructions)
        self.var_step_speed = tk.StringVar(value=self.defaults["step_speed"])
        self.var_overstep = tk.StringVar(value=self.defaults["overstep"])
        self.var_acceleration = tk.StringVar(value=self.defaults["acceleration"])
        self.var_pause = tk.StringVar(value=self.defaults["pause"])
        self.var_sandwich_speed = tk.StringVar(value=self.defaults["sandwich_speed"])
        self.var_output_base = tk.StringVar(value=self.defaults["output_base"])

        # Setup GUI Widgets
        self._create_widgets()
        
        # Apply initial state
        self._on_mode_switch()

    def _gather_defaults(self):
        """Pulls print parameter defaults from the main Prince app, if available."""
        defaults = {
            "layer_height": "5.0",
            "led_current": "1.0",
            "exposure_time": "2.0",
            "step_speed": "1000.0",
            "overstep": "500.0",
            "acceleration": "5.0",
            "pause": "0.0",
            "sandwich_speed": "500.0",
            "output_base": os.getcwd(),
        }
        
        ref = self.prince_main_app_ref
        if ref:
            try:
                if hasattr(ref, "t10") and ref.t10.get():
                    defaults["layer_height"] = ref.t10.get().strip()
                if hasattr(ref, "t14") and ref.t14.get():
                    defaults["led_current"] = ref.t14.get().strip()
                if hasattr(ref, "t11") and ref.t11.get():
                    defaults["exposure_time"] = ref.t11.get().strip()
                if hasattr(ref, "t16") and ref.t16.get():
                    defaults["step_speed"] = ref.t16.get().strip()
                if hasattr(ref, "t19") and ref.t19.get():
                    defaults["overstep"] = ref.t19.get().strip()
                if hasattr(ref, "t21") and ref.t21.get():
                    defaults["acceleration"] = ref.t21.get().strip()
                if hasattr(ref, "t17") and ref.t17.get():
                    defaults["pause"] = ref.t17.get().strip()
                if hasattr(ref, "t_sandwich_speed") and ref.t_sandwich_speed.get():
                    defaults["sandwich_speed"] = ref.t_sandwich_speed.get().strip()
            except Exception as e:
                print(f"[RampedCylinder] Error reading parent GUI parameters: {e}")
                
        return defaults

    def _create_widgets(self):
        # 1. Window Header
        header_frame = tk.Frame(self.window, bg=COLOR_BG)
        header_frame.pack(fill=tk.X, padx=20, pady=15)
        
        lbl_title = tk.Label(
            header_frame,
            text="RAMPED CYLINDER GENERATOR",
            font=("Segoe UI", 16, "bold"),
            bg=COLOR_BG,
            fg=COLOR_ACCENT,
        )
        lbl_title.pack(anchor=tk.W)
        
        lbl_desc = tk.Label(
            header_frame,
            text="Creates identical circles of a specified diameter with a continuous-motion speed or power ramp.",
            font=("Segoe UI", 9, "italic"),
            bg=COLOR_BG,
            fg=COLOR_TEXT,
        )
        lbl_desc.pack(anchor=tk.W, pady=(2, 0))

        # 2. Main Parameters Frame
        main_frame = tk.Frame(self.window, bg=COLOR_BG)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

        # Left Column - Ramp & Cylinder Settings
        left_col = tk.LabelFrame(
            main_frame,
            text=" Cylinder & Ramp Parameters ",
            font=("Segoe UI", 10, "bold"),
            bg=COLOR_CARD_BG,
            fg=COLOR_ACCENT,
            bd=1,
            relief=tk.SOLID,
            padx=15,
            pady=15,
        )
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        # Ramp Mode selection row
        mode_frame = tk.Frame(left_col, bg=COLOR_CARD_BG)
        mode_frame.pack(fill=tk.X, pady=(0, 10))
        
        lbl_mode = tk.Label(
            mode_frame,
            text="Ramp Mode:",
            font=("Segoe UI", 9, "bold"),
            bg=COLOR_CARD_BG,
            fg=COLOR_TEXT,
        )
        lbl_mode.pack(side=tk.LEFT, padx=(0, 10))
        
        rb_speed = tk.Radiobutton(
            mode_frame,
            text="Speed Ramping",
            variable=self.var_ramp_mode,
            value="speed",
            command=self._on_mode_switch,
            bg=COLOR_CARD_BG,
            fg=COLOR_TEXT,
            selectcolor=COLOR_CARD_BG,
            activebackground=COLOR_CARD_BG,
            activeforeground=COLOR_ACCENT,
            font=("Segoe UI", 9),
        )
        rb_speed.pack(side=tk.LEFT, padx=(0, 10))
        
        rb_power = tk.Radiobutton(
            mode_frame,
            text="Power Ramping",
            variable=self.var_ramp_mode,
            value="power",
            command=self._on_mode_switch,
            bg=COLOR_CARD_BG,
            fg=COLOR_TEXT,
            selectcolor=COLOR_CARD_BG,
            activebackground=COLOR_CARD_BG,
            activeforeground=COLOR_ACCENT,
            font=("Segoe UI", 9),
        )
        rb_power.pack(side=tk.LEFT)

        self._add_entry_row(left_col, "Cylinder Diameter (μm):", self.var_diameter)
        self.lbl_start, self.ent_start = self._add_entry_row(left_col, "Starting Speed (μm/s):", self.var_start_val)
        self.lbl_end, self.ent_end = self._add_entry_row(left_col, "Ending Speed (μm/s):", self.var_end_val)
        self._add_entry_row(left_col, "Unique Points (N):", self.var_points)
        self._add_entry_row(left_col, "Replicates per Point (R):", self.var_replicates)

        # Right Column - Print Constants (Inherited from Main GUI)
        right_col = tk.LabelFrame(
            main_frame,
            text=" Inherited Print Constants ",
            font=("Segoe UI", 10, "bold"),
            bg=COLOR_CARD_BG,
            fg=COLOR_ACCENT,
            bd=1,
            relief=tk.SOLID,
            padx=15,
            pady=15,
        )
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))

        self.lbl_layer_height, self.ent_layer_height = self._add_entry_row(right_col, "Layer Height (μm):", self.var_layer_height)
        self.lbl_led_current, self.ent_led_current = self._add_entry_row(right_col, "LED Current / Intensity (1-255):", self.var_led_current)
        self.lbl_exposure_time, self.ent_exposure_time = self._add_entry_row(right_col, "Exposure Time (s):", self.var_exposure_time)
        self.lbl_acceleration, self.ent_acceleration = self._add_entry_row(right_col, "Acceleration (mm/s²):", self.var_acceleration)

        # 3. Output Folder Selection
        output_frame = tk.LabelFrame(
            self.window,
            text=" Output Location ",
            font=("Segoe UI", 10, "bold"),
            bg=COLOR_CARD_BG,
            fg=COLOR_ACCENT,
            bd=1,
            relief=tk.SOLID,
            padx=15,
            pady=10,
        )
        output_frame.pack(fill=tk.X, padx=20, pady=(15, 5))

        lbl_folder = tk.Label(
            output_frame,
            text="Output Base Folder:",
            font=("Segoe UI", 9),
            bg=COLOR_CARD_BG,
            fg=COLOR_TEXT,
        )
        lbl_folder.pack(side=tk.LEFT, padx=(0, 5))

        entry_folder = tk.Entry(
            output_frame,
            textvariable=self.var_output_base,
            bg=COLOR_ENTRY_BG,
            fg=COLOR_ENTRY_FG,
            insertbackground=COLOR_ENTRY_FG,
            bd=0,
            highlightthickness=1,
            highlightbackground=COLOR_TEXT,
            highlightcolor=COLOR_ACCENT,
            font=("Segoe UI", 9),
        )
        entry_folder.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, ipady=3)

        btn_browse = tk.Button(
            output_frame,
            text="Browse...",
            command=self._on_browse,
            bg=COLOR_BUTTON_BG,
            fg="#FFFFFF",
            font=("Segoe UI", 9, "bold"),
            activebackground=COLOR_BUTTON_HOVER,
            activeforeground="#FFFFFF",
            bd=0,
            padx=10,
            pady=2,
            cursor="hand2",
        )
        btn_browse.pack(side=tk.RIGHT, padx=(5, 0))

        # 4. Status Logging Window
        status_frame = tk.Frame(self.window, bg=COLOR_BG)
        status_frame.pack(fill=tk.X, padx=20, pady=(10, 5))

        self.txt_status = tk.Text(
            status_frame,
            height=5,
            bg=COLOR_ENTRY_BG,
            fg=COLOR_TEXT,
            bd=0,
            highlightthickness=1,
            highlightbackground=COLOR_TEXT,
            font=("Consolas", 9),
            state=tk.DISABLED,
        )
        self.txt_status.pack(fill=tk.X)

        # 5. Buttons Frame
        btn_frame = tk.Frame(self.window, bg=COLOR_BG)
        btn_frame.pack(fill=tk.X, padx=20, pady=15)

        btn_close = tk.Button(
            btn_frame,
            text="Close",
            command=self._on_close,
            bg="#4B5563",
            fg="#FFFFFF",
            font=("Segoe UI", 10, "bold"),
            activebackground="#6B7280",
            activeforeground="#FFFFFF",
            bd=0,
            padx=20,
            pady=6,
            cursor="hand2",
        )
        btn_close.pack(side=tk.LEFT)

        btn_generate = tk.Button(
            btn_frame,
            text="Generate Ramped Cylinder",
            command=self._on_generate,
            bg=COLOR_BUTTON_BG,
            fg="#FFFFFF",
            font=("Segoe UI", 10, "bold"),
            activebackground=COLOR_BUTTON_HOVER,
            activeforeground="#FFFFFF",
            bd=0,
            padx=20,
            pady=6,
            cursor="hand2",
        )
        btn_generate.pack(side=tk.RIGHT)

    def _add_entry_row(self, parent, label_text, var):
        row = tk.Frame(parent, bg=COLOR_CARD_BG)
        row.pack(fill=tk.X, pady=4)
        
        lbl = tk.Label(
            row,
            text=label_text,
            width=24,
            anchor=tk.W,
            font=("Segoe UI", 9),
            bg=COLOR_CARD_BG,
            fg=COLOR_TEXT,
        )
        lbl.pack(side=tk.LEFT)
        
        ent = tk.Entry(
            row,
            textvariable=var,
            bg=COLOR_ENTRY_BG,
            fg=COLOR_ENTRY_FG,
            insertbackground=COLOR_ENTRY_FG,
            bd=0,
            highlightthickness=1,
            highlightbackground=COLOR_TEXT,
            highlightcolor=COLOR_ACCENT,
            font=("Segoe UI", 9),
        )
        ent.pack(side=tk.RIGHT, fill=tk.X, expand=True, ipady=3)
        return lbl, ent

    def _on_mode_switch(self):
        mode = self.var_ramp_mode.get()
        if mode == "power":
            self.lbl_start.configure(text="Starting Power (1-255):")
            self.lbl_end.configure(text="Ending Power (1-255):")
            
            # Disable LED Current
            self.lbl_led_current.configure(fg="#4B5563")
            self.ent_led_current.configure(state=tk.DISABLED, bg="#1A1B26", fg="#4B5563")
            
            # Enable Exposure Time
            self.lbl_exposure_time.configure(fg=COLOR_TEXT)
            self.ent_exposure_time.configure(state=tk.NORMAL, bg=COLOR_ENTRY_BG, fg=COLOR_ENTRY_FG)
        else:  # "speed"
            self.lbl_start.configure(text="Starting Speed (μm/s):")
            self.lbl_end.configure(text="Ending Speed (μm/s):")
            
            # Enable LED Current
            self.lbl_led_current.configure(fg=COLOR_TEXT)
            self.ent_led_current.configure(state=tk.NORMAL, bg=COLOR_ENTRY_BG, fg=COLOR_ENTRY_FG)
            
            # Disable Exposure Time
            self.lbl_exposure_time.configure(fg="#4B5563")
            self.ent_exposure_time.configure(state=tk.DISABLED, bg="#1A1B26", fg="#4B5563")

    def _on_browse(self):
        dir_path = filedialog.askdirectory(
            parent=self.window,
            title="Select Base Output Folder",
            initialdir=self.var_output_base.get() or os.getcwd(),
        )
        if dir_path:
            self.var_output_base.set(dir_path)

    def log(self, message, is_error=False):
        self.txt_status.configure(state=tk.NORMAL)
        color = COLOR_ERROR if is_error else COLOR_TEXT
        
        # Define tag color if not already defined
        tag_name = "error" if is_error else "normal"
        if tag_name not in self.txt_status.tag_names():
            self.txt_status.tag_config(tag_name, foreground=color)
            
        self.txt_status.insert(tk.END, f"{message}\n", tag_name)
        self.txt_status.see(tk.END)
        self.txt_status.configure(state=tk.DISABLED)
        self.window.update_idletasks()

    def _on_generate(self):
        # Reset Status
        self.txt_status.configure(state=tk.NORMAL)
        self.txt_status.delete("1.0", tk.END)
        self.txt_status.configure(state=tk.DISABLED)

        try:
            # Parse parameters
            diameter_um = float(self.var_diameter.get())
            
            start_val_str = self.var_start_val.get().strip()
            end_val_str = self.var_end_val.get().strip()
            if not start_val_str or not end_val_str:
                raise ValueError("Starting and Ending values must not be empty.")
                
            start_val = float(start_val_str)
            end_val = float(end_val_str)
            points = int(self.var_points.get())
            replicates = int(self.var_replicates.get())
            
            layer_height = float(self.var_layer_height.get())
            ramp_mode = self.var_ramp_mode.get()
            
            if ramp_mode == "power":
                led_current = 1.0
                exposure_time_val = float(self.var_exposure_time.get())
            else:  # "speed"
                led_current = float(self.var_led_current.get())
                exposure_time_val = 0.0
                
            step_speed = float(self.var_step_speed.get())
            overstep = float(self.var_overstep.get())
            acceleration = float(self.var_acceleration.get())
            pause = float(self.var_pause.get())
            sandwich_speed = float(self.var_sandwich_speed.get())
            
            output_base = self.var_output_base.get().strip()

            # Execute Workflow
            folder_path = generate_ramped_cylinder_workflow(
                output_base_folder=output_base,
                diameter_um=diameter_um,
                start_val=start_val,
                end_val=end_val,
                layer_height=layer_height,
                points=points,
                replicates=replicates,
                led_current=led_current,
                step_speed=step_speed,
                overstep=overstep,
                acceleration=acceleration,
                pause=pause,
                sandwich_speed=sandwich_speed,
                ramp_mode=ramp_mode,
                exposure_time_val=exposure_time_val,
                status_callback=lambda msg, err=False: self.log(msg, err),
            )

            messagebox.showinfo(
                "Success",
                f"Ramped Cylinder generation complete!\nSaved to: {folder_path}",
                parent=self.window,
            )
            
            # Update parent status if callback exists
            if self.prince_main_app_ref:
                self.update_status(f"Generated Ramped Cylinder: {os.path.basename(folder_path)}")
                # Optionally set parent's active folder to load the new instructions
                if hasattr(self.prince_main_app_ref, "input_directory_path"):
                    self.prince_main_app_ref.input_directory_path = folder_path
                    self.prince_main_app_ref.input_directory()

        except ValueError as ve:
            self.log(f"Validation Error: {ve}", is_error=True)
            messagebox.showerror("Error", f"Invalid input parameters:\n{ve}", parent=self.window)
        except Exception as e:
            self.log(f"Unexpected Error: {e}", is_error=True)
            messagebox.showerror("Error", f"An unexpected error occurred:\n{e}", parent=self.window)

    def _on_close(self):
        self.window.grab_release()
        self.window.destroy()
