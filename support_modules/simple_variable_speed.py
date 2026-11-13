# -*- coding: utf-8 -*-
"""Simple Variable Speed schedule generator for Prince continuous prints.

Computes per-layer Z speed from max external Euclidean distance (EDT) on raw
slice masks, couples LED PWM to hold unitless dose (Time * PWM) constant, and
rewrites only Time/Intensity columns in the existing Prince instruction .txt.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence, Tuple, Union

import numpy as np

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None

try:
    from scipy import ndimage as ndi
except ImportError:  # pragma: no cover
    ndi = None


PX_PITCH_MM = 0.004005
BINARY_THRESHOLD = 127
PWM_SOFT_WARN_FLOOR = 5
# Parallel workers for per-layer EDT (I/O + OpenCV release the GIL).
_DEFAULT_EDT_WORKERS = max(2, min(8, (os.cpu_count() or 4)))


PathLike = Union[str, Path]


def _require_edt_backend() -> None:
    if cv2 is None and ndi is None:  # pragma: no cover
        raise ImportError(
            "Simple Variable Speed needs OpenCV (cv2) or scipy.ndimage for EDT."
        )


def _edt_px(feature_mask: np.ndarray) -> np.ndarray:
    """Euclidean distance (px) from each True pixel to the nearest False pixel."""
    _require_edt_backend()
    mask = np.ascontiguousarray(feature_mask.astype(bool))
    if cv2 is not None:
        # OpenCV: nonzero → distance to nearest zero. Much faster than scipy on large frames.
        return cv2.distanceTransform(
            mask.astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_PRECISE
        )
    return ndi.distance_transform_edt(mask)  # type: ignore[union-attr]


def _label_components(binary: np.ndarray) -> Tuple[np.ndarray, int]:
    """8-connected labels; return (labels, n_labels) with 0 = background."""
    _require_edt_backend()
    u8 = np.ascontiguousarray(binary.astype(bool).astype(np.uint8))
    if cv2 is not None:
        n_labels, labels = cv2.connectedComponents(u8, connectivity=8)
        return labels, int(n_labels) - 1  # exclude background
    structure = np.ones((3, 3), dtype=int)
    labeled, n = ndi.label(u8, structure=structure)  # type: ignore[union-attr]
    return labeled, int(n)


def _content_bbox(mask: np.ndarray, margin: int = 2) -> Tuple[slice, slice]:
    """Tight row/col slices around True pixels, plus margin (clamped to bounds)."""
    ys, xs = np.nonzero(mask)
    if len(ys) == 0:
        return slice(0, mask.shape[0]), slice(0, mask.shape[1])
    r0 = max(0, int(ys.min()) - margin)
    r1 = min(mask.shape[0], int(ys.max()) + 1 + margin)
    c0 = max(0, int(xs.min()) - margin)
    c1 = min(mask.shape[1], int(xs.max()) + 1 + margin)
    return slice(r0, r1), slice(c0, c1)


@dataclass
class LayerScheduleRow:
    layer_index: int  # 1-based
    file_name: str
    thickness_um: float
    z_height_mm: float
    d_max_mm: float
    radius_ratio: float
    speed_um_s: float
    time_s: float
    pwm: int
    white_pixel_count: int
    pwm_below_floor: bool


@dataclass
class ScheduleResult:
    rows: List[LayerScheduleRow]
    control_speed_um_s: float
    control_dose: float
    control_size_mm: float
    correction: float
    any_pwm_below_floor: bool

    @property
    def times_s(self) -> List[float]:
        return [r.time_s for r in self.rows]

    @property
    def pwms(self) -> List[int]:
        return [r.pwm for r in self.rows]

    @property
    def speeds_um_s(self) -> List[float]:
        return [r.speed_um_s for r in self.rows]

    @property
    def z_mm(self) -> List[float]:
        return [r.z_height_mm for r in self.rows]

    @property
    def d_max_mm(self) -> List[float]:
        return [r.d_max_mm for r in self.rows]


def load_binary_mask(image_path: PathLike, threshold: int = BINARY_THRESHOLD) -> np.ndarray:
    """Load a slice image as a boolean white mask."""
    path = Path(image_path)
    if cv2 is not None:
        img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise FileNotFoundError(f"Could not read image: {path}")
    else:  # pragma: no cover
        from PIL import Image

        img = np.array(Image.open(path).convert("L"))
    return img >= int(threshold)


def _border_connected_labels(labeled: np.ndarray) -> set:
    """Labels that touch the image border (exterior resin)."""
    border = np.unique(
        np.concatenate(
            [
                labeled[0, :],
                labeled[-1, :],
                labeled[:, 0],
                labeled[:, -1],
            ]
        )
    )
    return {int(v) for v in border if v != 0}


def fill_holes_by_max_ecd(
    white_mask: np.ndarray,
    max_hole_mm: float,
    px_pitch_mm: float = PX_PITCH_MM,
) -> np.ndarray:
    """Fill enclosed black holes whose max ECD-to-white is <= max_hole_mm.

    Hole size for a component = max Euclidean distance from any black pixel
    in that hole to the nearest white pixel (mm).
    """
    if max_hole_mm < 0:
        raise ValueError("max_hole_mm must be >= 0")

    # Work on a content crop — full 2560×1600 EDT is unnecessary for small parts.
    white_full = white_mask.astype(bool)
    rows, cols = _content_bbox(white_full, margin=4)
    white = white_full[rows, cols]

    padded = np.pad(white, pad_width=1, mode="constant", constant_values=False)
    black = ~padded
    labeled, n_labels = _label_components(black)
    if n_labels == 0:
        return white_full.copy()

    exterior = _border_connected_labels(labeled)
    edt_to_white_mm = _edt_px(black) * float(px_pitch_mm)

    filled_padded = padded.copy()
    # Vectorized per-label max via np.maximum.at is awkward; labels are few.
    for lab in range(1, n_labels + 1):
        if lab in exterior:
            continue
        comp = labeled == lab
        if not np.any(comp):
            continue
        if float(np.max(edt_to_white_mm[comp])) <= float(max_hole_mm):
            filled_padded[comp] = True

    filled_crop = filled_padded[1:-1, 1:-1]
    out = white_full.copy()
    out[rows, cols] = filled_crop
    return out


def compute_dmax_mm(
    mask: np.ndarray,
    px_pitch_mm: float = PX_PITCH_MM,
    fill_holes: bool = False,
    max_hole_mm: float = 0.0,
) -> float:
    """Maximum external drainage distance (mm) over original white pixels.

    When fill_holes is True, enclosed black components with hole size
    (max ECD black→white) <= max_hole_mm are filled before the drainage EDT.
    """
    white = mask.astype(bool)
    if not np.any(white):
        return 0.0

    if fill_holes:
        filled = fill_holes_by_max_ecd(
            white, max_hole_mm=max_hole_mm, px_pitch_mm=px_pitch_mm
        )
    else:
        filled = white

    # Crop to content, then 1-px black pad so exterior is always connected.
    rows, cols = _content_bbox(filled | white, margin=2)
    filled_c = filled[rows, cols]
    white_c = white[rows, cols]
    filled_padded = np.pad(
        filled_c, pad_width=1, mode="constant", constant_values=False
    )
    edt = _edt_px(filled_padded)[1:-1, 1:-1] * float(px_pitch_mm)
    return float(np.max(edt[white_c]))


def analyze_layer_image(
    image_path: PathLike,
    fill_holes: bool = False,
    max_hole_mm: float = 0.0,
    px_pitch_mm: float = PX_PITCH_MM,
    threshold: int = BINARY_THRESHOLD,
) -> Tuple[float, int]:
    """Return (d_max_mm, white_pixel_count) for one slice path."""
    mask = load_binary_mask(image_path, threshold=threshold)
    white_count = int(np.count_nonzero(mask))
    if white_count == 0:
        return 0.0, 0
    d_max = compute_dmax_mm(
        mask,
        px_pitch_mm=px_pitch_mm,
        fill_holes=fill_holes,
        max_hole_mm=max_hole_mm,
    )
    return d_max, white_count


def analyze_layers_parallel(
    image_paths: Sequence[PathLike],
    fill_holes: bool = False,
    max_hole_mm: float = 0.0,
    px_pitch_mm: float = PX_PITCH_MM,
    max_workers: int = _DEFAULT_EDT_WORKERS,
    progress_callback=None,
) -> Tuple[np.ndarray, np.ndarray]:
    """Parallel per-layer EDT. Returns (d_max_mm[n], white_counts[n])."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    n = len(image_paths)
    d_max = np.zeros(n, dtype=float)
    white = np.zeros(n, dtype=int)
    if n == 0:
        return d_max, white

    def _one(idx_path):
        idx, path = idx_path
        return idx, analyze_layer_image(
            path,
            fill_holes=fill_holes,
            max_hole_mm=max_hole_mm,
            px_pitch_mm=px_pitch_mm,
        )

    workers = max(1, min(int(max_workers), n))
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_one, (i, p)) for i, p in enumerate(image_paths)]
        for fut in as_completed(futures):
            idx, (d, w) = fut.result()
            d_max[idx] = d
            white[idx] = w
            done += 1
            if progress_callback is not None:
                progress_callback(done, n)
    return d_max, white


def compute_speed_um_s(
    d_max_mm: float,
    control_size_mm: float,
    control_speed_um_s: float,
    correction: float,
) -> float:
    """Simple β=4 speed law with correction factor c on the penalty term."""
    if control_size_mm <= 0:
        raise ValueError("control_size_mm must be > 0")
    if control_speed_um_s <= 0:
        raise ValueError("control_speed_um_s must be > 0")
    if correction < 0:
        raise ValueError("correction must be >= 0")

    if d_max_mm <= 0:
        return float(control_speed_um_s)

    r_tilde = float(d_max_mm) / float(control_size_mm)
    penalty = max(0.0, (r_tilde ** 4) - 1.0)
    speed = float(control_speed_um_s) / (1.0 + float(correction) * penalty)
    return min(speed, float(control_speed_um_s))


def compute_layer_pwm(
    speed_um_s: float,
    control_speed_um_s: float,
    control_dose: float,
    thickness_um: float,
    white_pixel_count: int,
) -> Tuple[int, float]:
    """Return (pwm, time_s) for one layer. Empty layers: pwm=0, time at control speed."""
    if thickness_um <= 0:
        raise ValueError("thickness_um must be > 0")
    if control_speed_um_s <= 0:
        raise ValueError("control_speed_um_s must be > 0")

    if white_pixel_count <= 0:
        time_s = float(thickness_um) / float(control_speed_um_s)
        return 0, time_s

    # PWM_ctrl = dose * v0 / thickness  (dose = time * PWM, time = thickness / v)
    pwm_ctrl = float(control_dose) * float(control_speed_um_s) / float(thickness_um)
    speed = max(float(speed_um_s), 1e-12)
    time_s = float(thickness_um) / speed
    pwm = int(round(pwm_ctrl * (speed / float(control_speed_um_s))))
    pwm = int(np.clip(pwm, 0, 255))
    if pwm < 1:
        pwm = 1
    return pwm, time_s


def instruction_txt_path(folder: PathLike) -> Path:
    folder = Path(folder)
    return folder / f"{folder.name}.txt"


def read_instruction_file(txt_path: PathLike) -> Tuple[List[str], List[List[str]]]:
    """Return (header_cells or empty, data rows as list of 10+ string cells)."""
    path = Path(txt_path)
    if not path.is_file():
        raise FileNotFoundError(f"Instruction file not found: {path}")
    lines = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not lines:
        raise ValueError(f"Instruction file is empty: {path}")
    header = lines[0].split("\t")
    rows: List[List[str]] = []
    for line in lines[1:]:
        cells = line.split("\t")
        if len(cells) < 10:
            raise ValueError(
                f"Incorrect format in line: {line}. Expected >= 10 columns, got {len(cells)}."
            )
        rows.append(cells)
    return header, rows


def rewrite_instruction_times_intensities(
    txt_path: PathLike,
    times_s: Sequence[float],
    pwms: Sequence[int],
) -> Path:
    """Overwrite Time (col 3) and Intensity (col 4); preserve all other columns."""
    path = Path(txt_path)
    header, rows = read_instruction_file(path)
    if len(times_s) != len(rows) or len(pwms) != len(rows):
        raise ValueError(
            f"Schedule length ({len(times_s)}) does not match instruction rows ({len(rows)})."
        )

    out_lines = ["\t".join(header)]
    for cells, t_s, pwm in zip(rows, times_s, pwms):
        new_cells = list(cells)
        new_cells[3] = f"{float(t_s):.6f}"
        new_cells[4] = str(int(pwm))
        out_lines.append("\t".join(new_cells))

    text = "\n".join(out_lines) + "\n"
    directory = path.parent
    fd, tmp_name = tempfile.mkstemp(prefix=path.stem + "_", suffix=".tmp", dir=str(directory))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
    return path


def _read_gray(path: PathLike) -> np.ndarray:
    path = Path(path)
    if cv2 is not None:
        img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise FileNotFoundError(f"Could not read image: {path}")
        return img
    from PIL import Image  # pragma: no cover

    return np.array(Image.open(path).convert("L"))


def build_xz_preview(
    image_paths: Sequence[PathLike],
    threshold: int = BINARY_THRESHOLD,
) -> np.ndarray:
    """Stack mid-row (H//2) of every layer into an XZ image (layers x width)."""
    rows: List[np.ndarray] = []
    width = None
    for p in image_paths:
        img = _read_gray(p)
        h, w = img.shape
        if width is None:
            width = w
        elif w != width:
            if w < width:
                pad = np.zeros((h, width), dtype=img.dtype)
                pad[:, :w] = img
                img = pad
            else:
                img = img[:, :width]
        y = h // 2
        rows.append(img[y, :].astype(np.uint8))
    if not rows:
        return np.zeros((0, 0), dtype=np.uint8)
    return np.vstack(rows)


def build_yz_preview(
    image_paths: Sequence[PathLike],
    threshold: int = BINARY_THRESHOLD,
) -> np.ndarray:
    """Stack a vertical column of every layer into a YZ image (layers x height).

    Prefers x = W//2. If that column is empty for the whole stack, uses the
    densest column (same fallback as the diagnostic plots).
    """
    paths = [Path(p) for p in image_paths]
    if not paths:
        return np.zeros((0, 0), dtype=np.uint8)

    sample = _read_gray(paths[0])
    height, width = sample.shape
    mid = width // 2

    def stack_at(x: int) -> np.ndarray:
        cols: List[np.ndarray] = []
        h_ref = None
        for p in paths:
            img = _read_gray(p)
            h, w = img.shape
            xx = min(max(x, 0), w - 1)
            line = img[:, xx]
            if h_ref is None:
                h_ref = h
            elif h != h_ref:
                if h < h_ref:
                    pad = np.zeros(h_ref, dtype=line.dtype)
                    pad[:h] = line
                    line = pad
                else:
                    line = line[:h_ref]
            cols.append(line.astype(np.uint8))
        return np.vstack(cols)

    yz_mid = stack_at(mid)
    if np.count_nonzero(yz_mid >= int(threshold)) > 0:
        return yz_mid

    totals = np.zeros(width, dtype=np.int64)
    step = max(1, len(paths) // 40)
    for p in paths[::step]:
        img = _read_gray(p)
        totals[: img.shape[1]] += (img >= int(threshold)).sum(axis=0)
    return stack_at(int(np.argmax(totals)))


def compute_schedule_for_folder(
    folder: PathLike,
    control_speed_um_s: float,
    control_dose: float,
    control_size_mm: float,
    correction: float,
    fill_holes: bool = False,
    max_hole_mm: float = 0.0,
    px_pitch_mm: float = PX_PITCH_MM,
    progress_callback=None,
    max_workers: int = _DEFAULT_EDT_WORKERS,
) -> ScheduleResult:
    """Build a full schedule from the instruction file (parallel per-layer EDT)."""
    folder = Path(folder)
    txt_path = instruction_txt_path(folder)
    _header, rows = read_instruction_file(txt_path)

    paths = [folder / cells[1] for cells in rows]
    d_max_arr, white_arr = analyze_layers_parallel(
        paths,
        fill_holes=fill_holes,
        max_hole_mm=max_hole_mm,
        px_pitch_mm=px_pitch_mm,
        max_workers=max_workers,
        progress_callback=progress_callback,
    )

    schedule_rows: List[LayerScheduleRow] = []
    z_um = 0.0
    any_low = False

    for i, cells in enumerate(rows):
        file_name = cells[1]
        thickness_um = float(cells[2])
        d_max = float(d_max_arr[i])
        white_count = int(white_arr[i])
        speed = compute_speed_um_s(
            d_max_mm=d_max,
            control_size_mm=control_size_mm,
            control_speed_um_s=control_speed_um_s,
            correction=correction,
        )
        pwm, time_s = compute_layer_pwm(
            speed_um_s=speed,
            control_speed_um_s=control_speed_um_s,
            control_dose=control_dose,
            thickness_um=thickness_um,
            white_pixel_count=white_count,
        )
        z_um += thickness_um
        r_tilde = (d_max / control_size_mm) if control_size_mm > 0 else 0.0
        below = white_count > 0 and pwm < PWM_SOFT_WARN_FLOOR
        any_low = any_low or below
        schedule_rows.append(
            LayerScheduleRow(
                layer_index=i + 1,
                file_name=file_name,
                thickness_um=thickness_um,
                z_height_mm=z_um / 1000.0,
                d_max_mm=d_max,
                radius_ratio=r_tilde,
                speed_um_s=speed if white_count > 0 else control_speed_um_s,
                time_s=time_s,
                pwm=pwm,
                white_pixel_count=white_count,
                pwm_below_floor=below,
            )
        )

    return ScheduleResult(
        rows=schedule_rows,
        control_speed_um_s=float(control_speed_um_s),
        control_dose=float(control_dose),
        control_size_mm=float(control_size_mm),
        correction=float(correction),
        any_pwm_below_floor=any_low,
    )


def dmax_for_layer_file(
    folder: PathLike,
    layer_index_1based: int,
    fill_holes: bool = False,
    max_hole_mm: float = 0.0,
    px_pitch_mm: float = PX_PITCH_MM,
) -> float:
    """Compute d_max (mm) for a 1-based layer index from the instruction file."""
    folder = Path(folder)
    _header, rows = read_instruction_file(instruction_txt_path(folder))
    if layer_index_1based < 1 or layer_index_1based > len(rows):
        raise ValueError(
            f"Control layer {layer_index_1based} out of range (1–{len(rows)})."
        )
    file_name = rows[layer_index_1based - 1][1]
    mask = load_binary_mask(folder / file_name)
    return compute_dmax_mm(
        mask,
        px_pitch_mm=px_pitch_mm,
        fill_holes=fill_holes,
        max_hole_mm=max_hole_mm,
    )


def list_instruction_image_paths(folder: PathLike) -> List[Path]:
    folder = Path(folder)
    _header, rows = read_instruction_file(instruction_txt_path(folder))
    return [folder / cells[1] for cells in rows]
