"""Bridge between the Python CLI and the C++ ``v2_engine_cli`` binary.

The C++ engine is optional.  When the binary is available the Python CLI can
invoke it, capture the JSON it emits on stdout, and archive the result
alongside the rest of the build evidence.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Optional


def find_engine_cli(hint: Optional[str] = None) -> Optional[str]:
    """Return the path to ``v2_engine_cli`` or *None* if it is not available.

    *hint* may be an explicit path supplied by the user (``--engine-cli``).
    When omitted the function looks on ``$PATH``.
    """
    if hint:
        path = Path(hint)
        if path.is_file():
            return str(path)
        return None
    return shutil.which("v2_engine_cli")


def run_engine(
    engine_cli: str,
    canonical_input: str,
    artifact_root: Optional[str] = None,
    *,
    no_write: bool = False,
) -> dict[str, Any]:
    """Invoke the C++ engine and return its JSON output as a dict.

    Raises ``RuntimeError`` when the engine exits with a non-zero code or
    emits output that cannot be parsed as JSON.
    """
    cmd = [engine_cli, "--canonical-input", canonical_input]
    if artifact_root:
        cmd.extend(["--artifact-root", artifact_root])
    if no_write:
        cmd.append("--no-write")

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError as exc:
        raise RuntimeError(f"v2_engine_cli not found: {engine_cli}") from exc

    if proc.returncode != 0:
        raise RuntimeError(
            f"v2_engine_cli exited with code {proc.returncode}: {proc.stderr.strip()}"
        )

    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"v2_engine_cli produced invalid JSON: {exc}") from exc
