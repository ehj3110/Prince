#!/usr/bin/env python3
"""Connect to a Thorlabs PM100A and print live power for 10 seconds.

Run from the repository root:

    .\\.conda\\python.exe -m calibration_modules.thorlabs_pm100a_stream_test
"""

from __future__ import annotations

import argparse
import sys
import time

from calibration_modules.thorlabs_pm100a import (
    PowerMeterError,
    PowerMeterNotFoundError,
    ThorlabsPM100A,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Stream live PM100A optical power.")
    parser.add_argument("--wavelength-nm", type=float, default=ThorlabsPM100A.DEFAULT_WAVELENGTH_NM)
    parser.add_argument("--seconds", type=float, default=10.0)
    parser.add_argument("--hz", type=float, default=4.0, help="Readout rate, between 2 and 5 Hz.")
    parser.add_argument("--resource", default=None, help="VISA resource name. Auto-detect when omitted.")
    args = parser.parse_args(argv)

    if not 2.0 <= args.hz <= 5.0:
        print("Readout rate must be between 2 and 5 Hz.", file=sys.stderr)
        return 2
    period = 1.0 / args.hz

    try:
        with ThorlabsPM100A(resource=args.resource, wavelength_nm=args.wavelength_nm) as meter:
            print(f"Identity: {meter.identity}")
            print(f"Resource: {meter.resource_name}")
            print(f"Backend: {meter.backend}")
            print(f"Wavelength: {meter.get_wavelength_nm():.2f} nm")
            print(f"Unit: {meter.get_power_unit()}")
            print(f"Streaming at {args.hz:.1f} Hz for {args.seconds:.0f} s")
            deadline = time.perf_counter() + args.seconds
            samples = 0
            while time.perf_counter() < deadline:
                started = time.perf_counter()
                reading = meter.read_power()
                samples += 1
                print(f"{reading.milliwatts:12.6f} mW   ({reading.watts:.6e} W)")
                remaining = period - (time.perf_counter() - started)
                if remaining > 0:
                    time.sleep(remaining)
    except PowerMeterNotFoundError as exc:
        print(f"Power meter not found: {exc}", file=sys.stderr)
        return 1
    except PowerMeterError as exc:
        print(f"Power meter did not respond: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Power meter test failed: {exc}", file=sys.stderr)
        return 2

    print(f"Collected {samples} samples.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
