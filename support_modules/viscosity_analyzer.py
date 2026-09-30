"""
In-Situ Viscosity Analyzer Module
=================================

Core mathematical engine for circular plate squeeze-flow rheometry
in vat photopolymerization 3D printing.

Features:
- Linearized Stefan regression (F^(-1/3) vs z) for simultaneous mu and z_0 extraction
- Lumped elastohydrodynamic compliance solver (decouples membrane flex from viscosity)
- Multi-speed power-law rheology solver (identifies Newtonian vs shear-thinning behavior)
- Pre-fluid dry membrane touch and stiffness detector
- Transfer-function relative calibration using reference fluids
- Synthetic squeeze curve generator for unit testing and validation

Author: Cheng Sun Lab Team
Date: September 2026
"""

import math
import numpy as np


class ViscosityAnalyzer:
    """
    Analyzes squeeze-flow force curves from circular build stages to extract
    fluid viscosity, zero-contact datum, membrane compliance, and non-Newtonian indices.
    """

    def __init__(self, stage_diameter_mm: float = 12.7):
        """
        Initialize analyzer with stage geometry.
        
        Args:
            stage_diameter_mm: Diameter of the circular build stage in mm (default: 12.7mm = 0.5")
        """
        self.stage_diameter_mm = float(stage_diameter_mm)
        self.stage_diameter_m = self.stage_diameter_mm * 1e-3
        self.stage_radius_m = self.stage_diameter_m / 2.0
        self.stage_area_m2 = math.pi * (self.stage_radius_m ** 2)
        
        # Geometric constant: C_geom = 3 * pi * D^4 / 32
        self.C_geom = (3.0 * math.pi * (self.stage_diameter_m ** 4)) / 32.0

    def analyze_stefan_linearized(
        self,
        z_mm: np.ndarray,
        force_n: np.ndarray,
        velocity_mm_s: float,
        tare_force_n: float = 0.0,
        gap_window_mm: tuple = (0.15, 0.45),
        z_contact_guess_mm: float = 0.0,
    ) -> dict:
        """
        Linearized Stefan solver: transforms F into F^(-1/3) and fits Y = m*z + c.
        
        Args:
            z_mm: 1D array of stage positions in mm
            force_n: 1D array of normal force readings in N
            velocity_mm_s: Constant descent speed in mm/s (positive value)
            tare_force_n: Baseline tare force to subtract
            gap_window_mm: (min_gap, max_gap) relative to z_contact_guess to restrict fit
            z_contact_guess_mm: Approximate datum position to evaluate gap window
            
        Returns:
            Dictionary containing:
                - viscosity_cp: Dynamic viscosity in centipoise (mPa.s)
                - viscosity_pa_s: Dynamic viscosity in Pa.s
                - z_contact_mm: Extrapolated zero-gap contact coordinate
                - r_squared: Goodness-of-fit coefficient of determination
                - slope: Slope of F^(-1/3) vs z
                - intercept: Intercept of F^(-1/3) vs z
                - points_used: Number of points included in regression
                - valid: Boolean flag indicating if regression met quality criteria
        """
        z = np.asarray(z_mm, dtype=float)
        F_raw = np.asarray(force_n, dtype=float)
        F = F_raw - tare_force_n
        v_m_s = abs(velocity_mm_s) * 1e-3

        if v_m_s <= 0:
            raise ValueError("Descent velocity must be positive non-zero.")

        # Window filtering based on approximate gap and positive force
        approx_gap = z - z_contact_guess_mm
        min_gap, max_gap = gap_window_mm
        
        mask = (F > 0.02) & (approx_gap >= min_gap) & (approx_gap <= max_gap)
        
        if np.sum(mask) < 5:
            # Fallback: take all points with positive force > 0.03N and reasonable range
            mask = (F > 0.03) & (F < 15.0)
            if np.sum(mask) < 5:
                return {
                    "valid": False,
                    "error": "Insufficient hydrodynamic force data in valid range (>0.03N)",
                    "viscosity_cp": 0.0,
                    "z_contact_mm": z_contact_guess_mm,
                    "r_squared": 0.0,
                    "points_used": int(np.sum(mask)),
                }

        z_sub = z[mask]
        F_sub = F[mask]

        # Transformation: Y = F^(-1/3)
        Y_sub = F_sub ** (-1.0 / 3.0)

        # Linear regression: Y = m * z + c
        # (z is in mm, so convert z to meters for direct SI viscosity computation)
        z_m_sub = z_sub * 1e-3
        
        N = len(z_m_sub)
        mean_z = np.mean(z_m_sub)
        mean_Y = np.mean(Y_sub)
        
        ss_zz = np.sum((z_m_sub - mean_z) ** 2)
        ss_zY = np.sum((z_m_sub - mean_z) * (Y_sub - mean_Y))
        ss_YY = np.sum((Y_sub - mean_Y) ** 2)

        if ss_zz <= 0:
            return {"valid": False, "error": "Zero variance in stage positions."}

        slope_m = ss_zY / ss_zz  # units: N^(-1/3) / m
        intercept = mean_Y - slope_m * mean_z

        # R-squared
        if ss_YY > 0:
            r_squared = (ss_zY ** 2) / (ss_zz * ss_YY)
        else:
            r_squared = 0.0

        # Physical checks: slope must be positive (F decreases as z increases, so F^(-1/3) increases with z)
        if slope_m <= 0:
            return {
                "valid": False,
                "error": "Non-physical negative slope in F^(-1/3) vs z",
                "slope": float(slope_m),
                "r_squared": float(r_squared),
                "points_used": N,
            }

        # Extracted zero-gap contact coordinate: z_0 = -intercept / slope (in meters -> convert to mm)
        z_0_m = -intercept / slope_m
        z_0_mm = z_0_m * 1e3

        # Dynamic viscosity mu from Stefan:
        # slope m = (32 / (3*pi*D^4 * v * mu))^(1/3) = (1 / (C_geom * v * mu))^(1/3)
        # m^3 = 1 / (C_geom * v * mu) => mu = 1 / (C_geom * v * m^3)
        mu_pa_s = 1.0 / (self.C_geom * v_m_s * (slope_m ** 3))
        mu_cp = mu_pa_s * 1000.0  # 1 Pa.s = 1000 cP

        return {
            "valid": bool(r_squared >= 0.85 and 0.1 <= mu_cp <= 50000.0),
            "viscosity_cp": float(mu_cp),
            "viscosity_pa_s": float(mu_pa_s),
            "z_contact_mm": float(z_0_mm),
            "r_squared": float(r_squared),
            "slope": float(slope_m),
            "intercept": float(intercept),
            "points_used": N,
            "z_filtered_mm": z_sub,
            "f_filtered_n": F_sub,
            "y_filtered": Y_sub,
        }

    def analyze_lumped_compliance(
        self,
        z_mm: np.ndarray,
        force_n: np.ndarray,
        velocity_mm_s: float,
        tare_force_n: float = 0.0,
    ) -> dict:
        """
        Multivariate regression decoupling viscosity from system compliance:
        z = beta_0 + beta_1 * F^(-1/3) - beta_2 * F
        
        Args:
            z_mm: Stage positions in mm
            force_n: Force in N
            velocity_mm_s: Descent speed in mm/s
            tare_force_n: Baseline tare
            
        Returns:
            Dictionary with viscosity, contact z_0, compliance, and fit stats.
        """
        z = np.asarray(z_mm, dtype=float)
        F = np.asarray(force_n, dtype=float) - tare_force_n
        v_m_s = abs(velocity_mm_s) * 1e-3

        mask = (F > 0.05) & (F < 15.0)
        if np.sum(mask) < 8:
            return {"valid": False, "error": "Insufficient points for compliance fit"}

        z_sub_m = z[mask] * 1e-3
        F_sub = F[mask]

        X1 = F_sub ** (-1.0 / 3.0)
        X2 = -F_sub
        X0 = np.ones_like(X1)

        X = np.column_stack([X0, X1, X2])

        try:
            # Solve OLS: beta = (X^T X)^(-1) X^T z
            beta, residuals, rank, s = np.linalg.lstsq(X, z_sub_m, rcond=None)
            beta_0, beta_1, beta_2 = beta

            # beta_1 = (C_geom * v * mu)^(1/3) => mu = beta_1^3 / (C_geom * v)
            if beta_1 <= 0:
                return {"valid": False, "error": "Non-physical beta_1 <= 0"}

            mu_pa_s = (beta_1 ** 3) / (self.C_geom * v_m_s)
            mu_cp = mu_pa_s * 1000.0

            z_0_mm = beta_0 * 1e3
            compliance_m_per_n = beta_2
            compliance_mm_per_n = compliance_m_per_n * 1e3
            stiffness_n_per_mm = 1.0 / compliance_mm_per_n if compliance_mm_per_n > 0 else 0.0

            # Compute R^2
            z_pred = X @ beta
            ss_tot = np.sum((z_sub_m - np.mean(z_sub_m)) ** 2)
            ss_res = np.sum((z_sub_m - z_pred) ** 2)
            r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

            return {
                "valid": bool(r_squared >= 0.90),
                "viscosity_cp": float(mu_cp),
                "viscosity_pa_s": float(mu_pa_s),
                "z_contact_mm": float(z_0_mm),
                "compliance_mm_per_n": float(compliance_mm_per_n),
                "stiffness_n_per_mm": float(stiffness_n_per_mm),
                "r_squared": float(r_squared),
                "points_used": len(z_sub_m),
            }
        except Exception as e:
            return {"valid": False, "error": str(e)}

    def analyze_multispeed(self, runs_data: list) -> dict:
        """
        Analyze multiple squeeze runs at different constant speeds to detect
        power-law non-Newtonian behavior: F(v) = C * v^n.
        
        Args:
            runs_data: List of dicts, each containing:
                - velocity_mm_s: float
                - z_mm: array
                - force_n: array
                - tare_force_n: float (optional)
                
        Returns:
            Dictionary with flow index n, rheology classification, and consistency index K.
        """
        if len(runs_data) < 2:
            raise ValueError("Multi-speed analysis requires at least 2 distinct velocity runs.")

        velocities = []
        clean_runs = []

        for run in runs_data:
            v = float(run["velocity_mm_s"])
            z = np.asarray(run["z_mm"], dtype=float)
            F = np.asarray(run["force_n"], dtype=float) - run.get("tare_force_n", 0.0)
            
            # Ensure strictly monotonic z for interpolation
            sort_idx = np.argsort(z)
            z_sorted = z[sort_idx]
            F_sorted = F[sort_idx]

            velocities.append(v)
            clean_runs.append((v, z_sorted, F_sorted))

        # Find common overlapping z range
        z_min_overlap = max(np.min(r[1]) for r in clean_runs)
        z_max_overlap = min(np.max(r[1]) for r in clean_runs)

        if z_min_overlap >= z_max_overlap:
            return {"valid": False, "error": "No overlapping z range across multi-speed runs"}

        # Select test grid points in overlap region
        z_grid = np.linspace(z_min_overlap, z_max_overlap, 20)
        
        n_estimates = []
        for z_eval in z_grid:
            forces_at_z = []
            for v, z_s, F_s in clean_runs:
                f_interp = float(np.interp(z_eval, z_s, F_s))
                forces_at_z.append(f_interp)
            
            forces_arr = np.array(forces_at_z)
            # Only use if all forces are reliably positive (>0.01 N)
            if np.all(forces_arr > 0.01):
                ln_v = np.log(velocities)
                ln_F = np.log(forces_arr)
                poly = np.polyfit(ln_v, ln_F, 1)
                n_estimates.append(poly[0])

        if len(n_estimates) < 3:
            # Fallback: take average of whatever valid points exist
            if len(n_estimates) == 0:
                n_slope = 1.0
            else:
                n_slope = float(np.median(n_estimates))
        else:
            # Take median or trimmed mean to reject boundary artifacts
            n_slope = float(np.median(n_estimates))

        # Run Stefan on each run to get individual viscosity estimates
        individual_viscosities_cp = []
        for run in runs_data:
            res = self.analyze_stefan_linearized(run["z_mm"], run["force_n"], run["velocity_mm_s"])
            if res.get("valid", False):
                individual_viscosities_cp.append(res["viscosity_cp"])

        mean_viscosity_cp = float(np.mean(individual_viscosities_cp)) if individual_viscosities_cp else 0.0

        # Rheological classification
        if 0.95 <= n_slope <= 1.05:
            classification = "Newtonian"
            is_newtonian = True
        elif n_slope < 0.95:
            classification = "Shear-Thinning (Pseudoplastic)"
            is_newtonian = False
        else:
            classification = "Dilatant (Shear-Thickening)"
            is_newtonian = False

        return {
            "valid": True,
            "flow_index_n": float(n_slope),
            "is_newtonian": is_newtonian,
            "classification": classification,
            "mean_viscosity_cp": mean_viscosity_cp,
            "individual_velocities_mm_s": velocities,
            "individual_viscosities_cp": individual_viscosities_cp,
        }

    def analyze_dry_membrane_touch(
        self,
        z_mm: np.ndarray,
        force_n: np.ndarray,
        tare_force_n: float = 0.0,
        touch_threshold_n: float = 0.03,
        max_safe_force_n: float = 2.0,
    ) -> dict:
        """
        Analyze a pre-fluid dry touch sequence in air to identify the true zero contact
        coordinate and measure membrane stiffness.
        
        Args:
            z_mm: Stage position array (descending)
            force_n: Normal force array
            tare_force_n: Baseline tare in air
            touch_threshold_n: Force rise threshold indicating physical touch (default 0.03N)
            max_safe_force_n: Safety ceiling
            
        Returns:
            Dictionary with touch detected, z_dry_touch_mm, membrane_stiffness_n_per_mm.
        """
        z = np.asarray(z_mm, dtype=float)
        F = np.asarray(force_n, dtype=float) - tare_force_n

        # Find first index where F exceeds touch threshold
        touch_indices = np.where(F >= touch_threshold_n)[0]

        if len(touch_indices) == 0:
            return {
                "touch_detected": False,
                "z_dry_touch_mm": None,
                "membrane_stiffness_n_per_mm": 0.0,
                "max_force_observed_n": float(np.max(F)),
            }

        first_touch_idx = touch_indices[0]
        z_touch = float(z[first_touch_idx])

        # Measure slope over the contact indentation region: dF / dz
        # (z is descending, so as z decreases, F increases => slope dF/dz is negative)
        contact_mask = (F >= touch_threshold_n) & (F <= max_safe_force_n)
        z_contact = z[contact_mask]
        F_contact = F[contact_mask]

        if len(z_contact) >= 4:
            # Linear fit: F = m * z + b
            m, b = np.polyfit(z_contact, F_contact, 1)
            stiffness_n_per_mm = abs(float(m))
        else:
            stiffness_n_per_mm = 0.0

        return {
            "touch_detected": True,
            "z_dry_touch_mm": z_touch,
            "membrane_stiffness_n_per_mm": stiffness_n_per_mm,
            "max_force_observed_n": float(np.max(F)),
            "points_in_contact": int(len(z_contact)),
        }

    def generate_synthetic_squeeze_curve(
        self,
        viscosity_cp: float,
        velocity_mm_s: float,
        z_start_mm: float = 1.0,
        z_end_mm: float = 0.1,
        z_contact_mm: float = 0.0,
        num_points: int = 100,
        noise_std_n: float = 0.005,
        compliance_mm_per_n: float = 0.0,
        power_law_n: float = 1.0,
    ) -> tuple:
        """
        Generate synthetic (z, F) data for testing and algorithm validation.
        
        Returns:
            Tuple of (z_mm_array, force_n_array)
        """
        z = np.linspace(z_start_mm, z_end_mm, num_points)
        v_m_s = abs(velocity_mm_s) * 1e-3
        mu_pa_s = (viscosity_cp * 1e-3)
        R_m = self.stage_radius_m

        forces = []
        for z_i in z:
            gap_nom_m = (z_i - z_contact_mm) * 1e-3
            if gap_nom_m <= 0:
                forces.append(50.0)  # Solid mechanical collision
                continue

            # Classical Stefan or Power-law
            if abs(power_law_n - 1.0) < 1e-4:
                # Newtonian
                if compliance_mm_per_n > 0:
                    # Solve F = C * mu * v / (h + F/k)^3 iteratively
                    F_est = (self.C_geom * mu_pa_s * v_m_s) / (gap_nom_m ** 3)
                    for _ in range(5):
                        h_eff_m = gap_nom_m + (F_est * compliance_mm_per_n * 1e-3)
                        F_est = (self.C_geom * mu_pa_s * v_m_s) / (h_eff_m ** 3)
                    F = F_est
                else:
                    F = (self.C_geom * mu_pa_s * v_m_s) / (gap_nom_m ** 3)
            else:
                # Power-law: F = ((2n+1)/n)^n * (2*pi*K*R^(n+3) / (n+3)) * (v^n / h^(2n+1))
                n = power_law_n
                prefactor = (((2.0 * n + 1.0) / n) ** n) * (2.0 * math.pi * mu_pa_s * (R_m ** (n + 3))) / (n + 3.0)
                F = prefactor * (v_m_s ** n) / (gap_nom_m ** (2.0 * n + 1.0))

            # Add Gaussian noise
            if noise_std_n > 0:
                noise = np.random.normal(0.0, noise_std_n)
                F = max(0.0, F + noise)

            forces.append(F)

        return z, np.array(forces)

    @staticmethod
    def compute_relative_viscosity_drift(baseline_slope: float, current_slope: float) -> dict:
        """
        Compute the percentage change in dynamic viscosity relative to a baseline:
            mu(t) / mu_0 = (m_0 / m(t))^3
            Delta_mu% = ((m_0 / m(t))^3 - 1.0) * 100%

        This method is completely immune to zero-point datum shifts (thermal expansion of z_0)
        and requires zero absolute calibration standards.

        Args:
            baseline_slope: Slope m_0 from linearized Stefan fit at start of day (N^(-1/3) / m)
            current_slope: Slope m_k from current linearized Stefan fit (N^(-1/3) / m)

        Returns:
            Dictionary containing:
                - valid: Boolean
                - viscosity_ratio: mu_k / mu_0 (1.0 = identical to baseline)
                - drift_percent: percentage change (+15% = thickened by 15%)
                - status: Human-readable description
                - alert_level: "NORMAL", "WARNING", or "CRITICAL"
        """
        if baseline_slope <= 0 or current_slope <= 0:
            return {
                "valid": False,
                "error": "Slopes must be strictly positive",
                "viscosity_ratio": 1.0,
                "drift_percent": 0.0,
                "status": "Invalid Slope",
                "alert_level": "NORMAL",
            }

        ratio = (baseline_slope / current_slope) ** 3.0
        drift_pct = (ratio - 1.0) * 100.0

        if drift_pct >= 25.0:
            status = f"Severe Thickening (+{drift_pct:.1f}% - Evaporation)"
            alert_level = "CRITICAL"
        elif drift_pct >= 10.0:
            status = f"Thickening (+{drift_pct:.1f}% - Solvent Loss)"
            alert_level = "WARNING"
        elif drift_pct <= -15.0:
            status = f"Significant Thinning ({drift_pct:.1f}% - Diluted/Hot)"
            alert_level = "WARNING"
        elif drift_pct <= -5.0:
            status = f"Slight Thinning ({drift_pct:.1f}% - Thermal Warmer)"
            alert_level = "NORMAL"
        else:
            status = f"Stable ({drift_pct:+.1f}% vs Baseline)"
            alert_level = "NORMAL"

        return {
            "valid": True,
            "viscosity_ratio": float(ratio),
            "drift_percent": float(drift_pct),
            "status": status,
            "alert_level": alert_level,
        }


def get_default_baseline_filepath() -> Path:
    """Return default path for daily viscosity baseline JSON."""
    repo_root = Path(__file__).resolve().parent.parent
    config_dir = repo_root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "daily_viscosity_baseline.json"


def save_daily_baseline(baseline_data: dict, filepath: Path = None) -> bool:
    """Save daily viscosity baseline dictionary to JSON."""
    import json
    path = filepath or get_default_baseline_filepath()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(baseline_data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving daily viscosity baseline: {e}")
        return False


def load_daily_baseline(filepath: Path = None, enforce_same_day: bool = True) -> dict:
    """
    Load daily viscosity baseline if exists.
    If enforce_same_day is True, returns None if file is from a previous day.
    """
    import json
    from datetime import date
    path = filepath or get_default_baseline_filepath()
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if enforce_day_check := enforce_same_day:
            today_str = date.today().isoformat()
            if data.get("date") != today_str:
                return None  # Expired baseline from yesterday
        return data
    except Exception as e:
        print(f"Error loading daily viscosity baseline: {e}")
        return None

