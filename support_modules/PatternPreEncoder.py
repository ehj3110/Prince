"""
Pattern Pre-Encoder Module

This module pre-encodes pattern batches and saves them to disk, eliminating
the need to re-encode patterns every time you print. This provides ~10x speedup
for batch upload operations.

Usage:
    1. Load instruction file in GUI
    2. Click "Pre-Encode Patterns" button
    3. Wait for encoding to complete (~1-2 minutes)
    4. .encoded file is saved alongside instruction file
    5. Future prints automatically use pre-encoded file (10-20s instead of 110s)

File format:
    .encoded files are Python pickle format containing:
    - Encoded image data (left/right halves for dual-controller)
    - Data sizes for each container
    - Exposure times
    - Metadata (pattern count, containers, timestamp)
"""

import os
import time
import pickle
import numpy as np
from PIL import Image
import concurrent.futures
from support_modules.pycrafter9000 import encode_custom


class PatternPreEncoder:
    """
    Handles pre-encoding of pattern batches for faster printing.
    """
    
    def __init__(self, status_callback=None):
        """
        Initialize pre-encoder.
        
        Args:
            status_callback: Optional function to call with status updates
        """
        self.status_callback = status_callback
        self.batch_size = 400  # Maximum patterns per batch
    
    def _update_status(self, message):
        """Send status update if callback is provided."""
        if self.status_callback:
            self.status_callback(message)
        else:
            print(message)
    
    def preprocess_image_to_1bit(self, image_path, threshold=128):
        """
        Load and convert image to 1-bit binary pattern.
        
        Args:
            image_path: Path to image file
            threshold: Grayscale threshold (0-255)
        
        Returns:
            numpy array (1600x2560) with binary values (0 or 1)
        """
        img = Image.open(image_path).convert('L')  # Convert to grayscale
        img_array = np.array(img)
        binary_pattern = (img_array > threshold).astype(np.uint8)
        return binary_pattern
    
    def _merge_patterns_to_container(self, patterns):
        """
        Merge up to 24 patterns into a single RGB container image.
        
        Args:
            patterns: List of binary pattern arrays (1600x2560)
        
        Returns:
            RGB numpy array (1600x2560x3) with patterns packed into bit planes
        """
        merged = np.zeros((1600, 2560, 3), dtype=np.uint8)
        
        for i, pattern in enumerate(patterns):
            if i < 8:
                # Blue channel bits 0-7
                merged[:, :, 2] += pattern * (2 ** i)
            elif i < 16:
                # Green channel bits 0-7
                merged[:, :, 1] += pattern * (2 ** (i - 8))
            else:
                # Red channel bits 0-7
                merged[:, :, 0] += pattern * (2 ** (i - 16))
        
        return merged
    
    def pre_encode_batch(self, image_paths, exposure_times, output_file):
        """
        Pre-encode a batch of patterns and save to disk.
        
        This performs all expensive operations (loading, merging, splitting,
        encoding) and saves the result. Future prints can load this file
        instead of re-encoding.
        
        Args:
            image_paths: List of pattern image file paths
            exposure_times: List of exposure times in seconds (must match length)
            output_file: Path to save .encoded file
        
        Returns:
            dict with encoding results and metadata
        """
        num_patterns = len(image_paths)
        
        if num_patterns > self.batch_size:
            raise ValueError(f"Batch size {num_patterns} exceeds maximum {self.batch_size}")
        
        if len(exposure_times) != num_patterns:
            raise ValueError("exposure_times length must match image_paths length")
        
        self._update_status(f"Pre-encoding {num_patterns} patterns...")
        self._update_status(f"  Output file: {output_file}")
        
        start_time = time.time()
        
        # Step 1: Load and preprocess all patterns
        self._update_status("Loading and preprocessing images...")
        patterns = []
        for i, img_path in enumerate(image_paths):
            if i % 50 == 0 and i > 0:
                self._update_status(f"  Loaded {i}/{num_patterns} patterns...")
            pattern = self.preprocess_image_to_1bit(img_path)
            patterns.append(pattern)
        
        # Step 2: Calculate containers needed
        num_containers = (num_patterns + 23) // 24  # Round up
        self._update_status(f"Organizing into {num_containers} containers (24 patterns each)...")
        
        # Step 3: Encode containers in parallel
        self._update_status("Encoding containers in parallel (4 threads)...")
        
        def encode_container(container_idx):
            """Encode a single container (called in parallel)"""
            start_pattern = container_idx * 24
            end_pattern = min(start_pattern + 24, num_patterns)
            container_patterns = patterns[start_pattern:end_pattern]
            
            # Merge patterns into RGB container
            merged_full = self._merge_patterns_to_container(container_patterns)
            
            # Split into left/right halves for dual-controller
            left_half = merged_full[:, 0:1280, :]      # Left 1280 pixels
            right_half = merged_full[:, 1280:2560, :]  # Right 1280 pixels
            
            # Encode each half
            left_encoded, left_size = encode_custom(left_half, 1280, 1600)
            right_encoded, right_size = encode_custom(right_half, 1280, 1600)
            
            return (left_encoded, left_size, right_encoded, right_size)
        
        # Parallel encoding
        left_encoded_images = [None] * num_containers
        right_encoded_images = [None] * num_containers
        left_data_sizes = [None] * num_containers
        right_data_sizes = [None] * num_containers
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(encode_container, i): i for i in range(num_containers)}
            
            for future in concurrent.futures.as_completed(futures):
                container_idx = futures[future]
                left_enc, left_size, right_enc, right_size = future.result()
                
                left_encoded_images[container_idx] = left_enc
                left_data_sizes[container_idx] = left_size
                right_encoded_images[container_idx] = right_enc
                right_data_sizes[container_idx] = right_size
                
                if (container_idx + 1) % 5 == 0:
                    self._update_status(f"  Encoded {container_idx + 1}/{num_containers} containers...")
        
        self._update_status(f"✓ Encoded {num_containers} containers")
        
        # Step 4: Save to disk
        self._update_status("Saving to disk...")
        
        encoded_data = {
            'version': 1,
            'num_patterns': num_patterns,
            'num_containers': num_containers,
            'left_encoded_images': left_encoded_images,
            'right_encoded_images': right_encoded_images,
            'left_data_sizes': left_data_sizes,
            'right_data_sizes': right_data_sizes,
            'exposure_times': exposure_times,
            'created_timestamp': time.time(),
            'created_date': time.strftime('%Y-%m-%d %H:%M:%S'),
        }
        
        with open(output_file, 'wb') as f:
            pickle.dump(encoded_data, f, protocol=pickle.HIGHEST_PROTOCOL)
        
        # Get file size
        file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
        
        elapsed = time.time() - start_time
        self._update_status(f"✓ Pre-encoding complete in {elapsed:.1f}s")
        self._update_status(f"  Saved to: {output_file}")
        self._update_status(f"  File size: {file_size_mb:.2f} MB")
        self._update_status(f"  Future uploads will be ~10x faster!")
        
        return {
            'num_patterns': num_patterns,
            'num_containers': num_containers,
            'file_path': output_file,
            'file_size_mb': file_size_mb,
            'encoding_time_s': elapsed
        }
    
    def load_pre_encoded_batch(self, encoded_file_path):
        """
        Load pre-encoded batch from disk.
        
        Args:
            encoded_file_path: Path to .encoded file
        
        Returns:
            dict with encoded data ready for upload
        """
        if not os.path.exists(encoded_file_path):
            raise FileNotFoundError(f"Pre-encoded file not found: {encoded_file_path}")
        
        self._update_status(f"Loading pre-encoded batch from: {encoded_file_path}")
        
        start_time = time.time()
        
        with open(encoded_file_path, 'rb') as f:
            data = pickle.load(f)
        
        elapsed = time.time() - start_time
        
        self._update_status(f"✓ Loaded {data['num_patterns']} patterns in {elapsed:.2f}s")
        self._update_status(f"  Created: {data.get('created_date', 'unknown')}")
        
        return data
    
    def verify_encoded_file(self, encoded_file_path):
        """
        Verify that a pre-encoded file is valid and readable.
        
        Args:
            encoded_file_path: Path to .encoded file
        
        Returns:
            dict with file metadata, or None if invalid
        """
        try:
            with open(encoded_file_path, 'rb') as f:
                data = pickle.load(f)
            
            required_keys = [
                'num_patterns', 'num_containers',
                'left_encoded_images', 'right_encoded_images',
                'left_data_sizes', 'right_data_sizes',
                'exposure_times'
            ]
            
            for key in required_keys:
                if key not in data:
                    return None
            
            file_size_mb = os.path.getsize(encoded_file_path) / (1024 * 1024)
            
            return {
                'valid': True,
                'num_patterns': data['num_patterns'],
                'num_containers': data['num_containers'],
                'file_size_mb': file_size_mb,
                'created_date': data.get('created_date', 'unknown'),
            }
            
        except Exception as e:
            self._update_status(f"Error verifying file: {e}")
            return None
