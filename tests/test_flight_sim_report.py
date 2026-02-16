import json
from pathlib import Path

from reidce.flight_sim import (
    GuidanceTarget,
    SimulationResult,
    VehicleState,
    simulate_flight,
)
from reidce.flight_sim_report import (
    build_report,
    generate_report,
    load_report,
    run_ai_flight,
    summarize_telemetry,
    write_report,
)


def test_simulation_result_has_energy_telemetry() -> None:
    """SimulationResult now tracks energy, battery, and temperature."""
    initial = VehicleState(z_m=0.0, vx_m_s=8.0)
    target = GuidanceTarget(altitude_m=50.0, speed_m_s=12.0, heading_rad=0.0)
    result = simulate_flight(initial, target, duration_s=5.0, dt_s=0.05)
    assert len(result.energy_used_j) == len(result.time_s)
    assert len(result.battery_pct) == len(result.time_s)
    assert len(result.temperature_c) == len(result.time_s)
    assert result.energy_used_j[0] >= 0.0
    assert result.energy_used_j[-1] > 0.0
    assert result.battery_pct[0] > 99.0
    assert result.battery_pct[-1] < 100.0


def test_battery_decreases_over_time() -> None:
    initial = VehicleState(z_m=0.0, vx_m_s=5.0)
    target = GuidanceTarget(altitude_m=30.0, speed_m_s=10.0, heading_rad=0.0)
    result = simulate_flight(initial, target, duration_s=10.0, dt_s=0.05)
    assert result.battery_pct[-1] < result.battery_pct[0]


def test_temperature_rises_from_ambient() -> None:
    initial = VehicleState(z_m=0.0, vx_m_s=5.0)
    target = GuidanceTarget(altitude_m=30.0, speed_m_s=10.0, heading_rad=0.0)
    result = simulate_flight(initial, target, duration_s=10.0, dt_s=0.05, ambient_temp_c=20.0)
    assert result.temperature_c[0] >= 20.0
    assert max(result.temperature_c) > 20.0


def test_run_ai_flight_returns_simulation_result() -> None:
    result = run_ai_flight(altitude_m=30.0, speed_m_s=10.0, duration_s=5.0, dt_s=0.1)
    assert isinstance(result, SimulationResult)
    assert len(result.time_s) > 1
    assert len(result.energy_used_j) == len(result.time_s)


def test_build_report_schema() -> None:
    result = run_ai_flight(duration_s=5.0, dt_s=0.1)
    report = build_report(result, max_points=100)
    assert report["schema"] == "dark/flight_sim/report/1.0"
    assert "summary" in report
    assert "telemetry" in report
    summary = report["summary"]
    for key in [
        "duration_s",
        "final_altitude_m",
        "final_speed_m_s",
        "max_altitude_m",
        "max_speed_m_s",
        "energy_used_j",
        "battery_remaining_pct",
        "max_temperature_c",
    ]:
        assert key in summary, f"missing summary key: {key}"
    telemetry = report["telemetry"]
    for key in [
        "time_s",
        "altitude_m",
        "speed_m_s",
        "throttle_pct",
        "roll_deg",
        "pitch_deg",
        "heading_deg",
        "energy_used_j",
        "battery_pct",
        "temperature_c",
        "x_m",
        "y_m",
    ]:
        assert key in telemetry, f"missing telemetry key: {key}"


def test_build_report_downsamples() -> None:
    result = run_ai_flight(duration_s=10.0, dt_s=0.01)
    assert len(result.time_s) > 600
    report = build_report(result, max_points=100)
    assert len(report["telemetry"]["time_s"]) <= 100


def test_generate_report_end_to_end() -> None:
    report = generate_report(duration_s=3.0, dt_s=0.1, max_points=50)
    assert report["schema"] == "dark/flight_sim/report/1.0"
    assert report["summary"]["duration_s"] > 0
    telemetry = report["telemetry"]
    assert len(telemetry["time_s"]) <= 50


def test_write_report_creates_file(tmp_path: Path) -> None:
    report = generate_report(duration_s=2.0, dt_s=0.1)
    out_path = tmp_path / "report.json"
    write_report(report, out_path)
    assert out_path.exists()
    loaded = json.loads(out_path.read_text(encoding="utf-8"))
    assert loaded["schema"] == "dark/flight_sim/report/1.0"


def test_report_values_are_json_serializable() -> None:
    report = generate_report(duration_s=3.0, dt_s=0.1)
    serialized = json.dumps(report)
    assert isinstance(serialized, str)
    roundtrip = json.loads(serialized)
    assert roundtrip["schema"] == report["schema"]


def test_flight_sim_html_exists() -> None:
    root = Path(__file__).resolve().parents[1]
    assert (root / "ui" / "flight_sim.html").is_file()


def test_dashboard_links_to_flight_sim() -> None:
    """dashboard.html is now a redirect placeholder linking to launcher.html."""
    root = Path(__file__).resolve().parents[1]
    # dashboard.html is now a placeholder, check launcher.html instead
    html = (root / "ui" / "launcher.html").read_text(encoding="utf-8")
    # launcher should have simulation capability
    assert "sim" in html.lower() or "flight" in html.lower()


def test_load_report_roundtrip(tmp_path: Path) -> None:
    report = generate_report(duration_s=2.0, dt_s=0.1)
    out_path = tmp_path / "report.json"
    write_report(report, out_path)
    loaded = load_report(out_path)
    assert loaded["schema"] == report["schema"]
    assert loaded["summary"] == report["summary"]


def test_generate_report_forwards_battery_params() -> None:
    report = generate_report(
        duration_s=3.0, dt_s=0.1, battery_capacity_j=50000.0, ambient_temp_c=35.0,
    )
    assert report["summary"]["battery_remaining_pct"] < 100.0
    assert report["summary"]["max_temperature_c"] >= 35.0


def test_summarize_telemetry_returns_aggregates() -> None:
    report = generate_report(duration_s=5.0, dt_s=0.1)
    summary = summarize_telemetry(report)
    assert "distance_traveled_m" in summary
    assert "average_speed_m_s" in summary
    assert "average_throttle_pct" in summary
    assert summary["distance_traveled_m"] >= 0.0
    assert summary["average_speed_m_s"] >= 0.0
    assert summary["average_throttle_pct"] >= 0.0
