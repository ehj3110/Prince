"""Composition helper for hardware adapters."""

from dataclasses import dataclass

from .interfaces import ILightEngineAdapter, IStageAdapter


@dataclass
class HardwareContext:
    stage: IStageAdapter
    light_engine: ILightEngineAdapter

    def connect_all(self) -> None:
        self.stage.connect()
        self.light_engine.connect()

    def disconnect_all(self) -> None:
        # Idempotent teardown ordering: light first, then stage.
        try:
            self.light_engine.disconnect()
        finally:
            self.stage.disconnect()
