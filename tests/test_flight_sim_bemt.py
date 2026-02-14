"""Tests for BEMT-enhanced flight simulation and rotor model."""

from __future__ import annotations

import math

from reidce.flight_sim import (
    GuidanceTarget,
    RotorParams,
    SimulationResult,
    VehicleState,
    bemt_rotor_thrust,
    simulate_flight_bemt,
)


def test_rotor_params_defaults() -> None:
    rp = RotorParams()
    assert rp.n_rotors == 4
    assert rp.rotor_radius_m == 0.12
    assert rp.n_blades == 2
    assert rp.base_rpm == 8000.0


def test_bemt_rotor_thrust_hover() -> None:
    result = bemt_rotor_thrust(1.0, 0.0, RotorParams())
    assert result["thrust_n"] > 0.0
    assert result["power_w"] > 0.0
    assert math.isfinite(result["fm"])
    assert result["rpm"] > 0.0


def test_bemt_rotor_thrust_zero_throttle() -> None:
    result = bemt_rotor_thrust(0.0, 0.0, RotorParams())
    # At 20% idle RPM, there should still be some thrust
    assert result["thrust_n"] >= 0.0
    assert result["rpm"] > 0.0


def test_bemt_rotor_thrust_higher_throttle_more_thrust() -> None:
    low = bemt_rotor_thrust(0.3, 0.0, RotorParams())
    high = bemt_rotor_thrust(0.9, 0.0, RotorParams())
    assert high["thrust_n"] > low["thrust_n"]


def test_bemt_rotor_thrust_clamped_throttle() -> None:
    r1 = bemt_rotor_thrust(-0.5, 0.0, RotorParams())
    r2 = bemt_rotor_thrust(0.0, 0.0, RotorParams())
    assert r1["rpm"] == r2["rpm"]

    r3 = bemt_rotor_thrust(2.0, 0.0, RotorParams())
    r4 = bemt_rotor_thrust(1.0, 0.0, RotorParams())
    assert r3["rpm"] == r4["rpm"]


def test_bemt_rotor_thrust_keys() -> None:
    result = bemt_rotor_thrust(0.5, 0.0, RotorParams())
    assert set(result.keys()) == {"thrust_n", "power_w", "torque_nm", "rpm", "fm"}


def test_bemt_rotor_thrust_n_rotors_scaling() -> None:
    r2 = bemt_rotor_thrust(0.8, 0.0, RotorParams(n_rotors=2))
    r4 = bemt_rotor_thrust(0.8, 0.0, RotorParams(n_rotors=4))
    assert abs(r4["thrust_n"] - 2.0 * r2["thrust_n"]) < 0.01


def test_simulate_flight_bemt_runs() -> None:
    state = VehicleState(z_m=50.0)
    target = GuidanceTarget(altitude_m=60.0, speed_m_s=10.0, heading_rad=0.0)
    result = simulate_flight_bemt(state, target, duration_s=1.0, dt_s=0.1)
    assert isinstance(result, SimulationResult)
    assert len(result.time_s) > 0
    assert len(result.state) > 0


def test_simulate_flight_bemt_energy_increases() -> None:
    state = VehicleState(z_m=50.0)
    target = GuidanceTarget(altitude_m=60.0, speed_m_s=10.0, heading_rad=0.0)
    result = simulate_flight_bemt(state, target, duration_s=2.0, dt_s=0.1)
    assert result.energy_used_j[-1] > result.energy_used_j[0]


def test_simulate_flight_bemt_battery_depletes() -> None:
    state = VehicleState(z_m=50.0)
    target = GuidanceTarget(altitude_m=60.0, speed_m_s=10.0, heading_rad=0.0)
    result = simulate_flight_bemt(state, target, duration_s=2.0, dt_s=0.1)
    assert result.battery_pct[-1] < result.battery_pct[0]


def test_simulate_flight_bemt_invalid_duration() -> None:
    state = VehicleState()
    target = GuidanceTarget(altitude_m=50.0, speed_m_s=10.0, heading_rad=0.0)
    try:
        simulate_flight_bemt(state, target, duration_s=-1.0, dt_s=0.1)
        raise AssertionError("Should raise ValueError")
    except ValueError:
        pass
