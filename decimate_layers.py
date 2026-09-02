#!/usr/bin/env python3
"""
Delete every other image in a folder to convert 24 um layers to 48 um.

Default behavior is a dry run (no files deleted).
Use --apply to actually delete files.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

IMAGE_EXTENSIONS = {".png", ".bmp", ".tif", ".tiff", ".jpg", ".jpeg"}


def natural_key(path: Path):
    """Sort paths naturally so layer_2 comes before layer_10."""
    parts = re.split(r"(\d+)", path.name.lower())
    return [int(p) if p.isdigit() else p for p in parts]


def find_images(folder: Path) -> list[Path]:
    return sorted(
        [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS],
        key=natural_key,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Delete every other image in a folder (for layer decimation)."
    )
    parser.add_argument(
        "folder",
        nargs="?",
        default=r"C:\Users\cheng sun\BoyuanSun\Slicing\Mirae\Mirae_DiscreteWoodpile_OneScaffold_24um - Copy",
        help="Folder containing layer images.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete files. Without this flag, script runs as dry-run.",
    )
    parser.add_argument(
        "--keep-odd",
        action="store_true",
        help="Keep odd-indexed files and delete even-indexed files (default keeps even-indexed).",
    )

    args = parser.parse_args()
    folder = Path(args.folder)

    if not folder.exists() or not folder.is_dir():
        print(f"ERROR: Folder not found or not a directory: {folder}")
        return 1

    images = find_images(folder)
    if not images:
        print(f"No image files found in: {folder}")
        return 1

    # Default behavior: keep indices 0,2,4... and delete 1,3,5...
    # Use --keep-odd to flip behavior.
    if args.keep_odd:
        to_delete = [img for i, img in enumerate(images) if i % 2 == 0]
    else:
        to_delete = [img for i, img in enumerate(images) if i % 2 == 1]

    to_keep = [img for img in images if img not in to_delete]

    print(f"Folder: {folder}")
    print(f"Total images found: {len(images)}")
    print(f"Will keep: {len(to_keep)}")
    print(f"Will delete: {len(to_delete)}")
    print()

    preview_count = min(10, len(to_delete))
    if preview_count > 0:
        print("Preview of files to delete:")
        for p in to_delete[:preview_count]:
            print(f"  {p.name}")
        if len(to_delete) > preview_count:
            print(f"  ... and {len(to_delete) - preview_count} more")
        print()

    if not args.apply:
        print("Dry run only. No files were deleted.")
        print("Re-run with --apply to perform deletion.")
        return 0

    deleted = 0
    for p in to_delete:
        p.unlink()
        deleted += 1

    print(f"Done. Deleted {deleted} files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
