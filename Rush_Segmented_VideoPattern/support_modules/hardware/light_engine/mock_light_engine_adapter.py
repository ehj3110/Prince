"""Mock light-engine adapter for dry-run validation."""


class MockLightEngineAdapter:
    def __init__(self):
        self.connected = False
        self.mode = "idle"
        self.last_power = 0

    def connect(self) -> None:
        self.connected = True

    def disconnect(self) -> None:
        self.connected = False

    def enter_dark_idle(self) -> None:
        self.mode = "dark_idle"
        self.last_power = 0

    def arm_video_pattern_mode(self, silent_wake_power: int, settle_s: float, color_mask: str) -> None:
        self.mode = "video_pattern"
        self.last_power = int(silent_wake_power)

    def set_exposure_power(self, current_0_255: int) -> None:
        self.last_power = int(current_0_255)

    def blackout_power_off(self) -> None:
        self.last_power = 0

    def restore_next_layer_power(self, current_0_255: int) -> None:
        self.last_power = int(current_0_255)

    def standby(self) -> None:
        self.mode = "standby"
