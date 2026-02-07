from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def _run(command: list[str], cwd: Path) -> int:
    result = subprocess.run(command, cwd=cwd, check=False)
    return result.returncode


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _lint_python(root: Path) -> int:
    python = sys.executable
    steps = [
        [python, "-m", "ruff", "check", "."],
        [python, "-m", "mypy", "src", "tests", "tools"],
        [python, "tools/lint_repo.py"],
    ]
    for command in steps:
        exit_code = _run(command, cwd=root)
        if exit_code != 0:
            return exit_code
    return 0


def _lint_web(root: Path) -> int:
    if shutil.which("npm") is None:
        print("FAIL: npm not found; install Node.js to run web linting")
        return 1
    return _run(["npm", "run", "lint:web"], cwd=root)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run repo lint checks.")
    parser.add_argument(
        "--with-web",
        action="store_true",
        help="Include HTML/CSS/JS linting (requires Node.js tooling).",
    )
    args = parser.parse_args()

    root = _repo_root()
    exit_code = _lint_python(root)
    if exit_code != 0:
        return exit_code
    if args.with_web:
        return _lint_web(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
