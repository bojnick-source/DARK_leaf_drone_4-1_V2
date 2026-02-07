from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import json
import os
import subprocess
from pathlib import Path


@dataclass
class SolverResult:
    objective: float
    metadata: dict[str, Any]


def _fallback_geometry(volume_fraction: float) -> dict[str, Any]:
    """Fallback geometry backend using an analytic SDF placeholder."""
    resolution = 16
    field = [
        [
            math.hypot(i - resolution / 2, j - resolution / 2)
            for j in range(resolution)
        ]
        for i in range(resolution)
    ]
    return {"resolution": resolution, "field": field, "volume_fraction": volume_fraction}


def _cpp_precision_objective(sample: dict[str, float], benchmark_id: str) -> float | None:
    if os.environ.get("TOPOPT_PRECISION_BACKEND", "").lower() != "cpp":
        return None

    root = Path(__file__).resolve().parents[3]
    candidates = [
        root / "build_on" / "topopt_precision",
        root / "build_off" / "topopt_precision",
        root / "build-ON" / "topopt_precision",
        root / "build-OFF" / "topopt_precision",
    ]
    binary = next((path for path in candidates if path.exists()), None)
    if binary is None:
        return None

    length = sample.get("length", 1.0)
    height = sample.get("height", 0.3)
    force = sample.get("tip_force", 1000.0)
    modulus = sample.get("youngs_modulus", 2.1e11)
    result = subprocess.run(
        [str(binary), str(length), str(height), str(force), str(modulus), benchmark_id],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout.strip())
    return float(payload["objective"])


def evaluate_sample(sample: dict[str, float], benchmark_id: str) -> SolverResult:
    """Analytic proxy solver for CI-small benchmarks."""
    length = sample.get("length", 1.0)
    height = sample.get("height", 0.3)
    force = sample.get("tip_force", 1000.0)
    modulus = sample.get("youngs_modulus", 2.1e11)

    geometry = _fallback_geometry(volume_fraction=0.4)

    cpp_objective = _cpp_precision_objective(sample, benchmark_id)
    if cpp_objective is None:
        compliance = (force * length) / (modulus * height)
        if benchmark_id == "mbb":
            objective = compliance * 1.1
        elif benchmark_id == "cantilever":
            objective = compliance * 1.0
        else:
            objective = compliance * 1.2
    else:
        objective = cpp_objective

    return SolverResult(
        objective=float(objective),
        metadata={
            "geometry_backend": "sdf-marching-cubes-placeholder",
            "geometry": geometry,
            "benchmark_id": benchmark_id,
            "precision_backend": "cpp" if cpp_objective is not None else "python",
        },
    )
