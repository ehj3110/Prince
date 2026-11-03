# -*- coding: utf-8 -*-
"""Edge Enhancement Module

Gaussian edge enhancement: blur, subtract to isolate edges,
normalize to intensity range, preserve black background.
Optimized for high-throughput batch processing via float32 SIMD vectorization
and fast OpenCV masked min/max localization.
Designed to be composable across pipeline stages.
"""

import cv2
import numpy as np


def edge_enhance(original_image: np.ndarray,
                 blurring: float,
                 filter_size: int,
                 min_val: float,
                 max_val: float,
                 invert: bool = False) -> np.ndarray:
    """
    Replicates Gaussian edge enhancement logic with high-efficiency vectorization.
    Operates internally using single-precision float32 for SIMD performance.
    Computes edge response from the geometry silhouette to cleanly compose with
    upstream stages (e.g. 3D axial Z-compensation) without clobbering internal attenuation.

    Args:
        original_image: Input image (float64 or float32, 0-255 range)
        blurring: Gaussian blur sigma
        filter_size: Kernel size (will be forced odd if even)
        min_val: Minimum output intensity for non-zero pixels
        max_val: Maximum output intensity
        invert: If True, compute (blurred - original) instead of
                (original - blurred). Suitable for inverse edge profiles.

    Returns:
        Edge-enhanced (or inverse edge-enhanced) image (matches input float type)
    """
    is_f64 = original_image.dtype == np.float64
    img = original_image.astype(np.float32, copy=False) if is_f64 else original_image

    mask = img > 0
    if not np.any(mask):
        return original_image

    if filter_size % 2 == 0:
        filter_size += 1
    if filter_size <= 0:
        filter_size = max(3, int(4 * blurring + 1))

    # Base the geometric edge detection on the binary mask (scaled to 255)
    # This prevents internal grayscale variations (from upstream 3D axial compensation)
    # from creating false edges, and enables composable multiplicative application.
    geom_mask = mask.astype(np.float32) * 255.0
    blurred_geom = cv2.GaussianBlur(geom_mask, (filter_size, filter_size), blurring)

    if invert:
        edge_signal = blurred_geom - geom_mask
    else:
        edge_signal = geom_mask - blurred_geom

    # Fast min/max over non-zero region using cv2.minMaxLoc
    mask_u8 = mask.astype(np.uint8)
    min_i, max_i, _, _ = cv2.minMaxLoc(edge_signal, mask=mask_u8)

    if max_i > min_i:
        scale = (max_val - min_val) / (max_i - min_i)
        offset = min_val - scale * min_i
        scaled_profile = edge_signal * scale + offset
    else:
        scaled_profile = edge_signal + (min_val - min_i)

    # Relative multiplier: at boundary, scaled_profile is max_val; in deep interior, min_val.
    multiplier = scaled_profile / 255.0
    scaled_image = img * multiplier
    scaled_image[~mask] = 0.0

    return scaled_image.astype(np.float64, copy=False) if is_f64 else scaled_image
