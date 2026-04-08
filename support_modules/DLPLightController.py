"""Seam module for DLP light-engine sequencing and power control."""

from support_modules.hardware.interfaces import ILightEngineAdapter


class DLPLightController:
    def __init__(self, light_engine: ILightEngineAdapter):
        self.light_engine = light_engine
        self.last_power = None

    def enter_dark_idle(self) -> None:
        self.light_engine.enter_dark_idle()
        self.last_power = 0

    def arm_video_pattern_mode(self, silent_wake_power: int, settle_s: float, color_mask: str) -> None:
        self.light_engine.arm_video_pattern_mode(
            silent_wake_power=silent_wake_power,
            settle_s=settle_s,
            color_mask=color_mask,
        )
        self.last_power = int(silent_wake_power)

    def set_exposure_power(self, power_0_255: int) -> None:
        power_0_255 = int(power_0_255)
        if self.last_power == power_0_255:
            return
        self.light_engine.set_exposure_power(power_0_255)
        self.last_power = power_0_255

    def movement_blackout(self) -> None:
        self.light_engine.blackout_power_off()
        self.last_power = 0

    def restore_next_layer_power(self, power_0_255: int) -> None:
        self.light_engine.restore_next_layer_power(int(power_0_255))
        self.last_power = int(power_0_255)

    def standby(self) -> None:
        self.light_engine.standby()
