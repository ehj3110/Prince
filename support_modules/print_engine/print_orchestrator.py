"""Parallel-path print orchestrator for modular stage/light operations."""

from dataclasses import dataclass
from typing import Any, Callable, Optional
import time


@dataclass
class PrintOrchestratorDeps:
    stage_sequencer: Any
    light_controller: Any
    frame_manager: Any
    status_callback: Callable[[str], None]


class PrintOrchestrator:
    def __init__(self, deps: PrintOrchestratorDeps):
        self.deps = deps

    def initialize_projection(self, silent_wake_power: int, settle_s: float, color_mask: str) -> None:
        self.deps.light_controller.enter_dark_idle()
        self.deps.light_controller.arm_video_pattern_mode(silent_wake_power, settle_s, color_mask)
        time.sleep(max(0.0, float(settle_s)))
        self.deps.status_callback("Modular path: projection initialized")

    def begin_layer_exposure(self, power_0_255: int, frame: Optional[Any] = None) -> None:
        self.deps.light_controller.set_exposure_power(power_0_255)
        if frame is not None:
            self.deps.frame_manager.show_frame(frame)

    def end_layer_blackout(self) -> None:
        self.deps.frame_manager.show_black()
        self.deps.light_controller.movement_blackout()

    def restore_next_layer_power(self, power_0_255: int) -> None:
        self.deps.light_controller.restore_next_layer_power(power_0_255)

    def execute_continuous_move(self, target_um: float, velocity_um_s: float, accel_um_s2: float, wait_until_idle: bool) -> None:
        self.deps.stage_sequencer.move_continuous_to_target(
            target_um=target_um,
            velocity_um_s=velocity_um_s,
            accel_um_s2=accel_um_s2,
            wait_until_idle=wait_until_idle,
        )

    def execute_stepped_move(self, peel_peak_um: float, return_um: float, velocity_um_s: float, accel_um_s2: float) -> None:
        self.deps.stage_sequencer.execute_stepped_peel_return(
            peel_peak_um=peel_peak_um,
            return_um=return_um,
            velocity_um_s=velocity_um_s,
            accel_um_s2=accel_um_s2,
        )

    def safe_shutdown(self) -> None:
        self.deps.frame_manager.show_black()
        self.deps.light_controller.movement_blackout()
        self.deps.light_controller.standby()
        self.deps.status_callback("Modular path: safe shutdown complete")

    def run(self, *args, **kwargs):
        self.deps.status_callback("Modular print orchestrator ready (legacy path remains selectable).")
        return True
