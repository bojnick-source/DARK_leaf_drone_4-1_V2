#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, List, Tuple

EXPECTED_KEYS = [
    "meta",
    "units",
    "conventions",
    "variable_registry",
    "models",
    "research_sources",
    "tripwires",
]
EXPECTED_TITLE = "MANUFACTURING MATHLIB V0"


def _print_pyyaml_hint() -> None:
    print('FAIL: / -> PyYAML missing; install with "python -m pip install PyYAML"')


def _load_yaml(path: Path) -> Any:
    try:
        import yaml  # type: ignore
    except ImportError:
        _print_pyyaml_hint()
        sys.exit(1)
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except Exception as exc:  # noqa: BLE001
        return exc


def _add_error(errors: List[Tuple[str, str]], path: str, message: str) -> None:
    errors.append((path, message))


def _validate_top_level(data: Any, errors: List[Tuple[str, str]]) -> None:
    if not isinstance(data, dict):
        _add_error(errors, "/", "top-level document must be a mapping")
        return
    actual_keys = set(data.keys())
    expected_keys = set(EXPECTED_KEYS)
    for key in sorted(expected_keys - actual_keys):
        _add_error(errors, f"/{key}", "missing key")
    for key in sorted(actual_keys - expected_keys):
        _add_error(errors, f"/{key}", "unexpected key")


def _validate_meta_title(data: Any, errors: List[Tuple[str, str]]) -> None:
    if not isinstance(data, dict):
        return
    meta = data.get("meta")
    if not isinstance(meta, dict):
        _add_error(errors, "/meta", "must be a mapping")
        return
    title = meta.get("title")
    if not isinstance(title, str) or not title.strip():
        _add_error(errors, "/meta/title", "must be a non-empty string")
        return
    if title != EXPECTED_TITLE:
        _add_error(errors, "/meta/title", f'must equal "{EXPECTED_TITLE}"')


def validate_mathlib(path: Path) -> List[Tuple[str, str]]:
    errors: List[Tuple[str, str]] = []
    if not path.is_file():
        _add_error(errors, "/", f"file not found: {path}")
        return errors
    data = _load_yaml(path)
    if isinstance(data, Exception):
        _add_error(errors, "/", f"YAML parse error: {data}")
        return errors
    if data is None:
        _add_error(errors, "/", "YAML document is empty or unreadable")
        return errors
    _validate_top_level(data, errors)
    _validate_meta_title(data, errors)
    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("FAIL: / -> usage: python3 tools/validate_mathlib_v0.py <path>")
        return 1
    path = Path(sys.argv[1])
    errors = validate_mathlib(path)
    if errors:
        for path_str, message in sorted(errors):
            print(f"FAIL: {path_str} -> {message}")
        return 1
    output_path = path.as_posix()
    if output_path.endswith("manufacturing/mathlib_v0.yaml"):
        output_path = "manufacturing/mathlib_v0.yaml"
    print(f"PASS: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
