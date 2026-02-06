#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Iterable

tomllib: ModuleType | None
try:
    import tomllib as _tomllib
except ImportError:  # pragma: no cover - py311+ only
    tomllib = None
else:
    tomllib = _tomllib

yaml: ModuleType | None
try:
    import yaml as _yaml
except ImportError:  # pragma: no cover - handled in runtime
    yaml = None
else:
    yaml = _yaml

EXCLUDE_DIRS = {
    ".git",
    ".venv",
    ".vscode",
    "build",
    "build_on",
    "build_off",
    "build-ON",
    "build-OFF",
    "external",
    "node_modules",
}

LINT_EXTENSIONS = {
    ".json",
    ".yaml",
    ".yml",
    ".toml",
}


def _iter_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in EXCLUDE_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in LINT_EXTENSIONS:
            continue
        yield path


def _lint_json(path: Path) -> str | None:
    try:
        json.loads(path.read_text(encoding="utf-8"))
        return None
    except json.JSONDecodeError as exc:
        return f"JSON parse error: {exc}"


def _lint_yaml(path: Path) -> str | None:
    if yaml is None:
        return "PyYAML missing; install with 'python -m pip install PyYAML'"
    try:
        yaml.safe_load(path.read_text(encoding="utf-8"))
        return None
    except yaml.YAMLError as exc:
        return f"YAML parse error: {exc}"


def _lint_toml(path: Path) -> str | None:
    if tomllib is None:
        return "tomllib missing; use Python 3.11+"
    try:
        tomllib.loads(path.read_text(encoding="utf-8"))
        return None
    except ValueError as exc:
        return f"TOML parse error: {exc}"


def _lint_file(path: Path) -> str | None:
    suffix = path.suffix.lower()
    if suffix == ".json":
        return _lint_json(path)
    if suffix in {".yaml", ".yml"}:
        return _lint_yaml(path)
    if suffix == ".toml":
        return _lint_toml(path)
    return None


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors: list[tuple[str, str]] = []
    for path in _iter_files(root):
        message = _lint_file(path)
        if message is not None:
            rel_path = path.relative_to(root).as_posix()
            errors.append((rel_path, message))
    if errors:
        for rel_path, message in sorted(errors):
            print(f"FAIL: {rel_path} -> {message}")
        return 1
    print("PASS: repo lint checks for JSON/YAML/TOML")
    return 0


if __name__ == "__main__":
    sys.exit(main())
