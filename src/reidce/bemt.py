"""Blade Element Momentum Theory (BEMT) module for rotor performance.

BEMT combines momentum theory (which relates thrust to induced velocity
through a rotor disk) with blade element theory (which computes local
aerodynamic forces on small radial blade sections).  By iteratively
matching the inflow predicted by both theories at each radial station,
BEMT produces accurate estimates of rotor thrust, torque, and power
without resorting to full CFD.

This is the standard first-order tool for drone rotor design: it sizes
blades, predicts hover performance, and computes the figure of merit
(FM) that measures how close a rotor operates to the ideal actuator
disk limit.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BladeElement:
    """A single radial station of the blade."""

    r_m: float
    chord_m: float
    twist_rad: float
    cl_alpha: float = 2.0 * math.pi
    cd0: float = 0.01


@dataclass(frozen=True)
class RotorGeometry:
    """Complete rotor geometry description."""

    n_blades: int = 2
    radius_m: float = 0.12
    hub_radius_m: float = 0.015
    root_chord_m: float = 0.025
    tip_chord_m: float = 0.015
    root_twist_rad: float = 0.35
    tip_twist_rad: float = 0.05


@dataclass(frozen=True)
class BEMTCondition:
    """Operating conditions for the BEMT solver."""

    rpm: float = 8000.0
    v_climb_m_s: float = 0.0
    rho_kg_m3: float = 1.225


@dataclass(frozen=True)
class ElementResult:
    """Aerodynamic results for a single blade element."""

    r_m: float
    thrust_per_m: float
    torque_per_m: float
    inflow_angle_rad: float
    aoa_rad: float
    cl: float
    cd: float


@dataclass(frozen=True)
class BEMTResult:
    """Integrated rotor performance results."""

    thrust_n: float
    torque_nm: float
    power_w: float
    ct: float
    cp: float
    fm: float
    elements: List[ElementResult]


# ---------------------------------------------------------------------------
# Discretisation
# ---------------------------------------------------------------------------


def discretize_rotor(
    geometry: RotorGeometry,
    n_elements: int = 20,
) -> List[BladeElement]:
    """Create blade elements with linear taper and linear twist."""
    if n_elements < 1:
        raise ValueError("n_elements must be >= 1")
    span = geometry.radius_m - geometry.hub_radius_m
    if span <= 0.0:
        raise ValueError("radius_m must be greater than hub_radius_m")

    elements: List[BladeElement] = []
    for i in range(n_elements):
        frac = (i + 0.5) / n_elements
        r = geometry.hub_radius_m + frac * span
        chord = (
            geometry.root_chord_m
            + frac * (geometry.tip_chord_m - geometry.root_chord_m)
        )
        twist = (
            geometry.root_twist_rad
            + frac * (geometry.tip_twist_rad - geometry.root_twist_rad)
        )
        elements.append(BladeElement(r_m=r, chord_m=chord, twist_rad=twist))
    return elements


# ---------------------------------------------------------------------------
# Core BEMT solver
# ---------------------------------------------------------------------------


def solve_bemt(
    geometry: RotorGeometry,
    condition: BEMTCondition,
    n_elements: int = 20,
    max_iter: int = 50,
    tol: float = 1e-6,
) -> BEMTResult:
    """Iterative BEMT solver for rotor thrust, torque, and power.

    For each blade element the solver iterates on the axial inflow
    factor *a* until the momentum-theory and blade-element-theory
    thrust predictions converge.
    """
    elements = discretize_rotor(geometry, n_elements)
    omega = condition.rpm * 2.0 * math.pi / 60.0
    if omega <= 0.0:
        raise ValueError("rpm must be > 0")

    span = geometry.radius_m - geometry.hub_radius_m
    dr = span / n_elements

    total_thrust = 0.0
    total_torque = 0.0
    results: List[ElementResult] = []

    for elem in elements:
        r = elem.r_m
        u_t = omega * r  # tangential velocity
        if u_t < 1e-12:
            results.append(ElementResult(
                r_m=r, thrust_per_m=0.0, torque_per_m=0.0,
                inflow_angle_rad=0.0, aoa_rad=0.0,
                cl=0.0, cd=elem.cd0,
            ))
            continue

        # Iterate on induced velocity v_i directly (robust for hover)
        v_i = 2.0  # initial guess for induced velocity [m/s]
        for _ in range(max_iter):
            v_axial = condition.v_climb_m_s + v_i
            phi = math.atan2(v_axial, u_t)
            alpha = elem.twist_rad - phi

            cl = elem.cl_alpha * alpha
            cd = elem.cd0

            w_sq = v_axial ** 2 + u_t ** 2

            # Thrust per unit span from blade element theory
            dt_be = (
                0.5
                * condition.rho_kg_m3
                * w_sq
                * geometry.n_blades
                * elem.chord_m
                * (cl * math.cos(phi) - cd * math.sin(phi))
            )
            # Thrust per unit span from momentum theory
            # dT = 4 pi r rho v_i (V_climb + v_i) dr
            mom_coeff = (
                4.0 * math.pi * r * condition.rho_kg_m3
                * max(v_axial, 1e-9)
            )
            if mom_coeff > 0.0:
                v_i_new = dt_be / mom_coeff
            else:
                v_i_new = v_i

            v_i_new = max(v_i_new, 0.0)
            v_i_new = min(v_i_new, u_t * 0.8)

            # Under-relaxation for stability
            v_i_next = 0.7 * v_i + 0.3 * v_i_new
            if abs(v_i_next - v_i) < tol:
                v_i = v_i_next
                break
            v_i = v_i_next

        # Final loads with converged v_i
        v_axial = condition.v_climb_m_s + v_i
        phi = math.atan2(v_axial, u_t)
        alpha = elem.twist_rad - phi
        cl = elem.cl_alpha * alpha
        cd = elem.cd0

        w_sq = v_axial**2 + u_t**2
        dt_dr = (
            0.5
            * condition.rho_kg_m3
            * w_sq
            * geometry.n_blades
            * elem.chord_m
            * (cl * math.cos(phi) - cd * math.sin(phi))
        )
        dq_dr = (
            0.5
            * condition.rho_kg_m3
            * w_sq
            * geometry.n_blades
            * elem.chord_m
            * r
            * (cl * math.sin(phi) + cd * math.cos(phi))
        )

        total_thrust += dt_dr * dr
        total_torque += dq_dr * dr
        results.append(ElementResult(
            r_m=r,
            thrust_per_m=dt_dr,
            torque_per_m=dq_dr,
            inflow_angle_rad=phi,
            aoa_rad=alpha,
            cl=cl,
            cd=cd,
        ))

    power = total_torque * omega

    # Non-dimensional coefficients
    area = math.pi * geometry.radius_m**2
    v_tip = omega * geometry.radius_m
    if v_tip > 0.0:
        ct = total_thrust / (
            condition.rho_kg_m3 * area * v_tip**2
        )
        cp = power / (
            condition.rho_kg_m3 * area * v_tip**3
        )
    else:
        ct = 0.0
        cp = 0.0

    # Figure of merit: FM = P_ideal / P_actual
    if power > 0.0 and total_thrust > 0.0:
        p_ideal = (
            total_thrust**1.5
            / math.sqrt(2.0 * condition.rho_kg_m3 * area)
        )
        fm = p_ideal / power
    else:
        fm = 0.0

    return BEMTResult(
        thrust_n=total_thrust,
        torque_nm=total_torque,
        power_w=power,
        ct=ct,
        cp=cp,
        fm=fm,
        elements=results,
    )


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------


def hover_thrust(
    geometry: RotorGeometry,
    condition: BEMTCondition,
    n_elements: int = 20,
) -> float:
    """Return the hover thrust in Newtons."""
    result = solve_bemt(geometry, condition, n_elements)
    return result.thrust_n


def compute_rotor_efficiency(
    geometry: RotorGeometry,
    condition: BEMTCondition,
) -> dict[str, float]:
    """Return a summary dict of rotor performance metrics."""
    result = solve_bemt(geometry, condition)
    area = math.pi * geometry.radius_m**2
    disk_loading = result.thrust_n / area if area > 0.0 else 0.0
    efficiency = (
        result.thrust_n / result.power_w if result.power_w > 0.0 else 0.0
    )
    return {
        "thrust": result.thrust_n,
        "power": result.power_w,
        "efficiency": efficiency,
        "fm": result.fm,
        "disk_loading": disk_loading,
    }


# ---------------------------------------------------------------------------
# Hardened BEMT — precomputed trig, RPM sweep, and batch evaluation
# ---------------------------------------------------------------------------

_TWO_PI = 2.0 * math.pi
_RPM_TO_RAD_S = _TWO_PI / 60.0


def _precompute_trig_table(n_points: int) -> List[Tuple[float, float]]:
    """Precompute (sin, cos) pairs for n equally-spaced inflow angles.

    Used by the batch BEMT solver to avoid repeated atan2/sin/cos calls
    during the inner iteration loop.
    """
    table: List[Tuple[float, float]] = []
    for i in range(n_points):
        phi = (i / max(n_points - 1, 1)) * (math.pi / 4.0)
        table.append((math.sin(phi), math.cos(phi)))
    return table


def solve_bemt_fast(
    geometry: RotorGeometry,
    condition: BEMTCondition,
    n_elements: int = 20,
    max_iter: int = 50,
    tol: float = 1e-6,
) -> BEMTResult:
    """Optimized BEMT solver with precomputed element geometry.

    Precomputes blade element positions, chords, and twists once, then
    runs the iterative inflow solver.  Avoids repeated discretization
    when called in a sweep.
    """
    if n_elements < 1:
        raise ValueError("n_elements must be >= 1")
    omega = condition.rpm * _RPM_TO_RAD_S
    if omega <= 0.0:
        raise ValueError("rpm must be > 0")

    span = geometry.radius_m - geometry.hub_radius_m
    if span <= 0.0:
        raise ValueError("radius_m must be greater than hub_radius_m")
    dr = span / n_elements

    # Precompute element geometry (avoids re-discretization)
    elem_r: List[float] = []
    elem_chord: List[float] = []
    elem_twist: List[float] = []
    for i in range(n_elements):
        frac = (i + 0.5) / n_elements
        elem_r.append(geometry.hub_radius_m + frac * span)
        elem_chord.append(
            geometry.root_chord_m
            + frac * (geometry.tip_chord_m - geometry.root_chord_m)
        )
        elem_twist.append(
            geometry.root_twist_rad
            + frac * (geometry.tip_twist_rad - geometry.root_twist_rad)
        )

    cl_alpha = 2.0 * math.pi  # thin airfoil default
    cd0 = 0.01
    rho = condition.rho_kg_m3
    nb = geometry.n_blades
    v_climb = condition.v_climb_m_s

    total_thrust = 0.0
    total_torque = 0.0
    results: List[ElementResult] = []

    for idx in range(n_elements):
        r = elem_r[idx]
        u_t = omega * r
        if u_t < 1e-12:
            results.append(ElementResult(
                r_m=r, thrust_per_m=0.0, torque_per_m=0.0,
                inflow_angle_rad=0.0, aoa_rad=0.0, cl=0.0, cd=cd0,
            ))
            continue

        chord = elem_chord[idx]
        twist = elem_twist[idx]
        v_i = 2.0

        for _ in range(max_iter):
            v_axial = v_climb + v_i
            phi = math.atan2(v_axial, u_t)
            alpha = twist - phi
            cl_val = cl_alpha * alpha
            w_sq = v_axial * v_axial + u_t * u_t
            sin_phi = math.sin(phi)
            cos_phi = math.cos(phi)

            dt_be = 0.5 * rho * w_sq * nb * chord * (
                cl_val * cos_phi - cd0 * sin_phi
            )
            mom_coeff = 4.0 * math.pi * r * rho * max(v_axial, 1e-9)
            v_i_new = max(0.0, min(dt_be / mom_coeff if mom_coeff > 0 else v_i, u_t * 0.8))
            v_i_next = 0.7 * v_i + 0.3 * v_i_new
            if abs(v_i_next - v_i) < tol:
                v_i = v_i_next
                break
            v_i = v_i_next

        v_axial = v_climb + v_i
        phi = math.atan2(v_axial, u_t)
        alpha = twist - phi
        cl_val = cl_alpha * alpha
        w_sq = v_axial * v_axial + u_t * u_t
        sin_phi = math.sin(phi)
        cos_phi = math.cos(phi)

        dt_dr = 0.5 * rho * w_sq * nb * chord * (cl_val * cos_phi - cd0 * sin_phi)
        dq_dr = 0.5 * rho * w_sq * nb * chord * r * (cl_val * sin_phi + cd0 * cos_phi)

        total_thrust += dt_dr * dr
        total_torque += dq_dr * dr
        results.append(ElementResult(
            r_m=r, thrust_per_m=dt_dr, torque_per_m=dq_dr,
            inflow_angle_rad=phi, aoa_rad=alpha, cl=cl_val, cd=cd0,
        ))

    power = total_torque * omega
    area = math.pi * geometry.radius_m ** 2
    v_tip = omega * geometry.radius_m
    ct = total_thrust / (rho * area * v_tip ** 2) if v_tip > 0 else 0.0
    cp = power / (rho * area * v_tip ** 3) if v_tip > 0 else 0.0

    if power > 0.0 and total_thrust > 0.0:
        p_ideal = total_thrust ** 1.5 / math.sqrt(2.0 * rho * area)
        fm = p_ideal / power
    else:
        fm = 0.0

    return BEMTResult(
        thrust_n=total_thrust, torque_nm=total_torque, power_w=power,
        ct=ct, cp=cp, fm=fm, elements=results,
    )


def rpm_sweep(
    geometry: RotorGeometry,
    rpm_range: Tuple[float, float],
    rpm_steps: int = 20,
    v_climb_m_s: float = 0.0,
    rho_kg_m3: float = 1.225,
    n_elements: int = 12,
) -> List[Dict[str, float]]:
    """Sweep RPM range and return performance at each operating point.

    Returns a list of dicts with keys: rpm, thrust, power, torque, fm, ct, cp.
    Uses the fast solver for each point.
    """
    if rpm_steps < 1:
        raise ValueError("rpm_steps must be >= 1")
    lo, hi = rpm_range
    if lo <= 0 or hi <= lo:
        raise ValueError("rpm_range must be (positive_lo, positive_hi) with lo < hi")

    step = (hi - lo) / max(rpm_steps - 1, 1)
    results: List[Dict[str, float]] = []

    for i in range(rpm_steps):
        rpm = lo + i * step
        cond = BEMTCondition(rpm=rpm, v_climb_m_s=v_climb_m_s, rho_kg_m3=rho_kg_m3)
        r = solve_bemt_fast(geometry, cond, n_elements=n_elements)
        results.append({
            "rpm": rpm,
            "thrust": r.thrust_n,
            "power": r.power_w,
            "torque": r.torque_nm,
            "fm": r.fm,
            "ct": r.ct,
            "cp": r.cp,
        })

    return results
