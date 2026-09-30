"""
Viscosity Monitor Window
========================

Dedicated secondary GUI window for in-situ resin viscosity measurement,
relative viscosity drift tracking (solvent evaporation), multi-speed rheology probing,
pre-fluid dry membrane touch checks, and daily reference precalibrations.

DEFAULT OPERATING MODE:
Relative Viscosity Tracking (Delta mu / mu_0 %):
Automatically tracks resin thickening across the day due to solvent/reactive diluent
evaporation without requiring external calibration fluids.

Author: Cheng Sun Lab Team
Date: September 2026
"""

from datetime import date, datetime
import math
from pathlib import Path
import queue
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk
import numpy as np

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from reference_fluids_db import (
    REFERENCE_FLUIDS,
    get_reference_fluid_viscosity,
    list_available_fluids,
)
from viscosity_analyzer import (
    ViscosityAnalyzer,
    load_daily_baseline,
    save_daily_baseline,
)

try:
    from zaber_motion import Units
except ImportError:
    Units = None


class ViscosityMonitorWindow:
    """
    Dedicated window for measuring and displaying in-situ resin viscosity,
    relative evaporation drift (% change), and force-position curves.
    """

    def __init__(
        self,
        parent_window,
        axis=None,
        force_gauge=None,
        update_status_callback=None,
        prince_main_app_ref=None,
    ):
        self.parent = parent_window
        self.axis = axis
        self.force_gauge = force_gauge
        self.update_status = update_status_callback or (lambda msg, error=False: print(msg))
        self.prince_app = prince_main_app_ref

        self.analyzer = ViscosityAnalyzer(stage_diameter_mm=12.7)

        # State variables
        self.is_probing = False
        self.abort_requested = False
        self.probe_thread = None
        self.tare_offset_n = 0.0

        # Load today's baseline if already recorded today
        self.daily_baseline = load_daily_baseline()
        self.daily_history = []  # list of {time, slope, drift_pct, status}

        # Calibration & dry touch baselines
        self.dry_datum_z_mm = None
        self.membrane_stiffness_n_mm = None
        self.latest_viscosity_cp = None
        self.latest_slope = None
        self.latest_drift_pct = 0.0
        self.latest_flow_index_n = None
        self.latest_r_squared = None

        # Build GUI
        self.window = tk.Toplevel(parent_window)
        self.window.title("In-Situ Resin Viscosity & Evaporation Monitor (Ø12.7mm Stage)")
        self.window.geometry("1060x860")
        self.window.minsize(920, 720)

        # Style configuration
        self.bg_color = "#f4f5f7"
        self.accent_color = "#1e3d59"
        self.window.configure(bg=self.bg_color)

        self._create_widgets()
        self._setup_plots()
        self._update_baseline_ui()

    def _create_widgets(self):
        """Construct top banner, control frames, and metrics panels."""
        # --- Top Banner ---
        banner_frame = tk.Frame(self.window, bg=self.accent_color, height=50)
        banner_frame.pack(side=tk.TOP, fill=tk.X)

        title_lbl = tk.Label(
            banner_frame,
            text="In-Situ Resin Viscosity & Evaporation Drift Monitor",
            font=("Helvetica", 14, "bold"),
            fg="white",
            bg=self.accent_color,
            pady=10,
        )
        title_lbl.pack(side=tk.LEFT, padx=15)

        sub_lbl = tk.Label(
            banner_frame,
            text="Relative Solvent Drift Tracking (Default) • Cheng Sun Lab",
            font=("Helvetica", 9, "italic"),
            fg="#e0e0e0",
            bg=self.accent_color,
        )
        sub_lbl.pack(side=tk.RIGHT, padx=15)

        # --- Main Layout Container ---
        main_container = tk.Frame(self.window, bg=self.bg_color)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left Column: Controls & Metrics (width ~370px)
        left_frame = tk.Frame(main_container, bg=self.bg_color, width=380)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        # Right Column: Live Matplotlib Plots
        self.right_frame = tk.Frame(main_container, bg="white", relief=tk.RIDGE, bd=1)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # --- Section 1: Pre-Fluid Dry Check Frame ---
        dry_frame = tk.LabelFrame(
            left_frame,
            text="1. Pre-Fluid Dry Check (Membrane Touch)",
            font=("Helvetica", 10, "bold"),
            bg=self.bg_color,
            padx=8,
            pady=6,
        )
        dry_frame.pack(fill=tk.X, pady=(0, 6))

        dry_desc = tk.Label(
            dry_frame,
            text="Run before adding resin to find true dry datum z_0 and verify membrane stiffness.",
            font=("Helvetica", 8),
            fg="#555555",
            bg=self.bg_color,
            wraplength=340,
            justify=tk.LEFT,
        )
        dry_desc.pack(anchor=tk.W, pady=(0, 4))

        self.btn_dry_check = tk.Button(
            dry_frame,
            text="Run Pre-Fluid Dry Touch Check",
            command=self.run_pre_fluid_check,
            bg="#3b71ca",
            fg="white",
            font=("Helvetica", 9, "bold"),
            relief=tk.RAISED,
            padx=6,
            pady=3,
        )
        self.btn_dry_check.pack(fill=tk.X, pady=2)

        self.lbl_dry_status = tk.Label(
            dry_frame,
            text="Dry Datum: Not measured | Stiffness: --",
            font=("Helvetica", 8),
            fg="#333333",
            bg=self.bg_color,
        )
        self.lbl_dry_status.pack(anchor=tk.W, pady=(2, 0))

        # --- Section 2: Relative Baseline & Solvent Evaporation Tracking ---
        base_frame = tk.LabelFrame(
            left_frame,
            text="2. Daily Baseline & Evaporation Tracking (Default)",
            font=("Helvetica", 10, "bold"),
            bg="#eaf2f8",
            padx=8,
            pady=6,
        )
        base_frame.pack(fill=tk.X, pady=(0, 6))

        base_desc = tk.Label(
            base_frame,
            text="Zero calibration required: Compares current resin squeeze slope against today's fresh baseline to detect solvent loss.",
            font=("Helvetica", 8),
            fg="#2c3e50",
            bg="#eaf2f8",
            wraplength=340,
            justify=tk.LEFT,
        )
        base_desc.pack(anchor=tk.W, pady=(0, 4))

        self.lbl_baseline_status = tk.Label(
            base_frame,
            text="Active Baseline: None (First run sets baseline)",
            font=("Helvetica", 9, "bold"),
            fg="#1b4f72",
            bg="#eaf2f8",
            wraplength=340,
            justify=tk.LEFT,
        )
        self.lbl_baseline_status.pack(anchor=tk.W, pady=2)

        base_btn_box = tk.Frame(base_frame, bg="#eaf2f8")
        base_btn_box.pack(fill=tk.X, pady=3)

        self.btn_set_baseline = tk.Button(
            base_btn_box,
            text="Set Fresh Resin Baseline (Reset to 0%)",
            command=self.set_fresh_resin_baseline,
            bg="#2980b9",
            fg="white",
            font=("Helvetica", 8, "bold"),
            padx=4,
            pady=2,
        )
        self.btn_set_baseline.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

        self.btn_clear_baseline = tk.Button(
            base_btn_box,
            text="Clear Baseline",
            command=self.clear_baseline,
            bg="#95a5a6",
            fg="white",
            font=("Helvetica", 8),
            padx=4,
            pady=2,
        )
        self.btn_clear_baseline.pack(side=tk.RIGHT)

        # --- Section 3: Probing Controls ---
        probe_frame = tk.LabelFrame(
            left_frame,
            text="3. Squeeze Flow Measurement Controls",
            font=("Helvetica", 10, "bold"),
            bg=self.bg_color,
            padx=8,
            pady=6,
        )
        probe_frame.pack(fill=tk.X, pady=(0, 6))

        v_grid = tk.Frame(probe_frame, bg=self.bg_color)
        v_grid.pack(fill=tk.X, pady=2)

        tk.Label(v_grid, text="v1 (mm/s):", bg=self.bg_color, font=("Helvetica", 8)).grid(row=0, column=0, sticky=tk.W)
        self.ent_v1 = tk.Entry(v_grid, width=5)
        self.ent_v1.insert(0, "0.5")
        self.ent_v1.grid(row=0, column=1, padx=2)

        tk.Label(v_grid, text="v2:", bg=self.bg_color, font=("Helvetica", 8)).grid(row=0, column=2, sticky=tk.W)
        self.ent_v2 = tk.Entry(v_grid, width=5)
        self.ent_v2.insert(0, "1.0")
        self.ent_v2.grid(row=0, column=3, padx=2)

        tk.Label(v_grid, text="v3:", bg=self.bg_color, font=("Helvetica", 8)).grid(row=0, column=4, sticky=tk.W)
        self.ent_v3 = tk.Entry(v_grid, width=5)
        self.ent_v3.insert(0, "2.0")
        self.ent_v3.grid(row=0, column=5, padx=2)

        btn_box = tk.Frame(probe_frame, bg=self.bg_color)
        btn_box.pack(fill=tk.X, pady=4)

        self.btn_single_probe = tk.Button(
            btn_box,
            text="Quick Single Probe (Default)",
            command=self.run_single_probe,
            bg="#14a44d",
            fg="white",
            font=("Helvetica", 9, "bold"),
            padx=4,
            pady=3,
        )
        self.btn_single_probe.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

        self.btn_multi_probe = tk.Button(
            btn_box,
            text="Multi-Speed Probe",
            command=self.run_multi_speed_probe,
            bg="#3b71ca",
            fg="white",
            font=("Helvetica", 9, "bold"),
            padx=4,
            pady=3,
        )
        self.btn_multi_probe.pack(side=tk.RIGHT, fill=tk.X, expand=True)

        self.btn_abort = tk.Button(
            probe_frame,
            text="ABORT MOTION",
            command=self.abort_motion,
            bg="#dc4c64",
            fg="white",
            font=("Helvetica", 8, "bold"),
            state=tk.DISABLED,
        )
        self.btn_abort.pack(fill=tk.X, pady=(2, 0))

        # --- Section 4: Live Viscosity Drift Dashboard ---
        metrics_frame = tk.LabelFrame(
            left_frame,
            text="Current Viscosity & Evaporation Drift",
            font=("Helvetica", 10, "bold"),
            bg="#eef2f7",
            padx=8,
            pady=6,
        )
        metrics_frame.pack(fill=tk.BOTH, expand=True)

        drift_box = tk.Frame(metrics_frame, bg="#ffffff", relief=tk.RIDGE, bd=2)
        drift_box.pack(fill=tk.X, pady=2)

        tk.Label(
            drift_box,
            text="VISCOSITY DRIFT VS BASELINE:",
            font=("Helvetica", 8, "bold"),
            fg="#7f8c8d",
            bg="#ffffff",
        ).pack(anchor=tk.CENTER, pady=(2, 0))

        self.lbl_drift_big = tk.Label(
            drift_box,
            text="0.0%",
            font=("Helvetica", 24, "bold"),
            fg="#27ae60",
            bg="#ffffff",
        )
        self.lbl_drift_big.pack(anchor=tk.CENTER, pady=(0, 2))

        self.lbl_drift_status = tk.Label(
            drift_box,
            text="Status: Baseline Reference (Fresh)",
            font=("Helvetica", 9, "bold"),
            fg="#2c3e50",
            bg="#ffffff",
            wraplength=330,
            justify=tk.CENTER,
        )
        self.lbl_drift_status.pack(anchor=tk.CENTER, pady=(0, 4))

        # Secondary metrics
        self.lbl_nominal_viscosity = tk.Label(
            metrics_frame,
            text="Apparent Viscosity: -- cP (Stefan nominal)",
            font=("Helvetica", 9),
            bg="#eef2f7",
        )
        self.lbl_nominal_viscosity.pack(anchor=tk.W, pady=1)

        self.lbl_rheology_class = tk.Label(
            metrics_frame,
            text="Rheology: Not measured",
            font=("Helvetica", 9),
            bg="#eef2f7",
        )
        self.lbl_rheology_class.pack(anchor=tk.W, pady=1)

        self.lbl_contact_point = tk.Label(
            metrics_frame,
            text="Virtual Datum (z0): -- mm",
            font=("Helvetica", 9),
            bg="#eef2f7",
        )
        self.lbl_contact_point.pack(anchor=tk.W, pady=1)

        self.lbl_r_squared = tk.Label(
            metrics_frame,
            text="Stefan Linearity (R²): --",
            font=("Helvetica", 9),
            bg="#eef2f7",
        )
        self.lbl_r_squared.pack(anchor=tk.W, pady=1)

        self.lbl_status_msg = tk.Label(
            metrics_frame,
            text="Ready. Stage: Standby",
            font=("Helvetica", 8, "italic"),
            fg="#666666",
            bg="#eef2f7",
            wraplength=330,
            justify=tk.LEFT,
        )
        self.lbl_status_msg.pack(anchor=tk.W, pady=(4, 0))

    def _setup_plots(self):
        """Configure Matplotlib figure and dual subplots."""
        self.fig = Figure(figsize=(6.5, 7.5), dpi=100)
        self.fig.patch.set_facecolor("white")

        # Top subplot: F(t) and z(t)
        self.ax_force = self.fig.add_subplot(2, 1, 1)
        self.ax_pos = self.ax_force.twinx()

        self.ax_force.set_title("Hydrodynamic Force & Stage Trajectory", fontsize=10, fontweight="bold")
        self.ax_force.set_xlabel("Time (s)", fontsize=9)
        self.ax_force.set_ylabel("Force F (N)", fontsize=9, color="blue")
        self.ax_pos.set_ylabel("Stage Position z (mm)", fontsize=9, color="purple")
        self.ax_force.grid(True, linestyle="--", alpha=0.5)

        # Bottom subplot: Linearized Stefan Diagnostic F^(-1/3) vs z
        self.ax_linear = self.fig.add_subplot(2, 1, 2)
        self.ax_linear.set_title("Linearized Squeeze Fit: Slope Comparison vs Baseline", fontsize=10, fontweight="bold")
        self.ax_linear.set_xlabel("Stage Position z (mm)", fontsize=9)
        self.ax_linear.set_ylabel("F^(-1/3) (N^(-1/3))", fontsize=9)
        self.ax_linear.grid(True, linestyle="--", alpha=0.5)

        self.fig.tight_layout(pad=2.8)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.right_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _update_baseline_ui(self):
        """Update labels reflecting current daily baseline status."""
        if self.daily_baseline:
            m_0 = self.daily_baseline.get("slope", 0.0)
            t_str = self.daily_baseline.get("timestamp", "--:--")
            mu_nom = self.daily_baseline.get("viscosity_cp", 0.0)
            self.lbl_baseline_status.config(
                text=f"Active Baseline: m0 = {m_0:.1f} N^(-1/3)/m\n(Recorded at {t_str} • ~{mu_nom:.0f} cP nominal)",
                fg="#1b4f72",
            )
        else:
            self.lbl_baseline_status.config(
                text="Active Baseline: None\n(First print/probe will set baseline at 0.0%)",
                fg="#7f8c8d",
            )

    def update_status_text(self, text: str, is_error: bool = False):
        """Update status bar label and call Prince main status callback."""
        color = "#b02a37" if is_error else "#14a44d"
        self.lbl_status_msg.config(text=text, fg=color)
        self.update_status(f"[Viscometer] {text}", error=is_error)

    def abort_motion(self):
        """Request immediate abort of active probe motion."""
        self.abort_requested = True
        self.update_status_text("Aborting motion requested...", is_error=True)
        if self.axis:
            try:
                self.axis.stop()
            except Exception as e:
                print(f"Error stopping axis: {e}")

    # =========================================================================
    # BASELINE MANAGEMENT (RELATIVE TRACKING)
    # =========================================================================
    def set_fresh_resin_baseline(self):
        """Establish the latest measurement (or prompt) as today's fresh baseline."""
        if self.latest_slope is not None and self.latest_slope > 0:
            self._save_baseline_record(
                slope=self.latest_slope,
                intercept=self.latest_intercept,
                r_squared=self.latest_r_squared,
                viscosity_cp=self.latest_viscosity_cp,
            )
            self.lbl_drift_big.config(text="0.0%", fg="#27ae60")
            self.lbl_drift_status.config(text="Status: Fresh Baseline Established (0.0%)", fg="#27ae60")
            self.update_status_text("Fresh resin baseline set to latest measurement (0.0% drift).")
            self._plot_last_run()
        else:
            messagebox.showinfo(
                "Set Baseline",
                "No measurement has been performed yet.\n\n"
                "Please run a Quick Single Probe first with your fresh resin to establish the baseline slope.",
                parent=self.window,
            )

    def _save_baseline_record(self, slope: float, intercept: float, r_squared: float, viscosity_cp: float):
        """Store baseline in memory and to daily JSON config."""
        now_str = datetime.now().strftime("%H:%M:%S")
        self.daily_baseline = {
            "date": date.today().isoformat(),
            "timestamp": now_str,
            "slope": float(slope),
            "intercept": float(intercept),
            "r_squared": float(r_squared),
            "viscosity_cp": float(viscosity_cp),
        }
        save_daily_baseline(self.daily_baseline)
        self._update_baseline_ui()

    def clear_baseline(self):
        """Clear today's baseline so the next run sets a new one."""
        self.daily_baseline = None
        p = Path(__file__).resolve().parent.parent / "config" / "daily_viscosity_baseline.json"
        if p.exists():
            try:
                p.unlink()
            except Exception:
                pass
        self._update_baseline_ui()
        self.lbl_drift_big.config(text="-- %", fg="#7f8c8d")
        self.lbl_drift_status.config(text="Status: Baseline Cleared", fg="#7f8c8d")
        self.update_status_text("Daily baseline cleared.")

    # =========================================================================
    # ACTION 1: PRE-FLUID DRY MEMBRANE TOUCH CHECK
    # =========================================================================
    def run_pre_fluid_check(self):
        """Initiate pre-fluid dry membrane touch sequence in a background thread."""
        if self.is_probing:
            return
        self.is_probing = True
        self.abort_requested = False
        self.btn_abort.config(state=tk.NORMAL)
        self.update_status_text("Starting dry membrane touch check...")

        thread = threading.Thread(target=self._worker_pre_fluid_check, daemon=True)
        thread.start()

    def _worker_pre_fluid_check(self):
        """Worker thread for pre-fluid dry touch routine."""
        try:
            if self.axis is None or self.force_gauge is None:
                # SIMULATION MODE for dry touch
                time.sleep(0.5)
                sim_z = np.linspace(10.2, 9.9, 31)
                sim_F = [0.001 if z_i > 10.0 else 15.0 * (10.0 - z_i) for z_i in sim_z]
                res = self.analyzer.analyze_dry_membrane_touch(sim_z, np.array(sim_F))
                self.window.after(0, self._on_dry_check_complete, res, sim_z, sim_F)
                return

            touch_thresh_n = 0.03
            max_safe_n = 2.0
            slow_speed_mm_s = 0.05  # 50 um/s safe slow touch

            start_pos_mm = self.axis.get_position(Units.LENGTH_MILLIMETRES)
            z_history = []
            f_history = []

            initial_tare = self.force_gauge.get_calibrated_force()
            self.axis.move_velocity(-slow_speed_mm_s, Units.VELOCITY_MILLIMETRES_PER_SECOND)

            while not self.abort_requested:
                curr_z = self.axis.get_position(Units.LENGTH_MILLIMETRES)
                curr_f = self.force_gauge.get_calibrated_force() - initial_tare
                z_history.append(curr_z)
                f_history.append(curr_f)

                if curr_f >= touch_thresh_n:
                    target_depth_z = curr_z - 0.050
                    while curr_z > target_depth_z and not self.abort_requested:
                        curr_z = self.axis.get_position(Units.LENGTH_MILLIMETRES)
                        curr_f = self.force_gauge.get_calibrated_force() - initial_tare
                        z_history.append(curr_z)
                        f_history.append(curr_f)
                        if curr_f >= max_safe_n:
                            break
                        time.sleep(0.02)
                    break

                if abs(start_pos_mm - curr_z) > 3.0:
                    break
                time.sleep(0.02)

            self.axis.stop()
            self.axis.move_absolute(start_pos_mm, Units.LENGTH_MILLIMETRES)

            res = self.analyzer.analyze_dry_membrane_touch(
                np.array(z_history), np.array(f_history), touch_threshold_n=touch_thresh_n
            )
            self.window.after(0, self._on_dry_check_complete, res, z_history, f_history)

        except Exception as e:
            self.window.after(0, self.update_status_text, f"Dry check error: {str(e)}", True)
        finally:
            self.is_probing = False
            self.window.after(0, lambda: self.btn_abort.config(state=tk.DISABLED))

    def _on_dry_check_complete(self, res: dict, z_data, f_data):
        """Handle completion of dry membrane check and update labels."""
        if res.get("touch_detected", False):
            self.dry_datum_z_mm = res["z_dry_touch_mm"]
            self.membrane_stiffness_n_mm = res["membrane_stiffness_n_per_mm"]

            status_desc = "Normal"
            if self.membrane_stiffness_n_mm < 5.0:
                status_desc = "Loose/Sagging (Check tension)"
            elif self.membrane_stiffness_n_mm > 40.0:
                status_desc = "Very Stiff / Glass Backed"

            msg = f"Datum z0 = {self.dry_datum_z_mm:.3f} mm | k = {self.membrane_stiffness_n_mm:.1f} N/mm ({status_desc})"
            self.lbl_dry_status.config(text=msg, fg="#14a44d")
            self.lbl_contact_point.config(text=f"Virtual Datum (z0): {self.dry_datum_z_mm:.3f} mm")
            self.update_status_text(f"Dry touch verified: {msg}")
        else:
            self.lbl_dry_status.config(text="Touch not detected (Check travel)", fg="#b02a37")
            self.update_status_text("Dry touch failed: threshold not reached.", is_error=True)

    # =========================================================================
    # ACTION 2: PROBING & SQUEEZE MEASUREMENT
    # =========================================================================
    def run_single_probe(self):
        """Run single velocity probe at v2 (default 1.0 mm/s)."""
        try:
            v2 = float(self.ent_v2.get())
        except ValueError:
            v2 = 1.0
        self._start_probe_routine([v2])

    def run_multi_speed_probe(self):
        """Run multi-speed probe sequence (v1, v2, v3)."""
        try:
            v1 = float(self.ent_v1.get())
            v2 = float(self.ent_v2.get())
            v3 = float(self.ent_v3.get())
            velocities = [v1, v2, v3]
        except ValueError:
            velocities = [0.5, 1.0, 2.0]
        self._start_probe_routine(velocities)

    def _start_probe_routine(self, velocities: list):
        """Common launcher for single or multi-speed probe routine."""
        if self.is_probing:
            return
        self.is_probing = True
        self.abort_requested = False
        self.btn_abort.config(state=tk.NORMAL)
        self.update_status_text(f"Starting probe at speeds: {velocities} mm/s...")

        thread = threading.Thread(target=self._worker_probe_routine, args=(velocities,), daemon=True)
        thread.start()

    def _worker_probe_routine(self, velocities: list):
        """Worker thread executing squeeze flow approaches."""
        try:
            runs_data = []

            if self.axis is None or self.force_gauge is None:
                # SIMULATION MODE: generate synthetic curves
                time.sleep(0.3)
                z_0_sim = self.dry_datum_z_mm if self.dry_datum_z_mm is not None else 50.0
                
                # If baseline exists, simulate a slight +12% solvent evaporation drift
                sim_visc = 420.0
                if self.daily_baseline:
                    sim_visc = self.daily_baseline.get("viscosity_cp", 420.0) * 1.14

                for v in velocities:
                    z_sim, f_sim = self.analyzer.generate_synthetic_squeeze_curve(
                        viscosity_cp=sim_visc,
                        velocity_mm_s=v,
                        z_start_mm=z_0_sim + 0.500,
                        z_end_mm=z_0_sim + 0.150,
                        z_contact_mm=z_0_sim,
                        num_points=60,
                        noise_std_n=0.005,
                    )
                    runs_data.append({"velocity_mm_s": v, "z_mm": z_sim, "force_n": f_sim})
                    time.sleep(0.2)

                self.window.after(0, self._on_probe_complete, runs_data)
                return

            z_datum = self.dry_datum_z_mm if self.dry_datum_z_mm is not None else 0.0
            z_start = z_datum + 0.800
            z_end = z_datum + 0.150

            for v in velocities:
                if self.abort_requested:
                    break

                self.axis.move_absolute(z_start, Units.LENGTH_MILLIMETRES)
                time.sleep(0.4)

                tare_f = self.force_gauge.get_calibrated_force()
                self.axis.move_velocity(-v, Units.VELOCITY_MILLIMETRES_PER_SECOND)

                z_run = []
                f_run = []
                t_run = []
                t0 = time.time()

                while not self.abort_requested:
                    curr_z = self.axis.get_position(Units.LENGTH_MILLIMETRES)
                    curr_f = self.force_gauge.get_calibrated_force() - tare_f
                    z_run.append(curr_z)
                    f_run.append(curr_f)
                    t_run.append(time.time() - t0)

                    if curr_z <= z_end or curr_f >= 12.0:
                        break
                    time.sleep(0.015)

                self.axis.stop()
                runs_data.append({
                    "velocity_mm_s": v,
                    "z_mm": np.array(z_run),
                    "force_n": np.array(f_run),
                    "time_s": np.array(t_run),
                })

                self.axis.move_absolute(z_start, Units.LENGTH_MILLIMETRES)
                time.sleep(0.4)

            self.window.after(0, self._on_probe_complete, runs_data)

        except Exception as e:
            self.window.after(0, self.update_status_text, f"Probe error: {str(e)}", True)
        finally:
            self.is_probing = False
            self.window.after(0, lambda: self.btn_abort.config(state=tk.DISABLED))

    def _on_probe_complete(self, runs_data: list):
        """Process probe data, calculate relative drift vs baseline, and update display."""
        if not runs_data:
            self.update_status_text("Probe aborted: no data collected.", is_error=True)
            return

        self.last_runs_data = runs_data

        # Multi-speed check
        if len(runs_data) >= 2:
            multi_res = self.analyzer.analyze_multispeed(runs_data)
            flow_n = multi_res.get("flow_index_n", 1.0)
            rheo_class = multi_res.get("classification", "Indeterminate")
            self.lbl_rheology_class.config(text=f"Rheology: {rheo_class} (n={flow_n:.2f})")
        else:
            self.lbl_rheology_class.config(text="Rheology: Single Probe (Assumed Newtonian)")

        # Stefan linear fit on primary run (1.0 mm/s or last)
        primary_run = runs_data[-1]
        stefan_res = self.analyzer.analyze_stefan_linearized(
            primary_run["z_mm"],
            primary_run["force_n"],
            primary_run["velocity_mm_s"],
            z_contact_guess_mm=self.dry_datum_z_mm if self.dry_datum_z_mm else 0.0,
        )

        if not stefan_res.get("valid", False):
            self.lbl_drift_big.config(text="Fit Error", fg="#b02a37")
            self.update_status_text(f"Stefan fit warning: {stefan_res.get('error', 'Check data')}", is_error=True)
            return

        slope_k = stefan_res["slope"]
        intercept_k = stefan_res["intercept"]
        visc_cp = stefan_res["viscosity_cp"]
        r2 = stefan_res["r_squared"]

        self.latest_slope = slope_k
        self.latest_intercept = intercept_k
        self.latest_viscosity_cp = visc_cp
        self.latest_r_squared = r2

        # Relative Drift Calculation
        if self.daily_baseline is None:
            # Auto-establish as first baseline of the day
            self._save_baseline_record(slope=slope_k, intercept=intercept_k, r_squared=r2, viscosity_cp=visc_cp)
            drift_pct = 0.0
            status_text = "Status: Baseline Reference Established (0.0% Drift)"
            drift_color = "#27ae60"
        else:
            m_0 = self.daily_baseline["slope"]
            drift_calc = self.analyzer.compute_relative_viscosity_drift(m_0, slope_k)
            drift_pct = drift_calc["drift_percent"]
            status_text = f"Status: {drift_calc['status']}"
            
            # Color coding
            if drift_calc["alert_level"] == "CRITICAL":
                drift_color = "#c0392b"  # Red
            elif drift_calc["alert_level"] == "WARNING":
                drift_color = "#e67e22"  # Orange
            else:
                drift_color = "#27ae60"  # Green

        self.latest_drift_pct = drift_pct

        # Update big primary readout
        self.lbl_drift_big.config(text=f"{drift_pct:+.1f}%", fg=drift_color)
        self.lbl_drift_status.config(text=status_text, fg=drift_color)

        # Update secondary readouts
        self.lbl_nominal_viscosity.config(text=f"Apparent Viscosity: ~{visc_cp:.1f} cP (Stefan nominal)")
        self.lbl_contact_point.config(text=f"Virtual Datum (z0): {stefan_res['z_contact_mm']:.3f} mm")
        self.lbl_r_squared.config(text=f"Stefan Linearity (R²): {r2:.4f}")

        log_msg = f"Viscosity Drift: {drift_pct:+.1f}% vs baseline | Nominal: ~{visc_cp:.0f} cP | R²: {r2:.3f}"
        self.update_status_text(log_msg)

        # Plot curves with baseline comparison overlay
        self._plot_results(runs_data, stefan_res)

    def _plot_last_run(self):
        """Re-plot last run data if available."""
        if hasattr(self, 'last_runs_data'):
            primary = self.last_runs_data[-1]
            stefan = self.analyzer.analyze_stefan_linearized(
                primary["z_mm"], primary["force_n"], primary["velocity_mm_s"]
            )
            self._plot_results(self.last_runs_data, stefan)

    def _plot_results(self, runs_data: list, stefan_res: dict):
        """Render updated hydrodynamic force and linearized Stefan comparison plot."""
        self.ax_force.clear()
        self.ax_pos.clear()
        self.ax_linear.clear()

        # Top plot: Force & Position vs Time
        colors = ["#3b71ca", "#14a44d", "#e4a11b", "#dc4c64"]
        for i, run in enumerate(runs_data):
            v = run["velocity_mm_s"]
            z = run["z_mm"]
            F = run["force_n"]
            t = run.get("time_s", np.linspace(0, len(z) * 0.02, len(z)))
            col = colors[i % len(colors)]

            self.ax_force.plot(t, F, color=col, label=f"F (v={v}mm/s)", linewidth=1.8)
            if i == len(runs_data) - 1:
                self.ax_pos.plot(t, z, color="purple", linestyle=":", label="Position z (mm)")

        self.ax_force.set_title("Hydrodynamic Squeeze Force vs Time", fontsize=10, fontweight="bold")
        self.ax_force.set_xlabel("Time (s)", fontsize=9)
        self.ax_force.set_ylabel("Force F (N)", fontsize=9, color="blue")
        self.ax_pos.set_ylabel("Stage Position z (mm)", fontsize=9, color="purple")
        self.ax_force.legend(loc="upper left", fontsize=8)
        self.ax_pos.legend(loc="upper right", fontsize=8)
        self.ax_force.grid(True, linestyle="--", alpha=0.5)

        # Bottom plot: F^(-1/3) vs z with baseline comparison
        if stefan_res.get("valid", False) and "z_filtered_mm" in stefan_res:
            z_fit = stefan_res["z_filtered_mm"]
            y_fit = stefan_res["y_filtered"]
            m_k = stefan_res["slope"]
            c_k = stefan_res["intercept"]
            z_0 = stefan_res["z_contact_mm"]

            # Scatter current points
            self.ax_linear.scatter(z_fit, y_fit, color="#3b71ca", s=18, label="Current F^(-1/3) Data", zorder=3)

            # Fit line for current run
            z_line = np.linspace(z_0, np.max(z_fit), 100)
            y_curr_line = m_k * (z_line * 1e-3) + c_k
            self.ax_linear.plot(
                z_line, y_curr_line, color="#e74c3c", linestyle="-", linewidth=2.0,
                label=f"Current: Drift {self.latest_drift_pct:+.1f}% (mk={m_k:.1f})"
            )

            # Overlay baseline slope (aligned at same virtual contact) if baseline exists
            if self.daily_baseline:
                m_0 = self.daily_baseline["slope"]
                c_0_aligned = -m_0 * (z_0 * 1e-3)  # Aligned at current z_0 to show slope difference
                y_base_line = m_0 * (z_line * 1e-3) + c_0_aligned
                self.ax_linear.plot(
                    z_line, y_base_line, color="#27ae60", linestyle="--", linewidth=1.8,
                    label=f"Morning Baseline (0.0% reference, m0={m_0:.1f})"
                )

            self.ax_linear.axvline(x=z_0, color="gray", linestyle=":", label=f"Datum z0 = {z_0:.3f}mm")

        self.ax_linear.set_title("Linearized Squeeze Fit: Slope Comparison vs Baseline (m0)", fontsize=10, fontweight="bold")
        self.ax_linear.set_xlabel("Stage Position z (mm)", fontsize=9)
        self.ax_linear.set_ylabel("F^(-1/3) (N^(-1/3))", fontsize=9)
        self.ax_linear.legend(loc="upper left", fontsize=8)
        self.ax_linear.grid(True, linestyle="--", alpha=0.5)

        self.fig.tight_layout(pad=2.5)
        self.canvas.draw()
