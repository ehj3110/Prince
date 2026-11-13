# -*- coding: utf-8 -*-
"""Uncapped, normalized Simple Variable Speed profiles (diagnostic).

Uses v/v0 = 1 / (1 + c * (R_tilde**beta - 1)) with no max(0, ...) floor
and no v <= v0 clamp. Empty layers (d_max=0) are left as NaN.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

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

BETA = 4.0
CORRECTION = 1.0  # c


def normalized_speed(d_max_mm: np.ndarray, r0_mm: float, c: float, beta: float) -> np.ndarray:
    """Return v/v0 with no clamps. NaN where undefined (empty or non-positive denom)."""
    out = np.full(d_max_mm.shape, np.nan, dtype=float)
    valid = d_max_mm > 0
    r_tilde = d_max_mm[valid] / float(r0_mm)
    denom = 1.0 + float(c) * (np.power(r_tilde, beta) - 1.0)
    good = denom > 1e-12
    vals = np.full(r_tilde.shape, np.nan, dtype=float)
    vals[good] = 1.0 / denom[good]
    out[valid] = vals
    return out


def main() -> None:
    out_dir = REPO / "documentation" / "analysis_summaries"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "simple_variable_speed_normalized_uncapped.png"
    cache_path = out_dir / "simple_variable_speed_dmax_cache.npz"

    cache = {}
    if cache_path.is_file():
        loaded = np.load(cache_path, allow_pickle=True)
        cache = {k: loaded[k] for k in loaded.files}
        print(f"Loaded d_max cache: {cache_path}", flush=True)

    results = []
    for label, folder in SAMPLES:
        key = folder.name
        print(f"\n=== {label}: {key} ===", flush=True)
        _header, rows = svs.read_instruction_file(svs.instruction_txt_path(folder))
        n = len(rows)
        thicknesses = np.array([float(r[2]) for r in rows], dtype=float)
        z_mm = np.cumsum(thicknesses) / 1000.0
        ctrl_idx = max(1, (n + 1) // 2)

        cache_key_d = f"{key}__dmax"
        cache_key_r0 = f"{key}__r0"
        cache_key_ctrl = f"{key}__ctrl"

        if cache_key_d in cache:
            d_max = np.asarray(cache[cache_key_d], dtype=float)
            r0 = float(cache[cache_key_r0])
            ctrl_idx = int(cache[cache_key_ctrl])
            print(f"using cached d_max ({len(d_max)} layers), R0={r0:.4f} mm (L{ctrl_idx})", flush=True)
        else:
            print(f"computing d_max for {n} layers…", flush=True)

            def prog(i, total, _label=label):
                if i == 1 or i == total or i % 50 == 0:
                    print(f"  [{_label}] {i}/{total}", flush=True)

            d_list = []
            for i, cells in enumerate(rows, start=1):
                mask = svs.load_binary_mask(folder / cells[1])
                d_list.append(
                    svs.compute_dmax_mm(mask, fill_holes=False)
                )
                prog(i, n)
            d_max = np.asarray(d_list, dtype=float)
            r0 = float(d_max[ctrl_idx - 1])
            if r0 <= 0:
                positives = np.where(d_max > 0)[0]
                if len(positives) == 0:
                    raise RuntimeError(f"No positive d_max in {folder}")
                ctrl_idx = int(positives[len(positives) // 2]) + 1
                r0 = float(d_max[ctrl_idx - 1])
            cache[cache_key_d] = d_max
            cache[cache_key_r0] = np.array(r0)
            cache[cache_key_ctrl] = np.array(ctrl_idx)

        v_norm = normalized_speed(d_max, r0, CORRECTION, BETA)
        finite = v_norm[np.isfinite(v_norm)]
        print(
            f"R0={r0:.4f} mm (L{ctrl_idx}); "
            f"v/v0 range [{np.min(finite):.4g}, {np.max(finite):.4g}]",
            flush=True,
        )
        results.append((label, key, ctrl_idx, r0, z_mm, d_max, v_norm))

    np.savez(cache_path, **cache)
    print(f"Wrote cache: {cache_path}", flush=True)

    fig, axes = plt.subplots(1, 3, figsize=(12.5, 4.2), constrained_layout=True)
    for ax, (label, folder_name, ctrl_idx, r0, z_mm, d_max, v_norm) in zip(axes, results):
        ax.plot(z_mm, v_norm, color="#2F6FED", lw=1.4)
        ax.axhline(1.0, color="#888", ls="--", lw=0.9, label="v/v0 = 1")
        ax.set_title(f"{label}\nR0={r0:.3f} mm (L{ctrl_idx})", fontsize=10)
        ax.set_xlabel("Z height (mm)")
        ax.set_ylabel("Normalized speed v / v0")
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
        # For NU / thin geometries, auto-scale can hide structure — keep a sensible floor view
        finite = v_norm[np.isfinite(v_norm)]
        if finite.size:
            ymin = max(0.0, float(np.min(finite)) * 0.95)
            ymax = float(np.max(finite)) * 1.05
            if ymax <= ymin:
                ymax = ymin + 0.1
            ax.set_ylim(ymin, ymax)

    fig.suptitle(
        "Simple Variable Speed — uncapped normalized profiles\n"
        fr"$v/v_0 = 1/\left(1 + c\,(\tilde{{R}}^{{\beta}}-1)\right)$  "
        f"with c={CORRECTION:g}, β={BETA:g}, no min/max clamps "
        r"(equiv. $v/v_0=\tilde{R}^{-4}$ when c=1)",
        fontsize=11,
    )
    fig.savefig(out_path, dpi=160)
    print(f"\nSaved: {out_path}", flush=True)


if __name__ == "__main__":
    main()
