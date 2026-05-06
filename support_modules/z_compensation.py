"""
Z Compensation Utilities

Dedicated utilities for axial print-through compensation in resin printing,
based on a simplified Beer-Lambert attenuation model.

Core model (per pixel):
    D_k_total = sum_{j=k..N-1} E_j * exp(-((j-k) * h) / Dp)

Inverse solver (backward in Z):
    E_k = max(0, D_target_k - sum_{j=k+1..N-1} E_j * exp(-((j-k) * h) / Dp))

Implementation notes:
- Iterates only along Z.
- Uses fully vectorized 2D NumPy operations in XY.
- Supports writing output to a memmap path to reduce peak RAM use.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import numpy as np


@dataclass(frozen=True)
class ZCompensationConfig:
    """Configuration for axial Z-compensation.

    Attributes:
        layer_thickness_um: Layer thickness in micrometers.
        penetration_depth_um: Resin penetration depth Dp in micrometers.
        target_dose: Target threshold dose per active voxel (arbitrary units).
        strength: Blend between no compensation (0.0) and full compensation (1.0).
        min_factor: Floor for grayscale scaling factors for stability/safety.
        work_dtype: Floating dtype used for computations.
    """

    layer_thickness_um: float
    penetration_depth_um: float
    target_dose: float = 1.0
    strength: float = 1.0
    min_factor: float = 0.25
    work_dtype: np.dtype = np.float32


def attenuation_per_layer(layer_thickness_um: float, penetration_depth_um: float) -> float:
    """Return Beer-Lambert attenuation factor for one layer step.

    Args:
        layer_thickness_um: Layer thickness in micrometers.
        penetration_depth_um: Resin penetration depth Dp in micrometers.

    Returns:
        Scalar attenuation factor in (0, 1] for one layer depth increment.
    """
    if layer_thickness_um <= 0 or penetration_depth_um <= 0:
        return 1.0
    return math.exp(-float(layer_thickness_um) / float(penetration_depth_um))


def estimate_stack_memory(
    num_layers: int,
    height: int,
    width: int,
    mask_dtype: np.dtype = np.uint8,
    exposure_dtype: np.dtype = np.float32,
) -> Dict[str, int]:
    """Estimate memory footprint for a Z stack and working arrays.

    Args:
        num_layers: Number of layers (Z).
        height: Pixels in Y.
        width: Pixels in X.
        mask_dtype: dtype for binary/mask stack.
        exposure_dtype: dtype for exposure stack.

    Returns:
        Dict with byte estimates for key arrays and total in-memory estimate.
    """
    voxel_count = int(num_layers) * int(height) * int(width)
    mask_bytes = voxel_count * np.dtype(mask_dtype).itemsize
    exposure_bytes = voxel_count * np.dtype(exposure_dtype).itemsize
    plane_work_bytes = int(height) * int(width) * np.dtype(exposure_dtype).itemsize
    total_with_one_work_plane = mask_bytes + exposure_bytes + (2 * plane_work_bytes)

    return {
        "voxel_count": voxel_count,
        "mask_stack_bytes": mask_bytes,
        "exposure_stack_bytes": exposure_bytes,
        "single_plane_work_bytes": plane_work_bytes,
        "estimated_total_bytes": total_with_one_work_plane,
    }


def format_bytes(n_bytes: int) -> str:
    """Human-readable byte string."""
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(n_bytes)
    idx = 0
    while value >= 1024.0 and idx < len(units) - 1:
        value /= 1024.0
        idx += 1
    return f"{value:.2f} {units[idx]}"


def solve_exposure_volume_backward(
    mask_volume: np.ndarray,
    config: ZCompensationConfig,
    out_path: Optional[str] = None,
) -> np.ndarray:
    """Solve per-voxel exposure map using backward Beer-Lambert inversion.

    Args:
        mask_volume: 3D array shape (Z, Y, X), values interpreted as active voxels.
            Non-zero voxels are considered printable targets.
        config: ZCompensationConfig parameters.
        out_path: Optional file path for np.memmap output. If provided, returns
            a memmap-backed array and reduces peak RAM.

    Returns:
        exposure_map: float array shape (Z, Y, X), dtype=config.work_dtype.

    Notes:
    - Loops only over Z, never over X/Y.
    - Uses vectorized 2D operations for each layer.
    """
    if mask_volume.ndim != 3:
        raise ValueError("mask_volume must be 3D with shape (Z, Y, X)")

    z_count, height, width = mask_volume.shape
    dtype = np.dtype(config.work_dtype)

    if out_path:
        out_dir = os.path.dirname(os.path.abspath(out_path))
        if out_dir and not os.path.isdir(out_dir):
            os.makedirs(out_dir, exist_ok=True)
        exposure = np.memmap(out_path, mode="w+", dtype=dtype, shape=(z_count, height, width))
    else:
        exposure = np.zeros((z_count, height, width), dtype=dtype)

    attenuation = np.array(
        attenuation_per_layer(config.layer_thickness_um, config.penetration_depth_um),
        dtype=dtype,
    )

    target_dose = np.array(float(config.target_dose), dtype=dtype)
    carry = np.zeros((height, width), dtype=dtype)

    # Backward pass over layers. XY remains vectorized.
    for k in range(z_count - 1, -1, -1):
        target_k = target_dose * (mask_volume[k] > 0).astype(dtype)
        ek = np.maximum(0.0, target_k - carry)
        exposure[k] = ek
        carry = attenuation * (ek + carry)

    return exposure


def compute_layer_factors(
    num_layers: int,
    layer_thickness_um: float,
    penetration_depth_um: float,
    strength: float = 1.0,
    min_factor: float = 0.25,
) -> list:
    """Compute per-layer scalar compensation factors (fast approximation).

    This is a lightweight layer-wise version intended for grayscale scaling in
    image preprocessing flows where per-voxel inversion is not yet applied.

    Args:
        num_layers: Total number of layers.
        layer_thickness_um: Layer thickness in micrometers.
        penetration_depth_um: Resin penetration depth Dp in micrometers.
        strength: Blend between no compensation (0) and full (1).
        min_factor: Lower clip bound for stability.

    Returns:
        List of factors in [min_factor, 1.0], one per layer.
    """
    if num_layers <= 0:
        return []
    if layer_thickness_um <= 0 or penetration_depth_um <= 0:
        return [1.0] * num_layers

    strength = float(np.clip(strength, 0.0, 1.0))
    min_factor = float(np.clip(min_factor, 0.01, 1.0))
    a = attenuation_per_layer(layer_thickness_um, penetration_depth_um)

    factors = []
    for layer_idx in range(num_layers):
        future_count = num_layers - 1 - layer_idx
        if future_count <= 0:
            extra_dose = 0.0
        elif abs(1.0 - a) < 1e-12:
            extra_dose = float(future_count)
        else:
            extra_dose = a * (1.0 - a ** future_count) / (1.0 - a)

        ideal_factor = 1.0 / (1.0 + extra_dose)
        blended = (1.0 - strength) + (strength * ideal_factor)
        factors.append(float(np.clip(blended, min_factor, 1.0)))

    return factors


def per_layer_dose_schedule(
    num_layers: int,
    layer_thickness_um: float,
    penetration_depth_um: float,
    d_target: float,
) -> np.ndarray:
    """Compute 1D per-layer exposure schedule using backward inversion.

    Useful for quick calibration checks and unit tests.
    """
    if num_layers <= 0:
        return np.zeros((0,), dtype=np.float64)
    a = attenuation_per_layer(layer_thickness_um, penetration_depth_um)
    d_target = float(max(0.0, d_target))
    e = np.zeros((num_layers,), dtype=np.float64)
    carry = 0.0

    for k in range(num_layers - 1, -1, -1):
        e[k] = max(0.0, d_target - carry)
        carry = a * (e[k] + carry)

    return e
