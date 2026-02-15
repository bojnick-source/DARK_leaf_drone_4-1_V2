"""Gimbal control systems — mechanical and electronic.

Models 2-axis and 3-axis gimbals with PID-based stabilization,
servo motor dynamics, and electronic image stabilization (EIS).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Tuple

# ---------------------------------------------------------------------------
# Axis / servo models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ServoMotor:
    """Simple DC servo model with torque constant and back-EMF."""

    name: str
    torque_constant_nm_per_a: float
    back_emf_constant_v_s_per_rad: float
    resistance_ohm: float
    inductance_h: float = 0.0
    max_current_a: float = 10.0

    def torque(self, current_a: float) -> float:
        clamped = max(-self.max_current_a, min(self.max_current_a, current_a))
        return self.torque_constant_nm_per_a * clamped

    def back_emf_v(self, omega_rad_s: float) -> float:
        return self.back_emf_constant_v_s_per_rad * omega_rad_s

    def steady_state_current(self, voltage_v: float, omega_rad_s: float) -> float:
        if self.resistance_ohm <= 0.0:
            raise ValueError(f"Invalid resistance for servo {self.name}")
        return (voltage_v - self.back_emf_v(omega_rad_s)) / self.resistance_ohm


@dataclass(frozen=True)
class GimbalAxis:
    """Single gimbal rotation axis."""

    name: str
    inertia_kg_m2: float
    damping_nm_s_per_rad: float = 0.001
    angle_min_deg: float = -180.0
    angle_max_deg: float = 180.0
    servo: ServoMotor | None = None

    def torque_net(
        self,
        applied_torque_nm: float,
        omega_rad_s: float,
    ) -> float:
        return applied_torque_nm - self.damping_nm_s_per_rad * omega_rad_s

    def clamp_angle_deg(self, angle_deg: float) -> float:
        return max(self.angle_min_deg, min(self.angle_max_deg, angle_deg))


# ---------------------------------------------------------------------------
# PID controller (gimbal-specific, supports rate-mode)
# ---------------------------------------------------------------------------


@dataclass
class GimbalPIDController:
    """PID controller with derivative-on-measurement and output limits."""

    kp: float
    ki: float = 0.0
    kd: float = 0.0
    output_min: float = -100.0
    output_max: float = 100.0
    _integral: float = field(default=0.0, init=False, repr=False)
    _prev_measurement: float = field(default=0.0, init=False, repr=False)
    _first_call: bool = field(default=True, init=False, repr=False)

    def reset(self) -> None:
        self._integral = 0.0
        self._prev_measurement = 0.0
        self._first_call = True

    def update(self, setpoint: float, measurement: float, dt_s: float) -> float:
        if dt_s <= 0.0:
            raise ValueError("dt_s must be > 0")
        error = setpoint - measurement
        self._integral += error * dt_s
        if self._first_call:
            derivative = 0.0
            self._first_call = False
        else:
            derivative = -(measurement - self._prev_measurement) / dt_s
        self._prev_measurement = measurement
        output = self.kp * error + self.ki * self._integral + self.kd * derivative
        clamped = max(self.output_min, min(self.output_max, output))
        if clamped != output:
            self._integral -= error * dt_s
        return clamped


# ---------------------------------------------------------------------------
# Gimbal assemblies
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TwoAxisGimbal:
    """2-axis (pitch/yaw) gimbal assembly."""

    name: str
    pitch_axis: GimbalAxis
    yaw_axis: GimbalAxis

    def axes(self) -> Tuple[GimbalAxis, GimbalAxis]:
        return (self.pitch_axis, self.yaw_axis)


@dataclass(frozen=True)
class ThreeAxisGimbal:
    """3-axis (pitch/roll/yaw) gimbal assembly."""

    name: str
    pitch_axis: GimbalAxis
    roll_axis: GimbalAxis
    yaw_axis: GimbalAxis

    def axes(self) -> Tuple[GimbalAxis, GimbalAxis, GimbalAxis]:
        return (self.pitch_axis, self.roll_axis, self.yaw_axis)


# ---------------------------------------------------------------------------
# Electronic image stabilization (EIS)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EISConfig:
    """Electronic image stabilization parameters."""

    sensor_width_px: int
    sensor_height_px: int
    stabilization_margin_px: int = 50
    filter_alpha: float = 0.85

    def effective_resolution(self) -> Tuple[int, int]:
        margin2 = 2 * self.stabilization_margin_px
        return (
            max(1, self.sensor_width_px - margin2),
            max(1, self.sensor_height_px - margin2),
        )

    def crop_fraction(self) -> float:
        eff_w, eff_h = self.effective_resolution()
        return (eff_w * eff_h) / max(
            1, self.sensor_width_px * self.sensor_height_px
        )


@dataclass
class EISFilter:
    """Low-pass smoothing filter for electronic stabilization."""

    alpha: float = 0.85
    _prev_x: float = field(default=0.0, init=False, repr=False)
    _prev_y: float = field(default=0.0, init=False, repr=False)

    def filter(self, raw_x: float, raw_y: float) -> Tuple[float, float]:
        self._prev_x = self.alpha * self._prev_x + (1.0 - self.alpha) * raw_x
        self._prev_y = self.alpha * self._prev_y + (1.0 - self.alpha) * raw_y
        return (self._prev_x, self._prev_y)


# ---------------------------------------------------------------------------
# Gimbal simulation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GimbalAxisState:
    """Time-series state of a single gimbal axis."""

    times_s: List[float]
    angles_deg: List[float]
    rates_deg_s: List[float]
    torques_nm: List[float]


@dataclass(frozen=True)
class GimbalSimResult:
    """Result of a gimbal stabilization simulation."""

    axis_states: dict[str, GimbalAxisState]


def simulate_gimbal_axis(
    axis: GimbalAxis,
    controller: GimbalPIDController,
    target_angle_deg: float,
    disturbance_torque_nm: float,
    t_stop_s: float,
    dt_s: float,
) -> GimbalAxisState:
    """Simulate a single gimbal axis under PID control.

    Rotational dynamics: I * d(omega)/dt = torque_net + disturbance
    """
    if axis.inertia_kg_m2 <= 0.0:
        raise ValueError(f"inertia must be > 0 for axis {axis.name}")
    if dt_s <= 0.0 or t_stop_s <= 0.0:
        raise ValueError("dt_s and t_stop_s must be > 0")

    controller.reset()
    n_steps = int(t_stop_s / dt_s)
    times: List[float] = []
    angles: List[float] = []
    rates: List[float] = []
    torques: List[float] = []

    angle_deg = 0.0
    omega_deg_s = 0.0

    for i in range(n_steps + 1):
        t = i * dt_s
        control_output = controller.update(target_angle_deg, angle_deg, dt_s) if i > 0 else 0.0

        if axis.servo is not None:
            applied_torque = axis.servo.torque(control_output)
        else:
            applied_torque = control_output

        omega_rad_s = omega_deg_s * math.pi / 180.0
        net_torque = axis.torque_net(applied_torque, omega_rad_s) + disturbance_torque_nm

        alpha_rad = net_torque / axis.inertia_kg_m2
        alpha_deg = alpha_rad * 180.0 / math.pi
        omega_deg_s += alpha_deg * dt_s
        angle_deg += omega_deg_s * dt_s
        angle_deg = axis.clamp_angle_deg(angle_deg)

        times.append(t)
        angles.append(angle_deg)
        rates.append(omega_deg_s)
        torques.append(applied_torque)

    return GimbalAxisState(
        times_s=times,
        angles_deg=angles,
        rates_deg_s=rates,
        torques_nm=torques,
    )


def simulate_two_axis_gimbal(
    gimbal: TwoAxisGimbal,
    pitch_controller: GimbalPIDController,
    yaw_controller: GimbalPIDController,
    pitch_target_deg: float,
    yaw_target_deg: float,
    disturbance_torque_nm: float,
    t_stop_s: float,
    dt_s: float,
) -> GimbalSimResult:
    """Simulate a 2-axis gimbal with independent PID loops."""
    pitch_state = simulate_gimbal_axis(
        gimbal.pitch_axis, pitch_controller, pitch_target_deg,
        disturbance_torque_nm, t_stop_s, dt_s,
    )
    yaw_state = simulate_gimbal_axis(
        gimbal.yaw_axis, yaw_controller, yaw_target_deg,
        disturbance_torque_nm, t_stop_s, dt_s,
    )
    return GimbalSimResult(axis_states={"pitch": pitch_state, "yaw": yaw_state})
