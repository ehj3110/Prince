"""
Image Edge Enhancement Module

Replicates the MATLAB edge enhancement algorithm:
1. Apply Gaussian blur to the original image
2. Subtract blurred from original to extract edges
3. Normalize to specified intensity range (default: 100-255)
4. Preserve background (zero) pixels

Author: Copilot
Date: January 2026
"""

import numpy as np
import cv2
from pathlib import Path
from typing import Tuple, Optional
import re


def edge_enhance_image(original_image: np.ndarray, 
                      blur_sigma: float = 25.0,
                      min_intensity: int = 100,
                      max_intensity: int = 255) -> np.ndarray:
    """
    Apply edge enhancement to a grayscale image.
    
    This replicates the MATLAB algorithm:
    - Gaussian blur with specified sigma
    - Subtract blurred from original to get edges
    - Normalize edges to [min_intensity, max_intensity] range
    - Preserve zero (background) pixels
    
    Args:
        original_image: Input grayscale image (uint8)
        blur_sigma: Standard deviation for Gaussian blur (default: 25)
        min_intensity: Minimum output intensity for non-zero pixels (default: 100)
        max_intensity: Maximum output intensity (default: 255)
    
    Returns:
        Enhanced image (uint8)
    """
    # Convert to float for processing
    img_float = original_image.astype(np.float64) / 255.0
    
    # Calculate filter size (matches MATLAB: 2*(2*sigma)+1)
    filter_size = int(2 * (2 * blur_sigma) + 1)
    # Ensure odd
    if filter_size % 2 == 0:
        filter_size += 1
    
    # Apply Gaussian blur
    blurred = cv2.GaussianBlur(img_float, (filter_size, filter_size), blur_sigma)
    
    # Extract edges by subtracting blurred from original
    edge_enhanced = img_float - blurred
    
    # Find max and min intensities (excluding zero values in original)
    mask_nonzero = original_image > 0
    if np.any(mask_nonzero):
        edge_values = edge_enhanced[mask_nonzero]
        max_val = np.max(edge_values)
        min_val = np.min(edge_values)
        
        # Normalize to [min_intensity, max_intensity] range
        if max_val > min_val:
            edge_enhanced = (edge_enhanced - min_val) / (max_val - min_val)
            edge_enhanced = edge_enhanced * (max_intensity - min_intensity) + min_intensity
        else:
            # If all edge values are the same, just map to mid-range
            edge_enhanced = np.full_like(edge_enhanced, (min_intensity + max_intensity) / 2)
    
    # Preserve background (zero pixels in original)
    edge_enhanced[~mask_nonzero] = 0
    
    # Convert back to uint8
    edge_enhanced = np.clip(edge_enhanced, 0, 255).astype(np.uint8)
    
    return edge_enhanced


def process_folder(input_folder: str,
                  output_folder: Optional[str] = None,
                  blur_sigma: float = 25.0,
                  min_intensity: int = 100,
                  max_intensity: int = 255,
                  verbose: bool = True) -> int:
    """
    Process all PNG images in a folder with edge enhancement.
    
    Args:
        input_folder: Path to folder containing PNG images
        output_folder: Path to output folder (default: input_folder/EdgeEnhanced)
        blur_sigma: Gaussian blur sigma (default: 25)
        min_intensity: Minimum intensity for enhanced pixels (default: 100)
        max_intensity: Maximum intensity (default: 255)
        verbose: Print progress messages (default: True)
    
    Returns:
        Number of images processed
    """
    input_path = Path(input_folder)
    
    # Create output folder
    if output_folder is None:
        output_path = input_path / f'EdgeEnhanced_{int(blur_sigma)}Blur_{min_intensity}Min'
    else:
        output_path = Path(output_folder)
    
    output_path.mkdir(parents=True, exist_ok=True)
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"Image Edge Enhancement")
        print(f"{'='*60}")
        print(f"Input folder:  {input_path}")
        print(f"Output folder: {output_path}")
        print(f"Parameters: blur_sigma={blur_sigma}, intensity=[{min_intensity}, {max_intensity}]")
        print(f"{'='*60}\n")
    
    # Get all PNG files, sorted numerically
    image_files = sorted(input_path.glob('*.png'), 
                        key=lambda x: int(re.search(r'\d+', x.stem).group()) if re.search(r'\d+', x.stem) else 0)
    
    if not image_files:
        print(f"ERROR: No PNG files found in {input_path}")
        return 0
    
    if verbose:
        print(f"Found {len(image_files)} PNG images")
    
    # Process each image
    processed_count = 0
    for i, img_path in enumerate(image_files, 1):
        try:
            # Read image as grayscale
            original = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
            
            if original is None:
                print(f"WARNING: Could not read {img_path.name}")
                continue
            
            # Apply edge enhancement
            enhanced = edge_enhance_image(original, blur_sigma, min_intensity, max_intensity)
            
            # Save with same filename
            output_file = output_path / img_path.name
            cv2.imwrite(str(output_file), enhanced)
            
            processed_count += 1
            
            if verbose and (i % 10 == 0 or i == len(image_files)):
                print(f"  Processed {i}/{len(image_files)}: {img_path.name}")
        
        except Exception as e:
            print(f"ERROR processing {img_path.name}: {e}")
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"✓ Successfully processed {processed_count}/{len(image_files)} images")
        print(f"✓ Output saved to: {output_path}")
        print(f"{'='*60}\n")
    
    return processed_count


# Command-line interface
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Apply edge enhancement to PNG images')
    parser.add_argument('input_folder', help='Path to folder containing PNG images')
    parser.add_argument('--output', '-o', help='Output folder path (default: input_folder/EdgeEnhanced_...)')
    parser.add_argument('--blur', '-b', type=float, default=25.0, help='Gaussian blur sigma (default: 25)')
    parser.add_argument('--min', '-m', type=int, default=100, help='Minimum intensity (default: 100)')
    parser.add_argument('--max', '-M', type=int, default=255, help='Maximum intensity (default: 255)')
    parser.add_argument('--quiet', '-q', action='store_true', help='Suppress progress messages')
    
    args = parser.parse_args()
    
    process_folder(
        input_folder=args.input_folder,
        output_folder=args.output,
        blur_sigma=args.blur,
        min_intensity=args.min,
        max_intensity=args.max,
        verbose=not args.quiet
    )
