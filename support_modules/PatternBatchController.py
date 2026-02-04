"""
Pattern Batch Controller for DLP Pattern-on-the-Fly Printing
Handles batch upload of 400 1-bit patterns and continuous motion printing.

This module uses existing pycrafter9000.py methods to:
- Upload 400 patterns per batch to DLP firmware
- Configure pattern sequences with proper timing
- Handle base layer special timing (stationary, then continuous)
- Manage batch transitions during multi-batch prints
"""

import cv2
import numpy as np
import time
from pathlib import Path


class PatternBatchController:
    """
    Manages batch upload and sequencing for pattern-on-the-fly printing.
    
    Key Features:
    - Loads up to 400 1-bit patterns per batch
    - Configures LUT with exposure times and dark times
    - Special handling for base layer (stationary exposure)
    - Continuous motion for remaining layers in batch
    """
    
    def __init__(self, dlp_controller, status_callback=None):
        """
        Initialize the pattern batch controller.
        
        Args:
            dlp_controller: Instance of pycrafter9000.dmd()
            status_callback: Optional function to call with status updates
        """
        self.dlp = dlp_controller
        self.status_callback = status_callback
        self.batch_size = 400  # Maximum patterns per batch
        self.patterns_loaded = []  # Track loaded pattern info
        self.num_patterns_in_current_batch = 0  # Track how many patterns in active batch
        
    def _update_status(self, message):
        """Send status update if callback is provided."""
        if self.status_callback:
            self.status_callback(message)
        else:
            print(message)
    
    def preprocess_image_to_1bit(self, image_path, threshold=128):
        """
        Load and convert image to 1-bit binary format.
        
        Args:
            image_path: Path to PNG image file
            threshold: Grayscale threshold for binary conversion (0-255)
            
        Returns:
            numpy array of 1-bit binary image (1600x2560), values are STRICTLY 0 or 1
        """
        # Load image as grayscale
        img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
        
        if img is None:
            raise ValueError(f"Could not load image: {image_path}")
        
        # Resize to DLP native resolution (2560x1600)
        if img.shape != (1600, 2560):
            img = cv2.resize(img, (2560, 1600))
        
        # Convert to 1-bit binary - STRICTLY 0 or 1, not 0 or 255
        binary = (img > threshold).astype(np.uint8)
        
        # Verify values are only 0 or 1
        assert np.all((binary == 0) | (binary == 1)), "Binary image must contain only 0 or 1"
        
        return binary
    
    def upload_batch(self, image_paths, exposure_times, is_first_batch=False):
        """
        Upload a batch of up to 400 patterns to DLP firmware.
        
        This method:
        1. Stops current sequence
        2. Switches to pattern-on-the-fly mode
        3. Loads patterns into image containers (packing 24 per container)
        4. Configures LUT with exposure times
        
        Args:
            image_paths: List of image file paths (up to 400)
            exposure_times: List of exposure times in seconds (same length as image_paths)
            is_first_batch: If True, first pattern is base layer (stationary)
            
        Returns:
            dict with upload results and timing info
        """
        num_patterns = len(image_paths)
        
        if num_patterns > self.batch_size:
            raise ValueError(f"Batch size {num_patterns} exceeds maximum {self.batch_size}")
        
        if len(exposure_times) != num_patterns:
            raise ValueError("exposure_times length must match image_paths length")
        
        # Track current batch size
        self.num_patterns_in_current_batch = num_patterns
        
        self._update_status(f"Starting batch upload: {num_patterns} patterns...")
        self._update_status(f"  Batch parameters:")
        self._update_status(f"    - Patterns: {num_patterns}")
        self._update_status(f"    - First batch: {is_first_batch}")
        self._update_status(f"    - Exposures: {exposure_times[0]:.3f}s to {exposure_times[-1]:.3f}s")
        upload_start_time = time.time()
        
        # Step 1: Stop current sequence and switch to pattern mode
        self._update_status("Stopping sequence and switching to pattern mode...")
        self.dlp.stopsequence()
        time.sleep(0.1)
        self._update_status("  Calling dlp.changemode(3) for Pattern Sequence Mode...")
        self.dlp.changemode(3)  # Mode 3 = Pattern sequence mode (NOT mode 0!)
        time.sleep(0.5)
        self._update_status("  ✓ Pattern mode active")
        
        # Step 2: Load images
        # We'll pack 24 1-bit patterns into each 24-bit image container
        # For 400 patterns, we need 17 containers (400 / 24 = 16.67, round up to 17)
        self._update_status("Loading patterns into firmware...")
        
        # Preprocess all images to 1-bit
        binary_patterns = []
        for i, img_path in enumerate(image_paths):
            if i % 50 == 0:
                self._update_status(f"  Processing image {i+1}/{num_patterns}...")
            binary = self.preprocess_image_to_1bit(img_path)
            binary_patterns.append(binary)
        
        # Pack patterns into image containers (24 patterns per container)
        num_containers = (num_patterns + 23) // 24  # Round up
        
        # Prepare all merged images first (needed for reverse upload order)
        self._update_status("Merging and encoding patterns (this may take a moment)...")
        left_encoded_images = []
        right_encoded_images = []
        left_data_sizes = []
        right_data_sizes = []
        
        from pycrafter9000 import encode_custom
        import concurrent.futures
        
        # Helper function for parallel encoding
        def encode_container(container_idx):
            # Get patterns for this container (up to 24)
            start_idx = container_idx * 24
            end_idx = min(start_idx + 24, num_patterns)
            container_patterns = binary_patterns[start_idx:end_idx]
            
            # Merge patterns into RGB channels (8 per channel)
            merged_full = self._merge_patterns_to_container(container_patterns)
            
            # CRITICAL: Split into left (PRIMARY) and right (SECONDARY) halves
            # DLP9000 dual-controller architecture requires separate 1280-width images
            left_half = merged_full[:, 0:1280, :]      # Left 1280 pixels
            right_half = merged_full[:, 1280:2560, :]  # Right 1280 pixels
            
            # Encode each half separately with 1280-width headers
            left_encoded, left_size = encode_custom(left_half, 1280, 1600)
            right_encoded, right_size = encode_custom(right_half, 1280, 1600)
            
            return (left_encoded, left_size, right_encoded, right_size)
        
        # Encode all containers in parallel using thread pool (up to 4x speedup)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(encode_container, i): i for i in range(num_containers)}
            
            # Collect results in order
            results = [None] * num_containers
            for future in concurrent.futures.as_completed(futures):
                container_idx = futures[future]
                results[container_idx] = future.result()
            
            # Store in arrays maintaining order
            for left_enc, left_sz, right_enc, right_sz in results:
                left_encoded_images.append(left_enc)
                left_data_sizes.append(left_sz)
                right_encoded_images.append(right_enc)
                right_data_sizes.append(right_sz)
        
        self._update_status(f"✓ Encoded {num_containers} containers in parallel")
        
        # Upload in REVERSE order (required by DLPC900 firmware)
        # CRITICAL: DLP9000 is a DUAL-CONTROLLER system (Primary + Secondary)
        # Primary handles left half, Secondary handles right half
        # Must upload to BOTH controllers separately
        upload_start = time.time()
        self._update_status("Uploading containers to DLP firmware (DUAL-CONTROLLER MODE)...")
        
        for i in range(num_containers):
            reverse_idx = num_containers - 1 - i
            
            # Initialize PRIMARY controller (left half) - command 0x1A2A
            self.dlp.setbmp(reverse_idx, left_data_sizes[reverse_idx])
            
            # Initialize SECONDARY controller (right half) - command 0x1A2C
            self.dlp.setbmp_secondary(reverse_idx, right_data_sizes[reverse_idx])
            
            # Upload LEFT half to PRIMARY - command 0x1A2B (has progress prints)
            self.dlp.bmpload(left_encoded_images[reverse_idx], left_data_sizes[reverse_idx])
            
            # Upload RIGHT half to SECONDARY - command 0x1A2D (has progress prints)
            self.dlp.bmpload_secondary(right_encoded_images[reverse_idx], right_data_sizes[reverse_idx])
            
            # Progress indicator every 2 containers
            if (i+1) % 2 == 0 or i == num_containers - 1:
                elapsed = time.time() - upload_start
                avg_time = elapsed / (i + 1)
                remaining = avg_time * (num_containers - i - 1)
                self._update_status(f"  Progress: {i+1}/{num_containers} containers ({elapsed:.1f}s elapsed, ~{remaining:.1f}s remaining)")
        
        upload_time = time.time() - upload_start
        self._update_status(f"✓ Upload complete in {upload_time:.1f}s")
        
        # Step 3: Configure LUT (pattern definitions)
        self._update_status("Configuring pattern sequence (LUT)...")
        self._update_status(f"  Total patterns to configure: {num_patterns}")
        
        # Debug: Show exposure times being programmed
        if num_patterns > 0:
            first_exp = exposure_times[0] * 1_000_000  # Convert to µs
            last_exp = exposure_times[-1] * 1_000_000
            avg_exp = sum(exposure_times) / len(exposure_times) * 1_000_000
            self._update_status(f"  Exposure times: First={first_exp:.0f}µs, Last={last_exp:.0f}µs, Avg={avg_exp:.0f}µs")
        
        for i in range(num_patterns):
            # Convert exposure time from seconds to microseconds
            exposure_us = int(exposure_times[i] * 1_000_000)
            
            # Calculate which container and position within container
            container_idx = i // 24
            pattern_in_container = i % 24
            
            # CRITICAL (per DLPC900 guide):
            # - color controls which LEDs turn ON (not which bit to read!)
            # - bitpos selects which of 24 bits in container to display (0-23)
            # - For monochrome with white LED: use color='111' for ALL patterns
            # - Changing color causes LED reconfiguration gaps!
            color = '111'  # Constant for all patterns (white LED output)
            bit_pos = pattern_in_container  # Direct 0-23 mapping
            
            # Debug: Print first few, last, and container boundary patterns
            if i < 3 or i == num_patterns - 1 or i % 24 == 0 or i % 24 == 23:
                self._update_status(f"  Pattern {i}: exp={exposure_us}µs, container={container_idx}, bit={bit_pos}, color={color}")
            
            # Define pattern in LUT
            # Parameters: index, exposure_us, bitdepth, color, triggerin, darktime, triggerout, patind, bitpos
            self.dlp.definepattern(
                index=i,
                exposure=exposure_us,
                bitdepth=1,         # 1-bit binary
                color=color,        # White - all LEDs on
                triggerin=False,    # No external trigger
                darktime=0,         # No dark time (continuous exposure during motion)
                triggerout=0,       # No trigger output
                patind=container_idx,
                bitpos=bit_pos
            )
        
        # Step 4: Configure sequence
        self._update_status("Configuring sequence parameters...")
        
        # Calculate total sequence duration
        total_sequence_time = sum(exposure_times)
        self._update_status(f"  CRITICAL TIMING INFO:")
        self._update_status(f"    - Patterns: {num_patterns}")
        self._update_status(f"    - Total sequence duration: {total_sequence_time:.2f}s")
        self._update_status(f"    - Average pattern time: {total_sequence_time/num_patterns:.3f}s")
        self._update_status(f"  WARNING: Sequence will complete in {total_sequence_time:.2f}s")
        self._update_status(f"           Stage motion may take longer!")
        self._update_status(f"           If print motion > {total_sequence_time:.2f}s, DLP will finish early")
        
        self._update_status(f"  Calling configurelut({num_patterns}, 0) - INFINITE REPEAT for testing")
        # configurelut(num_patterns, repeat_count)
        # repeat_count = 0 means infinite repeat
        # Going back to this to verify pattern display works
        self.dlp.configurelut(num_patterns, 0)
        self._update_status("  ✓ LUT configured (repeat=0 - INFINITE)")
        
        upload_duration = time.time() - upload_start_time
        self._update_status(f"✓ Batch upload complete: {num_patterns} patterns in {upload_duration:.1f}s")
        
        return {
            'num_patterns': num_patterns,
            'num_containers': num_containers,
            'upload_time': upload_duration,
            'is_first_batch': is_first_batch
        }
    
    def upload_pre_encoded_batch(self, encoded_data, is_first_batch=False):
        """
        Upload a pre-encoded batch to DLP (FAST - no encoding needed).
        
        This skips all image loading, merging, and encoding steps and directly
        uploads the pre-encoded data to the DLP. Provides ~10x speedup.
        
        Args:
            encoded_data: Dict from PatternPreEncoder.load_pre_encoded_batch()
            is_first_batch: If True, first pattern is base layer (stationary)
            
        Returns:
            dict with upload results and timing info
        """
        num_patterns = encoded_data['num_patterns']
        num_containers = encoded_data['num_containers']
        exposure_times = encoded_data['exposure_times']
        
        # Track current batch size
        self.num_patterns_in_current_batch = num_patterns
        
        self._update_status(f"Uploading PRE-ENCODED batch: {num_patterns} patterns...")
        self._update_status(f"  Batch parameters:")
        self._update_status(f"    - Patterns: {num_patterns}")
        self._update_status(f"    - Containers: {num_containers}")
        self._update_status(f"    - First batch: {is_first_batch}")
        self._update_status(f"    - Pre-encoded on: {encoded_data.get('created_date', 'unknown')}")
        upload_start_time = time.time()
        
        # Step 1: Stop current sequence and switch to pattern mode
        self._update_status("Stopping sequence and switching to pattern mode...")
        self.dlp.stopsequence()
        time.sleep(0.1)
        self._update_status("  Calling dlp.changemode(3) for Pattern Sequence Mode...")
        self.dlp.changemode(3)
        self._update_status("  ✓ Pattern mode active")
        
        # Step 2: Upload pre-encoded containers (already split and encoded)
        self._update_status(f"Uploading {num_containers} containers to DLP firmware (PRE-ENCODED)...")
        
        left_encoded_images = encoded_data['left_encoded_images']
        right_encoded_images = encoded_data['right_encoded_images']
        left_data_sizes = encoded_data['left_data_sizes']
        right_data_sizes = encoded_data['right_data_sizes']
        
        for i in range(num_containers):
            reverse_idx = num_containers - 1 - i
            
            # Initialize both controllers
            self.dlp.setbmp(reverse_idx, left_data_sizes[reverse_idx])
            self.dlp.setbmp_secondary(reverse_idx, right_data_sizes[reverse_idx])
            
            # Upload to both controllers
            self.dlp.bmpload(left_encoded_images[reverse_idx], left_data_sizes[reverse_idx])
            self.dlp.bmpload_secondary(right_encoded_images[reverse_idx], right_data_sizes[reverse_idx])
            
            # Progress update every 2 containers
            if (i + 1) % 2 == 0 or i == num_containers - 1:
                elapsed = time.time() - upload_start_time
                remaining = (elapsed / (i + 1)) * (num_containers - i - 1)
                self._update_status(f"  Progress: {i + 1}/{num_containers} containers ({elapsed:.1f}s elapsed, ~{remaining:.1f}s remaining)")
        
        self._update_status(f"✓ Upload complete in {time.time() - upload_start_time:.1f}s")
        
        # Step 3: Configure LUT (same as normal upload)
        self._update_status("Configuring pattern sequence (LUT)...")
        self._update_status(f"  Total patterns to configure: {num_patterns}")
        
        exposure_times_us = [int(t * 1_000_000) for t in exposure_times]
        self._update_status(f"  Exposure times: First={exposure_times_us[0]}µs, Last={exposure_times_us[-1]}µs, Avg={int(np.mean(exposure_times_us))}µs")
        
        for i in range(num_patterns):
            container_idx = i // 24
            pattern_in_container = i % 24
            
            # CRITICAL: Use constant color='111' for all patterns (per DLPC900 guide)
            # Color controls LED output, NOT which bit to read
            # bitpos goes 0-23 directly across full container
            color = '111'  # Constant for seamless playback
            bit_pos = pattern_in_container  # Direct 0-23 mapping
            
            if i < 3 or i == num_patterns - 1 or i % 24 == 0 or i % 24 == 23:
                self._update_status(f"  Pattern {i}: exp={exposure_times_us[i]}µs, container={container_idx}, bit={bit_pos}, color={color}")
            
            self.dlp.definepattern(
                index=i,
                exposure=exposure_times_us[i],
                bitdepth=1,
                color=color,
                triggerin=False,
                darktime=0,
                triggerout=0,
                patind=container_idx,
                bitpos=bit_pos
            )
        
        # Step 4: Configure sequence
        self._update_status("Configuring sequence parameters...")
        
        total_sequence_time = sum(exposure_times)
        self._update_status(f"  CRITICAL TIMING INFO:")
        self._update_status(f"    - Patterns: {num_patterns}")
        self._update_status(f"    - Total sequence duration: {total_sequence_time:.2f}s")
        self._update_status(f"    - Average pattern time: {total_sequence_time/num_patterns:.3f}s")
        self._update_status(f"  WARNING: Sequence will complete in {total_sequence_time:.2f}s")
        self._update_status(f"           Stage motion may take longer!")
        self._update_status(f"           If print motion > {total_sequence_time:.2f}s, DLP will finish early")
        
        self._update_status(f"  Calling configurelut({num_patterns}, 0) - INFINITE REPEAT for testing")
        self.dlp.configurelut(num_patterns, 0)
        self._update_status("  ✓ LUT configured (repeat=0 - INFINITE)")
        
        upload_duration = time.time() - upload_start_time
        self._update_status(f"✓ Batch upload complete: {num_patterns} patterns in {upload_duration:.1f}s")
        
        return {
            'num_patterns': num_patterns,
            'num_containers': num_containers,
            'upload_time': upload_duration,
            'is_first_batch': is_first_batch,
            'pre_encoded': True
        }
    
    def _merge_patterns_to_container(self, patterns):
        """
        Merge up to 24 1-bit patterns into a single 24-bit RGB image.
        
        CRITICAL: Per DLPC900 Programmer's Guide and Gemini verification:
        - Encoder writes bytes in R-G-B order (image[:,:,0], image[:,:,1], image[:,:,2])
        - DLP interprets memory as B-G-R (1st byte=Blue=bitpos 0-7, 2nd=Green=8-15, 3rd=Red=16-23)
        - Therefore: 1st byte written (Red in numpy) → becomes Blue (bitpos 0-7) in DLP
        
        CORRECT Mapping (verified by Gemini):
        - Patterns 0-7 → numpy[:,:,0] (Red) → Encoder writes 1st → DLP reads as bitpos 0-7
        - Patterns 8-15 → numpy[:,:,1] (Green) → Encoder writes 2nd → DLP reads as bitpos 8-15
        - Patterns 16-23 → numpy[:,:,2] (Blue) → Encoder writes 3rd → DLP reads as bitpos 16-23
        
        Args:
            patterns: List of 1-bit numpy arrays (up to 24)
            
        Returns:
            RGB numpy array (1600x2560x3) with patterns packed into bit planes
        """
        merged = np.zeros((1600, 2560, 3), dtype=np.uint8)
        
        for i, pattern in enumerate(patterns):
            if i < 8:
                # Patterns 0-7: bitpos 0-7 (Blue in DLP, but Red in numpy because encoder swaps)
                merged[:, :, 0] += pattern * (2 ** i)
            elif i < 16:
                # Patterns 8-15: bitpos 8-15 (Green in both)
                merged[:, :, 1] += pattern * (2 ** (i - 8))
            else:
                # Patterns 16-23: bitpos 16-23 (Red in DLP, but Blue in numpy because encoder swaps)
                merged[:, :, 2] += pattern * (2 ** (i - 16))
        
        return merged
    
    def start_sequence(self):
        """
        Start the DLP pattern sequence.
        Call this after uploading a batch to begin displaying patterns.
        """
        self._update_status("="*60)
        self._update_status("STARTING DLP PATTERN SEQUENCE")
        self._update_status("="*60)
        self._update_status(f"  REMINDER: Sequence configured for {self.num_patterns_in_current_batch} patterns")
        self._update_status(f"            Currently in INFINITE REPEAT mode for testing")
        self._update_status(f"            Patterns will loop continuously until stopped")
        self._update_status("  Calling dlp.startsequence()...")
        self.dlp.startsequence()
        self._update_status("  ✓ Sequence started!")
        self._update_status("  → Patterns should be displaying NOW")
        self._update_status("  → Sequence will auto-advance through all patterns")
        self._update_status("  → If not visible, check:")
        self._update_status("     - DLP mode (should be 3 = pattern mode)")
        self._update_status("     - DLP power/standby")
        self._update_status("     - Projection screen visibility")
        self._update_status("="*60)
    
    def stop_sequence(self):
        """
        Stop the current DLP pattern sequence.
        Call this before uploading a new batch.
        """
        self._update_status("Stopping DLP pattern sequence...")
        self.dlp.stopsequence()
        self._update_status("  ✓ Sequence stopped")
    
    def calculate_batch_info(self, total_layers):
        """
        Calculate how many batches are needed for a given number of layers.
        
        Args:
            total_layers: Total number of layers in print
            
        Returns:
            dict with batch planning info
        """
        num_batches = (total_layers + self.batch_size - 1) // self.batch_size
        
        batch_info = {
            'total_layers': total_layers,
            'batch_size': self.batch_size,
            'num_batches': num_batches,
            'batches': []
        }
        
        for batch_idx in range(num_batches):
            start_layer = batch_idx * self.batch_size
            end_layer = min(start_layer + self.batch_size, total_layers)
            layers_in_batch = end_layer - start_layer
            
            batch_info['batches'].append({
                'batch_number': batch_idx,
                'start_layer': start_layer,
                'end_layer': end_layer,
                'num_layers': layers_in_batch,
                'is_first': batch_idx == 0
            })
        
        return batch_info


def test_batch_controller():
    """
    Test function to verify batch controller functionality.
    Run this independently to test pattern upload without a full print.
    """
    print("=" * 70)
    print("PATTERN BATCH CONTROLLER TEST")
    print("=" * 70)
    
    # This would normally use the actual DLP controller
    # For testing, we'd need to create a mock or use a real device
    print("\nTest requires actual DLP hardware or mock implementation.")
    print("Integration test should be done through Prince_PatternMode.py")


if __name__ == "__main__":
    test_batch_controller()
