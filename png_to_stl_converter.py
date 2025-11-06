import os
import re
import numpy as np
import trimesh
from PIL import Image
from skimage import measure
from scipy.ndimage import gaussian_filter
import tkinter as tk
from tkinter import filedialog

def create_solid_stl_from_images(root_folder, pixel_size_xy, slice_height_z, 
                                  smooth_sigma=1.0, simplify_ratio=0.5, ensure_solid=True, 
                                  solidify_method='surface'):
    """
    Generates a solid, watertight STL file from the right half of a sequence of PNG images.

    Args:
        root_folder (str): Path to the main folder containing subfolders '1', '2', '3', etc.
        pixel_size_xy (float): Real-world size of a pixel in X and Y.
        slice_height_z (float): Real-world height (thickness) of each slice in Z.
        smooth_sigma (float): Gaussian smoothing strength (0 = no smoothing, 1-2 = moderate, >2 = high).
        simplify_ratio (float): Mesh simplification target (0.1-1.0, where 0.5 = 50% of original faces).
        ensure_solid (bool): If True, voxelizes and solidifies the mesh to fill any internal voids.
        solidify_method (str): 'surface' = watertight surface only, 'voxel' = truly filled interior (blocky),
                               'none' = skip solidification step
    """
    print("Starting SOLID STL generation process...")

    # --- 1. Collect and sort image files ---
    all_files = []
    # Ensure subfolders are sorted numerically if they are numbers
    try:
        subfolders = sorted([d for d in os.listdir(root_folder) if os.path.isdir(os.path.join(root_folder, d))], key=int)
    except ValueError:
        print("Warning: Subfolder names are not all numbers. Using alphanumeric sorting.")
        subfolders = sorted([d for d in os.listdir(root_folder) if os.path.isdir(os.path.join(root_folder, d))])
    
    print(f"Found and sorted subfolders: {subfolders}")

    for folder in subfolders:
        folder_path = os.path.join(root_folder, folder)
        try:
            # Sort files based on numbers in their filenames
            files = sorted(
                [f for f in os.listdir(folder_path) if f.lower().endswith('.png')],
                key=lambda f: int(re.search(r'(\d+)', f).group(1))
            )
            all_files.extend([os.path.join(folder_path, f) for f in files])
            print(f"Found and sorted {len(files)} images in subfolder '{folder}'.")
        except (ValueError, AttributeError):
            print(f"Warning: Could not sort files in '{folder}' by number. Using alphanumeric sorting.")
            files = sorted([f for f in os.listdir(folder_path) if f.lower().endswith('.png')])
            all_files.extend([os.path.join(folder_path, f) for f in files])

    if not all_files:
        print("Error: No PNG files found in the specified directory structure.")
        return

    print(f"\nTotal images to process: {len(all_files)}")

    # --- 2. Load images into a 3D volume ---
    print("Loading images and creating a 3D data volume...")
    
    # Use the first image to determine dimensions
    with Image.open(all_files[0]) as img:
        img_gray = img.convert('L')
        full_dims = np.array(img_gray).shape
        midpoint = full_dims[1] // 2
        right_half_dims = (full_dims[0], full_dims[1] - midpoint)

    # Create the volume array, adding padding for the marching cubes algorithm
    # Padding ensures the mesh is closed even if it touches the edges.
    volume = np.zeros((len(all_files) + 2, right_half_dims[0] + 2, right_half_dims[1] + 2), dtype=np.uint8)

    for i, file_path in enumerate(all_files):
        with Image.open(file_path) as img:
            img_gray = img.convert('L')
            img_array = np.array(img_gray)
            
            # Split image in half and use the right side
            midpoint = img_array.shape[1] // 2
            right_half = img_array[:, midpoint:]
            
            # Binarize the image (black pixels are 'on') and place it in the padded volume
            volume[i + 1, 1:-1, 1:-1] = (right_half > 128).astype(np.uint8)
    
    # Ensure the first and last slices are empty (all zeros) for proper closure
    # This helps marching cubes create closed top and bottom surfaces
    volume[0, :, :] = 0
    volume[-1, :, :] = 0

    print("3D volume created successfully.")

    # --- 3. Apply Gaussian smoothing (DISABLED - causes tendrils) ---
    # if smooth_sigma > 0:
    #     print(f"Applying Gaussian smoothing with sigma={smooth_sigma}...")
    #     volume = gaussian_filter(volume.astype(float), sigma=smooth_sigma)
    #     print("Smoothing complete.")

    # --- 4. Generate mesh using Marching Cubes ---
    print("Generating mesh with Marching Cubes algorithm...")
    try:
        verts, faces, _, _ = measure.marching_cubes(
            volume,
            level=0.5, # Iso-surface value
            spacing=(slice_height_z, pixel_size_xy, pixel_size_xy) # Real-world dimensions
        )
    except Exception as e:
        print(f"Error during Marching Cubes: {e}")
        return

    if len(verts) == 0 or len(faces) == 0:
        print("Error: Marching Cubes did not generate any geometry. The image stack might be all white.")
        return
        
    print(f"Initial mesh generated: {len(verts)} vertices, {len(faces)} faces.")

    # --- 5. Create, process, and repair the mesh with Trimesh ---
    print("Loading mesh into Trimesh for processing...")
    mesh = trimesh.Trimesh(vertices=verts, faces=faces)

    print("Diagnosing mesh issues...")
    print(f"  - Watertight: {mesh.is_watertight}")
    print(f"  - Volume: {mesh.volume if mesh.is_watertight else 'N/A (not watertight)'}")
    
    # --- 5a. Repair non-manifold edges and other mesh issues ---
    print("Repairing mesh (fixing non-manifold edges, duplicates, degenerate faces)...")
    
    # Remove duplicate vertices
    mesh.merge_vertices()
    print(f"  - Merged duplicate vertices")
    
    # Remove degenerate faces (zero area)
    mesh.remove_degenerate_faces()
    print(f"  - Removed degenerate faces")
    
    # Remove duplicate faces
    mesh.remove_duplicate_faces()
    print(f"  - Removed duplicate faces")
    
    # Remove unreferenced vertices
    mesh.remove_unreferenced_vertices()
    print(f"  - Removed unreferenced vertices")
    
    # Split mesh into connected components and keep only the largest
    # This removes small floating artifacts
    components = mesh.split(only_watertight=False)
    if len(components) > 1:
        print(f"  - Found {len(components)} separate mesh components")
        # Keep the largest component
        mesh = max(components, key=lambda m: len(m.faces))
        print(f"  - Kept largest component with {len(mesh.faces)} faces")
    
    # Fill holes to make it watertight
    print("Attempting to fill holes to ensure the mesh is watertight...")
    mesh.fill_holes()

    # Fix normals to ensure they point outwards
    print("Fixing face normals to define inside/outside correctly...")
    mesh.fix_normals()
    
    print(f"After repair: Watertight = {mesh.is_watertight}, Vertices = {len(mesh.vertices)}, Faces = {len(mesh.faces)}")

    # --- 6. Apply Laplacian smoothing (DISABLED - keeping original geometry) ---
    # if smooth_sigma > 0:
    #     print("Applying Laplacian mesh smoothing...")
    #     trimesh.smoothing.filter_laplacian(mesh, iterations=5)
    #     print("Mesh smoothing complete.")

    # --- 7. Simplify mesh (reduce face count) ---
    if 0 < simplify_ratio < 1.0:
        target_faces = int(len(mesh.faces) * simplify_ratio)
        print(f"Simplifying mesh from {len(mesh.faces)} to ~{target_faces} faces...")
        try:
            # Use quadric decimation for high-quality simplification
            mesh = mesh.simplify_quadric_decimation(target_faces)
            print(f"Mesh simplified: {len(mesh.vertices)} vertices, {len(mesh.faces)} faces.")
        except Exception as e:
            print(f"Warning: Simplification failed ({e}). Continuing with original mesh.")

    # --- 8. Ensure mesh is truly solid (fill interior) ---
    if ensure_solid and solidify_method != 'none':
        print(f"Solidifying mesh using method: {solidify_method}...")
        try:
            # First ensure the mesh is watertight
            if not mesh.is_watertight:
                print("Mesh is not watertight after initial repairs. Attempting aggressive repair...")
                
                # Try filling holes again more aggressively
                mesh.fill_holes()
                
                # If still not watertight, try more aggressive approaches
                if not mesh.is_watertight:
                    print("Attempting to fix non-manifold edges...")
                    
                    # Method 1: Split along non-manifold edges
                    # This separates the mesh at problematic edges
                    edges = mesh.edges_unique
                    edge_faces = mesh.edges_unique_inverse
                    
                    # Count how many faces each edge belongs to
                    from collections import Counter
                    edge_count = Counter(edge_faces)
                    
                    # Find edges that belong to more than 2 faces (non-manifold)
                    non_manifold_count = sum(1 for count in edge_count.values() if count != 2)
                    if non_manifold_count > 0:
                        print(f"  - Found {non_manifold_count} non-manifold edges")
                    
                    # Try convex hull as last resort for severely broken meshes
                    if not mesh.is_watertight:
                        print("Warning: Standard repairs failed. You may need to:")
                        print("  1. Check your PNG images for completeness")
                        print("  2. Try using 'voxel' solidify method")
                        print("  3. Manually repair in MeshLab or Blender")
            
            if solidify_method == 'voxel':
                if mesh.is_watertight:
                    print("Creating truly solid (filled) mesh using voxelization...")
                    
                    # Calculate appropriate voxel resolution
                    bounds = mesh.bounds
                    dimensions = bounds[1] - bounds[0]
                    max_dim = np.max(dimensions)
                    
                    # Use finer voxels for better quality
                    voxel_pitch = max_dim / 250.0  # Increase for more detail
                    print(f"Using voxel pitch: {voxel_pitch:.2f}")
                    
                    # Voxelize - this fills the interior
                    voxelized = mesh.voxelized(pitch=voxel_pitch)
                    
                    # Convert back to mesh surface
                    mesh = voxelized.marching_cubes
                    mesh.fill_holes()
                    mesh.fix_normals()
                    
                    print(f"Voxel solidification complete. {len(mesh.vertices)} vertices, {len(mesh.faces)} faces.")
                else:
                    print("Cannot voxelize: mesh is not watertight. Skipping voxel solidification.")
            
            elif solidify_method == 'surface':
                print("Ensuring watertight surface mesh (hollow interior for Blender)...")
                # Just make sure it's watertight - Blender can treat watertight meshes as solid
                if mesh.is_watertight:
                    print(f"Mesh is watertight with volume: {mesh.volume:.2f}")
                    print("Note: Mesh is a surface (hollow), but Blender's Boolean modifier will treat it as solid.")
                else:
                    print("Warning: Mesh is not watertight. May have gaps in Blender cross-sections.")
                    print("Recommendation: Fix source images or try exporting anyway and repair in Blender/MeshLab")
            
        except Exception as e:
            print(f"Warning: Solidification failed ({e}). Continuing with current mesh.")

    print(f"Mesh processing complete. Watertight: {mesh.is_watertight}")

    # --- 9. Prompt user for save location and export ---
    print("Please choose a location to save the final STL file.")
    root = tk.Tk()
    root.withdraw() # Hide the main tkinter window
    try:
        file_path = filedialog.asksaveasfilename(
            defaultextension=".stl",
            filetypes=[("STL files", "*.stl"), ("All files", "*.*")],
            title="Save the Solid STL File"
        )
    finally:
        root.destroy() # Ensure the tkinter root is destroyed

    if file_path:
        print(f"Saving final solid STL file to: {file_path}")
        # Export directly from trimesh as a binary STL
        mesh.export(file_path, file_type='stl')
        print("\nProcess complete! Solid STL file saved successfully.")
    else:
        print("\nProcess cancelled by user. No file was saved.")

if __name__ == '__main__':
    # --- Configuration ---
    # IMPORTANT: Set the main folder containing your numbered subfolders ('1', '2', '3')
    MAIN_FOLDER = r"C:\\Users\\ehunt\\OneDrive - Northwestern University\\Lab Work\\Mirae\\MZ_Recreation"
    PIXEL_SIZE = 4.0      # Real-world size of one pixel in X and Y
    SLICE_HEIGHT = 10.0   # Real-world thickness of each image slice in Z
    
    # --- NEW: Smoothing and Processing Parameters ---
    SMOOTH_SIGMA = 0.0        # Gaussian smoothing disabled (was causing tendrils and artifacts)
    SIMPLIFY_RATIO = 0.5      # Keep 50% of faces (0.1-1.0, where 1.0=no simplification)
    ENSURE_SOLID = True       # Check and ensure mesh is watertight
    SOLIDIFY_METHOD = 'surface'  # 'surface' = watertight shell (Blender treats as solid)
                                  # 'voxel' = truly filled interior (blockier but guaranteed solid)
                                  # 'none' = skip solidification
    
    # --- Run the script ---
    create_solid_stl_from_images(
        MAIN_FOLDER, 
        PIXEL_SIZE, 
        SLICE_HEIGHT,
        smooth_sigma=SMOOTH_SIGMA,
        simplify_ratio=SIMPLIFY_RATIO,
        ensure_solid=ENSURE_SOLID,
        solidify_method=SOLIDIFY_METHOD
    )