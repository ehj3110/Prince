"""Mock stage adapter for dry-run validation."""

from typing import Optional


class MockStageAdapter:
    def __init__(self):
        self.position_um = 0.0
        self.connected = False

    def connect(self) -> None:
        self.connected = True

    def disconnect(self) -> None:
        self.connected = False

    def home(self, wait_until_idle: bool = True) -> None:
        self.position_um = 0.0

    def move_absolute_um(
        self,
        position_um: float,
        velocity_um_s: Optional[float] = None,
        accel_um_s2: Optional[float] = None,
        wait_until_idle: bool = True,
    ) -> None:
        self.position_um = float(position_um)

    def move_relative_um(
        self,
        delta_um: float,
        velocity_um_s: Optional[float] = None,
        accel_um_s2: Optional[float] = None,
        wait_until_idle: bool = True,
    ) -> None:
        self.position_um += float(delta_um)

    def get_position_um(self) -> float:
        return self.position_um

    def wait_until_idle(self) -> None:
        return None

    def stop(self) -> None:
        return None

    def get_fault_flags(self):
        return None
