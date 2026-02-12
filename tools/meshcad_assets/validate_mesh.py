#!/usr/bin/env python3
"""CLI tool for mesh validation.

Usage::

    python tools/meshcad_assets/validate_mesh.py path/to/mesh.stl
    python tools/meshcad_assets/validate_mesh.py mesh.stl --output report.json

Exit codes:

- 0  mesh passes all validation checks
- 1  mesh has one or more validation failures
- 2  input/parse error
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure the *src/* directory is importable when running directly.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_DIR = _REPO_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from reidce.mesh_validator import IndexedMesh, validate_mesh  # noqa: E402


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate an ASCII STL mesh and report quality metrics.",
    )
    parser.add_argument(
        "stl_file",
        type=Path,
        help="Path to an ASCII STL file.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Write the JSON report to this file (default: stdout).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    stl_path: Path = args.stl_file
    if not stl_path.exists():
        print(f"error: file not found: {stl_path}", file=sys.stderr)
        return 2

    try:
        text = stl_path.read_text(encoding="utf-8")
    except Exception as exc:
        print(f"error: cannot read file: {exc}", file=sys.stderr)
        return 2

    mesh = IndexedMesh.from_stl_text(text)
    if not mesh.faces:
        print("error: no triangles found in STL file", file=sys.stderr)
        return 2

    result = validate_mesh(mesh)
    report_json = result.to_json()

    if args.output is not None:
        args.output.write_text(report_json + "\n", encoding="utf-8")
        print(f"Report written to {args.output}")
    else:
        print(report_json)

    if not result.is_valid:
        problems: list[str] = []
        if not result.is_watertight:
            problems.append(f"not watertight ({result.boundary_edge_count} boundary edges)")
        if not result.is_manifold:
            problems.append(
                f"not manifold ({result.non_manifold_edge_count} non-manifold edges)"
            )
        if result.degenerate_count:
            problems.append(f"{result.degenerate_count} degenerate face(s)")
        if not result.normals_consistent:
            problems.append("inconsistent normals")
        print(f"\nVALIDATION FAILED: {'; '.join(problems)}", file=sys.stderr)
        return 1

    print("\nVALIDATION PASSED", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
