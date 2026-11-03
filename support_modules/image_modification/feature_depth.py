# -*- coding: utf-8 -*-
"""Feature Depth Correction Module

Physics-motivated overcuring correction for DLP/SLA resin printing.

Problem:
    Resin flows from the outer resin bath, through black (open) channels,
    to reach white (curing) pixels. As it travels, scattered UV from
    adjacent white pixels partially cures it. Deep or enclosed features
    receive pre-cured resin, leading to overcuring relative to their
    nominal dose.

Algorithm (v3 - perimeter outer pool + physical scale):
  1. Classify black pixels as exterior-connected or enclosed.
  2. Find outer resin pool immediately outside the part perimeter (depth = 0).
  3. Channel depth for connected black = distance to nearest outer-pool pixel.
  4. Channel depth for enclosed black = distance through white + nearest channel depth.
  5. Normalized convolution spreads channel depth into white pixels without dilution.
  6. Effective depth = distance into strut + channel spread.
  7. Physical scale normalization: saturating exponential 1 - exp(-depth / D_char)
     so small isolated features are not artificially over-dimmed.
  8. Correction: dim white pixels by (1 - strength * depth_norm).
"""

import cv2
import numpy as np


def _classify_black(black_mask: np.ndarray):
    """Return (connected_black, enclosed_black, border_mask) bool arrays."""
    rows, cols = black_mask.shape
    num_labels, labels = cv2.connectedComponents(black_mask)

    border_mask = np.zeros((rows, cols), dtype=bool)
    border_mask[0, :] = True
    border_mask[-1, :] = True
    border_mask[:, 0] = True
    border_mask[:, -1] = True

    border_label_set = set(labels[border_mask & (black_mask == 1)].ravel())
    border_label_set.discard(0)

    if border_label_set:
        connected_black = np.isin(labels, list(border_label_set))
    else:
        connected_black = np.zeros((rows, cols), dtype=bool)

    enclosed_black = (black_mask == 1) & ~connected_black
    return connected_black, enclosed_black, border_mask


def _ray_white_integral(image: np.ndarray,
                        y0: int, x0: int,
                        y1: int, x1: int) -> float:
    """Sum image values along a Bresenham line from (y0,x0) to (y1,x1)."""
    rows, cols = image.shape
    dy = abs(y1 - y0)
    dx = abs(x1 - x0)
    sy = 1 if y1 > y0 else -1
    sx = 1 if x1 > x0 else -1
    err = dx - dy
    total = 0.0
    y, x = y0, x0
    while True:
        if 0 <= y < rows and 0 <= x < cols:
            total += float(image[y, x])
        if y == y1 and x == x1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy
    return total


def build_feature_depth_map(image: np.ndarray,
                             channel_decay_sigma: float = 50.0,
                             smooth_sigma: float = 10.0) -> np.ndarray:
    """
    Build a feature depth correction map using physical scale normalization.

    Returns a float64 array [0, 1], same shape as image.
      1.0  = deepest pixel (receives most pre-cured resin, needs most dimming)
      0.0  = shallowest pixel (fresh resin, no correction needed)

    Args:
        image:               Grayscale image (uint8 or float64, 0–255)
        channel_decay_sigma: Controls how far the fresh-resin "influence"
                             reaches from the outer pool into the channels.
        smooth_sigma:        Gaussian sigma to smooth the final depth map.
    """
    rows, cols = image.shape
    img_u8 = np.clip(image, 0, 255).astype(np.uint8)

    binary_mask = (img_u8 > 0).astype(np.uint8)   # 1 = white, 0 = black
    black_mask  = 1 - binary_mask

    if not np.any(black_mask) or not np.any(binary_mask):
        return np.zeros((rows, cols), dtype=np.float64)

    connected_black, enclosed_black, border_mask = _classify_black(black_mask)

    # Step 1: Identify outer resin pool
    filled_white_u8 = np.clip(
        binary_mask.astype(np.int32) + enclosed_black.astype(np.int32), 0, 1
    ).astype(np.uint8)

    kernel_3x3 = np.ones((3, 3), dtype=np.uint8)
    dilated_silhouette = cv2.dilate(filled_white_u8, kernel_3x3, iterations=1)
    outer_pool = (dilated_silhouette == 1) & (filled_white_u8 == 0) & connected_black

    if not np.any(outer_pool):
        dist_to_white = cv2.distanceTransform(
            black_mask, cv2.DIST_L2, cv2.DIST_MASK_PRECISE
        ).astype(np.float64)
        vals = dist_to_white[connected_black]
        if len(vals) > 0:
            thr = float(np.percentile(vals, 75))
            outer_pool = connected_black & (dist_to_white >= thr)
    if not np.any(outer_pool):
        outer_pool = connected_black & border_mask

    # Step 2: Channel depth for connected-black pixels
    dist_src = np.ones((rows, cols), dtype=np.uint8)
    dist_src[outer_pool] = 0
    channel_depth_map = cv2.distanceTransform(
        dist_src, cv2.DIST_L2, cv2.DIST_MASK_PRECISE
    ).astype(np.float64)
    channel_depth_map = np.where(connected_black, channel_depth_map, 0.0)

    # Step 3: Channel depth for enclosed black pixels
    if np.any(enclosed_black):
        dist_to_connected = cv2.distanceTransform(
            (~connected_black).astype(np.uint8),
            cv2.DIST_L2, cv2.DIST_MASK_PRECISE
        ).astype(np.float64)

        spread_for_enclosed = cv2.GaussianBlur(
            channel_depth_map.astype(np.float32), (0, 0), channel_decay_sigma
        ).astype(np.float64)

        enclosed_depth = dist_to_connected + spread_for_enclosed
        channel_depth_map = np.where(enclosed_black, enclosed_depth, channel_depth_map)

    # Step 4: Spread channel depth into white pixels using normalized convolution
    channel_depth_at_black = channel_depth_map * black_mask.astype(np.float64)
    num = cv2.GaussianBlur(
        channel_depth_at_black.astype(np.float32), (0, 0), channel_decay_sigma * 0.5
    ).astype(np.float64)
    den = cv2.GaussianBlur(
        black_mask.astype(np.float32), (0, 0), channel_decay_sigma * 0.5
    ).astype(np.float64)
    channel_spread = np.where(den > 1e-5, num / np.maximum(den, 1e-5), 0.0)

    # Step 5: Effective depth (distance into strut + channel spread)
    dist_to_black = cv2.distanceTransform(
        binary_mask, cv2.DIST_L2, cv2.DIST_MASK_PRECISE
    ).astype(np.float64)

    effective_depth = dist_to_black + channel_spread
    effective_depth[binary_mask == 0] = 0.0

    # Step 6: Optional smoothing
    if smooth_sigma > 0:
        effective_depth = cv2.GaussianBlur(
            effective_depth.astype(np.float32), (0, 0), smooth_sigma
        ).astype(np.float64)
        effective_depth[binary_mask == 0] = 0.0

    # Step 7: Saturating physical scale normalization
    white = binary_mask.astype(bool)
    if not np.any(white):
        return np.zeros((rows, cols), dtype=np.float64)

    char_depth = 2.0 * max(1.0, float(channel_decay_sigma))
    depth_norm = np.where(white, 1.0 - np.exp(-effective_depth / char_depth), 0.0)
    depth_norm = np.clip(depth_norm, 0.0, 1.0)
    return depth_norm.astype(np.float64)


def build_pressure_depth_map(image: np.ndarray,
                              channel_conductivity: float = 100.0,
                              sink_strength: float = 0.1,
                              max_iterations: int = 600,
                              tolerance: float = 5e-4) -> np.ndarray:
    """
    Build a resin starvation map by solving the 2D Poisson equation for
    pressure in a porous medium with coarse-grid acceleration.

    Args:
        image:                Grayscale image (uint8 or float64, 0–255)
        channel_conductivity: K ratio for open channels vs solid (default 100).
        sink_strength:        Source magnitude at each white pixel.
        max_iterations:       Maximum SOR iterations.
        tolerance:            Convergence threshold.

    Returns:
        float64 depth_norm in [0, 1], same shape as image.
    """
    rows, cols = image.shape
    img_u8 = np.clip(image, 0, 255).astype(np.uint8)

    # Use 2x or 4x coarse grid for fast convergence and wider information horizon on large grids
    scale = 4 if (rows >= 400 and cols >= 400) else (2 if (rows >= 200 and cols >= 200) else 1)
    if scale > 1:
        c_rows, c_cols = rows // scale, cols // scale
        c_img = cv2.resize(img_u8, (c_cols, c_rows), interpolation=cv2.INTER_AREA)
    else:
        c_rows, c_cols = rows, cols
        c_img = img_u8

    binary_mask = (c_img > 0).astype(np.uint8)
    black_mask = 1 - binary_mask

    if not np.any(black_mask) or not np.any(binary_mask):
        return np.zeros((rows, cols), dtype=np.float64)

    connected_black, enclosed_black, border_mask = _classify_black(black_mask)

    filled_white_u8 = np.clip(
        binary_mask.astype(np.int32) + enclosed_black.astype(np.int32), 0, 1
    ).astype(np.uint8)
    kernel_3x3 = np.ones((3, 3), dtype=np.uint8)
    dilated_silhouette = cv2.dilate(filled_white_u8, kernel_3x3, iterations=1)
    outer_pool = (dilated_silhouette == 1) & (filled_white_u8 == 0) & connected_black

    if not np.any(outer_pool):
        dist_to_white = cv2.distanceTransform(
            black_mask, cv2.DIST_L2, cv2.DIST_MASK_PRECISE
        ).astype(np.float64)
        vals = dist_to_white[connected_black]
        if len(vals) > 0:
            thr = float(np.percentile(vals, 75))
            outer_pool = connected_black & (dist_to_white >= thr)
    if not np.any(outer_pool):
        outer_pool = connected_black & border_mask

    K = np.where(binary_mask == 0, float(channel_conductivity), 1.0).astype(np.float64)
    source = binary_mask.astype(np.float64) * float(sink_strength)
    dirichlet_mask = outer_pool | border_mask

    K_n = (K + np.roll(K, 1, axis=0)) * 0.5
    K_s = (K + np.roll(K, -1, axis=0)) * 0.5
    K_w = (K + np.roll(K, 1, axis=1)) * 0.5
    K_e = (K + np.roll(K, -1, axis=1)) * 0.5
    denom = np.maximum(K_n + K_s + K_w + K_e, 1e-12)

    omega = 1.0  # Stable Jacobi/Gauss relaxation
    P = np.zeros((c_rows, c_cols), dtype=np.float64)

    for iteration in range(max_iterations):
        P_n = np.roll(P, 1, axis=0)
        P_s = np.roll(P, -1, axis=0)
        P_w = np.roll(P, 1, axis=1)
        P_e = np.roll(P, -1, axis=1)

        P_jacobi = (K_n * P_n + K_s * P_s + K_w * P_w + K_e * P_e + source) / denom
        P_new = np.where(dirichlet_mask, 0.0, (1.0 - omega) * P + omega * P_jacobi)

        if (iteration + 1) % 40 == 0:
            if float(np.max(np.abs(P_new - P))) < tolerance:
                P = P_new
                break
        P = P_new

    # Upsample if solved on coarse grid
    if scale > 1:
        P_full = cv2.resize(P, (cols, rows), interpolation=cv2.INTER_LINEAR).astype(np.float64)
    else:
        P_full = P

    full_white = (img_u8 > 0)
    P_full[~full_white] = 0.0

    if not np.any(full_white):
        return np.zeros((rows, cols), dtype=np.float64)

    char_pressure = max(1e-4, float(sink_strength) * float(channel_conductivity) * 5.0)
    depth_norm = np.where(full_white, 1.0 - np.exp(-P_full / char_pressure), 0.0)
    depth_norm = np.clip(depth_norm, 0.0, 1.0)
    return depth_norm.astype(np.float64)


def apply_feature_depth_correction(image: np.ndarray,
                                    depth_map: np.ndarray,
                                    correction_strength: float,
                                    min_intensity: float = 100.0) -> np.ndarray:
    """
    Dim white pixels proportionally to their effective depth.

    Correction multiplier = 1 - strength * depth_map
    Deepest pixel (depth=1) → multiplied by (1 - strength).
    Shallowest pixel (depth=0) → unchanged.
    Black pixels are untouched.

    Args:
        image:               Float64 or float32 image in [0, 255]
        depth_map:           From build_feature_depth_map, values in [0, 1]
        correction_strength: 0.0 = no correction, 1.0 = full correction
        min_intensity:       Floor value; corrected white pixels will not drop
                             below this intensity so features stay visible.

    Returns:
        Corrected image (same float type as input or float64)
    """
    multiplier = 1.0 - correction_strength * depth_map
    result = image * multiplier

    mask = image > 0
    result = np.where(mask, np.maximum(result, min_intensity), result)
    return np.clip(result, 0, 255)
