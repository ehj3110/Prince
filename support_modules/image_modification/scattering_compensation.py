# -*- coding: utf-8 -*-
"""Scattering Compensation Module

Reduces boundary intensity for highly scattering resin materials using a
Gaussian-based model that is the direct inverse of edge enhancement.

Physics motivation:
    UV photons scatter laterally inside the resin vat. A pixel projected
    exactly at the part boundary deposits some dose *outside* that boundary,
    leading to over-cured material that widens features. Pre-dimming boundary
    pixels compensates for this lateral bleed so the net deposited dose
    matches the intended geometry.

Algorithm:
    1. Compute the same edge signal as Edge Enhancement:
           signal = original − GaussianBlur(original)
       This gives a positive peak at boundaries and near-zero at the interior.
    2. Apply the INVERTED normalisation compared to EE:
           EE  maps  high signal (boundary) → max_val (bright)
           SC  maps  high signal (boundary) → min_val (dim)
               and   low signal  (interior) → max_val (bright)
       Concretely:
           normalised  = (signal − lo) / (hi − lo)    # boundary=1, interior=0
           output      = (1 − normalised) × (max_val − min_val) + min_val

    min_val sets how dark the boundary becomes; max_val is the interior ceiling.
    This mirrors the EE API exactly: same sigma, same min_val/max_val semantics,
    just with the normalisation direction flipped.
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

    Uses the same Gaussian edge signal as Edge Enhancement but with the
    normalisation direction inverted: boundary pixels (high signal) are
    mapped to min_val; interior pixels (low signal) are mapped to max_val.

    Args:
        image:    Grayscale image (uint8 or float64, 0–255).
        sigma:    Gaussian sigma — controls how far inward from the boundary
                  the dimming extends.  Larger sigma = wider affected band.
        min_val:  Output intensity at the exact boundary (the darkest value).
                  Analogous to the Min parameter in Edge Enhancement.
                  E.g. 127 means boundary pixels drop to ~50 % intensity.
        max_val:  Output intensity at the interior (the brightest value).
                  Normally 255.
        falloff:  Kernel size for the Gaussian blur (must be odd and > 0).
                  Controls how quickly the Gaussian tails are clipped.
                  Smaller falloff = tighter kernel = less cross-strut
                  interference on dense lattices.  If 0, auto-computed as
                  4*sigma+1 (same as Edge Enhancement default).

    Returns:
        Compensated image as float64 in [0, 255].
    """
    img_float = image.astype(np.float64)

    if sigma <= 0 or min_val >= max_val or not np.any(img_float > 0):
        return img_float

    filter_size = int(falloff) if falloff and falloff > 0 else int(2 * (2 * sigma) + 1)
    if filter_size % 2 == 0:
        filter_size += 1

    blurred = cv2.GaussianBlur(img_float, (filter_size, filter_size), sigma)

    # Edge signal: same direction as EE — positive at boundaries, ~0 at interior
    signal = img_float - blurred

    mask = img_float > 0
    sig_masked = signal[mask]

    lo = np.min(sig_masked)   # near-zero (interior)
    hi = np.max(sig_masked)   # peak (boundary)

    if hi <= lo:
        return img_float  # flat signal — no edge structure to work with

    # Normalise so boundary=1, interior=0, then INVERT before scaling
    normalised = (signal - lo) / (hi - lo)
    scaled = (1.0 - normalised) * (max_val - min_val) + min_val
    scaled[~mask] = 0

    return scaled

