"""
Prince Modern — PySide6 entry point for the printer control GUI.

Visual shell matches the Modern mockup (dark purple cards). Print and hardware
logic run through a withdrawn copy of Prince_Segmented_Unified (see
prince_modern_unified_source.py) so behavior stays at Unified parity while the
UI is rebuilt.

Launch (preferred):
  .\\.conda\\python.exe Prince_Modern.py
  or double-click Launch_Prince_Modern.bat
"""

from __future__ import annotations

import os
import sys


REPO = os.path.dirname(os.path.abspath(__file__))
CONDA_PYTHON = os.path.join(REPO, ".conda", "python.exe")


def _reexec_with_conda_if_needed() -> None:
    """Double-click / wrong python often lacks PySide6; bounce to .conda."""
    if os.environ.get("PRINCE_MODERN_BOOTSTRAPPED") == "1":
        return
    try:
        import PySide6  # noqa: F401
        return
    except ImportError:
        pass
    if not os.path.isfile(CONDA_PYTHON):
        print(
            "PySide6 is not installed for this Python, and "
            f".conda\\python.exe was not found at:\n  {CONDA_PYTHON}\n"
            "Install PySide6 or run:\n  .\\.conda\\python.exe Prince_Modern.py",
            file=sys.stderr,
        )
        raise SystemExit(1)
    if os.path.normcase(os.path.abspath(sys.executable)) == os.path.normcase(
        os.path.abspath(CONDA_PYTHON)
    ):
        print(
            "PySide6 is missing even in .conda\\python.exe. "
            "Install with:\n  .\\.conda\\python.exe -m pip install PySide6",
            file=sys.stderr,
        )
        raise SystemExit(1)
    env = os.environ.copy()
    env["PRINCE_MODERN_BOOTSTRAPPED"] = "1"
    print(f"Restarting with project Python:\n  {CONDA_PYTHON}")
    os.execve(CONDA_PYTHON, [CONDA_PYTHON, os.path.abspath(__file__), *sys.argv[1:]], env)


_reexec_with_conda_if_needed()

# Prefer project packages.
if REPO not in sys.path:
    sys.path.insert(0, REPO)
SUPPORT = os.path.join(REPO, "support_modules")
if SUPPORT not in sys.path:
    sys.path.insert(0, SUPPORT)

os.environ.setdefault("QT_API", "pyside6")

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from prince_modern.controller import ModernController
from prince_modern.main_window import ModernMainWindow
from prince_modern.theme import load_fonts


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Prince Modern")
    families = load_fonts()
    if families:
        app.setFont(QFont("Inter", 13))
    window = ModernMainWindow()
    controller = ModernController(window)

    _orig_close = window.closeEvent

    def on_close(event):
        controller.shutdown()
        _orig_close(event)

    window.closeEvent = on_close  # type: ignore[method-assign]
    window.show()
    from PySide6.QtCore import QTimer

    QTimer.singleShot(100, controller.start)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
