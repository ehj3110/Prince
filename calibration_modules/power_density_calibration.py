#!/usr/bin/env python3
"""Project Power_255.png and record UV power density at LED power 10 and 100.

The light engine is driven with Prince_Segmented.MyWindow's print sequence.
This script does not construct MyWindow, so it does not home the Zaber stage.

    .\\.conda\\python.exe -m calibration_modules.power_density_calibration
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import screeninfo

from Prince_Segmented import MyWindow
import pycrafter9000
from calibration_modules.monitoring_dashboard.workers import (
    PIXEL_MM,
    UvPowerCalibration,
    save_power_calibration,
)
from calibration_modules.thorlabs_pm100a import ThorlabsPM100A

DEFAULT_IMAGE = Path(r"C:\Users\cheng sun\BoyuanSun\Slicing\Calibration\Power_255\Power_255.png")
REPO_IMAGE = Path(__file__).resolve().parents[1] / "Power_255.png"
WINDOW_NAME = "show"
WAVELENGTH_NM = 385.0
LED_POWERS = (10, 100)
RANGE_LIMIT = 0.75
RANGE_REQUESTS_W = (1.0e-6, 3.0e-5, 3.0e-4, 3.0e-3)
STABILIZE_S = 4.0
HOLD_S = 3.0


def white_area_mm2(image: np.ndarray) -> tuple[int, float]:
    """Prince white-pixel area: pixels at or above 250, pitch 4.005 µm."""
    gray = image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    count = int(np.count_nonzero(gray >= 250))
    return count, count * PIXEL_MM * PIXEL_MM


def hold_range(meter: ThorlabsPM100A, request_w: float) -> tuple[float, float, float]:
    """Set one range and average the settled reading. Does not step the range itself."""
    meter.set_auto_range(False)
    meter.write(f"SENS:POW:RANG {request_w:.6E}")
    full_scale = meter.get_power_range_w()
    time.sleep(1.0)
    samples: list[float] = []
    deadline = time.perf_counter() + HOLD_S
    while time.perf_counter() < deadline:
        samples.append(meter._measure_watts() * 1000.0)
        time.sleep(0.25)
    mean_mw = float(np.mean(samples))
    fraction = abs(mean_mw / 1000.0) / full_scale if full_scale else float("inf")
    return full_scale, mean_mw, fraction


def measure_across_ranges(meter: ThorlabsPM100A) -> tuple[float, float, float]:
    """Try each power range and keep the tightest scale that is still under 75% full."""
    usable: list[tuple[float, float, float]] = []
    for request_w in RANGE_REQUESTS_W:
        full_scale, mean_mw, fraction = hold_range(meter, request_w)
        clipped = fraction >= RANGE_LIMIT or abs(mean_mw) > 1.0e6
        print(
            f"  range {full_scale:.3e} W ({fraction:.0%} of full scale): "
            f"{mean_mw:.4f} mW{'  clipped' if clipped else ''}"
        )
        if not clipped and 0.02 <= fraction < 0.40:
            usable.append((fraction, mean_mw, full_scale))
    if not usable:
        raise RuntimeError("No power range held the reading between 2% and 40% of full scale.")
    _fraction, milliwatts, full_scale = max(usable)
    return milliwatts, full_scale, _fraction


def measure_stable(meter: ThorlabsPM100A, seconds: float = 3.0) -> tuple[float, float, float]:
    """Average readings that are under 75% of the current full scale.

    read_power steps the range up when a sample reaches that fraction.
    """
    time.sleep(1.0)
    samples: list[float] = []
    full_scale = 0.0
    fraction = 1.0
    deadline = time.perf_counter() + seconds
    while time.perf_counter() < deadline:
        reading = meter.read_power()
        full_scale = meter.get_power_range_w()
        fraction = abs(reading.watts) / full_scale if full_scale else 1.0
        if fraction < RANGE_LIMIT:
            samples.append(reading.milliwatts)
        time.sleep(0.25)
    if len(samples) < 4:
        raise RuntimeError(
            f"Reading stayed at {fraction:.0%} of the {full_scale:.3e} W range. "
            "It needs to be under 75% of full scale."
        )
    return float(np.mean(samples)), full_scale, fraction


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Calibrate UV power density at LED power 10 and 100.")
    parser.add_argument("--image", type=Path, default=DEFAULT_IMAGE)
    args = parser.parse_args(argv)
    image_path = args.image if args.image.is_file() else REPO_IMAGE
    image = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
    if image is None:
        print(f"Could not read {image_path}", file=sys.stderr)
        return 1
    white_count, area_mm2 = white_area_mm2(image)
    if white_count <= 0 or area_mm2 <= 0:
        print(f"{image_path} has no white pixels.", file=sys.stderr)
        return 1
    print(f"Image: {image_path}")
    print(f"White pixels: {white_count} ({white_count ** 0.5:.0f} px on a side)")
    print(f"Area: {area_mm2:.4f} mm²")

    screen = screeninfo.get_monitors()[0]
    black = np.zeros((1600, 2560), dtype=np.uint8)
    controller = None
    window_open = False
    measured: dict[int, float] = {}
    try:
        with ThorlabsPM100A(wavelength_nm=WAVELENGTH_NM) as meter:
            print(f"Wavelength: {meter.get_wavelength_nm():.2f} nm")
            controller = pycrafter9000.dmd()
            MyWindow.open_projection_window(screen, WINDOW_NAME, black)
            window_open = True
            MyWindow.enter_pattern_mode(controller)
            MyWindow.show_projection(WINDOW_NAME, image)
            for led_power in LED_POWERS:
                MyWindow.set_projection_power(controller, led_power)
                print(f"Power {led_power}: waiting {STABILIZE_S:.0f} s for the beam to settle")
                time.sleep(STABILIZE_S)
                milliwatts, full_scale, fraction = measure_across_ranges(meter)
                density = milliwatts / (area_mm2 / 100.0)
                measured[led_power] = milliwatts
                print(
                    f"Power {led_power}: {milliwatts:.4f} mW, "
                    f"range {full_scale:.3e} W ({fraction:.0%} of full scale), "
                    f"density {density:.4f} mW/cm²"
                )
    except Exception as exc:
        print(f"Power density calibration failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if controller is not None:
            MyWindow.release_light_engine(
                controller,
                WINDOW_NAME if window_open else None,
                black if window_open else None,
                close_usb=True,
            )

    if set(measured) != set(LED_POWERS):
        return 1
    calibration = UvPowerCalibration(
        measured_mW_at_10=measured[10],
        measured_mW_at_200=measured[100],
        area_mm2=area_mm2,
        command_low=10.0,
        command_high=100.0,
    )
    save_power_calibration(calibration)
    low, high = calibration.densities_mW_cm2()
    print(f"Saved density {low:.4f} mW/cm² at power 10 and {high:.4f} mW/cm² at power 100.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
