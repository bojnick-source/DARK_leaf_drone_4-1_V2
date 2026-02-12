from reidce.drivetrain import (
    Backlash,
    BeltDrive,
    ChainDrive,
    DrivetrainSimResult,
    GearStage,
    LinearDrivetrain,
    NonLinearDrivetrain,
    NonLinearFriction,
    PIDController,
    simulate_drivetrain,
)


def test_gear_stage_ratio_and_torque() -> None:
    stage = GearStage(name="g1", teeth_input=20, teeth_output=60)
    assert abs(stage.ratio() - 3.0) < 1e-9
    out = stage.output_torque(1.0)
    assert abs(out - 3.0 * 0.98) < 1e-6


def test_gear_stage_speed_reduction() -> None:
    stage = GearStage(name="g1", teeth_input=20, teeth_output=60)
    assert abs(stage.output_speed(3000.0) - 1000.0) < 1e-6


def test_chain_drive_ratio_and_speed() -> None:
    chain = ChainDrive(
        name="c1",
        sprocket_input_teeth=15,
        sprocket_output_teeth=45,
        chain_pitch_m=0.0127,
    )
    assert abs(chain.ratio() - 3.0) < 1e-9
    assert chain.chain_speed_m_per_s(1000.0) > 0.0


def test_belt_drive_output() -> None:
    belt = BeltDrive(
        name="b1",
        pulley_input_diameter_m=0.05,
        pulley_output_diameter_m=0.15,
    )
    assert abs(belt.ratio() - 3.0) < 1e-9
    assert belt.output_torque(1.0) > 0.0
    assert belt.output_speed(3000.0) < 3000.0


def test_linear_drivetrain_cascade() -> None:
    stages = (
        GearStage(name="g1", teeth_input=20, teeth_output=40),
        GearStage(name="g2", teeth_input=15, teeth_output=45),
    )
    dt = LinearDrivetrain(name="dt", stages=stages)
    assert abs(dt.total_ratio() - 6.0) < 1e-9
    assert dt.total_efficiency() < 1.0
    assert dt.output_torque(1.0) > 1.0
    assert dt.output_speed(6000.0) < 6000.0


def test_nonlinear_friction_stribeck() -> None:
    friction = NonLinearFriction(
        coulomb_torque_nm=0.1,
        viscous_coeff_nm_s=0.001,
        stiction_torque_nm=0.2,
    )
    loss = friction.torque_loss(100.0)
    assert loss > 0.0
    # At zero speed, stiction is maximum
    loss_zero = friction.torque_loss(0.0)
    assert abs(loss_zero - (0.1 + 0.2)) < 1e-6


def test_backlash_dead_zone() -> None:
    bl = Backlash(deadband_rad=0.01)
    assert bl.effective_angle(0.003) == 0.0  # inside dead zone
    assert bl.effective_angle(0.02) > 0.0  # outside dead zone


def test_nonlinear_drivetrain_with_friction() -> None:
    stages = (GearStage(name="g1", teeth_input=20, teeth_output=40),)
    friction = NonLinearFriction(
        coulomb_torque_nm=0.05,
        viscous_coeff_nm_s=0.001,
        stiction_torque_nm=0.05,
    )
    dt = NonLinearDrivetrain(name="nldt", stages=stages, friction=friction)
    torque_no_friction = dt.total_ratio() * dt.total_efficiency() * 1.0
    torque_with_friction = dt.output_torque(1.0, speed_rpm=500.0)
    assert torque_with_friction < torque_no_friction


def test_pid_controller_step_response() -> None:
    pid = PIDController(kp=1.0, ki=0.1, kd=0.01)
    dt_s = 0.01
    value = 0.0
    for _ in range(200):
        error = 1.0 - value
        effort = pid.update(error, dt_s)
        value += effort * 0.01  # simple plant
    assert abs(value - 1.0) < 0.2


def test_simulate_drivetrain_linear() -> None:
    stages = (GearStage(name="g1", teeth_input=20, teeth_output=40),)
    dt = LinearDrivetrain(name="dt", stages=stages)
    pid = PIDController(kp=0.5, ki=0.1, kd=0.01)
    result = simulate_drivetrain(
        drivetrain=dt,
        controller=pid,
        target_speed_rpm=500.0,
        load_torque_nm=0.1,
        inertia_kg_m2=0.01,
        t_stop_s=1.0,
        dt_s=0.001,
    )
    assert isinstance(result, DrivetrainSimResult)
    assert len(result.times_s) > 0
    # Final output speed should have moved towards the target
    assert result.output_speeds_rpm[-1] != 0.0
