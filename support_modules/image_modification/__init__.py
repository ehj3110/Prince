# -*- coding: utf-8 -*-
"""Image Modification Package

SLA image processing with edge enhancement, global blur enhancement,
and padding normalization. Used by ImageModificationWindow GUI.
"""

from .edge_enhancement import edge_enhance
from .global_enhancement import build_gaussian_map, build_asymmetric_gaussian_map, apply_global_enhancement
from .padding import create_black_padding_image
from .processor import process_single_image, process_folder, process_single_for_preview, generate_cone_images
from .scattering_compensation import apply_scattering_compensation
try:
    from .feature_depth import (build_feature_depth_map, build_pressure_depth_map,
                                 apply_feature_depth_correction)
except ImportError:
    pass

__all__ = [
    'edge_enhance',
    'build_gaussian_map',
    'build_asymmetric_gaussian_map',
    'apply_global_enhancement',
    'create_black_padding_image',
    'process_single_image',
    'process_folder',
    'process_single_for_preview',
    'generate_cone_images',
    'apply_scattering_compensation',
]
