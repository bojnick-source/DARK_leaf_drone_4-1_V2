"""Run an AI-controlled flight simulation and produce a telemetry report.

The report is a JSON-serializable dictionary that can be loaded by the
``ui/flight_sim.html`` dashboard for visual presentation (gauges, graphs,
trajectory plots).
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

from reidce.energy_maneuverability import (
    StructuralLimits,
    compute_em_state,
    find_sustained_turn_rate,
)
from reidce.flight_sim import (
    Atmosphere,
    GuidanceTarget,
    SimulationResult,
    TripleRedundantController,
    VehicleParams,
    VehicleState,
    simulate_flight,
)


def run_ai_flight(
    *,
    altitude_m: float = 50.0,
    speed_m_s: float = 12.0,
    heading_rad: float = 0.0,
    duration_s: float = 30.0,
    dt_s: float = 0.05,
    battery_capacity_j: float = 180000.0,
    ambient_temp_c: float = 25.0,
    initial_speed_m_s: float = 5.0,
    params: Optional[VehicleParams] = None,
    atmosphere: Optional[Atmosphere] = None,
) -> SimulationResult:
    """Execute a flight simulation driven by the triple-redundant autopilot."""
    initial = VehicleState(z_m=0.0, vx_m_s=initial_speed_m_s)
    target = GuidanceTarget(
        altitude_m=altitude_m,
        speed_m_s=speed_m_s,
        heading_rad=heading_rad,
    )
    controller = TripleRedundantController()
    return simulate_flight(
        initial_state=initial,
        target=target,
        duration_s=duration_s,
        dt_s=dt_s,
        params=params,
        atmosphere=atmosphere,
        controller=controller,
        battery_capacity_j=battery_capacity_j,
        ambient_temp_c=ambient_temp_c,
    )


def _downsample(values: List[float], max_points: int) -> List[float]:
    """Return at most *max_points* evenly-spaced samples from *values*."""
    n = len(values)
    if n <= max_points:
        return values
    step = max(1, (n - 1) // (max_points - 1))
    sampled = [values[i] for i in range(0, n, step)]
    return sampled[:max_points]


def build_report(
    result: SimulationResult,
    *,
    max_points: int = 600,
    params_override: Optional[VehicleParams] = None,
) -> Dict[str, Any]:
    """Convert a SimulationResult into a JSON-serializable report dictionary."""
    time = _downsample(result.time_s, max_points)
    altitude = _downsample([s.z_m for s in result.state], max_points)
    speed = _downsample(
        [math.sqrt(s.vx_m_s**2 + s.vy_m_s**2 + s.vz_m_s**2) for s in result.state],
        max_points,
    )
    throttle = _downsample([c.throttle * 100.0 for c in result.commands], max_points)
    roll = _downsample([math.degrees(s.roll_rad) for s in result.state], max_points)
    pitch = _downsample([math.degrees(s.pitch_rad) for s in result.state], max_points)
    heading = _downsample([math.degrees(s.yaw_rad) for s in result.state], max_points)
    energy_used = _downsample(result.energy_used_j, max_points)
    battery = _downsample(result.battery_pct, max_points)
    temperature = _downsample(result.temperature_c, max_points)
    x_pos = _downsample([s.x_m for s in result.state], max_points)
    y_pos = _downsample([s.y_m for s in result.state], max_points)

    final = result.state[-1]
    final_speed = math.sqrt(final.vx_m_s**2 + final.vy_m_s**2 + final.vz_m_s**2)

    # E-M metrics at the final state
    params = params_override or VehicleParams()
    atm = Atmosphere()
    limits = StructuralLimits()
    em = compute_em_state(final, 0.8, 0.0, params, atm, limits)
    str_turn = find_sustained_turn_rate(
        max(final_speed, 5.0), max(final.z_m, 1.0), 0.9, params, atm,
    )

    return {
        "schema": "dark/flight_sim/report/1.0",
        "summary": {
            "duration_s": result.time_s[-1],
            "final_altitude_m": round(final.z_m, 2),
            "final_speed_m_s": round(final_speed, 2),
            "max_altitude_m": round(max(s.z_m for s in result.state), 2),
            "max_speed_m_s": round(
                max(
                    math.sqrt(s.vx_m_s**2 + s.vy_m_s**2 + s.vz_m_s**2)
                    for s in result.state
                ),
                2,
            ),
            "energy_used_j": round(result.energy_used_j[-1], 1),
            "battery_remaining_pct": round(result.battery_pct[-1], 1),
            "max_temperature_c": round(max(result.temperature_c), 1),
            "ps_m_s": em.ps_m_s,
            "sustained_turn_rate_deg_s": round(str_turn, 2),
            "specific_energy_j_per_kg": em.specific_energy_j_per_kg,
        },
        "telemetry": {
            "time_s": [round(v, 3) for v in time],
            "altitude_m": [round(v, 2) for v in altitude],
            "speed_m_s": [round(v, 2) for v in speed],
            "throttle_pct": [round(v, 1) for v in throttle],
            "roll_deg": [round(v, 2) for v in roll],
            "pitch_deg": [round(v, 2) for v in pitch],
            "heading_deg": [round(v, 2) for v in heading],
            "energy_used_j": [round(v, 1) for v in energy_used],
            "battery_pct": [round(v, 1) for v in battery],
            "temperature_c": [round(v, 1) for v in temperature],
            "x_m": [round(v, 2) for v in x_pos],
            "y_m": [round(v, 2) for v in y_pos],
        },
    }


def generate_report(
    *,
    altitude_m: float = 50.0,
    speed_m_s: float = 12.0,
    heading_rad: float = 0.0,
    duration_s: float = 30.0,
    dt_s: float = 0.05,
    max_points: int = 600,
) -> Dict[str, Any]:
    """Run the AI flight simulation and return a telemetry report."""
    result = run_ai_flight(
        altitude_m=altitude_m,
        speed_m_s=speed_m_s,
        heading_rad=heading_rad,
        duration_s=duration_s,
        dt_s=dt_s,
    )
    return build_report(result, max_points=max_points)


def write_report(report: Dict[str, Any], path: Path) -> None:
    """Write a telemetry report to a JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
