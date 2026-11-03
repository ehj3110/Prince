"""
Z Compensation Utilities

Dedicated utilities for axial print-through compensation in resin printing,
based on a simplified Beer-Lambert attenuation model and Jacobs working curve.

Core model (per pixel):
    D_k_total = sum_{j=k..N-1} E_j * exp(-((j-k) * h) / Dp)

Inverse solver (backward in Z):
    E_k = max(0, D_target_k - sum_{j=k+1..N-1} E_j * exp(-((j-k) * h) / Dp))

Physics parameterization:
    - h: Layer thickness in um
    - Dp: Penetration depth in um
    - Ec: Critical energy in mJ/cm^2
    - Exposure ratio gamma = E0 / Ec: Nominal dose delivered at grayscale 255 relative to Ec
    - D_target = Ec / a = Ec * exp(h / Dp) (exact energy to cure layer thickness h)

Implementation notes:
- Iterates only along Z.
- Uses fully vectorized 2D NumPy operations in XY.
- Supports streaming backward passes with a single 2D carry buffer (low RAM footprint).
- Supports writing output to a memmap path to reduce peak RAM use.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union

import numpy as np


@dataclass(frozen=True)
class ZCompensationConfig:
    """Configuration for axial Z-compensation.

    Attributes:
        layer_thickness_um: Layer thickness in micrometers.
        penetration_depth_um: Resin penetration depth Dp in micrometers.
        critical_energy_ec: Critical energy Ec in mJ/cm^2 (default: 10.0).
        exposure_ratio: Ratio E0 / Ec of nominal uncompensated dose to Ec (default: 2.5).
        target_dose: Optional explicit target dose per active voxel (mJ/cm^2 or arb units).
                     If omitted, Jacobs threshold D_target = Ec * exp(h / Dp) = Ec / a is used.
        strength: Blend between no compensation (0.0) and full compensation (1.0).
        min_factor: Floor for grayscale scaling factors for stability/safety (default: 0.0 for pure energy).
        work_dtype: Floating dtype used for computations.
    """

    layer_thickness_um: float
    penetration_depth_um: float
    critical_energy_ec: float = 10.0
    exposure_ratio: float = 2.5
    target_dose: Optional[float] = None
    strength: float = 1.0
    min_factor: float = 0.0
    work_dtype: np.dtype = np.float32

    def get_target_dose(self) -> float:
        """Return the target dose per active voxel."""
        if self.target_dose is not None:
            return float(self.target_dose)
        a = attenuation_per_layer(self.layer_thickness_um, self.penetration_depth_um)
        if a <= 1e-12:
            return float(self.critical_energy_ec)
        return float(self.critical_energy_ec / a)

    def get_nominal_dose(self) -> float:
        """Return uncompensated single-layer dose E0 = exposure_ratio * Ec."""
        if self.target_dose is not None:
            return float(max(self.target_dose, self.exposure_ratio * self.critical_energy_ec if self.critical_energy_ec != 10.0 else self.target_dose))
        return float(self.exposure_ratio * self.critical_energy_ec)


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

    target_dose = np.array(float(config.get_target_dose()), dtype=dtype)
    nominal_dose = np.array(float(config.get_nominal_dose()), dtype=dtype)
    strength = float(np.clip(config.strength, 0.0, 1.0))
    carry = np.zeros((height, width), dtype=dtype)

    # Backward pass over layers. XY remains vectorized.
    for k in range(z_count - 1, -1, -1):
        active = (mask_volume[k] > 0).astype(dtype)
        target_k = target_dose * active
        ideal_ek = np.maximum(0.0, target_k - carry)
        if strength < 1.0:
            ek = active * ((1.0 - strength) * nominal_dose + strength * ideal_ek)
        else:
            ek = ideal_ek
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
    min_factor = float(np.clip(min_factor, 0.0, 1.0))
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


def solve_single_layer_lookahead(
    image_files: List[str],
    layer_index: int,
    config: ZCompensationConfig,
    active_slice: Optional[np.ndarray] = None,
) -> np.ndarray:
    """Solve the 2D per-pixel compensation factor map f_k(y, x) for a single layer.

    Uses a finite lookahead window above layer_index based on penetration depth Dp.
    For Dp and layer thickness h, after M = ceil(6 * Dp / h) layers, transmission is
    a^M <= exp(-6) < 0.25%, so higher layers contribute negligible print-through.

    Args:
        image_files: Full list of slice file paths in print order (layer 0 to N-1).
        layer_index: 0-based index of the layer to solve.
        config: ZCompensationConfig.
        active_slice: Optional pre-loaded image for layer_index.

    Returns:
        factor_map: 2D array of shape (H, W), dtype float32, with values in [min_factor, 1.0].
    """
    import cv2

    if not image_files or layer_index < 0 or layer_index >= len(image_files):
        if active_slice is not None:
            return np.ones(active_slice.shape, dtype=np.float32)
        return np.ones((1, 1), dtype=np.float32)

    h = max(0.1, float(config.layer_thickness_um))
    dp = max(0.1, float(config.penetration_depth_um))
    a = attenuation_per_layer(h, dp)
    dtype = np.dtype(config.work_dtype)

    # Number of lookahead layers to capture >99.75% of penetrating light
    m_layers = max(1, int(math.ceil(6.0 * dp / h)))
    top_k = min(len(image_files) - 1, layer_index + m_layers)

    # Determine dimensions from target layer or active_slice
    if active_slice is not None:
        height, width = active_slice.shape[:2]
    else:
        sample = cv2.imread(image_files[layer_index], cv2.IMREAD_GRAYSCALE)
        if sample is None:
            return np.ones((1, 1), dtype=dtype)
        height, width = sample.shape[:2]

    target_dose = np.array(config.get_target_dose(), dtype=dtype)
    nominal_dose = np.array(config.get_nominal_dose(), dtype=dtype)
    strength = float(np.clip(config.strength, 0.0, 1.0))
    min_factor = float(np.clip(config.min_factor, 0.0, 1.0))

    carry = np.zeros((height, width), dtype=dtype)

    # Iterate backward from top_k down to layer_index
    for k in range(top_k, layer_index - 1, -1):
        if k == layer_index and active_slice is not None:
            img = active_slice
        else:
            img = cv2.imread(image_files[k], cv2.IMREAD_GRAYSCALE)
            if img is None:
                img = np.zeros((height, width), dtype=np.uint8)

        active = (img > 0).astype(dtype)
        target_k = target_dose * active
        ideal_ek = np.clip(target_k - carry, 0.0, nominal_dose)

        if strength < 1.0:
            ek = active * ((1.0 - strength) * nominal_dose + strength * ideal_ek)
        else:
            ek = ideal_ek

        if k == layer_index:
            factor = np.where(active > 0, ek / max(1e-6, float(nominal_dose)), 0.0)
            factor = np.where(active > 0, np.clip(factor, min_factor, 1.0), 0.0)
            return factor.astype(dtype)

        carry = a * (ek + carry)

    return np.ones((height, width), dtype=dtype)


def stream_axial_compensated_volume(
    image_files: List[str],
    config: ZCompensationConfig,
    progress_callback = None,
) -> List[np.ndarray]:
    """Execute a 3D backward pass across all images, streaming with a single 2D carry array.

    Args:
        image_files: Full list of slice file paths in print order (layer 0 to N-1).
        config: ZCompensationConfig.
        progress_callback: Optional fn(current, total, message).

    Returns:
        compensated_images: List of uint8 images with per-voxel axial attenuation applied.
    """
    import cv2

    n_layers = len(image_files)
    if n_layers == 0:
        return []

    # Read first image to determine dimensions
    first_img = cv2.imread(image_files[0], cv2.IMREAD_GRAYSCALE)
    if first_img is None:
        raise ValueError(f"Could not read first slice image: {image_files[0]}")
    height, width = first_img.shape[:2]

    h = max(0.1, float(config.layer_thickness_um))
    dp = max(0.1, float(config.penetration_depth_um))
    a = attenuation_per_layer(h, dp)
    dtype = np.dtype(config.work_dtype)

    target_dose = np.array(config.get_target_dose(), dtype=dtype)
    nominal_dose = np.array(config.get_nominal_dose(), dtype=dtype)
    strength = float(np.clip(config.strength, 0.0, 1.0))
    min_factor = float(np.clip(config.min_factor, 0.0, 1.0))

    carry = np.zeros((height, width), dtype=dtype)
    compensated_images = [None] * n_layers

    # Backward pass from top layer down to layer 0
    for k in range(n_layers - 1, -1, -1):
        img = cv2.imread(image_files[k], cv2.IMREAD_GRAYSCALE)
        if img is None:
            img = np.zeros((height, width), dtype=np.uint8)

        active = (img > 0).astype(dtype)
        target_k = target_dose * active
        ideal_ek = np.clip(target_k - carry, 0.0, nominal_dose)

        if strength < 1.0:
            ek = active * ((1.0 - strength) * nominal_dose + strength * ideal_ek)
        else:
            ek = ideal_ek

        factor = np.where(active > 0, ek / max(1e-6, float(nominal_dose)), 0.0)
        factor = np.where(active > 0, np.clip(factor, min_factor, 1.0), 0.0)

        compensated = np.clip(img.astype(np.float32) * factor, 0, 255).astype(np.uint8)
        compensated_images[k] = compensated

        carry = a * (ek + carry)

        if progress_callback and (n_layers - k) % max(1, n_layers // 10) == 0:
            progress_callback(n_layers - k, n_layers, f"Axial 3D solver: layer {k + 1}/{n_layers}")

    return compensated_images
