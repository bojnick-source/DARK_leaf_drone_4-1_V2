#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "tools" / "repo_facts.yaml"


def _format_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return repr(value)
    return json.dumps(str(value))


def _dump_yaml(data: Any, indent: int = 0) -> list[str]:
    lines: list[str] = []
    pad = " " * indent
    if isinstance(data, dict):
        for key in sorted(data.keys()):
            value = data[key]
            if isinstance(value, (dict, list)):
                lines.append(f"{pad}{key}:")
                lines.extend(_dump_yaml(value, indent + 2))
            else:
                lines.append(f"{pad}{key}: {_format_scalar(value)}")
        return lines
    if isinstance(data, list):
        for item in data:
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}-")
                lines.extend(_dump_yaml(item, indent + 2))
            else:
                lines.append(f"{pad}- {_format_scalar(item)}")
        return lines
    lines.append(f"{pad}{_format_scalar(data)}")
    return lines


def _build_facts(repo_root: Path) -> dict[str, Any]:
    return {
        "generated_by": "tools/generate_repo_facts.py",
        "generated_at": "1970-01-01T00:00:00Z",
        "repo": {
            "name": repo_root.name,
            "root": ".",
            "workflows": [
                {"path": ".github/workflows/ci.yaml", "purpose": "python-ci"},
                {"path": ".github/workflows/ci.yml", "purpose": "cmake-ci"},
            ],
        },
        "verification": {
            "python": {
                "install": "python -m pip install .[dev]",
                "lint": "python -m ruff check .",
                "type_check": "python -m mypy src",
                "tests": "python -m pytest",
                "mathlib_validate": (
                    "python3 tools/validate_mathlib_v0.py manufacturing/mathlib_v0.yaml"
                ),
            },
            "cmake": {
                "configure_off": "cmake -S . -B build -DENABLE_V2_ENGINE=OFF",
                "configure_on": "cmake -S . -B build -DENABLE_V2_ENGINE=ON",
                "build": "cmake --build build",
                "test": "ctest --test-dir build",
            },
        },
        "aero_metrics_contract": {
            "version_prefix": "AERO_METRICS_1.",
            "required_fields": ["contract_version", "allowlist", "metrics", "tripwires"],
            "metric_fields": ["name", "value"],
            "tripwire_fields": ["id", "metric", "min_allowed", "max_allowed"],
            "allowlist_required": True,
        },
    }


def _render_yaml(data: dict[str, Any]) -> str:
    return "\n".join(_dump_yaml(data)) + "\n"


def _write_output(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _check_output(path: Path, content: str) -> bool:
    if not path.exists():
        return False
    return path.read_text(encoding="utf-8") == content


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate repo facts YAML.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--check", action="store_true", help="Verify repo_facts.yaml is up-to-date."
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    data = _build_facts(repo_root)
    content = _render_yaml(data)

    if args.check:
        if not _check_output(args.output, content):
            print("repo_facts.yaml is out of date; re-run tools/generate_repo_facts.py")
            return 1
        print("repo_facts.yaml is up to date")
        return 0

    _write_output(args.output, content)
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
