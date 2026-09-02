# -*- coding: utf-8 -*-
"""
Ramped Cylinder Generation Module

Calculates layer-by-layer continuous stage speed or power ramps, draws circle image slices 
(forming a cylinder or expanding cone of a specified diameter), and generates the corresponding printer instruction file.
Supports linear and logarithmic (geometric) point spacing for both print parameters and geometry diameters.
"""

import os
import math
import shutil
import threading
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
COLOR_DISABLED_BG = "#141622"
COLOR_DISABLED_FG = "#565F89"


def compute_dosage_coupled_power(speed, control_speed, control_power):
    """Return power needed to hold dosage constant at the control point.

    Dosage proportionality:  power * (layer_height / speed) = const
    => power = control_power * (speed / control_speed)
    """
    return control_power * (speed / control_speed)


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
    # Dosage-coupled parameters (only used when ramp_mode == dosage_coupled)
    control_speed=None,
    control_power=None,
    # Cone & Base Layer options
    ending_diameter_um=None,  # If provided and != diameter_um, generates a cone profile
    base_diameter_um=None,    # If provided, sets Layer 1 (base layer) diameter. Defaults to diameter_um.
    # Spacing options
    param_spacing="linear",   # "linear" or "log"
    diameter_spacing="linear", # "linear" or "log"
    status_callback=None,
    progress_callback=None,
):
    """
    Executes the backend generation logic for the ramped cylinder / cone.
    Generates a folder with PNG circle images and a tab-separated instruction TXT file.
    Supports "speed" ramping, "power" ramping, and "dosage_coupled" (constant dosage) modes.
    Supports constant cylinder geometries or expanding cone geometries with linear or logarithmic spacing.
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
        raise ValueError("Starting diameter must be greater than zero.")
    if start_val <= 0 or end_val <= 0:
        raise ValueError("Start and end values must be greater than zero.")
    if layer_height <= 0:
        raise ValueError("Layer height must be greater than zero.")
    if points < 1:
        raise ValueError("Number of unique data points must be at least 1.")
    if replicates < 1:
        raise ValueError("Replicates must be at least 1.")
        
    if base_diameter_um is None:
        base_diameter_um = diameter_um
    if base_diameter_um <= 0:
        raise ValueError("Base layer diameter must be greater than zero.")

    is_cone = (ending_diameter_um is not None and ending_diameter_um != diameter_um)
    if is_cone and ending_diameter_um <= 0:
        raise ValueError("Ending diameter must be greater than zero for cone generation.")

    if param_spacing == "log":
        if start_val <= 0 or end_val <= 0:
            raise ValueError("Start and end values must be greater than zero for logarithmic parameter spacing.")
    if is_cone and diameter_spacing == "log":
        if diameter_um <= 0 or ending_diameter_um <= 0:
            raise ValueError("Starting and ending diameters must be greater than zero for logarithmic diameter spacing.")

    if ramp_mode == "power":
        if start_val < 1 or start_val > 255 or end_val < 1 or end_val > 255:
            raise ValueError("Power values must be whole numbers between 1 and 255.")
        if exposure_time_val <= 0:
            raise ValueError("Exposure time must be greater than zero for power ramping.")
    elif ramp_mode == "dosage_coupled":
        if control_speed is None or control_power is None:
            raise ValueError(
                "control_speed and control_power must be provided for dosage-coupled ramping."
            )
        if control_speed <= 0:
            raise ValueError("Control Speed must be greater than zero.")
        if not (1 <= control_power <= 255):
            raise ValueError("Control Power must be between 1 and 255.")

    else:  # speed
        if led_current < 1 or led_current > 255:
            raise ValueError("LED Current / Intensity must be between 1 and 255.")

    if exposure_time_val <= 0:
        raise ValueError("Base exposure time must be greater than zero.")

    # Validate all diameters fit printable area
    max_diameter_um = max(diameter_um, base_diameter_um)
    if is_cone:
        max_diameter_um = max(max_diameter_um, ending_diameter_um)

    max_radius_um = max_diameter_um / 2.0
    max_fit_radius_px = min((CONE_OUTPUT_WIDTH - 4) / 2.0, (CONE_OUTPUT_HEIGHT - 4) / 2.0)
    max_fit_radius_um = max_fit_radius_px * CONE_UM_PER_PIXEL
    if max_radius_um > max_fit_radius_um:
        shape_label = "Cone" if is_cone else "Cylinder"
        raise ValueError(
            f"{shape_label} maximum diameter {max_diameter_um:g} μm exceeds printable field limit. "
            f"Maximum safe diameter is {2.0 * max_fit_radius_um:.1f} μm."
        )

    total_ramp_layers = points * replicates
    total_layers = 1 + total_ramp_layers
    shape_title = "Cone" if is_cone else "Cylinder"
    log(f"Starting generation: {total_layers} total layers (1 base layer + {points} ramp points x {replicates} replicates)")

    # 2. Folder Setup
    p_log = "Log" if param_spacing == "log" else ""
    d_log = "Log" if (is_cone and diameter_spacing == "log") else ""

    if is_cone:
        if ramp_mode == "power":
            folder_name = f"{p_log}PowerRamped{d_log}Cone_D{diameter_um:g}_De{ending_diameter_um:g}_P{start_val:g}_P{end_val:g}_N{points}_R{replicates}"
        elif ramp_mode == "dosage_coupled":
            folder_name = (
                f"{p_log}DosageCoupled{d_log}Cone_D{diameter_um:g}_De{ending_diameter_um:g}"
                f"_S{start_val:g}_S{end_val:g}"
                f"_CP{control_power:g}_CS{control_speed:g}"
                f"_N{points}_R{replicates}"
            )
        else:
            folder_name = f"{p_log}Ramped{d_log}Cone_D{diameter_um:g}_De{ending_diameter_um:g}_S{start_val:g}_S{end_val:g}_N{points}_R{replicates}"
    else:
        if ramp_mode == "power":
            folder_name = f"{p_log}PowerRampedCylinder_D{diameter_um:g}_P{start_val:g}_P{end_val:g}_N{points}_R{replicates}"
        elif ramp_mode == "dosage_coupled":
            folder_name = (
                f"{p_log}DosageCoupledCylinder_D{diameter_um:g}"
                f"_S{start_val:g}_S{end_val:g}"
                f"_CP{control_power:g}_CS{control_speed:g}"
                f"_N{points}_R{replicates}"
            )
        else:
            folder_name = f"{p_log}RampedCylinder_D{diameter_um:g}_S{start_val:g}_S{end_val:g}_N{points}_R{replicates}"
        
    folder_path = os.path.join(output_base_folder, folder_name)
    os.makedirs(folder_path, exist_ok=True)
    log(f"Created output folder: {folder_path}")

    # 3. Create Circle Images
    log(f"Drawing {shape_title.lower()} slice images...")
    
    slice_diameters = [base_diameter_um]
    if is_cone:
        if total_ramp_layers == 1:
            cone_dias = [diameter_um]
        else:
            if diameter_spacing == "log":
                cone_dias = np.geomspace(diameter_um, ending_diameter_um, total_ramp_layers)
            else:
                cone_dias = np.linspace(diameter_um, ending_diameter_um, total_ramp_layers)
        slice_diameters.extend(cone_dias)
    else:
        slice_diameters.extend([diameter_um] * total_ramp_layers)

    def make_circle_image(dia_um):
        draw_radius = max(0, int(round((dia_um / 2.0) / CONE_UM_PER_PIXEL)))
        img = np.zeros((CONE_OUTPUT_HEIGHT, CONE_OUTPUT_WIDTH), dtype=np.uint8)
        cv2.circle(
            img,
            (CONE_OUTPUT_WIDTH // 2, CONE_OUTPUT_HEIGHT // 2),
            draw_radius,
            255,
            thickness=-1,
            lineType=cv2.LINE_8,
        )
        return img

    all_identical = all(d == slice_diameters[0] for d in slice_diameters)
    
    if all_identical:
        first_img = make_circle_image(slice_diameters[0])
        first_image_path = os.path.join(folder_path, "1.png")
        cv2.imwrite(first_image_path, first_img)
        for i in range(2, total_layers + 1):
            shutil.copy(first_image_path, os.path.join(folder_path, f"{i}.png"))
            if progress_callback:
                progress_callback(i / 2, total_layers)
    else:
        for idx_1based, d in enumerate(slice_diameters, start=1):
            img = make_circle_image(d)
            img_path = os.path.join(folder_path, f"{idx_1based}.png")
            cv2.imwrite(img_path, img)
            if progress_callback:
                progress_callback(idx_1based / 2, total_layers)

    log(f"Generated {total_layers} circle PNG slices (1 base layer + {total_ramp_layers} ramped layers).")

    # 4. Math: Ramped Array (Speed or Power)
    if points == 1:
        ramp_array = [start_val]
    else:
        if param_spacing == "log":
            ramp_array = np.geomspace(start_val, end_val, points)
        else:
            ramp_array = np.linspace(start_val, end_val, points)
    layer_ramp_vals = np.repeat(ramp_array, replicates)

    # 5. Write Instruction TXT File
    txt_path = os.path.join(folder_path, f"{folder_name}.txt")
    log(f"Writing instruction file: {txt_path}")
    
    clamped_layers = []
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(
            "Layer\tFile\tThickness\tTime\tIntensity\tStep Speed\t"
            "Overstep Distance\tAcceleration\tPause\tSandwich Speed\n"
        )

        # Layer 1: Base Layer (Cure time equals inherited base exposure time from GUI)
        if ramp_mode == "power":
            base_intensity = int(max(1, min(255, round(start_val))))
        elif ramp_mode == "dosage_coupled":
            base_intensity = int(max(1, min(255, round(control_power))))
        else:
            base_intensity = int(max(1, min(255, round(led_current))))

        base_line = (
            f"1\t1.png\t{layer_height:g}\t{exposure_time_val:.6f}\t"
            f"{base_intensity}\t{step_speed:g}\t{overstep:g}\t"
            f"{acceleration:g}\t{pause:g}\t{sandwich_speed:g}\n"
        )
        f.write(base_line)

        # Layers 2..N: Ramped Layers
        for ramp_idx in range(1, total_ramp_layers + 1):
            idx = ramp_idx + 1
            ramp_val = layer_ramp_vals[ramp_idx - 1]

            if ramp_mode == "power":
                exposure_time = exposure_time_val
                intensity = int(max(1, min(255, round(ramp_val))))
                row_step_speed = step_speed

            elif ramp_mode == "dosage_coupled":
                speed = ramp_val
                exposure_time = layer_height / speed
                raw_power = compute_dosage_coupled_power(speed, control_speed, control_power)
                clamped = max(1.0, min(255.0, raw_power))
                intensity = int(round(clamped))
                if abs(raw_power - clamped) > 0.49:
                    clamped_layers.append((idx, speed, raw_power, intensity))
                row_step_speed = step_speed

            else:  # speed
                speed = ramp_val
                exposure_time = layer_height / speed
                intensity = int(max(1, min(255, round(led_current))))
                row_step_speed = step_speed

            line = (
                f"{idx}\t{idx}.png\t{layer_height:g}\t{exposure_time:.6f}\t"
                f"{intensity}\t{row_step_speed:g}\t{overstep:g}\t"
                f"{acceleration:g}\t{pause:g}\t{sandwich_speed:g}\n"
            )
            f.write(line)
            if progress_callback:
                progress_callback(total_layers / 2 + idx / 2, total_layers)

    # Emit clamping warnings
    warnings = []
    if clamped_layers:
        warn_msg = (
            f"WARNING: {len(clamped_layers)} layer(s) required power outside [1,255] "
            f"and were clamped. Constant dosage cannot be maintained for those layers.\n"
            f"  First affected: Layer {clamped_layers[0][0]} "
            f"(speed={clamped_layers[0][1]:g} um/s, "
            f"ideal power={clamped_layers[0][2]:.1f}, clamped to {clamped_layers[0][3]})."
        )
        log(warn_msg, is_error=True)
        warnings.append(warn_msg)

    log(f"Instruction file generated successfully: {txt_path}")
    return folder_path, warnings


class RampedCylinderWindow:
    def __init__(self, master_window, update_status_callback=None, prince_main_app_ref=None):
        self.master = master_window
        self.update_status = update_status_callback or (lambda msg, err=False: print(msg))
        self.prince_main_app_ref = prince_main_app_ref

        # Create window
        self.window = tk.Toplevel(master_window)
        self.window.title("Ramped Cylinder Generator")
        self.window.geometry("960x640")
        self.window.minsize(820, 500)
        self.window.configure(bg=COLOR_BG)
        self.window.resizable(True, True)

        # Parse defaults from main GUI reference
        self.defaults = self._gather_defaults()

        # Set up variables
        self.var_workflow_mode = tk.StringVar(value="cylinder_ramp")  # "cylinder_ramp", "cone_constant", "combined"
        self.var_diameter = tk.StringVar(value="5000.0")
        self.var_ending_diameter = tk.StringVar(value="")
        self.var_base_diameter = tk.StringVar(value="")
        self.var_diameter_spacing = tk.StringVar(value="linear")  # "linear" or "log"
        self.var_ramp_mode = tk.StringVar(value="speed")
        self.var_param_spacing = tk.StringVar(value="linear")     # "linear" or "log"
        
        # Blank by default to force user input
        self.var_start_val = tk.StringVar(value="")
        self.var_end_val = tk.StringVar(value="")

        # Dosage-coupled anchor
        self.var_control_speed = tk.StringVar(value="")
        self.var_control_power = tk.StringVar(value="")
        
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
        self._update_ui_state()

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
                # Check base exposure time (t11_2) first, fallback to t11 if unavailable
                if hasattr(ref, "t11_2") and ref.t11_2.get():
                    defaults["exposure_time"] = ref.t11_2.get().strip()
                elif hasattr(ref, "t11") and ref.t11.get():
                    defaults["exposure_time"] = ref.t11.get().strip()
                if hasattr(ref, "t16") and ref.t16.get():
                    defaults["step_speed"] = ref.t16.get().strip()
                if hasattr(ref, "t19") and ref.t19.get():
                    defaults["overstep"] = ref.t19.get().strip()
                elif hasattr(ref, "default_overstep_microns"):
                    defaults["overstep"] = str(ref.default_overstep_microns)
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
        header_frame.pack(fill=tk.X, padx=16, pady=(10, 6))
        
        self.lbl_title = tk.Label(
            header_frame,
            text="RAMPED CYLINDER / CONE GENERATOR",
            font=("Segoe UI", 14, "bold"),
            bg=COLOR_BG,
            fg=COLOR_ACCENT,
        )
        self.lbl_title.pack(anchor=tk.W)
        
        self.lbl_desc = tk.Label(
            header_frame,
            text="Creates circular or expanding cone slices with a continuous-motion speed or power ramp.",
            font=("Segoe UI", 8, "italic"),
            bg=COLOR_BG,
            fg=COLOR_TEXT,
        )
        self.lbl_desc.pack(anchor=tk.W, pady=(1, 0))

        # 2. TOP ACTION CARD: Output Location & Action Controls (At the top!)
        top_action_card = tk.LabelFrame(
            self.window,
            text=" Output Location & Generation ",
            font=("Segoe UI", 9, "bold"),
            bg=COLOR_CARD_BG,
            fg=COLOR_ACCENT,
            bd=1,
            relief=tk.SOLID,
            padx=12,
            pady=6,
        )
        top_action_card.pack(fill=tk.X, padx=16, pady=(0, 6))

        top_row = tk.Frame(top_action_card, bg=COLOR_CARD_BG)
        top_row.pack(fill=tk.X)

        lbl_folder = tk.Label(
            top_row,
            text="Output Folder:",
            font=("Segoe UI", 9),
            bg=COLOR_CARD_BG,
            fg=COLOR_TEXT,
        )
        lbl_folder.pack(side=tk.LEFT, padx=(0, 6))

        entry_folder = tk.Entry(
            top_row,
            textvariable=self.var_output_base,
            bg=COLOR_ENTRY_BG,
            fg=COLOR_ENTRY_FG,
            insertbackground=COLOR_ENTRY_FG,
            disabledbackground=COLOR_DISABLED_BG,
            disabledforeground=COLOR_DISABLED_FG,
            bd=0,
            highlightthickness=1,
            highlightbackground=COLOR_TEXT,
            highlightcolor=COLOR_ACCENT,
            font=("Segoe UI", 9),
        )
        entry_folder.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4, ipady=3)

        btn_browse = tk.Button(
            top_row,
            text="Browse...",
            command=self._on_browse,
            bg=COLOR_BUTTON_BG,
            fg="#FFFFFF",
            font=("Segoe UI", 9, "bold"),
            activebackground=COLOR_BUTTON_HOVER,
            activeforeground="#FFFFFF",
            bd=0,
            padx=10,
            pady=3,
            cursor="hand2",
        )
        btn_browse.pack(side=tk.LEFT, padx=(4, 12))

        self.btn_generate = tk.Button(
            top_row,
            text="Generate Ramped Cylinder",
            command=self._on_generate,
            bg=COLOR_BUTTON_BG,
            fg="#FFFFFF",
            font=("Segoe UI", 9, "bold"),
            activebackground=COLOR_BUTTON_HOVER,
            activeforeground="#FFFFFF",
            bd=0,
            padx=14,
            pady=4,
            cursor="hand2",
        )
        self.btn_generate.pack(side=tk.RIGHT)

        btn_close = tk.Button(
            top_row,
            text="Close",
            command=self._on_close,
            bg="#4B5563",
            fg="#FFFFFF",
            font=("Segoe UI", 9, "bold"),
            activebackground="#6B7280",
            activeforeground="#FFFFFF",
            bd=0,
            padx=10,
            pady=4,
            cursor="hand2",
        )
        btn_close.pack(side=tk.RIGHT, padx=(0, 8))

        # 3. Main Parameters Frame (2 Columns)
        main_frame = tk.Frame(self.window, bg=COLOR_BG)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=2)

        # Left Column - Dynamic Configurations Container
        left_col = tk.Frame(main_frame, bg=COLOR_BG)
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        # 3A. Workflow Selection Card
        wf_frame = tk.LabelFrame(
            left_col,
            text=" Workflow Selection ",
            font=("Segoe UI", 9, "bold"),
            bg=COLOR_CARD_BG,
            fg=COLOR_ACCENT,
            bd=1,
            relief=tk.SOLID,
            padx=10,
            pady=6,
        )
        wf_frame.pack(fill=tk.X, pady=(0, 6))
        
        rb_wf1 = tk.Radiobutton(
            wf_frame,
            text="Parameter Ramp (Cylinder)",
            variable=self.var_workflow_mode,
            value="cylinder_ramp",
            command=self._update_ui_state,
            bg=COLOR_CARD_BG,
            fg=COLOR_TEXT,
            selectcolor=COLOR_CARD_BG,
            activebackground=COLOR_CARD_BG,
            activeforeground=COLOR_ACCENT,
            font=("Segoe UI", 9, "bold"),
        )
        rb_wf1.pack(side=tk.LEFT, padx=(0, 8))
        
        rb_wf2 = tk.Radiobutton(
            wf_frame,
            text="Geometry Ramp (Cone)",
            variable=self.var_workflow_mode,
            value="cone_constant",
            command=self._update_ui_state,
            bg=COLOR_CARD_BG,
            fg=COLOR_TEXT,
            selectcolor=COLOR_CARD_BG,
            activebackground=COLOR_CARD_BG,
            activeforeground=COLOR_ACCENT,
            font=("Segoe UI", 9, "bold"),
        )
        rb_wf2.pack(side=tk.LEFT, padx=(0, 8))

        rb_wf3 = tk.Radiobutton(
            wf_frame,
            text="Combined",
            variable=self.var_workflow_mode,
            value="combined",
            command=self._update_ui_state,
            bg=COLOR_CARD_BG,
            fg=COLOR_TEXT,
            selectcolor=COLOR_CARD_BG,
            activebackground=COLOR_CARD_BG,
            activeforeground=COLOR_ACCENT,
            font=("Segoe UI", 9, "bold"),
        )
        rb_wf3.pack(side=tk.LEFT)

        # 3B. Geometry Settings Card
        self.geo_frame = tk.LabelFrame(
            left_col,
            text=" Geometry Parameters ",
            font=("Segoe UI", 9, "bold"),
            bg=COLOR_CARD_BG,
            fg=COLOR_ACCENT,
            bd=1,
            relief=tk.SOLID,
            padx=10,
            pady=6,
        )
        self.geo_frame.pack(fill=tk.X, pady=(0, 6))

        self.lbl_diameter, self.ent_diameter, self.row_diameter = self._add_entry_row(self.geo_frame, "Cylinder Diameter (μm):", self.var_diameter)
        self.lbl_ending_diameter, self.ent_ending_diameter, self.row_ending_diameter = self._add_entry_row(self.geo_frame, "Ending Diameter (μm):", self.var_ending_diameter)

        # Geometry Spacing selection row
        self.row_geo_spacing = tk.Frame(self.geo_frame, bg=COLOR_CARD_BG)
        self.lbl_geo_spacing = tk.Label(
            self.row_geo_spacing,
            text="Diameter Spacing:",
            width=27,
            anchor=tk.W,
            font=("Segoe UI", 9),
            bg=COLOR_CARD_BG,
            fg=COLOR_TEXT,
        )
        self.lbl_geo_spacing.pack(side=tk.LEFT)

        self.rb_geo_linear = tk.Radiobutton(
            self.row_geo_spacing,
            text="Linear",
            variable=self.var_diameter_spacing,
            value="linear",
            bg=COLOR_CARD_BG,
            fg=COLOR_TEXT,
            selectcolor=COLOR_CARD_BG,
            activebackground=COLOR_CARD_BG,
            activeforeground=COLOR_ACCENT,
            font=("Segoe UI", 9),
        )
        self.rb_geo_linear.pack(side=tk.LEFT, padx=(0, 10))

        self.rb_geo_log = tk.Radiobutton(
            self.row_geo_spacing,
            text="Logarithmic",
            variable=self.var_diameter_spacing,
            value="log",
            bg=COLOR_CARD_BG,
            fg=COLOR_TEXT,
            selectcolor=COLOR_CARD_BG,
            activebackground=COLOR_CARD_BG,
            activeforeground=COLOR_ACCENT,
            font=("Segoe UI", 9),
        )
        self.rb_geo_log.pack(side=tk.LEFT)

        self.lbl_base_diameter, self.ent_base_diameter, self.row_base_diameter = self._add_entry_row(self.geo_frame, "Base Layer Dia. (μm, optional):", self.var_base_diameter)

        # Cone-only constant speed rows (shown inside geo_frame when ramp_frame is hidden)
        self.lbl_cone_speed, self.ent_cone_speed, self.row_cone_speed = self._add_entry_row(self.geo_frame, "Print Speed (μm/s):", self.var_start_val)
        self.lbl_cone_points, self.ent_cone_points, self.row_cone_points = self._add_entry_row(self.geo_frame, "Unique Points (N):", self.var_points)
        self.lbl_cone_repl, self.ent_cone_repl, self.row_cone_repl = self._add_entry_row(self.geo_frame, "Replicates per Point (R):", self.var_replicates)

        # 3C. Parameter Ramp Settings Card (Disappears completely when in cone_constant mode!)
        self.ramp_frame = tk.LabelFrame(
            left_col,
            text=" Print Parameter Ramping ",
            font=("Segoe UI", 9, "bold"),
            bg=COLOR_CARD_BG,
            fg=COLOR_ACCENT,
            bd=1,
            relief=tk.SOLID,
            padx=10,
            pady=6,
        )
        self.ramp_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 0))

        self.mode_frame = tk.Frame(self.ramp_frame, bg=COLOR_CARD_BG)
        self.mode_frame.pack(fill=tk.X, pady=(0, 4))
        
        self.lbl_mode = tk.Label(
            self.mode_frame,
            text="Ramp Mode:",
            font=("Segoe UI", 9, "bold"),
            bg=COLOR_CARD_BG,
            fg=COLOR_TEXT,
        )
        self.lbl_mode.pack(side=tk.LEFT, padx=(0, 10))
        
        self.rb_speed = tk.Radiobutton(
            self.mode_frame,
            text="Speed Ramping",
            variable=self.var_ramp_mode,
            value="speed",
            command=self._update_ui_state,
            bg=COLOR_CARD_BG,
            fg=COLOR_TEXT,
            selectcolor=COLOR_CARD_BG,
            activebackground=COLOR_CARD_BG,
            activeforeground=COLOR_ACCENT,
            font=("Segoe UI", 9),
        )
        self.rb_speed.pack(side=tk.LEFT, padx=(0, 10))
        
        self.rb_power = tk.Radiobutton(
            self.mode_frame,
            text="Power Ramping",
            variable=self.var_ramp_mode,
            value="power",
            command=self._update_ui_state,
            bg=COLOR_CARD_BG,
            fg=COLOR_TEXT,
            selectcolor=COLOR_CARD_BG,
            activebackground=COLOR_CARD_BG,
            activeforeground=COLOR_ACCENT,
            font=("Segoe UI", 9),
        )
        self.rb_power.pack(side=tk.LEFT, padx=(0, 10))

        self.rb_dosage = tk.Radiobutton(
            self.mode_frame,
            text="Speed+Power\n(Const. Dosage)",
            variable=self.var_ramp_mode,
            value="dosage_coupled",
            command=self._update_ui_state,
            bg=COLOR_CARD_BG,
            fg=COLOR_TEXT,
            selectcolor=COLOR_CARD_BG,
            activebackground=COLOR_CARD_BG,
            activeforeground=COLOR_ACCENT,
            font=("Segoe UI", 9),
            justify=tk.LEFT,
        )
        self.rb_dosage.pack(side=tk.LEFT)

        # Ramp Spacing selection row
        self.ramp_spacing_frame = tk.Frame(self.ramp_frame, bg=COLOR_CARD_BG)
        self.ramp_spacing_frame.pack(fill=tk.X, pady=(0, 4))

        self.lbl_ramp_spacing = tk.Label(
            self.ramp_spacing_frame,
            text="Ramp Spacing:",
            font=("Segoe UI", 9, "bold"),
            bg=COLOR_CARD_BG,
            fg=COLOR_TEXT,
        )
        self.lbl_ramp_spacing.pack(side=tk.LEFT, padx=(0, 10))

        self.rb_ramp_linear = tk.Radiobutton(
            self.ramp_spacing_frame,
            text="Linear",
            variable=self.var_param_spacing,
            value="linear",
            bg=COLOR_CARD_BG,
            fg=COLOR_TEXT,
            selectcolor=COLOR_CARD_BG,
            activebackground=COLOR_CARD_BG,
            activeforeground=COLOR_ACCENT,
            font=("Segoe UI", 9),
        )
        self.rb_ramp_linear.pack(side=tk.LEFT, padx=(0, 10))

        self.rb_ramp_log = tk.Radiobutton(
            self.ramp_spacing_frame,
            text="Logarithmic",
            variable=self.var_param_spacing,
            value="log",
            bg=COLOR_CARD_BG,
            fg=COLOR_TEXT,
            selectcolor=COLOR_CARD_BG,
            activebackground=COLOR_CARD_BG,
            activeforeground=COLOR_ACCENT,
            font=("Segoe UI", 9),
        )
        self.rb_ramp_log.pack(side=tk.LEFT)

        self.lbl_start, self.ent_start, self.row_start = self._add_entry_row(self.ramp_frame, "Starting Speed (μm/s):", self.var_start_val)
        self.lbl_end, self.ent_end, self.row_end = self._add_entry_row(self.ramp_frame, "Ending Speed (μm/s):", self.var_end_val)
        self.lbl_points, self.ent_points, self.row_points = self._add_entry_row(self.ramp_frame, "Unique Points (N):", self.var_points)
        self.lbl_replicates, self.ent_replicates, self.row_replicates = self._add_entry_row(self.ramp_frame, "Replicates per Point (R):", self.var_replicates)

        # Dosage anchor section (shown only when dosage_coupled mode is active)
        self.dosage_anchor_frame = tk.LabelFrame(
            self.ramp_frame,
            text=" Dosage Anchor (Control Point) ",
            font=("Segoe UI", 9, "bold"),
            bg=COLOR_CARD_BG,
            fg=COLOR_ACCENT,
            bd=1,
            relief=tk.SOLID,
            padx=8,
            pady=6,
        )
        self.dosage_anchor_frame.pack(fill=tk.X, pady=(6, 0))

        tk.Label(
            self.dosage_anchor_frame,
            text=(
                "One (speed, power) reference pair.\n"
                "All other layers derive power so that\n"
                "dose = power x (layer_height / speed) stays constant."
            ),
            font=("Segoe UI", 8, "italic"),
            bg=COLOR_CARD_BG,
            fg=COLOR_TEXT,
            justify=tk.LEFT,
            wraplength=260,
        ).pack(anchor=tk.W, pady=(0, 2))

        self.lbl_control_speed, self.ent_control_speed, self.row_control_speed = self._add_entry_row(
            self.dosage_anchor_frame, "Control Speed (um/s):", self.var_control_speed
        )
        self.lbl_control_power, self.ent_control_power, self.row_control_power = self._add_entry_row(
            self.dosage_anchor_frame, "Control Power (1-255):", self.var_control_power
        )

        # Right Column - Constants & Status Log Container
        right_col = tk.Frame(main_frame, bg=COLOR_BG)
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(8, 0))

        # 3D. Print Constants (Inherited from Main GUI)
        constants_frame = tk.LabelFrame(
            right_col,
            text=" Inherited Print Constants ",
            font=("Segoe UI", 9, "bold"),
            bg=COLOR_CARD_BG,
            fg=COLOR_ACCENT,
            bd=1,
            relief=tk.SOLID,
            padx=10,
            pady=8,
        )
        constants_frame.pack(fill=tk.X, pady=(0, 6))

        self.lbl_layer_height, self.ent_layer_height, _ = self._add_entry_row(constants_frame, "Layer Height (μm):", self.var_layer_height)
        self.lbl_led_current, self.ent_led_current, _ = self._add_entry_row(constants_frame, "LED Current / Intensity (1-255):", self.var_led_current)
        self.lbl_exposure_time, self.ent_exposure_time, _ = self._add_entry_row(constants_frame, "Base Exposure Time (s):", self.var_exposure_time)
        self.lbl_acceleration, self.ent_acceleration, _ = self._add_entry_row(constants_frame, "Acceleration (mm/s²):", self.var_acceleration)

        # 3E. Live Status / Console Log Card (Embedded neatly in right column)
        status_card = tk.LabelFrame(
            right_col,
            text=" Execution Status & Log ",
            font=("Segoe UI", 9, "bold"),
            bg=COLOR_CARD_BG,
            fg=COLOR_ACCENT,
            bd=1,
            relief=tk.SOLID,
            padx=10,
            pady=6,
        )
        status_card.pack(fill=tk.BOTH, expand=True, pady=(0, 0))

        self.txt_status = tk.Text(
            status_card,
            height=6,
            bg=COLOR_ENTRY_BG,
            fg=COLOR_TEXT,
            bd=0,
            highlightthickness=1,
            highlightbackground=COLOR_TEXT,
            font=("Consolas", 8),
            state=tk.DISABLED,
        )
        self.txt_status.pack(fill=tk.BOTH, expand=True)

    def _add_entry_row(self, parent, label_text, var):
        row = tk.Frame(parent, bg=COLOR_CARD_BG)
        row.pack(fill=tk.X, pady=2)
        
        lbl = tk.Label(
            row,
            text=label_text,
            width=27,
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
            disabledbackground=COLOR_DISABLED_BG,
            disabledforeground=COLOR_DISABLED_FG,
            bd=0,
            highlightthickness=1,
            highlightbackground=COLOR_TEXT,
            highlightcolor=COLOR_ACCENT,
            font=("Segoe UI", 9),
        )
        ent.pack(side=tk.RIGHT, fill=tk.X, expand=True, ipady=2)
        return lbl, ent, row

    def _set_entry_enabled(self, lbl, ent, enabled):
        state = tk.NORMAL if enabled else tk.DISABLED
        fg = COLOR_TEXT if enabled else COLOR_DISABLED_FG
        ent.configure(state=state)
        lbl.configure(fg=fg)

    def _set_radio_enabled(self, rb, enabled):
        if enabled:
            rb.configure(state=tk.NORMAL, fg=COLOR_TEXT)
        else:
            rb.configure(state=tk.DISABLED, fg=COLOR_DISABLED_FG)

    def _update_ui_state(self):
        wf = self.var_workflow_mode.get()
        ramp_mode = self.var_ramp_mode.get()

        is_cone = wf in ("cone_constant", "combined")
        is_ramped_params = wf in ("cylinder_ramp", "combined")

        # 1. Update Header & Action Button Text
        if wf == "cone_constant":
            if hasattr(self, "lbl_title"):
                self.lbl_title.configure(text="CONSTANT SPEED CONE GENERATOR")
            if hasattr(self, "lbl_desc"):
                self.lbl_desc.configure(text="Creates expanding cone slices printed at constant stage speed.")
            if hasattr(self, "btn_generate"):
                self.btn_generate.configure(text="Generate Constant Speed Cone")
        elif wf == "combined":
            if hasattr(self, "lbl_title"):
                self.lbl_title.configure(text="RAMPED CONE GENERATOR")
            if hasattr(self, "lbl_desc"):
                self.lbl_desc.configure(text="Creates expanding cone slices with a continuous-motion speed or power ramp.")
            if hasattr(self, "btn_generate"):
                self.btn_generate.configure(text="Generate Ramped Cone")
        else:  # cylinder_ramp
            if hasattr(self, "lbl_title"):
                self.lbl_title.configure(text="RAMPED CYLINDER GENERATOR")
            if hasattr(self, "lbl_desc"):
                self.lbl_desc.configure(text="Creates identical circles of a specified diameter with a continuous-motion speed or power ramp.")
            if hasattr(self, "btn_generate"):
                self.btn_generate.configure(text="Generate Ramped Cylinder")

        # 2. Geometry Section Visibility & Title
        if hasattr(self, "geo_frame"):
            geo_title = " Geometry Parameters (Cone) " if is_cone else " Geometry Parameters (Cylinder) "
            self.geo_frame.configure(text=geo_title)

        if hasattr(self, "lbl_diameter"):
            self.lbl_diameter.configure(text="Starting Diameter (μm):" if is_cone else "Cylinder Diameter (μm):")

        # Unpack and repack rows in geo_frame in clean vertical order
        if hasattr(self, "row_diameter"):
            self.row_diameter.pack(fill=tk.X, pady=2)

            if is_cone:
                self.row_ending_diameter.pack(fill=tk.X, pady=2)
                self.row_geo_spacing.pack(fill=tk.X, pady=(2, 2))
                self._set_entry_enabled(self.lbl_ending_diameter, self.ent_ending_diameter, True)
                self._set_radio_enabled(self.rb_geo_linear, True)
                self._set_radio_enabled(self.rb_geo_log, True)
            else:
                self.row_ending_diameter.pack_forget()
                self.row_geo_spacing.pack_forget()

            self.row_base_diameter.pack(fill=tk.X, pady=2)

            if wf == "cone_constant":
                self.row_cone_speed.pack(fill=tk.X, pady=2)
                self.row_cone_points.pack(fill=tk.X, pady=2)
                self.row_cone_repl.pack(fill=tk.X, pady=2)
            else:
                self.row_cone_speed.pack_forget()
                self.row_cone_points.pack_forget()
                self.row_cone_repl.pack_forget()

        # 3. Parameter Ramp Section Visibility (Disappears completely when unused!)
        if hasattr(self, "ramp_frame"):
            if not is_ramped_params:
                self.ramp_frame.pack_forget()
            else:
                self.ramp_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 0))

                if ramp_mode == "power":
                    self.lbl_start.configure(text="Starting Power (1-255):")
                    self.lbl_end.configure(text="Ending Power (1-255):")
                    self._set_entry_enabled(self.lbl_led_current, self.ent_led_current, False)
                    self.dosage_anchor_frame.pack_forget()
                elif ramp_mode == "dosage_coupled":
                    self.lbl_start.configure(text="Starting Speed (μm/s):")
                    self.lbl_end.configure(text="Ending Speed (μm/s):")
                    self._set_entry_enabled(self.lbl_led_current, self.ent_led_current, False)
                    self.dosage_anchor_frame.pack(fill=tk.X, pady=(6, 0))
                else:  # speed
                    self.lbl_start.configure(text="Starting Speed (μm/s):")
                    self.lbl_end.configure(text="Ending Speed (μm/s):")
                    self._set_entry_enabled(self.lbl_led_current, self.ent_led_current, True)
                    self.dosage_anchor_frame.pack_forget()

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
            # Parse parameters based on Workflow Mode
            wf = self.var_workflow_mode.get()
            
            # --- 1. Geometry parameters ---
            dia_str = self.var_diameter.get().strip()
            if not dia_str:
                label_str = "Starting Diameter" if wf in ("cone_constant", "combined") else "Cylinder Diameter"
                raise ValueError(f"{label_str} must not be empty.")
            diameter_um = float(dia_str)
            
            # Ending diameter is ONLY required for Cone modes
            if wf in ("cone_constant", "combined"):
                end_dia_str = self.var_ending_diameter.get().strip()
                if not end_dia_str:
                    raise ValueError("Ending Diameter must not be empty for Cone generation.")
                ending_diameter_um = float(end_dia_str)
                diameter_spacing = self.var_diameter_spacing.get()
            else:
                # In Cylinder mode, Ending Diameter is hidden/ignored
                ending_diameter_um = None
                diameter_spacing = "linear"

            # Base layer diameter is optional across all modes (defaults to diameter_um)
            base_dia_str = self.var_base_diameter.get().strip()
            base_diameter_um = float(base_dia_str) if base_dia_str else diameter_um

            # --- 2. Layer & Point Counts ---
            points_str = self.var_points.get().strip()
            if not points_str:
                raise ValueError("Unique Points (N) must not be empty.")
            points = int(points_str)

            repl_str = self.var_replicates.get().strip()
            if not repl_str:
                raise ValueError("Replicates per Point (R) must not be empty.")
            replicates = int(repl_str)

            lh_str = self.var_layer_height.get().strip()
            if not lh_str:
                raise ValueError("Layer Height must not be empty.")
            layer_height = float(lh_str)

            exp_str = self.var_exposure_time.get().strip()
            exposure_time_val = float(exp_str) if exp_str else float(self.defaults.get("exposure_time", 2.0))

            # --- 3. Print Parameters (Mode-Scoped) ---
            if wf == "cone_constant":
                # Constant speed cone: Ending speed, Dosage anchor, and Ramp Mode are hidden/ignored
                speed_str = self.var_start_val.get().strip()
                if not speed_str:
                    raise ValueError("Print Speed (μm/s) must not be empty for Constant Speed Cone.")
                start_val = float(speed_str)
                end_val = start_val
                ramp_mode = "speed"
                param_spacing = "linear"

                led_str = self.var_led_current.get().strip()
                led_current = float(led_str) if led_str else float(self.defaults.get("led_current", 1.0))
                control_speed = None
                control_power = None

            else:
                # Parameter Ramp (Cylinder) or Combined (Ramped Cone)
                ramp_mode = self.var_ramp_mode.get()
                param_spacing = self.var_param_spacing.get()
                
                start_val_str = self.var_start_val.get().strip()
                end_val_str = self.var_end_val.get().strip()

                if ramp_mode == "power":
                    if not start_val_str:
                        raise ValueError("Starting Power must not be empty.")
                    if not end_val_str:
                        raise ValueError("Ending Power must not be empty.")
                    start_val = float(start_val_str)
                    end_val = float(end_val_str)
                    led_current = 1.0
                    control_speed = None
                    control_power = None

                elif ramp_mode == "dosage_coupled":
                    if not start_val_str:
                        raise ValueError("Starting Speed must not be empty.")
                    if not end_val_str:
                        raise ValueError("Ending Speed must not be empty.")
                    start_val = float(start_val_str)
                    end_val = float(end_val_str)
                    led_current = 1.0

                    cs_str = self.var_control_speed.get().strip()
                    cp_str = self.var_control_power.get().strip()
                    if not cs_str or not cp_str:
                        raise ValueError(
                            "Control Speed and Control Power must be provided for Constant Dosage mode."
                        )
                    control_speed = float(cs_str)
                    control_power = float(cp_str)

                else:  # speed ramping
                    if not start_val_str:
                        raise ValueError("Starting Speed must not be empty.")
                    if not end_val_str:
                        raise ValueError("Ending Speed must not be empty.")
                    start_val = float(start_val_str)
                    end_val = float(end_val_str)

                    led_str = self.var_led_current.get().strip()
                    led_current = float(led_str) if led_str else float(self.defaults.get("led_current", 1.0))
                    control_speed = None
                    control_power = None

            # --- 4. Movement Constants ---
            step_speed = float(self.var_step_speed.get().strip() or self.defaults.get("step_speed", 1000.0))
            overstep = float(self.var_overstep.get().strip() or self.defaults.get("overstep", 500.0))
            acceleration = float(self.var_acceleration.get().strip() or self.defaults.get("acceleration", 5.0))
            pause = float(self.var_pause.get().strip() or self.defaults.get("pause", 0.0))
            sandwich_speed = float(self.var_sandwich_speed.get().strip() or self.defaults.get("sandwich_speed", 500.0))
            
            output_base = self.var_output_base.get().strip() or os.getcwd()

            # Execute Workflow
            folder_path, gen_warnings = generate_ramped_cylinder_workflow(
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
                control_speed=control_speed,
                control_power=control_power,
                ending_diameter_um=ending_diameter_um,
                base_diameter_um=base_diameter_um,
                param_spacing=param_spacing,
                diameter_spacing=diameter_spacing,
                status_callback=lambda msg, err=False: self.log(msg, err),
            )

            if gen_warnings:
                messagebox.showwarning(
                    "Dosage Clamping Warning",
                    "\n\n".join(gen_warnings)
                    + "\n\nThe instruction file has been written with clamped values.",
                    parent=self.window,
                )

            if wf == "cone_constant":
                shape_name = "Constant Speed Cone"
            elif ending_diameter_um:
                shape_name = "Ramped Cone"
            else:
                shape_name = "Ramped Cylinder"

            messagebox.showinfo(
                "Success",
                f"{shape_name} generation complete!\nSaved to: {folder_path}",
                parent=self.window,
            )
            
            # Update parent status if callback exists
            if self.prince_main_app_ref:
                self.update_status(f"Generated {shape_name}: {os.path.basename(folder_path)}")
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
