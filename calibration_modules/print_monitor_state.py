"""Shared print position for the monitoring dashboard.

Prince writes one small JSON file when the layer changes. The dashboard
reads it. The two processes do not share memory.
"""

from __future__ import annotations

import json
from pathlib import Path

STATE_PATH = Path(__file__).resolve().parents[1] / "data" / "monitor_print_state.json"


def write_print_monitor_state(*, layer: int, power: float, running: bool) -> None:
    """Publish the layer on the projector and its commanded power, 0–255."""
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "layer": int(layer),
        "power": float(power),
        "running": bool(running),
    }
    temporary = STATE_PATH.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload), encoding="utf-8")
    temporary.replace(STATE_PATH)


def read_print_monitor_state() -> dict | None:
    """Return the latest published state, or None when Prince has not written one."""
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return None
