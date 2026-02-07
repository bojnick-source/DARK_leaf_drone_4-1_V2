from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class KiteParams:
    area_m2: float
    cl: float
    cd: float
    air_density_kg_m3: float = 1.225
    tether_efficiency: float = 0.85


@dataclass(frozen=True)
class KiteWind:
    wind_speed_m_s: float


@dataclass(frozen=True)
class KitePowerResult:
    lift_n: float
    drag_n: float
    tether_tension_n: float
    mechanical_power_w: float
    electrical_power_w: float
    efficiency: float


def kite_aero_forces(params: KiteParams, wind: KiteWind) -> Dict[str, float]:
    if params.area_m2 <= 0.0 or wind.wind_speed_m_s <= 0.0:
        raise ValueError("area_m2 and wind_speed_m_s must be > 0")
    q = 0.5 * params.air_density_kg_m3 * wind.wind_speed_m_s**2
    lift = q * params.area_m2 * params.cl
    drag = q * params.area_m2 * params.cd
    return {"lift_n": lift, "drag_n": drag, "q_pa": q}


def kite_power(
    params: KiteParams,
    wind: KiteWind,
    reeling_speed_m_s: float,
) -> KitePowerResult:
    if reeling_speed_m_s <= 0.0:
        raise ValueError("reeling_speed_m_s must be > 0")
    forces = kite_aero_forces(params, wind)
    tension = math.hypot(forces["lift_n"], forces["drag_n"])
    mechanical = tension * reeling_speed_m_s
    electrical = mechanical * params.tether_efficiency
    efficiency = electrical / max(mechanical, 1e-9)
    return KitePowerResult(
        lift_n=forces["lift_n"],
        drag_n=forces["drag_n"],
        tether_tension_n=tension,
        mechanical_power_w=mechanical,
        electrical_power_w=electrical,
        efficiency=efficiency,
    )


def optimal_reeling_speed(
    params: KiteParams,
    wind: KiteWind,
    speed_fraction: float = 0.3,
) -> float:
    if not 0.05 <= speed_fraction <= 0.7:
        raise ValueError("speed_fraction must be within [0.05, 0.7]")
    return wind.wind_speed_m_s * speed_fraction
