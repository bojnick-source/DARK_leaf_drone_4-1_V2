"""Tests for DARPA LIFT challenge governing equations and design evaluation."""

import math

from reidce.lift_challenge import (
    ALADDIN_3B,
    ALADDIN_3B_MISSION,
    ALADDIN_3B_ROTORS,
    DARPA_MAX_AIRCRAFT_MASS_KG,
    DARPA_MIN_PAYLOAD_KG,
    DesignConfig,
    DiskAreaResult,
    MissionPhase,
    RotorConfig,
    effective_disk_area,
    evaluate_design,
    hover_power,
    ideal_induced_power,
    mission_closure,
    shaft_power,
)

# -- Disk area ---------------------------------------------------------------

def test_open_quad_disk_area() -> None:
    """4 × 2.45 m open rotors → A_eff ≈ 18.9 m²."""
    result = effective_disk_area(ALADDIN_3B_ROTORS)
    assert isinstance(result, DiskAreaResult)
    assert result.effective_disk_count == 4.0
    expected = 4.0 * math.pi * 1.225 ** 2
    assert abs(result.a_eff_m2 - expected) < 0.01


def test_coaxial_disk_area_halved() -> None:
    """Coaxial rotors in same footprint do NOT double area."""
    coax = RotorConfig(rotor_radius_m=0.54 / 2.0, rotor_count=8, is_coaxial=True)
    result = effective_disk_area(coax)
    assert result.effective_disk_count == 4.0
    single = math.pi * (0.54 / 2.0) ** 2
    assert abs(result.a_eff_m2 - single * 4.0) < 0.01


def test_coaxial_vs_open_area_ratio() -> None:
    """Open quad has much larger A_eff than ducted coaxial → less power."""
    open_cfg = RotorConfig(rotor_radius_m=1.225, rotor_count=4, is_coaxial=False)
    coax_cfg = RotorConfig(rotor_radius_m=0.54 / 2.0, rotor_count=8, is_coaxial=True)
    a_open = effective_disk_area(open_cfg).a_eff_m2
    a_coax = effective_disk_area(coax_cfg).a_eff_m2
    assert a_open > 10 * a_coax


# -- Momentum theory ---------------------------------------------------------

def test_ideal_induced_power_positive() -> None:
    """Ideal induced power is positive for valid inputs."""
    p = ideal_induced_power(thrust_n=1506.0, rho=1.225, a_eff_m2=18.85)
    assert p > 0


def test_ideal_induced_power_formula() -> None:
    """P_i_ideal = T^(3/2) / sqrt(2ρA)."""
    t = 1506.0
    rho = 1.225
    a = 18.85
    expected = t ** 1.5 / math.sqrt(2.0 * rho * a)
    actual = ideal_induced_power(t, rho, a)
    assert abs(actual - expected) < 1.0


def test_power_scales_with_inv_sqrt_area() -> None:
    """P ∝ 1/√A_eff — doubling area reduces power by ~29 %."""
    t, rho = 1506.0, 1.225
    p1 = ideal_induced_power(t, rho, 10.0)
    p2 = ideal_induced_power(t, rho, 20.0)
    ratio = p2 / p1
    assert abs(ratio - 1.0 / math.sqrt(2.0)) < 0.01


# -- Shaft power -------------------------------------------------------------

def test_shaft_power_with_fm() -> None:
    """P_shaft = P_ideal × (1/FM + k_profile)."""
    p_ideal = 8600.0
    p_shaft = shaft_power(p_ideal, fm_net=0.75, k_profile=0.25)
    expected = 8600.0 * (1.0 / 0.75 + 0.25)
    assert abs(p_shaft - expected) < 1.0


# -- Hover power (combined) --------------------------------------------------

def test_aladdin_3b_hover_power() -> None:
    """ALADDIN-3B hover shaft power ≈ 12.8 kW (within 15 % of manual calc)."""
    gross = ALADDIN_3B.dry_mass_kg + ALADDIN_3B.fuel_mass_kg + ALADDIN_3B.payload_mass_kg
    hp = hover_power(gross_mass_kg=gross, config=ALADDIN_3B_ROTORS, fm_net=0.75)
    assert 10_000 < hp.p_shaft_w < 16_000


def test_hover_power_returns_correct_thrust() -> None:
    hp = hover_power(gross_mass_kg=100.0, config=ALADDIN_3B_ROTORS)
    assert abs(hp.thrust_n - 100.0 * 9.80665) < 0.1


# -- Mission closure ----------------------------------------------------------

def test_aladdin_3b_mission_closes() -> None:
    """ALADDIN-3B mission closes with positive fuel margin."""
    sfc_kg_per_wh = 0.30 / 1000.0  # 0.30 kg/kWh → kg/Wh
    result = mission_closure(
        phases=ALADDIN_3B_MISSION,
        fuel_available_kg=1.55,
        sfc_kg_per_wh=sfc_kg_per_wh,
    )
    assert result.closes
    assert result.margin_fraction > 0
    assert result.total_time_s < 30 * 60  # < 30 min


def test_mission_phase_energy() -> None:
    phase = MissionPhase(name="test", duration_s=3600.0, power_w=1000.0)
    assert abs(phase.energy_wh - 1000.0) < 0.01


# -- Design evaluation -------------------------------------------------------

def test_evaluate_aladdin_3b() -> None:
    """ALADDIN-3B passes all DARPA LIFT constraints."""
    ev = evaluate_design(ALADDIN_3B)
    assert ev.mass_under_limit
    assert ev.ratio_meets_minimum
    assert ev.payload_ratio > DARPA_MIN_PAYLOAD_KG / DARPA_MAX_AIRCRAFT_MASS_KG
    assert len(ev.errors) == 0


def test_overweight_design_fails() -> None:
    """A design exceeding the 55 lb cap reports an error."""
    heavy = DesignConfig(
        design_id="X1",
        name="Overweight",
        rotor_config=ALADDIN_3B_ROTORS,
        dry_mass_kg=30.0,
        fuel_mass_kg=2.0,
        payload_mass_kg=60.0,
        installed_power_w=18000.0,
    )
    ev = evaluate_design(heavy)
    assert not ev.mass_under_limit
    assert len(ev.errors) > 0


def test_underpayload_design_fails() -> None:
    """A design below the 110 lb minimum payload reports an error."""
    light = DesignConfig(
        design_id="X2",
        name="Under-payload",
        rotor_config=ALADDIN_3B_ROTORS,
        dry_mass_kg=20.0,
        fuel_mass_kg=1.5,
        payload_mass_kg=30.0,
        installed_power_w=18000.0,
    )
    ev = evaluate_design(light)
    assert not ev.ratio_meets_minimum
    assert len(ev.errors) > 0
