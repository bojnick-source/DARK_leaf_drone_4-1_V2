
from reidce.electromagnetic import (
    AxialFluxGeometry,
    AxialFluxMotor,
    LinearBHCurve,
    MotorDesignPoint,
    NonLinearBHCurve,
    PermanentMagnet,
    Winding,
    efficiency_map,
    evaluate_motor,
    saturation_curve,
)


def test_linear_bh_curve() -> None:
    bh = LinearBHCurve(mu_r=5000.0)
    h = 1000.0
    b = bh.b_from_h(h)
    assert b > 0.0
    h_back = bh.h_from_b(b)
    assert abs(h_back - h) < 1e-6


def test_nonlinear_bh_saturation() -> None:
    bh = NonLinearBHCurve(mu_r_initial=5000.0, b_saturation_t=1.5)
    # At low H, should be approximately linear
    b_low = bh.b_from_h(10.0)
    assert b_low > 0.0
    # At very high H, should approach saturation
    b_high = bh.b_from_h(1e6)
    assert b_high < 1.5
    assert b_high > 1.0  # well into saturation region


def test_nonlinear_incremental_permeability() -> None:
    bh = NonLinearBHCurve(mu_r_initial=5000.0, b_saturation_t=1.5)
    mu_low = bh.incremental_mu_r(0.0)
    mu_high = bh.incremental_mu_r(1e5)
    assert mu_low > mu_high  # permeability drops with saturation


def test_saturation_curve_points() -> None:
    bh = NonLinearBHCurve(mu_r_initial=4000.0, b_saturation_t=1.8)
    curve = saturation_curve(bh, h_max_a_per_m=1e5, n_points=20)
    assert len(curve) == 20
    # B should be monotonically increasing
    for i in range(1, len(curve)):
        assert curve[i][1] >= curve[i - 1][1]


def test_winding_resistance() -> None:
    w = Winding(
        turns_per_coil=50,
        num_coils=12,
        wire_diameter_m=1e-3,
        mean_turn_length_m=0.08,
    )
    assert w.total_turns() == 600
    assert w.resistance() > 0.0
    assert w.copper_loss_w(5.0) > 0.0


def test_axial_flux_geometry() -> None:
    geo = AxialFluxGeometry(
        outer_radius_m=0.08,
        inner_radius_m=0.04,
        airgap_m=0.001,
        rotor_thickness_m=0.005,
        stator_thickness_m=0.01,
        num_poles=12,
    )
    assert geo.active_area_m2() > 0.0
    assert geo.mean_radius_m() == 0.06
    assert geo.pole_pitch_m() > 0.0
    assert geo.axial_length_m() > 0.0


def test_permanent_magnet_length() -> None:
    pm = PermanentMagnet(remanence_t=1.2, coercivity_a_per_m=900_000.0)
    lm = pm.magnet_length_for_airgap(airgap_m=0.001, target_b_t=0.8)
    assert lm > 0.0


def test_axial_flux_motor_linear() -> None:
    geo = AxialFluxGeometry(
        outer_radius_m=0.08,
        inner_radius_m=0.04,
        airgap_m=0.001,
        rotor_thickness_m=0.005,
        stator_thickness_m=0.01,
        num_poles=12,
    )
    w = Winding(
        turns_per_coil=50,
        num_coils=12,
        wire_diameter_m=1e-3,
        mean_turn_length_m=0.08,
    )
    pm = PermanentMagnet(remanence_t=1.2, coercivity_a_per_m=900_000.0)
    bh = LinearBHCurve(mu_r=5000.0)
    motor = AxialFluxMotor(name="m1", geometry=geo, winding=w, magnet=pm, bh_curve=bh)
    assert motor.airgap_flux_density_t() > 0.0
    assert motor.flux_per_pole_wb() > 0.0
    assert motor.torque_constant_nm_per_a() > 0.0
    assert motor.electromagnetic_torque_nm(10.0) > 0.0
    assert motor.mechanical_power_w(10.0, 3000.0) > 0.0
    assert motor.copper_loss_w(10.0) > 0.0


def test_axial_flux_motor_nonlinear() -> None:
    geo = AxialFluxGeometry(
        outer_radius_m=0.08,
        inner_radius_m=0.04,
        airgap_m=0.001,
        rotor_thickness_m=0.005,
        stator_thickness_m=0.01,
        num_poles=12,
    )
    w = Winding(
        turns_per_coil=50,
        num_coils=12,
        wire_diameter_m=1e-3,
        mean_turn_length_m=0.08,
    )
    pm = PermanentMagnet(remanence_t=1.2, coercivity_a_per_m=900_000.0)
    bh = NonLinearBHCurve(mu_r_initial=5000.0, b_saturation_t=1.5)
    motor = AxialFluxMotor(name="m2", geometry=geo, winding=w, magnet=pm, bh_curve=bh)
    assert motor.airgap_flux_density_t() > 0.0
    assert motor.electromagnetic_torque_nm(10.0) > 0.0


def test_motor_efficiency() -> None:
    geo = AxialFluxGeometry(
        outer_radius_m=0.08,
        inner_radius_m=0.04,
        airgap_m=0.001,
        rotor_thickness_m=0.005,
        stator_thickness_m=0.01,
        num_poles=12,
    )
    w = Winding(
        turns_per_coil=50,
        num_coils=12,
        wire_diameter_m=1e-3,
        mean_turn_length_m=0.08,
    )
    pm = PermanentMagnet(remanence_t=1.2, coercivity_a_per_m=900_000.0)
    bh = LinearBHCurve(mu_r=5000.0)
    motor = AxialFluxMotor(name="m1", geometry=geo, winding=w, magnet=pm, bh_curve=bh)
    eff = motor.efficiency(10.0, 3000.0)
    assert 0.0 < eff <= 1.0


def test_evaluate_motor_design_point() -> None:
    geo = AxialFluxGeometry(
        outer_radius_m=0.08,
        inner_radius_m=0.04,
        airgap_m=0.001,
        rotor_thickness_m=0.005,
        stator_thickness_m=0.01,
        num_poles=12,
    )
    w = Winding(
        turns_per_coil=50,
        num_coils=12,
        wire_diameter_m=1e-3,
        mean_turn_length_m=0.08,
    )
    pm = PermanentMagnet(remanence_t=1.2, coercivity_a_per_m=900_000.0)
    bh = LinearBHCurve(mu_r=5000.0)
    motor = AxialFluxMotor(name="m1", geometry=geo, winding=w, magnet=pm, bh_curve=bh)
    dp = evaluate_motor(motor, speed_rpm=2000.0, current_a=8.0)
    assert isinstance(dp, MotorDesignPoint)
    assert dp.torque_nm > 0.0
    assert dp.power_w > 0.0
    assert 0.0 < dp.efficiency <= 1.0


def test_efficiency_map() -> None:
    geo = AxialFluxGeometry(
        outer_radius_m=0.08,
        inner_radius_m=0.04,
        airgap_m=0.001,
        rotor_thickness_m=0.005,
        stator_thickness_m=0.01,
        num_poles=12,
    )
    w = Winding(
        turns_per_coil=50,
        num_coils=12,
        wire_diameter_m=1e-3,
        mean_turn_length_m=0.08,
    )
    pm = PermanentMagnet(remanence_t=1.2, coercivity_a_per_m=900_000.0)
    bh = LinearBHCurve(mu_r=5000.0)
    motor = AxialFluxMotor(name="m1", geometry=geo, winding=w, magnet=pm, bh_curve=bh)
    points = efficiency_map(
        motor,
        speed_range_rpm=(500.0, 5000.0),
        current_range_a=(1.0, 15.0),
        n_speed=5,
        n_current=4,
    )
    assert len(points) == 20
