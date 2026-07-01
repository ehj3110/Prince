# -*- coding: utf-8 -*-
"""
Standalone launcher for the Ramped Cylinder window.

Run this script to open the Ramped Cylinder GUI for testing and inspection.

Usage:
    python run_ramped_cylinder_standalone.py
"""

import sys
from pathlib import Path

# Add project root and support_modules to path
project_root = Path(__file__).parent
support_modules = project_root / "support_modules"
sys.path.insert(0, str(project_root))
if str(support_modules) not in sys.path:
    sys.path.insert(0, str(support_modules))

from tkinter import Tk


def main():
    root = Tk()
    root.withdraw()  # Hide the root window; only the Ramped Cylinder window will be visible

    from support_modules.image_modification.ramped_cylinder import RampedCylinderWindow

    app = RampedCylinderWindow(
        master_window=root,
        update_status_callback=lambda msg, err=False: print(msg),
        prince_main_app_ref=None,
    )

    # When standalone, quit the app when the user closes the window
    def on_close():
        app._on_close()
        root.quit()

    app.window.protocol("WM_DELETE_WINDOW", on_close)

    root.mainloop()


if __name__ == "__main__":
    main()
