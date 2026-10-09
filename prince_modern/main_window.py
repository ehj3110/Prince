"""Prince Modern main window — dark purple card layout (PySide6)."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .theme import QSS, load_fonts


def _card(title: str) -> tuple[QFrame, QVBoxLayout]:
    """Card with purple title bar matching the original Prince Modern mockup."""
    frame = QFrame()
    frame.setObjectName("card")
    outer = QVBoxLayout(frame)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(0)
    header = QFrame()
    header.setObjectName("cardHeader")
    hl = QHBoxLayout(header)
    hl.setContentsMargins(0, 0, 0, 0)
    caption = QLabel(title.upper())
    caption.setObjectName("cardTitle")
    hl.addWidget(caption)
    outer.addWidget(header)
    body = QVBoxLayout()
    body.setContentsMargins(14, 12, 14, 14)
    body.setSpacing(8)
    outer.addLayout(body)
    return frame, body


def _feed_label(placeholder: str) -> QLabel:
    label = QLabel(placeholder)
    label.setObjectName("feed")
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setMinimumSize(200, 200)
    # Ignored: pixmap must not drive the widget size (prevents the growing-slice bug).
    label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
    label.setScaledContents(False)
    return label


class ModernMainWindow(QMainWindow):
    """Dark modular shell with colorful purple card headers."""

    browse_directory = Signal()
    run_continuous = Signal()
    run_stepped = Signal()
    stop_print = Signal()
    move_up = Signal()
    move_down = Signal()
    set_home = Signal()
    get_position = Signal()
    simple_txt = Signal()
    open_image_mod = Signal()
    open_exp_conditions = Signal()
    open_sensor_logging = Signal()
    open_sensor_monitoring = Signal()
    open_monitoring_suite = Signal()
    disconnect_dlp = Signal()
    reconnect_dlp = Signal()
    open_ramped_cylinder = Signal()
    projection_mode_changed = Signal(bool)
    field_changed = Signal()

    def __init__(self):
        super().__init__()
        load_fonts()
        self.setWindowTitle("PRINCE Modern | DLP Resin Printer Control & Optics")
        self.resize(1560, 960)
        self.setMinimumSize(1200, 760)
        self.setStyleSheet(QSS)

        root = QWidget()
        root.setObjectName("modernRoot")
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        layout.addWidget(self._build_header())
        mid = QHBoxLayout()
        mid.setSpacing(12)
        mid.addLayout(self._build_left_column(), 2)
        mid.addLayout(self._build_center_column(), 3)
        mid.addLayout(self._build_right_column(), 2)
        layout.addLayout(mid, 1)
        layout.addWidget(self._build_footer())

        self._slice_dir: Path | None = None
        self._slice_paths: list[Path] = []
        self._viz_generated = False
        self._slice_source: np.ndarray | None = None
        self._stack_source: np.ndarray | None = None

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
        title = QLabel("PRINCE | DLP RESIN PRINTER CONTROL & OPTICS")
        title.setObjectName("title")
        row.addWidget(title)
        row.addStretch(1)
        self.state_chip = QLabel("PRINTER  IDLE")
        self.state_chip.setObjectName("chip")
        self.z_chip = QLabel("Z  — mm")
        self.z_chip.setObjectName("chip")
        row.addWidget(self.state_chip)
        row.addWidget(self.z_chip)
        outer.addLayout(row)
        return bar

    def _build_left_column(self) -> QVBoxLayout:
        col = QVBoxLayout()
        col.setSpacing(10)

        card, body = _card("PRINT SEQUENCE")
        dir_row = QHBoxLayout()
        self.image_dir = QLineEdit()
        self.image_dir.setPlaceholderText("Image / instruction directory")
        self.image_dir.editingFinished.connect(self.field_changed.emit)
        browse = QPushButton("Browse…")
        browse.clicked.connect(self.browse_directory.emit)
        dir_row.addWidget(self.image_dir, 1)
        dir_row.addWidget(browse)
        body.addLayout(dir_row)
        btn_row = QHBoxLayout()
        self.btn_run_cont = QPushButton("RUN CONT.")
        self.btn_run_cont.setObjectName("primary")
        self.btn_run_step = QPushButton("RUN STEP")
        self.btn_run_step.setObjectName("primary")
        self.btn_stop = QPushButton("STOP")
        self.btn_stop.setObjectName("danger")
        self.btn_run_cont.clicked.connect(self.run_continuous.emit)
        self.btn_run_step.clicked.connect(self.run_stepped.emit)
        self.btn_stop.clicked.connect(self.stop_print.emit)
        btn_row.addWidget(self.btn_run_cont)
        btn_row.addWidget(self.btn_run_step)
        btn_row.addWidget(self.btn_stop)
        body.addLayout(btn_row)
        col.addWidget(card)

        card, body = _card("LED CURRENT POWER (1-255)")
        self.led_power = QLineEdit("1")
        self.led_power.editingFinished.connect(self.field_changed.emit)
        body.addWidget(self.led_power)
        col.addWidget(card)

        card, body = _card("PRINT CONFIGURATION")
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)
        self.layer_thickness = QLineEdit("5")
        self.exposure_s = QLineEdit("1")
        self.base_cure_s = QLineEdit("1")
        self.step_speed = QLineEdit("1000")
        self.pause_s = QLineEdit("0")
        self.acceleration = QLineEdit("100")
        self.overstep_um = QLineEdit("0")  # hidden field kept in state; not labeled prominently
        fields = [
            ("Layer thickness (µm)", self.layer_thickness),
            ("Exposure time (s)", self.exposure_s),
            ("Base cure time (s)", self.base_cure_s),
            ("Step speed (µm/s)", self.step_speed),
            ("Pause (s)", self.pause_s),
            ("Acceleration (mm/s²)", self.acceleration),
        ]
        for row_i, (label, widget) in enumerate(fields):
            lab = QLabel(label)
            lab.setObjectName("muted")
            grid.addWidget(lab, row_i, 0)
            widget.editingFinished.connect(self.field_changed.emit)
            grid.addWidget(widget, row_i, 1)
        body.addLayout(grid)
        gen = QPushButton("Simple input txt generator")
        gen.clicked.connect(self.simple_txt.emit)
        body.addWidget(gen)
        col.addWidget(card)

        card, body = _card("STAGE CONTROL")
        dist_lab = QLabel("Move distance (mm)")
        dist_lab.setObjectName("muted")
        body.addWidget(dist_lab)
        self.move_distance = QLineEdit("0")
        self.move_distance.editingFinished.connect(self.field_changed.emit)
        body.addWidget(self.move_distance)
        move_row = QHBoxLayout()
        up = QPushButton("Move Up")
        down = QPushButton("Move Down")
        up.clicked.connect(self.move_up.emit)
        down.clicked.connect(self.move_down.emit)
        move_row.addWidget(up)
        move_row.addWidget(down)
        body.addLayout(move_row)
        home_row = QHBoxLayout()
        home = QPushButton("Set Home")
        getpos = QPushButton("Get Position")
        home.clicked.connect(self.set_home.emit)
        getpos.clicked.connect(self.get_position.emit)
        home_row.addWidget(home)
        home_row.addWidget(getpos)
        body.addLayout(home_row)
        self.z_readout = QLabel("Z Pos: — mm")
        self.z_readout.setObjectName("chip")
        body.addWidget(self.z_readout)
        col.addWidget(card)
        col.addStretch(1)
        return col

    def _build_center_column(self) -> QVBoxLayout:
        col = QVBoxLayout()
        col.setSpacing(10)

        card, body = _card("SYSTEM LOG")
        self.system_log = QTextEdit()
        self.system_log.setObjectName("systemLog")
        self.system_log.setReadOnly(True)
        self.system_log.setMinimumHeight(180)
        body.addWidget(self.system_log)
        col.addWidget(card, 2)

        card, body = _card("BUILD VISUALIZATION")
        controls = QHBoxLayout()
        self.btn_generate_viz = QPushButton("Generate visualization")
        self.btn_generate_viz.setObjectName("primary")
        self.btn_generate_viz.clicked.connect(self.generate_visualization)
        controls.addWidget(self.btn_generate_viz)
        controls.addStretch(1)
        body.addLayout(controls)
        viz = QHBoxLayout()
        viz.setSpacing(8)
        left = QVBoxLayout()
        left_cap = QLabel("3D preview")
        left_cap.setObjectName("muted")
        left.addWidget(left_cap)
        self.viz_3d = _feed_label("Click Generate visualization")
        left.addWidget(self.viz_3d, 1)
        right = QVBoxLayout()
        right_cap = QLabel("Layer slice")
        right_cap.setObjectName("muted")
        right.addWidget(right_cap)
        self.slice_view = _feed_label("Click Generate visualization")
        right.addWidget(self.slice_view, 1)
        viz.addLayout(left, 1)
        viz.addLayout(right, 1)
        body.addLayout(viz, 1)
        self.viz_meta = QLabel("No visualization loaded")
        self.viz_meta.setObjectName("muted")
        body.addWidget(self.viz_meta)
        col.addWidget(card, 3)
        return col

    def _build_right_column(self) -> QVBoxLayout:
        col = QVBoxLayout()
        col.setSpacing(10)

        card, body = _card("SYSTEM ACTIONS")
        grid = QGridLayout()
        grid.setSpacing(6)
        actions = [
            ("Image Modification", self.open_image_mod),
            ("Experimental Conditions", self.open_exp_conditions),
            ("Sensor Panel (Logging)", self.open_sensor_logging),
            ("Sensor Panel (Monitoring)", self.open_sensor_monitoring),
            ("Monitoring Suite", self.open_monitoring_suite),
            ("Disconnect DLP", self.disconnect_dlp),
            ("Reconnect DLP", self.reconnect_dlp),
            ("Ramped Cylinder", self.open_ramped_cylinder),
        ]
        self._action_buttons: dict[str, QPushButton] = {}
        for i, (label, signal) in enumerate(actions):
            btn = QPushButton(label)
            btn.clicked.connect(signal.emit)
            self._action_buttons[label] = btn
            grid.addWidget(btn, i // 2, i % 2)
        body.addLayout(grid)
        self.video_pattern_check = QCheckBox("Enable Video Pattern Mode (Newer)")
        self.video_pattern_check.toggled.connect(self.projection_mode_changed.emit)
        body.addWidget(self.video_pattern_check)
        col.addWidget(card)

        card, body = _card("SYSTEM INFO & TEAM")
        info = QLabel(
            "Northwestern University — Scalable & Additive Manufacturing Lab\n"
            "Prof. Cheng Sun  ·  Prince DLP platform"
        )
        info.setObjectName("muted")
        info.setWordWrap(True)
        body.addWidget(info)
        checklist = QLabel(
            "Checklist:\n"
            "1. Confirm DLP is powered and not held by TI GUI\n"
            "2. Confirm projector is the secondary display\n"
            "3. Keep Sensor Panel closed if Monitoring Suite needs the force gauge"
        )
        checklist.setWordWrap(True)
        body.addWidget(checklist)
        self.power_warning = QLabel("Power calibration differs between modes!")
        self.power_warning.setObjectName("warning")
        self.power_warning.setWordWrap(True)
        body.addWidget(self.power_warning)
        col.addWidget(card)
        col.addStretch(1)
        return col

    def _build_footer(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("footerBar")
        outer = QVBoxLayout(bar)
        outer.setContentsMargins(14, 10, 14, 10)
        outer.setSpacing(8)
        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setValue(0)
        outer.addWidget(self.progress)
        row = QHBoxLayout()
        self.layer_label = QLabel("LAYER: — / —")
        self.layer_label.setObjectName("chip")
        self.progress_label = QLabel("PROGRESS: 0%")
        self.progress_label.setObjectName("chip")
        self.time_label = QLabel("TIME REMAINING: —")
        self.time_label.setObjectName("chip")
        row.addWidget(self.layer_label)
        row.addWidget(self.progress_label)
        row.addWidget(self.time_label)
        row.addStretch(1)
        outer.addLayout(row)
        return bar

    # --- UI helpers used by controller ---

    def append_log(self, message: str) -> None:
        self.system_log.append(message.rstrip())
        self.system_log.verticalScrollBar().setValue(self.system_log.verticalScrollBar().maximum())

    def set_printer_state(self, text: str, printing: bool = False) -> None:
        self.state_chip.setText(f"PRINTER  {text}")
        self.state_chip.setObjectName("chipActive" if printing else "chip")
        self.state_chip.style().unpolish(self.state_chip)
        self.state_chip.style().polish(self.state_chip)
        self.btn_run_cont.setEnabled(not printing)
        self.btn_run_step.setEnabled(not printing)

    def set_z_position(self, z_mm: float | None) -> None:
        if z_mm is None:
            self.z_chip.setText("Z  — mm")
            self.z_readout.setText("Z Pos: — mm")
        else:
            self.z_chip.setText(f"Z  {z_mm:.3f} mm")
            self.z_readout.setText(f"Z Pos: {z_mm:.3f} mm")

    def set_progress(self, layer: int, total: int, fraction: float, eta: str) -> None:
        pct = max(0.0, min(1.0, fraction))
        self.progress.setValue(int(round(pct * 1000)))
        self.layer_label.setText(f"LAYER: {layer} / {total}" if total else "LAYER: — / —")
        self.progress_label.setText(f"PROGRESS: {pct * 100:.0f}%")
        self.time_label.setText(f"TIME REMAINING: {eta}")
        if self._viz_generated and total:
            self.viz_meta.setText(f"{len(self._slice_paths)} slices  ·  layer {layer}/{total}  ·  Est: {eta}")

    def set_sensor_button_states(self, logging_open: bool, monitoring_open: bool) -> None:
        self._action_buttons["Sensor Panel (Logging)"].setEnabled(not monitoring_open)
        self._action_buttons["Sensor Panel (Monitoring)"].setEnabled(not logging_open)

    def set_video_pattern_warning(self, video_pattern: bool) -> None:
        self.power_warning.setVisible(not video_pattern)

    def choose_directory(self, start: str = "") -> str | None:
        path = QFileDialog.getExistingDirectory(self, "Select image directory", start)
        return path or None

    def collect_fields(self) -> dict[str, str]:
        return {
            "directory": self.image_dir.text().strip(),
            "led_power": self.led_power.text().strip(),
            "move_distance": self.move_distance.text().strip(),
            "layer_thickness": self.layer_thickness.text().strip(),
            "exposure": self.exposure_s.text().strip(),
            "base_cure": self.base_cure_s.text().strip(),
            "step_speed": self.step_speed.text().strip(),
            "pause": self.pause_s.text().strip(),
            "acceleration": self.acceleration.text().strip(),
            "overstep": self.overstep_um.text().strip(),
            "video_pattern": "1" if self.video_pattern_check.isChecked() else "0",
        }

    def apply_fields(self, values: dict[str, str]) -> None:
        mapping = {
            "directory": self.image_dir,
            "led_power": self.led_power,
            "move_distance": self.move_distance,
            "layer_thickness": self.layer_thickness,
            "exposure": self.exposure_s,
            "base_cure": self.base_cure_s,
            "step_speed": self.step_speed,
            "pause": self.pause_s,
            "acceleration": self.acceleration,
            "overstep": self.overstep_um,
        }
        for key, widget in mapping.items():
            if key in values and values[key] is not None:
                widget.setText(str(values[key]))
        if "video_pattern" in values:
            self.video_pattern_check.blockSignals(True)
            self.video_pattern_check.setChecked(str(values["video_pattern"]) in ("1", "true", "video_pattern"))
            self.video_pattern_check.blockSignals(False)
            self.set_video_pattern_warning(self.video_pattern_check.isChecked())
        if "directory" in values:
            self.set_slice_directory(str(values["directory"]))

    def set_slice_directory(self, directory: str) -> None:
        """Remember the folder only — do not load until Generate visualization."""
        self._slice_dir = Path(directory) if directory else None
        self._viz_generated = False
        self._slice_paths = []
        self._slice_source = None
        self._stack_source = None
        self.slice_view.setText("Click Generate visualization")
        self.slice_view.setPixmap(QPixmap())
        self.viz_3d.setText("Click Generate visualization")
        self.viz_3d.setPixmap(QPixmap())
        self.viz_meta.setText("No visualization loaded")

    def generate_visualization(self) -> None:
        """Load slices from the image directory and show layer + stack preview once."""
        directory = self.image_dir.text().strip() or (str(self._slice_dir) if self._slice_dir else "")
        if not directory:
            self.viz_meta.setText("Set an image directory first")
            self.append_log("Generate visualization: no image directory set.")
            return
        root = Path(directory)
        if not root.is_dir():
            self.viz_meta.setText(f"Directory not found: {root}")
            self.append_log(f"Generate visualization failed: {root}")
            return

        candidates = sorted(root.glob("*.png"), key=lambda p: p.name)
        numbered = sorted(
            [p for p in candidates if p.stem.isdigit()],
            key=lambda p: int(p.stem),
        )
        paths = numbered or candidates
        if not paths:
            self.viz_meta.setText("No PNG slices in directory")
            self.append_log(f"Generate visualization: no PNGs in {root}")
            return

        # Cap how many layers we stack so large jobs stay responsive.
        max_stack = 80
        if len(paths) > max_stack:
            step = max(1, len(paths) // max_stack)
            stack_paths = paths[::step][:max_stack]
        else:
            stack_paths = list(paths)

        first = cv2.imread(str(paths[0]), cv2.IMREAD_GRAYSCALE)
        if first is None:
            self.viz_meta.setText(f"Could not read {paths[0].name}")
            return

        stack = []
        for path in stack_paths:
            img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            if img.shape != first.shape:
                img = cv2.resize(img, (first.shape[1], first.shape[0]), interpolation=cv2.INTER_NEAREST)
            stack.append(img)

        self._slice_dir = root
        self._slice_paths = paths
        self._slice_source = first
        self._stack_source = self._build_stack_preview(stack) if stack else None
        self._viz_generated = True
        self._paint_visualization()
        self.viz_meta.setText(
            f"{len(paths)} slices loaded  ·  showing {paths[0].name}  ·  stack samples {len(stack)}"
        )
        self.append_log(f"Visualization generated from {root} ({len(paths)} PNGs).")

    def _build_stack_preview(self, layers: list[np.ndarray]) -> np.ndarray:
        """Simple depth-tint composite (monitor-like stand-in for a 3D lattice)."""
        h, w = layers[0].shape
        canvas = np.zeros((h, w, 3), dtype=np.float32)
        n = max(1, len(layers))
        for i, layer in enumerate(layers):
            mask = layer.astype(np.float32) / 255.0
            # Purple depth ramp: near layers brighter / more lilac.
            t = i / max(1, n - 1)
            color = np.array([0.55 + 0.35 * t, 0.25 + 0.20 * t, 0.85 - 0.15 * t], dtype=np.float32)
            for c in range(3):
                canvas[:, :, c] = np.maximum(canvas[:, :, c], mask * color[c])
        out = np.clip(canvas * 255.0, 0, 255).astype(np.uint8)
        return out

    def _paint_visualization(self) -> None:
        self._set_feed_array(self.slice_view, self._slice_source, grayscale=True)
        self._set_feed_array(self.viz_3d, self._stack_source, grayscale=False)

    def _set_feed_array(self, label: QLabel, image: np.ndarray | None, grayscale: bool) -> None:
        if image is None:
            label.setPixmap(QPixmap())
            return
        if grayscale:
            if image.ndim != 2:
                image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            h, w = image.shape
            qimg = QImage(np.ascontiguousarray(image).data, w, h, w, QImage.Format.Format_Grayscale8).copy()
        else:
            if image.dtype != np.uint8:
                image = np.clip(image, 0, 255).astype(np.uint8)
            h, w, _ = image.shape
            contiguous = np.ascontiguousarray(image)
            qimg = QImage(contiguous.data, w, h, 3 * w, QImage.Format.Format_RGB888).copy()
        pix = QPixmap.fromImage(qimg)
        target = label.size()
        if target.width() > 20 and target.height() > 20:
            pix = pix.scaled(
                target,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        label.setPixmap(pix)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._viz_generated:
            self._paint_visualization()

    def set_build_placeholder(self, text: str = "Click Generate visualization") -> None:
        self._viz_generated = False
        self.viz_3d.setText(text)
        self.viz_3d.setPixmap(QPixmap())
        self.slice_view.setText(text)
        self.slice_view.setPixmap(QPixmap())
