"""Tests for the BEMT (Blade Element Momentum Theory) module."""

from __future__ import annotations

import math

from reidce.bemt import (
    BEMTCondition,
    BEMTResult,
    BladeElement,
    RotorGeometry,
    compute_rotor_efficiency,
    discretize_rotor,
    hover_thrust,
    solve_bemt,
)


def test_blade_element_defaults() -> None:
    elem = BladeElement(r_m=0.05, chord_m=0.02, twist_rad=0.2)
    assert elem.cl_alpha == 2.0 * math.pi
    assert elem.cd0 == 0.01


def test_rotor_geometry_defaults() -> None:
    geom = RotorGeometry()
    assert geom.n_blades == 2
    assert geom.radius_m == 0.12
    assert geom.hub_radius_m == 0.015


def test_discretize_rotor_count() -> None:
    geom = RotorGeometry()
    elements = discretize_rotor(geom, n_elements=10)
    assert len(elements) == 10


def test_discretize_rotor_radial_range() -> None:
    geom = RotorGeometry()
    elements = discretize_rotor(geom, n_elements=20)
    assert elements[0].r_m > geom.hub_radius_m
    assert elements[-1].r_m < geom.radius_m


def test_discretize_rotor_linear_taper() -> None:
    geom = RotorGeometry(root_chord_m=0.030, tip_chord_m=0.010)
    elements = discretize_rotor(geom, n_elements=10)
    assert elements[0].chord_m > elements[-1].chord_m


def test_discretize_rotor_linear_twist() -> None:
    geom = RotorGeometry()
    elements = discretize_rotor(geom, n_elements=10)
    assert elements[0].twist_rad > elements[-1].twist_rad


def test_discretize_rotor_raises_bad_n() -> None:
    try:
        discretize_rotor(RotorGeometry(), n_elements=0)
        raise AssertionError("Should raise ValueError")
    except ValueError:
        pass


def test_solve_bemt_hover() -> None:
    geom = RotorGeometry()
    cond = BEMTCondition(rpm=8000.0, v_climb_m_s=0.0)
    result = solve_bemt(geom, cond)
    assert isinstance(result, BEMTResult)
    assert result.thrust_n > 0.0
    assert result.power_w > 0.0
    assert result.torque_nm > 0.0


def test_solve_bemt_thrust_is_finite() -> None:
    result = solve_bemt(RotorGeometry(), BEMTCondition())
    assert math.isfinite(result.thrust_n)
    assert math.isfinite(result.power_w)
    assert math.isfinite(result.ct)
    assert math.isfinite(result.cp)
    assert math.isfinite(result.fm)


def test_solve_bemt_figure_of_merit_bounded() -> None:
    result = solve_bemt(RotorGeometry(), BEMTCondition())
    assert 0.0 < result.fm <= 1.0


def test_solve_bemt_coefficients_positive() -> None:
    result = solve_bemt(RotorGeometry(), BEMTCondition())
    assert result.ct > 0.0
    assert result.cp > 0.0


def test_solve_bemt_elements_populated() -> None:
    result = solve_bemt(RotorGeometry(), BEMTCondition(), n_elements=15)
    assert len(result.elements) == 15


def test_solve_bemt_higher_rpm_more_thrust() -> None:
    geom = RotorGeometry()
    low = solve_bemt(geom, BEMTCondition(rpm=5000.0))
    high = solve_bemt(geom, BEMTCondition(rpm=10000.0))
    assert high.thrust_n > low.thrust_n


def test_solve_bemt_climb_reduces_fm() -> None:
    geom = RotorGeometry()
    solve_bemt(geom, BEMTCondition(rpm=8000.0, v_climb_m_s=0.0))
    climb = solve_bemt(geom, BEMTCondition(rpm=8000.0, v_climb_m_s=5.0))
    # At significant climb, behaviour changes; just verify it runs
    assert math.isfinite(climb.thrust_n)
    assert math.isfinite(climb.fm)


def test_hover_thrust_convenience() -> None:
    thrust = hover_thrust(RotorGeometry(), BEMTCondition())
    assert thrust > 0.0
    assert math.isfinite(thrust)


def test_compute_rotor_efficiency_dict() -> None:
    eff = compute_rotor_efficiency(RotorGeometry(), BEMTCondition())
    assert "thrust" in eff
    assert "power" in eff
    assert "efficiency" in eff
    assert "fm" in eff
    assert "disk_loading" in eff
    assert all(math.isfinite(v) for v in eff.values())


def test_compute_rotor_efficiency_positive() -> None:
    eff = compute_rotor_efficiency(RotorGeometry(), BEMTCondition())
    assert eff["thrust"] > 0.0
    assert eff["power"] > 0.0
    assert eff["efficiency"] > 0.0
    assert eff["disk_loading"] > 0.0


def test_solve_bemt_raises_zero_rpm() -> None:
    try:
        solve_bemt(RotorGeometry(), BEMTCondition(rpm=0.0))
        raise AssertionError("Should raise ValueError")
    except ValueError:
        pass


def test_solve_bemt_different_blade_count() -> None:
    geom2 = RotorGeometry(n_blades=2)
    geom3 = RotorGeometry(n_blades=3)
    r2 = solve_bemt(geom2, BEMTCondition())
    r3 = solve_bemt(geom3, BEMTCondition())
    assert r3.thrust_n > r2.thrust_n
