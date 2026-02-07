#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, List, Tuple

try:
    import yaml  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover - handled in runtime
    yaml = None

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
EXPECTED_SPEC_RELATIVE = "manufacturing/mathlib_v0.yaml"


def _print_pyyaml_hint() -> None:
    print('FAIL: / -> PyYAML missing; install with "python -m pip install PyYAML"')


def _load_yaml(path: Path) -> Tuple[Any | None, str | None]:
    if yaml is None:
        _print_pyyaml_hint()
        sys.exit(1)
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")), None
    except FileNotFoundError:
        return None, f"File not found: {path.as_posix()}"
    except yaml.YAMLError as exc:
        message = f"YAML parse error in {path.as_posix()}: {exc}"
        return None, message


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
        _add_error(errors, "/", f"File not found: {path}")
        return errors
    data, parse_error = _load_yaml(path)
    if parse_error is not None:
        _add_error(errors, "/", parse_error)
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
    if output_path.endswith(EXPECTED_SPEC_RELATIVE):
        output_path = EXPECTED_SPEC_RELATIVE
    print(f"PASS: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
