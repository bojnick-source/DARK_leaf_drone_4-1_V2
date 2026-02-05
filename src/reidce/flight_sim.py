from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Callable, Dict, Iterable, List, Optional, Tuple


@dataclass(frozen=True)
class Atmosphere:
    rho_kg_m3: float = 1.225
    gravity_m_s2: float = 9.80665


@dataclass(frozen=True)
class VehicleParams:
    mass_kg: float = 2.4
    wing_area_m2: float = 0.35
    cl_alpha_per_rad: float = 4.8
    cd0: float = 0.04
    cd_alpha2: float = 0.6
    max_thrust_n: float = 45.0
    max_tilt_rad: float = math.radians(30.0)
    max_speed_m_s: float = 60.0
    max_accel_m_s2: float = 30.0


@dataclass
class VehicleState:
    x_m: float = 0.0
    y_m: float = 0.0
    z_m: float = 0.0
    vx_m_s: float = 0.0
    vy_m_s: float = 0.0
    vz_m_s: float = 0.0
    roll_rad: float = 0.0
    pitch_rad: float = 0.0
    yaw_rad: float = 0.0


@dataclass(frozen=True)
class ControlCommand:
    throttle: float
    roll_cmd_rad: float
    pitch_cmd_rad: float
    yaw_rate_cmd_rad_s: float


@dataclass(frozen=True)
class GuidanceTarget:
    altitude_m: float
    speed_m_s: float
    heading_rad: float


@dataclass(frozen=True)
class SensorSample:
    altitude_m: float
    speed_m_s: float
    heading_rad: float
    roll_rad: float
    pitch_rad: float
    yaw_rad: float


@dataclass(frozen=True)
class SimulationResult:
    time_s: List[float]
    state: List[VehicleState]
    commands: List[ControlCommand]


class PID:
    def __init__(self, kp: float, ki: float, kd: float, limit: float) -> None:
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.limit = limit
        self._integral = 0.0
        self._prev_error = 0.0

    def reset(self) -> None:
        self._integral = 0.0
        self._prev_error = 0.0

    def step(self, error: float, dt: float) -> float:
        if dt <= 0.0:
            return 0.0
        self._integral += error * dt
        derivative = (error - self._prev_error) / dt
        self._prev_error = error
        value = self.kp * error + self.ki * self._integral + self.kd * derivative
        return max(-self.limit, min(self.limit, value))


class AutopilotChannel:
    def __init__(self) -> None:
        self.altitude_pid = PID(0.6, 0.05, 0.12, limit=0.35)
        self.speed_pid = PID(0.8, 0.02, 0.08, limit=0.6)
        self.heading_pid = PID(1.2, 0.01, 0.15, limit=0.6)
        self.roll_pid = PID(2.0, 0.02, 0.2, limit=0.6)

    def reset(self) -> None:
        self.altitude_pid.reset()
        self.speed_pid.reset()
        self.heading_pid.reset()
        self.roll_pid.reset()

    def compute(self, target: GuidanceTarget, sensed: SensorSample, dt: float) -> ControlCommand:
        altitude_error = target.altitude_m - sensed.altitude_m
        speed_error = target.speed_m_s - sensed.speed_m_s
        heading_error = _wrap_angle(target.heading_rad - sensed.heading_rad)

        pitch_cmd = self.altitude_pid.step(altitude_error, dt)
        throttle = 0.5 + self.speed_pid.step(speed_error, dt)
        roll_cmd = self.heading_pid.step(heading_error, dt)
        yaw_rate = self.roll_pid.step(roll_cmd - sensed.roll_rad, dt)

        return ControlCommand(
            throttle=max(0.0, min(1.0, throttle)),
            roll_cmd_rad=roll_cmd,
            pitch_cmd_rad=pitch_cmd,
            yaw_rate_cmd_rad_s=yaw_rate,
        )


@dataclass
class TripleRedundantController:
    channels: Tuple[AutopilotChannel, AutopilotChannel, AutopilotChannel] = field(
        default_factory=lambda: (AutopilotChannel(), AutopilotChannel(), AutopilotChannel())
    )
    channel_faults: Tuple[bool, bool, bool] = (False, False, False)

    def reset(self) -> None:
        for channel in self.channels:
            channel.reset()

    def vote(self, commands: List[ControlCommand]) -> ControlCommand:
        throttle = _median([cmd.throttle for cmd in commands])
        roll_cmd = _median([cmd.roll_cmd_rad for cmd in commands])
        pitch_cmd = _median([cmd.pitch_cmd_rad for cmd in commands])
        yaw_rate = _median([cmd.yaw_rate_cmd_rad_s for cmd in commands])
        return ControlCommand(throttle, roll_cmd, pitch_cmd, yaw_rate)

    def compute(self, target: GuidanceTarget, sensed: SensorSample, dt: float) -> ControlCommand:
        cmds: List[ControlCommand] = []
        for idx, channel in enumerate(self.channels):
            if self.channel_faults[idx]:
                continue
            cmds.append(channel.compute(target, sensed, dt))
        if not cmds:
            return ControlCommand(0.3, 0.0, 0.0, 0.0)
        if len(cmds) == 1:
            return cmds[0]
        return self.vote(cmds)


def simulate_flight(
    initial_state: VehicleState,
    target: GuidanceTarget,
    duration_s: float,
    dt_s: float,
    params: VehicleParams = VehicleParams(),
    atmosphere: Atmosphere = Atmosphere(),
    controller: Optional[TripleRedundantController] = None,
    guidance_profile: Optional[Callable[[float, GuidanceTarget], GuidanceTarget]] = None,
) -> SimulationResult:
    if duration_s <= 0.0 or dt_s <= 0.0:
        raise ValueError("duration_s and dt_s must be > 0")

    controller = controller or TripleRedundantController()
    controller.reset()

    steps = int(duration_s / dt_s)
    state = _clone_state(initial_state)
    time: List[float] = []
    states: List[VehicleState] = []
    commands: List[ControlCommand] = []

    for step in range(steps + 1):
        t = step * dt_s
        active_target = guidance_profile(t, target) if guidance_profile else target
        sensed = _sense(state)
        cmd = controller.compute(active_target, sensed, dt_s)
        state = _integrate(state, cmd, dt_s, params, atmosphere)
        time.append(t)
        states.append(_clone_state(state))
        commands.append(cmd)

    return SimulationResult(time_s=time, state=states, commands=commands)


def _sense(state: VehicleState) -> SensorSample:
    speed = math.sqrt(state.vx_m_s**2 + state.vy_m_s**2 + state.vz_m_s**2)
    return SensorSample(
        altitude_m=state.z_m,
        speed_m_s=speed,
        heading_rad=state.yaw_rad,
        roll_rad=state.roll_rad,
        pitch_rad=state.pitch_rad,
        yaw_rad=state.yaw_rad,
    )


def _integrate(
    state: VehicleState,
    cmd: ControlCommand,
    dt: float,
    params: VehicleParams,
    atmosphere: Atmosphere,
) -> VehicleState:
    def deriv(s: VehicleState) -> VehicleState:
        speed = math.sqrt(s.vx_m_s**2 + s.vy_m_s**2 + s.vz_m_s**2) + 1e-6
        lift = _lift_force(speed, s.pitch_rad, params, atmosphere)
        drag = _drag_force(speed, s.pitch_rad, params, atmosphere)
        thrust = cmd.throttle * params.max_thrust_n

        ax = (thrust * math.cos(s.pitch_rad) - drag) / params.mass_kg
        az = (lift + thrust * math.sin(s.pitch_rad)) / params.mass_kg - atmosphere.gravity_m_s2
        ax = max(-params.max_accel_m_s2, min(params.max_accel_m_s2, ax))
        az = max(-params.max_accel_m_s2, min(params.max_accel_m_s2, az))

        return VehicleState(
            x_m=s.vx_m_s,
            y_m=s.vy_m_s,
            z_m=s.vz_m_s,
            vx_m_s=ax,
            vy_m_s=0.0,
            vz_m_s=az,
            roll_rad=_attitude_rate(s.roll_rad, cmd.roll_cmd_rad, dt, params),
            pitch_rad=_attitude_rate(s.pitch_rad, cmd.pitch_cmd_rad, dt, params),
            yaw_rad=cmd.yaw_rate_cmd_rad_s,
        )

    k1 = deriv(state)
    k2 = deriv(_step_state(state, k1, dt * 0.5))
    k3 = deriv(_step_state(state, k2, dt * 0.5))
    k4 = deriv(_step_state(state, k3, dt))

    next_state = VehicleState(
        x_m=state.x_m + dt / 6.0 * (k1.x_m + 2 * k2.x_m + 2 * k3.x_m + k4.x_m),
        y_m=state.y_m + dt / 6.0 * (k1.y_m + 2 * k2.y_m + 2 * k3.y_m + k4.y_m),
        z_m=state.z_m + dt / 6.0 * (k1.z_m + 2 * k2.z_m + 2 * k3.z_m + k4.z_m),
        vx_m_s=state.vx_m_s + dt / 6.0 * (k1.vx_m_s + 2 * k2.vx_m_s + 2 * k3.vx_m_s + k4.vx_m_s),
        vy_m_s=state.vy_m_s + dt / 6.0 * (k1.vy_m_s + 2 * k2.vy_m_s + 2 * k3.vy_m_s + k4.vy_m_s),
        vz_m_s=state.vz_m_s + dt / 6.0 * (k1.vz_m_s + 2 * k2.vz_m_s + 2 * k3.vz_m_s + k4.vz_m_s),
        roll_rad=state.roll_rad + dt / 6.0 * (k1.roll_rad + 2 * k2.roll_rad + 2 * k3.roll_rad + k4.roll_rad),
        pitch_rad=state.pitch_rad + dt / 6.0 * (k1.pitch_rad + 2 * k2.pitch_rad + 2 * k3.pitch_rad + k4.pitch_rad),
        yaw_rad=_wrap_angle(state.yaw_rad + dt * cmd.yaw_rate_cmd_rad_s),
    )
    return _limit_state(next_state, params)


def _attitude_rate(current: float, target: float, dt: float, params: VehicleParams) -> float:
    limited = max(-params.max_tilt_rad, min(params.max_tilt_rad, target))
    return (limited - current) / max(dt, 1e-6)


def _lift_force(speed: float, pitch: float, params: VehicleParams, atmosphere: Atmosphere) -> float:
    cl = params.cl_alpha_per_rad * pitch
    return 0.5 * atmosphere.rho_kg_m3 * speed**2 * params.wing_area_m2 * cl


def _drag_force(speed: float, pitch: float, params: VehicleParams, atmosphere: Atmosphere) -> float:
    alpha = pitch
    cd = params.cd0 + params.cd_alpha2 * alpha * alpha
    return 0.5 * atmosphere.rho_kg_m3 * speed**2 * params.wing_area_m2 * cd


def _wrap_angle(angle: float) -> float:
    while angle > math.pi:
        angle -= 2.0 * math.pi
    while angle < -math.pi:
        angle += 2.0 * math.pi
    return angle


def _median(values: Iterable[float]) -> float:
    sorted_vals = sorted(values)
    mid = len(sorted_vals) // 2
    return sorted_vals[mid]


def _clone_state(state: VehicleState) -> VehicleState:
    return VehicleState(**state.__dict__)


def _limit_state(state: VehicleState, params: VehicleParams) -> VehicleState:
    vmax = params.max_speed_m_s
    return VehicleState(
        x_m=state.x_m,
        y_m=state.y_m,
        z_m=state.z_m,
        vx_m_s=max(-vmax, min(vmax, state.vx_m_s)),
        vy_m_s=max(-vmax, min(vmax, state.vy_m_s)),
        vz_m_s=max(-vmax, min(vmax, state.vz_m_s)),
        roll_rad=state.roll_rad,
        pitch_rad=state.pitch_rad,
        yaw_rad=_wrap_angle(state.yaw_rad),
    )


def _step_state(state: VehicleState, deriv: VehicleState, dt: float) -> VehicleState:
    return VehicleState(
        x_m=state.x_m + deriv.x_m * dt,
        y_m=state.y_m + deriv.y_m * dt,
        z_m=state.z_m + deriv.z_m * dt,
        vx_m_s=state.vx_m_s + deriv.vx_m_s * dt,
        vy_m_s=state.vy_m_s + deriv.vy_m_s * dt,
        vz_m_s=state.vz_m_s + deriv.vz_m_s * dt,
        roll_rad=state.roll_rad + deriv.roll_rad * dt,
        pitch_rad=state.pitch_rad + deriv.pitch_rad * dt,
        yaw_rad=state.yaw_rad + deriv.yaw_rad * dt,
    )
