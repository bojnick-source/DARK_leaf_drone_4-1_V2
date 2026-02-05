from reidce.wind_ship import (
    WindCondition,
    WindShipParams,
    WindShipState,
    best_heading_for_wind,
    evaluate_wind_ship,
)


def test_wind_ship_performance() -> None:
    params = WindShipParams(sail_area_m2=80.0, hull_wetted_area_m2=120.0, mass_kg=12000.0)
    wind = WindCondition(true_wind_speed_m_s=12.0, true_wind_dir_rad=0.0)
    state = WindShipState(speed_m_s=6.0, heading_rad=0.3)
    perf = evaluate_wind_ship(state, wind, params)
    assert perf.apparent_wind_speed_m_s > 0.0
    assert perf.sail_force_n > 0.0


def test_best_heading_search() -> None:
    params = WindShipParams(sail_area_m2=60.0, hull_wetted_area_m2=90.0, mass_kg=9000.0)
    wind = WindCondition(true_wind_speed_m_s=10.0, true_wind_dir_rad=0.0)
    heading = best_heading_for_wind(wind, params, speed_m_s=5.0, heading_samples=36)
    assert -3.2 < heading < 3.2
