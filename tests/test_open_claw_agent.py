"""Tests for reidce.open_claw_agent — open-claw agent pipeline."""

from reidce.memory import MemoryStore
from reidce.open_claw_agent import (
    ClawSpec,
    OpenClawResult,
    compute_opening_trajectory,
    estimate_energy_j,
    run_open_claw_agent,
    run_safety_checks,
)

# ── ClawSpec ─────────────────────────────────────────────────────────


def test_default_spec_values() -> None:
    spec = ClawSpec()
    assert spec.finger_count == 3
    assert spec.finger_length_m > 0
    assert spec.max_open_angle_deg > spec.closed_angle_deg
    assert spec.servo_torque_nm > 0
    assert spec.servo_speed_dps > 0


def test_custom_spec() -> None:
    spec = ClawSpec(finger_count=4, finger_length_m=0.1)
    assert spec.finger_count == 4
    assert spec.finger_length_m == 0.1


# ── compute_opening_trajectory ───────────────────────────────────────


def test_trajectory_default() -> None:
    traj = compute_opening_trajectory(ClawSpec())
    assert len(traj) > 0
    assert traj[0].angle_deg >= ClawSpec().closed_angle_deg
    assert traj[-1].angle_deg == ClawSpec().max_open_angle_deg


def test_trajectory_starts_at_closed() -> None:
    spec = ClawSpec()
    traj = compute_opening_trajectory(spec)
    # First point should be at or near the closed angle
    assert abs(traj[0].angle_deg - spec.closed_angle_deg) < 1.0


def test_trajectory_ends_at_open() -> None:
    spec = ClawSpec()
    traj = compute_opening_trajectory(spec)
    assert traj[-1].angle_deg == spec.max_open_angle_deg
    assert traj[-1].angular_velocity_dps == 0.0


def test_trajectory_monotonically_increasing_angle() -> None:
    traj = compute_opening_trajectory(ClawSpec())
    for i in range(1, len(traj)):
        assert traj[i].angle_deg >= traj[i - 1].angle_deg


def test_trajectory_time_increases() -> None:
    traj = compute_opening_trajectory(ClawSpec())
    for i in range(1, len(traj)):
        assert traj[i].time_s >= traj[i - 1].time_s


def test_trajectory_custom_time_step() -> None:
    traj_fine = compute_opening_trajectory(ClawSpec(), time_step_s=0.005)
    traj_coarse = compute_opening_trajectory(ClawSpec(), time_step_s=0.05)
    assert len(traj_fine) > len(traj_coarse)


def test_trajectory_zero_travel() -> None:
    """When open angle equals closed angle the trajectory is a single point."""
    spec = ClawSpec(max_open_angle_deg=10.0, closed_angle_deg=10.0)
    traj = compute_opening_trajectory(spec)
    assert len(traj) == 1
    assert traj[0].angle_deg == 10.0


def test_trajectory_invalid_time_step() -> None:
    import pytest

    with pytest.raises(ValueError):
        compute_opening_trajectory(ClawSpec(), time_step_s=0.0)
    with pytest.raises(ValueError):
        compute_opening_trajectory(ClawSpec(), time_step_s=-0.01)


# ── run_safety_checks ────────────────────────────────────────────────


def test_safety_checks_default_pass() -> None:
    checks = run_safety_checks(ClawSpec())
    assert all(c.passed for c in checks)
    assert len(checks) >= 5


def test_safety_check_names() -> None:
    checks = run_safety_checks(ClawSpec())
    names = {c.name for c in checks}
    assert "servo_torque_positive" in names
    assert "open_exceeds_closed" in names
    assert "min_finger_count" in names
    assert "mass_budget" in names
    assert "grip_force_positive" in names


def test_safety_check_fails_bad_torque() -> None:
    spec = ClawSpec(servo_torque_nm=0.0)
    checks = run_safety_checks(spec)
    torque_check = [c for c in checks if c.name == "servo_torque_positive"][0]
    assert torque_check.passed is False


def test_safety_check_fails_bad_angle() -> None:
    spec = ClawSpec(max_open_angle_deg=5.0, closed_angle_deg=10.0)
    checks = run_safety_checks(spec)
    angle_check = [c for c in checks if c.name == "open_exceeds_closed"][0]
    assert angle_check.passed is False


def test_safety_check_fails_single_finger() -> None:
    spec = ClawSpec(finger_count=1)
    checks = run_safety_checks(spec)
    finger_check = [c for c in checks if c.name == "min_finger_count"][0]
    assert finger_check.passed is False


def test_safety_check_fails_overweight() -> None:
    spec = ClawSpec(mass_kg=3.0)
    checks = run_safety_checks(spec)
    mass_check = [c for c in checks if c.name == "mass_budget"][0]
    assert mass_check.passed is False


# ── estimate_energy_j ────────────────────────────────────────────────


def test_energy_positive() -> None:
    spec = ClawSpec()
    energy = estimate_energy_j(spec, total_time_s=0.5)
    assert energy > 0.0


def test_energy_zero_travel() -> None:
    spec = ClawSpec(max_open_angle_deg=10.0, closed_angle_deg=10.0)
    energy = estimate_energy_j(spec, total_time_s=0.5)
    assert energy == 0.0


# ── run_open_claw_agent ──────────────────────────────────────────────


def test_run_agent_default() -> None:
    result = run_open_claw_agent()
    assert isinstance(result, OpenClawResult)
    assert result.all_checks_passed is True
    assert result.total_time_s > 0.0
    assert len(result.trajectory) > 0
    assert len(result.safety_checks) >= 5
    assert result.energy_estimate_j > 0.0


def test_run_agent_custom_spec() -> None:
    spec = ClawSpec(finger_count=4, finger_length_m=0.1)
    result = run_open_claw_agent(spec=spec)
    assert result.spec.finger_count == 4
    assert result.all_checks_passed is True


def test_run_agent_with_memory_store() -> None:
    mem = MemoryStore()
    result = run_open_claw_agent(memory_store=mem)
    assert result.all_checks_passed is True
    events = [r for r in mem.records if "open_claw_agent" in r.tags]
    assert len(events) >= 1


def test_run_agent_peak_velocity() -> None:
    result = run_open_claw_agent()
    assert result.peak_angular_velocity_dps > 0.0
    # Peak velocity should not exceed servo limit
    assert result.peak_angular_velocity_dps <= result.spec.servo_speed_dps


def test_run_agent_safety_failure_propagates() -> None:
    spec = ClawSpec(servo_torque_nm=0.0)
    result = run_open_claw_agent(spec=spec)
    assert result.all_checks_passed is False
