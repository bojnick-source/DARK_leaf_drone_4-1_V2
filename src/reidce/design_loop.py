"""AI-driven iterative design loop for drone optimization.

Implements the "build → fly → push to limits → break → learn → rebuild"
cycle inspired by fighter-jet development programs.  Each iteration:

1. **Build** — construct a ``VehicleParams`` from the current design vector.
2. **Fly** — run a suite of flight tests (climb, speed, turn, endurance).
3. **Push** — progressively increase aggressiveness until a limit is hit.
4. **Learn** — analyse failures and compute parameter adjustments.
5. **Rebuild** — apply adjustments to produce a new design vector.
6. **Repeat** — continue until the design converges or max iterations.

The loop produces an ``IterationLog`` with full traceability of every
design tried, every failure encountered, and every improvement made.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from reidce.energy_maneuverability import (
    EMState,
    StructuralLimits,
    compute_em_state,
    find_sustained_turn_rate,
)
from reidce.flight_sim import (
    Atmosphere,
    GuidanceTarget,
    VehicleParams,
    VehicleState,
    simulate_flight,
)

# ── Data structures ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class FlightTestResult:
    """Outcome of a single flight test."""

    test_name: str
    passed: bool
    max_speed_m_s: float
    max_altitude_m: float
    max_load_factor_g: float
    max_temperature_c: float
    min_battery_pct: float
    ps_at_cruise: float
    sustained_turn_rate_deg_s: float
    failure_reason: str


@dataclass(frozen=True)
class DesignAdjustment:
    """One parameter tweak derived from a failure analysis."""

    parameter: str
    old_value: float
    new_value: float
    reason: str


@dataclass
class IterationRecord:
    """One full build-fly-learn cycle."""

    iteration: int
    params: VehicleParams
    test_results: List[FlightTestResult] = field(default_factory=list)
    adjustments: List[DesignAdjustment] = field(default_factory=list)
    em_snapshot: Optional[EMState] = None
    score: float = 0.0


@dataclass
class IterationLog:
    """Complete history of the AI design loop."""

    iterations: List[IterationRecord] = field(default_factory=list)
    converged: bool = False
    best_iteration: int = 0
    best_score: float = 0.0


# ── Flight tests ─────────────────────────────────────────────────────────


def _run_climb_test(
    params: VehicleParams, atmosphere: Atmosphere, limits: StructuralLimits
) -> FlightTestResult:
    """Fly to max altitude and assess climb performance."""
    initial = VehicleState(z_m=0.0, vx_m_s=8.0)
    target = GuidanceTarget(altitude_m=100.0, speed_m_s=12.0, heading_rad=0.0)
    result = simulate_flight(initial, target, duration_s=20.0, dt_s=0.05, params=params)
    max_alt = max(s.z_m for s in result.state)
    max_spd = max(
        math.sqrt(s.vx_m_s**2 + s.vy_m_s**2 + s.vz_m_s**2) for s in result.state
    )
    max_temp = max(result.temperature_c)
    min_batt = min(result.battery_pct)

    state_cruise = VehicleState(z_m=max_alt * 0.5, vx_m_s=10.0)
    em = compute_em_state(state_cruise, 0.8, 0.0, params, atmosphere, limits)

    failure = ""
    passed = True
    if max_alt < 30.0:
        failure = "insufficient_climb"
        passed = False
    if max_temp > limits.max_temperature_c:
        failure = "thermal_limit"
        passed = False

    return FlightTestResult(
        test_name="climb",
        passed=passed,
        max_speed_m_s=round(max_spd, 2),
        max_altitude_m=round(max_alt, 2),
        max_load_factor_g=1.0,
        max_temperature_c=round(max_temp, 2),
        min_battery_pct=round(min_batt, 1),
        ps_at_cruise=em.ps_m_s,
        sustained_turn_rate_deg_s=0.0,
        failure_reason=failure,
    )


def _run_speed_test(
    params: VehicleParams, atmosphere: Atmosphere, limits: StructuralLimits
) -> FlightTestResult:
    """Push to maximum speed at low altitude."""
    initial = VehicleState(z_m=10.0, vx_m_s=5.0)
    target = GuidanceTarget(altitude_m=10.0, speed_m_s=params.max_speed_m_s, heading_rad=0.0)
    result = simulate_flight(initial, target, duration_s=15.0, dt_s=0.05, params=params)
    max_spd = max(
        math.sqrt(s.vx_m_s**2 + s.vy_m_s**2 + s.vz_m_s**2) for s in result.state
    )
    max_temp = max(result.temperature_c)
    min_batt = min(result.battery_pct)

    state_fast = VehicleState(z_m=10.0, vx_m_s=max_spd)
    em = compute_em_state(state_fast, 1.0, 0.0, params, atmosphere, limits)

    failure = ""
    passed = True
    if max_spd > limits.max_speed_m_s:
        failure = "speed_limit_exceeded"
        passed = False
    if max_temp > limits.max_temperature_c:
        failure = "thermal_limit"
        passed = False

    return FlightTestResult(
        test_name="speed",
        passed=passed,
        max_speed_m_s=round(max_spd, 2),
        max_altitude_m=10.0,
        max_load_factor_g=1.0,
        max_temperature_c=round(max_temp, 2),
        min_battery_pct=round(min_batt, 1),
        ps_at_cruise=em.ps_m_s,
        sustained_turn_rate_deg_s=0.0,
        failure_reason=failure,
    )


def _run_turn_test(
    params: VehicleParams, atmosphere: Atmosphere, limits: StructuralLimits
) -> FlightTestResult:
    """Test turning performance at cruise speed."""
    cruise_speed = min(12.0, params.max_speed_m_s * 0.6)
    str_rate = find_sustained_turn_rate(
        cruise_speed, 30.0, 0.9, params, atmosphere,
    )

    # Find max instantaneous g in a hard turn
    max_bank = math.radians(min(60.0, math.degrees(params.max_tilt_rad)))
    cos_bank = math.cos(max_bank)
    max_g = 1.0 / max(cos_bank, 1e-6)

    failure = ""
    passed = True
    if max_g > limits.max_g:
        failure = "structural_g_limit"
        passed = False
    if str_rate < 5.0:
        failure = "insufficient_turn_rate"
        passed = False

    return FlightTestResult(
        test_name="turn",
        passed=passed,
        max_speed_m_s=round(cruise_speed, 2),
        max_altitude_m=30.0,
        max_load_factor_g=round(max_g, 2),
        max_temperature_c=25.0,
        min_battery_pct=100.0,
        ps_at_cruise=0.0,
        sustained_turn_rate_deg_s=round(str_rate, 2),
        failure_reason=failure,
    )


def _run_endurance_test(
    params: VehicleParams, atmosphere: Atmosphere, limits: StructuralLimits
) -> FlightTestResult:
    """Fly until battery depletes to assess endurance."""
    initial = VehicleState(z_m=30.0, vx_m_s=8.0)
    target = GuidanceTarget(altitude_m=30.0, speed_m_s=10.0, heading_rad=0.0)
    result = simulate_flight(
        initial, target, duration_s=60.0, dt_s=0.1, params=params,
        battery_capacity_j=180000.0,
    )
    min_batt = min(result.battery_pct)
    max_temp = max(result.temperature_c)

    failure = ""
    passed = True
    if min_batt < 10.0:
        failure = "battery_depleted"
        passed = False
    if max_temp > limits.max_temperature_c:
        failure = "thermal_limit"
        passed = False

    max_spd = max(
        math.sqrt(s.vx_m_s**2 + s.vy_m_s**2 + s.vz_m_s**2) for s in result.state
    )
    return FlightTestResult(
        test_name="endurance",
        passed=passed,
        max_speed_m_s=round(max_spd, 2),
        max_altitude_m=round(max(s.z_m for s in result.state), 2),
        max_load_factor_g=1.0,
        max_temperature_c=round(max_temp, 2),
        min_battery_pct=round(min_batt, 1),
        ps_at_cruise=0.0,
        sustained_turn_rate_deg_s=0.0,
        failure_reason=failure,
    )


# ── Learning / adjustment engine ─────────────────────────────────────────


def _analyse_failures(
    params: VehicleParams, results: List[FlightTestResult]
) -> List[DesignAdjustment]:
    """Derive parameter adjustments from test failures."""
    adjustments: List[DesignAdjustment] = []

    for r in results:
        if r.passed:
            continue

        if r.failure_reason == "insufficient_climb":
            new_thrust = min(params.max_thrust_n * 1.15, 120.0)
            adjustments.append(DesignAdjustment(
                "max_thrust_n", params.max_thrust_n, round(new_thrust, 2),
                "Increase thrust 15% to improve climb rate",
            ))

        elif r.failure_reason == "thermal_limit":
            new_cd0 = max(params.cd0 * 0.9, 0.01)
            adjustments.append(DesignAdjustment(
                "cd0", params.cd0, round(new_cd0, 4),
                "Reduce parasitic drag 10% to lower power demand and heat",
            ))

        elif r.failure_reason == "speed_limit_exceeded":
            new_cd0 = params.cd0 * 1.05
            adjustments.append(DesignAdjustment(
                "cd0", params.cd0, round(new_cd0, 4),
                "Increase drag 5% to limit top speed within structural envelope",
            ))

        elif r.failure_reason == "structural_g_limit":
            new_tilt = max(params.max_tilt_rad * 0.9, math.radians(10.0))
            adjustments.append(DesignAdjustment(
                "max_tilt_rad", params.max_tilt_rad, round(new_tilt, 4),
                "Reduce max bank angle to keep g-load within structural limits",
            ))

        elif r.failure_reason == "insufficient_turn_rate":
            new_area = min(params.wing_area_m2 * 1.1, 1.0)
            adjustments.append(DesignAdjustment(
                "wing_area_m2", params.wing_area_m2, round(new_area, 4),
                "Increase wing area 10% to improve lift-to-drag and turn rate",
            ))

        elif r.failure_reason == "battery_depleted":
            new_mass = max(params.mass_kg * 0.95, 0.5)
            adjustments.append(DesignAdjustment(
                "mass_kg", params.mass_kg, round(new_mass, 3),
                "Reduce mass 5% to improve specific energy and endurance",
            ))

    return adjustments


def _apply_adjustments(
    params: VehicleParams, adjustments: List[DesignAdjustment]
) -> VehicleParams:
    """Create a new VehicleParams with adjustments applied."""
    values = {
        "mass_kg": params.mass_kg,
        "wing_area_m2": params.wing_area_m2,
        "cl_alpha_per_rad": params.cl_alpha_per_rad,
        "cd0": params.cd0,
        "cd_alpha2": params.cd_alpha2,
        "max_thrust_n": params.max_thrust_n,
        "max_tilt_rad": params.max_tilt_rad,
        "max_speed_m_s": params.max_speed_m_s,
        "max_accel_m_s2": params.max_accel_m_s2,
    }
    for adj in adjustments:
        if adj.parameter in values:
            values[adj.parameter] = adj.new_value
    return VehicleParams(**values)


def _score_design(results: List[FlightTestResult]) -> float:
    """Score a design 0–100 based on test results and performance."""
    passed = sum(1 for r in results if r.passed)
    total = max(len(results), 1)
    pass_score = (passed / total) * 50.0

    perf_score = 0.0
    for r in results:
        if r.test_name == "climb":
            perf_score += min(r.max_altitude_m / 100.0, 1.0) * 15.0
        elif r.test_name == "speed":
            perf_score += min(r.max_speed_m_s / 60.0, 1.0) * 10.0
        elif r.test_name == "turn":
            perf_score += min(r.sustained_turn_rate_deg_s / 60.0, 1.0) * 15.0
        elif r.test_name == "endurance":
            perf_score += min(r.min_battery_pct / 80.0, 1.0) * 10.0

    return round(pass_score + perf_score, 1)


# ── Main loop ────────────────────────────────────────────────────────────


def run_design_loop(
    initial_params: Optional[VehicleParams] = None,
    max_iterations: int = 5,
    convergence_score: float = 85.0,
    atmosphere: Optional[Atmosphere] = None,
    limits: Optional[StructuralLimits] = None,
) -> IterationLog:
    """Run the AI build-fly-learn-rebuild design loop.

    Parameters
    ----------
    initial_params : starting vehicle parameters (defaults to ``VehicleParams()``)
    max_iterations : maximum number of design iterations
    convergence_score : stop if the design scores above this threshold
    atmosphere : atmospheric conditions for testing
    limits : structural / thermal limits to enforce

    Returns
    -------
    IterationLog with full traceability of every iteration.
    """
    params = initial_params or VehicleParams()
    atmosphere = atmosphere or Atmosphere()
    limits = limits or StructuralLimits()
    log = IterationLog()
    best_score = 0.0
    best_iter = 0

    for i in range(max_iterations):
        record = IterationRecord(iteration=i, params=params)

        # Fly the test suite
        record.test_results = [
            _run_climb_test(params, atmosphere, limits),
            _run_speed_test(params, atmosphere, limits),
            _run_turn_test(params, atmosphere, limits),
            _run_endurance_test(params, atmosphere, limits),
        ]

        # Compute E-M snapshot at a representative condition
        cruise = VehicleState(z_m=30.0, vx_m_s=10.0)
        record.em_snapshot = compute_em_state(
            cruise, 0.8, 0.0, params, atmosphere, limits,
        )

        # Score the design
        record.score = _score_design(record.test_results)
        if record.score > best_score:
            best_score = record.score
            best_iter = i

        # Learn from failures and rebuild
        record.adjustments = _analyse_failures(params, record.test_results)
        log.iterations.append(record)

        if record.score >= convergence_score:
            log.converged = True
            break

        if record.adjustments:
            params = _apply_adjustments(params, record.adjustments)

    log.best_iteration = best_iter
    log.best_score = best_score
    return log


def iteration_log_to_dict(log: IterationLog) -> Dict[str, Any]:
    """Convert an IterationLog to a JSON-serializable dictionary."""
    return {
        "schema": "dark/design_loop/log/1.0",
        "converged": log.converged,
        "best_iteration": log.best_iteration,
        "best_score": log.best_score,
        "total_iterations": len(log.iterations),
        "iterations": [
            {
                "iteration": rec.iteration,
                "score": rec.score,
                "params": {
                    "mass_kg": rec.params.mass_kg,
                    "wing_area_m2": rec.params.wing_area_m2,
                    "max_thrust_n": rec.params.max_thrust_n,
                    "cd0": rec.params.cd0,
                    "max_tilt_rad": round(rec.params.max_tilt_rad, 4),
                    "max_speed_m_s": rec.params.max_speed_m_s,
                },
                "em_snapshot": {
                    "ps_m_s": rec.em_snapshot.ps_m_s,
                    "load_factor_g": rec.em_snapshot.load_factor_g,
                    "specific_energy_j_per_kg": rec.em_snapshot.specific_energy_j_per_kg,
                    "sustained_turn_rate_deg_s": rec.em_snapshot.sustained_turn_rate_deg_s,
                } if rec.em_snapshot else None,
                "tests": [
                    {
                        "name": t.test_name,
                        "passed": t.passed,
                        "failure_reason": t.failure_reason,
                        "max_speed_m_s": t.max_speed_m_s,
                        "max_altitude_m": t.max_altitude_m,
                        "max_g": t.max_load_factor_g,
                        "sustained_turn_deg_s": t.sustained_turn_rate_deg_s,
                    }
                    for t in rec.test_results
                ],
                "adjustments": [
                    {
                        "parameter": a.parameter,
                        "old": a.old_value,
                        "new": a.new_value,
                        "reason": a.reason,
                    }
                    for a in rec.adjustments
                ],
            }
            for rec in log.iterations
        ],
    }
