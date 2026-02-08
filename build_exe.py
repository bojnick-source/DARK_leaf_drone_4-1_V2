"""Build a standalone sfcs-mdp executable using PyInstaller.

Usage
-----
    python build_exe.py          # produces dist/sfcs-mdp (or dist/sfcs-mdp.exe on Windows)
    python build_exe.py --onedir # produces dist/sfcs-mdp/ directory bundle

The script automatically includes the ``manufacturing/`` data directory so
that the default spec file is available inside the bundled executable.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
ENTRY_POINT = REPO_ROOT / "src" / "sfcs_mdp" / "__main__.py"
MANUFACTURING_DIR = REPO_ROOT / "manufacturing"
EXE_NAME = "sfcs-mdp"


def build(onedir: bool = False) -> Path:
    """Run PyInstaller and return the path to the output artifact."""
    if not ENTRY_POINT.is_file():
        raise FileNotFoundError(f"Entry point not found: {ENTRY_POINT}")

    cmd: list[str] = [
        sys.executable,
        "-m",
        "PyInstaller",
        str(ENTRY_POINT),
        "--name",
        EXE_NAME,
        "--noconfirm",
        "--clean",
    ]

    if onedir:
        cmd.append("--onedir")
    else:
        cmd.append("--onefile")

    # Bundle the manufacturing specs so the default --spec path resolves.
    if MANUFACTURING_DIR.is_dir():
        cmd.extend(["--add-data", f"{MANUFACTURING_DIR}{_sep()}manufacturing"])

    # Hidden imports that PyInstaller may miss during analysis.
    for mod in ("pydantic", "yaml"):
        cmd.extend(["--hidden-import", mod])

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(REPO_ROOT), check=False)
    if result.returncode != 0:
        raise RuntimeError(f"PyInstaller exited with code {result.returncode}")

    dist = REPO_ROOT / "dist"
    if onedir:
        artifact = dist / EXE_NAME
    else:
        artifact = dist / (EXE_NAME + (".exe" if sys.platform == "win32" else ""))
    if not artifact.exists():
        raise FileNotFoundError(f"Expected output not found: {artifact}")
    return artifact


def _sep() -> str:
    """Return the PyInstaller --add-data separator for the current platform."""
    return ";" if sys.platform == "win32" else ":"


def main() -> int:
    onedir = "--onedir" in sys.argv
    try:
        artifact = build(onedir=onedir)
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"\nBuild complete: {artifact}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
