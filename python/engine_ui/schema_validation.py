from __future__ import annotations

import json
import importlib
import importlib.util
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, List


@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str]

    @property
    def missing_fields(self) -> List[str]:
        missing = []
        for error in self.errors:
            if "is a required property" in error:
                missing.append(error.split("'")[1])
        return sorted(set(missing))


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_payload(payload: Any, schema: Any) -> ValidationResult:
    if importlib.util.find_spec("jsonschema"):
        jsonschema = importlib.import_module("jsonschema")
        validator = jsonschema.Draft202012Validator(schema)
        errors = sorted(validator.iter_errors(payload), key=lambda err: err.path)
        formatted = [format_error(error) for error in errors]
        return ValidationResult(is_valid=not formatted, errors=formatted)
    formatted = basic_validate(payload, schema)
    return ValidationResult(is_valid=not formatted, errors=formatted)


def format_error(error) -> str:
    path = "/".join(str(item) for item in error.path) or "<root>"
    return f"{path}: {error.message}"


def basic_validate(payload: Any, schema: Any) -> List[str]:
    errors: List[str] = []
    _validate_against_schema(payload, schema, errors, path="<root>")
    return errors


def _validate_against_schema(value: Any, schema: Any, errors: List[str], path: str) -> None:
    expected_type = schema.get("type")
    if expected_type:
        if not _matches_type(value, expected_type):
            errors.append(f"{path}: expected {expected_type} but got {type(value).__name__}")
            return

    if isinstance(value, dict):
        required = schema.get("required", [])
        for field in required:
            if field not in value:
                errors.append(f"{path}: '{field}' is a required property")

        properties = schema.get("properties", {})
        for key, subschema in properties.items():
            if key in value:
                _validate_against_schema(value[key], subschema, errors, path=f"{path}/{key}")

        if schema.get("additionalProperties") is False:
            extra = set(value.keys()) - set(properties.keys())
            for key in sorted(extra):
                errors.append(f"{path}: additional property '{key}' is not allowed")

    if isinstance(value, list):
        items_schema = schema.get("items")
        if items_schema:
            for idx, item in enumerate(value):
                _validate_against_schema(item, items_schema, errors, path=f"{path}/{idx}")


def _matches_type(value: Any, expected_type: str) -> bool:
    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected_type == "boolean":
        return isinstance(value, bool)
    return True


def validate_payload_file(payload_path: Path, schema_path: Path) -> ValidationResult:
    payload = load_json(payload_path)
    schema = load_json(schema_path)
    return validate_payload(payload, schema)


def summarize_errors(errors: Iterable[str]) -> str:
    if not errors:
        return "Validation passed."
    return "Validation failed:\n" + "\n".join(f"- {error}" for error in errors)
