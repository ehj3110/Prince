"""DLP9000 (pycrafter9000) light-engine adapter implementation."""

import cv2


class DLP9000LightEngineAdapter:
    def __init__(self, controller):
        self.controller = controller
        self.last_power = None

    def connect(self) -> None:
        return None

    def disconnect(self) -> None:
        try:
            self.standby()
        except Exception:
            pass

    def enter_dark_idle(self) -> None:
        self.controller.power(current=0)
        cv2.waitKey(1)
        self.controller.stopsequence()
        cv2.waitKey(1)
        self.controller.changemode(0x03)
        cv2.waitKey(1)
        self.last_power = 0

    def arm_video_pattern_mode(self, silent_wake_power: int, settle_s: float, color_mask: str) -> None:
        # Keep startup sequence aligned with known-good flow.
        self.controller.stopsequence()
        cv2.waitKey(1)
        self.controller.power(current=0)
        cv2.waitKey(1)
        self.controller.changemode(0x00)
        cv2.waitKey(1)
        self.controller.hdmi()
        cv2.waitKey(1)
        self.controller.changemode(0x02)
        cv2.waitKey(1)
        self.controller.configurelut(1, 0xFFFFFFFF)
        cv2.waitKey(1)
        self.controller.definepattern(
            index=0,
            exposure=0,
            bitdepth=8,
            color=color_mask,
            triggerin=False,
            darktime=0,
            triggerout=False,
            patind=0,
            bitpos=0,
        )
        cv2.waitKey(1)
        self.controller.startsequence()
        cv2.waitKey(1)
        self.controller.power(current=int(silent_wake_power))
        cv2.waitKey(1)
        self.last_power = int(silent_wake_power)
        # Caller handles sleep(settle_s) to keep timing control in orchestrator.

    def set_exposure_power(self, current_0_255: int) -> None:
        self.controller.power(current=int(current_0_255))
        cv2.waitKey(1)
        self.last_power = int(current_0_255)

    def blackout_power_off(self) -> None:
        self.controller.power(current=0)
        cv2.waitKey(1)
        self.last_power = 0

    def restore_next_layer_power(self, current_0_255: int) -> None:
        self.set_exposure_power(current_0_255)

    def standby(self) -> None:
        self.controller.standby()
