
from reidce.gimbal import (
    EISConfig,
    EISFilter,
    GimbalAxis,
    GimbalPIDController,
    GimbalSimResult,
    ServoMotor,
    ThreeAxisGimbal,
    TwoAxisGimbal,
    simulate_gimbal_axis,
    simulate_two_axis_gimbal,
)


def test_servo_motor_torque() -> None:
    servo = ServoMotor(
        name="s1",
        torque_constant_nm_per_a=0.05,
        back_emf_constant_v_s_per_rad=0.05,
        resistance_ohm=1.0,
    )
    assert abs(servo.torque(2.0) - 0.1) < 1e-9
    assert servo.back_emf_v(100.0) > 0.0


def test_servo_current_clamp() -> None:
    servo = ServoMotor(
        name="s1",
        torque_constant_nm_per_a=0.05,
        back_emf_constant_v_s_per_rad=0.05,
        resistance_ohm=1.0,
        max_current_a=5.0,
    )
    assert abs(servo.torque(100.0) - servo.torque(5.0)) < 1e-9


def test_gimbal_axis_clamp() -> None:
    axis = GimbalAxis(
        name="pitch",
        inertia_kg_m2=0.001,
        angle_min_deg=-45.0,
        angle_max_deg=45.0,
    )
    assert axis.clamp_angle_deg(90.0) == 45.0
    assert axis.clamp_angle_deg(-90.0) == -45.0


def test_gimbal_axis_damping() -> None:
    axis = GimbalAxis(name="yaw", inertia_kg_m2=0.001, damping_nm_s_per_rad=0.01)
    net = axis.torque_net(1.0, 10.0)  # 10 rad/s
    assert net < 1.0  # damping reduces net torque


def test_gimbal_pid_controller() -> None:
    pid = GimbalPIDController(kp=5.0, ki=0.5, kd=0.1)
    output = pid.update(setpoint=10.0, measurement=0.0, dt_s=0.01)
    assert output > 0.0


def test_two_axis_gimbal_axes() -> None:
    pitch = GimbalAxis(name="pitch", inertia_kg_m2=0.001)
    yaw = GimbalAxis(name="yaw", inertia_kg_m2=0.001)
    gimbal = TwoAxisGimbal(name="g2", pitch_axis=pitch, yaw_axis=yaw)
    assert len(gimbal.axes()) == 2


def test_three_axis_gimbal_axes() -> None:
    pitch = GimbalAxis(name="pitch", inertia_kg_m2=0.001)
    roll = GimbalAxis(name="roll", inertia_kg_m2=0.001)
    yaw = GimbalAxis(name="yaw", inertia_kg_m2=0.001)
    gimbal = ThreeAxisGimbal(name="g3", pitch_axis=pitch, roll_axis=roll, yaw_axis=yaw)
    assert len(gimbal.axes()) == 3


def test_eis_config_crop() -> None:
    eis = EISConfig(sensor_width_px=1920, sensor_height_px=1080, stabilization_margin_px=60)
    eff_w, eff_h = eis.effective_resolution()
    assert eff_w == 1800
    assert eff_h == 960
    assert 0.0 < eis.crop_fraction() < 1.0


def test_eis_filter_smoothing() -> None:
    f = EISFilter(alpha=0.8)
    # Feed a step input
    for _ in range(20):
        x, y = f.filter(10.0, 5.0)
    # After many steps, output should converge to input
    assert abs(x - 10.0) < 0.5
    assert abs(y - 5.0) < 0.5


def test_simulate_gimbal_axis_converges() -> None:
    axis = GimbalAxis(name="pitch", inertia_kg_m2=0.001, damping_nm_s_per_rad=0.01)
    pid = GimbalPIDController(kp=2.0, ki=0.5, kd=0.1)
    state = simulate_gimbal_axis(
        axis=axis,
        controller=pid,
        target_angle_deg=15.0,
        disturbance_torque_nm=0.0,
        t_stop_s=2.0,
        dt_s=0.001,
    )
    assert len(state.times_s) > 0
    # Should have moved towards target
    assert abs(state.angles_deg[-1]) > 0.0


def test_simulate_two_axis_gimbal() -> None:
    pitch = GimbalAxis(name="pitch", inertia_kg_m2=0.001, damping_nm_s_per_rad=0.005)
    yaw = GimbalAxis(name="yaw", inertia_kg_m2=0.001, damping_nm_s_per_rad=0.005)
    gimbal = TwoAxisGimbal(name="g2", pitch_axis=pitch, yaw_axis=yaw)
    pid_p = GimbalPIDController(kp=2.0, ki=0.3, kd=0.05)
    pid_y = GimbalPIDController(kp=2.0, ki=0.3, kd=0.05)
    result = simulate_two_axis_gimbal(
        gimbal=gimbal,
        pitch_controller=pid_p,
        yaw_controller=pid_y,
        pitch_target_deg=10.0,
        yaw_target_deg=-5.0,
        disturbance_torque_nm=0.0,
        t_stop_s=1.0,
        dt_s=0.001,
    )
    assert isinstance(result, GimbalSimResult)
    assert "pitch" in result.axis_states
    assert "yaw" in result.axis_states


def test_gimbal_with_servo_motor() -> None:
    servo = ServoMotor(
        name="s1",
        torque_constant_nm_per_a=0.05,
        back_emf_constant_v_s_per_rad=0.05,
        resistance_ohm=1.0,
    )
    axis = GimbalAxis(
        name="pitch",
        inertia_kg_m2=0.001,
        damping_nm_s_per_rad=0.005,
        servo=servo,
    )
    pid = GimbalPIDController(kp=5.0, ki=1.0, kd=0.2, output_max=10.0, output_min=-10.0)
    state = simulate_gimbal_axis(
        axis=axis,
        controller=pid,
        target_angle_deg=20.0,
        disturbance_torque_nm=0.0,
        t_stop_s=2.0,
        dt_s=0.001,
    )
    assert len(state.angles_deg) > 0
