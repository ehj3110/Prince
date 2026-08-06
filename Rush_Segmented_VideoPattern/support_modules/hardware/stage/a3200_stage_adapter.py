"""A3200-backed stage adapter implementation for Rush."""

import logging
import socket
import threading
import time
from typing import Optional

from zaber_motion import Units


class A3200StageAdapter:
    IDLE_STATUS_CODE = "4202508"

    def __init__(self, host: str = "localhost", port: int = 8000, axis_name: str = "Z"):
        self.host = host
        self.port = port
        self.axis_name = axis_name
        self._socket: Optional[socket.socket] = None
        self._connected = False
        # Shared socket must be serialized across print thread and live-readout thread.
        self._io_lock = threading.RLock()

    def connect(self) -> None:
        if self._connected:
            return
        self._socket = socket.create_connection((self.host, self.port), timeout=10.0)
        # Keep a generous read timeout for long controller responses while waiting-idle.
        self._socket.settimeout(30.0)
        self._connected = True
        self._prime_controller()
        logging.info("A3200 stage connected on %s:%s", self.host, self.port)

    def disconnect(self) -> None:
        try:
            self.stop()
        except Exception:
            pass
        if self._socket is not None:
            try:
                self._socket.close()
            finally:
                self._socket = None
                self._connected = False

    def home(self, wait_until_idle: bool = True) -> None:
        return None

    def move_absolute_um(
        self,
        position_um: float,
        velocity_um_s: Optional[float] = None,
        accel_um_s2: Optional[float] = None,
        wait_until_idle: bool = True,
    ) -> None:
        self._prime_controller()
        self._write_read(f"MOVEABS {self.axis_name} {float(position_um) / 1000.0} {self._normalize_velocity(velocity_um_s)}")
        if wait_until_idle:
            self.wait_until_idle()

    def move_relative_um(
        self,
        delta_um: float,
        velocity_um_s: Optional[float] = None,
        accel_um_s2: Optional[float] = None,
        wait_until_idle: bool = True,
    ) -> None:
        self._prime_controller()
        self._write_read(f"MOVEINC {self.axis_name} {float(delta_um) / 1000.0} {self._normalize_velocity(velocity_um_s)}")
        if wait_until_idle:
            self.wait_until_idle()

    def move_absolute(
        self,
        position,
        unit=None,
        wait_until_idle: bool = True,
        velocity=None,
        velocity_unit=None,
        acceleration=None,
        acceleration_unit=None,
    ) -> None:
        self.move_absolute_um(
            self._convert_position_to_um(position, unit),
            velocity_um_s=self._convert_velocity_to_um_s(velocity, velocity_unit),
            wait_until_idle=wait_until_idle,
        )

    def move_relative(
        self,
        position,
        unit=None,
        wait_until_idle: bool = True,
        velocity=None,
        velocity_unit=None,
        acceleration=None,
        acceleration_unit=None,
    ) -> None:
        self.move_relative_um(
            self._convert_position_to_um(position, unit),
            velocity_um_s=self._convert_velocity_to_um_s(velocity, velocity_unit),
            wait_until_idle=wait_until_idle,
        )

    def get_position_um(self) -> float:
        return self._get_position_um()

    def get_position(self, unit=Units.LENGTH_MILLIMETRES):
        position_um = self._get_position_um()
        if unit == Units.LENGTH_MICROMETRES:
            return position_um
        return position_um / 1000.0

    def wait_until_idle(self) -> None:
        if not self._connected:
            return
        timeout_retries = 0
        while True:
            try:
                status = self._write_read(f"AXISSTATUS({self.axis_name}, DATAITEM_AxisStatus)")
                timeout_retries = 0
            except TimeoutError:
                timeout_retries += 1
                # Transient timeouts can happen under heavy concurrent polling; retry a few times.
                if timeout_retries <= 3:
                    logging.warning("A3200 wait_until_idle timeout (%s/3), retrying", timeout_retries)
                    continue
                raise
            if status == self.IDLE_STATUS_CODE:
                return
            time.sleep(0.01)

    def is_busy(self) -> bool:
        if not self._connected:
            return False
        return self._write_read(f"AXISSTATUS({self.axis_name}, DATAITEM_AxisStatus)") != self.IDLE_STATUS_CODE

    def stop(self) -> None:
        if not self._connected:
            return
        try:
            self._write_read(f"STOP {self.axis_name}")
        except Exception:
            pass

    def get_fault_flags(self):
        if not self._connected:
            return None
        try:
            return self._write_read(f"AXISSTATUS({self.axis_name}, DATAITEM_AxisStatus)")
        except Exception:
            return None

    def _prime_controller(self) -> None:
        self._write_read("BLOCKMOTION X Y 1")
        self._write_read(f"BLOCKMOTION {self.axis_name} 0")
        self._write_read(f"ENABLE {self.axis_name}")

    def _normalize_velocity(self, velocity_um_s: Optional[float]) -> float:
        if velocity_um_s is None:
            return 5.0
        return float(velocity_um_s) / 1000.0

    def _convert_position_to_um(self, value, unit) -> float:
        if unit == Units.LENGTH_MILLIMETRES:
            return float(value) * 1000.0
        return float(value)

    def _convert_velocity_to_um_s(self, value, unit) -> Optional[float]:
        if value is None:
            return None
        if unit == Units.VELOCITY_MILLIMETRES_PER_SECOND:
            return float(value) * 1000.0
        return float(value)

    def _get_position_um(self) -> float:
        response = self._write_read(f"AXISSTATUS({self.axis_name}, DATAITEM_PositionCommand)")
        try:
            return float(response) * 1000.0
        except (TypeError, ValueError):
            return 0.0

    def _write_read(self, command: str) -> str:
        if not self._connected or self._socket is None:
            raise RuntimeError("A3200 stage is not connected.")
        if not command.endswith("\n"):
            command = f"{command}\n"
        with self._io_lock:
            self._socket.sendall(command.encode("ascii"))
            response = self._socket.recv(4096).decode("ascii", errors="ignore").strip()
        if not response:
            return ""
        code = response[0]
        payload = response[1:]
        if code != "%":
            logging.error("A3200 command error: %s %s", code, payload)
        return payload