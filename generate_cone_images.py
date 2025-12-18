import os
import numpy as np
from PIL import Image
import math

# --- Configuration ---
IMAGE_WIDTH = 2560
IMAGE_HEIGHT = 1600
PIXEL_SIDE_UM = 7.607  # Side length of a square pixel in micrometers
OUTPUT_DIR = "cone_images"
TOTAL_IMAGES = 350

# --- Expansion Profile ---
INITIAL_PADDING_COUNT = 50
INITIAL_PADDING_AREA_MM2 = 5.0

EXPANSION_STEPS = 60
EXPANSION_REPEATS_PER_STEP = 5
EXPANSION_START_AREA_MM2 = 10.0
EXPANSION_END_AREA_MM2 = 100.0

# --- Sanity Check ---
if INITIAL_PADDING_COUNT + (EXPANSION_STEPS * EXPANSION_REPEATS_PER_STEP) != 350:
    print(f"Warning: The configuration will generate a total of {INITIAL_PADDING_COUNT + (EXPANSION_STEPS * EXPANSION_REPEATS_PER_STEP)} images, not 350.")

# --- Calculations ---
PIXEL_SIDE_MM = PIXEL_SIDE_UM / 1000.0  # Convert micrometers to millimeters
PIXEL_AREA_MM2 = PIXEL_SIDE_MM**2

def area_mm2_to_pixel_radius(area_mm2):
    """Converts a desired circle area in mm^2 to the required radius in pixels."""
    area_in_pixels = area_mm2 / PIXEL_AREA_MM2
    radius_in_pixels = math.sqrt(area_in_pixels / math.pi)
    return radius_in_pixels

def create_circle_image(radius_px, width, height):
    """Creates a binary image of a centered circle."""
    center_x, center_y = width / 2, height / 2
    y, x = np.ogrid[:height, :width]

    dist_from_center_sq = (x - center_x)**2 + (y - center_y)**2
    mask = dist_from_center_sq <= radius_px**2
    
    # Create an 8-bit black image and set the circle to white
    image_array = np.zeros((height, width), dtype=np.uint8)
    image_array[mask] = 255
    
    return Image.fromarray(image_array, 'L')

def main():
    """Main function to generate and save all images."""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"Created directory: {OUTPUT_DIR}")

    image_counter = 1

    # --- 1. Generate Initial Padding Images ---
    print(f"Generating {INITIAL_PADDING_COUNT} initial padding images (Area: {INITIAL_PADDING_AREA_MM2} mm^2)...")
    padding_radius_px = area_mm2_to_pixel_radius(INITIAL_PADDING_AREA_MM2)
    padding_image = create_circle_image(padding_radius_px, IMAGE_WIDTH, IMAGE_HEIGHT)
    for _ in range(INITIAL_PADDING_COUNT):
        file_path = os.path.join(OUTPUT_DIR, f"{image_counter}.png")
        padding_image.save(file_path)
        image_counter += 1
    
    print(f"Done. Last image number: {image_counter - 1}")

    # --- 2. Generate Expanding Cone Images ---
    print(f"Generating {EXPANSION_STEPS * EXPANSION_REPEATS_PER_STEP} expanding cone images...")
    
    # Generate area values on a logarithmic scale
    log_spaced_areas = np.logspace(
        math.log10(EXPANSION_START_AREA_MM2),
        math.log10(EXPANSION_END_AREA_MM2),
        num=EXPANSION_STEPS
    )

    for i, step_area_mm2 in enumerate(log_spaced_areas):
        radius_px = area_mm2_to_pixel_radius(step_area_mm2)
        circle_image = create_circle_image(radius_px, IMAGE_WIDTH, IMAGE_HEIGHT)
        
        # Repeat this image
        for _ in range(EXPANSION_REPEATS_PER_STEP):
            if image_counter > TOTAL_IMAGES:
                break
            file_path = os.path.join(OUTPUT_DIR, f"{image_counter}.png")
            circle_image.save(file_path)
            image_counter += 1
        
        print(f"  - Step {i+1}/{EXPANSION_STEPS}: Area={step_area_mm2:.2f} mm^2, Radius={radius_px:.2f} px. Saved images up to {image_counter - 1}.png")

        if image_counter > TOTAL_IMAGES:
            break
            
    print(f"\nScript finished. Total images generated: {image_counter - 1}")
    print(f"Images are in the '{OUTPUT_DIR}' folder.")

if __name__ == "__main__":
    main()
