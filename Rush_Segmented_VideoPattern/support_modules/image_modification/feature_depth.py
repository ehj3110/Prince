# -*- coding: utf-8 -*-
"""Feature Depth Correction Module

Physics-motivated overcuring correction for DLP/SLA resin printing.

Problem:
    Resin flows from the outer resin bath, through black (open) channels,
    to reach white (curing) pixels. As it travels, scattered UV from
    adjacent white pixels partially cures it. Deep or enclosed features
    receive pre-cured resin, leading to overcuring relative to their
    nominal dose.

Algorithm (v3 - perimeter outer pool):

  1. Classify black pixels as exterior-connected or enclosed.

  2. Fill enclosed pores (treat them as white) to produce the outer
     silhouette of the part. Dilate that silhouette by one pixel; the
     newly covered pixels that lie in connected-black are the OUTER RESIN
     POOL — the first ring of fresh resin immediately outside the part
     perimeter. These pixels have channel_depth = 0.

  3. For every other connected-black pixel, channel_depth = Euclidean
     distance to the nearest outer-pool pixel. Channels that penetrate
     deeper into the lattice accumulate more channel_depth and therefore
     carry more pre-cured resin.

  4. Enclosed black pores have no connected path to the outer pool.
     Their channel_depth = (Euclidean distance through white to the
     nearest connected-black pixel) + (channel_depth of that neighbour).
     This estimates how much pre-curing the resin "seeped" through to
     reach a sealed pore.

  5. Spread channel_depth from black pixels into white pixels via Gaussian
     blur. Each white pixel inherits the depth of its surrounding channels.

  6. effective_depth = dist_to_black  +  channel_depth_spread
     (additive: how deep inside the strut  +  how deep the supplying
     channel is). This is monotonically larger toward lattice centres.

  7. Clip outliers at the 99th percentile before normalising to [0, 1] so
     that a single pathological enclosed pore doesn't compress the rest of
     the dynamic range.

  8. Correction: dim white pixels by  (1 - strength * depth_norm).
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

    connected_black = np.zeros((rows, cols), dtype=bool)
    for lbl in border_label_set:
        connected_black |= (labels == lbl)

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
    Build a feature depth correction map.

    Returns a float64 array [0, 1], same shape as image.
      1.0  = deepest pixel (receives most pre-cured resin, needs most dimming)
      0.0  = shallowest pixel (fresh resin, no correction needed)

    Args:
        image:               Grayscale image (uint8 or float64, 0–255)
        channel_decay_sigma: Controls how far the fresh-resin "influence"
                             reaches from the outer pool into the channels.
                             Also used as the spread sigma for blending channel
                             depth into the adjacent white pixels.
        smooth_sigma:        Gaussian sigma to smooth the final depth map
                             (removes sharp medial-axis ridges).
    """
    rows, cols = image.shape
    img_u8 = np.clip(image, 0, 255).astype(np.uint8)

    binary_mask = (img_u8 > 0).astype(np.uint8)   # 1 = white, 0 = black
    black_mask  = 1 - binary_mask

    if not np.any(black_mask) or not np.any(binary_mask):
        return np.zeros((rows, cols), dtype=np.float64)

    connected_black, enclosed_black, border_mask = _classify_black(black_mask)

    # ------------------------------------------------------------------ #
    #  Step 1: Identify the OUTER RESIN POOL                              #
    #  = first ring of connected-black pixels immediately outside the     #
    #    outer perimeter of the part.                                     #
    #                                                                     #
    #  Method:                                                            #
    #   a) Treat enclosed pores as white → filled silhouette of the part. #
    #   b) Dilate that silhouette by 1 px via a 3×3 kernel.              #
    #   c) Any pixel touched by the dilation that is still in             #
    #      connected-black (and not already white/enclosed) is on the     #
    #      first-ring boundary → outer pool, channel_depth = 0.           #
    # ------------------------------------------------------------------ #
    filled_white_u8 = np.clip(
        binary_mask.astype(np.int32) + enclosed_black.astype(np.int32), 0, 1
    ).astype(np.uint8)

    kernel_3x3 = np.ones((3, 3), dtype=np.uint8)
    dilated_silhouette = cv2.dilate(filled_white_u8, kernel_3x3, iterations=1)

    # Pixels added by dilation that are in connected-black = outer pool
    outer_pool = (dilated_silhouette == 1) & (filled_white_u8 == 0) & connected_black

    # Fallback: if the part covers the whole canvas (no exterior black),
    # fall back to the most-open connected-black pixels by dist_to_white.
    if not np.any(outer_pool):
        dist_to_white = cv2.distanceTransform(
            black_mask, cv2.DIST_L2, cv2.DIST_MASK_PRECISE
        ).astype(np.float64)
        vals = dist_to_white[connected_black]
        if len(vals) > 0:
            thr = float(np.percentile(vals, 75))
            outer_pool = connected_black & (dist_to_white >= thr)
    if not np.any(outer_pool):
        outer_pool = connected_black & border_mask   # last resort

    # ------------------------------------------------------------------ #
    #  Step 2: Channel depth for connected-black pixels                   #
    #  = Euclidean distance to nearest outer-pool pixel                   #
    # ------------------------------------------------------------------ #
    dist_src = np.ones((rows, cols), dtype=np.uint8)
    dist_src[outer_pool] = 0
    channel_depth_map = cv2.distanceTransform(
        dist_src, cv2.DIST_L2, cv2.DIST_MASK_PRECISE
    ).astype(np.float64)

    # Apply only to connected-black pixels (outer_pool gets 0, others > 0)
    channel_depth_map = np.where(connected_black, channel_depth_map, 0.0)

    # ------------------------------------------------------------------ #
    #  Step 3: Channel depth for enclosed black pixels                    #
    #  = (distance through white to nearest connected-black channel)      #
    #    + (channel depth of that connected-black neighbour)              #
    # ------------------------------------------------------------------ #
    if np.any(enclosed_black):
        # Euclidean distance from each pixel to nearest connected-black pixel
        dist_to_connected = cv2.distanceTransform(
            (~connected_black).astype(np.uint8),
            cv2.DIST_L2, cv2.DIST_MASK_PRECISE
        ).astype(np.float64)

        # To find the channel_depth of the nearest connected-black neighbour
        # we spread channel_depth_map out of connected-black pixels via a
        # large Gaussian (sigma = channel_decay_sigma) so enclosed pores
        # can pick up their nearest channel's depth.
        spread_for_enclosed = cv2.GaussianBlur(
            channel_depth_map.astype(np.float32), (0, 0), channel_decay_sigma
        ).astype(np.float64)

        # Enclosed pore channel_depth = white thickness + neighbour channel depth
        enclosed_depth = dist_to_connected + spread_for_enclosed
        channel_depth_map = np.where(enclosed_black, enclosed_depth, channel_depth_map)

    # ------------------------------------------------------------------ #
    #  Step 4: Spread channel depth into white pixels                     #
    # ------------------------------------------------------------------ #
    # channel_depth_map is non-zero at black pixels; zero at white.
    # Gaussian blur spreads it into the adjacent white region so every
    # white pixel inherits the depth of its surrounding channels.
    channel_depth_at_black = channel_depth_map * black_mask.astype(np.float64)
    channel_spread = cv2.GaussianBlur(
        channel_depth_at_black.astype(np.float32), (0, 0), channel_decay_sigma * 0.5
    ).astype(np.float64)

    # ------------------------------------------------------------------ #
    #  Step 5: Effective depth (additive)                                 #
    #  = how far into the strut  +  how deep the channel itself is        #
    # ------------------------------------------------------------------ #
    dist_to_black = cv2.distanceTransform(
        binary_mask, cv2.DIST_L2, cv2.DIST_MASK_PRECISE
    ).astype(np.float64)

    effective_depth = dist_to_black + channel_spread
    effective_depth[binary_mask == 0] = 0.0

    # ------------------------------------------------------------------ #
    #  Step 6: Optional smoothing                                         #
    # ------------------------------------------------------------------ #
    if smooth_sigma > 0:
        effective_depth = cv2.GaussianBlur(
            effective_depth.astype(np.float32), (0, 0), smooth_sigma
        ).astype(np.float64)
        effective_depth[binary_mask == 0] = 0.0

    # ------------------------------------------------------------------ #
    #  Step 7: Normalise [0, 1] over white pixels; clip outliers at 99th  #
    #  percentile so one pathological enclosed pore doesn't dominate.     #
    # ------------------------------------------------------------------ #
    white = binary_mask.astype(bool)
    vals = effective_depth[white]
    if len(vals) == 0:
        return np.zeros((rows, cols), dtype=np.float64)

    dmin = float(np.min(vals))
    dmax = float(np.percentile(vals, 99))  # robust max

    if dmax > dmin:
        depth_norm = np.clip((effective_depth - dmin) / (dmax - dmin), 0.0, 1.0)
    else:
        depth_norm = np.zeros_like(effective_depth)

    depth_norm[~white] = 0.0
    return depth_norm


def build_pressure_depth_map(image: np.ndarray,
                              channel_conductivity: float = 100.0,
                              sink_strength: float = 0.1,
                              max_iterations: int = 600,
                              tolerance: float = 5e-4) -> np.ndarray:
    """
    Build a resin starvation map by solving the 2D Poisson equation for
    pressure in a porous medium (Reynolds lubrication approximation).

    Physics model:
        ∇·(K ∇P) = -Q
        K = channel_conductivity  in black (open) channels  → fast flow
        K = 1.0                   in white (solid) features → slow flow
        Q = -sink_strength        at white pixels            → resin consumption
        P = 0                     at the outer resin pool   (Dirichlet BC)

    The solved pressure field P gives the "vacuum" at each point — the
    effort required to pull fresh resin there.  High P = deep starvation
    = more overcuring correction needed.

    Compared to the distance-based map, this model also captures:
      - Channel WIDTH: narrow channels have higher resistance, raise P more.
      - White density: features surrounded by dense struts accumulate higher P.

    Args:
        image:                Grayscale image (uint8 or float64, 0–255)
        channel_conductivity: K ratio for open channels vs solid (default 100).
                              Higher → sharper gradient between edge and centre.
        sink_strength:        Source magnitude at each white pixel.
                              Higher → steeper starvation gradient.
        max_iterations:       Maximum SOR iterations (SOR converges ~4× faster
                              than Jacobi, so 600 iterations ≈ 2400 Jacobi iters).
        tolerance:            Convergence threshold (max pixel change per step).

    Returns:
        float64 depth_norm in [0, 1], same shape as image.
        1.0 = highest starvation (needs most correction).
        0.0 = outer pool / no starvation.
    """
    rows, cols = image.shape
    img_u8 = np.clip(image, 0, 255).astype(np.uint8)
    binary_mask = (img_u8 > 0).astype(np.uint8)   # 1 = white, 0 = black
    black_mask  = 1 - binary_mask

    if not np.any(black_mask) or not np.any(binary_mask):
        return np.zeros((rows, cols), dtype=np.float64)

    connected_black, enclosed_black, border_mask = _classify_black(black_mask)

    # Outer pool (same perimeter-dilation definition as v3)
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

    # ------------------------------------------------------------------ #
    #  Conductivity map                                                    #
    # ------------------------------------------------------------------ #
    K = np.where(binary_mask == 0,
                 float(channel_conductivity), 1.0).astype(np.float64)

    # Source term: white pixels consume resin → positive starvation pressure
    source = binary_mask.astype(np.float64) * float(sink_strength)

    # Dirichlet BC: outer pool + image border → P = 0 (fresh resin)
    dirichlet_mask = outer_pool | border_mask

    # ------------------------------------------------------------------ #
    #  Precompute face-averaged conductivities (constant across iterations)#
    #  K_face = (K[i,j] + K[neighbor]) / 2                               #
    # ------------------------------------------------------------------ #
    K_n = (K + np.roll(K,  1, axis=0)) * 0.5
    K_s = (K + np.roll(K, -1, axis=0)) * 0.5
    K_w = (K + np.roll(K,  1, axis=1)) * 0.5
    K_e = (K + np.roll(K, -1, axis=1)) * 0.5
    denom = np.maximum(K_n + K_s + K_w + K_e, 1e-12)

    # ------------------------------------------------------------------ #
    #  SOR iteration (ω = 1.5 gives ~4× speedup over Jacobi)             #
    #  Update rule: P_new = (1-ω)·P + ω·P_jacobi                        #
    #  P_jacobi = (Σ K_face·P_neighbor + source) / denom                 #
    # ------------------------------------------------------------------ #
    omega = 1.5
    P = np.zeros((rows, cols), dtype=np.float64)

    for iteration in range(max_iterations):
        P_n = np.roll(P,  1, axis=0)
        P_s = np.roll(P, -1, axis=0)
        P_w = np.roll(P,  1, axis=1)
        P_e = np.roll(P, -1, axis=1)

        P_jacobi = (K_n * P_n + K_s * P_s + K_w * P_w + K_e * P_e + source) / denom
        P_new = np.where(dirichlet_mask, 0.0,
                         (1.0 - omega) * P + omega * P_jacobi)

        # Check convergence every 50 iterations
        if (iteration + 1) % 50 == 0:
            if float(np.max(np.abs(P_new - P))) < tolerance:
                P = P_new
                break

        P = P_new

    # ------------------------------------------------------------------ #
    #  Normalise [0, 1] over white pixels only; clip outliers at 99th pct #
    # ------------------------------------------------------------------ #
    white = binary_mask.astype(bool)
    P[~white] = 0.0

    vals = P[white]
    if len(vals) == 0 or float(np.max(vals)) == 0:
        return np.zeros((rows, cols), dtype=np.float64)

    dmin = float(np.min(vals))
    dmax = float(np.percentile(vals, 99))

    if dmax > dmin:
        depth_norm = np.clip((P - dmin) / (dmax - dmin), 0.0, 1.0)
    else:
        depth_norm = np.zeros_like(P)

    depth_norm[~white] = 0.0
    return depth_norm


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
        image:               Float64 image in [0, 255]
        depth_map:           From build_feature_depth_map, values in [0, 1]
        correction_strength: 0.0 = no correction, 1.0 = full correction
        min_intensity:       Floor value; corrected white pixels will not drop
                             below this intensity so features stay visible.

    Returns:
        Corrected image (float64)
    """
    multiplier = 1.0 - correction_strength * depth_map
    result = image * multiplier

    # Apply a constant intensity floor to all originally-white pixels
    # (not proportional to multiplier, which would raise shallowest pixels
    # and compress the correction range).
    mask = image > 0
    result = np.where(mask, np.maximum(result, min_intensity), result)

    return np.clip(result, 0, 255)
