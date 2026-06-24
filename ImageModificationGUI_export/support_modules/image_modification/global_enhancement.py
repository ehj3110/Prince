# -*- coding: utf-8 -*-
"""Global Blur Enhancement Module.

Symmetric: Gaussian vignette (center darker, edges brighter).
Asymmetric: Angular-sector gradients based on furthest white pixel from center,
with boundary-centered blending.
"""

import numpy as np


def _smoothstep(t: np.ndarray) -> np.ndarray:
    """Smoothstep for blending: 3t^2 - 2t^3, clamps t to [0,1]."""
    t = np.clip(t, 0, 1)
    return 3 * t**2 - 2 * t**3


def build_asymmetric_gaussian_map(image: np.ndarray,
                                 globe: float,
                                 blend_angle_deg: float = 20.0) -> np.ndarray:
    """
    Build an asymmetric vignette map using angular sectors. Each sector has a
    gradient from center (min) to the furthest white pixel in that sector (max).
    Values are blended smoothly near sector boundaries.

    Args:
        image: Grayscale image (uint8 or float) - used to find white (non-zero) pixels
        globe: Minimum value at center (e.g., 0.8 = center is 80% of edge intensity)
        blend_angle_deg: Angular width for blending at sector boundaries (degrees)

    Returns:
        2D float array, same shape as image
    """
    rows, cols = image.shape
    center_x = (cols - 1) / 2.0
    center_y = (rows - 1) / 2.0

    # Meshgrid: x increases left-to-right, y increases top-to-bottom
    y_idx = np.arange(rows)
    x_idx = np.arange(cols)
    X, Y = np.meshgrid(x_idx, y_idx)

    # Distance and angle from center (angle in degrees, 0 = right, 90 = down)
    dX = X - center_x
    dY = Y - center_y
    r = np.sqrt(dX**2 + dY**2)
    theta_deg = np.degrees(np.arctan2(dY, dX))  # -180 to 180
    theta_deg = (theta_deg + 360) % 360  # 0 to 360

    # Sector boundaries distributed evenly around 360°.
    mask_nonzero = image > 0
    if not np.any(mask_nonzero):
        return np.ones_like(image, dtype=np.float64)

    # Find r_max for each sector (furthest white pixel from center)
    r_max_per_quad = np.zeros(4)
    for q in range(4):
        theta_lo = 90 * q
        theta_hi = 90 * (q + 1)
        in_q = mask_nonzero & (theta_deg >= theta_lo) & (theta_deg < theta_hi)
        if np.any(in_q):
            r_max_per_quad[q] = np.max(r[in_q])
        else:
            r_max_per_quad[q] = np.max(r)

    # Avoid division by zero
    r_max_per_quad = np.maximum(r_max_per_quad, 1e-6)

    min_val = globe
    max_val = 1.0

    # For each sector, compute gradient value: min + (max-min) * (r / r_max)
    # r/r_max capped at 1 so we don't exceed max
    map_q0 = min_val + (max_val - min_val) * np.minimum(r / r_max_per_quad[0], 1.0)
    map_q1 = min_val + (max_val - min_val) * np.minimum(r / r_max_per_quad[1], 1.0)
    map_q2 = min_val + (max_val - min_val) * np.minimum(r / r_max_per_quad[2], 1.0)
    map_q3 = min_val + (max_val - min_val) * np.minimum(r / r_max_per_quad[3], 1.0)

    # Build blended map: for each pixel, use its sector's gradient and blend at boundaries
    maps = [map_q0, map_q1, map_q2, map_q3]
    half_blend = blend_angle_deg / 2.0

    result = np.zeros_like(r, dtype=np.float64)
    for q in range(4):
        theta_lo = 90 * q
        theta_hi = 90 * (q + 1)
        in_quadrant = (theta_deg >= theta_lo) & (theta_deg < theta_hi)

        base_val = maps[q]
        blended = base_val.copy()

        # Near lower boundary: blend with previous quadrant
        prev_q = (q - 1) % 4
        dist_to_lo = theta_deg - theta_lo
        in_blend_lo = in_quadrant & (dist_to_lo < half_blend)
        t_lo = np.where(in_blend_lo, dist_to_lo / half_blend, 0)
        w_prev = _smoothstep(t_lo)
        blended = np.where(in_blend_lo, (1 - w_prev) * base_val + w_prev * maps[prev_q], blended)

        # Near upper boundary: blend with next quadrant
        next_q = (q + 1) % 4
        dist_to_hi = theta_hi - theta_deg
        in_blend_hi = in_quadrant & (dist_to_hi < half_blend)
        t_hi = np.where(in_blend_hi, dist_to_hi / half_blend, 0)
        w_next = _smoothstep(t_hi)
        blended = np.where(in_blend_hi, (1 - w_next) * base_val + w_next * maps[next_q], blended)

        result = np.where(in_quadrant, blended, result)

    return result


def build_gaussian_map(rows: int, cols: int, globe: float, sig: float) -> np.ndarray:
    """
    Build a Gaussian vignette map (center lowest, edges highest).
    Used for global blur enhancement.

    Args:
        rows: Image height
        cols: Image width
        globe: Minimum value at center (e.g., 0.8 = center is 80% of edge intensity)
        sig: Sigma divisor (filter_size_global / sig gives sigma)

    Returns:
        2D float array, same shape as image
    """
    min_value = globe
    max_value = 1.0
    filter_size_global = max(rows, cols)
    sigma = filter_size_global / sig

    x = np.arange(1, cols + 1)
    y = np.arange(1, rows + 1)
    X, Y = np.meshgrid(x, y)

    center_x = cols / 2.0
    center_y = rows / 2.0

    gaussian_map = np.exp(-((X - center_x)**2 + (Y - center_y)**2) / (2 * sigma**2))
    gaussian_map = gaussian_map / np.max(gaussian_map)

    gaussian_map = 1.0 - gaussian_map
    gaussian_map = min_value + (max_value - min_value) * gaussian_map

    return gaussian_map


def apply_global_enhancement(image: np.ndarray, gaussian_map: np.ndarray) -> np.ndarray:
    """
    Multiply image by gaussian map and clip to valid range.

    Args:
        image: Input image (float64)
        gaussian_map: Map from build_gaussian_map

    Returns:
        Enhanced image (float64)
    """
    result = image * gaussian_map
    return np.clip(result, 0, 255)
