"""
Cylinder Generator for DLP 3D Printing
======================================

Generates PNG image files for printing cylindrical structures.

Usage:
    python cylinder_generator.py --diameter 0.67 --layers 50 --output "C:/Path/To/Output"
    python cylinder_generator.py --area 10 --layers 100 --output "C:/Path/To/Output"

Pixel size: 7.607 µm x 7.607 µm
Image resolution: 2560 x 1600 pixels

Author: Cheng Sun Lab Team
Date: February 11, 2026
"""

import numpy as np
from PIL import Image
import argparse
from pathlib import Path
import math


# Constants
PIXEL_SIZE_UM = 7.607  # micrometers per pixel
IMAGE_WIDTH = 2560
IMAGE_HEIGHT = 1600


def calculate_diameter_from_area(area_mm2):
    """
    Calculate diameter in mm from area in mm².
    
    Args:
        area_mm2: Area in square millimeters
    
    Returns:
        diameter_mm: Diameter in millimeters
    """
    # A = π * r²  =>  r = sqrt(A / π)  =>  d = 2 * r
    radius_mm = math.sqrt(area_mm2 / math.pi)
    diameter_mm = 2 * radius_mm
    return diameter_mm


def calculate_area_from_diameter(diameter_mm):
    """
    Calculate area in mm² from diameter in mm.
    
    Args:
        diameter_mm: Diameter in millimeters
    
    Returns:
        area_mm2: Area in square millimeters
    """
    radius_mm = diameter_mm / 2
    area_mm2 = math.pi * radius_mm ** 2
    return area_mm2


def mm_to_pixels(mm):
    """
    Convert millimeters to pixels.
    
    Args:
        mm: Distance in millimeters
    
    Returns:
        pixels: Distance in pixels
    """
    um = mm * 1000  # Convert mm to µm
    pixels = um / PIXEL_SIZE_UM
    return pixels


def format_decimal_for_filename(value):
    """
    Format decimal number for filename (replace . with p).
    
    Args:
        value: Decimal number
    
    Returns:
        formatted_str: String with 'p' instead of '.'
    """
    return f"{value:.3f}".replace('.', 'p').rstrip('0').rstrip('p')


def generate_cylinder_image(diameter_mm):
    """
    Generate a single cylinder image (white circle on black background).
    
    Args:
        diameter_mm: Diameter of cylinder in millimeters
    
    Returns:
        image: PIL Image object
    """
    # Create black background
    img_array = np.zeros((IMAGE_HEIGHT, IMAGE_WIDTH), dtype=np.uint8)
    
    # Calculate radius in pixels
    diameter_pixels = mm_to_pixels(diameter_mm)
    radius_pixels = diameter_pixels / 2
    
    # Center coordinates
    center_x = IMAGE_WIDTH / 2
    center_y = IMAGE_HEIGHT / 2
    
    # Create coordinate grids
    y, x = np.ogrid[:IMAGE_HEIGHT, :IMAGE_WIDTH]
    
    # Calculate distance from center for each pixel
    distance_from_center = np.sqrt((x - center_x)**2 + (y - center_y)**2)
    
    # Set pixels within radius to white (255)
    img_array[distance_from_center <= radius_pixels] = 255
    
    # Convert to PIL Image
    image = Image.fromarray(img_array, mode='L')
    
    return image


def generate_cylinder_stack(diameter_mm=None, area_mm2=None, num_layers=1, output_dir=None):
    """
    Generate a stack of cylinder images for 3D printing.
    
    Args:
        diameter_mm: Diameter in millimeters (optional if area provided)
        area_mm2: Area in square millimeters (optional if diameter provided)
        num_layers: Number of layers to generate
        output_dir: Output directory path
    
    Returns:
        output_folder: Path to created folder
    """
    # Validate inputs
    if diameter_mm is None and area_mm2 is None:
        raise ValueError("Must provide either diameter or area")
    
    if diameter_mm is not None and area_mm2 is not None:
        raise ValueError("Provide only diameter OR area, not both")
    
    # Calculate the other parameter
    if diameter_mm is not None:
        area_mm2 = calculate_area_from_diameter(diameter_mm)
    else:
        diameter_mm = calculate_diameter_from_area(area_mm2)
    
    # Format values for folder name
    diameter_str = format_decimal_for_filename(diameter_mm)
    area_str = format_decimal_for_filename(area_mm2)
    
    # Create folder name
    folder_name = f"Cylinder_{diameter_str}mmDia_{area_str}mm2Area"
    
    # Create output directory
    if output_dir is None:
        output_dir = Path.cwd()
    else:
        # Ensure output_dir is a string and properly formatted
        output_dir = str(output_dir).strip()
        # Remove any quotes that might have been included
        output_dir = output_dir.strip('"').strip("'")
        output_dir = Path(output_dir).resolve()
    
    # Validate output directory exists or can be created
    if not output_dir.exists():
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise ValueError(f"Cannot create output directory: {output_dir}\nError: {e}")
    
    output_folder = output_dir / folder_name
    
    try:
        output_folder.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise ValueError(f"Cannot create cylinder folder: {output_folder}\nError: {e}")
    
    print("=" * 80)
    print("CYLINDER GENERATOR")
    print("=" * 80)
    print(f"Diameter: {diameter_mm:.4f} mm ({mm_to_pixels(diameter_mm):.2f} pixels)")
    print(f"Area: {area_mm2:.4f} mm²")
    print(f"Number of layers: {num_layers}")
    print(f"Output folder: {output_folder}")
    print("=" * 80)
    
    # Generate the cylinder image (same for all layers)
    print("\nGenerating cylinder image...")
    cylinder_image = generate_cylinder_image(diameter_mm)
    
    # Save multiple copies
    print(f"Saving {num_layers} layers...")
    for layer_num in range(1, num_layers + 1):
        filename = f"{layer_num}.png"
        filepath = output_folder / filename
        cylinder_image.save(filepath)
        
        if layer_num % 10 == 0 or layer_num == num_layers:
            print(f"  Saved layer {layer_num}/{num_layers}")
    
    print("\n" + "=" * 80)
    print(f"[SUCCESS] Generated {num_layers} layers in: {output_folder}")
    print("=" * 80)
    
    return output_folder


def main():
    parser = argparse.ArgumentParser(
        description="Generate cylinder images for DLP 3D printing",
        epilog=f"Image resolution: {IMAGE_WIDTH} x {IMAGE_HEIGHT} pixels\n"
               f"Pixel size: {PIXEL_SIZE_UM} µm x {PIXEL_SIZE_UM} µm",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Mutually exclusive group for diameter or area
    size_group = parser.add_mutually_exclusive_group(required=True)
    size_group.add_argument('--diameter', type=float,
                           help='Cylinder diameter in millimeters (e.g., 0.67)')
    size_group.add_argument('--area', type=float,
                           help='Cylinder cross-sectional area in mm² (e.g., 10)')
    
    parser.add_argument('--layers', type=int, required=True,
                       help='Number of layers to generate (e.g., 50)')
    parser.add_argument('--output', type=str, required=True,
                       help='Output directory path (e.g., "C:/Prints/Cylinders")')
    
    args = parser.parse_args()
    
    # Generate cylinder stack
    try:
        output_folder = generate_cylinder_stack(
            diameter_mm=args.diameter,
            area_mm2=args.area,
            num_layers=args.layers,
            output_dir=args.output
        )
        
        print(f"\n✓ Ready for printing!")
        print(f"  Load images from: {output_folder}")
        
    except Exception as e:
        print(f"\n[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())
