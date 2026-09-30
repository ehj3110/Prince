"""
Unit Tests for In-Situ Viscosity Analyzer & Rheology Solvers
============================================================

Compatible with both unittest and pytest.
"""

import sys
import unittest
from pathlib import Path
import numpy as np

# Add support_modules to path
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "support_modules"))

from viscosity_analyzer import ViscosityAnalyzer
from reference_fluids_db import get_reference_fluid_viscosity, list_available_fluids


class TestViscosityAnalyzer(unittest.TestCase):
    def test_analyzer_geometry(self):
        """Verify geometric prefactors for 12.7mm circular aluminum stage."""
        analyzer = ViscosityAnalyzer(stage_diameter_mm=12.7)
        self.assertEqual(analyzer.stage_diameter_mm, 12.7)
        self.assertAlmostEqual(analyzer.stage_radius_m, 0.00635, places=5)
        # C_geom = 3 * pi * D^4 / 32 approx 7.662e-9 m^4
        self.assertAlmostEqual(analyzer.C_geom, 7.662e-9, delta=1e-11)

    def test_stefan_linearized_exact_recovery(self):
        """Verify exact viscosity and datum recovery on noise-free synthetic Stefan data."""
        analyzer = ViscosityAnalyzer(stage_diameter_mm=12.7)
        target_mu_cp = 450.0  # 450 cP
        v_mm_s = 1.0          # 1 mm/s
        z_0_true = 50.000     # 50.0 mm stage datum

        z, F = analyzer.generate_synthetic_squeeze_curve(
            viscosity_cp=target_mu_cp,
            velocity_mm_s=v_mm_s,
            z_start_mm=50.500,
            z_end_mm=50.150,
            z_contact_mm=z_0_true,
            num_points=50,
            noise_std_n=0.0,
        )

        res = analyzer.analyze_stefan_linearized(
            z_mm=z,
            force_n=F,
            velocity_mm_s=v_mm_s,
            z_contact_guess_mm=z_0_true,
        )

        self.assertTrue(res["valid"])
        # Viscosity error < 0.5%
        self.assertLess(abs(res["viscosity_cp"] - target_mu_cp) / target_mu_cp, 0.005)
        # Contact point error < 1 micron (0.001 mm)
        self.assertLess(abs(res["z_contact_mm"] - z_0_true), 0.001)
        self.assertGreater(res["r_squared"], 0.9999)

    def test_stefan_linearized_with_noise(self):
        """Verify noise tolerance with 5mN load cell noise."""
        np.random.seed(42)
        analyzer = ViscosityAnalyzer(stage_diameter_mm=12.7)
        target_mu_cp = 300.0
        v_mm_s = 1.0
        z_0_true = 25.000

        z, F = analyzer.generate_synthetic_squeeze_curve(
            viscosity_cp=target_mu_cp,
            velocity_mm_s=v_mm_s,
            z_start_mm=25.400,
            z_end_mm=25.120,
            z_contact_mm=z_0_true,
            num_points=100,
            noise_std_n=0.005,  # 5 mN Gaussian noise
        )

        res = analyzer.analyze_stefan_linearized(
            z_mm=z,
            force_n=F,
            velocity_mm_s=v_mm_s,
            z_contact_guess_mm=z_0_true,
        )

        self.assertTrue(res["valid"])
        # Recovered within 3% despite noise
        self.assertLess(abs(res["viscosity_cp"] - target_mu_cp) / target_mu_cp, 0.03)
        # Contact point within 10 microns
        self.assertLess(abs(res["z_contact_mm"] - z_0_true), 0.010)
        self.assertGreater(res["r_squared"], 0.98)

    def test_multispeed_newtonian(self):
        """Verify that a Newtonian fluid yields flow index n approx 1.0."""
        analyzer = ViscosityAnalyzer(stage_diameter_mm=12.7)
        target_mu_cp = 500.0
        z_0 = 10.0

        runs = []
        for v in [0.5, 1.0, 2.0]:
            z, F = analyzer.generate_synthetic_squeeze_curve(
                viscosity_cp=target_mu_cp,
                velocity_mm_s=v,
                z_start_mm=10.450,
                z_end_mm=10.150,
                z_contact_mm=z_0,
                num_points=60,
                noise_std_n=0.0,
                power_law_n=1.0,
            )
            runs.append({"velocity_mm_s": v, "z_mm": z, "force_n": F})

        res = analyzer.analyze_multispeed(runs)
        self.assertTrue(res["valid"])
        self.assertTrue(res["is_newtonian"])
        self.assertEqual(res["classification"], "Newtonian")
        self.assertLess(abs(res["flow_index_n"] - 1.0), 0.03)
        self.assertLess(abs(res["mean_viscosity_cp"] - target_mu_cp) / target_mu_cp, 0.02)

    def test_multispeed_shear_thinning(self):
        """Verify that a shear-thinning fluid yields flow index n < 0.95."""
        analyzer = ViscosityAnalyzer(stage_diameter_mm=12.7)
        true_n = 0.70  # Strongly shear-thinning (e.g. ceramic slurry)
        z_0 = 10.0

        runs = []
        for v in [0.5, 1.0, 2.0]:
            z, F = analyzer.generate_synthetic_squeeze_curve(
                viscosity_cp=600.0,
                velocity_mm_s=v,
                z_start_mm=10.450,
                z_end_mm=10.150,
                z_contact_mm=z_0,
                num_points=60,
                noise_std_n=0.0,
                power_law_n=true_n,
            )
            runs.append({"velocity_mm_s": v, "z_mm": z, "force_n": F})

        res = analyzer.analyze_multispeed(runs)
        self.assertTrue(res["valid"])
        self.assertFalse(res["is_newtonian"])
        self.assertEqual(res["classification"], "Shear-Thinning (Pseudoplastic)")
        self.assertLess(abs(res["flow_index_n"] - true_n), 0.05)

    def test_dry_membrane_touch(self):
        """Verify pre-fluid dry touch detection and membrane stiffness measurement."""
        analyzer = ViscosityAnalyzer(stage_diameter_mm=12.7)
        
        # Simulate dry approach in air: zero force until z = 10.0mm, then linear spring k = 15 N/mm
        z_coords = np.linspace(10.2, 9.9, 31)  # 10um steps descending
        k_true = 15.0  # N/mm
        z_touch_true = 10.000

        forces = []
        for z_i in z_coords:
            if z_i > z_touch_true:
                forces.append(0.001)  # Air baseline
            else:
                indentation = z_touch_true - z_i
                forces.append(k_true * indentation)

        res = analyzer.analyze_dry_membrane_touch(
            z_mm=z_coords,
            force_n=np.array(forces),
            touch_threshold_n=0.03,
        )

        self.assertTrue(res["touch_detected"])
        # Contact detected within 1 step (10 um)
        self.assertLess(abs(res["z_dry_touch_mm"] - z_touch_true), 0.015)
        # Stiffness recovered within 5%
        self.assertLess(abs(res["membrane_stiffness_n_per_mm"] - k_true) / k_true, 0.05)

    def test_reference_fluids_db(self):
        """Verify reference fluid database lookups and temperature sensitivity."""
        fluids = list_available_fluids()
        self.assertIn("PEG 400 (Recommended)", fluids)
        self.assertIn("Glycerol 85% w/w (Recommended)", fluids)
        self.assertIn("Water (DI)", fluids)

        # Water at 20C should be ~1.002 cP
        mu_water_20 = get_reference_fluid_viscosity("Water (DI)", 20.0)
        self.assertLess(abs(mu_water_20 - 1.002), 0.05)

        # PEG 400 at 25C should be ~90 cP
        mu_peg_25 = get_reference_fluid_viscosity("PEG 400 (Recommended)", 25.0)
        self.assertLess(abs(mu_peg_25 - 90.0), 5.0)

        # Viscosity should decrease with increasing temperature
        mu_peg_20 = get_reference_fluid_viscosity("PEG 400 (Recommended)", 20.0)
        self.assertGreater(mu_peg_20, mu_peg_25)

    def test_relative_viscosity_drift(self):
        """Verify relative viscosity drift calculation under solvent evaporation."""
        analyzer = ViscosityAnalyzer(stage_diameter_mm=12.7)

        # Baseline: mu_0 = 400 cP => m_0 proportional to 400^(-1/3)
        mu_0 = 400.0
        m_0 = (1.0 / (analyzer.C_geom * 1e-3 * (mu_0 * 1e-3))) ** (1.0 / 3.0)

        # Thickened by exactly +25% (mu_1 = 500 cP) due to solvent evaporation
        mu_1 = 500.0
        m_1 = (1.0 / (analyzer.C_geom * 1e-3 * (mu_1 * 1e-3))) ** (1.0 / 3.0)

        res = analyzer.compute_relative_viscosity_drift(m_0, m_1)
        self.assertTrue(res["valid"])
        self.assertAlmostEqual(res["viscosity_ratio"], 1.25, places=4)
        self.assertAlmostEqual(res["drift_percent"], 25.0, places=2)
        self.assertEqual(res["alert_level"], "CRITICAL")
        self.assertIn("Severe Thickening", res["status"])

        # Thinning by -10% (e.g. warming)
        mu_warm = 360.0
        m_warm = (1.0 / (analyzer.C_geom * 1e-3 * (mu_warm * 1e-3))) ** (1.0 / 3.0)
        res_warm = analyzer.compute_relative_viscosity_drift(m_0, m_warm)
        self.assertAlmostEqual(res_warm["drift_percent"], -10.0, places=2)
        self.assertEqual(res_warm["alert_level"], "NORMAL")

    def test_daily_baseline_persistence(self):
        """Verify saving and loading daily baseline JSON with date validation."""
        import tempfile
        from datetime import date
        from viscosity_analyzer import save_daily_baseline, load_daily_baseline

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            today_str = date.today().isoformat()
            test_data = {
                "date": today_str,
                "timestamp": "09:30:00",
                "slope": 125.4,
                "intercept": 0.05,
                "r_squared": 0.998,
                "viscosity_cp": 415.0,
            }

            self.assertTrue(save_daily_baseline(test_data, filepath=tmp_path))
            loaded = load_daily_baseline(filepath=tmp_path, enforce_same_day=True)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded["slope"], 125.4)

            # Test expiration on yesterday's date
            test_data["date"] = "2020-01-01"
            save_daily_baseline(test_data, filepath=tmp_path)
            expired = load_daily_baseline(filepath=tmp_path, enforce_same_day=True)
            self.assertIsNone(expired)  # Expired baseline correctly discarded
        finally:
            if tmp_path.exists():
                tmp_path.unlink()


if __name__ == "__main__":
    unittest.main()
