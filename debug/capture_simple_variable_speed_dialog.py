# -*- coding: utf-8 -*-
"""Capture a screenshot of the Simple Variable Speed Qt dialog."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from prince_modern.simple_variable_speed_dialog import SimpleVariableSpeedDialog  # noqa: E402

FOLDER = Path(r"C:\Users\cheng sun\BoyuanSun\Slicing\Evan\Cone_R500_0_To2500_0_H5000_0_LH50_0")
OUT = REPO / "documentation" / "analysis_summaries" / "simple_variable_speed_dialog_preview.png"


def main() -> None:
    app = QApplication(sys.argv)
    dlg = SimpleVariableSpeedDialog(folder=FOLDER)
    dlg.show()

    # Demo values so the screenshot looks like a filled operator session.
    dlg.speed.set_user_value(1000.0)
    dlg.dose.set_user_value(5.0)
    dlg.size.set_user_value(0.785)
    dlg.correction.set_user_value(1.0)
    dlg.control_layer.setValue(50)
    dlg.fill_holes.setChecked(False)
    dlg.max_hole_um.set_user_value(1000.0)

    def _finish() -> None:
        # Run Update so the plot panes show real content.
        try:
            dlg._on_update()
        except Exception as exc:  # pragma: no cover
            dlg.status.setText(f"Update skipped: {exc}")
        app.processEvents()
        pix = dlg.grab()
        OUT.parent.mkdir(parents=True, exist_ok=True)
        pix.save(str(OUT))
        print(
            f"Saved: {OUT} size={dlg.width()}x{dlg.height()}",
            flush=True,
        )
        dlg.close()
        app.quit()

    # Allow the window to paint, then capture after preview.
    QTimer.singleShot(400, _finish)
    app.exec()


if __name__ == "__main__":
    main()
