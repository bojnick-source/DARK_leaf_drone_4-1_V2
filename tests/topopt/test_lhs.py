import importlib
import importlib.util
import os
import statistics
import sys

import pytest

from topopt.uq.lhs import VariableSpec, batch_samples, generate_lhs
from topopt.uq.metrics import min_pairwise_distance


def _default_vars():
    return [
        VariableSpec("x", "uniform", {"low": 0.0, "high": 1.0}),
        VariableSpec("y", "normal", {"mean": 0.0, "std": 1.0}),
    ]


def test_lhs_stratification_union_level():
    result = generate_lhs(12, _default_vars(), seed=123, maximin=True, attempts=5)
    unit = result["unit_samples"]
    n = len(unit)
    dims = len(unit[0])
    for dim in range(dims):
        bins = [min(int(row[dim] * n), n - 1) for row in unit]
        assert len(set(bins)) == n


def test_lhs_reproducibility():
    result_a = generate_lhs(8, _default_vars(), seed=42, maximin=True, attempts=3)
    result_b = generate_lhs(8, _default_vars(), seed=42, maximin=True, attempts=3)
    assert result_a["unit_samples"] == result_b["unit_samples"]


def test_lhs_marginal_checks():
    result = generate_lhs(200, _default_vars(), seed=7, maximin=False, attempts=1)
    samples = result["samples"]
    uniform = samples["x"]
    normal = samples["y"]
    assert abs(statistics.fmean(uniform) - 0.5) < 0.1
    assert abs(statistics.fmean(normal) - 0.0) < 0.2


def test_lhs_maximin_improves_min_distance():
    base = generate_lhs(20, _default_vars(), seed=1, maximin=False, attempts=1)
    improved = generate_lhs(20, _default_vars(), seed=1, maximin=True, attempts=10)
    assert min_pairwise_distance(improved["unit_samples"]) >= min_pairwise_distance(
        base["unit_samples"]
    )


def test_lhs_batching_fixed_schedule():
    result = generate_lhs(10, _default_vars(), seed=11, maximin=True, attempts=3)
    batches = batch_samples(result["samples"], batch_size=4)
    assert len(batches) == 3
    assert len(batches[0]["x"]) == 4
    assert len(batches[-1]["x"]) == 2


def test_metrics_present_and_reasonable():
    result = generate_lhs(16, _default_vars(), seed=5, maximin=True, attempts=5)
    metrics = result["metrics"]
    assert metrics["min_pairwise_distance"] > 0.0
    assert 0.0 <= metrics["max_abs_correlation"] <= 1.0
    assert metrics["centered_l2_discrepancy"] >= 0.0


def test_build_off_disallows_numpy_import():
    if os.environ.get("TOPOPT_BUILD_MODE") != "OFF":
        pytest.skip(
            "missing build_off mode: enable by setting TOPOPT_BUILD_MODE=OFF; affects VERIFIED status if build_off required."
        )
    try:
        importlib.import_module("numpy")
    except Exception:
        return
    pytest.fail("NumPy must not be importable in build_off mode.")


def test_build_off_forbidden_modules_not_loaded():
    if os.environ.get("TOPOPT_BUILD_MODE") != "OFF":
        pytest.skip(
            "missing build_off mode: enable by setting TOPOPT_BUILD_MODE=OFF; affects VERIFIED status if build_off required."
        )
    forbidden_prefixes = ("numpy", "scipy", "pandas")
    loaded = [name for name in list(sys.modules) if name.startswith(forbidden_prefixes)]
    assert not loaded


def test_build_off_optional_heavy_not_loaded():
    if os.environ.get("TOPOPT_BUILD_MODE") != "OFF":
        pytest.skip(
            "missing build_off mode: enable by setting TOPOPT_BUILD_MODE=OFF; affects VERIFIED status if build_off required."
        )
    assert "topopt.optional_heavy" not in sys.modules


def test_numpy_backend_agreement_when_available():
    try:
        numpy_spec = importlib.util.find_spec("numpy")
    except ImportError:
        numpy_spec = None
    if numpy_spec is None:
        pytest.skip(
            "missing numpy: enable by installing topopt-full; affects VERIFIED status if build_on required."
        )
    result = generate_lhs(12, _default_vars(), seed=9, maximin=True, attempts=5)
    unit = result["unit_samples"]
    python_min_dist = _pure_python_min_distance(unit)
    metrics = result["metrics"]
    assert abs(metrics["min_pairwise_distance"] - python_min_dist) < 1e-9


def _pure_python_min_distance(samples):
    if len(samples) < 2:
        return 0.0
    min_dist = float("inf")
    for i in range(len(samples)):
        for j in range(i + 1, len(samples)):
            dist_sq = 0.0
            for k in range(len(samples[i])):
                diff = samples[i][k] - samples[j][k]
                dist_sq += diff * diff
            dist = dist_sq**0.5
            if dist < min_dist:
                min_dist = dist
    return min_dist if min_dist != float("inf") else 0.0
