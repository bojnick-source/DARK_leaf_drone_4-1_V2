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
