"""Zaber-backed stage adapter implementation."""

from typing import Optional

from zaber_motion import Units


class ZaberStageAdapter:
    def __init__(self, axis):
        self.axis = axis

    def connect(self) -> None:
        # Connection lifecycle currently handled by caller.
        return None

    def disconnect(self) -> None:
        try:
            self.axis.stop()
        except Exception:
            pass

    def home(self, wait_until_idle: bool = True) -> None:
        self.axis.home(wait_until_idle=wait_until_idle)

    def move_absolute_um(
        self,
        position_um: float,
        velocity_um_s: Optional[float] = None,
        accel_um_s2: Optional[float] = None,
        wait_until_idle: bool = True,
    ) -> None:
        kwargs = {
            "position": position_um,
            "unit": Units.LENGTH_MICROMETRES,
            "wait_until_idle": wait_until_idle,
        }
        if velocity_um_s is not None:
            kwargs["velocity"] = velocity_um_s
            kwargs["velocity_unit"] = Units.VELOCITY_MICROMETRES_PER_SECOND
        if accel_um_s2 is not None:
            kwargs["acceleration"] = accel_um_s2
            kwargs["acceleration_unit"] = Units.ACCELERATION_MICROMETRES_PER_SECOND_SQUARED
        self.axis.move_absolute(**kwargs)

    def move_relative_um(
        self,
        delta_um: float,
        velocity_um_s: Optional[float] = None,
        accel_um_s2: Optional[float] = None,
        wait_until_idle: bool = True,
    ) -> None:
        kwargs = {
            "position": delta_um,
            "unit": Units.LENGTH_MICROMETRES,
            "wait_until_idle": wait_until_idle,
        }
        if velocity_um_s is not None:
            kwargs["velocity"] = velocity_um_s
            kwargs["velocity_unit"] = Units.VELOCITY_MICROMETRES_PER_SECOND
        if accel_um_s2 is not None:
            kwargs["acceleration"] = accel_um_s2
            kwargs["acceleration_unit"] = Units.ACCELERATION_MICROMETRES_PER_SECOND_SQUARED
        self.axis.move_relative(**kwargs)

    def get_position_um(self) -> float:
        return self.axis.get_position(unit=Units.LENGTH_MICROMETRES)

    def wait_until_idle(self) -> None:
        self.axis.wait_until_idle()

    def stop(self) -> None:
        self.axis.stop()

    def get_fault_flags(self):
        return self.axis.warnings.get_flags()
