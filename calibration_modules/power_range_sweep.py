#!/usr/bin/env python3
"""Project stent layer 1 and hold several meter ranges at each LED power.

Reads with a raw measurement so the 75% step-up does not change the range
under test. Each range is held for a few seconds before the mean is taken.

    .\\.conda\\python.exe -m calibration_modules.power_range_sweep
"""

from __future__ import annotations

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
)
from calibration_modules.power_density_calibration import WAVELENGTH_NM, WINDOW_NAME, white_area_mm2
from calibration_modules.thorlabs_pm100a import ThorlabsPM100A

IMAGE = Path(r"C:\Users\cheng sun\BoyuanSun\Slicing\Evan\Old Prince\Prince_Stent\1.png")
LED_POWERS = (10, 50, 100, 200)
# Requests spaced across the watt ranges this sensor has used.
RANGE_REQUESTS_W = (1.0e-6, 3.0e-5, 3.0e-4, 3.0e-3)
HOLD_S = 3.0
RESULT_PATH = Path(__file__).resolve().parents[1] / "data" / "stent_layer1_range_sweep.csv"


def settle_on_range(meter: ThorlabsPM100A, request_w: float) -> tuple[float, float, float, str]:
    """Set one range, wait, and return full scale, mean mW, fraction, and current range."""
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
    fraction = abs(mean_mw / 1000.0) / full_scale if full_scale else float("nan")
    try:
        current_range = meter.query("SENS:CURR:RANG?")
    except Exception:
        current_range = ""
    return full_scale, mean_mw, fraction, current_range


def main() -> int:
    image = cv2.imread(str(IMAGE), cv2.IMREAD_UNCHANGED)
    if image is None:
        print(f"Could not read {IMAGE}", file=sys.stderr)
        return 1
    _count, area_mm2 = white_area_mm2(image)
    calibration = load_power_calibration()
    screen = screeninfo.get_monitors()[0]
    black = np.zeros((1600, 2560), dtype=np.uint8)
    controller = None
    window_open = False
    rows: list[dict[str, object]] = []
    try:
        with ThorlabsPM100A(wavelength_nm=WAVELENGTH_NM) as meter:
            print(f"Layer 1 area {area_mm2:.4f} mm², wavelength {meter.get_wavelength_nm():.2f} nm")
            controller = pycrafter9000.dmd()
            MyWindow.open_projection_window(screen, WINDOW_NAME, black)
            window_open = True
            MyWindow.enter_pattern_mode(controller)
            MyWindow.show_projection(WINDOW_NAME, image)
            for led_power in LED_POWERS:
                expected = expected_power_mW(led_power, area_mm2, calibration)
                MyWindow.set_projection_power(controller, led_power)
                print(f"Power {led_power}, expected {expected:.4f} mW")
                for request_w in RANGE_REQUESTS_W:
                    full_scale, measured, fraction, current_range = settle_on_range(meter, request_w)
                    error = None if not expected else 100.0 * (measured - expected) / expected
                    print(
                        f"  request {request_w:.1e} W -> range {full_scale:.3e} W "
                        f"({fraction:.0%}), measured {measured:.4f} mW, "
                        f"error {error:.1f}%, current range {current_range or 'n/a'}"
                    )
                    rows.append(
                        {
                            "led_power": led_power,
                            "expected_mW": f"{expected:.6f}",
                            "requested_range_W": f"{request_w:.6e}",
                            "full_scale_W": f"{full_scale:.6e}",
                            "measured_mW": f"{measured:.6f}",
                            "error_percent": f"{error:.2f}",
                            "range_fraction": f"{fraction:.4f}",
                            "current_range": current_range,
                        }
                    )
    except Exception as exc:
        print(f"Range sweep failed: {exc}", file=sys.stderr)
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
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved {RESULT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
