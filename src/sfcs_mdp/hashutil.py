from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable


def sha256_bytes(data: bytes) -> str:
    digest = hashlib.sha256()
    digest.update(data)
    return digest.hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_files(paths: Iterable[Path], base_dir: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in paths:
        if path.is_file():
            relative = path.relative_to(base_dir).as_posix()
            hashes[relative] = sha256_file(path)
    return hashes
