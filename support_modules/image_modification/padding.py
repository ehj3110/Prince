# -*- coding: utf-8 -*-
"""Padding Module

Generate fully black padding images and handle interleaving with {x}_1.png naming.
"""

import numpy as np


def create_black_padding_image(rows: int, cols: int) -> np.ndarray:
    """
    Create a fully black image with the given resolution.

    Args:
        rows: Image height
        cols: Image width

    Returns:
        uint8 array of zeros
    """
    return np.zeros((rows, cols), dtype=np.uint8)


def get_output_sequence(processed_images: list, source_filenames: list, use_padding: bool) -> list:
    """
    Build the output sequence: for each processed image, optionally append
    a black padding image. Returns list of (image_array, output_filename) tuples.

    Output naming: processed image keeps source base number (e.g., 5.png),
    padding after it is {x}_1.png (e.g., 5_1.png).

    Args:
        processed_images: List of processed uint8 images (or None for failed)
        source_filenames: List of source file paths (for extracting base number)
        use_padding: Whether to insert black padding after each image

    Returns:
        List of (np.ndarray, str) for (image, output_filename)
    """
    import os
    import re

    def extract_base_number(filepath: str) -> int:
        match = re.search(r'\d+', os.path.basename(filepath))
        return int(match.group()) if match else 0

    result = []
    for img, filepath in zip(processed_images, source_filenames):
        if img is None:
            continue
        base_num = extract_base_number(filepath)
        result.append((img, f"{base_num}.png"))
        if use_padding:
            black = create_black_padding_image(img.shape[0], img.shape[1])
            result.append((black, f"{base_num}_1.png"))
    return result
