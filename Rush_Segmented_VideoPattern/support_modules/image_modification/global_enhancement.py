# -*- coding: utf-8 -*-
"""Global Blur Enhancement Module.

Symmetric: Gaussian vignette (center darker, edges brighter).
Asymmetric: Angular-sector gradients based on furthest white pixel from center,
with continuous interpolation across sector boundaries.
"""

import numpy as np


def _smoothstep(t: np.ndarray) -> np.ndarray:
    """Smoothstep for blending: 3t^2 - 2t^3, clamps t to [0,1]."""
    t = np.clip(t, 0, 1)
    return 3 * t**2 - 2 * t**3


def _fill_missing_sector_rmax(values: np.ndarray, fallback: float) -> np.ndarray:
    """Fill NaN sectors via circular interpolation."""
    if values.size == 0:
        return values
    valid = ~np.isnan(values)
    if not np.any(valid):
        return np.full_like(values, float(fallback), dtype=np.float64)

    n = values.size
    idx = np.arange(n, dtype=np.float64)
    valid_idx = idx[valid]
    valid_vals = values[valid]

    ext_idx = np.concatenate((valid_idx - n, valid_idx, valid_idx + n))
    ext_vals = np.concatenate((valid_vals, valid_vals, valid_vals))
    return np.interp(idx, ext_idx, ext_vals)


def _smooth_circular(values: np.ndarray, half_window: int) -> np.ndarray:
    """Circular moving-average smoothing."""
    half_window = max(0, int(half_window))
    if half_window == 0 or values.size <= 1:
        return values
    kernel_size = 2 * half_window + 1
    kernel = np.ones(kernel_size, dtype=np.float64) / float(kernel_size)
    padded = np.pad(values, (half_window, half_window), mode="wrap")
    return np.convolve(padded, kernel, mode="valid")


def _sample_blended_circular_profile(theta_deg: np.ndarray,
                                     profile: np.ndarray,
                                     sector_angle_deg: float,
                                     blend_angle_deg: float) -> np.ndarray:
    """Sample an evenly spaced circular profile with boundary-centered crossfades."""
    sector_angle_deg = float(sector_angle_deg)
    blend_angle_deg = max(0.0, float(blend_angle_deg))
    sector_count = profile.size
    if sector_count == 1:
        return np.full_like(theta_deg, float(profile[0]), dtype=np.float64)

    profile = np.asarray(profile, dtype=np.float64)
    theta = np.asarray(theta_deg, dtype=np.float64) % 360.0
    sector_pos = theta / sector_angle_deg
    left_idx = np.floor(sector_pos).astype(np.int32) % sector_count
    frac = sector_pos - np.floor(sector_pos)
    right_idx = (left_idx + 1) % sector_count

    if blend_angle_deg <= 0:
        return profile[left_idx]

    half_width_deg = 0.5 * blend_angle_deg
    if half_width_deg <= 0:
        return profile[left_idx]

    result = profile[left_idx].astype(np.float64, copy=True)

    # Find nearest sector boundary in degrees and blend only around that boundary.
    boundary_idx = np.rint(theta / sector_angle_deg).astype(np.int32) % sector_count
    boundary_angle = boundary_idx * sector_angle_deg
    delta = ((theta - boundary_angle + 180.0) % 360.0) - 180.0

    in_blend = np.abs(delta) <= half_width_deg
    if np.any(in_blend):
        # Boundary k separates sector k-1 (left) and sector k (right).
        left_boundary_idx = (boundary_idx[in_blend] - 1) % sector_count
        right_boundary_idx = boundary_idx[in_blend]
        t = (delta[in_blend] + half_width_deg) / (2.0 * half_width_deg)
        w = _smoothstep(t)
        result[in_blend] = (1.0 - w) * profile[left_boundary_idx] + w * profile[right_boundary_idx]

    return result


def build_angular_asymmetric_map(
    image: np.ndarray,
    globe: float,
    sector_angle_deg: float = 10.0,
    blend_angle_deg: float = 10.0,
    smooth_window_sectors: int = 1,
) -> np.ndarray:
    """Build an asymmetric vignette map using angular sectors.

    Each sector gets its own furthest-white radius. Per-pixel radii are blended
    with neighboring sectors near boundaries for smooth transitions.
    """
    sector_angle_deg = float(sector_angle_deg)
    if sector_angle_deg <= 0:
        raise ValueError("sector_angle_deg must be > 0")
    if sector_angle_deg > 180:
        raise ValueError("sector_angle_deg must be <= 180")

    blend_angle_deg = max(0.0, float(blend_angle_deg))
    smooth_window_sectors = max(0, int(smooth_window_sectors))

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

    # Sector setup
    sector_count = max(1, int(round(360.0 / sector_angle_deg)))
    actual_sector_angle = 360.0 / float(sector_count)

    mask_nonzero = image > 0
    if not np.any(mask_nonzero):
        return np.ones_like(image, dtype=np.float64)

    sector_idx = np.floor(theta_deg / actual_sector_angle).astype(np.int32) % sector_count

    # Find r_max for each sector; fill sparse sectors from neighbors.
    r_max_per_sector = np.full(sector_count, np.nan, dtype=np.float64)
    for s in range(sector_count):
        in_s = mask_nonzero & (sector_idx == s)
        if np.any(in_s):
            r_max_per_sector[s] = float(np.max(r[in_s]))
    global_rmax = float(np.max(r[mask_nonzero]))
    r_max_per_sector = _fill_missing_sector_rmax(r_max_per_sector, fallback=global_rmax)
    r_max_per_sector = _smooth_circular(r_max_per_sector, smooth_window_sectors)
    r_max_per_sector = np.maximum(r_max_per_sector, 1e-6)

    min_val = globe
    max_val = 1.0

    rmax_eff = _sample_blended_circular_profile(
        theta_deg,
        r_max_per_sector,
        actual_sector_angle,
        blend_angle_deg,
    )

    result = min_val + (max_val - min_val) * np.minimum(r / rmax_eff, 1.0)
    return result


def build_asymmetric_gaussian_map(
    image: np.ndarray,
    globe: float,
    blend_angle_deg: float = 20.0,
) -> np.ndarray:
    """Compatibility wrapper for the legacy 4-quadrant asymmetric map."""
    return build_angular_asymmetric_map(
        image=image,
        globe=globe,
        sector_angle_deg=90.0,
        blend_angle_deg=blend_angle_deg,
        smooth_window_sectors=0,
    )


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
