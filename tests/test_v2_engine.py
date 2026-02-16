import json
from pathlib import Path
from unittest.mock import patch

import pytest
from v2.python.engine import find_engine_cli, run_engine


def test_find_engine_cli_with_explicit_path(tmp_path: Path) -> None:
    fake_cli = tmp_path / "v2_engine_cli"
    fake_cli.write_text("#!/bin/sh\n", encoding="utf-8")
    assert find_engine_cli(str(fake_cli)) == str(fake_cli)


def test_find_engine_cli_missing_path() -> None:
    assert find_engine_cli("/nonexistent/v2_engine_cli") is None


def test_find_engine_cli_none_when_not_on_path() -> None:
    with patch("shutil.which", return_value=None):
        assert find_engine_cli() is None


def test_find_engine_cli_found_on_path() -> None:
    with patch("shutil.which", return_value="/usr/bin/v2_engine_cli"):
        assert find_engine_cli() == "/usr/bin/v2_engine_cli"


def test_run_engine_success(tmp_path: Path) -> None:
    # Create a fake engine script that outputs valid JSON
    fake_cli = tmp_path / "fake_engine"
    golden = {
        "schema": "dark/v2/io/run_output/2.0",
        "run_id": "abc123",
        "ok": True,
        "inputs": {"alpha": "1.0"},
        "metrics": {"energy": 42.0},
    }
    fake_cli.write_text(
        f"#!/bin/sh\necho '{json.dumps(golden)}'\n", encoding="utf-8"
    )
    fake_cli.chmod(0o755)

    result = run_engine(str(fake_cli), '{"alpha":"1.0"}', no_write=True)
    assert result["ok"] is True
    assert result["run_id"] == "abc123"
    assert result["metrics"]["energy"] == 42.0


def test_run_engine_nonzero_exit(tmp_path: Path) -> None:
    fake_cli = tmp_path / "fail_engine"
    fake_cli.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    fake_cli.chmod(0o755)

    with pytest.raises(RuntimeError, match="exited with code 1"):
        run_engine(str(fake_cli), '{"alpha":"1.0"}')


def test_run_engine_bad_json(tmp_path: Path) -> None:
    fake_cli = tmp_path / "bad_engine"
    fake_cli.write_text("#!/bin/sh\necho 'NOT JSON'\n", encoding="utf-8")
    fake_cli.chmod(0o755)

    with pytest.raises(RuntimeError, match="invalid JSON"):
        run_engine(str(fake_cli), '{"alpha":"1.0"}')


def test_run_engine_missing_binary() -> None:
    with pytest.raises(RuntimeError, match="not found"):
        run_engine("/nonexistent/v2_engine_cli", '{"alpha":"1.0"}')


def test_engine_cli_subcommand_missing_engine(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from sfcs_mdp.cli import main

    monkeypatch.setattr(
        "sys.argv",
        [
            "sfcs-mdp",
            "engine",
            "--engine-cli",
            "/nonexistent/v2_engine_cli",
            "--canonical-input",
            '{"alpha":"1.0"}',
        ],
    )
    assert main() == 1
    output = capsys.readouterr().out
    assert "v2_engine_cli not found" in output


def test_engine_cli_subcommand_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from sfcs_mdp.cli import main

    golden = {"schema": "dark/v2/io/run_output/2.0", "run_id": "test", "ok": True}
    fake_cli = tmp_path / "fake_engine"
    fake_cli.write_text(
        f"#!/bin/sh\necho '{json.dumps(golden)}'\n", encoding="utf-8"
    )
    fake_cli.chmod(0o755)

    monkeypatch.setattr(
        "sys.argv",
        [
            "sfcs-mdp",
            "engine",
            "--engine-cli",
            str(fake_cli),
            "--canonical-input",
            '{"alpha":"1.0"}',
        ],
    )
    assert main() == 0
    output = capsys.readouterr().out
    assert '"ok": true' in output


def test_run_traveler_with_engine_cli(tmp_path: Path) -> None:
    from sfcs_mdp.model import BlockLevel
    from sfcs_mdp.runner import run_traveler

    spec_path = (
        Path(__file__).resolve().parents[1]
        / "manufacturing"
        / "sfcs_drone_mdp_v0.yaml"
    )

    golden = {"schema": "dark/v2/io/run_output/2.0", "run_id": "integ", "ok": True}
    fake_cli = tmp_path / "fake_engine"
    fake_cli.write_text(
        f"#!/bin/sh\necho '{json.dumps(golden)}'\n", encoding="utf-8"
    )
    fake_cli.chmod(0o755)

    build_dir = run_traveler(
        spec_path=spec_path,
        build_id="BUILD_ENGINE_TEST",
        rev_tag="REV_A",
        block_level=BlockLevel.BLOCK_0_STRUCTURE_ONLY,
        simulate=True,
        repo_root=tmp_path,
        engine_cli=str(fake_cli),
    )

    # v2_engine_output.json should be archived in the build directory
    engine_output = build_dir / "v2_engine_output.json"
    assert engine_output.exists()
    data = json.loads(engine_output.read_text(encoding="utf-8"))
    assert data["ok"] is True
    assert data["run_id"] == "integ"

    # ledger should include the v2_engine result
    ledger = json.loads((build_dir / "ledger.json").read_text(encoding="utf-8"))
    assert "v2_engine" in ledger
    assert ledger["v2_engine"]["ok"] is True


def test_run_traveler_without_engine_cli(tmp_path: Path) -> None:
    """Without --engine-cli, no engine output should be created."""
    from sfcs_mdp.model import BlockLevel
    from sfcs_mdp.runner import run_traveler

    spec_path = (
        Path(__file__).resolve().parents[1]
        / "manufacturing"
        / "sfcs_drone_mdp_v0.yaml"
    )

    build_dir = run_traveler(
        spec_path=spec_path,
        build_id="BUILD_NO_ENGINE",
        rev_tag="REV_A",
        block_level=BlockLevel.BLOCK_0_STRUCTURE_ONLY,
        simulate=True,
        repo_root=tmp_path,
    )

    assert not (build_dir / "v2_engine_output.json").exists()
    ledger = json.loads((build_dir / "ledger.json").read_text(encoding="utf-8"))
    assert "v2_engine" not in ledger
