"""Drivetrain and proportional control systems for drone propulsion.

Covers linear and non-linear gear trains, chain drives, belt drives,
and PID-based proportional control loops for drive regulation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Tuple

# ---------------------------------------------------------------------------
# Gear / chain / belt elements
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GearStage:
    """Single gear stage with teeth counts and efficiency."""

    name: str
    teeth_input: int
    teeth_output: int
    efficiency: float = 0.98

    def ratio(self) -> float:
        if self.teeth_input <= 0 or self.teeth_output <= 0:
            raise ValueError(f"Invalid teeth counts for {self.name}")
        return self.teeth_output / self.teeth_input

    def output_torque(self, input_torque_nm: float) -> float:
        return input_torque_nm * self.ratio() * self.efficiency

    def output_speed(self, input_speed_rpm: float) -> float:
        return input_speed_rpm / self.ratio()


@dataclass(frozen=True)
class ChainDrive:
    """Roller-chain drive with sprocket teeth."""

    name: str
    sprocket_input_teeth: int
    sprocket_output_teeth: int
    chain_pitch_m: float
    efficiency: float = 0.97

    def ratio(self) -> float:
        if self.sprocket_input_teeth <= 0 or self.sprocket_output_teeth <= 0:
            raise ValueError(f"Invalid sprocket teeth for {self.name}")
        return self.sprocket_output_teeth / self.sprocket_input_teeth

    def chain_speed_m_per_s(self, input_speed_rpm: float) -> float:
        return (
            self.sprocket_input_teeth
            * self.chain_pitch_m
            * input_speed_rpm
            / 60.0
        )

    def output_torque(self, input_torque_nm: float) -> float:
        return input_torque_nm * self.ratio() * self.efficiency

    def output_speed(self, input_speed_rpm: float) -> float:
        return input_speed_rpm / self.ratio()


@dataclass(frozen=True)
class BeltDrive:
    """Belt drive with pulley diameters."""

    name: str
    pulley_input_diameter_m: float
    pulley_output_diameter_m: float
    efficiency: float = 0.96

    def ratio(self) -> float:
        if self.pulley_input_diameter_m <= 0.0 or self.pulley_output_diameter_m <= 0.0:
            raise ValueError(f"Invalid pulley diameters for {self.name}")
        return self.pulley_output_diameter_m / self.pulley_input_diameter_m

    def output_torque(self, input_torque_nm: float) -> float:
        return input_torque_nm * self.ratio() * self.efficiency

    def output_speed(self, input_speed_rpm: float) -> float:
        return input_speed_rpm / self.ratio()


# ---------------------------------------------------------------------------
# Non-linear friction / backlash helpers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NonLinearFriction:
    """Stribeck friction model: coulomb + viscous + stiction."""

    coulomb_torque_nm: float
    viscous_coeff_nm_s: float
    stiction_torque_nm: float
    stribeck_speed_rpm: float = 10.0

    def torque_loss(self, speed_rpm: float) -> float:
        sign = 1.0 if speed_rpm >= 0.0 else -1.0
        abs_speed = abs(speed_rpm)
        stribeck = self.stiction_torque_nm * math.exp(
            -abs_speed / max(self.stribeck_speed_rpm, 1e-9)
        )
        return sign * (
            self.coulomb_torque_nm + stribeck + self.viscous_coeff_nm_s * abs_speed
        )


@dataclass(frozen=True)
class Backlash:
    """Dead-zone backlash model."""

    deadband_rad: float

    def effective_angle(self, command_rad: float) -> float:
        half = self.deadband_rad / 2.0
        if command_rad > half:
            return command_rad - half
        if command_rad < -half:
            return command_rad + half
        return 0.0


# ---------------------------------------------------------------------------
# Linear drivetrain
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LinearDrivetrain:
    """Multi-stage drivetrain composed of gear/chain/belt stages (linear model)."""

    name: str
    stages: Tuple[GearStage | ChainDrive | BeltDrive, ...]

    def total_ratio(self) -> float:
        ratio = 1.0
        for stage in self.stages:
            ratio *= stage.ratio()
        return ratio

    def total_efficiency(self) -> float:
        eff = 1.0
        for stage in self.stages:
            eff *= stage.efficiency
        return eff

    def output_torque(self, input_torque_nm: float) -> float:
        torque = input_torque_nm
        for stage in self.stages:
            torque = stage.output_torque(torque)
        return torque

    def output_speed(self, input_speed_rpm: float) -> float:
        speed = input_speed_rpm
        for stage in self.stages:
            speed = stage.output_speed(speed)
        return speed


# ---------------------------------------------------------------------------
# Non-linear drivetrain
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NonLinearDrivetrain:
    """Drivetrain with non-linear friction and backlash effects."""

    name: str
    stages: Tuple[GearStage | ChainDrive | BeltDrive, ...]
    friction: NonLinearFriction | None = None
    backlash: Backlash | None = None

    def total_ratio(self) -> float:
        ratio = 1.0
        for stage in self.stages:
            ratio *= stage.ratio()
        return ratio

    def total_efficiency(self) -> float:
        eff = 1.0
        for stage in self.stages:
            eff *= stage.efficiency
        return eff

    def output_torque(self, input_torque_nm: float, speed_rpm: float) -> float:
        torque = input_torque_nm
        for stage in self.stages:
            torque = stage.output_torque(torque)
        if self.friction is not None:
            torque -= self.friction.torque_loss(speed_rpm)
        return torque

    def output_speed(self, input_speed_rpm: float) -> float:
        speed = input_speed_rpm
        for stage in self.stages:
            speed = stage.output_speed(speed)
        return speed

    def effective_output_angle(self, command_rad: float) -> float:
        if self.backlash is not None:
            return self.backlash.effective_angle(command_rad)
        return command_rad


# ---------------------------------------------------------------------------
# Proportional / PID control
# ---------------------------------------------------------------------------


@dataclass
class PIDController:
    """Discrete PID controller with anti-windup clamping."""

    kp: float
    ki: float = 0.0
    kd: float = 0.0
    output_min: float = -1e6
    output_max: float = 1e6
    _integral: float = field(default=0.0, init=False, repr=False)
    _prev_error: float = field(default=0.0, init=False, repr=False)
    _first_call: bool = field(default=True, init=False, repr=False)

    def reset(self) -> None:
        self._integral = 0.0
        self._prev_error = 0.0
        self._first_call = True

    def update(self, error: float, dt_s: float) -> float:
        if dt_s <= 0.0:
            raise ValueError("dt_s must be > 0")
        # Proportional
        p_term = self.kp * error
        # Integral with anti-windup
        self._integral += error * dt_s
        i_term = self.ki * self._integral
        # Derivative (skip on first call)
        if self._first_call:
            d_term = 0.0
            self._first_call = False
        else:
            d_term = self.kd * (error - self._prev_error) / dt_s
        self._prev_error = error
        output = p_term + i_term + d_term
        # Clamp output and anti-windup
        clamped = max(self.output_min, min(self.output_max, output))
        if clamped != output:
            self._integral -= error * dt_s  # undo integral accumulation
        return clamped


# ---------------------------------------------------------------------------
# Drivetrain simulation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DrivetrainSimResult:
    """Result of a drivetrain time-domain simulation step."""

    times_s: List[float]
    input_speeds_rpm: List[float]
    output_speeds_rpm: List[float]
    output_torques_nm: List[float]
    control_efforts: List[float]


def simulate_drivetrain(
    drivetrain: LinearDrivetrain | NonLinearDrivetrain,
    controller: PIDController,
    target_speed_rpm: float,
    load_torque_nm: float,
    inertia_kg_m2: float,
    t_stop_s: float,
    dt_s: float,
) -> DrivetrainSimResult:
    """Simulate closed-loop drivetrain speed control.

    Uses a simple rotational dynamics model:
        inertia * d(omega)/dt = applied_torque - load_torque
    where the controller modulates input torque to track target speed.
    """
    if inertia_kg_m2 <= 0.0:
        raise ValueError("inertia_kg_m2 must be > 0")
    if dt_s <= 0.0 or t_stop_s <= 0.0:
        raise ValueError("dt_s and t_stop_s must be > 0")

    controller.reset()
    n_steps = int(t_stop_s / dt_s)
    times: List[float] = []
    in_speeds: List[float] = []
    out_speeds: List[float] = []
    out_torques: List[float] = []
    efforts: List[float] = []

    current_speed_rpm = 0.0
    for i in range(n_steps + 1):
        t = i * dt_s
        output_speed = drivetrain.output_speed(current_speed_rpm)
        error = target_speed_rpm - output_speed
        effort = controller.update(error, dt_s) if i > 0 else 0.0
        input_torque = effort

        if isinstance(drivetrain, NonLinearDrivetrain):
            out_torque = drivetrain.output_torque(input_torque, current_speed_rpm)
        else:
            out_torque = drivetrain.output_torque(input_torque)

        net_torque = out_torque - load_torque_nm
        # omega in rad/s, speed in RPM
        omega = current_speed_rpm * 2.0 * math.pi / 60.0
        alpha = net_torque / inertia_kg_m2
        omega += alpha * dt_s
        current_speed_rpm = omega * 60.0 / (2.0 * math.pi)

        times.append(t)
        in_speeds.append(current_speed_rpm)
        out_speeds.append(drivetrain.output_speed(current_speed_rpm))
        out_torques.append(out_torque)
        efforts.append(effort)

    return DrivetrainSimResult(
        times_s=times,
        input_speeds_rpm=in_speeds,
        output_speeds_rpm=out_speeds,
        output_torques_nm=out_torques,
        control_efforts=efforts,
    )
