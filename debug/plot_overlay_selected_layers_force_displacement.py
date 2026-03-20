from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from support_modules.RawData_Processor import RawDataProcessor
from support_modules.adhesion_metrics_calculator import AdhesionMetricsCalculator


def extract_layer_curve(csv_path: Path, target_layer: int) -> tuple[np.ndarray, np.ndarray, float]:
    calc = AdhesionMetricsCalculator(
        median_kernel=5,
        savgol_window=9,
        savgol_order=2,
        baseline_threshold_factor=0.002,
        min_peak_height=0.01,
        min_peak_distance=50,
        prop_end_mode="two_step_max_second_derivative",
    )
    proc = RawDataProcessor(calc)

    df = proc._load_and_prepare_data(str(csv_path))
    if df is None:
        raise RuntimeError(f"Failed to load {csv_path}")

    time_data = df["Elapsed Time (s)"].to_numpy()
    force_data = df["Force (N)"].to_numpy()
    pos_data = df["Position (mm)"].to_numpy()

    if "Phase" in df.columns:
        phase_data = df["Phase"].to_numpy()
        boundaries = proc._detect_boundaries_from_phases(time_data, pos_data, force_data, phase_data)
        if len(boundaries) == 0:
            boundaries = proc._detect_boundaries_adaptive(time_data, pos_data, force_data)
    else:
        boundaries = proc._detect_boundaries_adaptive(time_data, pos_data, force_data)

    layer_numbers = proc._extract_layer_numbers_from_filename(str(csv_path))
    if target_layer not in layer_numbers:
        raise RuntimeError(f"Layer {target_layer} not in file {csv_path.name}: layers={layer_numbers}")

    idx = layer_numbers.index(target_layer)
    lifting_start, lifting_end = boundaries[idx]["lifting"]

    layer_results = proc.process_csv(str(csv_path)) or []
    selected_layer = None
    for layer in layer_results:
        if int(layer.get("number", -1)) == int(target_layer):
            selected_layer = layer
            break
    if selected_layer is None:
        raise RuntimeError(f"Could not find metrics for layer {target_layer} in {csv_path.name}")

    energy_release_rate = float(
        selected_layer.get("metrics", {}).get("energy_release_rate_G_J_per_m2", 0.0)
    )

    lift_force = force_data[lifting_start : lifting_end + 1]
    lift_pos = pos_data[lifting_start : lifting_end + 1]

    smoothed_force = calc._apply_smoothing(lift_force)

    # Sync displacement so all traces start at x = 0 at lift onset.
    disp_rel = np.abs(lift_pos - lift_pos[0])

    return disp_rel, smoothed_force, energy_release_rate


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    out_dir = root / "debug" / "plots"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "overlay_force_vs_displacement_selected_layers.png"

    plt.rcParams["font.family"] = "Times New Roman"

    configs = [
        {
            "label": "Flat PDMS",
            "path": root / "post-processing" / "manuscript_data" / "FlatPDMS_19p63" / "autolog_L10-L14.csv",
            "layer": 10,
            "color": "orange",
            "linestyle": "-",
        },
        {
            "label": "800nm PDMS",
            "path": root / "post-processing" / "manuscript_data" / "800nmPDMS_19p63" / "autolog_L10-L14.csv",
            "layer": 10,
            "color": "red",
            "linestyle": "-",
        },
        {
            "label": "PFPE",
            "path": root / "post-processing" / "manuscript_data" / "PFPE_19p63" / "autolog_L10-L14.csv",
            "layer": 13,
            "color": "blue",
            "linestyle": "-",
        },
        {
            "label": "TEMPO",
            "path": root / "post-processing" / "manuscript_data" / "TEMPO_19p63" / "autolog_L5-L9.csv",
            "layer": 5,
            "color": "green",
            "linestyle": "-",
        },
    ]

    curves = []
    for cfg in configs:
        x, y, g_value = extract_layer_curve(cfg["path"], cfg["layer"])
        curves.append((cfg, x, y, g_value))

    plt.figure(figsize=(10, 6), dpi=180)

    xmax = 0.0
    for cfg, x, y, g_value in curves:
        x_um = x * 1000.0
        xmax = max(xmax, float(np.max(x_um)))
        peak_idx = int(np.argmax(y))
        peak_x = float(x_um[peak_idx])
        g_coeff = g_value / 1e-5

        plt.plot(
            x_um,
            y,
            color=cfg["color"],
            linestyle=cfg["linestyle"],
            linewidth=2.2,
            label=f"{cfg['label']} (G={g_coeff:.3g} x 10^-5)",
        )
        plt.axvline(
            x=peak_x,
            color=cfg["color"],
            linestyle="--",
            linewidth=1.8,
            alpha=0.9,
            label="_nolegend_",
        )

    plt.xlim(0.0, xmax)
    plt.xlabel("Displacement from lift start (micrometers)", fontsize=18, fontweight="bold")
    plt.ylabel("Force (N)", fontsize=18, fontweight="bold")
    plt.title("Controlled experiment: Compound Energy Release Rate", fontsize=18, fontweight="bold")
    plt.tick_params(axis="both", which="major", labelsize=15)
    plt.grid(alpha=0.25)
    plt.legend(loc="best", framealpha=0.9, fontsize=13)
    plt.tight_layout()
    plt.savefig(out_path, dpi=180)
    plt.close()

    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
