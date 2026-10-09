"""Thorlabs PM100A optical power meter over NI-VISA / USBTMC.

Uses PyVISA SCPI only. The system VISA library (NI-VISA, after the Thorlabs
Driver Switcher) is preferred. ``@py`` is used only when that library is absent.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

_THORLABS_USB = re.compile(r"^USB\d*::0x1313::.*::INSTR$", re.IGNORECASE)


class PowerMeterError(Exception):
    """The meter was found but did not complete a command."""


class PowerMeterNotFoundError(PowerMeterError):
    """No Thorlabs PM100 USB instrument answered VISA."""


@dataclass(frozen=True)
class PowerReading:
    """One optical-power sample."""

    watts: float
    milliwatts: float


class ThorlabsPM100A:
    """PM100A console on USB vendor 0x1313.

    Wavelength values on this class are nanometers. 385 nm matches the UV source.
    """

    VENDOR_ID = 0x1313
    DEFAULT_WAVELENGTH_NM = 385.0
    TIMEOUT_MS = 2000

    def __init__(
        self,
        resource: Optional[str] = None,
        wavelength_nm: float = DEFAULT_WAVELENGTH_NM,
        backend: Optional[str] = None,
    ) -> None:
        self.resource_name = resource
        self.wavelength_nm = float(wavelength_nm)
        self.identity = ""
        self.backend = ""
        self._backend_request = backend
        self._rm = None
        self._inst = None
        self._power_unit = "W"
        self._range_w: Optional[float] = None

    def __enter__(self) -> "ThorlabsPM100A":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def connect(self) -> str:
        """Open the console, check ``*IDN?``, and apply wavelength and watts."""
        if self._inst is not None:
            return self.identity

        pyvisa = _import_pyvisa()
        self._rm = _open_resource_manager(pyvisa, self._backend_request)
        self.backend = str(getattr(self._rm, "visalib", ""))
        name = self.resource_name or self.find_resource(self._rm)
        self.resource_name = name
        try:
            inst = self._rm.open_resource(name)
        except Exception as exc:
            self.close()
            raise PowerMeterError(f"Could not open {name}: {exc}") from exc

        inst.timeout = self.TIMEOUT_MS
        inst.read_termination = "\n"
        inst.write_termination = "\n"
        self._inst = inst
        try:
            self.identity = self.query("*IDN?")
        except PowerMeterError:
            self.close()
            raise
        if not _looks_like_power_meter(self.identity):
            found = self.identity
            self.close()
            raise PowerMeterError(f"{name} answered *IDN? as {found!r}, which is not a PM100 meter.")

        self.set_power_unit("W")
        self.set_auto_range(False)
        self._range_w = self.get_power_range_w()
        print(
            f"Power meter range {self._range_w:.3e} W. "
            "Hardware auto-range is off; the next range is selected at 75% of full scale."
        )
        self.set_wavelength_nm(self.wavelength_nm)
        return self.identity

    def close(self) -> None:
        """Release the USB instrument. Safe to call more than once."""
        inst = self._inst
        rm = self._rm
        self._inst = None
        self._rm = None
        self._range_w = None
        if inst is not None:
            try:
                inst.close()
            except Exception:
                pass
        if rm is not None:
            try:
                rm.close()
            except Exception:
                pass

    def find_resource(self, resource_manager=None) -> str:
        """Return the VISA name of a connected PM100.

        Searches ``USB*<n>::0x1313::...::INSTR``. When several Thorlabs USB
        instruments are present, the one whose identity contains PM100A wins.
        """
        rm = resource_manager or self._rm
        if rm is None:
            pyvisa = _import_pyvisa()
            rm = _open_resource_manager(pyvisa, self._backend_request)
            own_manager = True
        else:
            own_manager = False
        try:
            return _select_pm100(rm)
        finally:
            if own_manager:
                rm.close()

    def query(self, command: str) -> str:
        if self._inst is None:
            raise PowerMeterError("Power meter is not open.")
        try:
            return str(self._inst.query(command)).strip()
        except Exception as exc:
            raise PowerMeterError(f"No response to {command}: {exc}") from exc

    def write(self, command: str) -> None:
        if self._inst is None:
            raise PowerMeterError("Power meter is not open.")
        try:
            self._inst.write(command)
        except Exception as exc:
            raise PowerMeterError(f"Command failed ({command}): {exc}") from exc

    def set_wavelength_nm(self, wavelength_nm: float) -> float:
        """Set the sensor wavelength correction. ``wavelength_nm`` is nanometers."""
        requested = float(wavelength_nm)
        if requested <= 0:
            raise ValueError("Wavelength must be positive.")
        self.write(f"SENS:CORR:WAV {requested}")
        raw = _first_float(self.query("SENS:CORR:WAV?"))
        if _near(raw, requested):
            self.wavelength_nm = raw
            return raw
        # Some PM100 firmware stores this command in meters.
        if raw < 0.01:
            self.write(f"SENS:CORR:WAV {requested * 1e-9}")
            raw = _first_float(self.query("SENS:CORR:WAV?"))
        self.wavelength_nm = raw * 1e9 if raw < 0.01 else raw
        return self.wavelength_nm

    def get_wavelength_nm(self) -> float:
        raw = _first_float(self.query("SENS:CORR:WAV?"))
        if abs(raw) < 0.01:
            return raw * 1e9
        return raw

    def set_power_unit(self, unit: str) -> str:
        """Select ``W`` or ``dBm``."""
        token = _unit_token(unit)
        self.write(f"SENS:POW:UNIT {token}")
        self._power_unit = self.get_power_unit()
        return self._power_unit

    def get_power_unit(self) -> str:
        return self.query("SENS:POW:UNIT?").upper()

    def set_auto_range(self, enabled: bool = True) -> None:
        self.write(f"SENS:POW:RANG:AUTO {'ON' if enabled else 'OFF'}")

    def get_power_range_w(self) -> float:
        """Full-scale power of the range in use, in watts."""
        self._range_w = _first_float(self.query("SENS:POW:RANG?"))
        return self._range_w

    def _raise_power_range(self) -> bool:
        """Select the next higher power range. False when the meter is already at the top."""
        current = self._range_w if self._range_w and self._range_w > 0 else self.get_power_range_w()
        self.write(f"SENS:POW:RANG {current * 2.0:.6E}")
        updated = self.get_power_range_w()
        if updated <= current * 1.01:
            return False
        print(f"Power meter range {current:.3e} W -> {updated:.3e} W")
        return True

    def read_power(self) -> PowerReading:
        """Read one sample with ``MEAS:POW?`` and return watts and milliwatts.

        When the reading reaches 75% of the current full scale, the next range is
        selected and the measurement is repeated. The range is never lowered.
        """
        watts = self._measure_watts()
        for _ in range(6):
            full_scale = self._range_w if self._range_w and self._range_w > 0 else self.get_power_range_w()
            if full_scale <= 0 or abs(watts) < 0.75 * full_scale:
                break
            if not self._raise_power_range():
                break
            watts = self._measure_watts()
        return PowerReading(watts=watts, milliwatts=watts * 1000.0)

    def _measure_watts(self) -> float:
        reported = _first_float(self.query("MEAS:POW?"))
        return _as_watts(reported, self._power_unit)


def _import_pyvisa():
    try:
        import pyvisa
    except ImportError as exc:
        raise PowerMeterError(
            "pyvisa is not installed. Install pyvisa and pyvisa-py in the project environment."
        ) from exc
    return pyvisa


def _open_resource_manager(pyvisa, backend: Optional[str]):
    if backend:
        try:
            return pyvisa.ResourceManager(backend)
        except Exception as exc:
            raise PowerMeterError(f"VISA backend {backend!r} did not load: {exc}") from exc
    try:
        return pyvisa.ResourceManager()
    except Exception as ni_error:
        try:
            return pyvisa.ResourceManager("@py")
        except Exception as py_error:
            raise PowerMeterError(
                f"Neither NI-VISA nor pyvisa-py loaded. NI-VISA: {ni_error}. pyvisa-py: {py_error}."
            ) from py_error


def _select_pm100(resource_manager) -> str:
    try:
        resources = list(resource_manager.list_resources())
    except Exception as exc:
        raise PowerMeterError(f"Could not list VISA resources: {exc}") from exc

    thorlabs = [name for name in resources if _THORLABS_USB.match(name)]
    if not thorlabs:
        shown = ", ".join(resources) if resources else "(none)"
        raise PowerMeterNotFoundError(
            "No Thorlabs USB instrument matching USB*::0x1313::...::INSTR. "
            f"VISA resources: {shown}."
        )

    ranked: list[tuple[int, str]] = []
    failures: list[str] = []
    for name in thorlabs:
        try:
            with resource_manager.open_resource(name) as inst:
                inst.timeout = ThorlabsPM100A.TIMEOUT_MS
                inst.read_termination = "\n"
                inst.write_termination = "\n"
                identity = str(inst.query("*IDN?")).strip()
        except Exception as exc:
            failures.append(f"{name}: {exc}")
            continue
        if not _looks_like_power_meter(identity):
            failures.append(f"{name}: {identity}")
            continue
        rank = 0 if "PM100A" in identity.upper() else 1
        ranked.append((rank, name))

    if not ranked:
        detail = "; ".join(failures) if failures else "no instrument responded"
        raise PowerMeterNotFoundError(f"Thorlabs USB devices did not identify as a PM100. {detail}.")
    ranked.sort()
    return ranked[0][1]


def _looks_like_power_meter(identity: str) -> bool:
    text = identity.upper()
    return any(model in text for model in ("PM100", "PM160", "PM200", "PM400"))


def _unit_token(unit: str) -> str:
    text = unit.strip().upper()
    if text in {"W", "WATT", "WATTS"}:
        return "W"
    if text in {"DBM", "D BM"}:
        return "DBM"
    raise ValueError("Power unit must be 'W' or 'dBm'.")


def _near(actual: float, expected: float) -> bool:
    if expected == 0:
        return actual == 0
    return abs(actual - expected) / abs(expected) <= 0.02


def _first_float(response: str) -> float:
    token = response.replace(",", " ").split()[0]
    return float(token)


def _as_watts(reported: float, unit: str) -> float:
    if unit.upper().startswith("DB"):
        return (10 ** (reported / 10.0)) / 1000.0
    return reported
