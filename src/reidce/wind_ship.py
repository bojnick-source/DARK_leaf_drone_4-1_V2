from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Dict


@dataclass(frozen=True)
class WindShipParams:
    sail_area_m2: float
    hull_wetted_area_m2: float
    mass_kg: float
    cl_max: float = 1.2
    cd0: float = 0.08
    cd2: float = 0.6
    water_density_kg_m3: float = 1025.0
    air_density_kg_m3: float = 1.225


@dataclass(frozen=True)
class WindCondition:
    true_wind_speed_m_s: float
    true_wind_dir_rad: float


@dataclass(frozen=True)
class WindShipState:
    speed_m_s: float
    heading_rad: float


@dataclass(frozen=True)
class WindShipPerformance:
    apparent_wind_speed_m_s: float
    apparent_wind_angle_rad: float
    sail_force_n: float
    drive_force_n: float
    drag_force_n: float
    net_force_n: float
    propulsive_efficiency: float


def apparent_wind(state: WindShipState, wind: WindCondition) -> Dict[str, float]:
    rel_x = wind.true_wind_speed_m_s * math.cos(wind.true_wind_dir_rad) - state.speed_m_s * math.cos(
        state.heading_rad
    )
    rel_y = wind.true_wind_speed_m_s * math.sin(wind.true_wind_dir_rad) - state.speed_m_s * math.sin(
        state.heading_rad
    )
    speed = math.hypot(rel_x, rel_y)
    angle = math.atan2(rel_y, rel_x)
    return {"speed": speed, "angle": angle}


def sail_aero_force(aw_speed: float, aw_angle: float, params: WindShipParams) -> float:
    if aw_speed <= 0.0:
        return 0.0
    alpha = _wrap_angle(aw_angle)
    cl = max(-params.cl_max, min(params.cl_max, 2.0 * math.sin(alpha)))
    cd = params.cd0 + params.cd2 * alpha * alpha
    q = 0.5 * params.air_density_kg_m3 * aw_speed * aw_speed
    lift = q * params.sail_area_m2 * cl
    drag = q * params.sail_area_m2 * cd
    return math.hypot(lift, drag)


def hull_drag(speed_m_s: float, params: WindShipParams) -> float:
    if speed_m_s <= 0.0:
        return 0.0
    cf = 0.004
    q = 0.5 * params.water_density_kg_m3 * speed_m_s * speed_m_s
    return q * params.hull_wetted_area_m2 * cf


def evaluate_wind_ship(
    state: WindShipState,
    wind: WindCondition,
    params: WindShipParams,
) -> WindShipPerformance:
    aw = apparent_wind(state, wind)
    sail_force = sail_aero_force(aw["speed"], aw["angle"], params)
    drag = hull_drag(state.speed_m_s, params)
    drive_force = sail_force * math.cos(aw["angle"] - state.heading_rad)
    net_force = drive_force - drag
    efficiency = drive_force / max(sail_force, 1e-6)
    return WindShipPerformance(
        apparent_wind_speed_m_s=aw["speed"],
        apparent_wind_angle_rad=aw["angle"],
        sail_force_n=sail_force,
        drive_force_n=drive_force,
        drag_force_n=drag,
        net_force_n=net_force,
        propulsive_efficiency=efficiency,
    )


def best_heading_for_wind(
    wind: WindCondition,
    params: WindShipParams,
    speed_m_s: float,
    heading_samples: int = 72,
) -> float:
    if heading_samples <= 0:
        raise ValueError("heading_samples must be > 0")
    best_heading = 0.0
    best_net = -1e9
    for idx in range(heading_samples):
        heading = -math.pi + 2.0 * math.pi * idx / heading_samples
        perf = evaluate_wind_ship(
            WindShipState(speed_m_s=speed_m_s, heading_rad=heading), wind, params
        )
        if perf.net_force_n > best_net:
            best_net = perf.net_force_n
            best_heading = heading
    return best_heading


def _wrap_angle(angle: float) -> float:
    while angle > math.pi:
        angle -= 2.0 * math.pi
    while angle < -math.pi:
        angle += 2.0 * math.pi
    return angle
