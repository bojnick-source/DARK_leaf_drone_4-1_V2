import json
import subprocess
import sys
from pathlib import Path

import pytest

from sfcs_mdp.cli import main, resolve_spec_path


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


def _patch(role: str, lab: dict[str, float]) -> dict[str, object]:
    return {
        "name": role,
        "role": role,
        "reference_lab": lab,
        "sample_lab": lab,
    }


def _color_scene_payload() -> dict[str, object]:
    return {
        "icc_profile": {"profile_hash": None},
        "reference_mode": False,
        "patches": [
            _patch("grayscale", {"L": 10, "a": 0, "b": 0}),
            _patch("grayscale", {"L": 50, "a": 0, "b": 0}),
            _patch("neutral", {"L": 50, "a": 0.5, "b": -0.2}),
            _patch("warm_neutral", {"L": 55, "a": 4, "b": 6}),
            _patch("primary_red", {"L": 50, "a": 70, "b": 40}),
            _patch("primary_green", {"L": 50, "a": -60, "b": 60}),
            _patch("primary_blue", {"L": 50, "a": 0, "b": -70}),
            _patch("secondary_cyan", {"L": 60, "a": -40, "b": -20}),
            _patch("secondary_magenta", {"L": 50, "a": 70, "b": -20}),
            _patch("secondary_yellow", {"L": 70, "a": -5, "b": 70}),
            _patch("deep_black", {"L": 0, "a": 0, "b": 0}),
            _patch("near_white", {"L": 98, "a": 0, "b": 0}),
        ],
    }


def test_color_qa_cli_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    report_path = tmp_path / "scene.json"
    report_path.write_text(json.dumps(_color_scene_payload()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        ["sfcs-mdp", "color-qa", "--report", report_path.as_posix()],
    )
    assert main() == 0
    output = capsys.readouterr().out
    payload = json.loads(output)
    assert payload["passed"] is True


def test_color_qa_cli_missing_file(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    missing = Path("missing.json")
    monkeypatch.setattr(
        "sys.argv",
        ["sfcs-mdp", "color-qa", "--report", missing.as_posix()],
    )
    assert main() == 1
    output = capsys.readouterr().out
    assert "QA report not found" in output


def test_color_qa_cli_invalid_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    report_path = tmp_path / "scene.json"
    report_path.write_text(
        json.dumps({"icc_profile": {"profile_hash": None}, "patches": []}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv",
        ["sfcs-mdp", "color-qa", "--report", report_path.as_posix()],
    )
    assert main() == 1
    output = capsys.readouterr().out
    assert "QA REPORT INVALID" in output


def test_cli_validate_outputs_grading_footer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    spec_dir = tmp_path / "manufacturing"
    spec_dir.mkdir()
    spec_path = spec_dir / "sfcs_drone_mdp_v0.yaml"
    spec_path.write_text("meta: {}\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["sfcs-mdp", "validate"])
    assert main() == 1
    output = capsys.readouterr().out
    assert "VALIDATION FAILED" in output
    assert "Total: 100.00/100.00" in output


def test_module_invocation_help() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "sfcs_mdp", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "validate" in result.stdout
    assert "simulate" in result.stdout
