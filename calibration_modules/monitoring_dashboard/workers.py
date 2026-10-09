"""Acquisition threads for the monitoring dashboard.

Cameras use the Allied Vision and Seek workers. A missing device stays
unconnected instead of drawing a stand-in image. Force uses the Phidget
bridge directly so the dashboard can run without Prince open.
"""

from __future__ import annotations

import json
import os
import queue
import re
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal


class OpticalThread(QThread):
    """Grayscale vat image. Signal carries a uint8 HxW array."""

    frame_ready = Signal(object)
    source_changed = Signal(str)
    exposure_ready = Signal(float, float, float)  # lo_us, hi_us, current_us

    DEFAULT_EXPOSURE_US = 5000.0
    MAX_EXPOSURE_US = 500_000.0  # 0.5 s — never needed higher for the vat view

    def __init__(self, use_hardware: bool = True):
        super().__init__()
        self.use_hardware = use_hardware
        self._stop = False
        self._worker = None
        self._pending_exposure_us: float | None = self.DEFAULT_EXPOSURE_US

    def stop(self) -> None:
        self._stop = True

    def set_exposure_us(self, exposure_us: float) -> None:
        """Manual ExposureTime in microseconds (auto exposure stays off)."""
        clamped = max(1.0, min(float(exposure_us), self.MAX_EXPOSURE_US))
        self._pending_exposure_us = clamped
        worker = self._worker
        if worker is not None:
            worker.auto_exposure = False
            worker.request_exposure(clamped)

    def run(self) -> None:
        if self.use_hardware and self._run_hardware():
            return
        self.source_changed.emit("not connected")
        while not self._stop:
            self.msleep(200)

    def _run_hardware(self) -> bool:
        try:
            from calibration_modules.vmb_camera_worker import VMBPY_AVAILABLE, VmbCameraWorker
        except ImportError:
            return False
        if not VMBPY_AVAILABLE:
            return False
        frames: queue.Queue = queue.Queue(maxsize=1)
        # Manual exposure: continuous auto was leaving the live view soft/blurry.
        worker = VmbCameraWorker(frames, fallback_to_mock=False, auto_exposure=False)
        self._worker = worker
        if self._pending_exposure_us is not None:
            worker.request_exposure(self._pending_exposure_us)
        worker.start()
        try:
            announced = False
            deadline = time.perf_counter() + 12.0
            while not self._stop:
                try:
                    frame = frames.get(timeout=0.05)
                except queue.Empty:
                    if not announced and time.perf_counter() > deadline and not worker.is_alive():
                        return False
                    continue
                if worker.is_mock:
                    return False
                if not announced and worker.connected:
                    lo, hi = worker.exposure_range
                    hi = min(float(hi), self.MAX_EXPOSURE_US)
                    current = worker.current_exposure or self.DEFAULT_EXPOSURE_US
                    current = min(float(current), self.MAX_EXPOSURE_US)
                    self.exposure_ready.emit(float(lo), hi, current)
                    self.source_changed.emit("live")
                    announced = True
                self.frame_ready.emit(np.ascontiguousarray(frame))
        finally:
            self._worker = None
            worker.stop(join_timeout=4.0)
        return True


class ThermalThread(QThread):
    """Radiometric float32 °C image. Signal carries the temperature array."""

    frame_ready = Signal(object)
    source_changed = Signal(str)

    def __init__(self, use_hardware: bool = True):
        super().__init__()
        self.use_hardware = use_hardware
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        if self.use_hardware and self._run_hardware():
            return
        self.source_changed.emit("not connected")
        while not self._stop:
            self.msleep(200)

    def _run_hardware(self) -> bool:
        try:
            from calibration_modules.seek_thermal_worker import SeekThermalWorker
        except ImportError:
            return False
        frames: queue.Queue = queue.Queue(maxsize=1)
        worker = SeekThermalWorker(frames, fallback_to_mock=False)
        worker.start()
        try:
            deadline = time.perf_counter() + 8.0
            announced = False
            while not self._stop:
                try:
                    payload = frames.get(timeout=0.05)
                except queue.Empty:
                    if not announced and time.perf_counter() > deadline and not worker.is_alive():
                        return False
                    continue
                if worker.is_mock:
                    return False
                if not announced and worker.connected:
                    self.source_changed.emit("live")
                    announced = True
                temp = payload[0] if isinstance(payload, tuple) else payload
                self.frame_ready.emit(np.ascontiguousarray(temp, dtype=np.float32))
        finally:
            worker.stop(join_timeout=3.0)
        return True


@dataclass
class ForceCalibration:
    """Single bridge channel or triple load cells on channels 0–2."""

    path: Path | None
    triple: bool
    channels: list[tuple[int, float, float]]  # channel, gain N/(V/V), offset V/V

    @property
    def primary(self) -> tuple[int, float, float]:
        return self.channels[0]


class ForceGaugeThread(QThread):
    """Live Phidget bridge reading for as long as the dashboard is open."""

    sample = Signal(float, float)  # t_s, measured_N
    channels_sample = Signal(float, float, float)  # tared Ch0, Ch1, Ch2 (triple mode)
    source_changed = Signal(str)
    tared = Signal()
    ratios_captured = Signal(object)  # list[float] voltage ratios
    ratios_failed = Signal(str)

    def __init__(self, force_triple: bool | None = None):
        super().__init__()
        self._stop = False
        self.force_period_s = 0.025
        self.tare_requested = False
        self._tare_n = 0.0
        self._tare_channels = [0.0, 0.0, 0.0]
        self._open_tare_pending = True
        self._tare_started: float | None = None
        self._tare_bucket: list[float] = []
        self._tare_channel_buckets: list[list[float]] = [[], [], []]
        self._force_triple_override = force_triple
        self._calibration: ForceCalibration | None = None
        self._pending_calibration: ForceCalibration | None = None
        self._ratio_snapshot_s: float | None = None
        self._ratio_started: float | None = None
        self._ratio_buckets: list[list[float]] = []

    @property
    def is_triple(self) -> bool:
        return bool(self._calibration and self._calibration.triple)

    def stop(self) -> None:
        self._stop = True

    def request_tare(self) -> None:
        """Zero the next sample against the current live reading."""
        self.tare_requested = True

    def request_ratio_snapshot(self, seconds: float = 0.5) -> None:
        """Average raw voltage ratios on the open channels for ``seconds``."""
        self._ratio_snapshot_s = max(0.2, float(seconds))
        self._ratio_started = None
        self._ratio_buckets = []

    def apply_calibration(self, calibration: ForceCalibration) -> None:
        """Hot-swap gains/offsets without closing the Phidget handles."""
        self._pending_calibration = calibration

    def run(self) -> None:
        """Sample for the whole time the dashboard is open, and reconnect if the gauge drops."""
        calibration = _load_force_calibration()
        if self._force_triple_override is True:
            calibration = _as_triple_calibration(calibration)
        elif self._force_triple_override is False:
            calibration = _as_single_calibration(calibration)
        self._calibration = calibration
        _log_force_calibration(calibration)
        t0 = time.perf_counter()
        devices: list | None = None
        reported = ""
        self.source_changed.emit("connecting")
        reported = "connecting"
        live_status = "live · triple sum" if calibration.triple else "live"
        try:
            while not self._stop:
                if self._pending_calibration is not None:
                    calibration = self._pending_calibration
                    self._pending_calibration = None
                    self._calibration = calibration
                    live_status = "live · triple sum" if calibration.triple else "live"
                    self._tare_n = 0.0
                    self._tare_channels = [0.0, 0.0, 0.0]
                    self._open_tare_pending = True
                    self._reset_tare_buffers(clear_pending_only=True)
                    _log_force_calibration(calibration)
                    if reported.startswith("live"):
                        self.source_changed.emit(live_status)
                        reported = live_status
                if devices is None:
                    if calibration.triple:
                        devices = _open_force_phidget_channels(
                            tuple(ch for ch, _g, _o in calibration.channels)
                        )
                    else:
                        ch, _g, _o = calibration.primary
                        one = _open_force_phidget_channel(ch)
                        devices = [one] if one is not None else None
                    if devices is None:
                        if reported != "not connected":
                            self.source_changed.emit("not connected")
                            reported = "not connected"
                        if self._ratio_snapshot_s is not None:
                            self._ratio_snapshot_s = None
                            self.ratios_failed.emit("Force gauge is not connected.")
                        self.msleep(1000)
                        continue
                elapsed = time.perf_counter() - t0
                try:
                    raw_ratios = [float(device.getVoltageRatio()) for device in devices]
                    measured, channel_forces = _forces_from_ratios(raw_ratios, calibration)
                except Exception as exc:
                    if _phidget_value_not_ready(exc):
                        self.msleep(50)
                        continue
                    print(f"Force gauge read failed, reconnecting: {exc}")
                    _close_force_phidget_devices(devices)
                    devices = None
                    self._reset_tare_buffers()
                    if self._ratio_snapshot_s is not None:
                        self._ratio_snapshot_s = None
                        self.ratios_failed.emit(str(exc))
                    if reported != "not connected":
                        self.source_changed.emit("not connected")
                        reported = "not connected"
                    continue
                if reported != live_status:
                    self.source_changed.emit(live_status)
                    reported = live_status
                if self._ratio_snapshot_s is not None:
                    now = time.perf_counter()
                    if self._ratio_started is None:
                        self._ratio_started = now
                        self._ratio_buckets = [[] for _ in raw_ratios]
                    for idx, ratio in enumerate(raw_ratios):
                        self._ratio_buckets[idx].append(ratio)
                    if now - self._ratio_started < self._ratio_snapshot_s:
                        self.msleep(int(max(0.008, self.force_period_s) * 1000))
                        continue
                    averages = [
                        sum(bucket) / len(bucket) if bucket else 0.0
                        for bucket in self._ratio_buckets
                    ]
                    self._ratio_snapshot_s = None
                    self._ratio_started = None
                    self._ratio_buckets = []
                    self.ratios_captured.emit(averages)
                if self._open_tare_pending or self.tare_requested:
                    now = time.perf_counter()
                    if self._tare_started is None:
                        self._tare_started = now
                        self._tare_bucket = []
                        self._tare_channel_buckets = [[], [], []]
                    self._tare_bucket.append(measured)
                    if calibration.triple and channel_forces is not None:
                        for idx, value in enumerate(channel_forces[:3]):
                            self._tare_channel_buckets[idx].append(value)
                    if now - self._tare_started < 0.5:
                        self.msleep(int(max(0.008, self.force_period_s) * 1000))
                        continue
                    self._tare_n = sum(self._tare_bucket) / len(self._tare_bucket)
                    if calibration.triple:
                        for idx in range(3):
                            bucket = self._tare_channel_buckets[idx]
                            self._tare_channels[idx] = (
                                sum(bucket) / len(bucket) if bucket else 0.0
                            )
                        print(
                            "Force gauge tared (triple): "
                            f"total {self._tare_n:.4f} N, "
                            f"ch0 {self._tare_channels[0]:.4f}, "
                            f"ch1 {self._tare_channels[1]:.4f}, "
                            f"ch2 {self._tare_channels[2]:.4f} N."
                        )
                    else:
                        print(f"Force gauge tared at {self._tare_n:.4f} N.")
                    self._open_tare_pending = False
                    self.tare_requested = False
                    self._reset_tare_buffers(clear_pending_only=True)
                    self.tared.emit()
                tared_total = measured - self._tare_n
                self.sample.emit(elapsed, tared_total)
                if calibration.triple and channel_forces is not None:
                    tared = [
                        channel_forces[i] - self._tare_channels[i]
                        for i in range(min(3, len(channel_forces)))
                    ]
                    while len(tared) < 3:
                        tared.append(0.0)
                    self.channels_sample.emit(tared[0], tared[1], tared[2])
                self.msleep(int(max(0.008, self.force_period_s) * 1000))
        finally:
            if devices is not None:
                _close_force_phidget_devices(devices)

    def _reset_tare_buffers(self, clear_pending_only: bool = False) -> None:
        self._tare_started = None
        self._tare_bucket.clear()
        self._tare_channel_buckets = [[], [], []]
        if not clear_pending_only:
            self._open_tare_pending = True


def _log_force_calibration(calibration: ForceCalibration) -> None:
    if calibration.path is None:
        ch, gain, offset = calibration.primary
        print(f"Force calibration defaults ch{ch}: gain {gain:.4f}, offset {offset:.8f}")
        return
    mode = "triple sum" if calibration.triple else "single"
    print(f"Force calibration {calibration.path.name} ({mode})")
    for ch, gain, offset in calibration.channels:
        print(f"  channel {ch}: gain {gain:.4f} N/V, offset {offset:.8f}")


def compute_triple_calibration(
    zero_ratios: list[float],
    loaded_ratios: list[float],
    total_force_n: float,
) -> ForceCalibration:
    """Proportional total-force calibration for three parallel cells (docs)."""
    if len(zero_ratios) < 3 or len(loaded_ratios) < 3:
        raise ValueError("Triple calibration needs voltage ratios for channels 0, 1, and 2.")
    if abs(total_force_n) < 1e-9:
        raise ValueError("Known force must be a non-zero number.")
    deltas = [loaded_ratios[i] - zero_ratios[i] for i in range(3)]
    delta_sum = sum(deltas)
    if abs(delta_sum) < 1e-9:
        raise ValueError("Voltage ratio did not change significantly with the known force.")
    channels: list[tuple[int, float, float]] = []
    for i in range(3):
        share = deltas[i] / delta_sum
        force_i = total_force_n * share
        if abs(deltas[i]) < 1e-12:
            raise ValueError(f"Channel {i} voltage ratio did not change with the known force.")
        gain = force_i / deltas[i]
        channels.append((i, gain, zero_ratios[i]))
    return ForceCalibration(path=None, triple=True, channels=channels)


def compute_single_calibration(
    zero_ratio: float,
    loaded_ratio: float,
    known_force_n: float,
    channel: int = 0,
) -> ForceCalibration:
    """SensorDataWindow two-point calibration on one bridge channel."""
    if abs(known_force_n) < 1e-9:
        raise ValueError("Known force must be a non-zero number.")
    delta = loaded_ratio - zero_ratio
    if abs(delta) < 1e-9:
        raise ValueError("Voltage ratio did not change significantly with the known force.")
    gain = known_force_n / delta
    return ForceCalibration(
        path=None,
        triple=False,
        channels=[(channel, gain, zero_ratio)],
    )


def calibration_distribution(
    zero_ratios: list[float],
    loaded_ratios: list[float],
    total_force_n: float,
    calibration: ForceCalibration,
) -> str:
    """Human-readable share of the known total force across channels."""
    if not calibration.triple:
        ch, gain, offset = calibration.primary
        return f"Channel {ch}: GAIN={gain:.4f}, OFFSET={offset:.8f}"
    deltas = [loaded_ratios[i] - zero_ratios[i] for i in range(3)]
    delta_sum = sum(deltas)
    lines = []
    warn = False
    for i, (ch, gain, offset) in enumerate(calibration.channels):
        share = deltas[i] / delta_sum if abs(delta_sum) > 1e-15 else 0.0
        force_i = total_force_n * share
        pct = 100.0 * share
        lines.append(
            f"Ch{ch}: {pct:.1f}% ({force_i:.3f} N)  GAIN={gain:.4f}  OFFSET={offset:.8f}"
        )
        if pct > 40.0 or pct < 25.0:
            warn = True
    text = "Distribution at calibration:\n" + "\n".join(lines)
    if warn:
        text += (
            "\n\nWarning: load share is uneven (one cell outside ~25-40%). "
            "Check platform alignment before the tour."
        )
    return text


def save_force_calibration(calibration: ForceCalibration, directory: Path | None = None) -> Path:
    """Write MODE=TRIPLE or single GAIN/OFFSET file under data/."""
    root = Path(__file__).resolve().parents[2]
    out_dir = directory or (root / "data")
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = out_dir / f"force_gauge_calibration_{stamp}.txt"
    mode = "TRIPLE CELL" if calibration.triple else "SINGLE CELL"
    lines = [
        "# Force Gauge Calibration File",
        f"# Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"# Mode: {mode}",
        f"MODE={'TRIPLE' if calibration.triple else 'SINGLE'}",
    ]
    if calibration.triple:
        for ch, gain, offset in calibration.channels:
            lines.append(f"GAIN_{ch}={gain}")
            lines.append(f"OFFSET_{ch}={offset}")
    else:
        _ch, gain, offset = calibration.primary
        lines.append(f"GAIN={gain}")
        lines.append(f"OFFSET={offset}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    calibration.path = path
    print(f"Saved force calibration to {path}")
    return path


def _load_force_calibration() -> ForceCalibration:
    """Most recent saved gauge file. Triple mode when MODE=TRIPLE and ch0–2 cal exist."""
    root = Path(__file__).resolve().parents[2]
    files = list((root / "data").glob("force_gauge_calibration_*.txt"))
    files += list(root.glob("force_gauge_calibration_*.txt"))
    default_gain, default_offset = 10118.0739, -0.00000914
    if not files:
        return ForceCalibration(
            path=None,
            triple=False,
            channels=[(0, default_gain, default_offset)],
        )
    latest = max(files, key=lambda path: path.stat().st_mtime)
    mode = ""
    gains: dict[int, float] = {}
    offsets: dict[int, float] = {}
    single_gain = single_offset = None
    for line in latest.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if line.startswith("MODE="):
            mode = line.split("=", 1)[1].strip().upper()
        elif line.startswith("GAIN_") and "=" in line:
            key, value = line.split("=", 1)
            gains[int(key.split("_", 1)[1])] = float(value)
        elif line.startswith("OFFSET_") and "=" in line:
            key, value = line.split("=", 1)
            offsets[int(key.split("_", 1)[1])] = float(value)
        elif line.startswith("GAIN=") and single_gain is None:
            single_gain = float(line.split("=", 1)[1])
        elif line.startswith("OFFSET=") and single_offset is None:
            single_offset = float(line.split("=", 1)[1])
    triple_requested = mode == "TRIPLE" or os.environ.get("PRINCE_MONITOR_TRIPLE_FORCE") == "1"
    if triple_requested and all(ch in gains and ch in offsets for ch in (0, 1, 2)):
        channels = [(ch, gains[ch], offsets[ch]) for ch in (0, 1, 2)]
        return ForceCalibration(path=latest, triple=True, channels=channels)
    gain = gains.get(0, single_gain if single_gain is not None else default_gain)
    offset = offsets.get(0, single_offset if single_offset is not None else default_offset)
    return ForceCalibration(path=latest, triple=False, channels=[(0, gain, offset)])


def _as_triple_calibration(calibration: ForceCalibration) -> ForceCalibration:
    if calibration.triple:
        return calibration
    if calibration.path is None:
        return calibration
    text = calibration.path.read_text(encoding="utf-8", errors="ignore")
    gains: dict[int, float] = {}
    offsets: dict[int, float] = {}
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("GAIN_") and "=" in line:
            key, value = line.split("=", 1)
            gains[int(key.split("_", 1)[1])] = float(value)
        elif line.startswith("OFFSET_") and "=" in line:
            key, value = line.split("=", 1)
            offsets[int(key.split("_", 1)[1])] = float(value)
    if all(ch in gains and ch in offsets for ch in (0, 1, 2)):
        return ForceCalibration(
            path=calibration.path,
            triple=True,
            channels=[(ch, gains[ch], offsets[ch]) for ch in (0, 1, 2)],
        )
    return calibration


def _as_single_calibration(calibration: ForceCalibration) -> ForceCalibration:
    ch, gain, offset = calibration.primary
    return ForceCalibration(path=calibration.path, triple=False, channels=[(ch, gain, offset)])


def _forces_from_ratios(
    ratios: list[float],
    calibration: ForceCalibration,
) -> tuple[float, list[float] | None]:
    channel_forces: list[float] = []
    for ratio, (_ch, gain, offset) in zip(ratios, calibration.channels, strict=False):
        channel_forces.append((ratio - offset) * gain)
    total = sum(channel_forces)
    if calibration.triple:
        return total, channel_forces
    return channel_forces[0], None


def _read_force_sample(
    devices: list,
    calibration: ForceCalibration,
) -> tuple[float, list[float] | None]:
    ratios = [float(device.getVoltageRatio()) for device in devices]
    return _forces_from_ratios(ratios, calibration)


def _phidget_value_not_ready(exc: Exception) -> bool:
    """Bridge inputs raise 0x33 until the first conversion is available."""
    code = getattr(exc, "code", None)
    if code in (0x33, 51):
        return True
    text = str(exc).lower()
    return "unknown" in text or "0x33" in text


def _configure_force_phidget_channel(device) -> None:
    from Phidget22.BridgeGain import BridgeGain

    device.setBridgeGain(BridgeGain.BRIDGE_GAIN_1)
    if hasattr(device, "setBridgeEnabled"):
        device.setBridgeEnabled(True)
    device.setDataInterval(25)
    if hasattr(device, "setVoltageRatioChangeTrigger"):
        device.setVoltageRatioChangeTrigger(0.0)


def _open_force_phidget_channel(channel: int):
    try:
        from Phidget22.Devices.VoltageRatioInput import VoltageRatioInput
        from Phidget22.PhidgetException import PhidgetException
    except ImportError:
        print("Force gauge: Phidget22 is not installed.")
        return None

    device = VoltageRatioInput()
    try:
        device.setHubPort(-1)
        device.setChannel(channel)
        device.openWaitForAttachment(4000)
        _configure_force_phidget_channel(device)
        print(f"Force gauge attached on channel {channel}.")
        time.sleep(0.3)
        return device
    except PhidgetException as exc:
        print(f"Force gauge channel {channel} not attached: {exc}")
        try:
            device.close()
        except Exception:
            pass
        return None


def _open_force_phidget_channels(channels: tuple[int, ...]):
    opened = []
    for channel in channels:
        device = _open_force_phidget_channel(channel)
        if device is None:
            _close_force_phidget_devices(opened)
            return None
        opened.append(device)
    return opened


def _close_force_phidget_devices(devices: list) -> None:
    for device in devices:
        try:
            device.close()
        except Exception:
            pass


def _open_force_phidget():
    """First channel that attaches (legacy single-channel probe)."""
    for channel in (0, 1, 2, 3):
        device = _open_force_phidget_channel(channel)
        if device is not None:
            return device
    return None


class PowerMeterThread(QThread):
    """Live Thorlabs PM100A power. Missing hardware stays unconnected."""

    sample = Signal(float, float)  # t_s, milliwatts
    source_changed = Signal(str)

    def __init__(self, use_hardware: bool = True, wavelength_nm: float = 385.0):
        super().__init__()
        self.use_hardware = use_hardware
        self.wavelength_nm = float(wavelength_nm)
        self._stop = False
        self.period_s = 0.25

    def stop(self) -> None:
        self._stop = True

    def set_wavelength_nm(self, wavelength_nm: float) -> None:
        self.wavelength_nm = float(wavelength_nm)

    def run(self) -> None:
        if not self.use_hardware:
            self.source_changed.emit("not connected")
            while not self._stop:
                self.msleep(200)
            return

        from calibration_modules.thorlabs_pm100a import PowerMeterError, ThorlabsPM100A

        meter = None
        applied_nm = None
        t0 = time.perf_counter()
        reported = ""
        self.source_changed.emit("connecting")
        try:
            while not self._stop:
                if meter is None:
                    try:
                        meter = ThorlabsPM100A(wavelength_nm=self.wavelength_nm)
                        identity = meter.connect()
                        applied_nm = meter.wavelength_nm
                        print(f"Power meter: {identity} at {applied_nm:.0f} nm")
                    except (PowerMeterError, OSError, ValueError) as exc:
                        print(f"Power meter not connected: {exc}")
                        if meter is not None:
                            meter.close()
                        meter = None
                        if reported != "not connected":
                            self.source_changed.emit("not connected")
                            reported = "not connected"
                        self.msleep(1000)
                        continue
                if applied_nm is None or abs(self.wavelength_nm - applied_nm) > 0.5:
                    try:
                        applied_nm = meter.set_wavelength_nm(self.wavelength_nm)
                    except (PowerMeterError, OSError, ValueError) as exc:
                        print(f"Power meter wavelength change failed, reconnecting: {exc}")
                        meter.close()
                        meter = None
                        continue
                try:
                    reading = meter.read_power()
                except (PowerMeterError, OSError, ValueError) as exc:
                    print(f"Power meter read failed, reconnecting: {exc}")
                    meter.close()
                    meter = None
                    if reported != "not connected":
                        self.source_changed.emit("not connected")
                        reported = "not connected"
                    continue
                if reported != "live":
                    self.source_changed.emit("live")
                    reported = "live"
                self.sample.emit(time.perf_counter() - t0, reading.milliwatts)
                self.msleep(int(self.period_s * 1000))
        finally:
            if meter is not None:
                meter.close()


class PhysicsThread(QThread):
    """Simulated print progress and optical intensity for an arbitrary part."""

    dose_sample = Signal(float, float)  # t_s, measured_intensity_mW_cm2
    print_state = Signal(object)  # dict

    def __init__(self):
        super().__init__()
        self._stop = False
        self.force_period_s = 0.05

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        t0 = time.perf_counter()
        total_layers = 120
        layer_period_s = 4.0
        layer_height_mm = 0.05
        exposure_s = 2.5
        led_current_mA = 100.0
        rng = np.random.default_rng(7)

        while not self._stop:
            elapsed = time.perf_counter() - t0
            layer_index = min(total_layers - 1, int(elapsed / layer_period_s))
            phase = (elapsed % layer_period_s) / layer_period_s

            intensity = 14.2 + 0.35 * np.sin(elapsed * 0.7) + float(rng.normal(0.0, 0.05))
            self.dose_sample.emit(elapsed, float(intensity))

            progress = min(100.0, 100.0 * elapsed / (total_layers * layer_period_s))
            remaining_s = max(0.0, total_layers * layer_period_s - elapsed)
            z_mm = (layer_index + phase) * layer_height_mm
            self.print_state.emit(
                {
                    "state": "COMPLETE" if progress >= 100.0 else "PRINTING",
                    "z_mm": z_mm,
                    "layer": layer_index + 1,
                    "total_layers": total_layers,
                    "progress": progress,
                    "remaining_s": remaining_s,
                    "exposure_s": exposure_s,
                    "intensity": float(intensity),
                    "layer_height_mm": layer_height_mm,
                    "led_current_mA": led_current_mA,
                }
            )
            self.msleep(50)


def _peel_model(phase: float) -> float:
    """One peel pulse per layer: rapid rise, exponential separation decay."""
    if phase < 0.08:
        return 0.15
    if phase < 0.22:
        return 0.15 + 2.6 * ((phase - 0.08) / 0.14)
    return 2.75 * np.exp(-(phase - 0.22) / 0.16) + 0.08


def _optical_pattern(frame_idx: int) -> np.ndarray:
    height, width = 480, 640
    img = np.zeros((height, width), dtype=np.uint8)
    img[::32, :] = 36
    img[:, ::32] = 36
    cx, cy = width // 2, height // 2
    yy, xx = np.ogrid[:height, :width]
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    vat = ((dist < 180) * 28).astype(np.uint8)
    img = np.maximum(img, vat)
    angle = (frame_idx % 90) * (2 * np.pi / 90)
    ox = int(cx + 90 * np.cos(angle))
    oy = int(cy + 70 * np.sin(angle))
    meniscus = (xx - ox) ** 2 + (yy - oy) ** 2 <= 18 ** 2
    img[meniscus] = 210
    img[cy - 1 : cy + 2, :] = 160
    img[:, cx - 1 : cx + 2] = 160
    return img


def _thermal_pattern(frame_idx: int) -> np.ndarray:
    height, width = 240, 320
    yy, xx = np.mgrid[0:height, 0:width]
    cx = width / 2 + 18 * np.sin(frame_idx / 12.0)
    cy = height / 2 + 10 * np.cos(frame_idx / 15.0)
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    blob = np.exp(-(dist ** 2) / (2 * 28 ** 2))
    ambient = 23.4 + 0.15 * np.sin(frame_idx / 20.0)
    exotherm = 8.5 * blob * (0.65 + 0.35 * np.sin(frame_idx / 8.0))
    return (ambient + exotherm).astype(np.float32)


PIXEL_MM = 0.004005  # Prince projected pixel pitch, 4.005 µm
LAYER_HEIGHT_MM = 0.05
VOLUME_SAMPLE = 48


def slice_mask(layer_index: int, size: int = 280) -> np.ndarray:
    """Binary projected mask for the current layer. White is exposed."""
    img = np.zeros((size, size), dtype=np.uint8)
    yy, xx = np.mgrid[0:size, 0:size]
    pitch = 46
    radius = 10 + (layer_index % 12)
    for gy in range(24, size - 12, pitch):
        for gx in range(24, size - 12, pitch):
            mask = (xx - gx) ** 2 + (yy - gy) ** 2 <= radius ** 2
            img[mask] = 255
    return img


def layer_areas_mm2(mask: np.ndarray, pixel_mm: float = PIXEL_MM) -> tuple[float, float]:
    """Return (total exposed area, largest connected region) in mm²."""
    binary = (mask > 127).astype(np.uint8)
    total_px = int(binary.sum())
    _count, _labels, stats, _centroids = cv2.connectedComponentsWithStats(binary, connectivity=8)
    peak_px = 0
    if stats.shape[0] > 1:
        peak_px = int(stats[1:, cv2.CC_STAT_AREA].max())
    pixel_area = pixel_mm * pixel_mm
    return total_px * pixel_area, peak_px * pixel_area


@dataclass
class PrintJob:
    """Sliced part loaded from a Prince image directory."""

    paths: list[Path]
    exposure_s: list[float]
    thickness_um: list[float]
    total_areas: list[float]
    peak_areas: list[float]
    powers: list[float]
    volume: np.ndarray
    width_mm: float
    height_mm: float
    layer_height_mm: float
    print_volume_mm3: float


def _sorted_images(directory: Path) -> list[Path]:
    images: list[Path] = []
    for pattern in ("*.png", "*.bmp", "*.tif", "*.tiff", "*.jpg", "*.jpeg"):
        images.extend(directory.glob(pattern))

    def order(path: Path) -> tuple[int, str]:
        numbers = re.findall(r"\d+", path.stem)
        return (int(numbers[-1]) if numbers else 10**9, path.name.lower())

    return sorted(images, key=order)


def load_print_job(directory: str | Path) -> PrintJob | None:
    """Read the instruction file, or the images themselves, into a print job."""
    root = Path(directory)
    if not root.is_dir():
        print(f"Print job: directory not found: {root}")
        return None

    paths: list[Path] = []
    exposures: list[float] = []
    thicknesses: list[float] = []
    powers: list[float] = []
    instruction = root / f"{root.name}.txt"
    if instruction.is_file():
        lines = [
            line.strip()
            for line in instruction.read_text(encoding="utf-8", errors="ignore").splitlines()
            if line.strip()
        ]
        start = 1 if lines and not lines[0][:1].isdigit() else 0
        for line in lines[start:]:
            parts = line.split("\t")
            if len(parts) < 4:
                continue
            image_path = root / parts[1]
            if not image_path.is_file():
                image_path = root / Path(parts[1]).name
            paths.append(image_path)
            try:
                thicknesses.append(float(parts[2]))
                exposures.append(float(parts[3]))
            except ValueError:
                thicknesses.append(50.0)
                exposures.append(0.0)
            try:
                powers.append(float(parts[4]) if len(parts) > 4 else float("nan"))
            except ValueError:
                powers.append(float("nan"))
    if not paths:
        paths = _sorted_images(root)
        exposures = [0.0] * len(paths)
        thicknesses = [50.0] * len(paths)
        powers = [float("nan")] * len(paths)
    if not paths:
        print(f"Print job: no layer images in {root}")
        return None

    total_areas: list[float] = []
    peak_areas: list[float] = []
    volume = np.zeros((VOLUME_SAMPLE, VOLUME_SAMPLE, len(paths)), dtype=np.uint8)
    width_mm = height_mm = 0.0
    for index, path in enumerate(paths):
        image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if image is None:
            total_areas.append(0.0)
            peak_areas.append(0.0)
            continue
        if width_mm == 0.0:
            height_mm = image.shape[0] * PIXEL_MM
            width_mm = image.shape[1] * PIXEL_MM
        total_area, peak_area = layer_areas_mm2((image >= 250).astype(np.uint8) * 255, PIXEL_MM)
        total_areas.append(total_area)
        peak_areas.append(peak_area)
        small = cv2.resize(image, (VOLUME_SAMPLE, VOLUME_SAMPLE), interpolation=cv2.INTER_AREA)
        volume[:, :, index] = (small.T >= 128).astype(np.uint8)
        if index % 25 == 0:
            print(f"Print job: loaded layer {index + 1}/{len(paths)}")

    positive = [value / 1000.0 for value in thicknesses if value > 0]
    layer_height_mm = float(np.mean(positive)) if positive else LAYER_HEIGHT_MM
    print_volume_mm3 = sum(
        area * (thickness / 1000.0 if thickness > 0 else layer_height_mm)
        for area, thickness in zip(total_areas, thicknesses)
    )
    print(f"Print job: {len(paths)} layers from {root}")
    return PrintJob(
        paths=paths,
        exposure_s=exposures,
        thickness_um=thicknesses,
        total_areas=total_areas,
        peak_areas=peak_areas,
        powers=powers,
        volume=volume,
        width_mm=width_mm,
        height_mm=height_mm,
        layer_height_mm=layer_height_mm,
        print_volume_mm3=print_volume_mm3,
    )


CALIBRATION_PATH = Path(__file__).resolve().parents[2] / "data" / "uv_power_calibration.json"
COMMAND_LOW = 10.0
COMMAND_HIGH = 100.0


@dataclass
class UvPowerCalibration:
    """Optical power measured while the same image is projected at two LED settings."""

    measured_mW_at_10: float | None = None
    measured_mW_at_200: float | None = None
    area_mm2: float | None = None
    command_low: float = COMMAND_LOW
    command_high: float = COMMAND_HIGH

    def densities_mW_cm2(self) -> tuple[float, float] | None:
        """Power density at the two stored LED commands. None until both readings and an area exist."""
        if (
            self.measured_mW_at_10 is None
            or self.measured_mW_at_200 is None
            or self.area_mm2 is None
            or self.area_mm2 <= 0
            or self.command_high == self.command_low
        ):
            return None
        area_cm2 = self.area_mm2 / 100.0
        return self.measured_mW_at_10 / area_cm2, self.measured_mW_at_200 / area_cm2


def load_power_calibration() -> UvPowerCalibration:
    try:
        raw = json.loads(CALIBRATION_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return UvPowerCalibration()
    return UvPowerCalibration(
        measured_mW_at_10=_optional_float(raw.get("measured_mW_at_10")),
        measured_mW_at_200=_optional_float(raw.get("measured_mW_at_200")),
        area_mm2=_optional_float(raw.get("area_mm2")),
        command_low=_optional_float(raw.get("command_low")) or COMMAND_LOW,
        command_high=_optional_float(raw.get("command_high")) or COMMAND_HIGH,
    )


def save_power_calibration(calibration: UvPowerCalibration) -> None:
    CALIBRATION_PATH.parent.mkdir(parents=True, exist_ok=True)
    CALIBRATION_PATH.write_text(
        json.dumps(
            {
                "measured_mW_at_10": calibration.measured_mW_at_10,
                "measured_mW_at_200": calibration.measured_mW_at_200,
                "area_mm2": calibration.area_mm2,
                "command_low": calibration.command_low,
                "command_high": calibration.command_high,
            }
        ),
        encoding="utf-8",
    )


def power_density_mW_cm2(command: float, calibration: UvPowerCalibration) -> float | None:
    """Linear power density from the two calibration points, across commands 1–255."""
    pair = calibration.densities_mW_cm2()
    if pair is None or float(command) <= 0:
        return 0.0 if pair is not None else None
    low, high = pair
    span = float(calibration.command_high) - float(calibration.command_low)
    if span == 0:
        return None
    slope = (high - low) / span
    return low + slope * (float(command) - float(calibration.command_low))


def expected_power_mW(command: float, area_mm2: float, calibration: UvPowerCalibration) -> float | None:
    """Expected meter reading: power density at this LED command, times this layer's area."""
    density = power_density_mW_cm2(command, calibration)
    if density is None:
        return None
    if float(area_mm2) <= 0:
        return 0.0
    return density * (float(area_mm2) / 100.0)


def _optional_float(value) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(number):
        return None
    return number
