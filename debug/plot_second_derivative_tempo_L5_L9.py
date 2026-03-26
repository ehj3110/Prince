from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from support_modules.RawData_Processor import RawDataProcessor
from support_modules.adhesion_metrics_calculator import AdhesionMetricsCalculator


def smooth_for_plot(y: np.ndarray, window: int = 31) -> np.ndarray:
    """Light smoothing for derivative visualization only."""
    if len(y) < 5:
        return y
    # Keep an odd, bounded window for stable smoothing on short traces.
    w = min(window, len(y) if len(y) % 2 == 1 else len(y) - 1)
    w = max(5, w)
    kernel = np.ones(w, dtype=float) / float(w)
    return np.convolve(y, kernel, mode="same")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    csv_path = root / "post-processing" / "manuscript_data" / "TEMPO_19p63" / "autolog_L5-L9.csv"
    out_dir = root / "debug" / "plots"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "tempo_L5-L9_second_derivative_diagnostics.png"

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

    boundaries = proc._detect_boundaries_from_phases(
        time_data, pos_data, force_data, df["Phase"].to_numpy()
    )
    if len(boundaries) == 0:
        boundaries = proc._detect_boundaries_adaptive(time_data, pos_data, force_data)

    layer_numbers = proc._extract_layer_numbers_from_filename(str(csv_path))

    fig, axes = plt.subplots(len(layer_numbers), 2, figsize=(16, 3.5 * len(layer_numbers)), dpi=150)
    if len(layer_numbers) == 1:
        axes = np.array([axes])

    for i, layer_num in enumerate(layer_numbers):
        lifting_start, lifting_end = boundaries[i]["lifting"]

        lt = time_data[lifting_start : lifting_end + 1]
        lf = force_data[lifting_start : lifting_end + 1]
        rel_t = lt - lt[0]

        smoothed = calc._apply_smoothing(lf)
        peak_idx, peak_force = calc._find_peak_force(smoothed)
        search_end = len(smoothed) - 1

        old_idx = calc._find_propagation_end_two_step_legacy_local_max_second_derivative(
            rel_t, smoothed, peak_idx, search_end
        )

        threshold = 0.1 * peak_force if peak_force < 0.5 else 0.1
        crossing_idx = None
        for idx in range(peak_idx, search_end + 1):
            if float(smoothed[idx]) < float(threshold):
                crossing_idx = idx
                break

        if crossing_idx is None:
            new_idx = old_idx
            sec = np.gradient(np.gradient(smoothed[peak_idx : search_end + 1]))
            sec = smooth_for_plot(sec)
            sec_x = rel_t[peak_idx : search_end + 1]
            sec_peak_idx = peak_idx + int(np.argmax(sec))
            sec_zero_idx = sec_peak_idx
        else:
            detector = smoothed[crossing_idx : search_end + 1]
            if len(detector) < 3:
                new_idx = old_idx
                sec = np.gradient(np.gradient(detector)) if len(detector) > 1 else np.array([0.0])
                sec = smooth_for_plot(sec)
                sec_x = rel_t[crossing_idx : search_end + 1]
                sec_peak_idx = old_idx
                sec_zero_idx = old_idx
            else:
                sec = np.gradient(np.gradient(detector))
                sec = smooth_for_plot(sec)
                local_max = int(np.argmax(sec))
                new_idx = crossing_idx + local_max
                local_zero = local_max
                for j in range(local_max + 1, len(sec)):
                    if float(sec[j - 1]) > 0 and float(sec[j]) <= 0:
                        local_zero = j
                        break
                sec_x = rel_t[crossing_idx : search_end + 1]
                sec_peak_idx = crossing_idx + local_max
                sec_zero_idx = crossing_idx + local_zero

        ax_force = axes[i, 0]
        ax_sec = axes[i, 1]

        ax_force.plot(rel_t, lf, color="black", alpha=0.35, linewidth=1.0, label="Raw force")
        ax_force.plot(rel_t, smoothed, color="navy", linewidth=1.8, label="Smoothed force")
        ax_force.axvline(rel_t[peak_idx], color="tab:blue", linestyle="--", linewidth=1.5, label="Peak")
        ax_force.axvline(
            rel_t[sec_peak_idx],
            color="mediumorchid",
            linestyle="--",
            linewidth=1.3,
            alpha=0.9,
            label="2nd-deriv peak",
        )
        ax_force.axvline(rel_t[old_idx], color="tab:orange", linestyle=":", linewidth=1.5, label="Old prop end")
        ax_force.axvline(rel_t[new_idx], color="tab:green", linestyle="-.", linewidth=1.5, label="New prop end")
        if crossing_idx is not None:
            ax_force.axvline(rel_t[crossing_idx], color="tab:red", linestyle="--", linewidth=1.2, label="Threshold crossing")
        ax_force.axhline(threshold, color="tab:red", linestyle="-", linewidth=1.2, alpha=0.8, label=f"Threshold={threshold:.3f}N")
        ax_force.plot(
            rel_t[sec_peak_idx],
            smoothed[sec_peak_idx],
            marker="o",
            color="mediumorchid",
            markersize=4,
            zorder=5,
        )
        ax_force.annotate(
            "2nd-deriv peak",
            xy=(rel_t[sec_peak_idx], smoothed[sec_peak_idx]),
            xytext=(6, 8),
            textcoords="offset points",
            color="mediumorchid",
            fontsize=8,
        )
        ax_force.set_ylabel("Force (N)")
        ax_force.set_title(f"Layer {layer_num}: force domain")
        ax_force.grid(alpha=0.25)
        if i == 0:
            ax_force.legend(fontsize=8, loc="best")

        ax_sec.plot(sec_x, sec, color="purple", linewidth=1.5, label="2nd derivative (smoothed, strong)")
        if len(sec_x) > 0:
            ax_sec.axvline(rel_t[sec_peak_idx], color="tab:blue", linestyle="--", linewidth=1.5, label="2nd-deriv peak")
            ax_sec.axvline(rel_t[sec_zero_idx], color="tab:green", linestyle="-.", linewidth=1.5, label="First zero crossing")
        ax_sec.axhline(0.0, color="gray", linewidth=1.0)
        ax_sec.set_ylabel("d2F/dt2 (a.u.)")
        ax_sec.set_title(f"Layer {layer_num}: detector domain")
        ax_sec.grid(alpha=0.25)
        if i == 0:
            ax_sec.legend(fontsize=8, loc="best")

    axes[-1, 0].set_xlabel("Time from lift start (s)")
    axes[-1, 1].set_xlabel("Time from lift start (s)")

    fig.suptitle("TEMPO autolog_L5-L9: propagation-end second-derivative diagnostics", fontsize=14, y=0.995)
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.985))
    fig.savefig(out_path, dpi=150)
    plt.close(fig)

    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
