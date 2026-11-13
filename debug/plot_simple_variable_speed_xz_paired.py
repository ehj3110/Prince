# -*- coding: utf-8 -*-
"""XZ + YZ cross-sections paired with uncapped normalized speed (log) vs Z.

Comparative diagnostic figure: shared Z scale across samples, fixed XZ/YZ panel
sizes, presentable titles. (Per-part Z scaling belongs in the operator tool UI.)
"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import gridspec
from matplotlib.colors import Normalize

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from support_modules import simple_variable_speed as svs  # noqa: E402
from debug.plot_simple_variable_speed_normalized import (  # noqa: E402
    BETA,
    CORRECTION,
    SAMPLES,
    normalized_speed,
)

PX_PITCH_MM = svs.PX_PITCH_MM

ROW_TITLES = {
    "Ramped cone": "Ramped Cone",
    "NU (50 µm layers)": "NU",
    "Mouse microscope top": "Mouse Microscope",
}
PLOT_TITLES = ("XZ Cross-section", "YZ Cross-section", "Normalized ramping routine")


def _stack_horizontal_rows(paths: list[Path], y: int) -> np.ndarray:
    rows = []
    width = None
    for p in paths:
        img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise FileNotFoundError(p)
        h, w = img.shape
        yy = min(max(y, 0), h - 1)
        line = img[yy, :]
        if width is None:
            width = w
        elif w != width:
            if w < width:
                pad = np.zeros(width, dtype=line.dtype)
                pad[:w] = line
                line = pad
            else:
                line = line[:width]
        rows.append(line.astype(np.uint8))
    return np.vstack(rows)


def _stack_vertical_cols(paths: list[Path], x: int) -> np.ndarray:
    cols = []
    height = None
    for p in paths:
        img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise FileNotFoundError(p)
        h, w = img.shape
        xx = min(max(x, 0), w - 1)
        line = img[:, xx]
        if height is None:
            height = h
        elif h != height:
            if h < height:
                pad = np.zeros(height, dtype=line.dtype)
                pad[:h] = line
                line = pad
            else:
                line = line[:height]
        cols.append(line.astype(np.uint8))
    return np.vstack(cols)


def _choose_xz_row(paths: list[Path]) -> np.ndarray:
    sample = cv2.imread(str(paths[0]), cv2.IMREAD_GRAYSCALE)
    if sample is None:
        raise FileNotFoundError(paths[0])
    height = int(sample.shape[0])
    mid = height // 2
    xz_mid = _stack_horizontal_rows(paths, mid)
    if np.count_nonzero(xz_mid >= 127) > 0:
        return xz_mid
    totals = np.zeros(height, dtype=np.int64)
    step = max(1, len(paths) // 40)
    for p in paths[::step]:
        img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        totals[: img.shape[0]] += (img >= 127).sum(axis=1)
    return _stack_horizontal_rows(paths, int(np.argmax(totals)))


def _choose_yz_col(paths: list[Path]) -> np.ndarray:
    sample = cv2.imread(str(paths[0]), cv2.IMREAD_GRAYSCALE)
    if sample is None:
        raise FileNotFoundError(paths[0])
    width = int(sample.shape[1])
    mid = width // 2
    yz_mid = _stack_vertical_cols(paths, mid)
    if np.count_nonzero(yz_mid >= 127) > 0:
        return yz_mid
    totals = np.zeros(width, dtype=np.int64)
    step = max(1, len(paths) // 40)
    for p in paths[::step]:
        img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        totals[: img.shape[1]] += (img >= 127).sum(axis=0)
    return _stack_vertical_cols(paths, int(np.argmax(totals)))


def _fit_width(section: np.ndarray, target_w: int) -> np.ndarray:
    if section.shape[1] == target_w:
        return section
    if section.shape[1] > target_w:
        return section[:, :target_w]
    pad = np.zeros((section.shape[0], target_w), dtype=section.dtype)
    pad[:, : section.shape[1]] = section
    return pad


def _pad_section_to_z(
    section: np.ndarray, z_edges: np.ndarray, z_max_mm: float
) -> np.ndarray:
    if z_edges[-1] >= z_max_mm - 1e-9:
        return section
    dz = float(np.mean(np.diff(z_edges))) if len(z_edges) > 1 else 0.05
    if dz <= 0:
        dz = 0.05
    n_extra = int(np.ceil((z_max_mm - z_edges[-1]) / dz))
    if n_extra <= 0:
        return section
    pad = np.zeros((n_extra, section.shape[1]), dtype=section.dtype)
    return np.vstack([section, pad])


def _style_axes(ax) -> None:
    ax.tick_params(labelsize=8)
    for spine in ax.spines.values():
        spine.set_linewidth(0.8)
        spine.set_color("#444444")


def _show_section(
    ax, section: np.ndarray, lat_mm: float, z_max_mm: float, title: str
) -> None:
    ax.imshow(
        section,
        cmap="gray",
        aspect="equal",
        interpolation="nearest",
        origin="lower",
        extent=[0.0, lat_mm, 0.0, z_max_mm],
        norm=Normalize(vmin=0, vmax=255),
    )
    ax.set_xlim(0.0, lat_mm)
    ax.set_ylim(0.0, z_max_mm)
    ax.set_xlabel("mm", fontsize=9)
    ax.set_ylabel("Z (mm)", fontsize=9)
    if title:
        ax.set_title(title, fontsize=10, pad=6)
    ax.set_adjustable("box")
    _style_axes(ax)


def main() -> None:
    out_dir = REPO / "documentation" / "analysis_summaries"
    cache_path = out_dir / "simple_variable_speed_dmax_cache.npz"
    out_path = out_dir / "simple_variable_speed_xz_yz_speed_paired.png"
    cache = np.load(cache_path)

    sample0 = cv2.imread(
        str(svs.list_instruction_image_paths(SAMPLES[0][1])[0]),
        cv2.IMREAD_GRAYSCALE,
    )
    if sample0 is None:
        raise FileNotFoundError("Could not read a sample slice for panel sizing")
    frame_h_px, frame_w_px = sample0.shape
    x_extent_mm = frame_w_px * PX_PITCH_MM
    y_extent_mm = frame_h_px * PX_PITCH_MM

    prepared = []
    z_max_mm = 0.0
    for label, folder in SAMPLES:
        key = folder.name
        d_max = np.asarray(cache[f"{key}__dmax"], dtype=float)
        r0 = float(cache[f"{key}__r0"])
        _header, rows = svs.read_instruction_file(svs.instruction_txt_path(folder))
        thicknesses = np.array([float(r[2]) for r in rows], dtype=float)
        z_mm = np.cumsum(thicknesses) / 1000.0
        z_edges = np.concatenate([[0.0], z_mm])
        z_max_mm = max(z_max_mm, float(z_edges[-1]))
        print(f"Building XZ/YZ for {key} ({len(rows)} layers)…", flush=True)
        paths = [folder / cells[1] for cells in rows]
        xz = _fit_width(_choose_xz_row(paths), frame_w_px)
        yz = _fit_width(_choose_yz_col(paths), frame_h_px)
        v_norm = normalized_speed(d_max, r0, CORRECTION, BETA)
        prepared.append((label, xz, yz, z_edges, z_mm, v_norm, r0))

    for i, (label, xz, yz, z_edges, z_mm, v_norm, r0) in enumerate(prepared):
        prepared[i] = (
            label,
            _pad_section_to_z(xz, z_edges, z_max_mm),
            _pad_section_to_z(yz, z_edges, z_max_mm),
            z_mm,
            v_norm,
            r0,
        )

    # Fixed panel geometry so every XZ (and every YZ) matches across rows.
    xz_panel_w_in = 2.85
    row_h_in = xz_panel_w_in * (z_max_mm / x_extent_mm)
    yz_panel_w_in = row_h_in * (y_extent_mm / z_max_mm)
    speed_panel_w_in = 3.8
    sample_header_in = 0.30
    plot_title_in = 0.26
    block_gap_in = 0.55  # room for x-axis labels before next sample

    n = len(prepared)
    main_title_in = 0.78
    bottom_in = 0.35
    left_in = 0.55
    right_in = 0.28

    # Per sample: sample header → plot titles → plots → gap
    height_ratios: list[float] = []
    for i in range(n):
        height_ratios.extend([sample_header_in, plot_title_in, row_h_in])
        if i < n - 1:
            height_ratios.append(block_gap_in)

    fig_w = left_in + xz_panel_w_in + yz_panel_w_in + speed_panel_w_in + right_in + 0.90
    fig_h = main_title_in + sum(height_ratios) + bottom_in

    fig = plt.figure(figsize=(fig_w, fig_h), facecolor="white")
    gs = gridspec.GridSpec(
        len(height_ratios),
        3,
        figure=fig,
        width_ratios=[xz_panel_w_in, yz_panel_w_in, speed_panel_w_in],
        height_ratios=height_ratios,
        left=left_in / fig_w,
        right=1.0 - right_in / fig_w,
        top=1.0 - main_title_in / fig_h,
        bottom=bottom_in / fig_h,
        wspace=0.30,
        hspace=0.05,
    )

    fig.suptitle(
        "Simple Variable Speed — Cross-sections and Uncapped Normalized Profiles",
        fontsize=14,
        fontweight="semibold",
        y=1.0 - 0.16 / fig_h,
    )
    fig.text(
        0.5,
        1.0 - 0.38 / fig_h,
        rf"$v/v_0 = 1/\left(1 + c\,(\tilde{{R}}^{{\beta}}-1)\right)$"
        f"   ·   c = {CORRECTION:g},  β = {BETA:g}"
        r"   ·   uncapped ($v/v_0=\tilde{R}^{-4}$ when c = 1)",
        ha="center",
        va="top",
        fontsize=9.5,
        color="#333333",
    )
    fig.text(
        0.5,
        1.0 - 0.54 / fig_h,
        "Shared Z scale for comparison  ·  Operator tool will scale Z to each part",
        ha="center",
        va="top",
        fontsize=8.5,
        color="#666666",
        style="italic",
    )

    gs_row = 0
    for label, xz, yz, z_mm, v_norm, r0 in prepared:
        ax_hdr = fig.add_subplot(gs[gs_row, :])
        ax_hdr.axis("off")
        ax_hdr.text(
            0.5,
            0.35,
            ROW_TITLES.get(label, label),
            transform=ax_hdr.transAxes,
            ha="center",
            va="center",
            fontsize=12,
            fontweight="semibold",
        )
        gs_row += 1

        plot_titles = [
            PLOT_TITLES[0],
            PLOT_TITLES[1],
            f"{PLOT_TITLES[2]}  ·  $R_0={r0:.3f}$ mm",
        ]
        for c, t in enumerate(plot_titles):
            ax_t = fig.add_subplot(gs[gs_row, c])
            ax_t.axis("off")
            ax_t.text(
                0.5,
                0.2,
                t,
                transform=ax_t.transAxes,
                ha="center",
                va="center",
                fontsize=10,
            )
        gs_row += 1

        ax_xz = fig.add_subplot(gs[gs_row, 0])
        ax_yz = fig.add_subplot(gs[gs_row, 1])
        ax_sp = fig.add_subplot(gs[gs_row, 2])
        gs_row += 1
        if gs_row < len(height_ratios) and abs(height_ratios[gs_row] - block_gap_in) < 1e-9:
            gs_row += 1

        _show_section(ax_xz, xz, x_extent_mm, z_max_mm, "")
        _show_section(ax_yz, yz, y_extent_mm, z_max_mm, "")
        # Clear empty titles from helper when title="" still calls set_title
        ax_xz.set_title("")
        ax_yz.set_title("")

        finite = v_norm[np.isfinite(v_norm) & (v_norm > 0)]
        ax_sp.plot(v_norm, z_mm, color="#2F6FED", lw=1.6)
        ax_sp.axvline(1.0, color="#666666", ls="--", lw=1.0, label=r"$v/v_0 = 1$")
        if finite.size:
            lo = float(np.min(finite))
            hi = float(np.max(finite))
            if hi <= lo:
                hi = lo * 1.05
            # Narrow ranges (e.g. NU) stay readable on linear; wide ranges use log.
            if hi / lo < 2.0:
                ax_sp.set_xscale("linear")
                pad = 0.08 * (hi - lo if hi > lo else 1.0)
                ax_sp.set_xlim(lo - pad, hi + pad)
            else:
                ax_sp.set_xscale("log")
                ax_sp.set_xlim(lo / 1.4, hi * 1.4)
                ax_sp.grid(True, which="minor", alpha=0.12)
        ax_sp.set_ylim(0.0, z_max_mm)
        ax_sp.set_xlabel(r"$v / v_0$", fontsize=9)
        ax_sp.set_ylabel("Z (mm)", fontsize=9)
        ax_sp.grid(True, which="major", alpha=0.28)
        ax_sp.legend(fontsize=8, loc="best", framealpha=0.92)
        _style_axes(ax_sp)

    fig.savefig(out_path, dpi=170, facecolor="white")
    fig.savefig(
        out_dir / "simple_variable_speed_xz_speed_paired.png",
        dpi=170,
        facecolor="white",
    )
    print(f"Saved: {out_path}", flush=True)


if __name__ == "__main__":
    main()
