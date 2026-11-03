# -*- coding: utf-8 -*-
"""Scattering Compensation Module

Reduces boundary intensity for highly scattering resin materials using a
Gaussian-based model that is the direct inverse of edge enhancement.
Optimized with float32 SIMD vectorization and fast OpenCV masked min/max localization.
Designed to be composable across pipeline stages.

Physics motivation:
    UV photons scatter laterally inside the resin vat. A pixel projected
    exactly at the part boundary deposits some dose *outside* that boundary,
    leading to over-cured material that widens features. Pre-dimming boundary
    pixels compensates for this lateral bleed so the net deposited dose
    matches the intended geometry.

Algorithm:
    1. Compute the edge signal from the part geometry:
           signal = geom_mask − GaussianBlur(geom_mask)
       This gives a positive peak at boundaries and near-zero at the interior.
    2. Apply inverted normalisation:
           Boundary (high signal) → min_val (dim)
           Interior (low signal)  → max_val (bright)
    3. Apply as a composable multiplier (scaled / 255.0) to preserve upstream
       attenuation from 3D axial Z-compensation.
"""

import cv2
import numpy as np


def apply_scattering_compensation(image: np.ndarray,
                                   sigma: float,
                                   min_val: float,
                                   max_val: float,
                                   falloff: int = 0) -> np.ndarray:
    """
    Dim pixels near part boundaries to compensate for lateral UV scatter.

    Uses the Gaussian edge signal but with the normalisation direction inverted:
    boundary pixels (high signal) are mapped to min_val; interior pixels (low signal)
    are mapped to max_val.

    Args:
        image:    Grayscale image (uint8 or float64/float32, 0–255).
        sigma:    Gaussian sigma — controls how far inward from the boundary
                  the dimming extends.
        min_val:  Output intensity at the exact boundary (the darkest value).
        max_val:  Output intensity at the interior (the brightest value).
        falloff:  Kernel size for the Gaussian blur (must be odd and > 0).

    Returns:
        Compensated image matching input float type or float64 in [0, 255].
    """
    if sigma <= 0 or min_val >= max_val or not np.any(image > 0):
        return image.astype(np.float64, copy=False) if image.dtype == np.float64 else image

    is_f64 = image.dtype == np.float64
    img = image.astype(np.float32, copy=False) if is_f64 else image

    mask = img > 0
    if not np.any(mask):
        return image.astype(np.float64, copy=False) if image.dtype == np.float64 else image

    filter_size = int(falloff) if falloff and falloff > 0 else int(2 * (2 * sigma) + 1)
    if filter_size % 2 == 0:
        filter_size += 1
    if filter_size <= 0:
        filter_size = max(3, int(4 * sigma + 1))

    geom_mask = mask.astype(np.float32) * 255.0
    blurred = cv2.GaussianBlur(geom_mask, (filter_size, filter_size), sigma)
    signal = geom_mask - blurred

    mask_u8 = mask.astype(np.uint8)
    lo, hi, _, _ = cv2.minMaxLoc(signal, mask=mask_u8)

    if hi <= lo:
        return image.astype(np.float64, copy=False) if is_f64 else image

    # Normalise so boundary=1, interior=0, then INVERT before scaling
    scale = (max_val - min_val) / (hi - lo)
    scaled = (max_val + scale * lo) - signal * scale
    multiplier = scaled / 255.0
    out = img * multiplier
    out[~mask] = 0.0

    return out.astype(np.float64, copy=False) if is_f64 else out
