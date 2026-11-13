# -*- coding: utf-8 -*-
"""Qt dialog: Simple Variable Speed schedule preview and apply."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, List, Optional, Tuple

import numpy as np
from PySide6.QtCore import QSize
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from support_modules import simple_variable_speed as svs

try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
    from matplotlib.figure import Figure
except ImportError:  # pragma: no cover
    try:
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
        from matplotlib.figure import Figure
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "matplotlib is required for the Simple Variable Speed dialog plots."
        ) from exc

try:
    from .theme import QSS
except ImportError:  # pragma: no cover
    QSS = ""


# Default dialog size: controls + plots with room for limits + C help text.
_DIALOG_WIDTH = 900
_DIALOG_HEIGHT = 720


class _BlankDoubleSpin(QDoubleSpinBox):
    """Spin box that starts empty."""

    def __init__(
        self,
        empty_value: float,
        maximum: float,
        decimals: int = 4,
        parent=None,
        *,
        value_minimum: Optional[float] = None,
    ):
        super().__init__(parent)
        self._empty = float(empty_value)
        self._value_minimum = (
            float(value_minimum) if value_minimum is not None else self._empty
        )
        self.setRange(self._empty, maximum)
        self.setDecimals(decimals)
        self.setSpecialValueText(" ")
        self.setValue(self._empty)
        self.lineEdit().clear()

    def has_value(self) -> bool:
        return self.value() > self._empty + 10 ** (-(self.decimals() + 1))

    def set_user_value(self, value: float) -> None:
        self.setValue(float(value))

    def valid_or_raise(self, label: str, *, allow_zero: bool = False) -> float:
        if not self.has_value():
            raise ValueError(f"{label} is required")
        val = float(self.value())
        if allow_zero:
            if val < self._value_minimum:
                raise ValueError(f"{label} must be >= {self._value_minimum}")
        elif val <= 0:
            raise ValueError(f"{label} must be > 0")
        return val


class SimpleVariableSpeedDialog(QDialog):
    """YZ cross-section + speed-vs-Z schedule editor for continuous prints."""

    def __init__(
        self,
        folder: Path,
        parent: Optional[QWidget] = None,
        on_applied: Optional[Callable[[], None]] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Simple Variable Speed")
        self.setObjectName("modernRoot")
        self.setStyleSheet(
            (QSS or "")
            + """
            QGroupBox {
                color: #F2F2F5;
                border: 1px solid #3A4152;
                border-radius: 8px;
                margin-top: 10px;
                background-color: #1F2130;
                font-weight: 600;
                font-size: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
                color: #C8B8DC;
            }
            QLineEdit, QComboBox, QPushButton, QSpinBox, QDoubleSpinBox {
                padding: 4px 8px;
                min-height: 14px;
            }
            """
        )
        self.resize(_DIALOG_WIDTH, _DIALOG_HEIGHT)
        self.setMinimumSize(780, 620)

        self.folder = Path(folder)
        self.on_applied = on_applied
        self._schedule: Optional[svs.ScheduleResult] = None

        self._cached_dmax: Optional[np.ndarray] = None
        self._cached_thickness_um: Optional[np.ndarray] = None
        self._cached_white: Optional[np.ndarray] = None
        self._cached_file_names: Optional[List[str]] = None
        self._cached_yz: Optional[np.ndarray] = None
        self._cached_fill_key: Optional[Tuple[bool, float]] = None

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(8)

        self.path_lbl = QLabel(f"Print folder: {self.folder}")
        self.path_lbl.setObjectName("muted")
        self.path_lbl.setWordWrap(True)
        root.addWidget(self.path_lbl)

        body = QHBoxLayout()
        body.setSpacing(10)
        controls = self._build_controls()
        controls.setFixedWidth(270)
        body.addWidget(controls, 0)
        body.addWidget(self._build_plots(), 1)
        root.addLayout(body, 1)

        self.status = QLabel("Enter control values, then Update or Apply.")
        self.status.setObjectName("muted")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        self.btn_update = QPushButton("Update")
        self.btn_update.setObjectName("primary")
        self.btn_update.setToolTip(
            "Recompute the schedule from the current control parameters and refresh plots."
        )
        self.btn_update.clicked.connect(self._on_update)
        self.btn_apply = QPushButton("Apply to instruction file")
        self.btn_apply.setObjectName("primary")
        self.btn_apply.clicked.connect(self._on_apply)
        self.btn_browse = QPushButton("Browse…")
        self.btn_browse.setToolTip("Select a different print folder.")
        self.btn_browse.clicked.connect(self._on_browse)
        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.reject)
        buttons.addWidget(self.btn_update)
        buttons.addWidget(self.btn_apply)
        buttons.addWidget(self.btn_browse)
        buttons.addStretch(1)
        buttons.addWidget(self.btn_close)
        root.addLayout(buttons)

        self._sync_hole_enable()

    def sizeHint(self) -> QSize:  # noqa: N802 — Qt API
        return QSize(_DIALOG_WIDTH, _DIALOG_HEIGHT)

    def _section(self, title: str) -> tuple[QGroupBox, QVBoxLayout]:
        box = QGroupBox(title)
        layout = QVBoxLayout(box)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(5)
        return box, layout

    def _labeled_field(self, label: str, widget: QWidget) -> QWidget:
        """Stack a field label above its control for narrow, readable columns."""
        wrap = QWidget()
        lay = QVBoxLayout(wrap)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        lbl = QLabel(label)
        lbl.setObjectName("muted")
        lbl.setWordWrap(True)
        lay.addWidget(lbl)
        lay.addWidget(widget)
        return wrap

    def _build_controls(self) -> QWidget:
        wrap = QWidget()
        col = QVBoxLayout(wrap)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(6)

        # --- Control layer ---
        box, lay = self._section("Control layer")
        self.btn_use_layer = QPushButton("Use control layer")
        self.btn_use_layer.setToolTip(
            "Measure d_max on the selected layer and write it into Size d_max."
        )
        self.btn_use_layer.clicked.connect(self._on_use_control_layer)
        lay.addWidget(self.btn_use_layer)

        self.control_layer = QSpinBox()
        self.control_layer.setRange(1, 1_000_000)
        self.control_layer.setValue(1)
        lay.addWidget(self._labeled_field("Control layer", self.control_layer))
        col.addWidget(box)

        # --- Parameter limits (2×2: LED Current / Speed × Min / Max) ---
        box, lay = self._section("Parameter limits")
        limits = QGridLayout()
        limits.setContentsMargins(0, 0, 0, 0)
        limits.setHorizontalSpacing(6)
        limits.setVerticalSpacing(4)

        hdr_min = QLabel("Min")
        hdr_min.setObjectName("muted")
        hdr_max = QLabel("Max")
        hdr_max.setObjectName("muted")
        limits.addWidget(QLabel(""), 0, 0)
        limits.addWidget(hdr_min, 0, 1)
        limits.addWidget(hdr_max, 0, 2)

        led_lbl = QLabel("LED Current")
        led_lbl.setObjectName("muted")
        led_lbl.setWordWrap(True)
        self.led_min = _BlankDoubleSpin(0.0, 255.0, decimals=0)
        self.led_max = _BlankDoubleSpin(0.0, 255.0, decimals=0)
        limits.addWidget(led_lbl, 1, 0)
        limits.addWidget(self.led_min, 1, 1)
        limits.addWidget(self.led_max, 1, 2)

        spd_lbl = QLabel("Speed (µm/s)")
        spd_lbl.setObjectName("muted")
        spd_lbl.setWordWrap(True)
        self.speed_min = _BlankDoubleSpin(0.0, 1_000_000.0, decimals=3)
        self.speed_max = _BlankDoubleSpin(0.0, 1_000_000.0, decimals=3)
        limits.addWidget(spd_lbl, 2, 0)
        limits.addWidget(self.speed_min, 2, 1)
        limits.addWidget(self.speed_max, 2, 2)

        limits.setColumnStretch(1, 1)
        limits.setColumnStretch(2, 1)
        lay.addLayout(limits)
        col.addWidget(box)

        # --- Manual control ---
        box, lay = self._section("Manual control")
        self.speed = _BlankDoubleSpin(0.0, 1_000_000.0, decimals=3)
        lay.addWidget(
            self._labeled_field("Control speed (µm/s)", self.speed)
        )

        self.dose = _BlankDoubleSpin(0.0, 1_000_000.0, decimals=6)
        lay.addWidget(
            self._labeled_field("Dose (layer time * LED Current)", self.dose)
        )

        self.correction = _BlankDoubleSpin(
            -1.0, 100.0, decimals=3, value_minimum=0.0
        )
        lay.addWidget(
            self._labeled_field("Correction Factor", self.correction)
        )

        help_c = QLabel(
            "C = correction factor\n"
            "0.0 = no correction\n"
            "1.0 = Default Stefan-Adhesion\n"
            "1.5 = 50% extra correction"
        )
        help_c.setObjectName("muted")
        help_c.setWordWrap(True)
        lay.addWidget(help_c)
        col.addWidget(box)

        # --- Fill holes (+ size reference) ---
        box, lay = self._section("Fill holes")
        self.size = _BlankDoubleSpin(0.0, 1000.0, decimals=4)
        self.size.setSuffix(" mm")
        lay.addWidget(self._labeled_field("Size d_max", self.size))

        # UI in µm; converted to mm for the EDT API.
        self.max_hole_um = _BlankDoubleSpin(
            -1.0, 1_000_000.0, decimals=1, value_minimum=0.0
        )
        lay.addWidget(
            self._labeled_field("Minimum hole size (µm)", self.max_hole_um)
        )
        self.fill_holes = QCheckBox("Enable")
        self.fill_holes.toggled.connect(self._sync_hole_enable)
        lay.addWidget(self.fill_holes)
        col.addWidget(box)

        col.addStretch(1)
        return wrap

    def _build_plots(self) -> QWidget:
        wrap = QFrame()
        wrap.setObjectName("card")
        wrap.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout = QHBoxLayout(wrap)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(0)

        # Compact figure — dialog height stays moderate with isotropic YZ.
        self.fig = Figure(figsize=(6.8, 3.6), facecolor="#1F2130")
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.canvas.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.ax_yz = None
        self.ax_speed = None
        self._reset_plot_axes()

        layout.addWidget(self.canvas, 1)
        return wrap

    def _style_axes(self, ax) -> None:
        ax.set_facecolor("#1A1B26")
        ax.tick_params(colors="#C0C0C8", labelsize=8)
        ax.xaxis.label.set_color("#E8E8EE")
        ax.yaxis.label.set_color("#E8E8EE")
        ax.title.set_color("#F2F2F5")
        for spine in ax.spines.values():
            spine.set_color("#3A4152")

    def _reset_plot_axes(self) -> None:
        self.fig.clear()
        self.fig.patch.set_facecolor("#1F2130")
        gs = self.fig.add_gridspec(
            1,
            2,
            width_ratios=[1.0, 1.15],
            left=0.11,
            right=0.98,
            top=0.90,
            bottom=0.14,
            wspace=0.26,
        )
        self.ax_yz = self.fig.add_subplot(gs[0, 0])
        self.ax_speed = self.fig.add_subplot(gs[0, 1])
        self.ax_speed.set_aspect("auto")
        self._style_axes(self.ax_yz)
        self._style_axes(self.ax_speed)

    def _sync_hole_enable(self) -> None:
        self.max_hole_um.setEnabled(self.fill_holes.isChecked())
        self._cached_fill_key = None

    def _hole_size_mm(self) -> float:
        """Convert UI µm threshold to mm for the EDT API."""
        if not self.fill_holes.isChecked():
            return 0.0
        return self.max_hole_um.valid_or_raise(
            "Minimum hole size (µm)", allow_zero=True
        ) / 1000.0

    def _optional_limit(
        self, spin: _BlankDoubleSpin, label: str
    ) -> Optional[float]:
        if not spin.has_value():
            return None
        return spin.valid_or_raise(label, allow_zero=True)

    def _read_params(self) -> dict:
        speed = self.speed.valid_or_raise("Control speed (µm/s)")
        dose = self.dose.valid_or_raise("Dose (layer time * LED Current)")
        size = self.size.valid_or_raise("Size d_max")
        correction = self.correction.valid_or_raise(
            "Correction Factor", allow_zero=True
        )
        fill = bool(self.fill_holes.isChecked())
        max_hole = self._hole_size_mm() if fill else 0.0

        led_min = self._optional_limit(self.led_min, "LED Current min")
        led_max = self._optional_limit(self.led_max, "LED Current max")
        speed_min = self._optional_limit(self.speed_min, "Speed min (µm/s)")
        speed_max = self._optional_limit(self.speed_max, "Speed max (µm/s)")

        if led_min is not None and led_max is not None and led_min > led_max:
            raise ValueError("LED Current min must be ≤ max")
        if (
            speed_min is not None
            and speed_max is not None
            and speed_min > speed_max
        ):
            raise ValueError("Speed min must be ≤ max")

        return {
            "control_speed_um_s": speed,
            "control_dose": dose,
            "control_size_mm": size,
            "correction": correction,
            "fill_holes": fill,
            "max_hole_mm": max_hole,
            "led_min": led_min,
            "led_max": led_max,
            "speed_min": speed_min,
            "speed_max": speed_max,
        }

    def _on_use_control_layer(self) -> None:
        try:
            fill = self.fill_holes.isChecked()
            max_hole = self._hole_size_mm() if fill else 0.0
            if fill and not self.max_hole_um.has_value():
                raise ValueError(
                    "Enter Minimum hole size before measuring the control layer."
                )
            d_max = svs.dmax_for_layer_file(
                self.folder,
                int(self.control_layer.value()),
                fill_holes=fill,
                max_hole_mm=max_hole,
            )
            self.size.set_user_value(d_max)
            self.status.setText(
                f"Control layer {self.control_layer.value()}: "
                f"d_max = {d_max:.4f} mm → Size d_max."
            )
        except Exception as exc:
            QMessageBox.warning(self, "Control layer", str(exc))
            self.status.setText(f"Control layer failed: {exc}")

    def _clear_geometry_cache(self) -> None:
        self._cached_dmax = None
        self._cached_thickness_um = None
        self._cached_white = None
        self._cached_file_names = None
        self._cached_yz = None
        self._cached_fill_key = None
        self._schedule = None

    def _on_browse(self) -> None:
        start = str(self.folder if self.folder.is_dir() else Path.home())
        chosen = QFileDialog.getExistingDirectory(
            self, "Select print folder", start
        )
        if not chosen:
            return
        new_folder = Path(chosen)
        self.folder = new_folder
        self.path_lbl.setText(f"Print folder: {self.folder}")
        self._clear_geometry_cache()
        self.status.setText(
            f"Folder changed to {self.folder.name}. Press Update to refresh."
        )

    def _ensure_geometry_cache(self, fill_holes: bool, max_hole_mm: float) -> None:
        fill_key = (bool(fill_holes), float(max_hole_mm) if fill_holes else 0.0)
        if (
            self._cached_dmax is not None
            and self._cached_yz is not None
            and self._cached_fill_key == fill_key
        ):
            return

        self.status.setText("Computing layer geometry (EDT)…")
        QApplication.processEvents()

        _header, rows = svs.read_instruction_file(svs.instruction_txt_path(self.folder))
        thickness = np.array([float(cells[2]) for cells in rows], dtype=float)
        file_names = [cells[1] for cells in rows]
        paths = [self.folder / name for name in file_names]

        def _progress(done: int, total: int) -> None:
            self.status.setText(f"Computing layer geometry {done}/{total}…")
            QApplication.processEvents()

        dmax, white = svs.analyze_layers_parallel(
            paths,
            fill_holes=fill_holes,
            max_hole_mm=max_hole_mm,
            progress_callback=_progress,
        )

        self.status.setText("Building YZ preview…")
        QApplication.processEvents()
        self._cached_dmax = dmax
        self._cached_thickness_um = thickness
        self._cached_white = white
        self._cached_file_names = file_names
        self._cached_yz = svs.build_yz_preview(paths)
        self._cached_fill_key = fill_key

    def _compute_schedule_from_cache(self, params: dict) -> svs.ScheduleResult:
        assert self._cached_dmax is not None
        assert self._cached_thickness_um is not None
        assert self._cached_white is not None
        assert self._cached_file_names is not None

        v0 = float(params["control_speed_um_s"])
        dose = float(params["control_dose"])
        r0 = float(params["control_size_mm"])
        c = float(params["correction"])
        led_min = params.get("led_min")
        led_max = params.get("led_max")
        speed_min = params.get("speed_min")
        speed_max = params.get("speed_max")

        rows = []
        z_um = 0.0
        any_low = False
        for i, (d_max, th_um, white_count, file_name) in enumerate(
            zip(
                self._cached_dmax,
                self._cached_thickness_um,
                self._cached_white,
                self._cached_file_names,
            )
        ):
            speed = svs.compute_speed_um_s(
                d_max_mm=float(d_max),
                control_size_mm=r0,
                control_speed_um_s=v0,
                correction=c,
            )
            if int(white_count) > 0:
                if speed_min is not None:
                    speed = max(speed, float(speed_min))
                if speed_max is not None:
                    speed = min(speed, float(speed_max))
            pwm, time_s = svs.compute_layer_pwm(
                speed_um_s=speed,
                control_speed_um_s=v0,
                control_dose=dose,
                thickness_um=float(th_um),
                white_pixel_count=int(white_count),
            )
            if int(white_count) > 0:
                if led_min is not None:
                    pwm = max(int(pwm), int(round(float(led_min))))
                if led_max is not None:
                    pwm = min(int(pwm), int(round(float(led_max))))
                pwm = int(np.clip(pwm, 0, 255))
            z_um += float(th_um)
            below = int(white_count) > 0 and pwm < svs.PWM_SOFT_WARN_FLOOR
            any_low = any_low or below
            rows.append(
                svs.LayerScheduleRow(
                    layer_index=i + 1,
                    file_name=file_name,
                    thickness_um=float(th_um),
                    z_height_mm=z_um / 1000.0,
                    d_max_mm=float(d_max),
                    radius_ratio=(float(d_max) / r0) if r0 > 0 else 0.0,
                    speed_um_s=speed if int(white_count) > 0 else v0,
                    time_s=time_s,
                    pwm=pwm,
                    white_pixel_count=int(white_count),
                    pwm_below_floor=below,
                )
            )

        return svs.ScheduleResult(
            rows=rows,
            control_speed_um_s=v0,
            control_dose=dose,
            control_size_mm=r0,
            correction=c,
            any_pwm_below_floor=any_low,
        )

    def _compute_schedule(self) -> svs.ScheduleResult:
        params = self._read_params()
        self._ensure_geometry_cache(params["fill_holes"], params["max_hole_mm"])
        return self._compute_schedule_from_cache(params)

    def _update_plots(self, schedule: svs.ScheduleResult) -> None:
        z_mm = np.asarray(schedule.z_mm, dtype=float)
        speeds = np.asarray(schedule.speeds_um_s, dtype=float)
        z_max = float(z_mm[-1]) if len(z_mm) else 1.0
        y_extent_mm = (
            float(self._cached_yz.shape[1]) * svs.PX_PITCH_MM
            if self._cached_yz is not None and self._cached_yz.size
            else 1.0
        )

        self._reset_plot_axes()

        try:
            yz = self._cached_yz
            if yz is not None and yz.size:
                self.ax_yz.imshow(
                    yz,
                    cmap="gray",
                    aspect="equal",
                    interpolation="nearest",
                    origin="lower",
                    extent=[0.0, y_extent_mm, 0.0, z_max],
                )
            self.ax_yz.set_xlim(0.0, y_extent_mm)
            self.ax_yz.set_ylim(0.0, z_max)
            if y_extent_mm > 0:
                self.ax_yz.set_box_aspect(z_max / y_extent_mm)
        except Exception as exc:
            self.ax_yz.text(
                0.5, 0.5, f"YZ preview failed:\n{exc}", ha="center", va="center",
                color="#F2F2F5",
            )
            self.ax_yz.set_ylim(0.0, z_max)
        self.ax_yz.set_title("YZ Cross-section", fontsize=10, pad=6)
        self.ax_yz.set_xlabel("Y (mm)")
        self.ax_yz.set_ylabel("Z (mm)")
        self._style_axes(self.ax_yz)

        self.ax_speed.plot(speeds, z_mm, color="#B794F4", linewidth=1.6)
        self.ax_speed.axvline(
            schedule.control_speed_um_s,
            color="#8870A3",
            ls="--",
            lw=1.0,
            label=f"v0 = {schedule.control_speed_um_s:g}",
        )
        if len(speeds):
            self.ax_speed.set_xlim(
                0.0,
                max(float(np.max(speeds)), float(schedule.control_speed_um_s)) * 1.05,
            )
        self.ax_speed.set_ylim(0.0, z_max)
        self.ax_speed.set_title("Normalized ramping routine", fontsize=10, pad=6)
        self.ax_speed.set_xlabel("Speed (µm/s)")
        self.ax_speed.set_ylabel("")
        self.ax_speed.grid(True, alpha=0.25, color="#3A4152")
        legend = self.ax_speed.legend(fontsize=8, loc="best", framealpha=0.9)
        legend.get_frame().set_facecolor("#1F2130")
        legend.get_frame().set_edgecolor("#3A4152")
        for text in legend.get_texts():
            text.set_color("#E8E8EE")
        self.ax_speed.tick_params(axis="y", labelleft=False)
        self._style_axes(self.ax_speed)

        self.fig.canvas.draw()
        b0 = self.ax_yz.get_position()
        b1 = self.ax_speed.get_position()
        self.ax_speed.set_position([b1.x0, b0.y0, b1.width, b0.height])
        self.canvas.draw_idle()

    def _warn_low_pwm(self, schedule: svs.ScheduleResult) -> None:
        if not schedule.any_pwm_below_floor:
            return
        lows = [r.layer_index for r in schedule.rows if r.pwm_below_floor]
        sample = ", ".join(str(i) for i in lows[:12])
        extra = f" (+{len(lows) - 12} more)" if len(lows) > 12 else ""
        QMessageBox.warning(
            self,
            "Low LED PWM",
            f"{len(lows)} layer(s) would use PWM below {svs.PWM_SOFT_WARN_FLOOR} "
            f"(e.g. layers {sample}{extra}).\n\n"
            "Consider a smaller Correction Factor so speeds and coupled PWM stay higher. "
            "Apply is still allowed.",
        )

    def _on_update(self) -> None:
        try:
            self._schedule = self._compute_schedule()
            self._update_plots(self._schedule)
            self._warn_low_pwm(self._schedule)
            self.status.setText(
                f"Updated: {len(self._schedule.rows)} layers. "
                f"Min speed {min(self._schedule.speeds_um_s):.3f} µm/s, "
                f"PWM range {min(self._schedule.pwms)}–{max(self._schedule.pwms)}."
            )
        except Exception as exc:
            QMessageBox.critical(self, "Update failed", str(exc))
            self.status.setText(f"Update failed: {exc}")

    def _on_apply(self) -> None:
        try:
            schedule = self._compute_schedule()
            self._schedule = schedule
            self._update_plots(schedule)
            self._warn_low_pwm(schedule)

            txt_path = svs.instruction_txt_path(self.folder)
            svs.rewrite_instruction_times_intensities(
                txt_path, schedule.times_s, schedule.pwms
            )
            self.status.setText(
                f"Wrote Time/Intensity to {txt_path.name} ({len(schedule.rows)} layers)."
            )
            if self.on_applied is not None:
                self.on_applied()
            QMessageBox.information(
                self,
                "Applied",
                f"Updated {txt_path.name} and reloaded the instruction file.",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Apply failed", str(exc))
            self.status.setText(f"Apply failed: {exc}")


def main(argv: Optional[list] = None) -> int:
    """CLI entry for launching the dialog from Tk Prince apps via subprocess."""
    import sys as _sys

    args = list(_sys.argv[1:] if argv is None else argv)
    folder = Path(args[0]) if args else Path.cwd()
    app = QApplication.instance() or QApplication(_sys.argv[:1])
    dlg = SimpleVariableSpeedDialog(folder=folder)
    dlg.show()
    return int(app.exec())


if __name__ == "__main__":
    raise SystemExit(main())
