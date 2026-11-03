# -*- coding: utf-8 -*-
"""Processor Module

Composes 3D axial Z-compensation, edge enhancement, global enhancement,
feature depth correction, and scattering compensation.
Handles file I/O, natural sort, multiprocessing, and configurable pipeline stage ordering.
"""

import os
import re
import glob
import math
import cv2
import numpy as np
import multiprocessing
from functools import partial
from typing import List, Optional, Tuple, Union

from .edge_enhancement import edge_enhance
from .global_enhancement import (
    build_gaussian_map,
    build_angular_asymmetric_map,
    apply_global_enhancement,
)
from .padding import create_black_padding_image, get_output_sequence
try:
    from .feature_depth import (build_feature_depth_map, build_pressure_depth_map,
                                 apply_feature_depth_correction)
    HAS_FEATURE_DEPTH = True
except ImportError:
    HAS_FEATURE_DEPTH = False

from .scattering_compensation import apply_scattering_compensation
from support_modules.z_compensation import (
    ZCompensationConfig,
    attenuation_per_layer,
    compute_layer_factors,
    solve_single_layer_lookahead,
    stream_axial_compensated_volume,
)

MIN_INTENSITY = 100
MAX_INTENSITY = 255
CONE_OUTPUT_WIDTH = 2560
CONE_OUTPUT_HEIGHT = 1600
CONE_UM_PER_PIXEL = 4.005

DEFAULT_PIPELINE_ORDER = ["axial", "edge", "global", "depth", "scatter"]

STAGE_LABELS = {
    "axial": "Axial Z Compensation",
    "edge": "Edge Enhancement",
    "global": "Global Blur Enhancement",
    "depth": "Feature Depth Correction",
    "scatter": "Scattering Compensation",
}


def _extract_number(filepath: str) -> int:
    match = re.search(r'\d+', os.path.basename(filepath))
    return int(match.group()) if match else 0


def _natural_sort(files: list) -> list:
    return sorted(files, key=_extract_number)


def _get_output_folder_name(input_folder: str, blur: float, padded: bool, globe: float,
                            edge_enabled: bool, global_enabled: bool,
                            global_asymmetric: bool = False,
                            ge_sector_angle: float = 90.0,
                            ge_sector_smoothing: int = 0,
                            ge_blend_angle: float = 20.0,
                            depth_enabled: bool = False,
                            depth_strength: float = 0.0,
                            depth_mode: str = "distance",
                            scatter_enabled: bool = False,
                            axial_enabled: bool = False,
                            layer_thickness_um: float = 50.0,
                            penetration_depth_um: float = 120.0,
                            exposure_ratio: float = 2.5,
                            pipeline_order: Optional[List[str]] = None) -> str:
    """Format: EE_{blur}_{Padded|NoPad}_GE_{globe}[_Asym...][_FD...][_SC...][_ZA...][_Ord...]"""
    ee_val = int(blur) if edge_enabled else 0
    pad_str = "Padded" if padded else "NoPad"
    ge_val = globe if global_enabled else 0
    ge_str = str(ge_val).replace(".", "_") if ge_val != 0 else "0"
    if global_asymmetric:
        angle_tag = str(round(float(ge_sector_angle), 2)).replace(".", "_")
        blend_tag = str(round(float(ge_blend_angle), 2)).replace(".", "_")
        asym_str = f"_AsymA{angle_tag}_S{int(ge_sector_smoothing)}_B{blend_tag}"
    else:
        asym_str = ""
    if depth_enabled:
        mode_tag = "_Pres" if depth_mode == "pressure" else ""
        fd_str = f"_FD_{str(round(depth_strength, 2)).replace('.', '_')}{mode_tag}"
    else:
        fd_str = ""
    sc_str = "_SC" if scatter_enabled else ""

    za_str = ""
    if axial_enabled:
        lt_tag = str(round(float(layer_thickness_um), 2)).replace('.', '_')
        dp_tag = str(round(float(penetration_depth_um), 2)).replace('.', '_')
        er_tag = str(round(float(exposure_ratio), 2)).replace('.', '_')
        za_str = f"_ZA_LT{lt_tag}_DP{dp_tag}_ER{er_tag}"

    order_str = ""
    if pipeline_order and pipeline_order != DEFAULT_PIPELINE_ORDER:
        enabled_stages = []
        for s in pipeline_order:
            if s == "axial" and axial_enabled:
                enabled_stages.append("ZA")
            elif s == "edge" and edge_enabled:
                enabled_stages.append("EE")
            elif s == "global" and global_enabled:
                enabled_stages.append("GE")
            elif s == "depth" and depth_enabled:
                enabled_stages.append("FD")
            elif s == "scatter" and scatter_enabled:
                enabled_stages.append("SC")
        if enabled_stages:
            order_str = f"_Ord-{''.join(enabled_stages)}"

    return f"EE_{ee_val}_{pad_str}_GE_{ge_str}{asym_str}{fd_str}{sc_str}{za_str}{order_str}"


def _apply_padding_normalization(intermediate: np.ndarray, img_float: np.ndarray, min_intensity: float = 100.0, max_intensity: float = 255.0) -> np.ndarray:
    """Padding normalization: only when EE and GE are off. Normalize non-zero pixels to intensity range."""
    mask = img_float > 0
    if not np.any(mask):
        return intermediate
    max_i = np.max(intermediate[mask])
    min_i = np.min(intermediate[mask])
    if max_i > min_i:
        intermediate = (intermediate - min_i) / (max_i - min_i)
    intermediate = intermediate * (max_intensity - min_intensity) + min_intensity
    intermediate[~mask] = 0
    return intermediate


def _format_um_tag(value: float) -> str:
    return str(round(float(value), 2)).replace('.', '_')


def _build_cone_slice_image(radius_px: float, canvas_size: int) -> np.ndarray:
    image = np.zeros((CONE_OUTPUT_HEIGHT, CONE_OUTPUT_WIDTH), dtype=np.uint8)
    center_x = CONE_OUTPUT_WIDTH // 2
    center_y = CONE_OUTPUT_HEIGHT // 2
    draw_radius = max(0, int(round(float(radius_px))))
    cv2.circle(image, (center_x, center_y), draw_radius, 255, thickness=-1, lineType=cv2.LINE_8)
    return image


def generate_cone_images(input_folder: str,
                         initial_radius_um: float,
                         ending_radius_um: float,
                         height_um: float,
                         layer_height_um: float,
                         progress_callback=None) -> str:
    """Generate a sequential PNG stack for a cone-shaped cross-section."""
    if not input_folder:
        raise ValueError("An output folder must be selected for cone generation")
    if height_um <= 0:
        raise ValueError("Height must be greater than zero")
    if layer_height_um <= 0:
        raise ValueError("Layer height must be greater than zero")
    if initial_radius_um < 0 or ending_radius_um < 0:
        raise ValueError("Cone radii must be non-negative")

    layer_count = max(1, int(math.ceil(float(height_um) / float(layer_height_um))))
    if layer_count == 1:
        radii = [float(ending_radius_um)]
    else:
        radii = [
            float(initial_radius_um) + (
                (float(ending_radius_um) - float(initial_radius_um)) * (layer_index / float(layer_count - 1))
            )
            for layer_index in range(layer_count)
        ]

    max_radius_um = max(float(initial_radius_um), float(ending_radius_um))
    max_fit_radius_px = min((CONE_OUTPUT_WIDTH - 4) / 2.0, (CONE_OUTPUT_HEIGHT - 4) / 2.0)
    max_fit_radius_um = max_fit_radius_px * CONE_UM_PER_PIXEL
    if max_radius_um > max_fit_radius_um:
        raise ValueError(
            f"Cone radius {max_radius_um:g} um exceeds the printable field for {CONE_UM_PER_PIXEL:g} um/px "
            f"on a {CONE_OUTPUT_WIDTH}x{CONE_OUTPUT_HEIGHT} frame. Maximum safe radius is {max_fit_radius_um:.1f} um."
        )

    output_folder_name = (
        f"Cone_R{_format_um_tag(initial_radius_um)}_To{_format_um_tag(ending_radius_um)}"
        f"_H{_format_um_tag(height_um)}_LH{_format_um_tag(layer_height_um)}"
    )
    output_folder = os.path.join(input_folder, output_folder_name)
    os.makedirs(output_folder, exist_ok=True)

    if progress_callback:
        progress_callback(0, layer_count, "Generating cone images...")

    for index, radius_um in enumerate(radii, start=1):
        image = _build_cone_slice_image(radius_um / CONE_UM_PER_PIXEL, 0)
        output_path = os.path.join(output_folder, f"{index}.png")
        cv2.imwrite(output_path, image)
        if progress_callback:
            progress_callback(index, layer_count, f"Generated layer {index}/{layer_count}")

    return output_folder


def _apply_2d_stage(intermediate: np.ndarray,
                     stage: str,
                     edge_check: int,
                     blurring: float,
                     filter_size: int,
                     ee_min: float,
                     ee_max: float,
                     global_check: int,
                     gaussian_map: Optional[np.ndarray],
                     global_asymmetric: bool,
                     globe: float,
                     blend_angle: float,
                     ge_sector_angle: float,
                     ge_sector_smoothing: int,
                     depth_check: int,
                     depth_strength: float,
                     depth_decay_sigma: float,
                     depth_smooth_sigma: float,
                     depth_mode: str,
                     pressure_conductivity: float,
                     pressure_sink: float,
                     scatter_check: int,
                     scatter_width: float,
                     scatter_min_val: float,
                     scatter_max_val: float,
                     scatter_falloff: int) -> np.ndarray:
    """Apply a single 2D stage to intermediate float array."""
    if stage == "edge" and edge_check == 1:
        intermediate = edge_enhance(
            intermediate, blurring, filter_size, ee_min, ee_max
        )
    elif stage == "global" and global_check == 1:
        if global_asymmetric:
            ge_map = build_angular_asymmetric_map(
                intermediate,
                globe,
                sector_angle_deg=ge_sector_angle,
                blend_angle_deg=blend_angle,
                smooth_window_sectors=ge_sector_smoothing,
            )
        else:
            ge_map = gaussian_map
        if ge_map is not None:
            intermediate = apply_global_enhancement(intermediate, ge_map)
    elif stage == "depth" and HAS_FEATURE_DEPTH and depth_check == 1:
        if depth_mode == "pressure":
            depth_map = build_pressure_depth_map(
                intermediate, pressure_conductivity, pressure_sink
            )
        else:
            depth_map = build_feature_depth_map(
                intermediate, depth_decay_sigma, depth_smooth_sigma
            )
        intermediate = apply_feature_depth_correction(
            intermediate, depth_map, depth_strength
        )
    elif stage == "scatter" and scatter_check == 1:
        intermediate = apply_scattering_compensation(
            intermediate, scatter_width, scatter_min_val, scatter_max_val, scatter_falloff
        )
    return intermediate


def process_single_image(image_input: Union[str, np.ndarray],
                         edge_check: int,
                         blurring: float,
                         filter_size: int,
                         global_check: int,
                         gaussian_map: np.ndarray,
                         guide_padding: int,
                         global_asymmetric: bool = False,
                         globe: float = 0.8,
                         blend_angle: float = 20.0,
                         ge_sector_angle: float = 90.0,
                         ge_sector_smoothing: int = 0,
                         depth_check: int = 0,
                         depth_strength: float = 0.5,
                         depth_decay_sigma: float = 50.0,
                         depth_smooth_sigma: float = 10.0,
                         depth_mode: str = "distance",
                         pressure_conductivity: float = 100.0,
                         pressure_sink: float = 0.1,
                         scatter_check: int = 0,
                         scatter_width: float = 15.0,
                         scatter_min_val: float = 127.0,
                         scatter_max_val: float = 255.0,
                         scatter_falloff: int = 0,
                         ee_min: float = 100.0,
                         ee_max: float = 255.0,
                         pipeline_order: Optional[List[str]] = None) -> np.ndarray:
    """
    Process a single image through 2D pipeline stages in the specified order.
    Used by the multiprocessing pool.
    """
    if isinstance(image_input, str):
        img = cv2.imread(image_input, cv2.IMREAD_GRAYSCALE)
    else:
        img = image_input

    if img is None:
        return None

    img_float = img.astype(np.float64)
    intermediate = np.copy(img_float)

    order = [s for s in (pipeline_order or DEFAULT_PIPELINE_ORDER) if s != "axial"]

    for stage in order:
        intermediate = _apply_2d_stage(
            intermediate, stage,
            edge_check=edge_check, blurring=blurring, filter_size=filter_size, ee_min=ee_min, ee_max=ee_max,
            global_check=global_check, gaussian_map=gaussian_map, global_asymmetric=global_asymmetric,
            globe=globe, blend_angle=blend_angle, ge_sector_angle=ge_sector_angle, ge_sector_smoothing=ge_sector_smoothing,
            depth_check=depth_check, depth_strength=depth_strength, depth_decay_sigma=depth_decay_sigma,
            depth_smooth_sigma=depth_smooth_sigma, depth_mode=depth_mode, pressure_conductivity=pressure_conductivity,
            pressure_sink=pressure_sink, scatter_check=scatter_check, scatter_width=scatter_width,
            scatter_min_val=scatter_min_val, scatter_max_val=scatter_max_val, scatter_falloff=scatter_falloff
        )

    if guide_padding == 1 and edge_check == 0 and global_check == 0:
        intermediate = _apply_padding_normalization(intermediate, img_float, ee_min, ee_max)

    final_img = np.clip(intermediate, 0, 255).astype(np.uint8)
    return final_img


def process_single_for_preview(image_path: str,
                               edge_enabled: bool = False,
                               blurring: float = 25.0,
                               global_enabled: bool = False,
                               globe: float = 0.8,
                               sigma: float = 6.0,
                               global_asymmetric: bool = False,
                               blend_angle: float = 20.0,
                               ge_sector_angle: float = 90.0,
                               ge_sector_smoothing: int = 0,
                               depth_enabled: bool = False,
                               depth_strength: float = 0.5,
                               depth_decay_sigma: float = 50.0,
                               depth_smooth_sigma: float = 10.0,
                               depth_mode: str = "distance",
                               pressure_conductivity: float = 100.0,
                               pressure_sink: float = 0.1,
                               scatter_enabled: bool = False,
                               scatter_width: float = 15.0,
                               scatter_min_val: float = 127.0,
                               scatter_max_val: float = 255.0,
                               axial_factor: Union[float, np.ndarray] = 1.0,
                               axial_enabled: bool = False,
                               ee_falloff: int = 0,
                               scatter_falloff: int = 0,
                               ee_min: float = 100.0,
                               ee_max: float = 255.0,
                               pipeline_order: Optional[List[str]] = None) -> np.ndarray:
    """
    Process a single image for GUI preview following the requested stage order.
    """
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"Could not read image: {image_path}")

    img_float = img.astype(np.float64)
    intermediate = np.copy(img_float)

    rows, cols = img.shape
    gaussian_map = None
    if global_enabled and not global_asymmetric:
        gaussian_map = build_gaussian_map(rows, cols, globe, sigma)

    edge_filter_size = int(ee_falloff) if ee_falloff and ee_falloff > 0 else int(2 * (2 * blurring) + 1)
    order = pipeline_order or DEFAULT_PIPELINE_ORDER

    for stage in order:
        if stage == "axial":
            if axial_enabled or not (isinstance(axial_factor, (int, float)) and abs(float(axial_factor) - 1.0) < 1e-9):
                intermediate = intermediate * axial_factor
        else:
            intermediate = _apply_2d_stage(
                intermediate, stage,
                edge_check=1 if edge_enabled else 0, blurring=blurring, filter_size=edge_filter_size,
                ee_min=ee_min, ee_max=ee_max, global_check=1 if global_enabled else 0,
                gaussian_map=gaussian_map, global_asymmetric=global_asymmetric, globe=globe,
                blend_angle=blend_angle, ge_sector_angle=ge_sector_angle, ge_sector_smoothing=ge_sector_smoothing,
                depth_check=1 if depth_enabled else 0, depth_strength=depth_strength,
                depth_decay_sigma=depth_decay_sigma, depth_smooth_sigma=depth_smooth_sigma,
                depth_mode=depth_mode, pressure_conductivity=pressure_conductivity,
                pressure_sink=pressure_sink, scatter_check=1 if scatter_enabled else 0,
                scatter_width=scatter_width, scatter_min_val=scatter_min_val,
                scatter_max_val=scatter_max_val, scatter_falloff=scatter_falloff
            )

    return np.clip(intermediate, 0, 255).astype(np.uint8)


def process_folder(input_folder: str,
                   edge_enabled: bool = False,
                   blurring: float = 25.0,
                   global_enabled: bool = False,
                   globe: float = 0.8,
                   sigma: float = 6.0,
                   padding_enabled: bool = False,
                   global_asymmetric: bool = False,
                   blend_angle: float = 20.0,
                   ge_sector_angle: float = 90.0,
                   ge_sector_smoothing: int = 0,
                   depth_enabled: bool = False,
                   depth_strength: float = 0.5,
                   depth_decay_sigma: float = 50.0,
                   depth_smooth_sigma: float = 10.0,
                   depth_mode: str = "distance",
                   pressure_conductivity: float = 100.0,
                   pressure_sink: float = 0.1,
                   scatter_enabled: bool = False,
                   scatter_width: float = 15.0,
                   scatter_min_val: float = 127.0,
                   scatter_max_val: float = 255.0,
                   axial_enabled: bool = False,
                   layer_thickness_um: float = 50.0,
                   penetration_depth_um: float = 120.0,
                   critical_energy_ec: float = 10.0,
                   exposure_ratio: float = 2.5,
                   axial_strength: float = 1.0,
                   axial_min_factor: float = 0.0,
                   ee_falloff: int = 0,
                   scatter_falloff: int = 0,
                   ee_min: float = 100.0,
                   ee_max: float = 255.0,
                   pipeline_order: Optional[List[str]] = None,
                   progress_callback=None) -> str:
    """
    Process all PNG images in folder following the configured pipeline order.
    """
    search_path = os.path.join(input_folder, '*.png')
    image_files = glob.glob(search_path)
    image_files = _natural_sort(image_files)

    if not image_files:
        raise ValueError(f"No PNG files found in {input_folder}")

    # Exclude files that look like padding outputs (e.g., 5_1.png) from processing
    def is_padding_file(f):
        base = os.path.basename(f)
        return '_' in base and base.endswith('.png') and re.match(r'\d+_\d+\.png', base)
    image_files = [f for f in image_files if not is_padding_file(f)]

    if not image_files:
        raise ValueError(f"No source PNG files found (excluding *_1.png) in {input_folder}")

    first_img = cv2.imread(image_files[0], cv2.IMREAD_GRAYSCALE)
    if first_img is None:
        raise ValueError(f"Could not read first image: {image_files[0]}")
    rows, cols = first_img.shape

    gaussian_map = None
    if global_enabled and not global_asymmetric:
        gaussian_map = build_gaussian_map(rows, cols, globe, sigma)

    edge_filter_size = int(ee_falloff) if ee_falloff and ee_falloff > 0 else int(2 * (2 * blurring) + 1)
    order = pipeline_order or DEFAULT_PIPELINE_ORDER

    # Determine execution flow based on position of 'axial' in pipeline_order
    current_stack: List[Union[str, np.ndarray]] = list(image_files)

    if axial_enabled and "axial" in order:
        axial_idx = order.index("axial")
        stages_before = [s for s in order[:axial_idx] if s != "axial"]
        stages_after = [s for s in order[axial_idx + 1:] if s != "axial"]

        zc_config = ZCompensationConfig(
            layer_thickness_um=layer_thickness_um,
            penetration_depth_um=penetration_depth_um,
            critical_energy_ec=critical_energy_ec,
            exposure_ratio=exposure_ratio,
            strength=axial_strength,
            min_factor=axial_min_factor,
        )

        # 1. Run 2D stages before axial if any
        if stages_before:
            if progress_callback:
                progress_callback(0, len(image_files), f"Running stages before axial: {stages_before}...")
            worker_before = partial(
                process_single_image,
                edge_check=1 if (edge_enabled and "edge" in stages_before) else 0,
                blurring=blurring, filter_size=edge_filter_size,
                global_check=1 if (global_enabled and "global" in stages_before) else 0,
                gaussian_map=gaussian_map, guide_padding=0,
                global_asymmetric=global_asymmetric, globe=globe, blend_angle=blend_angle,
                ge_sector_angle=ge_sector_angle, ge_sector_smoothing=ge_sector_smoothing,
                depth_check=1 if (depth_enabled and "depth" in stages_before) else 0,
                depth_strength=depth_strength, depth_decay_sigma=depth_decay_sigma,
                depth_smooth_sigma=depth_smooth_sigma, depth_mode=depth_mode,
                pressure_conductivity=pressure_conductivity, pressure_sink=pressure_sink,
                scatter_check=1 if (scatter_enabled and "scatter" in stages_before) else 0,
                scatter_width=scatter_width, scatter_min_val=scatter_min_val,
                scatter_max_val=scatter_max_val, scatter_falloff=scatter_falloff,
                ee_min=ee_min, ee_max=ee_max, pipeline_order=stages_before
            )
            with multiprocessing.Pool() as pool:
                current_stack = pool.map(worker_before, current_stack)

        # 2. Run 3D axial Z-compensation streaming pass
        if progress_callback:
            progress_callback(0, len(image_files), "Running 3D axial voxel solver...")
        current_stack = stream_axial_compensated_volume(
            image_files, zc_config, progress_callback=progress_callback
        )

        # 3. Run 2D stages after axial
        if stages_after:
            if progress_callback:
                progress_callback(0, len(image_files), f"Running stages after axial: {stages_after}...")
            worker_after = partial(
                process_single_image,
                edge_check=1 if (edge_enabled and "edge" in stages_after) else 0,
                blurring=blurring, filter_size=edge_filter_size,
                global_check=1 if (global_enabled and "global" in stages_after) else 0,
                gaussian_map=gaussian_map, guide_padding=1 if padding_enabled else 0,
                global_asymmetric=global_asymmetric, globe=globe, blend_angle=blend_angle,
                ge_sector_angle=ge_sector_angle, ge_sector_smoothing=ge_sector_smoothing,
                depth_check=1 if (depth_enabled and "depth" in stages_after) else 0,
                depth_strength=depth_strength, depth_decay_sigma=depth_decay_sigma,
                depth_smooth_sigma=depth_smooth_sigma, depth_mode=depth_mode,
                pressure_conductivity=pressure_conductivity, pressure_sink=pressure_sink,
                scatter_check=1 if (scatter_enabled and "scatter" in stages_after) else 0,
                scatter_width=scatter_width, scatter_min_val=scatter_min_val,
                scatter_max_val=scatter_max_val, scatter_falloff=scatter_falloff,
                ee_min=ee_min, ee_max=ee_max, pipeline_order=stages_after
            )
            with multiprocessing.Pool() as pool:
                processed = pool.map(worker_after, current_stack)
        else:
            processed = current_stack

    else:
        # Standard 2D flow without 3D axial
        worker_2d = partial(
            process_single_image,
            edge_check=1 if edge_enabled else 0,
            blurring=blurring, filter_size=edge_filter_size,
            global_check=1 if global_enabled else 0,
            gaussian_map=gaussian_map, guide_padding=1 if padding_enabled else 0,
            global_asymmetric=global_asymmetric, globe=globe, blend_angle=blend_angle,
            ge_sector_angle=ge_sector_angle, ge_sector_smoothing=ge_sector_smoothing,
            depth_check=1 if depth_enabled else 0, depth_strength=depth_strength,
            depth_decay_sigma=depth_decay_sigma, depth_smooth_sigma=depth_smooth_sigma,
            depth_mode=depth_mode, pressure_conductivity=pressure_conductivity,
            pressure_sink=pressure_sink, scatter_check=1 if scatter_enabled else 0,
            scatter_width=scatter_width, scatter_min_val=scatter_min_val,
            scatter_max_val=scatter_max_val, scatter_falloff=scatter_falloff,
            ee_min=ee_min, ee_max=ee_max, pipeline_order=[s for s in order if s != "axial"]
        )
        if progress_callback:
            progress_callback(0, len(image_files), "Processing images...")
        with multiprocessing.Pool() as pool:
            processed = pool.map(worker_2d, current_stack)

    output_folder_name = _get_output_folder_name(
        input_folder, blurring, padding_enabled, globe, edge_enabled, global_enabled,
        global_asymmetric, ge_sector_angle, ge_sector_smoothing, blend_angle,
        depth_enabled, depth_strength, depth_mode, scatter_enabled,
        axial_enabled=axial_enabled, layer_thickness_um=layer_thickness_um,
        penetration_depth_um=penetration_depth_um, exposure_ratio=exposure_ratio,
        pipeline_order=pipeline_order
    )

    output_folder = os.path.join(input_folder, output_folder_name)
    os.makedirs(output_folder, exist_ok=True)

    if progress_callback:
        progress_callback(len(image_files), len(image_files), "Saving images...")

    output_sequence = get_output_sequence(processed, image_files, padding_enabled)
    for img, out_name in output_sequence:
        out_path = os.path.join(output_folder, out_name)
        cv2.imwrite(out_path, img)

    return output_folder
