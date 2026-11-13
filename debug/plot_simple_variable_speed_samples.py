# -*- coding: utf-8 -*-
"""Diagnostic figure: Simple Variable Speed profiles for representative slices."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from support_modules import simple_variable_speed as svs  # noqa: E402

SAMPLES = [
    (
        "Ramped cone",
        Path(r"C:\Users\cheng sun\BoyuanSun\Slicing\Evan\Cone_R500_0_To2500_0_H5000_0_LH50_0"),
    ),
    (
        "NU (50 µm layers)",
        Path(r"C:\Users\cheng sun\BoyuanSun\Slicing\Evan\Old Prince\NU_50umLauers"),
    ),
    (
        "Mouse microscope top",
        Path(r"C:\Users\cheng sun\BoyuanSun\Slicing\Evan\MouseMicroscope_Top_12um"),
    ),
]

CONTROL_SPEED = 1000.0  # µm/s
CORRECTION = 1.0
TARGET_PWM = 100.0


def main() -> None:
    out_dir = REPO / "documentation" / "analysis_summaries"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "simple_variable_speed_representative_profiles.png"

    results = []
    for label, folder in SAMPLES:
        print(f"\n=== {label}: {folder.name} ===", flush=True)
        _header, rows = svs.read_instruction_file(svs.instruction_txt_path(folder))
        n = len(rows)
        ctrl_idx = max(1, (n + 1) // 2)
        print(f"layers={n}, control_layer={ctrl_idx}", flush=True)

        def prog(i, total, _label=label):
            if i == 1 or i == total or i % 50 == 0:
                print(f"  [{_label}] {i}/{total}", flush=True)

        r0 = svs.dmax_for_layer_file(folder, ctrl_idx, fill_holes=False)
        if r0 <= 0:
            for k in range(1, n + 1):
                r0 = svs.dmax_for_layer_file(folder, k, fill_holes=False)
                if r0 > 0:
                    ctrl_idx = k
                    break
        thickness = float(rows[ctrl_idx - 1][2])
        dose = TARGET_PWM * thickness / CONTROL_SPEED
        print(
            f"R0={r0:.4f} mm from layer {ctrl_idx}, "
            f"thickness={thickness} µm, dose={dose:.6f}",
            flush=True,
        )

        sched = svs.compute_schedule_for_folder(
            folder,
            control_speed_um_s=CONTROL_SPEED,
            control_dose=dose,
            control_size_mm=r0,
            correction=CORRECTION,
            fill_holes=False,
            progress_callback=prog,
        )
        results.append((label, folder.name, ctrl_idx, r0, sched))
        print(
            f"done: zmax={sched.z_mm[-1]:.3f} mm, "
            f"speed [{min(sched.speeds_um_s):.1f}, {max(sched.speeds_um_s):.1f}] µm/s",
            flush=True,
        )

    fig, axes = plt.subplots(1, 3, figsize=(12.5, 4.2), constrained_layout=True)
    for ax, (label, folder_name, ctrl_idx, r0, sched) in zip(axes, results):
        ax.plot(sched.z_mm, sched.speeds_um_s, color="#2F6FED", lw=1.4)
        ax.axhline(
            CONTROL_SPEED,
            color="#888",
            ls="--",
            lw=0.9,
            label=f"v0={CONTROL_SPEED:.0f}",
        )
        ax.set_title(f"{label}\nR0={r0:.3f} mm (L{ctrl_idx})", fontsize=10)
        ax.set_xlabel("Z height (mm)")
        ax.set_ylabel("Speed (µm/s)")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8, loc="best")
        ax.text(
            0.02,
            0.02,
            folder_name,
            transform=ax.transAxes,
            fontsize=6,
            color="#666",
            va="bottom",
        )

    fig.suptitle(
        "Simple Variable Speed — representative Speed vs Z\n"
        f"c=1, β=4, no hole fill, v0={CONTROL_SPEED:.0f} µm/s, "
        f"PWM_ctrl≈{TARGET_PWM:.0f}",
        fontsize=12,
    )
    fig.savefig(out_path, dpi=160)
    print(f"\nSaved: {out_path}", flush=True)


if __name__ == "__main__":
    main()
