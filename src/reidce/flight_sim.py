from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional, Tuple


@dataclass(frozen=True)
class WindModel:
    """Constant wind vector in the world frame (m/s).

    ``gust_intensity`` adds a random perturbation to each component on every
    evaluation, modelling turbulence as white noise scaled by this value.
    """

    wx_m_s: float = 0.0
    wy_m_s: float = 0.0
    wz_m_s: float = 0.0
    gust_intensity: float = 0.0

    def sample(self) -> tuple[float, float, float]:
        """Return an instantaneous wind vector including gust."""
        g = self.gust_intensity
        return (
            self.wx_m_s + random.gauss(0.0, g) if g > 0 else self.wx_m_s,
            self.wy_m_s + random.gauss(0.0, g) if g > 0 else self.wy_m_s,
            self.wz_m_s + random.gauss(0.0, g) if g > 0 else self.wz_m_s,
        )

    @property
    def steady_speed_m_s(self) -> float:
        """Magnitude of the steady-state (non-gust) wind."""
        return math.sqrt(self.wx_m_s**2 + self.wy_m_s**2 + self.wz_m_s**2)

    @staticmethod
    def vector_speed(vec: tuple[float, float, float]) -> float:
        """Magnitude of a 3-component wind vector sample."""
        return math.sqrt(vec[0] ** 2 + vec[1] ** 2 + vec[2] ** 2)


@dataclass(frozen=True)
class SensorNoise:
    """Gaussian noise standard deviations applied to sensor readings."""

    altitude_m_std: float = 0.0
    speed_m_s_std: float = 0.0
    heading_rad_std: float = 0.0


@dataclass(frozen=True)
class Atmosphere:
    rho_kg_m3: float = 1.225
    gravity_m_s2: float = 9.80665
    wind: WindModel = field(default_factory=WindModel)
    sensor_noise: SensorNoise = field(default_factory=SensorNoise)
    use_isa_density: bool = False

    def density_at(self, altitude_m: float) -> float:
        """Return air density at *altitude_m* using ISA troposphere model.

        If ``use_isa_density`` is *False* the constant ``rho_kg_m3`` is
        returned regardless of altitude.
        """
        if not self.use_isa_density:
            return self.rho_kg_m3
        # ISA troposphere: T = T0 - L*h, rho = rho0 * (T/T0)^(g/(L*R)-1)
        t0 = 288.15  # sea-level temperature K
        lapse = 0.0065  # K/m
        r_air = 287.058  # J/(kg·K)
        t = max(t0 - lapse * altitude_m, 1.0)
        exponent = self.gravity_m_s2 / (lapse * r_air) - 1.0
        return self.rho_kg_m3 * (t / t0) ** exponent


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
    energy_used_j: List[float]
    battery_pct: List[float]
    temperature_c: List[float]
    wind_speed_m_s: List[float] = field(default_factory=list)


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


@dataclass(frozen=True)
class AutopilotConfig:
    altitude_kp: float = 0.6
    altitude_ki: float = 0.05
    altitude_kd: float = 0.12
    altitude_limit: float = 0.35
    speed_kp: float = 0.8
    speed_ki: float = 0.02
    speed_kd: float = 0.08
    speed_limit: float = 0.6
    heading_kp: float = 1.2
    heading_ki: float = 0.01
    heading_kd: float = 0.15
    heading_limit: float = 0.6
    roll_kp: float = 2.0
    roll_ki: float = 0.02
    roll_kd: float = 0.2
    roll_limit: float = 0.6
    throttle_trim: float = 0.5


class AutopilotChannel:
    def __init__(self, config: Optional[AutopilotConfig] = None) -> None:
        config = config or AutopilotConfig()
        self.config = config
        self.altitude_pid = PID(
            config.altitude_kp, config.altitude_ki, config.altitude_kd,
            limit=config.altitude_limit,
        )
        self.speed_pid = PID(
            config.speed_kp, config.speed_ki, config.speed_kd,
            limit=config.speed_limit,
        )
        self.heading_pid = PID(
            config.heading_kp, config.heading_ki, config.heading_kd,
            limit=config.heading_limit,
        )
        self.roll_pid = PID(
            config.roll_kp, config.roll_ki, config.roll_kd,
            limit=config.roll_limit,
        )

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
        throttle = self.config.throttle_trim + self.speed_pid.step(speed_error, dt)
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
    params: Optional[VehicleParams] = None,
    atmosphere: Optional[Atmosphere] = None,
    controller: Optional[TripleRedundantController] = None,
    guidance_profile: Optional[Callable[[float, GuidanceTarget], GuidanceTarget]] = None,
    battery_capacity_j: float = 180000.0,
    ambient_temp_c: float = 25.0,
) -> SimulationResult:
    if duration_s <= 0.0 or dt_s <= 0.0:
        raise ValueError("duration_s and dt_s must be > 0")

    params = params or VehicleParams()
    atmosphere = atmosphere or Atmosphere()
    controller = controller or TripleRedundantController()
    controller.reset()

    steps = int(duration_s / dt_s)
    state = _clone_state(initial_state)
    time: List[float] = []
    states: List[VehicleState] = []
    commands: List[ControlCommand] = []
    energy_used: List[float] = []
    battery_pct: List[float] = []
    temperature_c: List[float] = []
    wind_speed_log: List[float] = []

    cumulative_energy_j = 0.0
    motor_temp_c = ambient_temp_c

    for step in range(steps + 1):
        t = step * dt_s
        active_target = guidance_profile(t, target) if guidance_profile else target
        sensed = _sense(state, atmosphere.sensor_noise)
        cmd = controller.compute(active_target, sensed, dt_s)
        wind_vec = atmosphere.wind.sample()
        state = _integrate(state, cmd, dt_s, params, atmosphere, wind_vec)

        # Power model: motor efficiency ~30%, plus 15 W idle draw
        power_w = cmd.throttle * params.max_thrust_n * sensed.speed_m_s * 0.3 + 15.0
        cumulative_energy_j += power_w * dt_s
        remaining_pct = max(0.0, 100.0 * (1.0 - cumulative_energy_j / battery_capacity_j))
        # Thermal model: 0.08 °C/s heating per unit throttle, 0.005 dissipation coeff
        heating = cmd.throttle * 0.08 * dt_s
        cooling = (motor_temp_c - ambient_temp_c) * 0.005 * dt_s
        motor_temp_c += heating - cooling

        time.append(t)
        states.append(_clone_state(state))
        commands.append(cmd)
        energy_used.append(cumulative_energy_j)
        battery_pct.append(remaining_pct)
        temperature_c.append(motor_temp_c)
        wind_speed_log.append(WindModel.vector_speed(wind_vec))

    return SimulationResult(
        time_s=time,
        state=states,
        commands=commands,
        energy_used_j=energy_used,
        battery_pct=battery_pct,
        temperature_c=temperature_c,
        wind_speed_m_s=wind_speed_log,
    )


def _sense(state: VehicleState, noise: Optional[SensorNoise] = None) -> SensorSample:
    speed = math.sqrt(state.vx_m_s**2 + state.vy_m_s**2 + state.vz_m_s**2)
    if noise and (noise.altitude_m_std > 0 or noise.speed_m_s_std > 0 or noise.heading_rad_std > 0):
        return SensorSample(
            altitude_m=state.z_m + random.gauss(0.0, noise.altitude_m_std),
            speed_m_s=max(0.0, speed + random.gauss(0.0, noise.speed_m_s_std)),
            heading_rad=state.yaw_rad + random.gauss(0.0, noise.heading_rad_std),
            roll_rad=state.roll_rad,
            pitch_rad=state.pitch_rad,
            yaw_rad=state.yaw_rad,
        )
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
    wind_sample: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> VehicleState:
    rho = atmosphere.density_at(state.z_m)

    def deriv(s: VehicleState) -> VehicleState:
        # Airspeed = ground speed − wind
        air_vx = s.vx_m_s - wind_sample[0]
        air_vy = s.vy_m_s - wind_sample[1]
        air_vz = s.vz_m_s - wind_sample[2]
        airspeed = math.sqrt(air_vx**2 + air_vy**2 + air_vz**2) + 1e-6
        lift = _lift_force(airspeed, s.pitch_rad, params, rho)
        drag = _drag_force(airspeed, s.pitch_rad, params, rho)
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
        vx_m_s=state.vx_m_s
        + dt / 6.0 * (k1.vx_m_s + 2 * k2.vx_m_s + 2 * k3.vx_m_s + k4.vx_m_s),
        vy_m_s=state.vy_m_s
        + dt / 6.0 * (k1.vy_m_s + 2 * k2.vy_m_s + 2 * k3.vy_m_s + k4.vy_m_s),
        vz_m_s=state.vz_m_s
        + dt / 6.0 * (k1.vz_m_s + 2 * k2.vz_m_s + 2 * k3.vz_m_s + k4.vz_m_s),
        roll_rad=state.roll_rad
        + dt / 6.0 * (k1.roll_rad + 2 * k2.roll_rad + 2 * k3.roll_rad + k4.roll_rad),
        pitch_rad=state.pitch_rad
        + dt / 6.0 * (k1.pitch_rad + 2 * k2.pitch_rad + 2 * k3.pitch_rad + k4.pitch_rad),
        yaw_rad=_wrap_angle(state.yaw_rad + dt * cmd.yaw_rate_cmd_rad_s),
    )
    return _limit_state(next_state, params)


def _attitude_rate(current: float, target: float, dt: float, params: VehicleParams) -> float:
    limited = max(-params.max_tilt_rad, min(params.max_tilt_rad, target))
    return (limited - current) / max(dt, 1e-6)


def _lift_force(speed: float, pitch: float, params: VehicleParams, rho: float) -> float:
    cl = params.cl_alpha_per_rad * pitch
    return 0.5 * rho * speed**2 * params.wing_area_m2 * cl


def _drag_force(speed: float, pitch: float, params: VehicleParams, rho: float) -> float:
    alpha = pitch
    cd = params.cd0 + params.cd_alpha2 * alpha * alpha
    return 0.5 * rho * speed**2 * params.wing_area_m2 * cd


def _wrap_angle(angle: float) -> float:
    return math.remainder(angle, 2.0 * math.pi)


def _median(values: Iterable[float]) -> float:
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    mid = n // 2
    if n % 2 == 0:
        return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0
    return sorted_vals[mid]


def _clone_state(state: VehicleState) -> VehicleState:
    return VehicleState(**state.__dict__)


def _limit_state(state: VehicleState, params: VehicleParams) -> VehicleState:
    vmax = params.max_speed_m_s
    z = max(0.0, state.z_m)  # ground collision clamp
    vz = state.vz_m_s
    if z == 0.0 and vz < 0.0:
        vz = 0.0
    return VehicleState(
        x_m=state.x_m,
        y_m=state.y_m,
        z_m=z,
        vx_m_s=max(-vmax, min(vmax, state.vx_m_s)),
        vy_m_s=max(-vmax, min(vmax, state.vy_m_s)),
        vz_m_s=max(-vmax, min(vmax, vz)),
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


# ── BEMT-enhanced rotor model ────────────────────────────────────────────


@dataclass(frozen=True)
class RotorParams:
    """Parameters for a BEMT-based rotor model.

    Provides a higher-fidelity thrust and power model compared to
    the simple ``max_thrust_n`` scaling in ``VehicleParams``.
    """

    n_rotors: int = 4
    rotor_radius_m: float = 0.12
    n_blades: int = 2
    root_chord_m: float = 0.025
    tip_chord_m: float = 0.015
    root_twist_rad: float = 0.35
    tip_twist_rad: float = 0.05
    hub_radius_m: float = 0.015
    base_rpm: float = 8000.0


def bemt_rotor_thrust(
    throttle: float,
    v_climb_m_s: float,
    rotor: RotorParams,
    rho_kg_m3: float = 1.225,
) -> Dict[str, float]:
    """Compute rotor thrust and power using BEMT for the given throttle.

    Throttle (0–1) scales the RPM linearly from idle (20 % base) to
    full base_rpm.  Returns a dict with ``thrust_n``, ``power_w``,
    ``torque_nm``, ``rpm``, and ``fm``.
    """
    from reidce.bemt import BEMTCondition, RotorGeometry, solve_bemt

    clamped = max(0.0, min(1.0, throttle))
    rpm = rotor.base_rpm * (0.20 + 0.80 * clamped)

    geom = RotorGeometry(
        n_blades=rotor.n_blades,
        radius_m=rotor.rotor_radius_m,
        hub_radius_m=rotor.hub_radius_m,
        root_chord_m=rotor.root_chord_m,
        tip_chord_m=rotor.tip_chord_m,
        root_twist_rad=rotor.root_twist_rad,
        tip_twist_rad=rotor.tip_twist_rad,
    )
    cond = BEMTCondition(rpm=rpm, v_climb_m_s=v_climb_m_s, rho_kg_m3=rho_kg_m3)
    result = solve_bemt(geom, cond, n_elements=12)

    n = rotor.n_rotors
    return {
        "thrust_n": result.thrust_n * n,
        "power_w": result.power_w * n,
        "torque_nm": result.torque_nm * n,
        "rpm": rpm,
        "fm": result.fm,
    }


def simulate_flight_bemt(
    initial_state: VehicleState,
    target: GuidanceTarget,
    duration_s: float,
    dt_s: float,
    params: Optional[VehicleParams] = None,
    atmosphere: Optional[Atmosphere] = None,
    rotor: Optional[RotorParams] = None,
    controller: Optional[TripleRedundantController] = None,
    guidance_profile: Optional[
        Callable[[float, GuidanceTarget], GuidanceTarget]
    ] = None,
    battery_capacity_j: float = 180000.0,
    ambient_temp_c: float = 25.0,
) -> SimulationResult:
    """Flight simulation using BEMT rotor model for thrust and power.

    Identical interface to ``simulate_flight`` but replaces the simple
    ``throttle × max_thrust`` model with a BEMT-computed thrust at the
    commanded RPM.  This provides physically realistic rotor loading
    that varies with climb rate and air density.
    """
    if duration_s <= 0.0 or dt_s <= 0.0:
        raise ValueError("duration_s and dt_s must be > 0")

    params = params or VehicleParams()
    atmosphere = atmosphere or Atmosphere()
    rotor = rotor or RotorParams()
    controller = controller or TripleRedundantController()
    controller.reset()

    steps = int(duration_s / dt_s)
    state = _clone_state(initial_state)
    time: List[float] = []
    states: List[VehicleState] = []
    commands: List[ControlCommand] = []
    energy_used: List[float] = []
    battery_pct: List[float] = []
    temperature_c: List[float] = []
    wind_speed_log: List[float] = []

    cumulative_energy_j = 0.0
    motor_temp_c = ambient_temp_c

    for step in range(steps + 1):
        t = step * dt_s
        active_target = (
            guidance_profile(t, target) if guidance_profile else target
        )
        sensed = _sense(state, atmosphere.sensor_noise)
        cmd = controller.compute(active_target, sensed, dt_s)
        wind_vec = atmosphere.wind.sample()

        # BEMT-based thrust and power
        rho = atmosphere.density_at(state.z_m)
        rotor_out = bemt_rotor_thrust(
            cmd.throttle, state.vz_m_s, rotor, rho,
        )
        thrust = rotor_out["thrust_n"]
        power_w = rotor_out["power_w"] + 15.0  # idle electronics draw

        # Physics integration with BEMT thrust — use airspeed
        air_vx = state.vx_m_s - wind_vec[0]
        air_vy = state.vy_m_s - wind_vec[1]
        air_vz = state.vz_m_s - wind_vec[2]
        airspeed = math.sqrt(air_vx**2 + air_vy**2 + air_vz**2) + 1e-6
        lift = _lift_force(airspeed, state.pitch_rad, params, rho)
        drag = _drag_force(airspeed, state.pitch_rad, params, rho)

        ax = (
            thrust * math.cos(state.pitch_rad) - drag
        ) / params.mass_kg
        az = (
            lift + thrust * math.sin(state.pitch_rad)
        ) / params.mass_kg - atmosphere.gravity_m_s2
        ax = max(-params.max_accel_m_s2, min(params.max_accel_m_s2, ax))
        az = max(-params.max_accel_m_s2, min(params.max_accel_m_s2, az))

        state.vx_m_s += ax * dt_s
        state.vz_m_s += az * dt_s
        state.x_m += state.vx_m_s * dt_s
        state.z_m += state.vz_m_s * dt_s
        state.yaw_rad = _wrap_angle(
            state.yaw_rad + cmd.yaw_rate_cmd_rad_s * dt_s
        )
        state = _limit_state(state, params)

        cumulative_energy_j += power_w * dt_s
        remaining_pct = max(
            0.0, 100.0 * (1.0 - cumulative_energy_j / battery_capacity_j)
        )
        heating = cmd.throttle * 0.08 * dt_s
        cooling = (motor_temp_c - ambient_temp_c) * 0.005 * dt_s
        motor_temp_c += heating - cooling

        time.append(t)
        states.append(_clone_state(state))
        commands.append(cmd)
        energy_used.append(cumulative_energy_j)
        battery_pct.append(remaining_pct)
        temperature_c.append(motor_temp_c)
        wind_speed_log.append(WindModel.vector_speed(wind_vec))

    return SimulationResult(
        time_s=time,
        state=states,
        commands=commands,
        energy_used_j=energy_used,
        battery_pct=battery_pct,
        temperature_c=temperature_c,
        wind_speed_m_s=wind_speed_log,
    )
