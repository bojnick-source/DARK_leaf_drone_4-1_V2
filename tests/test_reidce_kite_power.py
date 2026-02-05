from reidce.kite_power import KiteParams, KiteWind, kite_aero_forces, kite_power, optimal_reeling_speed


def test_kite_aero_forces() -> None:
    params = KiteParams(area_m2=25.0, cl=1.1, cd=0.1)
    wind = KiteWind(wind_speed_m_s=12.0)
    forces = kite_aero_forces(params, wind)
    assert forces["lift_n"] > 0.0
    assert forces["drag_n"] > 0.0


def test_kite_power() -> None:
    params = KiteParams(area_m2=18.0, cl=1.0, cd=0.12, tether_efficiency=0.85)
    wind = KiteWind(wind_speed_m_s=10.0)
    reel = optimal_reeling_speed(params, wind, speed_fraction=0.3)
    result = kite_power(params, wind, reeling_speed_m_s=reel)
    assert result.electrical_power_w > 0.0
    assert 0.0 < result.efficiency <= 1.0
