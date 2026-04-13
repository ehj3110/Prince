"""Seam module for stage movement orchestration."""

from support_modules.hardware.interfaces import IStageAdapter


class StageSequencer:
    def __init__(self, stage: IStageAdapter):
        self.stage = stage

    def move_continuous_to_target(
        self,
        target_um: float,
        velocity_um_s: float,
        accel_um_s2: float,
        wait_until_idle: bool,
    ) -> None:
        self.stage.move_absolute_um(
            position_um=target_um,
            velocity_um_s=velocity_um_s,
            accel_um_s2=accel_um_s2,
            wait_until_idle=wait_until_idle,
        )

    def wait_until_idle(self) -> None:
        self.stage.wait_until_idle()

    def execute_stepped_peel_return(
        self,
        peel_peak_um: float,
        return_um: float,
        velocity_um_s: float,
        accel_um_s2: float,
    ) -> None:
        self.stage.move_absolute_um(
            position_um=peel_peak_um,
            velocity_um_s=velocity_um_s,
            accel_um_s2=accel_um_s2,
            wait_until_idle=True,
        )
        self.stage.move_absolute_um(
            position_um=return_um,
            velocity_um_s=velocity_um_s,
            accel_um_s2=accel_um_s2,
            wait_until_idle=True,
        )

    def get_position_um(self) -> float:
        return self.stage.get_position_um()

    def stop(self) -> None:
        self.stage.stop()
