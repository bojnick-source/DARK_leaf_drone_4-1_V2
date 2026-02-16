"""Tests for the desktop launcher module (sfcs_mdp.desktop)."""

from __future__ import annotations

import socket
from pathlib import Path

import pytest
from sfcs_mdp.desktop import (
    _find_free_port,
    _find_ui_dir,
    detect_hardware,
    launch,
)

# ── detect_hardware ──────────────────────────────────────────────────

def test_detect_hardware_returns_cores() -> None:
    hw = detect_hardware()
    assert "cores" in hw
    assert int(hw["cores"]) >= 1


def test_detect_hardware_returns_platform() -> None:
    hw = detect_hardware()
    assert "platform" in hw
    assert hw["platform"] in ("linux", "darwin", "windows")


def test_detect_hardware_returns_arch_bits() -> None:
    hw = detect_hardware()
    assert hw["arch_bits"] in ("32", "64")


# ── _find_free_port ──────────────────────────────────────────────────

def test_find_free_port_returns_int() -> None:
    port = _find_free_port()
    assert isinstance(port, int)
    assert 8000 <= port < 8100


def test_find_free_port_is_actually_free() -> None:
    port = _find_free_port()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", port))  # should not raise


def test_find_free_port_skips_occupied() -> None:
    # Occupy the first port so it has to pick the next one
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 8000))
        port = _find_free_port(start=8000, stop=8010)
        assert port != 8000


def test_find_free_port_raises_when_exhausted() -> None:
    # Occupy the entire range
    socks = []
    try:
        for p in range(9900, 9903):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(("127.0.0.1", p))
            socks.append(s)
        with pytest.raises(RuntimeError, match="No free port"):
            _find_free_port(start=9900, stop=9903)
    finally:
        for s in socks:
            s.close()


# ── _find_ui_dir ─────────────────────────────────────────────────────

def test_find_ui_dir_from_repo_root() -> None:
    """The ui/ dir should be found when run from the repo root."""
    root = Path(__file__).resolve().parents[1]
    ui_dir = root / "ui"
    if ui_dir.is_dir():
        found = _find_ui_dir()
        assert found.is_dir()
        assert (found / "launcher.html").is_file()


def test_find_ui_dir_raises_when_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    # Patch __file__ so the module-relative candidate also fails
    monkeypatch.setattr("sfcs_mdp.desktop.__file__", str(tmp_path / "fake.py"))
    with pytest.raises(FileNotFoundError, match="launcher.html"):
        _find_ui_dir()


# ── launch (unit-level) ──────────────────────────────────────────────

def test_launch_returns_1_when_ui_missing(tmp_path: Path) -> None:
    result = launch(ui_dir=tmp_path / "nonexistent")
    assert result == 1


def test_launch_returns_1_when_no_launcher_html(tmp_path: Path) -> None:
    """Even if the directory exists, it must contain launcher.html."""
    empty_dir = tmp_path / "ui"
    empty_dir.mkdir()
    result = launch(ui_dir=empty_dir)
    assert result == 1


def test_launch_cli_subcommand_registered() -> None:
    """The 'launch' subcommand should appear in --help output."""
    from sfcs_mdp.cli import _build_parser

    parser = _build_parser()
    # Parsing 'launch --no-browser' should work without error
    args = parser.parse_args(["launch", "--no-browser"])
    assert args.command == "launch"
    assert args.no_browser is True
