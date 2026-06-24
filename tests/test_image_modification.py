# -*- coding: utf-8 -*-
"""
Test script for Image Modification module.

Runs through all routines that ImageModificationWindow can do:
- process_single_for_preview (EE only, GE only, both, neither)
- process_folder (EE only, GE only, both, padding)
- Output folder naming (EE_{blur}_{Padded|NoPad}_GE_{globe})
- Padding {x}_1.png naming

Test images path: C:\\Users\\cheng sun\\BoyuanSun\\Prince_CurrentWorkingVersion\\TestImages

Usage:
    python tests/test_image_modification.py
"""

import sys
import os
import unittest
import tempfile
import shutil
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "support_modules"))

TEST_IMAGES_PATH = project_root / "TestImages"

# Check for required dependencies
try:
    import cv2  # noqa: F401
    import numpy as np  # noqa: F401
    DEPS_AVAILABLE = True
except ImportError as e:
    DEPS_AVAILABLE = False
    IMPORT_ERROR = str(e)


def ensure_test_images():
    """Create TestImages folder and synthetic PNGs if empty."""
    TEST_IMAGES_PATH.mkdir(parents=True, exist_ok=True)
    existing = list(TEST_IMAGES_PATH.glob("*.png"))
    # Exclude *_1.png (padding outputs)
    existing = [f for f in existing if not (f.name.count("_") == 1 and f.stem.endswith("_1"))]
    if existing:
        return

    import cv2
    import numpy as np
    # Create 3 synthetic images: 1.png, 2.png, 3.png, 1600x2560 (typical SLA size)
    rows, cols = 160, 256  # Smaller for fast tests
    for i in range(1, 4):
        img = np.zeros((rows, cols), dtype=np.uint8)
        # Add some pattern (circle + gradient)
        center = (cols // 2, rows // 2)
        for y in range(rows):
            for x in range(cols):
                d = ((x - center[0]) ** 2 + (y - center[1]) ** 2) ** 0.5
                if d < 40:
                    img[y, x] = 200
                elif d < 80:
                    img[y, x] = 100
        img = cv2.GaussianBlur(img, (5, 5), 2)
        path = TEST_IMAGES_PATH / f"{i}.png"
        cv2.imwrite(str(path), img)
        print(f"  Created {path.name}")


@unittest.skipUnless(DEPS_AVAILABLE, f"Requires cv2/numpy: {IMPORT_ERROR if not DEPS_AVAILABLE else ''}")
class TestImageModification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ensure_test_images()
        cls.test_path = str(TEST_IMAGES_PATH)

    def test_process_single_for_preview_no_enhancements(self):
        """Preview: no EE, no GE."""
        from support_modules.image_modification.processor import process_single_for_preview

        images = sorted(Path(self.test_path).glob("*.png"), key=lambda p: int(p.stem) if p.stem.isdigit() else 0)
        images = [p for p in images if "_" not in p.stem or not p.stem.endswith("_1")]
        self.assertGreater(len(images), 0, "No test images found")
        path = str(images[0])
        result = process_single_for_preview(path, edge_enabled=False, blurring=25, global_enabled=False, globe=0.8, sigma=6.0)
        self.assertIsNotNone(result)
        self.assertEqual(result.dtype, "uint8")
        self.assertEqual(result.ndim, 2)

    def test_process_single_for_preview_edge_only(self):
        """Preview: EE only."""
        from support_modules.image_modification.processor import process_single_for_preview

        images = sorted(Path(self.test_path).glob("*.png"), key=lambda p: int(p.stem) if p.stem.isdigit() else 0)
        images = [p for p in images if "_" not in p.stem or not p.stem.endswith("_1")]
        path = str(images[0])
        result = process_single_for_preview(path, edge_enabled=True, blurring=25, global_enabled=False, globe=0.8, sigma=6.0)
        self.assertIsNotNone(result)
        self.assertEqual(result.dtype, "uint8")

    def test_process_single_for_preview_global_only(self):
        """Preview: GE only."""
        from support_modules.image_modification.processor import process_single_for_preview

        images = sorted(Path(self.test_path).glob("*.png"), key=lambda p: int(p.stem) if p.stem.isdigit() else 0)
        images = [p for p in images if "_" not in p.stem or not p.stem.endswith("_1")]
        path = str(images[0])
        result = process_single_for_preview(path, edge_enabled=False, blurring=25, global_enabled=True, globe=0.8, sigma=6.0)
        self.assertIsNotNone(result)
        self.assertEqual(result.dtype, "uint8")

    def test_process_single_for_preview_both(self):
        """Preview: EE + GE."""
        from support_modules.image_modification.processor import process_single_for_preview

        images = sorted(Path(self.test_path).glob("*.png"), key=lambda p: int(p.stem) if p.stem.isdigit() else 0)
        images = [p for p in images if "_" not in p.stem or not p.stem.endswith("_1")]
        path = str(images[0])
        result = process_single_for_preview(path, edge_enabled=True, blurring=25, global_enabled=True, globe=0.8, sigma=6.0)
        self.assertIsNotNone(result)
        self.assertEqual(result.dtype, "uint8")

    def test_process_single_for_preview_asymmetric(self):
        """Preview: GE asymmetric (angular sectors, 90° compatibility)."""
        from support_modules.image_modification.processor import process_single_for_preview

        images = sorted(Path(self.test_path).glob("*.png"), key=lambda p: int(p.stem) if p.stem.isdigit() else 0)
        images = [p for p in images if "_" not in p.stem or not p.stem.endswith("_1")]
        path = str(images[0])
        result = process_single_for_preview(path, edge_enabled=False, blurring=25, global_enabled=True, globe=0.8, sigma=6.0, global_asymmetric=True, blend_angle=20.0)
        self.assertIsNotNone(result)
        self.assertEqual(result.dtype, "uint8")

    def test_process_single_for_preview_asymmetric_fine_slices(self):
        """Preview: GE asymmetric with fine angular slices (e.g., 10°)."""
        from support_modules.image_modification.processor import process_single_for_preview

        images = sorted(Path(self.test_path).glob("*.png"), key=lambda p: int(p.stem) if p.stem.isdigit() else 0)
        images = [p for p in images if "_" not in p.stem or not p.stem.endswith("_1")]
        path = str(images[0])
        result = process_single_for_preview(
            path,
            edge_enabled=False,
            blurring=25,
            global_enabled=True,
            globe=0.8,
            sigma=6.0,
            global_asymmetric=True,
            blend_angle=8.0,
            ge_sector_angle=10.0,
            ge_sector_smoothing=1,
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.dtype, "uint8")

    def test_process_folder_edge_only(self):
        """Build: EE only, no padding."""
        from support_modules.image_modification.processor import process_folder

        output = process_folder(
            self.test_path,
            edge_enabled=True,
            blurring=25,
            global_enabled=False,
            globe=0.8,
            sigma=6.0,
            padding_enabled=False,
        )
        self.assertTrue(os.path.isdir(output))
        self.assertIn("EE_25_NoPad_GE_0", output)
        out_files = sorted(os.listdir(output))
        self.assertGreater(len(out_files), 0)
        for f in out_files:
            self.assertTrue(f.endswith(".png"))

    def test_process_folder_global_only(self):
        """Build: GE only."""
        from support_modules.image_modification.processor import process_folder

        output = process_folder(
            self.test_path,
            edge_enabled=False,
            blurring=25,
            global_enabled=True,
            globe=0.8,
            sigma=6.0,
            padding_enabled=False,
        )
        self.assertTrue(os.path.isdir(output))
        self.assertIn("EE_0_NoPad_GE_0_8", output)

    def test_process_folder_both_ee_ge(self):
        """Build: EE + GE."""
        from support_modules.image_modification.processor import process_folder

        output = process_folder(
            self.test_path,
            edge_enabled=True,
            blurring=25,
            global_enabled=True,
            globe=0.8,
            sigma=6.0,
            padding_enabled=False,
        )
        self.assertTrue(os.path.isdir(output))
        self.assertIn("EE_25_NoPad_GE_0_8", output)

    def test_process_folder_with_padding(self):
        """Build: EE + padding ({x}_1.png naming)."""
        from support_modules.image_modification.processor import process_folder

        output = process_folder(
            self.test_path,
            edge_enabled=True,
            blurring=25,
            global_enabled=False,
            globe=0.8,
            sigma=6.0,
            padding_enabled=True,
        )
        self.assertTrue(os.path.isdir(output))
        self.assertIn("Padded", output)
        out_files = sorted(os.listdir(output))
        # Expect: 1.png, 1_1.png, 2.png, 2_1.png, 3.png, 3_1.png
        padded = [f for f in out_files if "_1.png" in f]
        self.assertGreater(len(padded), 0)

    def test_process_folder_asymmetric_fine_slices(self):
        """Build: GE asymmetric with fine angular slices and naming tags."""
        from support_modules.image_modification.processor import process_folder

        output = process_folder(
            self.test_path,
            edge_enabled=False,
            blurring=25,
            global_enabled=True,
            globe=0.8,
            sigma=6.0,
            padding_enabled=False,
            global_asymmetric=True,
            blend_angle=8.0,
            ge_sector_angle=10.0,
            ge_sector_smoothing=1,
        )
        self.assertTrue(os.path.isdir(output))
        self.assertIn("_AsymA10", output)

    def test_angular_profile_interpolation_is_continuous(self):
        """Angular profile interpolation should not jump at sector boundaries."""
        from support_modules.image_modification.global_enhancement import _sample_blended_circular_profile

        profile = np.array([1.0, 2.5, 4.0, 2.0], dtype=np.float64)
        theta = np.array([89.999, 90.001], dtype=np.float64)
        values = _sample_blended_circular_profile(theta, profile, sector_angle_deg=90.0, blend_angle_deg=20.0)
        self.assertLess(abs(values[0] - values[1]), 0.01)

    def test_blend_angle_changes_result(self):
        """Blend angle should materially change the sampled angular profile."""
        from support_modules.image_modification.global_enhancement import _sample_blended_circular_profile

        profile = np.array([1.0, 4.0], dtype=np.float64)
        theta = np.array([1.0, 45.0, 89.0], dtype=np.float64)
        no_blend = _sample_blended_circular_profile(theta, profile, sector_angle_deg=90.0, blend_angle_deg=0.0)
        full_blend = _sample_blended_circular_profile(theta, profile, sector_angle_deg=90.0, blend_angle_deg=180.0)
        self.assertFalse(np.allclose(no_blend, full_blend))

    def test_import_image_modification_window(self):
        """Import ImageModificationWindow (GUI class)."""
        from support_modules.ImageModificationWindow import ImageModificationWindow

        self.assertTrue(callable(ImageModificationWindow))


def run_standalone():
    """Run as standalone script with verbose output."""
    if not DEPS_AVAILABLE:
        print(f"SKIP: Cannot run tests - {IMPORT_ERROR}")
        print("Install: pip install numpy opencv-python")
        return False
    ensure_test_images()
    print(f"\nTest images: {TEST_IMAGES_PATH}")
    print(f"Source images: {list(TEST_IMAGES_PATH.glob('*.png'))}\n")
    print("Running Image Modification tests...\n")
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestImageModification)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_standalone()
    sys.exit(0 if success else 1)
