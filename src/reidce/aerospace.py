from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict


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
