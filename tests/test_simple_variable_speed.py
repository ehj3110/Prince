# -*- coding: utf-8 -*-
"""Unit tests for support_modules.simple_variable_speed."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from support_modules.simple_variable_speed import (
    compute_dmax_mm,
    compute_layer_pwm,
    compute_speed_um_s,
    fill_holes_by_max_ecd,
    rewrite_instruction_times_intensities,
)


def _disk_mask(size: int, cx: float, cy: float, radius_px: float) -> np.ndarray:
    yy, xx = np.ogrid[:size, :size]
    return ((xx - cx) ** 2 + (yy - cy) ** 2) <= radius_px**2


def _annulus_mask(
    size: int, cx: float, cy: float, r_out_px: float, r_in_px: float
) -> np.ndarray:
    yy, xx = np.ogrid[:size, :size]
    r2 = (xx - cx) ** 2 + (yy - cy) ** 2
    return (r2 <= r_out_px**2) & (r2 >= r_in_px**2)


class TestSimpleVariableSpeed(unittest.TestCase):
    def test_solid_disk_dmax_approx_radius(self):
        pitch = 0.01  # mm/px
        size = 500
        cx = cy = 249.5
        r_mm = 0.50
        r_px = r_mm / pitch
        mask = _disk_mask(size, cx, cy, r_px)
        d_max = compute_dmax_mm(mask, px_pitch_mm=pitch, fill_holes=False)
        self.assertLessEqual(abs(d_max - r_mm), 0.015)

    def test_small_pinhole_filled_when_below_threshold(self):
        pitch = 0.01
        size = 500
        cx = cy = 249.5
        r_out_mm, r_in_mm = 1.00, 0.10
        mask = _annulus_mask(size, cx, cy, r_out_mm / pitch, r_in_mm / pitch)

        d_filled = compute_dmax_mm(
            mask, px_pitch_mm=pitch, fill_holes=True, max_hole_mm=0.15
        )
        self.assertLessEqual(abs(d_filled - (r_out_mm - r_in_mm)), 0.03)

    def test_large_hole_not_filled_above_threshold(self):
        pitch = 0.01
        size = 500
        cx = cy = 249.5
        r_out_mm, r_in_mm = 2.00, 1.50
        mask = _annulus_mask(size, cx, cy, r_out_mm / pitch, r_in_mm / pitch)

        d_raw = compute_dmax_mm(
            mask, px_pitch_mm=pitch, fill_holes=True, max_hole_mm=1.0
        )
        wall_half = 0.5 * (r_out_mm - r_in_mm)
        self.assertLessEqual(abs(d_raw - wall_half), 0.05)

    def test_fill_holes_by_max_ecd_respects_threshold(self):
        pitch = 0.01
        size = 200
        cx = cy = 99.5
        mask = _annulus_mask(size, cx, cy, 40, 8)
        filled = fill_holes_by_max_ecd(mask, max_hole_mm=0.10, px_pitch_mm=pitch)
        self.assertTrue(filled[100, 100])
        not_filled = fill_holes_by_max_ecd(mask, max_hole_mm=0.05, px_pitch_mm=pitch)
        self.assertFalse(not_filled[100, 100])

    def test_speed_law_control_invariance_and_correction_zero(self):
        v0 = 1000.0
        r0 = 0.5
        for c in (0.0, 1.0, 2.5):
            self.assertAlmostEqual(compute_speed_um_s(0.5, r0, v0, c), v0)
        self.assertAlmostEqual(compute_speed_um_s(2.0, r0, v0, 0.0), v0)
        v_slow = compute_speed_um_s(1.0, r0, v0, 1.0)
        self.assertLess(v_slow, v0)
        v_slower = compute_speed_um_s(1.0, r0, v0, 2.0)
        self.assertLess(v_slower, v_slow)

    def test_speed_law_beta4_analytic(self):
        v0 = 1000.0
        r0 = 0.5
        d = 1.0  # R_tilde = 2 → 2^4 - 1 = 15 → v = v0 / 16
        self.assertAlmostEqual(compute_speed_um_s(d, r0, v0, 1.0), v0 / 16.0)

    def test_pwm_dose_coupling_and_empty_layer(self):
        thickness = 5.0  # um
        v0 = 1000.0
        pwm_ctrl = 200
        dose = pwm_ctrl * thickness / v0
        pwm, t = compute_layer_pwm(v0, v0, dose, thickness, white_pixel_count=10)
        self.assertEqual(pwm, 200)
        self.assertAlmostEqual(t, thickness / v0)

        pwm2, t2 = compute_layer_pwm(v0 / 2, v0, dose, thickness, white_pixel_count=10)
        self.assertEqual(pwm2, 100)
        self.assertAlmostEqual(t2, 2.0 * thickness / v0)

        pwm0, t0 = compute_layer_pwm(v0, v0, dose, thickness, white_pixel_count=0)
        self.assertEqual(pwm0, 0)
        self.assertAlmostEqual(t0, thickness / v0)

    def test_rewrite_preserves_other_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "PartA"
            folder.mkdir()
            txt = folder / "PartA.txt"
            txt.write_text(
                "Layer\tFile\tThickness\tTime\tIntensity\tStep Speed\t"
                "Overstep Distance\tAcceleration\tPause\tSandwich Speed\n"
                "1\t1.png\t5\t0.010000\t255\t800\t0\t6\t0.5\t600\n"
                "2\t2.png\t5\t0.020000\t128\t800\t0\t6\t0.5\t600\n",
                encoding="utf-8",
            )
            rewrite_instruction_times_intensities(txt, [0.1, 0.2], [50, 25])
            lines = txt.read_text(encoding="utf-8").strip().splitlines()
            r1 = lines[1].split("\t")
            r2 = lines[2].split("\t")
            self.assertEqual(r1[3], "0.100000")
            self.assertEqual(r1[4], "50")
            self.assertEqual(r1[5], "800")
            self.assertEqual(r1[6], "0")
            self.assertEqual(r1[7], "6")
            self.assertEqual(r1[8], "0.5")
            self.assertEqual(r1[9], "600")
            self.assertEqual(r2[3], "0.200000")
            self.assertEqual(r2[4], "25")
            self.assertEqual(r2[5], "800")

    def test_dmax_prince_pitch_smoke(self):
        """Smoke check at Prince pitch 4.005 um."""
        pitch = 0.004005
        size = 400
        cx = cy = 199.5
        r_mm = 0.40
        mask = _disk_mask(size, cx, cy, r_mm / pitch)
        d_max = compute_dmax_mm(mask, px_pitch_mm=pitch, fill_holes=False)
        self.assertLessEqual(abs(d_max - r_mm), 0.02)


if __name__ == "__main__":
    unittest.main()
