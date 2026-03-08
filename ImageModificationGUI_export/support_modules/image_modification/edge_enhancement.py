# -*- coding: utf-8 -*-
"""Edge Enhancement Module

Gaussian edge enhancement: blur, subtract to isolate edges,
normalize to intensity range, preserve black background.
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
    Replicates MATLAB's Gaussian edge enhancement logic.
    Uses float64 without 0-1 scaling so min/max intensity behave correctly.

    Args:
        original_image: Input image (float64, 0-255 range)
        blurring: Gaussian blur sigma
        filter_size: Kernel size (will be forced odd if even)
        min_val: Minimum output intensity for non-zero pixels
        max_val: Maximum output intensity
        invert: If True, compute (blurred - original) instead of
                (original - blurred).  The result is a Gaussian-shaped
                dip at edges and a flat plateau in the interior — the
                natural inverse of edge enhancement, suitable for
                scattering compensation.

    Returns:
        Edge-enhanced (or inverse edge-enhanced) image (float64)
    """
    if filter_size % 2 == 0:
        filter_size += 1

    blurred_image = cv2.GaussianBlur(original_image, (filter_size, filter_size), blurring)
    if invert:
        edge_enhanced = blurred_image - original_image
    else:
        edge_enhanced = original_image - blurred_image

    mask = original_image > 0
    if not np.any(mask):
        return original_image

    min_i = np.min(edge_enhanced[mask])
    max_i = np.max(edge_enhanced[mask])

    if max_i > min_i:
        normalized = (edge_enhanced - min_i) / (max_i - min_i)
    else:
        normalized = edge_enhanced - min_i

    scaled_image = normalized * (max_val - min_val) + min_val
    scaled_image[~mask] = 0

    return scaled_image
