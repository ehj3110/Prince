"""PySide6 research dashboard for Prince sensor monitoring."""

from __future__ import annotations

import os

os.environ.setdefault("QT_API", "pyside6")

from PySide6.QtCore import QEvent, QEventLoop, QObject, Qt, QTimer
from PySide6.QtGui import QImage, QPixmap

from collections import deque

import cv2
import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from calibration_modules.print_monitor_state import read_print_monitor_state
from .theme import QSS
from .workers import (
    ForceGaugeThread,
    OpticalThread,
    PowerMeterThread,
    ThermalThread,
    calibration_distribution,
    compute_single_calibration,
    compute_triple_calibration,
    expected_power_mW,
    load_power_calibration,
    load_print_job,
    save_force_calibration,
    save_power_calibration,
)

try:
    import pyvista as pv
    from pyvistaqt import QtInteractor

    PYVISTA_AVAILABLE = True
except Exception:
    pv = None
    QtInteractor = None
    PYVISTA_AVAILABLE = False

pg.setConfigOptions(antialias=True, background="#18191E", foreground="#9E9EA8")

# SensorDataWindow keeps 5000 points at its 10 ms default, a 50 s trace.
FORCE_HISTORY_S = 50.0


class MonitoringDashboard(QMainWindow):
    """2x2 monitoring dashboard. Acquisition runs off the UI thread."""

    def __init__(
        self,
        use_hardware: bool = True,
        image_dir: str | None = None,
        force_triple: bool | None = None,
    ):
        super().__init__()
        self.setWindowTitle("System Monitoring & Physics Analytics")
        self.resize(1560, 960)
        self.setMinimumSize(1200, 760)
        self.setStyleSheet(QSS)

        self._force_t: deque[float] = deque(maxlen=self._force_history_count(0.025))
        self._force_meas: deque[float] = deque(maxlen=self._force_history_count(0.025))
        self._power_t: deque[float] = deque(maxlen=self._power_history_count(0.25))
        self._power_mw: deque[float] = deque(maxlen=self._power_history_count(0.25))
        self._power_expected: deque[float] = deque(maxlen=self._power_history_count(0.25))
        self._latest_mw: float | None = None
        self._calibration = load_power_calibration()
        self._following_print = False
        self._shown_layer = 1
        self._live_power: float | None = None
        self._last_layer = 1
        self._thermal_span: tuple[float, float] | None = None
        self._plotter = None
        self._plane = None
        self._job = load_print_job(image_dir) if image_dir else None
        self._cover_watchers: list[_CoverWatcher] = []
        self._exposure_apply_timer = QTimer(self)
        self._exposure_apply_timer.setSingleShot(True)
        self._exposure_apply_timer.timeout.connect(self._apply_optical_exposure)

        root = QWidget()
        root.setObjectName("dashboardRoot")
        self.setCentralWidget(root)
        grid = QGridLayout(root)
        grid.setContentsMargins(12, 12, 12, 12)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        grid.setRowStretch(1, 3)
        grid.setRowStretch(2, 3)
        grid.setRowStretch(3, 0)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        grid.addWidget(self._build_header(), 0, 0, 1, 2)
        grid.addWidget(self._build_cameras(), 1, 0)
        grid.addWidget(self._build_force(), 1, 1)
        grid.addWidget(self._build_geometry(), 2, 0)
        grid.addWidget(self._build_power(), 2, 1)
        grid.addWidget(self._build_status(), 3, 0, 1, 2)

        self._optical = OpticalThread(use_hardware=use_hardware)
        self._thermal = ThermalThread(use_hardware=use_hardware)
        self._force = ForceGaugeThread(force_triple=force_triple)
        self._power = PowerMeterThread(use_hardware=use_hardware)
        self.tare_button.clicked.connect(self._force.request_tare)
        self.calibrate_button.clicked.connect(self._calibrate_force)
        self.wavelength_combo.currentIndexChanged.connect(self._on_power_wavelength)
        self._optical.frame_ready.connect(self._on_optical)
        self._thermal.frame_ready.connect(self._on_thermal)
        self._optical.source_changed.connect(self._on_optical_source)
        self._optical.exposure_ready.connect(self._on_optical_exposure_ready)
        self._thermal.source_changed.connect(self._on_thermal_source)
        self._force.sample.connect(self._on_force)
        self._force.tared.connect(self._on_force_tared)
        self._force.source_changed.connect(self._on_force_source)
        self._power.sample.connect(self._on_power)
        self._power.source_changed.connect(self._on_power_source)
        self._apply_idle_state()
        self._optical.start()
        self._thermal.start()
        self._force.start()
        self._power.start()
        self._state_timer = QTimer(self)
        self._state_timer.timeout.connect(self._poll_print_state)
        self._state_timer.start(250)
        self._refresh_calibration_fields()

    def _card(self, title: str) -> tuple[QFrame, QVBoxLayout]:
        frame = QFrame()
        frame.setObjectName("card")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(8)
        heading = QLabel(title)
        heading.setObjectName("muted")
        layout.addWidget(heading)
        return frame, layout

    def _attach_cover(self, host: QWidget, top: int = 36, inset: int = 8, visible: bool = False) -> QWidget:
        """Translucent gray cover with a status banner. Hidden until a source is missing."""
        cover = QWidget(host)
        cover.setObjectName("unavailableCover")
        cover.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        cover.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        layout = QVBoxLayout(cover)
        banner = QLabel("Sensor readout unavailable")
        banner.setObjectName("unavailableBanner")
        banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(banner, alignment=Qt.AlignmentFlag.AlignCenter)
        cover.setVisible(visible)
        watcher = _CoverWatcher(host, cover, top, inset, self)
        host.installEventFilter(watcher)
        self._cover_watchers.append(watcher)
        return cover

    def _build_header(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("headerBar")
        outer = QVBoxLayout(bar)
        outer.setContentsMargins(14, 10, 14, 10)
        outer.setSpacing(8)
        accent = QFrame()
        accent.setObjectName("accentBar")
        outer.addWidget(accent)
        row = QHBoxLayout()
        title = QLabel("SYSTEM MONITORING & PHYSICS ANALYTICS")
        title.setObjectName("title")
        row.addWidget(title)
        row.addStretch(1)
        self.state_chip = QLabel("PRINTER  —")
        self.state_chip.setObjectName("chip")
        self.z_chip = QLabel("Z  — mm")
        self.z_chip.setObjectName("chip")
        row.addWidget(self.state_chip)
        row.addWidget(self.z_chip)
        outer.addLayout(row)
        return bar

    def _build_cameras(self) -> QFrame:
        card, layout = self._card("DUAL CAMERA FEEDS")
        row = QHBoxLayout()
        row.setSpacing(8)
        self.optical_view = self._feed_label()
        self.thermal_view = self._feed_label()
        self.optical_status = QLabel("connecting")
        self.thermal_status = QLabel("connecting")
        self.temp_badge = QLabel("TEMP: — °C", self.thermal_view)
        self.temp_badge.setObjectName("overlay")
        self.temp_badge.move(8, 8)
        self._optical_cover = self._attach_cover(self.optical_view, top=0, inset=0)
        self._thermal_cover = self._attach_cover(self.thermal_view, top=0, inset=0)
        optical_col = self._captioned_feed("Projection Camera", self.optical_view, self.optical_status)
        optical_col.addLayout(self._build_optical_exposure_row())
        row.addLayout(optical_col, 1)
        row.addLayout(self._captioned_feed("Thermal camera", self.thermal_view, self.thermal_status), 1)
        layout.addLayout(row, 1)
        return card

    def _build_optical_exposure_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)
        label = QLabel("Exposure")
        label.setObjectName("muted")
        self.optical_exposure_slider = QSlider(Qt.Orientation.Horizontal)
        self.optical_exposure_slider.setRange(100, int(OpticalThread.MAX_EXPOSURE_US))
        self.optical_exposure_slider.setValue(int(OpticalThread.DEFAULT_EXPOSURE_US))
        self.optical_exposure_slider.setEnabled(False)
        self.optical_exposure_slider.valueChanged.connect(self._on_optical_exposure_slider)
        self.optical_exposure_value = QLabel(f"{int(OpticalThread.DEFAULT_EXPOSURE_US)} µs")
        self.optical_exposure_value.setObjectName("muted")
        self.optical_exposure_value.setMinimumWidth(84)
        row.addWidget(label)
        row.addWidget(self.optical_exposure_slider, 1)
        row.addWidget(self.optical_exposure_value)
        return row

    def _captioned_feed(self, title: str, view: QLabel, status: QLabel) -> QVBoxLayout:
        column = QVBoxLayout()
        column.setSpacing(4)
        header = QHBoxLayout()
        caption = QLabel(title)
        caption.setObjectName("muted")
        status.setObjectName("chip")
        header.addWidget(caption)
        header.addStretch(1)
        header.addWidget(status)
        column.addLayout(header)
        column.addWidget(view, 1)
        return column

    def _feed_label(self) -> QLabel:
        label = QLabel()
        label.setObjectName("feed")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setMinimumSize(280, 200)
        label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        return label

    def _build_force(self) -> QFrame:
        card, layout = self._card("Force Gauge Readout")
        body = QHBoxLayout()
        body.setSpacing(10)
        self.force_plot = pg.PlotWidget()
        self._style_plot(self.force_plot, "Time", "s", "Force", "N")
        self.force_plot.enableAutoRange(axis="x", enable=False)
        self.force_plot.enableAutoRange(axis="y", enable=True)
        self.force_plot.setXRange(0.0, FORCE_HISTORY_S, padding=0)
        self.force_base_curve = self.force_plot.plot(pen=None)
        self.force_meas_curve = self.force_plot.plot(
            pen=pg.mkPen("#B084F4", width=2),
            name="Measured",
        )
        self.force_fill = pg.FillBetweenItem(
            self.force_meas_curve,
            self.force_base_curve,
            brush=pg.mkBrush(176, 132, 244, 70),
        )
        self.force_plot.addItem(self.force_fill)
        body.addWidget(self.force_plot, 3)

        controls = QVBoxLayout()
        controls.setSpacing(6)
        self.force_readout = QLabel(" 0.000 N")
        self.force_readout.setObjectName("metricValue")
        self.force_status = QLabel("connecting")
        self.force_status.setObjectName("chip")
        controls.addWidget(self.force_readout)
        controls.addWidget(self.force_status)
        rate_label = QLabel("Sensor refresh")
        rate_label.setObjectName("muted")
        controls.addWidget(rate_label)
        self.rate_combo = QComboBox()
        for hz in (5, 10, 20, 40, 50, 100):
            self.rate_combo.addItem(f"{hz} Hz", hz)
        # Default 40 Hz = 25 ms sampling for the tour force plot.
        self.rate_combo.setCurrentIndex(3)
        self.rate_combo.currentIndexChanged.connect(self._on_force_rate)
        controls.addWidget(self.rate_combo)
        reset = QPushButton("Reset view")
        reset.clicked.connect(self._reset_force_view)
        controls.addWidget(reset)
        self.tare_button = QPushButton("Tare")
        self.tare_button.setEnabled(False)
        controls.addWidget(self.tare_button)
        self.calibrate_button = QPushButton("Calibrate")
        self.calibrate_button.setEnabled(False)
        controls.addWidget(self.calibrate_button)
        controls.addStretch(1)
        body.addLayout(controls, 0)
        layout.addLayout(body, 1)
        return card

    def _force_history_count(self, period_s: float) -> int:
        """Point count for the sensor panel's history: 5000 samples at 10 ms is 50 s."""
        return max(2, int(round(FORCE_HISTORY_S / max(period_s, 0.008))))

    def _on_force_rate(self, _index: int) -> None:
        period_s = 1.0 / float(self.rate_combo.currentData())
        self._force.force_period_s = period_s
        self._force_t = deque(self._force_t, maxlen=self._force_history_count(period_s))
        self._force_meas = deque(self._force_meas, maxlen=self._force_history_count(period_s))

    def _reset_force_view(self) -> None:
        self.force_plot.enableAutoRange(axis="y", enable=True)
        if self._force_t:
            self._apply_force_time_range(self._force_t[-1])
        else:
            self.force_plot.setXRange(0.0, FORCE_HISTORY_S, padding=0)

    def _apply_force_time_range(self, latest_s: float) -> None:
        if latest_s < FORCE_HISTORY_S:
            self.force_plot.setXRange(0.0, max(latest_s, 0.5), padding=0)
        else:
            self.force_plot.setXRange(latest_s - FORCE_HISTORY_S, latest_s, padding=0)

    def _build_geometry(self) -> QFrame:
        card, layout = self._card("PRINT GEOMETRY & SLICED LAYER")
        if self._job is None:
            layout.addWidget(self._unavailable_panel("Print images unavailable"), 1)
            self.slice_view = None
            self.slice_meta = None
            return card

        split = QHBoxLayout()
        split.setSpacing(8)
        if PYVISTA_AVAILABLE:
            host = QWidget()
            host_layout = QVBoxLayout(host)
            host_layout.setContentsMargins(0, 0, 0, 0)
            self._plotter = QtInteractor(host)
            host_layout.addWidget(self._plotter)
            self._init_stacked_volume()
            split.addWidget(host, 3)
        else:
            missing = QLabel("3D view unavailable. Install pyvista and pyvistaqt.")
            missing.setObjectName("muted")
            missing.setWordWrap(True)
            split.addWidget(missing, 3)

        side = QVBoxLayout()
        self.slice_view = QLabel("Slice")
        self.slice_view.setObjectName("feed")
        self.slice_view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.slice_view.setMinimumSize(180, 180)
        self.slice_meta = QLabel("")
        self.slice_meta.setObjectName("metricUnit")
        side.addWidget(self.slice_view, 1)
        side.addWidget(self.slice_meta)
        split.addLayout(side, 2)
        layout.addLayout(split, 1)
        return card

    def _unavailable_panel(self, text: str) -> QFrame:
        panel = QFrame()
        panel.setObjectName("unavailablePanel")
        layout = QVBoxLayout(panel)
        banner = QLabel(text)
        banner.setObjectName("unavailableBanner")
        banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(banner, alignment=Qt.AlignmentFlag.AlignCenter)
        return panel

    def _init_stacked_volume(self) -> None:
        """Stack the resized layer images into one voxel solid."""
        job = self._job
        plotter = self._plotter
        plotter.set_background("#0E0F12")
        if job is None or job.width_mm <= 0 or job.height_mm <= 0 or job.volume.shape[2] == 0:
            return
        sample = job.volume.shape[0]
        count = job.volume.shape[2]
        grid = pv.ImageData()
        grid.dimensions = (sample + 1, sample + 1, count + 1)
        grid.spacing = (
            job.width_mm / sample,
            job.height_mm / sample,
            job.layer_height_mm,
        )
        grid.cell_data["exposed"] = job.volume.ravel(order="F")
        solid = grid.threshold(0.5, scalars="exposed")
        if solid.n_cells:
            plotter.add_mesh(solid, color="#4E2A84", opacity=0.9, name="print_solid")
        self._plane = pv.Plane(
            center=(job.width_mm / 2.0, job.height_mm / 2.0, 0.0),
            direction=(0, 0, 1),
            i_size=job.width_mm,
            j_size=job.height_mm,
        )
        plotter.add_mesh(self._plane, color="#B084F4", opacity=0.35, name="slice_plane")
        plotter.view_isometric()
        plotter.enable_anti_aliasing()

    def _build_power(self) -> QFrame:
        card, layout = self._card("POWER METER")
        controls = QHBoxLayout()
        wave = QLabel("Wavelength")
        wave.setObjectName("muted")
        self.wavelength_combo = QComboBox()
        self.wavelength_combo.addItem("365 nm", 365.0)
        self.wavelength_combo.addItem("385 nm", 385.0)
        self.wavelength_combo.addItem("405 nm", 405.0)
        self.wavelength_combo.setCurrentIndex(1)
        self.power_status = QLabel("connecting")
        self.power_status.setObjectName("chip")
        controls.addWidget(wave)
        controls.addWidget(self.wavelength_combo)
        controls.addStretch(1)
        controls.addWidget(self.power_status)
        layout.addLayout(controls)
        self.power_value = QLabel("OPTICAL POWER: — mW")
        self.power_value.setObjectName("metricValue")
        self.power_value.setWordWrap(True)
        layout.addWidget(self.power_value)
        self.expected_value = QLabel("EXPECTED: —")
        self.expected_value.setObjectName("muted")
        self.expected_value.setWordWrap(True)
        layout.addWidget(self.expected_value)
        cal = QHBoxLayout()
        self.cal_low = QLineEdit()
        self.cal_high = QLineEdit()
        for field in (self.cal_low, self.cal_high):
            field.setPlaceholderText("mW")
            field.setMaximumWidth(90)
            field.editingFinished.connect(self._on_calibration_edited)
        record_low = QPushButton("Record 10")
        record_high = QPushButton("Record 100")
        record_low.clicked.connect(lambda: self._record_calibration(10))
        record_high.clicked.connect(lambda: self._record_calibration(100))
        cal.addWidget(QLabel("10"))
        cal.addWidget(self.cal_low)
        cal.addWidget(record_low)
        cal.addWidget(QLabel("100"))
        cal.addWidget(self.cal_high)
        cal.addWidget(record_high)
        cal.addStretch(1)
        layout.addLayout(cal)
        self.dose_plot = pg.PlotWidget()
        self._style_plot(self.dose_plot, "Time", "s", "Power", "mW")
        self.dose_plot.enableAutoRange(axis="x", enable=False)
        self.dose_plot.enableAutoRange(axis="y", enable=True)
        self.dose_plot.setXRange(0.0, FORCE_HISTORY_S, padding=0)
        self.power_curve = self.dose_plot.plot(
            pen=pg.mkPen("#B084F4", width=2),
            name="Measured",
        )
        self.power_expected_curve = self.dose_plot.plot(
            pen=pg.mkPen("#9E9EA8", width=1.5, style=Qt.PenStyle.DashLine),
            name="Expected",
        )
        self.dose_plot.addLegend(offset=(8, 8))
        layout.addWidget(self.dose_plot, 1)
        self._power_cover = self._attach_cover(card, top=150, visible=True)
        return card

    def _power_history_count(self, period_s: float) -> int:
        return max(2, int(round(FORCE_HISTORY_S / max(period_s, 0.05))))

    def _on_power_wavelength(self, _index: int) -> None:
        self._power.set_wavelength_nm(float(self.wavelength_combo.currentData()))

    def _on_power_source(self, text: str) -> None:
        self.power_status.setText(text)
        self._power_cover.setVisible(text != "live")
        if text != "live":
            self._power_cover.raise_()

    def _on_power(self, t_s: float, milliwatts: float) -> None:
        self._latest_mw = milliwatts
        self.power_value.setText(f"OPTICAL POWER: {milliwatts:.4f} mW")
        expected = self._expected_power_now()
        self.expected_value.setText(self._expected_caption(expected))
        self._power_t.append(t_s)
        self._power_mw.append(milliwatts)
        self._power_expected.append(float("nan") if expected is None else expected)
        self.power_curve.setData(np.asarray(self._power_t), np.asarray(self._power_mw))
        self.power_expected_curve.setData(np.asarray(self._power_t), np.asarray(self._power_expected))
        if t_s < FORCE_HISTORY_S:
            self.dose_plot.setXRange(0.0, max(t_s, 0.5), padding=0)
        else:
            self.dose_plot.setXRange(t_s - FORCE_HISTORY_S, t_s, padding=0)

    def _refresh_calibration_fields(self) -> None:
        self.cal_low.setText(self._format_mw(self._calibration.measured_mW_at_10))
        self.cal_high.setText(self._format_mw(self._calibration.measured_mW_at_200))

    def _format_mw(self, value: float | None) -> str:
        return "" if value is None else f"{value:.4f}"

    def _on_calibration_edited(self) -> None:
        self._calibration.measured_mW_at_10 = self._parse_field(self.cal_low)
        self._calibration.measured_mW_at_200 = self._parse_field(self.cal_high)
        if self._calibration.area_mm2 is None and self._job is not None and self._job.total_areas:
            area = self._job.total_areas[self._current_layer_index()]
            if area > 0:
                self._calibration.area_mm2 = area
        save_power_calibration(self._calibration)

    def _parse_field(self, field: QLineEdit) -> float | None:
        text = field.text().strip()
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None

    def _record_calibration(self, command: int) -> None:
        if self._latest_mw is None:
            return
        area = self._current_area_mm2()
        if area is not None and area > 0 and self._calibration.area_mm2 is None:
            self._calibration.area_mm2 = area
        if command == int(self._calibration.command_low):
            self._calibration.measured_mW_at_10 = self._latest_mw
        else:
            self._calibration.command_high = float(command)
            self._calibration.measured_mW_at_200 = self._latest_mw
        save_power_calibration(self._calibration)
        self._refresh_calibration_fields()

    def _current_layer_index(self) -> int:
        if self._job is None or not self._job.total_areas:
            return 0
        layer = self._shown_layer if self._following_print else 1
        return max(0, min(len(self._job.total_areas) - 1, layer - 1))

    def _current_area_mm2(self) -> float | None:
        if self._job is None or not self._job.total_areas:
            return self._calibration.area_mm2
        return self._job.total_areas[self._current_layer_index()]

    def _current_command(self) -> float | None:
        if self._following_print and self._live_power is not None:
            return self._live_power
        if self._job is None or not self._job.powers:
            return None
        command = self._job.powers[self._current_layer_index()]
        if not np.isfinite(command):
            return None
        return float(command)

    def _expected_power_now(self) -> float | None:
        command = self._current_command()
        area = self._current_area_mm2()
        if command is None or area is None:
            return None
        return expected_power_mW(command, area, self._calibration)

    def _expected_caption(self, expected: float | None) -> str:
        densities = self._calibration.densities_mW_cm2()
        area = self._calibration.area_mm2
        if densities is None or area is None:
            return "EXPECTED: record the meter at projector power 10 and 100, on the same image"
        low, high = densities
        if expected is None:
            return (
                f"DENSITY: {low:.3f} mW/cm² at {self._calibration.command_low:.0f}, "
                f"{high:.3f} at {self._calibration.command_high:.0f}"
                f"  ·  cal area {area:.2f} mm²"
            )
        command = self._current_command()
        layer_area = self._current_area_mm2()
        return (
            f"EXPECTED: {expected:.4f} mW"
            f"  ·  command {command:.0f}, layer area {layer_area:.2f} mm²"
        )

    def _poll_print_state(self) -> None:
        state = read_print_monitor_state()
        running = bool(state and state.get("running"))
        if running:
            layer = max(1, int(state.get("layer", 1)))
            try:
                self._live_power = float(state.get("power"))
            except (TypeError, ValueError):
                self._live_power = None
            self._following_print = True
            if layer != self._shown_layer:
                self._shown_layer = layer
                self._show_layer(layer)
                count = 0 if self._job is None else len(self._job.paths)
                self.layer_label.setText(f"LAYER: {layer} / {count}" if count else f"LAYER: {layer}")
                if count:
                    fraction = min(1.0, layer / count)
                    self.progress.setValue(int(1000 * fraction))
                    self.progress_label.setText(f"PROGRESS: {100 * fraction:.0f}%")
                self.state_chip.setText("PRINTER  PRINTING")
            return
        if self._following_print:
            self._following_print = False
            self._live_power = None
            self._shown_layer = 1
            self._apply_idle_state()
            self._show_layer(1)

    def _build_status(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("headerBar")
        bar.setMinimumHeight(84)
        row = QHBoxLayout(bar)
        row.setContentsMargins(14, 14, 14, 14)
        row.setSpacing(16)
        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setTextVisible(False)
        row.addWidget(self.progress, 1)
        self.progress_label = QLabel("PROGRESS: 0%")
        self.time_label = QLabel("TIME REMAINING: —")
        self.layer_label = QLabel("LAYER: — / —")
        for label in (self.progress_label, self.time_label, self.layer_label):
            label.setObjectName("metricUnit")
            row.addWidget(label)
        return bar

    def _style_plot(self, plot: pg.PlotWidget, x_label: str, x_unit: str, y_label: str, y_unit: str) -> None:
        plot.setBackground("#18191E")
        plot.showGrid(x=True, y=True, alpha=0.25)
        plot.setLabel("bottom", x_label, units=x_unit, color="#9E9EA8")
        plot.setLabel("left", y_label, units=y_unit, color="#9E9EA8")
        plot.getAxis("bottom").setPen(pg.mkPen("#2B2D35"))
        plot.getAxis("left").setPen(pg.mkPen("#2B2D35"))
        plot.getAxis("bottom").setTextPen(pg.mkPen("#9E9EA8"))
        plot.getAxis("left").setTextPen(pg.mkPen("#9E9EA8"))

    def _thermal_auto_span(self, finite: np.ndarray) -> tuple[float, float]:
        """Percentile auto-level, smoothed so the palette does not flicker."""
        low = float(np.percentile(finite, 2))
        high = float(np.percentile(finite, 98))
        if high - low < 1.0:
            high = low + 1.0
        if self._thermal_span is None:
            self._thermal_span = (low, high)
        else:
            previous_low, previous_high = self._thermal_span
            blend = 0.3
            self._thermal_span = (
                previous_low * (1.0 - blend) + low * blend,
                previous_high * (1.0 - blend) + high * blend,
            )
        return self._thermal_span

    def _on_optical(self, frame: np.ndarray) -> None:
        self._show_array(self.optical_view, frame)

    def _on_thermal(self, temps: np.ndarray) -> None:
        finite = temps[np.isfinite(temps)]
        if finite.size == 0:
            return
        t_min, t_max = self._thermal_auto_span(finite)
        span = max(t_max - t_min, 0.5)
        norm = np.clip((temps - t_min) / span * 255.0, 0, 255).astype(np.uint8)
        color = cv2.applyColorMap(norm, cv2.COLORMAP_INFERNO)
        mean_c = float(np.mean(finite))
        self.temp_badge.setText(f"TEMP: {mean_c:.1f} °C")
        self.temp_badge.adjustSize()
        self.temp_badge.raise_()
        self._show_array(self.thermal_view, color)

    def _show_array(self, label: QLabel, image: np.ndarray) -> None:
        pix = _to_pixmap(image)
        target = label.size()
        if target.width() > 20 and target.height() > 20:
            pix = pix.scaled(
                target,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        label.setPixmap(pix)

    def _on_optical_source(self, text: str) -> None:
        self.optical_status.setText(text)
        live = text == "live"
        self._optical_cover.setVisible(not live)
        self.optical_exposure_slider.setEnabled(live)
        if not live:
            self._optical_cover.raise_()

    def _on_optical_exposure_ready(self, lo_us: float, hi_us: float, current_us: float) -> None:
        lo = max(1, int(round(lo_us)))
        hi = max(lo + 1, min(int(round(hi_us)), int(OpticalThread.MAX_EXPOSURE_US)))
        current = max(lo, min(int(round(current_us)), hi))
        self.optical_exposure_slider.blockSignals(True)
        self.optical_exposure_slider.setRange(lo, hi)
        self.optical_exposure_slider.setValue(current)
        self.optical_exposure_slider.blockSignals(False)
        self.optical_exposure_value.setText(f"{current} µs")
        self.optical_exposure_slider.setEnabled(True)

    def _on_optical_exposure_slider(self, value: int) -> None:
        self.optical_exposure_value.setText(f"{value} µs")
        self._exposure_apply_timer.start(120)

    def _apply_optical_exposure(self) -> None:
        self._optical.set_exposure_us(float(self.optical_exposure_slider.value()))

    def _on_thermal_source(self, text: str) -> None:
        self.thermal_status.setText(text)
        unavailable = text != "live"
        self._thermal_cover.setVisible(unavailable)
        self.temp_badge.setVisible(not unavailable)
        if unavailable:
            self._thermal_cover.raise_()
        else:
            self.temp_badge.raise_()

    def _on_force_source(self, text: str) -> None:
        self.force_status.setText(text)
        live = text.startswith("live")
        self.tare_button.setEnabled(live)
        self.calibrate_button.setEnabled(live)

    def _on_force_tared(self) -> None:
        self._force_t.clear()
        self._force_meas.clear()
        self.force_readout.setText(" 0.000 N")

    def _format_force_n(self, measured: float) -> str:
        """Three decimals; leading space when non-negative so digits do not shift."""
        return f"{measured: .3f} N"

    def _capture_force_ratios(self, seconds: float = 0.5) -> list[float] | None:
        """Block the UI briefly while the force thread averages raw voltage ratios."""
        result: dict[str, object] = {}
        loop = QEventLoop(self)

        def on_ok(ratios: object) -> None:
            result["ratios"] = ratios
            loop.quit()

        def on_fail(message: str) -> None:
            result["error"] = message
            loop.quit()

        self._force.ratios_captured.connect(on_ok)
        self._force.ratios_failed.connect(on_fail)
        self._force.request_ratio_snapshot(seconds)
        # Safety timeout so a dropped gauge cannot hang the wizard forever.
        QTimer.singleShot(int((seconds + 4.0) * 1000), loop.quit)
        loop.exec()
        self._force.ratios_captured.disconnect(on_ok)
        self._force.ratios_failed.disconnect(on_fail)
        if "error" in result:
            QMessageBox.critical(self, "Calibration Error", str(result["error"]))
            return None
        ratios = result.get("ratios")
        if not isinstance(ratios, list) or not ratios:
            QMessageBox.critical(
                self,
                "Calibration Error",
                "Timed out waiting for force-gauge voltage ratios.",
            )
            return None
        return [float(value) for value in ratios]

    def _calibrate_force(self) -> None:
        """SensorDataWindow-style two-point calibrate; triple uses proportional total force."""
        if not self.force_status.text().startswith("live"):
            QMessageBox.critical(self, "Calibration Error", "Force gauge is not connected.")
            return
        triple = self._force.is_triple
        zero_msg = (
            "Please ensure all three load cells are at zero force, then click OK."
            if triple
            else "Please ensure the load cell is at zero force, then click OK."
        )
        reply = QMessageBox.information(
            self,
            "Calibration Step 1",
            zero_msg,
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
        )
        if reply != QMessageBox.StandardButton.Ok:
            return
        zero_ratios = self._capture_force_ratios(0.5)
        if zero_ratios is None:
            return
        known_force, ok = QInputDialog.getDouble(
            self,
            "Calibration Step 2",
            "Enter the total known force in Newtons (N):" if triple else "Enter the known force in Newtons (N):",
            9.81,
            -1.0e6,
            1.0e6,
            4,
        )
        if not ok:
            return
        apply_msg = (
            f"Please apply the known force of {known_force:.4f} N total "
            f"(centered on the platform so all three cells share the load), then click OK."
            if triple
            else f"Please apply the known force of {known_force:.4f} N to the load cell, then click OK."
        )
        reply = QMessageBox.information(
            self,
            "Calibration Step 2",
            apply_msg,
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
        )
        if reply != QMessageBox.StandardButton.Ok:
            return
        loaded_ratios = self._capture_force_ratios(0.5)
        if loaded_ratios is None:
            return
        try:
            if triple:
                if len(zero_ratios) < 3 or len(loaded_ratios) < 3:
                    raise ValueError("Triple calibration needs readings on channels 0, 1, and 2.")
                calibration = compute_triple_calibration(zero_ratios, loaded_ratios, known_force)
                summary = calibration_distribution(
                    zero_ratios, loaded_ratios, known_force, calibration
                )
            else:
                calibration = compute_single_calibration(
                    zero_ratios[0], loaded_ratios[0], known_force
                )
                summary = calibration_distribution(
                    zero_ratios, loaded_ratios, known_force, calibration
                )
        except ValueError as exc:
            QMessageBox.critical(self, "Calibration Error", str(exc))
            return
        self._force.apply_calibration(calibration)
        self._force.request_tare()
        QMessageBox.information(
            self,
            "Calibration Complete",
            f"All channels calibrated successfully.\n\n{summary}",
        )
        save = QMessageBox.question(
            self,
            "Save Calibration",
            "Save these values to a file?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if save == QMessageBox.StandardButton.Yes:
            path = save_force_calibration(calibration)
            QMessageBox.information(
                self,
                "Calibration Saved",
                f"Calibration saved to:\n{path}",
            )

    def _on_force(self, t_s: float, measured: float) -> None:
        self.force_readout.setText(self._format_force_n(measured))
        self._force_t.append(t_s)
        self._force_meas.append(measured)
        meas = np.asarray(self._force_meas)
        times = np.asarray(self._force_t)
        self.force_meas_curve.setData(times, meas)
        self.force_base_curve.setData(times, np.zeros_like(meas))
        self._apply_force_time_range(t_s)

    def _apply_idle_state(self) -> None:
        count = 0 if self._job is None else len(self._job.paths)
        self.state_chip.setText("PRINTER  IDLE")
        self.z_chip.setText("Z  — mm")
        self.progress.setValue(0)
        self.progress_label.setText("PROGRESS: 0%")
        self.time_label.setText("TIME REMAINING: —")
        self.layer_label.setText(f"LAYER: 1 / {count}" if count else "LAYER: — / —")

    def _show_layer(self, layer_number: int) -> None:
        if self._job is None or self.slice_view is None:
            return
        index = max(0, min(len(self._job.paths) - 1, layer_number - 1))
        image = cv2.imread(str(self._job.paths[index]), cv2.IMREAD_GRAYSCALE)
        if image is not None:
            self._show_array(self.slice_view, image)
        exposure = self._job.exposure_s[index]
        self.slice_meta.setText(
            f"TOTAL AREA: {self._job.total_areas[index]:.2f} mm²\n"
            f"PEAK AREA: {self._job.peak_areas[index]:.2f} mm²\n"
            f"TOTAL VOLUME: {self._job.print_volume_mm3:.2f} mm³\n"
            f"EXPOSURE: {exposure:.1f} s"
        )
        if self._plotter is not None and self._plane is not None:
            points = np.array(self._plane.points)
            points[:, 2] = index * self._job.layer_height_mm
            self._plane.points = points
            self._plotter.render()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._show_layer(1)
        for watcher in self._cover_watchers:
            watcher.fit()

    def closeEvent(self, event) -> None:
        self._state_timer.stop()
        for thread in (self._optical, self._thermal, self._force, self._power):
            thread.stop()
            thread.wait(4000)
        if self._plotter is not None:
            try:
                self._plotter.close()
            except Exception:
                pass
        super().closeEvent(event)


class _CoverWatcher(QObject):
    """Keep an unavailable cover sized to its host."""

    def __init__(self, host: QWidget, cover: QWidget, top: int, inset: int, parent: QObject):
        super().__init__(parent)
        self._host = host
        self._cover = cover
        self._top = top
        self._inset = inset

    def eventFilter(self, watched, event) -> bool:
        if watched is self._host and event.type() == QEvent.Type.Resize:
            self.fit()
        return False

    def fit(self) -> None:
        host = self._host
        self._cover.setGeometry(
            self._inset,
            self._top,
            max(0, host.width() - 2 * self._inset),
            max(0, host.height() - self._top - self._inset),
        )
        self._cover.raise_()


def _to_pixmap(image: np.ndarray) -> QPixmap:
    image = np.ascontiguousarray(image)
    if image.ndim == 2:
        height, width = image.shape
        qimg = QImage(image.data, width, height, width, QImage.Format.Format_Grayscale8).copy()
    else:
        rgb = np.ascontiguousarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        height, width, _channels = rgb.shape
        qimg = QImage(rgb.data, width, height, 3 * width, QImage.Format.Format_RGB888).copy()
    return QPixmap.fromImage(qimg)


def _format_remaining(seconds: float) -> str:
    total = int(max(0, round(seconds)))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes:02d}m"
    return f"{minutes}m {secs:02d}s"
