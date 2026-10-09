"""Standalone monitoring dashboard. Prince does not need to be open.

    .\\.conda\\python.exe -m calibration_modules.monitoring_dashboard
    .\\.conda\\python.exe -m calibration_modules.monitoring_dashboard --image-dir PATH

Hardware mode (the default) reads the Alvium, the Seek thermal camera, the
Phidget force gauge, and the Thorlabs PM100A. --image-dir loads that folder's
slices into the geometry card and shows layer 1. A sensor with no data is grayed out.
"""

from __future__ import annotations

import argparse
import os
import sys

os.environ.setdefault("QT_API", "pyside6")

from PySide6.QtWidgets import QApplication

from .window import MonitoringDashboard


def main() -> int:
    parser = argparse.ArgumentParser(description="Prince monitoring dashboard")
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Skip hardware cameras and the force gauge",
    )
    parser.add_argument(
        "--image-dir",
        default="",
        help="Prince image directory whose slices fill the geometry card",
    )
    parser.add_argument(
        "--triple-force",
        action="store_true",
        help="Sum Phidget bridge channels 0–2 using MODE=TRIPLE calibration (also auto on that file)",
    )
    parser.add_argument(
        "--single-force",
        action="store_true",
        help="Use one bridge channel only (overrides triple calibration file)",
    )
    args = parser.parse_args()
    force_triple = None
    if args.triple_force:
        force_triple = True
    elif args.single_force:
        force_triple = False
    app = QApplication(sys.argv)
    window = MonitoringDashboard(
        use_hardware=not args.mock,
        image_dir=args.image_dir or None,
        force_triple=force_triple,
    )
    window.show()
    code = app.exec()
    # Leave no thread behind. A lingering process can keep an inherited
    # DLPC900 USB handle open after Prince itself has closed.
    os._exit(code)


if __name__ == "__main__":
    raise SystemExit(main())
