#!/usr/bin/env python3
"""
export_image_gui.py
-------------------
Copies the ImageModificationWindow GUI and all its dependencies into a
self-contained export folder ready to zip and send to another computer.

Usage (run from the project root):
    python export_image_gui.py [--out <destination_folder>]

The other computer only needs Python 3.8+ installed. On first run it will
create a virtual-env and install the small set of required packages via
launch_image_modification.bat.
"""

import argparse
import shutil
from pathlib import Path

# Files / folders relative to project root that must be included
INCLUDE = [
    "support_modules/ImageModificationWindow.py",
    "support_modules/image_modification/__init__.py",
    "support_modules/image_modification/edge_enhancement.py",
    "support_modules/image_modification/global_enhancement.py",
    "support_modules/image_modification/padding.py",
    "support_modules/image_modification/processor.py",
    "support_modules/image_modification/scattering_compensation.py",
    "requirements_image_gui.txt",
    "launch_image_modification.bat",
]


def export(out_dir: Path, project_root: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    missing = []
    for rel in INCLUDE:
        src = project_root / rel
        if not src.exists():
            missing.append(rel)
            continue
        dst = out_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        print(f"  copied  {rel}")

    if missing:
        print("\nWARNING – these files were not found and were skipped:")
        for m in missing:
            print(f"  MISSING  {m}")

    print(f"\nExport complete → {out_dir}")
    print("Zip that folder and copy it to the target machine.")
    print("On the target machine: double-click launch_image_modification.bat")


def main():
    parser = argparse.ArgumentParser(description="Export ImageModificationWindow GUI")
    parser.add_argument("--out", default="ImageModificationGUI_export",
                        help="Destination folder (default: ImageModificationGUI_export)")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent
    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = project_root / out_dir

    export(out_dir, project_root)


if __name__ == "__main__":
    main()
