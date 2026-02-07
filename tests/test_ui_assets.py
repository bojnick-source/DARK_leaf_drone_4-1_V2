from pathlib import Path


def test_ui_assets_present() -> None:
    root = Path(__file__).resolve().parents[1]
    ui_dir = root / "ui"

    # Assert only on UI assets that are guaranteed to be committed to the repo.
    # Additional build-generated or optional assets should be validated by
    # build-specific tests rather than hardcoded here.
    assert ui_dir.is_dir()
    assert (ui_dir / "README.md").is_file()
    assert (ui_dir / ".gitignore").is_file()


def test_cad_viewer_assets_present() -> None:
    root = Path(__file__).resolve().parents[1]
    ui_dir = root / "ui"

    assert (ui_dir / "cad_viewer.html").is_file()
    assert (ui_dir / "cad_viewer.js").is_file()
    assert (ui_dir / "cad_viewer.css").is_file()


def test_cad_viewer_html_has_three_js_import() -> None:
    root = Path(__file__).resolve().parents[1]
    html = (root / "ui" / "cad_viewer.html").read_text(encoding="utf-8")

    assert "three" in html.lower()
    assert "cad_viewer.js" in html
    assert "cad_viewer.css" in html


def test_cad_viewer_js_has_constraint_validation() -> None:
    root = Path(__file__).resolve().parents[1]
    js = (root / "ui" / "cad_viewer.js").read_text(encoding="utf-8")

    assert "validateConstraints" in js
    assert "constraintViolated" in js
    assert "0xff4d6a" in js or "ff4d6a" in js  # red color for constraint violation


def test_cad_viewer_js_has_interactive_controls() -> None:
    root = Path(__file__).resolve().parents[1]
    js = (root / "ui" / "cad_viewer.js").read_text(encoding="utf-8")

    assert "attachSliders" in js
    assert "onParamsChanged" in js
    assert "exportSTL" in js
    assert "applyPayload" in js


def test_dashboard_links_to_cad_viewer() -> None:
    root = Path(__file__).resolve().parents[1]
    html = (root / "ui" / "dashboard.html").read_text(encoding="utf-8")

    assert "cad_viewer.html" in html
