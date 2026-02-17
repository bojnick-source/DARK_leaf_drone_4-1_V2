from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def basic_environment() -> dict[str, Any]:
    return {
        "python": sys.version.replace("\n", " "),
        "platform": platform.platform(),
        "executable": sys.executable,
    }


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def hash_outputs(paths: dict[str, str]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for k, p in paths.items():
        if not os.path.exists(p):
            raise FileNotFoundError(p)
        out[k] = {"path": p, "sha256": sha256_file(p)}
    return out


@dataclass
class RunManifest:
    schema_version: int
    run_id: str
    created_at: str
    command: str
    config: dict[str, Any]
    environment: dict[str, Any]
    outputs: dict[str, Any]


def write_manifest(path: str, manifest: RunManifest) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(asdict(manifest), f, indent=2, sort_keys=False)
        f.write("\n")
    os.replace(tmp, path)
