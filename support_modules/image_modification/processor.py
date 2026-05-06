# -*- coding: utf-8 -*-
"""Processor Module

Composes edge enhancement, global enhancement, and padding.
Handles file I/O, natural sort, multiprocessing, output naming.
"""

import os
import re
import glob
import cv2
import numpy as np
import multiprocessing
from functools import partial

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
from support_modules.z_compensation import compute_layer_factors

MIN_INTENSITY = 100
MAX_INTENSITY = 255


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
                            scatter_enabled: bool = False) -> str:
    """Format: EE_{blur}_{Padded|NoPad}_GE_{globe}[_AsymA{deg}_S{n}_B{deg}][_FD_{strength}[_Pres]][_SC]"""
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
    return f"EE_{ee_val}_{pad_str}_GE_{ge_str}{asym_str}{fd_str}{sc_str}"


def _apply_padding_normalization(intermediate: np.ndarray, img_float: np.ndarray) -> np.ndarray:
    """Padding normalization: only when EE and GE are off. Normalize non-zero pixels to intensity range."""
    mask = img_float > 0
    if not np.any(mask):
        return intermediate
    max_i = np.max(intermediate[mask])
    min_i = np.min(intermediate[mask])
    if max_i > min_i:
        intermediate = (intermediate - min_i) / (max_i - min_i)
    intermediate = intermediate * (MAX_INTENSITY - MIN_INTENSITY) + MIN_INTENSITY
    intermediate[~mask] = 0
    return intermediate


def process_single_image(filename: str,
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
                         scatter_falloff: int = 0) -> np.ndarray:
    """
    Process a single image. Used by multiprocessing pool.

    Args:
        filename: Path to source image
        edge_check: 1 to enable edge enhancement
        blurring: Gaussian blur sigma
        filter_size: Edge filter kernel size
        global_check: 1 to enable global enhancement
        gaussian_map: Pre-built map for symmetric mode (or None if asymmetric)
        guide_padding: 1 to enable padding normalization (when EE and GE off)
        global_asymmetric: Use angular-sector asymmetric map instead of symmetric
        globe: Center min value for global enhancement
        blend_angle: Angular blend width near sector boundaries (degrees)
        ge_sector_angle: Sector width for asymmetric mode (degrees)
        ge_sector_smoothing: Circular smoothing window in sector-count units
        depth_check: 1 to enable feature depth correction
        depth_strength: Correction strength [0, 1]
        depth_decay_sigma: Channel quality decay distance (pixels) — distance mode
        depth_smooth_sigma: Depth map smoothing sigma (pixels) — distance mode
        depth_mode: "distance" (v3 Euclidean) or "pressure" (Poisson PDE solver)
        pressure_conductivity: Channel conductivity K ratio — pressure mode
        pressure_sink: Resin consumption sink strength — pressure mode

    Returns:
        Processed uint8 image or None if read failed
    """
    img = cv2.imread(filename, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return None

    img_float = img.astype(np.float64)
    intermediate = np.copy(img_float)

    if edge_check == 1:
        intermediate = edge_enhance(
            intermediate, blurring, filter_size, MIN_INTENSITY, MAX_INTENSITY
        )

    if global_check == 1:
        if global_asymmetric:
            ge_map = build_angular_asymmetric_map(
                img_float,
                globe,
                sector_angle_deg=ge_sector_angle,
                blend_angle_deg=blend_angle,
                smooth_window_sectors=ge_sector_smoothing,
            )
        else:
            ge_map = gaussian_map
        if ge_map is not None:
            intermediate = apply_global_enhancement(intermediate, ge_map)

    if HAS_FEATURE_DEPTH and depth_check == 1:
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

    if scatter_check == 1:
        intermediate = apply_scattering_compensation(
            intermediate, scatter_width, scatter_min_val, scatter_max_val, scatter_falloff
        )

    if guide_padding == 1 and edge_check == 0 and global_check == 0:
        intermediate = _apply_padding_normalization(intermediate, img_float)

    final_img = np.clip(intermediate, 0, 255).astype(np.uint8)
    return final_img


def process_single_for_preview(image_path: str,
                               edge_enabled: bool,
                               blurring: float,
                               global_enabled: bool,
                               globe: float,
                               sigma: float,
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
                               axial_factor: float = 1.0,
                               ee_falloff: int = 0,
                               scatter_falloff: int = 0) -> np.ndarray:
    """
    Process a single image for GUI preview. Applies EE and GE only (no padding insertion).

    Args:
        image_path: Path to image
        edge_enabled: Enable edge enhancement
        blurring: Gaussian blur sigma
        global_enabled: Enable global enhancement
        globe: Global map center ratio
        sigma: Global map sigma divisor (symmetric mode)
        global_asymmetric: Use angular-sector asymmetric map
        blend_angle: Angular blend width near sector boundaries (degrees)
        ge_sector_angle: Sector width for asymmetric mode (degrees)
        ge_sector_smoothing: Circular smoothing window in sector-count units
        depth_mode: "distance" or "pressure"
        pressure_conductivity: Channel K ratio — pressure mode
        pressure_sink: Resin sink strength — pressure mode

    Returns:
        Processed uint8 image
    """
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"Could not read image: {image_path}")

    img_float = img.astype(np.float64)
    intermediate = np.copy(img_float)

    if edge_enabled:
        filter_size = int(ee_falloff) if ee_falloff and ee_falloff > 0 else int(2 * (2 * blurring) + 1)
        intermediate = edge_enhance(
            intermediate, blurring, filter_size, MIN_INTENSITY, MAX_INTENSITY
        )

    if global_enabled:
        if global_asymmetric:
            ge_map = build_angular_asymmetric_map(
                img_float,
                globe,
                sector_angle_deg=ge_sector_angle,
                blend_angle_deg=blend_angle,
                smooth_window_sectors=ge_sector_smoothing,
            )
        else:
            rows, cols = img.shape
            ge_map = build_gaussian_map(rows, cols, globe, sigma)
        intermediate = apply_global_enhancement(intermediate, ge_map)

    if HAS_FEATURE_DEPTH and depth_enabled:
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

    if scatter_enabled:
        intermediate = apply_scattering_compensation(
            intermediate, scatter_width, scatter_min_val, scatter_max_val, scatter_falloff
        )

    if abs(axial_factor - 1.0) > 1e-9:
        intermediate = intermediate * float(axial_factor)

    return np.clip(intermediate, 0, 255).astype(np.uint8)


def process_folder(input_folder: str,
                   edge_enabled: bool,
                   blurring: float,
                   global_enabled: bool,
                   globe: float,
                   sigma: float,
                   padding_enabled: bool,
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
                   axial_strength: float = 1.0,
                   axial_min_factor: float = 0.25,
                   ee_falloff: int = 0,
                   scatter_falloff: int = 0,
                   progress_callback=None) -> str:
    """
    Process all PNG images in folder. Output to subfolder named
    EE_{blur}_{Padded|NoPad}_GE_{globe}.

    Args:
        input_folder: Path to folder containing PNGs
        edge_enabled: Enable edge enhancement
        blurring: Gaussian blur sigma
        global_enabled: Enable global enhancement
        globe: Global map center ratio
        sigma: Global map sigma divisor (symmetric mode)
        padding_enabled: Insert black {x}_1.png after each image
        global_asymmetric: Use angular-sector asymmetric map
        blend_angle: Angular blend width near sector boundaries (degrees)
        ge_sector_angle: Sector width for asymmetric mode (degrees)
        ge_sector_smoothing: Circular smoothing window in sector-count units
        progress_callback: Optional fn(current, total, message)

    Returns:
        Output folder path
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

    # Get image dimensions from first image
    first_img = cv2.imread(image_files[0], cv2.IMREAD_GRAYSCALE)
    if first_img is None:
        raise ValueError(f"Could not read first image: {image_files[0]}")
    rows, cols = first_img.shape

    # Build gaussian map if needed (symmetric mode only; asymmetric builds per-image)
    gaussian_map = None
    if global_enabled and not global_asymmetric:
        gaussian_map = build_gaussian_map(rows, cols, globe, sigma)

    edge_filter_size = int(ee_falloff) if ee_falloff and ee_falloff > 0 else int(2 * (2 * blurring) + 1)
    worker = partial(
        process_single_image,
        edge_check=1 if edge_enabled else 0,
        blurring=blurring,
        filter_size=edge_filter_size,
        global_check=1 if global_enabled else 0,
        gaussian_map=gaussian_map,
        guide_padding=1 if padding_enabled else 0,
        global_asymmetric=global_asymmetric,
        globe=globe,
        blend_angle=blend_angle,
        ge_sector_angle=ge_sector_angle,
        ge_sector_smoothing=ge_sector_smoothing,
        depth_check=1 if depth_enabled else 0,
        depth_strength=depth_strength,
        depth_decay_sigma=depth_decay_sigma,
        depth_smooth_sigma=depth_smooth_sigma,
        depth_mode=depth_mode,
        pressure_conductivity=pressure_conductivity,
        pressure_sink=pressure_sink,
        scatter_check=1 if scatter_enabled else 0,
        scatter_width=scatter_width,
        scatter_min_val=scatter_min_val,
        scatter_max_val=scatter_max_val,
        scatter_falloff=scatter_falloff,
    )

    if progress_callback:
        progress_callback(0, len(image_files), "Processing images...")

    with multiprocessing.Pool() as pool:
        processed = pool.map(worker, image_files)

    output_folder_name = _get_output_folder_name(
        input_folder, blurring, padding_enabled, globe, edge_enabled, global_enabled,
        global_asymmetric, ge_sector_angle, ge_sector_smoothing, blend_angle,
        depth_enabled, depth_strength, depth_mode, scatter_enabled
    )

    if axial_enabled:
        axial_tag = str(round(float(layer_thickness_um), 2)).replace('.', '_')
        dp_tag = str(round(float(penetration_depth_um), 2)).replace('.', '_')
        output_folder_name = f"{output_folder_name}_ZA_LT{axial_tag}_DP{dp_tag}"

    output_folder = os.path.join(input_folder, output_folder_name)
    os.makedirs(output_folder, exist_ok=True)

    if progress_callback:
        progress_callback(len(image_files), len(image_files), "Saving images...")

    if axial_enabled:
        factors = compute_layer_factors(
            num_layers=len(processed),
            layer_thickness_um=layer_thickness_um,
            penetration_depth_um=penetration_depth_um,
            strength=axial_strength,
            min_factor=axial_min_factor,
        )
        for i, img in enumerate(processed):
            if img is None:
                continue
            processed[i] = np.clip(img.astype(np.float64) * factors[i], 0, 255).astype(np.uint8)

    output_sequence = get_output_sequence(processed, image_files, padding_enabled)
    for img, out_name in output_sequence:
        out_path = os.path.join(output_folder, out_name)
        cv2.imwrite(out_path, img)

    return output_folder
