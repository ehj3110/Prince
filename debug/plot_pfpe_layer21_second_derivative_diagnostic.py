from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from support_modules.RawData_Processor import RawDataProcessor
from support_modules.adhesion_metrics_calculator import AdhesionMetricsCalculator


def smooth_trace(y: np.ndarray, window: int = 11) -> np.ndarray:
    if len(y) < 5:
        return y
    w = min(window, len(y) if len(y) % 2 == 1 else len(y) - 1)
    w = max(5, w)
    if w % 2 == 0:
        w -= 1
    kernel = np.ones(w, dtype=float) / float(w)
    return np.convolve(y, kernel, mode="same")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    csv_path = root / "post-processing" / "manuscript_data" / "PFPE_19p63" / "autolog_L20-L24.csv"
    out_dir = root / "debug" / "plots"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "pfpe_layer21_second_derivative_diagnostic.png"

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
    try:
        layer_idx = layer_numbers.index(21)
    except ValueError as exc:
        raise RuntimeError("Layer 21 not found in filename-derived layers") from exc

    lifting_start, lifting_end = boundaries[layer_idx]["lifting"]
    retraction_start, retraction_end = boundaries[layer_idx]["retraction"]

    # Use full lift->retraction window so we can see if decay continues after stage stop.
    window_start = lifting_start
    window_end = retraction_end

    window_time_abs = time_data[window_start : window_end + 1]
    window_force_raw = force_data[window_start : window_end + 1]

    smoothed_all = calc._apply_smoothing(force_data)
    window_force_smooth = smoothed_all[window_start : window_end + 1]

    lifting_time = time_data[lifting_start : lifting_end + 1]
    lifting_pos = pos_data[lifting_start : lifting_end + 1]
    lifting_force = force_data[lifting_start : lifting_end + 1]
    retraction_force = force_data[retraction_start : retraction_end + 1]
    lifting_time_rel = lifting_time - lifting_time[0]

    metrics = calc.calculate_from_arrays(
        time_data=lifting_time_rel,
        position_data=lifting_pos,
        force_data=lifting_force,
        layer_number=21,
        lifting_start_idx=0,
        retraction_force_data=retraction_force,
        retraction_start_idx=retraction_start,
        contact_area=19.63e-6,
    )

    baseline = float(metrics.get("baseline_force", 0.0))
    prop_end_time_rel = float(metrics.get("propagation_end_time", 0.0))
    prop_end_time_abs = lifting_time[0] + prop_end_time_rel

    lifting_smoothed = calc._apply_smoothing(lifting_force)
    peak_idx_local, peak_force_abs = calc._find_peak_force(lifting_smoothed)
    peak_time_abs = lifting_time[peak_idx_local]

    ten_percent_peak = 0.1 * float(peak_force_abs)

    peak_idx_window = peak_idx_local

    below_10_idx = None
    for i in range(peak_idx_window, len(window_force_smooth)):
        if float(window_force_smooth[i]) <= ten_percent_peak:
            below_10_idx = i
            break

    guard_threshold = 0.1 * float(peak_force_abs) if peak_force_abs < 0.5 else 0.1
    below_guard_idx = None
    for i in range(peak_idx_window, len(window_force_smooth)):
        if float(window_force_smooth[i]) <= guard_threshold:
            below_guard_idx = i
            break

    rel_t = window_time_abs - lifting_time[0]
    stage_stop_time_rel = float(time_data[lifting_end] - lifting_time[0])
    prop_end_time_rel_window = float(prop_end_time_abs - lifting_time[0])

    d2 = np.gradient(np.gradient(window_force_smooth))
    d2_smooth = smooth_trace(d2, window=11)

    fig, (ax_force, ax_d2) = plt.subplots(2, 1, figsize=(14, 9), dpi=160, sharex=True)

    ax_force.plot(rel_t, window_force_raw, color="black", alpha=0.35, linewidth=1.0, label="Raw force")
    ax_force.plot(rel_t, window_force_smooth, color="navy", linewidth=2.0, label="Smoothed force")

    ax_force.axhline(baseline, color="gray", linestyle="--", linewidth=1.8, label=f"Baseline={baseline:.4f} N")
    ax_force.axhline(ten_percent_peak, color="tab:red", linestyle="-.", linewidth=1.5, label=f"10% peak={ten_percent_peak:.4f} N")
    ax_force.axhline(guard_threshold, color="tab:orange", linestyle=":", linewidth=1.5, label=f"Guard threshold={guard_threshold:.4f} N")

    ax_force.axvline(float(peak_time_abs - lifting_time[0]), color="tab:blue", linestyle="--", linewidth=1.8, label="Peak force")
    ax_force.axvline(prop_end_time_rel_window, color="purple", linestyle=":", linewidth=2.0, label="Chosen propagation end")
    ax_force.axvline(stage_stop_time_rel, color="tab:brown", linestyle="-", linewidth=2.0, label="Stage stop (lift end)")

    if below_10_idx is not None:
        ax_force.plot(rel_t[below_10_idx], window_force_smooth[below_10_idx], marker="o", color="tab:red", markersize=6)
    else:
        ax_force.text(0.02, 0.03, "No 10%-of-peak crossing in plotted window", transform=ax_force.transAxes, color="tab:red", fontsize=10)

    if below_guard_idx is not None:
        ax_force.plot(rel_t[below_guard_idx], window_force_smooth[below_guard_idx], marker="s", color="tab:orange", markersize=6)
    else:
        ax_force.text(0.02, 0.09, "No guard-threshold crossing in plotted window", transform=ax_force.transAxes, color="tab:orange", fontsize=10)

    ax_force.set_ylabel("Force (N)")
    ax_force.set_title("PFPE Layer 21 diagnostic: force + baseline/threshold markers")
    ax_force.grid(alpha=0.25)
    ax_force.legend(loc="best", fontsize=9)

    ax_d2.plot(rel_t, d2_smooth, color="darkmagenta", linewidth=1.8, label="Smoothed 2nd derivative")
    ax_d2.axhline(0.0, color="gray", linewidth=1.0)
    ax_d2.axvline(float(peak_time_abs - lifting_time[0]), color="tab:blue", linestyle="--", linewidth=1.6, label="Peak force")
    ax_d2.axvline(prop_end_time_rel_window, color="purple", linestyle=":", linewidth=2.0, label="Chosen propagation end")
    ax_d2.axvline(stage_stop_time_rel, color="tab:brown", linestyle="-", linewidth=2.0, label="Stage stop (lift end)")
    if below_10_idx is not None:
        ax_d2.axvline(rel_t[below_10_idx], color="tab:red", linestyle="-.", linewidth=1.4, label="10% peak crossing")
    if below_guard_idx is not None:
        ax_d2.axvline(rel_t[below_guard_idx], color="tab:orange", linestyle="-.", linewidth=1.4, label="Guard-threshold crossing")

    ax_d2.set_xlabel("Time from lift start (s)")
    ax_d2.set_ylabel("d2F/dt2 (a.u.)")
    ax_d2.set_title("Smoothed second derivative for Layer 21")
    ax_d2.grid(alpha=0.25)
    ax_d2.legend(loc="best", fontsize=9)

    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)

    print(f"Saved: {out_path}")
    print(f"Layer 21 peak_abs={peak_force_abs:.6f} N")
    print(f"Layer 21 baseline={baseline:.6f} N")
    print(f"10pct_peak={ten_percent_peak:.6f} N | guard_threshold={guard_threshold:.6f} N")
    print(f"Stage stop rel-time={stage_stop_time_rel:.6f} s | prop_end rel-time={prop_end_time_rel_window:.6f} s")
    if below_10_idx is None:
        print("No 10%-of-peak crossing in plotted window (lift+retraction).")
    else:
        print(f"10%-of-peak crossing rel-time={rel_t[below_10_idx]:.6f} s")
    if below_guard_idx is None:
        print("No guard-threshold crossing in plotted window (lift+retraction).")
    else:
        print(f"Guard-threshold crossing rel-time={rel_t[below_guard_idx]:.6f} s")


if __name__ == "__main__":
    main()
