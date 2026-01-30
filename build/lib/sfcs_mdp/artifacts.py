from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

PLACEHOLDERS = {"build_id", "REV_TAG", "lot_id", "ncr_id"}


def expand_placeholders(text: str, values: dict[str, str]) -> str:
    expanded = text
    for key, value in values.items():
        expanded = expanded.replace(f"<{key}>", value)
    return expanded


def normalize_optional_name(name: str) -> tuple[str, bool]:
    marker = " (if applicable)"
    if name.endswith(marker):
        return name[: -len(marker)], True
    return name, False


def safe_relative_path(path: str) -> PurePosixPath:
    pure_path = PurePosixPath(path)
    if pure_path.is_absolute():
        raise ValueError(f"Absolute paths are not allowed: {path}")
    if ".." in pure_path.parts:
        raise ValueError(f"Path traversal is not allowed: {path}")
    return pure_path


def resolve_path(root: Path, relative_path: str) -> Path:
    safe_path = safe_relative_path(relative_path)
    return root.joinpath(*safe_path.parts)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_yaml(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def create_placeholder_file(path: Path, content: str = "") -> None:
    write_text(path, content)


def create_placeholder_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
