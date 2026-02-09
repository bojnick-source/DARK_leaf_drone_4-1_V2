import json

from reidce.design_loop import (
    IterationLog,
    iteration_log_to_dict,
    run_design_loop,
)
from reidce.flight_sim import VehicleParams


def test_run_design_loop_returns_iteration_log() -> None:
    log = run_design_loop(max_iterations=2)
    assert isinstance(log, IterationLog)
    assert len(log.iterations) >= 1
    assert len(log.iterations) <= 2


def test_design_loop_produces_test_results() -> None:
    log = run_design_loop(max_iterations=1)
    record = log.iterations[0]
    assert len(record.test_results) == 4
    test_names = {t.test_name for t in record.test_results}
    assert test_names == {"climb", "speed", "turn", "endurance"}


def test_design_loop_scores_design() -> None:
    log = run_design_loop(max_iterations=1)
    assert log.iterations[0].score >= 0.0
    assert log.iterations[0].score <= 100.0


def test_design_loop_best_score_tracked() -> None:
    log = run_design_loop(max_iterations=3)
    assert log.best_score >= 0.0
    assert 0 <= log.best_iteration < len(log.iterations)


def test_design_loop_learns_from_failures() -> None:
    """When failures occur, the loop should produce adjustments."""
    # Use params that will fail climb test (very low thrust, heavy)
    weak_params = VehicleParams(max_thrust_n=5.0, mass_kg=10.0, wing_area_m2=0.1)
    log = run_design_loop(initial_params=weak_params, max_iterations=3)
    # At least one iteration should have adjustments
    has_adjustments = any(len(r.adjustments) > 0 for r in log.iterations)
    assert has_adjustments


def test_design_loop_adjusts_parameters() -> None:
    """After learning, rebuilt params should differ from initial."""
    weak_params = VehicleParams(max_thrust_n=5.0, mass_kg=10.0, wing_area_m2=0.1)
    log = run_design_loop(initial_params=weak_params, max_iterations=3)
    if len(log.iterations) >= 2:
        p0 = log.iterations[0].params
        p1 = log.iterations[1].params
        changed = (
            p0.max_thrust_n != p1.max_thrust_n
            or p0.cd0 != p1.cd0
            or p0.mass_kg != p1.mass_kg
            or p0.wing_area_m2 != p1.wing_area_m2
            or p0.max_tilt_rad != p1.max_tilt_rad
        )
        assert changed


def test_design_loop_em_snapshot_present() -> None:
    log = run_design_loop(max_iterations=1)
    assert log.iterations[0].em_snapshot is not None
    assert log.iterations[0].em_snapshot.ps_m_s is not None


def test_design_loop_convergence() -> None:
    """With a very low convergence score, the loop should converge quickly."""
    log = run_design_loop(max_iterations=10, convergence_score=5.0)
    assert log.converged is True
    assert len(log.iterations) <= 10


def test_iteration_log_to_dict_schema() -> None:
    log = run_design_loop(max_iterations=2)
    d = iteration_log_to_dict(log)
    assert d["schema"] == "dark/design_loop/log/1.0"
    assert "converged" in d
    assert "best_iteration" in d
    assert "best_score" in d
    assert "iterations" in d
    assert len(d["iterations"]) == len(log.iterations)


def test_iteration_log_to_dict_json_serializable() -> None:
    log = run_design_loop(max_iterations=2)
    d = iteration_log_to_dict(log)
    serialized = json.dumps(d)
    assert isinstance(serialized, str)
    roundtrip = json.loads(serialized)
    assert roundtrip["schema"] == d["schema"]


def test_iteration_log_contains_tests_and_adjustments() -> None:
    log = run_design_loop(max_iterations=2)
    d = iteration_log_to_dict(log)
    for it in d["iterations"]:
        assert "tests" in it
        assert "adjustments" in it
        assert "params" in it
        assert "em_snapshot" in it
        for t in it["tests"]:
            assert "name" in t
            assert "passed" in t
