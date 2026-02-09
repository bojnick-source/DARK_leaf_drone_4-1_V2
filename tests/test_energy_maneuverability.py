import math

from reidce.energy_maneuverability import (
    EMState,
    StructuralLimits,
    compute_drag,
    compute_em_envelope,
    compute_em_state,
    find_sustained_turn_rate,
    load_factor,
    specific_energy,
    specific_excess_power,
    turn_radius,
    turn_rate,
)
from reidce.flight_sim import Atmosphere, VehicleParams, VehicleState


def test_specific_energy_ground_level() -> None:
    """At ground level with zero speed, specific energy equals altitude."""
    assert specific_energy(0.0, 0.0) == 0.0
    assert specific_energy(0.0, 100.0) == 100.0


def test_specific_energy_includes_kinetic() -> None:
    se = specific_energy(10.0, 50.0)
    kinetic = 10.0**2 / (2.0 * 9.80665)
    assert abs(se - (50.0 + kinetic)) < 0.01


def test_load_factor_level_flight() -> None:
    """Level flight (bank=0) should give n=1."""
    assert abs(load_factor(0.0) - 1.0) < 1e-6


def test_load_factor_60_degrees() -> None:
    """60° bank → n = 1/cos(60°) = 2.0."""
    n = load_factor(math.radians(60.0))
    assert abs(n - 2.0) < 0.01


def test_turn_rate_zero_speed() -> None:
    assert turn_rate(0.0, math.radians(30.0)) == 0.0


def test_turn_rate_positive_for_banked_flight() -> None:
    omega = turn_rate(15.0, math.radians(45.0))
    assert omega > 0.0


def test_turn_radius_finite_in_turn() -> None:
    r = turn_radius(15.0, math.radians(45.0))
    assert r > 0.0
    assert r < float("inf")


def test_turn_radius_infinite_wings_level() -> None:
    r = turn_radius(15.0, 0.0)
    assert r == float("inf")


def test_specific_excess_power_positive_when_thrust_exceeds_drag() -> None:
    ps = specific_excess_power(50.0, 20.0, 24.0, 12.0)
    assert ps > 0.0


def test_specific_excess_power_negative_when_drag_exceeds_thrust() -> None:
    ps = specific_excess_power(10.0, 30.0, 24.0, 12.0)
    assert ps < 0.0


def test_compute_drag_increases_with_load_factor() -> None:
    params = VehicleParams()
    atm = Atmosphere()
    d1 = compute_drag(15.0, 0.0, params, atm, n_load=1.0)
    d2 = compute_drag(15.0, 0.0, params, atm, n_load=2.0)
    assert d2 > d1


def test_compute_em_state_returns_valid_snapshot() -> None:
    params = VehicleParams()
    atm = Atmosphere()
    limits = StructuralLimits()
    state = VehicleState(z_m=30.0, vx_m_s=12.0)
    em = compute_em_state(state, 0.8, 0.0, params, atm, limits)
    assert isinstance(em, EMState)
    assert em.speed_m_s > 0.0
    assert em.altitude_m == 30.0


def test_compute_em_state_detects_structural_limit() -> None:
    params = VehicleParams()
    atm = Atmosphere()
    limits = StructuralLimits(max_g=1.5)
    state = VehicleState(z_m=30.0, vx_m_s=12.0)
    em = compute_em_state(state, 0.8, math.radians(60.0), params, atm, limits)
    assert em.exceeded_structural_limit is True


def test_compute_em_envelope_returns_results() -> None:
    params = VehicleParams()
    atm = Atmosphere()
    limits = StructuralLimits()
    results = compute_em_envelope(
        params, atm, limits,
        speeds_m_s=[5.0, 10.0, 20.0],
        altitudes_m=[0.0, 50.0],
    )
    assert len(results) == 6  # 3 speeds × 2 altitudes


def test_find_sustained_turn_rate_nonnegative() -> None:
    params = VehicleParams()
    atm = Atmosphere()
    rate = find_sustained_turn_rate(12.0, 30.0, 0.9, params, atm)
    assert rate >= 0.0
