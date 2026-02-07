from reidce.flight_sim import (
    GuidanceTarget,
    TripleRedundantController,
    VehicleState,
    simulate_flight,
)


def test_median_even_length_list() -> None:
    """Regression: _median must average two middle values for even-length lists."""
    from reidce.flight_sim import _median

    assert _median([1.0, 3.0]) == 2.0
    assert _median([1.0, 2.0, 3.0, 4.0]) == 2.5
    assert _median([10.0, 20.0]) == 15.0


def test_median_odd_length_list() -> None:
    """_median returns middle value for odd-length lists."""
    from reidce.flight_sim import _median

    assert _median([1.0, 2.0, 3.0]) == 2.0
    assert _median([5.0]) == 5.0
    assert _median([1.0, 3.0, 5.0, 7.0, 9.0]) == 5.0


def test_flight_sim_converges_altitude() -> None:
    initial = VehicleState(z_m=0.0, vx_m_s=8.0)
    target = GuidanceTarget(altitude_m=50.0, speed_m_s=12.0, heading_rad=0.0)
    controller = TripleRedundantController()
    result = simulate_flight(initial, target, duration_s=20.0, dt_s=0.05, controller=controller)
    final_alt = result.state[-1].z_m
    assert final_alt > 30.0


def test_triple_redundant_voting_with_fault() -> None:
    initial = VehicleState(z_m=10.0, vx_m_s=5.0)
    target = GuidanceTarget(altitude_m=20.0, speed_m_s=8.0, heading_rad=0.2)
    controller = TripleRedundantController(channel_faults=(True, False, False))
    result = simulate_flight(initial, target, duration_s=10.0, dt_s=0.05, controller=controller)
    assert len(result.commands) == len(result.state)
