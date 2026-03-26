"""
Manuscript Master Batch Processor
=================================

Batch-process all autolog CSV files under post-processing/manuscript_data,
using RawDataProcessor for segmentation and AdhesionMetricsCalculator
(Modern Mode) for metric computation.

Output:
- post-processing/MANUSCRIPT_MASTER_RESULTS_2026.csv
"""

from __future__ import annotations

import argparse
from datetime import datetime
import logging
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from support_modules.RawData_Processor import RawDataProcessor
from support_modules.adhesion_metrics_calculator import AdhesionMetricsCalculator
from analysis_plotter import AnalysisPlotter


DATA_ROOT = Path(__file__).resolve().parent / "manuscript_data"
OUTPUT_CSV = Path(__file__).resolve().parent / "MANUSCRIPT_MASTER_RESULTS_2026.csv"
OUTPUT_XLSX = Path(__file__).resolve().parent / "MANUSCRIPT_MASTER_RESULTS_2026.xlsx"
PLOT_RUNS_ROOT = Path(__file__).resolve().parent / "manuscript_plot_runs"
LAYER_LEGIT_FORCE_THRESHOLD_N = 0.1


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )


def extract_area_mm2(folder_name: str) -> Tuple[float, Optional[str]]:
    """
    Parse area from folder names like FlatPDMS_19p63 or FlatPDMS_19.63.

    Returns:
        (area_mm2, warning_message)
    """
    # Prefer trailing token after underscore for patterns like *_19p63.
    match = re.search(r"_([0-9]+(?:[p\.][0-9]+)?)$", folder_name)
    if match:
        area_token = match.group(1).replace("p", ".")
        try:
            area = float(area_token)
            if area > 0:
                return area, None
        except ValueError:
            pass

    # Fallback: any numeric token in folder name.
    generic_match = re.search(r"([0-9]+(?:[p\.][0-9]+)?)", folder_name)
    if generic_match:
        area_token = generic_match.group(1).replace("p", ".")
        try:
            area = float(area_token)
            if area > 0:
                return area, None
        except ValueError:
            pass

    warning = (
        f"No valid area found in folder name '{folder_name}'. "
        "Defaulting Area_mm2 to 1.0"
    )
    return 1.0, warning


def discover_autolog_files(data_root: Path) -> List[Path]:
    """
    Discover candidate autolog files from manuscript_data.

    Excludes previously generated layer-metrics outputs so only raw autolog
    inputs are processed.
    """
    candidates = sorted(data_root.rglob("autolog_*.csv"))
    filtered: List[Path] = []

    for csv_path in candidates:
        name = csv_path.name.lower()
        as_posix = csv_path.as_posix().lower()

        if name.endswith("_layer_metrics.csv"):
            continue
        if "manuscript_analysis_output" in as_posix:
            continue
        if "single_file_debug_output" in as_posix:
            continue

        filtered.append(csv_path)

    return filtered


def _sanitize_stem(name: str) -> str:
    """Create filesystem-safe filename stem for plot output."""
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name)


def save_autolog_plot(
    csv_path: Path,
    folder_label: str,
    area_mm2: float,
    time_data: np.ndarray,
    force_data: np.ndarray,
    smoothed_force: np.ndarray,
    layer_plot_points: List[Dict[str, Any]],
    plot_output_dir: Path,
    plotter: AnalysisPlotter,
) -> Path:
    """Save one analysis plot by delegating rendering to AnalysisPlotter."""
    plot_output_dir.mkdir(parents=True, exist_ok=True)

    layers = sorted(layer_plot_points, key=lambda x: int(x["layer_number"]))
    plotter_layers: List[Dict[str, Any]] = []
    for layer in layers:
        plotter_layers.append(
            {
                "number": int(layer["layer_number"]),
                "color": str(layer["color"]),
                "start_idx": int(layer["lifting_start_idx"]),
                "end_idx": int(layer["lifting_end_idx"]),
                "peak_idx": int(layer["peak_idx"]),
                "prop_end_idx": int(layer["prop_end_idx"]),
                "peak_time": float(layer["peak_time"]),
                "peak_force": float(layer.get("peak_force_absolute", layer["peak_force"])),
                "peak_force_corrected": float(layer.get("peak_force_corrected", layer["peak_force"])),
                "pre_init_time": float(layer["pre_init_time"]),
                "prop_end_time": float(layer["prop_end_time"]),
                "baseline": float(layer["baseline"]),
                "pre_init_duration": float(layer["pre_init_duration"]),
                "prop_duration": float(layer["prop_duration"]),
                "incomplete_peeling": bool(layer.get("incomplete_peeling", False)),
                "analysis_included": bool(layer.get("analysis_included", True)),
            }
        )

    min_layer = min(item["number"] for item in plotter_layers)
    max_layer = max(item["number"] for item in plotter_layers)
    title = f"{folder_label} - Layers {min_layer} -> {max_layer}\nAverage Area: {area_mm2:.2f} mm^2"

    # Keep naming aligned with universal/style-guide convention.
    plot_name = f"{_sanitize_stem(csv_path.stem)}_analysis.png"
    plot_path = plot_output_dir / plot_name
    plotter.create_plot(
        time_data=time_data,
        force_data=force_data,
        smoothed_force=smoothed_force,
        layers=plotter_layers,
        title=title,
        save_path=plot_path,
    )
    return plot_path


def _resolve_folder_label(csv_path: Path, data_root: Path) -> str:
    """Return dataset folder label for output table."""
    rel_parent = csv_path.parent.relative_to(data_root)
    if len(rel_parent.parts) == 0:
        return csv_path.parent.name
    return rel_parent.parts[0]


def _get_layer_boundaries(
    processor: RawDataProcessor,
    df: pd.DataFrame,
    time_data: np.ndarray,
    position_data: np.ndarray,
    force_data: np.ndarray,
) -> List[Dict]:
    """Use RawDataProcessor segmentation logic with phase-aware preference."""
    if "Phase" in df.columns:
        logging.info("Phase column found: using phase-aware boundary detection")
        phase_data = df["Phase"].to_numpy()
        boundaries = processor._detect_boundaries_from_phases(
            time_data, position_data, force_data, phase_data
        )
        if len(boundaries) == 0:
            logging.warning("Phase-aware detection found no layers; falling back to adaptive")
            boundaries = processor._detect_boundaries_adaptive(
                time_data, position_data, force_data
            )
        return boundaries

    logging.info("Phase column not found: using adaptive boundary detection")
    return processor._detect_boundaries_adaptive(time_data, position_data, force_data)


def process_autolog_file(
    csv_path: Path,
    data_root: Path,
    processor: RawDataProcessor,
    calculator: AdhesionMetricsCalculator,
    plotter: AnalysisPlotter,
    plot_root_dir: Optional[Path] = None,
) -> List[Dict]:
    """Process a single autolog CSV into row records for the master output."""
    folder_label = _resolve_folder_label(csv_path, data_root)
    area_mm2, area_warning = extract_area_mm2(folder_label)
    if area_warning:
        logging.warning("%s | file=%s", area_warning, csv_path.name)

    contact_area_m2 = area_mm2 * 1e-6

    df = processor._load_and_prepare_data(str(csv_path))
    if df is None:
        logging.error("Failed to load file: %s", csv_path)
        return []

    required_columns = ["Elapsed Time (s)", "Force (N)", "Position (mm)"]
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        logging.warning("Skipping %s due to missing columns: %s", csv_path.name, missing)
        return []

    time_data = df["Elapsed Time (s)"].to_numpy()
    force_data = df["Force (N)"].to_numpy()
    position_data = df["Position (mm)"].to_numpy()

    if len(time_data) < 10:
        logging.warning("Skipping %s: insufficient points (%d)", csv_path.name, len(time_data))
        return []

    boundaries = _get_layer_boundaries(
        processor=processor,
        df=df,
        time_data=time_data,
        position_data=position_data,
        force_data=force_data,
    )
    if len(boundaries) == 0:
        logging.warning("No layer boundaries found in %s", csv_path.name)
        return []

    layer_numbers = processor._extract_layer_numbers_from_filename(str(csv_path))
    max_layers = min(len(layer_numbers), len(boundaries))
    smoothed_force = calculator._apply_smoothing(force_data)

    rows: List[Dict] = []
    incomplete_layers = 0
    layer_plot_points: List[Dict[str, Any]] = []
    color_cycle = ["red", "blue", "green", "orange", "purple", "brown"]
    for i in range(max_layers):
        layer_num = layer_numbers[i]
        boundary = boundaries[i]

        lifting_start, lifting_end = boundary["lifting"]
        retraction_start, retraction_end = boundary["retraction"]

        lifting_time = time_data[lifting_start : lifting_end + 1]
        lifting_pos = position_data[lifting_start : lifting_end + 1]
        lifting_force = force_data[lifting_start : lifting_end + 1]
        retraction_force = force_data[retraction_start : retraction_end + 1]

        if len(lifting_time) < 10:
            logging.warning(
                "Skipping layer %s in %s: lifting segment too short (%d)",
                layer_num,
                csv_path.name,
                len(lifting_time),
            )
            continue

        lifting_time_relative = lifting_time - lifting_time[0]

        try:
            metrics = calculator.calculate_from_arrays(
                time_data=lifting_time_relative,
                position_data=lifting_pos,
                force_data=lifting_force,
                layer_number=layer_num,
                lifting_start_idx=0,
                retraction_force_data=retraction_force,
                retraction_start_idx=retraction_start,
                contact_area=contact_area_m2,
            )
        except Exception as exc:
            logging.exception(
                "Metric computation failed for %s layer %s: %s",
                csv_path.name,
                layer_num,
                exc,
            )
            continue

        peak_time_relative = float(metrics.get("peak_force_time", 0.0))
        pre_time_relative = float(metrics.get("pre_initiation_time", 0.0))
        prop_time_relative = float(metrics.get("propagation_end_time", 0.0))

        peak_idx_in_segment = int(np.argmin(np.abs(lifting_time_relative - peak_time_relative)))
        peak_idx_global = lifting_start + peak_idx_in_segment

        pre_abs_time = lifting_time[0] + pre_time_relative
        prop_abs_time = lifting_time[0] + prop_time_relative
        pre_idx_global = int(np.argmin(np.abs(time_data - pre_abs_time)))
        prop_idx_global = int(np.argmin(np.abs(time_data - prop_abs_time)))

        pre_idx_global = int(np.clip(pre_idx_global, 0, len(time_data) - 1))
        peak_idx_global = int(np.clip(peak_idx_global, 0, len(time_data) - 1))
        prop_idx_global = int(np.clip(prop_idx_global, 0, len(time_data) - 1))

        baseline_force = float(metrics.get("baseline_force", 0.0))
        pre_init_force = float(metrics.get("pre_initiation_force", 0.0))
        is_legit_layer = (
            abs(baseline_force) < LAYER_LEGIT_FORCE_THRESHOLD_N
            and abs(pre_init_force) < LAYER_LEGIT_FORCE_THRESHOLD_N
        )
        is_incomplete_peeling = not is_legit_layer

        if is_incomplete_peeling:
            incomplete_layers += 1
            logging.warning(
                "Flagging incomplete peeling layer %s in %s: |baseline|=%.4f N, |pre-init force|=%.4f N (threshold=%.3f N)",
                layer_num,
                csv_path.name,
                abs(baseline_force),
                abs(pre_init_force),
                LAYER_LEGIT_FORCE_THRESHOLD_N,
            )

        layer_plot_points.append(
            {
                "lifting_start_idx": lifting_start,
                "lifting_end_idx": lifting_end,
                "peak_idx": peak_idx_global,
                "pre_init_idx": pre_idx_global,
                "prop_end_idx": prop_idx_global,
                "pre_init_time": float(time_data[pre_idx_global]),
                "peak_time": float(time_data[peak_idx_global]),
                "prop_end_time": float(time_data[prop_idx_global]),
                "baseline": baseline_force,
                "pre_init_duration": float(metrics.get("pre_initiation_duration", 0.0)),
                "prop_duration": float(metrics.get("propagation_duration", 0.0)),
                "peak_force": float(metrics.get("peak_force", 0.0)),
                "peak_force_corrected": float(metrics.get("peak_force", 0.0)),
                "peak_force_absolute": float(metrics.get("peak_force_absolute", metrics.get("peak_force", 0.0))),
                "layer_number": int(layer_num),
                "color": color_cycle[i % len(color_cycle)] if is_legit_layer else "dimgray",
                "incomplete_peeling": bool(is_incomplete_peeling),
                "analysis_included": bool(is_legit_layer),
            }
        )

        rows.append(
            {
                "Data_Section": "ANALYSIS" if is_legit_layer else "INCOMPLETE_PEELING",
                "Analysis_Included": bool(is_legit_layer),
                "Peeling_Status": "complete" if is_legit_layer else "incomplete_peeling",
                "Folder": folder_label,
                "Filename": csv_path.name,
                "Layer": layer_num,
                "Area_mm2": float(area_mm2),
                "Baseline_Force_N": baseline_force,
                "Pre_Initiation_Force_N": pre_init_force,
                "Peak_Force_N": float(metrics.get("peak_force", 0.0)),
                "Peak_Force_Absolute_N": float(metrics.get("peak_force_absolute", metrics.get("peak_force", 0.0))),
                "Peak_Force_Corrected_N": float(metrics.get("peak_force", 0.0)),
                "Propagation_Time_s": float(metrics.get("propagation_duration", 0.0)),
                "Total_Peel_Distance_mm": abs(float(metrics.get("total_peel_distance", 0.0))),
                "Work_Total_J": float(metrics.get("work_of_adhesion_total_J", 0.0)),
                "G_Energy_Release_Rate_Jm2": float(
                    metrics.get("energy_release_rate_G_J_per_m2", 0.0)
                ),
                "Dissipated_Energy_J": float(
                    metrics.get("dissipated_energy_initiation_J", 0.0)
                ),
            }
        )

    if plot_root_dir is not None and len(layer_plot_points) > 0:
        # Preserve source folder hierarchy under the timestamped run directory.
        relative_parent = csv_path.parent.relative_to(data_root)
        run_stamp = plot_root_dir.name.replace("run_", "")
        per_file_output_dir = plot_root_dir / relative_parent / "plots" / f"plots_{run_stamp}"
        plot_path = save_autolog_plot(
            csv_path=csv_path,
            folder_label=folder_label,
            area_mm2=area_mm2,
            time_data=time_data,
            force_data=force_data,
            smoothed_force=smoothed_force,
            layer_plot_points=layer_plot_points,
            plot_output_dir=per_file_output_dir,
            plotter=plotter,
        )
        logging.info("Saved plot: %s", plot_path)

    if incomplete_layers > 0:
        logging.info(
            "Flagged %d incomplete-peeling layers in %s using legitimacy threshold %.3f N",
            incomplete_layers,
            csv_path.name,
            LAYER_LEGIT_FORCE_THRESHOLD_N,
        )

    return rows


def run_master_batch(data_root: Path, output_csv: Path, save_plots: bool = False) -> pd.DataFrame:
    """Run the full manuscript batch processing workflow."""
    calculator = AdhesionMetricsCalculator(
        median_kernel=5,
        savgol_window=9,
        savgol_order=2,
        baseline_threshold_factor=0.002,
        min_peak_height=0.01,
        min_peak_distance=50,
        prop_end_mode="two_step_max_second_derivative",
    )
    processor = RawDataProcessor(calculator)
    plotter = AnalysisPlotter(figure_size=(16, 12), dpi=300)

    autolog_files = discover_autolog_files(data_root)
    logging.info("Discovered %d autolog input files under %s", len(autolog_files), data_root)

    plot_root_dir: Optional[Path] = None
    if save_plots:
        run_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        plot_root_dir = PLOT_RUNS_ROOT / f"run_{run_stamp}"
        plot_root_dir.mkdir(parents=True, exist_ok=True)
        logging.info("Per-file plots enabled. Output directory: %s", plot_root_dir)

    master_rows: List[Dict] = []

    for index, csv_path in enumerate(autolog_files, start=1):
        logging.info("[%d/%d] Processing %s", index, len(autolog_files), csv_path)
        rows = process_autolog_file(
            csv_path=csv_path,
            data_root=data_root,
            processor=processor,
            calculator=calculator,
            plotter=plotter,
            plot_root_dir=plot_root_dir,
        )
        master_rows.extend(rows)
        logging.info("[%d/%d] Added %d rows from %s", index, len(autolog_files), len(rows), csv_path.name)

    result_df = pd.DataFrame(
        master_rows,
        columns=[
            "Data_Section",
            "Analysis_Included",
            "Peeling_Status",
            "Folder",
            "Filename",
            "Layer",
            "Area_mm2",
            "Baseline_Force_N",
            "Pre_Initiation_Force_N",
            "Peak_Force_N",
            "Peak_Force_Absolute_N",
            "Peak_Force_Corrected_N",
            "Propagation_Time_s",
            "Total_Peel_Distance_mm",
            "Work_Total_J",
            "G_Energy_Release_Rate_Jm2",
            "Dissipated_Energy_J",
        ],
    )

    if not result_df.empty:
        # Keep complete-analysis rows first and incomplete-peeling rows in a separate section below.
        complete_df = result_df[result_df["Analysis_Included"] == True].sort_values(
            by=["Folder", "Filename", "Layer"]
        )
        incomplete_df = result_df[result_df["Analysis_Included"] == False].sort_values(
            by=["Folder", "Filename", "Layer"]
        )
        result_df = pd.concat([complete_df, incomplete_df], ignore_index=True)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    result_df.to_csv(output_csv, index=False)
    logging.info("Saved consolidated results to %s", output_csv)
    logging.info("Total output rows: %d", len(result_df))

    # CSV has no tabs/sheets; emit workbook with detailed + folder averages sheets.
    summary_df = pd.DataFrame(
        columns=[
            "Folder",
            "Included_Layer_Count",
            "Avg_G_Energy_Release_Rate_Jm2",
            "Std_G_Energy_Release_Rate_Jm2",
            "Avg_Propagation_Time_s",
            "Std_Propagation_Time_s",
            "Avg_Total_Peel_Distance_mm",
            "Std_Total_Peel_Distance_mm",
        ]
    )

    if not result_df.empty:
        analysis_df = result_df[result_df["Analysis_Included"] == True].copy()
        if not analysis_df.empty:
            summary_df = (
                analysis_df.groupby("Folder", dropna=False)
                .agg(
                    Included_Layer_Count=("Layer", "count"),
                    Avg_G_Energy_Release_Rate_Jm2=("G_Energy_Release_Rate_Jm2", "mean"),
                    Std_G_Energy_Release_Rate_Jm2=("G_Energy_Release_Rate_Jm2", "std"),
                    Avg_Propagation_Time_s=("Propagation_Time_s", "mean"),
                    Std_Propagation_Time_s=("Propagation_Time_s", "std"),
                    Avg_Total_Peel_Distance_mm=("Total_Peel_Distance_mm", "mean"),
                    Std_Total_Peel_Distance_mm=("Total_Peel_Distance_mm", "std"),
                )
                .reset_index()
                .sort_values("Folder")
                .reset_index(drop=True)
            )

    try:
        with pd.ExcelWriter(OUTPUT_XLSX) as writer:
            result_df.to_excel(writer, sheet_name="Detailed", index=False)
            summary_df.to_excel(writer, sheet_name="Folder_Averages", index=False)
        logging.info("Saved workbook with detailed + averages sheets to %s", OUTPUT_XLSX)
    except Exception as exc:
        fallback_summary_csv = output_csv.with_name(output_csv.stem + "_FOLDER_AVERAGES.csv")
        summary_df.to_csv(fallback_summary_csv, index=False)
        logging.warning(
            "Failed to write workbook (%s). Wrote summary fallback CSV to %s",
            exc,
            fallback_summary_csv,
        )

    if not result_df.empty:
        included_count = int((result_df["Analysis_Included"] == True).sum())
        incomplete_count = int((result_df["Analysis_Included"] == False).sum())
        logging.info("Analysis rows: %d | Incomplete peeling rows: %d", included_count, incomplete_count)

    return result_df


def main(argv: Optional[Sequence[str]] = None) -> int:
    configure_logging()

    parser = argparse.ArgumentParser(description="Run manuscript master batch processing.")
    parser.add_argument(
        "--save-plots",
        action="store_true",
        help="Save one analysis plot per autolog CSV into a timestamped run folder.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    data_root = DATA_ROOT
    output_csv = OUTPUT_CSV

    if not data_root.exists():
        logging.error("Data root does not exist: %s", data_root)
        return 1

    run_master_batch(data_root=data_root, output_csv=output_csv, save_plots=args.save_plots)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
