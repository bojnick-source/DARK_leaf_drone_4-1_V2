"""Open-claw agent for the DARK leaf 4-1 competition drone.

Orchestrates the payload release sequence by commanding the gripper
mechanism from a closed (gripping) state to a fully open position.
The agent validates servo parameters, computes an opening trajectory
with configurable speed profiles, runs safety pre-checks, and logs
every step to the shared :class:`MemoryStore`.

Key components
--------------
* ``ClawSpec`` — physical and servo parameters for the claw mechanism.
* ``OpenClawResult`` — structured output with trajectory, safety
  checks, and timing summary.
* ``compute_opening_trajectory`` — generates the angular trajectory
  for the claw servo from closed to open.
* ``run_open_claw_agent`` — top-level orchestrator that validates,
  plans, and executes the open-claw sequence.

The agent is intentionally local and deterministic — no external API
calls.  All parameters default to DARPA LIFT 4:1 competition
constraints for the payload-release gripper.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from reidce.memory import MemoryStore

# ── Claw specification ───────────────────────────────────────────────


@dataclass(frozen=True)
class ClawSpec:
    """Physical and servo parameters for the drone gripper mechanism.

    Defaults are sized for a competition-class payload-release claw
    capable of securing payloads up to 50 kg with a single-servo
    actuation.

    Parameters
    ----------
    finger_count:
        Number of gripper fingers (symmetric arrangement).
    finger_length_m:
        Length of each finger from pivot to tip.
    max_open_angle_deg:
        Fully open angle per finger measured from the closed axis.
    closed_angle_deg:
        Angle when the claw is fully gripping a payload.
    servo_torque_nm:
        Peak torque available from the claw servo.
    servo_speed_dps:
        Maximum angular velocity of the servo (degrees / second).
    grip_force_n:
        Nominal grip force applied to the payload when closed.
    mass_kg:
        Total mass of the claw mechanism (fingers + servo + mount).
    """

    finger_count: int = 3
    finger_length_m: float = 0.08
    max_open_angle_deg: float = 90.0
    closed_angle_deg: float = 5.0
    servo_torque_nm: float = 2.5
    servo_speed_dps: float = 300.0
    grip_force_n: float = 120.0
    mass_kg: float = 0.35


# ── Trajectory point ─────────────────────────────────────────────────


@dataclass(frozen=True)
class TrajectoryPoint:
    """A single point on the claw opening trajectory."""

    time_s: float
    angle_deg: float
    angular_velocity_dps: float


# ── Safety check result ──────────────────────────────────────────────


@dataclass(frozen=True)
class SafetyCheck:
    """Result of a single pre-open safety check."""

    name: str
    passed: bool
    detail: str


# ── Agent result ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class OpenClawResult:
    """Structured output of the open-claw agent pipeline."""

    spec: ClawSpec
    trajectory: List[TrajectoryPoint]
    safety_checks: List[SafetyCheck]
    all_checks_passed: bool
    total_time_s: float
    peak_angular_velocity_dps: float
    energy_estimate_j: float
    metadata: Dict[str, Any] = field(default_factory=dict)


# ── Trajectory computation ───────────────────────────────────────────


def compute_opening_trajectory(
    spec: ClawSpec,
    time_step_s: float = 0.01,
) -> List[TrajectoryPoint]:
    """Compute the angular trajectory for opening the claw.

    Uses a sinusoidal (smooth) velocity profile so the mechanism
    accelerates and decelerates gently, reducing mechanical shock on
    the payload and airframe.

    Returns a list of :class:`TrajectoryPoint` sampled at *time_step_s*
    intervals.
    """
    if time_step_s <= 0.0:
        raise ValueError("time_step_s must be positive")

    travel_deg = spec.max_open_angle_deg - spec.closed_angle_deg
    if travel_deg <= 0.0:
        return [
            TrajectoryPoint(
                time_s=0.0,
                angle_deg=spec.closed_angle_deg,
                angular_velocity_dps=0.0,
            )
        ]

    # Time for a smooth sinusoidal profile: peak velocity = π/2 * avg velocity
    # Peak velocity = travel * π / (2 * total_time), so:
    # total_time = travel * π / (2 * servo_speed_dps) to stay within servo limit
    total_time = travel_deg * math.pi / (2.0 * spec.servo_speed_dps)

    points: List[TrajectoryPoint] = []
    t = 0.0
    while t <= total_time:
        # Normalised progress [0, 1] using sinusoidal ease-in-out
        s = t / total_time
        angle_frac = 0.5 * (1.0 - math.cos(math.pi * s))
        angle_deg = spec.closed_angle_deg + travel_deg * angle_frac

        # Angular velocity (derivative of angle w.r.t. time)
        vel_dps = (
            travel_deg * math.pi / (2.0 * total_time) * math.sin(math.pi * s)
        )

        points.append(
            TrajectoryPoint(
                time_s=round(t, 6),
                angle_deg=round(angle_deg, 6),
                angular_velocity_dps=round(vel_dps, 6),
            )
        )
        t += time_step_s

    # Ensure final point is exactly at max open
    if not points or points[-1].angle_deg != spec.max_open_angle_deg:
        points.append(
            TrajectoryPoint(
                time_s=round(total_time, 6),
                angle_deg=spec.max_open_angle_deg,
                angular_velocity_dps=0.0,
            )
        )

    return points


# ── Safety pre-checks ────────────────────────────────────────────────


def run_safety_checks(spec: ClawSpec) -> List[SafetyCheck]:
    """Run pre-open safety validations on the claw specification."""
    checks: List[SafetyCheck] = []

    # 1. Servo torque must be positive
    checks.append(
        SafetyCheck(
            name="servo_torque_positive",
            passed=spec.servo_torque_nm > 0.0,
            detail=f"servo_torque_nm={spec.servo_torque_nm}",
        )
    )

    # 2. Open angle must exceed closed angle
    checks.append(
        SafetyCheck(
            name="open_exceeds_closed",
            passed=spec.max_open_angle_deg > spec.closed_angle_deg,
            detail=(
                f"max_open={spec.max_open_angle_deg} "
                f"closed={spec.closed_angle_deg}"
            ),
        )
    )

    # 3. Finger count must be at least 2 for a stable grip
    checks.append(
        SafetyCheck(
            name="min_finger_count",
            passed=spec.finger_count >= 2,
            detail=f"finger_count={spec.finger_count}",
        )
    )

    # 4. Mechanism mass within competition budget (≤ 2 kg)
    checks.append(
        SafetyCheck(
            name="mass_budget",
            passed=spec.mass_kg <= 2.0,
            detail=f"mass_kg={spec.mass_kg}",
        )
    )

    # 5. Grip force must be positive
    checks.append(
        SafetyCheck(
            name="grip_force_positive",
            passed=spec.grip_force_n > 0.0,
            detail=f"grip_force_n={spec.grip_force_n}",
        )
    )

    return checks


# ── Energy estimate ──────────────────────────────────────────────────


def estimate_energy_j(spec: ClawSpec, total_time_s: float) -> float:
    """Rough energy estimate for the claw opening manoeuvre.

    Uses ``E ≈ τ · θ`` (torque × angular displacement in radians) as
    a first-order approximation of the mechanical work performed.
    """
    travel_rad = math.radians(spec.max_open_angle_deg - spec.closed_angle_deg)
    return spec.servo_torque_nm * abs(travel_rad)


# ── Open-claw agent orchestrator ─────────────────────────────────────


def run_open_claw_agent(
    spec: ClawSpec | None = None,
    time_step_s: float = 0.01,
    memory_store: Optional[MemoryStore] = None,
) -> OpenClawResult:
    """Run the full open-claw agent pipeline.

    Steps
    -----
    1. Validate claw specification via safety pre-checks.
    2. Compute smooth opening trajectory.
    3. Estimate energy consumption.
    4. Log to memory store if provided.

    Parameters
    ----------
    spec:
        Claw parameters.  Defaults to competition-class gripper.
    time_step_s:
        Trajectory sampling interval in seconds.
    memory_store:
        Optional shared :class:`MemoryStore` for event logging.
    """
    spec = spec or ClawSpec()

    # Step 1 — safety checks
    safety_checks = run_safety_checks(spec)
    all_passed = all(c.passed for c in safety_checks)

    # Step 2 — trajectory
    trajectory = compute_opening_trajectory(spec, time_step_s)
    total_time = trajectory[-1].time_s if trajectory else 0.0
    peak_vel = max((p.angular_velocity_dps for p in trajectory), default=0.0)

    # Step 3 — energy
    energy_j = estimate_energy_j(spec, total_time)

    # Step 4 — memory logging
    if memory_store is not None:
        memory_store.log_event(
            "open_claw_agent",
            "Executed open-claw sequence",
            {
                "finger_count": spec.finger_count,
                "total_time_s": round(total_time, 4),
                "all_checks_passed": all_passed,
                "energy_estimate_j": round(energy_j, 4),
            },
        )

    return OpenClawResult(
        spec=spec,
        trajectory=trajectory,
        safety_checks=safety_checks,
        all_checks_passed=all_passed,
        total_time_s=total_time,
        peak_angular_velocity_dps=peak_vel,
        energy_estimate_j=energy_j,
    )
