#!/usr/bin/env python3
"""Project a few Prince_Stent layers and compare measured power with the calibration.

Uses the same light-engine sequence as a print, and the saved 10 / 100 density line.
Does not construct MyWindow, so the stage is not homed.

    .\\.conda\\python.exe -m calibration_modules.power_expected_stress_test
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import screeninfo

from Prince_Segmented import MyWindow
import pycrafter9000
from calibration_modules.monitoring_dashboard.workers import (
    expected_power_mW,
    load_power_calibration,
    power_density_mW_cm2,
)
from calibration_modules.power_density_calibration import (
    WAVELENGTH_NM,
    WINDOW_NAME,
    measure_stable,
    white_area_mm2,
)
from calibration_modules.thorlabs_pm100a import ThorlabsPM100A

DEFAULT_DIR = Path(r"C:\Users\cheng sun\BoyuanSun\Slicing\Evan\Old Prince\Prince_Stent")
DEFAULT_POWERS = (10, 50, 100, 200)
RESULT_PATH = Path(__file__).resolve().parents[1] / "data" / "stent_power_comparison.csv"


def layer_paths(directory: Path) -> list[Path]:
    images = [path for path in directory.glob("*.png") if path.stem.isdigit()]

    def order(path: Path) -> int:
        return int(path.stem)

    return sorted(images, key=order)


def pick_layers(images: list[Path], count: int) -> list[Path]:
    if count >= len(images):
        return images
    if count <= 1:
        return [images[len(images) // 2]]
    indexes = [round(i * (len(images) - 1) / (count - 1)) for i in range(count)]
    return [images[index] for index in indexes]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare expected and measured stent-layer power.")
    parser.add_argument("--image-dir", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--powers", type=int, nargs="+", default=list(DEFAULT_POWERS))
    parser.add_argument("--layers", type=int, default=3, help="How many layers to sample across the folder.")
    args = parser.parse_args(argv)

    images = layer_paths(args.image_dir)
    if not images:
        print(f"No numbered PNG layers in {args.image_dir}", file=sys.stderr)
        return 1
    chosen = pick_layers(images, args.layers)
    calibration = load_power_calibration()
    if calibration.densities_mW_cm2() is None:
        print("Power density calibration is missing. Run power_density_calibration first.", file=sys.stderr)
        return 1

    print(
        f"Density line: {calibration.command_low:.0f} -> "
        f"{power_density_mW_cm2(calibration.command_low, calibration):.3f} mW/cm², "
        f"{calibration.command_high:.0f} -> "
        f"{power_density_mW_cm2(calibration.command_high, calibration):.3f} mW/cm²"
    )
    jobs: list[tuple[Path, np.ndarray, float]] = []
    for path in chosen:
        image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
        if image is None:
            print(f"Could not read {path}", file=sys.stderr)
            return 1
        _count, area_mm2 = white_area_mm2(image)
        jobs.append((path, image, area_mm2))
        print(f"Layer {path.name}: {area_mm2:.4f} mm²")

    screen = screeninfo.get_monitors()[0]
    black = np.zeros((1600, 2560), dtype=np.uint8)
    controller = None
    window_open = False
    rows: list[dict[str, object]] = []
    failed = False
    try:
        with ThorlabsPM100A(wavelength_nm=WAVELENGTH_NM) as meter:
            print(f"Wavelength: {meter.get_wavelength_nm():.2f} nm")
            controller = pycrafter9000.dmd()
            MyWindow.open_projection_window(screen, WINDOW_NAME, black)
            window_open = True
            MyWindow.enter_pattern_mode(controller)
            for path, image, area_mm2 in jobs:
                MyWindow.show_projection(WINDOW_NAME, image)
                for led_power in args.powers:
                    expected = expected_power_mW(led_power, area_mm2, calibration)
                    MyWindow.set_projection_power(controller, led_power)
                    try:
                        measured, full_scale, fraction = measure_stable(meter)
                        error = None if not expected else 100.0 * (measured - expected) / expected
                        print(
                            f"{path.name}  power {led_power:3d}  "
                            f"expected {expected:.4f} mW  measured {measured:.4f} mW  "
                            f"error {error:.1f}%  range {fraction:.0%} of {full_scale:.3e} W"
                        )
                    except Exception as exc:
                        failed = True
                        measured = float("nan")
                        full_scale = float("nan")
                        fraction = float("nan")
                        error = float("nan")
                        print(f"{path.name}  power {led_power}: {exc}", file=sys.stderr)
                    rows.append(
                        {
                            "layer": path.name,
                            "area_mm2": f"{area_mm2:.6f}",
                            "led_power": led_power,
                            "expected_mW": "" if expected is None else f"{expected:.6f}",
                            "measured_mW": f"{measured:.6f}",
                            "error_percent": "" if error is None else f"{error:.2f}",
                            "range_fraction": f"{fraction:.4f}",
                            "full_scale_W": f"{full_scale:.6e}",
                        }
                    )
    except Exception as exc:
        print(f"Stress test failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if controller is not None:
            MyWindow.release_light_engine(
                controller,
                WINDOW_NAME if window_open else None,
                black if window_open else None,
                close_usb=True,
            )

    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with RESULT_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()) if rows else ["layer"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved {RESULT_PATH}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
