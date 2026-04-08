#!/usr/bin/env python3
"""Smoke test for modular stage/light architecture.

This validates basic behavior through the new abstraction stack using mock adapters:
- HardwareContext lifecycle
- DLPLightController transitions
- StageSequencer movement operations
- PrintOrchestrator basic execution calls
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass

ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from support_modules.DLPLightController import DLPLightController
from support_modules.StageSequencer import StageSequencer
from support_modules.hardware.hardware_context import HardwareContext
from support_modules.hardware.light_engine.mock_light_engine_adapter import MockLightEngineAdapter
from support_modules.hardware.stage.mock_stage_adapter import MockStageAdapter
from support_modules.print_engine.print_orchestrator import PrintOrchestrator, PrintOrchestratorDeps


@dataclass
class DummyFrameManager:
    black_shown: int = 0
    frame_shown: int = 0

    def show_frame(self, _frame):
        self.frame_shown += 1

    def show_black(self):
        self.black_shown += 1


def _status(msg: str):
    print(f"[STATUS] {msg}")


def run_smoke() -> None:
    stage = MockStageAdapter()
    light_engine = MockLightEngineAdapter()

    ctx = HardwareContext(stage=stage, light_engine=light_engine)
    ctx.connect_all()

    assert stage.connected, "Stage should be connected"
    assert light_engine.connected, "Light engine should be connected"

    light_controller = DLPLightController(light_engine)
    stage_sequencer = StageSequencer(stage)
    frame_manager = DummyFrameManager()

    orchestrator = PrintOrchestrator(
        PrintOrchestratorDeps(
            stage_sequencer=stage_sequencer,
            light_controller=light_controller,
            frame_manager=frame_manager,
            status_callback=_status,
        )
    )

    # Light engine basics
    light_controller.enter_dark_idle()
    assert light_engine.mode == "dark_idle", "Expected dark_idle mode"
    assert light_engine.last_power == 0, "Expected power 0 after dark idle"

    orchestrator.initialize_projection(silent_wake_power=35, settle_s=0.01, color_mask="100")
    assert light_engine.mode == "video_pattern", "Expected video_pattern mode"
    assert light_engine.last_power == 35, "Expected silent wake power"

    orchestrator.begin_layer_exposure(power_0_255=80, frame=None)
    assert light_engine.last_power == 80, "Expected layer exposure power"

    orchestrator.end_layer_blackout()
    assert light_engine.last_power == 0, "Expected blackout power"
    assert frame_manager.black_shown >= 1, "Expected black frame shown"

    orchestrator.restore_next_layer_power(55)
    assert light_engine.last_power == 55, "Expected restored next-layer power"

    # Stage basics
    stage.home()
    assert abs(stage.get_position_um()) < 1e-9, "Expected home position 0"

    stage_sequencer.move_continuous_to_target(
        target_um=1200,
        velocity_um_s=300,
        accel_um_s2=1000,
        wait_until_idle=True,
    )
    assert abs(stage.get_position_um() - 1200) < 1e-9, "Expected stage at 1200 um"

    stage_sequencer.execute_stepped_peel_return(
        peel_peak_um=600,
        return_um=950,
        velocity_um_s=300,
        accel_um_s2=1000,
    )
    assert abs(stage.get_position_um() - 950) < 1e-9, "Expected stage return at 950 um"

    orchestrator.safe_shutdown()
    assert light_engine.mode == "standby", "Expected standby after shutdown"

    ctx.disconnect_all()
    assert not stage.connected, "Stage should be disconnected"
    assert not light_engine.connected, "Light engine should be disconnected"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeat", type=int, default=1, help="Number of times to run smoke loop")
    args = parser.parse_args()

    t0 = time.time()
    for _ in range(max(1, args.repeat)):
        run_smoke()
    dt = time.time() - t0
    print(f"PASS: modular stage/light architecture smoke test completed in {dt:.3f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
