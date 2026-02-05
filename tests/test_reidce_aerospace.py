from reidce.aerospace import AeroCoefficients, isa_atmosphere, lift_drag, range_endurance


def test_aero_lift_drag() -> None:
    atmo = isa_atmosphere(altitude_m=0.0)
    coeffs = AeroCoefficients(cl=0.6, cd=0.05)
    result = lift_drag(speed_m_s=20.0, wing_area_m2=0.5, coeffs=coeffs, rho_kg_m3=atmo.density_kg_m3)
    assert result["lift_n"] > 0.0
    assert result["drag_n"] > 0.0


def test_range_endurance() -> None:
    estimate = range_endurance(cruise_speed_m_s=18.0, specific_energy_j_kg=900000.0, mass_kg=2.4)
    assert estimate.range_km > 0.0
    assert estimate.endurance_s > 0.0
