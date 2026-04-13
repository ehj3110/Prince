"""Hardware adapter interfaces for stage and light engine."""

from typing import Any, Optional, Protocol, runtime_checkable


@runtime_checkable
class IStageAdapter(Protocol):
    def connect(self) -> None:
        ...

    def disconnect(self) -> None:
        ...

    def home(self, wait_until_idle: bool = True) -> None:
        ...

    def move_absolute_um(
        self,
        position_um: float,
        velocity_um_s: Optional[float] = None,
        accel_um_s2: Optional[float] = None,
        wait_until_idle: bool = True,
    ) -> None:
        ...

    def move_relative_um(
        self,
        delta_um: float,
        velocity_um_s: Optional[float] = None,
        accel_um_s2: Optional[float] = None,
        wait_until_idle: bool = True,
    ) -> None:
        ...

    def get_position_um(self) -> float:
        ...

    def wait_until_idle(self) -> None:
        ...

    def stop(self) -> None:
        ...

    def get_fault_flags(self) -> Any:
        ...


@runtime_checkable
class ILightEngineAdapter(Protocol):
    def connect(self) -> None:
        ...

    def disconnect(self) -> None:
        ...

    def enter_dark_idle(self) -> None:
        ...

    def arm_video_pattern_mode(self, silent_wake_power: int, settle_s: float, color_mask: str) -> None:
        ...

    def set_exposure_power(self, current_0_255: int) -> None:
        ...

    def blackout_power_off(self) -> None:
        ...

    def restore_next_layer_power(self, current_0_255: int) -> None:
        ...

    def standby(self) -> None:
        ...
