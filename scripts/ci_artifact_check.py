#!/usr/bin/env python3
import json
import pathlib
import sys
from typing import Any

SCHEMA_MAP = {
    "build_report.json": "schemas/ci/build_report.schema.json",
    "test_report.json": "schemas/ci/test_report.schema.json",
    "import_audit.json": "schemas/ci/import_audit.schema.json",
    "perf_report.json": "schemas/ci/perf_report.schema.json",
    "skip_report.json": "schemas/ci/skip_report.schema.json",
    "repo_check.json": "schemas/ci/repo_check.schema.json",
}


def _check_type(value: Any, schema_type: str) -> bool:
    if schema_type == "object":
        return isinstance(value, dict)
    if schema_type == "array":
        return isinstance(value, list)
    if schema_type == "string":
        return isinstance(value, str)
    if schema_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if schema_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if schema_type == "boolean":
        return isinstance(value, bool)
    return True


def _validate(data: Any, schema: dict[str, Any], errors: list[str], path: str) -> None:
    schema_type = schema.get("type")
    if schema_type and not _check_type(data, schema_type):
        errors.append(f"{path}: expected {schema_type}")
        return

    if isinstance(data, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in data:
                errors.append(f"{path}: missing required key {key}")
        properties = schema.get("properties", {})
        for key, subschema in properties.items():
            if key in data:
                _validate(data[key], subschema, errors, f"{path}.{key}")


def main() -> int:
    root = pathlib.Path.cwd()
    errors: list[str] = []

    for filename, schema_path in SCHEMA_MAP.items():
        target = root / "ci_out" / filename
        if not target.exists():
            errors.append(f"Missing artifact: {target}")
            continue
        data = json.loads(target.read_text(encoding="utf-8"))
        schema = json.loads((root / schema_path).read_text(encoding="utf-8"))
        _validate(data, schema, errors, filename)

    if errors:
        print("ci_artifact_check failed:")
        print("\n".join(errors))
        return 1
    print("ci_artifact_check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
