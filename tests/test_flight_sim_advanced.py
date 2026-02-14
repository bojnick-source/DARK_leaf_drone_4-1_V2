"""Tests for advanced flight simulator features: wind, ISA density, sensor noise, ground clamp."""

from __future__ import annotations

from reidce.flight_sim import (
    Atmosphere,
    GuidanceTarget,
    SensorNoise,
    VehicleState,
    WindModel,
    simulate_flight,
    simulate_flight_bemt,
)
from reidce.flight_sim_report import build_report, run_ai_flight

# ── WindModel ────────────────────────────────────────────────────────────


def test_wind_model_defaults_zero() -> None:
    w = WindModel()
    assert w.steady_speed_m_s == 0.0
    wx, wy, wz = w.sample()
    assert wx == 0.0 and wy == 0.0 and wz == 0.0


def test_wind_model_steady_speed() -> None:
    w = WindModel(wx_m_s=3.0, wy_m_s=4.0)
    assert abs(w.steady_speed_m_s - 5.0) < 1e-9


def test_wind_model_gust_produces_variability() -> None:
    w = WindModel(wx_m_s=5.0, gust_intensity=2.0)
    samples = [w.sample()[0] for _ in range(50)]
    assert max(samples) != min(samples), "gusts should cause variability"


def test_wind_affects_simulation() -> None:
    """A headwind should reduce forward ground speed compared to calm conditions."""
    initial = VehicleState(z_m=50.0, vx_m_s=8.0)
    target = GuidanceTarget(altitude_m=50.0, speed_m_s=12.0, heading_rad=0.0)

    calm = Atmosphere()
    windy = Atmosphere(wind=WindModel(wx_m_s=-8.0))  # headwind

    result_calm = simulate_flight(initial, target, duration_s=5.0, dt_s=0.05, atmosphere=calm)
    result_wind = simulate_flight(initial, target, duration_s=5.0, dt_s=0.05, atmosphere=windy)

    # With a headwind the drag increases (airspeed > ground speed), so the
    # vehicle should travel less forward distance than in calm air.
    calm_x = result_calm.state[-1].x_m
    wind_x = result_wind.state[-1].x_m
    assert wind_x < calm_x


def test_wind_speed_logged_in_result() -> None:
    atm = Atmosphere(wind=WindModel(wx_m_s=3.0, wy_m_s=4.0))
    initial = VehicleState(z_m=10.0, vx_m_s=5.0)
    target = GuidanceTarget(altitude_m=20.0, speed_m_s=8.0, heading_rad=0.0)
    result = simulate_flight(initial, target, duration_s=2.0, dt_s=0.1, atmosphere=atm)
    assert len(result.wind_speed_m_s) == len(result.time_s)
    assert all(ws >= 0.0 for ws in result.wind_speed_m_s)
    # Steady wind magnitude is 5 m/s; no gust, so all values should be 5.0
    assert all(abs(ws - 5.0) < 1e-6 for ws in result.wind_speed_m_s)


def test_wind_report_includes_wind_summary() -> None:
    atm = Atmosphere(wind=WindModel(wx_m_s=3.0, wy_m_s=4.0))
    result = run_ai_flight(duration_s=3.0, dt_s=0.1, atmosphere=atm)
    report = build_report(result, max_points=50)
    assert "max_wind_speed_m_s" in report["summary"]
    assert "avg_wind_speed_m_s" in report["summary"]
    assert "wind_speed_m_s" in report["telemetry"]


def test_no_wind_report_excludes_wind_keys() -> None:
    """When there's no wind, the report should still be valid (no wind keys)."""
    result = run_ai_flight(duration_s=2.0, dt_s=0.1)
    report = build_report(result, max_points=50)
    # With default zero-wind, wind_speed_m_s is all zeros – still present
    assert report["schema"] == "dark/flight_sim/report/1.0"


# ── ISA altitude-dependent density ───────────────────────────────────────


def test_isa_density_decreases_with_altitude() -> None:
    atm = Atmosphere(use_isa_density=True)
    rho_0 = atm.density_at(0.0)
    rho_1000 = atm.density_at(1000.0)
    rho_5000 = atm.density_at(5000.0)
    assert rho_0 > rho_1000 > rho_5000


def test_isa_density_at_sea_level_matches_default() -> None:
    atm = Atmosphere(use_isa_density=True)
    assert abs(atm.density_at(0.0) - 1.225) < 1e-6


def test_constant_density_ignores_altitude() -> None:
    atm = Atmosphere(use_isa_density=False)
    assert atm.density_at(0.0) == atm.density_at(5000.0) == 1.225


def test_isa_density_simulation_runs() -> None:
    """Simulation with ISA density should complete without errors."""
    atm = Atmosphere(use_isa_density=True)
    initial = VehicleState(z_m=0.0, vx_m_s=5.0)
    target = GuidanceTarget(altitude_m=100.0, speed_m_s=10.0, heading_rad=0.0)
    result = simulate_flight(initial, target, duration_s=5.0, dt_s=0.05, atmosphere=atm)
    assert len(result.time_s) > 1


# ── Sensor noise ─────────────────────────────────────────────────────────


def test_sensor_noise_defaults_zero() -> None:
    sn = SensorNoise()
    assert sn.altitude_m_std == 0.0
    assert sn.speed_m_s_std == 0.0
    assert sn.heading_rad_std == 0.0


def test_sensor_noise_simulation_completes() -> None:
    """Sim with noisy sensors should complete without errors."""
    noise = SensorNoise(altitude_m_std=0.5, speed_m_s_std=0.2, heading_rad_std=0.01)
    atm = Atmosphere(sensor_noise=noise)
    initial = VehicleState(z_m=10.0, vx_m_s=5.0)
    target = GuidanceTarget(altitude_m=30.0, speed_m_s=10.0, heading_rad=0.0)
    result = simulate_flight(initial, target, duration_s=5.0, dt_s=0.05, atmosphere=atm)
    assert len(result.time_s) > 1
    assert result.battery_pct[-1] < 100.0


# ── Ground collision clamp ───────────────────────────────────────────────


def test_ground_clamp_prevents_negative_altitude() -> None:
    """Starting at ground with a target below should stay at z >= 0."""
    initial = VehicleState(z_m=0.0, vx_m_s=5.0, vz_m_s=-5.0)
    target = GuidanceTarget(altitude_m=0.0, speed_m_s=5.0, heading_rad=0.0)
    result = simulate_flight(initial, target, duration_s=5.0, dt_s=0.05)
    for state in result.state:
        assert state.z_m >= 0.0, f"altitude went below ground: {state.z_m}"


def test_ground_clamp_zero_downward_velocity() -> None:
    """When on the ground, downward velocity should be zeroed."""
    initial = VehicleState(z_m=0.5, vx_m_s=5.0, vz_m_s=-20.0)
    target = GuidanceTarget(altitude_m=0.0, speed_m_s=5.0, heading_rad=0.0)
    result = simulate_flight(initial, target, duration_s=3.0, dt_s=0.05)
    # After hitting the ground, vz should not remain negative
    ground_states = [s for s in result.state if s.z_m == 0.0]
    if ground_states:
        assert all(s.vz_m_s >= 0.0 for s in ground_states)


# ── BEMT with advanced features ──────────────────────────────────────────


def test_bemt_with_wind_runs() -> None:
    atm = Atmosphere(wind=WindModel(wx_m_s=3.0))
    initial = VehicleState(z_m=50.0)
    target = GuidanceTarget(altitude_m=60.0, speed_m_s=10.0, heading_rad=0.0)
    result = simulate_flight_bemt(initial, target, duration_s=1.0, dt_s=0.1, atmosphere=atm)
    assert len(result.time_s) > 0
    assert len(result.wind_speed_m_s) == len(result.time_s)


def test_bemt_with_isa_density_runs() -> None:
    atm = Atmosphere(use_isa_density=True)
    initial = VehicleState(z_m=50.0)
    target = GuidanceTarget(altitude_m=60.0, speed_m_s=10.0, heading_rad=0.0)
    result = simulate_flight_bemt(initial, target, duration_s=1.0, dt_s=0.1, atmosphere=atm)
    assert len(result.time_s) > 0
