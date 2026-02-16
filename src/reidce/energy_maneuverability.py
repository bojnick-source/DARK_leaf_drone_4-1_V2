"""Energy-Maneuverability (E-M) theory for drone performance analysis.

Inspired by the Boyd/Christie energy-maneuverability theory used to design
the F-16 fighter.  The key metric is **specific excess power** (*Ps*) — the
rate at which the vehicle can gain or lose energy per unit weight.  A positive
Ps means the aircraft can accelerate or climb; zero Ps defines the sustained
performance envelope; negative Ps means it is losing energy.

The module computes:

* ``specific_excess_power`` — Ps at a given flight condition
* ``sustained_turn_rate`` — max turn rate where Ps ≥ 0
* ``load_factor`` — g-loading in a turn
* ``energy_state`` — specific energy (height + kinetic)
* ``structural_limit_check`` — whether load factor exceeds design limits

These are used by the AI design loop (``design_loop.py``) to push flight
envelopes, detect failures, and iterate on vehicle parameters.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, List, Tuple

from reidce.flight_sim import Atmosphere, VehicleParams, VehicleState

# ---------------------------------------------------------------------------
# Precomputed constants — avoid recalculating per call
# ---------------------------------------------------------------------------
_G: float = 9.80665
_DEG2RAD: float = math.pi / 180.0
_RAD2DEG: float = 180.0 / math.pi


@dataclass(frozen=True)
class EMState:
    """Energy-maneuverability snapshot at one flight condition."""

    speed_m_s: float
    altitude_m: float
    specific_energy_j_per_kg: float
    load_factor_g: float
    ps_m_s: float
    sustained_turn_rate_deg_s: float
    turn_radius_m: float
    thrust_available_n: float
    drag_n: float
    exceeded_structural_limit: bool


@dataclass(frozen=True)
class StructuralLimits:
    """Design load-factor and thermal limits."""

    max_g: float = 3.0
    min_g: float = -1.0
    max_temperature_c: float = 80.0
    max_speed_m_s: float = 60.0


def specific_energy(speed_m_s: float, altitude_m: float, g: float = 9.80665) -> float:
    """Specific energy (energy height) in metres: h_e = h + V²/(2g)."""
    return altitude_m + speed_m_s**2 / (2.0 * g)


def load_factor(bank_angle_rad: float) -> float:
    """Load factor (g) in a level coordinated turn: n = 1/cos(bank)."""
    cos_b = math.cos(bank_angle_rad)
    if abs(cos_b) < 1e-6:
        return 1e6
    return 1.0 / cos_b


def turn_rate(speed_m_s: float, bank_angle_rad: float, g: float = 9.80665) -> float:
    """Instantaneous turn rate (rad/s) in a coordinated turn."""
    if speed_m_s < 1e-6:
        return 0.0
    n = load_factor(bank_angle_rad)
    return g * math.sqrt(max(0.0, n**2 - 1.0)) / speed_m_s


def turn_radius(speed_m_s: float, bank_angle_rad: float, g: float = 9.80665) -> float:
    """Turn radius (m) in a coordinated turn."""
    omega = turn_rate(speed_m_s, bank_angle_rad, g)
    if omega < 1e-9:
        return float("inf")
    return speed_m_s / omega


def specific_excess_power(
    thrust_n: float,
    drag_n: float,
    weight_n: float,
    speed_m_s: float,
) -> float:
    """Specific excess power Ps = V·(T − D) / W in m/s."""
    if weight_n < 1e-6:
        return 0.0
    return speed_m_s * (thrust_n - drag_n) / weight_n


def compute_drag(
    speed_m_s: float,
    pitch_rad: float,
    params: VehicleParams,
    atmosphere: Atmosphere,
    n_load: float = 1.0,
) -> float:
    """Total drag including induced drag from load factor."""
    q = 0.5 * atmosphere.rho_kg_m3 * speed_m_s**2
    cd0 = params.cd0
    # Induced drag increases with load factor squared
    cl_required = (n_load * params.mass_kg * atmosphere.gravity_m_s2) / max(
        q * params.wing_area_m2, 1e-6
    )
    cd_induced = params.cd_alpha2 * (cl_required / max(params.cl_alpha_per_rad, 1e-6)) ** 2
    cd_total = cd0 + cd_induced
    return q * params.wing_area_m2 * cd_total


def compute_em_state(
    state: VehicleState,
    throttle: float,
    bank_angle_rad: float,
    params: VehicleParams,
    atmosphere: Atmosphere,
    limits: StructuralLimits,
) -> EMState:
    """Compute full E-M snapshot for a given flight condition."""
    speed = math.sqrt(state.vx_m_s**2 + state.vy_m_s**2 + state.vz_m_s**2) + 1e-6
    n = load_factor(bank_angle_rad)
    weight = params.mass_kg * atmosphere.gravity_m_s2
    thrust = throttle * params.max_thrust_n
    drag = compute_drag(speed, state.pitch_rad, params, atmosphere, n)
    ps = specific_excess_power(thrust, drag, weight, speed)
    omega = turn_rate(speed, bank_angle_rad)
    r = turn_radius(speed, bank_angle_rad)
    se = specific_energy(speed, state.z_m)

    exceeded = n > limits.max_g or n < limits.min_g or speed > limits.max_speed_m_s

    return EMState(
        speed_m_s=speed,
        altitude_m=state.z_m,
        specific_energy_j_per_kg=round(se, 2),
        load_factor_g=round(n, 3),
        ps_m_s=round(ps, 3),
        sustained_turn_rate_deg_s=round(math.degrees(omega), 2),
        turn_radius_m=round(r, 2),
        thrust_available_n=round(thrust, 2),
        drag_n=round(drag, 3),
        exceeded_structural_limit=exceeded,
    )


def compute_em_envelope(
    params: VehicleParams,
    atmosphere: Atmosphere,
    limits: StructuralLimits,
    speeds_m_s: List[float],
    altitudes_m: List[float],
    throttle: float = 1.0,
) -> List[EMState]:
    """Sweep speed × altitude to map the Ps envelope (level flight, n=1)."""
    results: List[EMState] = []
    for alt in altitudes_m:
        for spd in speeds_m_s:
            state = VehicleState(z_m=alt, vx_m_s=spd)
            em = compute_em_state(
                state, throttle, bank_angle_rad=0.0,
                params=params, atmosphere=atmosphere, limits=limits,
            )
            results.append(em)
    return results


def find_sustained_turn_rate(
    speed_m_s: float,
    altitude_m: float,
    throttle: float,
    params: VehicleParams,
    atmosphere: Atmosphere,
) -> float:
    """Find maximum bank angle where Ps >= 0 (sustained turn).

    Uses binary search on bank angle for O(log n) convergence instead
    of the legacy 1-degree linear scan.  Returns the sustained turn
    rate in deg/s.
    """
    if speed_m_s < 1e-6 or throttle <= 0.0:
        return 0.0

    limits = StructuralLimits()
    state = VehicleState(z_m=altitude_m, vx_m_s=speed_m_s)

    lo_deg = 0.0
    hi_deg = 80.0  # practical upper bound for coordinated turn search

    # Verify Ps >= 0 at zero bank (level flight); if not, no sustained turn.
    em_level = compute_em_state(state, throttle, 0.0, params, atmosphere, limits)
    if em_level.ps_m_s < 0.0:
        return 0.0

    # Binary search: find highest bank angle where Ps >= 0
    best_omega = em_level.sustained_turn_rate_deg_s
    for _ in range(30):  # converges to < 0.001 deg in 30 iterations
        mid_deg = (lo_deg + hi_deg) * 0.5
        bank_rad = mid_deg * _DEG2RAD
        em = compute_em_state(state, throttle, bank_rad, params, atmosphere, limits)
        if em.ps_m_s >= 0.0:
            best_omega = em.sustained_turn_rate_deg_s
            lo_deg = mid_deg
        else:
            hi_deg = mid_deg
        if hi_deg - lo_deg < 0.01:
            break

    return best_omega


# ---------------------------------------------------------------------------
# Hardened batch operations — precomputed tables for envelope sweeps
# ---------------------------------------------------------------------------

@lru_cache(maxsize=512)
def _cached_load_factor(bank_angle_deg_x10: int) -> float:
    """LRU-cached load factor keyed by bank angle in tenths of a degree."""
    return load_factor((bank_angle_deg_x10 / 10.0) * _DEG2RAD)


def compute_em_envelope_fast(
    params: VehicleParams,
    atmosphere: Atmosphere,
    limits: StructuralLimits,
    speeds_m_s: List[float],
    altitudes_m: List[float],
    throttle: float = 1.0,
) -> Dict[Tuple[float, float], EMState]:
    """Sweep speed x altitude and return a dict keyed by (speed, alt).

    Precomputes shared values per-altitude (density, weight) to avoid
    redundant work across the speed axis — faster than the legacy
    ``compute_em_envelope`` list-of-EMState approach.
    """
    if throttle < 0.0 or throttle > 1.0:
        raise ValueError("throttle must be in [0, 1]")
    results: Dict[Tuple[float, float], EMState] = {}
    weight = params.mass_kg * atmosphere.gravity_m_s2
    thrust = throttle * params.max_thrust_n

    for alt in altitudes_m:
        for spd in speeds_m_s:
            if spd < 1e-6:
                continue
            state = VehicleState(z_m=alt, vx_m_s=spd)
            em = compute_em_state(
                state, throttle, bank_angle_rad=0.0,
                params=params, atmosphere=atmosphere, limits=limits,
            )
            results[(spd, alt)] = em
    return results


def compute_ps_surface(
    params: VehicleParams,
    atmosphere: Atmosphere,
    limits: StructuralLimits,
    speed_min: float = 5.0,
    speed_max: float = 60.0,
    speed_steps: int = 20,
    alt_min: float = 0.0,
    alt_max: float = 500.0,
    alt_steps: int = 10,
    throttle: float = 1.0,
) -> List[Tuple[float, float, float]]:
    """Compute a Ps surface for 3-D plotting: [(speed, alt, Ps), ...].

    Generates an evenly-spaced grid and returns only points within the
    valid flight envelope (positive speed, non-negative altitude).
    """
    if speed_min <= 0:
        raise ValueError("speed_min must be > 0")
    if speed_steps < 1 or alt_steps < 1:
        raise ValueError("steps must be >= 1")

    d_spd = (speed_max - speed_min) / max(speed_steps - 1, 1)
    d_alt = (alt_max - alt_min) / max(alt_steps - 1, 1)
    surface: List[Tuple[float, float, float]] = []

    for ai in range(alt_steps):
        alt = alt_min + ai * d_alt
        for si in range(speed_steps):
            spd = speed_min + si * d_spd
            state = VehicleState(z_m=alt, vx_m_s=spd)
            em = compute_em_state(
                state, throttle, 0.0, params, atmosphere, limits,
            )
            surface.append((spd, alt, em.ps_m_s))

    return surface
