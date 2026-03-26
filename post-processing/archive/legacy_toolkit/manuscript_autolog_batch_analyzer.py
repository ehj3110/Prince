"""
Manuscript Autolog Batch Analyzer
=================================

Batch post-processing for autolog files arranged in subfolders named:
    WindowType_ContactArea

Features:
- Recursively discovers autolog CSV files.
- Computes existing adhesion metrics using the unified AdhesionMetricsCalculator.
- Adds manuscript metrics:
  1) Potential energy (baseline-corrected) from lifting start to peak force [mJ].
  2) Critical energy release rate from peak force to propagation end:
       Gc = (baseline-corrected energy) / contact_area  [J/m^2].
- Generates one analysis plot per autolog file.
- Writes per-file layer metrics CSV plus a combined summary CSV.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, cast

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.signal import find_peaks
from scipy.ndimage import gaussian_filter1d

# Add project root so support_modules can be imported from this folder.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from support_modules.adhesion_metrics_calculator import AdhesionMetricsCalculator


DEFAULT_CONTACT_AREA_MM2 = 19.625


@dataclass
class FolderMetadata:
    window_type: str
    contact_area_mm2: float


@dataclass
class LayerSelection:
    layer_index: int
    layer_number: int
    start_idx: int
    end_idx: int
    peak_idx: int


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Map known autolog column names to Time/Position/Force."""
    renamed = df.rename(
        columns={
            "Elapsed Time (s)": "Time",
            "Position (mm)": "Position",
            "Force (N)": "Force",
        }
    )

    required = ["Time", "Position", "Force"]
    missing = [c for c in required if c not in renamed.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    return cast(pd.DataFrame, renamed[required].dropna())


def parse_folder_metadata(folder_name: str, default_area_mm2: float) -> FolderMetadata:
    """
    Parse folder name as WindowType_ContactArea.

    If contact area is not parseable, uses default_area_mm2.
    """
    # Supports names like: FastWindow_19.625
    match = re.match(r"^(?P<window>.+)_(?P<area>[0-9]+(?:\.[0-9]+)?)$", folder_name)
    if not match:
        return FolderMetadata(window_type=folder_name, contact_area_mm2=default_area_mm2)

    window_type = match.group("window")
    area_mm2 = float(match.group("area"))
    if area_mm2 <= 0:
        area_mm2 = default_area_mm2

    return FolderMetadata(window_type=window_type, contact_area_mm2=area_mm2)


def extract_layer_numbers_from_filename(csv_path: Path, expected_count: int) -> List[int]:
    """Extract layer numbers from autolog_Lx-Ly naming; fallback to 1..N."""
    match = re.search(r"L(\d+)-L(\d+)", csv_path.stem)
    if not match:
        return list(range(1, expected_count + 1))

    start_layer = int(match.group(1))
    end_layer = int(match.group(2))
    layers = list(range(start_layer, end_layer + 1))

    if len(layers) >= expected_count:
        return layers[:expected_count]

    # Extend if detection finds more segments than filename implies.
    while len(layers) < expected_count:
        layers.append(layers[-1] + 1)
    return layers


def expected_layer_count_from_filename(csv_path: Path) -> Optional[int]:
    """Return expected number of layers from autolog_Lx-Ly filename, if present."""
    match = re.search(r"L(\d+)-L(\d+)", csv_path.stem)
    if not match:
        return None

    start_layer = int(match.group(1))
    end_layer = int(match.group(2))
    if end_layer < start_layer:
        return None
    return end_layer - start_layer + 1


def _select_top_peaks(peaks: np.ndarray, scores: np.ndarray, target_count: int) -> np.ndarray:
    """Select up to target_count peaks by score, preserving temporal order."""
    if target_count <= 0 or len(peaks) <= target_count:
        return np.sort(peaks.astype(int))

    top_idx = np.argsort(scores)[-target_count:]
    chosen = np.sort(peaks[top_idx].astype(int))
    return chosen


def detect_peaks_adaptive(
    smoothed_force: np.ndarray,
    expected_count: Optional[int],
    min_peak_height: float,
) -> np.ndarray:
    """Detect peaks with progressively relaxed settings when needed."""
    if len(smoothed_force) < 5:
        return np.array([], dtype=int)

    signal_span = float(np.nanmax(smoothed_force) - np.nanmin(smoothed_force))
    dynamic_prom = max(0.001, 0.03 * signal_span)

    configs = [
        (max(20, int(len(smoothed_force) * 0.02)), max(0.005, dynamic_prom), min_peak_height),
        (max(12, int(len(smoothed_force) * 0.012)), max(0.002, dynamic_prom * 0.7), max(0.005, min_peak_height * 0.6)),
        (8, max(0.001, dynamic_prom * 0.45), max(0.003, min_peak_height * 0.4)),
    ]

    best_peaks = np.array([], dtype=int)
    best_score = np.array([], dtype=float)

    for distance, prominence, height in configs:
        peaks, props = find_peaks(smoothed_force, height=height, distance=distance, prominence=prominence)
        if len(peaks) == 0:
            continue

        scores = np.asarray(props.get("prominences", smoothed_force[peaks]), dtype=float)

        if expected_count and expected_count > 0 and len(peaks) >= expected_count:
            return _select_top_peaks(peaks, scores, expected_count)

        if len(peaks) > len(best_peaks):
            best_peaks = peaks.astype(int)
            best_score = scores

    if len(best_peaks) == 0:
        # Last-resort fallback: use global maximum as a single peak.
        return np.array([int(np.argmax(smoothed_force))], dtype=int)

    if expected_count and expected_count > 0:
        return _select_top_peaks(best_peaks, best_score, expected_count)

    return np.sort(best_peaks.astype(int))


def boundaries_from_peaks(peaks: np.ndarray, n_points: int) -> List[Tuple[int, int]]:
    """Build layer boundaries from temporally ordered peak indices."""
    if len(peaks) == 0:
        return [(0, max(0, n_points - 1))]

    peaks_sorted = np.sort(peaks.astype(int))
    starts = [0]
    for i in range(1, len(peaks_sorted)):
        midpoint = int((peaks_sorted[i - 1] + peaks_sorted[i]) // 2)
        starts.append(midpoint)

    return starts_to_boundaries(starts, n_points)


def uniform_boundaries(expected_count: int, n_points: int) -> List[Tuple[int, int]]:
    """Last-resort equal-width segmentation when start detection is unreliable."""
    if expected_count <= 1 or n_points < 2:
        return [(0, max(0, n_points - 1))]

    starts = [int(i * (n_points - 1) / expected_count) for i in range(expected_count)]
    starts = sorted(set(starts))
    return starts_to_boundaries(starts, n_points)


def detect_layer_starts(position_data: np.ndarray) -> List[int]:
    """
    Detect layer start indices from stage motion pattern.

    Based on existing repository logic:
    - Lifting is downward motion (position decreasing).
    - New layer starts once retraction is complete and position stabilizes.
    """
    if len(position_data) < 20:
        return [0]

    sampling_rate = 50
    window_size = 5
    pos_threshold = 0.03
    min_stable_points = int(0.2 * sampling_rate)

    def detect_movement(curr_pos: float, last_pos: float) -> int:
        diff = curr_pos - last_pos
        if abs(diff) < pos_threshold / 2:
            return 0
        return 1 if diff > 0 else -1

    layer_starts = [5]
    i = 10
    last_pos = float(position_data[i])

    while i < len(position_data) - window_size:
        window = position_data[i : i + window_size]
        current_pos = float(np.mean(window))
        direction = detect_movement(current_pos, last_pos)

        # Detect lifting (downward).
        if direction == -1:
            lift_end = None
            lift_end_pos = current_pos

            while i < len(position_data) - window_size:
                i += 1
                window = position_data[i : i + window_size]
                current_pos = float(np.mean(window))
                if detect_movement(current_pos, last_pos) >= 0:
                    lift_end = i
                    lift_end_pos = current_pos
                    break
                last_pos = current_pos

            if lift_end is None:
                break

            retraction_found = False
            return_stable_count = 0
            last_pos = lift_end_pos

            while i < len(position_data) - window_size:
                i += 1
                window = position_data[i : i + window_size]
                current_pos = float(np.mean(window))
                direction = detect_movement(current_pos, last_pos)

                if not retraction_found and direction == 1:
                    retraction_found = True

                if retraction_found:
                    if direction == 0:
                        return_stable_count += 1
                        if return_stable_count >= min_stable_points:
                            layer_starts.append(i)
                            break
                    else:
                        return_stable_count = 0

                last_pos = current_pos

        i += 1
        last_pos = current_pos

    # Keep starts unique and in-range.
    unique_starts = sorted(set(idx for idx in layer_starts if 0 <= idx < len(position_data)))
    return unique_starts if unique_starts else [0]


def starts_to_boundaries(starts: Sequence[int], n_points: int) -> List[Tuple[int, int]]:
    """Convert sorted start indices to inclusive (start, end) boundaries."""
    if not starts:
        return [(0, max(0, n_points - 1))]

    boundaries: List[Tuple[int, int]] = []
    for i in range(len(starts) - 1):
        s = starts[i]
        e = starts[i + 1] - 1
        if e > s:
            boundaries.append((s, e))

    last_start = starts[-1]
    if n_points - 1 > last_start:
        boundaries.append((last_start, n_points - 1))

    return boundaries if boundaries else [(0, max(0, n_points - 1))]


def select_layer_segments(
    boundaries: Sequence[Tuple[int, int]],
    peaks: np.ndarray,
    smoothed_force: np.ndarray,
    layer_numbers: Sequence[int],
) -> List[LayerSelection]:
    """
    Match one representative peak to each boundary segment.

    If a segment has multiple peaks, choose the strongest by smoothed force.
    """
    selected: List[LayerSelection] = []

    for i, (start_idx, end_idx) in enumerate(boundaries):
        in_segment = [p for p in peaks if start_idx <= int(p) <= end_idx]
        if len(in_segment) == 1:
            peak_idx = int(in_segment[0])
        elif len(in_segment) > 1:
            peak_idx = int(max(in_segment, key=lambda p: smoothed_force[int(p)]))
        else:
            # If no peak was detected in this segment, keep the layer by using
            # the segment-local maximum of smoothed force.
            local_slice = smoothed_force[start_idx : end_idx + 1]
            if len(local_slice) == 0:
                continue
            local_max_offset = int(np.argmax(local_slice))
            peak_idx = start_idx + local_max_offset

        layer_number = layer_numbers[i] if i < len(layer_numbers) else (i + 1)
        selected.append(
            LayerSelection(
                layer_index=i,
                layer_number=layer_number,
                start_idx=int(start_idx),
                end_idx=int(end_idx),
                peak_idx=peak_idx,
            )
        )

    return selected


def detect_lift_start_idx(force_data: np.ndarray, baseline_force: float, start_idx: int, peak_idx: int) -> int:
    """Find lift start as first force crossing above baseline before peak."""
    if peak_idx <= start_idx + 1:
        return start_idx

    # Crossing definition: force transitions from <= baseline to > baseline.
    for i in range(start_idx + 1, peak_idx + 1):
        prev_force = float(force_data[i - 1])
        curr_force = float(force_data[i])
        if prev_force <= baseline_force and curr_force > baseline_force:
            return i

    # Fallback if no clean crossing exists in interval.
    return start_idx


def integrate_force_displacement_joule(position_mm: np.ndarray, corrected_force_n: np.ndarray) -> float:
    """Integrate baseline-corrected force vs displacement and return absolute energy [J]."""
    if len(position_mm) < 2:
        return 0.0

    position_m = np.asarray(position_mm, dtype=float) / 1000.0
    force_n = np.asarray(corrected_force_n, dtype=float)

    valid = np.isfinite(position_m) & np.isfinite(force_n)
    position_m = position_m[valid]
    force_n = force_n[valid]

    if len(position_m) < 2:
        return 0.0

    sort_idx = np.argsort(position_m)
    position_sorted = position_m[sort_idx]
    force_sorted = force_n[sort_idx]

    energy_j = float(np.trapezoid(force_sorted, position_sorted))
    return abs(energy_j)


def time_to_global_index(relative_time_s: float, seg_time_s: np.ndarray, global_start_idx: int) -> int:
    """Map a segment-relative timestamp to global index."""
    if len(seg_time_s) == 0:
        return global_start_idx
    local_idx = int(np.argmin(np.abs(seg_time_s - relative_time_s)))
    return global_start_idx + local_idx


def analyze_single_file(
    csv_path: Path,
    calculator: AdhesionMetricsCalculator,
    folder_meta: FolderMetadata,
) -> Tuple[pd.DataFrame, Dict[str, np.ndarray], List[Dict[str, Any]]]:
    """Analyze one autolog CSV and return records plus arrays needed for plotting."""
    raw_df = pd.read_csv(csv_path)
    df = standardize_columns(raw_df)

    time_data = df["Time"].to_numpy(dtype=float)
    position_data = df["Position"].to_numpy(dtype=float)
    force_data = df["Force"].to_numpy(dtype=float)

    if len(df) < 20:
        return pd.DataFrame(), {"time": time_data, "force": force_data, "smoothed": force_data}, []

    smoothed_force = calculator._apply_smoothing(force_data)
    expected_count = expected_layer_count_from_filename(csv_path)
    peaks = detect_peaks_adaptive(
        smoothed_force=smoothed_force,
        expected_count=expected_count,
        min_peak_height=float(getattr(calculator, "min_peak_height", 0.01)),
    )

    starts = detect_layer_starts(position_data)
    boundaries = starts_to_boundaries(starts, len(df))

    # Fallback path for datasets where position-only segmentation collapses.
    if expected_count and expected_count > 1 and len(boundaries) < expected_count:
        if len(peaks) >= 2:
            boundaries = boundaries_from_peaks(peaks, len(df))
        else:
            boundaries = uniform_boundaries(expected_count, len(df))

    if expected_count and expected_count > 0 and len(boundaries) > expected_count:
        boundaries = boundaries[:expected_count]

    layer_numbers = extract_layer_numbers_from_filename(csv_path, len(boundaries))
    segments = select_layer_segments(boundaries, peaks, smoothed_force, layer_numbers)

    records: List[Dict[str, float]] = []
    layer_plot_data: List[Dict[str, Any]] = []

    for seg in segments:
        start_idx = seg.start_idx
        end_idx = seg.end_idx
        peak_idx = seg.peak_idx

        seg_time_abs = time_data[start_idx : end_idx + 1]
        seg_time = seg_time_abs - seg_time_abs[0]
        seg_pos = position_data[start_idx : end_idx + 1]
        seg_force = force_data[start_idx : end_idx + 1]

        if len(seg_time) < 10:
            continue

        metrics = calculator.calculate_from_arrays(
            time_data=seg_time,
            position_data=seg_pos,
            force_data=seg_force,
            layer_number=seg.layer_number,
        )

        baseline = float(metrics.get("baseline_force", 0.0))

        # Map calculator-relative indices/times back to global indices.
        prop_end_global_idx = time_to_global_index(
            relative_time_s=float(metrics.get("propagation_end_time", 0.0)),
            seg_time_s=seg_time,
            global_start_idx=start_idx,
        )
        prop_end_global_idx = int(np.clip(prop_end_global_idx, start_idx, end_idx))

        pre_init_global_idx = time_to_global_index(
            relative_time_s=float(metrics.get("pre_initiation_time", 0.0)),
            seg_time_s=seg_time,
            global_start_idx=start_idx,
        )
        pre_init_global_idx = int(np.clip(pre_init_global_idx, start_idx, peak_idx))

        lift_start_idx = detect_lift_start_idx(force_data, baseline, start_idx, peak_idx)
        lift_start_idx = int(np.clip(lift_start_idx, start_idx, peak_idx))

        corrected_force = force_data - baseline

        potential_energy_j = integrate_force_displacement_joule(
            position_mm=position_data[lift_start_idx : peak_idx + 1],
            corrected_force_n=corrected_force[lift_start_idx : peak_idx + 1],
        )
        release_energy_j = integrate_force_displacement_joule(
            position_mm=position_data[peak_idx : prop_end_global_idx + 1],
            corrected_force_n=corrected_force[peak_idx : prop_end_global_idx + 1],
        )

        area_m2 = folder_meta.contact_area_mm2 * 1e-6
        critical_energy_release_rate_j_m2 = np.nan
        if area_m2 > 0:
            critical_energy_release_rate_j_m2 = release_energy_j / area_m2

        record = {
            "csv_file": csv_path.name,
            "window_type": folder_meta.window_type,
            "contact_area_mm2": folder_meta.contact_area_mm2,
            "layer_number": seg.layer_number,
            "layer_start_idx": start_idx,
            "layer_end_idx": end_idx,
            "lift_start_time_s": float(time_data[lift_start_idx]),
            "pre_initiation_time_s": float(time_data[pre_init_global_idx]),
            "peak_time_s": float(time_data[peak_idx]),
            "propagation_end_time_s": float(time_data[prop_end_global_idx]),
            "peak_force_N": float(metrics.get("peak_force", 0.0)),
            "baseline_force_N": baseline,
            "work_of_adhesion_corrected_mJ": float(metrics.get("work_of_adhesion_corrected_mJ", 0.0)),
            "potential_energy_mJ": potential_energy_j * 1000.0,
            "critical_energy_release_rate_J_per_m2": float(critical_energy_release_rate_j_m2),
            "peak_to_prop_energy_mJ": release_energy_j * 1000.0,
            "pre_initiation_duration_s": float(metrics.get("pre_initiation_duration", 0.0)),
            "propagation_duration_s": float(metrics.get("propagation_duration", 0.0)),
            "total_peel_duration_s": float(metrics.get("total_peel_duration", 0.0)),
        }
        records.append(record)

        layer_plot_data.append(
            {
                "layer_number": seg.layer_number,
                "start_idx": start_idx,
                "end_idx": end_idx,
                "lift_start_idx": lift_start_idx,
                "pre_init_idx": pre_init_global_idx,
                "peak_idx": peak_idx,
                "prop_end_idx": prop_end_global_idx,
                "baseline_force": baseline,
                "potential_energy_mJ": potential_energy_j * 1000.0,
                "critical_energy_release_rate": float(critical_energy_release_rate_j_m2),
            }
        )

    records_df = pd.DataFrame(records)
    arrays = {"time": time_data, "force": force_data, "smoothed": smoothed_force}
    return records_df, arrays, layer_plot_data


def plot_file_analysis(
    csv_path: Path,
    output_png: Path,
    arrays: Dict[str, np.ndarray],
    layer_plot_data: Sequence[Dict[str, Any]],
    folder_meta: FolderMetadata,
) -> None:
    """Create and save per-file plot matching project visual conventions (2-column layout)."""
    matplotlib.use('Agg')
    
    time_data = arrays["time"]
    force_data = arrays["force"]
    smoothed = arrays["smoothed"]
    
    # Predefined color palette (matches analysis_plotter.py)
    layer_colors = ['red', 'blue', 'green', 'orange', 'purple', 'brown']
    
    n_layers = len(layer_plot_data)
    if n_layers == 0:
        print(f"    [SKIP PLOT] No layers for {csv_path.name}")
        return
    
    # Calculate grid layout
    total_plots = 1 + n_layers  # 1 overview + N layers
    rows_needed = (total_plots + 1) // 2  # 2-column layout
    
    # Adaptive font sizing based on row count
    base_title_size, base_label_size = 16, 10
    if rows_needed <= 2:
        title_size, label_size = base_title_size, base_label_size
    elif rows_needed <= 3:
        title_size, label_size = base_title_size - 2, base_label_size - 1
    else:
        title_size, label_size = base_title_size - 4, base_label_size - 2
    
    # Figure size adjusted for rows
    base_fig_size = (16, 12)
    fig_height = base_fig_size[1] * (rows_needed / 2.0)
    
    # Create figure with GridSpec (2 columns)
    fig = plt.figure(figsize=(base_fig_size[0], fig_height), dpi=100)
    gs = fig.add_gridspec(rows_needed, 2)
    
    # Add peak/baseline info to layer_plot_data for reference
    for i, layer in enumerate(layer_plot_data):
        layer['color'] = layer_colors[i % len(layer_colors)]
    
    # ===== OVERVIEW PLOT =====
    ax_ov = fig.add_subplot(gs[0, 0])
    
    # Plot raw and smoothed force
    ax_ov.plot(time_data, force_data, 'k-', linewidth=1, alpha=0.4, label='Raw Force')
    ax_ov.plot(time_data, smoothed, 'navy', linewidth=2.5, alpha=0.9, label='Smoothed Force')
    
    # Add layer regions and annotations
    for layer in layer_plot_data:
        color = layer['color']
        s, e = int(layer['start_idx']), int(layer['end_idx'])
        p = int(layer['peak_idx'])
        
        # Layer region shading
        ax_ov.axvspan(time_data[s], time_data[e], alpha=0.08, color=color)
        
        # Peak marker and line
        peak_force = smoothed[p] if p < len(smoothed) else 0
        ax_ov.plot(time_data[p], peak_force, 'o', color=color, markersize=12,
                  zorder=5, markeredgecolor='black', markeredgewidth=2)
        ax_ov.axvline(x=time_data[p], color=color, linestyle='--', linewidth=3, alpha=0.8, zorder=3)
        
        # Layer label
        ax_ov.annotate(f'L{int(layer["layer_number"])}', 
                      xy=(time_data[p], peak_force),
                      xytext=(0, 5), textcoords='offset points',
                      ha='center', va='bottom', fontsize=label_size+2, fontweight='bold',
                      color=color, zorder=6)
    
    ax_ov.set_xlabel('Time (s)', fontsize=label_size+2, fontweight='bold')
    ax_ov.set_ylabel('Force (N)', fontsize=label_size+2, fontweight='bold')
    ax_ov.set_title('Complete Force Profile', fontsize=label_size+4, fontweight='bold')
    ax_ov.grid(True, alpha=0.3)
    ax_ov.legend(fontsize=label_size, loc='upper right')
    
    # ===== INDIVIDUAL LAYER PLOTS =====
    subplot_positions = [gs[0, 1]]
    for row in range(1, rows_needed):
        subplot_positions.append(gs[row, 0])
        if len(subplot_positions) < n_layers:
            subplot_positions.append(gs[row, 1])
    
    for i, layer in enumerate(layer_plot_data):
        if i >= len(subplot_positions):
            break
        
        ax = fig.add_subplot(subplot_positions[i])
        color = layer['color']
        
        s, e = int(layer['start_idx']), int(layer['end_idx'])
        ls = int(layer['lift_start_idx'])
        p = int(layer['peak_idx'])
        pe = int(layer['prop_end_idx'])
        baseline = float(layer['baseline_force'])
        
        # Define windowed region with 1.0s buffer
        buffer_time = 1.0
        window_start_time = max(time_data[ls] - buffer_time, time_data[s])
        window_end_time = min(time_data[pe] + buffer_time, time_data[e])
        
        window_start = np.argmin(np.abs(time_data - window_start_time))
        window_end = np.argmin(np.abs(time_data - window_end_time))
        
        window_time = time_data[window_start:window_end+1]
        window_force = force_data[window_start:window_end+1]
        window_smoothed = smoothed[window_start:window_end+1]
        
        # Plot force data
        ax.plot(window_time, window_force, 'k-', linewidth=1, alpha=0.4, label='Raw Force')
        ax.plot(window_time, window_smoothed, color=color, linewidth=3.5, alpha=0.95,
               label='Smoothed Force', zorder=3)
        
        # Peeling stage shading
        ax.axvspan(time_data[ls], time_data[p], color='lightblue', alpha=0.5,
                  label='Pre-Initiation', zorder=1)
        ax.axvspan(time_data[p], time_data[pe], color='lightcoral', alpha=0.5,
                  label='Propagation', zorder=1)
        
        # Vertical lines and markers
        ax.axvline(x=time_data[p], color=color, linestyle='--', linewidth=4, zorder=4)
        peak_force = smoothed[p] if p < len(smoothed) else baseline
        ax.plot(time_data[p], peak_force, 'o', color=color, markersize=14,
               zorder=5, markeredgecolor='black', markeredgewidth=2,
               label=f'Peak: {peak_force:.4f}N')
        
        ax.axvline(x=time_data[pe], color='purple', linestyle=':', linewidth=4, zorder=4)
        prop_force = smoothed[pe] if pe < len(smoothed) else baseline
        ax.plot(time_data[pe], prop_force, 's', color='purple', markersize=10,
               zorder=5, markeredgecolor='black', markeredgewidth=1, label='Prop End')
        
        # Baseline
        ax.axhline(y=baseline, color='gray', linestyle='--', linewidth=3, alpha=0.6,
                  label=f'Baseline: {baseline:.4f}N', zorder=2)
        
        # Formatting
        ax.set_xlabel('Time (s)', fontsize=label_size+1, fontweight='bold')
        ax.set_ylabel('Force (N)', fontsize=label_size+1, fontweight='bold')
        ax.set_title(f'Layer {int(layer["layer_number"])} - Peeling Stages',
                    fontsize=label_size+3, fontweight='bold', color=color)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=label_size-1, loc='upper left', framealpha=0.9)
        
        # Set axis limits
        y_min = baseline - 0.045
        y_max = peak_force + 0.015
        ax.set_ylim(y_min, y_max)
        
        x_margin = (time_data[pe] - time_data[ls]) * 0.3
        ax.set_xlim(time_data[ls] - x_margin, time_data[pe] + x_margin)
    
    # Main title
    fig.suptitle(f'{csv_path.name}\nPeeling Stages with Shaded Bands and Event Markers',
                fontsize=title_size, fontweight='bold', y=0.98)
    
    # Adjust layout
    plt.tight_layout()
    plt.subplots_adjust(top=0.90, bottom=0.08, hspace=0.4, wspace=0.3)
    
    # Save
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(output_png), dpi=100, bbox_inches='tight', facecolor='white')
    print(f"    [PLOT] Saved: {output_png.name}")
    plt.close(fig)


def plot_second_derivative_diagnostics(
    csv_path: Path,
    output_png: Path,
    arrays: Dict[str, np.ndarray],
    layer_plot_data: Sequence[Dict[str, Any]],
    calculator: AdhesionMetricsCalculator,
) -> None:
    """Create a per-file diagnostic plot of smoothed second derivative by layer."""
    time_data = arrays["time"]
    smoothed = arrays["smoothed"]

    n_layers = len(layer_plot_data)
    if n_layers == 0:
        print(f"    [SKIP PLOT] No second-derivative diagnostics for {csv_path.name}")
        return

    fig, axes = plt.subplots(n_layers, 1, figsize=(14, max(3.0 * n_layers, 4.0)), sharex=False)
    if not isinstance(axes, np.ndarray):
        axes = np.array([axes])

    sd_sigma = float(getattr(calculator, "prop_end_second_derivative_sigma", 0.0) or 0.0)

    for i, layer in enumerate(layer_plot_data):
        ax = axes[i]

        s = int(layer["start_idx"])
        e = int(layer["end_idx"])
        p = int(layer["peak_idx"])
        pe = int(layer["prop_end_idx"])
        layer_num = int(layer["layer_number"])

        # Use the full detected layer window for diagnostics.
        local_smoothed = smoothed[s : e + 1]
        local_time = time_data[s : e + 1]

        if len(local_smoothed) < 5:
            ax.text(0.5, 0.5, f"Layer {layer_num}: insufficient points for derivative",
                    transform=ax.transAxes, ha="center", va="center")
            ax.set_title(f"Layer {layer_num} - Second Derivative")
            ax.grid(alpha=0.3)
            continue

        second_derivative = np.gradient(np.gradient(local_smoothed))
        if sd_sigma > 0:
            second_derivative = gaussian_filter1d(second_derivative, sigma=sd_sigma)

        ax.plot(local_time, second_derivative, color="black", linewidth=1.8, label="Smoothed 2nd Derivative")
        ax.axhline(0.0, color="gray", linestyle="--", linewidth=1.0, alpha=0.7)

        peak_time = time_data[p]
        prop_end_time = time_data[pe]
        ax.axvline(peak_time, color="tab:blue", linestyle="--", linewidth=2.0, label="Peak")
        ax.axvline(prop_end_time, color="tab:red", linestyle=":", linewidth=2.5, label="Propagation End")

        mode = str(getattr(calculator, "prop_end_mode", "reverse_search"))
        ax.set_title(f"Layer {layer_num} - 2nd Derivative (mode={mode})", fontsize=11, fontweight="bold")
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("d2F/dt2")
        ax.grid(alpha=0.3)
        ax.legend(loc="upper right", fontsize=9)

    fig.suptitle(f"{csv_path.name}\nPropagation-End Diagnostic: Smoothed Second Derivative", fontsize=13, fontweight="bold")
    plt.tight_layout(rect=(0, 0, 1, 0.97))

    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(output_png), dpi=120, bbox_inches="tight", facecolor="white")
    print(f"    [PLOT] Saved: {output_png.name}")
    plt.close(fig)


def plot_second_derivative_unsmoothed(
    csv_path: Path,
    output_png: Path,
    arrays: Dict[str, np.ndarray],
    layer_plot_data: Sequence[Dict[str, Any]],
    calculator: AdhesionMetricsCalculator,
) -> None:
    """Create a per-file diagnostic plot of unsmoothed second derivative by layer."""
    time_data = arrays["time"]
    smoothed = arrays["smoothed"]

    n_layers = len(layer_plot_data)
    if n_layers == 0:
        print(f"    [SKIP PLOT] No unsmoothed second-derivative diagnostics for {csv_path.name}")
        return

    fig, axes = plt.subplots(n_layers, 1, figsize=(14, max(3.0 * n_layers, 4.0)), sharex=False)
    if not isinstance(axes, np.ndarray):
        axes = np.array([axes])

    for i, layer in enumerate(layer_plot_data):
        ax = axes[i]

        s = int(layer["start_idx"])
        e = int(layer["end_idx"])
        p = int(layer["peak_idx"])
        pe = int(layer["prop_end_idx"])
        layer_num = int(layer["layer_number"])

        # Use the full detected layer window for diagnostics.
        local_smoothed = smoothed[s : e + 1]
        local_time = time_data[s : e + 1]

        if len(local_smoothed) < 5:
            ax.text(0.5, 0.5, f"Layer {layer_num}: insufficient points for derivative",
                    transform=ax.transAxes, ha="center", va="center")
            ax.set_title(f"Layer {layer_num} - Unsmoothed 2nd Derivative")
            ax.grid(alpha=0.3)
            continue

        # Compute second derivative WITHOUT smoothing (unlike the diagnostics plot)
        second_derivative = np.gradient(np.gradient(local_smoothed))

        # Crop time range to 1 second before peak to 5 seconds after peak
        peak_time = time_data[p]
        crop_start_time = peak_time - 1.0
        crop_end_time = peak_time + 5.0
        
        crop_start_idx = np.argmin(np.abs(local_time - crop_start_time))
        crop_end_idx = np.argmin(np.abs(local_time - crop_end_time))
        
        cropped_time = local_time[crop_start_idx:crop_end_idx+1]
        cropped_deriv = second_derivative[crop_start_idx:crop_end_idx+1]

        ax.plot(cropped_time, cropped_deriv, color="black", linewidth=1.8, label="Unsmoothed 2nd Derivative")
        ax.axhline(0.0, color="gray", linestyle="--", linewidth=1.0, alpha=0.7)

        prop_end_time = time_data[pe]
        ax.axvline(peak_time, color="tab:blue", linestyle="--", linewidth=2.0, label="Peak")
        ax.axvline(prop_end_time, color="tab:red", linestyle=":", linewidth=2.5, label="Propagation End")

        mode = str(getattr(calculator, "prop_end_mode", "reverse_search"))
        ax.set_title(f"Layer {layer_num} - Unsmoothed 2nd Derivative (mode={mode})", fontsize=11, fontweight="bold")
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("d2F/dt2 (raw)")
        ax.grid(alpha=0.3)
        ax.legend(loc="upper right", fontsize=9)

    fig.suptitle(f"{csv_path.name}\nPropagation-End Diagnostic: Unsmoothed Second Derivative", fontsize=13, fontweight="bold")
    plt.tight_layout(rect=(0, 0, 1, 0.97))

    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(output_png), dpi=120, bbox_inches="tight", facecolor="white")
    print(f"    [PLOT] Saved: {output_png.name}")
    plt.close(fig)


def run_batch_analysis(root_dir: Path, output_dir: Path, default_contact_area_mm2: float) -> None:
    """Main batch routine."""
    calculator = AdhesionMetricsCalculator(
        smoothing_sigma=0.5,
        baseline_threshold_factor=0.002,
        min_peak_height=0.01,
        min_peak_distance=50,
        prop_end_mode='second_derivative_zero_crossing',
        prop_end_peak_fraction=0.02,
        prop_end_baseline_window_points=50,
        prop_end_sustain_points=3,
        prop_end_min_relative_distance=0.0,
        prop_end_second_derivative_sigma=3.0,
        prop_end_prominence_sigma=2.5,
        prop_end_min_abs_prominence=1e-5,
    )

    root_dir_resolved = root_dir.resolve()
    output_dir_resolved = output_dir.resolve()

    # Guard against using the same directory for both input and output.
    # In that case every candidate file appears under output_dir and gets filtered out.
    if output_dir_resolved == root_dir_resolved:
        output_dir = root_dir / "manuscript_analysis_output"
        output_dir_resolved = output_dir.resolve()
        print(
            "[Output Adjusted] --output-dir matched root_dir. "
            f"Writing results to: {output_dir_resolved}"
        )

    # Clean previous generated outputs to keep runs comparable and avoid stale files.
    if output_dir.exists():
        for pattern in ("*_analysis.png", "*_second_derivative_unsmoothed.png", "*_second_derivative.png", "*_layer_metrics.csv", "manuscript_layer_summary.csv"):
            for stale_file in output_dir.rglob(pattern):
                try:
                    stale_file.unlink()
                except OSError:
                    pass

        # Remove empty directories left after deleting stale artifacts.
        for directory in sorted(
            (p for p in output_dir.rglob("*") if p.is_dir()),
            key=lambda p: len(p.parts),
            reverse=True,
        ):
            try:
                directory.rmdir()
            except OSError:
                pass

    candidate_files = sorted(root_dir.rglob("autolog_*.csv"))
    csv_files = [
        p
        for p in candidate_files
        if output_dir_resolved not in p.resolve().parents and not p.name.endswith("_layer_metrics.csv")
    ]

    if not csv_files:
        print(f"No autolog files found under: {root_dir}")
        return

    print(f"Found {len(csv_files)} autolog files")
    combined_rows: List[pd.DataFrame] = []

    for csv_path in csv_files:
        rel_parent = csv_path.parent.relative_to(root_dir)
        folder_meta = parse_folder_metadata(csv_path.parent.name, default_contact_area_mm2)

        if abs(folder_meta.contact_area_mm2 - default_contact_area_mm2) > 1e-9:
            print(
                f"[Area Note] {csv_path.parent.name}: using parsed area "
                f"{folder_meta.contact_area_mm2:.3f} mm^2 (default {default_contact_area_mm2:.3f} mm^2)"
            )

        try:
            records_df, arrays, layer_plot_data = analyze_single_file(
                csv_path=csv_path,
                calculator=calculator,
                folder_meta=folder_meta,
            )

            out_subdir = output_dir / rel_parent
            out_subdir.mkdir(parents=True, exist_ok=True)

            plot_path = out_subdir / f"{csv_path.stem}_analysis.png"
            plot_file_analysis(
                csv_path=csv_path,
                output_png=plot_path,
                arrays=arrays,
                layer_plot_data=layer_plot_data,
                folder_meta=folder_meta,
            )

            sd_unsmoothed_path = out_subdir / f"{csv_path.stem}_second_derivative_unsmoothed.png"
            plot_second_derivative_unsmoothed(
                csv_path=csv_path,
                output_png=sd_unsmoothed_path,
                arrays=arrays,
                layer_plot_data=layer_plot_data,
                calculator=calculator,
            )

            per_file_csv = out_subdir / f"{csv_path.stem}_layer_metrics.csv"
            records_df.to_csv(per_file_csv, index=False)

            if not records_df.empty:
                records_df.insert(0, "source_subfolder", str(rel_parent))
                combined_rows.append(records_df)

            print(
                f"Processed {csv_path.name}: layers={len(records_df)} | "
                f"plot={plot_path.name} | metrics={per_file_csv.name}"
            )

        except Exception as exc:
            print(f"[ERROR] Failed {csv_path}: {exc}")

    summary_path = output_dir / "manuscript_layer_summary.csv"
    output_dir.mkdir(parents=True, exist_ok=True)

    if combined_rows:
        summary_df = pd.concat(combined_rows, ignore_index=True)
        summary_df.to_csv(summary_path, index=False)
        print(f"\nWrote combined summary: {summary_path}")
    else:
        print("\nNo layer metrics were generated; combined summary not written.")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Batch manuscript autolog analyzer")
    parser.add_argument(
        "root_dir",
        type=Path,
        help="Root directory containing WindowType_ContactArea subfolders with autolog files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory for plots/CSVs (default: <root_dir>/manuscript_analysis_output).",
    )
    parser.add_argument(
        "--default-contact-area-mm2",
        type=float,
        default=DEFAULT_CONTACT_AREA_MM2,
        help=f"Fallback contact area in mm^2 (default: {DEFAULT_CONTACT_AREA_MM2}).",
    )
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    root_dir: Path = args.root_dir.resolve()
    if not root_dir.exists():
        raise FileNotFoundError(f"Root directory does not exist: {root_dir}")

    output_dir = args.output_dir.resolve() if args.output_dir else (root_dir / "manuscript_analysis_output")

    run_batch_analysis(
        root_dir=root_dir,
        output_dir=output_dir,
        default_contact_area_mm2=float(args.default_contact_area_mm2),
    )


if __name__ == "__main__":
    main()
