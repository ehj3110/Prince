"""
Reference Fluids Database for Squeeze-Flow Viscometry
=====================================================

Provides certified and literature temperature-dependent viscosity models
for common laboratory reference fluids used in DLP/SLA precalibration.

References:
- CRC Handbook of Chemistry and Physics (Water, Ethanol, Glycerol)
- Dow Chemical Technical Sheets (Propylene Glycol, PEG 400)
- Standard ASTM Viscosity Standards
"""

import math

REFERENCE_FLUIDS = {
    "PEG 400 (Recommended)": {
        "name": "Polyethylene Glycol 400",
        "description": "Lab standard; non-toxic, water-soluble, highly stable, matches typical resin viscosity",
        "nominal_cp_20c": 110.0,
        "nominal_cp_25c": 90.0,
        "cleanability": "Rinses cleanly with deionized water wipe",
        "is_recommended": True,
        # Arrhenius fit: ln(mu) = A + B / (T_kelvin)
        "arrhenius_A": -7.2654,
        "arrhenius_B": 3507.8,
        "density_g_cm3": 1.128,
    },
    "Glycerol 85% w/w (Recommended)": {
        "name": "Glycerol-Water Mixture (85% w/w)",
        "description": "Easily prepared in lab; water-soluble, completely Newtonian, excellent SNR",
        "nominal_cp_20c": 109.0,
        "nominal_cp_25c": 82.5,
        "cleanability": "Rinses cleanly with deionized water wipe",
        "is_recommended": True,
        "arrhenius_A": -11.9186,
        "arrhenius_B": 4869.2,
        "density_g_cm3": 1.224,
    },
    "Glycerol 90% w/w": {
        "name": "Glycerol-Water Mixture (90% w/w)",
        "description": "Medium-high viscosity reference fluid for heavy resins",
        "nominal_cp_20c": 219.0,
        "nominal_cp_25c": 156.0,
        "cleanability": "Rinses cleanly with warm water wipe",
        "is_recommended": True,
        "arrhenius_A": -15.15,
        "arrhenius_B": 5930.0,
        "density_g_cm3": 1.238,
    },
    "Propylene Glycol": {
        "name": "Propylene Glycol (USP)",
        "description": "Low-medium viscosity; safe, water-soluble, stable",
        "nominal_cp_20c": 56.0,
        "nominal_cp_25c": 42.0,
        "cleanability": "Water or isopropanol wipe",
        "is_recommended": True,
        "arrhenius_A": -14.95,
        "arrhenius_B": 5420.0,
        "density_g_cm3": 1.036,
    },
    "Pure Glycerol (99.5%)": {
        "name": "Pure Glycerin",
        "description": "High viscosity reference standard for thick resins and pastes",
        "nominal_cp_20c": 1412.0,
        "nominal_cp_25c": 945.0,
        "cleanability": "Warm water wipe",
        "is_recommended": False,
        "arrhenius_A": -18.72,
        "arrhenius_B": 7450.0,
        "density_g_cm3": 1.261,
    },
    "Standard Silicone Oil 100 cP": {
        "name": "Silicone Calibration Standard (100 cP)",
        "description": "Certified ASTM standard oil; non-volatile",
        "nominal_cp_20c": 108.0,
        "nominal_cp_25c": 100.0,
        "cleanability": "Requires isopropanol / solvent wipe",
        "is_recommended": False,
        "arrhenius_A": -4.20,
        "arrhenius_B": 1950.0,
        "density_g_cm3": 0.965,
    },
    "Water (DI)": {
        "name": "Deionized Water",
        "description": "Low viscosity (1 cP). Requires high descent speed (>= 5 mm/s) for usable SNR",
        "nominal_cp_20c": 1.002,
        "nominal_cp_25c": 0.890,
        "cleanability": "Clean wipe / dries residue-free",
        "is_recommended": False,
        "arrhenius_A": -6.74,
        "arrhenius_B": 1975.0,
        "density_g_cm3": 0.998,
    },
    "Ethanol (99.5%)": {
        "name": "Ethanol (Anhydrous)",
        "description": "Low viscosity (1.2 cP). Volatile; evaporates quickly during open-vat testing",
        "nominal_cp_20c": 1.20,
        "nominal_cp_25c": 1.07,
        "cleanability": "Evaporates completely",
        "is_recommended": False,
        "arrhenius_A": -7.32,
        "arrhenius_B": 2180.0,
        "density_g_cm3": 0.789,
    },
}


def get_reference_fluid_viscosity(fluid_name: str, temp_c: float = 22.0) -> float:
    """
    Compute dynamic viscosity in mPa.s (cP) for a named reference fluid at temperature temp_c.
    
    Args:
        fluid_name: Name key from REFERENCE_FLUIDS
        temp_c: Temperature in Celsius
        
    Returns:
        Viscosity in mPa.s (cP)
    """
    if fluid_name not in REFERENCE_FLUIDS:
        raise KeyError(f"Unknown reference fluid: {fluid_name}. Available: {list(REFERENCE_FLUIDS.keys())}")
    
    fluid = REFERENCE_FLUIDS[fluid_name]
    T_kelvin = temp_c + 273.15
    A = fluid["arrhenius_A"]
    B = fluid["arrhenius_B"]
    
    # Arrhenius equation: ln(mu_mPas) = A + B / T
    ln_mu = A + (B / T_kelvin)
    return float(math.exp(ln_mu))


def list_available_fluids():
    """Return a list of all supported reference fluid names."""
    return list(REFERENCE_FLUIDS.keys())
