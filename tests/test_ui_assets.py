from pathlib import Path


def test_ui_assets_present() -> None:
    root = Path(__file__).resolve().parents[1]
    ui_dir = root / "ui"
    assert (ui_dir / "dashboard.html").is_file()
    assert (ui_dir / "dashboard.css").is_file()
    assert (ui_dir / "dashboard.js").is_file()
    assert (ui_dir / "dashboard_preview.html").is_file()
    assert (ui_dir / "schemas" / "engine_output.schema.json").is_file()
    assert (ui_dir / "sample_payload.json").is_file()
