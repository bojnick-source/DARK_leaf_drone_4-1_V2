from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class ISAAtmosphere:
    altitude_m: float
    temperature_k: float
    pressure_pa: float
    density_kg_m3: float


@dataclass(frozen=True)
class AeroCoefficients:
    cl: float
    cd: float


@dataclass(frozen=True)
class RangeEstimate:
    range_km: float
    endurance_s: float
    avg_speed_m_s: float


def isa_atmosphere(altitude_m: float) -> ISAAtmosphere:
    if altitude_m < 0:
        altitude_m = 0.0
    t0 = 288.15
    p0 = 101325.0
    lapse = -0.0065
    r = 287.05
    g = 9.80665
    if altitude_m <= 11000.0:
        temperature = t0 + lapse * altitude_m
        pressure = p0 * (temperature / t0) ** (-g / (lapse * r))
    else:
        temperature = t0 + lapse * 11000.0
        pressure = p0 * (temperature / t0) ** (-g / (lapse * r)) * math.exp(
            -g * (altitude_m - 11000.0) / (r * temperature)
        )
    density = pressure / (r * temperature)
    return ISAAtmosphere(
        altitude_m=altitude_m,
        temperature_k=temperature,
        pressure_pa=pressure,
        density_kg_m3=density,
    )


def lift_drag(
    speed_m_s: float,
    wing_area_m2: float,
    coeffs: AeroCoefficients,
    rho_kg_m3: float,
) -> Dict[str, float]:
    if speed_m_s <= 0 or wing_area_m2 <= 0:
        raise ValueError("speed_m_s and wing_area_m2 must be > 0")
    q = 0.5 * rho_kg_m3 * speed_m_s**2
    lift = q * wing_area_m2 * coeffs.cl
    drag = q * wing_area_m2 * coeffs.cd
    return {"lift_n": lift, "drag_n": drag, "q_pa": q}


def estimate_glide_ratio(coeffs: AeroCoefficients) -> float:
    if coeffs.cd <= 0:
        raise ValueError("cd must be > 0")
    return coeffs.cl / coeffs.cd


def wing_loading(weight_n: float, wing_area_m2: float) -> float:
    if wing_area_m2 <= 0:
        raise ValueError("wing_area_m2 must be > 0")
    return weight_n / wing_area_m2


def thrust_to_weight(thrust_n: float, weight_n: float) -> float:
    if weight_n <= 0:
        raise ValueError("weight_n must be > 0")
    return thrust_n / weight_n


def range_endurance(
    cruise_speed_m_s: float,
    specific_energy_j_kg: float,
    mass_kg: float,
    efficiency: float = 0.35,
) -> RangeEstimate:
    if cruise_speed_m_s <= 0 or specific_energy_j_kg <= 0 or mass_kg <= 0:
        raise ValueError("inputs must be > 0")
    if not 0.01 <= efficiency <= 1.0:
        raise ValueError("efficiency must be within (0,1]")
    usable_energy = specific_energy_j_kg * mass_kg * efficiency
    power_required = mass_kg * 9.80665 * cruise_speed_m_s * 0.05
    endurance_s = usable_energy / max(power_required, 1e-6)
    range_km = cruise_speed_m_s * endurance_s / 1000.0
    return RangeEstimate(range_km=range_km, endurance_s=endurance_s, avg_speed_m_s=cruise_speed_m_s)


# ---------------------------------------------------------------------------
# Hardened ISA — cached, precomputed, and validated
# ---------------------------------------------------------------------------

# ISA constants (precomputed to avoid per-call overhead)
_ISA_T0 = 288.15       # sea-level temperature (K)
_ISA_P0 = 101325.0     # sea-level pressure (Pa)
_ISA_LAPSE = -0.0065   # temperature lapse rate (K/m)
_ISA_R = 287.05        # specific gas constant for dry air (J/(kg K))
_ISA_G = 9.80665       # gravitational acceleration (m/s^2)
_ISA_EXPONENT = -_ISA_G / (_ISA_LAPSE * _ISA_R)  # precomputed exponent
_ISA_TROPO_TEMP = _ISA_T0 + _ISA_LAPSE * 11000.0  # tropopause temperature
_ISA_TROPO_PRESSURE = _ISA_P0 * (_ISA_TROPO_TEMP / _ISA_T0) ** _ISA_EXPONENT


@lru_cache(maxsize=1024)
def isa_atmosphere_cached(altitude_m_x10: int) -> ISAAtmosphere:
    """LRU-cached ISA atmosphere keyed by altitude in decimeters.

    Avoids repeated exp/pow calls for commonly-queried altitudes.
    Rounds altitude to nearest 0.1 m for cache efficiency.
    """
    altitude_m = altitude_m_x10 / 10.0
    return isa_atmosphere(max(0.0, altitude_m))


def isa_density_at(altitude_m: float) -> float:
    """Fast ISA density lookup using the cached atmosphere model."""
    key = round(altitude_m * 10.0)
    return isa_atmosphere_cached(key).density_kg_m3


@dataclass(frozen=True)
class FlightCondition:
    """Complete flight condition for aerodynamic analysis."""
    altitude_m: float
    speed_m_s: float
    wing_area_m2: float
    coeffs: AeroCoefficients
    mass_kg: float

    def validate(self) -> List[str]:
        """Return a list of validation errors (empty if valid)."""
        errors: List[str] = []
        if self.altitude_m < 0.0:
            errors.append("altitude_m must be >= 0")
        if self.speed_m_s <= 0.0:
            errors.append("speed_m_s must be > 0")
        if self.wing_area_m2 <= 0.0:
            errors.append("wing_area_m2 must be > 0")
        if self.mass_kg <= 0.0:
            errors.append("mass_kg must be > 0")
        if self.coeffs.cd <= 0.0:
            errors.append("cd must be > 0")
        return errors


def analyze_flight_condition(condition: FlightCondition) -> Dict[str, float]:
    """Full aerodynamic analysis at a flight condition.

    Returns lift, drag, L/D, wing loading, dynamic pressure, ISA density,
    and range estimate in a single call — avoids redundant ISA lookups.
    """
    errors = condition.validate()
    if errors:
        raise ValueError(f"Invalid flight condition: {'; '.join(errors)}")

    isa = isa_atmosphere(condition.altitude_m)
    rho = isa.density_kg_m3
    forces = lift_drag(
        condition.speed_m_s, condition.wing_area_m2,
        condition.coeffs, rho,
    )
    weight_n = condition.mass_kg * _ISA_G
    ld_ratio = estimate_glide_ratio(condition.coeffs)
    wl = wing_loading(weight_n, condition.wing_area_m2)

    return {
        "lift_n": forces["lift_n"],
        "drag_n": forces["drag_n"],
        "q_pa": forces["q_pa"],
        "l_over_d": ld_ratio,
        "wing_loading_pa": wl,
        "density_kg_m3": rho,
        "temperature_k": isa.temperature_k,
        "pressure_pa": isa.pressure_pa,
        "weight_n": weight_n,
    }


def compute_drag_polar(
    wing_area_m2: float,
    cl_range: Tuple[float, float],
    cd0: float,
    k_induced: float,
    n_points: int = 50,
) -> List[Tuple[float, float]]:
    """Generate a drag polar curve: list of (CL, CD) points.

    CD = CD0 + k * CL^2  (parabolic drag polar)
    """
    if n_points < 2:
        raise ValueError("n_points must be >= 2")
    if cd0 < 0:
        raise ValueError("cd0 must be >= 0")
    if k_induced < 0:
        raise ValueError("k_induced must be >= 0")

    cl_min, cl_max = cl_range
    step = (cl_max - cl_min) / (n_points - 1)
    polar: List[Tuple[float, float]] = []
    for i in range(n_points):
        cl = cl_min + i * step
        cd = cd0 + k_induced * cl * cl
        polar.append((cl, cd))
    return polar
