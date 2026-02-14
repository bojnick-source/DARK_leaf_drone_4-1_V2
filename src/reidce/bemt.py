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
from typing import List

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

        sigma_r = geometry.n_blades * elem.chord_m / (2.0 * math.pi * r)

        # initial guess for axial inflow factor
        a = 0.01
        for _ in range(max_iter):
            v_axial = condition.v_climb_m_s + a * u_t
            phi = math.atan2(v_axial, u_t)
            alpha = elem.twist_rad - phi

            cl = elem.cl_alpha * alpha
            cd = elem.cd0

            cn = cl * math.cos(phi) - cd * math.sin(phi)

            sin_phi = math.sin(phi)
            denom = 4.0 * sin_phi * sin_phi
            if abs(denom) < 1e-15:
                break

            a_new = sigma_r * cn / denom

            # Glauert correction for high inflow
            a_new = max(a_new, 0.0)
            if a_new > 0.5:
                a_new = 0.5

            if abs(a_new - a) < tol:
                a = a_new
                break
            a = a_new

        # final loads
        v_axial = condition.v_climb_m_s + a * u_t
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
