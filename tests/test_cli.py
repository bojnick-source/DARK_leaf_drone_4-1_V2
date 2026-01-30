from pathlib import Path

import pytest
from sfcs_mdp.cli import resolve_spec_path


def test_resolve_spec_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    spec_dir = tmp_path / "manufacturing"
    spec_dir.mkdir()
    spec_path = spec_dir / "sfcs_drone_mdp_v0.yaml"
    spec_path.write_text("meta: {}\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert resolve_spec_path(None) == spec_path


def test_resolve_spec_missing_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileNotFoundError):
        resolve_spec_path(None)


def test_resolve_spec_relative(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    spec_path = tmp_path / "spec.yaml"
    spec_path.write_text("meta: {}\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    resolved = resolve_spec_path(Path("spec.yaml"))
    assert resolved == spec_path
