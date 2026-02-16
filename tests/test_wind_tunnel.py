"""Tests for computational wind tunnel and flight-sim integration."""

from __future__ import annotations

import math

import pytest
from reidce.wind_tunnel import (
    AirfoilGeometry,
    ConvergenceMetrics,
    DrydenGust,
    FlowCondition,
    WindTunnelResult,
    compute_aero,
    dryden_gust_velocities,
    interpolate_aero,
    run_wind_tunnel,
)

# ── AirfoilGeometry ──────────────────────────────────────────────────────


def test_airfoil_geometry_defaults() -> None:
    g = AirfoilGeometry()
    assert g.chord_m == 0.15
    assert g.span_m == 0.60
    assert g.oswald_efficiency == 0.85


def test_airfoil_effective_aspect_ratio() -> None:
    g = AirfoilGeometry(chord_m=0.10, span_m=0.80)
    ar = g.effective_aspect_ratio()
    assert abs(ar - 8.0) < 1e-6


def test_airfoil_explicit_aspect_ratio() -> None:
    g = AirfoilGeometry(aspect_ratio=6.0)
    assert g.effective_aspect_ratio() == 6.0


# ── FlowCondition properties ─────────────────────────────────────────────


def test_flow_condition_mach() -> None:
    c = FlowCondition(velocity_m_s=34.0, alpha_rad=0.0)
    # Speed of sound at 288.15 K ≈ 340 m/s → Mach ≈ 0.1
    assert abs(c.mach - 0.1) < 0.01


def test_flow_condition_reynolds() -> None:
    c = FlowCondition(velocity_m_s=20.0, alpha_rad=0.0)
    assert c.reynolds > 0.0


def test_flow_condition_dynamic_pressure() -> None:
    c = FlowCondition(velocity_m_s=10.0, alpha_rad=0.0, rho_kg_m3=1.225)
    q = c.dynamic_pressure_pa
    assert abs(q - 0.5 * 1.225 * 100.0) < 1e-6


# ── Single-point compute_aero ────────────────────────────────────────────


def test_compute_aero_zero_alpha_positive_cl() -> None:
    """Cambered airfoil at zero alpha should produce positive lift."""
    geom = AirfoilGeometry(camber_ratio=0.02)
    cond = FlowCondition(velocity_m_s=20.0, alpha_rad=0.0)
    r = compute_aero(geom, cond)
    assert r.cl > 0.0


def test_compute_aero_positive_drag() -> None:
    geom = AirfoilGeometry()
    cond = FlowCondition(velocity_m_s=20.0, alpha_rad=math.radians(5.0))
    r = compute_aero(geom, cond)
    assert r.cd > 0.0


def test_compute_aero_lift_increases_with_alpha() -> None:
    geom = AirfoilGeometry()
    r_low = compute_aero(geom, FlowCondition(velocity_m_s=20.0, alpha_rad=math.radians(2.0)))
    r_high = compute_aero(geom, FlowCondition(velocity_m_s=20.0, alpha_rad=math.radians(8.0)))
    assert r_high.cl > r_low.cl


def test_compute_aero_error_bounds_finite() -> None:
    geom = AirfoilGeometry()
    cond = FlowCondition(velocity_m_s=20.0, alpha_rad=math.radians(5.0))
    r = compute_aero(geom, cond)
    assert math.isfinite(r.cl_error)
    assert math.isfinite(r.cd_error)
    assert math.isfinite(r.cm_error)


def test_compute_aero_error_bounds_small() -> None:
    """Error bounds should be small relative to the coefficients."""
    geom = AirfoilGeometry()
    cond = FlowCondition(velocity_m_s=20.0, alpha_rad=math.radians(5.0))
    r = compute_aero(geom, cond)
    assert r.cl_error < abs(r.cl) * 0.05
    assert r.cd_error < abs(r.cd) * 0.05


def test_compute_aero_l_over_d() -> None:
    geom = AirfoilGeometry()
    cond = FlowCondition(velocity_m_s=20.0, alpha_rad=math.radians(5.0))
    r = compute_aero(geom, cond)
    expected = r.cl / abs(r.cd)
    assert abs(r.cl_over_cd - expected) < 0.1


def test_compute_aero_reynolds_and_mach_populated() -> None:
    geom = AirfoilGeometry()
    cond = FlowCondition(velocity_m_s=30.0, alpha_rad=math.radians(3.0))
    r = compute_aero(geom, cond)
    assert r.reynolds > 0.0
    assert r.mach > 0.0


def test_compute_aero_symmetric_airfoil_zero_lift_at_zero_alpha() -> None:
    """Symmetric airfoil (zero camber) should have ~0 lift at alpha=0."""
    geom = AirfoilGeometry(camber_ratio=0.0)
    cond = FlowCondition(velocity_m_s=20.0, alpha_rad=0.0)
    r = compute_aero(geom, cond)
    assert abs(r.cl) < 0.01


def test_compute_aero_compressibility_increases_cl() -> None:
    """Higher Mach should increase Cl via Prandtl-Glauert correction."""
    geom = AirfoilGeometry()
    alpha = math.radians(5.0)
    r_low_mach = compute_aero(
        geom, FlowCondition(velocity_m_s=20.0, alpha_rad=alpha),
    )
    r_high_mach = compute_aero(
        geom, FlowCondition(velocity_m_s=200.0, alpha_rad=alpha),
    )
    assert r_high_mach.cl > r_low_mach.cl


# ── Wind tunnel sweep ────────────────────────────────────────────────────


def test_run_wind_tunnel_returns_result() -> None:
    geom = AirfoilGeometry()
    wt = run_wind_tunnel(geom, velocities_m_s=[20.0], alphas_deg=[0.0, 5.0])
    assert isinstance(wt, WindTunnelResult)
    assert len(wt.sweep) == 2


def test_run_wind_tunnel_default_sweep() -> None:
    geom = AirfoilGeometry()
    wt = run_wind_tunnel(geom)
    # Default: 4 velocities × 20 alphas = 80 points
    assert len(wt.sweep) == 80


def test_run_wind_tunnel_best_l_over_d() -> None:
    geom = AirfoilGeometry()
    wt = run_wind_tunnel(geom, velocities_m_s=[20.0], alphas_deg=[0.0, 5.0, 10.0])
    assert wt.best_l_over_d > 0.0


def test_run_wind_tunnel_convergence_metrics() -> None:
    geom = AirfoilGeometry()
    wt = run_wind_tunnel(geom, velocities_m_s=[20.0], alphas_deg=[0.0, 5.0])
    assert isinstance(wt.convergence, ConvergenceMetrics)
    assert math.isfinite(wt.convergence.estimated_error)


def test_run_wind_tunnel_max_cl_and_min_cd() -> None:
    geom = AirfoilGeometry()
    wt = run_wind_tunnel(geom, velocities_m_s=[20.0], alphas_deg=[0.0, 5.0, 10.0])
    assert wt.max_cl > 0.0
    assert wt.min_cd > 0.0


# ── Interpolation ────────────────────────────────────────────────────────


def test_interpolate_aero_at_sweep_point() -> None:
    """Interpolation at an exact sweep point should match the original."""
    geom = AirfoilGeometry()
    wt = run_wind_tunnel(geom, velocities_m_s=[20.0], alphas_deg=[5.0])
    interp = interpolate_aero(wt, math.radians(5.0), 20.0)
    assert abs(interp.cl - wt.sweep[0].aero.cl) < 1e-6


def test_interpolate_aero_between_points() -> None:
    geom = AirfoilGeometry()
    wt = run_wind_tunnel(
        geom, velocities_m_s=[10.0, 30.0], alphas_deg=[0.0, 10.0],
    )
    interp = interpolate_aero(wt, math.radians(5.0), 20.0)
    assert math.isfinite(interp.cl)
    assert math.isfinite(interp.cd)


def test_interpolate_aero_outside_range() -> None:
    """Queries outside sweep range should return nearest-neighbour values."""
    geom = AirfoilGeometry()
    wt = run_wind_tunnel(geom, velocities_m_s=[20.0], alphas_deg=[5.0])
    interp = interpolate_aero(wt, math.radians(30.0), 100.0)
    assert math.isfinite(interp.cl)


def test_interpolate_empty_sweep() -> None:
    from reidce.wind_tunnel import ConvergenceMetrics, WindTunnelResult

    wt = WindTunnelResult(
        sweep=[], geometry=AirfoilGeometry(),
        convergence=ConvergenceMetrics(0, 0, 0, 0, 2),
        max_cl=0, min_cd=0, best_l_over_d=0, best_l_over_d_alpha_rad=0,
    )
    r = interpolate_aero(wt, 0.0, 20.0)
    assert r.cl == 0.0


# ── Dryden gust model ────────────────────────────────────────────────────


def test_dryden_gust_deterministic() -> None:
    """Same seed must produce identical gust sequences."""
    gust = DrydenGust(seed=123)
    times = [i * 0.01 for i in range(100)]
    v1 = dryden_gust_velocities(gust, times, 15.0)
    v2 = dryden_gust_velocities(gust, times, 15.0)
    assert v1 == v2


def test_dryden_gust_length() -> None:
    gust = DrydenGust()
    times = [i * 0.01 for i in range(50)]
    vels = dryden_gust_velocities(gust, times, 20.0)
    assert len(vels) == 50


def test_dryden_gust_three_components() -> None:
    gust = DrydenGust()
    times = [i * 0.01 for i in range(10)]
    vels = dryden_gust_velocities(gust, times, 20.0)
    for u, v, w in vels:
        assert math.isfinite(u)
        assert math.isfinite(v)
        assert math.isfinite(w)


def test_dryden_gust_intensity_scales() -> None:
    """Higher intensity should produce larger gust magnitudes on average."""
    times = [i * 0.01 for i in range(200)]
    low = dryden_gust_velocities(DrydenGust(intensity_m_s=0.5, seed=1), times, 20.0)
    high = dryden_gust_velocities(DrydenGust(intensity_m_s=5.0, seed=1), times, 20.0)
    avg_low = sum(abs(u) for u, _, _ in low) / len(low)
    avg_high = sum(abs(u) for u, _, _ in high) / len(high)
    assert avg_high > avg_low


# ── Flight-sim integration ───────────────────────────────────────────────


def test_simulate_flight_wind_tunnel_runs() -> None:
    from reidce.flight_sim import (
        GuidanceTarget,
        SimulationResult,
        VehicleState,
        simulate_flight_wind_tunnel,
    )

    geom = AirfoilGeometry()
    wt = run_wind_tunnel(geom, velocities_m_s=[5.0, 15.0, 30.0])
    state = VehicleState(z_m=50.0, vx_m_s=10.0)
    target = GuidanceTarget(altitude_m=60.0, speed_m_s=12.0, heading_rad=0.0)
    result = simulate_flight_wind_tunnel(state, target, 1.0, 0.1, wt)
    assert isinstance(result, SimulationResult)
    assert len(result.time_s) > 0
    assert len(result.state) > 0


def test_simulate_flight_wind_tunnel_energy_increases() -> None:
    from reidce.flight_sim import (
        GuidanceTarget,
        VehicleState,
        simulate_flight_wind_tunnel,
    )

    geom = AirfoilGeometry()
    wt = run_wind_tunnel(geom, velocities_m_s=[5.0, 20.0])
    state = VehicleState(z_m=50.0, vx_m_s=10.0)
    target = GuidanceTarget(altitude_m=60.0, speed_m_s=12.0, heading_rad=0.0)
    result = simulate_flight_wind_tunnel(state, target, 2.0, 0.1, wt)
    assert result.energy_used_j[-1] > result.energy_used_j[0]


def test_simulate_flight_wind_tunnel_with_gust() -> None:
    from reidce.flight_sim import (
        GuidanceTarget,
        VehicleState,
        simulate_flight_wind_tunnel,
    )

    geom = AirfoilGeometry()
    wt = run_wind_tunnel(geom, velocities_m_s=[5.0, 20.0])
    state = VehicleState(z_m=50.0, vx_m_s=10.0)
    target = GuidanceTarget(altitude_m=60.0, speed_m_s=12.0, heading_rad=0.0)
    gust = DrydenGust(intensity_m_s=2.0)
    result = simulate_flight_wind_tunnel(state, target, 2.0, 0.1, wt, gust=gust)
    assert len(result.state) > 0


def test_simulate_flight_wind_tunnel_invalid_duration() -> None:
    from reidce.flight_sim import (
        GuidanceTarget,
        VehicleState,
        simulate_flight_wind_tunnel,
    )

    geom = AirfoilGeometry()
    wt = run_wind_tunnel(geom, velocities_m_s=[20.0], alphas_deg=[5.0])
    state = VehicleState()
    target = GuidanceTarget(altitude_m=50.0, speed_m_s=10.0, heading_rad=0.0)
    with pytest.raises(ValueError):
        simulate_flight_wind_tunnel(state, target, -1.0, 0.1, wt)


def test_simulate_flight_wind_tunnel_invalid_tunnel_result() -> None:
    from reidce.flight_sim import (
        GuidanceTarget,
        VehicleState,
        simulate_flight_wind_tunnel,
    )

    state = VehicleState()
    target = GuidanceTarget(altitude_m=50.0, speed_m_s=10.0, heading_rad=0.0)
    with pytest.raises(TypeError):
        simulate_flight_wind_tunnel(state, target, 1.0, 0.1, "not_a_result")


def test_simulate_flight_wind_tunnel_battery_depletes() -> None:
    from reidce.flight_sim import (
        GuidanceTarget,
        VehicleState,
        simulate_flight_wind_tunnel,
    )

    geom = AirfoilGeometry()
    wt = run_wind_tunnel(geom, velocities_m_s=[5.0, 20.0])
    state = VehicleState(z_m=50.0, vx_m_s=10.0)
    target = GuidanceTarget(altitude_m=60.0, speed_m_s=12.0, heading_rad=0.0)
    result = simulate_flight_wind_tunnel(state, target, 2.0, 0.1, wt)
    assert result.battery_pct[-1] < result.battery_pct[0]
