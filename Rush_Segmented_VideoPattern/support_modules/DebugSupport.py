"""
Shared debug helpers for Prince support modules.

Use this module to keep normal runs quiet while still allowing a central
debug mode to emit very verbose terminal output when needed.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, Optional


def _env_enabled(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on", "debug"}


def is_debug_mode_enabled() -> bool:
    """Return True when debug mode is enabled via environment variable."""
    return _env_enabled(os.getenv("PRINCE_DEBUG_MODE", ""))


@dataclass
class DebugSupport:
    """Small shared helper for gated debug output."""

    enabled: bool = False
    prefix: str = "DEBUG"
    callback: Optional[Callable[[str], None]] = None

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)

    def emit(self, message: str, *, force: bool = False) -> None:
        if force or self.enabled:
            text = f"{self.prefix}: {message}" if self.prefix else message
            if self.callback:
                self.callback(text)
            else:
                print(text)


debug_support = DebugSupport(enabled=is_debug_mode_enabled())


def set_debug_mode(enabled: bool) -> None:
    """Enable or disable shared debug output."""
    debug_support.set_enabled(enabled)


def debug_print(message: str, *, force: bool = False) -> None:
    """Print only when debug mode is enabled, unless forced."""
    debug_support.emit(message, force=force)
