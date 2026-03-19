"""
Standalone pipeline integration validator for manuscript FlatPDMS_19p63 dataset.

This script validates:
1) Folder-level CSV discovery and layer segmentation via RawDataProcessor.
2) Modern-mode calculator execution with explicit contact area.
3) Partitioned energy outputs and sign health checks.
4) Production plot generation via AnalysisPlotter.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd


CONTACT_AREA_MM2 = 19.63
CONTACT_AREA_M2 = 1.963e-5


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _resolve_data_dir(root: Path) -> Path:
    manuscript_root = root / "post-processing" / "manuscript_data"
    explicit_candidates = [
        manuscript_root / "flatPDMS_19p63",
        manuscript_root / "FlatPDMS_19p63",
    ]
    for candidate in explicit_candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate

    # Case-insensitive fallback
    if manuscript_root.exists():
        for child in manuscript_root.iterdir():
            if child.is_dir() and child.name.lower() == "flatpdms_19p63":
                return child

    raise FileNotFoundError("Could not locate manuscript folder for FlatPDMS_19p63")


def _load_analysis_plotter_class(root: Path):
    plotter_file = root / "post-processing" / "analysis_plotter.py"
    if not plotter_file.exists():
        raise FileNotFoundError(f"Missing production plotter: {plotter_file}")

    spec = importlib.util.spec_from_file_location("analysis_plotter_module", plotter_file)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module spec for {plotter_file}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, "AnalysisPlotter"):
        raise RuntimeError("analysis_plotter module does not expose AnalysisPlotter")

    return module.AnalysisPlotter


def _find_candidate_csvs(data_dir: Path) -> List[Path]:
    csvs = sorted(data_dir.glob("autolog*.csv"))
    if csvs:
        return csvs

    # Fallback: any csv excluding metadata summary files
    excluded = {"automated_work_of_adhesion.csv", "experimental_conditions.csv"}
    csvs = [p for p in sorted(data_dir.glob("*.csv")) if p.name not in excluded]
    return csvs


def _build_modern_calculator():
    from support_modules.adhesion_metrics_calculator import AdhesionMetricsCalculator

    return AdhesionMetricsCalculator(
        prop_end_mode="second_derivative_zero_crossing",
        baseline_mode="prop_end_point",
    )


def _run_segmentation_on_folder(data_dir: Path):
    from support_modules.RawData_Processor import RawDataProcessor

    csvs = _find_candidate_csvs(data_dir)
    if not csvs:
        raise FileNotFoundError(f"No candidate CSVs found in {data_dir}")

    for csv_path in csvs:
        calculator = _build_modern_calculator()
        processor = RawDataProcessor(calculator)

        print(f"\n[SEGMENTATION] Trying file: {csv_path.name}")
        layers = processor.process_csv(str(csv_path))

        if not layers:
            print("  -> No valid layers in this file")
            continue

        # First valid layer = has phases and non-empty lifting/retraction windows
        for layer in layers:
            phases = layer.get("phases", {})
            if not phases:
                continue

            lifting = phases.get("lifting")
            retraction = phases.get("retraction")
            if not lifting or not retraction:
                continue

            if lifting[1] <= lifting[0] or retraction[1] <= retraction[0]:
                continue

            return csv_path, layers, layer

    raise RuntimeError("No valid segmented layers found across manuscript folder")


def _compute_first_layer_metrics(
    csv_path: Path,
    first_layer: Dict,
    contact_area_m2: float,
) -> Tuple[Dict, Dict]:
    """
    Recompute first-layer metrics with explicit contact area.

    Returns:
        metrics, debug_context
    """
    calculator = _build_modern_calculator()

    df = pd.read_csv(csv_path)
    time_data = df["Elapsed Time (s)"].to_numpy()
    force_data = df["Force (N)"].to_numpy()
    position_data = df["Position (mm)"].to_numpy()

    lifting_start, lifting_end = first_layer["phases"]["lifting"]
    retraction_start, retraction_end = first_layer["phases"]["retraction"]

    lifting_time = time_data[lifting_start:lifting_end + 1]
    lifting_time_relative = lifting_time - lifting_time[0]
    lifting_pos = position_data[lifting_start:lifting_end + 1]
    lifting_force = force_data[lifting_start:lifting_end + 1]

    retraction_force = force_data[retraction_start:retraction_end + 1]

    metrics = calculator.calculate_from_arrays(
        time_data=lifting_time_relative,
        position_data=lifting_pos,
        force_data=lifting_force,
        layer_number=first_layer.get("number"),
        retraction_force_data=retraction_force,
        retraction_start_idx=retraction_start,
        contact_area=contact_area_m2,
    )

    smoothed_lifting = calculator._apply_smoothing(lifting_force)

    peak_idx_local = int(np.argmin(np.abs(lifting_time_relative - metrics["peak_force_time"])))
    prop_end_idx_local = int(np.argmin(np.abs(lifting_time_relative - metrics["propagation_end_time"])))

    debug_context = {
        "time_data": time_data,
        "force_data": force_data,
        "smoothed_lifting": smoothed_lifting,
        "lifting_force": lifting_force,
        "lifting_start": lifting_start,
        "peak_idx_local": peak_idx_local,
        "prop_end_idx_local": prop_end_idx_local,
        "peak_idx_global": lifting_start + peak_idx_local,
        "prop_end_idx_global": lifting_start + prop_end_idx_local,
    }

    return metrics, debug_context


def _enforce_positive_energy(metrics: Dict) -> Dict:
    """
    Ensure energy-like values are positive magnitudes for scientific reporting.
    """
    adjusted = dict(metrics)

    work_total = float(adjusted.get("work_of_adhesion_total_J", 0.0))
    g_value = float(adjusted.get("energy_release_rate_G_J_per_m2", 0.0))
    area = float(adjusted.get("contact_area_m2", 0.0))
    initiation = float(adjusted.get("dissipated_energy_initiation_J", 0.0))

    propagation = g_value * area if area > 0 else 0.0

    sign_issue = any(v < 0 for v in [work_total, g_value, initiation, propagation])
    if sign_issue:
        print("\n[SIGN CHECK] Negative energy detected. Converting to positive magnitudes for Work Done reporting.")

    adjusted["work_of_adhesion_total_J"] = abs(work_total)
    adjusted["dissipated_energy_initiation_J"] = abs(initiation)

    propagation_abs = abs(propagation)
    if area > 0:
        adjusted["energy_release_rate_G_J_per_m2"] = propagation_abs / area
    else:
        adjusted["energy_release_rate_G_J_per_m2"] = 0.0

    adjusted["_propagation_energy_J"] = propagation_abs
    adjusted["_sign_corrected"] = sign_issue

    return adjusted


def _generate_production_plot(root: Path, csv_path: Path, layers: List[Dict]) -> Path:
    AnalysisPlotter = _load_analysis_plotter_class(root)

    df = pd.read_csv(csv_path)
    time_data = df["Elapsed Time (s)"].to_numpy()
    force_data = df["Force (N)"].to_numpy()

    # Use production calculator smoothing for consistency with processing path.
    calculator = _build_modern_calculator()
    smoothed_force = calculator._apply_smoothing(force_data)

    output_path = root / "debug" / "validation_plot_flatPDMS_19p63.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    title = f"Pipeline Validation: {csv_path.name}"
    plotter = AnalysisPlotter(figure_size=(16, 12), dpi=120)
    plotter.create_plot(
        time_data=time_data,
        force_data=force_data,
        smoothed_force=smoothed_force,
        layers=layers,
        title=title,
        save_path=str(output_path),
    )

    return output_path


def main() -> int:
    root = _repo_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    print("=" * 88)
    print("PIPELINE INTEGRATION SCIENTIFIC HEALTH CHECK")
    print("=" * 88)

    data_dir = _resolve_data_dir(root)
    print(f"Data folder: {data_dir}")
    print(f"Known contact area: {CONTACT_AREA_MM2:.2f} mm^2 ({CONTACT_AREA_M2:.6e} m^2)")

    csv_path, layers, first_layer = _run_segmentation_on_folder(data_dir)
    print(f"\n[SELECTION] First valid segmented layer from: {csv_path.name}")
    print(f"Layer number: {first_layer.get('number')}")

    raw_metrics, ctx = _compute_first_layer_metrics(csv_path, first_layer, CONTACT_AREA_M2)
    metrics = _enforce_positive_energy(raw_metrics)

    peak_idx_g = ctx["peak_idx_global"]
    prop_idx_g = ctx["prop_end_idx_global"]
    peak_idx_l = ctx["peak_idx_local"]
    prop_idx_l = ctx["prop_end_idx_local"]

    lifting_force = ctx["lifting_force"]
    smoothed_lifting = ctx["smoothed_lifting"]

    print("\n[INDEX DEBUG]")
    print(f"peak_idx (local/global): {peak_idx_l} / {peak_idx_g}")
    print(f"prop_end_idx (local/global): {prop_idx_l} / {prop_idx_g}")
    print(f"Force at peak (raw/smoothed): {lifting_force[peak_idx_l]:.6f} / {smoothed_lifting[peak_idx_l]:.6f} N")
    print(f"Force at prop_end (raw/smoothed): {lifting_force[prop_idx_l]:.6f} / {smoothed_lifting[prop_idx_l]:.6f} N")

    print("\n[PARTITIONED ENERGIES]")
    print(f"Initiation energy (J): {metrics['dissipated_energy_initiation_J']:.9e}")
    print(f"Propagation energy (J): {metrics['_propagation_energy_J']:.9e}")
    print(f"Total work of adhesion (J): {metrics['work_of_adhesion_total_J']:.9e}")
    print(f"Energy release rate G (J/m^2): {metrics['energy_release_rate_G_J_per_m2']:.9e}")
    print(f"Contact area used (m^2): {metrics['contact_area_m2']:.9e}")

    closure_error = abs(
        metrics["work_of_adhesion_total_J"]
        - (metrics["dissipated_energy_initiation_J"] + metrics["_propagation_energy_J"])
    )

    print("\n[SCIENTIFIC HEALTH SUMMARY]")
    print(f"Sign corrected: {'YES' if metrics['_sign_corrected'] else 'NO'}")
    print(f"Energy partition closure |W - (Init + Prop)|: {closure_error:.9e} J")

    plot_path = _generate_production_plot(root, csv_path, layers)
    print(f"\n[PLOT] Saved production plot to: {plot_path}")

    print("\nValidation complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
